# Part 4 housing: referee reports on design draft v1 (29 Sep 2026), consolidated

Three referees: housing economics, statistics, data audit. There is no "open questions" list in the draft, so the
referees ruled on the [verify] items instead.

## 1. Definitions that change the design (data audit, confirmed from ČSÚ methodology)

- **ČSÚ "zahájené byty" are dwellings permitted in the period**, not physically started. The statistics "vychází z
  údajů o stavebních povoleních" (are based on building-permit data).
  - Completions are dwellings given a house number, or new dwellings in existing buildings.
  - Rename "starts" to **permitted dwellings** throughout.
  - **RQ2 becomes the permit-to-house-number lag**, which includes permitted projects never built (absorbed in θ).
  - **H3 becomes the responsiveness of permitting** to prices.
  - Delete the claim that the pipeline "cannot be traced from permits in dwellings".
  - State in §8 that H2 does not measure the time needed to obtain a permit.
- **Multi-dwelling series.** Codes 3074 (permitted) and 3114 (completed) "v nových bytových domech" exist for all 14
  kraje, 2006-01 to 2025-12.
  - "All new construction" = 3072 + 3074 and 3113 + 3114. Do not use 3049/3111; 3111 starts in 2018.
- **Gaps.** The 2006-11 cumulation is missing in every series. Pre-register how Nov + Dec 2006 is split, or start the
  completion window so that it is not needed. Negative monthly differences (5 in permitted, 9 in completed, none in
  Prague) need a rule, and December revisions need month effects.
- **2026 break.** It applies to permitted dwellings (STA09A1) and permits (STA08A2) only; completions (STA09B2) stay
  on the old coding. Fix the text.
- **Price index `icncr`.**
  - It is ČÚZK cadastre purchase contracts: an unmixed mean price per m², **covering new and existing flats together**,
    2015 Q1 – 2024 Q4.
  - There is no 2010–2014 kraj series, so drop the "from 2011" clause.
  - New supply in Prague shifts the index mechanically; state this.
  - Window: g = ln P(q−1) − ln P(q−5) is first defined in **2016 Q2**, so the sample is 2016 Q2 – 2024 Q4 (35 quarters).
  - Alternatives:
    - ČSÚ realised existing-flat and new-flat indices (Prague vs the rest) as robustness, or as the preferred regressor;
    - the icncr family-house index as a placebo regressor.
- **Eurostat census and H1 sample.**
  - After the unknown-period filter and the covariate requirements, **n = 178**, not "well over 200".
  - **Warsaw drops**, because PL912/913 population starts in 2014. Rebuild it from BDL powiat population (72305).
  - Only 15 capital metros survive, so the capital dummy rests on 15 units.
  - GDP is missing for RO, CH and 8 NL regions. Take RO from 2012 and CH from national accounts, or drop GDP;
    pre-register the choice.
  - Metro mapping, confirmed: Prague = CZ010 + CZ020; Vienna = AT112, AT125, AT126, AT127, AT130; Warsaw = PL911–913.
    Download and hash the NUTS 2021 typology file.
  - The **Czech census concept is "construction or reconstruction"**, and so are ES and HR. This inflates the Czech
    numerator, which works against H1. The robustness check "drop countries that count reconstruction" would drop
    Prague itself, so rebuild Prague's numerator from ČSÚ municipal completions (new construction only) and report its
    rank under both.
  - Unknown-period share: Prague metro 4.6 %, and 7 of 14 Czech kraje above 5 %.
  - Reference dates: CZ 26 Mar, PL 31 Mar, AT 31 Oct 2021, DE 15 May 2022 [verify], IE 3 Apr 2022 [verify]. Annualise
    with each country's own date.
- **BDL.**
  - **"For rent" (747733, 2019+) is an "of which" line of "for sale or rent"**. Adding it to non-market double-counts
    and moves market rental across. Remove it from non-market, and drop the SIM claim.
  - Non-market primary = municipal + TBS/social rental. Cooperatives are a variant: since the 2007 reform they build
    mostly for sale.
  - Completions and permits have no "for rent" line.
  - Price attribute 91 with value 0 means no transactions: treat it as missing.
  - Merge powiat wałbrzyski with Wałbrzych city for all years.
  - The primary-market price is valid in only 64.9 % of powiat-years.
  - Polish starts are notified starts of works, which is a different concept from the Czech one; say so in H6.
- **RÚIAN.**
  - A Prague filter by the 57 city-district codes is mandatory; the extract includes other statutory cities.
  - Missing completion date: 2.14 % of Prague flats.
  - Dates heap on 31 December, not 1 January (harmless for annual windows).
  - **6.8 % of the 2012–2024 flats have construction types implausible for new building** (codes 10 and 4 mainly),
    which suggests reconstructions. Add a robustness check excluding them.
  - Re-query with `nespravny`, `platiod` and `pocetpodlazi`.
- **Vienna by builder.** No annual series was found. The 2024 builder coding is back-coded from current federation
  membership, and completions are partly imputed.
  - Possible sources are STATcube cubes (login) and IIBW/BMF subsidy commitments by Bundesland [verify].

## 2. Family and inference

1. **H1 is effectively seen for Prague.** Prague's census numerator is close to the ČSÚ completions already published
   in Part 4, and the direction and SESOI were chosen after Part 4. State this in §0.
   - Simulated power at the SESOI is negligible unless σ ≲ 0.1: 80 % power needs about 3.4 SD at α = 0.01 and 2.6 SD
     at 0.05.
   - **Take H1 out of the Holm family.** Report Prague's rank as the estimand.
   - Compute each region's score from a **leave-one-country-out** fit, studentised (locally weighted conformal).
   - Report a country-level rank as sensitivity.
   - Add a decomposition: Czechia's national residual against Prague minus the other Czech metro regions.
   - Cite Vovk–Gammerman–Shafer 2005 and Lei et al. 2018, not jackknife+ or Chernozhukov et al., for the rank p.
2. **H1 model.**
   - Add ln(dwellings / 1 000 pop) in 2011 and the change in households 2001–2011.
   - Use a kink at zero population growth: max/min terms.
   - Pre-register the core-versus-metro reading ("displacement to the suburbs").
   - Add a Bartik employment shifter as robustness.
   - State that lagged growth absorbs long-standing constraints.
3. **H3 inference is invalid as written.**
   - Driscoll–Kraay with a single treated unit collapses to a single-series HAC, and with T = 35 it over-rejects.
   - A permutation over kraje has minimum p = 1/13 or 1/14.
   - **Move H3 out of the family.** Report the estimate with a 90 % EWC interval (ν ≈ 4) or fixed-b, plus Prague's
     rank among the kraje.
   - Estimand: the **cumulative** response Σ β over 12 lags, plus the lag profile. This distinguishes "less" from
     "later".
   - A relative SESOI of β_P/β_R ≤ 0.5.
4. **Středočeský kraj is contaminated** by Prague's spillover. Drop it from the reference group in H2 and H3, and
   treat Prague + CZ020 as a treated-unit variant.
5. **H2.**
   - Fixed-design residual block bootstrap: S held fixed, the same block indices for Prague and the rest, a stationary
     bootstrap with Politis–White block length, and 12/24 as sensitivity.
   - Use no renormalisation of the truncated gamma (report the tail mass), or K = 96.
   - Report the profile likelihood of μ and the (θ, μ) correlation.
   - A composition limitation: Prague's projects are larger.
   - Robustness: Prague against Jihomoravský kraj (Brno) alone.
   - Little's law becomes a consistency diagnostic, shown as a band, because it is not independent.
6. **H4.**
   - The fixed effects δ_{b,t} remove the aggregate cycle, so H4 cannot speak to counter-cyclicality. Restate RQ4 as a
     question about Poland only.
   - Add a separate cyclicality estimand: national price growth, without δ_{b,t}.
   - Common support: estimate both arms on powiats with any non-market start.
   - Cluster by powiat with a WCR score bootstrap. Report the effective number of clusters. Use 16 voivodeships with
     Webb weights as robustness.
   - The §5a statistic (share of powiat-years with any non-market start) is computed from 2005–2011 only.
   - Vienna: an Austrian Länder panel of subsidy commitments, descriptive [verify availability].
7. **H5.**
   - RQ5's interpretation is not identified. Near-metro cells are built-out estates, so a zero or positive γ is also
     consistent with lack of land or with redevelopment cost. Replace the sentence; no reading is confirmatory.
   - **Existing flats as a control is contaminated**, because demolitions are missing. Use the Census 2011 1 km grid
     dwellings if available, with a restricted cubic spline.
   - Ladder:
     - (i) primary;
     - (ii) + developable land in 2012 (Urban Atlas);
     - (iii) + regulatory layers (heritage reserve and zones, floodplain, nature protection, airport noise, 1999 plan).
       This last step is reported as a decomposition.
   - **Confirmatory window 1 Jan 2012 – 25 Mar 2021**, never inspected. Part 2 saw the post-census flats. 2012–2024 is
     secondary.
   - Clustering by the 22 administrative districts (WCR, Webb); 57 as sensitivity. Decision p = max(p_Conley, p_WCR).
     Conley at 1.5 and 3 km. A distance floor of 100 m. Buildable-land restriction. Flag cells near line D.
8. **The confirmatory family is therefore about {H2, H4, H5}**, Holm, pending the author's reasoning. Anything
   demoted is reported as an estimate with a pre-written reporting rule.
9. **Relevance checks.** Rename "manipulation check" to "relevance check". If one fails, the paired result is labelled
   uninformative.
10. **H2 power simulation leaks H3's outcome** (monthly permitted dwellings). Use a sealed script, committed and
    hashed, that outputs only the power table; or synthetic permitted dwellings from an AR process fitted to
    2006–2014.
11. **Specification curve.** Robust = at least 75 % of specifications share the sign and at least 50 % reach p < 0.05.

## 3. Framing

- The title and the "who builds" section invite a causal reading about limited-profit builders; nothing tests that.
  Say so in §8, citing Sinai & Waldfogel 2005 and Eriksen & Rosenthal 2010.
- Quantity is not welfare: Warsaw built the most and still had fast price growth.
- Doing Business: say it is a warehouse case from a report discontinued in 2021, or drop it. Use an OECD housing
  chapter [verify].
- **Core vs metro.** Prague may build normally at metro scale, in the suburbs.

## 4. Literature to add (mark [verify] where unsure)

Paciorek 2013; Mayer & Somerville 2000b; Glaeser & Gyourko 2005; Glaeser, Gyourko & Saiz 2008; Ball, Meen & Nygaard
2010; Cavalleri, Cournède & Özsöğüt 2019; Sinai & Waldfogel 2005; Eriksen & Rosenthal 2010; Stephens, Lux & Sunega
2015; Lux & Sunega 2014; Matznetter 2002; Lei et al. 2018; Vovk, Gammerman & Shafer 2005; Kiefer & Vogelsang 2005;
Lazarus et al. 2018 (EWC); Politis & White 2004.
