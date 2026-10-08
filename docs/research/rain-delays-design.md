# Does rain delay Prague's trams? — research design

**Status: pre-specified analysis, design committed 6 October 2026, before any delay or precipitation value was read.**
The steps follow in dated commits: design → power (treatment only) → code → data → results. Commit times are
self-reported. Deviations are listed, dated, under "Changes after registration". Work on this study began in
October 2026; the delay data come from the author's master's thesis (2025).

## 0. What has already been seen

- **Feasibility check (6 October 2026).** A read-only check listed sources, years, fields and file schemas. No delay
  value and no precipitation value was printed, summarised or written anywhere. Facts found:
  - **Delays.** The thesis used Prague Integrated Transport (PID) vehicle positions from Golemio (Operátor ICT),
    15 March – 8 September 2025, 121 197 794 vehicle-location records (count from the thesis page). The thesis's raw
    and derived files were **not found on this machine**; the site's `texts/delayed` uses only five days of 5-minute
    aggregates (`tools/data/sonification_days.json`), which this study does not use. The fields of the raw records
    (delay, trip, route, stop, timestamp) are therefore not confirmed here; §2 fixes a rule for each case.
  - **Precipitation.** ČHMÚ open climatological data (CC BY 4.0), `opendata.chmi.cz/meteorology/climate`, hourly
    files per station and month (`historical/data/1hour/<year>/1h-<WSI>-<yyyymm>.json`, 2018–2025; `recent/` for
    2026), schema `STATION, ELEMENT, DT, VAL, FLAG, QUALITY`. Element **SRA1H** (hourly precipitation total) is
    present for four Prague stations: Ruzyně (0-20000-0-11518), Libuš (0-20000-0-11520), Kbely (0-20000-0-11567) and
    Klementinum (0-203-0-11514), with 12 monthly files each for 2025. Only the element list of one month per station
    was read, not its values.
  - **Breaks not yet screened.** Planned tram and bus closures (summer track works), timetable (GTFS) changes and
    feed outages in the window are not known yet; §3 screens them before any delay value is read.
- **Prior expectation.** The author expects rain hours to add some delay to buses and trams, more to buses (which share
  the road with cars) than to trams, and expects the tram estimate to be small and possibly within the margin.

## 1. Question and estimand

- **Q (primary).** In a clock hour with rain in Prague, do trams gain more delay than in a dry hour of the same route,
  hour of day and weekday, in the same week?
- **Unit.** A route-direction × clock hour (route r, direction, date d, hour h) of surface PID service in Prague:
  trams and city buses (regional buses, trolleybuses, ferries and the metro excluded; the metro is a negative control,
  §6).
- **Outcome Y (primary).** *Delay gained*: for each trip observed in the hour, its delay at its last position in the
  hour minus its delay at its first position in the hour, in seconds; Y is the mean over the trips of the unit. This
  measures delay *added* during the hour, so delay carried in from earlier hours (which the thesis found persistent)
  is not counted as an effect of the hour's rain.
- **Treatment (fixed now).** Hourly precipitation P is the mean SRA1H of the four stations for the hour (h:00–h:59,
  local time; ČHMÚ times converted from UTC).
  - **Rain hour:** P ≥ 0.5 mm.
  - **Dry hour:** all four stations report 0.0 mm in the hour and in the two hours before.
  - Hours in between (0 < P < 0.5 mm, or dry with rain in the two hours before) are left out of the primary contrast
    and enter only the dose check.
- **Estimand (primary).** δ_tram: the average difference in Y between rain hours and dry hours for trams, within route
  × direction × hour-of-day × weekday cells and within dates, in **seconds of delay gained per trip-hour**. δ_bus is
  estimated alongside and reported; it is secondary.

## 2. Data

- **Delays.** The thesis's vehicle positions, 15 March – 8 September 2025, if the author supplies them. Rules fixed
  now for what the records turn out to hold:
  1. A delay field and a trip identifier exist: Y as defined in §1.
  2. A delay field exists but no trip identifier: trips are rebuilt as runs of one vehicle on one route without a gap
     over 10 minutes; Y as in §1.
  3. No delay field: the study is **not estimable** from these data (no schedule matching is attempted).
  If the data are not available, the alternative is a new collection from Golemio's PID vehicle-positions API from the
  date of a dated change note, for at least 8 weeks; the window, the API terms and the collection script are
  committed before any value is read.
- **Precipitation.** ČHMÚ hourly SRA1H for the four stations (§0), same window.
- **Calendar.** Czech public holidays and school holidays (weekday definition), daylight-saving dates.

## 3. Screening (before any delay value is read)

Committed as `rain-delays-screen.md`, from PID announcements, GTFS feed versions and Golemio status notes only:

1. **Disruption days.** A route-direction × date is excluded if PID announced a closure, diversion or replacement
   service for it, from the announcement's first to last day.
2. **Feed gaps.** A date is excluded if the feed has no positions for more than 60 consecutive minutes between 05:00
   and 23:00 (counted from record timestamps only, without reading delays).
3. **Thin units.** A unit with fewer than 2 trips observed is dropped.

## 4. Estimation

- **Model.** Y_{r,d,h} = δ_m · Rain_{d,h} + α_{r × hour × weekday} + γ_d + ε, by OLS, separately for trams and buses
  (m), on rain and dry hours only. α absorbs the route's usual pattern by hour and weekday; γ_d absorbs anything common
  to a whole day (season, events, ridership level). δ is identified from rain and dry hours within the same day and
  from the same route-hour on different days. Units are weighted equally.
- **Why OLS.** Delay gained can be negative (a vehicle catches up), so a log or count model does not fit; seconds are
  the reported scale.
- **Inference.** Standard errors clustered by date (rain is common to the whole city within an hour and correlated
  across hours of a day). The window holds about 178 dates; the number of dates with at least one rain hour is stated
  with the result. If fewer than 30 dates have a rain hour, a wild cluster bootstrap by date (999 draws, Rademacher)
  replaces the analytic interval [R4].

## 5. Labels (δ_tram; the same rules give δ_bus its own label)

- **Supported:** the 95 % interval of δ lies wholly above 0.
- **Not supported:** the 90 % interval of δ lies wholly within ±10 s (two one-sided tests, [R5]). The margin is fixed
  now: 10 s of delay gained per trip-hour is below a delay a passenger would notice.
- **Inconclusive:** anything else, with the reason stated.

## 6. Checks (all reported, none relabels the primary result)

- **Placebo (lead).** Rain in the *next* hour instead of the current one; expected near 0.
- **Lags.** Rain one and two hours earlier, alongside the current hour.
- **Dose.** P in bands 0.1–0.5, 0.5–2, 2–5 and ≥ 5 mm against dry hours.
- **Station choice.** Each route-hour assigned to its nearest station (by route centroid) instead of the four-station
  mean.
- **Negative control.** The metro, underground and on its own track, with the same model; expected near 0 apart
  from crowding.
- **Level instead of gain.** Mean delay at the hour's positions instead of delay gained.
- **Disruption days kept.** The model with the §3 exclusions undone.

## 7. Power

Power is computed in a separate committed step before any delay value is read. That step reads precipitation only
(the number of rain and dry hours by date in the window) and simulates δ_tram's standard error from the delay
dispersion reported in the thesis; it states the minimum detectable δ at 80 % power. If the minimum detectable δ is
above 30 s, the study is reported as underpowered in advance and the primary label can be at most inconclusive.

## 8. Outputs

A Research article: the rain and dry contrast for trams and buses, the dose curve, the placebo and the metro control,
a map of routes by estimated δ (descriptive), and the hour-by-hour precipitation series of the window.

## 9. What this will not show

- **Why.** A rain hour bundles more passengers boarding slowly, more car traffic, lower driving speeds and wet rails;
  δ is the total of all of them, not the effect of water on a tram.
- **Winter.** The window has no snow or frost; nothing is said about winter weather.
- **Other years.** One season, 2025; network and timetable change across years.
- **Individual trips.** δ is an average; it does not say how late a given tram will be.

## References

- [R1] Koetse, M. J., Rietveld, P. (2009). The impact of climate change and weather on transport: an overview of
  empirical findings. *Transportation Research Part D* 14(3), 205–221. https://doi.org/10.1016/j.trd.2008.12.004
- [R2] Tsapakis, I., Cheng, T., Bolbol, A. (2013). Impact of weather conditions on macroscopic urban travel times.
  *Journal of Transport Geography* 28, 204–211. https://doi.org/10.1016/j.jtrangeo.2012.11.003
- [R3] Arana, P., Cabezudo, S., Peñalba, M. (2014). Influence of weather conditions on transit ridership: a
  statistical study using data from smartcards. *Transportation Research Part A* 59, 1–12. https://doi.org/10.1016/j.tra.2013.10.019
- [R4] Cameron, A. C., Gelbach, J. B., Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered
  errors. *Review of Economics and Statistics* 90(3), 414–427. https://doi.org/10.1162/rest.90.3.414
- [R5] Lakens, D. (2017). Equivalence tests: a practical primer for t tests, correlations, and meta-analyses. *Social
  Psychological and Personality Science* 8(4), 355–362. https://doi.org/10.1177/1948550617697177

## Changes after registration

**6 October 2026 (author's decisions, before any delay or precipitation value was read).** The thesis's raw vehicle
positions are on the author's other computer and will be copied to `tools/data/rain/` (not committed); §2 rule 1–3
applies to them as written. The ±10 s equivalence margin of §5 is confirmed. δ_tram is the only primary estimand;
δ_bus is secondary, reported with its own label and no multiple-testing correction, because it carries no primary
claim.

**6 October 2026 (power, §7; precipitation read, no delay value).** `tools/rain/power.py`, output
`rain-delays-power.json`. In 15 March – 8 September 2025 (178 dates, 3 382 service hours 05:00–23:59) the four
stations give 123 rain hours on 48 dates, 2 753 dry hours and 506 hours in neither class; no station-hour is missing.
With 48 rain dates the analytic date-clustered interval applies (§4). ČHMÚ stamps each hourly total at the end of its
hour in UTC, and the script reads it that way. Deviation: the thesis page reports no delay dispersion in seconds, so
the simulation uses a grid of structure-only assumptions (unit noise σ_e 60–180 s over 50 tram route-directions; a
city-wide date × hour shock σ_c 10–30 s with within-date autocorrelation ρ 0–0.8). The minimum detectable δ_tram
(80 % power, two-sided 5 %) is 4–15 s across the grid, so the 30 s rule passes in every scenario. The same grid puts
the standard error at 1.5–5.5 s, so the "not supported" label (90 % interval within ±10 s) is reachable only in the
lower-noise scenarios; this is stated now, before any delay value is read. The grid is re-run with the dispersion the
thesis data imply (route-hour spread of delay gained, read without the rain indicator) once the files arrive, as a
dated note before the estimation.

**8 October 2026 (screening, rule 1; no delay value read).** `rain-delays-screen.md`, code `tools/rain/screen_pid.py`.
pid.cz deletes finished change pages, so the announcements come from the Internet Archive (2 234 archived change
pages and 8 list snapshots in the window); 125 of the 173 closures the snapshots list have an archived page, and the
other 48 enter from the snapshots. Historical GTFS versions were not used: the archives that hold them need an API
key. Two clarifications of §3 rule 1, fixed before any delay value is read: (a) only planned closures (*výluka*)
exclude, not incidents (*mimořádnost*), because rain can cause incidents; (b) a closure in force on every day of the
window is the line's regular pattern and does not exclude (author's decision; three tram closures and the Pankrác C
replacement on line 19). The literal reading is added to §6 as a check. Rule 1 excludes 1 320 tram and 4 076 city bus
line-days (literal reading: 2 832 and 7 287). Rules 2 and 3 follow when the thesis files arrive.
