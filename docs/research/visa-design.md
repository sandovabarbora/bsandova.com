# After visa-free travel to Schengen: do more Kosovars settle in the EU? — research design

**Status: pre-specified analysis, design committed 24 October 2026, before any first-permit, asylum or
immigration-enforcement figure for Kosovo or any comparison country was read.** The steps follow in dated commits:
design → data snapshot and screening → code (frozen with tests on made-up data) → results. Commit times are
self-reported; the signed tag `visa-design`, set by the author, fixes this text. Deviations are listed, dated, in the
change log.

## 0. What has already been seen

- **The author** knows nothing about the topic (stated 24 October 2026: "vůbec nic o tom nevím"). The idea came from
  her trip to Kosovo and North Macedonia in October 2026.
- **Prior expectation.** Stated by the author on 24 October 2026, before any data and before reading anything below:
  option "c" — the number of Kosovars settling in the EU (first residence permits or asylum applications) hardly
  changed. No timing stated.
- **The assistant** that drafted this design is an AI model with general training knowledge up to mid-2026. It may
  have seen news coverage of migration from Kosovo after 1 January 2024, and blinding cannot remove that; it did not
  look any of it up, and no design choice below was made by opening a value. From the same general knowledge it knew,
  before drafting, three facts about the pre-period that shaped choices: a large outflow of asylum seekers from Kosovo
  in the winter of 2014–15; Germany's Western Balkans regulation (a labour route for the six countries from 2016,
  capped at 25 000 approvals a year from 2021 and at 50 000 from June 2024 — not checked against the text of the
  regulation in this session); and the asylum rise after the 2009–10 liberalisations for the other five countries.
  They are why the pre-period starts in 2011, why Germany is left out in check 1, and why check 17 exists.
- **Structure-only scouting (24 October 2026).** The assistant, told not to download, print or compute any outcome
  value, made these calls (User-Agent "bsandova.com research"; the URLs are listed in the change log):
  (a) the Eurostat table of contents: dataset codes, last data update, first and last period;
  (b) the SDMX data structure definitions of `migr_resfirst`, `migr_resocc`, `migr_asyappctzm`, `migr_asyappctza`,
  `migr_eirfs`, `migr_eipre`, `migr_eiord`, `migr_eiord1` and `tgs00027` (dimension names), and the content
  constraints of all but `migr_asyappctza` (which codes and periods exist in each cube);
  (c) the codelists `CITIZEN`, `REASON` and `APPREHEN` (labels only);
  (d) a `detail=serieskeysonly` request for first permits and first-time asylum applicants of the eight origins in
  §2, after testing on an unrelated table (`tps00001`) that the mode returns no observations; the parser stopped on
  any observation element and none was present. Every reporter is listed for every origin, so the series keys say
  nothing about gaps; gaps are left to the screening (§3);
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
  `migr_eipre`, `migr_eiord` 2008–2025; `migr_eiord1` 2018-Q1 – 2026-Q2; `tgs00027` (population on 1 January,
  enlargement countries including `XK`) 2015–2026. Asylum and enforcement figures are rounded to the nearest 5; permit
  figures are not. The permit metadata note a break in 2018 in Poland (mainly employment and other reasons) and that
  UK figures are not comparable. DG HOME publishes yearly files of visa statistics by consulate, 2009–2025.
- **Sources read.** Only the Eurostat and DG HOME pages above. No paper, news item or report on migration from Kosovo
  was read. The methods references in §4 (Abadie, Diamond and Hainmueller 2010; Ferman and Pinto 2021; Conley and Taber
  2011; Chernozhukov, Wüthrich and Zhu 2021) are cited from the assistant's general knowledge and were not opened in
  this session.
- **Nothing of the outcome.** No observation of any dataset in §2 has been downloaded.
- **Review.** Not yet reviewed. An independent methods review (outcome unopened) is due before the tag; its changes go
  in the change log.

## 1. Questions

Kosovo's citizens got visa-free short stays (90 days in any 180) in the Schengen area from 1 January 2024
(Regulation (EU) 2023/850, adopted April 2023). The citizens of Albania, Bosnia and Herzegovina, Montenegro, North
Macedonia and Serbia have had them since December 2009 or December 2010, so nothing changed for them in January 2024.
The study compares Kosovo with those five. It is one treated country with two post years; the estimates are
associations around a dated change, and §4 and §8 say how far they go.

Visa-free travel removes the short-stay visa, not the national long-stay visa that work, study and family permits
still need. A change in first permits would therefore come through easier job-search and family visits, or through
people who arrive visa-free and then regularise; a change in asylum and in irregular stay can come directly.

- **Q1 (headline).** The change in first residence permits issued to citizens of Kosovo by the EU and EFTA countries,
  in the two years after liberalisation (2024 and 2025) against the two years before (2022 and 2023), relative to the
  same change for the five comparison countries combined. In log points, reported also in per cent.
- **Q2 (why).** The same for first permits by reason: family, education, remunerated activities, other.
- **Q3 (path and asylum).** The same for first-time asylum applicants, monthly: January 2024 – December 2025 against
  January 2022 – December 2023; and the month-by-month path from January 2024 to the last month published (§3, item 2).
- **Q4 (arrive, then stay; descriptive).** The same for third-country nationals refused entry at the external
  borders, found to be illegally present, and ordered to leave. No label: these series also measure enforcement, and
  liberalisation changes them mechanically (a refusal for "no valid visa" can no longer happen).
- **Q5 (benchmark; descriptive).** What first permits and first-time asylum applications of citizens of earlier
  liberalised countries did in the two years after their liberalisation: Serbia, North Macedonia and Montenegro
  (19 December 2009), Albania and Bosnia and Herzegovina (15 December 2010), Moldova (28 April 2014), Georgia
  (28 March 2017), Ukraine (11 June 2017). Context for Kosovo; no comparison group, interval or label.

## 2. Data and definitions

- **Snapshot.** Every Eurostat dataset is downloaded once, in full for the codes used, on one day between 2 and 13
  November 2026; the date, file names and sha256 go in the change log before any value is read. Whatever Eurostat has
  published that day is the data; later updates and revisions are not used.
- **Origins.** Treated: Kosovo (`XK`). Comparison: Albania, Bosnia and Herzegovina, Montenegro, North Macedonia,
  Serbia (`AL`, `BA`, `ME`, `MK`, `RS`). Wider pool for check 7 only: Moldova (`MD`) and Georgia (`GE`). Ukraine is
  not a comparison (war from February 2022, temporary protection); it appears only in Q5.
- **Reporting area.** The 27 member states and Iceland, Liechtenstein, Norway and Switzerland, summed reporter by
  reporter. Not used: the United Kingdom (left in 2020; not comparable before), enlargement countries reporting
  (`RS`, `ME`), and Eurostat's aggregates (so that a reporter can be dropped).
- **Missing reports, annual tables (Q1, Q2, Q4).** A value is missing if it is shown as not available (":") or
  confidential. A reporter is kept only if it has a value for all six origins in every used pre-year (2011–2019,
  2022–2023); otherwise it is dropped for all years and listed. If that rule would drop Germany or Switzerland, the
  first used year moves to the first year from which both are complete, provided at least seven used pre-years remain;
  otherwise Q1–Q4 are reported without labels. Then the post years: if every kept reporter has 2025, the post years are
  2024 and 2025; if any lacks 2025, the post year is 2024 alone and 2025 is check 12. A kept reporter that lacks 2024
  is dropped and listed; if it is Germany or Switzerland, Q1–Q4 are reported without labels. Values flagged as
  estimated, provisional or as a break are used, and the flags are counted per reporter and year. The rule is applied
  per table; Q2 uses the Q1 reporter set, and a reporter lacking a reason cell in a used year is dropped from that
  reason only.
- **Missing reports, monthly table (Q3).** The same rule on months: a reporter is kept only if it has all six origins
  in every month of January 2011 – December 2019 and January 2022 – December 2025; if that drops Germany or Switzerland,
  Q3 is reported without labels.
- **Outcomes.**
  - Q1: `migr_resfirst`, reason `TOTAL`, duration `TOTAL`, unit `PER`, annual. Q2: the same with reason `FAM`,
    `EDUC`, `EMP`, `OTH`. First permits count permits issued to a person for the first time, or after a gap of at
    least six months, for the same reason; permits after a change of status are not in them.
  - Q3: `migr_asyappctzm`, applicant `FRST` (first-time), sex `T`, age `TOTAL`, unit `PER`, monthly.
  - Q4: `migr_eirfs` (border `TOTAL`; reason `TOTAL`, and separately `VISA_RPRM_NV` "no valid visa or residence
    permit" and `STAY_M3` "already stayed 3 months in a 6-months period"); `migr_eipre` (reason `TOTAL` and `OSTAY`
    "overstay", apprehension `TOTAL`, sex `T`, age `TOTAL`); `migr_eiord` (sex `T`, age `TOTAL`); and the quarterly
    path of `migr_eiord1` from 2018-Q1. A breakdown that starts after 2011 is used over the years it exists.
  - Population (check 14): `tgs00027`, 1 January, for the six origins, 2015–2026, as published.
- **Counts and gap.** For origin o and period t, Y(o, t) is the sum over the kept reporters. The **gap** is
  g(t) = ln Y(XK, t) − ln Σ Y(c, t), the sum over the five comparison countries: Kosovo against the other five
  combined, so that a small comparison country does not add noise. Monthly asylum counts get 5 (the rounding unit)
  added before the log: h(m) = ln(Y(XK, m) + 5) − ln(Σ Y(c, m) + 5). An annual count of zero gets 1 added, and that is
  reported.
- **Years.** Used pre-years: 2011–2019 and 2022–2023. 2011 is the first year in which all five comparison countries
  were visa-free in every month, and it leaves out 2008–2010, when some reporters may still have counted Kosovars as
  Serbs (screening item 4). 2020 and 2021 (covid) are shown in the figures but enter no estimate. Reference years:
  2022 and 2023. Post years: 2024 and 2025 (or 2024 alone, see above). The year of the regulation's adoption, 2023,
  is a reference year; anticipation is discussed in §8 and check 10 uses 2018–2019 instead.
- **First stage.** Uniform short-stay visa applications lodged at Schengen consulates located in Kosovo, from the DG
  HOME yearly consulate files 2019–2025 (`2023-schengen-visa-statistics-consulates_en.xlsx.xlsx`,
  `2024-schengen-visa-statistics-consulates_en.xlsx`, `2025-consulates-schengen-visa-statistics.xlsx` and earlier),
  downloaded on the snapshot day, hashed and read only in the results step. These files count consulate location,
  not nationality.
- **Q5 benchmark data.** First permits (`migr_resfirst`, `TOTAL`) and first-time asylum applicants summed to calendar
  years (`migr_asyappctzm`) of each earlier liberalised country, over the reporters complete in the years used, and
  the same for all non-EU citizens (`TOTAL` in permits, `EXT_EU27_2020` in asylum) as context. Years −2 and −1 and
  years 1 and 2: 2008–09 and 2010–11 for the December 2009 group, 2009–10 and 2011–12 for the December 2010 group
  (a liberalisation in the last two weeks of December counts from the next year), 2012–13 and 2015–16 for Moldova,
  2015–16 and 2018–19 for Georgia and Ukraine (the year of liberalisation is dropped). Data start in 2008, so the 2009
  group has nothing earlier; the monthly series before 2008 (`migr_asyctzm`) is a different collection and
  is not joined.

## 3. Screening (before any outcome is compared)

1. For every table: reporters kept and dropped, and why; for each kept reporter, the years or months missing for any
   origin; the flags per reporter and year; whether the 2025 post year and the post months to December 2025 are
   complete. This decides, before any value is compared, which post years Q1 uses and whether any question loses its
   labels.
2. The last month for which every kept reporter has all six origins in `migr_asyappctzm` (the end of the Q3 path,
   at most September 2026).
3. For Q4: the first year of each breakdown (`OSTAY`, `STAY_M3`, `VISA_RPRM_NV`).
4. Whether any kept reporter reports `XK` as missing while reporting `RS` in the same year (a sign that Kosovars were
   counted as Serbs): years and reporters listed, from flags only.
5. Whether `tgs00027` shows a flag or break for `XK` around the 2024 census.

The screening prints availability and flags, never a count. Code that reads values is frozen, with tests on made-up
data (seed 20261025), before it is run on the snapshot.

## 4. Estimation

- **Statistic (Q1, Q2, Q4).** D = mean of g over the post years − mean of g over 2022 and 2023. 100 × (e^D − 1) is the
  per-cent change of Kosovo's count relative to the comparison countries. The **path**: g(t) − mean(g(2022), g(2023))
  for every year 2011–2025, with the 90 % band below.
- **Why this and not synthetic control.** With five comparison countries and eleven pre-years a synthetic control has
  few donors to weigh and fits noise; equal pooling of the five is transparent and is what "nothing changed for them"
  supports. A synthetic control (demeaned, after Ferman and Pinto 2021) is check 4; the equal-weight mean of logs is
  check 3.
- **Inference (Q1, Q2, Q4): prediction interval from the pre-period.** One treated country gives no sampling
  distribution across units: comparing Kosovo with five placebo countries gives at best p = 1/6 (check 6, in the
  spirit of Abadie, Diamond and Hainmueller 2010 and Conley and Taber 2011), and with eleven pre-years and two post
  years a placebo in time gives at best p = 1/7 (check 11). The interval is therefore built from how much the gap
  moved from year to year before 2024, under a stated model: the gap is a **random walk** under no effect. The yearly
  changes Δ(t) = g(t) − g(t − 1) are taken for t = 2012, …, 2019 and 2023 (nine changes; none spans covid), and
  σ̂² = (1/n) Σ Δ(t)², with n the number of changes (no drift). Under the model D is a sum of yearly changes,
  D = Δ(2024) + Δ(2025)/2 + Δ(2023)/2, so se = σ̂ × √1.5 (√1.25 when the post year is 2024 alone: D = Δ(2024) +
  Δ(2023)/2). Intervals: D ± t × se with the Student quantile on n degrees of freedom (n = 9: 1.833 for 90 %, 2.262
  for 95 %, 3.250 for 99 %); p = 2 × (1 − F(|D| / se)). A random walk is the cautious choice: if the gap is in fact
  stationary around a level, it overstates the variance of D (by up to three times), and a level-stationary gap is
  not credible over a pre-period that contains the 2016 German labour route. Check 9 uses a stationary model instead.
- **The 90 % band of the path** in year t is ± 1.833 × σ̂ × √k(t), with k(t) the variance factor of that year's
  difference under the same model (1.25 for 2024, 2.25 for 2025; for a pre-year, the factor of its difference from
  the 2022–2023 mean, with covid years counted like the others).
- **Shift before 2024.** D_pre = mean(g(2022), g(2023)) − mean(g(2018), g(2019)); under the model it spans three yearly
  changes over covid plus two halves, se = σ̂ × √3.5 (covid years assumed to move like the others). If its 95 %
  interval excludes zero, the labels of Q1 and Q2 carry a suffix (§6).
- **Q3: placebo in time on the monthly path.** D_A(b) = mean of h over the 24 months from b − mean of h over the 24
  months before b. The estimate is D_A at b = January 2024. Placebo starts b run over every month from January 2013 to
  January 2018 (61 placebos), so that every placebo window lies in January 2011 – December 2019. Intervals invert the
  placebo distribution: the 90 % interval is [D_A − q95, D_A − q05], the 95 % interval [D_A − q97.5, D_A − q2.5], with
  q the quantiles of the 61 placebo values (linear interpolation); p = (1 + number of placebos with |D_A(b)| ≥ |D_A|)
  / 62, so p can reach 0.05. The placebo windows overlap heavily and include the 2014–15 outflow; this is a test under
  the assumption that the next 48 months behave like a typical 48 months of 2011–2019, nothing more (Chernozhukov,
  Wüthrich and Zhu 2021 discuss the general form). The monthly path from January 2024 to the end month of §3 is
  h(m) − mean of h over 2022–2023, with a pointwise 90 % band from the 5th and 95th percentiles of the same-lag
  placebo values (at least 52 per lag up to September 2026).
- **Minimum.** If fewer than seven used pre-years remain for a series, it is reported without labels (Q1–Q3) or
  without an interval (Q4).
- **No randomness in the primary.** Seeds are used only in check 15 (20261024) and in the made-up test data (20261025).
- **First stage (reported, does not relabel).** The first stage holds if applications at consulates in Kosovo in 2024
  and in 2025 are each below 10 % of 2023, and if D for refusals for `VISA_RPRM_NV` (Kosovo relative to the five) is
  below −0.50. If it does not hold, the article says so next to every label.
- **Q5.** For each earlier liberalised country: the mean of ln Y over years 1 and 2 minus the mean over years −2 and
  −1, for first permits and first-time asylum, and the same for all non-EU citizens. No interval, no label.
- Python (pandas, numpy, scipy for the t quantiles and the synthetic-control weights); versions recorded.

## 5. Power

Not computed: it would need the pre-period gap, which is the outcome. What can be said from the rules alone, for Q1
with two post years and nine yearly changes:

- The 90 % interval is 2 × 1.833 × √1.5 × σ̂ = 4.49 σ̂ wide, so **"underpowered" (wider than 0.40) holds whenever
  σ̂ > 0.089**: whenever the Kosovo-to-comparison gap moved by more than about 9 % a year (root mean square) before
  2024.
- "No change larger than 20 %" needs |D| + 2.245 σ̂ ≤ 0.20, so σ̂ below 0.089 and D near zero.
- A directional label needs |D| ≥ 2.770 σ̂ and |D| ≥ 0.10: for σ̂ = 0.05, 0.10, 0.20 the smallest change it can
  report is 0.14, 0.28, 0.55 log points (+15 %, +32 %, +73 %, or −13 %, −24 %, −42 %).

Country-level counts of first permits for one citizenship move a lot from year to year, and the pre-period contains
the 2016 German labour route and the 2014–15 outflow, so σ̂ above 0.10 is plausible, and **"underpowered" is a likely
label for Q1 and Q3**. With the author's prior of no change it is an expected outcome, not a failure; the article says
so. Only a large change (a third or more) is likely to be labelled. The thresholds are fixed now and are not moved
after the benchmark (Q5) shows the scale of earlier liberalisations.

**Why these thresholds.** 0.10 log points (about 10 %) is the smallest change worth a directional label: below it,
year-to-year noise in administrative counts and a single reporter's practice can produce the difference. 0.20 log
points (−18 % to +22 %) is the margin of "hardly changed", the author's prior read as less than about a fifth either
way. For asylum (Q3), counts are smaller, rounded and more volatile, and earlier liberalisations moved them more, so
the margins are 0.15 and 0.30.

## 6. Labels

For Q1, the first that holds:

1. **more Kosovars got first permits** — the 95 % interval lies above 0 and D is at least +0.10 (+10.5 %).
2. **fewer Kosovars got first permits** — the 95 % interval lies below 0 and D is at most −0.10 (−9.5 %).
3. **no change larger than 20 %** — the 90 % interval lies within −0.20 and +0.20.
4. **underpowered** — the 90 % interval is wider than 0.40.
5. **inconclusive** — anything else.

For Q2, per reason, the same with the 99 % interval in labels 1 and 2 (four reasons; about 0.05 / 4 per reason).

For Q3, the same with "first-time asylum applications" in labels 1 and 2, which need the 95 % placebo interval on one
side of zero, |D_A| ≥ 0.15 and p ≤ 0.05; label 3 is "no change larger than 30 %" (90 % interval within −0.30 and
+0.30); label 4 holds when the 90 % interval is wider than 0.60.

If D_pre's 95 % interval excludes zero, the Q1 and Q2 labels are followed by "with a shift in the gap between 2018–19
and 2022–23"; the label stands. If check 1 (without Germany) has an estimate of the opposite sign to the primary, or
the first stage does not hold, the article says so next to the label; the label stands. Q4 and Q5 carry no label.

## 7. Checks (reported; none relabels the primary)

1. Without Germany as a reporter, for Q1–Q4 (the Western Balkans regulation reaches all six countries, but uptake may
   differ); and Germany alone.
2. Without Switzerland as a reporter.
3. Comparison as the equal-weight mean of the five ln Y instead of the log of their sum.
4. Demeaned synthetic control: non-negative weights on the five summing to one, fitted to the demeaned ln Y over the
   used pre-years; D and the random-walk interval on its gap; the weights reported.
5. Leaving out each comparison country in turn.
6. Placebo in space: each comparison country as treated against the other four (Kosovo left out); Kosovo's rank among
   the six by |D| / se (p at best 1/6).
7. Wider pool: Moldova and Georgia added to the comparison. Both were visa-free in every month only from 2018, so the
   pre-years are 2018, 2019, 2022 and 2023 and the interval rests on two yearly changes; reported as such.
8. Drift allowed: D − 2δ̂ (D − 1.5δ̂ with 2024 alone), with δ̂ the mean yearly change and se from the sample variance of
   the changes (n − 1 degrees of freedom), inflated for the estimated drift.
9. Stationary model: se = s × √(1/|P| + 1/2), s the standard deviation of g over the used pre-years, |P| the number
   of post years.
10. Reference years 2018–2019 instead of 2022–2023 (before covid and before the regulation was adopted); under the
    random walk se = σ̂ × √5.5.
11. Placebo in time, annual: D with break years 2013–2018 (reference the two years before, post the break year and the
    next); the rank of the real D among the seven.
12. Each post year alone (2024; 2025 if it is not in the primary, over the reporters that have it).
13. First permits valid for 12 months or more (`M_GE12`) only, closer to settling.
14. Per capita: ln(Y / population) of each origin, with `tgs00027`; years 2015–2019 and 2022–2025 only. Kosovo's
    population figures may break with the 2024 census, which is why counts are the primary.
15. Reporter bootstrap: 2 000 draws of the kept reporters with replacement (seed 20261024), D recomputed; percentile
    90 % interval. It shows how much D rests on a few destination countries, not sampling error.
16. Asylum, annual: all applicants (`migr_asyappctza`, applicant `TOTAL`) and first-time applicants summed to calendar
    years, with the random-walk interval of Q1.
17. Q3 without the placebo windows that overlap September 2014 – December 2015 (the outflow).
18. Eurostat's published `EU27_2020` aggregate in place of the summed reporting area (no EFTA, no reporter rule).

## 8. Limits stated now

- One treated country and two post years. Every interval rests on the assumption that the gap before 2024 tells how
  much it moves without an effect; a random walk for Q1–Q2, a typical 48-month window of 2011–2019 for Q3. Nothing in
  the data can test that assumption.
- The comparison countries were not untouched in 2024–2025: the German labour route doubled its cap from June 2024 for
  all six, and Kosovo's uptake may differ; EU accession steps, and the Serbia–Kosovo relationship, differ by country.
  Differencing removes only the common part.
- Passports are not people. Kosovars who travelled on Albanian, Serbian or Croatian passports before 2024 were counted
  under those citizenships (or, as EU citizens, not at all); if some switch to Kosovo passports after 2024, Kosovo's
  counts rise and Albania's or Serbia's fall with no change in who moves. Holders of Serbian passports issued to
  Kosovo residents by Serbia's Coordination Directorate had separate visa rules; how they are counted is not known
  from the structure.
- Permits need a national long-stay visa, unchanged by the liberalisation; Q1 can move only through indirect routes.
  First permits are permits, not persons settling: a person can hold permits in two countries, and changes of status
  are not counted.
- Anticipation: the regulation was adopted in April 2023, so 2023 is a reference year that may already respond (check
  10). Covid: 2020–2021 are left out, so the reference years are the first two after it.
- Enforcement series (Q4) move with border practice: Croatia joined Schengen in January 2023, Bulgaria and Romania in
  2024–2025, and the Entry/Exit System began in October 2025 (from general knowledge), which detects overstays of all
  visa-free travellers; differencing takes the common part only.
- Asylum and enforcement figures are rounded to the nearest 5, which matters for small monthly counts (the +5 in h).
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
