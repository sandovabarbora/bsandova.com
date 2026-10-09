# Did the Eras Tour show up in Europe's prices? Accommodation and restaurant inflation, 2023–2025 — research design

**Status: analysis plan committed 2 October 2026, before this analysis was run; the author had worked with these
data since March 2026.** Registration is
self-timestamped, as for the other studies on bsandova.com. Deviations are listed, dated, under "Changes after
registration".

## 0. What has already been seen

- **Tour schedule.** The Wikipedia article *The Eras Tour* (revision 1376835990), collected for Pop, measured, was
  parsed for its 2024 show dates by country. Its Boxscore figures (50 attendance cells) were seen; no Taylor Swift result of Pop, measured has been computed.
- **Eurostat.** The author has worked with these data since March 2026; the plan fixes the analysis, not ignorance
  of the data.
- **Prior knowledge.** In June 2023 Swedish economists attributed part of May 2023's rise in Swedish hotel prices to
  Beyoncé's concerts in Stockholm; that episode is outside this design's window and not tested here.
- **Prior expectation.** The author expects accommodation prices to rise in a show month; no expectation for
  restaurants.

## 1. Questions

- **Q1 (accommodation).** In the month of its first Eras Tour show, did a country's year-on-year inflation in
  accommodation services rise, compared with countries without a show?
- **Q2 (restaurants and cafés).** The same for restaurants, cafés and similar (the prices residents pay most often
  of the two).
- **Q3 (all items).** The same for the headline index, to say whether anything reaches the basket as a whole.

## 2. Data

- **Prices.** Eurostat HICP, monthly index 2015 = 100 (`prc_hicp_midx`, unit I15), COICOP CP112 (accommodation
  services), CP111 (restaurants, cafés and the like) and CP00 (all items), for every EU and EEA country and
  Switzerland, January 2022 to December 2025, downloaded once; the response is hashed and published.
- **Outcome.** Year-on-year inflation in percent: 100 × (ln index − ln index twelve months earlier). This removes
  each country's own seasonal pattern, which is strong for accommodation.
- **Treatment.** The month of a country's first Eras Tour show in 2024: May (France, Sweden, Portugal, Spain), June
  (Ireland), July (the Netherlands, Switzerland, Italy, Germany), August (Poland). The United Kingdom has no HICP in
  Eurostat after 2020 and is not in the data.
- **Comparison countries.** Every other country in the data with a complete series. They may have hosted other
  tours; that is not modelled and is stated as a limit.
- **Austria.** Its three Vienna shows (8–10 August 2024) were cancelled on 7 August, after visitors had booked.
  Austria is left out of the estimation and reported separately (§5).
- **Window.** January 2023 to June 2025 for estimation (the outcome needs twelve earlier months, so the index runs
  from January 2022).

## 3. Estimation

- **Estimator.** Callaway and Sant'Anna's group-time effects for staggered adoption [R1], groups = the month of the
  first show; comparison units not-yet-treated and never-treated (primary), never-treated only (sensitivity). No
  covariates. Python `csdid`, the multiplier bootstrap clustered by country, 999 draws, fixed seed, uniform bands.
- **Event window.** Months −6 to +6 around the first show.
- **Primary estimate.** The effect in the show month (event month 0) for Q1. Shows last a few days, so month 0 is
  where an effect should be; months +1 to +2 are reported to see whether it persists.
- **Few clusters.** Ten treated countries are few for a clustered bootstrap. As a second inference, a permutation
  test: the treatment months are assigned at random to ten of the countries, 2 000 times, and the share of
  permutations with an event-month-0 effect at least as large in absolute value as the real one is reported.

## 4. Labels

For each question, on the event-month-0 effect:

- **supported** if its 95 % interval excludes zero, the pre-trend months −6 to −2 all have bands including zero, and
  the permutation p-value is below 0.05;
- **not supported** if its interval includes zero and lies within ±1 percentage point of year-on-year inflation;
- **inconclusive** otherwise, with the reason.

## 5. Checks

- **Pre-trends** as above.
- **Placebo year.** The same treatment months moved to 2023, when there was no Eras Tour in Europe, estimated on
  the same window.
- **Leave one out.** Dropping each treated country in turn, for Q1.
- **Austria (descriptive).** Austria's year-on-year accommodation inflation in August 2024 against the comparison
  countries' August 2024 values, placed as a percentile. Not tested.

## 6. What this will not show

- Prices in the host city: the HICP is national, so a city's effect is diluted by the rest of the country, and a
  null result does not mean the city saw no rise.
- Prices actually paid by visitors versus residents; the index mixes both.
- Other tours, festivals or sport events in the same months (Euro 2024 in Germany, June–July 2024, overlaps
  Germany's treatment month and is named in the article; the leave-one-out check shows Germany's weight).
- Welfare or spending.

## References

- [R1] Callaway, B., Sant'Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. *Journal of
  Econometrics* 225(2), 200–230. doi:10.1016/j.jeconom.2020.12.001
- [D1] Eurostat (2026). HICP, monthly data (index), `prc_hicp_midx`. Accessed on the collection date.
- Wikipedia contributors, *The Eras Tour*, revision 1376835990.

## Changes after registration

None yet.

**9 October 2026 (a correction to the 5 October rewording, after a model-based review after publication).** The
status line and §0 of this design were rewritten in place on 5 October 2026 (`c953c92`). The original wording, as
committed at `f5d702c` on 2 October 2026, was: "**Status: design committed 2 October 2026, before any price index
value was downloaded or read.**"; on Wikipedia, "Its Boxscore figures were seen only as structure (50 attendance
cells)"; and on Eurostat: "One request to the HICP monthly index (`prc_hicp_midx`, COICOP CP112, unit I15) for Sweden
and Austria, January–February 2023, was made to check the format; it returned four values, which were not printed or
read. A second request read only the dataset's latest month (December 2025) for Czechia, not its value." That
disclosure was replaced by "The author has worked with these data since March 2026"; the original stands as the
record of what was seen. The rewording covers the source (Eurostat's HICP), which the author had used since March
2026; the series analysed were downloaded on 2 October 2026 and committed at `dc9dba3`, after this plan by the
self-reported commit order. Design, code (`d1d25cd`), data (`dc9dba3`) and results (`4401fda`) were committed within
two minutes on the branch (tags `pop-eras-design` and `pop-eras-results`, created on 9 October 2026, so they do not
date the commits) and reach `main` in one squash commit, `942e304`, so the order is not independently timestamped.

**9 October 2026 (post hoc, not registered).** The article now gives pointwise 95 % intervals (estimate ± 1.96 ×
the stored standard error, `tools/eras/estimate.py --pointwise`, `eras-inflation-pointwise.json`) beside the
registered 95 % uniform bands, which the article had called "95 % CI". The labels are unchanged; they use the
uniform bands as registered. Limits now stated in the article: the identifying assumptions (parallel trends, no
anticipation, no spillover to comparison countries); the accommodation pre-trend at month −4 (the registered check
fails); France's months +2 and +3 fall in the Paris Olympic Games, and France had a second exposure in Lyon in its
month +1 (Décines-Charpieu, 2–3 June 2024); the United Kingdom, with 15 of the 48 European shows that have attendance figures in Pop, measured's tour file, has no HICP after 2020; three outcomes are
tested with no correction for multiplicity.
