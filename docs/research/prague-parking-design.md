# Prague's kerb, measured: research design (Part 6, parking)

**Status: draft for review.** Version 1, written 2026-09-28 before referee review. It merges the three published
parking texts (Parts I–III, `texts/prague-parking*.html`) into one pre-registered study. It becomes "registered" only
after review, when it is committed together with the hashes of the raw files (Appendix A). No new outcome statistic
has been computed for this draft. Everything outcome-related that the author has already seen is listed in §0.
Deviations after registration are listed, dated, in "Changes after registration".

Unverified factual claims are marked **[verify]**. They must be resolved, or dropped, before registration.

## 0. What has already been seen

The three texts share one model (the analysis repo `~/Downloads/parking/`, `METODIKA.md`, `src/`, 30 tests). Capacity
on a parallel kerb is kerb length ÷ pitch, pitch = car length L + gap g. With the kerb held fixed, and anchored on
today's stall count N₂₀₂₅, the 2012 count is N₂₀₂₅ · (L₂₀₂₅ + g) / (L₂₀₁₂ + g) on the parallel share s. The fleet
length L_t is a survival-weighted average of new-car cohorts, calibrated to the published mean age of the Czech fleet.

**Part I (published 8 Sep 2026, T&E new-car series).**

- Supply: 16 874 segment polygons on `gs-pub.praha.eu` (S-JTSK). 168 456 stalls (PS_ZPS): RES 103 641, MIX 63 697,
  VIS 1 118, type 7 zero. That is +1.37 % against TSK's December 2024 figure of 166 180. Gross area 2 400 507 m², net of
  disabled, reserved, delivery and special bays 2 272 593 m²; 13.49 m² net per stall (14.25 gross). District range
  13.7 (Praha 10) to 16.0 (Praha 1) m² per stall. The area model by district gives 5 635, the citywide model 5 627.
- Fleet: mean age 13.62 (2012) → 16.68 (2025). New car +17.0 cm (4.21 → 4.38 m). Fleet car 4.050 → 4.167 m
  (+11.7 cm). Fleet width +5.8 cm. Weibull, exponential and uniform age shapes differ by hundredths of a centimetre.
- Gap: g = 0.82 m (T&E's 5.20 m Berlin pitch minus 4.38 m). Parallel share s = 0.68 (Berlin, via T&E).
- Results (lost 2012→2025 on today's kerb):
  - length model, fleet, s = 0.68: **2 745 stalls (1.60 %)**;
  - all parallel: 4 036 (2.34 %); new-car lengths instead of fleet: 3 871 (2.25 %);
  - discrete Monte Carlo over the real segment sizes (16 784 segments, median 8, max 114; 200 draws): 2 953 (1.72 %),
    SD 46;
  - area model 5 627 (absolute overhead), 10 846 (proportional overhead);
  - full grid (3 growth scenarios × 3 gaps × 3 parallel shares): 1 946 – 8 058 (1.14 – 4.57 %). The top end
    appears only with the "2 cm a year" media rate, for which no primary source was found.
  - Gap sensitivity: 2 938 (g = 0.5 m) to 2 647 (g = 1.0 m).
- Width: +5.8 cm on the parallel stalls is 27 598 m² of roadway (≈ 2 046 of today's stalls). A new car with mirrors is
  2.02 m wide (T&E body width + 0.20 m) against the 2.00 m parallel stall of ČSN 73 6056 (secondary sources).
- T&E's 8.5–14 % loss by 2040 could not be reproduced from T&E's own parameters: 3.95 % (constant ratio of car to
  gap) or 3.35 % (constant gap).
- Price: 1 200 Kč a year per resident permit ÷ 13.49 m² = **89 Kč / m² / year**, the same for every car size.

**Part II (published 15 Sep 2026, EEA CO₂ monitoring, CZ).**

- 2 501 048 M1 registrations, 2010–2022, final rows only. Registrations per year: 2010 164 618; 2011 169 259; 2012
  169 576; 2013 161 155; 2014 174 562; 2015 221 289; 2016 214 408; 2017 213 542; 2018 229 002; 2019 233 603; 2020
  186 262; 2021 189 449; 2022 174 323.
- Data issues: P/F duplicates; plausibility filters; 81 215 cars in 2018 under make `?KODA` with no wheelbase, repaired
  by make normalisation and per-model imputation (2 653 mm); no EEA wheelbase or track for CZ from 2023.
- Wheelbase of new cars 2 616 → 2 684 mm (2012 → 2022, +68 mm, 6.0 mm a year). Via ratio r = 0.618 (Holder 2021;
  band 0.52–0.70), anchored on Závadská's 4.30 m (2019), that is +11.0 cm (band 9.7–13.1). T&E, same years: +11.0 cm.
- Mass 1 366 → 1 461 kg; track 1 560 → 1 554 mm (2022 track coverage 45 %). Škoda's share 31 % → 33 %; the mix shifted
  from Octavia and Fabia to compact SUVs.
- Same fleet and capacity model: fleet car 4.098 → 4.195 m; **2 263 stalls (1.33 %), band 1 988 – 2 710** (ratio). The
  whole gap to Part I's 2 745 lies in 2023–2025: T&E accelerates to 2 cm a year, while the Czech trend extended at its
  own pace adds 1.0 cm a year.

**Part III (published 23 Sep 2026, against Deník N, 22 Sep 2026).**

- The size effect spread evenly: 174 stalls a year (153–208).
- Praha 7 issues 280 new residential permits a year since 2018. This is Deník N's number, from Praha 7, and it is not
  clear whether it is gross or net. Thirteen years of the size effect equal about eight years of Praha 7's permit
  growth.
- Perpendicular parking: 5.0 m of kerb per parallel car against 2.5 m, bought with about 3.0 m of street width.
- A Fabia (4 108 mm) takes 12 % less kerb than a first-generation Kodiaq (4 697 mm) at g = 0.82 m. At a flat price the
  Kodiaq pays 218 Kč per kerb metre a year, the Fabia 244. A revenue-neutral length price would be ≈ 1 180 / 1 320 Kč.
  PAQ Research's Praha 7 threshold of 6 000 Kč (via Deník N) is not verified.

**Seen while drafting this design (2026-09-28). Prices, schemas and metadata only; no outcome data.**

- **Permit prices** (TSK price list, `cdn.parking.praha.eu/.../Vytah_z_ceniku_parkovacich_opravneni_.pdf`, notes
  valid from 1 Jan 2026):
  - Areas P1–P10 and P18: resident first car 1 200 Kč a year; residents aged 65+ and ZTP holders 360; second car 7 000;
    third and further cars 24 000–36 000 by price band. Abonent (business, property owner) first car 7 000.
  - Outer sub-areas (P5.1–P5.6, P8.1–P8.3, P9.1–P9.2, P10.1–P10.4, P18.1–P18.3): resident first car **600 Kč**
    (65+: 180), second car 3 500.
  - Since 1 Jan 2026, low-emission (EL-plate) cars no longer park free. Zero-emission cars get 50 % off, in their
    own district only.
  - **Consequence:** Part I's "89 Kč / m² / year" holds only for a first car of a resident under 65 in the core areas.
    It is flat across car sizes, but not uniform across residents. Part 6 corrects this.
- **City's own price of exclusive kerb space.** OZV hl. m. Prahy No. 16/2025 (local fee for use of public space, in
  force 1 Jan 2026), §2(1)(k): reserving a permanent parking place costs 10 Kč per m² per day (3 650 Kč / m² / year),
  unless Annex 1 sets otherwise for a district. The annex overrides for item (k) have not been read **[verify]**.
- **Mean age 2012 is an extrapolation.** `data/raw/rozmery_vozidel.json` has no 2012 value. The 13.62 used in Parts I
  and II is extrapolated from ČSÚ 2014 (14.06) and SDA 2016 (14.5). Part I calls it "published", which is wrong.
- **Supply schema.** The segment layer (`MapServer/3`) has no date fields (OBJECTID, POSKYT, SHAPE.AREA, ZPS_ID,
  TYPZONY, KODMC_T, TARIFTAB, PS_ZPS), so zone expansion cannot be dated from it.
- **TSK Ročenka dopravy 2024** (downloaded). Section 10.1 has a table of stalls by district and zone type (Dec 2024) and
  a paragraph on the 2024 zone extensions; the digits were masked when read. No permit counts appear in that section.
  Transferable permits ended by council resolution at the end of 2024.
- **data.praha.eu "Počty parkovacích míst"**: December 2024 totals only (as in Part I). The same page embeds a series of
  EL-plate vehicles registered in Prague: 2017 1 124; 2018 1 569; 2019 2 253; 2020 4 547; 2021 7 191; 2022 9 496.
- **Vehicle register (RSV) export** `RSV_vypis_vozidel_20260901.csv`: only the header line was read. It has overall
  length / width / height, wheelbase, track, mass, first registration (anywhere, and in CZ), year of manufacture,
  category, make, type, commercial name, status and PČV. It has **no location field**. The data cube can count by
  kraj / okres / obec with filters on body length and width **[verify semantics, §3]**.
- **Other cities' size pricing** (inputs to RQ5, secondary sources; see §3).

Parts I–III are known, so H1 below tests whether a known result **survives** measured inputs and propagated
uncertainty. It is not an independent discovery. H2a–H4 concern quantities no one has computed.

## 1. Research questions and estimands

- **RQ1 (size).** How much paid-zone kerb capacity did the lengthening of the parked car cost between 2012 and 2025?
  This time the answer comes with the measured parallel share, measured post-2022 car lengths, and every input's
  uncertainty propagated end to end.
  - **Estimand θ₁** = s · N₂₀₂₅ · [(L̄₂₀₂₅ + g)/(L̄₂₀₁₂ + g) − 1] / N₂₀₁₂ (loss as a share of the 2012-fleet capacity of
    today's kerb). Reported in stalls and per cent, as the median and the 2.5–97.5 % MC interval.
  - It is a counterfactual on today's kerb ("on today's zones, 2012's fleet would park θ₁ more"), not the historical
    number of stalls lost.
- **RQ2 (what fills the kerb).** Within a fixed zone footprint, how does the growth in kerb demand from **car count**
  compare with the growth from **car length**? Citywide, how does zone **supply expansion** compare with both?
  - **Estimand.** Kerb pressure Π_t = n_t · p̄_t / K_t:
    - n_t = long-term permits valid at year end (§3);
    - p̄_t = s · (L̄_t + g) + (1 − s) · b_⊥, the kerb used per car, with b_⊥ = 2.5 m for perpendicular bays;
    - K_t = kerb supply in car-equivalents at the reference pitch, which is proportional to stalls N_t.
  - Exact log decomposition over window W = [t₀, t₁]:
    Δ ln Π = c_n + c_L − c_K, with c_n = Δ ln n, c_L = Δ ln p̄ and c_K = Δ ln K.
  - Estimated in the fixed-footprint **core** C (c_K ≈ 0 by construction) and citywide.
- **RQ3 (price).** Does a flat permit subsidise size, and how big is that subsidy against the subsidy to parking at all?
  - **Estimand.** For car i: ρ_i = s · (L_i + g)/(L̄ + g) + (1 − s), its kerb use relative to the mean car. Opportunity
    value V_i = B · A · ρ_i, with A = 13.49 m² net zone area per stall and B the benchmark price per m² per year (§3).
    Subsidy S_i = V_i − P, where P is the permit price.
  - Level component S̄ = B·A − P. Size component S_i − S̄ = B·A·(ρ_i − 1).
  - **Ratio R** = E|S_i − S̄| / S̄ = E|ρ_i − 1| · B·A / (B·A − P), over the Prague-registered M1 fleet.
- **RQ4 (validation).** Does the EEA-based fleet-length model of Part II agree with the independent vehicle register,
  and where does the register put the years 2023–2025 that Part II had to extrapolate?
  - Estimands: Δ_RSV(2012→2022) and Δ_RSV(2022→2025), the change in the registration-weighted mean overall length of
    cars new to CZ.
- **RQ5 (elsewhere).** How do cities that price residential parking by size (length, footprint or weight) compare
  with Prague, per m² of kerb per year? Descriptive only.

## 2. Hypotheses, tests and decision rules

**One p-value per hypothesis; Holm step-down at family-wise α = 0.05 over H1, H2a, H2b, H3 and H4** (thresholds
0.010, 0.0125, 0.0167, 0.025, 0.05). RQ5 is descriptive and carries no test.

**Two kinds of p-value, stated plainly.**

- H2a and H2b are sampling-type questions about a trend estimated from a census of registrations. Their p-values come
  from a cluster bootstrap over car models, which treats model-level composition as the random element.
- H1, H3 and H4 are propagated-uncertainty questions: the data are near-censuses, and the uncertainty lies in the
  inputs (gap, parallel share, fleet ageing, the 2012 fleet). Their "p" is **P_MC**: the Monte Carlo probability of the
  null region under the input distributions in §5. It is calibrated only if those distributions are honest. It is put
  into Holm for discipline, not because it carries a frequentist guarantee.
- The referees are asked to judge this (Open question 1).

- **H1 (the size effect is small).** θ₁ < τ₁ = 3.7 % of capacity.
  - τ₁ is half the lower end of T&E's European projection pro-rated to 13 years: 0.5 × 8.5 % × 13/15. It assumes
    T&E's horizon is 2025 → 2040 **[verify base year]**.
  - Test: p = P_MC(θ₁ ≥ τ₁). *Supported* if p passes its Holm threshold.
  - τ₁ was set after Parts I–II (1.33–1.60 % central, 4.57 % at the top of Part I's grid).
- **H2a (validation, equivalence).** Δ_RSV(2012→2022) is within ±2.0 cm of Part II's EEA-derived +11.0 cm.
  - The margin equals the half-width of Part II's own ratio band (9.7–13.1 cm), so validation passes if the register
    agrees within the uncertainty Part II declared.
  - TOST: p = the larger of the two one-sided p-values from a studentised cluster bootstrap (clusters = make × commercial
    name, B = 9 999). +11.0 is treated as fixed.
  - The register and EEA cover largely the same cars. The test is of an independent *measurement* (overall length
    against wheelbase ÷ ratio), not of independent cars.
- **H2b (the missing years).** Δ_RSV(2022→2025) < 6.0 cm, the change T&E's series implies (4.32 m in 2022 by linear
  interpolation → 4.38 m in 2025).
  - One-sided, studentised cluster bootstrap as in H2a.
  - *Supported* means the Czech market did not follow T&E's acceleration, so Part II's lower band is the relevant one.
- **H3 (count, not size).** In the fixed-footprint core over the window W: c_n − c_L > 0. Car count raised kerb demand
  more than car length did.
  - n_t is an administrative count, used as observed, and its alternative definitions are robustness checks (R8).
    c_L carries the MC. p = P_MC(c_n − c_L ≤ 0).
  - Runs only if permit counts exist for the core over at least five consecutive years (DS6). Otherwise it is recorded
    as **not run**, or run as **H3-fallback**: citywide, n_t = M1 registered in Prague (data cube), reported as such,
    with zone expansion (c_K) reported alongside. Which one applies is fixed at the design stage, before any c_n is
    computed.
  - Part III's Praha 7 comparison makes the direction expected. The test is whether it holds when both terms are
    measured on the same area and the same years.
- **H4 (the size subsidy is second-order).** R < τ₄ = 0.10.
  - The size component of the subsidy averages less than a tenth of the level subsidy.
  - τ₄ follows Part III's framing ("a tenth of the price") and is disclosed as set after it.
  - p = P_MC(R ≥ 0.10) over s, g and fleet-bin placement.
  - Primary B: the city's own rate for reserving a parking place, 10 Kč / m² / day (§0). Primary P: 1 200 Kč. B, P and
    the fleet definition vary in R9.
  - Because B·A ≫ P, R ≈ s · E|L_i − L̄| / (L̄ + g) almost regardless of B. R is essentially a statement about how
    unequal car lengths are, measured on Prague's register.

Every hypothesis is reported whichever way it falls. The outcomes are "supported", "not supported", "not supported:
inconclusive" (TOST) and "not run". An H2a failure is a finding about Part II's method, and it is written as such.

## 3. Data and measures

**Supply (kerb).**

- Segment polygons, full geometry, from `gs-pub.praha.eu/arcgis/rest/services/dop/zony_placeneho_stani/MapServer/3`,
  one dated snapshot. The same layer as Part I, now per feature rather than aggregated. N₂₀₂₅ = 168 456 is re-derived
  from features, and any difference is reported.
- **Parallel share s (measured, replaces 0.68).** For each segment: length ℓ ≈ perimeter/2 and band width
  w ≈ area/ℓ (long thin rectangles).
  - w ∈ [1.6, 3.2] m → parallel; w ∈ [4.0, 6.5] m → perpendicular or angled; otherwise unclassified.
  - s is stall-weighted by PS_ZPS.
  - Accuracy is checked on a random sample of 200 segments labelled by hand on the IPR orthophoto **[verify current
    orthophoto year and licence]**. The labeller does not see the classifier output.
  - The confusion matrix feeds the MC for s: a Beta draw for each class's misclassification rate.
- **Supply over time (RQ2).** Stalls by district and zone type from TSK's *Ročenka dopravy*, each year 2012–2025
  (`www.tsk-praha.cz/o-nas/vyrocni-zpravy-a-rocenky/`). Whether the table exists for every year, and its definitional
  breaks, are checked in DS5.
  - **Core C:** districts whose December stall count in t₀ is at least 90 % of their count in t₁. This rule uses supply
    only.

**Demand (count), RQ2.**

- Primary: long-term parking permits (resident and abonent) valid on 31 Dec, by district, 2012–2025. Possible sources:
  a request under Act 106/1999, pending per `METODIKA.md` **[verify status]**; TSK's published 106 answers
  (`tsk-praha.cz/.../poskytnute-informace-as/`); district reports.
- Fallback: M1 vehicles registered in hl. m. Praha at year end, from the RSV data cube. The register is known to be
  inflated by leasing and company fleets registered at Prague addresses.
- Deník N's Praha 7 figure (280 a year) is used only as a cross-check.

**Car dimensions.**

- **RSV, Vozidla – technické údaje**, the monthly full export (`https://download.dataovozidlech.cz/vypiszregistru/
  vypisvozidel`), snapshot `RSV_vypis_vozidel_20260901.csv`, hashed at download.
  - Fields: `Celková délka/šířka/výška [mm]` (parsed from "L / W / H"), `Rozvor [mm]`, `Kategorie vozidla` (M1),
    `Datum 1. registrace`, `Datum 1. registrace v ČR`, `Rok výroby`, `Tovární značka`, `Obchodní označení`, `Status`,
    `PČV`.
  - Plausibility for M1: length 2 400–6 000 mm, width 1 400–2 300 mm, wheelbase 1 800–3 800 mm (Part II's range).
    Rows outside are counted and excluded.
  - **New to CZ** = first registration in CZ within 90 days of first registration anywhere. **Used import** = the rest.
  - The make is normalised as in Part II (`?KODA`).
- **RSV, Vozidla vyřazená z provozu**, the same portal, for deregistration spells (DS2).
- **RSV data cube** (`dataovozidlech.cz`): M1 counts in obec Praha and in CZ by 10 cm length bins (filter
  `karoserieDelkaOd/Do`) and 5 cm width bins.
  - Whether the location is the owner's or the operator's address, and how legal persons are placed, is **[verify]**.
    Nothing finer than the obec (no city district) appears to be available **[verify]**.
- **EEA** (Part II, unchanged): wheelbase series 2010–2022 for R1 and for DS8.
- **T&E (2026)** series (Part I) for R2.

**Fleet age.** Published mean ages 2014–2025 (ČSÚ, SDA via ČAPPO). The 2012 value is to be located in a primary
source (DS7). Until then it is an extrapolation, drawn in the MC (§5).

**Prices (RQ3, RQ5).**

- The TSK permit price list (§0), and OZV 16/2025 with its Annex 1 overrides for item (k).
- Other cities, from primary municipal sources, checked one by one before registration:
  - **Koblenz** (from 1 Mar 2024): length × width (registration fields 18/19) × 23.40 € a year, minimum 100 €
    (koblenz.de).
  - **Aachen** (from May 2025): 30 € per m² of footprint + 15 € fee **[verify, secondary source]**.
  - **Bonn**: footprint-based fee to 2026, then a flat 120 € from Jan 2027 **[verify]**.
  - **Köln** (from 1 Mar 2025): ≤ 4 109 mm 100 €, 4 110–4 709 mm 110 €, > 4 709 mm 120 €; no permit above 5 600 mm
    (stadt-koeln.de press release).
  - **Freiburg**: 240 / 360 / 480 € by length (≤ 4.20, 4.21–4.70, > 4.70 m). BVerwG 9 CN 2.22 (13 Jun 2023) annulled
    it: wrong legal form, inadmissible social discounts, and price jumps between length classes too large under
    Art. 3(1) GG. The 360 € level itself was not objected to.
  - **Tübingen**: weight surcharge (ICE ≥ 1 800 kg, EV ≥ 2 000 kg) **[verify current amounts]**.
  - **Lyon** (from 11 Jun 2024): resident permit by weight, 15 / 30 / 45 € a month **[verify on lyon.fr]**.
  - **Paris** (from 1 Oct 2024): visitor tariff tripled for ICE/hybrid ≥ 1.6 t and EV ≥ 2 t; residents exempt.
  - Converted to Kč per m² of kerb per year at the ECB reference rate of the registration date (fixed at
    registration), and with Eurostat PPS as a sensitivity check.

## 4. Models

**Fleet length L̄_t (RQ1, RQ2).**

- **2025, measured.** The registration-weighted mean length of M1 vehicles with status "provozované" **[verify status
  label]** in the snapshot. National (primary) and Prague (data cube bins; R5).
- **2012.** Chosen at the design stage by DS2:
  - **(a) Reconstructed:** if the register holds permanently removed vehicles with removal dates, the 2012 stock is
    every M1 first registered in CZ before 31 Dec 2012 and not removed by then. Its mean length is measured.
  - **(b) Modelled:** otherwise, a survival-weighted convolution of cohort lengths, as in Parts I–II. Cohort lengths
    come from the register (cars new to CZ, and used imports by year of import, weighted by their share of that year's
    registrations). Cohorts before 2010 are survivor-biased in a current export, so they are drawn in the MC between
    the survivor mean and the survivor mean minus the 2010–2012 new-car trend extended backwards.
- **Capacity.** The continuous pitch model is primary. The discrete segment model (Part I), with per-segment parallel
  classification, is R4.

**Monte Carlo (RQ1, RQ2, RQ3).** 20 000 draws, seed fixed at registration. Inputs:

| Input | Distribution |
|---|---|
| g | triangular (0.5, 0.82, 1.0) m |
| s | from the DS4 classifier and confusion matrix; if DS4 fails, uniform (0.50, 0.85) |
| 2012 mean age (route b) | normal (13.62, 0.25), truncated at ±3 SD, unless DS7 finds a published value |
| Age shape (route b) | Weibull k ~ uniform (1.5, 3.0) |
| Pre-2010 cohort lengths (route b) | uniform between the two bounds above |
| Post-2022 lengths | none: measured |
| b_⊥ | 2.5 m fixed (standard) |

- Sobol first-order and total indices (Saltelli estimator) show which input carries the variance of θ₁.

**H2a/H2b.** Registration-weighted mean length by cohort year y, over cars new to CZ. Δ is estimated from the two
year means. B = 9 999 cluster-bootstrap draws over make × commercial name, studentised, with the SE from an inner
jackknife.

**H3.** c_n is taken from the permit counts, c_L from the MC (fleet length in t₀ and t₁ on the chosen route), and c_K
from the yearbook stall counts.

**H4.** The distribution of L_i is the Prague 10 cm bins, with lengths drawn uniformly within bins. ρ_i and R are
computed per MC draw.

**What is not modelled.** Occupancy, cruising, turnover and where visitors park. No causal effect of price on
ownership is estimated.

## 5. Design-stage checks (before any outcome is computed)

Each check records its result, and any pre-committed consequence, under "Changes after registration", before
estimation.

- **DS1. Register parse.**
  - M1 row count and status distribution.
  - Share of rows with a parsable length, by cohort year, 2005–2025.
  - Counts of cars new to CZ by year against the EEA counts (§0). This compares counts only, not dimensions.
  - Consequence: if coverage of any year 2012–2025 is below 90 %, H2a/H2b reweight by make × model × year to the EEA
    counts (2012–2022), or to the register's own count of new registrations (2023–2025), and are flagged.
- **DS2. Removed vehicles.** Does the export keep permanently removed vehicles, and with a date? This decides route (a)
  or (b) for 2012.
- **DS3. Data cube semantics.** The location basis (owner or operator), legal persons, the availability of a time
  dimension (stock at past dates) and of length bins. This decides the H4 fleet and the H3 fallback.
- **DS4. Parallel classifier.**
  - Build it, hand-label 200 segments blind, report the confusion matrix.
  - Consequence: if overall accuracy is below 80 %, s reverts to the uniform prior and the failure is reported.
- **DS5. Yearbook series.** Stalls by district, 2012–2025, and definitional breaks (e.g. the "Ostatní" column). This
  fixes W and C.
- **DS6. Permit counts.** Source, definition (valid at year end or issued; resident or abonent; the end of transferable
  permits in 2024) and years covered. This decides H3 or H3-fallback.
- **DS7. Mean age 2012.** Search SDA/ČAPPO archives for a published 2012 value, and replace the prior if found.
- **DS8. Precision.**
  - For H2a/H2b, the cluster-bootstrap SE of a change in mean wheelbase is taken from the EEA model-level file (already
    seen) and converted to length at r = 0.618. It gives the minimum detectable Δ at 80 % power and the TOST power at a
    true difference of 0.
  - For H1, H3 and H4, the prior-predictive spread uses the input distributions only, with no outcome data.
  - Consequence: if the TOST power for H2a is below 50 %, H2a is still run, and "inconclusive" is read as
    underpowered, not as disagreement.
- **DS9. Prices.** Read OZV 16/2025 Annex 1 for district overrides of item (k), and the primary municipal sources for
  RQ5. Every [verify] in §3 is resolved or the entry is dropped.

## 6. Robustness checks (reported, not in the family)

1. **R1, the EEA route.** Part II's wheelbase series with the ratio recalibrated on Czech register cars that have both
   length and wheelbase (the median and IQR of W/L by cohort), in place of 0.618.
2. **R2, the T&E route.** Part I's series.
3. **R3, the fixed parallel share.** s = 0.68 (Part I and II) against the measured s.
4. **R4, the discrete model.** The Monte Carlo over real segment sizes, with per-segment classification.
5. **R5, the fleet definition.** National against Prague-registered; excluding legal-person registrations if DS3 allows;
   excluding used imports.
6. **R6, age shape** (route b): Weibull k = 2 against exponential and uniform, as in Part I.
7. **R7, the gap.** 0.5 / 0.82 / 1.0 m fixed; gap proportional to length (T&E's constant ratio) against a constant gap.
8. **R8, the decomposition.**
   - Permits gross issued, valid at year end, or resident only.
   - Core thresholds of 80 / 90 / 100 %.
   - W trimmed by one year at each end.
   - The citywide version.
9. **R9, the subsidy.**
   - B: the OZV rate, the second-car price (7 000 Kč), the abonent price, PAQ's 6 000 Kč **[verify]** or the visitor
     tariff × hours occupied (declared at registration).
   - P: 1 200 (core), 600 (outer sub-areas), 360 (65+), zero-emission −50 %.
   - The sharing factor (stalls ÷ permits), because a permit is a licence to search, not a bay.
10. **R10, the area model.** Part I's footprint model, and the width encroachment re-measured with register widths.
11. **R11, sensitivity decomposition.** Sobol indices for θ₁ and for c_n − c_L.
12. **R12, the 2018 check.** H2a with 2018 dropped, the year of the `?KODA` fault in EEA.
13. **R13, specification curve** over:
    - {route a/b}
    - {s measured / 0.68 / uniform}
    - {g triangular / fixed}
    - {national / Prague fleet}
    - {continuous / discrete}

    The share of specifications that support H1 and H3 is reported.

## 7. Limitations (stated in the article)

- **Counterfactual.** θ₁ holds today's kerb fixed. It is not the history of Prague's stall count.
- **Marked bays.** Where bays are painted, a longer car does not reduce the count, it overhangs. The pitch model
  applies to unmarked kerbs. Which Prague segments are painted is not in the data **[open question 3]**.
- **Registered is not parked.** The register describes cars registered in Prague or in CZ, not the cars in the zones.
  The parked fleet could be measured only by joining TSK's camera-car plate reads to the register, which is not open
  data.
- **Survivorship.** Old cohorts in a current export are survivors. Route (b) brackets them, and does not identify them.
- **Gap.** No Prague measurement exists. Berlin's pitch sets its centre.
- **Permits ≠ cars on the street.** Permits count entitlement, not presence. Business and visitor demand are outside n.
- **Price benchmark.** The OZV rate prices exclusive 24-hour use. A permit is shared, and not guaranteed. R is robust
  to B, the level subsidy is not.
- **No behaviour.** Nothing here estimates how drivers respond to price or size.

## 8. Deliverables

- `tools/parking6/` in this repo: `parking6_data.py` (downloads, hashes, parsing), `parking6_design.py` (DS1–DS9),
  `parking6_estimate.py` (H1–H4, MC), `parking6_robust.py` (R1–R13), `parking6_figures.py`. The repo
  `~/Downloads/parking/` is read-only and is imported or copied, never modified.
- `assets/parking6/*.json` and figures.
- `texts/prague-parking-study.html`: Part 6, the long version, in the form of `texts/prague-rings-study.html`.
- This file, and `docs/research/prague-parking-files.sha256` at registration.

## Appendix A. Raw files at this draft (SHA-256)

Stored in `tools/data/parking6/` (gitignored). The full list, including the RSV export and the segment geometry, is
committed at registration.

```
1f48e4c12f60b24a37fa1a137ae483ede05e17e5aa329cc5e559330ffecb75f0  RSV_vypis_vozidel_20260901_header.csv
b2bea8b9a2cf7bdcc0ffa66164ec6ab5a2541037e2fe152cac7eeeb6f9e124fe  TSK-Rocenka-dopravy-za-rok-2024.pdf
```

## Appendix B. Literature the article will engage

- **Pricing kerb space.**
  - Shoup, D. (1997): The high cost of free parking. *Journal of Planning Education and Research* 17(1), 3–20.
  - Shoup, D. (2005; updated 2011): *The High Cost of Free Parking*. APA Planners Press.
  - Shoup, D., ed. (2018): *Parking and the City*. Routledge.
  - Pierce, G., Shoup, D. (2013): Getting the prices right. *Journal of the American Planning Association* 79(1),
    67–81.
- **Residential permits and on-street parking.**
  - van Ommeren, J., de Groote, J., Mingardo, G. (2014): Residential parking permits and parking supply. *Regional
    Science and Urban Economics* 45, 33–44 **[verify pages]**.
  - Molenda, I., Sieg, G. (2013): Residential parking in vibrant city districts. *Economics of Transportation* 2(4),
    131–139 **[verify]**.
  - Inci, E. (2015): A review of the economics of parking. *Economics of Transportation* 4(1–2), 50–63.
  - van Ommeren, J., Wentink, D., Rietveld, P. (2012): Empirical evidence on cruising for parking. *Transportation
    Research A* 46(1), 123–130.
- **Car size.**
  - Transport & Environment (2026): *Ever-bigger? Car size at a crossroads*.
  - Transport & Environment (2024): *Width limit for light duty vehicles*.
  - ICCT, *European Vehicle Market Statistics* pocketbook, footprint series **[verify edition]**.
  - Holder, D. et al. (2021), ICED21.
- **Monitoring.** Regulation (EU) 2019/631; EEA CO₂ monitoring (Discodata).
- **Method.**
  - Holm (1979).
  - Schuirmann, D. J. (1987): A comparison of the two one-sided tests procedure … *Journal of Pharmacokinetics and
    Biopharmaceutics* 15(6), 657–680.
  - Cameron, Gelbach, Miller (2008).
  - Saltelli, A. et al. (2008): *Global Sensitivity Analysis: The Primer*. Wiley.
- **Law and practice.** BVerwG 9 CN 2.22 (2023); OZV hl. m. Prahy 16/2025; the TSK price list; Deník N (Vodrážka,
  22 Sep 2026).

## Open questions for the referees

1. Is putting Monte Carlo "p-values" (P_MC under stated input distributions) into a Holm family defensible? Or should
   H1, H3 and H4 be framed as pre-registered interval rules (e.g. "97.5 % MC upper bound below τ") outside the family,
   leaving H2a/H2b as the only frequentist tests?
2. Are the thresholds acceptable, given that they were set after Parts I–III: τ₁ = 3.7 % (from T&E's headline) and
   τ₄ = 0.10 (from Part III)? Is ±2 cm, Part II's own band, the right margin for H2a?
3. Marked against unmarked bays: should RQ1 be restricted to unmarked kerb? Is there a way to tell painted segments from
   the data (the orthophoto sample in DS4)?
4. Is the 2012 fleet better reconstructed from the register (route a, with the survivorship of old cohorts) or
   modelled (route b)? Is the pre-2010 cohort bracket reasonable?
5. Is the OZV reserved-place rate an acceptable primary benchmark B for the level subsidy, or should the level be
   benchmarked against market garage rents (not open data) or the visitor tariff?
6. H3 depends on permit counts that may not exist for enough years. Is the fallback (Prague-registered M1, citywide)
   informative enough to keep H3 in the family, or should the fallback be descriptive only?
7. Should an orthophoto audit of the gap g (cars and kerb length on a sample of segments) be added at the design stage?
   It would replace the Berlin-derived centre of the prior.

## Changes after registration

(none yet)
