# Does heat delay Prague's trams? — research design

**Status: pre-specified analysis, design committed 8 October 2026, before any temperature value was read.** The steps
follow in dated commits: design → power (temperature only) → code → results. Commit times are self-reported.
Deviations are listed, dated, in the change log. Work on this study began in October 2026; the delay data are the
same as in the rain study (`rain-delays-design.md`).

## 0. What has already been seen

This study reuses the rain study's data, screening and code, so it does **not** start blind on the outcome:

- **Delays.** The rain study (8 October 2026) built the units (`tools/rain/units.py`) and read delay gained against
  rain: its dispersion (σ_e 36.7 s, city-wide shock σ_c 11.9 s, ρ 0.34), the rain and dry-hour means, the dose curve
  and one estimate per tram route. Delay gained has **not** been read against temperature, by hour of day, by season
  or by date in any table or chart.
- **Temperature.** Only the element list of one ČHMÚ 10-minute file (Ruzyně, July 2025) was opened to confirm that air
  temperature (`T`) is published; no value was printed. All four stations of the rain study publish 10-minute files
  for every month of 2025.
- **Prior expectation.** The author expects hot hours to add some delay to trams (rail and overhead-line limits, slower
  boarding, failing air conditioning) and less, or none, to the metro. The tram estimate is expected to be small.

## 1. Question and estimand

- **Q (primary).** In a clock hour with heat in Prague, do trams gain more delay than in a mild hour of the same route,
  direction, hour of day and weekday, in the same week?
- **Unit and outcome.** As in the rain study (§1 there): a route-direction × date × clock hour of trams, 05:00–23:59
  Prague time, outcome Y = mean delay gained per trip in the hour (seconds), from stop passes.
- **Treatment (fixed now).** T_h = the mean over the four stations (Ruzyně, Libuš, Kbely, Klementinum) of the hour's
  10-minute air temperatures `T` (h:00–h:59 local; ČHMÚ times converted from UTC; a station counts if it has at least
  four of its six values).
  - **Hot hour:** T_h ≥ 30.0 °C.
  - **Mild hour:** 15.0 °C ≤ T_h ≤ 25.0 °C.
  - Hours in between, hours below 15 °C, and every hour that is not a dry hour under the rain study's rule (all four
    stations 0.0 mm of precipitation in the hour and the two before) are left out of the primary contrast.
- **Estimand (primary).** δ_tram: the average difference in Y between hot and mild hours for trams, within route ×
  direction × hour-of-day × weekday cells and within ISO weeks, in seconds of delay gained per trip-hour. δ_bus (city
  buses, routes 100–299) is estimated alongside and reported with its own label; it is secondary.

## 2. Data

- **Delays.** `tools/data/rain/units.parquet`, the rain study's units, with its screening applied unchanged: planned
  closures (rule 1 as applied), feed-gap dates (rule 2, 8 dates) and units with fewer than two trips (rule 3).
- **Temperature.** ČHMÚ open climate data, 10-minute files (`historical/data/10min/2025/10m-<WSI>-<yyyymm>.json`),
  element `T`, the four stations, March to September 2025; CC BY 4.0.
- **Precipitation.** As in the rain study (hourly `SRA1H`), used only to keep dry hours.

## 3. Estimation

- **Model.** Y_{r,d,h} = δ · Hot_{d,h} + α_{r × hour × weekday} + ω_{week} + ε, OLS, separately for trams and buses, on
  hot and mild dry hours only. α absorbs a route's usual pattern by hour and weekday; ω absorbs anything common to an
  ISO week (season, school holidays, timetable regime). Units weighted equally; units alone in their cell or week are
  dropped before fitting (as fixed in the rain study's code).
- **Why the week and not the date.** Heat is a property of the day as much as of the hour; with date effects, δ would
  be identified only from the part of a hot afternoon that departs from that same day's morning, which is what the
  hour effects already model. The date-effect version is reported as a check (§5), and its interval is expected to be
  wide; this is stated now.
- **Inference.** Standard errors clustered by date. If fewer than 30 dates hold a hot hour, a wild cluster bootstrap by
  date (999 draws, Rademacher, percentile-t) replaces the analytic interval.

## 4. Labels (δ_tram; the same rules give δ_bus its own label)

- **Supported:** the 95 % interval of δ lies wholly above 0.
- **Not supported:** the 90 % interval of δ lies wholly within ±10 s (two one-sided tests), the margin of the rain study.
- **Inconclusive:** anything else, with the reason stated.

## 5. Checks (all reported, none relabels the primary result)

- **Date effects instead of week effects** (the rain study's specification).
- **Dose.** T_h in bands 25–28, 28–30, 30–32 and ≥ 32 °C against mild hours.
- **Negative control.** The metro, same model; expected near 0.
- **Thresholds.** Hot at ≥ 28 °C and at ≥ 32 °C.
- **Wet hours kept.** The model without the dry-hour restriction, with a rain indicator.
- **Level instead of gain.** Mean delay at the hour's passes.
- **Placebo (lag).** Heat two days later in the same hour instead of the current one; expected near 0 once week
  effects are in.

## 6. Power

Computed in a separate committed step before δ is estimated, from temperature only (the number of hot and mild dry
hours by date and week) and the rain study's measured dispersion (σ_e 36.7 s, σ_c 11.9 s, ρ 0.34, a median 46 tram
units per date × hour), with the simulation of `tools/rain/power.py` adapted to week effects. It states the minimum
detectable δ at 80 % power. If it is above 30 s, the study is reported as underpowered in advance and the primary label
can be at most inconclusive. If fewer than 10 dates hold a hot hour, the study is reported as not estimable.

## 7. Outputs

An article on bsandova.com in the form of the rain study: the hot–mild contrast for trams, buses and the metro, the
dose curve, the checks, and the hour-by-hour temperature series of the window, every figure interactive.

## 8. What this will not show

- **Why.** A hot hour bundles slower boarding, more open doors and air-conditioning faults, rail and overhead-line
  limits, and different ridership; δ is the sum.
- **Extremes.** The window has the 2025 summer only; a heatwave hotter than any in it is outside what is measured.
- **Comfort.** Delay is not the passenger's experience of heat on board.
- **Other years and cities.**

## References

To be verified (DOIs and pages) before publication, in a dated commit; none is cited in the analysis itself.

## Changes after registration

**8 October 2026 (power, §6; temperature read, no delay read against temperature).** `tools/heat/power.py`, output
`heat-delays-power.json`. On the 170 dates left by the rain study's screening (3 230 service hours, none without a
temperature), 58 dry hours reach 30 °C, on 11 dates in 7 weeks, against 1 341 mild dry hours. The study is estimable
(≥ 10 hot dates) but has fewer than 30, so the wild cluster bootstrap of §3 applies, and the evidence rests on 11 hot
days: this is stated now. Deviation: with week effects a shock common to a whole date is not absorbed, so its size was
measured from the rain study's tram units without any temperature (residuals on cell and week effects, averaged by
date): σ_day 5.2 s. With the rain study's σ_e 36.7 s, σ_c 11.9 s and ρ 0.34, the simulated SE of δ_tram is 3.3 s and
the minimum detectable δ 9.1 s (80 % power, two-sided 5 %); the 30 s rule passes, and "not supported" is reachable only
if the estimate lies near zero.
