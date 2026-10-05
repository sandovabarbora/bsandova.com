# One city, 57 budgets: research design (Part 3, extended)

**Status: pre-specified analysis, version 2 (29 September 2026).** Revised after three referee reports on draft v1: public
finance and political economy, statistics, and data audit (`docs/research/prague-districts-referees.md`). The
response is item by item in §10.

Analysis plan committed at `683b0c8` on 29 September 2026, before this analysis was run; the author had worked with
these data since May 2024; commit times are self-reported. At that commit:

- every raw file listed in Appendix A had been downloaded and hashed (`docs/research/prague-districts-files.sha256`);
- the grant lists had been parsed for **structure only** (`docs/research/prague-districts-grants-structure.json`);
- the alignment coding had been frozen and hashed (`docs/research/prague-districts-alignment.csv`, `.json`);
- the design-stage power simulation had been run on the real switch vectors (`docs/research/prague-districts-power.json`).

Deviations will be listed, dated, under "Changes after registration".

## 0. What has already been seen

The author has worked with these data since May 2024; the plan sets the analysis in advance; the author already knew the data. The
items below are those recorded while preparing this design.

### 0.1 Part 3 as published (before the correction)

MONITOR actuals ("reality") for 2022, 2023 and 2024 for all 57 districts, divided by residents at 31 December and
averaged.

- **Public per district** in `districts.json`:
  - spending per resident, the three-year mean and each year;
  - spending shares of eight function groups and of capital outlays;
  - income shares and per-resident income, split into taxes, non-tax and class 4;
  - the 2022 district lists with their votes and seats.
- **Headline figures:**
  - the 13 districts over 40 000 residents spend 8 346–17 604 CZK per resident;
  - Praha 1 spends 35 320 (35 602 / 34 564 / 35 794 in the three years);
  - the median district spends 14 669, and the range is 7 763–73 020;
  - Praha-Lysolaje spent 119 531 in 2022 and 27 118 in 2024, and 73 % of its spending over the three years was
    capital;
  - Praha 1's overnight-stay fee was 47.5 → 82.9 m CZK and its public-space fee 97.3 → 114.2 m CZK (2022 → 2024);
  - in the large districts, the median town-hall share is 29 % (24–38), education 32 % (18–42), social 7.5 % (2–17)
    and capital 28 % (14–48).
- **The size shape.** Figure 1 plots spending per resident against population, so the shape of that relation for
  2022–2024 has been seen.

### 0.2 The Part 3 correction (branch `docs/PRAHA-3_transfer-label-fix`, 28 Sep 2026)

The correction removed items 4131, 4132 and 4140 from "transfers" and counted them as own non-tax revenue. It
changed only the three-year means that had already been published.

| Figure | Old | New |
|---|---|---|
| Transfers, share of the median district's income | 82 % | 76 % |
| Transfers, range of that share | 66–92 % | 38–92 % |
| Transfers per resident, Praha 1 | 23 570 | 13 655 |
| Transfers per resident, Praha 4 | 7 009 | 6 804 |
| Non-tax income per resident, Praha 1 | 2 393 | 12 308 |
| Non-tax income per resident, Praha 4 | 699 | 905 |
| Districts whose share of income from transfers is changed | – | 48 |
| Districts where transfers are below half of income | none | Praha 1, Praha 2 |

**What this reveals.** The referees found that district reports carry no 411x/42xx state items: all state money
arrives through 4137/4251. So the new "transfers" column is, per district, the 2022–2024 three-year mean of actual
4137 + 4251 (+ 4121/4122, if present) per resident. This is part of the *reality* half of the MONITOR secondary
outcome.

### 0.3 Seen by the referees (reported in their file, §0)

- **Data referee, by accident:**
  - MONITOR totals nodes for Praha 1 and Praha 4, 2023;
  - for Praha 2 and Praha 3, 2019, item 4137 approved, amended and actual (from the closing-account PDF);
  - the city's totals for 4137 and 5347 in 2019.
- **Statistics referee:** rough alignment counts for 2022→2023 from the election files, with no budget data. 17
  up-switchers, 3 down, 32 never aligned, 5 always aligned. 15 of the 17 switched because the coalition changed.
- **Public-finance referee:** the published income shares sum to 0.91–1.00 of total income.

### 0.4 Seen by the author while preparing v1 and v2

- **v1** (see the v1 file in git history):
  - MONITOR JSON structure;
  - the empty 2015–2021 district reports;
  - the Praha 8 2022 budget memo, one district-year of approved amounts (formula transfer 357 379 thousand CZK,
    state-administration contribution 88 527 thousand CZK, property tax 118 200 thousand CZK);
  - search snippets for Praha 6 and Praha 9 (2024) and city totals for 2019 and 2024;
  - the election files, RÚIAN and ČSÚ structure.
- **v2, closing-account text read while locating the lists.** Numbers were masked in the author's own tools, except
  in these cases:
  - **The first rows of the 2019 city-grant list (section 5.3).** About 35 lines were read unmasked while learning
    the layout: environmental grants (ÚZ 81, ZHMP resolution 8/27, chapter 02), each with its amount. The districts
    were Praha 2, 3, 5, 6, 8, 17 and 18, Běchovice, Březiněves, Čakovice, Ďáblice and Klánovice.
  - **A header scan of the 2025 part III report**, which printed several city-wide 2025 sentences with their
    amounts:
    - non-investment targeted grants to districts, 891 557.9 thousand CZK;
    - investment targeted grants, 3 475 335.4 thousand CZK;
    - ÚZ 84 investment, 2 552 075.6 thousand CZK;
    - an MŽP grant, 1 722.9 thousand CZK;
    - the text of the ZHMP resolutions on retained grants (22/35, 22/33, 26/53, 26/66, 20/16).

    No district-level amount for 2025 was printed.
  - **Allocation tables** (annexes of each approved budget): sheet names, shapes, the number of cells naming a
    district, and the header "Kritéria: 30 % dle počtu obyvatel MČ, 10 % dle rozlohy MČ, 30 % dle počtu dětí MŠ a
    žáků ZŠ…" for 2019–2023. No amount was read in preparing this design.
  - **Grant-list structure:** row counts by section, layout, resolution type, ÚZ class and column header, and the
    coverage of resolution dating (§4.2). These are counts of rows, not of money.
- **Coders.** Six coding agents (two blind coders × three groups of districts) reported that they saw, and did not
  record, incidental money figures in district newsletters, resolutions and minutes:
  - councillors' pay;
  - individual grant or project sums in Zbraslav, Ďáblice, Velká Chuchle, Chaberský zpravodaj, Koloděje, Kolovraty,
    Nedvězí and Šeberov documents;
  - an idnes.cz headline (Sep 2026) about extra money for outlying districts.

  One coder listed the scratchpad directory and saw file names only. None of this reaches the author's analysis
  files.

## 1. Background: how a Prague district is financed

- **The legal frame.**
  - Prague is one municipality and one region (Act 131/2000 Coll.).
  - Shared taxes go to the city under the budgetary allocation of taxes (Act 243/2000 Coll.). The districts receive
    what the city's Statute (OZV 55/2000 Sb. hl. m. Prahy) and its budget give them.
- **The districts' own revenue:**
  - the full property-tax yield;
  - local fees;
  - rents and sales, often through the business account that feeds the budget as item 4131.
- **The rule-based transfer ("finanční vztah", item 4137).** It is set in the city's December budget as a formula
  share of the expected shared-tax yield. The data audit found three regimes:
  - **2015–2019:** 30 % of the personal-income-tax yield, then the criteria 30/10/30/20/10 (residents, area, pupils,
    green space, roads), with different weights for districts 23–57 in 2015, and with floors and caps;
  - **2020–2023:** 30/10/30/20/10, with a per-resident floor and cap of 3 000 / 5 500 CZK, raised to 3 500 / 6 000
    in 2023;
  - **2024–2025:** a new rule, last year's actual plus a top-up tied to the tax forecast. The new coalition adopted
    it on 14 Dec 2023. The 2023 allocation had been adopted on 15 Dec 2022, by the old council.
- **The state-administration contribution** (PVSS, also 4137) is financed by the state and routed through the city.
- **Discretionary grants.** During the year the city council (RHMP) and assembly (ZHMP) grant targeted
  non-investment (4137) and investment (4251 from 2020) money through budget measures (rozpočtová opatření).
  - The city's closing accounts list every one of them by district, with the resolution, the purpose code (ÚZ) and
    the amount.
  - State pass-throughs (ÚZ 98xxx and other state ÚZ) and operational programmes are listed separately.
- **City coalitions** (sources: Part 1, `docs/research/prague-council-sources.md`):

  | From | To | Coalition |
  |---|---|---|
  | 26 Nov 2014 | 14 Nov 2018 | ANO, ČSSD, SZ, KDU-ČSL, STAN |
  | 15 Nov 2018 | 15 Feb 2023 | Piráti, Praha Sobě, TOP 09, STAN, KDU-ČSL (Spojené síly pro Prahu) |
  | 16 Feb 2023 | – | ODS, TOP 09, KDU-ČSL, Piráti, STAN |

  - 2014–2018: the coalition was declared dead on 10 Nov 2015 and renewed on 28 Apr 2016. That period is the
    **interregnum**.
  - 2018–2023: from the Sept 2022 election until 16 Feb 2023 the council was a caretaker.

## 2. Research questions and estimands

- **RQ1 (alignment premium).** When a district becomes governed by a party of the city coalition, do the city's own
  in-year grants to it rise, relative to districts whose status did not change?
- **RQ2 (what kind of money).** Is the premium carried by investment grants?

**Estimand of H1: the switch-in effect.** Take districts unaligned in the three regime-years before a city-coalition
event and aligned in the three after. The estimand is the average, over those districts, of the change in the city's
own grants (scaled as in §4.3) between the pre and post windows, minus the same change in districts unaligned
throughout. It is pooled over the two events (Nov 2018, Feb 2023), weighted by the number of switchers.

- Switch-out is descriptive: its units are few (§6).
- **Switches are party-level.** In 2023 the switch is essentially ODS entering (and Praha Sobě leaving). In 2018
  the Piráti, Praha Sobě and TOP 09 entered, and ANO, ČSSD and SZ left.
- The alignment effect therefore cannot be separated from shocks common to one party's districts. The number of
  independent treatment changes is the number of parties that switched: 4 entries and 4 exits over the two events.
- The design says so, and adds a party-level permutation (§5.3).

**Estimand of H2.** The part of the switch-in effect carried by investment grants, and its excess over the
non-investment part.

**Not registered as confirmatory** (moved out of the family, §3):

- capacity, i.e. capital-budget execution by size (exploratory, two-sided);
- planned deficits and realised surpluses (descriptive);
- size economies, dual mandates, the property-tax windfall and forecast bias (exploratory).

**Literature.**

- Alignment:
  - Solé-Ollé and Sorribas-Navarro (2008);
  - Brollo and Nannicini (2012);
  - Bracco, Lockwood, Porcelli and Redoano (2015);
  - Migueis (2013);
  - Curto-Grau, Solé-Ollé and Sorribas-Navarro (2018);
  - Baskaran and Hessami (2017) on German parliamentary coalitions;
  - Arulampalam et al. (2009).
  - Related, but not clean alignment premiums (corrected 30 Sep 2026): Kauder, Potrafke and Reischmann (2016) on core
    supporters in one discretionary programme; Fiva and Halse (2016) on local favouritism by representatives' home
    municipalities; Muraközy and Telegdy (2016) on subsidy allocation by electoral incentives.
- H2's premise, that visible, investment-type spending is favoured: Drazen and Eslava (2010); Veiga and Veiga
  (2007).
- Inference with few treated clusters:
  - MacKinnon and Webb (2017, 2018, 2020);
  - Conley and Taber (2011);
  - Wu and Ding (2021);
  - Rambachan and Roth (2023);
  - de Chaisemartin and D'Haultfœuille (2020, 2026);
  - Cengiz, Dube, Lindner and Zipperer (2019);
  - McKenzie (2012) on power with noisy, lumpy outcomes.

**Literature benchmark.** As registered, it read: Solé-Ollé and Sorribas-Navarro (2008) "of the order of 40 %";
Bracco et al. (2015) "of the order of 10–20 %"; power statements against "a premium of 20–40 %". The Bracco figure was
wrong. **Corrected 30 Sep 2026 (after outcomes, from the independent audit; see Changes):** Spain, Brazil and Italy
find that aligned municipalities receive roughly a third to a half more (about 40 %, 26–41 %, 36–47 %); Portugal 19 %.
In Germany the sign depended on the governing bloc (+25 % under one state government, −20 to −40 % under the other).
The magnitudes are taken from the audit and were not re-derived from the papers here. The power statements now
compare the design's minimum detectable effect (about 100 %) with "roughly a third to a half". The conclusion is
unchanged: the design could detect only a premium two to three times the published ones.

## 3. Hypotheses, tests and decision rules

**Confirmatory family {H1, H2}. Holm step-down at family-wise α = 0.05.** One one-sided p-value each. Every
hypothesis is reported whichever way it falls.

- **H1 (switch-in premium).** β > 0 for the estimand in §2.
  - The p-value is from **randomisation inference**. Within strata of tier (the 22 numbered districts vs the 35
    others) and among units unaligned at baseline, the switch-in label is permuted, holding the number of switchers
    per stratum and event fixed.
  - The statistic is the studentised pooled difference (Wu and Ding 2021), with 9 999 draws, or full enumeration if
    there are fewer distinct assignments.
  - The smallest attainable p-value is reported.
  - **Co-primary interval:** Conley–Taber.
  - Reported alongside: wild cluster restricted bootstrap (Webb) and CR2.
  - Decision: *supported* if the RI p-value passes its Holm threshold.
- **Equivalence for H1 (not in the family).** A two one-sided test (TOST) with margin ±20 % of the clean controls'
  pre-window mean. A non-significant H1 is called "consistent with no premium larger than 20 %" only if the TOST
  rejects. Otherwise it is "inconclusive".
- **H2 (investment share), intersection–union.** Supported only if both of these hold:
  - β_cap > 0;
  - β_cap − β_cur > 0.

  The p-value is the larger of the two one-sided RI p-values.
  - If the pre-2020 lists do not mark investment grants for at least 95 % of rows (§4.2), H2 is estimated on the
    2023 event alone, whose window (2020–2025) lies wholly in the 4251 period.
- **Outside the family:**
  - H3 (capacity; exploratory, two-sided): the slope of capital-budget execution (MONITOR, 2022–2025) on log
    population, within tier;
  - H4 (planned deficits and realised surpluses; descriptive): (actual − approved) balance per resident, 2022–2025,
    with D (§4.4) and 5901 reserves / class 8 netted out as variants;
  - E1–E4: see v1 §3; they are unchanged in content and remain exploratory.

## 4. Data and measures

### 4.1 Sources

- **The city's closing accounts, 2014–2025** (`https://praha.eu/zpravy-o-plneni-rozpoctu`; the per-year /w/ pages
  are listed in `tools/praha/districts_city.py`).
  - Part III ("městské části"), section 5, gives the per-grant lists:
    - 5.2: state pass-throughs;
    - 5.3: the city's own grants;
    - 5.4: operational programmes;
    - 5.5–5.6: drawdown.
  - The per-district statements are also in part III, and the year-end settlement with the districts is an annex.
- **Approved budgets and proposals, 2015–2026.** The allocation tables ("Finanční vztahy k MČ", per district) exist
  for **2016–2026**. The 2015 approved-budget page carries no attachments, and the 2015 proposal is in PDF. PVSS
  tables exist for 2021–2026.
- **MONITOR** district reports, 2022–2025 (v1), for the secondary outcome.
- **Elections:** ČSÚ open data 2014, 2018 and 2022 (v1).
- **Population:** ČSÚ Prague office. **ZHMP session dates:** Part 1's roll-call files (`tools/data/zhmp/votes{2010,2014,2018,2022}.csv`).

### 4.2 Structure of the grant lists (from the structure pass)

- **Parsed rows** (district, budget-measure number, resolution, ÚZ): about 1 700–4 200 rows per year for
  2014–2023, 1 566 for 2024 and 142 for 2025. In 2025 only drawdown lists remain, with a new layout.
  - Lines naming a district with an amount but not parsed: 115–1 055 per year. Most are continuation lines, subtotals
    and the drawdown tables of 5.6.
  - **Registered rule:** before any amount is summed, the parser is extended until at least 97 % of the amount-bearing
    district lines in 5.3 are parsed in every year. The count is reported; amounts are not.
- **Section 5.3 (the city's own grants)** is present in every year 2014–2023.
  - In 2015 the lists sit in a single section 5.4 that combines 5.3 and 5.4 by source. They are separated by ÚZ.
  - For 2024–2025 the budget-measure lists are gone. **The primary outcome for 2024–2025 is taken from the drawdown
    lists** ("skutečně poskytnuto", amount provided, by resolution).
  - This is a bridging risk. For 2019–2023, where both lists exist, their agreement is computed blind (a statistic
    only, no amounts) before 2024–2025 are used. If Lin's concordance across district-years is below 0.9, the post
    window of the 2023 event is shortened to 2023 alone and H1 uses ℓ = 0 for that event.
- **Resolutions.**
  - In 5.3, 93–99 % of rows cite a ZHMP resolution ("session/item"). **Every one resolves to a dated ZHMP session**
    in Part 1's roll-call files (7 of 1 087 in 2018 and 1 of 782 in 2024 do not).
  - The remaining rows cite an RHMP resolution. They are dated by linear interpolation of the budget-measure number
    (RO), which is sequential within the year, between the nearest ZHMP-dated rows.
- **ÚZ** is present on every parsed row. State ÚZ are 0 rows in 5.3 in every year but one (1 in 2020).
- **Investment / non-investment.** Column headers carry 4251/6363 (investment) and 4137/5347 (non-investment) from
  2020. Before 2020 the 5.3 lists have only 4137/5347 columns.
  - Whether investment grants before 2020 can be separated (by ORG/ORJ codes or a "b" marker) is to be established
    by the parser. H2's fallback in §3 applies otherwise.

### 4.3 The primary outcome

**Y_ir** = the city's own grants to district i whose resolution falls in regime-year r (5.3 lists; drawdown lists
for 2024–2025), in CZK:

- excluding state ÚZ (98xxx and other state codes) and operational programmes (5.4);
- including returns (negative rows) in the year of their resolution;
- **divided by R_i,2016**, the district's approved "finanční vztah" in the 2016 allocation table. This is the
  earliest year with a table in the panel, and a base year before both events.

**Secondary scalings:**

- per resident, with population on 1 January of r − 1 (ČSÚ 31 December of r − 2). The **definition break at 31 Dec
  2022**, when temporary-protection holders are included, is flagged. Robustness holds the 2021 stock.
- log(1 + Y_ir per resident).

**Components:** Y_cap (investment) and Y_cur (non-investment).

**Regime-years.** A regime-year runs 1 Jan – 31 Dec, with two exceptions:

- 15 Nov – 31 Dec 2018 belongs to r = 2019;
- 1 Jan – 15 Feb 2023 belongs to r = 2022. Grants the caretaker council decided remain in the old regime.

Amounts in the lengthened or shortened regime-years are annualised by days. Grants resolved in the interregnum (10
Nov 2015 – 27 Apr 2016) are kept in the primary outcome, and dropped in robustness.

**Panel:** 57 districts × regime-years 2015–2025. 2014 is excluded: it lies outside every event window.

### 4.4 Secondary outcome (MONITOR, 2022–2025)

- D_it = (reality − approved) of 4137 + 4251 per resident, with a variant net of 5347 (returns flow in 226 of 228
  district-years).
- `finalBudget` is dropped: it is always 0.
- 4251 approved is 0 in all 228 district-years.
- **Blind validation:** the parsed 2022–2023 grant lists (all sources) are compared with MONITOR reality − approved
  of 4137 + 4251. Only an agreement statistic (Spearman across district-years) is published.

### 4.5 Alignment (frozen)

- **Primary A_ir:** the district's mayor on 30 June of r belongs to a party in the city coalition of that date.
  - Party is membership at candidacy (candidate register PSTRANA), or, for a non-member, the nominating party
    (NSTRANA).
  - Local lists and movements are not aligned.
  - During a vacancy the previous mayor's party carries over, because the rada elected with that mayor stays in
    office.
- **Where the rule comes from.** The referees asked for "the parties on the rada, or the mayor's party". Small
  districts have no rada, so the mayor's party is the only measure defined for all 57, and it is primary. Rada
  composition, where coded, is kept for robustness.
- **Coding.** Two blind coders coded every mayoral spell from the 2014 constituent sessions to Sept 2026, with
  sources: `tools/data/praha3x/alignment/coder_{A,B}.csv`. Both files are frozen.
  - The mayor's party is taken mechanically from the register, so disagreement can arise only over *who* was mayor.
    The coders named the same mayor in 98.9 % of 627 district-years.
  - The 7 district-years where they differed (Křeslice 2023–24, Lipence 2019, Přední Kopanina 2015–18) were adjudicated before any outcome was joined, with reasons, in `tools/data/praha3x/alignment/adjudication.csv`. All 7 resolve to A = 0. The coders' own party-membership field gives the identical A in all 627 district-years.
- **Hashes:** the frozen coding `46ca3b84765926589c6ac107e56cf507f858fe004b806bf2ec8b9edc18b01949`, the panel `6aa4987457967a9f5b928f495ea8669821d2c58779ad80e8949ecb41ab2a8400`.
- **Robustness rules:**
  - the coders' own party-membership field, which captures mid-term party switches;
  - seat majority by NSTRANA ∪ PSTRANA;
  - the largest list containing a coalition party;
  - the continuous aligned seat share.

  Counts under each rule are in §6.
- **Before publication**, the coding is checked against the constituent-session resolutions. Any change is recorded
  under Changes after registration, and the analysis is rerun both ways.

## 5. Models and inference

### 5.1 Primary estimator (H1, H2): stacked difference-in-differences by event (Cengiz et al. 2019)

- **Events:** e ∈ {2018, 2023}. Window: regime-years e − 3 … e + 2, i.e. 2016–2021 and 2020–2025.
- **Stack e contains:**
  - switch-in units: A = 0 in every pre year and A = 1 in every post year;
  - clean controls: A = 0 in every year of the window.

  Other units are left out of stack e. Mid-term switchers and always-aligned districts are reported separately.
- **Statistic:** per unit, Δ_i = mean(post) − mean(pre) of Y. Per event, the difference between switchers' and
  controls' mean Δ, studentised (Welch). Pooled over events with weights proportional to the number of switchers.
- **The same estimate in regression form:** Y_ier = α_ie + γ_re + β·(switch_ie × post_r), with district×event and
  year×event effects. It is reported with CR2 (clusters = districts) and WCR.

### 5.2 Dynamics and pre-trends

- Event-study coefficients for leads −3 … −1 and lags 0 … 2, with a joint RI pre-trend test on the leads.
- HonestDiD (Rambachan and Roth 2023) intervals for β at M̄ ∈ {0.5, 1}.
- de Chaisemartin–D'Haultfœuille `did_multiplegt_dyn` over the whole panel, all switches on and off, as robustness.
- No two-way-fixed-effects event study is estimated.

### 5.3 Inference

- **RI (primary):** described in §3. The randomisation is conditional on the number of switchers per tier and event.
- **Party-level permutation (reported, coarse by design):** at each event the set of entering parties is replaced by
  a random set of equal size drawn from the parties that held at least one district mayor at the time. Switch vectors
  are rebuilt and the statistic recomputed over all such sets.
- **Conley–Taber:** co-primary interval, with the controls' residual distribution.
- **WCR** (Webb, B = 9 999) and **CR2** are reported, with the caveat that they are unreliable when few clusters are
  treated (MacKinnon and Webb 2018).

### 5.4 What can realistically be learned

- There are 30 switch-in units over two events, but only 4 entering parties. The design can detect a premium of
  about 100 % of a district's usual grants at 80 % power under the base scenario (§6), which is 2.5 times
  the upper literature benchmark (40 %) and 5 times the lower (20 %).
- A null result will not be informative: the ±20 % TOST has essentially no power (§6.2). The confirmatory test can detect only a very large premium.

## 6. Design-stage checks (covariates only; completed before registration)

Scripts:

- `tools/praha/districts_alignment.py`, output `docs/research/prague-districts-alignment.{csv,json}`;
- `tools/praha/districts_power.py`, output `docs/research/prague-districts-power.json`;
- `tools/praha/districts_grants.py --structure`, output `docs/research/prague-districts-grants-structure.json`.

### 6.1 Alignment counts per event (primary rule, 30 June)

| | 2018 event (2018 → 2019) | 2023 event (2022 → 2023) |
|---|---|---|
| up (0 → 1) | 10 | 24 |
| down (1 → 0) | 8 | 4 |
| always aligned | 7 | 10 |
| never aligned | 32 | 19 |
| unresolved | 0 | 0 |

- Switch-in units meeting the full-window rule (§5.1): 7 in 2018 and 23 in 2023. Clean controls:
  31 and 14.
- Mid-term switches outside the events: 12 (Praha 1 2020 (0→1); Praha 11 2017 (0→1); Praha 11 2024 (0→1); Praha 14 2021 (1→0); Praha 21 2016 (1→0); Praha 22 2021 (1→0); Praha 5 2020 (1→0); Praha 5 2025 (0→1); Praha-Klánovice 2025 (0→1); Praha-Křeslice 2025 (0→1); Praha-Velká Chuchle 2022 (1→0); Praha-Velká Chuchle 2024 (0→1)).
- Aligned districts on 30 June 2018 / 2019 / 2022 / 2023, under the three count-based rules (the fourth, the continuous seat share, has no count):
  - mayor (primary): 15 / 17 / 14 / 34;
  - seat majority: 9 / 8 / 8 / 22;
  - largest list with a coalition party: 18 / 23 / 23 / 32.
- For comparison, the referees found 12 / 22 / 22 / 34 aligned districts in 2022 under their four rules, and a
  2022 → 2023 split of 17 up, 3 down, 32 never and 5 always, from election files only.
  - Ours, on the mayor rule, is 24 up, 4 down, 19 never and 10 always.
  - The difference comes from the mayor's actual party, which the election files alone do not give.

### 6.2 Power on the real switch vectors

The simulation uses:

- outcomes in units of each district's own mean;
- standardised t innovations with ν ∈ {3, 5};
- SD ∝ (N / median N)^(−θ/2), θ ∈ {0, 0.5, 1};
- AR(1) with ρ ∈ {0, 0.3, 0.6};
- a zero-grant probability q ∈ {0, 0.2, 0.4};
- a coefficient of variation CV ∈ {0.5, 1, 2};
- 400 data sets × 999 permutations.

The base scenario is CV 1, ν 3, θ 0.5, ρ 0.3, q 0.2.

| scenario (change from base) | power at +20 % | +50 % | +100 % | MDE80, α = 0.025 | MDE80, α = 0.05 | size at 0.05 |
|---|---|---|---|---|---|---|
| base | 0.11 | 0.38 | 0.83 | 100 % | 100 % | 0.048 |
| CV = 0.5 | 0.17 | 0.67 | 0.99 | 75 % | 75 % | 0.040 |
| CV = 2.0 | 0.07 | 0.20 | 0.55 | 150 % | 150 % | 0.045 |
| ν = 5 | 0.10 | 0.38 | 0.82 | 100 % | 100 % | 0.050 |
| θ = 0.0 | 0.10 | 0.42 | 0.89 | 100 % | 75 % | 0.045 |
| θ = 1.0 | 0.09 | 0.33 | 0.79 | 150 % | 100 % | 0.037 |
| ρ = 0.0 | 0.12 | 0.43 | 0.88 | 100 % | 75 % | 0.065 |
| ρ = 0.6 | 0.13 | 0.40 | 0.84 | 100 % | 100 % | 0.055 |
| q = 0.0 | 0.15 | 0.57 | 0.96 | 75 % | 75 % | 0.050 |
| q = 0.4 | 0.10 | 0.26 | 0.70 | 150 % | 150 % | 0.058 |

Power columns: one-sided RI at α = 0.025 (Holm's first step). Effects are proportional premiums on a district's usual city grants.

- Smallest attainable p: 0.001. There are 2.2e+15 distinct within-stratum assignments, so the bound is set by the number of draws (1/1 000 here; 1/10 000 at estimation).
- TOST power at margin ±20 % with no true effect: at most 0.003 in every scenario, i.e. essentially zero.

**Pre-committed consequences:**

- **Result.** In the base scenario, the minimum detectable effect at 80 % power is a premium of about 100 % of a
  district's usual city grants (75–150 % across scenarios). The upper literature benchmark is 40 %, and power at a
  20 % premium is about 0.1.
- **H1 is therefore declared underpowered for effects of the size found in the literature.** The article says so in
  its first section. A non-rejection is reported as "not detected", never as "no premium".
- **The TOST at ±20 % has essentially zero power.** The margin is kept, because it was chosen on substantive
  grounds. A null H1 will therefore be reported as "inconclusive", with its interval drawn against the ±20 % band
  and the 20–40 % benchmark.
- **Size.** The RI test holds its level in every scenario (0.04–0.065 at a nominal 0.05, with 400 simulations).
- **H2 is not simulated separately.** It splits the same switchers into two components, and the intersection–union
  rule is at least as conservative, so it is underpowered by construction.

### 6.3 Covariate balance (for the MONITOR secondary, 2023 event)

Population growth 2015–2021, the 0–14 and 65+ shares, and 2018 seat shares by party, for switchers against
controls, with RI p-values. If population growth is imbalanced at p < 0.1, it is added as a covariate.
**Computed at estimation, from covariates only.**

## 7. The formula channel (descriptive)

- For 2020–2023, the residual of each district's approved finanční vztah from the published criteria, where the
  table gives them, is related to alignment. Descriptive only.
- The 2024 formula change (adopted 14 Dec 2023 by the new coalition) is reported as a separate "formula-level
  alignment channel". The changes it made to each district's allocation are compared by alignment. Descriptive; no
  test.

## 8. Robustness (reported, not in the family)

1. Per-resident scaling; log(1 + Y).
2. Robustness alignment rules (§4.5).
3. Dropping interregnum grants; dropping the regime-years adjacent to each event (2018, 2019 and 2022, 2023).
4. Population denominators with the 2021 stock held.
5. Including always-aligned districts as controls.
6. Without Praha 1; without districts under 1 000 residents.
7. Leave one district out; leave one party out (all districts whose mayor's party is P).
8. dCDH `did_multiplegt_dyn`; HonestDiD.
9. MONITOR secondary outcome, 2023 event (one pre year): D, D net of 5347, with the covariate balance of §6.3.
10. **Placebo event:** a pseudo-event at 2020/21, with the same window rules and no coalition change.
11. **Specification curve** over:
    - {R_2016 scaling, per resident, log};
    - {mayor, seat majority, largest list};
    - {with, without interregnum};
    - {all, without Praha 1, without < 1 000};
    - {RI, CT, WCR, CR2}.

## 9. Limitations and framing

- **Party-level treatment.** The effect of alignment cannot be separated from what else happened to one party's
  districts (§2).
- **What the lists contain.** The city can also favour a district by building there itself or through its
  companies. The lists measure one channel.
- **The bridge between list formats** in 2024–2025 (§4.2).
- **Coding error** in who was mayor: minimised by double coding, but not zero.
- **Framing (registered):**
  - neutral words only: "alignment premium", "in-year grants to aligned districts". Never "favouritism", "pork" or
    "clientelism";
  - parties are named only as coalition membership, with the statement that the design cannot separate party from
    alignment;
  - no per-district table of the outcome next to party labels;
  - named individuals only as counts (E2).

## 10. Response to referees

Items refer to `docs/research/prague-districts-referees.md`.

- **§0, cells seen.** Recorded in §0.3. The author's own exposures are in §0.2–0.4.
- **§1, data foundation.**
  - MONITOR from 2022 only: accepted, and MONITOR becomes the secondary source (§4.4).
  - Closing-account lists, allocation tables and PVSS annexes: downloaded (820 MB, 535 linked files, 3 of them missing on the portal, hashed) and parsed
    for structure (§4.2).
  - **Differences from the audit:**
    - allocation tables start in **2016**, not 2015: the 2015 page has no attachments;
    - the 2024 and 2025 lists are drawdown-only, as the audit said, and the bridge rule is registered;
    - the 2014 list parses as text, but it lies outside every window and stays excluded.
  - Formula regimes, items, consolidation, elections (wards, court decisions, new elections) and population
    definitions: adopted in §1, §4.4 and §4.5.
    - In the register, the 2014 Praha 13 and 2018 Praha 8 court records have the same party seat totals as the
      originals. Praha 4 2018 differs, and the latest record per assembly on or before 30 June is used.
- **§2.1 scope.** Adopted: the 2015–2025 grantor-side panel; MONITOR secondary.
- **§2.2 primary outcome.** Adopted: own grants, excluding state ÚZ and operational programmes, split
  investment / non-investment, dated by resolution, scaled by the base-year allocation, per resident secondary.
  - The base year is 2016, the first table. Blind validation against MONITOR is registered (§4.4).
- **§2.3 events.** Adopted, with Part 1's dates. The interregnum is flagged, kept in the primary outcome and dropped
  in robustness. No TWFE; stacked design with clean controls; leads, joint pre-trend test, HonestDiD.
- **§2.4 estimands.** Adopted. Switch-in is H1; switch-out is descriptive; the party-level caveat is stated in §2.
- **§2.5 inference.** Adopted: RI within tier × baseline alignment with a studentised statistic, the smallest
  attainable p, the party-level permutation, Conley–Taber co-primary, WCR and CR2 alongside.
- **§2.6 alignment measure.**
  - Adopted, with one change: the mayor's party is primary, because 35 small districts have no rada. The coding is
    double and blind, with sources, frozen and hashed (§4.5).
  - Robustness rules and their counts are in §6.1.
- **§2.7 family.** Adopted: {H1, H2} with Holm; H2 intersection–union; H3 and H4 out of the family.
- **§2.8 covariate balance.** Adopted for the MONITOR secondary (§6.3).
- **§2.9 formula channel.** Adopted (§7).
- **§2.10 denominators.** Adopted (§4.3).
- **§2.11 refugee pass-throughs.** State ÚZ are excluded from the primary outcome, so the 2022 refugee money is not
  in it. They remain in the MONITOR secondary, and the 2022 pre-year of the 2023 event is flagged.
- **§2.12 power.** Adopted and run (§6.2). The benchmark is registered (§2), and was corrected after the audit.
- **§2.13 equivalence.** Adopted: TOST at ±20 % (§3).
- **§2.14 literature.** Added. Volumes and pages checked against Crossref on 30 Sep 2026.
- **§3, the Part 3 correction.** Done first, on its own branch, before this analysis touched any grant amount. The figures it
  changed are recorded in §0.2.
- **§4 framing.** Adopted (§9).

## 11. Deliverables

- `tools/praha/districts_data.py`: MONITOR, population, elections, RÚIAN (v1).
- `tools/praha/districts_city.py`: closing accounts, approved budgets, proposals; `city/manifest.csv`.
- `tools/praha/districts_grants.py`: the grant lists. `--structure` only, until registration.
- `tools/praha/districts_alignment.py`: the frozen alignment.
- `tools/praha/districts_power.py`: §6.2.
- `tools/praha/districts_extended.py` and `districts_robust.py`: after registration.
- `assets/praha/districts_extended.json` and `texts/prague-districts-study.html`.

## References

As in v1, plus:

- Baskaran, T., Hessami, Z. (2017): Political alignment and intergovernmental transfers in parliamentary systems:
  evidence from Germany. Public Choice 171(1–2), 75–98.
- Cengiz, D., Dube, A., Lindner, A., Zipperer, B. (2019): The effect of minimum wages on low-wage jobs. Quarterly
  Journal of Economics 134(3), 1405–1454.
- Curto-Grau, M., Solé-Ollé, A., Sorribas-Navarro, P. (2018): Does electoral competition curb party favoritism?
  American Economic Journal: Applied Economics 10(4), 378–407.
- de Chaisemartin, C., D'Haultfœuille, X. (2026): Difference-in-differences estimators of intertemporal treatment
  effects. Review of Economics and Statistics 108(4), 863–880.
- Fiva, J. H., Halse, A. H. (2016): Local favoritism in at-large proportional representation systems. Journal of
  Public Economics 143, 15–26.
- Kauder, B., Potrafke, N., Reischmann, M. (2016): Do politicians reward core supporters? Evidence from a
  discretionary grant program. European Journal of Political Economy 45, 39–56.
- MacKinnon, J. G., Webb, M. D. (2020): Randomization inference for difference-in-differences with few treated
  clusters. Journal of Econometrics 218(2), 435–450.
- McKenzie, D. (2012): Beyond baseline and follow-up: the case for more T in experiments. Journal of Development
  Economics 99(2), 210–221.
- Migueis, M. (2013): The effect of political alignment on transfers to Portuguese municipalities. Economics &
  Politics 25(1), 110–133.
- Muraközy, B., Telegdy, Á. (2016): Political incentives and state subsidy allocation: evidence from Hungarian
  municipalities. European Economic Review 89, 324–344.
- Rambachan, A., Roth, J. (2023): A more credible approach to parallel trends. Review of Economic Studies 90(5),
  2555–2591.
- Wu, J., Ding, P. (2021): Randomization tests for weak null hypotheses in randomized experiments. Journal of the
  American Statistical Association 116(536), 1898–1913.

## Appendix A. Raw files

SHA-256 of every raw file in `tools/data/praha3x/`, in `docs/research/prague-districts-files.sha256`. The derived
text dumps (`city_txt/`) are excluded.

## Changes after registration

### 29 September 2026, before any outcome was joined: parser, bridge and investment split

Built by `tools/praha/districts_grants.py` in `--structure` and `--bridge` mode. The counts are in
`docs/research/prague-districts-grants-structure.json`, and the bridge statistic in
`docs/research/prague-districts-bridge.json`.

**Parser coverage (§4.2 rule: at least 97 %).** The share of amount-bearing item lines that were parsed, in the
lists the design uses:

| List | Years | Coverage |
|---|---|---|
| city's budget measures (5.3; 5.4 in 2015) | 2014–2023 | 0.9947–1.000 |
| drawdown 5.5 (for the bridge) | 2019–2023 | 0.9796–0.9986 |
| drawdown 2024 (5.2) | 2024 | 0.9975 |
| drawdown 2025 (5.2.1) | 2025 | 0.9923 |

The rule is met in every list. City-own rows per year range from 646 (2025) to 2 099 (2022). All 57 districts
appear in every year. Changes to the parser, all made on structure, with amounts masked:

- **Recognised forms:**
  - resolution forms "Z 8/45", "R 1092", "R 3170 bod 2" and "2M/34";
  - ÚZ with a ZJ suffix ("137/100") or zero padding ("000000081");
  - the settlement markers "xx", "-" and blank;
  - "MČ" before a district, short or abbreviated district names ("Kopanina", "Dol. Měcholupy", "D. Měcholupy",
    "Průhonic"), and one typo ("Śtěrboholy");
  - in 2017, six rows name a district by the city's 1–57 index ("Praha 37"). They are mapped with the order of the
    allocation tables, read from the name column only.
- **The 2025 layout:** district blocks ("MČ Praha 1"). The row carries RO, purpose, [ORG], ÚZ and five amounts in
  CZK; the resolution sits inline or on the lines above.
- **2024:** the lists are reprinted in the resolution file, which is skipped.

**Outcome rule made explicit (§4.3 said "the city's own grants").** A row is counted if both of these hold:

- its ÚZ is a number from 1 to 999;
- its RO is outside the year-end settlement series 8000–8999.

This excludes rows with no ÚZ, "-" or "xx": the settlement of the previous year, local-fee top-ups, refunds, and the
"additional financial relationship" paid to every district in 2022. It also excludes state ÚZ (98xxx, 1xxxx, 3xxxx
and longer codes). The rule was decided on row labels, before any amount was summed.

**Amount per row:**

- budget-measure lists: the value in the 4137 / 4251 column (the last amount on the line; the city-side 5347 / 6363
  copy is equal);
- drawdown lists: the first column, the budget adjustment.

*[30 Sep 2026: the "copy is equal" premise above was wrong. The two column pairs are two directions of money. See
the audit entry at the end.]*

**Dating (§4.2).**

- ZHMP resolutions resolve to Part 1's session dates, except 30 rows in the 2020 list and 7 in the 2018 list.
- Rows without a resolvable resolution take the date of the nearest dated RO in the same list. This covers 0–92
  rows a year: at most 6 % of city-own rows in 2014–2024, and 14 % in 2025.
- Every city-own row has a date.

**Investment split (§3, H2 fallback).**

- Every list in every year has a "b) Investiční" subsection against "a) Neinvestiční", including 2014 and
  2016–2019, where the column header shows only 4137 / 5347.
- In 2020–2023 the 4251 / 6363 column is used where the header has it. It disagrees with the subsection on no
  city-own row. The disagreements seen, 119–171 a year, all lie in the excluded 8xxx settlement block.
- 2015's combined list is not separable. 2015 lies outside both event windows.
- **So the pre-2020 split exists for 100 % of city-own rows in the event windows, and under the registered rule H2
  uses both events.**

**Bridge (§4.2).**

- Lin's concordance between the city's budget-measure list (5.3) and its drawdown list (5.5), summed by district and
  list year for 2019–2023: **0.7246 on 285 cells**, below the registered 0.9.
- **Registered consequence, applied:** the post window of the 2023 event is regime-year 2023 only (ℓ = 0). The
  2024–2025 drawdown lists are not used for H1 or H2.
- The event-study lags +1 and +2 for 2023 (from the drawdown lists) are reported descriptively and marked as such.
- The pre-join note: the two lists differ by construction. The budget-measure list records each measure including
  returns; the drawdown list records current-year grants at their adjusted budget. The rule was fixed before the
  check and is applied as written.

**Also seen during this step (§0 addendum).** One unmasked line of the 2025 drawdown list was printed while learning
the layout: the "CELKEM MČ Praha 1" total row, with its five amounts (adjusted budget, provided, returned, drawn,
remaining). The 2023 event's window now ends in 2023, so that 2025 row is not part of H1.


### 29 September 2026, estimation (after outcomes were joined)

Built by `tools/praha/districts_extended.py` and `districts_robust.py`. Output is in
`assets/praha/districts_extended.json` and `districts_extended_robust.json`.

**A measurement correction found after outcomes were visible.** The first run gave the city's own grants in
regime-year 2023 as 24.6 m CZK, against 3–6 bn CZK in every other year, and an investment share above 1.

- **Cause.** The 2023 list prints each amount in the city-side column (5347 / 6363) and 0,00 in the district-side
  column (4137 / 4251). The parser took the last amount on the line.
- **Fix.** The rule became the last non-zero amount on the line.
  - The rule recorded before joining (commit `7be2ad5`) read: "the value in the 4137 / 4251 column (the last amount
    on the line; the city-side 5347 / 6363 copy is equal)".
  - The fix was prompted by the implausible 2023 total (25 m CZK against 3–6 bn in every other year), not by the
    direction or size of H1.
  - *[Corrected 30 Sep 2026: an earlier version of this entry misquoted the pre-join rule as "…or 5347 / 6363 where
    only the city's side is printed".]*
  - Other years: 2016–2021 are unchanged, and 2015 changes by +0.07 %.
  - 2022 changes by +4.9 %, because regime-year 2022 includes 1 Jan – 15 Feb 2023 grants from the 2023 list.
- **Effect.** H1 moved from +0.33 R (+19 % of the controls' usual level, RI p = 0.21) to −0.70 R (−38 %,
  p = 0.74). Almost all of the change comes from this fix. Both runs are reported. The first was wrong, because its
  2023 outcome was near zero for every district.

**Implementation choices the registration left open:**

- **Relative effect:** the pooled estimate divided by the unweighted mean, over the two events, of the controls'
  pre-window level.
- **TOST:** randomisation inference, with the switchers' Δ shifted by ± the margin. The margin m is 20 % of that
  mean, 0.36 R.
- **Regression form (CR2 and WCR):** the stacked model with unit×event and year×event effects, 47 district clusters.
  The CR2 reference distribution is t(G − 1).
- **Conley–Taber:** 20 000 draws of the controls' demeaned Δ.
- **HonestDiD:** a simplified relative-magnitudes interval. The bound is M̄ × the largest pre-period change of the
  switcher–control difference, added to a ±1.96 SE interval. The sampling noise in the bound is ignored. This is
  simpler than Rambachan and Roth's optimal interval.
- **Placebo event:** the 2023 stack's units, pre 2019–2020 and post 2021–2022. That is two years on each side,
  because a three-year pre window would reach the 2018 event.
- **de Chaisemartin–D'Haultfœuille:** DID_M and the joiners-only DID_+ over 2015–2023, implemented directly, with a
  district bootstrap of 999 draws. The R/Stata package was not used.
- **Party-level permutation:** at each event the entering set is replaced by every equal-size set of parties that
  held a mayor on 30 June of the first post year. That gives 10 options in 2018 and 2 in 2023, 20 sets in all.
  Mayors' parties come from coder A's spells, which match the adjudicated panel wherever the two coders' mayor
  agrees.
- **Power.** The simulation (§6.2) assumed a 2023 post window of 2023–2025. After the bridge rule, the window is
  2023 alone, and the 2023 stack has 23 switch-ins and 17 clean controls. The design-stage minimum detectable effect
  is therefore, if anything, optimistic for the realised design.
- **MONITOR secondary:**
  - window 2022 (pre) and 2023–2025 (post): 24 switch-ins, 15 controls;
  - population growth 2015–2021 was imbalanced (RI p = 0.098), so the rule of §6.3 applied. The estimate adjusted
    for it (residualised on growth, fitted on the controls) is reported;
  - the 0–14 share was also imbalanced (p = 0.066). The registered rule names population growth only, so the 0–14
    share is not added.
- **H3:** capital execution = MONITOR class 6 reality / afterChanges. No district-year had a zero amended capital
  budget.
- **H4 variants:** net of D (the unbudgeted in-year 4137 + 4251), and net of approved 5901 reserves. Class 8 is not
  netted: the gap is defined on incomes minus outgoings, which excludes financing.
- **Formula channel:**
  - the 2024 rule change is reported as the change in each district's approved allocation from 2023 to 2024, by
    2024 alignment;
  - the 2020–2023 floor/cap adjustment is computed but **not interpreted**. Its "final" column includes the pupil
    top-up (DFVz) in 2023 but not in 2020, so the years are not comparable.
- **E1–E4 were not run** in this version. They were exploratory and remain so.
- **The specification curve** uses 999 permutations and 999 WCR draws per specification, 54 specifications.
  - WCR and CR2 are computed only for the full sample (18 specifications).
  - Dropping Praha 1 changes nothing: it is in neither stack.


### 30 September 2026, after an independent audit (outcomes known)

The audit reproduced H1 (−38.3 %, RI p = 0.7386) with the code of `d8270ac`/`7171ea7`. It checked about 40 alignment
spells against official sources, all of which match the registered rule, and it confirmed that the parsed amounts
match the PDFs. It also found the problems below. Every item is a post-outcome correction, and each one is reported
with its effect.

**1. Direction of flows (the main correction).**

- In the budget-measure lists, 5347 / 6363 is the city's expenditure, i.e. the city paying the district. 4137 / 4251
  is the city's income, i.e. the district paying the city: loan repayments ("splátka NFV", "přijetí mimořádné
  splátky"), returned grants ("vratka dotace") and transfers from districts. They are not copies of each other, as
  the pre-join rule and the parser assumed.
- The parser now assigns every amount to its column, as follows:
  - **by order,** where a line prints every column (most do, with 0,00 in the empty one);
  - **by the positions learned from such lines,** otherwise. Amounts are right-aligned and offset from their header
    codes, so matching by header position alone put some 6363 amounts under 4251 in 2023.
- The city's own grant is the 5347 / 6363 amount. A 4137 / 4251 amount is a district-to-city flow, kept separately
  and excluded from the outcome: 162 rows and 1.12 bn CZK in 2016–2023. The audit counted 164 rows and 1.11 bn.
- The 2015 list exists only as a .docx rendition without column layout, so its single-amount lines are treated as
  city-to-district. 2015 lies outside both event windows.
- A sign-flip variant (city-to-district minus district-to-city) is reported as robustness.

**2. Dating by resolution.**

- The first version kept one date per session number. Sessions continue over several days: the 2022-term session 1
  sat on 3 Nov, 24 Nov and 15 Dec 2022 and on 16 Feb 2023, and session 10 of 2015 sat on 22 Oct, 5 Nov and 26 Nov.
- ZHMP resolutions are now dated by the exact resolution number in the roll-call files, then by a session that sat
  on a single day in the list's year, and otherwise by the RO order in the same list.
- Effect:
  - 112 rows (208 m CZK) approved on 16 Feb 2023 move from regime-year 2022 to 2023;
  - 117 rows (324 m CZK) approved on 22 Oct and 5 Nov 2015 get their own dates;
  - 258 of 10 390 city-own rows are dated by RO order (1.2–6.2 % a year).

**3. Results after corrections 1 and 2.**

- **H1:** −0.640 R = **−37 %** of the controls' usual level. RI p = **0.704**; 95 % Conley–Taber −115 to +21 %.
- **H2:** investment −39 %, non-investment +2 %. p = **0.759**.
- **Holm:** neither rejected.
- **The three runs,** for the record:

  | Run | Commit | H1 | RI p |
  |---|---|---|---|
  | first | before `d8270ac` | +19 % | 0.21 |
  | second | `d8270ac` | −38 % | 0.74 |
  | third | this commit | −37 % | 0.70 |

- **The TOST sides are now reported:**
  - H0 premium ≥ +20 %: p = 0.108. A 20 % premium is not ruled out.
  - H0 effect ≤ −20 %: p = 0.531.
- **Bridge statistic.** Recomputed with the corrected parser for disclosure only, it is 0.795. It is still below 0.9,
  and the registered decision, taken before outcomes, stands.

**4. Outcome composition, disclosed, with a robustness check added.**

- Of the city-own grants, 20–39 % a year in 2016–2023 (57 % in 2015) is not discretionary in the usual sense:
  - ÚZ 99, income-tax refunds passed to districts: 11–28 %;
  - ÚZ 98, shares of the gambling levy: 4–10 %;
  - ÚZ 8, repayable loans (NFV): 1–13 %; 13 % in 2019.
- The outcome rule (ÚZ 1–999) includes them, and the article's statement that refunds are left out was wrong.
- Without ÚZ 8, 98 and 99: −43 %, p = 0.71. The audit got −44 %, p = 0.68.

**5. Robustness added or rebuilt:**

| Check | Result |
|---|---|
| Praha 10 in 2022 coded by its acting head (Piráti) | −36 % |
| interregnum dated from the recalls of 22/23 Oct 2015 | −38 % (the same as from 10 Nov) |
| alignment rule "coders' own membership", rebuilt | −36 % (p = 0.66) |

- The previous version of the membership rule fell back to the registered rule whenever the coders disagreed or a
  mayor was a non-member, so it was identical by construction. It now uses a single agreed membership where one
  exists (535 district-years): a recorded non-member is unaligned even if nominated by a coalition party. This
  changes 38 district-years.
- **Leave one district out.** Dropping Praha-Troja, unaligned throughout and so a control in both events, moves the
  estimate from −37 % to about 0 %. No other district moves it by more than 9.4 points. The earlier article's "no
  single district decides it" was wrong.
- **Specification curve.** The "without Praha 1" samples duplicated "all" (Praha 1 is in no stack) and are removed,
  leaving 36 specifications. WCR and CR2 are now computed for every one, not 18.
- **Random streams.** Each block now draws from its own fixed random stream. Adding the switch-out block had moved the
  MONITOR balance p-values.

**6. Reported now, registered but missing before:**

- HonestDiD at M̄ = 0.5 (−131 to +57 %) as well as 1 (−143 to +69 %), still the simplified interval.
- Switch-out: −7 %, p = 0.50. That is 8 units in 2018 and 4 in 2023, against 6 and 10 always-aligned districts.
- The 12 mid-term switches and the always-aligned counts (7 and 10).
- The smallest attainable p: 0.0001.

**7. MONITOR covariate adjustment.** With 9 999 permutations, the population-growth balance is p = 0.113, so the
registered adjustment (p < 0.1) is **not** triggered. The earlier run used 1 999 draws, got 0.098 and applied it. The
adjusted estimate is reported either way:

| Estimate | Per resident a year | p |
|---|---|---|
| unadjusted | −2 128 CZK | 0.77 |
| adjusted | −2 196 CZK | 0.77 |

The 0–14 share (p = 0.086) is not named by the registered rule and is not added.

**8. Literature benchmark corrected** (§2). Bracco et al. were misstated as 10–20 %. The benchmark is now "roughly a
third to a half more", with Germany's sign depending on the bloc.

**9. Not done:**

- the alignment check against every constituent-session resolution (about 40 spells were checked against official
  sources by the audit);
- E1–E4.

**3 October 2026 (audit).** Several notes in this file are dated 30 September 2026; the commits that carry them are of 29 September 2026, which is the correct date. The corrected-parser Lin concordance (0.795, reported above as disclosure only) is not in `prague-districts-bridge.json`, which keeps the registered 0.7246.

**5 October 2026.** Wording only: statements that no amount was read or touched are scoped to this analysis and this design. The author had worked with these data for a long time before the plan was committed. The plan sets the analysis in advance; the author already knew the data. No number, estimate or result changed.
