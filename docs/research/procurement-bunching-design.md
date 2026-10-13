# Just under the limit: Czech public contracts and the small-scale procurement threshold — research design

**Status: draft analysis plan, revised 12 October 2026 after two independent review rounds (see the end of the file). No contract
value in the analysis range has been read, counted or plotted.** Registration follows the workflow of §14. The design
and its code are committed on `feature/PROC-1_procurement-bunching`. The study is described as pre-registered only if
Bára pushes the branch and a signed tag `procurement-bunching-design` to the public remote before the data step
(editorial standard §6); otherwise the self-timestamped wording of §14 applies. Deviations after registration go,
dated, into `docs/changelogs/procurement-thresholds.html`. The article's slug is `texts/procurement-thresholds`
(decided 12 October 2026). No tooling ties design or code file names to a slug (`check_standard.py` ties only the
article and its change log), so the design, the code and the data files keep the name `procurement-bunching`, and so
does the registration tag.

## 0. What has already been seen (exposure)

Everything below was seen by the drafting session (Claude, 12 October 2026) while writing and revising this design.
To the drafting session's knowledge, Bára has not analysed these data. She wrote the proposal (`study16`, Czech, in
the session's scratchpad) from dated news articles, and its facts were treated as unverified and checked in §2–§3.

### 0.1 Data

| # | What | How much was read | Outcome information |
|---|---|---|---|
| E1 | Proposal text `study16.txt` | In full | None (no data; prior expectation in §0.4) |
| E2 | Legal texts and guidance (§2, list in §0.2) | The cited provisions | None |
| E3 | `data.smlouvy.gov.cz` index of dumps | Whole index (file names, SHA-1, sizes, generation times) | None |
| E4 | Daily dumps `dump_2017_01_01.xml` (25 records), `dump_2023_01_01.xml` (empty) and `dump_2024_01_01.xml` (145 records) | Element paths and their counts only (a scratchpad script equivalent to the path pass of `structure.py`); no text value printed | None |
| E5 | Monthly dumps `dump_2024_05.xml` (91 552 records) and `dump_2025_10.xml` (100 554 records), two passes of `tools/procurement/structure.py` (the second after the review) | Element paths, field presence, currencies, year concluded, publication lag, distinct publishers, presence of each price field by design period over all values, subject-stem hits over all records. Every count that conditions on value uses only records whose price without VAT and whose VAT-inclusive price / 1.21 both lie outside BLIND = 0.45–14 million Kč: counts in five far bands, presence of the price without VAT by band of the VAT-inclusive price, equal with- and without-VAT values, content-key duplicates, stem and flag hits. Output: `docs/research/procurement-bunching-structure.json` | No count, share or statistic conditioned on a value inside BLIND |
| E5′ | The same two dumps: stems | The stem lists of `rules.py` were changed after the first structure pass (`dodatek` → `dodatk`; frameworks, call-offs and periodic prices added) and before the second, so the stems were not frozen before their hit counts were seen. The hit counts are over all records or outside BLIND only | None about the analysis range |
| E6 | Synthetic data | Tests, power simulations and two smoke runs of `estimate.py` | None |

Not seen: any value, count, share or plot of contracts priced between 0.45 and 14 million Kč; any contract subject
text, party or authority name (subjects entered only as stem counts); any data from Hlídač státu, ISVZ, NEN or
authority profiles.

### 0.2 Web searches and fetches (all 12 October 2026)

None of the pages or search results opened reported counts or distributions of Czech contract values after 3 April
2025. Search results were seen as titles, URLs and the search tool's summary; the summaries contained legal facts
only.

| Kind | Query or URL | What was read |
|---|---|---|
| Search | novela zákona 134/2016 … 3 000 000 9 000 000 účinnost 2025 | Titles (MZe, MPSV, DAUC, ANAG, IVB, Právní prostor, epravo, CRR); summary of the limits |
| Search | MMR portal-vz.cz novela ZZVZ 69/2025 … | Titles (CRR, IROP monitoring PDFs, Právní prostor, slov-lex, RVOZP minutes); summary of the limits |
| Search | "Ke zvýšení limitů pro veřejné zakázky malého rozsahu dojde od 3. dubna 2025" | Titles (CRR, Právní prostor, MPSV, ARWS, Liberec Region, Advokátní deník) |
| Search | portal-vz.cz zvýšení limitů … (site-restricted) | Titles of MMR posts and the model directive; summary of the limits |
| Search | Hlídač státu API token licence … | Titles (the R package `hlidacr`, unrelated API terms) |
| Search | registr smluv … hodnotaBezDph … xsd | Titles (testrs.gov.cz documents, unrelated XSDs); summary of field names |
| Search | Registr smluv otevřená data … podmínky užití | Titles (epravo, opendata.gov.cz) |
| Search | ISVZ otevřená data … VZMR rozsah | Titles, including an MMR annual procurement report for 2018 and an MMR document of 14 March 2026, neither opened; summary of the ISVZ open-data sections |
| Search | hlavní město Praha směrnice … VZMR limity 2025 | Titles (Liberec and Plzeň regions, CRR, Právní prostor) |
| Search (review) | "navazanyZaznam" registr smluv | No relevant result |
| Fetch | zakonyprolidi.cz: 2025-69, 2016-134, 2016-172 (versions and history), 2017-471, 2019-335, 2021-475, 2023-435, 2025-541, 2015-340, 2016-425 (and its relations page) | The cited provisions |
| Fetch | e-sbirka.gov.cz/sb/2025/69 | An empty application shell (the page needs a browser) |
| Fetch | portal-vz.cz MMR post of 20 March 2025; MMR model directive (December 2025) | Full text |
| Fetch | crr.gov.cz information of May 2025 | Full text (3 pages) |
| Fetch | kraj-lbc.cz news item of 4 June 2025 | Lines with amounts and dates |
| Fetch | hlidacstatu.cz/api (401), hlidacstatu.cz/texty/licence | Licence text |
| Fetch | aeaweb.org abstract of [R1] (twice) | The abstract |
| Fetch | api.crossref.org, 11 bibliographic queries | Titles, journals, volumes, DOIs |
| Fetch (review) | smlouvy.gov.cz home, `/stranka/otevrena-data`, `/stranka/metodika`, `/stranka/popis-aplikacniho-rozhrani-isrs`; `xsd-1-7-0.zip`; testrs.gov.cz `ISRS_aplikacni_rozhrani.pdf` | Page text, the XSD field documentation, the interface description |
| Fetch | `robots.txt` of zakonyprolidi.cz, e-sbirka.gov.cz, data.smlouvy.gov.cz, smlouvy.gov.cz, isvz.nipez.cz, hlidacstatu.cz (www; the API host answered 429), nen.nipez.cz, opentender.eu, vvz.nipez.cz, portal-vz.cz | The rules |

All scripted requests (curl, Python) used the User-Agent `bsandova.com research`, no e-mail address and pauses of
1–5 s between files. The web-fetch and web-search tools set their own User-Agent. No browser was opened.

### 0.3 Earlier work in this repository

`git grep` for Registr smluv, smlouvy.gov.cz and Hlídač státu finds one link to a single contract on smlouvy.gov.cz,
used in `docs/research/prague-districts-alignment.csv` as a source for a councillor's party affiliation. No contract
value has been analysed on this site before.

### 0.4 Prior knowledge and expectation

The drafting session knew before this work of the bunching literature [R2–R4], of Palguta and Pertold [R1] (bunching
of Czech procurement values below discretionary thresholds when they were introduced, and more frequent awards of
such contracts to firms with concealed ownership), and of [R5–R7]. It knows of no analysis of the April 2025 change
and cannot rule out that its training data contained commentary on it. The proposal expects the bunching below 2 and
6 million Kč to move to 3 and 9 million if authorities respond to the limit, and to stay put if it is only a taste for
round numbers; the drafting session also expects some bunching at the old limits before the change.

## 1. Question and contribution

Czech contracting authorities may award a *small-scale public contract* (veřejná zakázka malého rozsahu, ZMR)
without a procurement procedure, subject only to the principles of § 6 ZZVZ (§ 31). Above the limit they must run a
procedure, with publication and deadlines. An authority that prefers discretion therefore has a reason to keep a
contract at or below the limit: by setting the estimated value low, by splitting a purchase into parts, by
negotiating the price down to the limit, or by narrowing the scope. Bunching designs [R2–R4] read such responses
from excess mass in the distribution just below a threshold, and Palguta and Pertold [R1] applied one to Czech
procurement; Coviello, Guglielmo and Spagnolo [R5], Szucs [R6] and Baránek and Titl [R7] study what discretion below
thresholds does to prices, competition and favoritism.

A single threshold leaves one ambiguity: the limits were round numbers (2 and 6 million Kč), and contract values
bunch at round numbers anyway. On 3 April 2025 the limits rose to 3 and 9 million Kč (§2). The question is whether
the excess mass **moved with the limit**: whether it appeared at the new limits and shrank at the old ones, beyond
what happened at round millions that carry no legal meaning. The contribution is the use of the move to separate a
response to the limit from round-number focality, in data that cover contracts below the limit.

## 2. The legal change, verified

### 2.1 The amendment

| Item | Verified fact | Source |
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

**Which date decides.** § 16(5) sets the estimated value "k okamžiku zahájení zadávacího řízení, nebo k okamžiku
zadání veřejné zakázky, pokud nebyla zadána v zadávacím řízení", and § 16(6), second sentence, reads: "Nebyla-li
veřejná zakázka zadána v zadávacím řízení, použijí se pro stanovení předpokládané hodnoty cena nebo údaje rozhodné
pro její určení uvedené ve smlouvě na veřejnou zakázku." The MMR announcement of 20 March 2025 [L4], quoted by the CRR
[L5], draws from this that the new limits apply to small-scale contracts **concluded on or after 3 April 2025**, and
that a procedure started under the old limit is completed under the ZZVZ. The conclusion-date rule is MMR guidance, an
interpretation of § 16, not a provision of the act; the design dates contracts by conclusion date (§4.1) and leaves a
transition quarter out of the primary analysis.

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
| EU-funded projects (MPZ 2021–2027, MMR methodological statement no. 4): direct purchase | 500 000 → 750 000 from 1 May 2025; for recipients that are not contracting authorities 6 000 000 (supplies, services) and 18 000 000 (works) | CRR information, May 2025 | [L5] | 750 000 nuisance window; the 6 million limit is noted under §6.5 |
| Internal rules | MMR model directive (December 2025): category bounds of 150 000–750 000, 750 000–2 000 000 and 3 000 000 (supplies, services); 600 000–1 500 000, 1 500 000–6 000 000 and 9 000 000 (works), set by each municipality | [L7] | 2 and 6 million can remain internal bounds; read in §8.2 |
| Internal rules, a large authority | Liberec Region amended its 2021 directive to the new limits; news item dated 4 June 2025 | [L8] | Evidence of adjustment lag (§4.1) |

The proposal's history of EU limits (3 686 000 … 3 491 000) matches the central-authority supplies and services
thresholds of the six versions of NV 172/2016.

## 3. Data

### 3.1 Sources considered

| Source | What it records | Covers ZMR? | Access | Verdict |
|---|---|---|---|---|
| **Registr smluv**, monthly XML dumps (`data.smlouvy.gov.cz`) | Every contract of an obliged public entity above 50 000 Kč without VAT: conclusion date, publication time, price without VAT (`hodnotaBezDph`) and/or with VAT (`hodnotaVcetneDph`), price withheld (`cenaNeuvedena`), foreign currency, an optional link to another record (`navazanyZaznam`), version id and validity flag, publisher IČO and payer flag, parties, subject (free text), since late 2025 a rarely filled VVZ procurement number | Yes, from 50 000 Kč, whether or not a procedure was run | Open data [D1]; no `robots.txt` (404); the index lists a hash per dump | **Primary** |
| ISVZ / Věstník veřejných zakázek open data | Notices of procedures (estimated value, type, procedure); from February 2024 the Registr veřejných zakázek, fed by VVZ, NEN, Tender arena and Tendermarket | Only ZMR that an authority records in an e-tool | `isvz.nipez.cz/robots.txt` disallows all paths to all agents | **Not used** (decided 12 October 2026): the site's `robots.txt` excludes automated access |
| NEN | Procedures in the state's e-tool, including some ZMR | Partly | `robots.txt` allows most paths, `Crawl-delay: 10` (the proposal's "blocks" is wrong) | Not used: slow per-contract scraping of a self-selected subset |
| Hlídač státu API | Re-processed Registr smluv records with a contract classification | As the Registr smluv | Token in `HLIDAC_STATU_TOKEN` (environment or the gitignored `.env`), never printed, logged or written; CC BY 3.0 CZ [D2] | **Optional, contract type only** (§4.11); skipped, and said so, without a token |
| Profiles of contracting authorities | Procedures and § 219 contracts | Few | Hundreds of sites | Not used |
| OpenTender (Digiwhist) | Harmonised notices | No | Cloudflare challenge | Not used |

**What the register documents say about the fields** (XSD 1.7.0 and interface description [D3]). `idVerze` is unique
per version; versions are added, never edited. `platnyZaznam` marks whether a version was the last valid one at
export. `navazanyZaznam` is documented only as "volitelná vazba na existující záznam v ISRS dle ID záznamu": an
optional link to another record, not specifically an amendment. In the two months read, 10–12 % of records carry it,
and of those only 72 and 78 have "dodatk" in the subject, so the design keeps linked records and drops them in a
robustness row. `subjekt/platce` (1 = the publisher pays) is filled on 28 % of records and was never 0; no party had
`prijemce = 0`. Dumps are regenerated whenever a contract is modified or withdrawn, for any past period, and a
withdrawn contract disappears from every dump.

**Terms and personal data.** The register's open-data page [D1] declares the metadata open data and warns that they
contain personal data under the GDPR: the recipient becomes a controller and must delete data that are later
withdrawn. The legal basis is Art. 6(1)(f) GDPR (legitimate interest in research on public spending, on data the
state publishes for that purpose), with the safeguards of Art. 89(1): data minimisation and aggregate publication.
The rules are: the raw dumps stay local and outside the repository; `contracts.parquet` keeps only the record id,
the publishing authority's IČO (a public body), the conclusion date, the prices and the screening flags, and never a
party's name or IČO or the subject text; contracts with natural persons are not excluded (that would select on the
counterparty, and the parquet holds nothing about them); only aggregates (bin counts and estimates) are published;
after the results commit the raw dumps are deleted, and the manifest's hashes and the minimised parquet are kept.

### 3.2 Value definition and the measurement mismatch

The limit applies to the **estimated value without VAT** (§ 16). The register holds the **contract price**, with or
without VAT, as the publisher typed it. Three cases follow.

1. **ZMR awarded without a procedure.** By § 16(5)–(6), as read by MMR [L4], the estimated value is the price in the
   contract at award, so the recorded price without VAT is the legally decisive quantity, up to reporting errors.
2. **Contracts awarded in a procedure.** The estimated value was set when the procedure started; the contract price is
   the winning bid, usually lower. Because the regime changes at the limit, contracts estimated just above it and
   discounted by competition land just below it. This produces a **step** in the price density at the limit with no
   deliberate placement. It is a consequence of the limit, but not bunching behaviour, and the article will not call it
   that. It affects estimand b, hardly a (§6.1).
3. **Reporting.** In the two months read, 69.4 % (pre-period contracts in the May 2024 dump) and 69.1 % (post-period
   contracts in the October 2025 dump) of records carry a price without VAT, and 17.9 % and 18.4 % only a
   VAT-inclusive price. Outside BLIND, the share of VAT-inclusive records that also carry a price without VAT rises
   with value, from 62–66 % in the bands below 450 000 Kč to 69–81 % in the bands above 15 million. On 9.4 % and 6.6 % of
   records outside BLIND that carry both, the two numbers are equal.

**Rules.** The primary value is `hodnotaBezDph`. Records with only a VAT-inclusive price are left out and added,
divided by 1.21, in row R-VAT. Records whose two values are equal stay in the primary analysis (most are VAT-exempt
payers or one number typed twice, which is then the price without VAT for a non-payer) and are dropped in a
robustness row. A VAT-inclusive price typed as without VAT puts a contract at 1.21 times its value, so the limits'
"VAT images" (2.42, 3.63, 7.26 and 10.89 million) are excluded from the fit in a robustness row, and 11 million is
not a control. Before estimating, the data step reports the presence of the price without VAT by period over all
values (§4.9); a difference of more than 5 percentage points between periods is reported in the article beside the
results.

**What it does to the estimand.** The estimands are mass in the distribution of **recorded contract prices without
VAT**. For direct awards that is the legal value; for contracts from procedures it is where their prices fall. Because
the presence of the price without VAT rises smoothly with value, the counterfactual polynomial absorbs it; a jump in
presence exactly at a limit, which the design cannot see, would bias both periods alike and cancel in the
difference unless it changed with the limit.

### 3.3 Collection and freeze

- **Dumps.** Monthly dumps by publication month, January 2020 to September 2026 (81 files, about 130 MB each, about
  10 GB). A contract concluded on 30 June 2026, the last day of the post period, must be published within three
  months or is cancelled from the start (§ 7 zákon 340/2015); in the two months read, about 93 % of records were
  published within 30 days of conclusion and about 2 % after more than 91 days. Every month must be marked complete in
  the index.
- **Manifest.** `collect.py` downloads each file once and records URL, size, the index entry seen (SHA-1, generation
  time), the file's own SHA-1 and SHA-256 and the download time in `tools/data/procurement/manifest.json`. Because
  dumps are regenerated, the hashes identify the snapshot used, not the month.
- **Politeness.** One file at a time, 5 s apart, User-Agent `bsandova.com research`, no e-mail address, no browser.
  Parsing and estimation run under `nice -n 20` with two threads.

## 4. Sample and screening

Fixed now; `prepare.py` reports the count after each step in `docs/research/procurement-bunching-screen.json`
(over all values, never by value) and prints only "ok".

1. **Periods, by conclusion date.** *Pre:* 1 January 2020 – 31 December 2024. *Post (primary):* 1 July 2025 – 30 June
   2026. *Transition:* 3 April – 30 June 2025, outside the primary analysis. Contracts concluded 1 January – 2 April
   2025 are dropped (the act was adopted on 27 February and promulgated on 19 March, so contracts priced between the
   limits could have been delayed into April). The post period starts on 1 July because, during the first quarter,
   procedures opened under the old limit were completed under it (MMR [L4]), simplified below-threshold procedures
   typically take one to three months, and internal rules were still being amended (Liberec Region in June [L8]).
   The 3 April and 1 October starts are robustness rows with the reading rules of §10. Years before 2020 are left out
   because the sub-central EU thresholds of 2016–2019 (5.706 and 5.944 million) lie inside the 6 million window.
2. **Versions.** Records with `platnyZaznam = 1`; for each `idSmlouvy`, the highest `idVerze`.
3. **Content-key duplicates.** Among records with a price without VAT **and a non-empty `cisloSmlouvy`**, all but
   the latest record per (sorted IČO of the publisher and all parties, conclusion date, `cisloSmlouvy`, price without
   VAT) are flagged and left out of the primary analysis; without a contract number, two genuine contracts can share
   the rest of the key, so nothing is flagged. The flagged count is reported separately for prices at an exact whole
   million and for other prices, and a robustness row keeps them (in the two months read, outside BLIND and before the
   number condition, 313 and 391 within a single dump, 0.6–0.7 %).
4. **Price.** CZK (no `ciziMena`), no `cenaNeuvedena`, price without VAT > 0.
5. **Not a purchase.** Records whose subject contains a stem of `NOT_PURCHASE` in `rules.py` (grants and subsidies,
   gifts, leases and loans, easements, future and cooperation agreements, sales, exchanges, public-law contracts,
   employment agreements, `dodatk`) are dropped. Outside BLIND the list hits 11.5 % and 8.3 % of priced records in the
   two months read; each stem's hit count over all records and outside BLIND is in the structure file (the largest:
   `dotac`, `příspěvku`, `nájem`, `veřejnoprávní smlouv`, `prodej`).
6. **Kept with a flag (robustness rows).** Call-offs (`objednávk`: 34 % and 40 % of priced records outside BLIND),
   framework agreements (`rámcov`: 1.4 %), periodic prices (`za měsíc`, `měsíčn`, `za rok`, `ročn`, `paušál`,
   `hodinov`: 0.4–0.9 %), linked records, equal with- and without-VAT values, and the publisher flagged as payer.
   Orders are kept because a small purchase is often awarded by an order; a framework's or a periodic price is not the
   price of one award, so they get their own row.
7. **Range.** Prices in (500 000, 13 500 000] Kč.
8. **Publishing authority.** Records without a publisher IČO are dropped and counted; `bunching.estimate` stops
   with an error if any reaches it, instead of pooling them into one cluster.
9. **Presence check.** Before `estimate.py`, the share of records with a price without VAT and with a VAT-inclusive
   price only, by period, over all values.
10. **Hand-labelled check of the stems (secondary).** Before any type split or flag row is read, 300 records drawn at
   random from prices outside BLIND are labelled by hand (supplies, services, works, not a purchase, call-off,
   framework). The report gives the accuracy of the `WORKS` flag and the precision of the `call_off`, `framework` and
   `not_purchase` stems.
11. **Hlídač státu classification (optional, type only).** `hlidac.py` reads the token from `HLIDAC_STATU_TOKEN`
   (environment, else the gitignored `.env`); without it, it prints that the classification was skipped and the
   results record the Hlídač rows as skipped. With it, a random sample of 20 000 primary contracts in the range (drawn
   by id with a fixed seed) is requested one per second from `api.hlidacstatu.cz/api/v2/smlouvy/{id}`, User-Agent
   `bsandova.com research`, no e-mail address, the token only in the `Authorization` header; errors are counted by
   HTTP status only. A contract is works if any classification type names construction (`stav…`). The endpoint and the
   field names are taken from the public API description; on the first response the script checks the field names
   only, and any change is logged before the classification is used. The code was tested against mocked responses
   only; no request to Hlídač státu has been made.

The primary analysis **pools all contract types**. Each limit binds one type, so the other type dilutes the
estimate by its share at that location; the dilution biases towards zero and creates no excess of its own (§9.2).

## 5. Histogram and counterfactual

### 5.1 Two histograms

Contracts priced at exactly a whole million (to within half a crown) are counted separately, by million (1 … 13). All
other contracts form the **open histogram**: bins of 10 000 Kč over (500 000, 13 500 000], 1 300 bins, bin *j* =
(500 000 + 10 000·j, 500 000 + 10 000·(j+1)].

### 5.2 Locations and windows

The band of a location is (0.95 L, L]; the missing-mass window above a limit is (T, 1.05 T].

| Role | Locations (million Kč) |
|---|---|
| Old limits | 2 (supplies and services), 6 (works) |
| New limits | 3 (supplies and services), 9 (works) |
| Controls (round millions with no legal meaning in 2020–2026) | 4, 5, 7, 8, 10, 12, 13 |

1 million (the § 219 limit after 3 April 2025) and 11 million (holds the VAT image of 9 million) are not controls.

### 5.3 Nuisance windows (excluded from the fit, not analysed)

The 5 % band below each of: the EU central thresholds of 2020–2026, the EU sub-central thresholds, the § 18(3) part
amounts, 750 000, 1 million and 11 million; snapped outwards to bin edges.

### 5.4 Counterfactual

For each period, a Poisson regression of the open histogram on a degree-7 Legendre polynomial in the log bin midpoint
and three indicators for bins containing a multiple of 500 000, of 100 000 (not 500 000) and of 50 000 (not 100 000),
fitted on all bins outside the location, missing-mass and nuisance windows. Its fitted counts ĉ are the
counterfactual (`bunching.excess`, iteratively reweighted least squares).

## 6. Estimands and identification

### 6.1 Two estimands at each location

With E(L) = Σ ĉ over the band (0.95 L, L], the expected number of contracts in the band:

- **a(L), mass at exactly L** = (contracts priced at exactly L) / E(L).
- **b(L), excess strictly below L** = Σ over the band of (open count − ĉ) / E(L), contracts at exactly L excluded.

a + b is the total excess of the band. b_inner and b_outer, the same over (0.975 L, L) and (0.95 L, 0.975 L], describe
its shape (§7.3).

**H1 is carried by a.** § 27 makes a price equal to the limit legal, and for a direct award the price in the
contract is the legal value, so an authority or a bidder who wants the largest contract that stays small-scale can
price at exactly the limit. The competitive-discount step of §3.2 hardly puts contracts at exactly L: it lands in b.
So a isolates deliberate placement at the limit, while b mixes placement below it with the step. Reading the other
estimand: **a supported, b null**: the response is placement at exactly the limit, with no broader shift of prices
below it. **b moves, a null**: an excess spread under the limit appeared without placement at it, which the step of
§3.2 could produce without anyone aiming at the limit; it is not read as a response by authorities. **Both move**: both
are reported, and only a carries the label. b never changes the label of H1.

### 6.2 The move

With control mass A_C = Σ_C (contracts at exactly C) / Σ_C E(C) over the seven controls, and k = A_C(post) /
A_C(pre):

- **H1 (primary): mass at the new limits appears.** D_new,a = ½ Σ_{L ∈ {3 M, 9 M}} [a(L, post) − k·a(L, pre)] > 0.
- **H2 (secondary, own label): mass at the old limits shrinks.** D_old,a = ½ Σ_{L ∈ {2 M, 6 M}} [k·a(L, pre) − a(L, post)] > 0.
- **Descriptive, no label:** D_new,b and D_old,b, with the additive adjustment B_C(post) − B_C(pre) in place of k
  (B_C is the control excess on b, close to zero by construction, so a ratio would be undefined); each location's D
  alone; the type split.

Before the change 3 and 9 million were round millions only, so k·a(L, pre) is their expected mass at exactly L after
the change; anything beyond it is a response to the new limit. The ratio assumes that a change in the taste for round
millions scales exact-million mass by the same factor everywhere; the synthetic test where rounding triples leaves a
residual below 0.15 with the ratio and above 0.2 with the additive form.

**Ratio or additive, and undefined draws.** The choice is made once, on the full sample, from counts at the control
millions only: the ratio is used if at least 200 contracts in the pre period and 50 in the post period sit at exactly a
control million, the additive form otherwise; the choice is recorded and applied to every bootstrap draw. A draw in
which k is undefined (no exact-control contract in the pre period of that draw) is counted as failed; intervals use
the remaining draws (`nanpercentile`), and if more than 1 % of draws fail for any statistic that enters a label or the gate (D_new,a, D_old,a, the seven
placebos, their mean and, with the ratio, k_low − k_high) the run stops with an error instead of producing a label.

**Calibration by the placebos.** Each control C in turn is treated as a "new limit", with k from the other six:
placebo_C = a(C, post) − k₋C·a(C, pre). Their mean P̄ is the bias of the adjustment at a round million with no legal
meaning, and their spread s_P beyond their own sampling noise is the error the adjustment adds at a single location.
The labelled statistics are calibrated: D*_new,a = D_new,a − P̄ and D*_old,a = D_old,a + P̄ (the opposite sign
convention), with standard error se* = √(se² + max(0, s_P² − mean of the seven placebos' bootstrap se²)), where se is
D's own bootstrap standard error; the 95 % and 90 % intervals are D* ± 2.447 se* and ± 1.943 se*, the t quantiles with six degrees of freedom
(decided 12 October 2026, after the round-2 sweep showed a false "supported" in 5–8 % of null simulations with normal
quantiles under heavy rounding). With seven
placebos the spread is estimated on six degrees of freedom, so it is a rough correction; it is the one the lead
reviewer recommended (round 2).

**Controls.** The primary k pools all seven controls, weighted by their expected counts, for precision. Proximity-weighted
controls (4 and 5 million for the 2 and 3 million limits, 5 and 7 for 6 million, 8 and 10 for 9 million) are a
robustness row, and the stability of k across magnitude (k from 4–5 million against k from 10–13 million) is reported
(§7.1).

### 6.3 What the move would identify and what it would not

Under assumptions A1–A5, D*_new,a > 0 would be consistent with a response of recorded contract prices to the legal
limit: more contracts priced at exactly 3 and 9 million after those became the limits, beyond what round millions
explain. It would not identify which
behaviour produced it. From prices alone the design cannot tell apart an estimated value or a price set to fit the
limit (manipulation in the sense of [R1]), a legitimate narrowing of scope, a budget set at the limit and a bidder
pricing to it, or splitting (which moves mass far below the limit, mostly outside the band). The article will call it
a response to the limit and will not use "manipulation", "splitting" or "corruption" for it; nothing here says
whether discretion below the limit raises prices or favours particular firms.

### 6.4 Assumptions

A1, a smooth counterfactual for the open histogram, given sub-million rounding. A2, proportional rounding: exact-million
mass changes by a common factor k across locations between periods (tested by §7.1). A3, no other change at the
limit locations on the change date (§6.5). A4, stable coverage: the Registr smluv act was last amended with effect from
1 January 2025 (consolidated version 8). A5, stable reporting: the share of VAT-inclusive prices typed as without VAT,
and the presence of the price without VAT, do not change at the limits differently across periods.

### 6.5 Other changes at the same locations

The § 219 profile limit moved from 500 000 to 1 million on the same day (no bite in the register; 1 million not
used). From 1 May 2025, EU-funded recipients that are not contracting authorities have a 6 million direct-purchase
limit for supplies and services, which can hold some mass at 6 million after the change (biasing D_old,a towards zero,
not D_new,a). Internal rules may keep 2 and 6 million as category bounds (§2.2).

## 7. Placebos and checks

1. **Validity gate (can change the labels; the lead reviewer's recommendation, round 2).** The placebos calibrate D
   (§6.2), so the gate stops a label only when the calibration itself cannot be trusted. It fails if (i) the 90 %
   interval of the mean placebo P̄ lies wholly outside ±0.15: the adjustment is off at round millions by more than the
   margin, too far for a linear correction to be credible; or (ii) with the ratio adjustment, the 90 % interval of
   k_low − k_high (k from 4–5 million against k from 10–13 million) lies wholly outside ±0.5: the taste for round
   millions changed by magnitude, which A2 rules out, and half the scale of k is a change no common factor can absorb.
   If the gate fails, H1 and H2 are labelled inconclusive, with the reason. The seven placebos, P̄, s_P, k_low and
   k_high are reported. Earlier gate rules are described under "Changes before registration".
2. **Placebo date.** The pre period alone, split at 1 January 2023, read by the "not supported" rule: a 90 % interval
   of D_new,a inside ±0.15 passes; otherwise the article says that the design finds a response where there was no
   change of limit.
3. **Shape of b.** b_inner against b_outer at each limit and period. Descriptive.
4. **Missing mass** above each limit, m(T) over (T, 1.05 T], in both periods. Descriptive.
5. **Monthly series.** By month of conclusion, January 2020 – June 2026, the share of contracts in the range priced at
   exactly 2, 3, 6 and 9 million and at the pooled controls. Descriptive, shown as a figure.
6. **Type cross-check (needs §4.10, and §4.11 for the Hlídač version).** Within works no response is expected at 3
   million, within supplies and services none at 9 million. Read by the "not supported" rule: the check passes if the
   90 % interval of D_new,a at 3 million within works and at 9 million within supplies and services both lie inside
   ±0.15. It is run twice, with the stem flag and, if available, with Hlídač státu's classification (whose agreement
   with the stem flag is reported); a failure says that the type split or the pooling assumption is unreliable and is
   reported beside the headline, without relabelling.

All of 1–6 are implemented in `bunching.py` and `estimate.py`.

## 8. Reading rules

### 8.1 Labels for H1 and H2

Applied in this order, to each hypothesis on its own:

1. **Underpowered** if the minimum detectable effect computed at the data step (§9.4) exceeds 0.25.
2. **Inconclusive** if the validity gate of §7.1 fails.
3. **Not supported** if the 90 % interval of D* lies wholly inside (−0.15, +0.15) (sentences in §8.2, with and
   without the note "detected, below the margin", which applies when the 95 % interval also lies above 0).
4. **Supported** if the 95 % interval of D* lies wholly above 0.
5. **Inconclusive** otherwise; an interval wholly below 0 is reported as such.

The margin 0.15 is the smallest response the author considers worth an article on the pooled scale: 15 contracts
at exactly the limit per 100 expected in its band. On the scale of the contracts the limit binds it is 0.15 / s, where
s is their share at the location (0.30 for s = 0.5). The underpowered bound follows from the margin: "not supported"
needs a 90 % half-width below 0.15, i.e. a standard error below 0.15 / 1.943 = 0.077 (t, six degrees of freedom), i.e. an MDE
(2.447 + 0.906 = 3.35 standard errors) below 0.259; the bound is 0.25, unchanged by the switch to t quantiles.

### 8.2 Reading H1 and H2 together (pre-written sentences, no further label)

- H1 supported, H2 supported: "Contracts priced at exactly the limit moved with it: more at the new limits, fewer at
  the old ones."
- H1 supported, H2 not supported or inconclusive: "More contracts were priced at exactly the new limits; at the old
  limits the mass did not measurably shrink, which internal rules keeping 2 and 6 million as category bounds, the
  § 18(3) part amount near 2 million and slow adjustment could each explain."
- H1 not supported, without the note: "No more contracts were priced at exactly the new limits than round millions
  explain, within 0.15 on the pooled scale, i.e. within 0.15 / s among the contracts the limits bind (0.30 if half of
  the contracts there are of the binding type)."
- H1 not supported, with the note "detected, below the margin": "Slightly more contracts were priced at exactly the new
  limits than round millions explain, but the difference is smaller than the margin of 0.15 on the pooled scale
  (0.15 / s among the contracts the limits bind), so the study does not count it as a response."
- H1 inconclusive or underpowered: the label and its reason; H2 is not read as evidence of a response.

The headline is H1. H2 never supports H1, and b, location-specific and type-specific estimates carry no labels.

### 8.3 Several thresholds

Four limit locations enter two pooled statistics fixed before data; per-location estimates are shown, not labelled,
so there is no search over thresholds. EU and § 18(3) thresholds are nuisance windows, never tested. There are no
tallies across hypotheses.

### 8.4 Inference

Cluster bootstrap by publishing authority (`subjekt/ico`): 999 draws for the primary row, 199 for the others,
percentile intervals over defined draws (§6.2) for unlabelled statistics and the calibrated t intervals of
§6.2 for D*. An authority is drawn with all its contracts in both periods. The Poisson counterfactual must converge
(steps below 10⁻⁹ within 100 iterations) in the point estimate and in every draw, or the run stops.

## 9. Power

### 9.1 Calibration away from the thresholds

From the two monthly dumps (E5), the counts of priced records outside BLIND in five far bands were fitted by a
power-law density (Poisson deviance): α = 1.675, about 11 300 priced records a month interpolated into the range
before screening. This figure is an extrapolation across a factor of 30 in value and is plausible within a factor of
two; the retained-share scenarios below span part of that uncertainty.

### 9.2 Simulation

`power.py` draws contracts from the calibrated density and assigns them to 8 000 authorities of lognormal size
(σ = 1.5), each with its own price level (lognormal, σ = 0.3) and its own habit of rounding to whole millions (gamma,
shape 0.5); 15 % of prices are rounded up to the next 100 000. The share rounded to a whole million is unknown and is
swept over 2 %, 10 % and 30 %. The retained share after screening is 0.6 or 0.35, and the post period is 12 months.
For each scenario the registered estimator runs 150 times under the null for the spread of D, and once with a
199-draw bootstrap for the calibrated standard error; the MDE is 3.35 times the larger (t quantiles, as the labels use). Labels and the gate are then
computed by the registered code (`bunching.decide`, which `estimate.py` calls) on 60 simulated datasets under the null
and 60 with a planted placement at exactly the limits (30 % of the binding-type contracts just above each limit, in
both periods; half of the contracts are of the binding type), each with a 99-draw bootstrap. A seventh scenario lets
the rounding share grow with price in the post period only (probability × price / 3 M), so k differs by magnitude
and the gate's k-stability rule is exercised. Dilution: in the tests, a
planted response among half of the contracts gives a pooled estimate of 0.35–0.65 of the undiluted one, so the MDE on
the scale of affected contracts is MDE / s.

### 9.3 Results

From `docs/research/procurement-bunching-power.json`, with the registered t intervals (6 degrees of freedom). MDE at
80 % power on the pooled scale (D* for a), 3.35 standard errors. Label and gate rates come from 40 simulated datasets
per cell, each run through `bunching.decide`; a rate of 0.025 is 1 of 40, so the rates carry a sampling error of
several points. The planted alternative gives a calibrated D*_new,a of about 0.19–0.20.

| Retained | Rounded to a million | Contracts pre / post | MDE D_new,a (s = 0.3 / 0.5 / 0.7) | MDE D_old,a | MDE D_new,b | Null: gate fails | Null: "supported" | Null: "not supported" | Alternative: "supported" (effective power, gate included) |
|---|---|---|---|---|---|---|---|---|---|
| 0.60 | 2 % | 407 612 / 81 522 | 0.05 (0.16 / 0.09 / 0.07) | 0.06 | 0.13 | 0.00 | 0.00 | 1.00 | 1.00 |
| 0.60 | 10 % | 407 612 / 81 522 | 0.09 (0.30 / 0.18 / 0.13) | 0.12 | 0.13 | 0.00 | 0.00 | 0.98 | 0.98 |
| 0.60 | 30 % | 407 612 / 81 522 | 0.18 (0.60 / 0.36 / 0.26) | 0.27 | 0.14 | 0.00 | 0.03 | 0.38 | 0.70 |
| 0.35 | 2 % | 237 774 / 47 554 | 0.07 (0.24 / 0.14 / 0.10) | 0.10 | 0.17 | 0.00 | 0.00 | 1.00 | 1.00 |
| 0.35 | 10 % | 237 774 / 47 554 | 0.12 (0.39 / 0.24 / 0.17) | 0.17 | 0.19 | 0.00 | 0.00 | 0.83 | 0.98 |
| 0.35 | 30 % | 237 774 / 47 554 | 0.24 (0.81 / 0.49 / 0.35) | 0.44 | 0.21 | 0.00 | 0.03 | 0.08 | 0.45 |
| 0.60 | 10 %, drifting by magnitude after the change | 407 612 / 81 522 | 1.43 | 1.46 | 0.14 | 1.00 | 0.00 | 0.00 | 0.00 (gate fails in every dataset) |

With t quantiles the rate of a false "supported" under the null is at most 1 of 40 in every scenario (0.03), in line
with the nominal 0.025; with normal quantiles (round 2) it was 0.05–0.08 under heavy rounding. The cost is power under
heavy rounding: a calibrated response of about 0.19 is labelled "supported" in 70 % (more contracts) and 45 % (fewer)
of simulations, and more of the null datasets end "inconclusive" instead of "not supported". The gate never fails when
rounding changes by a common factor and fails in every dataset when it drifts by magnitude, where the calibrated D*
is −0.37 under the null and −0.18 under the alternative and would otherwise give wrong labels. The MDE of H1 stays
below the underpowered bound of 0.25 in every common-factor scenario (0.24 in the worst); H2's exceeds it with heavy
rounding (0.27 and 0.44), where H2 would be labelled underpowered. On the scale of the contracts a limit binds, the
design detects 0.07–0.24 with light rounding and needs 0.26–0.81 with heavy rounding, depending on s.

### 9.4 At the data step

`prepare.py --totals-to-power` passes the real numbers of primary contracts in the range (pre and post) and of
authorities straight to `power.data_step`, which reruns the MDE for the three rounding scenarios and writes the worst
case as `data_step_mde`; the totals are neither printed nor written. A hypothesis whose MDE exceeds 0.25 is labelled underpowered (§8.1). `estimate.py` refuses to run
without it.

## 10. Robustness

Each row is reported in a table with D_new,a, D_old,a, D_new,b and the calibrated D*_new,a; none relabels. Each row
runs inside its own error handler (a row that fails, for example with an undefined k, is recorded as failed and
listed), and the results file is written after every row. **Aggregate rule:** a row marked † flips if its own label
for H1, computed by §8.1 on its D* without the gate and the underpowered rule, differs from the primary's label
computed the same way. A label flip is used rather than a fixed change of the point estimate because the labels are
what the article reports, and a change of, say, 0.05 means different things at different standard errors. If 3 or
more of the 16 † rows flip, the article says "the result is sensitive to specification" next to the headline. The two
start-date rows are not counted; they read by direction.

| Row | Change | Reading |
|---|---|---|
| Windows † | 2.5 % and 10 % bands | a depends on the band only through E(L); a large change points to a poor counterfactual |
| Polynomial † | degree 5 and 9 | as above |
| Adjustment † | the other form (additive or ratio) | a sign change means the result rests on the rounding model |
| Neighbouring controls † | k per limit from its neighbours | a large change means k varies with magnitude (§7.1) |
| VAT images † | excluded from the fit | a change means VAT typing errors matter |
| R-VAT † | VAT-only prices added, / 1.21 | a change means the 18 % without a price without VAT differ |
| No deduplication † | content-key duplicates kept | a change means duplicated records drive the result |
| Equal values † | records with equal with- and without-VAT values dropped | as above, for the 7–9 % with equal values |
| Post from 3 April 2025 | transition quarter included | "consistent" if D* is at most the primary's (slow adjustment dilutes the first quarter) |
| Post from 1 October 2025 | first quarter after the transition dropped too | "consistent" if D* is at least the primary's; smaller points to a transient response |
| Pre 2022–2024 † | pandemic years dropped | a change points to a pre-period trend |
| Concentration † | largest 1 % of authorities dropped | a change means a few authorities drive the result |
| Linked records † | dropped | a change means linked records (meaning undocumented, §3.1) matter |
| Call-offs † | dropped | a change means orders under frameworks drive the result |
| Frameworks and periodic prices † | dropped | as above |
| Payer flag † | only records whose publisher is flagged as payer (28 %) | a change means sales or income contracts survive the stems |
| Placebo date | §7.2 | 90 % interval inside ±0.15 |
| Type split | works and supplies/services separately by stems; and by Hlídač státu's classification on its sample, if a token was present | §7.6; not counted for sensitivity |

## 11. Choices register

| Choice | Value | Rationale, or the row that tests it |
|---|---|---|
| Source | Registr smluv dumps | The only open source with contracts below the limit (§3.1) |
| Value | price without VAT | The legal value for direct awards (§3.2); R-VAT, equal-values rows |
| Range | 0.5–13.5 million | Covers all four limits and seven controls; arbitrary beyond that |
| Bin width | 10 000 Kč | Fine enough for 5 % bands at 1 million; arbitrary, not varied |
| Band | 5 % below | Arbitrary; 2.5 % and 10 % rows |
| Missing-mass window | 5 % above | Arbitrary; limited by neighbouring controls |
| Polynomial | degree 7, log scale | Common default [R3]; degree 5 and 9 rows |
| Sub-million rounding | 50k, 100k, 500k indicators | Visible spikes in price data; not varied |
| Controls | 4, 5, 7, 8, 10, 12, 13 million | Every round million with no legal meaning and no overlap (§5.2); neighbours row |
| Primary estimand | a (exact mass) | §6.1 |
| Adjustment | ratio if enough exact-control contracts | §6.2; other-adjustment row |
| Pre period | 2020–2024 | EU sub-central thresholds before 2020 sit in the 6 million band; 2022–2024 row |
| Post period | 1 July 2025 – 30 June 2026 | §4.1; 3 April and 1 October rows |
| Pooling | all types | No classifier needed; type-split rows |
| Screening stems | `rules.py` | Written without reading subjects; hit counts reported; payer-flag row |
| Margin | 0.15 | §8.1; the author's smallest response of interest |
| Underpowered bound | 0.25 | Derived from the margin (§8.1) |
| Calibration | D minus mean placebo, SE inflated by the placebos' excess spread | §6.2; the lead reviewer's recommendation |
| Gate | mean placebo or k_low − k_high wholly outside ±0.15 / ±0.5 (90 %) | §7.1; ±0.5 is arbitrary, half the scale of k |
| Bootstrap | by authority, 999 / 199 draws | Contracts of one authority are not independent |
| Interval for D* | t quantiles, 6 degrees of freedom | §6.2; decided 12 October 2026 |
| Sensitivity rule | label flip in 3 of 16 † rows | §10; the count of 3 is arbitrary |
| Deduplication | content key with a contract number | §4.3; no-deduplication row |

## 12. Exposure handling during the analysis

The order is fixed: register (§14) → collect all dumps → `prepare.py --totals-to-power` (prints "ok"; screening counts only, totals go
straight to the power data step) → `estimate.py` once → results commit. `estimate.py --quick` is a crash check: it
writes nothing and prints only "ok". No histogram of the range is drawn before the results commit. Any look outside
this order is logged in the change log with its date and what was seen.

## 13. What this will not show (limitations)

- **Mechanism.** §6.3: a response to the limit, not manipulation, splitting, favoritism or prices paid.
- **Estimated values.** The register holds prices; contracts from procedures cannot be told from direct awards except
  through the rarely filled procurement number.
- **Coverage.** The register exempts contracts of municipalities without extended powers and their organisations
  (§ 3(2)(k) zákon 340/2015), so small municipalities, a large share of small-scale purchasing, are missing; so are
  contracts at or below 50 000 Kč, and trade secrets may hide some state companies' prices (§ 5(6)).
- **Splitting** mostly places parts far below the limit and escapes the band.
- **Short post period.** Twelve months, after a transition quarter.
- **Scale.** "Not supported" bounds a response at 0.15 on the pooled scale, which is 0.15 / s among the contracts the
  limit binds: 0.30 if half of them are of its type, 0.50 if 30 %.
- **Type.** The pooled analysis dilutes each limit by the other type; the type split rests on keywords.
- **Not a purchase.** The stems are coarse; grants and sales that survive add round-number noise.
- **Field meanings.** `navazanyZaznam` is documented only as a link; the payer flag is filled on 28 % of records.
- **Earlier limits.** Limits set under the 2006 act predate the register and are not studied.

## 14. Registration workflow

The study is described as **pre-registered only if a signed annotated tag `procurement-bunching-design`, on the
registration commit, has been pushed to the public remote before any dump beyond the two of §0 is downloaded** (editorial
standard §6: a signed tag pushed to the public remote is a tamper-evident anchor). The lead creates and pushes the
tag once Bára's SSH signing is set up. The steps:

1. **Freeze.** The design, `tools/procurement/` and the structure and power files are committed on
   `feature/PROC-1_procurement-bunching` (one-line messages, no AI attribution); the working tree is clean.
2. **Tag.** `git tag -s -a procurement-bunching-design <registration commit> -m "Registered design: procurement thresholds"`
   with SSH signing (`git config gpg.format ssh`, `user.signingkey` set to Bára's key).
3. **Verify.** `git tag -v procurement-bunching-design` reports a good signature for the key, and
   `git rev-parse procurement-bunching-design^{commit}` equals the registration commit.
4. **Push.** `git push origin feature/PROC-1_procurement-bunching` and `git push origin procurement-bunching-design`.
5. **Record.** The tag's object hash, the commit hash and GitHub's push time go into the change log
   (`docs/changelogs/procurement-thresholds.html`) in a dated note, before the data step.
6. **Data step,** only after step 5: `collect.py`, `prepare.py --totals-to-power`, optionally `hlidac.py`, then
   `estimate.py` once, each in dated commits, then one results commit; deviations go into the change log.
7. **Article wording.** With steps 2–5 done before step 6: "pre-registered: signed tag `procurement-bunching-design`
   (commit `<hash>`), pushed `<date>`, before any outcome data were joined." If anything of step 6 ran before the push,
   the only permitted wording is: "registered analysis plan: design committed at `<hash>` on `<date>`, before the
   results commit `<hash>`; commit times are self-reported, and the branch was pushed after the analysis" (with the
   push-time variant of §6 where GitHub's activity log applies).
8. **Disclosure.** §0 is repeated in the article (editorial standard §6, last rule).
9. **Retention.** After the results commit the raw dumps are deleted; the manifest's hashes and the minimised parquet
   are kept (§3.1).

## 15. Decisions taken (Bára, 12 October 2026)

1. **Anchor.** A signed annotated tag `procurement-bunching-design`, pushed before the data step (§14); the lead
   creates and pushes it.
2. **Source.** Registr smluv only. ISVZ is not used: its `robots.txt` disallows all agents. Hlídač státu is optional,
   for contract type only (§4.11).
3. **Post start.** 1 July 2025 (primary); 3 April and 1 October 2025 as robustness rows.
4. **Margins.** 0.15 and the derived underpowered bound 0.25, on the pooled scale.
5. **Gate and intervals.** The calibration design of §6.2 and §7.1, with t quantiles on six degrees of freedom.
6. **H2.** Its own label.
7. **Stems.** `rules.py` as it stands, with the disclosure of §0.1 (E5′).
8. **Download, compute and retention.** About 10 GB of dumps, one full run, deletion of the raw dumps after the
   results commit.
9. **Slug.** `texts/procurement-thresholds`; file names stay `procurement-bunching` (see the status note).

## 16. Code and reproduction

- `collect.py` (dumps and manifest), `structure.py` (the E5 pass), `rules.py` (stems), `prepare.py` (§4, with
  `--totals-to-power`), `bunching.py` (histograms, counterfactual, a and b, contrasts, placebos, calibration, gate,
  bootstrap with the failure cap, labels through `decide`), `synth_contracts.py` (made-up contracts: rounding with
  authority habits, price levels and a drift by magnitude, placement at or below a limit, dilution by type),
  `power.py` (§9), `estimate.py` (§6–§10), `hlidac.py` (§4.11).
- `test_procurement.py` checks: a price equal to a limit falls below it; every whole million is in a window; rounding
  alone moves neither estimand; placement at the limit lands in a and spread below it in b, with missing mass above;
  more rounding after the change is scaled out of a by the ratio and not by the additive form; a planted response is
  recovered within 15 % on average and 25 % in each of five seeds, for a and for b; dilution by type scales the
  estimate; undefined ratio draws stop the run and the full-sample rule avoids them; the failure cap at exactly 1 % and
  just above it, for every statistic of a label or the gate; non-convergence and a missing IČO stop the run; drifting
  rounding moves k_low − k_high; the calibration arithmetic; the gate; the label order.
- `test_pipeline.py` checks, on made-up records and a made-up parquet: deduplication only with a contract number,
  counted apart at exact millions; versions, flags, dropped records and no party column; `estimate.py` stops without a
  data-step MDE; `--quick` writes nothing; R-VAT adds the VAT-only records; the sensitivity rule (label flips, failed
  rows, start-date directions, placebo date); a registered run writes 21 robustness rows.
- `test_hlidac.py` checks, against mocked responses only: the token from the environment or `.env`; the
  User-Agent, no e-mail address, the token only in a header; the classification parsing; the one-second pause; error
  counting by status; the token never appearing in any output; the skip message without a token.
- `uv run --with-requirements tools/requirements-tests.txt pytest -q tools/procurement`.

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
  readable only in a browser). Accessed 12 October 2026.
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
  https://www.zakonyprolidi.cz/cs/2015-340. Accessed 12 October 2026.
- [L7] Ministerstvo pro místní rozvoj (December 2025). Vzorová vnitřní směrnice obce pro zadávání veřejných zakázek
  malého rozsahu, verze 1.0.
  https://portal-vz.cz/wp-content/uploads/2025/12/Vzorov%C3%A1-vnit%C5%99n%C3%AD-sm%C4%9Brnice-VZMR_verze-1.0-prosinec-2025_final.pdf.
  Accessed 12 October 2026.
- [L8] Liberecký kraj (4 June 2025). News item on amendment no. 2 of Směrnice Rady Libereckého kraje č. 1/2021.
  https://www.kraj-lbc.cz/aktuality/case:detailPdf/itemId:581150/cgId:15623. Accessed 12 October 2026.
- [D1] Digitální a informační agentura. Registr smluv, open data: dumps https://data.smlouvy.gov.cz/ and terms
  https://smlouvy.gov.cz/stranka/otevrena-data (snapshots and hashes in `tools/data/procurement/manifest.json`).
  Accessed 12 October 2026.
- [D2] Hlídač státu. Licence. https://www.hlidacstatu.cz/texty/licence/ (CC BY 3.0 CZ). Accessed 12 October 2026.
- [D3] Digitální a informační agentura. XSD 1.7.0 for the Registr smluv (https://smlouvy.gov.cz/soubor/xsd-1-7-0.zip)
  and Popis aplikačního rozhraní Registru smluv
  (https://testrs.gov.cz/smlouva/soubor/338090/ISRS_aplikacni_rozhrani.pdf). Accessed 12 October 2026.

## Changes before registration

**12 October 2026 (round-1 independent review of `ac51167`; no outcome seen).** The review found the legal base,
the exposure handling and the formulas sound and asked for the following, all applied here: two estimands at each
location (exact mass a, carrying H1, and the open-band excess b), replacing one band total that mixed the exact-limit
price with the round number; a full-sample rule for ratio or additive adjustment, with undefined bootstrap draws
counted and the run stopped above 1 %; `--quick` printing only "ok"; MDEs on the scale of affected contracts; a sweep of
the rounding share and authority-specific price levels and rounding habits in the simulation; an underpowered bound
derived from the margin (0.30 → 0.25) and a "detected, below the margin" sentence; per-control placebos and a k
stability check; content-key deduplication; the XSD's documentation of `navazanyZaznam` (linked records now kept, with
a row that drops them); flags and rows for call-offs, frameworks and periodic prices; presence of the price without
VAT by period and by value band; the primary post period moved to 1 July 2025; a monthly series of exact-limit
shares; `estimate.py` stopping without a data-step MDE; the shape, missing-mass and type checks implemented; a tighter
recovery test over five seeds; the full log of searches and fetches, prior knowledge and the repository search; a
choices register; a reading rule for each robustness row and an aggregate sensitivity rule; the stem `dodatk`; the
quotation of § 16(6). One request was not adopted as written: the per-control gate (§7.1, §9.3).

**12 October 2026 (round-2 independent review of `e3d4f99`; no outcome seen).** The lead reviewer found one blocker:
`estimate.py` dropped records without a price without VAT before building the R-VAT row, so that row silently equalled
the primary; it is now built first and tested. The validity gate was redesigned on the lead's recommendation. The
round-1 version required the mean placebo of the four controls nearest the new limits (4, 5, 8 and 10 million) to have
its 90 % interval inside ±0.15, and each of the four to have its point inside ±0.15 and its interval not wholly
outside; the round-1 reviewer's own proposal, each control's interval inside ±0.15, had been rejected because it failed
under the null in almost every simulation with heavy rounding. The registered version calibrates D by the mean of all
seven leave-one-out placebos, inflates its standard error by their excess spread, and gates only on a placebo bias or
a k drift by magnitude wholly outside fixed bounds; the power sweep now runs the registered label and gate code on
simulated data, including a scenario with rounding that drifts by magnitude. Also applied: deduplication only with a
contract number, counted apart at exact millions, and a no-deduplication row; the sentences for "detected, below the
margin" and the 0.15 / s scale; the sensitivity rule as a label flip, with the start-date rows read by direction;
robustness rows that record their own failure and a results file written after each row; the hand-labelled check
extended to the call-off, framework and not-a-purchase stems, and the disclosure that the stems were revised after their
counts were seen; `prepare.py --totals-to-power`; the failure cap on every statistic of a label or the gate, tested at
the 1 % boundary; the placebo date read by the same rule; loud failure on a non-converging counterfactual or a missing
IČO; "consistent with" in §6.3; the GDPR basis and a retention rule.

**12 October 2026 (Bára's decisions on the open items; no outcome seen).** Calibrated intervals use t quantiles
with six degrees of freedom (2.447 and 1.943) instead of normal ones, and the power sweep was rerun with them. The
study is pre-registered only through a signed tag pushed before the data step (§14, with the exact steps). Registr smluv
is the only source; ISVZ is not used because its `robots.txt` excludes automated access; Hlídač státu is an optional
type classification (`hlidac.py`, tested against mocked responses only, with a cross-check row and its reading rule).
The post period starts on 1 July 2025; H2 keeps its own label; margins, stems, the download and the retention rule are
approved; the slug is `texts/procurement-thresholds`, and the change log moves to
`docs/changelogs/procurement-thresholds.html`.
