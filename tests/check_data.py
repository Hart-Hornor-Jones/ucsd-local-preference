"""Integrity checks for the data files of the UCSD local-preference visualizer.

Run from anywhere:  python tests/check_data.py
Needs only the standard library and pandas. Every file is opened with encoding='utf-8'.
Exit status 0 when every check passes, 1 otherwise. Known artifacts of the build are
pinned (their exact counts are asserted) so that a change in either direction is noticed.

What is checked
  1. data/schools.csv     - header, one row per CEEB, code formats, the derived group columns
                            (local, county_cat, dgroup, dband, name) recomputed from the raw columns
  2. data/panel_long.csv  - header, allowed periods, no duplicate keys, every value finite and
                            stored with at most the measure's decimals, CEEBs match schools.csv
  3. README.md            - the file table, the column table and the measure table agree with
                            the files (row counts, columns, labels, units, decimals, year
                            coverage, periods, rows per measure) and with the eras of the build
  4. build/measures_block.js and index.html - the measure dictionary lists exactly the measures
                            in the data (one documented exception), its coverage fields never
                            exclude a year or period the data has, category lists match the data,
                            and both JS blocks are embedded verbatim in index.html
  5. index.html           - the embedded PANEL blob equals the two CSVs, byte for byte, when
                            rebuilt the way build/build_panel.py serializes it
  6. ranges               - percentages within 0-100, flags 0/1, categories in range, counts
                            integers, admits <= applicants
  7. identities           - admit rate, advantage, GPA premium, log-odds and log odds ratios
                            recomputed from the other measures within rounding; the pooled
                            periods recomputed from the single years within rounding;
                            bind_years recomputed from quota_bind
"""
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAILS = []
WARNS = []
PASSED = 0


def check(cond, msg):
    global PASSED
    if cond:
        PASSED += 1
    else:
        FAILS.append(msg)
        print("FAIL:", msg)


def warn(msg):
    WARNS.append(msg)
    print("NOTE:", msg)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ----------------------------------------------------------------------------------------
# constants mirrored from build/build_panel.py and build/measures_block.js
# ----------------------------------------------------------------------------------------
YEARS = list(range(1994, 2026))
ERA_CODES = "ABCDEFG"
ERA_PERIODS = ["era_" + c for c in ERA_CODES]
PERIODS = [str(y) for y in YEARS] + ERA_PERIODS + ["const"]
PSEUDO_YEAR = {"era_" + c: 2026 + i for i, c in enumerate(ERA_CODES)}

# order of measures in the embedded blob (YEARLY then CONST in build_panel.py)
YEARLY_ORDER = [
    "ucsd_admit", "ucsd_exp", "ucsd_adv", "ucsd_exp2", "ucsd_adv2", "ucsd_yield",
    "ucsd_logodds", "ucsd_lor_year", "ucsd_lor_pred", "ucsd_apps", "ucsd_adm",
    "ucsd_app_gpa", "ucsd_adm_gpa", "gpa_prem", "uc_app_gpa", "oth_admit", "ucsd_share",
    "apps_per100", "caaspp", "star", "cahsee", "ctx_upp", "ctx_lcff", "ctx_urg",
    "quota", "apps_per_quota", "quota_bind",
]
CONST_ORDER = ["dist", "local", "county_cat", "dgroup", "dband", "prof_terc", "bind_years", "ctx_size"]
# decimals used when the blob was written (build_panel.py YEARLY/CONST tables)
DECIMALS = {
    "ucsd_admit": 1, "ucsd_exp": 1, "ucsd_adv": 1, "ucsd_exp2": 1, "ucsd_adv2": 1, "ucsd_yield": 1,
    "ucsd_logodds": 2, "ucsd_lor_year": 2, "ucsd_lor_pred": 2, "ucsd_apps": 0, "ucsd_adm": 0,
    "ucsd_app_gpa": 2, "ucsd_adm_gpa": 2, "gpa_prem": 2, "uc_app_gpa": 2, "oth_admit": 1,
    "ucsd_share": 1, "apps_per100": 1, "caaspp": 1, "star": 1, "cahsee": 1, "ctx_upp": 1,
    "ctx_lcff": 0, "ctx_urg": 1, "quota": 1, "apps_per_quota": 2, "quota_bind": 0,
    "dist": 1, "local": 0, "county_cat": 0, "dgroup": 0, "dband": 0, "prof_terc": 0,
    "bind_years": 0, "ctx_size": 0,
}
# measures carried in the data but absent from the page's dictionary (documented in README)
NOT_ON_PAGE = {"ucsd_exp2"}
PCT_MEASURES = ["ucsd_admit", "ucsd_exp", "ucsd_exp2", "ucsd_yield", "oth_admit", "ucsd_share",
                "caaspp", "star", "cahsee", "ctx_upp", "ctx_urg"]
FLAG_MEASURES = ["ctx_lcff", "quota_bind", "local"]
CAT_RANGE = {"county_cat": 5, "dgroup": 5, "dband": 5, "prof_terc": 2}
COUNT_MEASURES = ["ucsd_apps", "ucsd_adm", "ctx_size", "bind_years"]
UNIT_WORDS = {  # dictionary unit code -> the word used in the README measure table
    "pct": "percent", "pts": "percentage points", "lo": "log-odds", "lor": "log odds ratio",
    "nstud": "students", "gpa": "GPA", "gpad": "GPA points", "per100s": "applicants per 100 seniors",
    "seats": "seats", "ratio": "applicants per seat", "flag": "0/1", "mi": "miles",
    "cat": "category code", "yrs": "years", "stud": "students",
}
SCHOOL_COLUMNS = ["ceeb", "school_name", "city", "county", "cds14", "district", "district_name",
                  "local", "dist", "prof_terc", "apps_mean", "g12", "dgroup", "county_cat",
                  "dband", "bind_years", "name"]
COUNTY_ORDER = ["San Diego", "Imperial", "Orange", "Riverside", "Los Angeles"]
DBAND_CUTS = [-1, 10, 20, 30, 60, 100, 10000]


def half_ulp(dec):
    return 0.5 * 10 ** (-dec)


def tol(*decs):
    """rounding tolerance for an identity whose terms were each rounded to `decs` decimals"""
    return sum(half_ulp(d) for d in decs) + 1e-9


# ----------------------------------------------------------------------------------------
# 1. schools.csv
# ----------------------------------------------------------------------------------------
print("== data/schools.csv")
S = pd.read_csv(DATA / "schools.csv", dtype=str, keep_default_na=False, encoding="utf-8")
check(list(S.columns) == SCHOOL_COLUMNS, "schools.csv header differs from the documented columns")
check(S["ceeb"].is_unique, "schools.csv has a duplicated CEEB")
check(S["ceeb"].str.fullmatch(r"\d{6,7}").all(), "CEEB codes are not 6- or 7-digit strings")
check(((S["cds14"] == "") | S["cds14"].str.fullmatch(r"\d{14}")).all(), "cds14 is not 14 digits or blank")
check((S["district"] == S["cds14"].str[:7]).all(), "district is not the first 7 digits of cds14")
check(S["local"].isin(["0", "1"]).all(), "local is not 0/1")
local = S["local"] == "1"
is_sd_imp = S["county"].isin(["San Diego", "Imperial"])
check((local == is_sd_imp).all(), "local flag does not equal (county is San Diego or Imperial)")
exp_cc = S["county"].map(lambda c: str(COUNTY_ORDER.index(c)) if c in COUNTY_ORDER else "5")
check((S["county_cat"] == exp_cc).all(), "county_cat does not follow the documented county coding")


def dgroup(r):
    if r["local"] != "1":
        return "5"
    if r["district"] == "3768411":
        return "0"
    if r["district"] == "3768338":
        return "1"
    if r["county"] == "Imperial":
        return "2"
    if r["district"] in ("3768296", "3768346", "3768213"):
        return "3"
    return "4"


check((S.apply(dgroup, axis=1) == S["dgroup"]).all(), "dgroup does not follow the documented district rule")
dist = pd.to_numeric(S["dist"].replace("", None))
dband_exp = pd.cut(dist, DBAND_CUTS, labels=["0", "1", "2", "3", "4", "5"]).astype(object)
dband_exp = dband_exp.where(dist.notna(), "")
check((S["dband"] == dband_exp.map(lambda v: "" if v == "" else v + ".0")).all(),
      "dband does not follow the documented distance cuts")
check(S["prof_terc"].isin(["", "0.0", "1.0", "2.0"]).all(), "prof_terc outside {blank, 0, 1, 2}")
check(S["dgroup"].isin(list("012345")).all() and S["county_cat"].isin(list("012345")).all(),
      "dgroup or county_cat outside 0-5")
by = pd.to_numeric(S["bind_years"].replace("", None))
check(by.dropna().between(0, 6).all() and (by.dropna() == by.dropna().round()).all(),
      "bind_years is not an integer 0-6")
check((by.isna() | local).all(), "bind_years is set for a non-local school")
apps_mean = pd.to_numeric(S["apps_mean"])
check((apps_mean > 0).all(), "apps_mean is not positive for every school")
g12 = pd.to_numeric(S["g12"].replace("", None))
check((g12.dropna() >= 0).all(), "g12 is negative")
name_exp = (S["school_name"].str.title().str.replace(" High School", " High", regex=False)
            + " (" + S["city"].str.title() + ")")
check((S["name"] == name_exp).all(), "name is not title(school_name) with ' High School' -> ' High' plus (city)")
# rows that share identifiers are documented facts, not failures; report them
n_shared_cds = int(((S["cds14"] != "") & S["cds14"].duplicated(keep=False)).sum())
n_blank_cds = int((S["cds14"] == "").sum())
n_dup_name = int(S["name"].duplicated(keep=False).sum())
print(f"   {len(S)} schools; {int(local.sum())} local; {n_shared_cds} rows share a CDS code with another row; "
      f"{n_blank_cds} rows have no CDS code; {n_dup_name} rows have a display name used twice")

# ----------------------------------------------------------------------------------------
# 2. panel_long.csv
# ----------------------------------------------------------------------------------------
print("== data/panel_long.csv")
L = pd.read_csv(DATA / "panel_long.csv", dtype={"ceeb": str, "period": str, "measure": str, "value": float},
                encoding="utf-8")
check(list(L.columns) == ["ceeb", "period", "measure", "value"], "panel_long.csv header is not ceeb,period,measure,value")
check(L["period"].isin(PERIODS).all(), "panel_long.csv has a period outside 1994-2025, era_A..era_G, const")
check(not L.duplicated(["ceeb", "period", "measure"]).any(), "panel_long.csv has duplicate (ceeb, period, measure) keys")
check(L["value"].map(math.isfinite).all(), "panel_long.csv has a non-finite value")
check(set(L["ceeb"]) == set(S["ceeb"]), "the CEEBs in panel_long.csv and schools.csv differ")
measures = sorted(L["measure"].unique())
check(set(measures) == set(YEARLY_ORDER) | set(CONST_ORDER), "the measures in panel_long.csv are not the expected 35")
for m, dec in DECIMALS.items():
    v = L.loc[L["measure"] == m, "value"] * 10 ** dec
    check(((v - v.round()).abs() < 1e-6).all(), f"{m}: a value has more than {dec} decimals")
is_const = L["measure"].isin(CONST_ORDER)
check((L.loc[is_const, "period"] == "const").all() and (L.loc[~is_const, "period"] != "const").all(),
      "const rows are not exactly the fixed school measures")
W = L.pivot(index=["ceeb", "period"], columns="measure", values="value")
Y = W[W.index.get_level_values("period").str.isdigit()].copy()
Y["yr"] = Y.index.get_level_values("period").astype(int)
E = W[W.index.get_level_values("period").str.startswith("era")]
C = W.xs("const", level="period")
print(f"   {len(L)} rows; {len(measures)} measures; {Y.index.get_level_values('ceeb').nunique()} schools with yearly rows")

# ----------------------------------------------------------------------------------------
# 3. README tables
# ----------------------------------------------------------------------------------------
print("== README.md")
readme = read_text(ROOT / "README.md")


def section(text, title):
    """the text under the heading that contains `title`, up to the next heading"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#") and title in line:
            out = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("#"):
                    break
                out.append(nxt)
            return "\n".join(out)
    return ""


def md_rows(text, first_cell_pattern):
    out = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if re.fullmatch(first_cell_pattern, cells[0]):
            out.append(cells)
    return out


def num(s):
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return -1


file_rows = {r[0].strip("`"): r for r in md_rows(section(readme, "Data dictionary"), r"`data/[^`]+`")}
check("data/schools.csv" in file_rows and num(file_rows["data/schools.csv"][1]) == len(S)
      and num(file_rows["data/schools.csv"][2]) == len(S.columns),
      "README file table: schools.csv rows/columns differ from the file")
check("data/panel_long.csv" in file_rows and num(file_rows["data/panel_long.csv"][1]) == len(L)
      and num(file_rows["data/panel_long.csv"][2]) == len(L.columns),
      "README file table: panel_long.csv rows/columns differ from the file")
col_rows = [r[0].strip("`") for r in md_rows(section(readme, "Columns of `data/schools.csv`"), r"`[a-z0-9_]+`")]
check(col_rows == SCHOOL_COLUMNS, "README column table does not list the schools.csv columns in file order")

# the measure dictionary from build/measures_block.js (also embedded in index.html)
mb = read_text(ROOT / "build" / "measures_block.js")
DICT = {}
for mm in re.finditer(r"\{id:'([a-z0-9_]+)',(.*?)\n\s*label:'(.*?)',\n\s*axis:", mb, re.S):
    mid, head, label = mm.group(1), mm.group(2), mm.group(3)
    f = dict(re.findall(r"(\w+):('[^']*'|\[[^\]]*\]|\w+)", head))
    DICT[mid] = {
        "adv": f["adv"] == "true", "unit": f["unit"].strip("'"), "dec": int(f["dec"]),
        "y0": int(f["y0"]), "y1": int(f["y1"]), "skip": [int(x) for x in f["skip"].strip("[]").split(",") if x],
        "cats": re.findall(r"'([^']*)'", f["cats"]) if "cats" in f else None, "label": label.replace("\\'", "'"),
    }
check(len(DICT) == 34, f"parsed {len(DICT)} dictionary entries from measures_block.js, expected 34")


def coverage(m):
    g = L[L["measure"] == m]
    yrs = sorted(int(p) for p in g["period"].unique() if p.isdigit())
    eras = sorted(p[-1] for p in g["period"].unique() if p.startswith("era"))
    return yrs, eras, len(g)


def years_word(yrs):
    if not yrs:
        return "fixed"
    gaps = [y for y in range(yrs[0], yrs[-1] + 1) if y not in yrs]
    s = f"{yrs[0]}–{yrs[-1]}"
    return s + (" (not " + ", ".join(str(g) for g in gaps) + ")" if gaps else "")


def eras_word(eras, yrs):
    if not yrs:
        return "const"
    if not eras:
        return "none"
    if eras == list(ERA_CODES[ERA_CODES.index(eras[0]):ERA_CODES.index(eras[-1]) + 1]):
        return f"{eras[0]}–{eras[-1]}" if len(eras) > 1 else eras[0]
    return ", ".join(eras)


meas_rows = {r[0].strip("`"): r for r in md_rows(section(readme, "Measures in `data/panel_long.csv`"), r"`[a-z0-9_]+`")}
check(list(meas_rows) == YEARLY_ORDER + CONST_ORDER, "README measure table does not list the 35 measures in blob order")
for m in YEARLY_ORDER + CONST_ORDER:
    if m not in meas_rows:
        continue
    r = meas_rows[m]
    yrs, eras, n = coverage(m)
    d = DICT.get(m)
    label = d["label"] if d else "(not on the page)"
    unit = UNIT_WORDS[d["unit"]] if d else UNIT_WORDS["pct"]
    expect = [label, unit, str(DECIMALS[m]), years_word(yrs), eras_word(eras, yrs), f"{n:,}"]
    got = r[1:7]
    check(got == expect, f"README measure table row for {m}: {got} != {expect}")

# eras: README vs build_panel.py vs measures_block.js
bp = read_text(ROOT / "build" / "build_panel.py")
build_eras = re.findall(r"\((\d{4}),'([A-G])',(\d{4}),(\d{4}),", bp)
check(len(build_eras) == 7 and [e[1] for e in build_eras] == list(ERA_CODES), "build_panel.py does not define eras A-G")
ERA_YEARS = {e[1]: (int(e[2]), int(e[3])) for e in build_eras}
page_eras = dict(re.findall(r"(\d{4}):\['([^']+)'", mb))
era_rows = {r[0]: r for r in md_rows(section(readme, "Periods"), r"[A-G]")}
check(list(era_rows) == list(ERA_CODES), "README era table does not list eras A-G")
for c, (a, b) in ERA_YEARS.items():
    r = era_rows.get(c)
    check(r is not None and r[1] == f"{a}–{b}", f"README era {c} years differ from build_panel.py ({a}-{b})")
    short = f"{a}–{str(b)[2:] if str(a)[:2] == str(b)[:2] else b}"
    check(page_eras.get(str(PSEUDO_YEAR['era_' + c])) == short, f"page era label for {c} is not {short}")
    check(r is not None and r[2] == str(PSEUDO_YEAR["era_" + c]), f"README era {c} pseudo-year differs")

# ----------------------------------------------------------------------------------------
# 4. the measure dictionary against the data
# ----------------------------------------------------------------------------------------
print("== measure dictionary")
html = read_text(ROOT / "index.html")
check(mb in html, "build/measures_block.js is not embedded verbatim in index.html")
check(read_text(ROOT / "build" / "export_block.js") in html, "build/export_block.js is not embedded verbatim in index.html")
check(set(DICT) <= set(measures), "the dictionary lists a measure that is not in the data")
check(set(measures) - set(DICT) == NOT_ON_PAGE, f"measures in the data but not on the page differ from {NOT_ON_PAGE}")
order = re.search(r"var MEASURE_ORDER=\[(.*?)\];", mb, re.S).group(1)
check(set(re.findall(r"'([a-z0-9_]+)'", order)) == set(DICT), "MEASURE_ORDER does not list exactly the dictionary measures")
fam = re.search(r"var FAM_OF=\{(.*?)\};", mb, re.S).group(1)
check(set(re.findall(r"([a-z0-9_]+):'", fam)) == set(DICT), "FAM_OF does not cover exactly the dictionary measures")
delta = re.search(r"var DELTA_IDS=\[(.*?)\];", mb).group(1)
check(set(re.findall(r"'([a-z0-9_]+)'", delta)) <= set(DICT), "DELTA_IDS has an id outside the dictionary")
for m, d in DICT.items():
    yrs, eras, _ = coverage(m)
    valid = {y for y in range(d["y0"], d["y1"] + 1) if y not in d["skip"]}
    have = set(yrs) | {PSEUDO_YEAR["era_" + e] for e in eras}
    check(have <= valid, f"{m}: the dictionary's y0/y1/skip exclude a period the data has")
    check(d["dec"] == DECIMALS[m], f"{m}: dictionary decimals differ from the blob's")
    if d["cats"] is not None:
        check(m in CAT_RANGE and len(d["cats"]) == CAT_RANGE[m] + 1, f"{m}: category list length differs from the data range")
        vals = L.loc[L["measure"] == m, "value"]
        check(set(vals.unique()) == set(float(i) for i in range(CAT_RANGE[m] + 1)) or
              (m == "prof_terc" and set(vals.unique()) <= {0.0, 1.0, 2.0}), f"{m}: category values are not 0..{CAT_RANGE[m]}")

# ----------------------------------------------------------------------------------------
# 5. the embedded PANEL blob equals the CSVs (long form vs the page's wide form)
# ----------------------------------------------------------------------------------------
print("== embedded PANEL blob")
a = html.find("var PANEL=")
b = html.find(";\n", a)
blob = html[a + len("var PANEL="):b]
idx = {c: i for i, c in enumerate(S["ceeb"])}
m_out = {}
for mid in YEARLY_ORDER + CONST_ORDER:
    g = L[L["measure"] == mid]
    dec = DECIMALS[mid]
    sc = 10 ** dec
    if mid in CONST_ORDER:
        vals = [""] * len(S)
        for c, v in zip(g["ceeb"], g["value"]):
            vals[idx[c]] = str(int(round(v * sc)))
        m_out[mid] = {"y0": 1994, "y1": 2032, "dec": dec, "k": 1, "rows": [",".join(vals)]}
    else:
        rows = []
        for p in [str(y) for y in YEARS] + ERA_PERIODS:
            gp = g[g["period"] == p]
            vals = [""] * len(S)
            for c, v in zip(gp["ceeb"], gp["value"]):
                vals[idx[c]] = str(int(round(v * sc)))
            rows.append(",".join(vals))
        m_out[mid] = {"y0": 1994, "y1": 2032, "dec": dec, "rows": rows}
panel = {"names": S["name"].tolist(), "ceeb": S["ceeb"].tolist(),
         "sizes": [int(round(float(v))) for v in S["apps_mean"]], "m": m_out}
rebuilt = json.dumps(panel, separators=(",", ":"))
check(rebuilt == blob, "the PANEL blob embedded in index.html differs from the one rebuilt from the CSVs")
# the fixed school measures in the long file equal the schools.csv columns (rounded as stored)
for col, mid in [("dist", "dist"), ("local", "local"), ("county_cat", "county_cat"), ("dgroup", "dgroup"),
                 ("dband", "dband"), ("prof_terc", "prof_terc"), ("bind_years", "bind_years"), ("g12", "ctx_size")]:
    sv = pd.to_numeric(S[col].replace("", None)).round(DECIMALS[mid])
    cv = C[mid].reindex(S["ceeb"]).reset_index(drop=True)
    check((sv.isna() == cv.isna()).all() and ((sv - cv).abs().fillna(0) < 1e-9).all(),
          f"const measure {mid} differs from schools.csv column {col}")

# ----------------------------------------------------------------------------------------
# 6. ranges
# ----------------------------------------------------------------------------------------
print("== ranges")
for m in PCT_MEASURES:
    v = L.loc[L["measure"] == m, "value"]
    check(v.between(0, 100).all(), f"{m}: a percentage is outside 0-100")
for m in FLAG_MEASURES:
    yv = Y[m].dropna() if m in Y else pd.Series(dtype=float)
    ev = E[m].dropna() if m in E else pd.Series(dtype=float)
    cv = C[m].dropna() if m in C else pd.Series(dtype=float)
    check(yv.isin([0.0, 1.0]).all() and cv.isin([0.0, 1.0]).all(), f"{m}: a single-year or fixed flag is not 0/1")
    check(ev.between(0, 1).all(), f"{m}: a period share is outside 0-1")
for m, hi in CAT_RANGE.items():
    v = C[m].dropna()
    check(v.between(0, hi).all() and (v == v.round()).all(), f"{m}: a category code is outside 0-{hi}")
for m in COUNT_MEASURES:
    v = L.loc[L["measure"] == m, "value"]
    check((v >= 0).all() and (v == v.round()).all(), f"{m}: a count is negative or fractional")
check((Y["ucsd_adm"] <= Y["ucsd_apps"]).where(Y["ucsd_adm"].notna(), True).all(), "admits exceed applicants in a year")
check((E["ucsd_adm"] <= E["ucsd_apps"]).where(E["ucsd_adm"].notna(), True).all(), "admits exceed applicants in a period")
check(Y["ucsd_apps"].min() >= 5 and Y["ucsd_adm"].min() >= 3, "a yearly applicant count below 5 or admit count below 3 appeared (README states the floors)")
check(Y["ucsd_adm"].notna().equals(Y["ucsd_admit"].notna()), "ucsd_adm and ucsd_admit are not present for the same school-years")
check((Y["quota"].notna() & ~Y.index.get_level_values("ceeb").map(lambda c: S.set_index("ceeb").loc[c, "local"] == "1")).sum() == 0,
      "quota is set for a non-local school")
check((Y["ucsd_logodds"].notna() & (Y["ucsd_apps"] < 10)).sum() == 0, "log-odds present with fewer than 10 applicants")
check((Y["ucsd_logodds"].isna() & (Y["ucsd_apps"] >= 10) & Y["ucsd_adm"].notna()).sum() == 0,
      "log-odds missing with 10+ applicants and a published admit count")

# ----------------------------------------------------------------------------------------
# 7. identities within rounding
# ----------------------------------------------------------------------------------------
print("== identities")


def within(name, a, b, t):
    d = (a - b).abs().dropna()
    check((d <= t).all(), f"{name}: max deviation {d.max():.4f} exceeds the rounding tolerance {t:.4f} ({int((d > t).sum())} rows)")


within("ucsd_admit = 100*ucsd_adm/ucsd_apps", Y["ucsd_admit"], 100 * Y["ucsd_adm"] / Y["ucsd_apps"], tol(1))
within("ucsd_adv = ucsd_admit - ucsd_exp", Y["ucsd_adv"], Y["ucsd_admit"] - Y["ucsd_exp"], tol(1, 1, 1))
within("ucsd_adv2 = ucsd_admit - ucsd_exp2", Y["ucsd_adv2"], Y["ucsd_admit"] - Y["ucsd_exp2"], tol(1, 1, 1))
within("gpa_prem = ucsd_adm_gpa - ucsd_app_gpa", Y["gpa_prem"], Y["ucsd_adm_gpa"] - Y["ucsd_app_gpa"], tol(2, 2, 2))
lo = ((Y["ucsd_adm"] + 0.5) / (Y["ucsd_apps"] - Y["ucsd_adm"] + 0.5)).map(math.log)
lo = lo.where(Y["ucsd_apps"] >= 10)
within("ucsd_logodds = ln((adm+.5)/(apps-adm+.5))", Y["ucsd_logodds"], lo, tol(2))
yt = Y.groupby("yr").agg(A=("ucsd_adm", "sum"), N=("ucsd_apps", "sum"))
ylo = (yt["A"] / (yt["N"] - yt["A"])).map(math.log)
within("ucsd_lor_year = logodds - year log-odds", Y["ucsd_lor_year"], Y["ucsd_logodds"] - Y["yr"].map(ylo), tol(2, 2))
pred = Y["ucsd_exp"] * Y["ucsd_apps"] / 100  # predicted admits, recovered from the rounded rate
# the recovered prediction is off by up to apps*0.0005; the log-odds error is bounded by that over the smaller count
lp = ((pred + 0.5) / (Y["ucsd_apps"] - pred + 0.5)).map(math.log)
d = (Y["ucsd_lor_pred"] - (Y["ucsd_logodds"] - lp)).abs()
bound = tol(2, 2) + (0.0005 * Y["ucsd_apps"]) * (1 / (pred + 0.5) + 1 / (Y["ucsd_apps"] - pred + 0.5))
check((d.dropna() <= bound[d.notna()]).all(), "ucsd_lor_pred deviates from logodds - ln(pred odds) beyond rounding")
# applicants per quota: the quota is stored to 0.1, so bracket the ratio
q = Y["quota"]
lo_r = Y["ucsd_apps"] / (q + 0.05 + 1e-12)
hi_r = (Y["ucsd_apps"] / (q - 0.05)).where(q - 0.05 > 0, float("inf"))
ok = Y["apps_per_quota"].isna() | ((Y["apps_per_quota"] >= lo_r - tol(2)) & (Y["apps_per_quota"] <= hi_r + tol(2)))
check(ok.all(), "apps_per_quota is not ucsd_apps/quota within rounding")
check(by.reindex(range(len(S))).fillna(-1).tolist() == C["bind_years"].reindex(S["ceeb"]).fillna(-1).tolist(),
      "bind_years in panel_long.csv differs from schools.csv")
yb = Y[(Y["yr"] >= 1999) & (Y["yr"] <= 2004)].groupby(level="ceeb")["quota_bind"].sum(min_count=1)
within("bind_years = sum of quota_bind over 1999-2004", C["bind_years"], yb.reindex(C.index), 1e-9)
check(C["bind_years"].notna().equals(yb.reindex(C.index).notna()), "bind_years present/absent pattern differs from quota_bind 1999-2004")

# pooled periods recomputed from the single years
n_adv_no_admit = 0
n_lo_no_adm = 0
for code, (a0, b0) in ERA_YEARS.items():
    y = Y[(Y["yr"] >= a0) & (Y["yr"] <= b0)]
    ny = b0 - a0 + 1
    er = E.xs("era_" + code, level="period")
    g = y.groupby(level="ceeb")
    s_apps = g["ucsd_apps"].sum(min_count=1).reindex(er.index)
    s_adm = g["ucsd_adm"].sum(min_count=1).reindex(er.index)
    within(f"era {code} ucsd_apps = sum of years", er["ucsd_apps"], s_apps, 1e-9)
    within(f"era {code} ucsd_adm = sum of years", er["ucsd_adm"], s_adm, 1e-9)
    both = y[y["ucsd_adm"].notna()].groupby(level="ceeb")
    within(f"era {code} ucsd_admit = pooled admits/applicants", er["ucsd_admit"],
           (100 * both["ucsd_adm"].sum() / both["ucsd_apps"].sum()).reindex(er.index), tol(1))
    within(f"era {code} quota = sum of years", er["quota"], g["quota"].sum(min_count=1).reindex(er.index), tol(*([1] * (ny + 1))))
    within(f"era {code} quota_bind = share of years", er["quota_bind"], g["quota_bind"].mean().reindex(er.index), tol(0))
    within(f"era {code} ctx_lcff = share of years", er["ctx_lcff"], g["ctx_lcff"].mean().reindex(er.index), tol(0))
    for m in ["caaspp", "star", "cahsee", "ctx_upp", "ctx_urg"]:
        within(f"era {code} {m} = mean of years", er[m], g[m].mean().reindex(er.index), tol(1, 1))
    for m, w in [("ucsd_app_gpa", "ucsd_apps"), ("ucsd_adm_gpa", "ucsd_adm"), ("gpa_prem", "ucsd_adm"), ("ucsd_share", "ucsd_apps")]:
        yy = y[y[m].notna() & y[w].notna()]
        wm = (yy[m] * yy[w]).groupby(level="ceeb").sum() / yy.groupby(level="ceeb")[w].sum()
        within(f"era {code} {m} = applicant/admit-weighted mean of years", er[m], wm.reindex(er.index), tol(DECIMALS[m], DECIMALS[m]))
    yy = y[y["ucsd_exp"].notna()]
    wm = (yy["ucsd_exp"] * yy["ucsd_apps"]).groupby(level="ceeb").sum() / yy.groupby(level="ceeb")["ucsd_apps"].sum()
    within(f"era {code} ucsd_exp = pooled predicted admits/applicants", er["ucsd_exp"], wm.reindex(er.index), tol(1, 1))
    # advantage: the build sums admits and predicted admits with missing years counted as zero
    pa = y["ucsd_adm"].fillna(0).groupby(level="ceeb").sum()
    pp = (y["ucsd_exp"] * y["ucsd_apps"] / 100).fillna(0).groupby(level="ceeb").sum()
    n = g["ucsd_apps"].sum()
    within(f"era {code} ucsd_adv = 100*(sum adm - sum pred)/sum apps", er["ucsd_adv"], (100 * (pa - pp) / n).reindex(er.index), tol(1, 1))
    plo = ((s_adm + 0.5) / (s_apps - s_adm + 0.5)).map(math.log).where(s_apps >= 10)
    within(f"era {code} ucsd_logodds from pooled counts", er["ucsd_logodds"], plo, tol(2))
    A = y["ucsd_adm"].sum()
    N = y["ucsd_apps"].sum()
    within(f"era {code} ucsd_lor_year from pooled counts", er["ucsd_lor_year"], plo - math.log(A / (N - A)), tol(2))
    n_adv_no_admit += int((er["ucsd_adv"].notna() & er["ucsd_admit"].isna()).sum())
    n_lo_no_adm += int((er["ucsd_logodds"].notna() & er["ucsd_adm"].isna()).sum())

# known artifacts of the pooling (documented in README under "Known limitations"), pinned
print("== known artifacts (pinned)")
x = E[E["ucsd_adv"].notna() & E["ucsd_admit"].isna()]
check(n_adv_no_admit == 664 and (x["ucsd_adv"] == 0).all() and (x["ucsd_adv2"] == 0).all() and x["ucsd_exp"].isna().all(),
      f"period rows with an advantage but no admit rate: {n_adv_no_admit} (expected 664, all exactly 0)")
warn(f"{n_adv_no_admit} period rows carry ucsd_adv = ucsd_adv2 = 0.0 for schools with no published admit "
     "count and no prediction in any year of the period")
x2 = E[E["ucsd_logodds"].notna() & E["ucsd_adm"].isna()]
check(n_lo_no_adm == 340 and (x2["ucsd_logodds"] < 0).all(),
      f"period rows with log-odds but no admit count: {n_lo_no_adm} (expected 340)")
warn(f"{n_lo_no_adm} period rows carry log-odds measures computed with the period's admits taken as 0 "
     "because no year's admit count was published")

# ----------------------------------------------------------------------------------------
print()
print(f"{PASSED} checks passed, {len(FAILS)} failed, {len(WARNS)} notes")
if FAILS:
    print("FAILED:")
    for f in FAILS:
        print(" -", f)
    sys.exit(1)
print("OK")
