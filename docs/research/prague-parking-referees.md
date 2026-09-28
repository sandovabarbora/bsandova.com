# Part 6 parking: referee reports on design draft v1 (28 Sep 2026), consolidated

Three referees reviewed the draft: transport economics, statistics and a data audit. Their must-fix points agree, and
are merged below. The author revises the design to v2 against this list and records, item by item, what was
done.

## A. Family and status of claims (all three referees)

1. **Monte Carlo probabilities.** P_MC is prior mass under the chosen input distributions, not a p-value, so it does
   not go into Holm.
2. **Confirmatory family.** H2a and H2b only, Holm at 0.05.
3. **H1, H3 and H4 become pre-specified estimates** with reporting rules written now, results-blind.
   - They are reported as median and 2.5–97.5 % "uncertainty interval under the registered input distribution".
     Never "CI" or "p".
   - The Monte Carlo standard error of the quantiles is reported. P_MC is reported as (k+1)/(M+1).
   - Each also gets a tipping-point line: the smallest input change that reverses the headline.
4. **Predictability rule.** A claim whose prior-predictive probability of being "supported" exceeds 0.95 before any
   outcome data is reported as descriptive.
5. **Wording.** In the article, say "registered analysis plan", not "pre-registered study". §0 states that for H1, H3
   and H4 the direction, and for H1 and H4 the size, are known from Parts I–III.

## B. H1 / RQ1

1. **Unit mismatch.** T&E's 8.5–14 % is a share of *parallel* spaces, while θ₁ is a share of all stalls (already × s).
   The threshold τ₁ also rests on a headline that Part I could not reproduce (3.4–4.0 % from T&E's own parameters),
   and pro-rates a forward projection backwards.
2. **Design-stage arithmetic.** θ₁ ≥ 3.7 % needs about 17.5–22 cm of fleet-mean growth.
3. **Replacement.** A banded reporting rule: <1 % / 1–2.5 % / 2.5–5 % / straddles, with the sentence for each band
   written now. θ₁/s is compared with T&E's per-parallel rate and with the 3.4–4.0 % reproduction.
4. **Define N₂₀₁₂** as a counterfactual: N₂₀₁₂ᶜᶠ = N₂₀₂₅·[1 + s((L̄₂₀₂₅+g)/(L̄₂₀₁₂+g) − 1)].
5. **Primary estimand.** θ₁ᵘ on *unmarked* parallel kerb, anchored on kerb length ℓ.
   - Painted bays lose capacity only for the fleet tail longer than the bay length minus 0.5 m.
   - Identify painted bays from the ℓ/PS_ZPS clustering, the orthophoto sample and the TSK marking inventory.
   - Report stalls as "administrative stalls" if PS_ZPS is a nominal count; θ₁ in % is primary.

## C. H2a / H2b (the only confirmatory tests)

1. **Margin.** Part II's band 9.7–13.1 cm has a half-width of 1.7 cm, not 2.0, and is asymmetric. Set the margin by
   consequence instead:
   - δ = the change in new-car length over 2012–2022 that moves θ₁ by 0.25 pp;
   - compute it at design stage through the fleet transfer coefficient κ, from constants only;
   - state it as a fixed, symmetric value.
2. **Conversion.** Use the register's *marginal* length-on-wheelbase slope, estimated within model lines, not the
   average ratio r.
3. **Survivorship.** Post-stratify register cohort lengths unconditionally by EEA registration shares, in
   make × commercial-name × year cells.
   - Cells with no survivors are imputed from adjacent years, and the imputed weight is reported.
   - All statuses are kept, including ZÁNIK and VÝVOZ; no status filter.
4. **Estimator.** Fit the trend over 2012–2022, not endpoint means.
   - Paired cluster bootstrap by normalised model line, using a frozen normalisation dictionary.
   - Report the Kish effective number of clusters. If it is below 30, use a wild cluster bootstrap.
   - Report leave-one-model-out influence (the Octavia alone is about 12 %).
   - Run a size check by simulation at Δ = ±δ.
5. **H2b as a forecast contest.** Part II predicted +3.0 cm for 2022→2025 and T&E +6.0 cm.
   - Classify by the 95 % interval against the 4.5 cm midpoint.
   - The one-sided test against 6.0 stays in the family.
   - Note that T&E's figures are rounded (about ±0.7 cm).
6. **Fleet definition.** M1 + M1G, with N1 as a sensitivity. The EEA pipeline dropped M1G, which was 0.2 % of
   registrations in 2012 and about 6 % in 2021–22 (2016 is a coding break). Re-pull the EEA series with
   Ct IN ('M1','M1G').
   - This changes Part II's comparator. Record it; a correction to Part II follows if its numbers change.
7. **Register traps.**
   - Length 0 means missing, and 0/0/0 appears in 47 % of legacy rows.
   - Some dimension triplets are shifted between fields.
   - 57 % of first-registration dates are 1 January (imputed), which breaks any 90-day "new to CZ" rule.
   - Cohort coverage by manufacture year is reported (DS1) before any value is read.
   - Missing lengths are handled by multiple imputation (make × model × year), nested in the Monte Carlo.
   - DS1 needs the FULL export, about 11–12 GB. The file is sorted oldest first and the server has no range requests.

## D. Fleet route and ages

1. **Route (a) is not feasible.** ZÁNIK has no date, and the deregistration dataset starts in July 2012 with the
   2012–15 phantom clean-up. Commit to route (b) now.
2. **Same route at both ends.** Use route (b) for 2012 *and* 2025. Measured-minus-modelled for 2025 is a calibration
   diagnostic, with a pre-registered rule if it exceeds 2 cm.
3. **Mean age 2012.** Replace the Normal(13.62, 0.25) prior with an SDA-only back-extrapolation (2016–2019 slope),
   a source-offset term and a residual term; or a uniform(13.3, 14.1).
   - Add a definitional shift common to both years.
   - Add an R-check on the STK-active fleet (13.79 against 16.41 years in 2024).
4. **Cohorts.** Weight by manufacture year, blending new and used imports. Weight by entry size × survival,
   because registrations grew from 165k to 230k a year.
5. **Pre-2010 survivor bracket.** Two-sided and symmetric, with the formula written out.
6. **New check DS10.** Validate the reconstructed stock against the published 2016–2019 counts and mean ages, with
   pre-committed tolerances.
7. **New check DS11.** A blind dry run with permuted lengths, and a code hash before real outcomes.

## E. Inputs and sensitivity

1. **Gap.** The gap g = 5.20 − 4.38 subtracts a new-car length from a pitch observed on the parked fleet, which
   implies about 1.0 m.
   - Parametrise by the reference pitch p ~ triangular(4.9, 5.2, 5.5) and derive g in each draw.
   - Treat gap-law choices as a structural switch.
   - Optional: an orthophoto pitch measured on saturated runs.
2. **Correlated inputs.** Shared cohorts and the Weibull k are common to both years in each draw. Use Shapley effects
   or grouped Sobol, not independent-input Sobol.
3. **Parallel share s.** TSK's source data carry the stall type (TYPSTANI) and validity dates.
   - Ask TSK (Act 106/1999) for the full IS ZPS segment export. Until it arrives, validate the geometry classifier on
     the 1 593 labelled 2019 segments (`tools/data/parking6/zpsmap/`).
   - Fix the width formula: solve the quadratic from area and half-perimeter; perimeter/2 = length + width.
   - Sample stratified by predicted class, PPS on stalls, using a PPV-based ratio estimator. Fall back to the prior only
     if the interval of ŝ is wider than the uniform's.
   - Record painted/unmarked and angled in the same pass.
4. **Supply is live.** The layer drifts: 168 424 stalls today against 168 456 twenty days ago. Snapshot and hash it,
   and call it a September 2026 state, not N₂₀₂₅.

## F. RQ2 / H3 (count vs length vs zones)

1. **Descriptive.** Estimate the share c_L/(c_n+c_L) with its interval, plus c_K.
2. **Core definition.** Symmetric: |ln(N_t1/N_t0)| ≤ 0.02, using the yearbooks' stalls by district for 2012–2024. The
   core is P1, P2, P3 and P7. Treat "Ostatní" and the 2016–18 scheme change as breaks.
3. **Permits.** No public series by year. The only public anchor is 215 108 valid permits on 1 May 2026, from TSK's
   answer to an information request. Year-end counts by category and district can be requested (Act 106/1999). The
   request is for the author of the study (Bára) to send; do not send it.
4. **Rule-change dates.** Transferable permits ended in 2024. Free EV parking ended 30 Jun 2025, and EL-plate cars
   pay from 1 Jan 2026. Hybrids got 100 Kč permits in 2018. A virtual-address rule also applies.
5. **Fallback.** The Prague-registered fleet is descriptive only, because of leasing and company fleets. The cube's
   "territory" may be the registration office, and since June 2017 registration can be done at any office.

## G. RQ3 / H4 (subsidy)

1. **Descriptive.** R is small by construction whenever B·A ≫ P.
2. **Size component.** In Kč per kerb-metre per year, plus a revenue-neutral length schedule over the fleet.
3. **Level component.** A bracket, never one number:
   - the city's second-car price, 7 000 Kč (lower);
   - land rent × 4 % (central);
   - off-street garage rents from a dated snapshot (upper-middle);
   - the OZV public-space fee (upper; an administrative ceiling for exclusive 24 h use, not an opportunity cost).
4. **Language.** Say "implicit subsidy (forgone rent)". Never headline a single Kč figure.
5. **Prices by area and user.** The published texts were corrected on 28 Sep 2026: 1 200 / 600 / 360 Kč, 7 000 Kč for
   a second car, −50 % for zero-emission cars from 2026. Use the permit-mix-weighted price, or state "core first-car
   case".

## H. Other cities (RQ5)

1. **Köln** is a red flag: its 4 109 / 4 709 mm class limits sit a millimetre from this series' Fabia and Kodiaq.
   Verify on stadt-koeln.de or drop it.
2. **Paris** prices visitors, not residents; list it separately.
3. **Weight-based schemes** go in their own row group, in their own units.
4. Everything unverified stays marked, or is dropped.

## I. Privacy and data handling

- **Personal data.** The owner/operator dataset holds birth dates and home addresses in about 25 % of type-3 rows.
  The 20 MB sample was deleted. Never download, process or commit personal fields. Use only aggregate or legal-person
  data.
- **Snapshots.** Hash every snapshot. The design's §0 must list every file opened.

## J. Framing

- Phrase every headline as a counterfactual ("on today's kerb, 2012's cars would fit about X more").
- Round to hundreds.
- No mirror-width claim.
- Right of reply to T&E, TSK and PAQ is for Bára to send, not for the author.
