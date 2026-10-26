# After a large investment incentive is promised: does unemployment in the district fall? — research design

**Status: pre-specified analysis, design committed 16 October 2026, before any
unemployment figure for a district or a period was read.** The steps follow in dated commits: design → data and
screening → code (frozen with tests on made-up data) → results. Commit times are self-reported; the signed tag
`incentives-design` fixes this text and the hashes of the project list in `docs/research/incentives-files.sha256`.
Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The author** has read nothing about Czech investment incentives or their evaluation (stated 16 October 2026: "o
  pobídkách vím absolutně nic").
- **Prior expectation.** Stated by the author on 16 October 2026, before reading anything below: a large promise lowers
  unemployment in the district a little, barely visible in district-wide figures. No timing stated.
- **Feasibility and data scouting (15–16 October 2026).** AI agents, told not to read or compute any unemployment figure
  for a place or a period, (a) downloaded the CzechInvest project list from the public dashboard on
  czechinvest.org (2 265 projects 1993–2025, of which 1 632 with an incentive decision, 1998–2025), and reported its
  columns, the number of projects by year, by promised-jobs band and by cancellation flag; (b) read the structure of the
  Ministry of Labour (MPSV) open data on registered unemployment by district (monthly, July 2004 – December 2024, 77
  districts) and by municipality (March 2014 on), field names only; (c) read the Supreme Audit Office audit 20/13 (NKÚ,
  2021): the ministry did not record how many promised jobs were created or how many went to registered job seekers.
  The agents also listed earlier studies (Dinga and Münich 2010 on the Kolín car plant; Damborský 2023; Greenstone,
  Hornbeck and Moretti 2010; Criscuolo et al. 2019); their results were not given to the author before her prior.
- **Event counts (16 October 2026).** A methods reviewer and the assistant counted events on the project list alone,
  matching places by name string (no outcome read): with at least 500 promised jobs and a clean window, about 19 events
  (2007–2018); with at least 300, about 48. On these counts the threshold was set at 300 (§2) and 500 became check 1. After the
  second review widened the clean window (−48 to +47 months), the same string count gives 41 events in 38 places.
- **Nothing of the outcome.** No MPSV unemployment file has been downloaded; only the schemas.
- **Review.** A first draft was read by an independent methods reviewer (outcome unopened); the version below takes in
  the review: the threshold above, blockers that cannot be placed, a fixed outcome fallback, explicit weights, a
  two-year reference, randomisation inference beside the bootstrap, rules for missing months and boundary changes. A
  second round aligned the decision window and the clean window with the event years, defined the permutation and
  bootstrap pools, Q3 and the placebo, and narrowed label 3.

## 1. Questions

Associations around a dated promise, compared with districts that got no large promise at the time. Firms choose where
to invest, and until September 2019 the incentive rules themselves were looser in districts with high unemployment, so
treated districts are not a random draw; §4 and §7 say what is done about it, §8 what is left.

- **Q1 (headline).** The change in the share of registered unemployed among the population aged 15–64 in a district,
  in percentage points, averaged over years 1–3 after a large incentive was promised there (year 0, the first 12
  months, is not in it), relative to the mean of the two years before, and relative to districts with no large promise in the same window.
- **Q2 (path).** The same change year by year, from the year of the promise (year 0) to year 3.
- **Q3 (size).** Q1 divided by the event-weighted mean of 100 × promised jobs / population aged 15–64 of the treated
  district (in year −1): the share of the arithmetic upper bound — every promised job going to a registered job seeker
  of the district — that Q1 amounts to. Descriptive; it carries no label.

This is the effect of a **promise**: the list records promised jobs and investment, not what was built, and
cancelled projects stay in (intention to treat).

## 2. Data and definitions

- **Projects.** The CzechInvest dashboard table `RP_1993-2025` (download date and sha256 in the hash file). Before
  registration the data step confirms that the decoded table is complete (the dashboard's response carried a flag that
  may mean a truncated result). Only rows with an incentive decision (`ipo` true) are used.
- **District of a project.** `lokalita_mesto` is free text with the region. It is matched to a RÚIAN municipality (by
  name, and by region and district where a name is shared) and so to its district as of 2024; the matching table is
  committed and every unmatched or ambiguous name is listed. A project naming more than one place is not an event (92 of
  568 place strings name several).
- **Large promise (event).** An incentive decision with at least **300** promised jobs (`pracovni_mista`), in one
  district outside Prague, with the decision date between 1 July 2006 and 31 January 2021 (years −2 to 3 inside the data, July 2004 – December
  2024). The 300 and 200 thresholds apply to the project's total promised jobs. Cancelled (`ipo_zruseni` "ANO") and to-be-verified rows count as events. The date is `rozhodnuti_datum`, the
  decision; a project can be announced months earlier, so some response may come before it (§8).
- **Clean window.** An event is used only if no other incentive decision with at least 200 promised jobs falls in the
  same district from 48 months before to 47 months after its decision month (an earlier project's response would reach
  the reference years; a later one would fall inside years 1–3); events failing this are listed. Of two
  events that block each other, both drop. A project of at least 200 jobs that names several places blocks the district of each place that can be matched;
  a place string that matches no municipality, or several in different districts, blocks every district it could be
  in, and their number is reported. The clean window and comparison status are evaluated on the
  matched districts.
- **Comparison districts (per event).** Districts other than Prague with no incentive decision of at least 200 promised
  jobs in the event's window (48 months before to 47 after), under the same blocking rule. Events with fewer than 10
  comparison districts are dropped and listed. They are not matched on
  unemployment before the event: matching a difference-in-differences design on pre-period levels can itself create a
  spurious change when levels revert to the mean; reweighting and a same-region comparison are checks 3 and 4.
- **Outcome.** For each district and month, registered available job seekers aged 15–64 (`dosazitelniUchazeci15_64`)
  divided by the population aged 15–64 (`celkemObyvatelstvo15_64`), times 100, computed from the MPSV monthly files
  (July 2004 – December 2024; file names, download date and sha256 entered in the change log before any value is read).
  Computing it from the two fields keeps one definition across the 2013 change of the published rate. Before any value
  is read, the screening checks per month that both fields are present and that the district set is the same; a month
  without them is dropped and listed, after the outcome rule below is fixed. **Fallback, fixed now:** if `dosazitelniUchazeci15_64` is missing before 2013
  but `uchazeciOZamestnaniUoZ` (all registered job seekers) and the population field exist throughout, the outcome is
  `uchazeciOZamestnaniUoZ` / `celkemObyvatelstvo15_64` × 100 in **every** month; if the population field, or both job-seeker fields, are missing before 2013, the panel starts in January 2013, the window becomes 1 January 2015 – 31 December 2021, and the study is
  reported as descriptive, without labels. The screening records which applies before any value is read, and whether
  the population field changes monthly or once a year (an annual figure repeated over the months makes a January
  step, absorbed by the event-year fixed effects only nationally).
- **Missing months.** Within an event, a calendar month missing for any of its districts is dropped for all of them, so
  treated and comparison means use the same months; an event-year with fewer than 10 months left is missing. An event
  missing any year from −2 to 3 for its treated district is dropped.
- **Event time.** Year k is months 12k to 12k+11 counted from the decision month (month 0): year 0 is the decision
  month and the 11 after it; years −1 and −2 are the 24 months before it; year 3 ends 47 months after it. The outcome per district and event year is the mean
  of its months.
- **District boundaries.** MPSV publishes districts as they were in each month; events are placed in districts as of
  2024. A district that gained or lost municipalities on 1 January 2007 (Vyhláška 513/2006) or 1 January 2016 (Brdy) is
  left out, as treated or comparison, of any event whose years −2 to 3 cover that date; the list is in the screening.
  Check 6 puts them back.

## 3. Screening (before any outcome is compared)

1. Projects: rows, incentive rows, matched to one district, multi-site, by decision year and promised-jobs band;
   events and comparison districts per event; events dropped and why (window, Prague, clean window, matching,
   boundaries); the number of events and of distinct treated districts, which decides the minimum rule of §4 before any
   outcome is read; whether the decoded dashboard table is complete.
2. MPSV files: months present, districts per month, presence of each field used (and of the fallback fields) per
   month, and whether the population field varies within a year — not their values; which outcome rule of §2 applies.
3. Districts affected by the 2007 and 2016 boundary changes.

None of it reads an unemployment value.

## 4. Estimation

- **Stacked design.** For each event e, a sub-panel of the treated district and its comparison districts over event
  years −2 to 3. Stacked over events, the model is weighted OLS of the outcome on treated × event-year indicators,
  with district-by-event and event-year-by-event fixed effects (after Cengiz, Dube, Lindner and Zipperer 2019).
  **Weights:** 1 for the treated district, 1/n_e for each of the n_e comparison districts of event e, so each event
  counts once on each side; a district that is a comparison in many events carries more total weight, and that is
  reported.
  **Q1** is the mean of the year 1–3 coefficients minus the mean of the year −2 and −1 coefficients (the
  reference is the mean of the two pre-years; year −1's coefficient is normalised to zero for identification).
- **Pre-trend.** The difference between years −1 and −2, with its interval. With two pre-years this says little and
  passing it does not show parallel trends; it does not change any label (§6), and the article says the design cannot
  test trends before the promise properly.
- **Intervals.** A bootstrap of whole districts, 2 000 draws, seed 20261016: 90 % and 95 % percentile intervals. A
  district drawn k times enters every sub-panel it belongs to as k copies with their own fixed effects; n_e is counted
  on the drawn comparison copies; an event with no treated copy or no comparison copy is absent from that draw. Draws
  with no event are redrawn and counted. The number of events and of distinct treated districts is reported with every interval.
- **Randomisation inference.** In each of 2 000 permutations (seed 20261017), for every event one district is drawn at
  random from its pool — its comparison districts plus the true treated district — to stand as treated, the other n_e
  stand as comparisons with weight 1/n_e, and Q1 is re-estimated; the p-value is the share
  of permutations with |Q1| at least the observed |Q1|. Labels 1 and 2 need this p-value to be at most 0.05 as well as the bootstrap interval. The
  permutation treats districts in a pool as exchangeable; treated districts were chosen by firms and, before 2019,
  favoured by the rules where unemployment was high, so the test can reject on selection as well as on an effect
  (§8).
- **Minimum.** If fewer than 20 events or fewer than 15 distinct treated districts remain after the exclusions of §2
  (counted in the screening, before any outcome), Q1 is reported without labels 1–3.
- Python, statsmodels or pyfixest; versions recorded.

## 5. Power

Not computed before registration: it would need the variance of the outcome. For scale only, from §2's definitions and
no data: 300 jobs in a district of 70 000 inhabitants aged 15–64 is 0.43 points if every job went to a registered job
seeker of the district, which is unlikely. With some 30–50 events and district-level noise, **"underpowered" is a likely
label**; with the author's prior of a barely visible effect it is an expected outcome, not a failure, and the article
says so. The width of the 90 % interval and the smallest change it could tell from zero are reported with the results.

## 6. Labels

For Q1, the first that holds:

1. **lower unemployment after the promise** — the 95 % interval lies below 0, the estimate is at most −0.10 points and
   the randomisation p-value is at most 0.05.
2. **higher unemployment after the promise** — the 95 % interval lies above 0, the estimate is at least +0.10 points and
   the randomisation p-value is at most 0.05.
3. **no change larger than 0.20 points** — the 90 % interval lies within −0.20 and +0.20 (about half the arithmetic
   upper bound of the smallest event, §5).
4. **underpowered** — the 90 % interval is wider than 0.40 points.
5. **inconclusive** — anything else.

If the 95 % interval of year −1 minus year −2 excludes zero, the label is followed by "with differing paths in the two
years before the promise"; the label itself stands.

## 7. Checks (reported; none relabels the primary)

1. Thresholds of 500 and 1 000 promised jobs (blockers unchanged); without the largest event.
2. Cancelled and to-be-verified projects left out.
3. Comparison districts in the same region only.
4. Comparison districts restricted to the treated district's tercile of the mean outcome in years −2 and −1 (tercile
   cut-offs from that mean over all districts outside Prague), against selection on high unemployment; the
   permutation pools restricted the same way.
5. Without events whose years −2 to 3 cover 2009 (the crisis) or 2020–21 (covid); few events remain, so it is
   reported without labels.
6. Without districts that lost or gained municipalities in 2007 or 2016.
7. Years 1–5 where the data allow (decisions to December 2019).
8. Only decisions under the statutory incentive regime (`ipo_rezim`), without framework and programme schemes.
9. Placebo: the decision month moved two years earlier; the placebo estimate is the mean of shifted years 0 and 1
   minus the mean of shifted years −2 and −1 (all before the real decision). Events whose shifted year −2 starts
   before July 2004 are left out, and their number is reported.
10. Q1 with year −1 alone as the reference.
11. The change from year −3 to year −2 added as a control interacted with event year, against selection on a recent
    rise; only events with year −3 in the data.

## 8. Limits stated now

- The promise is not the plant: projects are cancelled, scaled down or late, and no realisation data exist (NKÚ 20/13);
  the estimate is of a promise.
- Anticipation: a project announced before its decision could move hiring or registration earlier; a reference made of
  the two pre-years would then understate the change.
- Few events: the clean-window rule keeps districts that got one large promise and no other in eight years, which may
  differ from districts that attract many; the estimate is about those.
- Firms choose districts with available labour; before 5 September 2019 the minimum investment was lower in districts
  with unemployment at least 50 % above the national mean. Treated districts may have been on a different path;
  two pre-years show little of that, and check 4 only partly addresses it.
- Commuting: jobs can go to residents of neighbouring districts, so a district-level change understates the effect on
  the local labour market and spreads some of it to the comparison districts.
- Registered unemployment counts people registered with the labour office; it moves with registration rules and
  benefits, which year effects absorb only nationally.
- The project list is a dashboard snapshot of 16 October 2026; earlier versions may differ, and the dashboard can change.

## Change log

- 16 October 2026: design committed.
- 26 October 2026: **deviation from the registered design, approved by the author before any outcome was read.** The
  data step (screening in `docs/research/incentives-screening.json`, files and hashes in
  `docs/research/incentives-mpsv-files.sha256`) found two problems, from field presence and event counts alone:
  (a) the field `celkemObyvatelstvo15_64` is missing in all 246 MPSV monthly files (July 2004 – December 2024), so the
  outcome of §2 cannot be computed, and neither can its fallback (which divides by the same field) or the
  descriptive rule (same); the rule of §2 gives "none". (b) With the rules as registered, the event list is 12
  events in 11 districts, below the minimum of §4 (20 events, 15 districts). No unemployment value, and no number
  derived from one, had been read, printed or computed by anyone when the author approved the changes; the only MPSV
  content looked at is which fields exist and that each is present (not null) in every district of every month.
  Changes, all binding from this entry:
  1. **Outcome (§1, §2).** MPSV's own `podilNezamestnanychOsobPNO`, the share of unemployed persons, as published, in
     every month; present in all 246 files and all districts. It replaces the outcome of §2 and the rule for
     missing fields (the fixed fallback and the descriptive panel fall away, as the amended outcome exists in every month).
     Its unit is percentage points, so the thresholds of §6 (0.10, 0.20, 0.40) keep their values. Months without it, or
     with a different district set, are dropped and listed by the screening (none are). §1's wording "share of
     registered unemployed among the population aged 15–64" now reads "MPSV's rate of unemployed persons".
  2. **Clean window (§2).** From 24 months before to 47 months after the decision month, instead of 48 before. It is
     used both for the event's own district and for the comparison districts of the event (one rule, one function), the
     reading under which the approved count is reproduced.
  3. **Blockers (§2).** A project blocks only with at least 300 promised jobs, instead of 200: for the clean window, for
     the comparison pools, for multi-place projects and for place strings that cannot be matched. The two thresholds
     are now both 300. Check 1 ("blockers unchanged") means blockers at 300.
  4. **Boundary changes (§2, §7).** Districts with a boundary change on 1 January 2007 or 2016 stay in the headline,
     as treated and as comparison. Check 6 now removes them, as before only for events whose years −2 to 3 cover the
     date: an event whose treated district moved drops out, and moved districts leave the comparison pools. The
     screening lists, per event, the districts moved inside its years −2 to 3.
  5. **Q3 (§1).** Q3 divides by the population aged 15–64 of the treated district, which is in no MPSV file. It is
     reported as "not computable" in the results. It is not recovered from MPSV fields (job seekers divided by the
     rate would be a computation on outcome values, which the blinding forbids). The narrowest fix, which the author
     has not yet decided: the population aged 15–64 by district, for the year before each event, from the public ČSÚ
     table (structure and coverage checked first, no outcome), used only in the denominator of Q3 and entered in a
     further dated entry before it is used. Until then Q3 stays "not computable". It carries no label either way.
  **Event counts, as the same code run on the project list alone:** as registered (≥ 200 blockers, window −48/+47,
  boundary districts excluded as treated) 12 events in 11 districts, minimum not met; as amended 34 events in 28
  districts, minimum met (20 and 15), 6 of them with a treated district on the boundary list and 23 with at least one boundary
  district inside years −2 to 3. Dropped as amended: 114 outside the decision window, 48 by the clean window, 8 naming
  several places, 5 in Prague; the 300-job projects that name several places or cannot be placed number 9 and 0.
  **Consequences stated now, not part of the approval.** (i) The window is no longer symmetric in effect: of two
  events 25 to 47 months apart only the earlier one drops, and the later one keeps an earlier project whose years 1–3
  (months 12–47 after it) can reach the later one's reference years −2 and −1, which the window of −48 mostly
  prevented. (ii) The published rate of MPSV changed its definition in 2013 (the design's reason for computing the
  outcome from two fields); a level break in January 2013 can differ between districts and is absorbed only by the
  event-year effects, which are shared within an event; it has not been looked at, and no check is added here.
  (iii) Placebo check 9 reads years −2 to 1 shifted two years back, which now lie partly outside the clean window.
- 26 October 2026 (code choices, still before any outcome was read; `tools/incentives/estimate.py`, reviewed line by
  line against §4–§7 as amended and by an independent read-only, blinded reviewer): (1) Draws. Only a bootstrap draw
  with no event is a gate (redrawn, counted, logged, capped at 100 000). Any other failure inside a bootstrap or
  permutation draw is caught, logged with its error and left missing; missing bootstrap draws drop out of the
  percentile intervals, missing permutations out of the p-value share (an unestimable permutation is never counted
  as smaller than the observed value), and both counts are reported. If more than 1 % of the 2 000 bootstrap draws
  or permutations are missing, or any input of the label is missing, the primary label is "not computable". (2) Log.
  Every draw is appended and flushed to `tools/data/incentives/draws.jsonl` as it is made, with a run stamp, the
  run name (primary or check) and its error if any; the file is not committed. (3) Checks. A check that cannot be
  built or estimated is reported with its error and the others still run; results are saved after the primary and
  after every check. (4) Check 6 is per event, a district being left out only for events whose years −2 to 3
  contain 1 January 2007 or 1 January 2016 (a span that starts that month counts as containing it, which removes
  slightly more). (5) The run uses 2 000 draws and 2 000 permutations; `--draws` is refused with `--unblind`. The
  run refuses if the screening names no amended rule or an event district code is absent from the MPSV files; Q3 is
  "not computable" (§1 entry above). (6) Reported with the primary: events dropped for a missing year, total
  comparison weight per district, mean events per bootstrap draw. Two threads, `nice -n 20`.
- 26 October 2026 (second deviation, **approved by the author before any outcome was read**; no unemployment value, and
  no number derived from one, had been read, printed or computed by anyone). Changes, binding from this entry:
  1. **Q3 denominator (§1; first 26 October entry, item 5).** The population aged 15–64 of the treated district comes
     from ČSÚ open data set 130149, "Obyvatelstvo podle pohlaví a základních věkových skupin" (both sexes, age group
     "15 až 64", statistical variable 2406, districts of číselník 101, stock at 31 December, 2000–2024; product page
     csu.gov.cz/produkty/obyvatelstvo-k-3112-podle-pohlavi-v-obcich), with the ČSÚ district list (číselník 101); URLs,
     download date and sha256 in `docs/research/incentives-mpsv-files.sha256`. The set 130142 (five-year groups) was
     not used: it starts in 2010, and events from 2006 need 2005. ČSÚ districts are mapped to the MPSV district codes by
     their LAU 1 code and cross-checked against ČSÚ's `kod_ruian` and the district name; all 76 districts outside Prague
     map one to one (Brno-město 40711 → 3702, Brno-venkov 40720 → 3703). Prague has no district row in the set and is
     outside the study; asking for it, or any district or data row that does not map, stops the run
     (`tools/incentives/population.py`). Year-end stocks are interpolated linearly to month ends, and the denominator is
     the mean over the months of year −1 kept for the event, so "population in year −1" is a mean over that year. ČSÚ
     publishes each year on that year's boundaries, not those of 2024; the difference matters only for the districts on
     the 2007 and 2016 boundary list. There the stock steps at the change and the interpolation spreads the step over
     the year: Brno-venkov's 15–64 stock is 122 787 at the end of 2006 and 137 463 at the end of 2007, so an event decided
     in 2008 has a year −1 mean about 7 % below the new-boundary stock and a Q3 about 7 % too high; for Brdy's
     neighbours the error is 1 to 2 %. This is accepted, not corrected, because Q3 carries no label. The population is used in the Q3 denominator and nowhere else; it is not an
     outcome. Q3 stays descriptive, with no label; check 11 builds its own Q3 the same way. The run refuses if any used
     event has no population for year −1.
  2. **Check 12 (§7).** Without events whose months −24 to +47 (the clean window, and years −2 to 3) contain January
     2013, when MPSV changed the definition of the published rate (consequence (ii) of the first 26 October entry):
     decisions from February 2009 to January 2015 drop. On the project list alone, 10 of the 34 events drop and 24 in 22
     districts remain, before any event lost for a missing year. Reported like the other checks; it never relabels the
     primary result.
- 26 October 2026 (after the results, **not registered**): `tools/incentives/districts.py` lists the 34 events one by
  one (promise, promised jobs per 100 residents aged 15–64 in year −1, and the raw gap between the treated district's
  outcome and the plain mean of its comparison districts per event year), draws the map of the 28 treated districts
  from ČÚZK RÚIAN municipal polygons and names an example district, Kutná Hora (the event check 1 leaves out), picked
  after the per-event gaps had been computed. It builds the panels with the frozen code and checks that the mean of the
  per-event gap changes reproduces the registered Q1 exactly. Raw figures, no interval, no label; nothing was
  re-estimated and no label changes (`docs/research/incentives-districts.json`).
- 26 October 2026 (after the results, **not registered**; correction of §8, whose registered text stays unchanged):
  §8 says "no realisation data exist (NKÚ 20/13)". The audit says more narrowly that the ministry checked at the
  recipients that the legal minimums of investment and new jobs were met, had no duty to compare, and did not compare,
  the jobs created with those promised, and had no duty to track how many went to registered job seekers. No
  per-project realisation figures are published.
- 26 October 2026 (after the results, **not registered**): the base of the outcome. Read back from the MPSV files as
  the sum over districts of `dosazitelniUchazeci15_64` / `podilNezamestnanychOsobPNO` × 100
  (`tools/incentives/districts.py`, `implied_denominator` in `docs/research/incentives-districts.json`), the national
  base is about 5.4 to 5.7 million and constant within each year through December 2013 (5 689 303 in every month of
  2013), and about 7.1 million, the population aged 15–64, varying by month from January 2014 (7 127 654). The step in
  these files is therefore in January 2014, not January 2013 as the change log assumed for check 12. Check 12 is
  reported as registered; all 10 events it leaves out also span January 2014, and 3 more do (Most and Cheb 2015, Beroun
  2015). A check at January 2014 is not run. For Q3, the bound −1 is exact only for months from 2014; earlier months
  have a smaller base, so the bound there is larger in size.
