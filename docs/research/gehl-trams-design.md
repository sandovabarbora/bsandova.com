# Does rain empty Prague's trams? — research design

**Status: pre-specified analysis, design committed 8 October 2026, before any dwell time was read.** Part 1 of the
series *Gehl, measured*. The steps follow in dated commits: design → screening (dwell alone) → power (weather only) →
code → results. Commit times are self-reported. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **Dwell times.** Only the schema of `stop_times_history_modeling` was read: it has `planned_dwell_time` and
  `real_dwell_time` (both `DOUBLE`) next to the scheduled and observed arrival and departure. No dwell value was
  printed, summarised or written. The rain and heat studies (`rain-delays-design.md`, `heat-delays-design.md`) read
  delays only; their unit builder selects no dwell column. The author's thesis and its article on this site do not
  report dwell times.
- **Weather.** ČHMÚ hourly precipitation (March–September 2025) and ten-minute air temperature (May–September 2025)
  were read for those two studies, and delay gained was read against both. Neither study read dwell, boarding or any
  ridership proxy against weather.
- **The heat result.** Part 2 of *Weather on the rails* found trams gaining less delay in hot hours, and its article
  names fewer passengers as one possible reading. This study tests that reading (§6, H) and says so in advance.
- **Prior expectation.** The author expects rain to shorten dwell more on weekend middays than on weekday mornings, as
  Gehl predicts, with a small difference in seconds, and expects heat to shorten dwell somewhat.

## 1. Theory and question

Jan Gehl divides outdoor activities into *necessary* ones, which take place in nearly any conditions because people
have to do them (going to work or school), and *optional* ones, which take place only when conditions invite them,
weather first among them (*Life Between Buildings*, 2011 edition, pp. 9–11; *Cities for People*, 2010, pp. 20–21). He
states it for walking and staying in public space. A tram trip begins and ends on foot, so the same split should show
in who boards: in bad weather the commute happens anyway and the trip to the park, the shops or a friend's does not.

Prague publishes no passenger counts by hour for these months. The study therefore uses **dwell time**, the seconds a
tram stands at a stop between arrival and departure, which grows with the number of people boarding and alighting.
It measures boarding indirectly and says so wherever the result is reported.

- **Q (primary).** In Prague in 2025, does rain shorten tram dwell times more in optional hours than in necessary
  hours?
- **Necessary hours:** Monday to Friday, 06:00–08:59 Prague time, excluding Czech public holidays.
- **Optional hours:** Saturdays, Sundays and Czech public holidays, 10:00–17:59.
- All other hours are left out of the primary contrast.
- **Rain hour / dry hour:** as in the rain study (§1 there): four-station mean `SRA1H` ≥ 0.5 mm is a rain hour; a dry
  hour has 0.0 mm at all four stations in the hour and the two before; other hours are left out of the primary
  contrast.
- **Estimand (primary).** θ = (rain − dry difference in Y in optional hours) − (rain − dry difference in Y in necessary
  hours), in seconds, from the model of §4. Gehl's prediction is θ < 0: rain takes away a larger part of the optional
  boarding.

**Why a difference of differences.** Rain may lengthen every stop by itself: umbrellas, wet floors, slower steps,
doors held for someone running. That effect is common to both kinds of hour and cancels in θ, provided a wet
passenger takes as long to board on a Saturday as on a Tuesday. The rain effect in each window alone is reported but
not labelled.

## 2. Data

- **Dwell.** `stop_times_history_modeling` (the author's master's thesis, Golemio vehicle positions for PID,
  March–September 2025), trams only (`route_type = 'tramvaj'`). Per stop pass: observed dwell D = `real_dwell_time`
  in seconds. Route = second field of `rt_trip_id`; direction = the trip's terminal, as in the rain study.
- **Weather.** ČHMÚ open climate data, the rain study's four stations: hourly `SRA1H` and ten-minute air temperature
  `T` (hourly mean, a station counting with at least four of six values); CC BY 4.0.
- **Calendar.** Czech public holidays (Act No. 245/2000 Coll.): in the window 18 and 21 April, 1 and 8 May, 5 July and
  28 September 2025; the school summer holidays 28 June – 31 August 2025 and Prague's spring break.
- **Screening of service.** The rain study's screening (planned closures, feed-gap dates) is applied unchanged.

## 3. Screening (dwell alone, before any dwell value is joined to weather)

Fixed now, applied from the stop passes alone and committed as `gehl-trams-screen.json` and `-screen.md`:

1. **Definition check.** On a random 0.1 % of tram passes, D is compared with observed departure minus observed
   arrival; if they differ by more than 1 s in more than 1 % of passes, D is recomputed from the timestamps and the
   change is logged.
2. **Pass rules.** A pass is kept if it is not the trip's first or last stop (layovers), has both observed times, and
   0 ≤ D ≤ 180 s. The shares removed by each rule are reported by month and hour, not by weather.
3. **Zeros.** Passes with D = 0 (no stop, or a request stop not served) stay in; their share is reported. The
   outcome on stopped passes only is a check (§6).
4. **Unit.** A route-direction × date × clock hour, 05:00–23:59. Y = mean D over the unit's kept passes, in seconds.
   A unit needs at least 10 kept passes.
5. **Dispersion.** The residual spread of Y on the cell and date effects of §4 (σ_e) and the share of a date's
   variance common to all units (σ_c, ρ) are measured on dwell alone, for the power step, as the rain study did for
   delays.
6. **Margin.** m = 5 % of mean Y in dry necessary hours, rounded to 0.1 s, fixed at this step from that one mean. It
   is the "same response" band of §5.

## 4. Estimation

- **Model.** Y_{r,d,h} = β · Rain_{d,h} + θ · Rain_{d,h} × Optional_{d,h} + α_{r × direction × hour × weekday} +
  γ_date + ε, OLS on trams, rain and dry hours in the two windows only. α absorbs each route's usual dwell by hour and
  weekday, which already holds the two windows' different levels; γ absorbs anything common to a date (season,
  holidays, events, a feed's quirks). Units weighted by their number of kept passes. Singleton cells and dates dropped
  before fitting, as in the rain study.
- **Inference.** Standard errors clustered by date. If fewer than 30 dates hold a rain hour in the optional window, a
  wild cluster bootstrap by date (999 draws, Rademacher, percentile-t) replaces the analytic interval.

## 5. Labels

- **Supported:** the 95 % interval of θ lies wholly below 0.
- **Not supported:** the 90 % interval of θ lies wholly within ±m (two one-sided tests): rain shortens dwell alike in
  both kinds of hour.
- **Inconclusive:** anything else, with the reason stated, including an interval wholly above 0 (the opposite of the
  prediction), which is reported as such.

## 6. Secondary questions and checks (reported; none relabels the primary result)

- **H, heat (secondary, own label by the same rules on its own estimand).** Do hot hours shorten tram dwell?
  δ_H = hot − mild difference in Y, the heat study's definitions and model (hot ≥ 30 °C, mild 15–25 °C, dry hours,
  route × direction × hour × weekday and ISO-week effects), all hours 05:00–23:59. Supported if the 95 % interval lies
  wholly below 0; not supported if the 90 % interval lies within ±m. A supported δ_H is consistent with fewer
  passengers in the heat; it does not prove it.
- **Heat, Gehl's contrast.** Hot hours fall mostly in the afternoon, outside the necessary window, so θ_H uses weekday
  15:00–18:59 (the trip home, partly optional) against optional 12:00–18:59, week effects. Reported without a label.
- **Dose.** Rain in bands 0.5–2, 2–5 and ≥ 5 mm, by window.
- **Evening.** Weekday 15:00–18:59 as the necessary window.
- **School holidays out.** 28 June – 31 August and the spring break dropped.
- **Stopped passes only** (D > 0).
- **Weekday midday.** Weekday 10:00–14:59 as a third window, between the two.
- **Centre against outskirts.** Stops within the Prague 1 and 2 districts against the rest, by the stop coordinates.
- **Placebo.** Rain two days later in the same hour instead of the current one; expected near 0.
- **Delay held.** The model with the unit's delay gained (the rain study's Y) added as a control, to separate standing
  longer because the tram is early or held from standing longer because people board.

## 7. Power

Computed after screening and before θ is estimated, from weather only (the number of rain and dry hours in each window
by date) and the dispersion measured in §3.5, with the simulation of `tools/rain/power.py` adapted to the interaction.
It states the minimum detectable θ at 80 % power. If it is larger than 4m, the study is reported as underpowered in
advance and the primary label can be at most inconclusive. If fewer than 10 dates hold a rain hour in the optional
window, the study is reported as not estimable.

## 8. Outputs

An article on bsandova.com, part 1 of *Gehl, measured*: the rain response of dwell in necessary and optional hours,
the heat answer to *Weather on the rails* part 2, the dose and the checks, and a map of where Prague boards (mean
dwell by stop, dry hours only, no weather), every figure interactive.

## 9. What this will not show

- **Passengers.** Dwell rises with boarding and alighting, but also with door faults, wheelchairs and prams, and
  drivers holding for time; it is not a count.
- **Walking.** Gehl's claim is about people on foot and in public space; this is its trace in who boards a tram.
- **Who and why.** "Necessary" and "optional" are defined by the clock and the calendar, not by asking anyone.
- **Other modes, years and cities.** Buses share the road with traffic that also responds to rain, so they are left
  out; the window is one season of 2025.

## References

Gehl, J. (2010) *Cities for People*. Washington, DC: Island Press. Gehl, J. (2011) *Life Between Buildings: Using
Public Space*. Washington, DC: Island Press. Further references (dwell-time models, ridership and weather) are verified
before publication, in a dated commit.

## Changes after registration

**8 October 2026 (screening, §3; dwell read alone, no dwell read against weather).** `tools/gehl/screen.py`, output
`gehl-trams-screen.json`. `real_dwell_time` equals observed departure minus arrival in every sampled pass, so it is used
as is. A departure is detected for about half of the non-terminal tram passes (from about 4 % missing at Anděl to all
at Nákladové nádraží Žižkov), steady across months and hours; dwell is therefore measured at the stops that detect a
departure, and the article says so. Whether weather changes that coverage was checked from counts alone, before any
dwell is joined to weather (`tools/gehl/coverage.py`, `gehl-trams-coverage.json`, a check the design did not name):
the share with a departure is 50.8 % in rain hours and 50.6 % in dry hours, 0.2 points apart within dates (hot against
mild: 0.1 points). No zero dwell occurs, since a detected stop always takes time, so the "stopped passes only" check
of §6 coincides with the primary outcome and is dropped. Units: 160 696 on 170 dates; σ_e 2.57 s, σ_c 0.47 s, ρ 0.34,
a median 46 units per date × hour; mean dwell in dry necessary hours 39.9 s, so m = 2.0 s.

**8 October 2026 (power, §7; weather only, no dwell read against weather).** `tools/gehl/power.py`. As registered,
the optional window holds 15 rain hours on 8 dates, below the 10 dates §7 requires, and only 3 optional and 1 necessary
date hold both a rain and a dry hour in the window, which is all that date effects leave to identify θ. The primary
question was therefore not estimable as registered.

**8 October 2026 (deviation, decided before any dwell is read against weather).** To keep Gehl's question and the
series' definition of rain:

- **Optional hours** become Saturdays, Sundays and Czech public holidays, 08:00–20:59 (was 10:00–17:59): a weekend
  outing spans the day. Necessary hours are unchanged.
- **Week instead of date effects** in §4, as in the heat study: Y = β · Rain + θ · Rain × Optional +
  α_{route × direction × hour × weekday} + ω_{ISO week} + ε. Date effects are reported as a check, with the interval
  expected to be wide.
- The rain and dry definitions, the labels (§5), m and the other checks are unchanged. Power is recomputed for this
  model with a date-level shock measured from dwell alone (residuals on cell and week effects, averaged by date), as
  the heat study did.

**8 October 2026 (power after the deviation; weather and dwell alone).** `gehl-trams-power.json`. The date-level
shock, measured from dwell alone, is σ_day 0.41 s. With optional hours 08:00–20:59 and week effects, the optional
window holds 30 rain hours on 14 dates (10 of them also with a dry hour in the window) and the necessary window 19 on
10; the simulated SE of θ is 0.29 s and the minimum detectable θ 0.8 s, well under the 8 s rule. With fewer than 30
optional rain dates the wild cluster bootstrap applies, and the evidence rests on 14 wet weekend days: this is stated
now. The simulation assumes normal shocks and is a floor on the real interval.
