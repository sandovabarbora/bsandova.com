# Where could the causes be found? Follow-up designs from the October 2026 review

**Status: planning note, 9 October 2026.** An independent review of every published article (five model-based
reviewers, read-only, 9 October 2026) flagged sentences that read an association as a cause, and proposed for each a
design that could identify the cause from data that exist. This note collects those proposals, ranked by how feasible
they are with data already on disk. None has been run; each would be registered on its own before any outcome is read,
as the other studies on the site are.

Feasibility: **yes** = data on disk or public and cheap; **maybe** = data public but must be collected, or power is
doubtful; **no** = the data do not exist.

## Ready now (data on disk)

| # | Question | Design | Identifying assumption | Main threat | Data |
|---|---|---|---|---|---|
| 1 | Does rain itself slow trams? (*Weather on the rails* 1) | Event study around rain onset (first rain hour after ≥ 3 dry hours, hours −3 to +3), route × hour × weekday and date effects, hourly temperature, the metro as a non-street control within date × hour | Onset timing within a day is as good as random given hour and temperature; the metro shares the ridership shock but not the street | Riders move ahead of forecast rain (pre-trends); storms cluster on hot afternoons | Thesis DuckDB, ČHMÚ hourly precipitation and 10-min temperature |
| 2 | Do shorter stops in rain mean fewer passengers? (*Weather on the rails* 3) | Within-pass restriction to trams running on time or early, with the registered delay-held control | Among on-time trams, dwell changes only through boarding | Timing-point holds make dwell mechanical; conditioning on delay selects on an outcome of rain | Thesis DuckDB |
| 3 | Does evening darkness raise pedestrian crashes? (*When the clocks go back*) | Within-date dose–response across regions (dusk differs by about 21 minutes from west to east on each post-change date), region × year effects; leave-one-autumn-out | Region × year effects absorb other regional differences | Regions differ in urbanity and exposure by longitude; low power | `cells.parquet` (dark already computed) |
| 4 | Do councillors dissent less because their club joins the coalition? (*Prague, measured* 1) | Event study of the same councillors around dated coalition changes (2018, 2022 handovers, mid-term splits); councillors whose club status did not change as controls | Parallel dissent trends absent the change | The agenda changes at the same moment | Roll calls and stayer subset |
| 5 | Does moving to a stronger league change a player's output? (*Player Pool Atlas*, football) | Event study of goals plus assists per 90 around a move, mover fixed effects | No time-varying shock at the move | Players move after good seasons (an Ashenfelter dip) | Atlas repo (2 125 movers) |
| 6 | Did Harry Styles's first shows raise his local streaming share? (*Does a concert move the charts?*) | Daily event study around show dates, using postponements, cancellations and second dates as timing shocks; not-visited same-language neighbours as controls | Parallel trends at day level; no other country-specific promotion on show days | Promotion bundled with the show (identifies the show bundle, not the performance) | Kaggle daily charts |
| 7 | Does a wiki surface cross-document tensions that plain retrieval misses? (*A wiki that an agent keeps*) | — | — | — | No (private vault) |

## Needs collection or more power (maybe)

| # | Question | Design | Assumption | Threat |
|---|---|---|---|---|
| 8 | Does film-fund money get films released? (*film-fund*) | Fuzzy regression discontinuity: "funded within k years" instrumented by "above the cut-off at first application"; add 2022+ calls and 2014–15 PDFs for power | Monotonicity; the first-call score affects release only through funding | Reapplicants are rescored; shorter outcome window |
| 9 | Do two lines meeting at a stop share delay because they share track? (*Running late* 3) | Triple difference: mixed-traffic vs reserved-track segments, heat or rain as the shock, metro as a second control | Heat and rain affect both segment types alike except through traffic | Reserved-track routes sit in different parts of the city; a segregated-track flag must be built from GTFS/OSM |
| 10 | Is ANO's housing-estate vote about the metro? (*Prague, measured* 2) | Difference-in-differences around station openings (line A extension 2015) with matched distant precincts, 2017–2025 | Parallel trends | Stations open where the city is already changing; few openings |
| 11 | Does a mayor's party joining City Hall bring grants? (*Prague, measured* 3) | Regression discontinuity on close district council-majority outcomes in 2018 and 2022 | Margins as good as random near the threshold | Few close cases among 22 large districts |
| 12 | Does the Prague procedure delay completion? (*Prague, measured* 4) | Unit-level permit-to-completion (permits linked to RÚIAN house numbers), Prague vs Brno, Plzeň, Ostrava, controlling project size and phasing | Conditional comparability | Selection into finishing; linking is hard |
| 13 | Does a permit tariff ration car size? (*Prague, measured* 5) | Event study around the 2023 zone tariffs, flat-permit or unzoned districts as controls, dated vehicle-register data | Tariff timing unrelated to fleet trends | Slow fleet turnover |
| 14 | Did the Treaty of Aachen bring France and Germany closer? (*thesis-eu*) | Difference-in-differences of pair agreement against other large-state pairs (Italy–Spain, Italy–Poland, Spain–Poland), 2014–2021 | Parallel pre-trends | Brexit and the 2019 Parliament renewal affect pairs differently |
| 15 | Does diaspora size raise televotes? (*Eurovision*) | Staggered opening of labour markets after the 2004 and 2007 enlargements; televote-minus-jury gap | Timing exogenous to taste | The jury/televote split exists only for 2016–2025 |
| 16 | Does language keep a song in the chart? (*Pop, measured*) | Song × country panel with song and country effects, all 164 global number ones across 75 charts; event study around local-language re-releases or features | Language match unrelated to song × country promotion and diaspora | Promotion, tours, diaspora; chart start dates |
| 17 | Did cheap annual passes fill trams? (*annual-pass*) | Synthetic control around Vienna 2012 and Prague 2015 | Parallel trends | Too few clean series; operator monthly data would be needed |

## Not identifiable with existing data (no)

- Whether a live delay feed saves travellers money (*thesis*): needs departure-time choice data.
- Whether readers notice large errors more than small ones (*Quaesitor*): needs a reader study.
- Whether housing type itself shapes votes (*Prague, measured* 2): ecological data only; needs movers.

## Cheap experiments for the tools (AI and data)

- **Quaesitor documentation effect:** interleaved A/B per question and repeat in one session, pre-specified, paired
  exact test (harness on disk; a few dollars).
- **sitewitness rules:** a labelled adversarial set (injected unsupported numbers, fabricated quotes, bogus sources)
  with rules on and off; catch rate and false-refusal rate with intervals.
- **quotecheck accuracy:** synthetic splice and negation-drop mutations of a public-domain text; recall and false-pass
  rate.
- **cutover attribution:** remove the rounding on the legacy side and show zero mismatches; save the re-runs.

## Suggested order

1, 3 and 4 are the strongest next registered studies: the data are on disk, the designs are standard, and each would
turn an association already published into a tested causal claim or a clear null. 2 and 6 follow. Of the tool
experiments, the sitewitness adversarial set is the cheapest and most useful.

## Changes after this note

**9 October 2026, follow-up 1 (rain onset) not run.** A design was drafted and reviewed before registration. The review
showed that a credible version needs a stricter onset (rain at ≥ 2 of 4 stations after ≥ 6 dry hours), a reference
period before the hour in which Part 1's placebo failed, and an equivalence test of the pre-trend. Counted from
precipitation alone (no delay read), the season holds only 17 such onsets on 17 dates (23 with a 3-hour run-up,
7–10 under the looser mean-based rule). With so few events the minimum detectable effect would exceed the expected
4–10 s, "not supported" would be unreachable and the pre-trend test powerless, so the study could only end
inconclusive. It is not run. It becomes feasible with several seasons of stop passes, or with minute-level radar to
date the rain's arrival per route.

**9 October 2026, follow-ups 3 and 4 not run.** *Darkness by region (3):* from totals already published (about 410
evening pedestrian crashes in the two weeks after the change, over ten autumns), a regional dose design has far too
little variation: regions differ by a few minutes of dusk (about 21 minutes from west to east at the extreme). If the
whole 75 % evening rise were due to the hour of darkness, the effect would be about 0.9 % per minute; the minimum
detectable slope with these counts is about 2.4 times that, before region × year effects reduce power further, and the
original study's darkness-dose estimate (H3) was already inconclusive. *Council coalitions (4):* an event study of the
same councillors around coalition changes would largely repeat Part 1 of *Prague, measured*, which already measures
within-councillor change against the change in opposition share. Neither is run. None of the three follow-ups recommended first (1, 3, 4) can give an informative answer with the data
on disk; the others in the table have not been checked for power yet, and the associations already published stay
described as associations.
