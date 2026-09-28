# Prague's council: research design (Part 1, extended)

**Status: registered (v2, after review)** by three referees (legislative studies, statistics, data audit). Written before any
vote-outcome statistic beyond §0 was computed. The roll-call files of the four terms have been inspected for
structure only: columns, identifiers, dates, seat coverage, value vocabularies and official totals. Term-level value
counts were also inspected, as far as Part 1 had already published them.

## 0. What has already been seen

**Published in Part 1 for 2022–26:**

- 2 468 votes.
- Club agreement with SPOLU, a club's position being the majority of its present members:
  - STAN 98 %
  - Pirates 97 %
  - Praha sobě 88 %
  - ANO 64 %
  - SPD 52 %
- Present non-yes entries: 403 against, 1 269 abstain, 25 734 nehlasoval.
- A per-councillor table.

**Published for four terms, passed votes, term aggregates:**

- Against per 100 present: 1.06 in 2010–14, falling each term to 0.28.
- Votes with any against: 11.5 % in 2010–14, 4.5 % in 2022–26.
- Nehlasoval per 100 present: 12 in 2010–14, 18 in 2022–26.
- An abrupt fall in abstentions between 2014–18 and 2018–22.

**Seen by the data referee, term level only.** Cell counts per term (pro / proti / zdržel / nehlasoval / chyběl):

| Term | pro | proti | zdržel | nehlasoval | chyběl |
|---|---|---|---|---|---|
| 2010 | 88 050 | 1 236 | 5 508 | 12 928 | 16 071 |
| 2014 | 133 859 | 1 149 | 9 665 | 26 069 | 18 954 |
| 2018 | 142 218 | 567 | 1 494 | 29 613 | 29 038 |
| 2022 | 115 954 | 403 | 1 269 | 25 734 | 16 638 |

The official totals (`pocetzdrzel`) show the same fall. No evidence was found that the fall is an encoding artefact:

- the vocabulary is identical in all four terms;
- no empty cell falls inside a seat period;
- official and cell totals differ only by the seats that have no column.

**Not yet seen:**

- anything within councillors across terms;
- the fall below term level in time;
- any scaling of votes;
- anything by item subject;
- club positions before 2022;
- anything by coalition status.

**Structure:**

- **Councillors.** 199 people; 62 in two or more terms. Consecutive-term transitions: 22 (2010→2014), 20 (2014→2018) and 34 (2018→2022). Only 3 people sat in both 2010–14 and 2022–26.
- **Sittings.** Clusters of roll-call times separated by more than 10 h: 41, 39, 43 and 40 per term. §0 of Part 1 said "42 sessions" for 2022–26: that count used meeting dates, which split overnight sittings.
- **Coverage.** The files hold about 67 %, 55 %, 67 % and 55 % of the roll calls actually held (rows over the highest vote number `poradi` per sitting). Missing are procedural votes, amendments and the like, in every term.
- **Titles.** `nazevtisku` is filled for 2010–2022. For 2022–26, titles were recovered from the city's resolution register for all 2 477 resolutions (`tools/zhmp/titles.py`).
- **`pritomno`.** Until 17 Sep 2020 it equals pro + proti + zdržel; from 15 Oct 2020 it also includes nehlasoval. It is never used here, and the date goes into Appendix A.

## 1. Research questions and estimands

- **RQ1 (conversion, club norm or replacement).** Is the decline of votes against a change in how the same
  councillors vote, in how clubs vote, or in who sits in the assembly?
- **RQ2 (where the abstentions went).** Did the substitution of pressing nothing for abstaining happen as a jump at
  a point in time, or gradually? A jump is read as procedural only if it is dated to a documented change
  (Appendix A); otherwise the label stays descriptive.
- **RQ3 (what divides the assembly).** Is voting organised by government against opposition more than by left and
  right?
- **RQ4 (what the opposition opposes).** Is opposition non-support higher on land-use planning and property than on
  grants?
- **RQ5 (exploratory, pre-registered).** Does a list that moves between coalition and opposition change how it votes?

**Terms.**

- **Explicit non-support** = (against + abstain) / (present and not yes): the share of a councillor's non-support that
  the record shows as an active position. Under Prague's absolute-majority rule (33 of 65) against, abstain and
  pressing nothing have the same legal effect, so the measure describes the record, not intent.
- **Present** is the voting system's log-in state, not physical presence.
- "Dissent" is not used: in the literature it means voting against one's own club. That quantity, club defection, is
  reported descriptively.

**Estimands.** All estimands describe recorded behaviour on the final votes the city publishes, which are about 55–67 %
of the votes held (§6).

## 2. Hypotheses, tests and decision rules

**One one-sided p-value per hypothesis; Holm at family-wise α = 0.05 over H1, H3, H4.** H2 is descriptive (§0). A hypothesis whose data rule
(below) fails gets p = 1. Decision labels and dates are estimation, outside Holm.

- **H1 (the same councillors vote against less).**
  - **Units.** Every person i seated in consecutive terms t and t+1, with at least 300 seated votes in both.
  - **Rate.** For each person and term, the against rate is a_it = (against + 0.5) / (present + 1).
  - **Transitions.** Δ_it = logit a_i,t+1 − logit a_it. The person mean D_i is taken over i's transitions.
  - **Status adjustment.** Δ_it is residualised on the change in the share of i's seated votes cast while their club
    was in opposition (dated, Appendix A), by OLS across transitions, and the intercept is kept.
  - **Test.** The mean of D_i (equal weight per person) < 0. Sign-flip randomisation over persons, 99 999 flips,
    one-sided.
  - **Why "against" only.** A vote against needs a button press, so no change in how the system records a logged-in
    member who presses nothing can move it.
  - **Reported with it, outside the family:**
    - the three transition-specific means with person-level intervals;
    - the stayer-only estimate (status unchanged);
    - explicit non-support as a secondary outcome;
    - a three-way shift-share of the aggregate change: within person and club, club composition, entry and exit.
  - **Also reported.** Newcomers' (first-term) against rate by term, a cohort-constant contrast, subject to selection.
  - **Estimand.** Within-person change across terms, which is period change plus career stage; the two cannot be
    separated with person effects.
- **H2 (a jump, not a slope; descriptive, see §0).**
  - **Series.** Sitting-level substitution s = abstain / (abstain + nehlasoval), 2014–18 and 2018–22 sittings
    (82 sittings).
  - **Model.** s = α + β·k + γ·D + δ·k·D + u, where k = sitting order and D = 2018–22. Weighted least squares
    (weight = abstain + nehlasoval).
  - **Test.** γ < 0, the discontinuity at the term boundary against separate linear trends. p from a fixed-regressor
    AR(1)-sieve bootstrap (Hansen 2000), B = 9 999.
  - **Reported, outside the family:**
    - a sup-F for an unknown break within each term separately (15 % trimming, bootstrap p), with an
      Elliott–Müller confidence set;
    - whether any within-term break date is within two sittings of 15 Oct 2020 (Appendix A);
    - the same model on official totals, zdržel / (pro + proti + zdržel);
    - the same model on continuing councillors only (people seated in both terms).
  - **Decision labels.**
    - *jump at the boundary, among continuing councillors too*: procedure or rule, if dated in Appendix A;
      otherwise a common shift.
    - *jump at the boundary, absent among continuing councillors*: consistent with turnover.
    - *within-term break* (dated).
    - *gradual*.
- **H3 (government and opposition, not left and right).**
  - **Scope.** For each coalition period of at least 12 months in 2018–22 and 2022–26 (from 15 Feb 2023), on
    contested votes (minority ≥ 2.5 % of those present). The minority side is yes against present non-yes. Absent
    members are left out.
  - **Classification errors.** For each vote, count the errors of two rules among present councillors:
    - (a) the coalition partition, with the direction chosen per vote;
    - (b) the best single cut on the left–right order of the councillors' national parties, over all cuts and both
      directions.
  - **Left–right scores.** CHES `lrecon`: 2019 for 2018–22, 2024 for 2022–26. Party = the councillor's party
    membership from the ČSÚ candidate list where available, otherwise the list's party; a joint list uses the
    seat-weighted mean of its parties. Councillors without a party score (Praha sobě, non-partisans on a local list)
    enter rule (a) only; both rules are counted over the councillors that have a score.
  - **Statistic.** The mean over votes of (errors_b − errors_a) / scored present.
  - **Test.** Statistic > 0, one-sided, moving-block bootstrap over sittings (block 3, B = 9 999). With two periods,
    p is the larger of the two (intersection–union).
  - **Check before estimation.** The coalition must not be a contiguous interval of the left–right order in either
    period.
  - **Outside the family:**
    - 2PL IRT ideal points (one and two dimensions), priors N(0,1) on θ and N(0, 2.5²) on item parameters,
      10 random starts, sign fixed by the mayor (Hřib 2018–22; Svoboda from 15 Feb 2023);
    - APRE for one and two dimensions;
    - CHES `lrgen` and `galtan` as alternative axes;
    - the placement of Praha sobě in both terms.
- **H4 (planning and property, not grants).**
  - **Unit.** A vote in 2022–26 (titles cover 100 %, above the pre-set 95 % rule) proposed by the Rada HMP. Items
    from councillors or committees form a separate stratum, reported apart.
  - **Outcome.** The share of present opposition councillors (dated status) who did not vote yes.
  - **Model.** Weighted least squares, weight = present opposition count, with category dummies from the frozen
    dictionary (Appendix B).
  - **Test.** θ = (n_plan·β_plan + n_prop·β_prop) / (n_plan + n_prop) − β_grants > 0, one-sided. The n are category
    vote counts fixed from titles before outcomes are joined.
  - **Inference.** CR2 standard errors by sitting with Satterthwaite df; a wild cluster restricted bootstrap
    (Rademacher, B = 9 999) is reported alongside.
  - **Data rule.** If planning, property or grants appears in fewer than 8 sittings, H4 gets p = 1.
  - **Outside the family:** every category's coefficient; the same model for coalition councillors; the
    difference-in-differences across categories.
- **RQ5 (exploratory, pre-registered).**
  - **Unit.** List × coalition period.
  - **Measures.** Yes share and against rate for lists that change status (Praha sobě 2018→2022; ANO, ODS and
    TOP 09 across terms, and within terms where Appendix A dates it), against lists that do not.
  - **Reporting.** Descriptive, with intervals.

## 3. Data and measures

- **Loading.** Explicit separators, `utf-8-sig`, text dtype, headers stripped. Members are all columns after the
  17 metadata columns.
- **Rows.** A row is a resolution with its final roll call.
  - Rows with no roll call are dropped and reported: 155 / 105 / 3 / 9.
  - The 3 rows flagged "technická chyba" and the 2 rows whose totals disagree with the cells beyond missing seats
    (2014 `1/2`, 2022 `17/56`) are excluded.
  - Rows whose roll call predates the resolution's session (12 / 13 / 3 / 8) are flagged.
  - Rows whose `kbodu` marks repeat, procedural or amendment votes are flagged.
- **Present / seated.** Present is any of the four non-absent values; empty means not seated. Seat periods run from a
  member's first to last non-empty cell.
- **Passed.** `pocetpro` ≥ 33.
- **Seat coverage.**
  - 2010–14: 4, then 3 seats have no column.
  - 2014–18: 1.
  - 2022–26: 1–2 in 292 rows from 23 Apr 2026.
  - The unnamed replacement ("neurčeno") is excluded from H1 and H3.
- **Dates.** `datumcas` is parsed with an explicit format per term (`%d.%m.%Y %H:%M` for 2010 and 2014, ISO for 2018
  and 2022) and rows are sorted.
  - Sitting = cluster of `datumcas` with gaps of more than 10 h.
  - Legal session = the prefix of `cislousneseni`.
- **Identity.**
  - Surname + first name, parsed by the double-space rule; the `Bonhomme Hankeová` and `Dientsbier` exceptions are
    handled by hand.
  - Unverified links, reported with and without: Urban Milan (2010 and 2022); Kloudová → Lněničková; Vorlíčková →
    Tylová.
  - Aliases: Marvanová = Kordová Marvanová; Freitas = Freitas Lopesová.
- **Coalition status.** Dated from Appendix A. Interregna are coded "no coalition" and excluded from status-based
  measures.
- **Party positions.** CHES 2019 V3 and CHES 2024 (both in `tools/data/zhmp/ches/`).
- **Titles.** 2010–22 `nazevtisku`; 2022–26 from the resolution register. The two registers word titles slightly
  differently, so the dictionary is validated per term.

## 4. Design-stage checks (structure only, before any vote outcome is modelled)

- **H1.** Eligible persons and transitions under the 300-seated rule. Simulated power of the sign-flip test for
  between-person SD of Δ from 0.3 to 1.0 (logit units).
- **H2.** Sitting sizes. Simulated power of the jump test against the sup-F under AR(1) ρ ∈ {0, 0.3, 0.6}, with
  published term means as the level change.
- **H3.** The contiguity check on coalition and left–right order.
- **H4.** Category counts and sittings per category after the dictionary is frozen.

Simulation code and seeds are committed before registration.

## 5. Robustness (reported, not in the family)

1. H1 excluding the unverified identity links; with a conditional (Chamberlain) logit at the vote level with term
   dummies and status; with a restricted score wild bootstrap (Kline–Santos, Rademacher); stayers only; Lee bounds for
   non-return.
2. H2 with sittings at 6 h and 20 h gaps and legal sessions; excluding flagged rows; excluding votes after midnight
   (0.8 % of votes in 2010–14, 38 % in 2022–26); with and without sittings under COVID rules (Appendix A).
3. H3 with a 1 % and a 5 % lopsidedness cut-off; with nehlasoval coded as missing (Rosas, Shomer & Haptonstahl 2015);
   `lrgen` and `galtan` instead of `lrecon`; excluding the 2026 rows with missing seats.
4. H4 with each category's keywords dropped in turn; with session fixed effects; Firth-penalised logit at the
   councillor-by-vote level; 2018–22 as a replication on print titles.
5. Selection audit: one sitting per term, drawn at random before analysis (seed in the code), compared with the city's
   full voting record for that sitting, if published. Otherwise recorded as not run.

## 6. Limitations

- **Selection of votes.** About a third to a half of all roll calls (procedural, agenda and amendment votes) are not
  in the files. That is where agenda control and opposition conflict are most visible (Cox & McCubbins 2005;
  Carrubba et al. 2006, 2008).
- **Nehlasoval.** It cannot distinguish a deliberate non-vote from a member logged in but out of the room, the chair,
  a declared conflict of interest, or a club's collective decision not to vote.
- **CHES** measures national parties, not the Prague lists; Praha sobě has no score.
- **Causality.** No causal effect of procedure, norms or status is identified.

**Publication rules for any text that names people.**

- No per-person rates below 100 present votes.
- No words that attribute intent ("rebel", "deliberately").
- Ideal points only by club, or with intervals and without ranks.
- The identity crosswalk is published.

## Appendix A. Coalition periods and procedural dates

Sources are in the research note `docs/research/prague-council-sources.md`.

| Term | From | To | Coalition | Mayor |
|---|---|---|---|---|
| 2010–14 | 30 Nov 2010 | 24 Nov 2011 | ODS + ČSSD | Svoboda |
| | 24 Nov 2011 | 23 May 2013 | ODS + TOP 09 | Svoboda |
| | 23 May 2013 | 20 Jun 2013 | interregnum | Hudeček (acting) |
| | 20 Jun 2013 | end of term | TOP 09 minority council, ČSSD support (coded: TOP 09 governing; ČSSD opposition) | Hudeček |
| 2014–18 | 26 Nov 2014 | 23 Oct 2015 | ANO + ČSSD + Trojkoalice | Krnáčová |
| | 23 Oct 2015 | 28 Apr 2016 | crisis, coalition declared dead on 10 Nov 2015: interregnum | Krnáčová |
| | 28 Apr 2016 | end of term | ANO + ČSSD + Trojkoalice renewed | Krnáčová |
| 2018–22 | 15 Nov 2018 | end of term | Piráti + Praha sobě + Spojené síly | Hřib |
| 2022–26 | 3 Nov 2022 | 16 Feb 2023 | interregnum (caretaker council) | Hřib |
| | 16 Feb 2023 | end of term | SPOLU + Piráti + STAN | Svoboda |

**Club changes.** Kordová Marvanová was expelled from the SPOLU club on 17 Feb 2023. Komrsková left the Pirates for
"Jsme Team" in June 2026 (she stays in the club data as elected).

**Procedural dates.**

- Rules of procedure amended on 28 May 2015, 15 Sep 2016, 28 Feb 2019 ("mostly technical"; no change to voting),
  10 Sep 2020, 18 Mar 2021 (videoconference voting by cards for members in quarantine), 20 Nov 2025 and
  12 Feb 2026.
- The definition of `pritomno` in the open data changed between 17 Sep and 15 Oct 2020.
- New voting equipment was tendered in 2023.
- The chair's wording ("Kdo je pro? Proti? Zdržel se?") is unchanged in the transcripts checked (2015–2023).

## Appendix B. Title dictionary

The dictionary is `tools/zhmp/topics.py`, frozen at SHA-256 `c06df1ff95dece80ce9477c7f02a8d65791e7a0b33e92a28dc7a001e64d3906c`. Its precedence is planning > regulation >
budget amendment > grants > budget > property > appointments > companies > organisational > strategy > other.

**Validation on titles only.**

1. **Development sample.** 300 titles (75 per term) were coded blind by an independent coder: an LLM coding pass
   without access to the dictionary. The first version reached 88.7 % agreement, κ 0.85, macro-F1 0.79. That is below
   the 0.80 rule, so the dictionary was revised on these titles.
2. **Holdout.** A fresh 200 titles (50 per term), not used in revision, were coded blind in the same way against the
   frozen dictionary:
   - agreement 90.5 %, κ 0.88, macro-F1 0.88 over the categories present;
   - planning F1 0.97, property 0.98, grants 0.84, budget 0.92;
   - "other" has low precision (0.35), because the dictionary sends to "other" items the coder put elsewhere.

**Design-stage checks, 2022–26, council-proposed, from 16 Feb 2023.** Votes (sittings) per category:

| Category | Votes | Sittings |
|---|---|---|
| planning | 171 | 29 |
| property | 876 | 36 |
| grants | 128 | 33 |
| budget | 524 | 36 |

All three H4 categories exceed the 8-sitting rule. The weights for θ are n_plan = 171 and n_prop = 876.

**H3 contiguity check** (CHES party scores; SPOLU members by party):

- **2018–22, `lrecon` 2019.** Order: Piráti, ANO, KDU-ČSL, STAN, TOP 09, ODS. The coalition (Piráti, KDU-ČSL, STAN,
  TOP 09) is not contiguous: the test is informative.
- **2022–26, `lrecon` 2024.** Order: ANO, SPD, Piráti, KDU-ČSL, STAN, ODS, TOP 09. The coalition **is** contiguous, so
  a single cut reproduces it and the test cannot distinguish the two structures.
- **Pre-specified fallback order:** `lrecon` > `lrgen` > `galtan`. 2022–26 therefore uses `lrgen` 2024. Order: Piráti,
  ANO, STAN, KDU-ČSL, TOP 09, ODS, SPD. The coalition is not contiguous.

**H1 eligibility.**

- 74 consecutive-term transitions (22, 20, 32) of 59 people, each seated for at least 300 votes in both terms.
- The unverified identity links concern only non-consecutive terms, so they do not affect H1.
- With 59 persons, the sign-flip test's minimum detectable mean change at 80 % power is about 0.32 × SD(D) logit units.

## Changes after registration

**28 Sep 2026, before outcomes were modelled.**

- A crosswalk from councillor to list and party was built from the ČSÚ registers
  (`docs/research/prague-council-crosswalk.csv`). 276 of 277 columns were matched: by exact name, by the suffix of a
  double surname, or by spelling variants (Aleksandra/Alexandra, ű/ü). One 2010 column, "Novotný Petr", matches no
  candidate of a winning list. It is left unresolved and excluded wherever a list is needed.

**28 Sep 2026, after estimation.**

- **H4 inference.** CR2 uses a t(G − 1) reference instead of the Satterthwaite df, with G = 36 sittings. The wild
  cluster restricted bootstrap agrees (p 0.536 against 0.534).
- **H1 shift-share.** The decomposition is two-way (within continuing councillors; entry, exit and mix), not the
  registered three-way with a club term.
- **H2 continuing members.** Everyone seated in both 2014–18 and 2018–22: 20 people.
- **H3, exploratory.** Added after the result: which clubs formed the "not yes" side on contested votes. It shows that
  opposition clubs rarely vote against together, which a single left-right cut can isolate. The registered comparison
  gave the left-right rule more options (any cut, including the trivial ones) than the coalition rule (two
  directions). That asymmetry was in the registered design; it is reported, and the test is not re-specified.
- **IRT.** One dimension only; two dimensions were not estimated.
- **Not run:**
  - the conditional logit and the Kline–Santos score bootstrap for H1;
  - Lee bounds for H1;
  - H3 with 1 % / 5 % cut-offs and with nehlasoval coded as missing;
  - H4 with session fixed effects;
  - the selection audit.
- **Run and reported:**
  - H1 without the status adjustment;
  - H1 on passed votes only;
  - H1 without the 2010→2014 transition;
  - H1 on stayers only.
