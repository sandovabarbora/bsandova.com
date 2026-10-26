# After a bypass opens: fewer road accidents in the town, or more elsewhere? — research design

**Status: pre-specified analysis, design committed 16 October 2026, before any accident count for a place or a year was
computed.** The steps follow in dated commits: design (with the frozen list of bypasses) → data and screening → code →
results; a second data stage (§2) is registered now and run only if its data arrive. Commit times are self-reported; the signed tag `bypass-design` fixes this text and `tools/bypass/bypasses.csv`
(sha256 485055ed073df50827a9443ae90f6cc33ec7b1b886a8e98cc1c8427909106033). Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The author** has not looked at accident data or an accident map around any bypass (stated 15 October 2026).
- **Feasibility check (15 October 2026).** An AI agent, told not to compute any count by place or year, opened the
  Police of the Czech Republic accident files for 2018, 2022 and 2024 and reported back only their national row counts
  (about 92 000–105 000 accidents a year), the field descriptions and how often coordinates are filled (about 99.7 % in
  2018). It read the column layout of the ŘSD traffic census and the ŘSD 2020 list of projects in preparation. It
  reported one study of the question, Elvik, Amundsen and Hofset (2001): about a fifth fewer injury accidents after 20
  Norwegian bypasses, with earlier estimates likely inflated by selection. **The author was told of that result before
  she stated her prior.** She later found the item in the Ministry of Transport's evaluation plan (Programme Transport
  2021–2027, October 2025, p. 14: an analysis of the safety effect of built bypasses, focused on junctions and critical
  spots on the bypasses).
- **The list of bypasses** (`tools/bypass/bypasses.csv`) was built by an AI agent from construction facts only — what
  was built, where, when works started and when it opened — without any accident or traffic count. The ŘSD 2020 list
  was taken as published; no town was added or removed on any basis other than the criteria in §2. The list is frozen
  by the tag. It was built in two passes (15–16 October 2026): class D and I bypasses opened 2016–2026 and planned,
  then class D and I opened 2007–2015, class II and III opened 2007–2026 and planned, and geometry. Its README states
  the sources and, region by region, how complete the class II and III part is: the EU-co-financed projects are found
  systematically, the regionally funded ones before about 2014 only in part.
- **Two near-misses while building the list**, both disclosed in its README: one agent briefly displayed the header and
  six rows (bridge repairs, not bypasses) of the Středočeský kraj's 2025 prioritisation table, whose columns include
  traffic-load and accident-locality scores; another opened a 2009 Liberecký kraj study ranking candidate bypasses and
  stopped reading when it reached traffic and safety criteria. Neither was used, and no accident figure for a place
  was read.
- **What the design knew of the list when it was revised (16 October 2026).** Counts of rows by class, opening year and
  construction-start year — construction facts only. On them the treated window was widened from 2018–2024 to
  2008–2024, class III was kept out of the primary set, and checks by period and road class were added (§7).
- **Review.** A draft was read by an independent methods reviewer (accident data unopened); the version below takes in
  the review: construction years kept apart, a closed definition of the comparison group, pre-trends only where data
  exist, and the offset of accidents outside the town reported in counts. A second round (16 October 2026), on the widened
  window, added: a fixed rule and date for which data stage is the headline, two pre-construction years, comparison
  towns only at a dated stage, cohorts as bins of opening years, the bypass as the resampling unit, exclusion of towns
  with other road works, a minimum counted before any accident count, and checks on the change of source.
- **Prior expectation.** Stated by the author on 15 October 2026: the accidents will move onto the bypass
  ("předpokládala bych, že se přesunou na obchvat").

## 1. Questions

Associations around a dated event, compared with towns waiting for their own bypass. A bypass opens with other changes
(traffic growth, new junctions, works), and towns did not get theirs at random; §4 and §7 say what is done about it,
§8 what is left.

- **Q1, the town (headline).** The change in police-recorded injury accidents inside the built-up area of a town in
  years 1–3 after its bypass opened, relative to towns whose bypass works had not yet started, in per cent.
- **Q2, the municipality.** The same for injury accidents on the whole territory of the municipality (inside and
  outside the built-up area, which holds most of each bypass). Reported with it, in accidents per town and year: the
  change inside the built-up area and the change outside it. If Q1 falls and Q2 does not, the fall inside is offset by
  accidents elsewhere in the municipality, which is consistent with, but does not show, traffic moving onto the bypass.
  The **offset share**, 1 − (change in Q2 / change in Q1) in accidents, is reported only if Q1's 95 % interval excludes
  zero (rules in §4). Accidents in neighbouring municipalities are not counted, so Q2 understates any offset that lands
  there.
- **Q3, the bypass road (descriptive).** Injury accidents per kilometre and year on the bypass after opening, and the
  share of them at junctions, with the old through road's rate before construction beside it; different roads, length
  and traffic, so it is not comparable with Q1 and carries no label. This is the part closest to the ministry's
  question.

## 2. Data and definitions

- **Bypasses.** `tools/bypass/bypasses.csv` (columns: town and municipality code, road, class, kind, stage,
  construction start, opening date, length, end points, OpenStreetMap ways, sources). `kind` is a closed set: `full`
  (passes the built-up area of the town entirely on one side and takes the through traffic of the road), `partial`, `relocation`, `motorway_section`. Only `full` bypasses of class I and II roads are used; the four
  class III `full` rows enter check 12 only. **Staged openings**: the opening date is
  that of the first stage that carries the through traffic past the town. A bypass serving two municipalities treats
  both. A town with two `full` bypasses in the period is excluded and listed.
- **Treated towns.** Opening between 1 January 2008 and 31 December 2024, with a municipality code and a known
  construction-start year (rows without either are excluded and listed: 6 and 12 of the 87 rows), and with at least
  **two** calendar years before the construction-start year in the accident data of the stage.
- **Other works in the town.** A town with any other row of the list, of any kind (`partial`, `relocation`,
  `motorway_section` or another `full`), opened or started between the first accident year of the stage and the end of
  its treated or comparison years is excluded and listed.
- **Two data stages.** **Stage A** uses the police files that are public (from 2016): in practice towns whose works
  started in 2018 or later (31 rows before the other exclusions). **Stage B** adds the accident records of 2006–2015 that the
  author has requested from CDV (Centrum dopravního výzkumu, the transport research centre), which would bring in
  works started from 2008 (64 rows with both fields). Stage B runs only if CDV supplies the records; before any count
  is read, the change log records what arrived and which fields of §2 it lacks, and a field it lacks is replaced only
  by a rule written there first.
- **Which stage is the headline.** Stage B, if the CDV records arrive by **31 March 2027**; otherwise stage A. The date
  is not moved. No accident count is computed on either stage until the headline stage is fixed: by the records
  arriving, by CDV declining in writing, or by the date passing. Under a stage B headline, stage B is the pooled
  2006–2025 panel and stage A alone is a check; under a stage A headline, stage B is not run. The first year of the
  police files used (2016, or 2014 if those years exist in the same form) and so the stage A boundary on construction
  start are written in the change log before any count is read.
- **Comparison towns.** Towns with a class I or II `full` bypass that opened from 1 January 2025 on, or is planned with
  a dated stage (`in construction`, `tender`, `SP` or `ÚR`; 53 rows before exclusions). Planned rows at an earlier or
  unstated stage are left out: being planned in 2026 says little about a town in 2008. A comparison row without a
  construction start serves until the year before its opening if it opened, and to the end of the data if it is
  planned and not in construction; a row `in construction` without a start date is excluded and listed. Treated towns
  before their own construction start also serve as comparisons, as the model does by construction, and count towards
  the 15 below. A comparison town
  serves in a year only if its works had not started by the end of that year (its construction-start year censors it,
  as the opening year does for treated towns). If fewer than 15 comparison towns serve in a calendar year, that year's
  treated cells are reported but not used for Q1/Q2, and the count is given.
- **Event time.** For treated towns: **pre-construction years** (before the construction-start year), **construction
  years** (from the construction-start year to the year before opening), the **opening year** (dropped) and **post
  years** 1, 2, … from the January after opening.
- **Accidents.** Police of the Czech Republic record-level files (archiv.policie.gov.cz), every year available in that
  form, from 2016 (from 2014 if those years exist in the same form) to 2025, plus the CDV records of 2006–2015 in
  stage B; file names, download date and sha256 are
  entered in the change log before any count is read. Harmonised to one schema by a mapping committed with the code;
  severity and built-up-area codes are checked year by year. An **injury accident**: at least one person killed,
  seriously or slightly injured. Location from the S-JTSK coordinates, joined to RÚIAN municipality polygons (ČÚZK,
  version and hash recorded); records without coordinates count in Q2 where the record names the municipality, else are
  dropped; both shares per year are reported, and a year with 2 points more missing coordinates than the year before is
  flagged. **Inside the built-up area**: the record's own field (p5a), as recorded in the year of the accident.
- **Municipalities.** A town whose RÚIAN territory changed by more than 2 % of its area in the period is excluded and
  listed.
- **Q3 geometry.** The bypass line (OpenStreetMap ways listed in the CSV) buffered by 50 m; bypass accidents are those
  in the buffer, outside the built-up area, on the bypass's road number. The old through road before construction:
  accidents inside the built-up area on the road number the bypass took over. **At a junction**: the record's location
  code for junctions, checked per year.

## 3. Screening (before any count is compared)

1. Rows per year and file format; the shares with coordinates, joined to a municipality, with p5a and with a severity
   code; the code lists per year.
2. Treated and comparison towns by opening year, construction start, road class and kind; towns excluded and why;
   comparison towns serving per calendar year.
3. Municipal boundary changes from RÚIAN.
None of it compares counts across towns or years.

## 4. Estimation

- **Model.** A Poisson quasi-likelihood regression of town-year injury-accident counts, without covariates or offset,
  with town and year fixed effects, indicators for each treated cohort × construction year, and indicators for each
  treated cohort × post year (the extended two-way fixed-effects estimator of Wooldridge, 2023, for staggered adoption,
  with comparison towns before their works). A **cohort** is a bin of opening years: 2008–10, 2011–13, 2014–16,
  2017–19, 2020–22, 2023–24; construction indicators are by event time within the cohort (construction year 1, 2, …
  counted back from opening). The baseline is the pre-construction years. The **Q1/Q2 estimate** is exp
  of the average of the post-year 1–3 coefficients, weighted by the treated town-years in each cohort × post-year cell,
  minus one: a ratio of mean counts, not an average of towns' own changes. Towns with no injury accident in any year
  carry no information in this model, are dropped and listed. The changes in accidents per town and year (Q2) are the
  model's predicted differences for the treated towns in post years 1–3.
- **Pre-trends.** Leads for pre-construction years −3 and −2 relative to the last pre-construction year (−1), where
  they exist; a Wald test on those that exist, with the number of treated towns behind each lead. The test is declared
  **uninformative** if fewer than 20 treated towns contribute to leads −3 and −2 together. A **placebo**: each treated
  town's construction start moved two years earlier, using pre-construction years only.
- **Intervals.** A bootstrap of whole towns (all their years), treated and comparison resampled separately, the whole
  model re-estimated, 2 000 draws, seed 20261015: 90 % and 95 % percentile intervals. The resampling unit is the bypass
  (with all the municipalities it treats). Draws in which any post year 1–3 has no treated town, or whose Poisson fit
  does not converge or has a separated cell, are redrawn and counted. With few towns a percentile bootstrap can under-cover; the number of
  treated towns is reported with every interval.
- **Offset share.** From the same draws, in accidents per town and year; reported only if Q1's 95 % interval excludes
  zero, and as "not defined" if more than 5 % of draws have a change in Q1 within 0.1 accident a year of zero.
- **Minimum.** If fewer than 30 treated towns remain after the exclusions that need no accident count (class, kind,
  dates, municipality, other works, boundary changes), Q1 and Q2 are reported without labels 1–3. Towns dropped for
  having no injury accident are dropped afterwards and reported.
- **Change of source (stage B).** If any year is in both the CDV records and the police files, the two are compared for
  that year (records, share with coordinates, share joined to a municipality, p5a and severity codes) before any
  town-level count; the comparison is reported.
- Python with pyfixest (or statsmodels for the Poisson fit); versions recorded.

## 5. Power

Not computed before registration: any number would need accident counts. Reported with the results: the width of the
90 % interval and the smallest change it could tell from zero. With fewer than about 40 treated towns, "underpowered"
is the likely label, and the text says so.

## 6. Labels

For Q1 and Q2, in this order:

1. **fewer accidents after opening** — the 95 % interval lies below 0 and the estimate is at most −10 %.
2. **more accidents after opening** — the 95 % interval lies above 0 and the estimate is at least +10 %.
3. **no change larger than 15 %** — the 90 % interval lies within −15 % and +15 %.
4. **underpowered** — the 90 % interval is wider than 30 percentage points.
5. **inconclusive** — anything else.

An estimate between −10 % and −15 % with a 95 % interval below 0 is labelled "fewer", by the order. If the pre-trend
test rejects at 5 % or is uninformative, labels 1 and 2 are followed by "with differing trends before construction"
and label 3 becomes **inconclusive**. The pre-trend test has little power; passing it does not show parallel trends.
Under a stage A headline the pre-trend test is expected to be uninformative, so labels 1 and 2 carry the caveat and
label 3 cannot be issued; the article says this. If check 13 (class I and II apart) or check 14 has an estimate of the
opposite sign to the primary, the article says so next to the label; the label stands.

## 7. Checks (reported; none relabels a primary result)

1. All accidents, with damage only.
2. Killed and seriously injured only.
3. Without 2020 and 2021 (their years dropped; a town whose last pre-construction year falls in them uses the year
   before).
4. Construction years not kept apart: the reference is the year before opening, as in a plain event study.
5. Callaway and Sant'Anna (2021), not-yet-treated comparison (censored at construction start), counts in levels, as a
   percentage of the treated towns' pre-construction mean.
6. Post years 1–2 and 1–5.
7. Comparison towns only from the planned list (the 2025–26 openings left out).
8. Including the opening year, with the opening month's share of the year as the dose.
9. Town-specific linear trends estimated on pre-construction years and extrapolated, where a town has at least three;
   the shift in Q1 against the primary is reported.
10. Q1 on the old through road only: accidents inside the built-up area on the road number the bypass took over.
11. By size: towns below and above the median of their pre-construction mean injury accidents.
12. Class III `full` bypasses added to the treated and comparison towns.
13. By road class, class I and class II separately. The class I list is close to a census; the class II list is
    complete for EU-co-financed projects but before about 2014 misses some regionally funded ones (§0), so the two can
    differ in how towns entered the list as well as in the road.
14. Stage B only: by opening period, 2008–2016 and 2017–2024.
15. Stage B only: the years around the change of source (2015 and 2016) dropped.

## 8. Limits stated now

- Selection: towns got their bypass when its permits and money were ready, not at random; the comparison towns waited
  for the same kind of road but may differ. Pre-trends and the placebo show some of this, not all.
- Regression to the mean: a bypass brought forward after a bad year would be followed by a fall without any change; a
  single high year before construction is reported where it appears, as the pre-trend test may not catch it.
- Traffic: no yearly traffic counts per road; growth is common to all towns only through the year effects.
- The old through road is often downgraded after opening, and what police record as inside the built-up area can move
  with signs; Q1 uses the record as it stands.
- Police recording can change over time and between regions; year effects absorb national changes only.
- Long pre-construction periods are collapsed into one baseline and only leads −3 and −2 are tested; a slow drift
  further back is not tested (check 9 shows how much it could matter).
- In stage B the source changes from CDV to the police files in 2016, inside event time for cohorts around 2014–2019;
  the year effects absorb only a national break (check 15).
- The public data start in 2016 (perhaps 2014), so stage A rests on works started from 2017; earlier openings need
  stage B, which depends on CDV.
- The list of class II bypasses is a convenience sample before about 2014, leaning to EU-co-financed projects (§0,
  check 13). Whether a project got EU money could itself relate to its expected safety benefit.

## Change log

- 16 October 2026: design committed.
- 16 October 2026, before any accident count was computed: the author decided not to request the CDV records of
  2006–2015 for now. Under §2 the headline stage is therefore **stage A**, fixed today rather than on 31 March 2027,
  and stage B is not run as part of this study. If the records are obtained later, any analysis on them is reported as
  added after registration, not as the registered headline.
- 16 October 2026, data step and code, before any accident count by place was computed. Police record-level files
  exist in the same form from **2016** (2014 and 2015 have only yearbooks), so stage A takes works started from 2018.
  After the exclusions of §2 the screening gives 35 treated towns (31 bypasses; 13 class I, 22 class II) and 50
  comparison towns; comparison towns serving per year never fall below 15. Choices made in the code where the design
  was silent or loose, after an independent code review:
  - Coordinates: S-JTSK values accepted within the national range widened by 20 km; outside it a record counts as
    without coordinates (0–0.02 % of records a year).
  - Boundary changes (§2): measured by whole cadastral areas moving between municipalities; one town (Valdice, 3.7 %)
    is excluded. Parcel moves across a cadastral boundary are not seen.
  - Staged openings: an earlier `partial` row on the same road and town that carries the through traffic is the first
    stage and sets opening and start year (only Opočno, BYP-194 and BYP-219).
  - "Two `full` bypasses in the period": `full` rows of any class opened 2008–2025; planned rows never count as other
    works.
  - Zero-accident rule (§4): a town with no injury accident anywhere in its municipality in any year is dropped from
    Q1, Q2 and the outside change alike, so the inside and outside changes add up to Q2; a town with no accident of a
    given outcome stays in the cell weights with a change of zero.
  - Lead rule: towns with lead −3 or −2 are counted; under stage A the test is uninformative by rule (§6); Q2 reuses
    Q1's lead test.
  - Separation in bootstrap draws is checked only on the post, construction and lead indicators used.
  - Check 4: cohort-by-event-time indicators with the year before opening as the reference. Check 8: in the opening
    year, the opening month's share of the year goes to post year 1 and the rest to the last construction year; a
    year-only date gets 0.5. Check 10 and Q3: the road number the bypass took over is taken to be the bypass's own
    number. The placebo interval is cluster-robust by bypass, not bootstrapped.
  - Q3: bypass length from the list's `length_km` (OpenStreetMap lists both carriageways of dual roads); geometry from
    the 1 020 OpenStreetMap ways listed, a straight line between the end points where none are listed; the old road's
    rate is per year, not per km, as its length is not in the list.
  - Records without coordinates in 2023–2025 name their municipality only in text and are matched to a unique RÚIAN
    name.
- 26 October 2026, after the code freeze, before any estimate was read. The registered run stopped twice without an
  estimate. First, the run command in `estimate.py` lacked `geopandas` and `pyogrio`, which the town step imports; the
  command now lists them. Second, at bootstrap draw 500 the town-trend fit of check 9 failed (`SVD did not converge`)
  outside the guard that the main fit already had, so the whole run stopped instead of leaving check 9 missing for that
  draw as §4 and the code's own rule say. The trend fit now sits inside that guard, with a test. Nothing else changed;
  the run restarts from draw 1 with the same seed, so the accepted draws are the same as before.
- 26 October 2026, after the results, not registered: check 1 (all accidents, damage-only included) came out of the
  opposite sign to Q1. `tools/bypass/describe.py` (`docs/research/bypass-describe.json`) tabulates the counts behind it
  by place and year, importing the frozen code and estimating nothing: Prague, a comparison town through BYP-057
  (Úvaly), holds most of the comparison towns' accidents inside the built-up area, and its recorded damage-only
  accidents fell by about half over 2016–2025, almost all of them below 100 000 CZK of damage, while those of the
  treated and the other comparison towns did not. The article reports this as a note. No estimate was re-run and no
  label changes.
- 26 October 2026, after the results, not registered, at the author's request: Q1, Q2 and check 1 re-estimated
  without Prague among the comparison towns (`tools/bypass/without_prague.py`, `docs/research/bypass-without-prague.json`).
  Only Prague's row is dropped; the BYP-057 unit keeps Úvaly. The frozen code at `bypass-code-2` is imported unchanged,
  with the same years, seed and 2 000 draws by bypass. Q1 −15.3 % (95 % −52.7 to +7.0 %), Q2 +6.5 % (95 % −12.8 to
  +31.6 %), both underpowered by the §6 rule; check 1 −2.1 % (Q1) and +10.9 % (Q2). The registered labels stand.
- 26 October 2026, correction of the entry of 16 October: the town excluded for a boundary change of 3.7 % is Jičín
  (572659), not Valdice; Valdice (573701), the other municipality of BYP-199, is a treated town. The code and the
  screening file had it right; only the wording here was wrong.
- 26 October 2026, after the results, not registered: a map of the treated towns and one example town, raw counts only
  (`tools/bypass/towns_map.py`, `docs/research/bypass-towns.json`). The example is picked by a rule set before its
  counts were read: among the towns on class I roads, the most post-opening years in 2016–2025, ties by the earliest
  opening date (Kámen, BYP-014).
