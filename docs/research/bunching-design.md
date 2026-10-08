# Why do three 22s come at once? Tram bunching in Prague — research design

**Status: pre-specified analysis, design committed 8 October 2026, before any headway was computed.** Part 2 of the
series *Running late*. The steps follow in dated commits: design → screening → code → results. Commit times are
self-reported. Deviations are listed, dated, in the change log. A draft of this design was reviewed twice by an independent
methods reviewer before registration; the version below replaces the draft, whose estimands had no defined null,
and fixes a bias the first rewrite still had.

## 0. What has already been seen

- **Arrival times.** The *Weather on the rails* studies read observed and scheduled arrival times in
  `stop_times_history_modeling` to compute the delay a trip gains within a clock hour. The dwell study of that series
  read `real_dwell_time` and found an observed departure for only about half of non-terminal tram passes, varying by
  stop. To the author's knowledge, and by a search of this repository's code, no gap between two trams of the same line
  at the same stop (a headway) has been computed, on this site or in the thesis.
- **Part 1.** *Where is delay born?* (October 2026) measured the delay produced per tram segment (gain = delay at the
  next stop minus delay at the stop, so dwell at the first stop is included). The 10 % of segments that produce the
  most hold just over half of all positive delay produced (S = 0.506), the same segments every week, and much of it
  reflects how the timetable shares time between neighbouring segments. Q3 uses part 1's segment table, which is
  therefore known, and the author's expectations about where bunches form were formed after seeing it.
- **Prior expectation.** The author expects small headway deviations to amplify along a line (a late tram collects
  more passengers and falls further behind, the one behind catches up), and bunches to start at a few places.

## 1. Definitions

- **Service pattern.** Line × direction × ordered list of stops, the modal list for each (line, first stop, last stop)
  across all dates. Trips on other patterns (short turns, diversions) are removed and counted. A pattern's length and
  each stop's position (stops from the start, stops to the end) come from the modal list, not from a trip's observed
  rows.
- **Pair.** At the first non-terminal stop where two trips of the same pattern are both observed and consecutive in
  observed arrival, and the scheduled gap of those two trips, **H**, is 4–15 min (frequent service, where passengers
  arrive without a timetable), the two trip ids form a pair. This rule is applied only there; the same two trips are
  then followed at every later stop of the pattern, through swaps (a negative r), and the pair ends where a third
  trip of the pattern arrives between them. The frequency class is evaluated once per pair. Two trips with identical
  observed arrival at a stop are not ordered: that pair-stop is dropped and the share of ties is reported.
- **Headways.** H = the difference of the two trips' scheduled arrivals at the stop; h = the difference of their
  observed arrivals; the relative headway r = h / H.
- **Bunched:** 0 ≤ r < 0.25. **Gap:** r > 1.75. A follower that arrives first (h < 0) is a **swap**, reported as its
  own category and not pooled with bunching.
- **Birth / death / swap.** A pair is born bunched at stop k if 0 ≤ r_k < 0.25 and r_{k−1} ≥ 0.5; it dies at k if
  0 ≤ r_{k−1} < 0.25 and r_k ≥ 0.5; a pair that goes from r_{k−1} ≥ 0.5 to r_k < 0 is a swap transition, counted
  separately. Differences are taken only between consecutive stops of the pattern, both observed (or filled, §4.5); a
  missing stop breaks the difference and is not bridged.
- **Times.** All dates and hours are Europe/Prague local time; the service date of a trip is the date of its first
  scheduled arrival, so night trips crossing midnight stay on one date. The hour of a pair is the scheduled hour at its
  first stop.

## 2. Questions and estimands

- **Q1, amplification (primary).** γ from the model Δr_k = γ · (r_{k−1} − 1) + α_{pattern × stop} +
  α_{pattern × hour × weekday} + ε, where Δr_k = r_k − r_{k−1} for the same pair at consecutive stops, clustered by
  date. Noise in observed arrivals enters both sides with opposite signs and pushes γ below 0 by itself, so the
  estimand is **γ − γ₀**, where γ₀ is the same estimate on data in which each follower's stop-to-stop increments
  (h_k − h_{k−1}) are shuffled across pairs within pattern × hour × date: the noise and the day are kept, the dependence
  of a pair's next change on its current state is broken. γ − γ₀ > 0 means deviations grow by themselves (a late tram
  falling further behind); γ − γ₀ < 0 means they are corrected (holding, slack, drivers). Prediction: γ − γ₀ > 0. A
  result below 0 is a real possibility, because dispatchers and timetable slack correct headways, and is stated now.
- **Q2, places (primary).** The birth rate at a stop = births per eligible pair-stop (a pair observed at k − 1 and
  k with r_{k−1} ≥ 0.5). Stops are keyed by GTFS stop id grouped to the physical stop and direction (a platform) and
  need at least 2 000 eligible pair-stops in the window (lowered to 1 000 if fewer than 50 platforms pass, a rule fixed
  now). Each date takes the parity of its ISO week. Platforms are ranked by birth rate on odd weeks, and S_b = the share
  of even-week births at the top 10 % of them; then the roles are swapped and the two shares averaged. S_b0 = the same
  cross-fitted share under an exposure-only null, in which births are reassigned to eligible pair-stops at random (199
  draws) and split, ranked and evaluated by exactly the same procedure. The estimand is the ratio S_b / S_b0.
  Prediction: above 1.25 (the hottest tenth of platforms holds at least a quarter more births than exposure alone).
- **Q2b, stability (primary, own label).** Spearman's correlation of birth rate across those platforms between odd
  and even ISO weeks. A split-half correlation understates the full-sample one (0.50 split-half is about 0.67 by the
  Spearman–Brown formula). Prediction: high.
- **Q3, link to part 1 (secondary, own label).** ρ_b = Spearman's correlation, across part 1's tram segments with at
  least 500 observed pairs, between the birth rate at the segment's second stop and the standard deviation of the gain
  across passes on the segment (what moves two trams apart is the difference in their gains, not a shared mean).
  Prediction: ρ_b > 0. The standard deviation is computed here from `prague_cascade` by part 1's rule (gain = delay
  at the next stop minus delay at the stop, |g| ≤ 600 s), since part 1 stored sums only; the mean gain is a check, and
  ties in birth rate take average ranks.
- **Q4, when and how much (descriptive).** Shares of bunched pairs, gaps and swaps by hour, weekdays and weekends, and
  by position along the line (decile dummies), with the variance of r by position next to it.

## 3. Data

- `stop_times_history_modeling` (the author's master's thesis; Golemio vehicle positions for PID), trams, 15 March –
  8 September 2025: scheduled `current_stop_arrival`, observed `real_current_stop_arrival`, `gtfs_stop_id`, sequence;
  route = the second field of `rt_trip_id`. GTFS static data for the period (`stops.txt`) to group platforms.
- Part 1's segment table for Q3.
- City buses (routes 100–299) are a secondary analysis of Q1 and Q2 with their own labels; their stop sharing and
  branching make them noisier.

## 4. Screening (before any headway is summarised)

Fixed now; only counts and shares are summarised; committed as `bunching-screen.json`:

1. **Service.** The rain study's planned closures (by line and date) and feed-gap dates are removed.
2. **Terminals.** The first and last stop of each pattern are removed; positions therefore start at the second stop,
   and no birth can be counted at it.
3. **Patterns.** The share of trips on the modal pattern, per line × direction; lines where under 90 % of trips run one
   pattern are reported and kept only in the Q2 check without them.
4. **Timestamps.** Before any headway: the share of exact ties in observed arrival between two trips of a pattern at a
   stop, the share of observed arrivals equal to the scheduled arrival to the second, and the distribution of the
   seconds digit. If ties exceed 1 % of pair-stops, they are resolved by sequence in the feed and the rule is logged.
5. **Gaps in rows.** Where row k is missing but row k − 1 carries `real_next_stop_arrival`, that value fills the
   arrival at k, after checking on a sample that the two agree where both exist (share equal, share differing by more
   than 5 s).
6. **Coverage.** The share of pair-stops observed, by stop, month and hour; stops under 50 % coverage are listed.
7. **Thin units.** A pattern with fewer than 1 000 observed pairs is removed; counts per rule by month are reported.

## 5. Inference

- Q1: γ and γ₀ by OLS with the fixed effects of §2; the interval of γ − γ₀ from a bootstrap over dates (999 draws),
  with the shuffle redrawn in each draw; a check clusters by ISO week.
- Q2 and Q2b: a bootstrap over service dates (999 draws); a resampled date keeps the parity of its original ISO week;
  the ranking and the null are recomputed in each draw (the null with 49 draws inside each bootstrap draw).
- Q3: a bootstrap over dates in which part 1's segment values are recomputed from the resampled dates too.
- No correction for multiple questions: each has its own label and no check relabels a primary result, as in the
  earlier designs.

## 6. Labels

- **Q1, supported:** the 95 % interval of γ − γ₀ lies wholly above 0. **Not supported:** the 90 % interval lies
  wholly within ±0.01 per stop. **Inconclusive:** otherwise, including an interval wholly below 0 (correction
  outweighs amplification), reported as such.
- **Q2, supported:** the 95 % interval of S_b / S_b0 lies wholly above 1.25. **Not supported:** wholly below 1.25.
  **Inconclusive:** otherwise.
- **Q2b, supported:** the 95 % interval lies wholly at or above 0.50. **Not supported:** wholly below 0.30.
  **Inconclusive:** otherwise.
- **Q3, supported:** the 95 % interval of ρ_b lies wholly above 0. **Not supported:** the 90 % interval lies wholly
  within ±0.10. **Inconclusive:** otherwise; the achievable interval width is reported.

## 7. Checks (reported; none relabels a primary result)

- **Benchmark for the curve.** Followers' stop-to-stop increments are shuffled across pairs within pattern × hour ×
  date and the bunching-by-position curve is recomputed; the observed curve is shown against it.
- **Thresholds.** Bunched at r < 0.5 and gap at r > 1.5, the conventions of headway-reliability measures; and r < 0.20,
  r < 0.33.
- **Timetable order.** Pairs by scheduled order instead of observed order, swaps pooled with bunching.
- **Deaths and net births** by stop, with the Q2 procedure.
- **Reversed order placebo.** Q2 with the stop order reversed (births from k + 1 to k); strong agreement with the
  forward ranking would point to noise or fixed structure rather than a forward process.
- **Alternative birth rule.** Previous r ≥ 0.75 instead of 0.5.
- **Timing points.** Q1 and Q2 without stops where the median observed dwell (where a departure is observed) is at
  least 1.5 times the planned dwell and at least 20 s longer, or where the planned dwell is at least 60 s (where
  dispatchers hold trams); the stops removed are listed.
- **Incident days.** Q2 without the 1 % of dates with the most births, and with births capped at one per pair per date.
- **H of 3–4 min** analysed as a separate stratum.
- **Departures** instead of arrivals where both trips have an observed departure (about a quarter of pairs).
- **Week-clustered** intervals for Q1.
- **Q1 variants.** Anderson–Hsiao (r_{k−1} − 1 instrumented by r_{k−2} − 1); pairs cut at their first swap;
  weighting by H; a balanced panel of pairs observed at 80 % or more of their stops (bunching may itself make trams
  harder to tell apart in the feed).
- **Q2 as a difference** S_b − S_b0, beside the ratio.
- **Buses** (secondary): Q1, Q2 and Q2b.

## 8. Outputs

An article on bsandova.com, part 2 of *Running late*: the bunching curve against its shuffle benchmark, the
amplification estimate, a map of where bunches start (birth rate per platform) beside part 1's map, and the
hour-of-day pattern, every figure interactive.

## 9. What this will not show

- **Why a given bunch formed.** Births are located, not explained; a junction, a crowded stop or a late departure
  look alike here.
- **Control actions.** Dispatchers hold or short-turn trams; holding shows up as correction (γ < 0) and deaths, and
  the article cannot separate intervention from process.
- **Shared trunks.** A pair is two trams of one line; on stops shared by several lines to a common destination,
  passengers see a combined headway that this does not measure.
- **Passenger waiting time, other years, winter, the metro.**

## References

The headway-reliability conventions (bunching and gap thresholds) and the bunching mechanism are cited, with verified
sources, before the code is frozen, in a dated commit; thresholds that differ from the conventions are kept because
they were fixed here, and the conventional ones are run as checks.
