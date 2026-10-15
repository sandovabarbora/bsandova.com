# Does the Chamber follow what worries Czechs? Public concern, parliamentary attention and spending — research design

**Status: pre-specified analysis, design committed 14 October 2026, before any Czech value of public concern,
parliamentary attention or spending was read.** The steps follow in dated commits: design → data and validation →
code → results. Commit times are self-reported. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **Feasibility (14 October 2026).** A check read the sources' availability, formats, licences and category labels:
  Eurobarometer tables on data.europa.eu, ParlaMint-CZ and ParlaCAP-CZ (CLARIN.SI, CROSSDA), the psp.cz stenographic
  archive, Eurostat `gov_10a_exp`. It printed Czech respondent counts, year ranges, speech counts and labels, and no
  Czech share of concern, attention or spending. A second step listed the answer categories of the Eurobarometer item
  in every wave from EB61 to EB104 (labels, dates, question numbers and Czech N only).
- **The author's knowledge.** The author follows Czech politics and knows its broad history (the 2015 migration
  debate, the 2020–21 pandemic, energy prices in 2022, the war in Ukraine). No series of this study has been computed
  or plotted, and she has not worked with these data.
- **Literature.** Studies of the United States, the United Kingdom and the European Council (§9) find that
  attention in speeches follows public priorities more than laws, and laws more than budgets. No Czech study of this
  kind was found; none in Central and Eastern Europe except Hungarian agenda volumes.
- **Review.** A draft was read by an independent methods reviewer, without any Czech value; the version below takes
  in its points on spells, labels, the lagged outcome, windows, inference, units, the crosswalk and validation.
- **Prior expectation.** Stated by the author on 14 October 2026: the Chamber does not follow public concern, because
  it is paralysed by the quarrels of the political spectrum.

## 1. Questions and estimands

Unit: a topic k (§2.4) in a Eurobarometer wave t (or a year, for spending). C, A and S are proportions.

- **Q1, attention follows concern (primary).** The elasticity β₁ of A(k, t+) with respect to C(k, t), with C(k, t) the
  share of Czech respondents naming topic k in wave t and A(k, t+) the share of plenary words on topic k in the
  window after the wave (§4). Two co-primary models, both with topic, wave and topic × half-year (spring or autumn
  wave) effects, estimated by Poisson pseudo-maximum likelihood (PPML) with A(k, t+) as the outcome and log C(k, t) as
  the regressor:
  - **static:** no lagged attention;
  - **dynamic:** adding log A(k, t−), the window before the wave, with the bias of a lagged outcome in a short panel
    corrected by a split-panel jackknife (the panel split into its first and second halves of waves).
  A label needs both models to agree (§5); otherwise Q1 is reported as model-dependent.
- **Q1r, the reverse (own label).** The same two models with C(k, t_next) as the outcome and log A(k, t+) as the
  regressor: does attention lead concern?
- **Q2, spending follows concern (primary).** The elasticity β₂ in a PPML of S(k, y+1) on log C̄(k, y) with log S(k, y)
  as a control, topic and year effects, the dynamic model corrected as above; C̄(k, y) is the mean over the year's
  waves within one spell (§2.4); y a calendar year.
- **Q3, friction (primary).** β₁ʸ − β₂, with β₁ʸ attention estimated in Q2's form (yearly attention A(k, y+1) on
  log C̄(k, y), log A(k, y), topic and year effects) on the same topics and years, so that the two coefficients are of
  one form. Attention and spending are measured with different noise; a difference is reported as a difference in
  response, not proven to be friction.
- **Q4, who responds (descriptive, no label; the author's question).** Q1's static model separately for speeches by
  members of governing parties and of the opposition (ParlaCAP's `party_status`), and by government (Sobotka 2014–17,
  Babiš 2017–21, Fiala 2021–23, six to eight waves each). The quarrels of the spectrum are not measured.

## 2. Data

### 2.1 Public concern

Standard Eurobarometer, "What do you think are the two most important issues facing (OUR COUNTRY) at the moment?",
Czech column of Volume A (or the Czech Volume C file where Volume A is incomplete), data.europa.eu, waves EB62
(autumn 2004) to the latest published when the data step runs (EB104 at registration; EB61 has no Czech data).
C(k, t) is the sum over the topic's items of the share of respondents naming the item, as published (a respondent
naming two items of one topic counts twice, since only item shares are published); a zero is set to half a
respondent (0.5 ÷ Czech N) before the log. Split-ballot waves (EB65, EB71, EB74–76, EB92) use arm A, the list read out
as in the waves before (in EB71 the "Protecting the environment" half); arm B is a check where it exists. Fieldwork
dates are the Czech dates where the technical note gives them, else the survey's. EB93–96 (2020–22) are flagged for a
possible change of interview mode.

### 2.2 Parliamentary attention

- **Primary: ParlaCAP-CZ** (CROSSDA, doi:10.23669/1ZTELP, CC BY 4.0), the Chamber of Deputies' plenary speeches of
  November 2013 to July 2023 with a Comparative Agendas Project (CAP) major topic per speech from the classifier
  `classla/ParlaCAP-Topic-Classifier`. Speeches by the chair are dropped; speeches labelled "Mix" (the corpus's label
  for a top probability below 0.60) or "Other" are dropped from numerator and denominator. A(k, ·) = words of
  speeches on the topic's CAP major topics ÷ words of all kept speeches, all CAP topics included.
- **Extension (registered, co-primary with its own labels): psp.cz 2004–2013 and 2023–2025.** Q1, Q1r, Q3 and Q4
  are estimated and labelled twice: on ParlaCAP alone (2013–2023) and on the whole series 2004–2025, which roughly
  doubles the waves. Neither overrides the other; both are reported. The stenographic records split into
  speeches by speaker and classified with the same model and threshold. The pipeline is first run on the 2013–2023
  records: if its topics agree with ParlaCAP's on fewer than 90 % of matched speeches, the extension is not estimated.
  It tests reproducibility only; validity is checked by the validation sample below.
- **Validation of the classifier on Czech.** A sample of 600 speeches: 500 from ParlaCAP-CZ (Mix and Other included in
  the frame) and 100 from the 2004–2013 records, drawn with probability proportional to words within strata of the
  assigned label (equal expected numbers per harmonised topic and for Mix and Other). Two language models from
  different releases (Claude Sonnet and Claude Opus; one family, a weakness stated here) code each speech from the CAP
  codebook without seeing the classifier's label; the author adjudicates their disagreements, also without it. The
  coding is fixed before any attention share is computed. Reported, weighted back by inverse inclusion probability:
  the coders' agreement, the classifier's precision, recall and F1 per harmonised topic, and the error in each
  topic's word share implied by the confusion matrix. If the weighted macro-F1 over the harmonised topics is below
  0.50 (a bound set without a calibration of its own), Q1, Q3 and Q4 are reported as classifier-limited.

### 2.3 Spending

Eurostat `gov_10a_exp`, general government, total expenditure (TE) by COFOG, million national currency, Czechia,
2004–2024 (and later years if published when the data step runs). S(k, y) = the topic's divisions or groups ÷ total
expenditure.

### 2.4 Harmonised topics and spells

Fixed now from the category inventory.

| Topic | Eurobarometer items | CAP major topic | COFOG |
|---|---|---|---|
| Economy | economic situation; rising prices / inflation / cost of living; taxation; government debt | 1 Macroeconomics | — |
| Unemployment | unemployment | 5 Labour | GF1005 |
| Health | healthcare system; health and social security (EB77–92); health | 3 Health | GF07 |
| Pensions | pensions (to EB102) | 13 Social welfare | GF1002 (old age only) |
| Education | the educational system | 6 Education | GF09 |
| Crime | crime | 12 Law and crime | GF03 |
| Immigration | immigration | 9 Immigration | — |
| Housing | housing | 14 Housing | GF06 + GF1006 |
| Environment and energy | protecting the environment; (the) environment; energy (related issues); the environment, climate and energy issues; the environment and climate change (and risks related to climate change); energy supply | 7 Environment + 8 Energy | GF05 + GF0403 |
| Security and international | terrorism; defence / foreign affairs; the international situation; security and defence; Russia's invasion of Ukraine; the conflict in the Middle East; threats to democracy | 16 Defence + 19 International affairs | GF02 (defence only) |

Public transport (to EB65), the Cyprus issue, other, none and don't know are not used. Q2 and Q3 use the eight topics
with a COFOG counterpart.

**Spells instead of break dummies.** A topic's *spell* is a run of waves with an unchanged item list for that topic.
Where a topic's items change at wave w, its observations at w−1 and w are not paired: the dynamic model uses no lag
across the change, and each spell has its own topic effect. Spell changes: Economy (EB77 government debt added; EB83
prices renamed; EB104 taxation dropped), Health (EB77, EB93), Pensions (ends EB102), Environment and energy (EB66,
EB71, EB72, EB77, EB93, EB103), Security and international (EB77, EB97, EB103, EB104). A change in one topic's list
also shifts mentions of the others, since respondents give two answers; the wave effects absorb the common part of
that shift, and a check drops the waves in which any list changed.

## 3. Data step (before any Czech value is summarised)

Committed as `priorities-data.json`, with counts only: waves and Czech N read, whether Volume A gives whole or
decimal percentages; ParlaCAP speeches and words kept and dropped (chair, Mix, Other) by term; each window's coverage
by the corpus (a window less than 90 % covered is dropped); COFOG years present; for the extension, the agreement with
ParlaCAP on the overlap. The validation coding (§2.2) is done and committed before §4 runs. Before any Czech data are
read, a simulation on made-up series with the study's layout (ten topics, the waves and spells of §2.4, persistence
and noise over a stated grid) reports the elasticity each model could detect; it informs the reading and fixes no
label.

## 4. Estimation and inference

- **Windows.** The window after wave t starts the day after its fieldwork ends and ends at the earlier of 182 days
  later and the day before the next wave's fieldwork starts; the window before wave t is the same length, ending the
  day before its fieldwork starts.
- **Waves.** Those with both windows covered by the attention data (ParlaCAP: about 18; extension: about 41).
- **Inference.** Two intervals for each coefficient, and the label uses the wider: a wild cluster bootstrap over
  topics (Webb weights, 9 999 draws, null imposed, intervals by test inversion), and a randomisation interval from
  permuting whole topic series of C across topics (100 000 of the 10! permutations, seed fixed), which keeps each
  series' own persistence and the shocks shared within a wave. An interval may be unbounded; the label then follows.
- **Q3.** The difference with both equations resampled together by topic cluster (and permuted together).
- Weights: none in the primary models (each topic counts once); weighting by the topic's mean concern is a check.

## 5. Labels

The smallest elasticity of interest is 0.10. Evaluated in this order, for each of Q1, Q1r, Q2 and Q3 (for Q1, Q1r
and Q2 the static and the dynamic models must give the same label, otherwise "model-dependent"):

1. **Underpowered** if the 90 % interval is wider than 0.20, so that it could not lie within ±0.10.
2. **Not supported** if the 90 % interval lies within ±0.10.
3. **Supported** if the 95 % interval lies wholly above 0.10.
4. **Positive, possibly small** if the 95 % interval lies wholly above 0 but not above 0.10.
5. **Inconclusive** otherwise.

Classifier-limited (§2.2) is added next to Q1, Q3 and Q4.

## 6. Checks (reported; none relabels a primary result)

- **Speeches instead of words** (obstruction marathons inflate words), **chair kept**, **Mix kept** under its
  highest topic.
- **Window of one year** instead of half a year.
- **Without 2020–2022** (pandemic, energy prices and the war move several series at once); **without EB93–96**
  (interview mode).
- **Without the waves in which any item list changed.**
- **Split-ballot arm B** where it exists.
- **Leave one topic out** and **leave one wave out**: the range of the estimates.
- **Log model with the half-respondent floor** (OLS) instead of PPML; **levels**.
- **Weighted by the topic's mean concern.**
- **Topics with classifier F1 ≥ 0.60 only**; **attention corrected by the confusion matrix**.
- **Q2 on the discretionary topics** (Education, Crime, Housing, Environment and energy, Security), and with the
  unemployment rate and the old-age dependency ratio as controls.
- **Spending as change in share** instead of the dynamic share model.

## 7. Outputs

An article on bsandova.com: the ten topics' concern and attention over time, the estimates with their labels, and
what each side of the Chamber talks about when Czechs worry.

## 8. What this will not show

- **Why.** A link between concern and attention can run through the media, events that move both at once, or
  the Chamber's own debates; the wave effects remove only what moves all topics alike.
- **Whether the Chamber acts.** Words are not laws; the budget side is the nearest to action, and it is the
  weakest test.
- **Individual MPs or parties' sincerity**, the Senate, the government's own agenda, regional politics.
- **Concern beyond two answers:** an issue that ranks third for everyone is invisible in the item.

## 9. References

Jones, B. D., Baumgartner, F. R. (2004), Representation and agenda setting, *Policy Studies Journal* 32(1). Jennings,
W., John, P. (2009), The dynamics of political attention, *American Journal of Political Science* 53(4). Bevan, S.,
Jennings, W. (2014), Representation, agendas and institutions, *European Journal of Political Research* 53(1),
37–56. Alexandrova, P., Rasmussen, A., Toshkov, D. (2016), Agenda responsiveness in the European Council, *West
European Politics*. ParlaMint 5.0 (CLARIN.SI, hdl:11356/2004); ParlaCAP (CROSSDA, doi:10.23669/1ZTELP). Details are
verified before publication, in a dated commit.

## Changes after registration

**14 October 2026 (data step, §3; counts only).** `tools/priorities/fetch.py` and `prepare.py`; files and hashes in
`priorities-manifest.json`, counts in `priorities-data.json`. All 43 waves EB62–EB104 have a Czech column in Volume A;
EB105 is not yet published. Volume A gives shares as whole percentages and its Czech "Total" is a weighted base, not
the unweighted N; the half-respondent floor (§2.1) uses that base. Volume A has no Czech fieldwork dates, only the
survey's, and EB62–EB74 give months only; windows (§4) use the survey dates, the first day of a month-only start and
the last day of a month-only end. ParlaCAP-CZ: 196 182 speeches, 25 November 2013 – 26 July 2023; 64 258 kept after
dropping the chair, Mix and Other. COFOG: all codes, 1995–2024. **A blinding slip:** while the parser was debugged, a
diagnostic printed whether each Czech weighted-count cell was at most 1, without values; for the study's items it
showed that Terrorism was named by about no one in EB94 and EB96. No share, attention or spending value was printed or
computed.

**15 October 2026 (reproducibility check and validation sample, before any attention share).** The full classification
of the psp.cz records (379 034 speeches) agrees with ParlaCAP-CZ's label on 99.48 % of the 185 659 matched speeches of
2013–2023 (99.79 % without the chair), above the registered 90 %, so the extension is estimated
(`tools/priorities/overlap.py`, `priorities-overlap.json`). The validation sample (`validation_sample.py`) settles three
points the design left open: the strata are the ten harmonised topics, **the other CAP topics together**, Mix and Other
(13, equal expected numbers); chair speeches are outside the frame, as they are outside the analysis; and the coders
see an anonymous key and the text **cut at 1 500 words** (111 of the 600 speeches are longer; the classifier itself
reads only the beginning of a speech). Inclusion probabilities are kept for the weighting. The coding instructions
(`coding_instructions.md`) give the CAP major topics with short definitions and "Other" for speeches without a policy
topic.

**15 October 2026 (validation coding).** The two coders (Claude Sonnet and Claude Opus, each in twelve batches of 50,
without the classifier's label) agree on 544 of the 600 speeches (90.7 %, unweighted); the 56 disagreements go to the
author (`adjudicate.py`). A process slip: the coding agents wrote temporary files to a shared scratch folder, and two
reported reading another batch's text there before re-extracting their own; each output file's keys match its batch
in order, and the coders' agreement is 43–47 of 50 in every batch, with no batch out of line.

**15 October 2026 (adjudication and validation results).** The author adjudicated 9 of the 56 disagreements and asked
the assistant to decide the other 47 by her rule ("mostly borderline, so Other or whichever seemed more reasonable"),
with her 9 as examples and without the classifier's label. That departs from §2.2 (the author adjudicates); the
assistant is the same model family as both coders, so the reference topic of those 47 is less independent. Results
(`validation.py`, `priorities-validation.json`), weighted back by inverse inclusion probability: coders' agreement 86.4 %
weighted (90.7 % raw); weighted macro-F1 over the harmonised topics 0.69 on ParlaCAP-CZ and 0.77 on psp.cz 2004–2013,
above the registered bound of 0.50, so no result is reported as classifier-limited. Weakest: Unemployment (F1 0.33,
recall 0.24, on ParlaCAP) and Pensions (recall 0.47 and 0.41, word share 3.0 and 3.5 points too low). On the 9 speeches
the author decided herself, the classifier's label matched hers on 3. The coding is fixed from here; §4 runs after the
estimation code is frozen.

**15 October 2026 (estimation code frozen, tag `priorities-code`).** `tools/priorities/estimate.py` with worked
examples on made-up data (`test_estimate.py`, 34 tests and a slow size simulation), reviewed by an independent
reviewer before the freeze. Choices the design left open, as implemented: (1) the wild cluster bootstrap is a score
bootstrap with the null imposed, Webb weights, 9 999 draws, one-step re-estimation and a cluster-robust t with a
leave-one-cluster-out (CR3-type) scaling; for jackknifed models and Q3 the statistic is the same linear combination of
the pieces' scores; (2) Q3's null is imposed by a minimum-distance projection of the two equations; (3) the
randomisation permutes the regressor's topic series, centred within its spells, with a score statistic on
y·exp(−β₀x), spells and fixed effects staying with the outcome topic; Q1r permutes the attention series; only periods
where every topic has the regressor are used (EB103 drops out of the whole-series Q1 randomisation); (4) all 8! = 40 320
permutations for eight topics, 100 000 drawn for ten; (5) seeds 20261014 (bootstrap) and 20261015 (permutations);
(6) intervals by test inversion (outward steps to ±10, bisection to 10⁻⁴; a rejected estimate triggers a grid scan;
no accepted value gives a degenerate interval, labelled underpowered); **(7) "the wider of the two intervals" is
implemented as their hull at each level (lowest lower bound, highest upper bound), so a label needs both methods; each
method's own interval and label are stored**; (8) "wider than 0.20" strict, "within ±0.10" inclusive, "wholly above"
strict; (9) split-panel jackknife of Dhaene and Jochmans (2015), overlapping halves for odd T; (10) after-window = the
182 days after fieldwork ends, cut at the day before the next wave's fieldwork, before-window of the same length;
(11) coverage = share of window calendar days inside the corpus span (ParlaCAP EB81–98; whole series EB62–103, to the
earlier of 31 December 2025 and the last date in the data); (12) half-year by wave parity; (13) dynamic Q1 uses all
rows (its lag is a calendar window), dynamic Q1r drops pairs across a spell change; (14) Q1r on Q1's waves; (15) yearly
C̄ uses the waves of the spell of the year's last wave, floored before averaging, a wave's year being its fieldwork
start; (16) zero attention floored at half a word, spending not floored; (17) Q2 static and dynamic, Q3 dynamic only
in Q2's form; (18) Q4: party status only in ParlaCAP; a wave belongs to the government in office on most days of its
after-window; Sobotka 29 January 2014 – 12 December 2017, Babiš 13 December 2017 – 16 December 2021, Fiala 17 December
2021 – 14 December 2025; **on ParlaCAP alone Fiala has 3 waves, not the six to eight the design expected** (8 on the
whole series); (19) checks get point estimates and bootstrap intervals only; (20) the Mix-kept check uses our run of
the classifier throughout; (21) one-year window = 365 days uncut; (22) "without 2020–2022" drops waves whose before- or
after-window overlaps those years; list-change waves 66, 71, 72, 77, 83, 93, 97, 103, 104; (23) arm B in EB65, 71,
74–76, 92; items only in arm B unused; (24) levels by OLS at the sample means; spending as change in share by OLS;
(25) weights = mean C; (26) F1 ≥ 0.60 and classifier-limited by the frame(s) of the corpus used; (27) confusion
correction spreads labelled words over reference topics with inverse-probability word weights, by frame; (28) Q2
controls by topic (log unemployment × Unemployment, log old-age dependency × Pensions; Eurostat une_rt_a and
demo_pjanind added); (29) a randomisation failure gives "not estimable"; (30) a failed check is recorded, not fatal.
The size simulation found the wild bootstrap alone rejecting 11.5–15.5 % at a nominal 10 % with ten clusters, CR3
scaling included; the randomisation interval's size was 4.6 / 9.8 / 19.3 % at 5 / 10 / 20 %, and the hull makes every
label need both. A blinding note: while reading the validation code, the code agent printed the committed validation
file, which holds the weighted validation sample's word shares per topic (about 600 speeches), not the attention
series.

**15 October 2026 (results, frozen code at `priorities-code`).** `priorities-results.json`, no estimate failed. Q1 on
ParlaCAP: static elasticity +0.13 (hull 95 % +0.04 to +0.24), "positive, possibly small"; dynamic +0.12 (90 % −0.10
to +0.22), underpowered; combined **model-dependent**. Q1 on the whole series 2004–2025: static +0.18 (90 % +0.07 to
+0.31, wider than 0.20) and dynamic +0.03, both **underpowered**. Q1r and Q3: **underpowered** on both corpora. Q2
(spending): static +0.03 (90 % −0.02 to +0.08) and dynamic −0.01 (90 % −0.06 to +0.02), **not supported**. Q4: coalition
+0.14 and opposition +0.12, both "positive, possibly small"; each government alone underpowered. No result is
classifier-limited. Checks are in the results file and are read in the article, not here.
