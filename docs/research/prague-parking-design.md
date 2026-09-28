# Prague's kerb, measured: research design (Part 6, parking)

**Status: registered 29 Sep 2026.** This is version 2, revised against three referee reports (transport economics, statistics,
data audit; consolidated in `docs/research/prague-parking-referees.md`). It is committed before any vehicle length
from the register is read, and before any outcome below is estimated.

At registration, the design-stage checks in §5 have been run. They use constants, stall-type geometry, counts and
missingness only. Their results are in §5 and in `docs/research/prague-parking-ds.json`. The raw files and their
hashes are in `docs/research/prague-parking-files.sha256` (Appendix A). Deviations are listed, dated, in "Changes
after registration".

In the article this is a **registered analysis plan**, not a "pre-registered study". The direction of H1, H3 and H4,
and the size of H1 and H4, are known from Parts I–III (§0). Unverified claims are marked **[verify]**. None of them
enters a confirmatory test.

## 0. What has already been seen

The three published texts share one model (repo `~/Downloads/parking/`, `METODIKA.md`, 30 tests):

- On a parallel kerb, capacity = kerb length ÷ pitch, and pitch = car length L + gap g.
- The kerb is held fixed and anchored on today's stall count N₂₀₂₅. The 2012 count is then N₂₀₂₅ · (L₂₀₂₅ + g) /
  (L₂₀₁₂ + g), on the parallel share s.
- Fleet length is a survival-weighted mean of new-car cohorts, calibrated to the mean age of the Czech fleet.

**Part I (published 8 Sep 2026, T&E EU top-100 new-car series).**

- Supply: 16 874 polygons, 168 456 stalls (RES 103 641, MIX 63 697, VIS 1 118). That is +1.37 % against TSK's
  166 180 of December 2024.
- Area: net 2 272 593 m², 13.49 m² per stall; by district, 13.7–16.0 m² per stall.
- Fleet:
  - mean age 13.62 → 16.68 years;
  - new car +17.0 cm;
  - fleet car 4.050 → 4.167 m;
  - width +5.8 cm.
- g = 0.82 m and s = 0.68.
- Loss 2012→2025: **2 745 stalls (1.60 %)**. Other variants:
  - all parallel 4 036;
  - new-car lengths 3 871;
  - discrete model 2 953 (1.72 %);
  - area model 5 627 / 10 846;
  - the whole grid 1 946–8 058 (1.14–4.57 %);
  - by gap, 2 938 (0.5 m) to 2 647 (1.0 m).
- Width encroachment 27 598 m². Mirrors 2.02 m against a 2.00 m bay. T&E's 8.5–14 % could not be reproduced: its own
  parameters give 3.35–3.95 %.
- 89 Kč / m² / year.

**Part II (published 15 Sep 2026, EEA, M1 only).**

- 2 501 048 registrations 2010–2022. Registrations per year:

  | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | 164 618 | 169 259 | 169 576 | 161 155 | 174 562 | 221 289 | 214 408 | 213 542 | 229 002 | 233 603 | 186 262 | 189 449 | 174 323 |

- Wheelbase 2 616 → 2 684 mm (+68 mm, 6.0 mm a year). At r = 0.618 that is +11.0 cm (9.7–13.1). T&E, same years:
  +11.0 cm.
- Mass 1 366 → 1 461 kg. Track 1 560 → 1 554 mm.
- Fleet car 4.098 → 4.195 m. Loss **2 263 (1.33 %), band 1 988–2 710**.
- Part II's implied 2022→2025 new-car change: about +3.0 cm (1.0 cm a year). T&E's: +6.0 cm.

**Part III (published 23 Sep 2026).**

- 174 stalls a year (153–208).
- Praha 7: 280 new permits a year (Deník N).
- Perpendicular parking uses 2.5 m of kerb per car against 5.0 m parallel.
- Fabia against Kodiaq: +12 % kerb. 244 against 218 Kč per kerb metre. A length-proportional price of 1 180 / 1 320 Kč.

**Seen while drafting v1 (28 Sep 2026).**

- The TSK permit price list: core areas 1 200 Kč; outer sub-areas 600 Kč; 65+/ZTP 360 (180); second car 7 000
  (3 500); third car 24 000–36 000; abonent 7 000; zero-emission −50 % from 2026.
- OZV 16/2025 §2(1)(k): 10 Kč / m² / day.
- The 2012 mean age (13.62) is extrapolated, not published.
- The segment layer has no date fields.
- TSK Ročenka 2024 §10.1 was read with its digits masked.
- The EL-plate series on data.praha.eu: 2017 1 124 … 2022 9 496.
- The RSV export's header.
- Other cities' tariffs.

**Seen during review (reported by the referees, 28 Sep 2026).**

- M1G, which Part II's EEA pull dropped: 0.2 % of registrations in 2012, about 6 % in 2021–22, with a coding break in
  2016.
- In the RSV legacy rows, 47 % have dimensions 0/0/0; some triplets are shifted between fields; 57 % of first
  registration dates are 1 January.
- ZÁNIK carries no date, and the deregistration dataset starts in July 2012.
- Stall count on the live layer: 168 424 (September 2026).
- 215 108 valid long-term permits on 1 May 2026 (TSK answer 2026-05-19-058).
- Core districts by the stall rule: P1, P2, P3, P7.
- Rule-change dates (§3).
- The published parking texts were corrected on 28 Sep 2026 for permit prices by area and user.

**Seen at the design stage of v2 (28 Sep 2026; §5).**

- κ and δ (constants only).
- The 2019 labelled segments: 1 706 labelled (1 719 in the file). Stall-weighted true parallel share 0.702, in
  P4, P5, P6 and P9 only. Band widths by type.
- The layer-3 snapshot: 16 874 features, 168 424 stalls.
- **EEA re-pull with M1 + M1G**, wheelbase only, and no length conversion yet:
  - 2012 → 2022 endpoints +80.2 mm; trend 7.07 mm a year (2012–2022).
  - Part II had +68 mm and 6.0 mm a year, M1 only.
  - This moves Part II's comparator. A correction to Part II follows once it is converted (C.2).
- RSV coverage by manufacture year and missingness (§5, DS1). No length value was read.
- DS10 fit of the stock model to published counts and ages.

## 1. Research questions and estimands

**Fleet**, throughout: M1 + M1G (N1 as a sensitivity), all statuses. **Route (b) at both ends** (§4).

- **RQ1 (size).** How much less would today's paid-zone kerb hold of today's fleet than of 2012's?
  - **Primary: θ₁ᵘ, the loss on unmarked parallel kerb**, anchored on kerb length ℓ:
    θ₁ᵘ = 1 − (L̄₂₀₁₂ + g)/(L̄₂₀₂₅ + g). It is a share of the 2012-fleet capacity of the same kerb.
  - **Painted bays** lose capacity only through cars longer than the bay: θ₁ᵖ = F₂₀₁₂(b − 0.5) − F₂₀₂₅(b − 0.5).
    It is the growth in the share of the fleet longer than bay length b minus 0.5 m. F_t is the fleet length
    distribution from route (b), and b comes from the marking inventory (default 5.75 m).
  - **Citywide**, a share of all stalls: θ₁ = s_u·θ₁ᵘ + s_p·θ₁ᵖ, where s_u and s_p are the unmarked-parallel and
    painted-parallel shares of stalls.
  - The counterfactual count is N₂₀₁₂ᶜᶠ = N · [1 + s_u((L̄₂₀₂₅+g)/(L̄₂₀₁₂+g) − 1)] + painted term. N is the September
    2026 snapshot count, reported as "administrative stalls" because PS_ZPS may be a nominal count.
  - **θ₁ in per cent is the headline**; stalls are secondary and rounded to hundreds.
- **RQ2 (what fills the kerb).** In the fixed-footprint core, the length share of demand growth, c_L / (c_n + c_L),
  with c_n = Δ ln n (valid long-term permits) and c_L = Δ ln p̄. p̄ = s(L̄ + g) + (1 − s)·2.5 m is the kerb used per
  car. Citywide, c_K = Δ ln N is added.
- **RQ3 (price).**
  - **Size component:** each car's kerb use in metres per year, and the Kč per kerb metre per year it pays at a flat
    price. A revenue-neutral length schedule P_i = P̄ · ρ_i with ρ_i = s(L_i + g)/(L̄ + g) + (1 − s).
  - **Level component:** the implicit subsidy (forgone rent) S̄ = B·A − P, reported as a **bracket over B**, never
    as a single figure. A = 13.49 m².
- **RQ4 (validation; the confirmatory part).**
  - Δ₁ = 10 × the trend slope, 2012–2022, of the post-stratified mean overall length of cars new to CZ, measured on
    the register.
  - Δ₂ = the change 2022 → 2025, by the same rule.
- **RQ5 (elsewhere).** Size-based residential permit pricing, per m² of kerb per year. Descriptive only.

## 2. Hypotheses, estimates and reporting rules

### 2.1 Confirmatory family: H2a and H2b, Holm at α = 0.05 (thresholds 0.025 and 0.05)

- **H2a (validation, equivalence).** |Δ₁ − C| < δ.
  - **The comparator.** C = 10 × EEA trend slope 2012–2022 (M1 + M1G, fixed at design stage: 7.07 mm a year, so
    70.7 mm a decade) × b̂. Here b̂ is the register's marginal length-on-wheelbase slope, estimated **within model
    lines**: a fixed-effects regression of length on wheelbase, over M1 + M1G cars new to CZ, 2012–2022, with a
    fixed effect per normalised model line. b̂ is re-estimated in every bootstrap draw.
  - **The margin.** δ = 4.4 cm, fixed and symmetric. It is the new-car change over 2012–2022 that moves θ₁ᵘ by
    0.25 pp through the fleet transfer coefficient κ = 0.2988 (at k = 1.5, the centre of the DS10b-admissible
    range; §5, DS-κ).
  - **The test.** TOST. p = the larger of the two one-sided p-values from a paired cluster bootstrap by normalised
    model line (B = 9 999, studentised). If the Kish effective number of clusters is below 30, a wild cluster bootstrap
    is used (Webb weights).
  - **Reading.** *Supported*: the register agrees with the EEA route within the consequence margin. *Not supported:
    inconclusive* (neither side rejects) is read as **underpowered**: DS8 puts the power at d = 0 at 0.16. *Not
    supported: disagreement* when |Δ₁ − C| ≥ δ is rejected in the other direction, one-sided at 5 %.
- **H2b (the missing years).** Δ₂ < 6.0 cm (T&E: 4.32 m in 2022 by interpolation, 4.38 m in 2025).
  - One-sided, same bootstrap. The 2023–2025 cells are post-stratified on EEA registration counts (2025 provisional),
    because no EEA dimension exists after 2022.
  - **Forecast contest (reported alongside, not tested).** If the 95 % interval of Δ₂ lies wholly below 4.5 cm, it is
    "closer to Part II's +3.0"; wholly above, "closer to T&E's +6.0"; otherwise "undecided". T&E's figures are rounded
    to the centimetre (±0.7 cm on a difference), and this is stated next to the result.
- **Both.**
  - Leave-one-model-out influence, with the largest listed (the Octavia alone is about 12 % of the weight).
  - A size check by simulation at Δ = C ± δ (H2a) and Δ = 6.0 (H2b), using the fitted cluster residuals. The
    empirical rejection rate is reported.
  - DS8 found both prior-predictive probabilities below 0.95 (0.13 and 0.27), so both stay in the family (A.4).

### 2.2 Pre-specified estimates (not tested; results-blind reporting rules written now)

Each is reported as the median and the 2.5–97.5 % **uncertainty interval under the registered input distribution**,
never as "CI" or "p". Each also comes with:

- the Monte Carlo standard error of both quantiles (batch means, 20 batches);
- where a probability is quoted, P_MC = (k + 1)/(M + 1), with M = 20 000;
- a **tipping-point line**: the smallest single-input change, within the registered ranges, that moves the headline
  into another band. If no single input does so within its range, that is stated.

**H1 → E1 (the size loss).** θ₁ᵘ and θ₁ are reported in bands, with the sentence for each written now:

| Band (whole interval of θ₁) | Sentence |
|---|---|
| < 1 % | "On today's kerb, 2012's cars would fit fewer than one more car in a hundred." |
| 1 – 2.5 % | "On today's kerb, 2012's cars would fit between one and two and a half more cars in every hundred: real, and small next to the count of cars." |
| 2.5 – 5 % | "On today's kerb, 2012's cars would fit between two and a half and five more cars in every hundred, a loss the size of a zone extension." |
| ≥ 5 % | "On today's kerb, 2012's cars would fit at least one car in twenty more; the size of cars is a first-order pressure." |
| Straddles | Both adjacent sentences, joined by "between … and …", naming the input that decides (the tipping point). |

- **Comparisons, no test.** θ₁ᵘ (per parallel space) against T&E's rate pro-rated to 13 years (8.5–14 % → 7.4–12.1 %),
  and against Part I's reproduction of T&E's own parameters (3.35–3.95 % over 15 years → 2.9–3.4 %). If θ₁ᵘ lies below
  both, the sentence reads: "Prague's per-space loss is below what T&E's own parameters imply, and far below T&E's
  headline."
- DS-κ puts the fleet-mean growth needed for θ₁ = 3.7 % at 19–29 cm, depending on s and g, against the ~10 cm already
  published. The band is therefore very likely known in advance, and E1 is descriptive by rule A.4.

**H3 → E3 (count against length).** The length share λ = c_L/(c_n + c_L) in the core (P1, P2, P3, P7), over the longest
window W with year-end permit counts (at least five years), and c_K citywide.

| Band | Sentence |
|---|---|
| λ interval wholly < 0.5 | "In the districts whose zones did not grow, more cars, not bigger cars, filled the kerb." |
| wholly > 0.5 | "In the districts whose zones did not grow, bigger cars filled more of the kerb than more cars did." |
| Straddles 0.5 | "Count and size contributed comparably; the data cannot rank them." |
| c_n ≤ 0 | "Permits in the core did not grow; the length term is the only growing demand." |

If year-end permit counts are unavailable, E3 is **not run**. The Prague-registered fleet (data cube) is then shown
descriptively, labelled as registrations, which include leasing and company fleets, and located by registration
office or address as DS3 determines. It is never presented as permits.

**H4 → E4 (the size subsidy).**

- **Size.** The Kč per kerb metre per year at P (core first-car case, and the permit-mix-weighted price once permit
  counts by category exist). The revenue-neutral length schedule, as quantiles over the fleet: p10, p50, p90. The share
  of cars whose price would move by more than ±10 %.
- **Level (bracket).**
  - Lower: the city's second-car price, 7 000 Kč.
  - Central: land value × 4 % a year × A. The land value comes from a dated source fixed before estimation
    **[verify source: Prague price map of building land or ČSÚ land prices]**.
  - Upper-middle: off-street garage rents from a dated snapshot of listings, with the method fixed before collection.
  - Upper: the OZV rate, an administrative ceiling for exclusive 24-hour use, not an opportunity cost.
- **Sentence rule.** "The flat permit's size subsidy is X Kč a year between a short and a long car; the implicit
  subsidy to parking at all (forgone rent) is between Y₁ and Y₄ Kč." It is never a single Kč headline. It always says
  "implicit subsidy (forgone rent)".
- R is **not** a quantity of interest, because it is small by construction when B·A ≫ P.

## 3. Data and measures

**Supply.**

- The segment layer 3, snapshot `zps_layer3_snapshot_20260928.json` (S-JTSK, 16 874 features, 168 424 stalls, hashed).
  It is called the **September 2026 state**, not N₂₀₂₅. The layer is live and drifts: 168 456 on 8 Sep, 168 424 on
  28 Sep.
- **Band width.** Solve the quadratic w = (h − √(h² − 4A))/2, with h = perimeter/2 and A = area. Classes: parallel if
  w ∈ [1.6, 3.2] m; non-parallel if w ∈ [4.0, 6.5] m; unclassified otherwise.
- **Parallel share ŝ.** A PPV/NPV ratio estimator on the 2026 snapshot. The PPV and NPV come from the 2019 labels (DS4),
  drawn from Beta posteriors in the Monte Carlo.
  - A validation sample on 2026 geometry: 150 segments, stratified by predicted class, PPS on stalls, labelled blind
    on the IPR orthophoto **[verify year and licence]**.
  - Painted, unmarked and angled are recorded in the same pass.
  - The prior uniform(0.50, 0.85) is used only if the interval of ŝ is wider than the uniform's.
  - If TSK supplies the IS ZPS export with TYPSTANI (Requests), it replaces the classifier, recorded as a Change.
- **Supply over time.** TSK/ÚDI yearbooks 2012–2024, stalls by district.
  - **Core** = districts with |ln(N_2024/N_2012)| ≤ 0.02, which gives P1, P2, P3, P7 (referee C; the script reproduces
    it before estimation).
  - Breaks: the "Ostatní" column; the 2016–18 change of zone scheme.

**Permits.**

- The only public anchor is 215 108 valid on 1 May 2026 (TSK, answer 2026-05-19-058).
- Year-end counts by category and district: requested (Requests, R-TSK-2).
- **Rule-change dates**, treated as breaks in any series:
  - 2018: hybrids get 100 Kč permits **[verify exact date]**.
  - 31 Dec 2024: transferable permits end.
  - 30 Jun 2025: free parking for EVs ends.
  - 1 Jan 2026: EL-plate cars pay; zero-emission cars −50 %.
  - The virtual-address (ohlašovna) rule for residents **[verify date]**.

**Register (RSV).**

- `RSV_vypis_vozidel_20260901.csv`, the full export (hashed; §5 DS1).
- **Fleet** = `Kategorie vozidla` ∈ {M1, M1G}; N1/N1G as a sensitivity. **All statuses kept**, including ZÁNIK and
  VÝVOZ; no status filter.
- **Length missing** if the first element of `Celková délka/šířka/výška` is empty, 0 or non-numeric.
- **Shifted triplets** (length in the width slot, etc.) are detected by plausibility against make × model medians
  after the freeze (DS11). They are set to missing, never repaired by hand.
- **New to CZ** (year level; 57 % of dates are 1 Jan): year(first registration) = year(first registration in CZ), and
  manufacture year ≥ that year − 1. Everything else entering in year y is a **used import**.
- **Post-stratification (H2a/H2b):** cells of make × normalised model line × year, weighted to the EEA registration
  shares (M1 + M1G).
  - Cells with no register survivors: imputed from the adjacent years of the same model line, and the imputed weight is
    reported.
  - Missing lengths: multiple imputation (M = 20) within make × model × year, then make × model. It is nested in the
    bootstrap and in the Monte Carlo.
- **Normalisation dictionary** (EEA `Cn` ↔ RSV `Obchodní označení` / `Typ`): built from names and counts only, frozen
  and hashed before any length is read (DS12).
- **Owner/operator data are never downloaded or processed.** Location comes only from aggregate cube counts (DS3).

**EEA.** `eea_cz_by_model_m1_m1g.csv` (hashed): M1 + M1G, final rows 2010–2022, and registration counts 2023–2025
(the 2025 counts provisional) for post-stratification.

**Fleet age.** SDA means 2016–2025 and counts 2016–2025 (ČAPPO), ČSÚ 2014.

**Prices.** The TSK price list; OZV 16/2025 and its Annex 1 overrides for (k) **[verify]**; the level-bracket sources
(§2.2).

**RQ5 table.** Kept in three separate row groups, each in its own units:

1. **Residents, by size (length or footprint):**
   - **Koblenz:** length × width × 23.40 € a year, minimum 100 €, from 1 Mar 2024 (koblenz.de, verified).
   - **Köln:** ≤ 4 109 mm 100 €, 4 110–4 709 mm 110 €, > 4 709 mm 120 €, from 1 Mar 2025 (stadt-koeln.de press
     release, verified 28 Sep 2026). The thresholds sit a millimetre from this series' Fabia and Kodiaq, and that is
     verified, not a transcription error. The 5 600 mm exclusion is **[verify]**.
   - **Freiburg:** 240 / 360 / 480 € by length, annulled by BVerwG 9 CN 2.22 on 13 Jun 2023 (verified).
   - **Aachen:** 30 € per m² of footprint + 15 € **[verify]**.
   - **Bonn:** footprint-based, flat 120 € from 2027 **[verify]**.
2. **Residents, by weight:**
   - **Lyon:** 15 / 30 / 45 € a month by weight class, from 11 Jun 2024 **[verify; lyon.fr returned 403]**.
   - **Tübingen:** weight surcharge **[verify amounts]**.
3. **Visitors, by weight:**
   - **Paris:** hourly tariff tripled for ICE/hybrid ≥ 1.6 t and EV ≥ 2 t from 1 Oct 2024. Residents are exempt.

Entries still marked [verify] at estimation time are dropped. Conversion is at the ECB reference rate of 30 Sep 2026,
with PPS as a sensitivity check.

## 4. Models

**Route (b), both years (D.1–D.2).** For t ∈ {2012, 2025}:

L̄_t = Σ_c E_c · S(t − m_c | a_c) · L̄_c / Σ_c E_c · S(t − m_c | a_c)

- c indexes the (entry year, manufacture year m) cells.
- E_c are register entries (M1 + M1G, all statuses) by year of first registration in CZ and manufacture year.
- a_c = the age at entry, so a used import enters old. S(a | a₀) = exp(−(a/λ_t)^k + (a₀/λ_t)^k).
- λ_t is solved so the modelled mean age equals the year-t mean age.
- This weights by entry size × survival (D.4), and blends new cars and used imports by manufacture year.
- **Cohort lengths L̄_c.** Post-stratified cell means with multiple imputation.
  - **Pre-2010 cohorts (survivor bracket, D.5):** L̄_c = L̄_c^surv + u · 0.5 cm · min(2010 − m_c, 20), with
    u ~ uniform(−1, 1).
  - One u per draw, common to all pre-2010 cohorts and to both years.
- **Mean age 2012:** uniform(13.3, 14.1). A definitional shift e ~ uniform(−0.5, +0.5) years is added to *both* years'
  mean ages in the same draw. 2025 = 16.68 + e.
- **Shape:** Weibull k ~ uniform(1.4, 1.6), common to both years in a draw. This is the range admissible in DS10b;
  v1 had (1.5, 3.0).
- **Manufacture year** = `Rok výroby` if filled, else the year of `Datum 1. registrace` (anywhere). `Rok výroby` is
  empty for 4.07 M M1/M1G rows, most of them recent (DS1).
- **Calibration diagnostic (2025).** Measured-minus-modelled mean length of the active 2025 fleet (M1 + M1G, status
  "provozované" **[verify label]**).
  - **Rule:** if |diff| > 2 cm, k is re-chosen on [1.5, 3] to minimise it and used at both ends, recorded as a Change.
  - The primary estimate stays route (b), both years.

**Gap (E.1).** Reference pitch p ~ triangular(4.9, 5.2, 5.5) m. In each draw g = p − L̄₂₀₂₅.

- **Structural switch**, reported as two estimates: (i) constant gap (primary); (ii) gap proportional to length (T&E's
  constant ratio).
- An orthophoto pitch audit on saturated runs is optional. If done, it is recorded as a Change before estimation.

**Monte Carlo.** M = 20 000 draws, seed 20260928.

- Input groups: {ageing: k, the 2012 age, e}, {cohort lengths: MI draw, u}, {pitch p}, {s: PPV/NPV Betas, sample},
  {marking: painted share, b}.
- **Grouped Sobol / Shapley effects** over these groups (E.2), not independent-input Sobol.

**H2a / H2b.** Annual post-stratified means, then OLS of the annual means on year: 2012–2022 for Δ₁ (× 10), 2022–2025
for Δ₂ (× 3). There are no endpoint means.

- A paired cluster bootstrap by normalised model line resamples the same model lines for the length and the b̂
  regressions.
- The Kish effective number of clusters is reported (EEA proxy: 43.6).

**E3.** c_n from the counts (no sampling uncertainty claimed; definitional variants in R8), and c_L from the Monte
Carlo.

**E4.** Fleet lengths from the register (the active Prague-registered fleet from the cube's 10 cm bins if DS3 allows,
else national); g and s from the Monte Carlo.

**Not modelled.** Occupancy, cruising, turnover, behavioural response to price.

## 5. Design-stage checks and results (28 Sep 2026)

Scripts: `tools/parking6/parking6_design.py`, `tools/parking6/rsv_coverage.py` and `tools/parking6/eea_m1g.py`. Output:
`docs/research/prague-parking-ds.json`.

**DS-κ (constants only).**

- κ = ∂(fleet change 2012→2025)/∂(new-car change 2012→2022). The perturbation ramps from 0 in 2012 to 1 in 2022 and is
  held afterwards; Weibull weights are calibrated to 13.62 / 16.68.
  - κ = 0.2988 at k = 1.5 (registered, after DS10b); 0.2875 at k = 2; 0.2729 at k = 3; 0.3096 at k = 2 weighted
    by EEA entry size.
- ∂θ/∂(fleet length), with g = 5.20 − 4.195 = 1.005 m: 0.0962 (s = 0.5), 0.1299 (0.68), 0.1613 (0.85), 0.1887 (1.0)
  per metre.
- **δ (registered) = 4.4 cm**, for s = 1 because the primary estimand θ₁ᵘ is per parallel space. The first run at
  k = 2 gave 4.6 cm; it was re-set after DS10b, before any register length was read. It would be 6.4 cm for
  θ₁ at s = 0.68.
- **B.2 check.** θ₁ = 3.7 % needs 27.8–28.8 cm of fleet-mean growth at s = 0.68, 22.2–23.1 cm at s = 0.85, and
  18.9–19.6 cm at s = 1. The referees' 17.5–22 cm corresponds to s near 1.

**DS4 (classifier, 2019 labels).** 1 706 labelled segments; the file has 1 719, of which 13 are unlabelled. The
referees' 1 593 could not be reproduced; the difference is recorded, not resolved.

| Truth → predicted | parallel | non-parallel | unclassified |
|---|---|---|---|
| parallel (segments / stalls) | 1 301 / 11 329 | 15 / 192 | 10 / 51 |
| non-parallel | 12 / 45 | 338 / 4 607 | 30 / 266 |

- **Stall-weighted accuracy 0.966**, counting unclassified as wrong (0.985 among classified). PPV parallel 0.996, PPV
  non-parallel 0.960. **Passes** the ≥ 0.80 rule, so the classifier is used.
- Median band widths: parallel 2.03 m, perpendicular 4.58 m, angled 4.35 m.
- The 2019 true parallel share (0.70, stall-weighted) covers P4, P5, P6 and P9 only, so it is not representative of the
  city. It is not used as s.

**DS-supply.** The snapshot of 28 Sep 2026: 16 874 features, 168 424 stalls, 16 874 unique OBJECTIDs, hash in
Appendix A.

**DS-EEA (C.6).** The M1G share by year: 2012 0.21 %, 2013 0.55 %, 2014 2.48 %, 2015 2.87 %, **2016 0.01 %** (coding
break), 2017 3.31 %, 2018 3.46 %, 2019 4.55 %, 2020 5.32 %, 2021 5.76 %, 2022 6.19 %. With M1 + M1G, wheelbase
2 616.7 → 2 696.8 mm (+80.2 mm at the endpoints; trend 7.07 mm a year). This is the registered comparator input.

**DS8 (precision; EEA wheelbase clusters as proxy, no register value).**

- 3 986 model-line clusters; Kish effective 43.6.
- SE of the decade length change 2.39 cm (at 1/0.618). SE of the 3-year change 1.59 cm.
- H2a (δ = 4.4 cm): power at d = 0 is 0.16; the margin needed for 80 % power is 7.0 cm. Prior-predictive
  P(supported) = 0.13.
- H2b: power at a true +3.0 cm is 0.59. Prior-predictive P(supported) = 0.27.
- **Consequences (pre-committed):**
  - H2a is expected to be inconclusive and is read as underpowered. The margin is **not** widened, because δ is set by
    consequence.
  - Neither prior-predictive probability exceeds 0.95, so both stay confirmatory.

**DS1 (register coverage).** See "DS1 and DS10 results" at the end of this section.

**DS2 (removed vehicles).** Route (a) is infeasible: ZÁNIK carries no date, and deregistrations start in July 2012.
Route (b) is committed.

**DS3 (cube semantics).** Open. The location basis is unclear: it may be the registration office, and any office has
been possible since June 2017. Asked in R-MD-3. Until answered, the Prague fleet is used only in R5 and E4, and labelled
as such.

**DS5 (core).** P1, P2, P3, P7 (referee C, from the yearbooks). The script reproduces it before estimation.

**DS6 (permits).** No public year-end series; requested (R-TSK-2). E3 is not run until it arrives.

**DS7 (2012 age).** No published 2012 SDA value was found, so the uniform(13.3, 14.1) prior stands.

**DS9 (prices, RQ5).** Köln verified; Koblenz and Freiburg verified; the rest [verify] (§3).

**DS11 (before real outcomes, pre-committed).**

- A blind dry run of the full pipeline with register lengths permuted across cohorts within make.
- It checks that the code runs end to end, that H2a/H2b come out null, and that the plots render.
- The code hash is committed before the unpermuted run.

**DS12 (before real outcomes).** The normalisation dictionary is frozen and hashed; the matched EEA weight is reported
by year. If it is below 80 % in any year, that year falls back to make × year cells.

### DS1 and DS10 results

**DS1 (the full export).**

- File: `RSV_vypis_vozidel_20260901.csv`, 17 217 031 625 bytes, 19 383 927 rows, no short rows. It was streamed once;
  only missingness was tested.
- Rows by category: M1 13 057 729, M1G 341 852, N1 975 245, N1G 85 054, other 4 924 047.
- M1 + M1G by status: PROVOZOVANÉ 6 921 884, ZÁNIK 5 032 836, VÝVOZ 984 050, VYŘAZENO Z PROVOZU 460 811.
- **Length present, by manufacture year** (M1 + M1G):

  | Manufacture year | Length present |
  |---|---|
  | before 1990 (2.99 M rows) | 45 % |
  | 1990–94 | 24–44 % |
  | 1995 | 58 % |
  | 1996 | 70 % |
  | 1997 | 83 % |
  | 1998 | 92 % |
  | 1999–2011 | 94–99 % |
  | 2012–2026 | ≥ 99.6 % |
  | `Rok výroby` empty (4.07 M rows, mostly recent) | 99.98 % |

- Wheelbase is present for 87–97 % of each year from 1998.
- **Cars new to CZ (year rule, §3), against EEA M1 + M1G:**
  - Ratios 1.01–1.08 in 2010–2015 and 2019–2022, but **1.21 (2016), 1.23 (2017) and 1.11 (2018)**. The excess is
    consistent with new cars registered and re-exported. The EEA post-stratification in H2a removes it from the weights.
    This is recorded as a data feature, not as an outcome.
  - Length is present for ≥ 99.2 % of new-to-CZ cars in every year 2010–2025.
  - **The 90 % coverage rule (C.7) is not triggered.**
- **1 January dates.** Among M1 + M1G *first registrations in CZ*, 1 January is 8.4 % in 2000, below 1.6 % in
  2001–2008 and 0 % from 2009. The referees' 57 % concerns legacy rows or the first-registration-anywhere field. For
  2010–2025 the year-level rule is unaffected.
- Missing lengths before 1998 are concentrated in the cohorts the survival weights discount most. In route (b) they are
  multiply imputed and fall under the pre-2010 bracket.

**DS10 (stock model against SDA 2016–2019; tolerances written in the code before the run: age ±0.3 years, count
±5 %).**

- Entries (M1 + M1G, all statuses, by year of first registration in CZ and manufacture year): 13 394 875.
- **As first specified**, one time-invariant λ calibrated on the 2016 age: **fails** for every k.
  - k = 1.5: counts within 0.5 %, but the modelled age stays flat (14.48–14.56 against SDA 14.6–14.9; error −0.34 in
    2019).
  - k = 2: counts +8.1 to +8.7 %.
  - k = 3: +17 to +18 %.
  - A constant hazard cannot reproduce the ageing of the Czech fleet.
- **DS10b (the registered route (b), λ_t calibrated per year to that year's age).** Ages fit by construction. The
  counts are within ±5 % in all four years only for **k ∈ [1.4, 1.6]**:
  - k = 1.5: −0.1 / +0.9 / +2.4 / +2.6 %;
  - k = 2: +8.7 to +11.2 %.
  - The error drifts up by about 1 pp a year, which is noted.
- **Consequences, recorded before any length was read:**
  - the k prior becomes uniform(1.4, 1.6);
  - κ and δ are recomputed at k = 1.5 (δ from 4.6 to 4.4 cm);
  - DS8 is rerun (H2a power 0.16).
- The assumed age convention (age = t − manufacture year + 0.5) is absorbed by the per-year λ_t. It is stated.

## 6. Robustness checks (reported, not tested)

1. **R1, the EEA route.** EEA wheelbase × b̂, then the fleet model: the Part II method, now with M1 + M1G.
2. **R2, the T&E route** (Part I).
3. **R3, the fixed share.** s = 0.68, against the measured ŝ.
4. **R4, the discrete segment model** with per-segment classification.
5. **R5, the fleet definition.**
   - N1 included.
   - The Prague-registered fleet, from the cube if DS3 allows.
   - Used imports excluded.
   - STK-active age scaling (13.79 against 16.41 in 2024, ×0.84 on both years' ages).
6. **R6, the age shape.** Exponential and uniform, against Weibull.
7. **R7, the gap law.** The proportional-gap switch; p fixed at 4.9, 5.2 and 5.5 m.
8. **R8, the counts.**
   - Permits issued, valid at year end, or resident only.
   - Core thresholds of 0.01 and 0.05.
   - W trimmed by one year at each end.
   - A break-adjusted series.
9. **R9, prices.** The level bracket members one by one; P = 1 200, 600 or 360 Kč, or −50 % for zero-emission cars;
   the permit-mix weighting.
10. **R10, the area model** and width encroachment from register widths. No mirror-width claim is made (J).
11. **R11, grouped Sobol / Shapley effects.**
12. **R12, H2a/H2b sensitivity.**
    - Drop 2018 (the `?KODA` fault).
    - Drop 2016 (the M1G coding break).
    - Endpoint means instead of the trend.
    - Unweighted (not post-stratified).
    - Leave out the largest model line.
13. **R13, specification curve** over:
    - {constant / proportional gap}
    - {ŝ / 0.68 / uniform}
    - {national / Prague fleet}
    - {continuous / discrete}
    - {k fixed at 1.5 / drawn}

    The band of θ₁ in each specification is reported.

## 7. Limitations (stated in the article)

- **Counterfactual.** Every headline is phrased "on today's kerb, 2012's cars would fit about X more". It is not a
  history of stall counts.
- **Marked bays.** The painted/unmarked split comes from a sample (and TSK, if supplied). θ₁ᵘ is primary for that
  reason.
- **Registered is not parked.** The register describes registrations, not the cars in the zones. Prague location in the
  cube may be the registration office.
- **Survivorship.** Old cohorts are survivors. The bracket in §4 is an assumption, not an identification.
- **Two ages.** The 2012 mean age is not published; it is a prior.
- **Permits count entitlement, not presence.** Rule changes break the series.
- **Price benchmarks** bracket forgone rent. None is a market price for shared kerb.
- **No behaviour** is estimated.
- **H2a is underpowered** by design arithmetic (DS8), and an inconclusive result says so.

## 8. Deliverables

- `tools/parking6/`: `parking6_design.py`, `rsv_coverage.py` and `eea_m1g.py` (committed with this design). To come:
  `parking6_data.py` (dictionary, post-stratification, multiple imputation), `parking6_estimate.py`,
  `parking6_robust.py` and `parking6_figures.py`.
- `docs/research/prague-parking-ds.json` (design-stage results) and `docs/research/prague-parking-files.sha256`.
- `assets/parking6/`, and `texts/prague-parking-study.html` (Part 6, long version).
- If the converted M1 + M1G comparator changes Part II's numbers: a dated correction note on
  `texts/prague-parking-2.html`.

## Requests for the author to send

These were not sent by the author of this design. Bára sends them. All ask for aggregate data only.

**To TSK hl. m. Prahy (Act 106/1999):**

- **R-TSK-1.** The IS ZPS segment export, current and every historical state 2012–2026. Per segment: ZPS_ID, geometry,
  TYPZONY, TYPSTANI, PS_ZPS, CELKEM_PS, PLATNOSTOD and PLATNOSTDO, and whether the bays are painted (horizontal
  marking).
- **R-TSK-2.** Valid long-term parking permits on 31 Dec of each year 2012–2025, by category (resident first, second
  and third+ car; 65+/ZTP; abonent; property owner; zero-emission, hybrid or EL where distinguished) and by district
  (area and sub-area). Also the number issued per year, if kept separately.
- **R-TSK-3.** The inventory of horizontal parking marking in the zones (painted bays and their lengths).
- **R-TSK-4 (optional).** Occupancy aggregates by segment and hour from the monitoring vehicles, with no plates. And,
  if TSK can join internally: the 10 cm length distribution of vehicles holding valid resident permits, bins only.

**To the Ministry of Transport (MD ČR, Act 106/1999):**

- **R-MD-1.** The stock of registered M1 + M1G vehicles on 31 Dec of each year 2012–2025, by overall-length class
  (10 cm) and manufacture year, nationally and for hl. m. Praha, as aggregate counts.
- **R-MD-2.** Permanent removals (zánik) by year of removal and manufacture year, 2012–2025, as aggregate counts. This
  would make route (a) possible as a robustness check.
- **R-MD-3.** The definition of the territorial dimension in the data cube (dataovozidlech.cz): owner, operator or
  registration office; the treatment of legal persons and leasing; and whether it changed with the June 2017 reform.

**Optional, not Act 106:** SDA/ČAPPO, the published mean fleet age for 2012 and 2013, and its definition (manufacture
year or first registration).

**Right of reply (J), after results and before publication:** T&E (the reproduction of 8.5–14 %), TSK (the stall and
permit figures) and PAQ Research (the 6 000 Kč threshold).

## Response to referees

| Item | Response |
|---|---|
| A.1 P_MC not a p-value | Done. P_MC is out of Holm and is reported only as (k+1)/(M+1) (§2.2). |
| A.2 Family = H2a, H2b | Done (§2.1), Holm thresholds 0.025 and 0.05. |
| A.3 H1/H3/H4 as estimates | Done: E1, E3 and E4 with interval wording, quantile MC SE and tipping-point lines (§2.2). |
| A.4 Predictability rule | Done. It is applied to H2a/H2b through DS8 (0.13 and 0.27, so both are kept). E1 is descriptive by DS-κ arithmetic. |
| A.5 Wording, §0 | Done. "Registered analysis plan"; the known directions and sizes are stated in the status block and §0. |
| B.1 Unit mismatch, τ₁ | Done. τ₁ is dropped. θ₁ᵘ is per parallel space and is compared with T&E's rate and with Part I's 2.9–3.4 % reproduction. |
| B.2 Arithmetic | Done (DS-κ): 19–29 cm by s and g. The referees' 17.5–22 holds for s near 1. |
| B.3 Banded rule | Done, with the sentences written (§2.2). |
| B.4 N₂₀₁₂ᶜᶠ | Done (§1). |
| B.5 θ₁ᵘ primary, painted bays | Done (§1, §3). The TSK marking inventory is requested (R-TSK-3). "Administrative stalls" is used. |
| C.1 Margin by consequence | Done. κ = 0.2988 (k = 1.5, after DS10b); δ = 4.4 cm for θ₁ᵘ (6.4 cm for θ₁ at s = 0.68). |
| C.2 Marginal slope b̂ | Done: within model lines, re-estimated in every bootstrap draw (§2.1). |
| C.3 Survivorship post-stratification, all statuses | Done (§3). |
| C.4 Trend, paired cluster bootstrap, Kish, wild fallback, LOMO, size check | Done (§2.1, §4). |
| C.5 H2b forecast contest | Done. The contest is reported beside the test; the rounding is stated. |
| C.6 M1 + M1G, re-pull EEA | Done (DS-EEA): +80.2 mm at the endpoints against +68. A Part II correction will follow after conversion. |
| C.7 Register traps | Done. Missing codes, shifted triplets, a year-level new-to-CZ rule, multiple imputation, and DS1 on the full export. |
| D.1 Route (b) | Committed (DS2). |
| D.2 Same route both ends, 2 cm rule | Done (§4). |
| D.3 2012 age prior | Done. Uniform(13.3, 14.1) plus a common shift e; the STK-active check in R5. |
| D.4 Entry × survival, manufacture year | Done (§4). |
| D.5 Symmetric bracket with formula | Done (§4). |
| D.6 DS10 | Done. The time-invariant version fails the pre-committed tolerances. The registered per-year λ_t passes only for k ∈ [1.4, 1.6], so the k prior was narrowed, and κ, δ and DS8 were recomputed before any length was read (§5). |
| D.7 DS11 | Pre-committed (§5). It runs before the unpermuted estimation. |
| E.1 Gap from pitch | Done. p is triangular(4.9, 5.2, 5.5); the structural switch is reported. |
| E.2 Grouped Sobol / Shapley | Done (§4, R11). |
| E.3 Parallel share | Done. The 2019 validation passes (0.966); the quadratic formula is fixed; the stratified PPS sample and the TSK request are in place. The referees' "1 593" could not be reproduced (1 706 found). |
| E.4 Live supply | Done. Snapshot hashed; called the September 2026 state. |
| F.1 Descriptive λ, c_K | Done (E3). |
| F.2 Symmetric core | Done: P1, P2, P3, P7, with the stated breaks. |
| F.3 Permits | The anchor is cited and the series requested (R-TSK-2). Nothing was sent. |
| F.4 Rule-change dates | Listed as breaks (§3). Two dates remain [verify]. |
| F.5 Fallback descriptive only | Done (E3). |
| G.1–G.4 Subsidy | Done. R is dropped as a target; the size component is in Kč per metre with a schedule; the level is a bracket; "implicit subsidy (forgone rent)". |
| G.5 Prices by area and user | Done. Core first-car case, or the permit-mix weighting once counts arrive. |
| H.1 Köln | Verified on stadt-koeln.de (thresholds 4 109 / 4 709 mm). The 5 600 mm rule is still [verify]. |
| H.2–H.4 Row groups | Done (§3). Unverified entries are dropped at estimation if still unverified. |
| I Privacy | The owner/operator data are neither downloaded nor processed. §0 and Appendix A list every file opened. |
| J Framing | Adopted: counterfactual phrasing, rounding to hundreds, no mirror claim. Right of reply is left to Bára (Requests). |

## Appendix A. Raw files (SHA-256)

`docs/research/prague-parking-files.sha256`, committed with this file. It lists every raw file in
`tools/data/parking6/` and its subfolders (all gitignored), including files the referees opened. Personal-data files
are absent: the owner/operator sample was deleted before v2, and it is not listed.

## Appendix B. Literature

Unchanged from v1: Shoup 1997, 2005/2011, 2018; Pierce & Shoup 2013; van Ommeren et al. 2012, 2014; Molenda & Sieg 2013
**[verify]**; Inci 2015; T&E 2024, 2026; ICCT pocketbook **[verify]**; Holder et al. 2021; Regulation (EU) 2019/631;
Holm 1979; Schuirmann 1987; Cameron, Gelbach & Miller 2008; Webb 2023; Saltelli et al. 2008; Owen 2014 and Song, Nelson
& Staum 2016 (Shapley effects) **[verify]**; Kish 1965.

## Changes after registration

### 2026-09-29, before any unpermuted length was read (freeze commit `e589225`)

- **DS12 (dictionary).** Built from names and counts only, then frozen: `dict_model_lines.csv`, sha256 `ccfd595f…`.
  - EEA weight matched to a register model line in the same year: 97.3 % (2018) to 100 %. No year falls back.
  - The line key is the first token of the commercial name. It is coarse for a few makes (the Hyundai i-models share
    one line), and it was not changed after the freeze.
- **EEA 2023–2025 counts** pulled for post-stratification (`eea_counts_2325.py`; 2025 provisional).
- **Compact extract.** `rsv_extract.py` writes M1/M1G/N1/N1G technical fields only, with no VIN, PČV or owner data.
  Values above 100 000 and years outside 1900–2030 are set to missing; they overflowed the parquet types on the first
  run.
- **DS11, the dry run.** L, W and WB were permuted jointly **across cohorts within make**, as registered. The
  coordinator's brief said "within manufacture year". That would keep each year's mean length, and so reveal the trend
  that H2a/H2b test before the freeze, so the registered version was kept.
  - The dry run completed end to end: Δ₁ = 2.1 cm, Δ₂ = 0.0 cm (make mix only).
  - Size check at the null boundaries (reduced: 200 simulations, B = 199, not studentised): rejection rates 0.07,
    0.03 and 0.045.
- **Implementation choices, fixed in the frozen code:**
  - The multiple-imputation variance of a cell mean is a normal approximation to the within-cell hot-deck variance.
    Missing length among new-to-CZ cars is at most 0.8 %.
  - The studentised bootstrap uses an inner B of 50.
  - The size check is the reduced version above.
  - The fleet-cell lengths are observed cell means, with the pre-2010 bracket u on top.

### 2026-09-29, after the real run

- **A coding error, found in the output and fixed.** The painted-bay share F_t(5.25 m) counted cars with a missing
  length as longer than 5.25 m. That gave the impossible θ₁ᵖ = −11.5 %. Only non-missing lengths are now counted
  (code sha256 `1041a3fb…`; H2a/H2b come from the frozen `4fad464b…`, and E1/E4 were re-run).
  - After the fix, θ₁ᵖ = +0.76 %: the share of cars longer than 5.25 m rose from 0.29 % to 1.05 %.
  - θ₁ᵘ, θ₁ and the stall figure did not move beyond the fourth decimal.
- **The calibration rule fired.** Measured-minus-modelled 2025 mean length was +3.9 cm. The registered remedy
  (re-choose k on [1.5, 3], intersected with DS10b's [1.4, 1.6]) finds its minimum at the boundary, k = 1.5, where
  the gap is still 3.9 cm. It grows with k up to 4.7 cm at k = 3.
  - k is fixed at 1.5 at both ends. The estimates equal those with k drawn to four decimals. The gap stays and is
    reported as a limitation.
  - A level offset common to 2012 and 2025 would move θ₁ᵘ very little. One that differs between the years would not
    be captured.
- **Painted bays were not measured.** Neither the orthophoto sample nor TSK's marking inventory (R-TSK-3) exists
  yet. θ₁ is computed with every parallel stall unmarked (s_p = 0), which is an upper bound. s_p/ŝ = 0.25 and 0.5 are
  reported alongside.
- **No 2026 orthophoto validation sample** was labelled. ŝ uses the 2019-trained PPV and NPV only.
- **E4.** Two members of the level bracket were not computed: land value × 4 % and garage rents, because no dated
  source was fixed before estimation. The bracket shows its lower (second-car price) and upper (OZV) members only.
  - X ("between a short and a long car") is operationalised as p90 − p10 of the revenue-neutral length schedule at
    1 200 Kč.
  - The E4 fleet is the national active fleet, because DS3 is unresolved.
- **E3 not run:** awaiting TSK data (R-TSK-2).
- **H2a precision.** The realised SE of d (3.9 cm) is larger than the DS8 proxy (2.4 cm), so power was lower than
  planned. Kish = 37.1, so no wild-bootstrap fallback was needed.
  - The size check at +δ rejected at 0.11 (reduced B, not studentised). The H2a lower-tail test may be liberal. This
    does not affect the decision, which is "not supported".
- **Grouped Sobol.** The pick-freeze estimates for ageing and parallel share are slightly negative (−0.001 and
  −0.015): estimator noise at 4 000 draws, read as ≈ 0.
- **OZV Annex 1 (DS9) checked.** For item (k), the zone districts have exemptions for named users only. Praha 13
  charges 5 Kč, and several outer districts 1 Kč. The 10 Kč rate stands for the zone districts.
- **Part II correction (C.6).** Part II's own pipeline, run with M1 + M1G:
  - new-car length change 2012–2022: +13.0 cm (11.5–15.4), not +11.0 (9.7–13.1);
  - loss: 2 709 stalls (1.58 %), band 2 378–3 250, not 2 263 (1 988–2 710).
  - A correction note is prepared on a separate branch (`docs/PARK-2_m1g-correction`).
  - Part III's 174 stalls a year is derived from Part II; it is left untouched, and the conflict is flagged for the
    author.
