# Will you make your connection? Tram transfers in Prague — research design

**Status: pre-specified analysis, design committed 8 October 2026, before any transfer was computed.** Part 3 of the
series *Running late*. The steps follow in dated commits: design → screening → code → results. Commit times are
self-reported. Deviations are listed, dated, in the change log. A draft of this design was reviewed by an independent
methods reviewer before registration; the version below replaces the draft, whose primary prediction was close to true
by construction and whose stand-in for departures was biased towards it.

## 0. What has already been seen

- **Arrival times.** The *Weather on the rails* studies read observed and scheduled tram arrivals (or departures where
  the arrival was missing) in `stop_times_history_modeling`, to compute the delay a trip gains within a clock hour per
  route and direction; the dwell study of that series found an observed departure for only about half of non-terminal
  tram passes, varying by stop. No arrival of one line has been compared with a departure of another.
- **Part 1** (*Where is delay born?*): results computed and seen, not yet published (commit 52ef4b6 on the branch
  feature/LATE-1_where-delay-is-born, 8 October 2026):
  the per-segment delay produced, the screening (170 dates, the closure list, gain missing for 2–3 % of tram passes)
  and the list of top producers.
- **Part 2** (bunching) is designed; no headway has been computed.
- **Prior expectation.** The author expects tight tram-to-tram transfers to fail often enough to matter, more in the
  peaks, and expects the delays of two lines meeting at a hub to move together within a day, beyond what the day's
  conditions do to both (shared streets and junctions), which makes connections more likely than independent delays
  would.

## 1. Definitions

- **Platforms and hubs.** A platform is a GTFS stop id (`gtfs_stop_id` in the table, `stops.txt` for coordinates and
  parent station). A **transfer pair of platforms** is an arrival platform of line A and a departure platform of line
  B within 250 m of each other in a straight line. A **hub** is a parent station (or, where none, a stop name) whose
  platforms are served by at least four tram lines, each with at least 20 scheduled passes on a median weekday of the
  window, so that lines diverted for a few weeks and night lines do not count.
- **Walking margin.** m = 60 s + d / 1.2 m s⁻¹, where d is the straight-line distance between the two platforms (0 for
  the same platform): a minute to get off and orient, then walking at 1.2 m/s.
- **Transfers studied.** A ≠ B; B's next stop is neither A's previous stop (going back) nor A's next stop (the same
  trunk, where a traveller simply takes the first tram); stop identity by parent station, or by stop name where a
  stop has none. Branches and short turns of A or B are kept as their own directions. Excluded pairs are listed per
  hub.
- **Planned connection.** For each arrival of A at the hub, the planned B is the first B trip whose scheduled
  departure from its platform is at least m after A's scheduled arrival; the **planned slack** s = B's scheduled
  departure − A's scheduled arrival.
- **B leaves at** dep_hat = the later of B's observed arrival and B's scheduled departure, on the assumption that trams
  do not leave before their scheduled time at a hub. Using the observed arrival alone would count as missed a B that
  arrives early and waits, and would bias the share made downwards. The assumption is tested in screening (§4.7) on
  observed departures, where they exist.
- **Made.** The planned B is caught if dep_hat ≥ A's observed arrival + m.
- **Extra wait.** w = (dep_hat of the first B of any trip that is catchable) − (scheduled departure of the planned B):
  the traveller's wait over the plan, which may be negative when an earlier, late B is catchable. A miss is costly when
  w > 5 min. Waits over 30 min are censored at 30 and their share is reported.

## 2. Questions and estimands

- **Q1, do delays at a hub move together within a day? (primary).** Δp_within = p_obs − p_within. p_obs is the share
  of planned connections with slack 2–4 min that are made. p_within is the same share when each A arrival is set
  against the other B trips of the same line pair and hub on the same date, within ±60 min of its planned B (the
  planned B and the trips directly before and after it excluded), each shifted to the planned B's scheduled departure
  so the slack is unchanged: the day's conditions are kept, the trip-to-trip link between the two lines is broken.
  p_within is computed exactly, as the average over all such donors for each A arrival, not by random draws.
  Prediction: Δp_within > 0 (the two lines are late together at the moment, through shared streets and junctions).
- **Q1b, including the day (secondary, own label).** Δp_day = p_obs − p_day, with donors from other dates of the same
  timetable period and weekday type (a timetable period = dates with the same set of scheduled trips of the line pair
  at the hub), matched on A's scheduled arrival and the planned B's scheduled departure, so the slack is identical;
  adjacent dates (±1 day) are excluded as donors. This bundles same-moment and same-day co-movement (weather,
  disruptions), and is reported beside Q1, not instead of it.
- **Q2, the cost of a tight transfer (descriptive).** For slack 2, 3 and 4 min separately: the share made, the share
  of costly misses (w > 5 min), and the median extra wait; by hub, hour band (weekday peaks 07:00–08:59 and
  15:00–17:59, weekday daytime, evening, weekends).
- **Q3, the curve and the roulette (descriptive).** For each hub × line pair × direction × hour band, the distribution
  of Δd = (B's dep_hat − B's scheduled departure) − (A's observed arrival − A's scheduled arrival); the share made at
  any slack s is then P(Δd ≥ m − s) on the observed connections of that cell, and the share made computed from the
  connections themselves is shown beside it where the cell has them, as a test of the model, with a calibration plot
  of predicted against observed across all cells with data. The interactive "transfer roulette" shows the cell a
  reader picks, its interval, and a note that picking the best or worst of many cells exaggerates by selection.
- **Q4, where misses come from (descriptive).** The share of costly misses in which A was already later than s at the
  stop before the hub, against those where it lost the time on the last segment, and whether that segment is one of
  part 1's top producers (ranked on odd ISO weeks, evaluated on even weeks, then swapped); an A without an observed
  arrival at the stop before is its own category.

## 3. Data

- `stop_times_history_modeling` (the author's master's thesis; Golemio vehicle positions for PID), trams, 15 March –
  8 September 2025: scheduled `current_stop_arrival` and `current_stop_departure`, observed
  `real_current_stop_arrival` and `real_current_stop_departure`, `gtfs_stop_id`, `stop_name`, `next_stop_name`,
  sequence; date from `year`, `month`, `day`; route = the second field of `rt_trip_id`; direction = the trip's terminal.
  The service date of a trip is the date of its first scheduled arrival (Europe/Prague time).
- GTFS static data (`tools/data/praha2/gtfs/`, stops and trips) for platform coordinates and parent stations; it has
  no calendar, so it is not used to decide which trips ran.
- Part 1's segment table for Q4.

## 4. Screening (before any connection is summarised)

Fixed now; only counts and shares are summarised; committed as `transfers-screen.json`:

1. **Service.** The rain study's planned closures (by line and date) and feed-gap dates are removed for both lines:
   170 dates.
2. **Hubs and platform pairs** are listed with their lines, distances and margins.
3. **Missing trips.** For each hub × line × hour within a timetable period and weekday type, the modal number of
   scheduled trips across its dates is the expected count; a date with fewer trips in the table than expected has
   that many trips missing (cancelled or untracked). Their share is reported by hub and month, for A and B.
4. **Observed.** An A or B arrival missing in its row is filled from the previous row's `real_next_stop_arrival` when
   the two agree on a sample where both exist. Connections with an unobserved A arrival are removed; those whose
   planned B is missing or unobserved are kept as a separate class, and Q1, Q1b and Q2 are given bounds that count them all
   as made and all as missed.
5. **Terminals.** An A ending at the hub is kept (its last row's arrival is checked to exist). A B starting at the hub
   uses its scheduled departure as dep_hat when it has no observed departure, and the hubs affected are listed.
6. **Thin cells.** A roulette cell needs at least 500 observed connections on at least 30 dates; others are shown as
   "too few connections".
7. **Early departures.** Where B's departure is observed, the share leaving more than 30 s before its scheduled
   departure, by hub. A hub where that share exceeds 5 % is removed from Q1 and Q1b and marked in the roulette, and the
   list is reported.
8. **Precision.** From the counts alone (connections with slack 2–4 min per week), the expected width of Q1's interval
   and its minimum detectable Δp_within at 80 % power; if it exceeds 3 percentage points, Q1 is reported as
   underpowered in advance.

## 5. Inference

- Q1 and Q1b: a block bootstrap over ISO weeks (999 draws). Because p_within and p_day are exact averages per A
  arrival, each draw only re-weights arrivals and their donor averages; for Q1b, donor dates are restricted to the
  weeks in the draw, and the same date and adjacent dates are never donors. The donor tables are precomputed once.
  Hub-level estimates are reported beside the pooled one; the pooled estimate weights hubs by their connections (a
  network share, not an average hub), and a check resamples hubs as well as weeks.
- Descriptive intervals use the same week-block bootstrap.

## 6. Labels

- **Q1, supported:** the 95 % interval of Δp_within lies wholly above +1 percentage point. **Not supported:** the 90 %
  interval lies wholly within ±1 point (as good as independent at the moment). **Inconclusive:** otherwise, including
  an interval wholly below 0, reported as such.
- **Q1b:** the same rules on Δp_day.
- Q2–Q4 are descriptive and carry no label.

## 7. Checks (reported; none relabels a primary result)

- **Observed departures** instead of dep_hat where B's departure is observed, and the share of those where B left
  before its scheduled departure (a test of the assumption in §1).
- **Timing noise.** Q1 and Q2 with A's arrival, and separately B's, shifted by ±30 s.
- **Margins.** m − 30 s and m + 30 s, and a fixed m = 2 min.
- **Hub definition.** By stop name instead of parent station and distance.
- **Without the trunk and return exclusions.**
- **Peaks only**, **school holidays** (28 June – 31 August) separately, and **by line pair**.

## 8. Outputs

An article on bsandova.com, part 3 of *Running late*, with the transfer roulette as its main figure, the cost of a
tight transfer by slack, and a map of the hubs, every figure interactive.

## 9. What this will not show

- **Real travellers.** Connections are possible, not observed: no one is followed from one tram to another.
- **Walking in detail.** One walking speed and straight-line distances; stairs, crossings and crowds are not modelled.
- **Buses, the metro and rail.**
- **Other years, winter.**

## References

Sources on transfer reliability, walking speed in transit planning and connection planning are cited, verified,
before the code is frozen, in a dated commit.
