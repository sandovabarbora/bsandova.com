# One city, 57 budgets: research design (Part 3, extended)

**Status: draft for review.** Written before any budget figure outside Part 3's published 2022–2024 actuals has been
looked at, and before any model below has been estimated. The raw files in §4 have been downloaded by
`tools/praha/districts_data.py`. Only their structure has been inspected: columns, codes, coverage and counts of
units (§0). After review this file becomes the registered version. Deviations will then be listed, dated, under
"Changes after registration".

## 0. What has already been seen

**Part 3 (published, `texts/prague-districts.html`, `assets/praha/districts.json`).** MONITOR actuals ("reality")
for 2022, 2023 and 2024 for all 57 districts, divided by residents at 31 December of each year and averaged.

- Per district, public in `districts.json`:
  - spending per resident (three-year mean and each year);
  - spending shares of eight function groups and of capital outlays;
  - income shares and income per resident split into taxes, non-tax and class 4 "transfers";
  - the 2022 district-assembly lists with votes and seats.
- Headline numbers:
  - the 13 districts over 40 000 residents spend 8 346–17 604 CZK per resident, and Praha 1 spends 35 320 (35 602,
    34 564 and 35 794 in the three years);
  - the median district spends 14 669, and the JSON range is 7 763–73 020;
  - Praha-Lysolaje spent 119 531 per resident in 2022 and 27 118 in 2024, with 73 % of its three-year spending
    capital.
- Income:
  - class 4 transfers are 82 % of the median district's income (66–92 %);
  - taxes and fees per resident are 9 676 CZK in Praha 1 and 1 363 in Praha 4, and transfers per resident are
    23 570 and 7 009;
  - Praha 1's overnight-stay fee was 82.9 m CZK in 2024 (47.5 m in 2022), and its public-space fee 114.2 m (97.3 m).
- Spending shares in the 13 large districts (medians):
  - town hall (section 61) 29 % (24–38 %);
  - education 32 % (18–42 %);
  - social 7.5 % (2–17 %);
  - capital 28 % (14–48 %).
- Figure 1 plots spending per resident against population for all 57, so **the cross-sectional shape of size
  against total spending, 2022–2024, has been seen**. Figure 2 shows income per resident by type for the large
  districts.

**What Part 3 did not look at.** None of the following has been seen:

- 2025;
- the approved (`approved`), amended (`afterChanges`) or final (`finalBudget`) columns for any year;
- class 4 split into its items;
- the financing class (8) or the balance;
- the 2014 and 2018 elections;
- any partisan alignment;
- population by age;
- area.

Class 4 *actuals* for 2022–2024, which contain the actuals of 4137 and 4251, were seen only as totals.

**Seen while drafting this design (no outcome statistic computed).**

- **Coverage (the finding that shaped this design).** The MONITOR web API answers every district-year for 2015–2025,
  but **all 57 district reports for 2015–2021 are empty (399 of 399 district-years have zero outgoings)**. Only
  2022–2025 carry figures. The city's own reports (IČO 00064581) are filled in every year. The bulk FIN 2-12 M
  extract for 2019 has none of the 57 district IČOs (the city is present), as Part 3 found for 2024. **Open
  budget data for the districts therefore start in 2022.**
- **MONITOR JSON structure.** Every node carries `approved`, `afterChanges`, `finalBudget`, `reality` and four
  `sankey*` twins.
  - The class 4 items that occur across all district-years (names only, no amounts) include:
    - state transfers 4111, 4112, 4113, 4116, 4118 and 4119;
    - 4121 (from municipalities) and 4122 (from regions);
    - 4131 and 4132 (transfers from the district's own funds);
    - **4137** (non-investment transfers between statutory cities including Prague and their districts);
    - 4140;
    - foreign 4151, 4152 and 4155;
    - 4171;
    - investment 4213, 4216, 4218, 4221 and 4232;
    - **4251** (investment transfers between statutory cities … and their districts).
  - Consequence for Part 3: its class 4 "transfers from the city and the state" includes 4131/4132/4140, which are
    transfers from a district's own funds, not grants. Their size has not been computed (open question Q1).
- **Praha 8's explanatory memo to its 2022 draft budget** (m.praha8.cz, `Rozpocet-2022-duvodova-zprava.pdf`) was
  read for the allocation rule (§1). It also gives **one district-year of approved amounts**:
  - "finanční vztah" 357 379 thousand CZK;
  - state-administration contribution 88 527 thousand;
  - property tax (budgeted) 118 200 thousand.
- **Web-search snippets** showed further approved or city-level figures [unconfirmed at source]:
  - Praha 6 "dotační vztah" over 500 m CZK (2024);
  - Praha 9 "finanční vztah" 312 247.1 thousand (2024);
  - an unidentified line "the city receives 1 300 382.7 thousand, gives the districts 885 960.6 thousand" (2024);
  - for 2019, "Prague received 1 075 508.6 thousand CZK from the state and provided 905 123 thousand to districts",
    attributed to a closing-account table "Tabulka č. 9 – Finanční vztahy k MČ" (xls). The table itself has not
    been found or opened.
- **Election files for 2014, 2018 and 2022.**
  - Each holds 58 Prague assemblies (57 districts + ZHMP), with list composition (`SLOZENI`), each candidate's
    nominating party and membership (`NSTRANA`, `PSTRANA`) and seats. Seats have not been tabulated by party.
  - Election dates in the Prague rows show six repeat or new district elections (§4).
- **Other covariates.** RÚIAN has 57 district polygons and 22 administrative districts with an area attribute. ČSÚ
  has age by five-year group for all 57 districts, 2011–2025, and residents for 1991–2025.

## 1. Background: how a Prague district is financed

- **Legal frame.**
  - Prague is one municipality and one region (Act 131/2000 Coll. on the capital city of Prague).
  - Under the budgetary allocation of taxes (rozpočtové určení daní, Act 243/2000 Coll.), shared taxes go to the
    city, not to the districts.
  - The city's Statute (Obecně závazná vyhláška č. 55/2000 Sb. hl. m. Prahy, as amended) says which revenues are
    the districts' own and how the city shares its money with them.
- **Districts' own revenue.**
  - Property tax: its full yield goes to the district (Praha's statement reported in *Moderní obec*, 2019). From
    tax year 2020 the city let districts set a property-tax coefficient on their territory [verify which
    coefficient, and uptake].
  - Local fees.
  - Rents and sales, often through a business account that feeds the budget as 4131.
- **City to district, rule-based (item 4137, set in the city budget each December).**
  - **"Finanční vztah"**: a formula share of the city's expected shared-tax yield. Praha 8's 2022 memo gives the
    weights "as in 2021":
    - residents 30 %;
    - area 10 %;
    - kindergarten and primary pupils 30 %;
    - green space in the district's care 20 %;
    - roads in the district's care 10 %.

    Whether the weights changed in 2023–2025 is open [verify, Q3].
  - **State-administration contribution**: a per-100-residents rate plus a component for delegated agendas, paid by
    the state through the city (Praha 8 memo).
- **City to district, discretionary.** During the year the city council (RHMP) and assembly (ZHMP) grant targeted
  non-investment (4137) and investment (4251) transfers. They appear as budget amendments in the district's
  accounts. These are the margin on which partisan allocation can operate. State pass-throughs also arrive in-year
  under 4137, for example election costs and refugee-related grants in 2022–2023 [verify].
- **Tiers.** The 22 numbered districts (Praha 1–22) are seats of administrative districts. They carry extended
  delegated administration for their smaller neighbours; the 35 others do not.
- **City coalitions.**
  - 26 Nov 2014 – Nov 2018: ANO, ČSSD and the Trojkoalice (Greens, KDU-ČSL, STAN). The coalition broke in October
    2015 and was renewed on 28 April 2016.
  - 15 Nov 2018 – 16 Feb 2023: Pirates, Praha Sobě, Spojené síly pro Prahu (TOP 09, STAN, KDU-ČSL and others
    [verify]). Caretaker after the 23–24 Sept 2022 election.
  - 16 Feb 2023 – present: SPOLU (ODS, TOP 09, KDU-ČSL [verify KDU-ČSL on the 2022 Prague SPOLU list]), Pirates,
    STAN.
  - Sources: cs.wikipedia "Rada hlavního města Prahy"; Český rozhlas and Deník reporting of Nov 2015 and Apr 2016.
    All dates are [verify] against ZHMP resolutions before coding.

## 2. Research questions and estimands

The budget panel is **57 districts × 2022–2025 = 228 district-years**. In that window the city coalition changes
once, on 16 Feb 2023, and the district assemblies once, at the September 2022 election. Both changes fall between
budget year 2022 and budget year 2023. Every change in partisan alignment therefore happens at **one date**. That
gives a two-group, one-switch difference-in-differences with one pre-year (2022) and three post-years (2023–2025).

- **RQ1 (partisan alignment).** Do districts whose assembly majority belongs to the city's governing parties receive
  more discretionary, in-year city transfers per resident?
  - Estimand: the difference-in-differences contrast in in-year transfers per resident between districts that
    became aligned in 2023 and those that did not, and symmetrically for districts that stopped being aligned.
    This is pooled in a two-way fixed-effects model, which with a single switch date has no forbidden comparisons.
  - Reported by direction of switch.
- **RQ2 (what kind of money).** Is any alignment premium concentrated in investment transfers (4251), the visible,
  ribbon-cutting kind, rather than non-investment transfers (4137)?
  - Estimand: the difference between the alignment effects on the two components, in CZK per resident.
- **RQ3 (budget execution and capacity).** Do smaller districts execute a smaller share of their amended capital
  budgets?
  - Estimand: the conditional association between log population and the capital execution rate (actual /
    amended), within tier and year. Descriptive.
- **RQ4 (planned deficits, realised surpluses).** Do districts approve budgets that plan to draw on reserves, and
  then close the year better than planned?
  - Estimand: the mean, over districts, of (actual balance − approved balance) per resident, 2022–2025. This is the
    gap between the deficit a district tells its assembly it will run and what it runs.
  - It is the local form of the reserve accumulation that the Czech municipal sector is known for.

**Why these, and not a re-run.** Part 3 described levels.

- RQ1 and RQ2 need the approved / actual split of 4137 and 4251, and alignment. Neither was in Part 3.
- RQ3 and RQ4 need the approved and amended columns, which Part 3 never read.
- Size economies in total spending were shown in Part 3 (figure 1) and are not tested (E1).

**Questions this panel cannot answer, and why they are not registered.**

- **Pre-election pork (a political budget cycle in transfers).** 2025 is the only pre-election year in the panel,
  so there is one window and no replication. The question moves to the extension (§2a).
- **Flypaper / pass-through of formula money.** Identification needs the formula pot to move across many years.
  2022–2025 gives three usable shocks with year effects. The question is described in E3, and moves to the
  extension if district spending before 2022 can be found.

**Literature.**

- Alignment:
  - Solé-Ollé and Sorribas-Navarro (2008), Spain, difference-in-differences;
  - Brollo and Nannicini (2012), Brazil, close races;
  - Bracco et al. (2015), Italy;
  - Arulampalam et al. (2009), India.
- Composition of politically motivated spending: Drazen and Eslava (2010); Veiga and Veiga (2007).
- Flypaper: Hines and Thaler (1995); Knight (2002); Gordon (2004); Dahlberg et al. (2008); Inman (2008).
- Fiscal forecasting and strategic budgeting: Goeminne, Geys and Smolders (2008).
- Size: Blom-Hansen et al. (2016).
- Czech evidence on partisan alignment in regional or ministerial grants: [verify, locate before registration].
  We know of no study of Prague's intra-city transfers [verify].

### 2a. Conditional extension to 2015–2021 (decided before any outcome is seen)

The city's closing accounts are reported to contain, per year, a table of financial relationships with each
district: "Tabulka č. 9 – Finanční vztahy k MČ z rozpočtu hl. m. Prahy" (§0) [verify existence for 2015–2021, and
whether it separates the formula transfer, the state-administration contribution and targeted grants].

- **If** such tables are found for at least 2015–2021, in a machine-readable or cleanly extractable form, with
  targeted grants shown per district, then **before registration**:
  - H1 and H2 are re-specified on the grantor-side series 2015–2025 (627 district-years, alignment changes in
    2018/19 and 2023);
  - a pre-election hypothesis **H5** (alignment × {2017, 2018, 2021, 2022, 2025}) is added to the family;
  - the event-study pre-trends in §5 become available.
- **If not**, the design stays on 2022–2025 as written.
- The switch is decided on availability alone, and recorded under Changes after registration with the date.

## 3. Hypotheses, tests and decision rules

**One one-sided p-value per hypothesis; Holm step-down at family-wise α = 0.05 over H1, H2, H3, H4** (and H5 if
§2a triggers). Every hypothesis is reported whichever way it falls. "Not supported" and "underpowered" are written
as such.

- **H1 (alignment premium).** β_A > 0 in M1: in-year city transfers D per resident, on alignment A, with district
  and year effects.
  - H0: β_A ≤ 0.
  - p-value: **randomization inference** over the 2023–2025 alignment assignment. The observed 2023 alignment
    vector is permuted across districts within tier, keeping the number of aligned districts in each tier;
    9 999 draws; the statistic is the M1 t-statistic.
  - The wild cluster restricted bootstrap (Webb, B = 9 999) and CR2 are reported alongside.
  - RI is primary because all switches share one date. The number of switchers may be small, and wild bootstrap
    tests are unreliable with few treated clusters (MacKinnon and Webb 2018).
  - *Supported* if p passes its Holm threshold.
- **H2 (investment, not upkeep).** β_A^cap − β_A^cur > 0, the effects of A on D_cap (4251) and D_cur (4137) per
  resident, estimated jointly (stacked).
  - One-sided RI on the difference, as in H1.
  - H2 is tested whatever H1's result, because "no premium overall, but a shift toward investment" is a
    substantive outcome.
- **H3 (capacity).** β_N > 0 on log population in M3 (tier and year effects): the capital execution rate rises
  with size.
  - One-sided CR2 t-test, Satterthwaite degrees of freedom, clustered by district. WCR bootstrap alongside.
- **H4 (planned deficits, realised surpluses).** μ > 0, where μ is the mean over the 57 districts of the district's
  2022–2025 average of (actual balance − approved balance) per resident, balance = incomes − outgoings.
  - One-sided t-test on 57 district means. A sign test and a population-weighted mean are reported alongside.
  - One observation per district, so there is no within-district dependence.

**Exploratory, outside the family (no confirmatory test).**

- **E1 (size economies of the town hall).** Elasticity of section-61 spending per resident with respect to
  population, within tier.
  - Part 3 showed the 2022–2024 cross-section of total spending and the town-hall share. **Not an independent
    test.**
  - Council remuneration is set by population band (Government Decree 318/2017 Coll.). Paragraph 6112 is reported
    apart.
- **E2 (dual mandates).** Whether districts with a city-assembly member on their own assembly (name + age match
  across the ZHMP and district candidate files) receive more in-year transfers. A mechanism check for H1.
- **E3 (spend or save, and does the label matter).** The one-year spending response to rule-based transfers
  (approved 4137, instrumented by 2022 exposure share × leave-one-out pot, t = 2023–2025).
  - It is compared with the response to the 2024 property-tax windfall: Act 349/2023 Coll. raised property-tax
    rates from 2024 [verify rates]. Exposure = 2023 property tax per resident.
  - With three years and one reform, both are reported as estimates with intervals, not tests.
- **E4 (forecast bias by source).** Actual / approved for own-source revenue (classes 1 + 2, without 4131), for
  4137 and for 4251, by year. It is associated with assembly fragmentation (effective number of lists).

## 4. Data and measures

**Budgets.** MONITOR web API (Ministry of Finance), FIN 2-12 M at December, **2022–2025**, for the 57 districts and
the city (IČO 00064581):

- totals (`rozpocet`);
- incomes by type (`druhovy`, `cast=p`);
- outgoings by type (`druhovy`, `cast=v`);
- outgoings by function (`odvetvovy`, `cast=v`).

Column semantics: `approved` = schválený rozpočet, `afterChanges` = rozpočet po změnách, `reality` = skutečnost.
`finalBudget` is to be confirmed from MONITOR documentation [verify]. The 2015–2021 files were downloaded and are
empty (§0).

Measures, per resident, CZK nominal (year effects absorb prices):

- **Rule-based transfer R_it** = `approved` of 4137. This assumes the approved budget contains the December city
  allocation (formula + state administration) and nothing else.
  - Checked against the documented approved amounts (§0) and, if found, the city's tables (§2a).
  - Districts that approve their budget before the city's are flagged from resolution dates if obtainable
    [verify]; otherwise a limitation.
- **In-year city transfers D_it** = (`reality` − `approved`) of 4137 + 4251; D_cur (4137) and D_cap (4251) apart.
  Primary outcome for H1 and H2.
- **Capital execution rate E_it** = `reality` / `afterChanges` of class 6 outgoings (H3). Undefined when
  `afterChanges` = 0; those district-years are dropped and counted.
- **Balance gap G_it** = (incomes − outgoings)^reality − (incomes − outgoings)^approved, from the totals node (H4).
  - Totals are consolidated as in Part 3.
  - Transfers from own funds (4131, 4132, 4140) move money between a district's accounts. Whether they are removed
    by MONITOR's consolidation in the totals node is to be established from the item structure before estimation
    [verify, Q1]. If not, they are subtracted from incomes on both sides.
- **4131, 4132 and 4140 are excluded from "transfers" everywhere in this study.**

**Population.** ČSÚ Prague office, residents at 31 December (`CR_L3_MC.xlsx`). The denominator for year t is 31
December of t − 1, the stock the December allocation can know; robustness uses t. Age shares (0–14, 65+) come from
`1_PHA_VEK_obyv_mc.xlsx`, 2011–2025.

**Area and tier.** RÚIAN layer 8 (district polygons, `st_area`) and layer 10 (22 administrative districts).
Tier = seat of an administrative district (Praha 1–22).

**Elections and alignment.** volby.gov.cz open data: lists (`kvros`), candidates (`kvrk`), party code lists.

- Regular elections: first polling days 10 Oct 2014, 5 Oct 2018 and 23 Sept 2022 (`DATUMVOLEB`).
- The files also hold **repeat or new district elections**, which change the assembly mid-term:
  - Praha 13, 21 Nov 2014;
  - Praha-Koloděje, 13 Jun 2015;
  - Praha-Nedvězí, 5 Nov 2016 and 14 Sep 2019;
  - Praha 4 and Praha 8, 30 Nov 2018.

  None falls in 2022–2025. Whether each was a repeat or a new election is [verify].
- **City coalition set C_t.** Parties of the city council in office on **30 June of year t** (§1): Pirates, Praha
  Sobě, TOP 09, STAN, KDU-ČSL (+ others in Spojené síly [verify]) for 2022; ODS, TOP 09, KDU-ČSL, Pirates, STAN for
  2023–2025.
- **District assembly** in force on 30 June of t: the 2018 election (or its repeat) for 2022; the 2022 election for
  2023–2025.
- **Aligned seat share a_it.** The share of assembly seats won by candidates whose nominating party (`NSTRANA`) or
  membership (`PSTRANA`) is in C_t.
  - Independents nominated by a coalition party count as aligned.
  - Multi-party lists (e.g. SPOLU 2022) are coded by each elected candidate's `NSTRANA` and the list's `SLOZENI`.
  - Local lists do not count.
  - The party-code table is committed before estimation.
- **A_it = 1[a_it > 0.5]** (primary); a_it continuous (robustness).
- **Mayor's party** in office on 30 June of each year, 57 × 4, hand-coded from district websites and resolutions
  **before any outcome is joined**, sources kept (secondary; Q4).
- The 2014 election files are downloaded for the §2a extension only.

**Units.**

- 57 × 4 = 228 district-years for H1, H2 and H3.
- 57 district means for H4.

Constant district set: all 57 IČOs answer the API for 2022–2025 [verify validity dates in the MONITOR register].

## 5. Models and inference

Let i be the district, t ∈ {2022, …, 2025}, α_i and γ_t fixed effects, and X_it = (share 0–14, share 65+, log
population), all slow-moving. X_it is included as precision control, and results are reported with and without it.

- **M1 (H1):** D_it = α_i + γ_t + β_A·A_it + X_it'δ + ε_it. Unweighted: the unit is one allocation decision per
  district-year.
- **M2 (H2):** M1 stacked for D_cap and D_cur, with component-specific α, γ and β.
  H0: β_A^cap − β_A^cur ≤ 0.
- **M3 (H3):** E_it = γ_t + β_N·log N_it + τ·tier_i + ε_it, pooled, clustered by district. Robustness: district
  means (57 observations, HC2).
- **H4:** the one-sample t-test on district means (above).

**Inference, small-sample.** G = 57 clusters, T = 4.

- **H1 and H2: randomization inference is primary** (above). Its sharp null (no effect for any district) is
  stronger than H0. It is valid in finite samples under the permutation design, which treats the 2023 alignment
  as if assigned at random within tier, conditional on the number aligned. That assumption is the same one the
  difference-in-differences needs, stated as a design.
- Alongside:
  - the WCR bootstrap (Webb six-point, B = 9 999, restricted; Roodman et al. 2019);
  - CR2 with Pustejovsky–Tipton degrees of freedom;
  - Conley–Taber intervals;
  - the effective number of clusters;
  - the number of switchers in each direction.
- **H3: CR2** with Satterthwaite degrees of freedom is primary (between-district variation, 57 clusters, many
  "treated"). The WCR bootstrap is reported alongside.
- **What can realistically be learned.**
  - One pre-year means **no pre-trend test**. The parallel-trends assumption for H1 is untestable within
    2022–2025, and is stated as such.
  - The difference-in-differences compares switchers and stayers across one regime change. That change also
    replaced the district assemblies (the 2022 elections), so a new district government's lobbying skill is
    confounded with alignment for districts whose majority changed. Districts whose alignment changed **only**
    because the city coalition changed (same district majority, different city partners) isolate alignment from
    district turnover, and are reported as a subgroup.
  - STAN and KDU-ČSL sit in both coalitions, so districts run by them are aligned throughout and serve only as
    controls.
  - A close-election regression discontinuity (Brollo and Nannicini) is not feasible with 57 district elections.
  - H3 is a between-district association with 57 units, 22 of them of a different tier; the population range
    (about 380 to 136 000) is its main source of power.

## 6. Design-stage checks (covariates only; run before any outcome enters the model frame)

Script: `tools/praha/districts_power.py`, output committed as `docs/research/prague-districts-power.json`. It reads
no `reality` value of 4137, 4251, class 6 or totals, and no `approved` value of 4251, class 6 or totals.

1. **Alignment table.**
   - A_it and a_it for all district-years;
   - the numbers aligned in 2022 and 2023, by tier;
   - **switchers by direction**;
   - switchers whose district majority did not change (the "city-only" subgroup).
2. **Power for H1 and H2 from the design alone.** The minimum detectable effect at 80 % power, one-sided 5 %, of
   the RI test, in **residual-SD units**. Computed by simulating placebo outcomes: district effect + AR(1) error,
   ρ ∈ {0, 0.3, 0.6}, with a constant effect added to switchers, and running the full RI pipeline (1 000
   simulations × 999 permutations).
   - Pre-committed consequences, applied separately to H1 and H2 at ρ = 0.3:
     - MDE > 0.5 SD: the hypothesis is reported as "underpowered" if not supported;
     - MDE > 1 SD, or fewer than 5 switchers: this is recorded as a change before estimation, and the article
       states in its first section that H1 cannot detect effects of the size found in the literature. The
       literature's effects are converted to SD units only after estimation, from the observed residual SD, and
       that conversion is reported as post hoc.
3. **H3 design.**
   - Log population by tier.
   - The VIF of log population and tier.
   - The number of district-years with capital `afterChanges` = 0, dropped. This is a count of undefined
     denominators, not a value.
   - The MDE of β_N for a unit-variance outcome.
4. **H4 design.** The MDE of μ in SD units for n = 57. The number of districts whose MONITOR totals node carries
   `approved` (presence only).
5. **Validation of R.** Approved 4137 (a covariate; no hypothesis tests it) against the documented approved amounts
   (§0), and against the city tables if §2a finds them. This reveals approved 4137, which is part of D's
   definition, but not D.
6. **§2a search.** The outcome of the search for the city's per-district tables, with URLs, is recorded here,
   whichever way it goes.

## 7. Robustness checks (reported, not in the family)

1. Population-weighted estimates.
2. Continuous a_it instead of A_it.
3. Mayor's party alignment instead of seat majority.
4. D_cap by Poisson PML (a semi-elasticity), since D_cap ≥ 0 if approved 4251 is 0 [verify at design stage, by
   presence count only].
5. `afterChanges` − `approved` instead of `reality` − `approved`.
6. Without Praha 1, and without districts under 1 000 residents.
7. Without 2022, the refugee year: the contrast becomes 2023 vs 2024–2025, identified from nothing. This check
   therefore reduces to the "city-only" subgroup and the direction split.
8. Leave-one-district-out: the largest change in each confirmatory coefficient.
9. **Placebo outcome:** approved 4137 on A_it. It should be zero if the formula is followed. A non-zero value is a
   finding about the formula, reported, not tested.
10. **Placebo assignment:** A_it defined with the 2014–2018 city coalition (ANO, ČSSD, Greens, KDU-ČSL, STAN).
    It should show no effect.
11. H3: fractional logit; district means; controlling for D_cap as a share of amended capital budget (late grants
    cannot be spent), marked as a post-treatment control.
12. H4: without 4131/4132/4140 on both sides; by year; population-weighted.
13. **Specification curve** over:
    - {weighted, unweighted};
    - {A, a, mayor};
    - {reality, afterChanges};
    - {all, without Praha 1, without < 1 000};
    - {with, without X};
    - {RI, WCR, CR2}.

    The share of specifications supporting each confirmatory conclusion is reported.

## 8. Limitations (stated in the article)

- **Four years.** Open district budgets start in 2022. One regime change, one pre-year, no pre-trend test. If §2a
  fails, H1 is a before/after comparison around a single event, and its causal reading rests on an untestable
  assumption.
- **Few units.** 57 districts. Null results will mostly be uninformative; the intervals are the result.
- **Alignment is not assigned at random.** The 2022 elections changed district governments and alignment together.
  The "city-only" subgroup helps; it is small.
- **What in-year transfers contain.** D includes state pass-throughs routed through the city (elections, the 2022
  refugee wave). Year effects absorb them only if they are proportional to population.
- **The city's own spending in a district is invisible.** The city can favour a district by building there itself
  or through its companies. That is not in the district's accounts, so H1 measures one channel of favouritism.
- **Approved budgets and timing.** If a district approves its budget before the city's allocation is known, or
  budgets expected grants, `approved` mismeasures R and D.
- **Accounting.** Classification differs across districts: education was coded 31 or 32 in Part 3. Consolidation
  of own-fund transfers is to be established (Q1).
- **H3 and H4 are descriptive.** Size, tier, suburban location and project mix travel together (H3). A balance gap
  can be prudence, strategy or delayed projects, and the design does not separate them (H4).

## 9. Deliverables

- `tools/praha/districts_data.py`: raw data (written; downloads and a structure report only).
- `tools/praha/districts_frame.py`: alignment coding, measures, analysis frame.
- `tools/praha/districts_power.py`: §6.
- `tools/praha/districts_extended.py`: H1–H4, E1–E4.
- `tools/praha/districts_robust.py`: §7.
- `assets/praha/districts_extended.json`.
- `texts/prague-districts-study.html`, the long version.
- This file, and `docs/research/prague-districts-files.sha256` at registration.

## Open questions for the referees

- **Q0 (scope).** Open district budgets exist only for 2022–2025. Is a one-switch, one-pre-year design for H1
  worth registering? Or should registration wait for the §2a search (city closing-account tables 2015–2021) and
  register the 2015–2025 grantor-side design only?
- **Q1.** Part 3 counted 4131/4132/4140 (transfers from a district's own funds) as "transfers from the city and the
  state". Should Part 3 be corrected now? Is recomputing its class 4 share without them outcome-revealing for this
  design? It reveals class 4 actual totals by item, and so the actuals of 4137 and 4251, which are half of D.
- **Q2.** Is `reality` − `approved` of 4137 + 4251 a defensible measure of discretionary city transfers, given
  in-year state pass-throughs and districts that budget expected grants?
- **Q3.** Were the formula weights (30/10/30/20/10) constant over 2022–2025? This matters for the placebo outcome
  (§7.9) and for E3.
- **Q4.** Seat-majority alignment (mechanical, open data) or the mayor's party (hand-coded, closer to who governs)
  as primary?
- **Q5.** RI over the 2023 assignment within tier as the primary test for H1 and H2. Is the permutation design
  (fixed number aligned per tier) the right one? Or should assignment be permuted within strata of 2022 alignment?
- **Q6.** H3's direction. Is "smaller districts execute less" the right one-sided alternative? Large districts run
  larger, more complex projects, which argues the other way.
- **Q7.** H4 is likely to be supported. Is it informative enough to hold a place in the family? Or should it be
  replaced by its fragmentation version (E4), which has a less certain sign?
- **Q8.** Should the property-tax windfall comparison (E3) be promoted to a registered test, despite two
  post-reform years?

## References

- Arulampalam, W., Dasgupta, S., Dhillon, A., Dutta, B. (2009): Electoral goals and center-state transfers. Journal
  of Development Economics 88(1), 103–119.
- Blom-Hansen, J., Houlberg, K., Serritzlew, S., Treisman, D. (2016): Jurisdiction size and local government
  policy expenditure. American Political Science Review 110(4), 812–831.
- Bracco, E., Lockwood, B., Porcelli, F., Redoano, M. (2015): Intergovernmental grants as signals and the alignment
  effect. Journal of Public Economics 123, 78–91.
- Brollo, F., Nannicini, T. (2012): Tying your enemy's hands in close races. American Political Science Review
  106(4), 742–761.
- Conley, T. G., Taber, C. R. (2011): Inference with "difference in differences" with a small number of policy
  changes. Review of Economics and Statistics 93(1), 113–125.
- Dahlberg, M., Mörk, E., Rattsø, J., Ågren, H. (2008): Using a discontinuous grant rule to identify the effect of
  grants on local taxes and spending. Journal of Public Economics 92(12), 2320–2335.
- Drazen, A., Eslava, M. (2010): Electoral manipulation via voter-friendly spending. Journal of Development
  Economics 92(1), 39–52.
- Goeminne, S., Geys, B., Smolders, C. (2008): Political fragmentation and projected tax revenues: evidence from
  Flemish municipalities. International Tax and Public Finance 15(3), 297–315 [verify].
- Gordon, N. (2004): Do federal grants boost school spending? Evidence from Title I. Journal of Public Economics
  88(9–10), 1771–1792.
- Hines, J. R., Thaler, R. H. (1995): Anomalies: the flypaper effect. Journal of Economic Perspectives 9(4),
  217–226.
- Holm, S. (1979): A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics
  6(2), 65–70.
- Inman, R. P. (2008): The flypaper effect. NBER Working Paper 14579.
- Knight, B. (2002): Endogenous federal grants and crowd-out of state government spending. American Economic
  Review 92(1), 71–92.
- MacKinnon, J. G., Webb, M. D. (2018): The wild bootstrap for few (treated) clusters. Econometrics Journal 21(2),
  114–135.
- Pustejovsky, J. E., Tipton, E. (2018): Small-sample methods for cluster-robust variance estimation and hypothesis
  testing in fixed effects models. Journal of Business & Economic Statistics 36(4), 672–683.
- Roodman, D., Nielsen, M. Ø., MacKinnon, J. G., Webb, M. D. (2019): Fast and wild: bootstrap inference in Stata
  using boottest. Stata Journal 19(1), 4–60.
- Solé-Ollé, A., Sorribas-Navarro, P. (2008): The effects of partisan alignment on the allocation of
  intergovernmental transfers. Journal of Public Economics 92(12), 2302–2319.
- Veiga, L. G., Veiga, F. J. (2007): Political business cycles at the municipal level. Public Choice 131(1–2),
  45–64.
- Czech law: Act 131/2000 Coll. (capital city of Prague); Act 243/2000 Coll. (budgetary allocation of taxes);
  Statute of Prague, OZV 55/2000 Sb. hl. m. Prahy; Government Decree 318/2017 Coll. (councillors' remuneration);
  Act 349/2023 Coll. (2024 consolidation package, property tax) [verify].
- Moderní obec (2019): Hlavní město Praha nechá jednotlivé městské části na jejich územích rozhodnout o dani z
  nemovitých věcí.
- MČ Praha 8 (2021): Důvodová zpráva, návrh rozpočtu na rok 2022.

## Appendix A. Raw files (to be hashed at registration)

`tools/data/praha3x/` (gitignored):

- `api/{ico}_{year}_{tot,prij,dru,odv}.json`: 57 districts + the city, 2015–2025. The district files for 2015–2021
  are empty.
- `finm/2019_12.zip`: the bulk extract, kept as coverage evidence.
- `mc_ico.csv`, `mc_pop.xlsx`, `mc_age.xlsx`.
- `ruian_momc.json`, `ruian_spravni.json`.
- `kv2014/`, `kv2018/`, `kv2022/`: reg, data and code-list archives.
- `raw_report.json`: the structure report.

## Changes after registration

(none yet)
