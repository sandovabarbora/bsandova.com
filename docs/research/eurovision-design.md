# Eurovision, not Brussels? Diaspora, juries and the EU in Eurovision votes — research design

**Status: design committed 3 October 2026, before this analysis was run; the author has worked with these data since
April 2025.** Registration is self-timestamped, as for the other studies: design → power → code → data → results, each in
a dated commit. In the article: "pre-specified analysis: design committed at `<hash>` on 3 October 2026, before this
analysis was run; the author had worked with these data since April 2025; commit times are self-reported". Deviations are listed, dated, under "Changes after registration".

## 0. What has already been seen

- **Votes.** The author has worked with these data since April 2025. The plan sets the analysis in advance; the author
  already knew the data. Sources: the Eurovision Song Contest dataset by Spijkervet (GitHub, releases to 2023) [D1], with
  `votes.csv` (year, round, from, to, points), and the Mirovision repository by Burgoyne, Spijkervet and Baker (MIT)
  [D2], with `data/CSV/votes.csv` (year, round, from_country, to_country, total_points, televoting_points,
  jury_points) and `jurors.csv` (year, round, from_country, jurors A–E, to_country).
- **Rules, as general knowledge.** Since 2016 each country gives two sets of points, one from a five-member jury and
  one from its televote; since 2023 the semi-finals are decided by televote only, and a "rest of the world" online
  vote exists. These are checked against the data at the data step.
- **Prior expectations.** The author expects diaspora to matter more for televotes than for juries (H1), more
  televote points for Ukraine where more Ukrainian refugees live (H2), and has no firm expectation for EU accession
  (H3), half-hoping for "Eurovision, not Brussels".

## 1. Questions and hypotheses

- **H1 (primary).** The larger the diaspora of country *j* living in country *i*, the more points *i*'s televote gives
  *j* **relative to** *i*'s jury. Juries and televotes judge the same songs on the same night, so their difference
  isolates what a public brings that a panel of five professionals does not.
- **H2.** From 2022, voters in countries hosting more Ukrainian refugees per inhabitant gave Ukraine more televote
  points relative to their juries than before 2022.
- **H3.** When two countries are both in the European Union, they give each other a larger share of their points than
  before (EU accession as a staggered treatment of country pairs, 1975–2025). Brexit is reported as the reverse case,
  exploratory.

## 2. Data

- **Votes 2016–2023.** Mirovision `votes.csv` [D2] (televote and jury points by country pair, round and year).
- **Votes 2024–2025.** The split jury and televote tables of the English Wikipedia articles on the 2024 and 2025
  contests, at fixed revisions recorded at the data step (CC BY-SA) [D3]. The same parser is run on the 2023 article
  and must reproduce Mirovision's 2023 rows exactly; any mismatch is listed and resolved before estimation.
- **Votes 1975–2015 (H3).** Spijkervet `votes.csv` [D1], finals and semi-finals, total points.
- **Diaspora.** UN DESA, International Migrant Stock, by destination and origin [D4]: persons born in *j* living in *i*,
  per 1 000 inhabitants of *i*. Stock year: 2015 for contests 2016–2017, 2020 for 2018–2022, the latest revision
  (2024, if published; else 2020) for 2023–2025. Dyads with no figure are dropped and listed.
- **Refugees (H2).** UNHCR Refugee Data Finder [D5]: refugees and people under temporary protection from Ukraine in
  each country, end of 2022 (for 2022 and 2023) and end of 2024 (for 2024 and 2025), per 1 000 inhabitants (World
  Bank population).
- **EU membership (H3).** Accession and exit dates from the EU's official list [D6]: 1973, 1981, 1986, 1995, 2004,
  2007, 2013; the United Kingdom out from 2020.
- **Countries.** Each participant as in the data; "rest of the world" and any non-country voter are dropped. Australia
  is included. Yugoslavia, Serbia and Montenegro and their successors are separate units, as in the data.

## 3. H1: diaspora, televote against jury

- **Cells.** One row per voter *i*, performer *j* (*j* ≠ *i*), contest year *t*, round *r* (final, first or second
  semi-final) and audience *a* (televote, jury), wherever *i* voted in *r* with **both** audiences and *j* performed in
  *r*. Rounds where only one audience voted (semi-finals from 2023) are excluded. Points 0, 1–8, 10, 12. Years
  2016–2019 and 2021–2025.
- **Diaspora.** x = log(1 + migrants born in *j* per 1 000 inhabitants of *i*).
- **Model.** Poisson pseudo-maximum likelihood:

    log E[points] = μ(i, j) + φ(i, t, r, a) + ψ(j, t, r, a) + β · x · Televote

  The dyad effect μ absorbs everything fixed about the pair (neighbours, language, history, distance), common to both
  audiences. φ absorbs each voter's audience-specific generosity in each round, ψ each song's audience-specific
  appeal. β is how much faster televote points than jury points rise with the diaspora.
- **Inference.** Standard errors clustered by undirected country pair. 95 % intervals.
- **Software.** Python `pyfixest` (`fepois`), version recorded.
- **Label.** Let R = exp(β · x90), the televote-to-jury points ratio implied for a dyad at the 90th percentile of x
  among dyads with a positive diaspora, against a dyad with none. **Supported** if the 95 % interval of β lies wholly
  above 0. **Not supported** if the interval of R lies within 0.90–1.10. Otherwise **inconclusive**.

## 4. H2: Ukraine

- **Panel.** Each voter *i* in each final with Ukraine performing, 2016–2025 (Ukraine did not take part in 2019).
  Outcome: televote points minus jury points to Ukraine.
- **Model.** OLS: outcome ~ voter FE + year FE + γ · log(1 + Ukrainian refugees per 1 000 in *i*) · Post2022,
  where the refugee figure is fixed at its end-2022 value for the interaction. Standard errors clustered by voter.
- **Label.** **Supported** if the 95 % interval of γ lies wholly above 0; **not supported** if it lies within ±0.5
  points per unit of the log measure; otherwise **inconclusive**. H2 has about 40 voters and is reported as a second,
  smaller test.

## 5. H3: EU accession

- **Panel.** Directed dyads *i* → *j*, years 1975–2025, rounds in which *i* voted and *j* performed. Outcome: the
  share of *i*'s points in that round that went to *j* (so the doubling of points in 2016 and changes of scale do not
  matter). 2016 onwards: televote plus jury.
- **Treatment.** The dyad is treated from the first contest in which both countries are EU members. Dyads where
  either country is never an EU member in 1975–2025 are the comparison group. Dyads already both-EU in 1975 are
  always treated and excluded. Brexit: UK dyads stop being treated from 2020 and are excluded from the main estimate.
- **Estimator.** Gardner's two-stage difference-in-differences (`did2s` in pyfixest) with dyad and year effects,
  robust to staggered timing and an unbalanced panel; event time −10 … +10; standard errors clustered by undirected
  pair. Dyads with fewer than three pre-treatment contests are dropped and counted.
- **Estimand and label.** The average effect over event years 0 … +5. **Supported** if its 95 % interval lies wholly
  above 0; **not supported** if it lies within ±10 % of the treated dyads' mean share in event years −5 … −1;
  otherwise **inconclusive**.
- **Pre-trends.** Event-time coefficients −10 … −2 reported with intervals.
- **Brexit (exploratory).** UK ↔ EU dyads, 2016–2019 against 2021–2025, relative to UK ↔ non-EU dyads.

## 6. Checks (all reported)

- H1 without 2022 (Ukraine's year); finals only; semi-finals only; each juror's ranking (Mirovision `jurors.csv`,
  2016–2023) in place of the jury's points, as a Poisson model on rank-based points.
- H1 with contiguity × Televote and shared official language × Televote added (CEPII GeoDist [D7]), to see whether
  the diaspora term survives the other "affinity" terms.
- H3 restricted to finals; H3 without the 2004 cohort; H3 with juries only and televotes only for 2016–2025.

## 7. Power

Computed before the data commit by simulation on the cell structure only (numbers of voters, performers and rounds
per year from the rules, not from the data), for assumed values of β and of the H3 effect; logged in a change note.

## 8. Outputs

A Research article in Pop, measured (2 500–3 500 words): the H1 estimate and a map of Europe showing, for one
chosen country, which performers its televote favours over its jury; the H3 event study; H2 as a short section; a
table of the largest diaspora dyads. Data, code and the per-cell tables published.

## 9. What this will not show

- Friendship between peoples. Points measure a public's and a jury's taste for one song on one night.
- Why diaspora votes: identity, organisation, or simply more phones per capita among movers.
- Whether the EU made Europe friendlier: H3 measures one revealed preference, and accession comes with much else
  (travel, trade, migration), which the estimate bundles.

## References

- [D1] Spijkervet, J. The Eurovision Song Contest Dataset. GitHub, releases to 2023; Zenodo, doi:10.5281/zenodo.4036457.
- [D2] Burgoyne, J. A., Spijkervet, J., Baker, D. J. (2023). Mirovision data and code (MIT). github.com/Amsterdam-Music-Lab/mirovision.
- [D3] Wikipedia contributors, *Eurovision Song Contest 2023/2024/2025*, revisions recorded at the data step.
- [D4] United Nations, Department of Economic and Social Affairs, Population Division. International Migrant Stock.
- [D5] UNHCR. Refugee Data Finder.
- [D6] European Union. Countries: EU member countries and dates of accession (european-union.europa.eu).
- [D7] Mayer, T., Zignago, S. (2011). Notes on CEPII's distances measures: the GeoDist database. CEPII WP 2011-25.
- [R1] Gardner, J. (2022). Two-stage differences in differences. arXiv:2207.05943. [verify before publication]
- [R2] Santos Silva, J. M. C., Tenreyro, S. (2006). The log of gravity. *Review of Economics and Statistics* 88(4), 641–658.

## Changes after registration

**3 October 2026 (power; before this analysis read any vote).** Power was simulated as §7 promised.

- **H1** (`tools/eurovision/power.py`; structure from the rules, diaspora distribution assumed): with nine contests
  the registered model detects a televote premium of R = 1.18 at the 90th percentile of x with power about 1.00, and
  R = 1.09 with power 0.63; with no effect it rejects in 7 % of draws (nominal 5 %).
- **H3** (`tools/eurovision/power_h3.py`): participation by country and year was taken from Spijkervet's
  `contestants.csv`, reading only its `year` and `to_country` columns (its points columns were not used for the power calculation). With a
  simplified final-only structure, the standard error of the 0 … +5 average is about 0.0016 in share of points,
  about 4 % of the pre-accession mean (≈ 0.04); the minimum detectable effect at 80 % power is about 12 % of that
  mean. With no effect the simulated test rejects in 10 % of draws and the mean estimate is −3 % of the mean, because
  the simulation ignores the first stage's uncertainty; the registered estimator (did2s) accounts for it. The ±10 %
  margin for "not supported" is therefore reachable only if the estimate is close to zero.

Nothing in §1–§6 changes.

**3 October 2026 (sources; files downloaded for this analysis, which so far read only headers, round labels and country
codes).** All inputs were downloaded and hashed (`tools/eurovision/collect.py`, `tools/data/eurovision/manifest.json`).
Read so far by this analysis: the
header lines, the distinct round labels and voter codes of the vote files, the Mirovision country list, the header
rows of the UN DESA workbook (and its world-total row, which appears above the headers), the CEPII column names, the
UNHCR and World Bank JSON keys, and the captions and header layout of the Wikipedia tables with digits masked.

- Mirovision's `votes.csv` ends in **2022** and its `jurors.csv` covers 2016–2022, not 2023 as assumed in §2.
  Spijkervet's `votes.csv` (to 2023) carries `tele_points` and `jury_points` as well. **Change:** split votes
  2016–2023 come from Spijkervet; Mirovision 2016–2022 is used as a cross-check (rows and points compared, counts
  of mismatches reported); the individual-juror check covers 2016–2022.
- The Wikipedia parser is validated on 2023 against Spijkervet (not Mirovision).
- The UN DESA file is the 2024 revision, with stock years 1990–2024; 2015, 2020 and 2024 are used as in §2.
- CEPII GeoDist is the 2004 file (`dist_cepii.xls`): Romania is `ROM`, and Serbia appears as `YUG`, which is used
  for Serbia; Montenegro and any country absent from the file have no contiguity or language value and are left out
  of that check only.

Code registered with this note: `prepare.py`, `estimate.py`. `estimate.py` was run once on synthetic tables with
planted effects (H1 latent 0.25, H3 latent 0.3): H1 recovered β = 0.19 (0.13–0.24), labelled supported; H3 recovered
+0.013 in share (+41 % of the pre mean), supported.

**3 October 2026 (data step; deviations in prepare.py and estimate.py, before any estimate).** The first run of
`prepare.py` stopped: one Wikipedia table's voters' row was not all header cells. The row is now chosen as the one
with the most country names and no digits. The second run showed two code errors and one data fact, from counts
only: (1) Spijkervet's `contestants.csv` carries country names instead of codes in some years, so those performers
were unmatched; names are now mapped to codes. (2) The "rest of the world" televote (`WLD`) entered H3 as a voter in
2023; non-country voters are now dropped in H3 as in H1. (3) The UN table lists, for some destinations (e.g. the
United Kingdom), only the main origins; an absent origin is "not reported separately", not zero. As registered (§2),
such dyads are dropped: 8 944 of 26 316 H1 cells (661 directed pairs, listed in `eurovision-data.json`).
**Added check** (deviation, labelled as such): the same H1 model with absent origins counted as zero migrants.
Validation: the Wikipedia parser reproduces Spijkervet's 2023 points exactly (740 rows, no difference; Spijkervet's
10 extra rows are the rest-of-the-world televote); Spijkervet and Mirovision agree on every matched 2016–2022 row
(televote and jury points identical; 367 rows unmatched between the two files, reported).

**3 October 2026 (H1 fixed effects; after the data step, before any estimate was seen).** The registered H1 model
(pair + voter×year×round×audience + performer×year×round×audience) does not converge in pyfixest (demeaning fails
after 100 000 iterations, with and without the iterative separation check), and a Poisson GLM with the effects as
dummies diverges (infinite weights), a sign of separation among the three sets of effects. Testing which
combinations converge (no coefficient printed): voter + performer effects alone, pair + voter, and pair×year×round +
voter + performer all converge; pair + performer does not. **Change:** the pair effect μ(i, j) becomes μ(i, j, t, r),
one per pair, year and round. It nests the registered effect and absorbs more (anything about the pair in that
contest, e.g. a song in the voter's language), and β is still identified only from the televote against the jury of
the same voter for the same song. The cost is the cells of pair-rounds with no point from either audience, which
carry no information and drop out (17 372 → about 11 300 cells). All H1 checks use the same effects.

**3 October 2026 (estimation run; code changes after the first estimates were seen).** (1) pyfixest's `did2s` failed
in its variance step when its first stage dropped rows (pairs or years without an untreated row, pairs seen once);
those rows are now dropped before the call. The main H3 estimate was produced with this filter. (2) The registered
H3 checks of §6 (finals only; without the 2004 cohort) and the exploratory Brexit comparison were missing from the
registered code; they were added after the first H1–H3 estimates had been printed, as specified in §6, with a
stricter filter (pairs and years with at least two untreated rows) needed for `did2s` on the subsets. (3) The
registered check "H3 with juries only and televotes only, 2016–2025" cannot be estimated: no country joined the EU
between 2016 and 2025 (the last accession was Croatia's in 2013), so there is no treated change in that window.

**5 October 2026 (wording).** Work dates added: the author has worked with these data since April 2025. Notes that
read as if the votes had not been seen before the design are scoped to this analysis. No number, estimate, label or
reference changed.

**9 October 2026 (correction of the 5 October rewording; registered text quoted).** On 5 October 2026 (commit
`c953c92`) four passages of this file were rewritten in place instead of being corrected by a dated note. The
registered wording, as committed at `f304d8c` (tag `eurovision-design`) and in the later dated notes of 3 October, was:

- Status: "**Status: design committed 3 October 2026, before any vote, migrant-stock or refugee figure was downloaded
  or opened.** Registration is self-timestamped, as for the other studies: design → power → code → data → results,
  each in a dated commit. In the article: "registered analysis plan: design committed at `<hash>` on 3 October 2026,
  before the data commit; commit times are self-reported"."
- §0, Votes: "The Eurovision Song Contest dataset by Spijkervet (GitHub, releases to 2023) [D1]: its README, the
  release list and the description of `votes.csv` (year, round, from, to, points). The Mirovision repository by
  Burgoyne, Spijkervet and Baker (MIT) [D2]: its file list and the header lines of `data/CSV/votes.csv` (year, round,
  from_country, to_country, total_points, televoting_points, jury_points) and `jurors.csv` (year, round,
  from_country, jurors A–E, to_country). No row was read."
- Power note heading: "3 October 2026 (power; before any vote was read)", and in it: "(its points columns were not
  read)".
- Sources note heading: "3 October 2026 (sources; files downloaded, only headers, round labels and country codes
  read)", and in it: "Read so far: the header lines, …".

The rewording added that the author had worked with these data since April 2025. The repository holds no record of
that earlier work, so what it covers (the public vote datasets, Eurovision results in general) rests on the author's
statement (private; not verifiable); read with it, the registered statement "No row was read" describes this
analysis's files, not the author's prior knowledge of the votes. The article now uses the
wording of the editorial standard, §6: design committed at `f304d8c` on 3 October 2026, before the results commit
`70f75a9` (tag `eurovision-results`); commit times are self-reported, and the branch was pushed after the analysis.
Both commits reach `main` only in the squash commit `961638c`, so on `main` they are not independently timestamped;
the tags were created on 9 October 2026 and are not evidence of the commit dates. The article had said that no
change was made after its result was seen; three were made after the first estimates were printed (the row filter
for `did2s`, the finals-only and without-2004 checks, the Brexit comparison), as the 3 October estimation note
records. No number, estimate or label changes.

**9 October 2026 (clarification of today's note).** "Worked with these data since April 2025" means the author has worked
with these sources continuously since April 2025, in work that led to this study, so the design was written with knowledge of
the sources, not blind to them. This replaces the reading given earlier today (that its extent was unrecorded, or a
list of what it covers). The registered text and the dated notes above are unchanged.
