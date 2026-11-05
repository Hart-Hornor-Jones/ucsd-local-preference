"""Render check for index.html: open the page in headless Chromium through Playwright, exercise
every select, button, slider, checkbox and radio at least once (including the controls of the
derived plots and the export menus), and fail on any console error, uncaught page error, failed
request or HTTP error response.

    python tests/render_check.py [--screenshot-dir DIR] [--browser PATH] [--page FILE] [--headed]

Needs the `playwright` package and a Chromium it can launch (`python -m playwright install chromium`).
--browser (or the RENDER_CHECK_BROWSER environment variable) points at a Chrome/Chromium binary
when Playwright's own download is not available. Exit status 0 on success, 1 on failure.
"""
import argparse
import csv
import io
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROBLEMS = []
STEPS = 0


def problem(msg):
    if msg in PROBLEMS:
        return
    PROBLEMS.append(msg)
    print("FAIL:", msg)


def step(msg):
    global STEPS
    STEPS += 1
    print(f"  [{STEPS:3d}] {msg}")


class Page:
    """thin wrapper: every interaction marks the element as exercised and waits for the plots to settle"""

    def __init__(self, page):
        self.p = page

    def settle(self, timeout=15000):
        try:
            self.p.wait_for_function("window.chain && chain.every(function(c){return c.plot && c.plot.isSettled();})",
                                     timeout=timeout)
        except PlaywrightError as e:
            problem(f"plots did not settle within {timeout} ms: {e}")
        self.p.wait_for_timeout(40)

    def touch(self, locator):
        locator.evaluate("el => { el.dataset.rcTouched = '1'; }")

    def select(self, selector, value):
        loc = self.p.locator(selector)
        self.touch(loc)
        loc.select_option(value)
        self.settle()

    def click(self, locator):
        self.touch(locator)
        locator.click()
        self.settle()

    def set_range(self, selector, value, event="input"):
        loc = self.p.locator(selector)
        self.touch(loc)
        loc.evaluate("(el, v) => { el.value = v; el.dispatchEvent(new Event('%s', {bubbles: true})); }" % event, str(value))
        self.settle()

    def options(self, selector):
        return self.p.locator(selector).evaluate("el => Array.from(el.options).map(o => o.value)")

    def text(self, selector):
        return self.p.locator(selector).evaluate("el => el.textContent")

    def body_text(self):
        return self.p.evaluate("() => document.body.innerText")

    def no_bad_text(self, where):
        t = self.body_text()
        for bad in ("undefined", "NaN", "[object Object]"):
            if bad in t:
                i = t.find(bad)
                problem(f"'{bad}' appears in the page text after {where}: ...{t[max(0, i - 60):i + 40]!r}...")
        # the pooled periods live at pseudo-years 2026-2032 on the slider; the page must always
        # show them as period labels ("2022–25"), never as the bare pseudo-year
        labels = self.p.evaluate("() => Array.from(document.querySelectorAll('option')).map(o => o.textContent).join('\\n')")
        for src, txt in (("page text", t), ("option labels", labels)):
            m = re.search(r"(?<![\d–-])20(2[6-9]|3[0-2])(?![\d–-])", txt)
            if m:
                i = m.start()
                problem(f"a slider pseudo-year {m.group(0)} is shown as a bare number in the {src} after {where}: "
                        f"...{txt[max(0, i - 70):i + 30]!r}...")

    def untouched(self):
        return self.p.evaluate("""() => {
            var sel = 'select, button, [role=button], input[type=range], input[type=checkbox], input[type=radio]';
            var out = [];
            document.querySelectorAll(sel).forEach(function(el){
                var r = el.getBoundingClientRect();
                var visible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                if (visible && !el.dataset.rcTouched) out.push((el.tagName + '#' + (el.id || '') + '.' + el.className + ' ' + (el.textContent || '').trim().slice(0, 40)));
            });
            return out;
        }""")


def find_dot(pg, canvas):
    """hover a grid over the canvas until the tooltip shows, then move to a spot whose +-4 px
    neighbors all hit the same dot (the hover radius is wider than the click-to-tag radius);
    return the page coordinates of that spot"""
    box = canvas.bounding_box()
    if not box:
        return None

    def hit(x, y):
        pg.p.mouse.move(x, y)
        shown = pg.p.locator("#tip").evaluate("el => getComputedStyle(el).display !== 'none'")
        return pg.p.locator("#tip .tt-head").evaluate("el => el.textContent") if shown else None

    for fy in range(2, 19):
        for fx in range(2, 19):
            x = box["x"] + box["width"] * fx / 20
            y = box["y"] + box["height"] * fy / 20
            name = hit(x, y)
            if not name:
                continue
            for dx in range(-6, 7, 2):
                for dy in range(-6, 7, 2):
                    cx, cy = x + dx, y + dy
                    if all(hit(cx + ox, cy + oy) == name for ox, oy in ((0, 0), (4, 0), (-4, 0), (0, 4), (0, -4))):
                        hit(cx, cy)
                        return cx, cy
    return None


def download_from(pg, locator, what):
    try:
        with pg.p.expect_download(timeout=20000) as dl:
            pg.click(locator)
        d = dl.value
        path = d.path()
        size = os.path.getsize(path) if path else 0
        print(f"        {what}: {d.suggested_filename} ({size} bytes)")
        if size <= 0:
            problem(f"{what} produced an empty file")
        return d
    except PlaywrightError as e:
        problem(f"{what} did not produce a download: {e}")
        return None


def run(args):
    page_file = Path(args.page).resolve() if args.page else PAGE
    with sync_playwright() as pw:
        launch = {"headless": not args.headed}
        exe = args.browser or os.environ.get("RENDER_CHECK_BROWSER")
        if exe:
            launch["executable_path"] = exe
        browser = pw.chromium.launch(**launch)
        context = browser.new_context(viewport={"width": 1500, "height": 1000}, accept_downloads=True)
        try:
            context.grant_permissions(["clipboard-read", "clipboard-write"])
        except PlaywrightError:
            pass
        page = context.new_page()
        console_errors, console_warnings, page_errors, failed_requests, bad_responses = [], [], [], [], []
        page.on("console", lambda m: (console_errors if m.type == "error" else console_warnings if m.type == "warning" else []).append(m.text))
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("requestfailed", lambda r: failed_requests.append(f"{r.url} ({r.failure})"))
        page.on("response", lambda r: bad_responses.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        pg = Page(page)

        step(f"open {page_file.as_uri()}")
        page.goto(page_file.as_uri(), wait_until="load")
        page.wait_for_function("document.querySelectorAll('#xsel option').length > 0 && document.querySelector('#plots canvas')")
        pg.settle()
        if page.title() != "Admission to UCSD: Trends and Surprises":
            problem(f"unexpected title {page.title()!r}")
        if pg.text("#yearval") != "Period 2018–21":
            problem(f"initial year label is {pg.text('#yearval')!r}, expected 'Period 2018–21'")
        for sel, want in [("#xsel", "ucsd_app_gpa"), ("#ysel", "ucsd_admit"), ("#csel", "local")]:
            got = page.locator(sel).input_value()
            if got != want:
                problem(f"{sel} starts at {got!r}, expected {want!r}")
        n_dots = page.evaluate("() => chain[0].plot.getPoints().length")
        print(f"        {n_dots} dots on the initial plot")
        if n_dots < 100:
            problem(f"only {n_dots} dots on the initial plot")
        pg.no_bad_text("load")
        if args.screenshot_dir:
            Path(args.screenshot_dir).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(args.screenshot_dir) / "01-initial.png"), full_page=True)

        # ---- GUIDE toggle, controls toggle ---------------------------------------------------
        step("GUIDE toggle (open and close)")
        pg.click(page.locator("#guidetog"))
        if not page.locator("p.intro").is_visible():
            problem("the intro did not appear after clicking GUIDE")
        pg.click(page.locator("#guidetog"))
        step("chart-controls toggle on the plot bar (the sidebar starts hidden; open it)")
        if page.locator("#sidebar").is_visible():
            problem("the sidebar is visible before the controls toggle is clicked")
        pg.click(page.locator("#psec-1 .pctl"))
        if not page.locator("#sidebar").is_visible():
            problem("the sidebar did not appear after clicking the controls toggle")

        # ---- every option of the axis selects --------------------------------------------------
        for sel in ("#xsel", "#ysel"):
            opts = pg.options(sel)
            step(f"{sel}: every option ({len(opts)})")
            for v in opts:
                pg.select(sel, v)
                if v.startswith("d:"):
                    span = "#xspan" if sel == "#xsel" else "#yspan"
                    if not page.locator(span).is_visible():
                        problem(f"{span} did not appear for {v}")
            pg.no_bad_text(f"{sel} sweep")
        step("change-over-time span selects (xfrom/xto, yfrom/yto)")
        pg.select("#xsel", "d:ucsd_admit")
        for sel in ("#xfrom", "#xto"):
            opts = pg.options(sel)
            for v in (opts[0], opts[len(opts) // 2], opts[-1]):
                pg.select(sel, v)
        pg.select("#ysel", "d:ucsd_adv")
        for sel in ("#yfrom", "#yto"):
            opts = pg.options(sel)
            for v in (opts[0], opts[len(opts) // 2], opts[-1]):
                pg.select(sel, v)
        pg.no_bad_text("span selects")
        pg.select("#xsel", "ucsd_app_gpa")
        pg.select("#ysel", "ucsd_admit")

        # ---- every option of the color select ---------------------------------------------------
        opts = pg.options("#csel")
        step(f"#csel: every option ({len(opts)})")
        for v in opts:
            pg.select("#csel", v)
        pg.no_bad_text("color sweep")
        pg.select("#csel", "dgroup")

        # ---- the year slider, every position ----------------------------------------------------
        step("year slider: every position 1994-2032")
        for y in range(1994, 2033):
            pg.set_range("#year", y)
            label = pg.text("#yearval")
            if y <= 2025 and label != str(y):
                problem(f"year label for {y} reads {label!r}")
            if y > 2025 and not label.startswith("Period "):
                problem(f"period label for pseudo-year {y} reads {label!r}")
        pg.no_bad_text("year sweep")
        step("coverage note for a measure with a short span (STAR)")
        pg.select("#xsel", "star")
        print("        covnote:", pg.text("#covnote")[:160])
        pg.select("#xsel", "ucsd_app_gpa")
        pg.set_range("#year", 2031)

        # ---- trend line controls ----------------------------------------------------------------
        step("trend line checkbox and the four line types")
        pg.click(page.locator("#trendchk"))
        pg.click(page.locator("#trendchk"))
        for v in ("wols", "xsect", "ols"):
            loc = page.locator(f"input[name=tline][value={v}]")
            if loc.is_visible() and loc.is_enabled():
                pg.click(loc)
            else:
                pg.touch(loc)
                print(f"        line type {v} is not offered for this pair")
        step("equality line (needs the same unit on both axes: two admit rates)")
        eq = page.locator("input[name=tline][value=eq]")
        if eq.is_enabled():
            problem("the equality line is enabled for a GPA-vs-percent pair")
        pg.select("#xsel", "oth_admit")
        if not eq.is_enabled():
            problem("the equality line is disabled for two percentages")
        else:
            pg.click(eq)
            print("        trend stats:", pg.text("#trendstats")[:120])
            pg.click(page.locator("input[name=tline][value=ols]"))
        pg.select("#xsel", "ucsd_app_gpa")
        step("cross-section line (needs 'Change in' on both axes) and its year select")
        xs = page.locator("input[name=tline][value=xsect]")
        if xs.is_enabled():
            problem("the cross-section line is enabled without a change-over-time axis")
        pg.select("#xsel", "d:ucsd_app_gpa")
        pg.select("#ysel", "d:ucsd_admit")
        if not xs.is_enabled():
            problem("the cross-section line is disabled with 'Change in' on both axes")
        else:
            pg.click(xs)
            opts = pg.options("#xsyr")
            print(f"        {len(opts)} cross-section years")
            for v in (opts[0], opts[-1]):
                pg.select("#xsyr", v)
            print("        trend stats:", pg.text("#trendstats")[:120])
            pg.click(page.locator("input[name=tline][value=ols]"))
        pg.select("#xsel", "ucsd_app_gpa")
        pg.select("#ysel", "ucsd_admit")
        stats = pg.text("#trendstats")
        print("        trend stats:", stats[:120])
        if not stats.strip():
            problem("trend statistics are empty with a trend line on")
        pg.no_bad_text("trend controls")

        # ---- motion controls --------------------------------------------------------------------
        step("advanced motion controls")
        pg.click(page.locator("#motiontoggle"))
        pg.set_range("#s-spin", 45)
        pg.set_range("#s-tilt", 30)
        if page.locator("#s-shear").is_enabled():
            pg.set_range("#s-shear", 50)
            pg.set_range("#s-shear", 0)
        else:
            pg.touch(page.locator("#s-shear"))
        pg.set_range("#s-spin", 0)
        pg.set_range("#s-tilt", 0)
        pg.click(page.locator("#motiontoggle"))

        # ---- "more measures" --------------------------------------------------------------------
        step("more measures: show the hidden measures and select each of them")
        before = set(pg.options("#xsel")) | set(pg.options("#csel"))
        pg.click(page.locator("#moretoggle"))
        new_x = [v for v in pg.options("#xsel") if v not in before]
        new_c = [v for v in pg.options("#csel") if v not in before]
        print(f"        {len(new_x)} new axis options, {len(new_c)} new color options")
        if not new_x:
            problem("'more measures' added no axis options")
        for v in new_x:
            pg.select("#xsel", v)
            pg.select("#ysel", v)
        for v in new_c:
            pg.select("#csel", v)
        pg.no_bad_text("more measures")
        pg.select("#xsel", "ucsd_app_gpa")
        pg.select("#ysel", "ucsd_admit")
        pg.select("#csel", "dgroup")
        pg.click(page.locator("#moretoggle"))

        # ---- plot views and the residual chain -----------------------------------------------------
        step("plot 1 views: distribution of X, Y, residuals, joint")
        for v in ("x", "y", "r", "joint"):
            pg.click(page.locator(f"#psec-1 button[data-v={v}]"))
        step("spawn the residual chain (plots 2-4) and exercise their controls")
        for k in (1, 2, 3):
            rj = page.locator(f"#psec-{k} button[data-v=rj]")
            if not rj.is_visible():
                problem(f"the 'joint distribution of residuals' button is not offered on plot {k}")
                break
            pg.click(rj)
            nk = k + 1
            if page.locator(f"#psec-{nk}").count() == 0:
                problem(f"plot {nk} did not appear")
                break
            zsel = page.locator(f"#pc-{nk} select")
            zopts = pg.options(f"#pc-{nk} select")
            print(f"        plot {nk}: {len(zopts)} third-measure options")
            for v in zopts:
                pg.touch(zsel)
                zsel.select_option(v)
                pg.settle()
            pg.touch(zsel)
            zsel.select_option("dist")
            pg.settle()
            chk = page.locator(f"#pc-{nk} input[type=checkbox]")
            pg.click(chk)
            pg.click(chk)
            for v in ("wols", "ols"):
                pg.click(page.locator(f"#pc-{nk} input[type=radio][value={v}]"))
            for v in ("x", "y", "r", "joint"):
                b = page.locator(f"#psec-{nk} button[data-v={v}]")
                if b.is_visible():
                    pg.click(b)
                else:
                    pg.touch(b)
            pg.click(page.locator(f"#psec-{nk} .pctl"))  # the controls toggle on every plot bar
            pg.click(page.locator(f"#psec-{nk} .pctl"))
            pg.no_bad_text(f"plot {nk}")
        if args.screenshot_dir:
            page.screenshot(path=str(Path(args.screenshot_dir) / "02-chain.png"), full_page=True)

        # ---- export menus on every plot ------------------------------------------------------------
        n_plots = page.locator(".plotsec").count()
        step(f"export menus on {n_plots} plots: PNG 2x, PNG 4x, copy, CSV")
        for k in range(1, n_plots + 1):
            sec = f"#psec-{k}"
            exp = page.locator(f"{sec} .pexp")
            pg.click(exp)
            if not page.locator(f"{sec} .pmenu").is_visible():
                problem(f"export menu of plot {k} did not open")
            download_from(pg, page.locator(f"{sec} .pmenu button[data-kind=png2]"), f"plot {k} PNG 2x")
            pg.click(exp)
            download_from(pg, page.locator(f"{sec} .pmenu button[data-kind=png4]"), f"plot {k} PNG 4x")
            pg.click(exp)
            pg.click(page.locator(f"{sec} .pmenu button[data-kind=copy]"))
            page.wait_for_timeout(600)
            print(f"        plot {k} copy note: {pg.text(f'{sec} .pexpnote')!r}")
            pg.click(exp)
            d = download_from(pg, page.locator(f"{sec} .pmenu button[data-kind=csv]"), f"plot {k} CSV")
            if d is not None:
                with open(d.path(), encoding="utf-8") as fh:
                    lines = [ln for ln in fh.read().splitlines() if not ln.startswith("#")]
                rows = list(csv.reader(io.StringIO("\n".join(lines))))
                n_pts = page.evaluate("(k) => chain[k-1].plot.getPoints().length", k)
                if len(rows) - 1 != n_pts:
                    problem(f"plot {k} CSV has {len(rows) - 1} data rows but {n_pts} dots are plotted")
                if not rows or rows[0][:2] != ["school", "ceeb"]:
                    problem(f"plot {k} CSV header is {rows[0][:3] if rows else rows}")
            page.keyboard.press("Escape")
            page.mouse.click(5, 5)  # close the menu by clicking elsewhere

        # ---- untouched-control sweep while the chain is up (the remove buttons come next) -----------
        left = [u for u in pg.untouched() if ".pkill" not in u]
        if left:
            problem("controls never exercised while the chain was up: " + "; ".join(left))

        # ---- remove the derived plots ------------------------------------------------------------------
        step("REMOVE THIS PLOT on the derived plots")
        while page.locator(".pkill").count():
            pg.click(page.locator(".pkill").last)
        if page.locator(".plotsec").count() != 1:
            problem("derived plots did not all disappear")

        # ---- dots: tooltip, tag, clear, zoom --------------------------------------------------------------
        step("hover for a tooltip, click to tag a school, double-click to clear, scroll to zoom")
        canvas = page.locator("#psec-1 canvas")
        pos = find_dot(pg, canvas)
        if pos is None:
            problem("no dot produced a tooltip on plot 1")
        else:
            tip = pg.text("#tip")
            print("        tooltip:", re.sub(r"\s+", " ", tip)[:120])
            page.mouse.click(*pos)
            pg.settle()
            n_sel = page.evaluate("() => Object.keys(selSet).length")
            if n_sel < 1:
                problem("clicking a dot did not tag its school")
            page.mouse.dblclick(*pos)
            pg.settle()
            if page.evaluate("() => Object.keys(selSet).length") != 0:
                problem("double-click did not clear the tagged schools")
            page.mouse.move(*pos)
            page.mouse.wheel(0, -300)
            pg.settle()
            page.mouse.wheel(0, 300)
            pg.settle()
        pg.no_bad_text("dot interactions")
        if args.screenshot_dir:
            page.screenshot(path=str(Path(args.screenshot_dir) / "03-final.png"), full_page=True)

        step("chart-controls toggle: hide and show again")
        pg.click(page.locator("#psec-1 .pctl"))
        if page.locator("#sidebar").is_visible():
            problem("the sidebar did not hide")
        pg.click(page.locator("#psec-1 .pctl"))

        left = pg.untouched()
        if left:
            problem("controls never exercised: " + "; ".join(left))

        # ---- verdict ----------------------------------------------------------------------------------
        for name, items in (("console error", console_errors), ("page error", page_errors),
                            ("failed request", failed_requests), ("HTTP error response", bad_responses)):
            for it in items:
                problem(f"{name}: {it}")
        if console_warnings:
            print(f"  {len(console_warnings)} console warnings (not failures):")
            for w in console_warnings[:10]:
                print("     ", w[:200])
        browser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--screenshot-dir", help="write screenshots here")
    ap.add_argument("--browser", help="path to a Chrome/Chromium binary (default: Playwright's own)")
    ap.add_argument("--page", help="HTML file to open (default: the repository's index.html)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    args = ap.parse_args()
    t0 = time.time()
    try:
        run(args)
    except PlaywrightError as e:
        problem(f"Playwright error: {e}")
    print()
    print(f"{STEPS} steps, {len(PROBLEMS)} problems, {time.time() - t0:.0f} s")
    if PROBLEMS:
        print("FAILED:")
        for p in PROBLEMS:
            print(" -", p)
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
