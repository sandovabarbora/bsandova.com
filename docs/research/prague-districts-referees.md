# Part 3 districts: referee reports on design draft v1 (28 Sep 2026), consolidated

Three referees: public finance and political economy, statistics, and data audit. Their must-fix points are merged
below, and the data audit changes the design's foundation.

## 0. Outcome cells seen by referees (record in §0)

- **Data referee, by accident.** MONITOR totals nodes for Praha 1 2023 and Praha 4 2023; for Praha 2 and Praha 3 2019,
  item 4137 approved / amended / actual from the closing-account PDF; city totals for 4137 and 5347 in 2019.
- **Statistics referee.** Rough alignment counts for 2022→2023, from election files only (no budgets): 17 up-switchers,
  3 down-switchers, 32 never aligned, 5 always aligned. 15 of the 17 up-switchers switch because the coalition changed
  (ODS in, Praha Sobě out), not because of the election.
- **Public-finance referee.** Checked that the published three-year-mean income shares sum to 0.91–1.00 of total
  income.

## 1. The data foundation changes (data referee)

- **MONITOR.** District data exist only from 2022, because Decree 5/2014 as amended in 2022 makes the reporting annual
  and starts it with 2022. This is confirmed.
- **The city's closing accounts** (https://praha.eu/zpravy-o-plneni-rozpoctu, DZ III) give:
  - **A.** Per-district budget statements for 2016–2021 in text (57/57), with items 4137, 4251 (from 2020), 5347, 4121,
    4122, 4131+4132, classes and financing. 2015 is partly scanned; 2014 needs OCR.
  - **B.** Per-grant lists by district for 2014–2025. Each grant carries its budget measure, the RHMP/ZHMP resolution,
    the purpose code ÚZ, the chapter, the purpose, the amount and a non-investment (a) / investment (b) split. The lists
    are grouped by source: 5.2 state pass-throughs (ÚZ 98xxx), 5.3 the city's own grants, 5.4 operational programmes,
    5.5–5.6 drawdown. The format changes in 2024–2025, when only the city-grant drawdown lists remain. The file slugs
    per year are in the data report.
  - **C.** Allocation tables, "Finanční vztahy k MČ", for 2015–2025 (xls/xlsx), from https://praha.eu/rozpocet-a-jeho-plneni.
    PVSS annexes for 2021–2025. The year-end settlement is annex 7/8 of each closing account.
- **Formula regimes.**
  - 2015–2019: 30 % of personal-income-tax yield, then criteria 30/10/30/20/10 (different weights for districts 23–57 in
    2015), with floors and caps.
  - 2020–2023: 30/10/30/20/10, floor/cap 3 000/5 500, raised to 3 500/6 000 in 2023.
  - **2024–2025: a new rule** (last year's actual plus a top-up tied to the tax forecast), adopted on 14 Dec 2023 by the
    new coalition. The 2023 allocation was adopted on 15 Dec 2022, by the old council.
- **Items.**
  - All state transfers arrive through 4137/4251 (the 411x/42xx items are absent in district reports), so only ÚZ codes
    separate state money from city money.
  - 4251 exists only from 2020, and its approved value is 0 in 228/228 district-years.
  - `finalBudget` is always 0: drop it.
  - 5347 returns flow in 226/228 district-years.
  - 5901 reserves are approved in 136/228 and are never spent.
- **Consolidation.** The totals node is the unconsolidated sum. 4131 (in 48–51 districts a year) is mostly net income
  from business activity (rents), since 5341 appears in only 21 district-years, so it is own revenue, not a transfer.
- **Elections.**
  - 2014, 2018 and 2022 compositions are buildable. Sum seats over wards (Praha 9 in 2014 and 2018, Praha 4 in 2014).
  - Praha 13 (2014), Praha 4 and Praha 8 (2018) are court decisions, not elections. Praha 4's seats changed
    (ANO 7→8, Společně 6→5).
  - Koloděje 2015 and Nedvězí 2016 and 2019 are genuine new elections.
  - Rule: the latest record per assembly dated on or before 30 June of year t.
- **Population.**
  - Rebased on the 2021 census.
  - **From 31 Dec 2022 it includes temporary-protection holders.** That definition break falls at the treatment date.
  - 2025 is preliminary.
  - The allocation itself uses 1 Jan of t−1 (the Interior Ministry register in 2025).

## 2. Design changes required

1. **Scope.** Build the 2015–2025 grantor-side panel from the closing-account grant lists. Exclude 2014 unless OCR
   succeeds. The confirmatory H1 is estimated on this panel. The 2022–2025 MONITOR design becomes a secondary check.
2. **Primary outcome.** The city's own grants to district i in year t:
   - excluding state ÚZ 98xxx and operational programmes;
   - split into investment and non-investment;
   - **dated by resolution date**, so grants in Jan–Feb 2023 decided by the caretaker council belong to the old regime;
   - scaled by the district's allocation R_i from the allocation table in a fixed base year (not per resident), with per
     resident as secondary.

   Secondary: MONITOR reality minus approved of 4137+4251, for 2022–2025, with a variant net of 5347. Validate the
   parsed lists against MONITOR for 2022–2023 **blind**: publish only an agreement statistic.
3. **Events.** Coalition switches with dates from Part 1's sources (docs/research/prague-council-sources.md):
   - Nov 2018: Piráti + Praha sobě + Spojené síly replace ANO + ČSSD + Trojkoalice.
   - Feb 2023: SPOLU + Piráti + STAN.
   - The 2015–16 crisis (coalition declared dead 10 Nov 2015, renewed 28 Apr 2016) as an interregnum.

   Switches turn on and off, so use no TWFE and no TWFE event study. Use de Chaisemartin–D'Haultfœuille
   (did_multiplegt_dyn) or a stacked design by event (Cengiz et al. 2019) with clean controls. Leads −3…−1 with a joint
   pre-trend test; HonestDiD sensitivity (Rambachan–Roth) at M̄ ∈ {0.5, 1}.
4. **Estimands.** H1 = the switch-in effect (becoming aligned), relative to districts whose status did not change.
   Switch-out is descriptive if its units are few. Say explicitly that switches are *party-level* (in 2023, essentially
   ODS entering), so the alignment effect cannot be separated from shocks shared by that party's districts. The number
   of independent treatment changes is the number of parties that switched.
5. **Inference.**
   - Randomization inference within strata of tier × baseline alignment, holding the switcher count per stratum fixed,
     with a studentised statistic (Wu & Ding 2021).
   - Report the smallest attainable p-value.
   - Add a party-level permutation: which parties enter or leave, among those holding district mayors. It is coarse, and
     that is the point.
   - Co-primary interval: Conley–Taber.
   - Reported alongside: WCR and CR2.
6. **Alignment measure.**
   - **Primary: the parties on the district council (rada), or the mayor's party, in the city coalition C_t.**
     Hand-code it for every district-term with sources, double-coded blind, and freeze and hash the coding before any
     outcome is joined.
   - Robustness: seat majority by NSTRANA ∪ PSTRANA, whatever the list's name; a list containing a coalition party; a
     continuous seat share. Report the counts under each rule. They differ a lot: 12 / 22 / 22 / 34 districts under
     four rules in 2022.
7. **Family.**
   - Confirmatory {H1, H2}, Holm.
   - H2 = the investment share of the premium, tested intersection–union: β_cap > 0 and β_cap − β_cur > 0.
   - H3 (capacity; two-sided, exploratory) and H4 (surpluses; descriptive, with D and 5901/class 8 netted out as
     variants) leave the family.
8. **Covariate balance instead of outcome pre-trends** (for the 2022–25 secondary): population growth 2015–21, age
   shares and 2018 party seat shares, with RI p-values. If population growth is imbalanced at p < 0.1, add it.
9. **Formula channel.** Replace §7.9 with the allocation-table residual for 2020–2023, descriptive. Report the 2024
   formula change as a separate, descriptive "formula-level alignment channel".
10. **Denominators.** 1 Jan of t−1, matching the allocation. Flag the break at 31 Dec 2022 (temporary protection).
    Robustness: hold the 2021 stock.
11. **Refugee pass-throughs.** These are 2022 state money through 4137. Excluding state ÚZ removes them from the
    primary outcome. Say so.
12. **Power.** Simulate on the real strata and switch vectors, with heavy tails (t with ν = 3 or 5), variance ∝ N^−θ,
    AR(1) and lumpy grants. Pre-register the literature benchmark (Solé-Ollé & Sorribas-Navarro 2008; Bracco et al.
    2015), converted to % of grants [verify], now.
13. **Equivalence bound for H1** (TOST), so that a null result is informative.
14. **Literature.** Add Migueis 2013; Curto-Grau, Solé-Ollé & Sorribas-Navarro 2018; Baskaran & Hessami 2017
    (Germany, parliamentary coalitions); Kauder, Potrafke & Reischmann 2016; Fiva & Halse 2016; Muraközy & Telegdy 2016;
    MacKinnon & Webb 2020; McKenzie 2012. Mark all [verify]. Cite Drazen & Eslava and Veiga & Veiga only for H2's
    premise.

## 3. The Part 3 correction (do FIRST, separately, blind to H1)

The published Part 3 counts 4131/4132/4140 as transfers, and says the totals are consolidated. They are not.

- **Separate branch from main:** `docs/PRAHA-3_transfer-label-fix`.
- **Code** (`tools/praha/districts.py`): transfers = class 4 minus items 4131, 4132, 4140; 4131 goes to own non-tax
  revenue. The script reads only those three items and never selects 4137/4251 by code.
- **Change only the three-year means already published.** These are:
  - the transfers share;
  - the transfers per head;
  - the median/range tile;
  - figure 2;
  - the table column;
  - the Praha 1 sentence (it may not survive).

  Add no per-year values, no city/state/EU split, and do not print 4137/4251.
- **Replace the sentence "The totals are consolidated…"** with "Income and spending include the money a district moves
  between its own accounts; own-fund transfers (items 4131, 4132, 4140) are counted as the district's own revenue, not
  as transfers."
- **Dated correction note at the end:**
  > "Correction, 28 September 2026. The first version counted as transfers from the city and the state the money a
  > district moves into its budget from its own funds, mostly business income (items 4131, 4132 and 4140), and gave
  > [old figures]. The figures above exclude them."
- Record in the design's §0 exactly what the correction revealed.
- **Stop after committing on that branch.** The coordinator reviews and deploys.

## 4. Framing

- Neutral words only: "alignment premium", "in-year transfers to aligned districts". Never "favouritism", "pork" or
  "clientelism".
- Name parties only as coalition membership, and say the design cannot separate party from alignment.
- No per-district table of the outcome next to party labels. Named individuals only as counts (E2).
- Before publication, the alignment coding is checked against official resolutions.
