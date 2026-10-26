# Czech road bypasses: treatment and comparison list

`bypasses.csv` lists Czech road bypasses (obchvaty) that opened to traffic between 2007-01-01 and 2026-10-15 (treatment) and bypasses that were not open on 2026-10-15 (comparison). It covers class D and I roads (built by ŘSD) and class II and III roads (built by the regions). It is built from construction facts only: what was built, where, when works started, when it opened, road class and length. No accident data, no traffic counts and no safety records were opened, downloaded or used as an inclusion or exclusion criterion. Some leaflets, press releases and regional documents contain sentences about traffic or accidents; none of that was read into the file. Two near-misses are described under "Blinding".

Data cut-off: 2026-10-15. ŘSD leaflets are quoted in their latest version (most say "stav k 09/2026" or "10/2026").

The list was built in two passes. The first pass (rows BYP-001 to BYP-114) covered class D and I bypasses opened 2016-2026 and planned ones. The second pass (rows BYP-115 to BYP-333, October 2026) added class D and I bypasses opened 2007-2015, class II and III bypasses opened 2007-2026 and planned, further planned ŘSD bypasses, and geometry. Existing ids were kept; new rows are numbered from BYP-115, opened rows first by date, then planned rows by stage.

## Method

1. **Class D and I, 2016-2026 and planned** (first pass): ŘSD overviews (ministry-hosted maps of completed works 2014-2017, works under construction 2018-2019, planned openings 2023-2024, the 2020 list of projects in preparation, the 2026 regional construction maps on kraje.rsd.cz) and the ŘSD press archive from mid-2025 to October 2026, each entry verified on the ŘSD per-stavba leaflet (`letaky.rsd.cz`) or an ŘSD or ministry press release.
2. **Class D and I, 2007-2015** (second pass): every ŘSD annual report 2007-2015 (`rsd.cz/documents/38144/79710/RSD_VZ_<year>.pdf`, lists of works put into operation), the ministry map of completed works 2014-2017, ŘSD press releases 2006-2015 recovered from the Wayback Machine, old ŘSD leaflets (`apdos.roadmedia.cz/Upload/Stavby/...`), and ŘSD's APDOS project dataset (`apdos.roadmedia.cz/data/linestring-stavba.json`, 680 projects with status, dates, leaflet links and line geometry), screened for every project in use that finished 2006-2015. The OP Doprava 2007-2013 list of beneficiaries was checked item by item.
3. **Class II and III, 2007-2026 and planned** (second pass): for each of the 13 regions outside Prague, (a) the EU lists of operations, which are systematic: the 2007-2013 final list of beneficiaries (dotaceeu.cz, 11/2016; ROP NUTS II and OP Doprava), the IROP/OP Doprava 2014-2020 list of operations (10/2026) and the 2021-2027 list (10/2026), searched for "obchvat" and "přeložk" in project names and summaries; (b) the regional road authority's and the kraj's news archives, investment plans, budgets and project stacks; (c) regional press where the search budget allowed. Per-region coverage is under "Coverage of class II and III".
4. **Planned ŘSD bypasses**: the APDOS dataset was screened for every project with "obchvat" or "přeložka" in its name; projects missing from the list were added from their leaflets (14 planned rows: BYP-231, 258-262, 273-280; `notes` cite the APDOS record). The same check added I/44 Vlachov - Rájec, the 2014 bypass of Zvole (BYP-177). Projects at study stage with no approved záměr were not added.
5. Opening day = the day the stage opened to traffic as stated by ŘSD, the kraj or its road authority ("slavnostní zprovoznění", "uvedení do provozu"). Where traffic started earlier than the ceremony, the earlier day is used and `notes` says so. EU-list end dates and kolaudace dates are not opening days; a few class II/III rows have only a year from such a date and are `low`.
6. Municipality codes are RÚIAN kód obce (= ČSÚ 6-digit code), from Wikidata P7606, matched by name and, for duplicated names, by district or position. A blank code means the place is a part of a municipality (the parent is named in `notes` where known), not that the code is unknown.
7. `date_precision` is `day`, `month` or `year`.
8. Wikipedia was not used as a source.

## Columns

| Column | Meaning |
|---|---|
| `id` | BYP-nnn. 001-114 from the first pass, 115-333 from the second (opened by date, then planned by stage) |
| `town`, `municipality_code` | Municipality or municipalities served; several are separated by `; ` and the codes line up with the names |
| `road`, `road_class` | Road number as built and class (`D`, `I`, `II`, `III`). Two class II rows have no road number in any source (Zákupy, Králův Dvůr stage II) |
| `project_name` | Name as the builder uses it |
| `status` | `opened` or `planned` |
| `opened_date`, `date_precision` | Opening day to traffic |
| `construction_start` | Start of works (YYYY-MM-DD, YYYY-MM or YYYY); empty if not found or not started |
| `length_km` | Main route length |
| `kind` | `full`, `partial`, `relocation`, `motorway_section` (below) |
| `old_route` | Road or street through the town that the bypass relieves |
| `stage` | Opened rows: which stage of a multi-stage bypass. Planned rows: `in construction`, `tender`, `SP` (building or joint permit issued), `ÚR` (zoning decision issued), `pre-ÚR (EIA/záměr)`, or `preparation (stage not stated)` when the regional source only says the project is being prepared |
| `completes_bypass`, `carries_through_traffic` | Opened rows only. Whether this stage completes the bypass, and whether the stage as opened carries the through traffic of the old route. Judgements from the builder's description; where no source says, `no` is entered and `notes` says so |
| `expected_opening`, `as_of` | Planned rows only: expected opening in the latest source and the date of that source |
| `start_lat`, `start_lon`, `end_lat`, `end_lon`, `osm_ways` | Geometry (WGS84). See "Geometry" |
| `source_urls`, `confidence`, `notes` | Sources, `high`/`medium`/`low`, free text |

### How `kind` was assigned

- `full`: the builder or the press calls the work an obchvat, or the leaflet describes a new road that takes the through traffic of the road past one side of the built-up area entirely, and the opened stage completes it.
- `partial`: the stage, or the whole project, covers only one side or part of the town, or is one stage of a multi-stage bypass that does not yet take the whole through traffic.
- `relocation`: the builder calls it a přeložka and no source describes it as a bypass of a named town.
- `motorway_section`: a D-class section (R-class before 2016) that bypasses a named town (ŘSD "obchvat" in the name, or ŘSD says it relieves the town).

The assignment follows the builders' naming and descriptions; route geometry was not used to decide `kind`. Borderline cases are flagged in `notes`. Precedents are not fully consistent: some ŘSD "přeložky" that the press calls obchvat are `full` (Staňkov, Olbramovice, Zvole) and one is `relocation` (Horní Lukavice). The design (`docs/research/bypass-design.md` §2) defines `full` for class I and II roads and motorways; four opened class III rows are `full` and need a decision there.

## Counts

Opened, by year of opening, road class and kind (171 rows; "D motorway" = `motorway_section`; columns with no rows are left out):

| Year | D motorway | I full | I partial | I relocation | II full | II partial | II relocation | III full | III partial | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| 2007 | 1 | 4 | 1 |  |  |  |  |  |  | 6 |
| 2008 | 4 | 5 |  |  |  | 1 |  |  |  | 10 |
| 2009 | 1 | 3 | 1 |  | 3 |  | 1 |  |  | 9 |
| 2010 | 2 | 5 |  |  | 2 | 2 |  | 1 |  | 12 |
| 2011 |  | 6 | 1 |  |  | 1 | 1 | 1 |  | 10 |
| 2012 |  | 3 |  |  | 1 | 1 |  |  | 1 | 6 |
| 2013 | 1 | 2 |  |  | 1 | 1 |  |  | 1 | 6 |
| 2014 |  | 2 |  |  | 1 | 1 |  |  |  | 4 |
| 2015 |  |  | 1 | 2 | 4 | 1 | 1 |  |  | 9 |
| 2016 |  | 3 | 1 |  |  |  |  |  |  | 4 |
| 2017 |  | 2 |  |  |  |  |  |  |  | 2 |
| 2018 |  | 1 | 1 |  | 2 |  |  |  |  | 4 |
| 2019 |  | 3 | 2 |  | 2 |  |  | 1 |  | 8 |
| 2020 | 2 | 2 |  |  | 4 | 3 |  |  |  | 11 |
| 2021 | 2 | 2 | 2 |  | 5 | 2 |  |  |  | 13 |
| 2022 | 2 | 3 | 1 |  | 3 | 2 |  |  |  | 11 |
| 2023 |  | 5 | 2 | 2 | 6 | 1 |  | 1 |  | 17 |
| 2024 | 3 | 2 | 1 | 1 | 4 | 1 |  |  |  | 12 |
| 2025 | 3 | 3 | 2 |  | 3 | 1 |  |  |  | 12 |
| 2026 (to 15 Oct) |  |  | 2 |  | 1 | 2 |  |  |  | 5 |
| All | 21 | 56 | 18 | 5 | 42 | 20 | 3 | 4 | 2 | 171 |

`full` bypasses opened 2008-2024: 49 class I, 38 class II, 4 class III (91). Date precision of opened rows: 146 day, 10 month, 15 year.

Planned, not open on 2026-10-15 (162 rows), by stage and class:

| Stage | D | I | II | III | Total |
|---|---|---|---|---|---|
| in construction | 1 | 12 | 13 | 1 | 27 |
| tender | 0 | 6 | 1 | 0 | 7 |
| SP | 1 | 4 | 9 | 2 | 16 |
| ÚR | 1 | 16 | 9 | 1 | 27 |
| pre-ÚR (EIA/záměr) | 0 | 32 | 23 | 4 | 59 |
| preparation (stage not stated) | 0 | 0 | 25 | 1 | 26 |
| All | 3 | 70 | 80 | 9 | 162 |

Confidence over all 333 rows: 117 high, 131 medium, 85 low. Most low rows are regional planned projects whose stage is inferred or not stated, and class II/III openings with only a year.

## Coverage of class II and III

Class II and III rows by region (Prague is not covered):

| Region | Opened 2007-2015 | Opened 2016-2026 | of which `full` | Planned |
|---|---|---|---|---|
| Středočeský | 1 | 13 | 7 | 36 |
| Jihočeský | 1 | 5 | 5 | 14 |
| Plzeňský | 5 | 3 | 6 | 3 |
| Karlovarský | 6 | 2 | 6 | 3 |
| Ústecký | 0 | 2 | 1 | 1 |
| Liberecký | 3 | 1 | 1 | 0 |
| Královéhradecký | 0 | 4 | 3 | 3 |
| Pardubický | 1 | 3 | 4 | 3 |
| Vysočina | 5 | 8 | 9 | 10 |
| Jihomoravský | 1 | 2 | 3 | 3 |
| Olomoucký | 2 | 1 | 1 | 5 |
| Zlínský | 1 | 0 | 0 | 4 |
| Moravskoslezský | 1 | 0 | 0 | 4 |

In every region the EU lists of operations (2007-2013, 2014-2020, 2021-2027) were read in full for "obchvat" and "přeložk", so EU-co-financed bypasses are complete by that criterion. Regionally or state-funded (SFDI) bypasses depend on what each region publishes, and that differs:

- **Středočeský**: KSÚS news read in full from 2020-01 (567 posts), cross-checked with the kraj's 2020 list of 37 bypasses, the KSÚS project-priority export (05/2026, construction columns only) and the kraj's EU project stack (09/2026). 2020-2026 close to complete; 2014-2019 moderate to good (kraj site search); **2007-2013 weak** (ROP list, kraj investment plans 2009-2012 by name only, sparse Wayback archive). No regional press search. Planned stages are often inferred (flagged in `notes`), and many planned rows are `low`.
- **Jihočeský**: kraj news archive read in full (10/2018-10/2026), kraj construction portal and 2025 investment programme for planned rows. Openings 2018-2026 complete; **non-EU openings 2007 to mid-2018 not covered** (road authority site gone, kraj archive starts 10/2018).
- **Plzeňský**: all 65 ROP projects of SÚS PK, all 308 SÚS PK posts and annual works lists 2017-2025. 2015-2026 good; non-EU 2007-2014 gap (kraj archive behind a CAPTCHA). Planned rows come only from the SÚS PK 2026 design plan (names, no stage).
- **Karlovarský**: kraj full-text search back to 2004, road authority news from 2022. Estimated about 90 % of openings; planned rows may be incomplete (the kraj 2028-2034 preparation plan was not found).
- **Ústecký**: kraj press releases 2009-2026 (about 8 700) screened by title only; road authority has no news. About 90 % for 2018-2026, about 75 % for 2009-2017; 2007-2008 not covered.
- **Liberecký**: kraj full-text search back to 2004; a kraj FOI answer (Informace 58/2016) says Chrastava stage III was its only new road 10/2012-08/2016. High, except bypasses built by towns and later taken over by the kraj.
- **Královéhradecký**: kraj news archive read in full (2014-03 to 2026-10), road authority news about 2019-2026, 2026 construction and budget lists, E-ZAK tenders. Close to complete from 2014; 2007 to early 2014 only by press search. The opened rows are dominated by the state-funded Solnice-Kvasiny package.
- **Pardubický**: SÚS Pk news (sparse before 2019), the kraj transport project dataset (332 projects, mostly from 2020) with leaflets. 2010-2026 complete (Pardubický deník, 2021-09-14, calls Kojice the kraj's first new road since Chvaletice 2010); 2007-2009 nothing found, probably complete. The 2020s rows are D35 feeder roads.
- **Vysočina**: every kraj press-release title from 2022 (2 752), budgets 2025-2026 and plan 2026-2028; for 2009-2021 one Wayback query for kraj pages with "obchvat" or "přeložka" in the address (about 95 releases). 2022-2026 complete, 2009-2021 probably complete, **2007-2008 weak**. Study-only projects (Chotěboř, Nové Město na Moravě, Humpolec) not covered.
- **Jihomoravský**: road authority project database (about 1 300 completed projects from 2007) and its completed-works lists 2009-2025, kraj news 2019-2026. Close to complete for bypasses the road authority built; town- or developer-built ones only partly. Opening days are weak (one row has only the year the works ended).
- **Zlínský**: road authority completed-works table for every year and its news archive 2015-2026. Close to complete for the road authority's own works; it built almost no new II/III bypasses.
- **Olomoucký**: kraj press archive 2011-05 to 2026-10 (about 5 450) by title; ROP/IROP pages; regional action plan 2024 and investment overviews 2023-2026 for planned rows. From mid-2011 probably complete; **2007 to mid-2011 only ROP-funded projects**.
- **Moravskoslezský**: ROP projects checked one by one (including the bundled "Silnice 20xx" projects), the road authority's "Bílá kniha" bypass group for every edition 2013-2025, all road authority news 2020-2026 and kraj press releases 2021-2026. Complete for EU-funded and kraj-pipeline bypasses 2013-2026; **2007-2012 only ROP-funded**.

Common biases: (1) EU-co-financed and recent projects are better covered than regionally funded ones before about 2014; (2) bypasses built by towns, developers or industrial-zone programmes and later handed to the region are covered only when the region announced them; (3) the WebSearch budget of the second pass ran out early, so regional press (Deník, iDNES) was not searched systematically in most regions. The class II/III sample should be treated as a convenience sample with known gaps, not a census, especially for 2007-2013.

## Coverage of class D and I

- 2016-2026: as in the first pass (ŘSD overviews, leaflets, press).
- 2007-2015: every ŘSD annual report was read; the annual reports list only significant works, so they were combined with every APDOS project put into operation 2006-2015 and with the ŘSD press archive. 2014-2015 complete (completed-works map). 2008-2013 close to complete for works with an ŘSD leaflet; small SFDI-only class I relocations without a leaflet may be missing. 2007 is thinner.
- Planned: every APDOS project in preparation or under construction with "obchvat" or "přeložka" in the name was checked.

## Geometry

Opened rows with start/end coordinates: 92 of 171; with `osm_ways`: 57.

- **OpenStreetMap** (current data via Overpass, 2026-07 to 2026-10): for 49 of the first-pass rows and a few class II rows. The bypass is the chain of ways with the road's `ref` between the two junctions where it leaves and rejoins the old route (which OSM usually re-refs as a class II/III or `xxH`/`xxJ` road); where the old road is no longer mapped, the ends follow the leaflet's description of the start and end, node age, or ŘSD chainage. Dual carriageways list both directions in `osm_ways`; start and end are on one carriageway (named in `notes`). Six rows differ from `length_km` by more than 25 % (BYP-001, 004, 009, 025, 028, 030), mostly because the stavba length includes approach sections; this is said in `notes`.
- **ŘSD APDOS lines**: where OSM could not separate the new road from the old one, or Overpass was unavailable, start and end are the end points of the ŘSD APDOS line of that stavba (`notes`: "end points of the ŘSD APDOS line of stavba N"). These are construction limits, not junctions, and `osm_ways` is empty. For BYP-011 and BYP-033 (Opava north bypass) the APDOS lines are longer than `length_km`.
- Left blank: most class II/III rows (Overpass refused connections for most of the second pass), BYP-016's own geometry where noted, and any row where neither source was clear. Planned rows have no geometry.

## Towns with several rows

Staged bypasses have one row per stage. Towns with several rows: Opava (nine rows across I/11, I/46, I/57, II/461 and the 2009 S1 link), Mělník, Znojmo, Pardubice, Sezemice, Frýdek-Místek, Havlíčkův Brod, Krnov, Klatovy (also III/0228 north-west), Česká Lípa, Rychnov nad Kněžnou, Příbram, Řevničov, České Budějovice, Chrudim (stage 1 2015, stage 2 2021), Nymburk (2007, 2010), Kroměříž (two D1 sections), Bohumín (two parts), Jihlava (I/38 south 2008, II/352 Heroltice 2010, II/602 south-east in two parts), Sokolov (three class II rows), Chrastava (three stages), Kaplice, Králův Dvůr, Opočno, Jesenice, Roudnice nad Labem, Prostějov, Brandýs nad Labem-Stará Boleslav, Čelákovice, Rakovník, Tábor, Lysá nad Labem, Uničov, Horní Počaply. Bypasses serving two or more municipalities have all of them in `town`.

## Exclusions and reasons (construction facts only)

- Capacity or widening of an existing bypass: D7 Panenský Týnec (2021-12-16), D7 Louny, D7 Postoloprty (planned), I/9 Nový Bor-Svor (2024-07-04), I/16 Jičín (planned), I/37 Hrobice-Ohrazenice (second carriageway, 2012), D56 Frýdek-Místek connection (2022-09-02).
- Relocations that no source describes as bypassing a named town: I/21 Trstěnice-Drmoul (2020-06-04), I/34 Rouštany-Pohled (2018), I/16 Slaný-Velvary stage II (2020-09-21), I/14 Kunratice-Jablonec and I/62 Děčín-Vilsnice (2018), I/16 Martinovice link and I/43 Černá Hora relocation (under construction), I/44 Mohelnice-Vlachov (planned), I/49 Malenovice-Otrokovice, I/35 Valašské Meziříčí-Lešná stage 2, D3 connector to Český Krumlov (2026-08-28, borderline); class II/III: Číměř II/128, Trocnov II/155, Železná Ruda-Špičák II/190, Černovice III/19351, Vendryně III/4682, Šenov III/4701, Palkovická III/4848 Frýdek-Místek (2021; the IROP summary calls it an "obchvatová trasa" but no town is named), Brložec-Lažany II/207, Kojátky II/431 (realignment near the village), Běloves-Velké Poříčí II/303 (under construction).
- The I/21 Nová Hospoda-Kočov relocation, excluded in the first pass, now has a row for its first stage (2011), whose leaflet says it bypasses Kočov.
- Urban relocations and connectors, not town bypasses: II/156+II/157 relocation in České Budějovice (stages 1-6), Jižní tangenta České Budějovice, Úpice III/3012 (realignment in the town centre), Liberec "obchvat průmyslové zóny Jih", Litoměřice II/247 feeder (2009). Motorway sections that ŘSD does not name as a bypass or describe as relieving a named town: D3 Tábor-Veselí, R7 Vysočany-Droužkovice, R48 Rychaltice-Frýdek-Místek, D6 Lubenec-Bošov, R6 Nové Sedlo-Sokolov, D47 Bohumín-border, D11 (including Smiřice-Jaroměř, 2021-12-17), D35 Ostrov-Vysoké Mýto (2026-08-21), other D1, D3, D4, D46, D48, D49, D52 and D55 sections. Prague ring SOKP 512-514 (2010-09-20) excluded as the capital's ring road.
- Reconstruction through a town, not a bypass: I/55 Přerov průtah (2022-10-31), I/53 Dobšice průtah (2018), I/38 Hrdlořezy-Čistá (2015), Nové Sedlo-Chranišov II/209, Hartoušov III/21217, I/55 Kunovice průtah (2022), most "průtah" projects in the EU lists.
- Not open by the cut-off: Svor (expected 2026-11), Bruntál east stage I, Opava Hradecká-Olomoucká, Sezemice remainder, Veselov II/205 (first part reopened 2026-09-29 but the section past the village is closed), Drahelčice II/101; all are planned rows.
- Dropped for missing facts: Dobrovíz (developer-built 1.4 km road opened 2015-12-21; road number and class not found), Benátky nad Jizerou II/272 link (no opening notice; works from 2023-04-11), Beroun southern parallel road stage I (prepared by the town; road class not stated), Planá nad Lužnicí II/409 (ROP 2007-2013, no description or date found), I/55 Kunovice-Hodonín district boundary (ŘSD annual report 2012; nature unverified), I/16 Sobotka (OP Doprava 2007-2013; dates and cost suggest renovation), a 2012 Solnice segment (road number when opened not confirmed), Vítkov II/442 stage II (stopped 2017), Melč III/44337 (preparation not started).
- Planned without a concrete status dated 2023 or later, or study only: I/13 Frýdlant, I/17 Chrudim north, I/11 Žamberk, I/15 Liběšice, I/15 Zahrádky (negative EIA opinion 2024-02-27), I/11 Kostelec nad Orlicí, I/14 Česká Třebová, I/14 Trutnov west, I/13 Bílina, Kunovice (I/50-I/55), Olomoucký kraj intentions (Vícov, Ptení, Hranice north-east, Přerov south-west, Kojetín part 2), Ústecký kraj 2010 programme (Libochovice, Jiřetín pod Jedlovou, Podbořany, Siřejovice, Šluknov), Litoměřice west, Úvaly-Říčany II/101 (borderline, one of two permits), and Vysočina budget lines without description (Bořínov, Rouchovany, Humpolec).

## Fixes to first-pass rows (2026-10-15)

- BYP-031: municipality code 506711 was Dolní Lhota in Ostrava-město; the bypassed Dolní Lhota is a part of Stráž nad Nežárkou, so the code is now blank.
- BYP-077, 085, 095, 112: notes said Babylon, Rybnice, Stvolínky and Vrchy have no municipality code; they are municipalities and the codes in the row are right. BYP-006: Myslotín is a part of Pelhřimov. Parent municipalities added for Lvová, Hněvkov, Skrochovice and Vavřineč.
- BYP-054: a quoted traffic sentence was removed from `notes` (blinding rule).
- BYP-024: opened_date 2022-09-02 (ceremony) changed to 2022-06-30, when part of the stage opened to traffic, per rule 5.
- BYP-045: construction_start 2019-04-17 (ceremony) changed to 2019-04-23 (start of works, leaflet). BYP-016: construction_start was copied from the neighbouring stavba; now 2018 from the APDOS record of this stavba. BYP-051: construction_start to the day (2022-12-20).
- BYP-005: the Liberecký kraj release of 2017-06-29 now confirms the date. Notes added to BYP-009 (works first started 07/2007), BYP-020, BYP-025, BYP-039 (the kraj gives 2024-02-08 for first traffic), BYP-066 (also bypasses Otice) and BYP-023 (stage 1 is now its own row).

## Blinding

No accident or traffic data was used. Two incidents in the second pass, both reported by the agents that ran them:

- Středočeský kraj: while its structure was inspected, the kraj's 2025 prioritisation table (`TABULKA PRIORITIZACE AKCÍ`) printed its header and six bridge and repair rows, none of them a bypass, including traffic-load and accident-locality scores. The table was not used. From the KSÚS project-priority export only construction columns were read.
- Liberecký kraj: a 2009 kraj study ranking candidate bypasses turned out to use traffic and safety criteria; reading stopped when that was seen and it was not used for any row.

## Open items

- Opening day versus first traffic: see `notes` for Krnov, Frýdek-Místek stage I, Sezemice, Třemošná, Kočov, Božejov, Líbeznice, Česká Skalice, Holešov, Prostějov, Kaplice, Osek and Opočno.
- Month-only and year-only openings: 25 rows, mostly class II/III (`date_precision`).
- Planned stages for regional projects are often inferred from budget or project-stack entries; 26 rows have `preparation (stage not stated)`.
- Possible D/I gaps found by the regional passes: I/44 Zvole (2014) and the planned ŘSD bypasses in APDOS were added. Not added: the I/14 Solnice north-west part (under construction by the kraj for ŘSD; no ŘSD leaflet found).
- ŘSD press pages for Velemyšleves (2016-11-22) and Lhotsko are no longer retrievable; those dates rest on titles seen in search results and the ŘSD completed-works map.
