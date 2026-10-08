# Necessary and optional cycling in Prague's weather — research design

**Status: pre-specified analysis, design committed 8 October 2026, before any cycle count was read.** The steps follow in
dated commits: design → data and screening → power → code → results. Commit times are self-reported. Deviations are
listed, dated, in the change log.

## 0. What has already been seen

- **Counts.** Only the list of Golemio's 40 bicycle counters and the names of their directions was read
  (`/v2/bicyclecounters`); one detections request for a counter id returned no rows, because the endpoint takes
  direction ids. No count was printed, summarised or written. The pedestrian endpoint (`/v2/pedestrians`) is not open
  to a free key (HTTP 403), so this study is about cycling; the open counter list carries no pedestrian channel.
- **Weather.** ČHMÚ hourly precipitation for March–September 2025 and ten-minute air temperature for May–September 2025
  were read for the rain and heat studies (`rain-delays-design.md`, `heat-delays-design.md`). Weather was never read
  together with any cycle count.
- **Prior expectation.** The author expects leisure cycling to fall more in rain and rise more in warmth than commuting,
  as Gehl predicts for walking, with a large difference.

## 1. Theory and question

Jan Gehl divides outdoor activities into *necessary* ones, which take place in nearly any conditions because people
have to do them (going to work or school), and *optional* ones, which take place only when conditions are favourable,
weather among them (*Life Between Buildings*, 2011 edition, pp. 9–11; *Cities for People*, 2010, pp. 20–21). He states
it for walking and staying. This study transfers it to cycling, which has the same split between the commute and the
ride for its own sake, and says so wherever the result is reported.

- **Q (primary).** In Prague, does rain reduce cycling proportionally more in optional hours than in necessary hours?
- **Necessary hours:** Monday to Friday, 06:00–08:59 Prague time, excluding Czech public holidays.
- **Optional hours:** Saturdays, Sundays and Czech public holidays, 10:00–17:59.
- All other hours are left out of the primary contrast.
- **Unit and outcome.** A counter direction × clock hour; outcome = the number of cyclists recorded in the hour.
- **Rain hour / dry hour:** as in the rain study (four-station mean `SRA1H` ≥ 0.5 mm; dry = all four stations 0.0 mm in
  the hour and the two before); other hours are left out of the primary contrast.
- **Estimand (primary).** ρ = (rain/dry ratio of counts in optional hours) ÷ (rain/dry ratio in necessary hours), from
  the model of §4. Gehl's prediction is ρ < 1: rain cuts optional cycling by a larger share.

## 2. Data

- **Counts.** Golemio bicycle counters (Technická správa komunikací hl. m. Prahy; Camea and Eco-Counter devices),
  `/v2/bicyclecounters/detections` per direction, 1 January 2019 – 30 September 2026, summed to clock hours.
- **Weather.** ČHMÚ open climate data, the four stations of the rain study: hourly `SRA1H`, ten-minute air temperature
  `T` (hourly mean, a station counting with at least four of six values) and hourly sunshine `SSV1H`, same period;
  CC BY 4.0.
- **Calendar.** Czech public holidays from the law on public holidays (Act No. 245/2000 Coll., as amended); daylight
  saving dates.

## 3. Screening (before any count is joined to weather)

Fixed now, applied from the counts alone and committed as `cycling-weather-screen.json`:

1. **Dead days.** A direction × date is excluded if its daily total is zero, or below 10 % of the median daily total of
   the same direction on the same weekday in the same calendar month across all years.
2. **Gaps.** A direction × date is excluded if any of its 24 hours has no record.
3. **Short series.** A direction with fewer than 365 remaining days is dropped.
4. **Pandemic.** 2020-03-12 to 2021-05-31 is kept in the primary model; leaving it out is a check (§6).

## 4. Estimation

- **Model.** Poisson pseudo-maximum likelihood on hourly counts, rain and dry hours in necessary and optional hours:
  count ~ rain + rain × optional | direction × hour × day type + direction × ISO week-of-year × year,
  where day type is necessary/optional. The interaction's exponent is ρ. Standard errors clustered by date.
- **Why PPML.** Counts with zeros; the ratio scale makes a commuter route and a leisure path comparable.

## 5. Labels

- **Supported:** the 95 % interval of ρ lies wholly below 1.
- **Not supported:** the 90 % interval of ρ lies wholly within 0.90–1.10 (two one-sided tests): the two kinds of hour
  respond to rain alike within 10 %.
- **Inconclusive:** anything else, with the reason stated.

## 6. Secondary questions and checks (reported, none relabels the primary result)

- **Temperature (secondary, own label by the same rule on the ratio per 5 °C).** Among dry hours at 0–25 °C, the
  ratio of the count change per 5 °C in optional hours to that in necessary hours; Gehl predicts > 1.
- **Sunshine.** Dry hours with full sunshine (`SSV1H` ≥ 50 min) against none, same contrast.
- **Without the pandemic** (2020-03-12 to 2021-05-31 dropped).
- **Dose.** Rain in bands 0.5–2, 2–5, ≥ 5 mm.
- **Evening.** Weekday 17:00–18:59 as a second "necessary" window (the commute home, partly optional).
- **Leisure routes against street routes.** Counters on riverside paths and greenways (by the route label in the
  counter list, classified now from names alone in `cycling-weather-screen.json`) against counters on streets.
- **One counter out.** The primary model leaving out each direction in turn.

## 7. Power

Computed after screening and before the estimate, from weather only (rain and dry hours by day type and year) and an
assumed overdispersion, in a separate committed step. If the minimum detectable ρ is above 0.80 or below 1/0.80 on the
ratio scale, the study is reported as underpowered in advance.

## 8. Outputs

An article on bsandova.com: the rain and temperature responses of necessary and optional cycling, by counter, with
every figure interactive, and the transfer from Gehl's walking to cycling stated in the title area.

## 9. What this will not show

- **Walking.** Gehl's claim is about pedestrians; this is its transfer to cycling.
- **Who rides.** A counter sees passes, not people or purposes; "necessary" and "optional" are defined by the clock.
- **Why.** Weather changes trip choices, routes and modes at once; the estimate is their sum on these routes.
- **Places without counters.**

## References

Gehl, J. (2011). *Life Between Buildings: Using Public Space*. Island Press. Gehl, J. (2010). *Cities for People*.
Island Press. Further references are verified before publication, in a dated commit.
