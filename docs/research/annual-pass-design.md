# Does a cheaper annual pass fill the trams? Vienna 2012 and Prague 2015 — research design

**Status: pre-specified analysis, design committed 5 October 2026, before any ridership value was read by the author.**
The steps follow in dated commits: design → donor screening → code → data → results. Commit times are self-reported.
Deviations are listed, dated, under "Changes after registration". Work on this study began in October 2026.

## 0. What has already been seen

- **Feasibility check (5 October 2026).** A delegated read-only check listed, for each candidate city, the source of
  annual passenger counts, its years, format and known breaks, and the price history of the treated passes. It opened
  some files to confirm their year coverage; no ridership value, trend or ratio was reported to the author or written
  anywhere. Facts reported: the sources and years in §2, the price events in §1, and these breaks and risks: Vienna's
  split by mode changes method in 2012 (the total does not); Prague's counts are estimates from ticket sales and
  surveys; the PID network grew into Central Bohemia in 2016–2019; German statistics re-benchmark in census years;
  several Austrian regions introduced cheap annual passes (Vorarlberg 2014, Tirol 2017, KlimaTicket 2021, Salzburg
  2022); Germany's 9-euro ticket (June–August 2022) and Deutschlandticket (May 2023) were nationwide.
- **Prior expectation.** The author expects some rise in ridership after each price cut, smaller than the press
  accounts of the Vienna model suggest, and expects the estimate to be imprecise.

## 1. Question and estimands

- **Q (primary).** Did ridership on the city's public transport rise after its annual pass became cheaper, compared
  with what similar cities without such a cut would predict?
  - **Vienna:** 1 May 2012, annual pass (core zone) cut from 449 € to 365 € (−19 %).
  - **Prague:** 1 July 2015, annual coupon (Prague zones) cut from CZK 4 750 to CZK 3 650 (−23 %).
- **Estimand.** For each event, the average gap, in log points, between the treated city's log ridership index and
  its synthetic control over the post years: Vienna 2013–2016 (2012 is a part year), Prague 2016–2019 (2015 is a part
  year; 2020 onwards is COVID). Reported also as a percentage, exp(gap) − 1.
- **Berlin (descriptive, no label).** The indexed series of Berlin and of other German Länder around the 9-euro ticket
  and the Deutschlandticket, 2012–2025. Both measures were nationwide and coincide with the COVID recovery, so no
  comparison group exists and nothing causal is claimed.

## 2. Data

- **Outcome.** Annual passengers (journeys, as each operator or statistics office counts them) of the city's urban
  public transport, from the official source per city:
  - Vienna: Stadt Wien OGD "Wiener Linien – U-Bahn / Straßenbahn / Autobus" (MA 23), total of the three modes,
    2001–2024.
  - Prague: DPP annual reports, passengers by metro, tram and bus, city operator only (not the PID region),
    2005–2025.
  - Donor candidates: Plzeň (PMDP reports 2003–2025), Linz (Linz in Zahlen, Linz AG Linien 2003–2025), Graz (Holding
    Graz reports), Brno (DPMB reports), Ostrava (DPO reports 2012–2025), Berlin and Hamburg (statistics offices /
    Destatis 46181), Munich (SWM/MVG reports), Bratislava, Budapest and Warsaw (operator reports / GUS BDL), each
    only where an official annual series exists for the whole window.
- **Measure.** Because the cities count passengers differently, levels are not compared. Each series is
  log-transformed and indexed to its own mean over the pre-period, so the analysis compares changes.
- **Population** (for a per-resident check): national statistics offices, city population at 1 January.
- **First stage (descriptive).** Vienna: annual-pass holders ("Jahreskarten und Pkw seit 2002", data.gv.at), where
  available; Prague: annual coupons sold, if the DPP reports give them.

## 3. Donor screening (before any outcome is read)

A city enters the donor pool of an event only if, in that event's whole window (Vienna 2004–2016, Prague 2008–2019):

1. an official annual passenger series exists for every year, from one source, without a documented counting change;
2. its annual pass was not cut in price by 10 % or more, and no fare-free or flat-rate regional pass (KlimaTicket,
   365-euro regional tickets) was introduced for it;
3. its network was not merged or extended into a new area by a documented reorganisation.

Screening uses price histories, methodological notes and network histories only, and is committed, with the reasons
for every exclusion, before any passenger value is read (the "donor screening" commit). Vienna is never a donor for
Prague (treated), and Prague is not a donor for Vienna after 2014 (its window is cut to 2004–2014 if Prague is
needed; otherwise Prague is excluded). An event with fewer than four donors after screening is reported as not
estimable.

## 4. Estimation

- **Synthetic control** (Abadie, Diamond & Hainmueller 2010): non-negative donor weights summing to one, chosen to
  match the treated city's log index in every pre-period year; no other predictors. Software: a transparent
  implementation in Python (scipy quadratic programming), checked against a published worked example (the Basque or
  California tobacco data) before use.
- **Pre-fit rule.** If the root mean squared prediction error over the pre-period exceeds 0.05 log points, the fit is
  labelled poor and the event inconclusive whatever the estimate.
- **Inference.** Placebo in space: the same method is applied to every donor as if it were treated; the event's
  p-value is the rank of the treated city's post/pre RMSPE ratio among all units divided by their number. With J
  donors the smallest attainable p is 1/(J + 1), stated with every result.

## 5. Labels

- **Supported:** the average post gap is positive, the treated city has the largest post/pre RMSPE ratio of all units
  (p = 1/(J + 1)), and the pre-fit rule passes.
- **Not supported:** the pre-fit rule passes and the average post gap lies within ±5 % (|exp(gap) − 1| < 0.05).
- **Inconclusive:** anything else, with the reason stated.

Each event gets its own label; there is no pooled estimate.

## 6. Checks (all reported)

- Leave-one-donor-out: the gap re-estimated without each donor; the range.
- In-time placebo: a fake cut three years before the real one, with the post window shifted accordingly.
- Synthetic difference-in-differences (Arkhangelsky et al. 2021) on the same panel.
- Per-resident version (passengers per resident instead of passengers).
- Prague: the PID-region total instead of the city operator, as a sensitivity to network growth.

## 7. Power

No simulation before the data: the precision of synthetic control depends on the donors' pre-period dispersion,
which is not known before the outcomes are read. The minimum detectable gap is reported with the results as the
spread of the placebo gaps, and the article says so.

## 8. Outputs

A Research article in Prague, measured style: the treated and synthetic series for each event, the placebo
distribution, the price and first-stage facts, the Berlin descriptive panel, and a table of donors and weights.

## 9. What this will not show

- Why people ride: price, service, density and fuel prices move together; the estimate bundles everything that
  changed in the treated city and not in its synthetic twin.
- Who switched: no individual data; a rise in journeys can come from existing riders travelling more.
- Comparable levels across countries, because counting methods differ.
- Anything about Berlin's tickets beyond description.

## References

- [R1] Abadie, A., Diamond, A., Hainmueller, J. (2010). Synthetic control methods for comparative case studies.
  *Journal of the American Statistical Association* 105(490), 493–505. [verify DOI before publication]
- [R2] Arkhangelsky, D., Athey, S., Hirshberg, D. A., Imbens, G. W., Wager, S. (2021). Synthetic difference-in-
  differences. *American Economic Review* 111(12), 4088–4118. [verify DOI before publication]

## Changes after registration

None yet.
