# If the licence fees are replaced by the state budget: what do Czech Television and Czech Radio get, and who pays? — research design

**Status: pre-specified analysis, design committed 3 November 2026, before any outcome table was opened.** A descriptive
accounting comparison with registered rules; it makes no causal claim. The steps follow in dated commits: design →
data snapshot (files fetched and hashed, outcome tables unopened) → code (tagged before it opens them) → results. Commit
times are self-reported; the signed tag `fees-design` fixes this text. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The bill and the law.** On 3 November 2026 the drafting assistant read the text of the government bill (Sněmovní
  tisk 231/0, including the explanatory report), the stage page of the bill, the current text of act 348/2005 Coll.
  (version 14, in force from 1 January 2026) and act 243/2000 Coll. (version 17, in force 29 August 2026 – 31 December
  2027). They are legal texts, not outcome data. What they say is quoted in §2; the points where they differ from the
  figures first brought to this design, or are unclear, are in §2.6 and are open items, not guesses.
- **Outcome data: none opened.** No ČSÚ income-and-living-conditions (SILC) decile table, no ČSÚ household consumption
  table, no state-budget outturn by tax, no ČNB forecast number, and no fee-revenue table of Česká televize (ČT) or Český
  rozhlas (ČRo) has been opened for this study. One figure was in hand before registration: **ČT's fee revenue of
  6.73 bn CZK in its 2026 budget document** (as brought to this design); it is a baseline input (§1, Q-A), not an
  outcome, and its relation to the 5.742 bn CZK of 2024 in the bill is unexplained (§2.6). ČRo's 2026 figure has not
  been read. The bill's own amounts are quoted from the bill.
- **A press claim** that seniors pay about 40 % of fee revenue has been heard by the author; its source is not recorded
  here and it is not asserted (§1, Q-B).
- **The coalition proposal of May 2026** (further exemptions for people aged 75+, holders of ZTP cards and firms of up
  to 50 employees) is known to the author. It is a separate proposal and is not modelled (§8).
- **Position of the author.** The author has said publicly, in the discussion that led to this study, that she favours
  keeping the licence fee and raising it. The study is registered before any outcome data were seen precisely so that
  this view cannot shape the result: every rule below is fixed first, and a result against her view is published in
  the same way and with the same prominence. The article may carry a one-line disclosure of this position.
- **Prior expectation.** None beyond the position above is recorded.
- **Stage of the bill, checked 3 November 2026** on the Chamber's page (https://www.psp.cz/sqw/historie.sqw?O=10&T=231):
  submitted by the government 19 June 2026; first reading 24 October 2026 (34th session), sent to committees (resolution
  no. 349); the Committee on Media and Culture issued resolution 231/1 on 30 October 2026, which interrupts the
  deliberation; "further deliberation possible from 24 December 2026". The article is conditional ("if the bill passes
  as introduced") and dated, and the stage is checked again before publication.

## 1. Questions

Both questions compare two ways of paying for ČT and ČRo as the bill is introduced. They describe arithmetic on
published numbers under stated rules. They do not say what the change would cause, and they say nothing about the
independence or the quality of public broadcasting. About firms they say nothing beyond one aggregate.

**Q-A, real value of the money for ČT and ČRo (headline).** Three paths for the years 2027–2030, in 2026 prices, ČT and
ČRo together:

1. **Current law**: fee revenue starts from the fee revenue in the 2026 budgets of ČT (6.73 bn CZK as brought to this
   design, to be verified at snapshot) and ČRo (taken from its official 2026 budget at snapshot), and then moves only
   through the legal valorisation rule of act 348/2005, §6(2) (§2.1). The number of payers is held at the level behind
   the 2026 budget; no other assumption on payers, exemptions or collection is made. A fall in payers would lower this
   path, so holding them fixed favours current law.
2. **The bill with its valorisation clause**: the amounts of §10a(2) that the bill inserts into the ČT and ČRo acts
   for 2027, and the clause of §10a(3) afterwards (§2.2).
3. **The bill without valorisation**: the 2027 amounts held nominally constant to 2030.

Inflation is the latest ČNB forecast available at snapshot (the autumn 2026 *Zpráva o inflaci* if it is out, else the
summer 2026 one), annual-average CPI for each year it covers; after its horizon, 2 % a year (the ČNB target).
**Headline Q-A: the cumulative difference over 2027–2030, in billions of 2026 CZK, of path 2 minus path 1**, with the
paths of both laws run on the same inflation. Paths 1 and 3, and 2 and 3, are shown beside it. Sensitivity: the whole
inflation path ±1 percentage point in every year, forecast part and 2 % part alike.

**Q-B, who pays.** Burden of the two ways of funding on households by decile of net household income, and on firms as
one aggregate.

- **Unit and measure.** Households, ČSÚ's decile groups of the SILC 2025 tables ("Příjmy a životní podmínky domácností").
  **Burden = payment per household ÷ mean net household income of the decile**, as a ratio of decile means, in per cent;
  also CZK per household per year, by decile, today and after.
- **Today.** The fee is 2 460 CZK per household and year (150 + 55 CZK a month, ×12; act 348/2005, §6(1), §5(2): one fee
  per household). Households exempt under §4(2) pay nothing (§2.1). The share exempt in each decile is estimated from
  the SILC tables as the share of households whose net income is below 2.15 times the *životní minimum* of their
  composition; if the tables do not allow this, deciles 1 and 2 get a bound: no household exempt, or every household
  below the threshold exempt (the other deciles then take the same rule). A household pays if it is not exempt and is
  a payer; the share of non-exempt households that are payers is one number for all deciles, taken from the payer counts
  in the 2025 annual reports of ČT and ČRo if they give them, and set to 1 otherwise.
- **After.** The bill's total (7 807 592 000 CZK for 2027, §2.2) is allocated to taxes **in proportion to the state
  budget's own tax revenue, 2025 outturn** (Státní závěrečný účet or Monitor státní pokladny), after the shares of
  municipalities and regions under act 243/2000 (§2.4). Social insurance contributions are **excluded**, because they
  are earmarked for pensions and health care; this is an explicit choice. Pool of taxes: VAT, excise duties, personal
  income tax (PIT), corporate income tax (CIT); any other tax line (customs, property and road taxes, other) is out of
  the pool, and its share of the state's tax revenue is reported. Incidence:
  - **VAT** to households by decile of consumption: the decile's VAT content of spending, from the ČSÚ household budget
    statistics "Spotřební výdaje domácností" 2025 by quintile, with each quintile's value per household given to both of
    its deciles. Category-by-category rates (21 %, 12 %) follow the VAT act 235/2004 and are written into
    `tools/fees/vat_map.csv` before the consumption tables are opened.
  - **Excise duties** to households by decile share of spending on the excised categories (tobacco, alcohol, fuels,
    energy), mapped in `tools/fees/excise_map.csv` in the same way.
  - **PIT** to households by decile, in this order of availability: the decile's income tax paid, if SILC publishes it;
    else its gross employment-and-self-employment income; else its net income.
  - **CIT** to firms, not passed on to households.
  - **Firms** receive only the CIT part. Their share of other taxes is added only if a defensible published basis
    exists; otherwise it is not, and this is stated. Everything of VAT, excise and PIT is allocated to households,
    which is an upper bound for their part (government, businesses with non-deductible VAT, non-residents and tourists
    also pay these taxes; §8).
- **Scenarios** (sensitivity, none is the primary): **base** is the proportional allocation above; **VAT-only** puts all
  of the total on households as VAT; **PIT-only** puts all of it on households as PIT; **debt** (the amount is
  borrowed) puts no burden on current households and is reported as a sentence, not a number.
- **Firms, today.** Household fee revenue = paying households × the fee (CZK/year); the remainder of the budgeted fee
  revenue is attributed to firms and public bodies. If the remainder is negative or implausible (§3, check 1), firms are
  reported only as a range, from the numbers of employers by size band and the legal schedule of §5(3) (§2.1).
- **Seniors.** A separate cut (households of one or two persons aged 65+) only if SILC publishes by household type. The
  press claim that seniors pay about 40 % of fee revenue is tested only as far as the data allow: the modelled payments
  of those households over the budgeted fee revenue. It is cited as a press claim with its source at publication and not
  asserted.
- **Summary measure.** The ratio of burdens, **decile 1 ÷ decile 10**: above 1 the funding is regressive (the poorest
  tenth carries more of its income than the richest), below 1 progressive. Y is the ratio today; Z the ratio after, one
  for each scenario with a number.

**Pre-written readings** (numbers are filled in later; the wording does not change):

- **A.** "If the bill passes as introduced, ČT and ČRo would receive X bn CZK (2026 prices) less over 2027–2030 than
  under current law." If X is negative, "more" replaces "less" and X is its absolute value.
- **B.** "Today the poorest tenth of households carries Y times the share of its income that the richest tenth does;
  funded from the state budget it would be Z times." Z is given for the base scenario and for VAT-only and PIT-only.

## 2. Rules and sources

### 2.1 Current law (act 348/2005 Coll., version 14, from 1 January 2026; https://www.zakonyprolidi.cz/cs/2005-348)

- **Amounts, §6(1):** "Měsíční výše rozhlasového poplatku činí 55 Kč a měsíční výše televizního poplatku činí 150 Kč."
  Together 205 CZK a month, 2 460 CZK a year.
- **Valorisation, §6(2):** "Měsíční výše rozhlasového poplatku a televizního poplatku se zvýší o 6 % vždy k 1. červenci
  kalendářního roku následujícího po kalendářním roce, v němž součet inflace za předcházející roky od posledního
  zvýšení rozhlasového poplatku a televizního poplatku překročí 6 %. Výše rozhlasového poplatku a televizního poplatku
  se zaokrouhluje na celé koruny směrem nahoru." **§6(3):** the Ministry of Culture announces the new monthly amounts by
  a notice in the Collection of Laws. Modelling rule: the sum of the annual CPI inflation rates (ČSÚ annual averages;
  forecast values where not yet published) of the years since the last increase is accumulated; if the sum exceeds 6
  percentage points in year Y (strictly), the monthly amounts rise by 6 % on 1 July of Y+1, each rounded up to a whole
  crown (ČT 150 → 159; ČRo 55 → 59), and the sum restarts. A year's revenue is the mean of the monthly amounts in force
  (a July step counts 6 months at the old amount and 6 at the new) × 12 × payers. Which years count after the last
  increase, and when the last increase took effect, are open items (§2.6).
- **Exemption of households, §4(2):** "Od rozhlasového a televizního poplatku je dále osvobozena fyzická osoba, a) jde-li
  o jednotlivce, jehož čistý příjem za uplynulé kalendářní čtvrtletí je nižší než 2,15násobek životního minima,
  b) žije-li v téže domácnosti s dalšími osobami a součet jejího čistého příjmu a čistých příjmů těchto osob za
  uplynulé kalendářní čtvrtletí je nižší než 2,15násobek životního minima osob žijících v této domácnosti." The *životní
  minimum* is that of act 110/2006 Coll. (footnote 10 of the act). The figure **2.15 × životní minimum is verified.**
  Under §4(3) the exemption starts only after a declaration by the payer and ends at the latest after 6 calendar months,
  so exempt by entitlement is not exempt in fact; the model uses entitlement (an upper bound of the exempt share; §8).
- **Other exemptions, §4(1):** among others foreign missions, foreigners without long-term residence, licensed
  broadcasters, the blind or deaf living alone, schools, associations, employers of more than 50 % people with a
  disability.
- **One fee per household, §5(1)–(2):** a natural person pays one radio and one television fee however many sets;
  a person living in the household of a registered payer does not pay.
- **Firm schedule, §5(3)–(4), (6):** for a legal person or a self-employed entrepreneur, by number of employees in
  full-time equivalents: 25–49, 5 times the household monthly fee; 50–99, 10 times; 100–199, 20 times; 200–249, 30
  times; 250–499, 70 times; "více než 500", 100 times; up to 24 employees, no fee (§5(4)); a company that rents out
  vehicles with sets pays for each vehicle (§5(7)). The wording leaves exactly 500 employees out of the list (open
  item). Under §3(4) state and territorial bodies are treated as legal persons, so the "firm" remainder includes public
  bodies.

### 2.2 The bill (Sněmovní tisk 231/0, distributed 19 June 2026; https://www.psp.cz/sqw/historie.sqw?O=10&T=231, file `t023100.pdf`)

- **Čl. V:** the act takes effect on 1 January 2027. **Čl. IV(1):** act 348/2005 is repealed. **Čl. III:** fee duties
  that arose before the effective date remain under the old act.
- **ČT, Čl. I, new §10a of act 483/1991:** (1) ČT receives a contribution that is an expenditure of the state budget,
  chapter Ministry of Culture; **(2) "Příspěvek pro rok 2027 činí celkem 5 741 826 000 Kč."**
- **ČRo, Čl. II, new §10a of act 484/1991:** **(2) "Příspěvek pro rok 2027 činí celkem 2 065 766 000 Kč."**
- **Total for 2027: 7 807 592 000 CZK.** The explanatory report says these amounts equal the fee income of 2024 (ČT
  5 741 826 thousand CZK, ČRo 2 065 766 thousand CZK). This design uses the bill's own figures; the 5.740 bn and 7.805 bn
  first quoted to this design are replaced by them (§2.6).
- **Valorisation clause, §10a(3), identical in both acts:** "Pro rok 2028 a roky následující činí příspěvek částku
  odpovídající výši příspěvku pro bezprostředně předcházející kalendářní rok. Pokud kumulativní průměrná roční míra
  inflace za období od roku 2026 nebo od kalendářního roku bezprostředně předcházejícího poslednímu zvýšení příspěvku
  vypočtená podle údajů zveřejněných Českým statistickým úřadem překročí 10 procentních bodů, tato částka se zvýší
  o 10 %. Příspěvek se zaokrouhluje na celé koruny nahoru." The threshold is therefore **10 percentage points** (not
  "more than 10 %" of the amount), the base is **the year 2026**, the step is **+10 %** of the amount, and the data are
  ČSÚ's published inflation. The explanatory report restates it as "součet inflace za předcházející roky … přesáhl od
  posledního zvýšení příspěvku 10 %" and says that 2026 is the starting year "pro vyloučení interpretačních problémů".
- **Payment, §10a(4)–(5):** monthly payments of one twelfth by the 15th day of the month.
- **Modelling rule for the clause.** Primary reading **R1**: the cumulative measure is the sum of the annual CPI
  inflation rates (annual average on annual average) of the years from 2026, 2026 included; if it exceeds 10 percentage
  points in year Y (strictly), the amount rises by 10 % from year Y+1 (the report speaks of the increase "po kalendářním
  roce", after the calendar year, in which the sum was exceeded). Reading **R2** (a check): cumulative inflation as a
  compounded price index, 2026 average = 100, from the end of 2026, not including 2026's own inflation. The words
  "průměrná roční míra" (average annual rate) would, read literally, require an average rate above 10 points and make
  the clause void; the report's "součet" (sum) excludes that reading and it is not modelled. A second trigger inside
  2027–2030 would need a further 10 points of inflation after the first; if any path produces one, the code stops and
  the case is logged. Whether the clause triggers at all by 2030 depends on the forecast
  and on the reading; if it does not, paths 2 and 3 coincide and that is reported.

### 2.3 Real value

Prices of year t are the product of (1 + annual-average CPI inflation) from 2027 to t, with 2026 = 1. Nominal amounts of
the bill and of current law are divided by it. Q-B is stated in nominal amounts (today's fee at the 2026 level, the bill's
total at its 2027 level); the same with the bill's total deflated to 2026 prices is a check.

### 2.4 Sharing of taxes (act 243/2000 Coll., version 17; https://www.zakonyprolidi.cz/cs/2000-243)

What stays with the state budget is what the regions and municipalities do not receive:

- **Regions, §3(1)(b)–(g):** 10.23 % of the national gross yield of VAT, of PIT (all forms) and of CIT (other than the
  CIT paid by the region itself, §3(1)(a)).
- **Municipalities, §4(1)(b)–(f), (i):** 25.93 % of VAT, of PIT (all forms) and of CIT, plus 1.5 % of PIT on employment
  (§4(1)(h)); the CIT paid by the municipality itself is its own (§4(1)(g)).
- **State Fund for Transport Infrastructure, §5:** 9.1 % of the excise duty on mineral oils. Other excise duties are
  not shared.
- **Reading used when the outturn lines are gross yields:** the state keeps 63.84 % of VAT, of CIT and of PIT other than
  on employment, 62.34 % of PIT on employment, 90.9 % of the excise duty on mineral oils and all of other excise
  duties. If the Státní závěrečný účet lines are already net of these transfers they are used as they stand; which is
  the case is read from the document at snapshot, not decided from the numbers.

### 2.5 Snapshot

Every source is fetched headless (`curl`, User-Agent "bsandova.com research", at most two requests at a time, no
circumvention of any bot check: a source that blocks is recorded as unavailable and the design is adjusted in a dated
change-log entry, not worked around). Files are saved with the date under the gitignored `tools/data/fees/` and hashed
into `docs/research/fees-files.sha256` before any computation. The snapshot step writes only the raw files and the hash
file; the outcome tables are not opened. Only their layout (sheet names, row and column labels, no value) may be looked
at to write the parser. Sources:

1. Sněmovní tisk 231/0 with the explanatory report (the file read on 3 November 2026), and the stage page.
2. Act 348/2005 Coll., the version from 1 January 2026; and any notice of the Ministry of Culture under §6(3).
3. ČT and ČRo budgets for 2026 and their annual reports for 2024 and 2025 (fee revenue, numbers of payers if given).
4. ČSÚ SILC 2025 decile tables, and the tables by household type if there are any.
5. ČSÚ household consumption 2025, quintile tables by COICOP group.
6. State budget 2025 outturn by tax (Státní závěrečný účet or Monitor státní pokladny).
7. ČNB inflation forecast, the latest at snapshot.
8. Act 243/2000 Coll., the sharing percentages (§2.4), and act 110/2006 Coll. for the *životní minimum* amounts in force.
9. ČSÚ annual CPI inflation 2023–2025 (for the valorisation sums), the counts of employers by size band, and the number
   of households.

### 2.6 Open items to resolve at snapshot (none is guessed here)

1. **The bill's amounts.** The bill says ČT 5 741 826 000 CZK and ČRo 2 065 766 000 CZK, 7 807 592 000 CZK in all. The
   5.740 bn and 7.805 bn quoted first do not match it. The design uses the bill's figures; the change is logged.
2. **ČT's 6.73 bn.** It is 17 % above the 5.742 bn of 2024 fee income. It may include income other than fees, or reflect
   the fee rises, or be a different line. The baseline is the *fee* line of the budget only; if 6.73 bn is not that line,
   the fee line replaces it and the change is logged. The headline Q-A depends heavily on this level.
3. **When the fee was last raised, and which years count in §6(2).** The text says "od posledního zvýšení" (since the
   last increase) without a date. The last increase date is read from the version history of the act and the notices
   under §6(3). Primary: the sum starts with the calendar year in which the last increase took effect and includes it;
   check: it starts with the following year. A notice under §6(3) already published for 2027 overrides the model.
4. **Timing of the bill's increase** (year Y+1, §2.2) and the reading R1 or R2 — the bill's text does not settle them.
5. **Whether SILC deciles rank households by total net income or persons by equivalised income**, and which income year
   the SILC 2025 tables refer to (expected: the year before the survey, 2024). The household-based table with mean total
   net household income is used if it exists; otherwise the equivalised one with the mean household size of the decile.
   The income year is recorded in the results.
6. **Exactly 500 employees** are not covered by §5(3).
7. **Whether the state-budget tax lines are gross or net of the transfers of §2.4.**
8. **The source of the press claim on seniors.**

## 3. Checks that stop the run

Fail-stop in the code; on a failure the run stops, the cause is investigated and, if the method changes, the change is a
logged deviation:

1. **Fee revenue today.** The modelled fee payments of households (all deciles) plus firms are within ±5 % of the
   budgeted fee revenue of ČT plus ČRo for 2026. Where the firm side is the remainder, this holds by construction and
   the substantive test is its plausibility: the remainder is not negative, and if employer counts exist it lies within
   the range implied by the counts and the schedule of §5(3), widened by 5 % of the budgeted revenue at either end. If it
   does not, firms are reported as the range only and the test becomes: budgeted revenue lies within [households + low
   end, households + high end] widened by 5 % of the budgeted revenue. It is applied to each exemption bound.
2. **Allocation after.** The allocated total over households plus firms equals the bill's total, 7 807 592 000 CZK,
   exactly (to the crown), in the base scenario and in each scenario with a number.

## 4. Estimation and uncertainty

Everything is arithmetic on published aggregates; there is no sampling and no confidence interval. A published decile
table is itself an estimate with a sampling error that ČSÚ does not publish for the cells used, and a model of it adds
nothing that could be given an interval. The uncertainty is the **range over the scenarios**:

- Q-A: the ±1 point inflation paths, reading R1 against R2, the two starting years of §2.1, and, if the baseline is
  doubtful (§2.6, item 2), both baselines.
- Q-B: the two exemption bounds for deciles 1 and 2, the three tax scenarios, and the checks of §6.

A result that holds across the whole range is stated as it is; a result that flips is reported as **"depends on the
assumption"**, with the assumption named. The number reported is the primary specification's, and the range is given
beside it. The range is not a probability statement.

## 5. Power and precision

Not applicable in the sense of a test: the study has no sample to design for. What takes the place of power is the
width of the scenario range, which is known only after the run. Two things are known now. First, in Q-B the burden
ratio is a ratio of two decile means and is not sensitive to the level of the total, so scale errors (§2.6, item 2)
move the CZK figures much more than the ratios. Second, the quintile-to-decile split of consumption (§8) gives the
two deciles of a quintile the same spending, so the burden ratio between deciles 1 and 2, or 9 and 10, is driven by
income alone there.

## 6. Labels

Q-A, by the sign of the headline difference (path 2 minus path 1) over the scenario range of §4:

- **bill lower** — negative in every scenario; **bill higher** — positive in every scenario; **depends on the
  assumption** — the sign changes inside the range. The sentence of reading A states the primary value with the range.
- Paths 2 and 3 are reported with the note that they coincide if the clause does not trigger by 2030.

Q-B, by the ratio of burdens (decile 1 ÷ decile 10) over the scenarios with a number, today (Y) and after (Z):

- Today and after each: **regressive** — above 1 in every scenario; **progressive** — below 1 in every scenario;
  **depends on the assumption** otherwise.
- Change: **funding from the budget lowers the ratio** — Z below Y in every scenario; **raises** — Z above Y in every
  scenario; **depends on the assumption** otherwise.

Z is given scenario by scenario in the text, and the label requires only that the sign holds in all. The debt scenario is
a sentence and enters no label. There are no labels for firms, seniors, or the CZK-per-household figures.

## 7. Checks reported (none relabels a primary result)

1. Reading R2 of the clause (§2.2); the starting year after the last increase; the baseline levels of §2.6, item 2.
2. The bill's total deflated to 2026 prices in Q-B.
3. VAT with one uniform effective rate instead of the category map; "other taxes" allocated like VAT instead of dropped.
4. PIT by each of the three bases of §1 where more than one is available.
5. Payer share of non-exempt households set to 1 instead of the report-based value.
6. Burden measured as the mean of household ratios if the tables give it, not the ratio of means.
7. The seniors' cut and the press claim, if the data allow.

## 8. Limits stated now

- **Modelled, not measured, deciles.** There is no microdata (the SafeCentrum is not available); tax and fee burdens by
  decile are built from published decile and quintile aggregates under assumptions. Different assumptions give different
  numbers; the range of §4 shows how much.
- **Quintile to decile split.** Consumption is published by quintile; both deciles of a quintile get the same spending
  per household. The lower decile of a pair then shows a higher burden and the higher one a lower burden than a true
  split would, so the split leans towards a regressive reading of consumption taxes.
- **Different years.** SILC income refers to a year before 2025, consumption and tax outturn to 2025, the fee to 2026
  and the bill to 2027; nothing is re-based except what §2.3 says.
- **Exemptions are estimated.** The exempt share is by entitlement (§4(2)); in fact a declaration is needed and lapses
  after 6 months (§4(3)), so the true exempt share is lower. SILC income is annual, the law tests the last calendar
  quarter. The *životní minimum* of the household composition is approximated.
- **Standard, not measured, incidence.** That CIT stays with firms, that VAT and excise fall on household consumption
  entire, and that PIT falls on those who earn the income, are textbook assumptions. The allocation to households of the
  whole of VAT and excise is an upper bound on their share.
- **A tax-financed contribution is not a tax increase.** The allocation answers "who bears the cost if it is spread like
  the existing taxes"; the government may fund it by a different mix, by debt, or by cutting other spending (the debt
  scenario is a sentence for that reason).
- **Current-law baseline.** Payers are held at the 2026 budget level; the budget level itself may rest on an assumption
  of the broadcasters. The firm side is a remainder or a range.
- **The coalition proposal of May 2026** (more exemptions) is a separate bill and is out of scope, as is any other
  amendment of the fee.
- **The bill may change in committee**, including its amounts, its valorisation clause and its effective date (it takes
  effect on 1 January 2027 as introduced; the comparison keeps the window 2027–2030 whatever happens). The article says
  "as introduced". The explanatory report also says the European Commission will be asked whether the funding is state
  aid; that is not modelled.
- **Correlation is not the question and causation is not claimed.** Nothing here concerns the independence, quality or
  reach of public broadcasting, or what the broadcasters would do with the money.

## 9. Outputs

An article on bsandova.com: the three paths of Q-A with the headline sentence and its range, the burden by decile today
and after with the ratios Y and Z, firms as one aggregate, and a plain account of what the model cannot see. Machine
output in `docs/research/fees-results.json`.

## Running and verification

Code in `tools/fees/` (fetch, hash, parse, model, checks) with tests on made-up inputs only; commands and the verified
facts about each source, with dates, in `tools/fees/README.md`. The freeze tag is `fees-code`, set on the final code
before any outcome table is opened. Order: design tag `fees-design` → snapshot and `docs/research/fees-files.sha256`
→ code with tests, tag `fees-code` → run → `docs/research/fees-results.json` → article. The run refuses to start if a
hashed file has changed or the tag is not on HEAD with `tools/fees/` unchanged since. Both checks of §3 run first.

## Change log

- 3 November 2026: design committed, before any outcome table was opened. Facts verified the same day from the legal
  texts: the bill's amounts differ from the figures first quoted (§2.2, §2.6 item 1: ČT 5 741 826 000 and ČRo
  2 065 766 000 CZK, 7 807 592 000 in all), the bill's clause is 10 percentage points (not 10 %) from 2026 with a step
  of +10 %, and the current-law rule is 6 % when the sum of inflation since the last increase exceeds 6 %, from 1 July.
