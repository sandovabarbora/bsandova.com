# Czech road bypasses: treatment and comparison list

`bypasses.csv` lists Czech road bypasses (obchvaty) opened to traffic between 2016-01-01 and 2026-10-15 (treatment) and bypasses that were not open on 2026-10-15 (comparison). It is built from construction facts only: what was built, where, when it opened, road class, length. No accident data, no traffic counts and no safety records were opened, downloaded or used as an inclusion or exclusion criterion. Some ŘSD leaflets and press releases contain benefit sentences about traffic or accidents; none of that was read into the file.

Data cut-off: 2026-10-15. ŘSD leaflets are quoted in their latest version (most say "stav k 09/2026" or "10/2026").

## Method

1. Candidate lists came from ŘSD overviews: the ministry-hosted maps of completed works 2014-2017, projects under construction 2018-2019, planned openings 2023-2024, the 2020 list of projects in preparation, the 2026 regional construction maps (kraje.rsd.cz), and the archive of ŘSD press releases (rsd.cz, md.gov.cz) from mid-2025 to October 2026. The 2020 list is a map-style PDF and was used only as a pointer.
2. Each entry was then verified on a primary page: the ŘSD per-stavba information leaflet (`letaky.rsd.cz`, which gives construction start, ceremonial opening and expected opening), or an ŘSD or ministry press release. Opening day = the day ŘSD states the stage or section opened ("slavnostní zprovoznění", "zprovozňuje dnes"). A few rows were opened to traffic earlier in a reduced mode; that is said in `notes`.
3. Municipality codes are RÚIAN kód obce (identical to the ČSÚ 6-digit code), taken from Wikidata property P7606, matched by name and, for duplicated names, by position. A blank code means the named place is not a municipality in that list (a village part or locality), not that the code is unknown.
4. `date_precision` is `day`, `month` or `year`. Three rows are month-only and one year-only (Lhotsko, 2016, low confidence).
5. Wikipedia was not used.

## Columns

| Column | Meaning |
|---|---|
| `id` | BYP-nnn; opened rows first in date order, then planned rows by stage |
| `town`, `municipality_code` | Municipality or municipalities served; several are separated by `; ` and the codes line up with the names |
| `road`, `road_class` | New road number and class (D or I) |
| `project_name` | Name as ŘSD uses it |
| `status` | `opened` or `planned` |
| `opened_date`, `date_precision` | Opening day to traffic |
| `construction_start` | Start of works from ŘSD (YYYY-MM-DD, YYYY-MM or YYYY); empty if not found or not started |
| `length_km` | Main route length |
| `kind` | `full`, `partial`, `relocation`, `motorway_section` (below) |
| `old_route` | Road or street through the town that the bypass relieves |
| `stage` | Opened rows: which stage of a multi-stage bypass. Planned rows: `in construction`, `tender`, `SP` (building or joint permit issued), `ÚR` (zoning decision issued), `pre-ÚR (EIA/záměr)` |
| `completes_bypass`, `carries_through_traffic` | Opened rows only. Whether this stage completes the bypass, and whether the stage as opened carries the through traffic of the old route. Both are judgements from ŘSD descriptions, flagged in `notes` when unsure |
| `expected_opening`, `as_of` | Planned rows only: expected opening in the latest ŘSD source and the date of that source |
| `start_lat`, `start_lon`, `end_lat`, `end_lon`, `osm_ways` | Geometry columns. Empty for all rows, see "Open items" |
| `source_urls`, `confidence`, `notes` | Sources, `high`/`medium`/`low`, free text |

### How `kind` was assigned

- `full`: ŘSD or the press calls the work an obchvat (or the leaflet describes a relocation that takes the through traffic of a class I road past one side of the built-up area entirely), and the opened stage completes it.
- `partial`: the stage, or the whole project, covers only one side or part of the town, or is one stage of a multi-stage bypass that does not yet take the whole through traffic.
- `relocation`: ŘSD calls it a přeložka and no source describes it as a bypass of a named town.
- `motorway_section`: a D-class section that bypasses a named town (ŘSD "obchvat" in the name, or ŘSD says it relieves the town).

The assignment follows ŘSD naming and descriptions; route geometry was not checked.

## Counts

Opened, by year of opening and road class (55 rows):

| Year | D | I | Total |
|---|---|---|---|
| 2016 | 0 | 4 | 4 |
| 2017 | 0 | 2 | 2 |
| 2018 | 0 | 2 | 2 |
| 2019 | 0 | 5 | 5 |
| 2020 | 2 | 2 | 4 |
| 2021 | 2 | 4 | 6 |
| 2022 | 2 | 4 | 6 |
| 2023 | 0 | 9 | 9 |
| 2024 | 3 | 4 | 7 |
| 2025 | 3 | 5 | 8 |
| 2026 (to 15 Oct) | 0 | 2 | 2 |
| All | 12 | 43 | 55 |

By kind: 26 full, 14 partial, 12 motorway_section, 3 relocation. Date precision: 51 day, 3 month, 1 year.

Planned, not open on 2026-10-15 (59 rows), by stage and class:

| Stage | D | I | Total |
|---|---|---|---|
| in construction | 1 | 11 | 12 |
| tender | 0 | 6 | 6 |
| SP | 1 | 4 | 5 |
| ÚR | 0 | 12 | 12 |
| pre-ÚR (EIA/záměr) | 0 | 24 | 24 |

Confidence over all 114 rows: 47 high, 49 medium, 18 low. Low rows are listed in the report that accompanied this file; the main causes are stage readings from leaflet milestone dates and stale sources.

## Towns with several rows

Staged bypasses have one row per stage. Overlapping projects in the same town:

- Opava: north bypass east part (2019), south bypass junction with I/11 (2021), north bypass west part (2023); planned: south bypass Hradecká-Olomoucká (in construction), Olomoucká-Bruntálská, Opava-Komárov south bypass, Nové Sedlice north bypass (Nové Sedlice is a part of Opava).
- Mělník: stages 1 (2016) and 2 (2022) open, stage 3 planned, stage 4 not yet in preparation.
- Znojmo: stage 2 open (2019); stages 1 (nearly built), 3 and 4 planned.
- Pardubice: north-east bypass open (2025); south-east and south-west bypasses planned. Sezemice (I/36, near Pardubice) has a first 1.8 km open since 2026-08-30 and a remaining part due 2026-11-02.
- Frýdek-Místek (D48 stages I and II), Havlíčkův Brod (south-east open, north-east planned), Krnov (north-east open, west bypass planned), Klatovy (stage 1 open, stage 2 planned), Česká Lípa (middle section open, last section planned), Rychnov nad Kněžnou (stages I and II, both planned), Příbram (parts 1 and 2, both planned).
- Řevničov: two D6 rows opened the same day (Řevničov bypass and Nové Strašecí-Řevničov).
- České Budějovice: two D3 rows opened the same day (28.4 km in the press release also covers Třebonín-Kaplice, which is not a bypass).
- Bypasses serving two or more municipalities: Chrudim and Slatiňany, Lišov and Štěpánovice, Ondřejov with Ústrašín and Myslotín, Postřelmov and Chromeč; planned: Kaznějov and Rybnice, Hněvkov and Sedlice, Litomyšl and Janov, Úvaly with Prague districts.

## Exclusions and reasons (construction facts only)

- Capacity or widening of an existing bypass, not a new bypass: D7 Panenský Týnec (2021-12-16), D7 Louny, I/9 Nový Bor-Svor (2024-07-04), I/16 Jičín (planned), D56 Frýdek-Místek connection (2022-09-02).
- Relocations that no source describes as bypassing a named town: I/21 Trstěnice-Drmoul (2020-06-04), I/34 Rouštany-Pohled (2018), I/16 Slaný-Velvary stage II (2020-09-21), I/21 Nová Hospoda-Kočov, I/14 Kunratice-Jablonec and I/62 Děčín-Vilsnice (all listed by ŘSD for 2018; opening days not checked), I/16 Martinovice link (under construction 2026), I/43 Černá Hora relocation (under construction 2026), D3 connector to Český Krumlov (2026-08-28, 3.2 km, ŘSD says it also serves as a bypass of two villages; borderline).
- Reconstruction through a town, not a bypass: I/55 Přerov průtah (2022-10-31), I/53 Dobšice průtah (2018).
- Other motorway sections that pass towns but are not named as a bypass by ŘSD: D1, D3 (other sections), D4, D11 (including Smiřice-Jaroměř, 2021-12-17), D35 (other sections, including Ostrov-Vysoké Mýto, 2026-08-21), D46, D48 (other sections), D49, D52, D55 (other sections).
- Opened before the window: Chrudim stage 1 Medlešice-I/17 (2015-12-16), Žďár nad Sázavou Mělkovice relocation (2015).
- Not open by the cut-off: Svor (expected 2026-11), Bruntál east stage I (expected 2027-02), Opava Hradecká-Olomoucká (expected end of 2026), Sezemice remainder; all are in the planned rows.
- Class II and III bypasses: not covered. The regional road authorities (krajské správy silnic) were not searched systematically, so adding a handful would bias the treatment list. Names met in passing that a later pass could verify: Kojice, Dašice (Pardubický kraj), Zvole (Šumpersko), Slavětice II/152 and Velké Meziříčí, Brtnice, Zašovice (Vysočina), Veselov II/205 (Karlovarský kraj), Stará Boleslav II/331 (Středočeský kraj), Borovany II/157 (Jihočeský kraj), Kaplice. None of these has a date or source in the file.
- Projects named on the ŘSD 2026 regional maps whose leaflet was not retrieved, so no row: I/26 Holýšov, I/19 Kladruby, I/15 Želkovice, I/27 Havraň, I/57 Město Albrechtice, I/57 Vrchy and Skrochovice (rows exist with low confidence), I/11 Bruntál north, D52 Mikulov, I/17 Heřmanův Městec-Bylany (variants only), I/43 Mladějov-Lanškroun (variants only).

## Open items

- Geometry is not filled. OpenStreetMap (Overpass) is the only open source with the road geometry, but the historical ("attic") queries needed to separate the new road from the old one failed, and querying by road number alone cannot tell the new bypass from the road it replaces. ŘSD's Geoportal REST services require a login. Rather than guess, `start_lat`, `start_lon`, `end_lat`, `end_lon` and `osm_ways` are empty.
- Opening day versus first traffic: ŘSD leaflets give the ceremonial opening, which normally coincides with the start of traffic. Krnov, Frýdek-Místek stage I and Sezemice had earlier or staged traffic; see `notes`.
- Planned-row stages for `low` rows were mapped from the sequence of milestone dates in the leaflet, whose labels are not machine-readable. Expected opening is the last milestone date.
- Month-only and year-only openings: Mělník stage 1 (2016-09), Staňkov (2016-11), Sklené nad Oslavou (2018-10), Lhotsko (2016).
- ŘSD press pages for Velemyšleves (2016-11-22), Dubá (2017-06-30) and Lhotsko are no longer retrievable; those dates rest on titles seen in search results, a mailing-list copy (Dubá) and the ŘSD completed-works map.
