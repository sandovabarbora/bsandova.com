# Prague builds two homes for Vienna's three: research design (Part 4, extended)

**Status: registered.** Version 2, 29 September 2026, after review by three referees (housing economics,
statistics, data audit; `docs/research/prague-housing-referees.md`). Committed before any model below is estimated
and before any outcome in a confirmatory window is summarised. §0 lists everything outcome-related that had been seen
at registration. The design-stage scripts (`housing_data.py`, `housing_power.py`) were committed, sealed, in
`d264536` before they were first run. Their outputs are in §5a. Deviations are listed, dated, in "Changes after
registration".

Terminology. ČSÚ's "zahájené byty" are **dwellings permitted** in the period: the statistic is built from building
permits, not from physical starts. This design calls them *permitted dwellings* throughout. ČSÚ "completed dwellings"
are dwellings given a house number, or new dwellings created in existing buildings. Polish "mieszkania, których
budowę rozpoczęto" are notified starts of works, a different concept, and are called *starts*.

## 0. What has already been seen

**Part 4 (published).** `texts/prague-housing.html` and `assets/praha/cities.json` show dwellings completed per 1 000
residents, 2012–2024, each city counted by its own office:

- **Prague** (ČSÚ, including extensions and conversions): 3.09 (2013) to 4.91 (2022); 6 489 dwellings in 2024
  (first release 6 511); 2015–2024 mean 4.5. Every annual value 2012–2024 is in `cities.json`.
- **Vienna** (Statistik Austria, new buildings only): peak 8.5 (2021, 16 262 dwellings), 5.4 in 2024; 6.2 in 2024
  with extensions and conversions; 2015–2024 mean 6.6.
- **Warsaw** (BDL): peak 13.2 (2018, 23 430); 2015–2024 mean 10.4; own rates match the office's 11.50 (2016) and
  11.56 (2017).
- **Builders in 2024:**
  - Vienna: limited-profit associations 24.9 % (3 107 of 12 478), public sector 2.4 %, private persons 6.8 %.
  - Warsaw: municipal and TBS 0.7 % (96 of 14 873).

**Consequences for this design (disclosed at the referees' request).**

- **H1 is effectively seen for Prague.**
  - Prague's census numerator (dwellings built 2011–2021) is close to the ČSÚ completions of 2012–2021, which Part 4
    published.
  - The direction of H1 was chosen after Part 4, and so was its smallest effect of interest (SESOI).
  - H1 is therefore **not confirmatory** (§2).
- **The SESOIs of every question were set after Part 4 had been published.** They were chosen on substantive
  grounds (§5), not from outcome data of the confirmatory windows. No outcome in those windows has been summarised.
- **H5's post-2021 part was seen in Part 2.** Part 2 reported:
  - 33 300 flats (4.5 % of Prague's) completed after 26 March 2021;
  - 3.74 % of flats standing at the October 2025 election;
  - 88 of 1 120 precincts with more than 10 % of their flats post-census.

  The confirmatory H5 window is therefore **1 January 2012 – 25 March 2021**. Part 2 used flats completed before the
  census only as allocation weights and never summarised them by period or location. 2012–2024 is secondary.
- **Rows of the Part 4 Prague file** (`byt_vystavba.xlsx`, 1994–2025) beyond completions 2012–2024 were read into
  memory by `cities.py`. They are treated as possibly seen: permitted dwellings, dwellings under construction, other
  years.

**Seen while preparing draft v1 (structure inspection and web searches).**

- Austrian national completions 2022–2024.
- The ČSÚ flat-price index (base 2010) for 2015 Q1 – 2016 Q1 by kraj. This is H3's regressor.
- Prague's mean purchase price of flats, 103 693 CZK/m² (2023) and 115 889 CZK/m² (2024), from search snippets.
- Single cells printed in the first lines of the ČSÚ CSVs:
  - Czechia: 8 713 permits (January 2005); 61 004 permitted dwellings (1990); Q1 2026: 14 290 permits and 9 681
    permitted dwellings; 2 308 completions (January 2026).
  - Prague: 526 permitted dwellings (January 2006); 860 permitted and 640 completed (January 2026); 419 permits
    (Q1 2026).
- OeNB: Vienna property prices +2.9 % in 2025.
- World Bank Doing Business 2020 figures on construction permits.

**Seen in the referee reports (coverage statistics computed by the data referee).**

- H1: n = 178 under the referee's filters; Prague metro unknown-period share 4.6 %; 7 of 14 kraje above 5 %.
- Poland: the primary-market price is valid in 64.9 % of powiat-years.
- ČSÚ: 5 negative monthly differences in permitted dwellings and 9 in completions, none in Prague.
- RÚIAN:
  - `dokonceni` is missing for 2.14 % of Prague's flats.
  - **6.8 % of flats completed 2012–2024 have construction types implausible for new building** (mainly codes 10
    and 4). This is a count of H5's secondary-window outcome by type; it is used only to define robustness 5h.

**Seen at the design stage (v2).** These came from the sealed scripts' reports, which contain covariate-side counts
only:

- H1 sample counts and drop reasons.
- Warsaw's 2001 and 2011 population rebuilt from BDL.
- 15 negative monthly differences pooled across the four ČSÚ series.
- RÚIAN Prague: 100 713 buildings with flats, 736 369 flats, 11 flagged `nespravny`, `pocetpodlazi` missing for
  0.76 %.
- 524 grid cells.
- The power tables in §5a.

`housing_power.py` reads, inside its simulations, three pre-window outcome series and writes none of them out:

- permitted dwellings 2007–2014;
- Polish starts 2005–2011;
- Prague flats completed 2000–2011, which is the H6 replication window of H5.

## 1. Research questions and estimands

Three cities identify nothing beyond Part 4's description. Every question moves the unit of inference to a panel in
which Prague is one member among many. The questions come from the housing-supply literature:

- Binding regulation and slow permitting make supply respond little to demand, so prices, not quantities, absorb
  demand shocks (Glaeser, Gyourko and Saks 2005; Glaeser, Gyourko and Saiz 2008; Gyourko and Molloy 2015; Glaeser and
  Gyourko 2018).
- Durable housing makes supply asymmetric (Glaeser and Gyourko 2005).
- Responsiveness is measured on construction flows (Topel and Rosen 1988; Mayer and Somerville 2000a). It varies with
  land and regulation (Green, Malpezzi and Mayo 2005; Saiz 2010; Paciorek 2013; Hilber and Vermeulen 2016; Mayer and
  Somerville 2000b), and is low in much of continental Europe (Caldera and Johansson 2013; Cavalleri, Cournède and
  Özsöğüt 2019; Ball, Meen and Nygaard 2010).
- Czech housing policy after 1990 is traced by Lux and Sunega (2014) and Stephens, Lux and Sunega (2015).
- Czechia's permitting was reformed by Act No. 283/2021 Coll. (the new building act) [verify: in force from 1 January
  2024 for reserved structures and from 1 July 2024 in general].
- Vienna's limited-profit sector (WGG 1979) is described by Matznetter (2002), Kemeny (1995), Kadi (2015) and
  Friesenecker and Kazepov (2021).

- **RQ1 (benchmark; estimate, not tested).** Where does the Prague metropolitan region rank among European metro
  regions in dwellings built 2011–2021 per resident, given predetermined demand?
  - **Estimand:** Prague's rank, and its conformal p-value, among studentised leave-one-country-out residuals.
  - Reported with Czechia's national residual, and Prague's residual minus those of the other Czech metro regions.
  - This is a benchmark against peers, not a causal effect.
- **RQ2 (permit to house number).** Once dwellings in new multi-dwelling buildings are permitted, is the lag until
  they receive house numbers longer in Prague than in the rest of Czechia outside Středočeský kraj?
  - **Estimand:** μ_P − μ_R, the difference in the means of the distributed lag from permitted to completed
    dwellings, in months.
  - It is a property of the aggregate flow. Projects that are permitted but never built lower the yield θ, not μ.
  - It does not measure the time needed to obtain a permit (§8).
- **RQ3 (permitting responsiveness; estimate, not tested).** Does Prague's permitting respond less, or later, to
  price growth than that of the other kraje?
  - **Estimand:** the cumulative response Σ_{ℓ=1}^{12} β_ℓ of permitted dwellings in new multi-dwelling buildings to
    lagged quarterly log price growth, Prague relative to the rest (without Středočeský kraj), with the lag profile.
  - This is reduced-form responsiveness, not a structural elasticity.
- **RQ4 (builders in Poland).** Within Polish powiats, do non-market builders (municipal and public building
  societies, TBS) start fewer dwellings in response to local price growth than developers building for sale or rent?
  - **Estimand:** β_NM − β_M in a stacked Poisson model with powiat-by-group and year-by-group effects.
  - The year effects remove the national cycle, so RQ4 is about the **cross-sectional** allocation response in
    Poland. It is not about counter-cyclicality, and not about Vienna.
  - Cyclicality is a separate, descriptive estimand: the same model with national price growth and no year effects.
- **RQ5 (Prague and the metro).** Within Prague, is the density of new flats associated with metro proximity,
  holding distance from the centre and pre-period population density equal?
  - **Estimand:** γ, the coefficient on log₂ distance to the nearest metro station open on 1 January 2012, in a
    Poisson model of flats completed 1 January 2012 – 25 March 2021 per km² of 1 km cell.
  - This is a controlled association.
  - **No reading of its sign is confirmatory.**
    - Near-metro cells are largely built-out estates, so a zero or positive γ is consistent with binding
      regulation, with a lack of land, and with redevelopment cost alike.
    - A negative γ is consistent with an accessibility premium.
  - The ladder in §5 (developable land, then regulatory layers) is reported as a decomposition, not as
    identification.

## 2. The confirmatory family, hypotheses and reporting rules

**The confirmatory family is {H2, H4, H5}, with a Holm step-down at family-wise α = 0.05.**

The referees proposed this family, and it is adopted for three reasons:

- **H1 cannot be confirmatory.**
  - Its Prague numerator is effectively known (§0), and its direction and SESOI were set after Part 4.
  - It also has almost no power at the SESOI (§5a).
  - A test whose result is largely known and which could not reject at a plausible effect adds nothing to the family.
- **H3's registered inference was invalid.** With one treated unit, Driscoll–Kraay collapses to a single-series HAC,
  and with T = 35 quarters it over-rejects. A permutation over kraje has a smallest p of 1/13. No valid test at the
  family's thresholds exists for this design, so H3 is reported as an estimate with an honest interval.
- **H2, H4 and H5 each have:**
  - an outcome window that has not been summarised;
  - an inference procedure valid for their design (a time-series bootstrap; 380 clusters; spatial and 22-cluster
    procedures with the more conservative p);
  - enough units to reach the Holm thresholds.

H3 and H1 remain in the article with **pre-written reporting rules**, so that their wording cannot be chosen after the
estimates are seen.

**Relevance checks** (outside the family). If one fails, the paired result is labelled *uninformative*, whatever its
p-value:

- **R1 (H1):** lagged population growth has a positive coefficient.
- **R3 (H3):** the rest's cumulative response is positive.
- **R4 (H4):** market starts respond positively to local price growth.
- **R2 (H2):** the rest's estimated yield θ lies in (0, 1.2] and its μ̂ lies inside the lag support (3 to 60 months).

### Confirmatory

- **H2 (Prague's permit-to-house-number lag is longer).** μ_P − μ_R > 0.
  - Test: one-sided. The standard error comes from a fixed-design residual stationary bootstrap (Politis and Romano
    1994):
    - permitted dwellings are held fixed;
    - the same block indices are used for Prague and the rest;
    - the mean block length follows Politis and White (2004), with 12 and 24 months as sensitivity;
    - B = 9 999, and both lag distributions are re-estimated in each draw.
  - *Supported* if p passes its Holm threshold. The contrast is reported in months with its 90 % interval, and a
    positive result is written "longer by …".
- **H4 (non-market builders respond less, Poland).** β_NM − β_M < 0.
  - Test: one-sided Wald.
    - Standard errors are clustered by powiat, with a wild cluster restricted score bootstrap (WCR; Kline and Santos
      2012; Webb weights; B = 9 999).
    - The effective number of clusters is reported (Carter, Schnepel and Steigerwald 2017).
    - Clustering by the 16 voivodeships (WCR, Webb) is robustness.
  - *Supported* if p passes its Holm threshold.
- **H5 (new-flat density and the metro).** Two-sided question, one-sided tests:
  - H5 tests γ < 0 ("denser near the metro").
  - The decision p is max(p_Conley 1.5 km, p_WCR by the 22 administrative districts, Webb). Conley at 3 km and WCR
    by the 57 city districts are sensitivity.
  - *Supported* if p passes its Holm threshold.
  - If not, the one-sided test of γ > 0 at 5 % (same rule) is reported as "new construction is sparser near the
    metro". This second test is outside the family. Otherwise the result is *indeterminate*.
  - Either reading is described as an association under the caveats of RQ5.

### Estimates with pre-written reporting rules

- **H1.** Prague's rank r among the n regions and the conformal p = (1 + #{j: s_j ≤ s_P})/(n + 1). The scores s are
  studentised leave-one-country-out residuals (Vovk, Gammerman and Shafer 2005; Lei et al. 2018). The written
  statements are fixed in advance:
  - **"Prague builds less than peers with its demand"** only if p ≤ 0.05 for the metro region **and** for the core
    region (H6).
  - **"Prague builds little in the city but normally across its metropolitan region"** if the core p ≤ 0.05 and the
    metro p > 0.05. This is the pre-registered "displacement to the suburbs" reading.
  - **"Within the range of European peers"** otherwise. The rank is always shown.
  - The same statements are applied to Prague's rank under the numerator rebuilt from ČSÚ municipal completions of
    new construction (§3), and the article reports both.
- **H3.** The cumulative relative response with a 90 % EWC interval (Lazarus et al. 2018; about ν = 4 degrees of
  freedom; fixed-b, Kiefer and Vogelsang 2005, as sensitivity), and Prague's rank among the 13 kraje.
  - **"Prague's permitting responds less"** only if the whole 90 % interval lies below 0 and β_P/β_R ≤ 0.5 (the
    SESOI).
  - **"… responds later"** if the cumulative response is not below the rest's, but the lag profile's centre of mass
    is at least 2 quarters later.
  - **"Cannot be told apart"** otherwise.
- **H6 (replications, no test):**
  - H1 with core NUTS 3 regions and within Czechia;
  - H2 with Prague + Středočeský kraj as the treated unit, and against Jihomoravský kraj alone;
  - H3 on Polish powiats (Warsaw against others, starts, a different concept);
  - H5 on flats completed 2000–2011 and on 2012–2024 (secondary window).

## 3. Data and measures

URLs are in `tools/praha/housing_fetch.py`; hashes are in Appendix A.

**H1: harmonised benchmark.**

- **Numerator.** Eurostat Census 2021 `cens_21dwop_r3`: dwellings in buildings constructed 2011–2015 and 2016 or
  later, all occupancy states. It is annualised with **each country's own census reference date**:
  - dwellings / years from 1 January 2011 to the reference date / population on 1 January 2011 × 1 000;
  - CZ 26 March 2021, PL 31 March 2021, AT 31 October 2021, DE 15 May 2022 [verify], IE 3 April 2022 [verify];
  - the others are taken from Eurostat's census metadata and recorded before estimation.
- **Reconstruction.** Czechia, Spain and Croatia count "construction *or reconstruction*", which inflates their
  numerators. This works against H1's direction for Prague.
  - Prague's (and the other Czech metros') numerator is rebuilt from ČSÚ completions by municipality (`200068-25`,
    dwellings in new family and multi-dwelling houses, 2011–2021 prorated to the census date).
  - The rank is reported under both numerators.
- **Unit.** Eurostat metropolitan regions of the NUTS 2021 typology (`NUTS2021.xlsx`, sheet *Metropolitan*).
  Confirmed mappings:
  - Prague CZ001MC = CZ010 + CZ020;
  - Vienna AT001MC = AT112, AT125, AT126, AT127, AT130;
  - Warsaw PL001MC = PL911–913.
  - Capital metros are the codes ending in "MC".
- **Covariates, all dated 2011 or earlier:**
  - log population 2011;
  - annualised log population growth to 2011, with a kink at zero: max(g, 0) and min(g, 0);
  - log GDP per head in PPS, 2011;
  - log dwellings per 1 000 residents, 2011 (Census 2011);
  - a capital-metro indicator.
- **Registered data rules:**
  - Growth starts at the first year t0 ∈ [2001, 2007] in which every member region has a value, with
    2011 − t0 ≥ 4.
  - NUTS codes are traced back through pure recodes only (NUTS 2021 ← 2016 ← 2013, no boundary changes).
  - Warsaw's 2001 and 2011 population and 2010 dwelling stock are rebuilt from BDL powiats (72305, 60811), with
    Eurostat 1 January taken as the BDL year-end of t − 1.
  - Romania's GDP is taken from 2012. Metros with any other member missing GDP are dropped from the primary sample
    and kept in a no-GDP sensitivity check.
  - The change in households 2001–2011, which the referees requested, is **not available** for NUTS 3 in the 2011
    census (Eurostat publishes it at NUTS 2 only). It is omitted, and the omission is recorded.
- **Bartik robustness.** The employment shift-share for 2001–2011 comes from `nama_10r_3empers`: 2001 NACE shares
  times national growth excluding the region.
- **Final n = 208 metro regions in 22 countries**, 20 of them capital metros (§5a lists the drops). Prague, Vienna
  and Warsaw are all in.

**H2 and H3: ČSÚ.**

- **Series.** From `STA09B` (kraje, monthly cumulations, 2006-01 to 2025-12):
  - permitted dwellings in new multi-dwelling buildings (code 3074) and completed dwellings in the same (3114);
  - "all new construction" = 3072 + 3074 and 3113 + 3114. Codes 3049 and 3111 are not used, because 3111 begins in
    2018.
- **Monthly flows** are differences of the year-to-date cumulations, with these registered rules:
  - The 2006-11 cumulation is missing in every series, so 2006 is not used. Permitted dwellings enter from 2007-01.
  - The H2 completion window is 2013-01 to 2024-12. With K = 72, this needs permitted dwellings from 2007-01. With
    K = 96, the completion window starts in 2015-01.
  - A negative monthly difference is pooled with the preceding month or months until the pool is non-negative, and
    the pool is shared equally, so the annual total is unchanged. This affects 15 months across the four series.
  - Month-of-year effects absorb December bunching and revisions.
- **The 2026 break.** The new territorial coding applies to permitted dwellings (`STA09A1`) and permits (`STA08A2`)
  only; completions (`STA09B2`) keep the old coding. 2026 is outside every window.
- **Reference group.** The rest of Czechia is the 12 kraje other than Prague and Středočeský kraj. Středočeský kraj
  absorbs Prague's spillover, so it is excluded from the reference group and used only in the treated-unit variant
  Prague + CZ020.
- **Prices (H3).** `icncr`: ČÚZK cadastre purchase contracts, an unmixed mean price per m² of new and existing flats
  together, by kraj, 2015 Q1 – 2024 Q4.
  - g_q = ln P_{q−1} − ln P_{q−5}, so the sample is **2016 Q2 – 2024 Q4 (35 quarters)**.
  - New supply shifts a mixed index mechanically. This is stated.
  - The ČSÚ realised-price indices of existing and of new flats (Prague against the rest) are robustness.
  - The icncr family-house index is a **placebo regressor**.
- **Dwelling stock** by kraj is interpolated geometrically between the 2011 and 2021 censuses.
- **Permits** (`STA08`) are counts of permits and their indicative value. They are descriptive (§7).

**H4: Poland (BDL, powiat level, 380 units).**

- **Starts**, January–December, by form (P3822), 2005–2025. The window is 2012–2024.
- **Groups.**
  - Market = for sale or rent (747732). "For rent" (747733, from 2019) is an *of which* line of it and is not added
    anywhere.
  - Non-market (primary) = municipal (747734) + public building society, TBS (747735).
  - Cooperatives (747731) are a variant (robustness 4b): since the 2007 reform they build mostly for sale.
  - Private self-build and company housing are excluded.
- **Prices.** Median price per m² of flats sold in market transactions, all markets (633677). Attribute 91, and
  value 0, mean no transactions and are treated as missing. The primary-market price, valid in 64.9 % of powiat-years,
  is robustness only.
  - g_{p,t−1} = Δln P from t − 2 to t − 1.
- **Merges.** Powiat wałbrzyski is merged with Wałbrzych city in all years.
- **Common support.** Powiats with at least one non-market start in 2012–2024. With powiat-by-group effects, PPML
  drops all-zero groups anyway; this applies the same sample to the market arm.
- **Exposure.** ln dwelling stock (60811) at t − 1.

**Austria and Vienna (descriptive only).**

- Permits by Bundesland (quarterly 2010–2026), completions 2005–2024, demolitions, and the 2024 builder tables.
- No annual Vienna series by builder was found.
  - The 2024 builder coding is back-coded from current federation membership, and completions are partly imputed.
  - STATcube (login) and IIBW/BMF subsidy commitments by Bundesland are the remaining candidates [verify].
  - If a Länder panel of subsidy commitments can be assembled before estimation, it is shown descriptively and never
    tested.

**H5: Prague (RÚIAN and grid).**

- **Buildings.** RÚIAN building points re-queried on 29 September 2026 (layer 2) with `nespravny`, `platiod` and
  `pocetpodlazi`, **filtered to Prague's 57 city districts** (layer 8, obec 554782).
  - 100 713 buildings with flats and 736 369 flats.
  - `dokonceni` missing for 2.14 % of flats; `platiod` from 2011-07-01.
  - Completion dates heap on 31 December, which is harmless for the windows used.
- **Outcome.** Flats in buildings with `dokonceni` from 1 January 2012 to 25 March 2021 (confirmatory), or to
  31 December 2024 (secondary).
  - Buildings flagged `nespravny` (11) are dropped.
  - Robustness 5h drops construction types implausible for new building (codes 10 and 4) and buildings with
    `platiod` more than two years after `dokonceni` together with a changed flat count [verify: `platiod` alone cannot
    date a change of flats].
- **Units.** 1 km cells of the ČSÚ census grid (INSPIRE EPSG:3035 cells, geometry in EPSG:5514) with at least
  0.25 km² inside Prague: **524 cells**.
- **Density control.** The Census 2011 1 km grid with **dwellings** was not found:
  - the ČSÚ geodata portal returned HTTP 503 on 29 September 2026;
  - no ArcGIS Online item exists.
  - The control is therefore the **GEOSTAT 2011 1 km population grid** (Eurostat): ln(1 + residents per km²) as a
    restricted cubic spline with 4 knots at the 5th, 35th, 65th and 95th percentiles.
  - 40 of the 524 cells have no GEOSTAT record and are set to 0 (unpopulated).
  - RÚIAN pre-2012 flats per km² (spline) is sensitivity only, because demolished buildings are missing from RÚIAN.
- **Distances.**
  - Metro: to the 53 stations open on 1 January 2012 (Part 2's station list without the four Line A stations of
    April 2015 [verify date]), with a 100 m floor.
  - Centre: from Můstek.
- **Clusters.** The 22 administrative districts (layer 10); 57 city districts as sensitivity.
- **Ladder** (reported as a decomposition). Every layer below is fetched and hashed before any outcome is joined;
  a layer that cannot be obtained is recorded as not run.
  - (ii) Developable land in 2012: the share of the cell in Urban Atlas 2012 classes for construction sites, land
    without current use and arable land [verify access; Copernicus login].
  - (iii) Regulatory layers:
    - the Prague Heritage Reserve and heritage zones (NPÚ/IPR);
    - floodplain Q100 (IPR/DIBAVOD);
    - nature protection (RÚIAN layers 39–62);
    - the airport noise zone (IPR);
    - land-use categories of the 1999 Prague land-use plan (IPR) [verify each source].
- **Other rules.**
  - Buildable-land restriction (robustness 5f): cells with at least 0.25 km² outside forest and water (Urban Atlas).
  - Cells within 1 km of a planned line D station are flagged [verify source].

## 4. What three cities can identify, and why not synthetic control

- **Synthetic control** needs a dated intervention. None exists for Prague alone:
  - the 2024 act is national;
  - Vienna's limited-profit sector predates the windows.
- **H1** is a conformal benchmark: exact under exchangeability of the regions' scores, which is assumed and not
  tested.
  - Leave-one-country-out fitting and studentisation reduce, but do not remove, national common shocks.
  - A **country-level rank** (the country means of the scores, Czechia among 22) is reported as sensitivity.
- **Single-unit inference.**
  - H2 relies on Prague's own time series (the bootstrap).
  - H3 has no valid test at the family's thresholds and is an estimate (§2).
  - H4 and H5 have many units.

## 5. Models

**H1.** OLS across metro regions, unweighted:

ln Y_r = b₀ + b₁ max(g_r, 0) + b₂ min(g_r, 0) + b₃ ln Pop₂₀₁₁ + b₄ ln GDPpc₂₀₁₁ + b₅ ln(Dw/Pop)₂₀₁₁ + b₆ capital_r + ε_r.

- **Scores.** For each country c, the model is fitted without c. Every region of c gets the residual
  e_r = ln Y_r − x_r′b̂₋c.
- **Studentisation.** The residual is divided by σ̂₋c(x_r), a locally weighted scale (a second regression of |e| on
  the same covariates, fitted without c; Lei et al. 2018).
- **Decomposition.** Prague's score = Czechia's mean score + (Prague − mean of the other Czech metros). Both parts
  are reported.
- **Lagged growth absorbs long-standing constraints.** A region that has long built little grew little, so Prague's
  prediction is biased downward, against a "builds less" finding. This is stated; Bartik is robustness.

**H2.** For each unit u ∈ {Prague, rest}, with monthly completed dwellings C and permitted dwellings S in new
multi-dwelling buildings:

C_{u,m} = θ_u Σ_{k=0}^{K} w_k(μ_u, φ_u) S_{u,m−k} + Σ month effects + e_{u,m},

- w is the discretised gamma kernel on lags 0..K (K = 72), **not renormalised**, and the tail mass beyond K is
  reported. K = 96 is robustness.
- Estimation is by nonlinear least squares (profiled over μ and φ).
- Reported with the estimate:
  - the profile likelihood of μ for each unit;
  - the correlation of θ̂ and μ̂;
  - Little's law (the mean stock under construction / mean completions, Prague file and national) as a
    **consistency band**, not as an estimate. From 2006 ČSÚ computes that stock from permitted and completed
    dwellings, so it is not independent.

**H3.** Kraj r, quarter q, 2016 Q2 – 2024 Q4, the 13 kraje without Středočeský kraj:

E[S_{r,q}] = exp(α_r + δ_q + Σ_{ℓ=1}^{12} β_ℓ Δln P_{r,q−ℓ} + Σ_{ℓ=1}^{12} (β^P_ℓ − β_ℓ) Δln P_{r,q−ℓ} · 1[Prague] + ln Stock_{r,q}),

- PPML.
- The estimand is Σ(β^P_ℓ − β_ℓ) with the lag profile. The 12 lags are constrained to a quadratic polynomial
  (Almon), to keep 35 quarters estimable [a deviation from "12 free lags", fixed here].
- EWC 90 % interval (§2).

**H4.** Powiat p, group b ∈ {M, NM}, year t, 2012–2024:

E[S_{b,p,t}] = exp(α_{b,p} + δ_{b,t} + β_b g_{p,t−1} + ln Stock_{p,t−1}).

- Stacked PPML; β_NM − β_M is tested.
- Cyclicality (descriptive) replaces δ_{b,t} with a linear trend per group and g with national price growth.

**H5.** Cell c:

E[N_c] = exp(a + γ log₂ metro_c + δ log₂ centre_c + f(ln(1 + pop₂₀₁₁/A_c)) + ln A_c),

- PPML, with f the restricted cubic spline.
- Ladder:
  - (i) this model;
  - (ii) plus the developable-land share;
  - (iii) plus the regulatory layers.
- The change in γ from (i) to (iii) is decomposed by layer (Gelbach 2016).

### 5a. Design-stage checks (results)

Run by the sealed `tools/praha/housing_power.py` (committed in `d264536` before its first run; SHA-256 of the file
as run: see Appendix A), on frames from `tools/praha/housing_data.py`. Output:
`docs/research/prague-housing-power.json`.

**SESOIs** (set after Part 4, §0). They are not widened after these checks:

| | SESOI |
|---|---|
| H1 | Prague 25 % below prediction (−0.29 log) |
| H2 | 6 months |
| H3 | β_P/β_R ≤ 0.5 |
| H4 | a semi-elasticity gap of 1 (10 % fewer non-market starts per 10 pp of price growth, relative to market) |
| H5 | 0.25 per doubling of metro distance (22 % lower density) |

**Run history.**

- The first run (29 September 2026) aborted in H5 before writing anything: 32 boundary cells had their centroid
  outside every district polygon.
- `housing_data.py` was fixed to assign them to the nearest district (`4ca725c`), and the unchanged sealed script
  was rerun.
- Seed 20260929. Holm's first step for a family of three is α = 0.0167.

**H1 (estimate; power reported because the referees asked for it).**

- **Sample.** n = 208 metro regions in 22 countries, 20 of them capital metros. Prague (CZ001MC), Vienna (AT001MC)
  and Warsaw (PL001MC) are all in.
- **Drops**, from 297 metro regions in the typology:

  | step | lost | regions |
  |---|---|---|
  | no 2021 census period of construction | 42 | UK |
  | unknown period above 10 % | 4 | ES010M, IE001MC, IE002M, MT001MC |
  | no population in 2011, or no growth window of at least 4 years starting 2001–2007 | 26 | BE, DE, EL, FR520M, NL, NO, PL (NUTS 2016 boundary changes) |
  | GDP 2011 missing for a member | 10 | DE032M, FI002M, LV001MC, NL×5, PT001MC, PT005M |
  | Census 2011 dwellings not traceable by a pure recode | 7 | FR030M, HR×2, IT027M, PT002M, SI×2 |

  Growth windows start after 2001 for 23 metros (Denmark and two German metros in 2007, Norway in 2005, the
  Netherlands and Slovenia in 2003, four others in 2002).
  - Without GDP, n = 216.
  - The smallest attainable conformal p is 1/209 = 0.0048.
- **Power** of the rank test against a Prague gap of k residual SDs, one-sided:

  | gap (residual SDs) | 1 | 1.5 | 2 | 2.5 | 3 | 3.5 |
  |---|---|---|---|---|---|---|
  | power at α = 0.05 | 0.25 | 0.42 | 0.62 | 0.79 | 0.90 | 0.96 |
  | power at α = 0.0167 | 0.11 | 0.23 | 0.40 | 0.59 | 0.77 | 0.89 |

  - 80 % power at α = 0.05 needs a gap of about 2.6 SD. The SESOI (0.29 log) reaches that only if the residual SD
    is about 0.11 or less.
  - This confirms the referees' reason for taking H1 out of the family.

**H2 (confirmatory).**

- **Design.** Synthetic permitted dwellings come from AR(2) processes (log scale, month effects) fitted to 2007–2014
  only, for Prague and for the rest without Středočeský kraj. Completions are generated with θ = 0.8, φ = 4,
  μ_R = 24 months and AR(1) noise (ρ = 0.3).
- **Critical values** are the simulated null quantiles of the contrast (200 replications per cell).
- **Power**, one-sided, at α = 0.0167 (α = 0.05 in brackets):

  | noise SD / signal SD | Δμ = 3 months | Δμ = 6 (SESOI) | Δμ = 12 | null SD of μ̂_P − μ̂_R |
  |---|---|---|---|---|
  | 0.25 | 0.98 (0.98) | 1.00 (1.00) | 1.00 (1.00) | 0.8 months |
  | 0.5 | 0.37 (0.55) | 0.94 (0.96) | 1.00 (1.00) | 1.8 months |
  | 1.0 | 0.10 (0.20) | 0.25 (0.39) | 0.87 (0.95) | 4.1 months |

- **Adequate** at the SESOI unless monthly noise is as large as the signal.
- **Pre-committed consequence.** The noise ratio is estimated from the fitted residuals and reported. If it is at
  least 1, a non-supported H2 is written "underpowered", never "no difference".

**H3 (estimate; no power computed).**

- 35 quarters (2016 Q2 – 2024 Q4).
- The within-kraj SD of annual price growth is 0.072 in Prague and 0.089 in the median other kraj. Prague's price
  growth varies less, which widens its interval.

**H4 (confirmatory).**

- **Sample.** 252 powiats in common support (at least one non-market start in 2005–2011, used as the design-stage
  proxy for the registered 2012–2024 support). 3 240 powiat-years with a defined price change.
- Share of powiat-years with any non-market start, 2005–2011: **0.231**.
- Within-powiat SD of price growth: 0.119.
- **Design.** Powiat means and overdispersion from 2005–2011, β_M = 1. PPML with powiat-by-group and year-by-group
  effects, CR1 by powiat (the registered WCR bootstrap is not simulated). 200 replications.
- **Power:**

  | β_NM − β_M | 0 (size) | −0.5 | −1 (SESOI) |
  |---|---|---|---|
  | rejection at α = 0.0167 | 0.02 | 0.05 | 0.19 |
  | rejection at α = 0.05 | 0.06 | 0.13 | 0.26 |

- **H4 is underpowered at its SESOI.** Non-market starts are sparse (23 % of powiat-years), and local price growth
  varies little within powiats.
- **Pre-committed consequence.**
  - H4 stays in the family. A low-powered member costs the others only its share of α in Holm's steps, and dropping
    it after seeing its power would be a choice made on the design.
  - A non-supported H4 is written **"underpowered: the data cannot tell whether non-market builders respond less"**,
    never as evidence that they respond alike.
  - The SESOI is not widened.

**H5 (confirmatory).**

- **Sample.** 524 cells; VIF 2.15 (metro) and 2.06 (centre); 22 clusters.
- **Design.** The baseline surface and overdispersion (NB2, profiled) come from flats completed 2000–2011, rescaled
  to the 9.2-year window. γ is set by design. PPML with CR1 by district and t(21). 500 replications.
- **Power:**

  | γ | 0 (size) | −0.25 (SESOI) | −0.5 |
  |---|---|---|---|
  | rejection at α = 0.0167 | 0.018 | 0.99 | 1.00 |
  | rejection at α = 0.05 | 0.052 | 1.00 | 1.00 |

- The registered decision p = max(p_Conley, p_WCR) can only lower power. A margin this wide leaves room for that.

**Consequences recorded.**

- Well powered at the SESOI: H2 (unless noise ≥ signal) and H5.
- Underpowered: H4. It will be reported as such if not supported.
- H1: out of the family, confirmed.
- H3: estimate only.
- No margin is widened.

## 6. Robustness, placebo and specification checks (reported, not in the family)

1. **H1.**
   - (a) Core NUTS 3 regions (also H6).
   - (b) Country-level rank.
   - (c) Numerator rebuilt from ČSÚ for Czech metros; reconstruction-concept countries (CZ, ES, HR) dropped, with
     Prague kept on the rebuilt numerator.
   - (d) Bartik shifter in place of population growth.
   - (e) Without GDP (n = 216).
   - (f) 2016+ construction only.
   - (g) Unknown-period threshold 5 %.
   - (h) Population-weighted.
   - (i) Contemporaneous growth 2011–2021, labelled endogenous.
2. **H2.**
   - (a) All new construction.
   - (b) K = 96.
   - (c) Block lengths 12 and 24.
   - (d) Exponential kernel.
   - (e) Excluding 2020-03 to 2021-06.
   - (f) Prague + CZ020.
   - (g) Against Jihomoravský kraj alone.
   - (h) Little's law band.
3. **H3.**
   - (a) Fixed-b interval.
   - (b) Prague's rank among the 13 kraje.
   - (c) ČSÚ existing-flat and new-flat indices.
   - (d) Family-house index as placebo regressor: the expectation is no relative response.
   - (e) All new construction.
   - (f) Annual frequency.
   - (g) Excluding 2020–2021.
4. **H4.**
   - (a) Completions in place of starts (no "for rent" line exists).
   - (b) Cooperatives added to non-market.
   - (c) Primary-market prices.
   - (d) Voivodeship clustering.
   - (e) Excluding Warsaw and the four next-largest cities.
   - (f) 2012–2019 only.
   - (g) Negative binomial.
5. **H5.**
   - (a) 2012–2024 window.
   - (b) Basic settlement units (ZSJ).
   - (c) 500 m cells.
   - (d) Stations including the 2015 extension.
   - (e) Heritage Reserve excluded.
   - (f) Buildable-land restriction.
   - (g) RÚIAN pre-2012 density in place of GEOSTAT.
   - (h) Implausible construction types excluded.
   - (i) Negative binomial.
   - (j) Distance to rail and tram stops added.
   - (k) Leave-one-administrative-district-out.
   - (l) Cells near line D excluded.
6. **Specification curve** for H2, H4 and H5 over the checks above. A conclusion is called **robust** if at least
   75 % of specifications share the sign **and** at least 50 % reach p < 0.05 (one-sided, unadjusted).

## 7. Exploratory, not tested

- Permitted and completed dwellings before and after 1 July 2024, Prague and the other kraje, with the 2026 coding
  break marked.
- The indicative value of residential permits against permitted dwellings.
- Vienna's 2024 construction time by builder; Warsaw's non-market share over time; an Austrian Länder panel of
  subsidy commitments, if it exists.

## 8. Limitations and framing (stated in the article)

- **H2 does not measure the time needed to obtain a permit.** It starts at the permit. Prague's projects are also
  larger, so a longer lag may reflect project size (composition), not procedure.
- **No test of limited-profit builders' effect.**
  - Nothing here tests whether a Vienna-style sector would raise Prague's output.
  - Subsidised construction can crowd out private construction (Sinai and Waldfogel 2005; Eriksen and Rosenthal
    2010).
  - The title and the "who builds" section must not invite that reading.
- **H4 is about Poland.** Whether Austrian limited-profit builders behave like Polish municipalities and TBS is an
  assumption, not a finding.
- **Quantity is not welfare.** Warsaw built the most of the three and still had fast price growth.
- **Doing Business.** Czechia's 157th place (2020) is for a warehouse case, from a report the World Bank discontinued
  in 2021 after data irregularities. It is cited only as such, next to an OECD housing source [verify: Cavalleri,
  Cournède and Özsöğüt 2019 on Czech supply responsiveness].
- **Core against metro.** Prague may build normally at metro scale, in the suburbs. H1's reporting rule allows this.
- **Responsiveness, not elasticity.** Prices respond to supply, and icncr mixes new and existing flats.
- **Definitions.**
  - Census period of construction dates buildings (CZ, ES, HR: or their reconstruction).
  - Czech "permitted" and Polish "started" differ.
  - RÚIAN keeps only standing buildings, and dates buildings, not added flats.
- **Resolution.** 1 km cells, 13–14 kraje (Openshaw 1984).

## 9. Deliverables

- `housing_fetch.py`: downloads and hashes.
- `housing_data.py`: design frames.
- `housing_power.py`: §5a, sealed.
- To follow:
  - `housing_extended.py`: H2, H4, H5 and the H1/H3 estimates;
  - `housing_robust.py`: §6;
  - `figures_housing_extended.py`.
- `assets/praha/housing_extended.json`.
- `texts/prague-housing-study.html`.
- This file.

## 10. Response to referees

Item numbers follow `prague-housing-referees.md`.

**§1 Definitions (data audit).**

- *"Zahájené" = permitted.* Adopted throughout.
  - RQ2 is the permit-to-house-number lag, with never-built projects in θ.
  - RQ3 is the responsiveness of permitting.
  - The claim that the pipeline cannot be traced in dwellings is deleted.
  - §8 states that H2 excludes the time needed to obtain a permit.
- *Multi-dwelling codes.* 3074 and 3114 are primary; "all new" = 3072 + 3074 and 3113 + 3114; 3049 and 3111 are not
  used.
- *Gaps.* 2006 is not used. Windows are set so that Nov–Dec 2006 is never needed. There is a pooling rule for
  negative months, and month effects.
- *2026 break.* The text is corrected: permitted dwellings and permits only.
- *icncr.*
  - Described correctly (cadastre contracts, new and existing flats).
  - The "from 2011" clause is dropped.
  - The window is 2016 Q2 – 2024 Q4 (35 quarters).
  - The mechanical shift is stated.
  - ČSÚ realised indices are robustness; the family-house index is a placebo.
- *Eurostat and H1 sample.*
  - Warsaw is rebuilt from BDL.
  - The metro mapping is confirmed, and the typology file is downloaded and hashed.
  - GDP: RO from 2012. CH has 2011 GDP in the downloaded file, so no national-accounts input is needed. Metros with
    missing members are dropped, with a no-GDP sensitivity check.
  - The reconstruction concept is handled by a rebuilt Czech numerator and both ranks.
  - Reference dates are per country.
  - The final n is **208**, not 178. The difference comes from the registered growth-window rule (t0 up to 2007,
    which keeps Denmark, Norway, the Netherlands and others) and from tracing NUTS recodes back to Census 2011 codes
    (which keeps France). Every drop is listed in §5a.
- *BDL.*
  - "For rent" is an of-which line; it is removed from non-market, and the SIM claim is dropped.
  - Non-market = municipal + TBS; cooperatives are a variant.
  - Attribute 91 and 0 are treated as missing.
  - Wałbrzych is merged.
  - The primary-market price is robustness only.
  - Starts are described as a different concept in H6.
- *RÚIAN.* Re-queried with the Prague filter and the three fields. The missing share (2.14 %) and date heaping are
  recorded. The implausible-type exclusion is robustness 5h.
- *Vienna by builder.* Recorded as not found. The back-coding and imputation are stated. It is descriptive only.

**§2 Family and inference.**

1. H1 is out of the family. It is reported as a rank with a pre-written rule, with leave-one-country-out studentised
   scores, a country-level rank, the decomposition, and the citations corrected. The simulated power is confirmed
   (§5a).
2. H1 model: the 2011 dwelling density and the kink are added. Households are not available at NUTS 3 (recorded).
   The core-versus-metro reading is pre-registered. Bartik is robustness. The absorption of constraints is stated.
3. H3 is out of the family. The estimand is the cumulative response over 12 lags (Almon-constrained) with its
   profile. The interval is EWC with fixed-b as sensitivity, and Prague's rank is reported. The relative SESOI
   is 0.5.
4. Středočeský kraj is out of the reference group in H2 and H3, and Prague + CZ020 is a variant.
5. H2:
   - a fixed-design stationary bootstrap with shared indices, Politis–White block lengths, and 12/24 as sensitivity;
   - no renormalisation, with the tail mass reported;
   - the profile likelihood and the (θ, μ) correlation;
   - the composition limitation;
   - Jihomoravský as robustness;
   - Little's law as a band.
6. H4:
   - RQ4 is restated for Poland only;
   - the cyclicality estimand is separate;
   - common support;
   - WCR score bootstrap, effective clusters, voivodeship robustness;
   - the §5a share is from 2005–2011.
   - Vienna's Länder subsidy panel is descriptive, if available.
7. H5:
   - the interpretation sentence is replaced;
   - GEOSTAT population replaces RÚIAN existing flats, because the 2011 dwelling grid was not found;
   - the ladder (i)–(iii) is a decomposition;
   - the confirmatory window is 2012 – 25 March 2021;
   - clustering by the 22 administrative districts, with the 57 city districts as sensitivity;
   - decision p = max(Conley, WCR); Conley at 1.5 and 3 km;
   - a 100 m distance floor, a buildable-land restriction and a line D flag.
8. The family is {H2, H4, H5}, justified in §2.
9. "Manipulation check" is renamed to relevance check, with the "uninformative" rule, and R2 is added for H2.
10. The H2 power simulation uses synthetic permitted dwellings from an AR(2) fitted to 2007–2014 (2006 is unusable),
    inside a sealed script that outputs only power tables. H4's and H5's simulations are sealed the same way.
11. The specification-curve rule is adopted verbatim.

**§3 Framing.** All four points are in §8.

**§4 Literature.** Added: Paciorek 2013; Mayer & Somerville 2000b; Glaeser & Gyourko 2005; Glaeser, Gyourko & Saiz
2008; Ball, Meen & Nygaard 2010; Cavalleri, Cournède & Özsöğüt 2019; Sinai & Waldfogel 2005; Eriksen & Rosenthal
2010; Stephens, Lux & Sunega 2015; Lux & Sunega 2014; Matznetter 2002; Lei et al. 2018; Vovk, Gammerman & Shafer
2005; Kiefer & Vogelsang 2005; Lazarus et al. 2018; Politis & White 2004. Jackknife+ and Chernozhukov et al. are no
longer cited for the rank p.

## References

- Ball, M., Meen, G., Nygaard, C. (2010): Housing supply price elasticities revisited: evidence from international,
  national, local and company data. Journal of Housing Economics 19(4), 255–268.
- Caldera, A., Johansson, Å. (2013): The price responsiveness of housing supply in OECD countries. Journal of Housing
  Economics 22(3), 231–249.
- Carter, A. V., Schnepel, K. T., Steigerwald, D. G. (2017): Asymptotic behavior of a t-test robust to cluster
  heterogeneity. Review of Economics and Statistics 99(4), 698–709.
- Cavalleri, M. C., Cournède, B., Özsöğüt, E. (2019): How responsive are housing markets in the OECD? National level
  estimates. OECD Economics Department Working Papers 1589 [verify number].
- Eriksen, M. D., Rosenthal, S. S. (2010): Crowd out effects of place-based subsidized rental housing: new evidence
  from the LIHTC program. Journal of Public Economics 94(11–12), 953–966.
- Friesenecker, M., Kazepov, Y. (2021): Housing Vienna. Social Inclusion 9(2), 77–90.
- Gelbach, J. B. (2016): When do covariates matter? Journal of Labor Economics 34(2), 509–543.
- Glaeser, E. L., Gyourko, J. (2005): Urban decline and durable housing. Journal of Political Economy 113(2),
  345–375.
- Glaeser, E. L., Gyourko, J. (2018): The economic implications of housing supply. Journal of Economic Perspectives
  32(1), 3–30.
- Glaeser, E. L., Gyourko, J., Saiz, A. (2008): Housing supply and housing bubbles. Journal of Urban Economics 64(2),
  198–217.
- Glaeser, E. L., Gyourko, J., Saks, R. (2005): Why is Manhattan so expensive? Journal of Law and Economics 48(2),
  331–369.
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
- Kiefer, N. M., Vogelsang, T. J. (2005): A new asymptotic theory for heteroskedasticity-autocorrelation robust
  tests. Econometric Theory 21(6), 1130–1164.
- Kline, P., Santos, A. (2012): A score based approach to wild bootstrap inference. Journal of Econometric Methods
  1(1), 23–41.
- Lazarus, E., Lewis, D. J., Stock, J. H., Watson, M. W. (2018): HAR inference: recommendations for practice. Journal
  of Business & Economic Statistics 36(4), 541–559.
- Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J., Wasserman, L. (2018): Distribution-free predictive inference
  for regression. Journal of the American Statistical Association 113(523), 1094–1111.
- Lux, M., Sunega, P. (2014): Public housing in the post-socialist states of Central and Eastern Europe: decline and an
  open future. Housing Studies 29(4), 501–519 [verify].
- Matznetter, W. (2002): Social housing policy in a conservative welfare state: Austria as an example. Urban Studies
  39(2), 265–282.
- Mayer, C. J., Somerville, C. T. (2000a): Residential construction: using the urban growth model to estimate housing
  supply. Journal of Urban Economics 48(1), 85–109.
- Mayer, C. J., Somerville, C. T. (2000b): Land use regulation and new construction. Regional Science and Urban
  Economics 30(6), 639–662.
- Openshaw, S. (1984): The Modifiable Areal Unit Problem. CATMOG 38.
- Paciorek, A. (2013): Supply constraints and housing market dynamics. Journal of Urban Economics 77, 11–26.
- Politis, D. N., Romano, J. P. (1994): The stationary bootstrap. Journal of the American Statistical Association
  89(428), 1303–1313.
- Politis, D. N., White, H. (2004): Automatic block-length selection for the dependent bootstrap. Econometric Reviews
  23(1), 53–70.
- Saiz, A. (2010): The geographic determinants of housing supply. Quarterly Journal of Economics 125(3), 1253–1296.
- Sinai, T., Waldfogel, J. (2005): Do low-income housing subsidies increase the occupied housing stock? Journal of
  Public Economics 89(11–12), 2137–2164.
- Stephens, M., Lux, M., Sunega, P. (2015): Post-socialist housing systems in Europe: housing welfare regimes by
  default? Housing Studies 30(8), 1210–1234.
- Topel, R., Rosen, S. (1988): Housing investment in the United States. Journal of Political Economy 96(4),
  718–740.
- Vovk, V., Gammerman, A., Shafer, G. (2005): Algorithmic Learning in a Random World. Springer.
- World Bank (2020): Doing Business 2020, economy profile Czech Republic (warehouse case; series discontinued in 2021).

## Appendix A. Raw files and scripts (SHA-256)

`docs/research/prague-housing-files.sha256`, written by `tools/praha/housing_fetch.py`, lists every raw file (70) and
every RÚIAN query result used by the design frames. The scripts at registration:

| script | SHA-256 |
|---|---|
| `housing_power.py`, sealed in `d264536`, unchanged since and as run | `800d12ccd6aea44743e879fd01bbe8e7e8c94d9a7827105a183f06f27168dc6a` |
| `housing_data.py`, as run for §5a (`4ca725c`) | `381b4b52d40e40496f2cd0fc51f3bd38874dc25fcd6ce940a1d2975d7af21144` |
| `housing_fetch.py` | `779f2f4aa3172b3fe4c1d71d376896a55085f403e2d937d7c6b0af84714efc1f` |

**Not yet downloaded:** BDL gmina-level construction periods (747069, 747070). They feed only the H6 context for H2.
The anonymous BDL API has refused connections since 28 September. They will be fetched and hashed as a dated change
before any H2 estimate is computed, or recorded as not used.

## Changes after registration

### 2026-09-29, before any outcome was joined

**Not run.** These inputs could not be obtained before outcomes were joined, so the steps that needed them were not
run:

- **H5 ladder (ii) and (iii)**, and H5 robustness 5e (Heritage Reserve), 5f (buildable land) and 5l (line D). The
  Urban Atlas 2012 needs a Copernicus login. The IPR/NPÚ regulatory layers and official line D station coordinates
  were not obtained.
- **BDL gmina construction periods (747069, 747070)**, the H6 context for H2. The BDL API refused connections on
  28 and 29 September.
- **H2 robustness 2h (the Little's-law band).** The Prague file shows "." for dwellings under construction in every
  year of the window; its note 3 says the series is no longer published after 2009. The registration assumed the
  series existed.
- **H3 robustness 3c** (ČSÚ realised-price indices), not downloaded. **H3 robustness 3f** (annual frequency): nine
  annual observations cannot carry the lag structure.
- **H5 robustness 5b** (ZSJ). No 2011 population by basic settlement unit is among the registered inputs.

**Operationalised.**

- **H1 census reference dates** come from national census documentation compiled by the author, not from Eurostat
  metadata. CZ, PL and AT are as registered. The following are [verify]:
  - DE 15 May 2022, IE 3 April 2022, HU 1 October 2022;
  - IT, SE, FI, EE and CH 31 December 2021;
  - RO 1 December 2021, BG 7 September 2021, HR 31 August 2021, PT 19 April 2021, EL 22 October 2021,
    CY 19 October 2021, LU 8 November 2021, MT 21 November 2021.

  All other countries are dated 1 January 2021.
- **H1 core region.** The member NUTS 3 with the highest population per km² in 2011. Eurostat `demo_r_d3area` was
  added to the hashed inputs for this. It gives Prague CZ010, Vienna AT130 and Warsaw PL911.
- **H1 ČSÚ-rebuilt numerator.** It uses kraj monthly completions of new family and multi-dwelling houses (`STA09B`,
  3113 + 3114, January 2011 – 26 March 2021, with March prorated), not the municipal file (`200068-25`). Czech NUTS 3
  regions are kraje, and the monthly series allows proration to census day.
- **H1 within-Czechia replication.** Prague's rank among the 14 kraje on the raw annualised ČSÚ rate, without a
  model. 14 units cannot carry the 7-parameter model.
- **H2 point estimates.** Best of 10 starting values (μ ∈ {6, 12, 24, 36, 48} × φ ∈ {2, 8}). Bootstrap draws start
  from the point estimate.
- **H3 sample.** Twelve quarterly price-change lags need price data from q − 12. Prices begin in 2015 Q1, so the
  12-lag sample is 2018 Q2 – 2024 Q4 (27 quarters, ν = round(0.4 · 27^(2/3)) = 4). The registered 35-quarter window
  applies to a 4-lag version, which is reported alongside. The fixed-b critical value is simulated (20 000 draws).
- **H4 inference.**
  - WCR is the unstudentised Kline–Santos score bootstrap.
  - The effective number of clusters uses an independence working covariance, γ_g = Σ_{i∈g} μ_i x̃_i².
  - Common support is 242 powiats (at least one non-market start in 2012–2024).
- **Robustness bootstraps use B = 999.** The confirmatory tests use B = 9 999.
- **H5 robustness.** 5j uses today's PID network (tram and rail stops), not 2012's. 5c's 500 m cells take the 2011
  density of their parent 1 km cell.
- **Hashes.** GTFS, the 2021 grid, the metro station list and `demo_r_d3area` were added to
  `prague-housing-files.sha256`.

### 2026-09-29, after estimation

- **H5 falls on Holm's threshold.** H5's decision p is 0.0252 (the WCR p; Conley's p is 0.0011), against a Holm
  threshold of 0.025 at the second step. It is **not supported**, as registered. The Monte Carlo standard error of a
  p-value near 0.025 with B = 9 999 is about 0.0016. The test was not re-run with another seed. The reverse test is
  far from 5 %, so the reading is "indeterminate".
- **H2 lag distributions.** Prague's fitted kernel is degenerate (φ̂ very large: all mass at μ̂ = 16.1 months). The
  rest's mean lag of 5.1 months is implausibly short for building a block of flats. Relevance check R2 passes as
  registered (μ̂ ≥ 3). The short lag is reported as a caveat: it suggests the rest's fit tracks common reporting
  timing as well as construction.
  - The noise ratio is 3.3 for Prague and 1.1 for the rest, so the "underpowered" wording rule is triggered. It
    applies only to a non-supported H2, and H2 is supported.
- **Relevance checks R1, R3 and R4 failed.**
  - R1: the coefficient on positive population growth is −5.4.
  - R3: the rest's cumulative response is 16.0 with a 90 % EWC interval of −22 to 54.
  - R4: β_M = 0.09, p = 0.32.

  As registered, H1, H3 and H4 are labelled **uninformative**. Their numbers are reported, and their pre-written
  statements are shown only as what the rule would have said.
- **H2 identification.** Prague's profile likelihood for μ is flat: the 95 % profile region runs from about 14 to
  38 months. It is much wider than the bootstrap interval of the contrast (8.7 to 12.6 months). The article reports
  both and states that Prague's lag is weakly identified. The contrast's sign holds in every H2 specification.
- **H2 robustness 2d and 2e.**
  - In the exponential-kernel and COVID-excluded variants, a few bootstrap draws diverge (μ̂ unbounded), and the
    bootstrap standard error explodes.
  - Their SE-based p-values (0.50) carry no information, so the percentile intervals are reported. They count as
    "not p < 0.05" in the specification curve.
- **H4 frames.** Robustness variants contain powiat-by-group cells in which every count is zero, and these broke the
  restricted Poisson fit. They are dropped in all frames (`h4_frame`), because PPML ignores them anyway.
  - The main frame has none, so the main H4 estimates are unchanged.
  - The main estimates were produced before this line was added. The main frame was checked to contain zero such
    cells.
