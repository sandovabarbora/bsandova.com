# Prague votes in rings: research design (Part 2, extended)

**Status: pre-specified analysis.** Version 2, after review by three independent referees (statistics, electoral
geography, census data). Written before any model below is estimated; first committed at 1283162 on 28 September
2026, in the same commit as the results, so its timing is self-reported. The author has worked with Prague's precinct and housing
data since May 2024 (§0). Deviations are listed, dated, in "Changes after registration".

## 0. What has already been seen

The author has worked with Prague's precinct and housing data since May 2024. The plan sets the analysis in advance; the author already knew the data.

**Part 2 (published).** 2025 Chamber election, Prague precincts, with three precinct measures: distance to the
nearest metro station, distance from Můstek, and the share of flats in panel buildings (RÚIAN). Stated here per
doubling of distance (natural-log coefficient × ln 2):

- ANO's share rises with panel share (r = 0.70) and with distance from the centre (r = 0.54). Metro distance r = 0.19.
- WLS (weights = valid votes, HC1):
  - ANO: +0.90 pp per 10 pp panel [0.80, 0.99]; +1.97 pp per doubling of centre distance [1.53, 2.42]; metro −0.05 pp
    per doubling [−0.28, +0.19]; R² 0.56.
  - The Pirates follow the centre; SPOLU follows family houses.
- Turnout is lowest within 2 km of the centre (66.8 %) and about 73 % beyond 4 km.

**Census grid.** 580 cells intersect Prague (529 populated). The median
precinct is 0.12 km², about an eighth of a cell. Precincts draw composition from about 285 distinct dominant cells.
Education "not stated" (field 025) is 6.3 % of the education total and correlates 0.57 with the foreign share.
Suppression (026) affects 17 cells with 68 residents. Field 081 ("registered in the same obec") treats Prague as a
single obec (90.6 %). 33 300 flats (4.5 %) were completed after the census date.

Because Part 2's metro and panel estimates are known, H2 is a test of whether a known null **survives** the
composition controls. It is not an independent discovery. All 2025 conclusions are replicated on 2021 (§2, H5).

## 1. Research questions and estimand

- **RQ1 (place or people).** Is the association between panel housing and the ANO vote accounted for by who lives in
  panel estates (education, citizenship; then age)?
- **RQ2 (the metro).** Once composition, the centre and the housing stock are known, is metro proximity associated
  with the vote?
- **RQ3 (change).** Has the housing-estate gradient of the ANO vote steepened between 2017 and 2025?
- **RQ4 (turnout in the centre).** Is the centre's low registered turnout a property of registration, i.e. of who
  is on the register, rather than of the residents' propensity to vote?

**Estimand.** The coefficient on panel share conditional on composition is a descriptive, controlled association:
the difference in vote share between areas with equal measured composition and different housing stock. It is not a
causal effect of the estates. Age structure in the estates is partly a product of the housing stock (cohort
allocation in the 1970s–80s, ageing in place), so controlling for age may over-control. The **primary composition
block is education + citizenship**. Age is added in a second step and reported descriptively.

## 2. Hypotheses, tests and decision rules

**One p-value per hypothesis; Holm step-down at family-wise α = 0.05 over H1b, H1b′, H2, H3, H4a, H4b.**
H1a is a manipulation check outside the family. H5 is a replication, reported without a test.

- **H1a (manipulation check).** The tertiary-education share has a negative coefficient for ANO.
- **H1b (composition, ANO).** Let β₀ be the panel coefficient without composition and β₁ with the education +
  citizenship block, both estimated on the identical sample. Attenuation θ = 1 − β₁/β₀.
  - Test: H0: θ ≤ 0.5 against H1: θ > 0.5, via δ = β₁ − 0.5·β₀ < 0, one-sided.
  - The variance of δ comes from a wild cluster bootstrap by city district (Webb weights, B = 9 999) that
    re-estimates both models in each draw.
  - Three outcomes are declared in advance:
    - **"composition"**: H1b is supported.
    - **"place beyond composition"**: the one-sided test of θ < 0.5 rejects **and** β₁ > 0 at 5 %.
    - **"indeterminate"**: neither.
  - The attenuation is split across covariates with Gelbach's (2016) decomposition.
- **H1b′ (composition, SPOLU bloc).** The same test for the SPOLU bloc's panel coefficient (negative in Part 2).
  Here θ is defined on the absolute value.
- **H2 (metro, equivalence).** γ = coefficient on log₂(metro km) in the full model (§5).
  - Smallest effect of interest (SESOI): ±0.25 pp per doubling. Across the interquartile range of metro distance
    (about 2 doublings) that is 0.5 pp, 2.5 % of ANO's Prague share, and under an eighth of the centre gradient.
  - TOST using the **largest** standard error among HC1, Conley (1.5 km) and wild cluster bootstrap.
  - p = the larger of the two one-sided p-values. *Supported* if it passes its Holm threshold.
  - The margin was set after Part 2 (§0).
- **H3 (steepening).** In a pooled model of matched precincts (§4) with panel × year interactions, the ANO panel
  coefficient is larger in 2025 than in 2017.
  - One-sided Wald test on the interaction.
  - Composition is not included, because the census is from 2021.
- **H4a (registration, not residents).** The centre gradient (log₂ distance from Můstek) of *resident turnout*,
  envelopes / Â (§3), is smaller in absolute value than that of *registered turnout*, envelopes / registered voters.
  - One-sided test on the difference of the two coefficients, estimated jointly (stacked, cluster bootstrap as in H1b).
- **H4b (non-resident registrants).** In log E = a + b·log R + c·log Â + controls (E = envelopes, R = registered),
  b < 1: registrants not accounted for by residents add less than one proportional voter.
  - One-sided test of b = 1.
  - The descriptive regression of E/R on R/Â is reported but is not confirmatory, because the two share R
    (ratio bias).
- **H5 (replication, no test).** H1a, H1b, H1b′ and H2 are re-estimated on the 2021 election. Disagreements between
  2021 and 2025 are reported, and neither year is given priority.

Every hypothesis is reported whichever way it falls; "not supported" and "indeterminate" are written as such.

## 3. Data and measures

**Votes.** ČSÚ precinct results for the Chamber elections of 2017, 2021 and 2025. Party series are built so the same
electorate is compared in every year:

| Series | 2017 | 2021 | 2025 |
|---|---|---|---|
| ANO | its own list | its own list | its own list |
| SPOLU bloc (labelled "constructed" for 2017) | ODS + TOP 09 + KDU-ČSL | SPOLU list | SPOLU list |
| Pirates+STAN bloc | Pirates + STAN | PirSTAN list | Pirates + STAN |
| Pirates alone | – | – | 2025 only |

- The 2021 coalition thresholds (8 % and 11 %) invite strategic voting, so bloc changes are not read as realignment.
- Whether other parties' candidates stood on the 2025 lists (e.g. Greens on the Pirate list) is checked in the
  candidate register before estimation and recorded.
- Turnout = envelopes issued / registered voters.

**Housing.** RÚIAN buildings: `pocetbytu` (flats), `druhkonstrukcekod` ∈ {4, 41} = panel, `zpusobvyuzitikod` = 7
(rodinný dům) = family house, `dokonceni` (completion date).

**Composition.** Census 2021 1 km grid (ČSÚ). Its cells are INSPIRE EPSG:3035 cells distributed in EPSG:5514;
precincts (WGS84) are projected to EPSG:5514 and all overlays are done in EPSG:5514.

- **Education shares** use the 25+ residents with stated education (021–024) as the denominator. The share not stated
  (025) enters as a covariate. Whether 024 includes higher-vocational (VOŠ) is verified from ČSÚ metadata, and the
  label is set accordingly.
- **Foreign share** = (051 + 053 + 054) / 000, with 054 (citizenship not stated) named explicitly.
- **Age shares** = 011 and 013 over 000.
- Omitted reference categories: maturita, Czech citizens, age 15–64. Coefficients are substitution effects against
  these.
- The shares are of residents, including non-citizens. As a robustness check, they are recomputed with foreign
  residents removed proportionally.

**Grid → precinct allocation (dasymetric).**

- Each cell's counts go to the precincts it overlaps in proportion to RÚIAN flats in buildings completed on or before
  26 March 2021 (building point location). Buildings with no completion date are kept.
- Cells with no flats, or fewer than 1 flat per 4 residents: allocate by residential and accommodation buildings (use
  codes 3, 6, 7 and care/accommodation uses), otherwise by area. No populated cell is dropped, and the population so
  allocated is reported.
- Cells crossing the Prague boundary: the flat denominator includes flats outside Prague (Středočeský kraj buildings
  are downloaded for this), and only the in-Prague share is allocated.
- Allocated totals are checked against Census 2021 usual residents by ZSJ part. Precincts deviating by more than 25 %
  are flagged (robustness 10).

**Resident-adult estimate Â (RQ4).**

- Per cell: Czech 18+ = g050 × (g012 + g013) / g000 × (1 − s), where s = Prague share of 15–17 year-olds in 15+.
  Applying s uniformly is a stated limitation.
- Allocated as above, then increased by the flats completed 27 March 2021 – 3 October 2025 in the precinct, times
  Prague's Czech-18+ per flat in buildings completed 2016–2021.
- Field 081 is **not** used, because it treats Prague as one obec.

**Flags set before estimation (from RÚIAN and official lists, never from outcomes).**

- Precincts containing a district registration-office address (ohlašovna). Citizens without a real address are
  registered there.
- Precincts containing hospitals, care homes, dormitories or prisons (RÚIAN use codes).
- New-build precincts: more than 10 % of their flats completed after the census.
- H4a and H4b are confirmatory **without** the ohlašovna and institutional precincts, and reported with them.

**Framing (article).** A register ratio above 1 reflects Czech permanent-residence law. Trvalý pobyt is an
administrative address, not a residence, and people without one are registered at the town hall. It is not evidence
of irregular voting.

**N.** Polygons: 1 120 (current). Precincts in the 2025 results: 1 119. Precincts with flats: 1 118. Every join loss
is reported.

## 4. Matching across elections (RQ3)

Open 2017/2021 precinct geometry is not published. Before relying on the rule below, ČÚZK RÚIAN change files are
checked for VolebníOkrsek geometry valid on 20 Oct 2017 and 8 Oct 2021. If found, that geometry replaces the rule.

**Rule.** A precinct is matched if its (district code, number) exists in 2017, 2021 and 2025, and the observed
register change between consecutive elections is within ±10 % of the change predicted from new flats. Predicted
change = (pre-existing + newly completed flats inside the current polygon) / pre-existing flats × the Prague-wide
register change.

**Reported with the rule:**

- The share matched.
- Matched and unmatched precincts compared by panel share, distance and 2025 vote.
- Sensitivity: thresholds of 5 % and 20 %, and inverse-probability weights for being matched (logit on panel share,
  log centre distance, house share).
- The 57-district comparison, noting that aggregation inflates correlations.

## 5. Models

**Main unit (H1, H2, H4): the grid cluster.** Each precinct is assigned to the cell holding the largest share of its
pre-census flats. Votes, valid votes, registered voters, envelopes, flats, panel flats and house flats are summed
within each cluster. Housing and composition are then measured at the same resolution (about 285 clusters).
Distances are the flat-weighted mean of the precincts' log₂ distances.

- **Estimator.** WLS, weight = valid votes (the voter-weighted association); unweighted OLS reported alongside.
  Regressors: panel share, family-house share, log₂ distance from Můstek, log₂ distance to the nearest metro station,
  composition block.
- **Inference.** Wild cluster bootstrap by city district (Webb, B = 9 999, restricted). CR2 (Bell–McCaffrey) with
  Satterthwaite df as a second method, and the effective number of clusters G* reported.
- **Spatial.**
  - Conley spatial-HAC SEs (Bartlett, 1.5 km; sensitivity 1 and 3 km).
  - Moran's I of residuals (queen contiguity of cluster polygons, k = 4 nearest neighbours for islands, 999
    permutations) is reported.
  - A spatial error model (unweighted ML) is robustness, with the Pace–LeSage Hausman test. A significant difference
    is read as an omitted spatial variable, not as grounds to switch estimates.
  - SAR/SLX, if shown, are reported as impacts.
- **Precinct level (robustness).** The same models on 1 118 precincts, with standard errors clustered by dominant
  cell. Composition is coarser than housing here, so adjusted panel coefficients are upper bounds.

**Design-stage power (§5a), before outcomes enter the model frame.**

- VIFs and the condition number of the realised design are reported.
- Minimum detectable effects at 80 % power for H1b (θ), H2 (equivalence margin), H3, H4a and H4b, using the Part 2
  residual variance as an upper bound.
- If any VIF > 10, or the H1b minimum detectable θ exceeds 0.3, this is recorded under Changes before estimation.
  The pre-committed consequence: H1b is reported as underpowered, not as "place".

## 6. Robustness, placebo and specification checks (reported, not in the family)

1. Unweighted OLS.
2. Fractional logit (Papke–Wooldridge), reporting average marginal effects in pp.
3. Excluding precincts whose RÚIAN version postdates 1 December 2025. Every current version postdates the election,
   so this cannot rule out earlier redrawing.
4. Excluding precincts with fewer than 300 registered voters.
5. Leave-one-district-out: the largest change in each confirmatory coefficient.
6. Panel = code 4 only.
7. Allocation by area instead of flats.
8. Excluding cells with more than 10 % education not stated, and cells with fewer than 50 residents.
9. Composition recomputed without foreign residents.
10. Excluding precincts flagged by the ZSJ check (§3).
11. Homogeneous cells only: clusters whose cell panel share is below 0.2 or above 0.8.
12. **Placebo metro:** distance to planned, not yet open, line D stations. It should be equivalent to zero under the
    same TOST. Run only if official station coordinates are published; otherwise recorded as not run.
13. **Placebo shuffle:** panel share permuted within districts (1 000 draws). The attenuation statistic's null
    distribution should be centred on zero.
14. **Specification curve** over:
    - {weighted, unweighted}
    - {flats, area allocation}
    - {panel 4 / 4+41}
    - {all, ≥ 300 registered, homogeneous}
    - {cluster bootstrap, Conley}

    The share of specifications supporting each confirmatory conclusion is reported.

## 7. Limitations (stated in the article)

- **Ecological inference.** Associations between areas do not show how individuals vote (Robinson 1950).
- **Resolution.** A 1 km cell is about eight times the median precinct, so composition is nearly constant within the
  centre and within large estates. Measurement error in composition biases the adjusted panel coefficient away from
  zero. A "place" result is therefore an upper bound on the place effect, and a "composition" result is conservative.
- **Timing.** The census was taken in March 2021, four and a half years before the 2025 election, and during
  distance teaching, so student areas may be under-counted. It also predates the refugees who arrived from 2022.
- **Boundaries.** RÚIAN keeps only the current precinct polygons.
- **Coverage.** Composition covers residents, not voters.
- **Causality.** No causal effect is identified.

## 8. Deliverables

- `tools/praha/rings_extended.py`, which produces every number.
- `assets/praha/rings_extended.json`.
- An extended article: literature, methods, results table, robustness table and specification curve, limitations.
- This file.

## Appendix A. Raw files at registration (SHA-256)

See `docs/research/prague-rings-files.sha256`, committed with this file.

## Changes after registration

- 2026-09-28, before any estimation: the publication-timing rule (publish only after the 2026 municipal polls
  close) is dropped at the author's decision. It concerned publication, not analysis; the register-ratio framing
  rule in §3 stays.

### 2026-09-28, design stage (covariates only; no 2017, 2021 or new 2025 outcome joined)

Built by `tools/praha/rings_data.py`, report in `tools/data/praha2x/design_report.json`; checks by
`tools/praha/rings_power.py`, output committed as `docs/research/prague-rings-power.json`.

**Resolved open points.**

- Field 024 is "higher vocational or university" (ČSÚ alias), so the education label is *tertiary incl. VOŠ*.
- The 2025 Pirate list in Prague was nominated by the Pirates alone (36 candidates: 30 Pirates, 5 non-partisans,
  1 Green, the Greens' co-chair, 12th on the list and elected). The Greens ran no list of their own. "Pirates alone"
  2025 therefore includes the Greens' Prague vote as far as it went to this list.
- List codes: 2017 ODS 1, STAN 7, Pirates 15, TOP 09 20, ANO 21, KDU-ČSL 24; 2021 SPOLU 13, PirSTAN 17, ANO 20;
  2025 SPOLU 11, Pirates 16, ANO 22, STAN 23.

**Operationalisations the registration left open.**

- Allocation: 500 of 580 cells by pre-census flats. The other 80 fall back to area, with 2 612 residents between
  them. The flats-per-building-type fallback was not built, because RÚIAN points with flats cover every residential
  type used. Allocated total 1 301 482 against the census 1 301 432. 25 557 residents of boundary cells stay outside
  Prague.
- ZSJ check: an independent ZSJ-based allocation totals 1 300 991. 13 precincts deviate by more than 25 %
  (robustness 10).
- Share of 15–17 year olds: ČSÚ publishes five-year groups only (SLD21A011), so s = 0.6 × Czech citizens aged 15–19
  / Czech citizens 15+ = 0.6 × 43 065 / 933 243 = 0.0277.
- Czech adults per post-census flat: 1.18. This is the mean over the 15 cells where at least half of the pre-census
  flats were completed 2016 – census day.
- Post-census flats standing at the 2025 election: 3.74 % (the referee's 4.5 % counts to the present day). 88
  precincts exceed 10 %.
- Registration-office flag: the 57 district offices' RÚIAN address points from the register of public authorities
  (Seznam OVM, legal form 811). Each lies in a different precinct.
- Institution flag: 79 inpatient health sites (ÚZIS NRPZS NR-01-06), 74 care homes for seniors, special-regime
  homes and homes for people with disabilities (MPSV register), and the Pankrác and Ruzyně prisons, together
  flagging 106 precincts. Dormitories are **not** flagged, because no open list exists (deviation from §3). Sheltered
  housing and weekly care are not flagged.
- Grid clusters: 282, covering all 1 120 polygons.

**§5a results and their pre-committed consequences.**

- VIF > 10 for tertiary (14.6) and vocational (11.8). The collinearity sits inside the education block (three of
  four shares that sum to 100 with maturita). The panel VIF is 2.35, so the variance of the H1b contrast is
  unaffected. Individual education coefficients are not interpreted; the Gelbach decomposition reports the
  education block as one group.
- H1b: under the (pessimistic) precinct residual SD of 4.04 pp, power reaches 80 % at θ ≈ 0.2 (place) and falls just
  short at θ = 0.8 (composition, 0.77). The minimum detectable deviation from 0.5 is therefore about 0.3, at the
  trigger. As pre-committed, an "indeterminate" H1b is reported as **underpowered**, never as "place".
- H2: the SE of the metro coefficient at the cluster level is about 0.31 pp per doubling, above the ±0.25 margin.
  Power of the equivalence test is ≈ 0 even if the true effect is exactly zero; the smallest margin with 80 % power
  would be ±0.91. The margin is **not** widened: it was set on substantive grounds, and the 2025 estimate is already
  known. H2 is expected to be "not supported: inconclusive", and will be written as such, with the confidence
  interval shown against the margin. The precinct-level model (robustness) is reported next to it.
- H4a: the minimum detectable difference between the two centre gradients is about 4.1 pp per doubling under the
  precinct turnout SD, which is inflated by the flagged precincts that H4a excludes. Expect low power, and report
  the interval.
- H3: not computed at the design stage, because the matched sample needs the 2017/2021 registers.

### 2026-09-28, estimation (after outcomes were joined)

- **Inference implementation.** The wild cluster bootstrap is *unrestricted* (bootstrap-t, Webb weights, B = 9 999),
  not restricted as §5 says. Imposing the null on a contrast across two regressions (δ = β₁ − 0.5·β₀) has no
  standard restricted form. CR2 uses the √W-symmetrised hat matrix, with a t(G − 1) reference instead of the
  Satterthwaite df. G = 57 districts.
- **H4a coding error, found and fixed before reporting.** The first run tested sign(g_reg)·(g_reg − g_res). The
  registered test is on |g_reg| − |g_res|, and it is now implemented as registered. The two differ because the
  resident gradient came out with the opposite sign.
- **H4, measurement.** Across all 14.8 thousand precincts in the 2025 file, envelopes never exceed "voters in the
  list". This is consistent with voters on a voting pass being added to the list of the precinct where they vote,
  so R is the register plus pass voters, not the register alone. This cannot be separated with the published data,
  and it is stated as a limitation of RQ4.
- **H5 join.** 2021 results are joined to the current polygons by (district, number): 1 112 of 1 119 are joined,
  and they sum to 280 clusters. Housing is the 2025 stock.
- **Placebo 12** was not run: official coordinates of the line D stations were not located in open data.
- **Placebo 13.** The within-district shuffle null is centred on 0.19, not zero, because shuffling within districts
  keeps the between-district correlation of housing and composition. The observed attenuation (0.42 pp per 10 pp)
  lies outside the null's 95 % range. This is reported, and the claim is not re-framed.
- **H3 matching.** 1 103 precincts exist in all three elections; 819 pass the ±10 % register rule. The ČÚZK VFR
  historical geometry was not checked (deviation from §4), so the registered rule is used alone.

**3 October 2026 (audit).** The H1 note above that says 'G = 57 districts' is a typo: the estimate clusters over 56 districts (rings_extended.json, H1_ANO.delta.G = 56; one district holds no cluster).
