# When the power went out: how Prague's trams stopped and came back on 4 July 2025 — research design

**Status: pre-specified analysis, design committed 14 October 2026, before any transit record of 4 July 2025 was read
on its own.** A descriptive case study of one event. The steps follow in dated commits: design → screening → code →
results. Commit times are self-reported. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The event, from public sources.** The ENTSO-E expert panel's factual report (19 December 2025): line V411 tripped
  at 11:51:08, the island collapsed at 11:59:47 with about 2 300 MW of load lost; for Prague, Malešice 220/110 kV was
  back at 12:30 and Chodov 400 kV at 13:01; all lost load was back at 17:35. ERÚ's final report (23 June 2026). News
  live blogs citing DPP and TSK: right-bank tram lines stopped and left-bank ones ran; metro A and C resumed at 12:15
  and B at 12:35; two tram sections were still without power at 14:38; "tram service returned to normal" at 15:16; key
  traffic signals were back by 14:55. These times are known and are used below as external checks, not as unknowns.
- **The transit data.** `tools/data/rain/prague_transit.duckdb` (the author's master's thesis; Golemio data for PID),
  15 March – 8 September 2025. Every earlier study on this site used it with 4 July as one of about 170 dates, inside
  window-wide sums; none reported that date on its own. The author confirms (14 October 2026) that she never looked at
  4 July on its own, in the thesis or elsewhere. A feasibility check (14 October 2026) read the table schemas, the
  date range, row counts of four ordinary days (16 May, 6, 13 and 20 June) and whether 4 July is on two earlier
  exclusion lists: it is on the rain study's line-level closure list and not on its feed-gap list. No value of 4 July
  was read.
- **Review.** A draft of this design was read by an independent methods reviewer, who ran its rules on the baseline
  and June Fridays only (§2): tram passes per 10-minute bin, the spread between baseline days, empty segments in
  12:10–12:30 and long gaps on an ordinary day, and the rules applied to one baseline day against the other two (a
  placebo). Those ordinary-day numbers are known; the version below takes in the review.
- **Archived PID disruption pages** (`tools/data/rain/pid/pages`) may hold official restoration times. They have not
  been read for 4 July; they are used only as a check (§6).
- **Prior expectation.** Stated by the author on 14 October 2026, knowing the public timeline above: trams started
  running again soon after the power came back, but their delays lasted hours longer.

## 1. Questions

All are descriptive: one event cannot show what causes a network to recover faster, and nothing here is labelled
supported or not. Every statistic is reported with its **placebo**: the same rule applied to each baseline day against
the other two. A value of 4 July inside the placebo range is not read as an effect of the outage.

- **Q1, how much stopped.** The share of tram service in 12:10–12:30 on segments with no observed pass in that
  interval, each segment weighted by its mean passes in the interval over the baseline days. Segments with fewer than
  3 baseline passes on average in the interval are excluded from the share and counted separately.
- **Q2, how fast it came back (headline).** The service ratio R(t): observed passes of a mode in a 10-minute bin divided
  by the mean of the baseline days in the same bin. **T₅₀** and **T₉₀**: the start of the first bin at or after 12:00
  from which, of six consecutive bins (an hour), at least five have R at or above 0.5 (respectively 0.9) and none is
  missing.
- **Q3, how long delay lasted after restart (headline).** D(t), the median delay of a mode's passes in a bin; a bin with
  fewer than 20 passes is missing. The baseline band of a bin is the lowest to highest baseline-day median, widened on
  each side by max(30 s, 25 % of the mean of the three medians). **T_D**: the start of the first bin at or after 12:00
  from which at least five of six consecutive bins lie within the band and none is missing.
- **Q4, in what order.** For each tram segment that stopped (Q1), its restart lag: the time of its first observed pass
  after 12:10, minus 12:10, minus half its mean baseline headway in 12:00–14:00. Segments whose baseline headway
  there exceeds 15 minutes are listed but not mapped. The lag after 13:01 (the last Prague substation back) is
  reported for each mapped segment.
- **Q5, the rest of the system.** T₅₀, T₉₀ and T_D for metro and buses by the same rules. Trolleybuses are shown as
  curves only: their baseline varies too much between days for the rules (about 56 passes per bin).

## 2. Data and definitions

- **Table.** `stop_times_history_modeling`: one row per trip and segment with scheduled and observed times to the
  second. A **pass** is a row with an observed arrival at the next stop (`real_next_stop_arrival`); its time is that
  arrival in Europe/Prague local time (not the `day` column), its delay `next_stop_arr_delay`. Modes from
  `route_type`: `tramvaj`, `metro`, `autobus`, `trolejbus`; trains (`vlak`) are used only in §3.1, ferries (`přívoz`)
  not at all.
- **Segment** as in part 1 of *Running late*: an ordered pair (stop, next stop) by name; rows whose two names are equal
  are dropped.
- **Event day.** Friday 4 July 2025, 10:00–22:00 local, in 10-minute bins starting at 10:00:00.
- **Baseline days.** Fridays 11, 18 and 25 July 2025: the same summer-holiday timetable and weekday. If screening
  (§3) rejects one, it is replaced by Friday 1 August, then 8 August.

## 3. Screening (before any value of 4 July is summarised)

Committed as `blackout-screen.json`, with counts and flags only.

1. **Feed alive.** For each bin of 4 July, the ratio R of buses and of trains (neither runs on traction power). A bin
   with either below 0.5 is **feed-suspect**: it is missing for every mode. A bin with either in 0.5–0.8 is flagged and
   read, and the flag is shown. (On the baseline days, bus R against the other days stays within 0.89–1.07.) Only the
   flags are written at this step, not the ratios.
2. **Baseline days.** A baseline day is rejected if any mode's daily pass count is more than 20 % from the mean of the
   three, or if tram or bus R against the other two is below 0.7 in more than six bins.
3. **Rows.** Passes with |delay| > 3 600 s are kept (a tram standing for an hour is the event) and counted.

## 4. Estimation

- R(t), D(t), T₅₀, T₉₀, T_D, the Q1 share and Q4 per segment, exactly as defined, for 4 July and, as placebos, for
  each baseline day against the other two. No model, no interval: with one event, the placebo range is the only
  reference for ordinary variation.

## 5. What is read as the result

- **Q2–Q3:** T₅₀, T₉₀ and T_D for trams next to their placebo ranges, with the curves; the gap between T₉₀ and T_D
  (service back, delays still not), which is the author's prior expectation.
- **Q1:** the stopped share next to its placebo range.
- **Q4:** the order and the lag after 13:01.

## 6. Checks (reported; none changes a definition)

- **Metro as positive control.** For each metro line, the median over its segments of the first observed pass after
  12:00, against the reported 12:15 (A, C) and 12:35 (B). If a line misses by more than 10 minutes, every restart time
  in the study is reported as uncertain by that amount.
- **News and PID times.** Tram T₉₀ against the reported "back to normal" at 15:16; the two sections reported without
  power at 14:38 against their Q4 lags; and the PID disruption pages' restoration times, if any, against Q4.
- **Thresholds and bins.** 0.85 instead of 0.9; all six bins instead of five of six; bins of 5 and 15 minutes; Q1 over
  12:10–12:40.
- **Mean delay** instead of median in Q3.
- **Departures**, a different sample: R(t) from observed departures (`real_current_stop_departure`), present on about
  half of tram rows.
- **June Fridays** (6–27 June) as a second reference for the curves only; June has the school timetable and about a
  fifth more passes, so no T is computed against it.

## 7. Outputs

An article on bsandova.com: the R(t) and D(t) curves for each mode against the baseline band, a map of tram segments
coloured by restart time, and a timeline that sets the grid events next to the network's.

## 8. What this will not show

- **Why.** Which substation fed which section, how DPP dispatched trams and how many passengers were stranded are not
  in the data. Order of restart is confounded with geography and the traction supply.
- **Stopped against unrecorded.** A tram standing between stops, a trip cancelled midway, a short turn that matches no
  timetable trip and a gap in the feed all leave no pass. §3.1 separates a feed gap from a stop only when buses and trains keep
  logging; buses were also slowed by the traffic signals that failed.
- **Resilience in general.** One event in one city, one season and one time of day.

## References

ENTSO-E (2025), *4 July grid incident in the Czech Republic: expert panel factual report*. ERÚ (2026), *Závěrečná
zpráva k výpadku elektřiny 4. 7. 2025*. Zhang, Hörcher, Bansal and Graham, *Causal resilience curves* (arXiv
2310.07514). Further references are verified before publication, in a dated commit.

## Changes after registration

**14 October 2026 (screening, §3; no ratio, pass count or delay of 4 July summarised beyond the flags).**
`tools/blackout/screen.py`, output `blackout-screen.json`. The baseline days 11, 18 and 25 July all pass §3.2. §3.1 was
wrong to take trains as a reference that does not depend on traction power: most Czech lines are electric, and the
outage stopped trains too. With buses and trains, the first run flagged 29 bins of 4 July (12:00–17:10), three of them
(12:50–13:10) feed-suspect; that output was seen. The rule is applied to buses alone, as the reference the design
meant: with them, no bin is flagged, so the feed was alive all day and every bin is read. The bus-and-train flags are
reported next to the article as a disclosed first run. Rows with delay over an hour on 4 July are counted (§3.3):
3 910 tram passes, 75 bus passes.

**14 October 2026 (code frozen; no value of 4 July summarised).** `tools/blackout/estimate.py` runs §1, §4 and §6;
`tools/blackout/test_blackout.py` checks it on made-up data: a network stopped 12:00–13:00 restarts at 13:00 and its
delays come back two hours later, an ordinary day gives 12:00 for every time (the placebo), one thin bin does not move
T₉₀, the stopped share and the restart lag, the exclusion of low-frequency segments, and the metro control. The tests
showed that "the first bin from which at least five of six bins" lets a run open on a bin that fails, one bin before
service came back; the opening bin must now meet the rule itself. This reads the definitions as meant ("from which R
stays") and was fixed before any value of 4 July was computed.
