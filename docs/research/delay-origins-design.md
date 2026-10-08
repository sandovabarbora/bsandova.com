# Where is delay born on Prague's trams? — research design

**Status: pre-specified analysis, design committed 8 October 2026, before any segment-level delay was read.** Part 1
of the series *Running late*. The steps follow in dated commits: design → screening → code → results. Commit times
are self-reported. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **Segments.** Only the schema of `prague_cascade` was read: one row per trip and segment (from a stop to the next
  stop), with `delay_from`, `delay_to`, `delay_gain`, `planned_travel_time`, `real_travel_time`, the stop names and
  the arrival time at the first stop. No value of this table has been printed, summarised or written.
- **Delays elsewhere.** The thesis (2025) and the *Weather on the rails* studies (October 2026) read delay from
  `stop_times_history_modeling`: its persistence within a day (thesis), and the delay a trip gains within a clock hour,
  averaged over a route-direction and hour, against rain and heat. No delay was ever broken down by place.
- **Prior expectation.** The author expects delay to be born on a minority of segments, mostly in the centre and at
  junctions shared with cars, and expects the same segments to stand out week after week.

## 1. Questions and estimands

- **Unit.** A tram segment: an ordered pair (stop, next stop), named as in the data, so each direction is its own
  segment. A pass is one trip over one segment. Its gain g = `delay_gain` in seconds (delay at the next stop minus
  delay at the stop), checked in screening (§3).
- **Production of a segment.** N_s = the sum of g over all its kept passes in the window, in seconds: the delay the
  network takes on there. A segment with N_s > 0 is a *producer*, with N_s < 0 a *recoverer*.
- **Q1, concentration (primary).** S = (sum of N_s over the 10 % of segments with the largest N_s) ÷ (sum of N_s over
  all producers). Does a tenth of the network make most of the delay?
- **Q2, stability (primary, own label).** ρ = Spearman's rank correlation, across segments, between the mean gain per
  pass in odd ISO weeks and in even ISO weeks. Are the hotspots places, or noise?
- **Q3, recovery (descriptive).** Where trams make up time: the recoverers, their total and their share of the
  network's length in stops.
- **Q4, peak against off-peak (descriptive).** The overlap (Jaccard index) of the top-10 % producers by mean gain per
  pass in weekday peaks (07:00–08:59 and 15:00–17:59) and weekday middays (10:00–13:59).

## 2. Data

- `prague_cascade` (the author's master's thesis; Golemio vehicle positions for PID), trams (`route_type =
  'tramvaj'`), 15 March – 8 September 2025, the window of the earlier studies. Route = the second field of
  `rt_trip_id`. Stop coordinates from `stop_times_history_intermediate_stops`, for the map only.
- City buses (routes 100–299) are a secondary analysis with the same estimands and their own labels.

## 3. Screening (before any segment-level value is summarised)

Fixed now; applied from the passes alone; committed as `delay-origins-screen.json`:

1. **Definition check.** On a random 0.1 % of passes, g is compared with `delay_to − delay_from` and with
   `real_travel_time − planned_travel_time`; agreement within 1 s is reported. If g differs from `delay_to −
   delay_from` in more than 1 % of passes, g is recomputed as that difference and the change is logged.
2. **Service screening.** The rain study's planned closures (by line and date) and feed-gap dates are removed.
3. **Implausible passes.** |g| > 600 s is removed (a diversion, a vehicle out of service or a data fault); the share
   removed is reported by month.
4. **Rare segments.** A segment with fewer than 1 000 kept passes in the window (a diversion or a one-off routing) is
   removed; how many and their share of passes are reported.

## 4. Estimation and inference

- S and ρ are computed on the screened passes. Their 95 % and 90 % intervals come from a bootstrap that resamples whole
  service dates with replacement (999 draws, seed fixed in the code), recomputing the ranking in every draw, so the
  choice of the top 10 % is part of the uncertainty.
- For ρ, the odd/even split is made within each draw.

## 5. Labels

- **Q1, supported:** the 95 % interval of S lies wholly above 0.50 (a tenth of the segments makes most of the delay).
  **Not supported:** wholly below 0.50. **Inconclusive:** otherwise.
- **Q2, supported:** the 95 % interval of ρ lies wholly at or above 0.70. **Not supported:** wholly below 0.70.
  **Inconclusive:** otherwise.
- If either 95 % interval is wider than 0.20, the estimate is reported as imprecise next to its label.

## 6. Checks (reported; none relabels a primary result)

- **Per pass instead of total.** Q1 with segments ranked and summed by mean gain per pass.
- **Top 5 % and top 20 %** instead of 10 %.
- **Without the first and last segment of each trip** (terminal effects, timetable padding at the end).
- **|g| ≤ 300 s** instead of 600 s.
- **By month.** S for each calendar month.
- **Buses** (secondary): Q1 and Q2 with their own labels.

## 7. Outputs

An article on bsandova.com, part 1 of *Running late*, with an interactive map of the tram network: segments coloured
by the delay they produce, with views for all hours, peaks, middays and recovery, and the checks as interactive
charts.

## 8. What this will not show

- **Causes.** A segment where delay appears is not always where it is caused: a junction or a stop can hold a tram
  that then loses time on the next segment, and timetable padding decides where a late tram can catch up. The map
  shows where delay is recorded.
- **Passenger delay.** Seconds per vehicle, not per person on board.
- **Other years, the metro, winter.**

## References

Further references (on delay propagation and timetable padding) are verified before publication, in a dated commit.

## Changes after registration

**8 October 2026 (screening, §3; no segment's delay summarised).** `tools/late/screen.py`, output
`delay-origins-screen.json`. The column `delay_gain` equals `real_travel_time − planned_travel_time` in every sampled
pass and differs from `delay_to − delay_from` in 99.9 % of them: it is running time against schedule, without the
time spent at the stop. By §3.1 the gain is recomputed as `delay_to − delay_from`, so a segment's gain includes the
dwell at its first stop; with it, the gain is missing for 2–3 % of tram passes (48 % for `delay_gain`). Running time
alone is added as a check (§6), decided here before any value is read. After screening: 618 tram segments, 21.4
million passes, 170 dates; 48 rare tram segments (9 116 passes) removed. Planned closures remove 2–31 % of tram passes
by month, as in the earlier studies. Stop coordinates from the thesis's stop table cover 279 of the 618 tram segments;
the map takes the rest from another source, which affects the map only.

**8 October 2026 (code frozen; no segment's delay summarised).** `tools/late/estimate.py` runs §4–§6;
`tools/late/test_late.py` checks it on made-up data: the concentration share with recoverers outside the denominator,
the labels, strong stable hotspots labelled supported on both questions, pure noise labelled not supported on both,
and every check including the peak–midday overlap and the map rows.
