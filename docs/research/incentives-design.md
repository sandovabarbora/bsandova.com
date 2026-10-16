# After a large investment incentive is promised: does unemployment in the district fall? — research design

**Status: pre-specified analysis, design committed 16 October 2026, before any
unemployment figure for a district or a period was read. The steps follow in dated commits: design → data and
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
