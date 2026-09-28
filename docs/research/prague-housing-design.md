# Prague builds two homes for Vienna's three: research design (Part 4, extended)

**Status: draft for review.** Version 1, not yet registered. To be sent to three referees (housing economics,
econometrics of few-unit comparisons, official housing statistics) and revised before registration. At the time of
writing, the raw files listed in Appendix A had been downloaded; only their structure (sheet names, row and column
labels, territorial and time coverage, and missingness of one field) had been inspected, apart from the values listed
in §0. No model below has been estimated. Deviations will be listed, dated, in "Changes after registration".

## 0. What has already been seen

**Part 4 (published, `texts/prague-housing.html`, `assets/praha/cities.json`).** Dwellings completed per 1 000
residents, 2012–2024, each city counted by its own office:

- **Prague** (ČSÚ, including extensions and conversions): 3.09 (2013) to 4.91 (2022); 6 489 dwellings in 2024
  (first release 6 511); 2015–2024 mean 4.5; never above 4.91 in the window. Every annual value 2012–2024 is in
  `cities.json`.
- **Vienna** (Statistik Austria, new buildings only): peak 8.5 (2021, 16 262 dwellings), 5.4 in 2024; 6.2 in 2024
  with extensions and conversions; 2015–2024 mean 6.6.
- **Warsaw** (Statistics Poland, BDL): peak 13.2 (2018, 23 430); 2015–2024 mean 10.4; own-computed rate matches the
  office's published 11.50 (2016) and 11.56 (2017). Every annual completion count, and the municipal and TBS counts,
  2012–2024 are in `cities.json`.
- **Builders, 2024.** Vienna: limited-profit associations 3 107 of 12 478 (24.9 %), public sector 2.4 %, private
  persons 6.8 %, the rest companies. Warsaw: municipal 96, TBS 0; 0.7 % of 14 873.

**Rows of the Part 4 Prague file** (`byt_vystavba.xlsx`, 1994–2025) other than completions and completions per
1 000 in 2012–2024 were read by `cities.py` into memory but not extracted or published. Whether any of them (starts,
dwellings under construction, 1994–2011, 2025) were viewed during Part 4 cannot be ruled out. They are treated as
**possibly seen**. This affects H2 (§2), whose inputs are starts and completions: the Prague–rest contrast that H2
tests was never computed, but the Prague annual series may have been glanced at.

**Seen in Part 2 (`prague-rings-design.md`, §0 and changes).** From RÚIAN building points: 33 300 flats (4.5 % of
Prague's flats) completed after 26 March 2021, 3.74 % standing at the October 2025 election; 88 of 1 120 precincts
have more than 10 % of their flats completed after the census. The metro-distance measure exists per precinct. No
association between completions and metro distance was computed in Part 2.

**Seen while preparing this draft (structure inspection and web searches).** Listed so that nothing is hidden:

- Austrian national totals of completed dwellings for 2022–2024 (printed by accident when reading the sheet layout
  of `Whg11-24_Bdl_150925.ods`; not Vienna).
- ČSÚ price index of flats (base 2010 = 100), 2015 Q1 – 2016 Q1, for Czechia, Czechia without Prague and the first
  nine kraje, Prague included (first rows of `icncr.xlsx`). Prices are the regressor of H3, not its outcome.
- ČSÚ average purchase price of flats in Prague, 103 693 CZK/m² (2023) and 115 889 CZK/m² (2024), from search-result
  snippets of ČSÚ regional releases.
- Single cells printed in the first line of the ČSÚ open-data CSVs: Czechia, January 2005, 8 713 building permits;
  Czechia 1990, 61 004 dwellings started; Prague, January 2006, 526 dwellings started; Prague, January 2026, 860
  started and 640 completed; Prague, Q1 2026, 419 building permits; Czechia, Q1 2026, 14 290 permits and 9 681
  dwellings started; Czechia, January 2026, 2 308 completed.
- OeNB release (search snippet): Vienna residential property prices +2.9 % in 2025.
- RÚIAN building points (Part 2 extract, which covers every statutory city with city districts, not only Prague):
  225 768 buildings with flats; `dokonceni` missing for 3.5 % of buildings and 1.8 % of flats; dates run to
  23 September 2026. No count by year or area was computed.
- World Bank, Doing Business 2020: Czechia 157th of 190 on "dealing with construction permits", 246 days for the
  standard warehouse case.

No other value of any outcome series in Appendix A has been looked at.

## 1. Research questions and estimands

Part 4 showed volume: three cities, three offices, three definitions. Three cities identify nothing beyond that
description. Every question below therefore moves the unit of inference to a panel in which Prague (and, where the
data allow, Vienna and Warsaw) is one member among many, and asks something the three-city chart cannot answer.

The questions follow the housing-supply literature. Where regulation or slow permitting binds, new supply responds
little to demand, and prices rather than quantities absorb demand shocks (Glaeser, Gyourko and Saks 2005; Glaeser and
Gyourko 2018; Gyourko and Molloy 2015). Supply responsiveness is measured as the reaction of construction flows to
price changes (Topel and Rosen 1988; Mayer and Somerville 2000), varies across places with land and regulation (Green,
Malpezzi and Mayo 2005; Saiz 2010; Hilber and Vermeulen 2016), and is low in several continental European countries
(Caldera and Johansson 2013). Prague's permitting is slow by international standards: Czechia ranked 157th of 190 on
construction permits in Doing Business 2020, and a new building act (Act No. 283/2021 Coll.) was brought into force
in 2024 to shorten procedures [verify: 1 January 2024 for reserved structures and 1 July 2024 in general]. Vienna's
limited-profit housing associations, regulated by the Wohnungsgemeinnützigkeitsgesetz (WGG, 1979), are often described
as a stabilising, less cyclical source of supply (Kemeny 1995; Kadi 2015; Friesenecker and Kazepov 2021) [verify:
the counter-cyclicality claim needs a primary source, e.g. IIBW reports by Amann and Mundt].

- **RQ1 (benchmark).** Is Prague's recent construction low for a European metropolitan region with its demand?
  - **Estimand.** Prague's residual in a cross-regional model: the log of dwellings built 2011–2021 per resident
    (harmonised 2021 census) minus its prediction from predetermined demand variables. The prediction model is fitted
    on the other European metropolitan regions. This is a benchmark against peers, not a causal effect of any Czech
    institution.
- **RQ2 (the pipeline).** Once a Prague dwelling is started, does it take longer to complete than elsewhere in Czechia?
  - **Estimand.** The mean lag, in months, between starts and completions of dwellings in new multi-dwelling
    buildings, Prague minus the rest of Czechia pooled. It is a property of the aggregate flow (a distributed-lag mean),
    not of individual projects, which are not observed.
- **RQ3 (responsiveness).** Do Prague's housing starts respond less to price growth than starts in the rest of
  Czechia?
  - **Estimand.** The semi-elasticity of multi-dwelling starts with respect to lagged annual log price growth of flats,
    Prague minus the rest, within a kraj–quarter panel with kraj and quarter effects. This is the reduced-form
    responsiveness of the flow (Mayer–Somerville), not a structural supply elasticity: price growth is itself moved by
    supply shocks, and no instrument is claimed.
- **RQ4 (who builds).** Is construction by non-market builders (municipal, public building societies, cooperatives,
  social rental) less responsive to local price growth than construction for sale or rent by developers?
  - **Estimand.** Difference in the price semi-elasticity of starts between non-market and market builders, within
    Poland's 380 powiats, 2012–2024. Poland is the only one of the three countries with an annual, local, by-builder
    series of starts and a local price series. It is used as the laboratory for a claim made about Vienna. Austria
    publishes builder splits only for single recent years, so Vienna enters descriptively (§3).
- **RQ5 (where Prague builds).** Within Prague, is new construction denser near metro stations, holding distance from
  the centre equal?
  - **Estimand.** The coefficient on log₂ distance to the nearest metro station in a Poisson model of flats completed
    2012–2024 per km², across 1 km census grid cells, conditional on log₂ distance from Můstek and on the pre-2012
    flat density. The coefficient is a controlled association. Accessibility capitalises into land values, so an
    unconstrained market should build more densely where access is best (Alonso–Muth; Baum-Snow and Han 2024 on
    where supply responds). A zero or positive coefficient would point to constraints (heritage protection, zoning,
    brownfield availability) steering construction away from the metro.

## 2. Hypotheses, tests and decision rules

**One p-value per hypothesis; Holm step-down at family-wise α = 0.05 over H1–H5.** H1a, H3a and H4a are manipulation
checks outside the family. H6 is a set of replications reported without tests. Every hypothesis is reported whichever
way it falls; "not supported" and "underpowered" are written as such.

- **H1a (manipulation check).** In the benchmark model, lagged population growth has a positive coefficient.
- **H1 (Prague builds less than its peers predict).** Let R_P be Prague's leave-one-out residual (log scale) and
  R_j those of the n other metropolitan regions, each from the model fitted without that region (jackknife+; Barber
  et al. 2021).
  - Test: H0: Prague is exchangeable with the other regions; H1: R_P lies in the lower tail. One-sided conformal
    p = (1 + #{j: R_j ≤ R_P}) / (n + 1).
  - The smallest attainable p is 1/(n + 1), so H1 can pass the first Holm step (0.01) only if n ≥ 99. The metro
    sample is expected to have well over 200 regions (§3) [verify at the design stage].
  - Decision: *supported* if p passes its Holm threshold.
- **H2 (Prague's pipeline is slower).** μ_P − μ_R > 0, where μ is the mean start-to-completion lag of dwellings in
  new multi-dwelling buildings (§5).
  - Test: one-sided, with the standard error from a moving-block bootstrap over months (block 24 months, B = 9 999)
    that re-estimates both lag distributions in each draw.
  - Decision: *supported* if p passes its Holm threshold. The contrast is also reported in months with its 90 %
    interval.
- **H3a (manipulation check).** In the rest of Czechia, starts rise with lagged price growth (β_R > 0).
- **H3 (Prague responds less).** β_P − β_R < 0 in the kraj–quarter model (§5).
  - Test: one-sided, with Driscoll–Kraay standard errors (4 lags). Prague is a single unit, so clustering by kraj
    cannot deliver valid inference for its interaction (Conley and Taber 2011; MacKinnon and Webb 2018). The
    identifying variation is Prague's own time series, and the reference is t(T − 1).
  - Decision: *supported* if p passes its Holm threshold.
- **H4a (manipulation check).** Market (for sale or rent) starts rise with lagged local price growth.
- **H4 (non-market builders are less responsive).** β_NM − β_M < 0 in the stacked powiat model (§5).
  - Test: one-sided Wald test, standard errors clustered by powiat (380 clusters); two-way clustering by powiat and
    year as the second method. The larger of the two standard errors is used.
  - Decision: *supported* if p passes its Holm threshold.
- **H5 (Prague builds densely near the metro).** γ < 0: new-flat density falls with log₂ metro distance, holding
  centre distance and existing density equal.
  - Test: one-sided. The standard error is the largest among Conley (1.5 km, Bartlett) and a wild cluster bootstrap
    by city district (Webb weights, B = 9 999), as in Part 2.
  - Decision: *supported* if p passes its Holm threshold. A *significantly positive* γ, from the one-sided test in
    the other direction at 5 %, is reported as "construction avoids the metro". If neither test rejects, the result
    is "indeterminate".
- **H6 (replications, no test).**
  - H1 with the core NUTS 3 region (the city alone) in place of the metropolitan region, and within Czechia only
    (14 NUTS 3 regions, where the smallest attainable p is 1/15). Vienna's and Warsaw's residuals are reported in
    both.
  - H2 against the gmina-level average construction period of multi-family buildings in Poland (Warsaw against the
    other cities with powiat status) and Vienna's 2024 construction time by builder (Statistik Austria). Both are
    placed next to Prague's μ, with the definitions stated.
  - H3 with Warsaw against the other Polish powiats (annual), and with Vienna's permits against those of the rest of
    Austria (quarterly, OeNB price indices).
  - H5 on flats completed 2000–2011, before the window.

## 3. Data and measures

URLs are in `tools/praha/housing_fetch.py`, which downloads every raw file and writes their SHA-256 list (Appendix A).

**Harmonised benchmark (RQ1).** Eurostat, Census 2021:

- Conventional dwellings by period of construction and NUTS 3 region (`cens_21dwop_r3`): categories 2011–2015 and
  2016 and after. Numerator: dwellings in buildings constructed 2011 or later, all occupancy states.
- The unknown-period share (`UNK`) is a coverage filter: regions above 10 % are dropped. Whether a country's census
  records period of construction *or reconstruction* (the Czech census has used "period of construction or reconstruction" [verify for 2011 and 2021]) is checked from
  the national census metadata before estimation. Countries that count reconstruction are flagged and dropped in a
  robustness check.
- Reference dates differ (Czechia 26 March 2021, Poland 31 March 2021, Austria 31 October 2021 [verify each]). The
  outcome is annualised: dwellings built since 1 January 2011 / years to the census date / population on
  1 January 2011 × 1 000.
- Predictors, all dated 2011 or earlier: log population change 2001–2011 and log population 2011
  (`demo_r_pjanaggr3`), log GDP per head in PPS 2011 (`nama_10r_3gdp`), and a capital-region indicator. Both
  population series are in NUTS 2021 codes. Regions without back-cast data are dropped, and the count is reported.
- **Unit: Eurostat metropolitan regions** (aggregates of NUTS 3, NUTS 2021 version) [verify: typology file URL and
  that the Prague metro region is CZ010 + CZ020]. Housing markets are metropolitan: Prague's suburbs are in
  Středočeský kraj, Vienna's in Lower Austria, Warsaw's in the surrounding subregions. NUTS 3 sizes also differ by
  orders of magnitude across countries. The core-city comparison is H6.
- Other members of the panel are sums of their NUTS 3 regions, so the measure is the same for all.
- This is the only source found in which the three cities, and their peers, are counted by one definition.

**Czech pipeline and prices (RQ2, RQ3).** ČSÚ open data:

- `STA09B`: dwellings started and completed, by kraj, monthly cumulated, 2006-01 to 2025-12, split into new
  construction, alterations, new family houses, new multi-dwelling buildings and non-residential buildings.
  Monthly flows are differenced from the cumulated values within each year.
- `STA09A1`, `STA09B2` (2026): the territorial coding changes from "building office except special" (PCSU 2) to
  "building office by territory" (PCSU 4) with the new building act's data source. 2026 is outside every window.
- `STA08`: building permits by kraj, monthly 2005–2025. These are **counts of permits and their indicative value, not
  dwellings**, so Prague's pipeline cannot be traced from permits in dwellings. Permits enter only descriptively.
- `icncr.xlsx`: price indices of flats by kraj, quarterly, 2015 Q1 to 2024 Q4 (base 2010 = 100). Whether they cover
  realised transaction prices of existing flats only is checked in the ČSÚ methodology [verify]. Whether an earlier
  segment (2010–2014) is published by kraj is checked; if it is, the H3 window starts in 2011 [verify].
- Dwelling stock by kraj: census 2011 and 2021 (Eurostat, as above), interpolated geometrically.
- The Prague file of Part 4 (`byt_vystavba.xlsx`, 1994–2025) gives dwellings under construction at 31 December. From
  2006 ČSÚ computes this stock by an identity (previous stock + starts − completions), so it is used only in a
  robustness estimate of μ (Little's law) and not as primary.

**Poland (RQ4, replications).** BDL API, powiat level (380 units):

- Starts, January–December, by form of construction (subject P3822): total, private, cooperative, for sale or rent,
  for rent, municipal, public building society (TBS), company. 2005–2025; "for rent" from 2019.
- Permits (P3816) and completions (P3824) by the same forms.
- Median price per m² of flats sold in market transactions (P3787: total, primary, secondary), 2010–2024.
- Population (72305), dwelling stock (60811).
- Gmina level: average construction period of new single- and multi-family residential buildings, months
  (747069, 747070), 2013–2025.
- **Groups.** Market = for sale or rent. Non-market = municipal + TBS + cooperative + for rent. "For rent" is mostly
  social rental initiatives (SIM) from 2019 [verify], so the non-market group gains a member mid-window, and a
  robustness check drops it. Private self-build and company housing are excluded from both groups.

**Austria (descriptive, replications).** Statistik Austria:

- Dwellings permitted by Bundesland, quarterly 2010–2026 and annual 2005–2009.
- Completed by Bundesland 2005–2024 (Vienna: new buildings only before 2024).
- Demolitions 2011–2024.
- 2024 completions and construction time by builder; 2023–2025 permits by builder.
- Builder splits are not published as a time series in these files [verify in STATcube and the City of Vienna's
  statistical yearbook, which may report subsidised completions annually]. If an annual Vienna series of
  limited-profit or subsidised completions exists, it is added to H6 descriptively and not to the family.
- OeNB residential property price index, Vienna and Austria without Vienna, quarterly [verify download].

**Prague internal (RQ5).**

- RÚIAN building points (Part 2 extract): `pocetbytu` (flats), `dokonceni` (completion date), location in
  EPSG:5514.
  - New flats = flats in buildings with `dokonceni` from 1 January 2012 to 31 December 2024.
  - Existing flats = flats in buildings completed before 2012 and still standing. Demolished buildings are not in
    RÚIAN, a stated limitation.
  - Buildings without `dokonceni` (1.8 % of flats) are counted as existing.
  - Flats added by extending existing buildings are not dated in RÚIAN and are missed.
- Units: ČSÚ Census 2021 1 km grid cells (EPSG:3035 cells distributed in EPSG:5514), clipped to Prague. Cells with
  less than 0.25 km² inside Prague are dropped (their count is reported).
- Metro stations open on 1 January 2012 (Part 2's station list, minus the four Line A stations opened in April 2015
  [verify date]).
- Distance from Můstek as in Part 2.
- City-district (57 městské části) membership of each cell's centroid, for clustering.
- The Prague Heritage Reserve polygon (NPÚ) [verify source] for a robustness check.

**Flags set before estimation (never from outcomes).** COVID quarters (2020 Q2 – 2021 Q2), the building-act
transition (2024 onward), Polish powiats merged or split during the window.

## 4. Why not synthetic control, and what three cities can identify

- **Synthetic control needs an intervention.** None is dated for Prague in the window:
  - The 2024 building act applies to all of Czechia, so there is no untreated Czech donor. Cross-country donors
    differ in their national credit and cost cycles.
  - Vienna's limited-profit sector predates any window.
  - The act's effect is therefore not a registered question. §7 describes it as exploratory.
- **The conformal benchmark in H1 is the analogue that remains.** Prague is compared with a counterfactual formed from
  peers, and the p-value is exact under exchangeability (Chernozhukov, Wüthrich and Zhu 2021). Exchangeability of
  Prague with other European metro regions, conditional on the predictors, is the assumption. It is stated, not
  tested.
- **Single-unit inference.** Where Prague is one unit in a national panel (H2, H3), inference comes from its own time
  series (block bootstrap, Driscoll–Kraay). A permutation over kraje, reassigning "Prague" to each of the other 13, is
  reported as robustness. Its smallest attainable p is 1/14 = 0.071, which is why it cannot be the registered test.

## 5. Models

**H1.** OLS on log outcome across metro regions (unweighted):

  ln Y_r = b₀ + b₁ Δln Pop₂₀₀₁₋₂₀₁₁ + b₂ ln GDPpc_PPS,2011 + b₃ ln Pop₂₀₁₁ + b₄ capital_r + ε_r.

- Jackknife+ residuals as in §2.
- Also reported: Prague's predicted and observed rates in dwellings per 1 000 per year, and Vienna's and Warsaw's
  residuals and ranks.
- Lagged population growth is itself partly a product of past supply: a region that has long built little grows
  little. This biases Prague's prediction downward and H1 against rejection. It is stated, and robustness 1c uses
  lagged GDP growth instead.

**H2.** For each unit u ∈ {Prague, rest}, monthly completions C and starts S of dwellings in new multi-dwelling
buildings:

  C_u,m = θ_u Σ_{k=0}^{K} w_k(μ_u, φ_u) S_u,m−k + Σ month-of-year effects + e_u,m,

- w is a discretised gamma kernel with mean μ and shape φ, K = 72 months, and θ the completion yield.
- Estimation window: completions 2012-01 to 2024-12; starts from 2006-01 feed the lags.
- Estimated by nonlinear least squares.
- December bunching of completions is absorbed by the month effects.

**H3.** Kraj r, quarter q, 2015 Q2 – 2024 Q4 (or from 2011 if the earlier index exists):

  E[S_r,q] = exp(α_r + δ_q + β_R g_r,q + (β_P − β_R) g_r,q · 1[r = Prague] + ln Stock_r,q),

- S = dwellings started in new multi-dwelling buildings.
- g_r,q = ln P_r,q−1 − ln P_r,q−5, annual price growth lagged one quarter.
- Poisson pseudo-maximum likelihood (Santos Silva and Tenreyro 2006), because small kraje have quarters with few
  starts.
- Inference as in §2.

**H4.** Powiat p, builder group b ∈ {M, NM}, year t, 2012–2024:

  E[S_b,p,t] = exp(α_b,p + δ_b,t + β_b g_p,t−1 + ln Stock_p,t−1),

- g_p,t−1 = Δln median price per m² (all market transactions) from t−2 to t−1.
- Stacked PPML; β_NM − β_M is tested.
- Powiats with no market transactions in a year, or price series gaps, are dropped for that year, and the count is
  reported.

**H5.** Grid cell c:

  E[N_c] = exp(a + γ log₂ metro_c + δ log₂ centre_c + λ ln(1 + F_c/A_c) + ln A_c),

- N = new flats 2012–2024, F = existing flats, A = cell area in Prague (km²).
- PPML.
- Inference as in §2.

**Design-stage checks (§5a), before any outcome enters a model frame.** Each uses covariates only, plus, where a
residual scale is needed, a pre-window outcome series that no confirmatory test uses:

- **H1.**
  - n after the filters, Prague's leverage and the VIFs of the predictors.
  - The power of the conformal test to detect a Prague gap of 1, 1.5, 2 and 2.5 residual SDs, under normal
    residuals. This depends only on n and α.
  - If n < 99, it is recorded that H1 cannot pass the first Holm step.
- **H2.**
  - Simulated power for μ_P − μ_R = 3, 6 and 12 months. Completions are generated from the observed starts with
    gamma kernels (μ = 24, φ = 4), with noise SD at 0.25, 0.5 and 1 × the SD of monthly starts.
  - Starts are H2's regressor, and viewing them exposes the marginal variance of H3's outcome. That exposure is
    accepted and recorded; no price series is joined.
- **H3.**
  - The within-kraj SD of g, the VIF of the Prague interaction and the MDE of β_P − β_R at 80 % power.
  - The residual scale comes from Prague's and the rest's quarterly starts 2006–2014, which are outside the H3
    window.
- **H4.**
  - The share of powiat-years with any non-market start, the within-powiat SD of g, and the MDE of β_NM − β_M.
  - The overdispersion comes from 2005–2010 starts (outside the window).
- **H5.**
  - Number of cells, VIFs of the three regressors, and the MDE of γ.
  - The overdispersion comes from flats completed 2000–2011: the H6 replication window, not the confirmatory one.

**Pre-committed consequences.**

- Any hypothesis whose MDE at 80 % power exceeds the smallest effect of substantive interest is reported as
  underpowered if not supported, never as evidence of no effect. The SESOIs are fixed in this draft:
  - H1: Prague 25 % below prediction (0.29 on the log scale).
  - H2: 6 months.
  - H3: a semi-elasticity gap of 1 (starts 10 % lower per 10 pp of price growth).
  - H4: a gap of 1.
  - H5: 0.25 per doubling of metro distance (22 % lower density).
- Margins are **not** widened after the checks.

## 6. Robustness, placebo and specification checks (reported, not in the family)

1. **H1.**
   - (a) Core NUTS 3 regions (also H6).
   - (b) Country fixed effects: Prague compared within Czechia, which reduces n drastically; reported without a test.
   - (c) Lagged GDP growth 2001–2011 in place of population growth.
   - (d) Population-weighted.
   - (e) Only 2016+ construction.
   - (f) Unknown-period threshold 5 %.
   - (g) Countries counting reconstruction dropped.
   - (h) Contemporaneous population growth 2011–2021, labelled as endogenous.
2. **H2.**
   - (a) All new construction instead of multi-dwelling buildings.
   - (b) K = 48 and 96.
   - (c) Exponential kernel.
   - (d) Excluding the COVID months.
   - (e) Little's law on the Prague file's stock of dwellings under construction, against the national equivalent.
   - (f) The permutation over kraje (§4).
3. **H3.**
   - (a) Annual frequency.
   - (b) Price growth lagged 2 and 4 quarters.
   - (c) Completions in place of starts, lagged by the H2 estimate of μ.
   - (d) All new construction.
   - (e) OLS on ln(1 + S).
   - (f) Kraj permutation.
   - (g) Excluding 2020–2021.
4. **H4.**
   - (a) Completions in place of starts.
   - (b) Non-market without "for rent".
   - (c) Without cooperatives.
   - (d) Primary-market prices.
   - (e) Excluding Warsaw and the four next-largest cities.
   - (f) 2012–2019 only (before SIM and the rate shock).
5. **H5.**
   - (a) Basic settlement units (ZSJ) in place of grid cells.
   - (b) 500 m cells.
   - (c) Stations including the 2015 extension.
   - (d) Excluding the Heritage Reserve.
   - (e) Negative binomial.
   - (f) Adding the distance to the nearest rail or tram stop (PID GTFS, Part 2).
   - (g) Leave-one-district-out.
6. **Specification curve** for each confirmatory contrast over the checks above. The share of specifications
   supporting each conclusion is reported.

## 7. Exploratory, not tested

- **The 2024 building act.** Prague's and the other kraje's monthly starts before and after 1 July 2024, shown with
  the data-source break of 2026 marked. There is no untreated comparison, so no causal reading.
- **Permits.** The indicative value of residential building permits against starts, by kraj.
- **Builders in Vienna and Warsaw.** Vienna's 2024 construction time by builder; Warsaw's non-market share over time.

## 8. Limitations (stated in the article)

- **Benchmark, not cause.** H1 says whether Prague is unusual given its demand, not why.
- **Responsiveness, not elasticity.** Prices respond to supply too. H3 and H4 estimate reduced-form responsiveness,
  and supply shocks bias them in ways that need not be equal across units.
- **One Prague.** Every Prague-specific inference rests on Prague's own time series (H2, H3) or on exchangeability
  with peers (H1).
- **Definitions.**
  - Census period of construction dates the building, not the dwelling, so conversions in old buildings are missed
    everywhere.
  - Czech starts and completions come from building-office reports, and the stock under construction is an
    identity.
  - Polish "for sale or rent" mixes developers' sales and institutional rental.
  - RÚIAN keeps only standing buildings and dates buildings, not added flats.
- **Transfer.** H4 is tested in Poland. Whether Austrian limited-profit builders behave like Polish TBS and SIM is an
  assumption the article must state, not a finding.
- **Resolution.** 1 km cells and 14 kraje are coarse, and results may depend on the zoning (Openshaw 1984).

## 9. Deliverables

- `tools/praha/housing_fetch.py` (this draft): downloads, hashes.
- To follow after registration:
  - `tools/praha/housing_data.py`: panels.
  - `housing_power.py`: §5a.
  - `housing_extended.py`: H1–H5.
  - `housing_robust.py`: §6.
  - `figures_housing_extended.py`.
- `assets/praha/housing_extended.json`, `housing_robust.json`.
- An extended article, `texts/prague-housing-study.html`.
- This file.

## References

- Barber, R. F., Candès, E. J., Ramdas, A., Tibshirani, R. J. (2021): Predictive inference with the jackknife+.
  Annals of Statistics 49(1), 486–507.
- Baum-Snow, N., Han, L. (2024): The microgeography of housing supply. Journal of Political Economy 132(6)
  [verify pages].
- Caldera, A., Johansson, Å. (2013): The price responsiveness of housing supply in OECD countries. Journal of Housing
  Economics 22(3), 231–249.
- Chernozhukov, V., Wüthrich, K., Zhu, Y. (2021): An exact and robust conformal inference method for counterfactual
  and synthetic controls. Journal of the American Statistical Association 116(536), 1849–1864.
- Conley, T. G., Taber, C. R. (2011): Inference with "difference in differences" with a small number of policy
  changes. Review of Economics and Statistics 93(1), 113–125.
- Driscoll, J. C., Kraay, A. C. (1998): Consistent covariance matrix estimation with spatially dependent panel data.
  Review of Economics and Statistics 80(4), 549–560.
- Friesenecker, M., Kazepov, Y. (2021): Housing Vienna: the socio-spatial effects of inclusionary and exclusionary
  mechanisms of housing provision. Social Inclusion 9(2), 77–90.
- Glaeser, E. L., Gyourko, J. (2018): The economic implications of housing supply. Journal of Economic Perspectives
  32(1), 3–30.
- Glaeser, E. L., Gyourko, J., Saks, R. (2005): Why is Manhattan so expensive? Regulation and the rise in housing
  prices. Journal of Law and Economics 48(2), 331–369.
- Green, R. K., Malpezzi, S., Mayo, S. K. (2005): Metropolitan-specific estimates of the price elasticity of supply of
  housing, and their sources. American Economic Review 95(2), 334–339.
- Gyourko, J., Molloy, R. (2015): Regulation and housing supply. Handbook of Regional and Urban Economics 5,
  1289–1337.
- Hilber, C. A. L., Vermeulen, W. (2016): The impact of supply constraints on house prices in England. Economic
  Journal 126(591), 358–405.
- Holm, S. (1979): A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics 6(2),
  65–70.
- Kadi, J. (2015): Recommodifying housing in formerly "Red" Vienna? Housing, Theory and Society 32(3), 247–265.
- Kemeny, J. (1995): From Public Housing to the Social Market. Routledge.
- MacKinnon, J. G., Webb, M. D. (2018): The wild bootstrap for few (treated) clusters. Econometrics Journal 21(2),
  114–135.
- Mayer, C. J., Somerville, C. T. (2000): Residential construction: using the urban growth model to estimate housing
  supply. Journal of Urban Economics 48(1), 85–109.
- Openshaw, S. (1984): The Modifiable Areal Unit Problem. CATMOG 38.
- Saiz, A. (2010): The geographic determinants of housing supply. Quarterly Journal of Economics 125(3), 1253–1296.
- Santos Silva, J. M. C., Tenreyro, S. (2006): The log of gravity. Review of Economics and Statistics 88(4), 641–658.
- Topel, R., Rosen, S. (1988): Housing investment in the United States. Journal of Political Economy 96(4),
  718–740.
- World Bank (2020): Doing Business 2020, economy profile Czech Republic.

## Appendix A. Raw files (SHA-256)

See `docs/research/prague-housing-files.sha256`, written by `tools/praha/housing_fetch.py` and committed with this
file. 62 files. BDL powiat files cover 380 powiats (382 units for completions, population and stock, which include
units that ceased to exist); starts and permits 2005–2025 ("for rent" 2019–2025), prices 2010–2024, completions,
population and stock 1995–2025.

**Not yet downloaded:** the gmina-level construction periods (BDL 747069, 747070), which feed only the H6
replication. The anonymous BDL quota blocked the connection partway through; they will be fetched and hashed before
registration.

## Changes after registration

(none yet)
