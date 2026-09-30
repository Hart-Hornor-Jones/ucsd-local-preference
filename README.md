# UC San Diego and its local high schools: admit rates against expectation, 1994–2025

An interactive visualizer (`index.html`, self-contained, open in any browser) and the school-level
panel behind it. Every dot is one California public high school with freshman applicants to UCSD.
The page is a re-use of the `ca-hs-proficiency` visualizer engine with a new panel and measure
dictionary; the same buttons (joint distribution, distribution of X / Y / residuals, joint
distribution of residuals), tagging, zoom, trend lines and the recursive residual chain all work
the same way.

What is new here:

- **Eras on the year slider.** After the single years 1994–2025 the slider continues through seven
  eras (A–G) whose rows pool their years: 1994–96 (residency points), 1997–98 (residency as a
  qualitative factor), 1999–2004 (the Local 4% Plan), 2005–10 (after the October 2004 BOARS
  ruling), 2011–17 (holistic review, parity), 2018–21 (undocumented blanket local advantage),
  2022–25 (advantage re-targeted to Sweetwater UHSD and Imperial County, then fading).
- **An "expected admit rate" and an "advantage" measure.** Each year a binomial model of UCSD admits
  on a cubic in the school's mean UCSD-applicant GPA is fitted on schools *outside* San Diego and
  Imperial counties; the advantage is the school's admit rate minus that fit's prediction.
- **Group colorings.** The "Color dots by" menu offers fixed school groups: local (yes/no), county,
  district group (Sweetwater Union HSD / San Diego Unified / Imperial County / Poway–San
  Dieguito–Carlsbad / other San Diego County / not local), distance band, proficiency tercile, and
  the number of plan years the 4% quota bound at the school.
- **Export figure.** Each plot's bar has an EXPORT FIGURE menu: PNG at 2× or 4×, copy PNG to the clipboard, or a CSV of the plotted schools (name, CEEB, x, y, fitted value, residual, applicant weight, color group). The export waits for the plot's animation to settle, then re-renders it off-screen at the chosen scale under a title, era line, fit statistics and source line. Width follows the on-screen plot.
- **Local 4% Plan arithmetic.** For local schools: the quota (4% of the previous year's senior
  class), applicants ÷ quota, and whether the quota exceeded the GPA-expected regular admits.

The reading the page is built to show: fit the trend line on admit rate vs applicant GPA, open the
residual views, color by a group, and step through the eras. Local schools sit above the line in
1997–98 (broadly), in 1999–2004 (only the low-proficiency, quota-binding schools), in 2018–21
(everywhere, most at the affluent north-county districts), and in 2022–24 (Sweetwater and Imperial
County only); they sit below it in 2005–10.

## Files

| file | what it is |
|---|---|
| `index.html` | the visualizer (all data embedded) |
| `data/panel_long.csv` | `ceeb, period, measure, value` — periods are 1994–2025, `era_A`…`era_G`, or `const` |
| `data/schools.csv` | one row per school: CEEB, CDS, name, city, county, district, local flag, distance to UCSD, groups |
| `build/build_panel.py` | builds the panel from the 2026-09-29 analysis folder, the ca-hs-proficiency panel, CDE enrollment and coordinates |
| `build/measures_block.js`, `build/splice_page.py` | the measure dictionary and the script that assembles `index.html` from the ca-hs-proficiency page |
| `build/export_block.js`, `build/splice_export.py` | the export-figure code and the second build step that adds it (run after `splice_page.py`) |

Sources and methods: the three memos in `Svetlana\UCSD Local Preference 2026-09-29\`
(estimate and baseline; data tests of the documented mechanisms; scope of selection).
Private local schools, which the plan also covered, are not in UC's public-school data.
