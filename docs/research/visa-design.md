# After visa-free travel to Schengen: do more Kosovars settle in the EU? — research design

**Status: pre-specified analysis, design committed 24 October 2026, before any first-permit, asylum or
immigration-enforcement figure for Kosovo or any comparison country was read.** The steps follow in dated commits:
design → data snapshot and screening → code (frozen with tests on made-up data) → results. Commit times are
self-reported; the signed tag `visa-design`, set by the author, fixes this text. The hashes of the snapshot files go
in `docs/research/visa-files.sha256`, created at the data step. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The author** knows nothing about the topic (stated 24 October 2026: "vůbec nic o tom nevím", "I know nothing at
  all about it"). The idea came from her trip to Kosovo and North Macedonia in October 2026.
- **Prior expectation.** Stated by the author on 24 October 2026, before any data and before reading anything below:
  option "c" — the number of Kosovars settling in the EU (first residence permits or asylum applications) hardly
  changed. No timing stated.
- **The assistant** that drafted this design is an AI model with general training knowledge up to mid-2026. It may
  have seen news coverage of migration from Kosovo after 1 January 2024, and blinding cannot remove that; it did not
  look any of it up, and no design choice below was made by opening a value. General knowledge that shaped choices,
  none of it checked against a source in this session:
  - before 2024: a large outflow of asylum seekers from Kosovo in the winter of 2014–15; the asylum rise after the
    2009–10 liberalisations of the other five countries; Germany's Western Balkans regulation (a labour route for the
    six countries from 2016, capped at 25 000 approvals a year from 2021); a rise in asylum applications from the
    Western Balkans in autumn 2012; Kosovo residents holding Croatian passports, or Serbian passports issued by
    Serbia's Coordination Directorate under separate visa rules; the dates of the earlier liberalisations in Q5 and
    the number and adoption month of Regulation (EU) 2023/850;
  - after 2023: the German cap doubled to 50 000 from June 2024; Bulgaria and Romania joined Schengen (air and sea
    borders in March 2024, land borders in January 2025); the Entry/Exit System started in October 2025; Kosovo held
    a population census in 2024.
  They are why the pre-period starts in 2012, why Germany carries a label condition (§6), and why §8 lists what it
  lists.
- **Structure-only scouting (24 October 2026).** The assistant, told not to download, print or compute any outcome
  value, made these calls (User-Agent "bsandova.com research"; the URLs are listed in the change log):
  (a) the Eurostat table of contents: dataset codes, last data update, first and last period;
  (b) the SDMX data structure definitions of `migr_resfirst`, `migr_resocc`, `migr_asyappctzm`, `migr_asyappctza`,
  `migr_eirfs`, `migr_eipre`, `migr_eiord`, `migr_eiord1` and `tgs00027` (dimension names), and the content
  constraints of all but `migr_asyappctza` (which codes and periods exist in each cube);
  (c) the codelists `CITIZEN`, `REASON` and `APPREHEN` (labels only);
  (d) a `detail=serieskeysonly` request for first permits and first-time asylum applicants of the eight origins in
  §2, after testing on an unrelated table (`tps00001`) that the mode returns no observations; no observation element
  was present. Every reporter is listed for every origin, so the series keys say nothing about gaps; gaps are left to
  the screening (§3);
  (e) the Eurostat reference metadata pages `migr_resval_esms`, `migr_asyapp_esms` and `migr_eil_esms` (definitions,
  timeliness, breaks, rounding);
  (f) the DG HOME page "Short-stay visas issued by Schengen countries": file names only, and the HTTP headers (no body)
  of two unnamed downloads, which are the 2025 files. On the DG HOME visa-policy page, link titles of two news items
  were visible (2025 visa applications in general; an Armenia action plan); neither was opened.
- **What the structure says.** Kosovo is `XK` ("Kosovo*") in the citizenship codelist of every dataset used; the
  comparison countries are `AL`, `BA`, `ME`, `MK`, `RS`, the wider pool `MD`, `GE`; the legacy code `RS_ME` (Serbia
  and Montenegro) is in the codelist but in none of the cubes. Reporters: the 27 member states, `IS`, `LI`, `NO`, `CH`,
  plus `UK`, aggregates (`EU27_2020`, `EU28`) and one enlargement country (`RS` in the permit tables, `ME` in the
  asylum and enforcement tables). There is no EU+EFTA aggregate. Coverage at scouting: `migr_resfirst` 2008–2025
  (updated 22 October 2026); `migr_asyappctzm` January 2008 – September 2026 (22 October 2026); `migr_eirfs`,
  `migr_eipre`, `migr_eiord` 2008–2025; `tgs00027` (population on 1 January, enlargement countries including `XK`)
  2015–2026. Read from the metadata pages, not from data: asylum figures (`migr_asyapp_esms`) and enforcement figures
  (`migr_eil_esms`) are rounded to the nearest 5; the permit page (`migr_resval_esms`) mentions no rounding, and notes
  a break in 2018 in Poland (mainly employment and other reasons) and that UK figures are not comparable. DG HOME
  publishes yearly files of visa statistics by consulate, 2009–2025.
- **Sources read.** Only the Eurostat and DG HOME pages above. No paper, news item or report on migration from Kosovo
  was read. The methods references in §4 and §6 (Abadie, Diamond and Hainmueller 2010; Ferman and Pinto 2021; Conley
  and Taber 2011; Schuirmann 1987) are cited from the assistant's general knowledge and were not opened in this
  session.
- **Nothing of the outcome.** No observation of any dataset in §2 has been downloaded.
- **Review.** Two independent reviews of the first draft (a data review and a methods review, outcome unopened) were
  taken in on 24 October 2026. In one line: Q3 moved to annual counts with the Q1 interval; the interval now rests on
  the 2013–2019 changes; a Germany condition, a drift condition, a fat-tail rule and ratio-scale thresholds were added
  to the labels; reporter coverage, the snapshot date, missing values and every check were defined exactly. A second
  round (24 October 2026) found every point resolved or partly resolved and the arithmetic re-derived; it added the
  cases where Germany or Switzerland cannot be fixed, exemptions from the six-change minimum, first-stage fallbacks, a
  Q3 check without the 2013 change, a local-level fit on 2012–2019 with a failure rule, and exact label wording.

## 1. Questions

Kosovo's citizens got visa-free short stays (90 days in any 180) in the Schengen area from 1 January 2024
(Regulation (EU) 2023/850, adopted April 2023). The citizens of Albania, Bosnia and Herzegovina, Montenegro, North
Macedonia and Serbia have had them since December 2009 or December 2010, so nothing changed for them in January 2024.
The study compares Kosovo with those five. It is one treated country with two post years; the estimates are
associations around a dated change, and §4 and §8 say how far they go.

Visa-free travel removes the short-stay visa, not the national long-stay visa that work, study and family permits
still need. A change in first permits would therefore come through easier job-search and family visits, through
people who arrive visa-free and then regularise, or through consular capacity freed for long-stay visas (§8); a
change in asylum and in irregular stay can come directly.

- **Q1 (headline).** The change in first residence permits issued to citizens of Kosovo by the EU and EFTA countries,
  in the two years after liberalisation (2024 and 2025) against the two years before (2022 and 2023), relative to the
  same change for the five comparison countries combined. In log points, reported also as a ratio and in per cent.
- **Q2 (why).** The same for first permits by reason: family, education, remunerated activities, other.
- **Q3 (asylum).** The same for first-time asylum applicants, summed to calendar years. The monthly path from January
  2024 to the last month in the snapshot is shown, descriptive only.
- **Q4 (arrive, then stay; descriptive).** The same for third-country nationals refused entry at the external
  borders, found to be illegally present, and ordered to leave. No label: these series also measure enforcement, and
  liberalisation changes them mechanically (a refusal for "no valid visa" can no longer happen).
- **Q5 (benchmark; descriptive).** What first permits and first-time asylum applications of citizens of earlier
  liberalised countries did in the two years after their liberalisation: Serbia, North Macedonia and Montenegro
  (19 December 2009), Albania and Bosnia and Herzegovina (15 December 2010), Moldova (28 April 2014), Georgia
  (28 March 2017), Ukraine (11 June 2017). Context for Kosovo; no comparison group, interval or label.

## 2. Data and definitions

- **Snapshot.** Every Eurostat dataset of §2 is downloaded once, in full for the codes used, on **9 November 2026**
  (if a download fails that day, all of them move to the next working day); the DG HOME consulate files are downloaded
  the same day. The date, file names and sha256 go in `visa-files.sha256` and the change log before any value is
  read. Whatever is published that day is the data; later updates and revisions are not used.
- **Origins.** Treated: Kosovo (`XK`). Comparison: Albania, Bosnia and Herzegovina, Montenegro, North Macedonia,
  Serbia (`AL`, `BA`, `ME`, `MK`, `RS`). Wider pool for check 9 only: Moldova (`MD`) and Georgia (`GE`). Ukraine is
  not a comparison (war from February 2022, temporary protection); it appears only in Q5.
- **Reporting area.** The 27 member states and Iceland, Liechtenstein, Norway and Switzerland (31 reporters), summed
  reporter by reporter. Not used: the United Kingdom (left in 2020; not comparable before), enlargement countries
  reporting (`RS`, `ME`), and Eurostat's aggregates (so that a reporter can be dropped; one aggregate is check 20).
- **Missing, zero and flags.** A cell is **missing** if it shows ":" (not available), "c" (confidential) or "z" (not
  applicable). A published 0 is a **zero**, not missing. Any other flag (b, d, e, p, r, s, u and the like) leaves the
  value in use; flags are counted per reporter, origin and year, and cells flagged "b" (break) or "d" (definition
  differs) are listed one by one.
- **Years.** Used pre-years: 2012–2019 and 2022–2023. 2011 and the change from 2011 to 2012 are left out because
  Albania and Bosnia and Herzegovina were still adjusting to their December 2010 liberalisation; 2008–2010 is left
  out for the same reason and because some reporters may still have counted Kosovars as Serbs (screening item 4).
  2020 and 2021 (covid) are shown in the figures but enter no estimate. Reference years: 2022 and 2023. Post years:
  2024 and 2025, or 2024 alone (below).
- **Reporter rule, annual tables (Q1, Q2, Q4), in this order.**
  1. A reporter is kept only if it has a non-missing cell for all six origins in every used pre-year; otherwise it is
     dropped for all years and listed.
  2. If step 1 would drop Germany or Switzerland, the first used year moves to the first year from which both are
     complete for all six origins, provided at least six yearly changes (§4) remain; step 1 is then **recomputed**
     with the new first year (a reporter dropped only for an earlier year comes back). If fewer than six changes
     would remain, or if Germany or Switzerland lacks 2022 or 2023 for any origin (no change of first year can fix
     that), Q1–Q4 are reported without labels.
  3. **Coverage.** The kept reporters must hold at least 90 % of all first permits issued to non-EU citizens
     (citizen `TOTAL`, not Kosovo-specific) by the 31 reporters in 2022 and 2023 together. Otherwise Q1–Q4 are
     reported without labels.
  4. **2024 and 2025.** A kept reporter that lacks 2024 for any origin is dropped and listed, and step 3 is checked
     again; if it is Germany or Switzerland, Q1–Q4 are reported without labels. 2025 is a post year only if the
     kept reporters that have 2025 for all six origins hold at least 95 % of the same 2022–2023 all-citizens total;
     the reporters without 2025 are then dropped for all years. Otherwise the post year is 2024 alone and 2025 is
     reported in check 14 only.
  5. Q2 uses the Q1 reporter set; a reporter lacking a reason cell in a used year is dropped from that reason only.
     If Germany is dropped from `EMP` this way, the Germany condition of §6 cannot be computed and a directional
     label on Q2 `EMP` is withheld (inconclusive). Q4 applies steps 1–4 to each table, with that table's
     all-citizens total (citizen `TOTAL`).
- **Reporter rule, asylum (Q3).** The same steps on calendar years: a reporter-year counts as present only if all 12
  months are non-missing for all six origins; the coverage totals are first-time applicants who are non-EU citizens
  (citizen `EXT_EU27_2020`) in 2022–2023; step 4 applies to 2025, the last complete year. The coverage codes
  (`TOTAL` for permits and enforcement, `EXT_EU27_2020` for asylum) are confirmed against the snapshot at the data
  step, before any value is read.
- **Outcomes.**
  - Q1: `migr_resfirst`, reason `TOTAL`, duration `TOTAL`, unit `PER`, annual. Q2: the same with reason `FAM`,
    `EDUC`, `EMP`, `OTH`. First permits count permits issued to a person for the first time, or after a gap of at
    least six months, for the same reason; permits after a change of status are not in them.
  - Q3: `migr_asyappctzm`, applicant `FRST` (first-time), sex `T`, age `TOTAL`, unit `PER`; the 12 months of each
    calendar year summed per reporter.
  - Q4: `migr_eirfs` (border `TOTAL`; reason `TOTAL`, and separately `VISA_RPRM_NV` "no valid visa or residence
    permit" and `STAY_M3` "already stayed 3 months in a 6-months period"); `migr_eipre` (reason `TOTAL` and `OSTAY`
    "overstay", apprehension `TOTAL`, sex `T`, age `TOTAL`); `migr_eiord` (sex `T`, age `TOTAL`). A breakdown that
    starts after 2012 is used over the years it exists, without an interval if fewer than six changes remain.
  - Population (check 16): `tgs00027`, 1 January, for the six origins, 2015–2026, as published.
- **Counts and gap.** For origin o and year t, Y(o, t) is the sum over the kept reporters. The **gap** is
  g(t) = ln max(Y(XK, t), 1) − ln max(Σ Y(c, t), 1), the sum over the five comparison countries: Kosovo against the
  other five combined, so that a small comparison country does not add noise. The floor of 1 is applied to each of
  the two series separately, and every year in which it binds is reported. The monthly asylum path uses the same
  definition on months.
- **First stage (sanity check).** DG HOME yearly consulate files, 2019–2025, read in the results step. Column: the
  one whose header, lower-cased with white space collapsed, begins "uniform visas applied for". Rows: those whose
  "country where consulate is located" column, lower-cased and stripped of "*" and spaces, equals "kosovo", summed
  over Schengen states and consulates. The data step reads headers and the list of consulate countries only and
  records, in the change log and before any count is read, the column and rows matched in each file. If a file has no
  such column or no such row, that year is reported as "structure differs"; if that year is 2023, 2024 or 2025, the
  consulate part of the sanity check is not assessed (§4). These files count consulate location, not nationality.
- **Q5 benchmark data.** First permits (`migr_resfirst`, `TOTAL`) and first-time asylum applicants summed to calendar
  years (`migr_asyappctzm`) of each earlier liberalised country, and the same for all non-EU citizens (`TOTAL` in
  permits; `EXT_EU27_2020` in asylum). Per country, the reporters kept are those with non-missing cells (all 12 months
  for asylum) for that country and for the all-citizens total in each of its four years. Years −2 and −1, and years 1
  and 2: 2008–09 and 2010–11 for the December 2009 group, 2009–10 and 2011–12 for the December 2010 group (a
  liberalisation on or after 15 December counts from the next year), 2012–13 and 2015–16 for Moldova,
  2015–16 and 2018–19 for Georgia and Ukraine (the year of liberalisation is dropped). Data start in 2008, so the 2009
  group has nothing earlier; the monthly series before 2008 (`migr_asyctzm`) is a different collection and is not
  joined.

## 3. Screening (before any outcome is compared)

1. For every table: reporters kept and dropped at each step of the reporter rule, and why; whether the first year
   moved; the coverage shares of steps 3 and 4 (all-citizens totals only); which post years Q1–Q4 use; the flag counts
   and the listed "b" and "d" cells. This decides, before any Kosovo or comparison value is read, which post years are
   used and whether any question loses its labels.
2. The last month for which every kept asylum reporter has all six origins (the end of the monthly path).
3. For Q4: the first year of each breakdown (`OSTAY`, `STAY_M3`, `VISA_RPRM_NV`).
4. Whether any kept reporter has `XK` missing while `RS` is present in the same year (a sign that Kosovars were
   counted as Serbs): years and reporters listed, from the missing pattern only.
5. Whether `tgs00027` shows a flag or break for `XK` around the 2024 census.
6. The DG HOME files: the matched column and rows per year (§2).

The screening prints availability, flags and all-citizens coverage shares, never a count for the six origins. Code
that reads values is frozen, with tests on made-up data (seed 20261025), before it is run on the snapshot.

## 4. Estimation

- **Statistic (Q1–Q4).** D = mean of g over the post years − mean of g over 2022 and 2023. e^D is the ratio of
  Kosovo's change to the comparison countries' change; 100 × (e^D − 1) the per-cent change.
- **Why this and not synthetic control.** With five comparison countries and ten used pre-years a synthetic control
  has few donors to weigh and fits noise; pooling the five is transparent and is what "nothing changed for them"
  supports. A demeaned synthetic control (after Ferman and Pinto 2021) is check 6.
- **Inference: prediction interval from the pre-period.** One treated country gives no sampling distribution across
  units: Kosovo against five placebo countries gives at best p = 1/6 (check 7, in the spirit of Abadie, Diamond and
  Hainmueller 2010 and Conley and Taber 2011), and with the used pre-years a placebo in time gives at best p = 1/6
  (check 8). The interval is therefore built from how much the gap moved from year to year before 2024, under a
  stated model: the gap is a **random walk** under no effect. The yearly changes Δ(t) = g(t) − g(t − 1) are taken
  for t = 2013, …, 2019 (n = 7 changes, fewer if the first year moved; none spans covid). Δ(2023) is left out because
  it enters D. σ̂ is the sample standard deviation of the n changes (n − 1 degrees of freedom). Under the model
  D = Δ(2024) + Δ(2025)/2 + Δ(2023)/2, so se = σ̂ × √1.5; with 2024 alone, D = Δ(2024) + Δ(2023)/2 and
  se = σ̂ × √1.25. Intervals: D ± t × se, t the Student quantile on n − 1 degrees of freedom (table in §5);
  p = 2 × (1 − F(|D| / se)), F the Student cdf on the same degrees of freedom. A random walk is the cautious choice:
  if the gap is in fact stationary around a level it overstates the variance of D (by up to three times), and a
  level-stationary gap is not credible over a pre-period that contains the 2016 German labour route.
- **Fat tails (binding).** Two further intervals, same centre D, same confidence levels:
  (a) σ̂ from the n − 1 changes left after dropping the one with the largest |Δ| (n − 2 degrees of freedom);
  (b) a **local-level** model, g(t) = μ(t) + ε(t), μ(t) = μ(t − 1) + η(t), fitted by maximum likelihood to the
  used pre-years up to 2019 only (2022–2023 not used; statsmodels `UnobservedComponents`, level `llevel`); under it
  var(D) = 1.5 σ²_η + σ²_ε (1.25 σ²_η + 1.5 σ²_ε with 2024 alone), quantiles on n − 1 degrees of freedom. If the
  fit does not converge, or either variance ends at its lower bound (zero, or below 10⁻⁸), the failure is reported
  and interval (b) is not used.
  All are reported. **For labels, at each confidence level the widest of the intervals available is used.**
  Keeping the 2014 and 2015 changes in σ̂ is conservative if the 2014–15 outflow was an exceptional jump; check 13
  drops them.
- **Q3** uses exactly this, on the annual asylum gap. The **monthly path** (January 2024 to the last month of §3,
  item 2) is g(m) − the mean of g over January 2022 – December 2023, descriptive, without a band.
- **Path, annual (Q1–Q4).** g(t) − mean(g(2022), g(2023)) for every year from the first used year to the last post
  year, with a 90 % band ± t(0.95) × σ̂ × √k(t), k(t) = 2022 − t + 0.25 for t ≤ 2022 and t − 2023 + 0.25 for
  t ≥ 2023 (0.25 for 2022 and 2023, 1.25 for 2024, 2.25 for 2025); before 2022 the covid years are counted like the
  others. Descriptive.
- **Shift before 2024 (descriptive).** D_pre = mean(g(2022), g(2023)) − mean(g(2018), g(2019)), se = σ̂ × √3.5 under
  the model (three changes over covid plus two halves). Δ(2019) enters both D_pre and σ̂, so the two are not
  independent. Reported; it changes no label.
- **Without Germany (label condition, §6).** §2 and §4 rerun with Germany removed from the kept reporters (same
  first year, no other reporter re-admitted, the coverage step not applied), interval by the same widest-interval
  rule. **Germany alone**
  is reported as a separate descriptive estimate, with its random-walk interval.
- **Drift (label condition, §6).** D_drift = D − c × Δ̄, Δ̄ the mean of the n changes, c = 2 with two post years and
  1.5 with 2024 alone; se = σ̂ × √(k + c² / n), k = 1.5 or 1.25; n − 1 degrees of freedom.
- **Minimum.** If fewer than six changes are available for a series, it is reported without labels (Q1–Q3) or
  without an interval (Q4). Fat-tail interval (a) and check 13, which drop changes by construction, are exempt; they
  are computed whenever at least three changes remain.
- **First stage (sanity check; does not relabel).** Two parts: (i) applications at consulates in Kosovo in 2024 and
  in 2025 are each below 10 % of 2023; (ii) D for `VISA_RPRM_NV` refusals (Kosovo relative to the five) is below
  ln(0.5), on the point estimate only, no interval. The code also covers refusals for a missing residence permit,
  which liberalisation does not remove, so (ii) need not reach zero. Part (i) is not assessed if a consulate file of
  2023, 2024 or 2025 has a different structure (§2); part (ii) is not assessed if the series starts after 2022 or
  fails the reporter rule. The first stage is then judged on the other part, or not at all if neither can be
  assessed. If it does not hold, or is judged on one part or not at all, the article says so next to every label.
- **Q5.** For each earlier liberalised country: the mean of ln max(Y, 1) over years 1 and 2 minus the mean over years
  −2 and −1, for first permits and first-time asylum; the same for all non-EU citizens; and the difference of the
  two. For Moldova, Georgia and Ukraine also without Poland (break in 2018). No interval, no label.
- **Randomness.** None in the primary. Check 17 uses `numpy.random.default_rng(20261024)`; the made-up test data use
  seed 20261025.
- Python (pandas, numpy, scipy for t quantiles and synthetic-control weights, statsmodels for the local-level model);
  versions recorded.

## 5. Power

Not computed: it would need the pre-period gap, which is the outcome. From the rules alone, with two post years
(√1.5 = 1.225), for the random-walk interval (the binding interval can only be wider):

| n | df | t .95 | t .975 | t .99375 | 90 % width / σ̂ | underpowered (Q1) if σ̂ > | smallest directional |D| / σ̂ |
|---|---|---|---|---|---|---|---|
| 7 | 6 | 1.943 | 2.447 | 3.521 | 4.76 | 0.077 | 3.00 (Q2: 4.31) |
| 6 | 5 | 2.015 | 2.571 | 3.810 | 4.94 | 0.074 | 3.15 (Q2: 4.67) |

- With n = 7, the smallest change Q1 can label for σ̂ = 0.05, 0.10, 0.20 is 0.15, 0.30, 0.60 log points (ratio 1.16,
  1.35, 1.82 up; 0.86, 0.74, 0.55 down).
- "No change beyond ±20 %" needs |D| + 2.38 σ̂ ≤ ln(1.2) = 0.182 (n = 7), so σ̂ below 0.077 and D near zero.
- For Q3 (margin ln(1.3)), "underpowered" holds if σ̂ > 0.110 (n = 7) or 0.106 (n = 6).

Country-level counts of first permits for one citizenship move a lot from year to year, and the pre-period contains
the 2016 German labour route and the 2014–15 outflow, so σ̂ above 0.10 is plausible, and **"underpowered" is a likely
label for Q1 and Q3**. With the author's prior of no change it is an expected outcome, not a failure; the article says
so. Only a change of about a third or more is likely to be labelled. The thresholds are fixed now and are not moved
after the benchmark (Q5) shows the scale of earlier liberalisations.

**Why these thresholds.** A ratio of 1.1 (or 1/1.1) is the smallest change worth a directional label: below it,
year-to-year noise in administrative counts and a single reporter's practice can produce the difference. A ratio
within 1/1.2 and 1.2 is the margin of "hardly changed", the author's prior read as less than a fifth either way. For
asylum (Q3), counts are smaller, rounded and more volatile, and earlier liberalisations moved them more, so the
margins are 1.15 and 1.3.

## 6. Labels

For Q1, **every** label of 1–4 that holds is reported; 5 if none does. Intervals are the binding (widest available)
intervals of §4.

1. **more Kosovars got first permits (ratio at least 1.1)** — the 95 % interval lies above 0 and D ≥ ln(1.1).
2. **fewer Kosovars got first permits (ratio at most 1/1.1)** — the 95 % interval lies below 0 and D ≤ −ln(1.1).
3. **no change beyond ±20 % (ratio between 1/1.2 and 1.2)** — the 90 % interval lies within −ln(1.2) and +ln(1.2).
   This is a two one-sided test (TOST, Schuirmann 1987) at 5 % on each side.
4. **underpowered** — the 90 % interval is wider than 2 ln(1.2) = 0.365.
5. **inconclusive** — none of 1–4.

**Q2**, per reason: the same, with the 98.75 % interval in labels 1 and 2 (Bonferroni over four reasons) and the 90 %
interval in labels 3 and 4.

**Q3**: the same with "first-time asylum applications (ratio at least 1.15)" and "(ratio at most 1/1.15)" in labels
1 and 2, D ≥ ln(1.15) or D ≤ −ln(1.15); label 3 is "no change beyond ±30 % (ratio between 1/1.3 and 1.3)" (90 %
interval within ±ln(1.3)); label 4 holds when the 90 % interval is wider than 2 ln(1.3) = 0.525.

**Conditions on labels 1 and 2.** A directional label on Q1, Q3 or Q2 `EMP` stands only if the estimate without
Germany (§4) has the same sign and its 90 % interval excludes 0. A directional label on Q1, Q2 or Q3 stands only if
D_drift (§4) has the same sign and its 90 % interval excludes 0. If either condition fails, that label becomes
**inconclusive** (labels 3 and 4, if they hold, are still reported). If the first stage does not hold, the article
says so next to every label. Q4 and Q5 carry no label.

## 7. Checks (reported; none relabels the primary)

1. Germany alone (also in §4), for Q1–Q4.
2. Without Switzerland.
3. Leave one reporter out: D without each kept reporter in turn; the range, and the reporter whose removal moves D
   most.
4. Comparison as the equal-weight mean of the five ln max(Y, 1) instead of the log of their sum.
5. Leaving out each comparison country in turn, Albania first (passport switching, §8).
6. Demeaned synthetic control (descriptive): non-negative weights on the five summing to one, minimising the squared
   distance between demeaned ln Y of Kosovo and of the weighted five over the used pre-years up to 2019 only; D and
   the random-walk interval on its gap; the weights reported.
7. Placebo in space: each comparison country j as treated, gap ln max(Y(j), 1) − ln max(Σ of the other four, 1)
   (Kosovo left out), D_j and its random-walk se_j with its own σ̂; r = |D| / se; Kosovo's p is the share of the six
   (Kosovo included, with its random-walk se) with r at least Kosovo's (at best 1/6).
8. Placebo in time, annual: D(b) = mean(g(b), g(b + 1)) − mean(g(b − 2), g(b − 1)) for break years b from the first
   used year + 2 to 2018 (2014–2018 when the first year is 2012, all inside the used years up to 2019); the share of
   all values (the placebos and the real D) with |D| at least the real |D| (at best 1/6).
9. Wider pool: Moldova and Georgia added to the comparison. Both were visa-free in every month only from 2018, so the
   pre-years are 2018, 2019, 2022 and 2023. The reporter rule of §2 is applied afresh with eight origins in place of
   six and these pre-years (steps 1, 3 and 4; step 2 does not apply). σ̂ would rest on one change (2019), so only D
   is reported, without interval.
10. Kosovo and Serbia together against the other four: ln max(Y(XK) + Y(RS), 1) − ln max(Σ of AL, BA, ME, MK, 1),
    against Kosovars counted as Serbs.
11. Stationary model: se = s × √(1/|P| + 1/2), s the sample standard deviation of g over the used pre-years, |P| the
    number of post years; quantiles on (number of used pre-years − 1) degrees of freedom.
12. Reference years 2018–2019 instead of 2022–2023 (before covid and before the regulation was adopted):
    D = mean of g over the post years − mean(g(2018), g(2019)), se = σ̂ × √5.5 (√5.25 with 2024 alone). Descriptive;
    Δ(2019) enters both this D and σ̂.
13. (a) σ̂ without the 2014 and 2015 changes (n − 2 changes, n − 3 degrees of freedom). (b) Q3 only: σ̂ without
    Δ(2013), which may carry the Western Balkan asylum rise of autumn 2012 (n − 1 changes, n − 2 degrees of freedom).
14. Each post year alone: D(2024) = g(2024) − mean(g(2022), g(2023)), se = σ̂ × √1.25; D(2025) = g(2025) −
    mean(g(2022), g(2023)), se = σ̂ × √2.25. If 2025 is not a post year (§2), D(2025) uses the reporters that have it.
15. First permits valid for 12 months or more (`M_GE12`) only, closer to settling.
16. Per capita: ln(Y / population) of each origin, with `tgs00027`; years 2015–2019 and 2022–2025 only (four changes,
    so without labels in any case). Kosovo's population figures may break with the 2024 census, which is why counts
    are the primary.
17. Reporter bootstrap: `rng = numpy.random.default_rng(20261024)`; 2 000 draws, each drawing as many reporters as are
    kept, with replacement, from the kept set (`rng.integers`), Y summed with multiplicity, D recomputed; 5th and 95th
    percentiles (`numpy.percentile`, linear). It shows how much D rests on a few destinations, not sampling error.
18. Asylum: all applicants (`migr_asyappctza`, applicant `TOTAL`) with the Q3 rules.
19. Asylum constant: Q3 with ln(Y + 1), ln(Y + 5) and ln(max(Y − 5, 1)) in place of ln max(Y, 1), on each of the two
    annual series.
20. Eurostat's published `EU27_2020` aggregate in place of the summed reporting area (no EFTA, no reporter rule).

## 8. Limits stated now

- One treated country and two post years. Every interval rests on the assumption that the gap's year-to-year moves in
  2013–2019 tell how much it moves without an effect; nothing in the data can test that.
- The German labour route is not a common shock. Its cap (doubled from June 2024) is shared by the six countries, so
  more approvals for Kosovars can mean fewer for the others; differencing then doubles such a shift rather than
  removing it. Hence the Germany condition on labels (§6). EU accession steps and the Serbia–Kosovo relationship also
  differ by country.
- Consular capacity: until 2024 the Schengen consulates in Pristina handled both short-stay and long-stay visas. Fewer
  short-stay applications can free capacity for long-stay visas, so first permits can rise without any change in
  demand; the design cannot separate the two.
- Passports are not people. Kosovars who travelled on Albanian, Serbian or Croatian passports before 2024 were counted
  under those citizenships (or, as EU citizens, not at all); if some switch to Kosovo passports after 2024, Kosovo's
  counts rise and Albania's or Serbia's fall with no change in who moves (checks 5 and 10). How holders of Serbian
  passports issued by the Coordination Directorate are counted is not known from the structure.
- Permits need a national long-stay visa, unchanged by the liberalisation; Q1 can move only through indirect routes.
  First permits are permits, not persons settling: a person can hold permits in two countries, and changes of status
  are not counted.
- Anticipation: the regulation was adopted in April 2023, so 2023 is a reference year that may already respond (check
  12). Covid: 2020–2021 are left out, so the reference years are the first two after it.
- Enforcement series (Q4) move with border practice: Croatia joined Schengen in January 2023, Bulgaria and Romania in
  2024–2025, and the Entry/Exit System began in October 2025, which detects overstays of all visa-free travellers;
  differencing takes the common part only.
- The Q5 benchmark for 2009–2010 coincides with the 2008–09 financial crisis and the fall in labour demand in the EU;
  its changes mix the liberalisation with the crisis.
- Asylum and enforcement figures are rounded to the nearest 5 (from the metadata pages); check 19 shows how much the
  constant in the log matters.
- The snapshot is one day's publication; Eurostat revises, and a later download may differ.
- The assistant's general knowledge may include post-2023 coverage of the topic (§0).

## Change log

- 24 October 2026: design committed. Structure-only scouting made these requests, all on 24 October 2026:
  - https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en
  - https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/datastructure/ESTAT/{code}/latest and
    …/contentconstraint/ESTAT/{code}/latest for `migr_resfirst`, `migr_resocc`, `migr_asyappctzm`, `migr_asyappctza`
    (data structure only, no content constraint), `migr_eirfs`, `migr_eipre`, `migr_eiord`, `migr_eiord1`, `tgs00027`
  - …/sdmx/2.1/availableconstraint/migr_resfirst/all/all/all (refused by the server, nothing returned)
  - …/sdmx/2.1/dataflow/ESTAT/migr_resfirst/latest (and the same with `references=contentconstraint`, refused)
  - …/sdmx/2.1/codelist/ESTAT/CITIZEN/latest, …/REASON/latest, …/APPREHEN/latest
  - …/sdmx/2.1/data/tps00001?detail=serieskeysonly (test that the mode returns no observations)
  - …/sdmx/2.1/data/migr_resfirst/A.TOTAL.{o}.TOTAL.PER.?detail=serieskeysonly and
    …/data/migr_asyappctzm/M.PER.{o}.T.FRST.TOTAL.?detail=serieskeysonly for o in XK, AL, RS, MK, BA, ME, MD, GE
    (series keys only; no observation element present)
  - https://ec.europa.eu/eurostat/cache/metadata/en/migr_resval_esms.htm, …/migr_asyapp_esms.htm,
    …/migr_eil_esms.htm, and …/migr_res_esms.htm (not found)
  - https://home-affairs.ec.europa.eu/policies/schengen-borders-and-visa/visa-policy_en,
    …/policies/schengen-borders-and-visa/visa-policy/visa-statistics_en (not found),
    …/policies/schengen/visa-policy/short-stay-visas-issued-schengen-countries_en (file names), and headers only of
    …/document/download/56816949-e59f-442b-9091-5d03360bf860_en and …/bf4ae08e-4a30-4ce2-a9a0-e07f15d072b8_en
- 24 October 2026, before any outcome value was read: two reviews taken in (§0). Q3 moved from a monthly placebo in
  time (61 windows) to annual counts with the Q1 interval, the monthly path kept as description; the interval's
  changes became 2013–2019 (Δ(2023) out, sample standard deviation); thresholds moved to the ratio scale; every label
  that holds is reported; Q2 direction at 98.75 %; Germany and drift conditions and the widest-of-three interval rule
  added; snapshot fixed to 9 November 2026; coverage rules for reporters and for 2025; missing, zero and flags
  defined; the Q4 quarterly path dropped; first stage defined as a sanity check with its columns; checks renumbered
  and extended (leave one reporter out, Kosovo and Serbia together, 2014–15 dropped from σ̂, asylum constant).
- 24 October 2026, before any outcome value was read: second review round taken in (§0). Germany or Switzerland
  missing in 2022, 2023 or 2024 means no labels; Germany missing from `EMP` withholds that directional label; the
  six-change minimum exempts fat-tail interval (a) and check 13; the local-level model is fitted on 2012–2019 with a
  failure rule; first-stage fallbacks; check 8 break years from the first year + 2; check 9 reporter rule on eight
  origins; check 6 fitted on 2012–2019 and descriptive; check 13(b) for Q3 without Δ(2013); asylum coverage on
  `EXT_EU27_2020`; exact ratio wording in the labels; the Q5 cut-off "on or after 15 December".
