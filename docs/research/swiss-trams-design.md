# Is Prague's delay map a law of trams? Zurich, Basel, Geneva and Bern — research design

**Status: pre-specified analysis, design committed 14 October 2026, before the Swiss data of the window were
downloaded and before any Swiss delay was computed.** Part 4 of the series *Running late*, replicating part 1 (*Where
is delay born on Prague's trams?*, `delay-origins-design.md`) on four Swiss tram networks. The steps follow in dated
commits: design → screening → code → results. Commit times are self-reported. Deviations are listed, dated, in the
change log.

## 0. What has already been seen

- **Prague.** Part 1 is published: over 618 tram segments, 15 March – 8 September 2025, the top tenth of segments made
  S = 0.506 (95 % interval 0.503–0.509) of the delay produced, and the ranking was almost identical in odd and even
  weeks (ρ = 0.999). Its checks, including S by month (0.49–0.53), are published too. The design below is written
  knowing all of these numbers.
- **Swiss data.** A feasibility check (13 October 2026) read the archive's documentation and one sample day
  (`2025-06-10_IstDaten.csv`, Tuesday 10 June 2025). From that day it counted tram rows, trips and stops by operator,
  distinct stop-to-stop pairs by operator (Zurich VBZ 465, Basel BVB 266 and BLT 179, Geneva TPG 169, Bern SVB 147), the
  status of the actual arrival (REAL 77 %, forecast 18 %, the rest unknown or empty), the share of REAL arrivals with
  non-zero seconds (97.8 %) and the share of trip-minute groups holding two or more stops (1.4 %). No delay, gain or
  segment-level value of any Swiss day was computed or printed.
- **Before registration (14 October 2026), timetable only.** Prague's planned travel times are whole minutes in all
  5 085 282 tram passes of June 2025 with a planned time; the archive lists version 1 files for July–September 2025
  next to version 2. No delay was read for either check.
- **Review.** A draft of this design was read by an independent methods reviewer; the version below takes in its
  points on stop order, measured-time selection, the chance level, the length check and the Q3 labels.
- **Prior expectation.** Stated by the author on 14 October 2026, knowing part 1's results, picked from several
  drafted wordings: the Swiss networks will be less concentrated than Prague, because they have more reserved tram
  track and priority at junctions, so delay is not born in a few critical places.

## 1. Questions and estimands

Definitions follow part 1 unless stated here.

- **Networks.** Zurich (operator VBZ), Basel (BVB and BLT pooled: they run over one track network and share stops),
  Geneva (TPG) and Bern (SVB, Bernmobil), by the operator column `BETREIBER_ABK`; trams only (`PRODUKT_ID = 'Tram'`,
  the value seen in the sample day). Other tram operators in the archive (Limmattalbahn, Forchbahn) are excluded: each
  had fewer than 60 stop pairs in the sample day.
- **Segment.** An ordered pair (stop, next served stop) within a trip, with stops identified by name
  (`HALTESTELLEN_NAME`), so platforms of one stop are one stop, as in Prague. Each direction is its own segment. A pair
  whose two stops carry the same name is dropped.
- **Delay at a stop.** `AN_PROGNOSE − ANKUNFTSZEIT` in seconds where the stop has an arrival; at the first stop of a
  trip, which has none, `AB_PROGNOSE − ABFAHRTSZEIT`. **Gain** of a pass, g = delay at the next stop − delay at the stop,
  as part 1 computed it after screening (g = `delay_to − delay_from`, rows keyed on the arrival at the stop), so g
  includes the dwell at an intermediate stop. A trip's first segment has no dwell in g in either city as far as the
  data say; the check without terminal segments covers it.
- **Date and hour.** The date is the operating day (`BETRIEBSTAG`); part 1 used the calendar date of the arrival,
  which differs only for trips after midnight. The hour is that of the actual time at the segment's first stop, as in
  part 1.
- **Q1, concentration (primary, per city).** S = (sum of N_s over the ⌈0.10·K⌉ segments (K segments in the network) with the largest N_s) ÷ (sum of
  N_s over all producers), with N_s the sum of g over a segment's kept passes; the estimator of part 1, unchanged.
- **Q2, stability (primary, per city, own label).** ρ = Spearman's correlation, across segments, of the mean gain per
  pass in odd and in even ISO weeks.
- **Q3, like Prague? (primary, per city).** D = S_city − S_Prague, with S_Prague the published estimate of part 1.
  Alongside, the excess over chance E = S − S₀ (S₀ the chance level, §4) and D_E = E_city − E_Prague, which depends
  less on the number of segments.
- **Q4, recovery and peaks (descriptive).** Recoverers and their share of segments; the Jaccard overlap of the top-10 %
  producers by mean gain per pass in weekday peaks (07:00–08:59, 15:00–17:59) and weekday middays (10:00–13:59).

## 2. Data

- **Ist-Daten** (opentransportdata.swiss, open use with attribution, no key): one row per trip and stop for all of
  Switzerland, one CSV per operating day, monthly ZIPs at `archive.opentransportdata.swiss/istdaten/2025/`. Scheduled
  times are to the minute, actual times to the second.
- **Format.** Version 1 throughout. Version 2 exists from 13 July 2025 and changes the stop identifiers; version 1
  files are published in parallel, so the window keeps one format. If version 1 is missing for any date of the window,
  that date is removed for that city. Version 1 has no stops outside Switzerland, so the cross-border ends of Geneva's
  and Basel's lines are outside the networks on every date alike.
- **Window.** 15 March – 8 September 2025, the window of part 1 (178 calendar dates before screening).
- **Download.** Monthly ZIPs, anonymous, User-Agent "bsandova.com research"; only tram rows of the four networks are
  kept on disk.

## 3. Screening (before any segment-level value is summarised)

Fixed now; applied from the rows and passes alone; committed as `swiss-trams-screen.json`, with counts and shares only.

1. **Rows.** Drop stops flagged cancelled (`FAELLT_AUS_TF`) or passed without a stop (`DURCHFAHRT_TF`); an empty flag
   counts as false, as the archive documents. A segment joins consecutive served stops. Additional trips
   (`ZUSATZFAHRT_TF`) are kept, as in Prague.
2. **Stop order.** Within a trip (`BETRIEBSTAG`, `FAHRT_BEZEICHNER`), stops are ordered by scheduled departure, then
   scheduled arrival. Stops of a trip that tie on both are dropped, and no pass is formed across them. Actual times are
   never used to order. The share of passes lost is reported.
3. **Measured times only.** A pass is kept only if the time used for the delay at each of its two stops (§1) has status
   REAL (`AN_PROGNOSE_STATUS`, or `AB_PROGNOSE_STATUS` at a first stop); forecast, estimated, unknown and empty
   statuses are dropped. The share kept is reported by city, month and segment, and a segment with REAL times on fewer
   than half of its passes is removed (count and share of passes reported).
4. **Feed gaps.** A date is removed for a city if its REAL tram arrivals are fewer than half the city's median for the
   same day type (Monday–Friday, Saturday, Sunday and public holiday; holidays from the `holidays` package for the
   canton of each city: ZH, BS, GE, BE). Swiss planned closures are not listed in any
   open source; long closures are handled by rule 6.
5. **Implausible passes.** |g| > 600 s is removed; the share is reported by city and month.
6. **Rare segments.** A segment with fewer than 1 000 kept passes in the window is removed; how many and their share of
   passes are reported by city.
7. **Schedule resolution in Prague.** The share of Prague tram passes in the whole window whose planned travel time
   is not a whole number of minutes is reported (June: none). This reads the timetable only, not delay.

## 4. Estimation and inference

- S and ρ for each city on the screened passes, with the code of part 1 (`tools/late/estimate.py`), and 95 % and 90 %
  intervals from a bootstrap over service dates (999 draws, seed fixed in the code), the ranking recomputed in each
  draw.
- **D.** The city's bootstrap draws of S minus Prague's draws from part 1's bootstrap rerun with its own seed; the two
  are resampled independently. Intervals are the 2.5–97.5 % and 5–95 % quantiles of the differences.
- **Chance level S₀.** For each city and for Prague, the segment labels are permuted among the kept passes within each
  service date and hour, and S is recomputed; S₀ is the median over 199 permutations (seed fixed), reported with its
  2.5–97.5 % range. E and D_E are computed from the bootstrap draws of S minus S₀, which is held fixed.
- No correction across the four cities: each is a separate replication, and the read is how many of the four look like
  Prague.

## 5. Labels

- **Q1 and Q2:** the rules of part 1, per city. Q1 supported if the 95 % interval of S lies wholly above 0.50, not
  supported if wholly below, inconclusive otherwise; Q2 supported if the 95 % interval of ρ lies wholly at or above
  0.70, not supported if wholly below, inconclusive otherwise. An interval wider than 0.20 is reported as imprecise.
- **Q3:** **like Prague** if the 90 % interval of D lies wholly within ±0.05; **unlike Prague** if the 95 % interval
  of D lies wholly outside ±0.05 (more concentrated if above, less if below); **underpowered for equivalence** if the
  90 % interval of D is wider than 0.10, so it could not fit within the margin; **inconclusive** otherwise. The same
  rule labels D_E. The margin 0.05 is the smallest difference that would change part 1's sentence "about half of the
  delay from a tenth of the segments"; it is also about the spread of Prague's monthly S (0.49–0.53), which was known
  when it was chosen.

## 6. Checks (reported; none relabels a primary result)

- **Minute schedules.** Both timetables are to the minute (Prague by screening step 7). If step 7 finds more than 1 %
  of Prague passes off the minute, Prague's planned times are rounded once per timetable entry (stop and trip), down
  and to the nearest minute, and S, ρ and D are recomputed with each; if Prague's S then moves by more than 0.05 or ρ
  by more than 0.10, the Q3 labels are reported as resolution-limited.
- **Forecasts kept.** Passes with forecast (PROGNOSE) times at either end kept.
- **Well-measured segments.** Q1 on segments with REAL times on at least 90 % of passes.
- **Length.** A segment's length is the straight line between its stops. Segments are ranked by N_s and taken until
  their length reaches 10 % of the network's, the network's length counting each stop pair once whatever its
  directions; numerator and denominator as in S. Swiss coordinates are joined by `BPUIC` from the service-point
  register, Prague's from the PID timetable of part 1's map. Reported only if at least 90 % of a city's passes have both
  stops placed.
- **Gini** of N_s over producers, for each city and Prague.
- **Per pass** instead of total, **top 5 % and top 20 %**, **without the first and last segment of each trip**,
  **|g| ≤ 300 s**, and **S by month**, as in part 1.
- **Without stop-order ties.** Passes touching a tie (screening step 2) dropped.
- **Basel by operator:** BVB only, and S for BVB and for BLT passes within the pooled network.
- **Terminal segments** are the first and last served stop pair of each trip after screening.

## 7. Outputs

An article on bsandova.com, part 4 of *Running late*: the four cities next to Prague (S with intervals, chance level,
D), a concentration curve per city and one map per city coloured by delay produced, as in part 1.

## 8. What this will not show

- **Why** the cities differ. Network shape, stop spacing, street running against reserved track, signal priority and
  timetable padding all differ and are not measured; with five networks, none can be separated from the others.
- **Causes on a segment.** As in part 1: where delay is recorded is not always where it is caused.
- **Other cities.** Stockholm (needs a key and reconstruction from snapshots), Helsinki, the Netherlands and Vienna have
  no open archive of actual times for the window.
- **Passenger delay**, other years, winter.

## References

opentransportdata.swiss, *Ist-Daten* and its cookbook (`opentransportdata.swiss/cookbook/actual-data/`). Further
references are verified before publication, in a dated commit.

## Changes after registration
