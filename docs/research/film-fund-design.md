# Czech film fund: what production support changes, and whether the Council's points foresee audiences — research design

**Status: analysis plan committed 1 October 2026, before this analysis was run. The author had worked with these
data since July 2024; commit times are self-reported.** No OSF entry is made, by the author's decision of 1 October
2026. In the article this is a "pre-specified analysis: analysis plan committed at `<hash>` on 1 October 2026, before
this analysis was run and before the results commit; the author had worked with these data since July 2024; commit
times are self-reported". Deviations are listed, dated, under "Changes after registration".

## 0. What has already been seen

- The author has worked with these data since July 2024. The plan sets the analysis in advance; the author already
  knew the data.
- **Fund data (all of it seen).** 514 decision tables from the State Cinematography Fund (2014–2024) and the State
  Audiovisual Fund (2025–2026) have been downloaded. Their hashes are in `tools/data/film/manifest.csv`; the
  published hash list will be `docs/research/film-fund-files.sha256`. They were parsed into 6 026 applications in
  261 calls (`tools/film/parse_tables.py`). For production calls these were checked for this plan:
  - the distribution of points around each call's cut-off;
  - the funded share by year;
  - that the cut-off is sharp in all 77 production calls;
  - the counts near the cut-off (§5);
  - one full table: call 2026-A-2-1-3, feature fiction 2026, with titles, points and awards.
- **Outcome sources (structure).** For this plan, the author checked which columns the UFD premiere lists
  (2000–2025) and the UFD annual and monthly market tables contain. For this plan, LUMIERE (European Audiovisual
  Observatory) was queried for Czech-produced films of production year 2019, to see its format. That query showed
  the titles and admissions of its first three rows (*Ženy v běhu*, *Poslední aristokratka*, *Přes prsty*). When the
  plan was committed, this analysis had not matched any application to an outcome or compared any admissions
  figure with any score.
- **Prior expectation.** The author expects funded projects to reach cinemas more often. She has no stated
  expectation about whether points foresee audiences.

## 1. Questions

- **Q1 (effect).** Near a call's funding cut-off, does production support change whether a project reaches Czech
  cinemas, and how many admissions it gets?
- **Q2 (forecast).** Among projects that reached cinemas, do the Council's points foresee admissions?

Q1 is causal at the cut-off only. Q2 is descriptive: points are not randomly assigned, and they reflect what the
Council knows about cast, producer and genre.

## 2. Data

- **Units.** Applications in production calls ("výroba") for feature fiction, documentary and animation, including
  debuts, low-budget films and minority co-productions. Short-film calls are reported separately. Calls whose
  table could not be parsed are listed and excluded; 2015 results exist only as PDFs and are excluded.
- **Running variable.** The Council's total points, minus the call's cut-off. The cut-off is the midpoint between
  the lowest funded and the highest unfunded total.
- **Treatment.** An award greater than 0 in that call.
- **Outcome window.** Calls from 2016 to 2021 (primary): every project has had at least four years to be made and
  released by 30 September 2026. Calls from 2022 count only in a release-within-three-years sensitivity check.
  Later calls are used only for Q2's description of points.
- **Outcomes.**
  - O1, release: the project premiered in Czech cinemas by 30 September 2026. Source: UFD premiere lists
    2016–2025, plus LUMIERE Czech admissions above 0 for 2026.
  - O2, Czech admissions from LUMIERE (0 if not released), analysed as log(1 + admissions).
  - O3, total European admissions from LUMIERE, as a secondary outcome.
- **Repeated applications.** A project that applied in several calls appears once per call. The primary analysis
  keeps its first application only; the sensitivity check keeps all of them, with errors clustered by project.

## 3. Linking applications to films (fixed before this analysis joined any outcome)

Working titles change, and this is the main measurement risk. If funded projects were easier to trace, the
estimate would be biased towards an effect.

- **The matcher is blind.** It sees only the application's title, the applicant and the call year. It never sees
  the points or the award; the code reads those columns only after the links are frozen.
- **Rules, applied in order.**
  1. An exact normalized title match (case, diacritics and punctuation removed), released within 0–6 years of
     the call year.
  2. A fuzzy title match: token-set similarity of at least 0.90, plus the same producer company in LUMIERE's
     producer field where LUMIERE gives one.
  3. Otherwise, no match.
- **Human review.** Every rule-2 link and a random 10 % of rule-1 links are checked by hand, blind to funding.
  Every decision is logged in `docs/research/film-fund-links.csv`.
- **A check on the risk itself.** The match rate by funding status is reported. If it differs, the sensitivity in
  §6 treats unmatched funded and unfunded projects symmetrically.
- **Freezing.** The links are frozen and hashed in a commit before the analysis script joins any points.

## 4. Estimation

- **Q1.** A pooled, normalized regression discontinuity across calls (Cattaneo, Idrobo and Titiunik 2020):
  - local linear on each side, with a triangular kernel and the MSE-optimal bandwidth (`rdrobust`);
  - robust bias-corrected 95 % confidence intervals, clustered by call;
  - call fixed effects as a robustness check;
  - the effective n (applications and calls inside the bandwidth) is reported next to the estimate.
- **Q2.** Released projects only: Spearman's ρ between total points and log admissions within call (call-demeaned).
  A 95 % bootstrap interval resamples calls. The same is reported for each criterion that has a fixed meaning
  across the scheme years, and for "Potenciál pro publikum" where it exists (2025–, descriptive, no outcome yet).

## 5. Validity checks (run at design stage on points only, where possible)

- **Manipulation.** The Council scores knowing the allocation, so points could be bent around the cut-off. Tests:
  - a density test at the cut-off (`rddensity`; McCrary 2008);
  - balance at the cut-off of the budget, the amount requested, the share requested and the applicant's number of
    earlier funded applications.
  If either check fails at 5 %, Q1 is reported as **indeterminate**.
- **Structural gap.** By construction no application sits exactly at 0: the nearest are half the gap between the
  last funded and the first unfunded total. A donut sensitivity check drops |distance| < 0.5.
- **Sample at the design stage** (2016–2021, all production; points and funding only):

  | bandwidth | applications | funded / not | detectable difference in release share (80 % power, 5 %) |
  |---|---|---|---|
  | ±3 points | 112 | 53 / 59 | about 0.37 |
  | ±5 points | 249 | 128 / 121 | about 0.25 |
  | ±8 points | 412 | 204 / 208 | about 0.19 |

  An effect smaller than about 0.2 on the release share cannot be told apart from none. If the interval includes
  0 and the bound in this table, the result is labelled **underpowered**, not "no effect".

## 6. Labels and sensitivity

- **Q1, O1:** **supported** if the 95 % interval excludes 0; **not supported** if it lies within ±0.10;
  **underpowered** otherwise. O2 uses the same rule on the log scale, with ±0.25.
- **Q2:** ρ with its interval, descriptive, no label.
- **Sensitivity:**
  - bandwidth halved and doubled;
  - donut;
  - feature-length only;
  - 2016–2022 for O1 within three years;
  - all applications, with errors clustered by project;
  - unmatched projects in both groups counted as released, to bound the effect of linking errors.

## 7. What this will not show

- **The cut-off only.** The effect of support for projects far from the cut-off.
- **No counterfactual quality.** Whether a film would have been better with support.
- **Other money.** The effect of the production incentives, which are a separate scheme.
- **Television and festivals.** Television premieres and festival selection are outside the data.
- **Fund concentration.** Funding counts the fund's award only. A project may also have Czech Television or
  regional money that this data does not show.

## References

- Cattaneo, M. D., Idrobo, N. and Titiunik, R. (2020). *A Practical Introduction to Regression Discontinuity Designs: Foundations*. Cambridge University Press.
- McCrary, J. (2008). Manipulation of the running variable in the regression discontinuity design: a density test. *Journal of Econometrics* 142(2), 698–714.
- Státní fond audiovize (2026). Jednání rad — rozhodovací tabulky. https://sfa.gov.cz/jednani. Accessed 1 October 2026.
- Státní fond kinematografie (2014–2024). Zápisy z jednání Rady. https://oldfondkinematografie.cz/zapisy-z-jednani-rady-statniho-fondu-kinematografie.html. Accessed 1 October 2026.
- Unie filmových distributorů (2026). Premiéry v českých kinech. https://www.ufd.cz/prehledy-statistiky/premiery-v-ceskych-kinech. Accessed 1 October 2026.
- European Audiovisual Observatory (2026). LUMIERE database. https://lumiere.obs.coe.int/. Accessed 1 October 2026.

## Changes after registration

**1 October 2026 (1) — linking recall audit, written before it is run.**

- **Trigger.** The match-rate check in §3, run after the links were frozen at `9fc6666`, linked 51 % of funded and
  31 % of unfunded feature-length applications from 2016–2021 to a Czech release. A funded feature is expected to
  be released far more often than 51 %, so title changes are probably leaving many released films unmatched.
  Funded projects may be easier to trace, which would bias O1 towards an effect. No points-based estimate has been
  computed in this analysis; in this analysis, only this match rate by funding status has been computed.
- **Audit.**
  - Draw, with seed 20261002, 30 funded and 30 unfunded unmatched applications from the primary sample.
  - Shuffle them into one sheet that does not show funding or points.
  - For each, search by hand for a released film: candidates by title similarity (top 5), plus LUMIERE films whose
    Wikidata production company (P272) matches the applicant within the 0–6-year window.
  - Record "found / not found" with the film. Recall by group is computed only after every row is decided.
- **New rule 4 (producer), applied blind to every application if the audit finds released films missed in either
  group.**
  - Same production company (normalized name, via Wikidata P272 on LUMIERE films).
  - Release within the window.
  - Title token overlap of at least one distinctive word, or a unique candidate for that company in that window.
  - Every rule-4 link is hand-reviewed as in §3.
- **Reporting.** The audit's recall by group is reported in the article, whatever it shows. If recall still differs
  by group after rule 4, Q1 O1 reports the bounds from the §6 sensitivity as its primary range.

**1 October 2026 (2) — result of the recall audit (`docs/research/film-fund-recall-audit.csv`).** All 60 rows were
decided blind before the funding key was opened.

| group | audited | released under another title | unsure | not found |
|---|---|---|---|---|
| funded | 30 | 3 | 0 | 26 (+1 with no cinema release) |
| unfunded | 30 | 2 | 1 | 27 |

- **Implied linking recall** for released films: about 91 % among funded and 82–87 % among unfunded applications.
  The gap is small and goes the way that would inflate an effect, so Q1 O1 is reported with the §6 bounds.
- **Rule 4 (producer) runs as planned**, but Wikidata gives a production company for only 52 of the 999 LUMIERE
  films, so it can add little. This limitation is stated in the article.

**5 October 2026 — wording only.** The status line and §0 now state that the author had worked with these data
since July 2024, and statements about what had been looked at are scoped to this analysis. No rule, number or
label changed.

**9 October 2026 — correction to the 5 October wording change.** The 5 October 2026 change rewrote the status line
and parts of §0 in place instead of appending. The registered status line read: "**Status: design committed 1
October 2026, before any application is linked to a release or to admissions.** Registration is self-timestamped. No
OSF entry is made, by the author's decision of 1 October 2026. In the article this is a "registered analysis plan:
design committed at `<hash>` on 1 October 2026, before the results commit; commit times are self-reported"." The
registered §0 read, for the outcome sources: "**Outcome sources (structure only).** I have checked which columns the
UFD premiere lists (2000–2025) and the UFD annual and monthly market tables contain. LUMIERE (European Audiovisual
Observatory) was queried once, for Czech-produced films of production year 2019, to see its format. That query
showed the titles and admissions of its first three rows (*Ženy v běhu*, *Poslední aristokratka*, *Přes prsty*). No
application has been matched to any outcome. No admissions figure has been compared with any score." The heading of
§3 read "Linking applications to films (fixed before any outcome is looked at)". The original text is in the
history of this file at commit `488d7c6`. On main, this design and the results first appear together in the squash
commit `488d7c6`, so the order of design and results is not independently timestamped there; the branch commits
`3ddd69c` (design) and `5a48067` (results) are self-reported. The wording of 5 October 2026 is kept above; this note
records what it replaced.

**9 October 2026 (clarification of today's note).** "Worked with these data since July 2024" means the author has worked
with these sources continuously since July 2024, in work that led to this study, so the design was written with knowledge of
the sources, not blind to them. This replaces the reading given earlier today (that its extent was unrecorded, or a
list of what it covers). The registered text and the dated notes above are unchanged.
