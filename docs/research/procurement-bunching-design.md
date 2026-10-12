# Just under the limit: Czech public contracts and the small-scale procurement threshold — research design

**Status: draft analysis plan, 12 October 2026. No contract value in the analysis range has been read, counted or
plotted.** Registration follows the workflow of §13: the design and its code are committed on
`feature/PROC-1_procurement-bunching`; the study is described as pre-registered only if Bára pushes the branch and a
signed tag `procurement-bunching-design` to the public remote before the data step (editorial standard §6).
Otherwise the self-timestamped wording of §13 applies. Deviations after registration go, dated, into
`docs/changelogs/procurement-bunching.html`.

## 0. What has already been seen (exposure)

Everything below was seen by the drafting session (Claude, 12 October 2026) while writing this design. To the
drafting session's knowledge, Bára has not analysed these data; she wrote the proposal (`study16`, Czech, in the
session's scratchpad) from dated news articles, and its facts were treated as unverified and checked in §2–§3.

| # | What | How much was read | Outcome information |
|---|---|---|---|
| E1 | Proposal text `study16.txt` | In full | None (no data; prior expectation below) |
| E2 | Legal texts: zákon 69/2025 Sb., zákon 134/2016 Sb. (§ 6, 16, 18–27, 31, 52–53, 219), NV 172/2016 Sb. and its five amendments, zákon 340/2015 Sb. (§ 3, 5, 7), NV 425/2016 Sb.; MMR and CRR guidance; MMR model directive for small-scale contracts (December 2025); a Liberec Region news item (4 June 2025) | The cited provisions | None |
| E3 | `data.smlouvy.gov.cz` index of dumps | Whole index (file names, SHA-1, sizes, generation times) | None |
| E4 | Daily dumps `dump_2017_01_01.xml` (25 records) and `dump_2024_01_01.xml` (145 records) | Element paths and their counts only, by `scratchpad/scripts/xml_paths.py`; no text value printed | None |
| E5 | Monthly dumps `dump_2024_05.xml` (91 552 records) and `dump_2025_10.xml` (100 554 records) | `tools/procurement/structure.py`: element paths, field presence, currencies, year concluded, publication lag, distinct publishers, and record counts in five value bands far from every threshold (60–450 thousand and 15–45 million Kč). Records valued in 0.45–14 million Kč were parsed but not counted, tabulated or printed. Output: `docs/research/procurement-bunching-structure.json` | Counts in the far bands only; no information about the analysis range 0.5–13.5 million Kč |
| E6 | Synthetic data | Tests and power simulations of `tools/procurement/` | None |

Not seen: any value, count, share or plot of contracts between 0.45 and 14 million Kč; any contract subject
(`predmet`), party or authority name; any data from Hlídač státu, ISVZ, NEN or profiles of contracting
authorities.

**Prior expectation (from the proposal).** If authorities respond to the threshold, the bunching of contract values
just below 2 million Kč (supplies and services) and 6 million Kč (works) should move to 3 and 9 million Kč after 3
April 2025; if it is only a preference for round numbers, it should stay where it was. The published literature
(Palguta and Pertold 2017 [R1]) found bunching of Czech procurement values below the thresholds when they were
introduced, so the drafting session also expects some bunching at the old limits before the change.

**Requests.** All scripted requests (curl, Python) used the User-Agent `bsandova.com research`, no e-mail address
and pauses of 1–5 s between files. Legal pages and search results were also read through the session's web-fetch
and web-search tools, whose User-Agent the session does not set. No browser was opened.

## 1. Question and contribution

Czech contracting authorities may award a *small-scale public contract* (veřejná zakázka malého rozsahu, ZMR)
without a procurement procedure, subject only to the principles of § 6 ZZVZ (§ 31). Above the limit they must run a
procedure, with publication and deadlines. An authority that prefers discretion therefore has a reason to keep a
contract at or below the limit, by setting the estimated value low, by splitting a purchase into parts, by
negotiating the price down to the limit, or by narrowing the scope. Bunching designs [R2–R4] read such responses
from excess mass in the distribution just below a threshold, and Palguta and Pertold [R1] applied one to Czech
procurement when the thresholds were introduced; Coviello, Guglielmo and Spagnolo [R5], Szucs [R6] and Baránek and
Titl [R7] study what discretion below thresholds does to prices, competition and favoritism.

A single threshold leaves one ambiguity: the limits were round numbers (2 and 6 million Kč), and contract values
bunch at round numbers anyway. On 3 April 2025 the limits rose to 3 and 9 million Kč (§2). The question is whether
the excess mass **moved with the limit**: appeared below the new limits and shrank below the old ones, beyond what
happened at round millions that carry no legal meaning. The contribution is the use of the move to separate a
response to the threshold from round-number focality, with data on contracts below the threshold, which the
procurement notice data used in earlier work mostly do not cover.

## 2. The legal change, verified

### 2.1 The amendment

| Item | Verified fact | Primary source |
|---|---|---|
| Amending act | Zákon č. 69/2025 Sb., of 27 February 2025, amending zákon 215/2004 Sb. "a další související zákony"; part three, Čl. III, amends zákon 134/2016 Sb. (ZZVZ) | [L1] |
| Promulgation | Částka 69/2025, 19 March 2025 | [L1], [L4] |
| Effect | Čl. VI: "nabývá účinnosti patnáctým dnem po dni jeho vyhlášení" → **3 April 2025** | [L1] |
| § 27(a) supplies and services | "částka „2000000 Kč“ nahrazuje částkou „3000000 Kč“" | [L1] |
| § 27(b) works | "částka „6000000 Kč“ nahrazuje částkou „9000000 Kč“" | [L1] |
| Definition | § 27: a ZMR is a contract whose estimated value "je rovna nebo nižší" than the limit, so a value **equal to** the limit is a ZMR | [L2] |
| VAT | § 16(1): "Do předpokládané hodnoty veřejné zakázky se nezahrnuje daň z přidané hodnoty" — all limits are **without VAT** | [L2] |
| Transitional provisions | None in Čl. III | [L1], [L4], [L5] |
| Same act, same date | § 219(1)(a): contracts are published on the authority's profile above 1 000 000 Kč without VAT (was 500 000 Kč); a contract published in the Registr smluv is exempt (§ 219(1)(d)) | [L1], [L2] |

**Which date decides.** The MMR announcement of 20 March 2025 [L4], quoted by the CRR [L5], reads § 16(5) and
§ 16(6), second sentence, as follows: for a ZMR not awarded in a procedure, the estimated value is set at the
moment of award and is the price in the contract, so the new limits apply to small-scale contracts **concluded on or
after 3 April 2025**. A procedure started before that date under the old limit is completed under the ZZVZ. The
design dates contracts by their conclusion date (§4.1).

### 2.2 Other thresholds in or near the analysis range

| Threshold | Value (Kč, without VAT) | In force | Source | Treatment |
|---|---|---|---|---|
| EU threshold, supplies and services, central authorities (§ 4(1)(a)–(c) ZZVZ) | 3 686 000 (Oct 2016–2017); 3 873 000 (2018–19); 3 568 000 (2020–21); 3 653 000 (2022–23); 3 494 000 (2024–25); 3 491 000 (2026–) | NV 172/2016 § 2(1)(a), § 3(1)(a), amended by NV 471/2017, 335/2019, 475/2021, 435/2023, 541/2025 | [L3] | Nuisance window (§5.3) |
| EU threshold, supplies and services, regions and municipalities (§ 4(1)(d)–(e)) | 5 706 000; 5 944 000; 5 494 000; 5 610 000; 5 401 000; 5 386 000 (same periods) | NV 172/2016 § 2(1)(b), § 3(1)(b) | [L3] | Nuisance window |
| Part of a contract outside the regime of the whole (§ 18(3) ZZVZ), supplies and services | 2 184 000; 2 151 000; 2 054 000; 2 087 000; 1 955 000; 1 995 000 (same periods) | NV 172/2016 § 5(a) | [L3] | Nuisance window (lies at the old limit) |
| Same, works | 27 305 000 … 24 938 000 | § 5(b) | [L3] | Outside the range |
| EU threshold, works | 134 764 000 – 149 224 000 | § 4 | [L3] | Outside the range |
| Simplified below-threshold procedure not allowed for works above | 50 000 000 | § 52(a) ZZVZ | [L2] | Outside the range |
| Registr smluv: contracts **at or below 50 000 Kč without VAT** are exempt | 50 000 | § 3(2)(h) zákon 340/2015 | [L6] | Below the range; the proposal's "with VAT" is wrong |
| Profile publication (§ 219) | 500 000 → 1 000 000, 3 April 2025 | [L1] | No bite for contracts in the Registr smluv; 1 million is a nuisance window |
| EU-funded projects (MPZ 2021–2027, MMR methodological statement no. 4): direct purchase | 500 000 → 750 000, from 1 May 2025; for recipients that are not contracting authorities 6 000 000 (supplies, services) and 18 000 000 (works) | CRR information, May 2025 | [L5] | 750 000 nuisance window; the 6 million limit for non-authorities is noted under §6.4 |
| Internal rules of authorities | MMR model directive (December 2025): categories with upper bounds 150 000–750 000, 750 000–2 000 000 and 3 000 000 (supplies, services); 600 000–1 500 000, 1 500 000–6 000 000 and 9 000 000 (works), set by each municipality | [L7] | 2 and 6 million can remain internal category bounds after the change; read in §8.2 |
| Internal rules, a large authority | Liberec Region amended its 2021 directive to the new limits; news item dated 4 June 2025, two months after the change | [L8] | Evidence of adjustment lag; §10 robustness "post from 1 October 2025" |

The proposal's history of EU limits (3 686 000; 3 873 000; 3 568 000; 3 653 000; 3 494 000; 3 491 000) matches the
central-authority supplies and services thresholds of the six versions of NV 172/2016.

## 3. Data

### 3.1 Sources considered

| Source | What it records | Covers ZMR? | Access | Verdict |
|---|---|---|---|---|
| **Registr smluv**, monthly XML dumps (`data.smlouvy.gov.cz`) | Every contract of an obliged public entity above 50 000 Kč without VAT: conclusion date, publication time, price without VAT (`hodnotaBezDph`) and/or with VAT (`hodnotaVcetneDph`), "price not stated", foreign currency, link to an earlier record, version id and validity flag, publisher IČO, parties, subject (free text). Since late 2025 a rarely filled `evidencniCisloZakazky` (167 of 100 554 records in October 2025) | Yes, from 50 000 Kč, whether or not a procedure was run | Open; index lists SHA-1 per dump; no `robots.txt` (404); metadata were mandatory open data under NV 425/2016 item 22 (repealed 26 August 2021 by NV 304/2021) | **Primary** |
| ISVZ / Věstník veřejných zakázek open data | Notices of procedures (estimated value, type of contract, procedure); from February 2024 the "new open data" of the Registr veřejných zakázek, fed by VVZ, NEN, Tender arena and Tendermarket | Only ZMR that an authority chooses to record in an e-tool | `isvz.nipez.cz/robots.txt` disallows all paths to all agents | Not used without Bára's decision (§14) |
| NEN | Procedures in the state's e-tool, including some ZMR | Partly | `robots.txt` allows most paths, `Crawl-delay: 10` (the proposal's "blocks" is wrong) | Not used: scraping per contract is slow and covers a self-selected subset |
| Hlídač státu API | Re-processed Registr smluv records with a contract classification, plus procurement notices | As the Registr smluv | API token needed (none present in the environment; never printed if added); data under CC BY 3.0 CZ [D2] | Optional secondary source for the type split (§4.5) |
| Profiles of contracting authorities | Procedures and § 219 contracts above 1 million Kč (500 000 before 3 April 2025) | Few | Hundreds of separate sites | Not used |
| OpenTender (Digiwhist) | Harmonised notices | No | Cloudflare challenge; `robots.txt` not readable without a browser | Not used |

### 3.2 Value definition and the measurement mismatch

The threshold applies to the **estimated value without VAT** (§ 16). The Registr smluv records the **contract
price**, with or without VAT, as the publisher enters it. Three cases follow.

1. **ZMR awarded without a procedure.** By § 16(5) and § 16(6), second sentence, as read by MMR [L4], the estimated
   value of such a contract is the price in the contract at the moment of award. Here the recorded price without VAT
   is the legally decisive quantity, and the mismatch vanishes except for reporting errors.
2. **Contracts awarded in a procedure** (above the limit, or below it by choice). The estimated value was set when
   the procedure started; the contract price is the winning bid, usually lower. These contracts enter the price
   distribution shifted downwards from their estimates. Because the regime itself changes at the threshold, the shift
   produces a **step** in the price density at the limit (estimates just above the limit, discounted by competition,
   land just below it) even if no authority manipulates anything. §6.4 and the shape diagnostic of §7.3 deal with
   this.
3. **Reporting.** About 69 % of records carry `hodnotaBezDph` and 51 % `hodnotaVcetneDph` (E5, both months); some
   publishers type the VAT-inclusive price into the field without VAT.

**Rule.** The primary value is `hodnotaBezDph`. Records with only a VAT-inclusive value are excluded from the
primary analysis and added, divided by 1.21, in robustness R-VAT. A VAT-inclusive price entered as without VAT puts a
contract at 1.21 times its true value, so a limit's "VAT image" (2.42, 3.63, 7.26, 10.89 million) can carry a
spurious spike; the images are excluded from the fit in a robustness row, and 11 million, which sits at the image of
the 9 million limit, is not used as a control.

**What it does to the estimand.** The estimand is excess mass in the distribution of **recorded contract prices
without VAT**, not of estimated values. For direct awards the two coincide by law; for contracts from procedures the
design measures where their prices fall, which is a consequence of the threshold too (§6.4). The study can therefore
say whether recorded prices respond to the limit, not whether authorities misstated estimated values.

### 3.3 Collection and freeze

- **Dumps.** Monthly dumps by publication month, January 2020 to September 2026 (81 files, about 130 MB each, about
  10 GB). A contract concluded on 30 June 2026, the last day of the post period, must be published within three
  months or it is cancelled from the start (§ 7 zákon 340/2015), so September 2026 closes the window; in the two
  months read, about 93 % of records were published within 30 days of conclusion and about 2 % after more than 91 days.
  Every month must be marked complete in the index (`dokoncenyMesic`).
- **Manifest.** `tools/procurement/collect.py` downloads each file once, records URL, size, the index entry seen
  (SHA-1, generation time), the file's own SHA-1 and SHA-256 and the download time in
  `tools/data/procurement/manifest.json`. The index shows dumps regenerated long after their month (2017 dumps
  generated in 2026), so the hashes identify the snapshot used, not the month.
- **Politeness.** One file at a time, 5 s between files, User-Agent `bsandova.com research`, no e-mail address, no
  browser. Parsing runs under `nice -n 20` with two threads (`OMP_NUM_THREADS=2`).
- **Licence.** The site states no licence; the metadata are public-sector open data. The article will name the
  source, the snapshot dates and the hash list. Hlídač státu data, if used, are CC BY 3.0 CZ and cited as such.

## 4. Sample and screening

Fixed now; `tools/procurement/prepare.py` reports the count left after each step (over all values, not by value),
in `docs/research/procurement-bunching-screen.json`.

1. **Periods (by conclusion date, `datumUzavreni`).** *Pre:* 1 January 2020 – 31 December 2024. *Post:* 3 April 2025 –
   30 June 2026. Contracts concluded 1 January – 2 April 2025 are dropped: the act was adopted on 27 February and
   promulgated on 19 March, so contracts priced between the old and new limits could have been delayed into April
   (anticipation). Years before 2020 are left out because the EU sub-central thresholds of 2016–2019 (5.706 and 5.944
   million) sit inside the 6 million window, and because the register's first years had weaker reporting.
2. **Versions.** Records with `platnyZaznam = 1`; for each `idSmlouvy`, the record with the highest `idVerze`.
3. **Amendments.** Records with `navazanyZaznam` (a link to an earlier record) are dropped.
4. **Price.** CZK (no `ciziMena`), no `cenaNeuvedena`, `hodnotaBezDph` > 0.
5. **Not a purchase.** Records whose subject contains any of the registered stems in `prepare.py` (`NOT_PURCHASE`:
   grants and subsidies, gifts, leases and loans, easements, future and cooperation agreements, sales, exchanges,
   public-law contracts, employment agreements, "dodatek") are dropped. The list is applied as written, without
   reading any subject; its hit count is reported.
6. **Range.** Values in (500 000, 13 500 000] Kč.
7. **Type (secondary only).** A works flag from registered subject stems (`WORKS` in `prepare.py`). Before the type
   split is read, 300 records drawn at random from values outside 0.45–14 million Kč are labelled by hand
   (supplies, services, works, not a purchase) and the flag's accuracy is reported. If Bára adds a Hlídač státu token,
   its classification replaces the stems in a second robustness row.

The primary analysis **pools all contract types**. Each of the four limits binds one type only, so the other type
dilutes the excess at that location by its share, biasing towards zero but creating no excess of its own; the
pooled analysis needs no classifier.

## 5. Histogram and counterfactual

### 5.1 Bins

Bin width 10 000 Kč over (500 000, 13 500 000], 1 300 bins. Bin *j* holds (500 000 + 10 000·j, 500 000 + 10 000·(j+1)],
closed on the right, so a contract priced exactly at a limit falls in the bin that ends at it, i.e. below the limit,
as § 27 requires.

### 5.2 Locations and windows

Every location window is the 5 % band below the location, (0.95 L, L]; the missing-mass window above each limit is
(T, 1.05 T].

| Role | Locations (million Kč) |
|---|---|
| Old limits | 2 (supplies and services), 6 (works) |
| New limits | 3 (supplies and services), 9 (works) |
| Controls (round millions with no legal meaning in 2020–2026) | 4, 5, 7, 8, 10, 12, 13 |

1 and 11 million are not controls (1 million is the § 219 limit after 3 April 2025; 11 million holds the VAT image of
9 million). Every whole million in the range lies in a location or nuisance window.

### 5.3 Nuisance windows (excluded from the fit, not analysed)

The 5 % band below each of: the EU central thresholds of 2020–2026 (3.568, 3.653, 3.494, 3.491 million), the EU
sub-central thresholds (5.494, 5.610, 5.401, 5.386 million), the § 18(3) part amounts (2.054, 2.087, 1.955, 1.995
million), 750 000, 1 million and 11 million. Windows are snapped outwards to bin edges.

### 5.4 Counterfactual

For each period separately, a Poisson regression of bin counts on a degree-7 Legendre polynomial in the log bin
midpoint (scaled to [−1, 1]) and three indicators for bins that contain a multiple of 500 000, of 100 000 (not
500 000), and of 50 000 (not 100 000), fitted on all bins outside the location, missing-mass and nuisance windows.
The fitted counts ĉ, with the sub-million round-number effects included, are the counterfactual for every bin.
Implementation: `tools/procurement/bunching.py` (`excess`, iteratively reweighted least squares, no external GLM
library).

## 6. Estimands and identification

### 6.1 Excess at a location

r(L) = Σ_W (c − ĉ) / Σ_W ĉ over the window W = (0.95 L, L]: the number of contracts in the 5 % band below L beyond
the smooth density and sub-million rounding, as a share of the counterfactual count. r(L) = 0.2 means 20 % more
contracts in the band than expected. m(T), the same quantity above a limit, measures missing mass and is reported
without a label.

r(L) at a single location mixes two things: the response to a limit, if L is one, and the pull of a round million.
The pull is not the same at every location: in the synthetic tests a round million attracts more contracts,
relative to its 5 % band, the lower it lies (a contract rounded to the nearest million comes from a ±500 000 range,
which is wide against a band of 100 000 at 2 million and narrow against one of 650 000 at 13 million). The static
comparison of an old limit with the controls in one period is therefore biased upwards and is reported as
description only.

### 6.2 The move (primary)

The design compares each limit location with itself before and after 3 April 2025, and scales its round-number
component by how the controls changed. With R_C the pooled excess over the control windows (Σ excess / Σ expected
across all seven) and k = R_C(post) / R_C(pre):

- **H1, the excess appears at the new limits (primary):** D_new = ½ Σ_{L ∈ {3 M, 9 M}} [r(L, post) − k·r(L, pre)] > 0.
- **H2, the excess shrinks at the old limits (secondary, own label):** D_old = ½ Σ_{L ∈ {2 M, 6 M}} [k·r(L, pre) − r(L, post)] > 0.

Before the change, 3 and 9 million were round millions only, so k·r(L, pre) is their expected round-number excess
after the change; anything beyond it is a response to the new limit. The ratio form assumes that a change in the
taste for round millions scales the round-number excess by the same factor at every location; in the synthetic test
where rounding triples, the ratio leaves a residual of about 0.1 and an additive adjustment a residual of 0.37.
**Fallback, fixed now:** if the 95 % interval of R_C(pre) does not lie above 0 (no measurable round-million excess,
so k is undefined), the additive form D_new = ½ Σ [r(L, post) − r(L, pre) − (R_C(post) − R_C(pre))] is primary; the
choice is made from R_C(pre) before any D is read and recorded in the results file.

Location-specific D (3 million alone, 9 million alone, and the same for H2) are reported with intervals and without
labels.

### 6.3 Separating the round-number component

Three layers do this, in order of how much weight they carry. (a) The time difference at a fixed location removes
whatever makes 3 or 9 million focal in itself. (b) The control scaling k removes a general change in rounding. (c)
Sub-million rounding (50 000, 100 000, 500 000) is absorbed by the indicators of §5.4. A fourth, registered variant
drops every contract priced at exactly a whole million (to the crown) before the histogram: round-number focality
puts contracts on the million itself, whereas a price set to stay under a limit can be anything up to it (2 995 000,
2 999 999). The variant is a robustness row with the additive adjustment, since without exact millions R_C is close
to 0.

### 6.4 What the move identifies and what it does not

Under the assumptions below, D_new > 0 identifies a **causal response of recorded contract prices to the legal
limit**: the density of prices just under 3 and 9 million rose when, and because, these values became the limits.
It does not identify which behaviour produced it. From values alone the design cannot tell apart:

- an estimated value set or a price negotiated to fit under the limit (manipulation in the sense of [R1]);
- splitting one purchase into parts below the limit (it moves mass far below the limit, mostly outside the window,
  so most of it is not even counted);
- a legitimate narrowing of scope to use the simpler regime, which the law permits;
- bidders pricing to the authority's budget once it equals the limit;
- the regime step of §3.2: contracts estimated just above a limit go through competition and end up priced below
  it. This step needs no manipulation, and it moves with the limit too. §7.3 separates a spike at the limit from a
  step only descriptively.

The article will call D_new a response to the threshold and will not use "manipulation", "splitting" or
"corruption" for it. Nothing here says whether discretion below the limit raises prices or favours particular
firms.

**Assumptions.** A1, a smooth counterfactual: without the limit, the price density in each 5 % window would follow
the fitted polynomial and sub-million rounding. A2, proportional rounding: the round-million excess at each location
changes by a common factor k between the periods (tested by the placebos of §7.1–§7.2). A3, no other change on 3
April 2025 at these locations: the § 219 profile limit moved from 500 000 to 1 million on the same day (no bite in the
register, 1 million is not used), and from 1 May 2025 EU-funded recipients that are not contracting authorities have
a 6 million direct-purchase limit for supplies and services, which can hold some excess at 6 million (biasing D_old
towards zero, not D_new). A4, stable coverage: the Registr smluv act was last amended with effect from 1 January
2025 (consolidated version 8), so the population of publishers does not change at 3 April 2025. A5, stable
reporting: the share of VAT-inclusive prices typed as without VAT does not change around the limits differently
across periods.

## 7. Placebos and checks (reported; only §7.1 can change a label)

1. **Control placebo (validity gate).** Each control in turn is treated as a "new limit", with k computed from the
   other six: placebo = mean of r(C, post) − k₋C·r(C, pre). If its 95 % interval excludes 0 **and** its point
   estimate exceeds 0.15 in absolute value, the rounding adjustment has failed and H1 and H2 are labelled
   inconclusive whatever their intervals; the article says so.
2. **Placebo date.** The pre period alone, split at 1 January 2023 (2020–2022 against 2023–2024): D_new and D_old
   should be close to 0.
3. **Shape.** For each limit and period, the share of the window's excess in its top 1 % ((0.99 T, T]) and r for
   windows of 2.5 %, 5 % and 10 %. A spike at the limit concentrates there and its r falls as the window widens; a
   regime step spreads evenly and its r stays flat. Descriptive only.
4. **Missing mass** m(T) above each limit, before and after.
5. **Type cross-check (secondary, needs §4.7).** Within the works flag, 3 million should show no change (and within
   supplies and services, 9 million); a change there points to misclassification or to a common shock.

## 8. Reading rules

### 8.1 Labels for H1 and H2

Applied in this order, each hypothesis on its own:

1. **Underpowered** if the minimum detectable effect computed at the data step (§9.3, from the real counts, before
   any r is computed) exceeds 0.30.
2. **Inconclusive** if the validity gate of §7.1 fails.
3. **Supported** if the 95 % cluster-bootstrap interval of D lies wholly above 0.
4. **Not supported** if the 90 % interval lies wholly within (−0.15, +0.15): any response is smaller than 15 % of the
   counterfactual count in the band.
5. **Inconclusive** otherwise, including an interval wholly below 0, which is reported as such.

The margin 0.15 is the smallest excess the author considers worth an article (one contract in seven in the band
attributable to the limit); the underpowered bound 0.30 is twice it.

### 8.2 Reading H1 and H2 together (pre-written sentences, no further label)

- H1 supported, H2 supported: "The excess below the limit moved with it: it appeared below the new limits and shrank
  below the old ones."
- H1 supported, H2 not supported or inconclusive: "An excess appeared below the new limits; below the old limits it
  did not measurably shrink, which internal rules that keep 2 and 6 million as category bounds (§2.2), the § 18(3)
  part amount near 2 million and slow adjustment could each explain."
- H1 not supported: "No excess appeared below the new limits beyond what round millions carry; the data do not show a
  response of contract prices to the change."
- H1 inconclusive or underpowered: the label and its reason, and no reading of H2 as evidence of a response.

The headline is H1. H2 never supports H1, and location-specific and type-specific estimates carry no labels.

### 8.3 Several thresholds

Four limit locations enter two pooled statistics (H1 over the two new limits, H2 over the two old ones), fixed
before data; the per-location estimates are shown but not labelled, so there is no search over thresholds. The EU
and § 18(3) thresholds are nuisance windows, never tested. There are no tallies across hypotheses.

### 8.4 Inference

Cluster bootstrap by publishing authority (`subjekt/ico`): 999 draws for the primary row, 199 for robustness rows,
percentile intervals. An authority is drawn with all its contracts in both periods, so the covariance between pre and
post is kept. Each draw refits both counterfactuals.

## 9. Power

### 9.1 Calibration away from the thresholds

From the two monthly dumps (E5), record counts with `hodnotaBezDph` in five far bands (60–120, 120–240 and 240–450
thousand; 15–22 and 30–45 million Kč) were averaged and fitted by a power-law density c·v^(−α) (Poisson deviance):
α = 1.67. Interpolated into the analysis range, this gives about 11 360 records a month with a price without VAT,
before screening. No count inside 0.45–14 million was used.

### 9.2 Simulation

`tools/procurement/power.py` draws contracts from the calibrated density, assigns them to 8 000 authorities of
lognormal size (σ = 1.5), rounds 15 % of them up to the next 100 000 and 2 % to the nearest million, runs the
registered estimator 200 times under the null for the spread of D, and checks it against the cluster bootstrap in
three draws. The retained share after screening (§4) is not known before the data step and is taken as 0.6 or 0.35.
MDE = (1.96 + 0.84) × SD, the effect found with 80 % power by the rule "95 % interval above 0".

| Retained share | Contracts pre / post | MDE D_new (simulation SD) | MDE D_new (bootstrap SE) | MDE D_old | MDE, 3 M alone / 9 M alone |
|---|---|---|---|---|---|
| 0.60 | 408 972 / 102 243 | 0.11 | 0.14 | 0.16 | 0.17 / 0.14 |
| 0.35 | 238 567 / 59 641 | 0.16 | 0.24 | 0.21 | 0.23 / 0.21 |

The bootstrap standard errors (0.043–0.054 and 0.060–0.119 in the three checks) are larger than the simulation
spread, so the bootstrap column is the one to plan on. Under both scenarios H1 can reach "supported" for an excess
of about 0.14–0.24 and "not supported" when the true response is close to 0 (it needs a 90 % half-width below 0.15,
i.e. a standard error below about 0.09). The pooled r at 3 million is diluted by works contracts priced there: if a
share s of contracts in that band are supplies and services, the response among them is r/s.

### 9.3 At the data step

After `prepare.py` and before `estimate.py`, `power.py <n_pre> <n_post>` reruns the simulation with the real numbers
of contracts in the range (two totals, no histogram) and writes `data_step_mde`; if the larger of the simulation and
bootstrap MDE exceeds 0.30 for a hypothesis, it is labelled underpowered (§8.1) and its estimate is reported as
description.

## 10. Robustness (reported as a table; none relabels)

| Row | Change |
|---|---|
| Windows | 2.5 % and 10 % below each location |
| Polynomial | degree 5 and 9 |
| Adjustment | none (k = 1); additive |
| Exact millions | contracts at exactly a whole million dropped (additive adjustment) |
| VAT images | the 5 % bands below 2.42, 3.63, 7.26 and 10.89 million excluded from the fit |
| R-VAT | records with only a VAT-inclusive price added, divided by 1.21 |
| Adjustment lag | post period from 1 October 2025 |
| Pandemic years | pre period 2022–2024 only |
| Concentration | the largest 1 % of authorities by number of contracts dropped |
| Type split | works and supplies/services separately, by the keyword flag (and by Hlídač státu's classification if used) |
| Placebo date | §7.2 |

## 11. Exposure handling during the analysis

The order is fixed: register (§13) → collect all dumps → `prepare.py` (screening counts only) → `power.py` data step
→ `estimate.py` once, with `--quick` allowed only as a crash check whose output is deleted unread → results commit.
No histogram of the analysis range is drawn before the results commit. Any look outside this order is logged in the
change log with its date and what was seen.

## 12. What this will not show (limitations)

- **Mechanism.** §6.4: a response to the limit, not manipulation, splitting, favoritism or prices paid.
- **Estimated values.** The register holds prices. Contracts priced below a limit after a procedure cannot be told
  from direct awards, except through the rarely filled procurement number.
- **Coverage.** The register exempts contracts of municipalities without extended powers and their organisations
  (§ 3(2)(k) zákon 340/2015), i.e. all municipalities except those with extended powers, so small municipalities, a
  large share of small-scale purchasing, are missing. Contracts at or below 50 000 Kč are absent; trade secrets may hide prices
  of some state companies (§ 5(6)).
- **Splitting** mostly places parts far below the limit and escapes the window.
- **Short post period.** Fifteen months, with internal rules adjusting over the first months.
- **Type.** The pooled analysis dilutes each limit by the other type; the type split rests on keywords.
- **Not a purchase.** The keyword exclusion is coarse; grants and sales that survive add round-number noise.
- **Earlier limits.** Limits set under the 2006 act predate the register (in force from July 2016) and are not
  studied.

## 13. Registration workflow

1. **Commit.** This design, `tools/procurement/` (collect, structure, prepare, bunching, synth_contracts, power, estimate,
   tests) and the two JSON files of E5 and §9 are committed on `feature/PROC-1_procurement-bunching` (one-line
   commit message, no AI attribution).
2. **Review.** Bára reads the design and resolves §14; any change is committed before step 3.
3. **Anchor.** Bára pushes the branch and a signed annotated tag on the registration commit:
   `git tag -s procurement-bunching-design <commit> -m "Registered design: procurement bunching"` and
   `git push origin feature/PROC-1_procurement-bunching procurement-bunching-design`. A signed tag pushed to the
   public remote before any outcome is joined is a tamper-evident anchor under §6, and the article may then say
   "pre-registered: signed tag `procurement-bunching-design` (commit `<hash>`), pushed `<date>`".
4. **If the tag is not pushed before the data step,** the only permitted wording is: "registered analysis plan: design
   committed at `<hash>` on `<date>`, before the results commit `<hash>`; commit times are self-reported, and the
   branch was pushed after the analysis." If GitHub's activity log shows the design on the public branch before the
   results, the last clause is replaced by the recorded push times, with the note that a push is not a
   tamper-evident anchor.
5. **Data step** in dated commits (manifest, screening counts, data-step power), then one results commit. Deviations
   go into `docs/changelogs/procurement-bunching.html`.
6. **Disclosure.** §0 is repeated in the article (editorial standard §6, last rule).

## 14. Open decisions for Bára

1. **Anchor.** Push the branch and the signed tag before the data step (pre-registered), or keep the self-timestamped
   wording.
2. **Source.** Registr smluv alone (primary, as designed), or also ISVZ open data, whose `robots.txt` disallows all
   agents: a one-off manual download of the published open-data files would give estimated values and contract types
   for recorded procedures, and is Bára's call. A Hlídač státu token would give a second type classification.
3. **Periods.** Pre 2020–2024 (designed) or longer; post primary from 3 April 2025 (designed, conservative under slow
   adjustment) or from 1 October 2025 (now a robustness row).
4. **Margins.** Equivalence margin 0.15 and underpowered bound 0.30 on the r scale.
5. **H2.** Labelled as designed, or descriptive only, given the reasons in §8.2 why the old excess may persist.
6. **Exclusion list.** The `NOT_PURCHASE` stems of `prepare.py`, which act on text nobody has read.
7. **Download and compute.** About 10 GB of dumps; the full estimate (999 + 13 × 199 bootstrap draws) under
   `nice -n 20` with two threads, its run time measured first on the synthetic smoke run; OK to run once.
8. **Slug** `procurement-bunching` and series placement.

## 15. Code and reproduction

- `tools/procurement/collect.py` — dumps and manifest. `structure.py` — the E5 structure pass. `prepare.py` —
  screening (§4). `bunching.py` — histogram, counterfactual, r, D, placebo, bootstrap, labels. `synth_contracts.py` — made-up
  contracts with known rounding and bunching. `power.py` — §9. `estimate.py` — §6–§10. `test_procurement.py` — ten
  tests on synthetic data: a value equal to a limit falls below it; every whole million is in a window; rounding
  alone gives no move; a moved limit is found at both ends with missing mass above; more rounding after the change is
  differenced out by the ratio and not by the additive form; a planted excess is recovered; bootstrap and label on a
  clear move; label order; the control placebo is null; dropping exact millions removes pure rounding but not the
  move.
- Tests: `uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pytest==9.1.1 pytest -q tools/procurement`.

## References

- [R1] Palguta, J., Pertold, F. (2017). Manipulation of Procurement Contracts: Evidence from the Introduction of
  Discretionary Thresholds. *American Economic Journal: Economic Policy* 9(2), 293–315.
  https://doi.org/10.1257/pol.20150511. Accessed 12 October 2026.
- [R2] Kleven, H. J. (2016). Bunching. *Annual Review of Economics* 8, 435–464.
  https://doi.org/10.1146/annurev-economics-080315-015234. Accessed 12 October 2026.
- [R3] Chetty, R., Friedman, J. N., Olsen, T., Pistaferri, L. (2011). Adjustment Costs, Firm Responses, and Micro vs.
  Macro Labor Supply Elasticities: Evidence from Danish Tax Records. *Quarterly Journal of Economics* 126(2), 749–804.
  https://doi.org/10.1093/qje/qjr013. Accessed 12 October 2026.
- [R4] Kleven, H. J., Waseem, M. (2013). Using Notches to Uncover Optimization Frictions and Structural Elasticities:
  Theory and Evidence from Pakistan. *Quarterly Journal of Economics* 128(2), 669–723.
  https://doi.org/10.1093/qje/qjt004. Accessed 12 October 2026.
- [R5] Coviello, D., Guglielmo, A., Spagnolo, G. (2018). The Effect of Discretion on Procurement Performance.
  *Management Science* 64(2), 715–738. https://doi.org/10.1287/mnsc.2016.2628. Accessed 12 October 2026.
- [R6] Szucs, F. (2024). Discretion and Favoritism in Public Procurement. *Journal of the European Economic
  Association* 22(1), 117–160. https://doi.org/10.1093/jeea/jvad017. Accessed 12 October 2026. (The proposal's title
  "Discretion and corruption" is wrong.)
- [R7] Baránek, B., Titl, V. (2024). The Cost of Favoritism in Public Procurement. *Journal of Law and Economics*
  67(2), 445–477. https://doi.org/10.1086/727793. Accessed 12 October 2026. (The proposal's "Procurement in the Czech
  Republic" does not exist under that title.)
- [L1] Zákon č. 69/2025 Sb. https://www.zakonyprolidi.cz/cs/2025-69 (e-Sbírka: https://e-sbirka.gov.cz/sb/2025/69,
  a script-rendered page not readable without a browser). Accessed 12 October 2026.
- [L2] Zákon č. 134/2016 Sb., o zadávání veřejných zakázek, consolidated text. https://www.zakonyprolidi.cz/cs/2016-134.
  Accessed 12 October 2026.
- [L3] Nařízení vlády č. 172/2016 Sb. and amendments 471/2017, 335/2019, 475/2021, 435/2023 and 541/2025 Sb.
  https://www.zakonyprolidi.cz/cs/2016-172 (version history), https://www.zakonyprolidi.cz/cs/2017-471,
  https://www.zakonyprolidi.cz/cs/2019-335, https://www.zakonyprolidi.cz/cs/2021-475,
  https://www.zakonyprolidi.cz/cs/2023-435, https://www.zakonyprolidi.cz/cs/2025-541. Accessed 12 October 2026.
- [L4] Ministerstvo pro místní rozvoj (20 March 2025). Ke zvýšení limitů pro veřejné zakázky malého rozsahu dojde od
  3. dubna 2025. Portál o veřejných zakázkách.
  https://portal-vz.cz/info-forum-vzdelavani/aktuality/ke-zvyseni-limitu-pro-verejne-zakazky-maleho-rozsahu-dojde-od-3-dubna-2025/.
  Accessed 12 October 2026.
- [L5] Centrum pro regionální rozvoj ČR (May 2025). Informace Centra ke zvýšení limitů pro VZMR od 3. 4. 2025 a
  informace ke zvýšení limitu pro přímý nákup od 1. 5. 2025.
  https://crr.gov.cz/wp-content/uploads/2025/05/Informace-Centra-ke-zvyseni-limitu-VZMR-po-novele-3.-4.-2025-a-zvyseni-limitu-pro-primy-nakup_FINAL.pdf.
  Accessed 12 October 2026.
- [L6] Zákon č. 340/2015 Sb., o registru smluv, consolidated version 8 (from 1 January 2025).
  https://www.zakonyprolidi.cz/cs/2015-340. Accessed 12 October 2026. Nařízení vlády č. 425/2016 Sb., item 22,
  https://www.zakonyprolidi.cz/cs/2016-425. Accessed 12 October 2026.
- [L7] Ministerstvo pro místní rozvoj (December 2025). Vzorová vnitřní směrnice obce pro zadávání veřejných zakázek
  malého rozsahu, verze 1.0.
  https://portal-vz.cz/wp-content/uploads/2025/12/Vzorov%C3%A1-vnit%C5%99n%C3%AD-sm%C4%9Brnice-VZMR_verze-1.0-prosinec-2025_final.pdf.
  Accessed 12 October 2026.
- [L8] Liberecký kraj (4 June 2025). News item on amendment no. 2 of Směrnice Rady Libereckého kraje č. 1/2021.
  https://www.kraj-lbc.cz/aktuality/case:detailPdf/itemId:581150/cgId:15623. Accessed 12 October 2026.
- [D1] Digitální a informační agentura. Registr smluv, open data dumps. https://data.smlouvy.gov.cz/ (index;
  snapshots and hashes in `tools/data/procurement/manifest.json`). Accessed 12 October 2026.
- [D2] Hlídač státu. Licence. https://www.hlidacstatu.cz/texty/licence/ (CC BY 3.0 CZ). Accessed 12 October 2026.

## Changes after registration

None yet.
