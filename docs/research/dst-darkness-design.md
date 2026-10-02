# When the clocks go back: evening darkness and pedestrian crashes in Czechia — research design

**Status: design committed 2 October 2026, before any accident record was downloaded or opened.** Registration is
self-timestamped, as for the concert-effect study: design → code → data → results, each in a dated commit. In the
article: "registered analysis plan: design committed at `<hash>` on 2 October 2026, before the data commit; commit
times are self-reported". Deviations are listed, dated, under "Changes after registration".

## 0. What has already been seen

- **Source pages.** The Police of the Czech Republic accident-statistics pages (archiv.policie.gov.cz, "Statistika
  nehodovosti"): the list of monthly and yearly files (`data-web-*`, `datagis-*`, at least back to 2017) and the
  monthly summary PDFs' titles. No file of records was downloaded.
- **Field dictionary.** `polozky-formulare-web-1.xlsx` (the form's items): p1 id, p2a date, p2b time, p4a–c region,
  district and police unit, p5a in or outside a municipality, p6 kind of accident (4 = collision with a pedestrian),
  p7 kind of vehicle collision, p8 kind of fixed obstacle. The remaining items were not read.
- **Prior expectation.** The author expects more pedestrian crashes in the evening rush after the autumn change and
  fewer in the morning rush, as in the international literature [R1, R2].

## 1. Question and hypotheses

On the last Sunday of October, Czech clocks go back one hour (CEST → CET). Sunset moves from about 17:40 to about
16:40 by the clock, so the evening rush falls into darkness overnight, while the morning rush gets lighter. Nothing
else about the day changes: people keep their clock times for work and school. The change is an exogenous,
well-timed shift of darkness across clock hours.

- **H1 (primary).** After the change, pedestrian crashes in the evening hours (16:00–18:59) rise relative to the
  daytime control hours (10:00–13:59).
- **H2.** After the change, pedestrian crashes in the morning hours (06:00–07:59) fall relative to the control
  hours.
- **H3 (extension).** Darkness raises the hourly rate of pedestrian crashes. The clock change is used as an
  instrument for darkness (§5).

## 2. Data

- **Records.** Every police-recorded road accident in Czechia [D1], from the yearly files. Years: every autumn whose
  file has the same item layout, from the earliest available up to 2025, with 2017 as the minimum. The set of years
  is fixed from file availability and item layout only (headers and the dictionary), before any record's date,
  time or kind is read, and is logged in a change note before the data commit.
- **Window.** For each year, days −14 to −1 and +1 to +14 around the change day 0 (the last Sunday of October:
  29 Oct 2017, 28 Oct 2018, 27 Oct 2019, 25 Oct 2020, 31 Oct 2021, 30 Oct 2022, 29 Oct 2023, 27 Oct 2024,
  26 Oct 2025; earlier years by the same rule). Day 0 itself, which has 25 hours, is dropped.
- **Time.** p2b is read as local clock time (the form records the clock). Records with a missing or invalid time
  are counted, reported and dropped.
- **Unit of analysis.** District (okres, p4b, 77 districts with Prague as one) × date × clock hour. Cells with no
  crash are zeros.
- **Outcome.** Y = number of crashes with p6 = 4 (collision with a pedestrian) in the cell.
- **Sun position.** For each district's population-weighted centroid (or the geometric centroid if weights are not
  available; logged), the sun's altitude at the middle of every clock hour of the window, computed with the NOAA
  solar-position algorithm [R3]. **Dark** = altitude below −6° (after civil dusk or before civil dawn); **twilight**
  = between −6° and 0°.

## 3. Primary model (H1, H2)

Poisson pseudo-maximum likelihood on the district × date × hour cells of the evening, morning and control hours:

  log E[Y] = α(district × year) + γ(day of week) + δ(hour) + θ·Post + β_E·Post×Evening + β_M·Post×Morning
             + λ_E·t×Evening + λ_M·t×Morning + λ·t

where Post = 1 for days +1 to +14, t is the day relative to the change (−14 … +14), and Evening / Morning mark
the hour groups. The day trends absorb the steady shortening of the days and the seasonal drift that runs through
the window, so β_E and β_M measure the **jump** at the change, not the trend.

- **Estimands.** exp(β_E) and exp(β_M): the ratio by which the clock change multiplies evening (morning) pedestrian
  crashes relative to the control hours.
- **Inference.** Standard errors clustered by calendar date (about 27 dates × years). 95 % intervals.
- **Software.** Python `pyfixest` (`fepois`), version recorded at run time. If it fails, `statsmodels` GLM Poisson
  with the same dummies and cluster-robust errors, logged.

## 4. Labels

- **H1 supported** if the 95 % interval of exp(β_E) lies wholly above 1. **Not supported** if it lies within
  0.90–1.10 (equivalence margin ±10 %). Otherwise **inconclusive**, and the article says which condition failed.
- **H2** is labelled by the same rule, with the direction reversed (interval wholly below 1).
- The headline is H1. H2 and H3 do not change it.

## 5. Extension: darkness as the treatment (H3)

The clock change moves darkness only in some clock hours. Linear two-stage least squares on the same cells and
fixed effects:

- **First stage.** Dark (share of the hour after civil dusk or before civil dawn at the district centroid) on
  Post × hour-of-day dummies for 06–07 and 16–18, plus the controls and day trends of §3.
- **Second stage.** Y (per cell) on predicted Dark. The coefficient is the effect of one hour of darkness on the
  expected number of pedestrian crashes in a district, reported also as a percentage of the cell mean in the
  pre-change evening hours.
- First-stage F statistic reported (Kleibergen–Paap). If F < 10, H3 is reported as weakly identified and not
  interpreted.
- Districts differ in longitude by about 6°, so dusk comes about 24 minutes earlier in the east than in the west;
  this cross-district variation enters through the centroid sun position.

## 6. Validity checks (all reported)

- **Placebo date.** The same model with a fake change at day −14, on days −28 to −1 (no real change inside).
- **Event study.** Evening-minus-control log ratio by day, −14 to +14, plotted with 95 % bands. No pre-change jump
  is expected.
- **COVID autumns.** 2020 and 2021 dropped (curfews and closures in autumn 2020); the estimate is reported.
- **Window.** ±7 and ±21 days.
- **Other crash kinds.** The same model on crashes with p6 ≠ 4 (secondary, not a placebo: darkness can affect them
  too).
- **Police-recorded light.** If the records carry a lighting-condition item, its share "dark" by hour group,
  before and after, is reported as a check on the sun-position measure.

## 7. Power

Computed before the data commit from the police's published monthly summary PDFs (aggregates for October and
November, not records): the expected number of pedestrian crashes in the evening and control cells over all
windows, and the minimum detectable ratio at 80 % power and α = 0.05 for β_E. Logged in a change note.

## 8. Outputs

- A Research article (2 500–3 500 words) with: the hour-by-before/after figure, the event-study figure, and a map
  of districts showing how many minutes of the 16:00–18:59 rush fall after civil dusk before and after the change
  (astronomy only, no crash data).
- Data hashes, the code and the per-cell table published, as for the other studies. Records are aggregated to cells;
  no record-level field beyond those listed is published.

## 9. What this will not show

- Crashes the police did not record (minor ones without injury may be missing; the share is unknown).
- Exposure: how many people walk or drive in each hour. The design compares hours within the same days, so it
  holds exposure fixed only to the extent that clock-time routines do not change with the clocks.
- The spring change, sleep loss, or health effects.
- Whether permanent summer or winter time would be better overall; a one-hour shift of darkness in two rush hours
  is not a full welfare comparison.

## References

- [R1] Sullivan, J. M., Flannagan, M. J. (2002). The role of ambient light level in fatal crashes: inferences from
  daylight saving time transitions. *Accident Analysis & Prevention* 34(4), 487–498. [verify DOI before publication]
- [R2] Smith, A. C. (2016). Spring forward at your own risk: daylight saving time and fatal vehicle crashes.
  *American Economic Journal: Applied Economics* 8(2), 65–91. [verify DOI before publication]
- [R3] NOAA Global Monitoring Laboratory, Solar Calculation Details (the solar-position equations).
- [D1] Policie České republiky, Statistika nehodovosti, yearly data files and form items (archiv.policie.gov.cz).

## Changes after registration

None yet.
