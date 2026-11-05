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
| `index.html` | the visualizer (all data embedded; the embedded panel is byte-for-byte what the two CSVs below describe) |
| `data/panel_long.csv` | `ceeb, period, measure, value` — periods are 1994–2025, `era_A`…`era_G`, or `const`; 35 measures, listed in the data dictionary below |
| `data/schools.csv` | one row per school (keyed by CEEB): names, CDS code, city, county, district, local flag, distance to UCSD, mean applicants, mean grade-12 enrollment, and the fixed group codes; columns listed below |
| `build/build_panel.py` | builds the panel from the 2026-09-29 analysis folder, the ca-hs-proficiency panel, the uc-merit-admissions panel and school coordinates, and a CDE enrollment file; none of these inputs is in this repository, so it cannot be re-run from here |
| `build/measures_block.js`, `build/splice_page.py` | the measure dictionary and the script that assembles `index.html` from the ca-hs-proficiency page and `build/panel_blob.json` (the wide form of `panel_long.csv`, not committed) |
| `build/export_block.js`, `build/splice_export.py` | the export-figure code and the second build step that adds it (run after `splice_page.py`) |
| `tests/check_data.py` | integrity checks on the data files, this README and the embedded data (standard library + pandas) |
| `tests/render_check.py` | opens `index.html` in headless Chromium (Playwright), exercises every control, fails on any console error, page error or failed request |
| `.github/workflows/checks.yml` | runs both checks on every push and pull request |
| `LICENSE` | MIT |

Sources and methods: the three memos in `Svetlana\UCSD Local Preference 2026-09-29\`
(estimate and baseline; data tests of the documented mechanisms; scope of selection).
Private local schools, which the plan also covered, are not in UC's public-school data.

## Data dictionary

Both CSVs are UTF-8 with a header row. CEEB and CDS codes carry leading zeros, so read them as
strings (`dtype={'ceeb': str, 'cds14': str}` in pandas). Blank cells are missing values.

| file | rows | columns | notes |
|---|---|---|---|
| `data/schools.csv` | 1,497 | 17 | one row per CEEB code |
| `data/panel_long.csv` | 679,250 | 4 | one row per (school, period, measure) with a value; missing values have no row |

### Columns of `data/schools.csv`

| column | what it is |
|---|---|
| `ceeb` | College Board (CEEB) code of the school, the key used throughout; six digits, two schools have seven |
| `school_name` | school name as it appears in the UC admissions tables (upper case, abbreviated) |
| `city` | city, from the UC tables |
| `county` | county, from the UC tables |
| `cds14` | 14-digit CDE County-District-School code; blank for 7 schools |
| `district` | first 7 digits of `cds14` (the county-district code) |
| `district_name` | district name from CDE's 2019–20 school enrollment (race/ethnicity) file; blank where `cds14` is blank or the district was not in that file |
| `local` | 1 if the county is San Diego or Imperial, else 0 (143 local schools) |
| `dist` | great-circle distance from the school to the UCSD campus, miles, from CDE coordinates; blank for 39 schools |
| `prof_terc` | tercile of the school's 2015–19 mean CAASPP percent met (0 low, 1 middle, 2 high), cut into equal thirds of the schools with results (408 / 407 / 408); blank for 274 schools without 2015–19 results |
| `apps_mean` | mean number of UCSD freshman applicants per year over the years the school appears; rounded, it is the dot size on the page |
| `g12` | mean grade-12 enrollment over the years the school appears (CDE); blank for 26 schools |
| `dgroup` | district group: 0 Sweetwater Union HSD (district 3768411), 1 San Diego Unified (3768338), 2 Imperial County, 3 Poway Unified, San Dieguito Union or Carlsbad Unified (3768296, 3768346, 3768213), 4 other San Diego County, 5 not local |
| `county_cat` | 0 San Diego, 1 Imperial, 2 Orange, 3 Riverside, 4 Los Angeles, 5 rest of California |
| `dband` | distance band from `dist`: 0 up to 10 mi, 1 10–20, 2 20–30, 3 30–60, 4 60–100, 5 over 100; blank when `dist` is blank |
| `bind_years` | local schools only: number of years in 1999–2004 in which the 4% figure exceeded the admits predicted from GPA (the sum of `quota_bind`); blank for non-local schools and for local schools with no such year on record (67 schools have a value) |
| `name` | display name used on the page: title-cased `school_name` with "High School" shortened to "High", then the city in parentheses |

The 1,497 rows are 1,497 distinct CEEB codes. They are not 1,497 distinct campuses: 38 rows share
a CDS code with another row (the UC tables give some campuses more than one CEEB code over the
years), and 10 rows share a display name with another row. Rows are sorted local schools first,
then by county and name.

### Measures in `data/panel_long.csv`

`period` is a single admission year (fall 1994 to fall 2025), a pooled era (`era_A`…`era_G`,
see the next table), or `const` for the fixed school measures. Values are stored with the
decimals shown; a period value is computed from the unrounded yearly data, not from the rounded
yearly rows, so recomputing it from this file reproduces it only within rounding. Years with no
row for a measure (for example 2020 for CAASPP) have no data. Row counts are over all periods.

| measure | label on the page | unit | decimals | years | periods | rows |
|---|---|---|---|---|---|---|
| `ucsd_admit` | UCSD admit rate | percent | 1 | 1994–2025 | A–G | 31,054 |
| `ucsd_exp` | UCSD predicted admit rate (from GPA) | percent | 1 | 1994–2025 | A–G | 30,981 |
| `ucsd_adv` | UCSD admit rate minus predicted (from GPA) | percentage points | 1 | 1994–2025 | A–G | 31,663 |
| `ucsd_exp2` | (not on the page) | percent | 1 | 1994–2025 | A–G | 30,848 |
| `ucsd_adv2` | UCSD admit rate minus predicted (GPA and other campuses) | percentage points | 1 | 1994–2025 | A–G | 31,562 |
| `ucsd_yield` | UCSD yield | percent | 1 | 1994–2025 | A–G | 17,107 |
| `ucsd_logodds` | UCSD log-odds of admission | log-odds | 2 | 1994–2025 | A–G | 29,289 |
| `ucsd_lor_year` | UCSD log odds ratio vs all applicants that year | log odds ratio | 2 | 1994–2025 | A–G | 29,289 |
| `ucsd_lor_pred` | UCSD log odds ratio vs predicted (from GPA) | log odds ratio | 2 | 1994–2025 | A–G | 29,246 |
| `ucsd_apps` | UCSD applicants (count) | students | 0 | 1994–2025 | A–G | 35,678 |
| `ucsd_adm` | UCSD admits (count) | students | 0 | 1994–2025 | A–G | 31,054 |
| `ucsd_app_gpa` | HS GPA — UCSD applicants | GPA | 2 | 1994–2025 | A–G | 35,543 |
| `ucsd_adm_gpa` | HS GPA — UCSD admits | GPA | 2 | 1994–2025 | A–G | 26,653 |
| `gpa_prem` | UCSD admit GPA minus applicant GPA | GPA points | 2 | 1994–2025 | A–G | 26,653 |
| `uc_app_gpa` | HS GPA — all UC applicants | GPA | 2 | 1994–2025 | A–G | 34,968 |
| `oth_admit` | Admit rate at the other 8 UC campuses | percent | 1 | 1994–2025 | A–G | 35,098 |
| `ucsd_share` | Share of the school’s UC applicants who applied to UCSD | percent | 1 | 1994–2025 | A–G | 33,746 |
| `apps_per100` | UCSD applicants per 100 seniors | applicants per 100 seniors | 1 | 1994–2025 | A–G | 34,899 |
| `caaspp` | CAASPP (ELA + Math) | percent | 1 | 2015–2025 (not 2020) | E–G | 14,395 |
| `star` | STAR / CST proficient | percent | 1 | 2003–2013 | C–E | 11,741 |
| `cahsee` | CAHSEE pass rate | percent | 1 | 2002–2015 | C–E | 14,585 |
| `ctx_upp` | Student need (unduplicated pupil %) | percent | 1 | 2017–2025 | E–G | 14,310 |
| `ctx_lcff` | LCFF+ school (UPP above 75%) | 0/1 | 0 | 2017–2025 | E–G | 14,310 |
| `ctx_urg` | Under-represented share (Hispanic, Black, American Indian) | percent | 1 | 1994–2025 | A–G | 34,916 |
| `quota` | 4% of the previous senior class | seats | 1 | 1994–2025 | A–G | 3,253 |
| `apps_per_quota` | UCSD applicants ÷ the 4% figure | applicants per seat | 2 | 1994–2025 | A–G | 3,232 |
| `quota_bind` | 4% figure above predicted admits (yes/no) | 0/1 | 0 | 1994–2025 | A–G | 3,009 |
| `dist` | Distance to UCSD (miles) | miles | 1 | fixed | const | 1,458 |
| `local` | Local (San Diego or Imperial County) | 0/1 | 0 | fixed | const | 1,497 |
| `county_cat` | County | category code | 0 | fixed | const | 1,497 |
| `dgroup` | District group | category code | 0 | fixed | const | 1,497 |
| `dband` | Distance band | category code | 0 | fixed | const | 1,458 |
| `prof_terc` | Proficiency tercile (2015–19 CAASPP) | category code | 0 | fixed | const | 1,223 |
| `bind_years` | Years in 1999–2004 with the 4% figure above predicted admits | years | 0 | fixed | const | 67 |
| `ctx_size` | School size (grade-12 students, average) | students | 0 | fixed | const | 1,471 |

Notes on the measures:

- The definitions shown on the page (`build/measures_block.js`, embedded in `index.html`) are the
  authoritative descriptions. The category codes for `county_cat`, `dgroup`, `dband` and
  `prof_terc` are decoded in the `schools.csv` column table above.
- `ucsd_exp2` is the predicted admit rate from the second model (GPA and the school's pooled admit
  rate at the other eight UC campuses). It is in the CSV and in the embedded panel but is not in
  the page's measure dictionary, so it cannot be selected on the page; `ucsd_adv2`, which is
  `ucsd_admit − ucsd_exp2`, can.
- Six measures are hidden behind the page's "more measures" link: `ucsd_adv2`, `ucsd_exp`,
  `ucsd_adm`, `ucsd_adm_gpa`, `uc_app_gpa` and `quota_bind`.
- Single years: `ucsd_admit = 100 × ucsd_adm ÷ ucsd_apps`; `ucsd_adv = ucsd_admit − ucsd_exp`;
  `ucsd_adv2 = ucsd_admit − ucsd_exp2`; `gpa_prem = ucsd_adm_gpa − ucsd_app_gpa`;
  `ucsd_logodds = ln((ucsd_adm + 0.5) ÷ (ucsd_apps − ucsd_adm + 0.5))`, shown only with 10 or
  more applicants; `ucsd_lor_year` subtracts the log-odds of all schools' pooled admits that year;
  `ucsd_lor_pred` subtracts the log-odds of the predicted admits; `apps_per_quota = ucsd_apps ÷ quota`.
- Pooled periods: counts (`ucsd_apps`, `ucsd_adm`, `quota`) are sums over the period's years;
  rates (`ucsd_admit`, `ucsd_exp`, `ucsd_exp2`, `ucsd_yield`, `oth_admit`, `apps_per_quota`) are
  ratios of the summed numerator and denominator; the GPA measures and `ucsd_share` are weighted
  means (weights: applicants for `ucsd_app_gpa`, `uc_app_gpa` and `ucsd_share`, admits for
  `ucsd_adm_gpa` and `gpa_prem`); `apps_per100` is weighted by grade-12 enrollment; the test
  scores, `ctx_upp` and `ctx_urg` are plain means of the years; the flags `ctx_lcff` and
  `quota_bind` are the share of the period's years with a 1; the log-odds measures and the
  advantage measures are recomputed from the pooled counts (see "Known limitations").
- The yearly file never shows an applicant count below 5 or an admit count below 3. Smaller
  counts are blank, so a school-year with applicants but a blank admit count had fewer than
  three admits (or a masked count), not zero.
- `quota`, `apps_per_quota`, `quota_bind` and `bind_years` are blank for every non-local school.

### Periods

| era | years | pseudo-year on the slider | policy regime |
|---|---|---|---|
| A | 1994–1996 | 2026 | residency points |
| B | 1997–1998 | 2027 | residency as a qualitative factor |
| C | 1999–2004 | 2028 | the Local 4% Plan |
| D | 2005–2010 | 2029 | after the October 2004 BOARS ruling |
| E | 2011–2017 | 2030 | holistic review, parity |
| F | 2018–2021 | 2031 | undocumented blanket local advantage |
| G | 2022–2025 | 2032 | advantage re-targeted to Sweetwater UHSD and Imperial County, then fading |

A year is the fall of admission; the CDE and test measures for that year are the school year
ending that spring. On the slider the eras follow 2025 at the pseudo-years shown.

### Known limitations

- In the pooled periods, the admit-based measures are computed from the sum of the published
  admit counts, with a school-year whose admit count is blank (masked, fewer than three admits)
  contributing zero admits. For a school with no published admit count in any year of a period,
  `ucsd_logodds`, `ucsd_lor_year` and `ucsd_lor_pred` are therefore computed as if it had zero
  admits (340 period rows), and `ucsd_adv` and `ucsd_adv2` come out as exactly 0.0 because the
  prediction is blank in those years as well (664 period rows). Treat period values for small
  schools with care. The checks in `tests/check_data.py` pin these counts so that any change is
  noticed.
- Three school-years (CEEB 051260 in 2025, 051415 in 2022, 053209 in 2018) have a predicted admit
  rate of 0.0, so their advantage equals their admit rate; the cubic fit extrapolates to very low
  mean GPAs.
- `apps_per100` and `apps_per_quota` have extreme values for very small senior classes (up to
  1,300 applicants per 100 seniors and 1,025 applicants per seat).
- The page's measure dictionary gives `star` and `cahsee` a span through 2025, so the coverage
  note reads "2003–2025" and "2002–2025" and the slider can reach years after their last year of
  data (2013 and 2015); those years simply show no dots.

## Checks

```
python tests/check_data.py
python tests/render_check.py
```

`check_data.py` needs pandas; `render_check.py` needs Playwright and its Chromium
(`python -m playwright install chromium`). Both run on every push through
`.github/workflows/checks.yml`; the data checks also run on Windows. The data checks confirm
that the two CSVs, the measure dictionary, this README's tables and the panel embedded in
`index.html` agree, that every stored value is within its range, and that the derived and pooled
measures recompute from the others within rounding.

## License

MIT (see `LICENSE`). The figures derive from public records of the California Department of
Education and the University of California.
