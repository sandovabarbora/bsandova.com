# If the licence fees are replaced by the state budget: what do Czech Television and Czech Radio get, and who pays? — research design

**Status: pre-specified analysis, design committed 3 November 2026, before any outcome table was opened.** A descriptive
accounting comparison with registered rules; it makes no causal claim. The steps follow in dated commits: design →
data snapshot (files fetched and hashed, outcome tables unopened) → data-step code (tagged `fees-data-step` before it
opens any outcome table) → estimation code (tagged `fees-code`) → results. Commit times are self-reported; the signed
tag `fees-design` fixes this text. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The bill and the law.** On 3 November 2026 the drafting assistant read the text of the government bill (Sněmovní
  tisk 231/0, including the explanatory report), the stage page of the bill, act 348/2005 Coll. (version 14, in force
  from 1 January 2026, and, through its print versions, versions 11 and 13 and the text of amending acts 119/2025 and
  152/2025 Coll.) and act 243/2000 Coll. (versions 15, 16 and 17, with the version history). They are legal texts, not
  outcome data. What they say is quoted in §2.
- **Background known to the drafting assistant from feasibility research, not used as a result and not quoted as one.**
  (1) ČT's 2026 budget document, where a fee-revenue figure of 6.73 bn CZK was found; it did not come from the author.
  (2) ČRo's 2026 budget of about 2.48 bn CZK, from a press report (MediaGuru). (3) The ČNB summer 2026 forecast
  headline path of consumer prices, about 2.0, 2.5 and 2.4 % for three successive years. (4) The 2025 state-budget
  *plan* by tax (a plan, not the outturn). The author holds none of this beyond press coverage, as far as is recorded.
  These figures are inputs the rules of §2 will read again from the snapshot files; no rule below was chosen to fit them.
- **Outcome data: none opened.** No ČSÚ income-and-living-conditions (SILC) table, no ČSÚ household consumption table, no
  state-budget outturn by tax, no ČNB forecast file, and no fee-revenue table of Česká televize (ČT) or Český rozhlas
  (ČRo) has been opened for this study. For ČSÚ's SILC 2025 publication only the titles of its tables were read (§2.9).
- **A press claim** that seniors pay about 40 % of fee revenue has been heard; it has no traceable source and is not
  tested (§1, Q-B).
- **The coalition proposal of May 2026** (further exemptions for people aged 75+, holders of ZTP cards and firms of up
  to 50 employees) is known to the author. It is a separate proposal and is not modelled (§8).
- **Position of the author.** The author has said publicly, in the discussion that led to this study, that she favours
  keeping the licence fee and raising it. The study is registered before any outcome data were seen precisely so that
  this view cannot shape the result: every rule below is fixed first, and a result against her view is published in
  the same way and with the same prominence. §8 states, for every simplification, which way it pushes the result
  relative to that position, and §7 registers a check that pushes the other way for each of the main ones. The article
  **will** carry a one-line disclosure of this position, in its methods note.
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

1. **Current law**: fee revenue starts from the baseline of §2.7 (the fee-revenue line of each broadcaster's 2026 budget)
   and then moves only through the legal valorisation rule of act 348/2005, §6(2). The number of payers is held at the
   level behind the baseline; no other assumption on payers, exemptions or collection is made. A fall in payers would
   lower this path, so holding them fixed favours current law.
2. **The bill with its valorisation clause**: the amounts of §10a(2) that the bill inserts into the ČT and ČRo acts for
   2027, and the clause of §10a(3) afterwards.
3. **The bill without valorisation**: the 2027 amounts held nominally constant to 2030.

Inflation, the cutoff and the deflator are pinned in §2.6. **Headline Q-A: the cumulative difference over 2027–2030, in
billions of 2026 CZK, of path 1 minus path 2** (X, positive when the bill gives less), with both laws run on the same
inflation. Paths 1 and 3, and 2 and 3, are shown beside it. The scenario range of the label is in §4.

**Q-B, who pays.** Burden of the two ways of funding on households by decile of net household income, and on firms as
one aggregate. The rules (units, incidence, scenarios) are in §2.4.

- **Burden** = payment per household ÷ mean net household income of the decile, in per cent (a ratio of decile means);
  also CZK per household and year, by decile, today and after.
- **Summary measure.** The ratio of burdens, **decile 1 ÷ decile 10**. **Y** is the ratio today, a range over the two
  exemption bounds of §2.4 (Y(E1) ≤ Y(E0)). **Z** is the ratio after, in the primary specification, the average
  tax structure of the state budget. Z in the VAT-only and PIT-only scenarios is reported beside it. A monotonicity note
  (descriptive): the number of steps from decile to decile in which the burden rises with income, and the deciles where
  it does.
- **Firms** appear as one aggregate figure, today and after, with the caveat of reading B.
- **Seniors**: a descriptive cut (households with persons aged 65+) only if the SILC tables publish one. The press
  claim about 40 % is not tested.

**Pre-written readings** (numbers are filled in later; the wording does not change except as stated):

- **A.** "If the bill passes as introduced, ČT and ČRo would receive X bn CZK (2026 prices) less over 2027–2030 than
  under current law." If X is negative, "more" replaces "less" and X is its absolute value. If the label is **depends
  on the assumption** (§6): "Whether ČT and ČRo would receive more or less over 2027–2030 than under current law
  depends on the assumption: across the range the bill gives between X_max bn CZK less and X_min bn CZK more (2026
  prices)", with the signs taken from the range. If the label is **about equal**: "… the same, within 0.1 bn CZK".
- **B.** "Today the poorest tenth of households carries between Y_lo and Y_hi times the share of its income that the
  richest tenth does (the range is the two exemption bounds; exemptions are counted by entitlement, not by actual
  take-up). Funded from the state budget at the average tax structure it would be Z times; if the money came from VAT
  alone it would be Z_VAT times, and from personal income tax alone Z_PIT times." The debt scenario is one sentence:
  if the amount is borrowed, current households carry nothing now.
- **C (level).** "Today ČT and ČRo get B bn CZK a year in fee revenue (2026 budgets). The bill gives 7.808 bn CZK for
  2027, which is D bn CZK (2026 prices) more/less."
- **Firms (in B and C, in the same sentence as the figures).** "Firms and public bodies pay F_today bn CZK a year today
  (what remains of the budgeted fee revenue after households, public bodies included) and would carry F_after bn CZK
  after (the corporate-income-tax share of the total); the two figures are not like for like." If the remainder fails
  the plausibility test (§3), only the range is given.

## 2. Definitions, rules and sources

### 2.1 Definitions and arithmetic

- **Household.** As in the SILC tables: the private household of the survey. A household has at most one payer of each
  fee (act 348/2005, §5(1)–(2): one fee per household whatever the number of sets, and persons living with a registered
  payer do not pay).
- **Payer.** A household of natural persons registered as paying the TV fee (a TV payer) or the radio fee (a radio
  payer). Firms and public bodies are not household payers. **Payer share** π_s for service s (TV, radio) = the number of
  household payers of s in the 2025 annual report of the broadcaster ÷ the number of households of the SILC 2025 tables
  (weighted). If the report gives one combined count, π = that count ÷ households for both services; if it gives none,
  π = 1, which is stated as an upper bound. The same payer count is the basis of the baseline's "payers held fixed" in
  Q-A and of the household payments in Q-B.
- **Payment of a paying household.** 150 × 12 = 1 800 CZK (TV) and 55 × 12 = 660 CZK (radio) a year. The average payment
  of a household in a decile is 1 800 π_TV + 660 π_R (the share of non-exempt households that pay is in §2.4). With
  equal π this is 2 460 × π. A household really pays 0, 55, 150 or 205 CZK a month; **the simplification is that
  households of a decile are averaged through the payer shares**, so a household paying only one fee is not told apart
  from one paying both.
- **Arithmetic.** Every ceiling and rounding in the model is done in integer CZK or in exact decimals (Python `int`,
  `Decimal` or `Fraction`), never in binary floating point: the monthly amounts of §6(2) (ceiling to a whole crown), the
  bill's +10 % (ceiling to a whole crown), the inflation sums (decimals as published, comparison with the threshold is
  strict), and every allocation, which is rounded by the **largest-remainder method** to whole crowns so that parts sum
  to the whole. Floating point is used only to display.

### 2.2 Current law (act 348/2005 Coll., version 14, from 1 January 2026; https://www.zakonyprolidi.cz/cs/2005-348)

- **Amounts, §6(1):** "Měsíční výše rozhlasového poplatku činí 55 Kč a měsíční výše televizního poplatku činí 150 Kč."
  Together 205 CZK a month, 2 460 CZK a year.
- **Valorisation, §6(2):** "Měsíční výše rozhlasového poplatku a televizního poplatku se zvýší o 6 % vždy k 1. červenci
  kalendářního roku následujícího po kalendářním roce, v němž součet inflace za předcházející roky od posledního
  zvýšení rozhlasového poplatku a televizního poplatku překročí 6 %. Výše rozhlasového poplatku a televizního poplatku
  se zaokrouhluje na celé koruny směrem nahoru." **§6(3):** the Ministry of Culture announces the new monthly amounts by
  a notice in the Collection of Laws.
- **The last increase (read from the version history).** Before 1 May 2025 the text of §6 was "Měsíční výše
  rozhlasového poplatku činí 45 Kč, měsíční výše televizního poplatku činí 135 Kč" (print version of 1 February 2022;
  the ČT amount has stood since 1 January 2008). Act 119/2025 Coll., Čl. VI point 9, rewrote §6 to the present text; the
  act took effect on 1 May 2025 (Čl. VII; published 28 April 2025). **The last increase is therefore 1 May 2025**: ČT
  135 → 150 CZK (+11.1 %) and ČRo 45 → 55 CZK (+22.2 %); it is a statutory increase, not a §6(2) step; the act's text records
  no later step, and any notice under §6(3) is an open item (§2.10). Versions of the act: 11 (1 Feb 2022 – 30 Apr 2025), 12 (1 May – 30 Sep 2025, act 119/2025),
  13 (1 Oct – 31 Dec 2025, act 152/2025), 14 (from 1 Jan 2026, act 119/2025, Čl. VI points 20 and 22).
- **Modelling rule for §6(2).** Let π_t be the annual-average CPI inflation (ČSÚ's *průměrná roční míra inflace*, in per
  cent to one decimal) of calendar year t. The **window** for "years since the last increase" starts with calendar year
  2025, the year in which the last increase took effect, and includes it (primary); the window starting with 2026 is a
  check (§7). The sum of π_t over the window is compared with 6 (strictly greater). If it exceeds 6 in year Y, the
  monthly amounts rise on 1 July of Y+1: ČT 150 → ceil(150 × 106 / 100) = 159, ČRo 55 → ceil(55 × 106 / 100) = 59,
  each computed separately in integers; the window then restarts with year Y+1, the year of the increase. Second and
  later triggers inside 2027–2030 are computed by the same rule, not treated as an error.
- **Exemption of households, §4(2):** "Od rozhlasového a televizního poplatku je dále osvobozena fyzická osoba, a) jde-li
  o jednotlivce, jehož čistý příjem za uplynulé kalendářní čtvrtletí je nižší než 2,15násobek životního minima,
  b) žije-li v téže domácnosti s dalšími osobami a součet jejího čistého příjmu a čistých příjmů těchto osob za
  uplynulé kalendářní čtvrtletí je nižší než 2,15násobek životního minima osob žijících v této domácnosti." The
  *životní minimum* is that of act 110/2006 Coll. (footnote 10 of the act). The figure **2.15 × životní minimum is
  verified.** Under §4(3) the exemption starts only after a declaration by the payer and ends at the latest after 6
  calendar months, so exempt by entitlement is not exempt in fact; the model uses entitlement.
- **Other exemptions, §4(1):** among others foreign missions, foreigners without long-term residence, licensed
  broadcasters, the blind or deaf living alone, schools, associations, employers of more than 50 % people with a
  disability.
- **Firm schedule, §5(3)–(4), (6):** for a legal person or a self-employed entrepreneur, by number of employees in
  full-time equivalents: 25–49, 5 times the household monthly fee; 50–99, 10 times; 100–199, 20 times; 200–249, 30
  times; 250–499, 70 times; "více než 500", 100 times; up to 24 employees, no fee (§5(4)); a company that rents out
  vehicles with sets pays for each vehicle (§5(7)). Exactly 500 employees are not covered by the wording of (e)–(f);
  the schedule range of §3 takes the higher multiple (70 or 100) for a band that contains 500. Full-time equivalents
  between 24 and 25 fall in neither (a) nor (4); the published size bands are headcount bands and the difference
  between headcount and full-time equivalents is ignored (§8). Under §3(3)–(4) a customer of electricity not in the
  register is presumed a payer unless he declares otherwise, and state and territorial bodies are treated as legal
  persons, so the firm remainder includes public bodies.
- **Reform of 2025.** Act 119/2025 Coll. also introduced the present firm schedule and the exemptions of associations and
  of employers of people with disabilities, required firms and public bodies to re-register their number of employees
  within two months (transitional provisions 1–3), and renumbered the presumption for electricity customers (it
  existed before as §3(4)). Its effect on the number and structure of payers in 2025 and 2026 is not modelled; it is a
  candidate explanation, with the fee rise of 1 May 2025, of why ČT's budgeted fee revenue for 2026 is higher than the
  2024 level on which the bill rests. **It does not change the baseline rule of §2.7.**

### 2.3 The bill (Sněmovní tisk 231/0, distributed 19 June 2026; https://www.psp.cz/sqw/historie.sqw?O=10&T=231, file `t023100.pdf`)

- **Čl. V:** the act takes effect on 1 January 2027. **Čl. IV(1):** act 348/2005 is repealed. **Čl. III:** fee duties
  that arose before the effective date remain under the old act.
- **ČT, Čl. I, new §10a of act 483/1991:** (1) ČT receives a contribution that is an expenditure of the state budget,
  chapter Ministry of Culture; **(2) "Příspěvek pro rok 2027 činí celkem 5 741 826 000 Kč."**
- **ČRo, Čl. II, new §10a of act 484/1991:** **(2) "Příspěvek pro rok 2027 činí celkem 2 065 766 000 Kč."**
- **Total for 2027: 7 807 592 000 CZK** (the sum is checked in integers). The explanatory report says these amounts equal
  the fee income of 2024 (ČT 5 741 826 thousand CZK, ČRo 2 065 766 thousand CZK), that is, the level before the fee rise
  of 1 May 2025. The 5.740 bn and 7.805 bn first brought to this design are replaced by the bill's own figures.
- **Valorisation clause, §10a(3), identical in both acts:** "Pro rok 2028 a roky následující činí příspěvek částku
  odpovídající výši příspěvku pro bezprostředně předcházející kalendářní rok. Pokud kumulativní průměrná roční míra
  inflace za období od roku 2026 nebo od kalendářního roku bezprostředně předcházejícího poslednímu zvýšení příspěvku
  vypočtená podle údajů zveřejněných Českým statistickým úřadem překročí 10 procentních bodů, tato částka se zvýší
  o 10 %. Příspěvek se zaokrouhluje na celé koruny nahoru." The threshold is **10 percentage points**, the base is
  **the year 2026**, the step is **+10 %** of the amount, and the data are ČSÚ's published inflation.
- **Two readings of "kumulativní".** "Průměrná roční míra inflace" is ČSÚ's standard term for annual-average CPI
  inflation, so the clause applies "cumulative" to ČSÚ's published annual-average rates. The explanatory report words it
  in two ways: general part, point 3, "součet inflace za předcházející roky přesáhl od posledního zvýšení příspěvku
  10 %" (a **sum**), and the special part, "kumulovaná inflace vyhlášená Českým statistickým úřadem překročí 10
  procentních bodů od posledního zvýšení příspěvku" (a **cumulated** rate, which a reader may take as compounded). So:
  - **R1 (primary): the sum** of ČSÚ's annual-average rates of the window; it exceeds 10 if the sum is strictly greater.
  - **R2: the compounded** rate, ∏(1 + π_t/100) − 1 over the same years, compared with 0.10 (strictly greater), in exact
    decimals.
  Both use the same years. The two readings differ by a few tenths of a point over four to five years, which can decide
  whether the clause triggers by 2030; that is why both are in the range of the label.
- **Window and timing, literal reading.** The first window is the years from 2026, 2026 included. If the threshold is
  exceeded in year Y, the amount rises by 10 % from year Y+1 (the report speaks of the increase "po kalendářním roce" in
  which the threshold was exceeded). The next window starts at "the calendar year immediately preceding the last
  increase", that is, at year Y (the year of the crossing, counted again), as the text says. The two laws are followed
  literally and they differ: current law restarts at the year of the increase, the bill at the year before it. A
  second trigger inside 2027–2030 is computed, not an error. The +10 % is applied to the amount of each of ČT and ČRo
  separately: amount' = ceil(amount × 11 / 10) in integer crowns.
- **Payment, §10a(4)–(5):** monthly payments of one twelfth by the 15th day of the month.

### 2.4 Q-B rules

- **Units.** Households, in the deciles of the SILC 2025 tables of ČSÚ ("Příjmy a životní podmínky domácností"). Primary
  table: *Households by income decile distribution (per person)* (ČSÚ's Table 2 in the order of its publication page;
  confirmed at snapshot), the columns of mean total net household income and of mean household size. If that table has no
  mean total net household income column, the table *Households by income decile (modified OECD consumption unit)* is
  used: total income = mean income per consumption unit × mean number of consumption units, with the modified OECD scale
  (1 for the first adult, 0.5 for each further person aged 14 and over, 0.3 for each child under 14), and the **mean
  equivalent size of each decile** is reported. The SILC income year is recorded in the results (expected: the year
  before the survey).
- **Today, exemption bounds.** The fee of §2.1 is paid by non-exempt households. Two bounds:
  - **E0 (nobody exempt):** every decile has payer share π.
  - **E1 (decile rule):** a decile is exempt if its **mean net monthly household income** (annual ÷ 12) is below 2.15 ×
    the *životní minimum* of the decile's mean household, applied to every decile alike. The *životní minimum* is
    built from the amounts of act 110/2006 Coll. in force on 1 January 2026 for the first adult, further adults and
    children, using the decile's mean household size and mean number of dependent children from the same table (child
    amounts: the unweighted mean of the amounts of the age bands). If that rule leaves no decile exempt, decile 1 is
    exempt. Exempt deciles pay nothing; the payers are then spread equally over the other deciles so that the total number
    of payers stays at π × households (the payer share of a non-exempt decile is π × households ÷ non-exempt households,
    capped at 1, and any shortfall from the cap is reported).
  - The table *Households by net income relative to living minimum* is used only as a national cross-check of the exempt
    share if its class edges allow (descriptive).
- **After.** The bill's total (7 807 592 000 CZK for 2027, §2.3) is allocated to taxes **in proportion to the state
  budget's own tax revenue, 2025 outturn** (Státní závěrečný účet or Monitor státní pokladny), after the shares of
  municipalities and regions (§2.5). Social insurance contributions are **excluded**, because they are earmarked for
  pensions and health care; this is an explicit choice, and a check includes them (§7). Pool of taxes: VAT, excise
  duties, personal income tax (PIT), corporate income tax (CIT); any other tax line (customs, property and road taxes,
  other) is out of the pool, and its share of the state's tax revenue is reported. Incidence:
  - **VAT** to households by decile of consumption: the decile's VAT content of spending, from the ČSÚ household budget
    statistics "Spotřební výdaje domácností" 2025 by quintile, with each quintile's value per household given to both of
    its deciles. Category-by-category rates (21 %, 12 %) follow the VAT act 235/2004 and are written into
    `tools/fees/vat_map.csv` before the consumption tables are opened.
  - **Excise duties** to households by decile share of spending on the excised categories (tobacco, alcohol, fuels,
    energy), mapped in `tools/fees/excise_map.csv` in the same way.
  - **PIT** to households by decile, by the first basis available, decided from the headings of the SILC tables: the
    decile's income tax paid; else its gross employment-and-self-employment income; else its net income.
  - **CIT** to firms, not passed on to households.
  - **Firms** receive only the CIT part. Their share of other taxes is added only if a defensible published basis
    exists; otherwise it is not, and this is stated. The whole of VAT, excise and PIT is allocated to households, which
    is an upper bound for their part (government, businesses with non-deductible VAT, non-residents and tourists also
    pay these taxes; §8).
- **Scenarios.** **Primary: the base** (the proportional allocation above, the average tax structure of the state
  budget). Sensitivity scenarios, reported and not used for the label (§6): **VAT-only** and **PIT-only** put all of the
  total on households as VAT or as PIT; **debt** puts no burden on current households and is a sentence, not a number.
- **Firms, today.** Household fee revenue = paying households × fee (§2.1); the remainder of the budgeted fee revenue is
  attributed to firms and public bodies. It is plausible only if non-negative and inside the schedule range of §3.

### 2.5 Sharing of taxes (act 243/2000 Coll.)

What stays with the state budget is what regions and municipalities do not receive. The governing version for the **2025
outturn** is **version 15, in force from 1 January to 31 December 2025** (act 349/2023, https://www.zakonyprolidi.cz/cs/2000-243/historie
and print version https://www.zakonyprolidi.cz/print/cs/2000-243/zneni-20250101.htm): no other version was in force
in 2025, so the percentages did not change during the year. In it:

- **Regions, §3(1)(b)–(g):** 9.45 % of the national gross yield of VAT, PIT (all forms) and CIT.
- **Municipalities, §4(1)(b)–(f), (i):** 24.16 % of the same, plus 1.5 % of PIT on employment (§4(1)(h)).
- **State Fund for Transport Infrastructure, §5:** 9.1 % of the excise duty on mineral oils; other excise is not shared.
- **State share (primary), if the outturn lines are gross yields:** 66.39 % of VAT, of CIT and of PIT other than on
  employment; 64.89 % of PIT on employment; 90.9 % of the mineral-oil excise; all of the other excise.
- From 1 January 2026 (version 16, act 267/2025; and version 17, act 155/2026, in force 29 August 2026 – 31 December
  2027) the percentages are **10.23 %** (regions) and **25.93 %** (municipalities), 1.5 % unchanged: the state keeps
  63.84 % and 62.34 %. They are the check (§7), because the bill's money is a 2027 flow. A version 18 from 1 January
  2028 (act 360/2025) exists and has not been read; it does not affect 2027.
- If the Státní závěrečný účet lines are already net of these transfers they are used as they stand; which is the case
  is read from the document and logged before any value is read (§2.9).

### 2.6 Inflation and real value

- **Source and cutoff.** The ČNB forecast published by **30 November 2026**: the autumn 2026 *Zpráva o inflaci* if it is
  out by then, else the summer 2026 one. Later publications are not used.
- **Annual average.** For each calendar year t the annual-average inflation is the mean of the four quarterly y/y values
  of consumer prices in the forecast path. A year not fully covered by the path takes 2.0 % for the missing quarters.
  After the horizon, 2.0 % (the ČNB target).
- **2025 and 2026.** 2025: the ČSÚ annual-average CPI inflation (published January 2026). 2026: the ČNB forecast value
  (ČSÚ's actual for 2026 is published in January 2027, after the cutoff, so it is not used). The same series is used in
  the valorisation sums of §2.2 and §2.3 and in the deflator.
- **Deflator.** Price level of year t = ∏ over 2027..t of (1 + π/100), with 2026 = 1. Nominal amounts of year t are divided
  by it. In Q-B amounts are nominal (today's fee at the 2026 level, the bill at its 2027 level); the bill's total
  deflated to 2026 prices is a check.
- **Sensitivity.** The whole inflation path ±1 percentage point in every year, forecast and 2.0 % part alike, in both
  paths' triggers and in the deflator.

### 2.7 Q-A path formulas

Let b be ČT or ČRo, m_b(t, k) the monthly fee in force in month k of year t (integer CZK, 150 or 159 or … for ČT; 55 or
59 … for ČRo), and S_b(t) = Σ_k m_b(t, k) over the 12 months (an integer; a step on 1 July gives 6 months at the old and
6 at the new amount).

- **Baseline A (primary).** R_b(2026) = the **fee-revenue line of the broadcaster's 2026 budget**. If a budget has no
  separate fee line, the broadcaster's baseline is baseline B for that broadcaster. 6.73 bn for ČT is the figure found in
  the feasibility research in ČT's 2026 budget PDF (§0); the rule reads the budget line again at snapshot and the figure
  does not decide it.
- **Baseline B (always computed, reported, in the range).** R_b(2025) = the realised fee revenue of 2025 from the 2025
  annual report, indexed by the legal fee path: R_b(2026) = R_b(2025) × S_b(2026) / S_b(2025), with S_b(2025) = 4 × (135 or
  45) + 8 × (150 or 55) from the statutory change of 1 May 2025, and S_b(2026) from the §2.2 rule (12 × 150, 12 × 55, unless
  a step falls in 2026). Payers are held at the 2025 level; the effect of the 2025 reform on firms is not separated.
- **Path 1 (current law).** Rev_1(b, t) = R_b(2026) × S_b(t) / S_b(2026).
- **Path 2 (bill with clause).** Rev_2(b, 2027) = the §10a(2) amount; Rev_2(b, t) the previous year's amount, with the +10
  % step of §2.3 where triggered.
- **Path 3.** Rev_3(b, t) = Rev_2(b, 2027).
- **Real values.** Σ over t = 2027..2030, b in {ČT, ČRo}, of Rev / price level(t). **X = Σ Rev_1 − Σ Rev_2** (real).

### 2.8 Snapshot, files and tags

Every source is fetched headless (`curl`, User-Agent "bsandova.com research", at most two requests at a time, no
circumvention of any bot check: a source that blocks is recorded as unavailable and the design is adjusted in a dated
change-log entry, not worked around). Files are saved with the date under the gitignored `tools/data/fees/` and hashed
into `docs/research/fees-files.sha256` before any computation. The hash file also holds the hashes of
`tools/fees/vat_map.csv` and `tools/fees/excise_map.csv`, committed in the snapshot commit before the consumption tables
are opened. The snapshot step writes only the raw files and the hash file; the outcome tables are not opened. Only their
layout (sheet names, row and column labels, no value) may be looked at, and only to make the decisions of §2.9.

Sources:

1. Sněmovní tisk 231/0 with the explanatory report, and the stage page.
2. Act 348/2005 Coll., the version from 1 January 2026, and any notice of the Ministry of Culture under §6(3).
3. ČT and ČRo budgets for 2026 and their annual reports for 2024 and 2025 (fee revenue, numbers of household payers if
   given, numbers of firm payers if given).
4. ČSÚ SILC 2025 tables (§2.4), including the tables by household type.
5. ČSÚ household consumption 2025, quintile tables by COICOP group.
6. State budget 2025 outturn by tax and social-insurance line (Státní závěrečný účet or Monitor státní pokladny).
7. ČNB inflation forecast (§2.6) and ČSÚ annual CPI inflation 2025.
8. Act 243/2000 Coll. versions 15 and 17, and act 110/2006 Coll. for the *životní minimum* amounts in force.
9. Counts of employers by size band (ČSÚ business register or ČSSZ), and VAT act 235/2004 for the rate map.

Files in the repository: `docs/research/fees-design.md` (this text), `docs/research/fees-files.sha256`,
`docs/research/fees-results.json`, `tools/fees/` (`fetch.py`, `parse.py`, `model.py`, `checks.py`, `vat_map.csv`,
`excise_map.csv`, `README.md`, tests on made-up inputs). Tags: `fees-design`, `fees-data-step`, `fees-code`.

### 2.9 Decisions that depend on the layout of a file

Which SILC table carries a mean total net household income column (§2.4), which PIT basis is available, whether a
senior cut is published, whether the reports give household payer counts and whether they are separate for TV and
radio, and whether the state-budget tax lines are gross or net of the transfers of §2.5 depend on the layout of the files.
Each is decided from **headings and labels only**, before any value is read, by the drafting assistant at the snapshot
step; the decision and its reason are logged as a dated entry in the change log of this design, in the snapshot commit.
The rules above say what each decision selects; none is decided from a number.

For orientation, ČSÚ's SILC 2025 publication page lists, by title: *Households by income decile distribution (per
person)*; *Households by income decile (modified OECD consumption unit)*; *Households by net income relative to living
minimum*; *Households by EU household type*, and the confidence-interval tables. Table numbers and column names are
confirmed at snapshot.

### 2.10 Open items to resolve at snapshot (none is guessed here)

1. **ČT's budget fee line** and ČRo's: read at snapshot (§2.7). Whether a separate fee line exists decides baseline A or B.
2. **A notice under §6(3)** already published for 2027 overrides the model's §6(2) path; if none, the model stands.
3. **Whether SILC deciles rank households by income per person or per consumption unit,** and the income year (§2.4).
4. **Whether the state-budget tax lines are gross or net** of the transfers (§2.5).
5. **Household payer counts** in the 2025 reports, and whether TV and radio are separate (§2.1).

## 3. Checks that flag the run

1. **Fee revenue today.** The household payments (payers × fee) plus the firm remainder equal the budgeted fee revenue
   of ČT plus ČRo for 2026 **by construction**, because the remainder is defined as what is left; this identity is only
   an arithmetic guard. The substantive test is that the **remainder is plausible**: it is not negative and lies inside
   the **schedule range** [Low, High]. Range: take the published counts n_b of employers in each size band b; for a band
   let m_min(b) and m_max(b) be the lowest and highest multiple of §5(3) among the legal classes that overlap it (0 for
   a band wholly up to 24 employees, 0 for a straddling band's minimum, the multiple of the highest overlapping class for
   its maximum; 500 employees in the class of 70 or 100, the higher); Low = Σ n_b m_min(b) × 205 × 12 and High = Σ n_b
   m_max(b) × 205 × 12 (CZK, at the 2026 monthly amounts, plus the vehicle-rental payments if their counts are published).
   Exempt institutions (§4(1)) are not removed, so High is an upper bound and Low may be too high. **If the remainder is
   not plausible,** the pre-specified response is: firms are reported only as the range [Low, High], the household payments
   are flagged **unvalidated** in every table and sentence, and the run goes on. There is no change of method and there
   is no 5 % tolerance; the earlier plan of a ±5 % band was dropped because the identity holds exactly, and a band
   around the remainder test would only soften it. If no employer counts exist, Low and High are not computed, firms are
   reported as the remainder only if non-negative, and household payments are flagged unvalidated.
2. **Allocation after (a guard on code and rounding).** The allocated total over households plus firms equals the bill's
   total, 7 807 592 000 CZK, **to the crown**, in the base scenario and in each scenario with a number, after
   largest-remainder rounding (§2.1). A difference is a coding or rounding error and **stops the run**.

## 4. Estimation and uncertainty

Everything is arithmetic on published aggregates; there is no sampling and no confidence interval. A published decile
table is itself an estimate with a sampling error, which ČSÚ gives in separate tables for some aggregates only, and a
model of it adds nothing that could be given an interval. The uncertainty is the **range over the scenarios**.

- **Q-A range (feeds the label):** inflation −1, 0, +1 percentage point; clause reading R1 and R2; baseline A and B. That
  is 12 members; the primary is (0, R1, A).
- **Q-B range (feeds the label):** the two exemption bounds E0 and E1 for Y. Z is the primary, the average tax structure;
  the VAT-only and PIT-only scenarios are reported beside it and do not feed the label.
- **Checks (reported, never feed a label):** §7.

A result that holds across the whole range is stated as it is; a result that flips is reported as **"depends on the
assumption"**, with the assumption named. The number reported is the primary specification's, and the range is given
beside it. The range is not a probability statement.

## 5. Power and precision

Not applicable in the sense of a test: the study has no sample to design for, which is why there are no confidence
intervals (§4). What takes the place of power is the width of the scenario range, which is known only after the run.
Two things are known now. First, in Q-B the burden ratio is a ratio of two decile means and is not sensitive to the level
of the total, so scale errors (the baseline, the payer share) move the CZK figures much more than the ratios. Second, the
quintile-to-decile split of consumption (§8) gives the two deciles of a quintile the same spending, so the burden ratio
between deciles 1 and 2, or 9 and 10, is driven by income alone there.

## 6. Labels

**Q-A**, by the sign of X over the 12-member range of §4, with a tie threshold of 0.1 bn CZK (2026 prices, cumulative
2027–2030):

- **bill lower** — X ≥ 0.1 in every member; **bill higher** — X ≤ −0.1 in every member; **about equal** — |X| < 0.1 in
  every member; **depends on the assumption** — anything else. Paths 2 and 3 coincide if the clause does not trigger by
  2030, and that is stated.

**Q-B**, with a "similar" band of [0.9, 1.1] for a ratio:

- **Today (range Y_lo = Y(E1), Y_hi = Y(E0)):** **the poorest tenth carries a higher share of its income than the richest
  tenth** — both bounds above 1.1; **a lower share** — both below 0.9; **a similar share** — both within [0.9, 1.1];
  **depends on the assumption** — anything else.
- **After (primary Z):** higher if Z > 1.1; lower if Z < 0.9; similar if within [0.9, 1.1].
- **Change, primary Z against both bounds:** **higher after** — Z/Y > 1.1 for both bounds; **lower after** — Z/Y < 0.9
  for both; **about the same** — Z/Y within [0.9, 1.1] for both; **depends on the assumption** — anything else. The
  extreme scenarios VAT-only and PIT-only are reported but do not enter the label, because a scenario that puts the whole
  total on one tax almost always gives a different sign from the other and so almost always gives "depends on the
  assumption"; the label is about the average tax structure.

There are no labels for firms, seniors, the CZK-per-household figures or the monotonicity note. Where the label of a
check (§7), computed by the same rules, differs from the primary label, both are reported and the text does not choose.

## 7. Checks reported (none feeds a label or relabels a primary result)

1. The window of the current-law valorisation starting with 2026 instead of 2025 (§2.2).
2. The bill's total deflated to 2026 prices in Q-B.
3. VAT with one uniform effective rate instead of the category map; "other taxes" allocated like VAT instead of dropped.
4. PIT by each of the three bases of §2.4 where more than one is available.
5. Payer share π = 1 instead of the report-based value.
6. Burden measured as the mean of household ratios if the tables give it, not the ratio of means.
7. The sharing percentages of 2026–2027 (version 17: state share 63.84 % and 62.34 %) applied to gross lines instead
   of those of 2025 (version 15).
8. Seniors' cut, descriptive, if the tables publish one.
9. **Reverse-direction checks** (each pushes the other way from the main simplifications, §8): (a) social insurance
   contributions included in the pool, allocated by the decile share of gross income, the ceiling on contributions not
   modelled; (b) CIT attributed 50 % to households in proportion to net income, 50 % to firms; (c) within-quintile
   piecewise-linear interpolation of consumption instead of the equal split (a quintile's value is placed at its
   midpoint, decile positions 1.5, 3.5, 5.5, 7.5, 9.5, flat beyond the ends, rescaled so each pair of deciles averages
   to its quintile's value); (d) no exemption for any decile (E0, which is already the upper end of Y).

## 8. Limits stated now

Direction is given relative to the author's stated position (she favours keeping and raising the fee): a simplification
**favours** that position if it makes the fee look less regressive (a lower Y), makes budget funding look more regressive
(a higher Z) or makes the bill look less generous (a higher X), and works **against** it if it does the opposite. Where the
direction is not known, that is said.

- **Modelled, not measured, deciles.** There is no microdata (the SafeCentrum is not available); tax and fee burdens by
  decile are built from published decile and quintile aggregates under assumptions. Direction: none.
- **Quintile to decile split.** Both deciles of a quintile get the same spending per household. The lower decile of a pair
  then shows a higher burden and the higher one a lower burden than a true split would, which leans towards a regressive
  reading of consumption taxes: raises Z, **favours** her position. Check 9(c).
- **Different years.** SILC income refers to a year before 2025, consumption and tax outturn to 2025, the fee to 2026 and
  the bill to 2027; nothing is re-based except what §2.6 says. Direction: none known.
- **Exemptions are estimated by entitlement.** The exempt share is the entitlement under §4(2); in fact a declaration is
  needed and lapses after 6 months (§4(3)), so the true exempt share is lower. The upper bound E1 therefore lowers Y: it
  **favours** her position, and E0 works **against** it; both are in the range. SILC income is annual, the law tests the
  last calendar quarter. The *životní minimum* of the household composition is approximated.
- **Standard, not measured, incidence.** That CIT stays with firms (removes a possibly proportional or progressive part
  from households: raises Z, **favours**), that VAT and excise fall on household consumption entire (an upper bound of
  their share; raises Z, **favours**), and that PIT falls on those who earn the income, are textbook assumptions. Checks
  9(b) and 3.
- **Social insurance excluded** from the pool. If contributions are capped for high earners, including them would make the
  burden more regressive (raise Z); excluding them therefore **works against** her position, in expectation; the sign is
  not known. Check 9(a).
- **Payers held fixed in the current-law path** raises that path and so X: **favours** her position. The baseline B is
  indexed by the legal fee path only and the effect of the 2025 reform on firms and public bodies (re-registration,
  the new schedule) is not separated; direction unknown.
- **One average payment per household** instead of the cases 0 / 55 / 150 / 205 CZK a month: direction unknown, the level
  of payments only.
- **Headcount for full-time equivalents**, firms with 24–25 employees and exactly 500 employees in the schedule range
  (§2.2, §3): affects the firm range only.
- **A tax-financed contribution is not a tax increase.** The allocation answers "who bears the cost if it is spread like
  the existing taxes"; the government may fund it by a different mix, by debt, or by cutting other spending (the debt
  scenario is a sentence for that reason).
- **Firms are not like for like.** Today's figure is a remainder including public bodies; the after figure is the CIT
  share. They are not comparable and the article says so in the same sentence as the figures.
- **The coalition proposal of May 2026** (more exemptions) is a separate bill and is out of scope, as is any other
  amendment of the fee.
- **The bill may change in committee**, including its amounts, its valorisation clause and its effective date (it takes
  effect on 1 January 2027 as introduced; the comparison keeps the window 2027–2030 whatever happens). The article says
  "as introduced". The explanatory report also says the European Commission will be asked whether the funding is state
  aid; that is not modelled.
- **Correlation is not the question and causation is not claimed.** Nothing here concerns the independence, quality or
  reach of public broadcasting, or what the broadcasters would do with the money.

## 9. Outputs

An article on bsandova.com: the three paths of Q-A with the headline sentence and its range; the **aggregate level
comparison** (the budgeted fee revenue of 2026 against the bill's 7 807 592 000 CZK, at the same prices; reading C); the
burden by decile today and after with the ratios Y and Z and the monotonicity note; firms as one aggregate with the
sentence of reading B; seniors only as a descriptive cut if published; and a plain account of what the model cannot see.
The one-line disclosure of the author's position is in the methods note. Machine output in
`docs/research/fees-results.json`.

## Running and verification

Code in `tools/fees/` (fetch, hash, parse, model, checks) with tests on made-up inputs only; commands and the verified
facts about each source, with dates, in `tools/fees/README.md`. Order: design, tag `fees-design` → snapshot and
`docs/research/fees-files.sha256` (with the layout decisions of §2.9 logged) → data-step code (parsers), tests on made-up
files, tag `fees-data-step` before it opens any outcome table → estimation code, tests, tag `fees-code` → run →
`docs/research/fees-results.json` → article. The run refuses to start if a hashed file has changed, or if the tag is not
on HEAD with `tools/fees/` unchanged since. Check 2 of §3 runs with every allocation.

## Change log

- 3 November 2026: design committed, before any outcome table was opened. Facts verified the same day from the legal
  texts: the bill's amounts differ from the figures first quoted (§2.3: ČT 5 741 826 000 and ČRo 2 065 766 000 CZK,
  7 807 592 000 in all), the bill's clause is 10 percentage points (not 10 %) from 2026 with a step of +10 %, and the
  current-law rule is 6 % when the sum of inflation since the last increase exceeds 6 %, from 1 July.
- 3 November 2026, after an independent review of the design, before the tag `fees-design` and before any outcome table
  was opened. Every decision is pinned here:
  - **Legal.** (L1) The remark that the clause is void if read literally is deleted; "průměrná roční míra inflace" is
    ČSÚ's term for annual-average CPI inflation, and R1 (sum) and R2 (compounded) are two readings of "kumulativní"
    over the same years, with both wordings of the explanatory report quoted (§2.3). (L2) After an increase effective in
    Y+1 the bill's window restarts at Y, as the text says; current law's restarts at the year of the increase; second
    triggers are computed, not errors. (L3) Integer or exact-decimal arithmetic for every ceiling and rounding;
    largest-remainder rounding for every allocation (§2.1). (L4) The version history of act 348/2005 was read: the last
    increase is **1 May 2025** (act 119/2025 Coll., Čl. VI point 9: ČT 135 → 150, ČRo 45 → 55 CZK, together with the
    introduction of the §6(2) rule); this resolves the former open item on the date; 119/2025 is recorded as a candidate
    explanation of 6.73 bn against 5.742 bn, without changing the baseline rule. (L5) The 2025 outturn is governed by
    version 15 of act 243/2000 (regions 9.45 %, municipalities 24.16 %, in force through all of 2025, so no change in the
    year); versions 16–17 (10.23 % and 25.93 %) are a check. (L6) The household cases 0 / 55 / 150 / 205 CZK are averaged
    through payer shares; the 24–25 employee gap and exactly 500 employees are handled in the firm range (§2.2, §3).
  - **Forks.** (1) Baseline A the budget fee line (or baseline B for a broadcaster without one), baseline B always
    computed and in the range; the origin of 6.73 bn recorded as the feasibility research. (2) As L2. (3) Exemption bounds
    E0 and E1 by the decile rule on the mean net income against 2.15 × the *životní minimum* of the mean household,
    applied to every decile; if no decile is exempt, decile 1 is. The SILC tables are named by title (§2.4, §2.9), the
    numbers to be confirmed at snapshot. (4) Layout-dependent branches are decided from headings only, by the assistant at
    the snapshot step, logged in the snapshot commit. (5) The fallback is the modified OECD scale, the mean equivalent
    size per decile reported. (6) The ČNB cutoff is 30 November 2026, annual averages are means of the quarterly y/y path,
    and 2026 is the ČNB value (ČSÚ publishes in January 2027). (7) The firm range is defined explicitly in §3. (8) One
    payer-share concept for Q-A and Q-B (§2.1).
  - **Structure.** (M2) What is in the label range and what is a check: Q-A, inflation, R1/R2 and both baselines; Q-B,
    the exemption bounds; everything else is a check; the §4 reference is corrected (to §7); the house sentence on
    differing check labels added (§6). (M3) The Q-B primary is the average state-budget tax structure (the author's
    choice); VAT-only and PIT-only are sensitivity scenarios and do not enter the label; reading B has Y as a range and
    Z as the primary. (M4) Check 1 is stated as holding by construction, the substantive test is the plausibility of the
    remainder, the response to failure is a range plus an "unvalidated" flag; the ±5 % tolerance of the earlier plan is
    **dropped** (it was in the brief agreed with the author and is dropped on the reviewer's advice; the identity holds
    exactly); check 2 is a guard on code and rounding. (M5) Directions of every simplification stated against the author's
    position (§8), reverse-direction checks added (§7, 9), the article's disclosure becomes "will carry", in its methods
    note. (M6) Labels renamed ("carries a higher / lower / similar share of its income"), the "similar" band pinned at
    [0.9, 1.1], a monotonicity note added, the entitlement caveat placed in reading B. (M7) The aggregate level
    comparison added to the outputs and as reading C. (M8) The firm figures carry the not-like-for-like sentence.
  - **Nice-to-have.** (N1) Tie threshold of 0.1 bn CZK for Q-A. (N2) Path formulas with half-year July steps (§2.7). (N3)
    Wording of reading A when the label is "depends on the assumption". (N4) Background known from feasibility research
    recorded in §0. (N5) `vat_map.csv` and `excise_map.csv` are hashed in the snapshot commit before the consumption tables
    are opened. (N6) The review item numbered N6 was empty and nothing was done under it. (N7) The seniors' claim of about
    40 % is dropped as a test; the seniors' cut is descriptive. (N8) Typographical corrections, "annual" throughout.
    Readability: the Q-B incidence rules moved to §2.4, a file list and a definition of "payer" added, and the tag
    `fees-data-step` added between snapshot and code.
