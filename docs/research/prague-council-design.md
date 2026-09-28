# Prague's council: research design (Part 1, extended)

**Status: draft for review.** Written before any analysis beyond what Part 1 already published (§0). The raw roll-call
files for the four terms have been downloaded; their structure (columns, members, sessions, identifiers) has been
inspected, and their vote cells only as far as Part 1 reported.

## 0. What has already been seen

Part 1 (published) used the roll-call files of the Prague City Assembly (ZHMP), 2010–2026: one row per vote and one
column per councillor. Each cell holds one of:

- hlas pro
- hlas proti
- zdržel se
- nehlasoval (present, pressed nothing)
- chyběl (absent)

**2022–26:**

- 2 468 votes in 42 sessions.
- Club positions are set by the majority of members present. Agreement with SPOLU:
  - STAN 98 %
  - Pirates 97 %
  - Praha sobě 88 % (in opposition)
  - ANO 64 %
  - SPD 52 %
- Present non-yes entries: 403 against, 1 269 abstentions, 25 734 nehlasoval.
- Per-councillor attendance and vote shares have been published.

**Four terms, passed votes only (term aggregates):**

- "Against" per 100 present: 1.06, then falling in every term to 0.28.
- Share of votes with any "against": 11.5 % in 2010–14, 4.5 % in 2022–26.
- Nehlasoval per 100 present: 12, rising to 18.
- Abstentions fall abruptly between 2014–18 and 2018–22; no explanation has been found.

**Not yet seen:**

- any within-councillor comparison across terms;
- the timing of the abstention fall within or between terms, at session level;
- any scaling of votes (ideal points, dimensionality);
- any breakdown by the subject of the item;
- club positions in the terms before 2022.

**Structure seen at design stage (no vote cells):**

- Members per file: 65 / 70 / 74 / 67 columns (replacements add columns).
- Councillors (surname + first name) in consecutive terms:
  - 2010 & 2014: 22
  - 2014 & 2018: 20
  - 2018 & 2022: 34
- Proposer (`predkladatel`): "Rada HMP" (the council, i.e. the executive) for 2 302 of 2 468 votes in 2022–26.
- Item titles (`nazevtisku`) are filled in 2010–2022 and **empty for the whole 2022–26 file**.

## 1. Research questions and estimands

- **RQ1 (norm or turnover).** Is the decline of recorded dissent (against or abstain rather than pressing nothing) a
  change in how the same councillors behave, or a change in who sits in the assembly?
- **RQ2 (the break).** Did abstention fall at one point in time, which would point to a rule, a procedure or the
  equipment, or gradually, which would point to behaviour?
- **RQ3 (what divides the assembly).** Is the voting space organised by government against opposition rather than
  by left and right?
- **RQ4 (what they disagree on).** Is opposition non-support concentrated on particular kinds of item?

**Estimands.** All quantities describe recorded behaviour in the published files: final votes on substantive items.
They say nothing about deliberation, committee work or votes the files do not contain (§7). "Recorded dissent" is
(against + abstain) / (present and not yes). It is the share of non-support that the councillor chose to put on the
record.

## 2. Hypotheses, tests and decision rules

**One p-value per hypothesis; Holm step-down at family-wise α = 0.05 over H1, H2, H3, H4.**

- **H1 (within-councillor decline).**
  - Unit: councillor × term, restricted to councillors present at ≥ 50 non-yes votes in the term.
  - Outcome: recorded dissent. Binomial GLM (logit) with the number of present non-yes votes as trials.
  - Regressors: councillor fixed effects; a linear term index (0–3); an indicator for being in opposition for the
    majority of the councillor's present votes in that term (§3).
  - Test: term-index coefficient < 0, one-sided. Identified only from councillors serving in more than one term.
  - SE: clustered by councillor; wild cluster bootstrap (Webb, B = 9 999).
  - Reported with it, no test: a shift-share decomposition of the aggregate change between consecutive terms into
    within-councillor change and turnover.
- **H2 (a break, not a slope).** Session-level abstentions per 100 present, all votes, 2014–2022 (the two terms
  around the fall).
  - Test: a single mean shift at an unknown date against no shift, with a linear trend in both models (Andrews
    sup-F, 15 % trimming). p from the Andrews (1993) / Hansen (1997) approximation.
  - Reported with it:
    - the estimated break session with a 95 % confidence set (Bai 1997);
    - whether that set contains the term boundary (last session of 2014–18, first of 2018–22);
    - BIC of the break model against a linear-trend-only model and a quadratic trend.
  - Decision labels: *discrete break at the term boundary*, *discrete break inside a term* (date named),
    *no discrete break*.
- **H3 (government, not left and right).** For the two terms whose coalition did not change (2018–22, 2022–26, to be
  verified in §3):
  - Ideal points: first dimension of a one-dimensional 2PL IRT model, estimated by penalised ML. Coding: 1 = yes,
    0 = present non-yes, absent = missing. Lopsided votes (minority < 2.5 % of present) are dropped.
  - Test: |ρ(θ, coalition)| > |ρ(θ, left–right)|.
    - ρ is Spearman over councillors with a CHES score for their national party. Praha sobě and non-partisans are
      excluded from both correlations.
    - Left–right = CHES `lrgen` of the national party. SPOLU members take the ODS / TOP 09 / KDU-ČSL score of their
      own party where known, otherwise the list mean.
    - The difference of absolute correlations is bootstrapped by resampling votes (B = 2 000, IRT re-estimated),
      one-sided.
  - The two terms give two p-values; H3's p is the larger (intersection–union).
- **H4 (what the opposition opposes).** Items are classified from their titles by a keyword dictionary fixed in
  Appendix B before any title is joined to votes. Categories:
  - budget and finance
  - property transactions
  - grants and subsidies
  - organisational and routine
  - planning (územní plán)
  - other

  Unit: opposition councillor × vote, present votes, in each term with titles. Outcome: non-yes (1) versus yes (0).
  Logit with councillor fixed effects and category dummies (routine = reference).
  - Test: the vote-weighted mean of the budget, property and planning coefficients > 0.
  - SE: two-way clustered by vote and councillor.
  - Confirmatory term: the latest term with titles, 2018–22, or 2022–26 if titles are recovered (§3).

## 3. Data and measures

- **Votes.** ZHMP roll calls, four terms, Prague open data (golemio storage). Rows with an empty timestamp are dropped.
  "Present" means any entry but chyběl.
- **Passed.** Votes for ≥ 33, a majority of the 65 seats.
- **Councillor identity across terms.** Surname + first name after stripping titles, checked by hand against the ČSÚ
  candidate lists of 2010, 2014, 2018 and 2022. Homonyms are resolved by list.
- **Club and coalition status.**
  - Club = the list a councillor was elected from, with dated changes of club where documented.
  - Coalition status is dated: a vote is a coalition vote for a councillor if their club belonged to the governing
    coalition on that date.
  - Coalition periods are sourced from news reports and city records and listed in Appendix A.
- **Party positions.** CHES 2019 for 2018–22 and CHES 2024 for 2022–26, if released; otherwise CHES 2019 for both.
- **Titles.** `nazevtisku` for 2010–2022. For 2022–26, the city's resolution records matched by print number
  (`cislotisku`), if a bulk source exists; if not, H4 is confirmatory on 2018–22 only.
- **Sessions.** `datumjednani`. A session spanning several days counts as one.

## 4. Models (details)

- **H1:** statsmodels GLM Binomial with a councillor FE. Robustness in §6.
- **H2:** OLS on session means weighted by present-member count; sup-F over break dates within [15 %, 85 %] of
  sessions; HAC (Newey–West, 2 lags) in the Wald statistics.
- **H3:** 2PL IRT with an N(0, 1) prior on θ and N(0, 5²) priors on item parameters (MAP by L-BFGS). Identified by
  fixing the sign so that the mayor's θ is > 0. Robustness: classical MDS of the pairwise agreement matrix.
- **H4:** conditional (fixed-effects) logit; the category contrast by the delta method.

**Design-stage checks, before outcomes are modelled:**

- The number of councillors identified in two or more terms, and their present non-yes counts (power for H1).
- The number of sessions per term (H2).
- The share of lopsided votes (H3).
- Title coverage and the category distribution (H4).

## 5. Robustness (reported, not in the family)

1. H1 with seniority (number of earlier terms) as a control; excluding councillors who changed club; a random-effects
   version that also uses one-term councillors.
2. H1 on passed votes only; H1 with abstain and against separately (multinomial).
3. H2 on passed votes only; on log rates; excluding sessions held under COVID rules (dates from Appendix A);
   the same test on "against" and on nehlasoval.
4. H3 with lopsided thresholds of 1 % and 5 %; with abstain coded as its own category (ordinal); with MDS; excluding
   the 2026 rows where replacements have no column.
5. H4 with dictionary variants (each category's keywords dropped one at a time); with coalition councillors as a
   comparison group (difference-in-differences across categories).
6. All analyses excluding votes whose recorded totals (`pocetpro`) disagree with the named columns.

## 6. Limitations

- **Selection of votes.** The files hold final votes on substantive items; amendments and procedural votes are
  missing. Roll-call analyses on selected votes are biased toward the issues that reach a final vote (Carrubba et al.
  2006).
- **Nehlasoval** cannot distinguish a deliberate non-vote from stepping out of the room while logged in.
- **CHES** scores are for national parties, not the Prague lists, and Praha sobě has none.
- **Ecological reading.** Club positions summarise members; they are not club decisions.
- **Causality.** No causal effect of procedure or norms is identified. H2 locates a change; it does not explain it.

## Appendix A. Coalition periods and procedural dates

(to be filled from sources before registration)

## Appendix B. Title dictionary

(to be fixed before titles are joined to votes)

## Changes after registration

(none)
