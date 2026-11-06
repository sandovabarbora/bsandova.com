# Czech film production incentives: how much of what is promised is paid, how long it takes, and how much is already committed — research design

**Status: pre-specified analysis, design committed 5 November 2026, before any outcome column was read.** A descriptive
census of the incentive projects the State Audiovisual Fund lists; it makes no causal claim. The steps follow in dated
commits: design → data snapshot (files fetched and hashed, outcome columns unread) → data-step code (tagged
`rebates-data-step` before it reads any outcome column) → estimation code (tagged `rebates-code`) → results. Commit
times are self-reported; the signed tag `rebates-design` fixes this text. Deviations are listed, dated, in the change
log.

## 0. What has already been seen

- **The two project lists, structure only.** On 5 November 2026 the drafting assistant downloaded the Fund's two
  current lists of incentive projects (§2.1). It read their column headers, the number of evidence numbers per
  registration year in the number suffix, the patterns of the evidence numbers with digits masked, and the titles of
  the first four rows of each list. No allocation, no payout, no decision date and no applicant was read. Evidence
  numbers seen (by a pattern match on the start of a line, so not yet a row count): list A 507 (37, 75, 112, 116, 70
  and 97 for 2016–2021); list B 462 (151, 98 and 213 for 2023–2025), of which two are in odd formats (`###/P/####`,
  `##/####`) and 460 in the form `#P/####` to `###P/####`.
- **An older list, structure only.** The Fund's list of 15 March 2024 was downloaded to check year coverage; only its
  counts per registration year were read. It has no 2022 numbers either. It is not used (§2.1).
- **No 2022 registrations.** Press reports (ČT24, MediaGuru, July 2022) say the Fund stopped accepting registrations
  from January 2022, because demand registered by the end of 2021 exceeded the subsidy for 2022. The lists have no
  2022 numbers. §2.1 treats 2022 as a year without registrations, and §3 check 3 tests it.
- **The process, from the Fund's applicant guide (2025) for the law in force until 31 December 2025.** Registration
  certificate (OOR) → evidence certificate (OOE), which sets the allocation → application for the incentive (ŽOP) →
  incentive decision (RFP). The ŽOP must be filed within 4 years of delivery of the OOR, or it is rejected (§49(2));
  a live-action project may file it in two parts, the second within 12 months of the first; a single application is
  the "2nd or only" instalment. A ŽOP above the allocation by more than 5 % or 1 m CZK is cut to the allocation;
  one below it by as much is rejected and may be refiled within the 4 years. The allocation is therefore a ceiling,
  set from planned costs; the incentive is a share of the eligible costs actually spent.
- **One outcome pair from a search summary.** A web-search summary quoted one row of a Fund list: an amount of
  1,179,300 CZK beside a paid amount of 904,625 CZK (about 0.77), for a project it did not name. This is an exposure
  to two outcome numbers of one project out of about 970 listed projects; no rule below uses it, and the article's methods note will
  mention it.
- **Context figures (not results, not used as inputs).** The Fund's notice of 27 March 2026 stopping new registrations
  states the 2026 incentive subsidy as 1,611,972,229 CZK and says it is fully committed to projects already in the
  process, some of whose proceedings are interrupted for lack of money (it is the denominator of Q3, §2.8). Press
  figures heard: applications of about 9.3 bn CZK in 2025 (Screen Daily); a claim that filmmakers "bring Czechia four
  billion" this year (E15); a 2026 split of about 64 m EUR for incentives and 27 m EUR for selective support. The
  Fund's English page states a 25 % rebate on eligible costs, 35 % for animation, 66 % of withholding tax, a cap of
  450 m CZK per project and at most 80 % of the budget as eligible costs.
- **Position of the author.** The author works around Czech film production (she builds a production tool for film
  crews). She has no stated view on whether the incentives are worth their cost. The article **will** carry a one-line
  disclosure of this in its methods note.
- **Prior expectation (author, 5 November 2026):** "nearly everything that is promised is paid" — the problem being
  that too little money is left for new projects. The second half is not tested (§7).

## 1. Questions

The unit is the incentive project. All five parts describe the Fund's own lists as they stand on the list date; they
say nothing about whether the incentives pay off for the state (§7).

- **Q1, payout ratio (headline).** Among mature projects with an allocation (§2.5), what share of the allocated money
  was paid? R = Σ paid ÷ Σ P0, money-weighted, with the two bounds of §2.6. Reported with: the decomposition of the
  shortfall (§2.6), the share of projects in each status, and the project-level median of paid ÷ P0.
- **Q2, time to the final decision.** From the evidence certificate to the incentive decision on the 2nd or only
  instalment, on all projects with an allocation: the cumulative share with a final decision 1, 2, 3, 4 and 5 years
  after the certificate, with cancellation and lapse competing and open projects censored at the list date; and the
  time at which that share reaches 50 %, or "not reached" (§2.10).
- **Q3, money already allocated and not yet paid.** On each list's date, the unpaid remainder of open projects (§2.7),
  for list A and list B separately, and its ratio to one year's subsidy (S2026).
- **Q4, by size and concentration.** R (§2.6 bounds) separately for mature projects above (strictly greater) and at or
  below the median P0 of mature projects; the share of Σ P0 held by the 5 largest projects; R with the single largest
  project left out. Descriptive.
- **Q5, the planned costs behind the allocations.** By registration year, Σ P0 ÷ the headline rate in force (§2.9):
  the eligible-cost base the allocations imply. Descriptive, no label; set beside an official figure for the same
  years if one is pinned in the data step (§2.11).

## 2. Definitions, rules and sources

### 2.1 Sources

- **List A:** "Seznam pobídkových projektů 2016–2021", state of 30 January 2026,
  https://sfa.gov.cz/data/document/2026/02/Seznam-pobidkovych-projektu-2016-2021-30012026.pdf
- **List B:** "Seznam pobídkových projektů 2023–2026", state of 7 October 2026,
  https://sfa.gov.cz/data/document/2026/10/Seznam-pobidkovych-projektu-2023-2026-7.10.2026.pdf
- **The Fund's notice of 27 March 2026** (S2026),
  https://sfa.gov.cz/data/article/2026/03/Doprovodna-informace-k-zastaveni-prijmu-zadosti.pdf
- **The Fund's applicant guide 2025** (process, §0),
  https://sfa.gov.cz/data/download/2025/01/Pruvodce-zadatele-filmove-pobidky-2025.pdf
- **List date.** Each list has its own state date; status and times are measured to that date.
- **Coverage.** Projects registered under act 496/2012 Coll. as in force until 31 December 2025, with evidence numbers
  of 2016 to 2025; 2022 has none (§0). Projects entered ("zápis") under the law in force from 1 January 2026 are not in
  the lists and are outside the study (§7). Projects with evidence numbers before 2016 are outside.
- **Snapshot.** All four files are fetched again in the data step, hashed (SHA-256) into
  `docs/research/rebates-files.sha256` and kept under `tools/data/rebates/`. If a list on the Fund's site has a newer
  state date when the snapshot is taken, the newer one is used and the change is logged; the counts of §3 check 6 are
  then read from the newer file at the data step, before any outcome column is read.

### 2.2 Columns and parsing

The lists have the same columns: evidence number; title; applicant; tax ID; registration request (date received);
registration certificate (date issued); evidence certificate (date issued); the §48(1) deadline; cancellation of the
evidence certificate (date issued); change of the evidence certificate (date issued); allocation, 1st instalment;
allocation, 2nd or only instalment; new allocation, 1st instalment; new allocation, 2nd or only instalment; incentive
decision, 1st instalment (date issued); incentive decision, 2nd or only instalment (date issued); incentive paid
(current total). Amounts are CZK and are read as exact integers; an empty amount is 0. Repeated header rows, page
breaks and titles wrapped over several lines are merged before any check. The two odd-format numbers of §0 are kept as
printed and parsed like the others; their year is the four-digit suffix.

### 2.3 Promise

- **P0, primary:** allocation 1st + allocation 2nd/only, as set by the evidence certificate.
- **P1, latest:** (new allocation 1st if listed, else allocation 1st) + (new allocation 2nd/only if listed, else
  allocation 2nd/only).
- A project has an allocation if P0 > 0.

### 2.4 Deadline

- D = the §48(1) deadline as listed; if it is empty, the registration certificate date plus 4 years; if that is empty
  too, the project counts in §3 check 4 and has no D (it is never mature).
- **D_eff** = D, or D + 365 days for a project with a 1st-instalment decision date (its second part may be filed up
  to 12 months after the first, §0).
- §3 check 7 tests that the listed column is the 4-year deadline of §0.

### 2.5 Status on the list date (projects with an allocation)

- **Mature:** D_eff + 180 days ≤ the list date, whatever the status. Its outcome no longer depends on how fast it
  moved. The Q1 population is all mature projects, from both lists.
- Within the mature set, and on the same rules for every project:
  - **Decided:** has a 2nd/only decision date at least 180 days before the list date.
  - **Decided, payout pending:** has a 2nd/only decision date less than 180 days before the list date (the payout may
    not yet be entered).
  - **Cancelled:** has a cancellation date and no 2nd/only decision date.
  - **Lapsed or undecided:** none of the above. A ŽOP may have been filed in time and its decision delayed (§0), so
    this status is not read as "dropped".
- **Not mature (open):** every other project with an allocation, whatever its status; it enters Q2, Q3 and §6 checks
  5 and 6, not the headline.
- A project with both a cancellation date and a 2nd/only decision date is decided; such projects are counted and
  listed.
- Projects without an allocation are counted by list and status; they are not part of any money figure.

### 2.6 Q1 ratio, bounds and decomposition

- V = incentive paid (current total).
- **R_low** = Σ V ÷ Σ P0 over mature projects, lapsed or undecided projects at their listed V.
- **R_high** = the same, with lapsed or undecided and decided, payout pending projects counted at max(V, P0), as if
  each were later paid in full. In R_low, decided, payout pending projects count at their listed V.
- **Shortfall decomposition**, in CZK and as shares of Σ P0 − Σ V over mature projects: (a) cancelled, V = 0; (b)
  cancelled, V > 0; (c) decided, V < P0; (d) lapsed or undecided, split by V = 0 and V > 0 and by whether a 1st decision exists; (e)
  decided, payout pending; (f) decided, V > P0, entered as a negative part.

### 2.7 Q3 remainder

- **O** = Σ max(P1 − V, 0) over projects that are not mature and have no cancellation date and no 2nd/only decision
  date older than 180 days. It is reported for list A and list B separately, with no combined figure in the headline.
- **O_R** = Σ max(R1 × P1 − V, 0) over the same projects, where R1 is the Q1 ratio on P1 (§6 check 1), once with its
  low and once with its high bound: the remainder if these projects end as mature ones did.
- Mature lapsed or undecided projects are reported as a third figure, Σ max(P1 − V, 0), separately; they may still be
  paid.
- Each figure is divided by S2026 and reported as "a ratio to one year's subsidy". The lists do not show a payment
  queue, so the ratio is not read as a number of years.

### 2.8 The 2026 subsidy

S2026 = 1,611,972,229 CZK, the amount of the 2026 incentive subsidy under the state budget act of 21 March 2026, as
the Fund's notice of 27 March 2026 states it.

### 2.9 Headline rate (Q5)

The headline rate on eligible costs in force on the registration request date, read in the data step from the
versions of act 496/2012 Coll. (e-Sbírka) and pinned in `tools/rebates/config.py` with the version cited. Q5 is
reported on decided, open and lapsed or undecided projects; cancelled projects are shown as a separate series. The
range is P0 ÷ the highest rate in force for that date (low end) to P0 ÷ the headline rate (the reported figure).

### 2.10 Time (Q2)

- Start: the evidence certificate date (projects with an allocation have one). Event: the 2nd/only decision date.
  Competing events: the cancellation date, and lapse at D_eff + 180 days. Censoring: the list date.
- Estimated with the Aalen–Johansen cumulative incidence; time in days, reported in years (365.25 days).
- A horizon is reported only where at least 30 projects are still at risk at that horizon; otherwise it is "not
  estimable". The 50 % time is "not reached" if the curve stays below 50 % over the estimable range.
- Secondary: the same from the registration request date.

### 2.11 Official cost or spend figure (Q5)

In the data step, before any outcome column is read, the assistant looks, in this order only, in the Fund's annual
reports (výroční zprávy) for 2016–2025 and on the Czech Film Commission site, for a yearly figure of eligible costs or
production spend of incentive projects. If one is found, its source, table and years are pinned in the change log and
shown beside Q5, with its basis (registration year, decision year or calendar spending) stated. If none is found, Q5
is shown alone and the press claim of §0 is quoted as a claim, not tested.

## 3. Checks that flag or stop the run

1. **Row parse.** After the merging of §2.2, every row has an evidence number, a title and a registration request
   date. A row that fails stops the run with its evidence number.
2. **Unique evidence numbers** across both lists. A duplicate stops the run. Separately, pairs across A and B with the
   same title, tax ID and request date are listed (not dropped).
3. **Year coverage.** A number with suffix 2022 stops the run. A suffix outside the list's stated years (2016–2021
   for A, 2023–2026 for B) flags the run and is listed. A request date in 2022 with a suffix of another year
   flags the run and is listed; the decision on it is logged before the code tag.
4. **Order of dates.** Request ≤ registration ≤ evidence ≤ 1st decision ≤ 2nd/only decision, where present; any
   breach is counted and listed, not dropped. More than 2 % of projects with a breach flags the run. Projects without a
   D (§2.4) are counted here.
5. **Paid ≤ latest promise.** V > P1 is counted and listed; more than 2 % of decided projects flags the run.
6. **Counts.** Rows parsed equal the distinct evidence numbers, after the merging of §2.2. A difference stops the run.
   The number of rows of list A is compared with the 507 of §0, and of list B with the 462 of §0 (or with the newer
   counts of §2.1); a difference is logged and flags the run.
7. **The deadline column.** At the data step, before any outcome column is read, D − registration certificate date is
   logged in days, by list. If more than 5 % of projects with both dates deviate from 4 years ± 31 days, the run flags,
   and the definition of D is changed only by a decision logged before the code tag.

A flagged run is published with the flag in the methods note and is not relabelled.

## 4. Estimation

Arithmetic on all listed projects; exact integer and Fraction arithmetic for money; the Aalen–Johansen estimator for
Q2. The lists are the population of registered projects, not a sample, so the money figures carry no sampling
interval. Q2 has no interval either; its uncertainty is the censoring, which the estimator handles, and the at-risk
rule of §2.10.

## 5. Labels

Label on Q1, fixed now, from R_low and R_high (§2.6) on P0:

- **"nearly all paid"** if both are ≥ 0.95;
- **"most paid"** if both are in [0.80, 0.95);
- **"substantially less than allocated"** if both are < 0.80;
- **"depends on the undecided projects"** if they fall in different bands; the headline then states both.

The bands are round numbers chosen before any outcome column was read; the one pair of §0 is one project of about
970 and did not set them. Q2–Q5 carry no label. Labels are never loosened after results.

## 6. Checks reported (none relabels Q1)

1. R_low and R_high on P1 instead of P0.
2. R_low and R_high with cancelled projects left out.
3. R_low and R_high for list A only and list B only.
4. R_low and R_high by registration year (mature projects only).
5. R on all decided projects, mature or not (the fast closers), beside the headline.
6. R_floor = Σ V ÷ Σ P0 over all projects with an allocation, mature or not.
7. Q2 for list A only (the longest follow-up).
8. The 180-day margin of §2.5 and §2.10 at 90 and 365 days.

## 7. Limits stated now

- **Not value for money.** The lists hold allocations and payouts, not spending, jobs or taxes. Whether the incentives
  pay off needs the counterfactual (would the production come without them), displacement of crews and studios, and
  firm-level tax data; none is here.
- **An allocation is a ceiling, not a debt.** It is reserved from planned costs. A ratio below 1 mostly reflects
  spending below plan and cancellations that release money; the lists do not separate these from payment shortfalls,
  and the study does not read a shortfall as the Fund failing to pay.
- **Crowding out is not tested.** Whether money for new projects is short because of old allocations needs the
  Fund's payment schedule. Q3 compares a stock with one year's flow and shows no displacement.
- **Q3 is not a bound.** The new regime is excluded, which pushes it down; delayed payouts of old projects may sit in
  the lapsed or undecided figure, reported separately.
- **Two list dates.** List A is from 30 January 2026, so its open projects may have closed since; A and B are reported
  apart.
- **Q5 is a planned-cost base at registration, not spending.** Animation (35 %) and the rebate on withholding tax
  (66 %) push it up, read at the headline rate; the 450 m CZK cap pushes it down; the net direction is unknown.
  Registration years do not match calendar spending.
- **What the list shows.** The study reads the Fund's lists as published. Payments not yet entered, corrections and
  the meaning of an empty cell are as the Fund records them.
- **Paid is a current total.** Clawbacks may or may not be netted in V.
- **No origin.** The lists do not say whether a project is a foreign service production or a Czech one; the study
  does not split by origin.

## 8. Outputs

- `docs/research/rebates-results.json`: Q1–Q5, the checks, the label, the counts by list and status, the stamp (HEAD
  and tree).
- An article on bsandova.com in the house plain-language style: one chart per point (allocated vs. paid; time to the
  final decision; the unpaid remainder against one year's subsidy; by size; the planned-cost base by year), methods
  and limits folded away.

## Running and verification

- `tools/rebates/` with tests on synthetic lists (no real data read by the tests); a gate that refuses `--run` unless
  the design text equals `rebates-design`, the snapshot equals `rebates-data-step`, the code equals `rebates-code` and
  the tree is clean.
- An independent code review before the code tag, and an independent review of the article before its PR.

## Change log

- 5 November 2026: design rewritten twice after an independent methods review (process pinned from the Fund's
  applicant guide; mature population, bounds and checks); no outcome column was read. This is before the
  `rebates-design` tag.
- 5 November 2026, snapshot step (after the `rebates-design` tag): the four files of §2.1 were fetched again and
  hashed into `docs/research/rebates-files.sha256`; the Fund's page still links the same two lists (states of 30
  January and 7 October 2026), so no newer list is used. No outcome column was read.
- 5 November 2026, headline rate pinned (§2.9) from the law texts, also snapshotted: 20 % of eligible costs for
  registration requests before 1 January 2025 (act 496/2012 as promulgated, §43(4)(a); act 139/2016, point 74, for
  requests from 6 May 2016, transitional provision 3); 25 %, or 35 % for animation, for requests from 1 January 2025
  (act 480/2024, points 201–202, transitional provision 24). The highest rate in force for the low end of the Q5 range
  is therefore 20 % before 2025 (the range collapses there) and 35 % from 2025. The rebate on withholding tax (10 % of
  foreign cast costs before 6 May 2016, 66 % of the tax after) is not a rate on eligible costs and is not used.
  Versions 1–9 of the consolidated act were not readable (paywalled); the rate is read from the promulgated act and
  the amending acts.
- 5 November 2026, official figure for Q5 (§2.11), pinned before any outcome column was read. A separate agent
  searched the Fund's annual reports 2016–2025 and the Czech Film Commission site, and reported labels, pages and
  bases with every figure masked; the drafting assistant has seen no value. No single series covers 2016–2025. Pinned:
  the annual-report figure "Součet uznatelných nákladů, tj. předpokládaná investice všech projektů, které se v roce …
  alokovaly" for 2020 (report 2020, p. 38) and 2021 (report 2021, p. 35), basis the year of the evidence certificate,
  planned costs; and "Žádosti o evidenci podané v … – uznatelné náklady = investice v ČR celkem" for 2025 (report 2025,
  annex p. 84), basis the year the evidence application was filed, planned costs. Not used: 2016–2018 (paid projects
  by payout year, a different basis), 2019 (realisation year, coverage unclear), 2022–2024 (prose or chart, rounded,
  basis unclear), and the Film Commission turnover table (a producers' association figure, not limited to incentive
  projects). Because the pinned basis is the evidence year, Q5 is also reported by the year of the evidence
  certificate (the 2025 figure is set beside it with its different basis stated); the registration-year series of §1
  stays as registered. The three values are read into `tools/rebates/config.py` at the estimation-code step and are
  logged then; they inform no label. The searching agent saw these reports' values, including yearly totals of paid
  incentives; none was passed on.
- 5 November 2026, data step (before the `rebates-data-step` tag; no estimation code exists yet). The parser reads
  word positions (`pdftotext -tsv`) and assigns cells by the header of each page. Results of the structure checks are
  in `docs/research/rebates-structure.json`: §3 checks 1, 2, 3 and 7 pass; check 6 flags, because list A has 509
  rows, all distinct, against the 507 of §0 — two evidence numbers are printed without the slash (`11P2019`,
  `10P2021`) and the pattern match of §0 missed them. The registered comparison count stays 507 and the run stays
  flagged; the flag is explained in the methods note. Check 7: 4 of 508 (A) and 1 of 462 (B) deadlines deviate from
  4 years ± 31 days; 92P/2021 has no listed deadline and takes the §2.4 fallback.
- 5 November 2026, exposures in the data step. (1) While the code-writing agent inspected the layout, a faulty mask
  showed it two outcome cells of one project (60P/2016): a change-of-evidence date and four of the six digits of its
  allocation. (2) To check the column assignment, the agent counted non-empty cells per outcome column (masked
  shapes): this shows, per list, how many projects have an allocation, a cancellation date, a 1st and a 2nd/only
  decision date and a paid amount — status counts, no money. Neither changes a rule.
- 5 November 2026, the real columns differ from §2.2, decided before any estimation code. The lists print one
  allocation ("Alokace") and one new allocation ("Nová alokace"), not split by instalment; the two instalment columns
  are the incentive amounts of the 1st and the 2nd/only decision, beside their dates. Therefore: P0 = Alokace; P1 =
  Nová alokace where listed, else Alokace; "has an allocation" = Alokace > 0. The decision amounts are read but feed
  no rule. Amounts with haléře are read as exact Fractions (§2.2 said integers). Where an evidence-certificate cell
  holds two dates (33P/2017, 65P/2019), Q2 starts at the earlier. Change dates feed no rule; the one unreadable change
  cell (24P/2019) is pinned as unreadable.
- 6 November 2026, estimation-code step (after the `rebates-data-step` tag; no outcome column of the lists read).
  The three official Q5 figures of the 5 November entry were read from the snapshotted annual reports and pinned in
  `config.OFFICIAL_Q5`: 6,957,401,841 CZK for 2020 (report 2020, p. 38) and 6,244,202,515 CZK for 2021 (report 2021,
  p. 35), both "Součet uznatelných nákladů, tj. předpokládaná investice všech projektů, které se v roce … alokovaly",
  basis the evidence year, planned costs; and 9,376,844,134 CZK for 2025 (report 2025, annex p. 84, "Žádosti o
  evidenci podané v 2025 – uznatelné náklady = investice v ČR celkem"), basis the year the evidence application was
  filed. Exposure: the same pages print, next to these, the total allocation of evidence certificates issued in 2020
  and in 2021, the total allocation requested by evidence applications filed in 2025, and on p. 84 the requested
  allocations of a few 2025 projects whose evidence proceedings were interrupted. These are the Fund's published
  figures, not the lists' outcome columns; they change no rule and set no label.
- 6 November 2026, readings fixed in the estimation code where the text above leaves room (before the `rebates-code`
  tag, no outcome column read). (1) Q2 event kinds follow the §2.5 status: a project with a 2nd/only decision date
  has the decision as its event at that date, even if it comes after D_eff + 180 days or after a cancellation; else a
  cancellation date is a cancellation; else a mature project lapses at D_eff + 180 days; else it is censored at its
  list date. Each list's projects are censored at their own list date, and the two lists are pooled. A project whose
  event falls before its start (a date-order breach) is left out of Q2 and listed; one without a start date likewise.
  At a tie, censorings of the same day count as at risk; "at risk at a horizon" is time ≥ the horizon; the 50 % time
  is the first event time at which the decision curve reaches 1/2, reported only if at least 30 are at risk then. The
  curve is computed in exact Fractions. (2) The 180-day margin of §6 check 8 is changed everywhere it appears at
  once: mature (§2.5), payout pending (§2.5), lapse (§2.10) and the Q3 "older than 180 days" rule; Q1, Q2 horizons and
  Q3 are reported at 90 and 365 days. (3) "Registration year" (§1 Q5, §6 check 4) is the four-digit suffix of the
  evidence number (§2.2); the evidence year of the 5 November entry is the year of the earlier evidence-certificate
  date. (4) §3 check 4 uses the earlier evidence-certificate date and the chain of the dates present; its 2 % is of
  all listed projects. (5) §3 check 5 lists every project with V > P1 and flags on decided projects, meaning those
  with a 2nd/only decision date (decided or payout pending). (6) §6 check 5 is on the "decided" status of §2.5 (a
  decision at least 180 days old), mature or not. (7) The Q4 median is exact (the mean of the two middle P0 for an
  even count); the top 5 and the largest project are ranked by P0, ties broken by evidence number. (8) Q5 cancelled
  projects are those with the §2.5 cancelled status, whether mature or not; the rate of each project is that of its
  own request date. (9) A variant of §6 shows the band its bounds would get, beside the headline and never in its
  place. (10) A stop of the data-step checks (§3 checks 1, 2, 3, 6) also stops `--run`.
