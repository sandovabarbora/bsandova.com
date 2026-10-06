# Annual-pass study — panel units for the staggered difference-in-differences

**Date: 6 October 2026. Written before any passenger value was read.** This file applies the unit rules of the
"change of design" note (6 October 2026) in `annual-pass-design.md` to the window 2005–2019. Checks used only report
listings, tables of contents, file headers and year columns, tariff documents, methodological notes and network
histories. No passenger value, trend or ratio was read or recorded, with the disclosures at the end.

## Rules as applied

- **Rule 1.** The city operator's official annual passenger series exists for every year 2005–2019, from one
  source, with no documented change of counting method. If this cannot be confirmed, the city is out as "not
  verifiable", with what is missing.
- **Rule 3.** The operator's own network did not change area in 2005–2019: no merger, no transfer of a part of the
  network to or from another company, no own lines into a new municipality. Extensions inside the city do not
  exclude. Growth of a regional tariff area run by other operators does not exclude (as in `annual-pass-donors.md`).
- **Treatment.** First full calendar year after a cut of 10 % or more in the full-fare annual pass for the city
  zone (a city or resident subsidy counts), or after a flat-rate pass covering the city was introduced. A cut taking
  effect on 1 January makes that year the first treated year. Only events that give a first treated year of 2019
  or earlier treat a unit inside the panel; later events make the city a not-yet-treated control.
- Facts and sources from `annual-pass-donors.md` (the donor screening) are reused where they apply and cited there.

## Unit table

| City | Rule 1 (source, years confirmed) | Rule 3 (operator's network 2005–2019) | Treatment (first treated year, cut, source) | In / out |
|---|---|---|---|---|
| **Vienna** | Stadt Wien open data, "Fahrgastzahlen der Wiener Linien" (publisher Stadt Wien; [data.gv.at](https://www.data.gv.at/), file `wien.gv.at/data/ogd/ma20/fahrgaeste2024.csv`). Columns `YEAR`, `BUS`, `TRAM`, `UNDERGROUND`; the year column covers 1995–2024 without gaps, so 2005–2019 all present. The split by mode changes method in 2012, the total does not (feasibility check, design §0). **Pass**, flagged: the outcome must be the three-mode total | Wiener Linien runs the city network only; U2 extensions (2008, 2010, 2013) and U1 to Oberlaa (2017) lie inside Vienna. No merger or line into another municipality documented. **Pass** | **2013.** Annual pass cut from 449 € to 365 € (−19 %) on 1 May 2012 (design §1) | **IN, treated 2013** |
| **Prague** | DPP annual reports, every year 2001–2025 listed ([dpp.cz](https://www.dpp.cz/spolecnost/o-spolecnosti/vyrocni-zpravy)). 2005–2014 contain counts (donor screening). 2015–2019: each Czech report contains the sentence "…přepraveno celkem … tis. cestujících, z toho:" and the English report a "Transport Performance(s)" section; checked by keyword search with digits masked. The total is stated each year as based on transport surveys; no change of method is documented (no "metodika" hit relates to passenger counting). **Pass** (all 15 years), flagged: estimates from ticket sales and surveys | DPP stopped running six urban bus lines in eastern Prague in Nov 2005 (taken over by Hotliner, later Connex) ([cs.wikipedia Autobusová doprava v Praze](https://cs.wikipedia.org/wiki/Autobusová_doprava_v_Praze)); DPP took over single lines on 14 Dec 2008 and in 2013; metro C to Letňany 2008, inside the city. PID zones 6–7 (2012) and growth into Central Bohemia (2016–19) are run by other operators. **Pass** (area unchanged), flagged: the Nov 2005 hand-over shrinks DPP's own line set at the very start of the window | **2016.** Annual coupon (Prague zones) cut from CZK 4 750 to CZK 3 650 (−23 %) on 1 Jul 2015 (design §1; DPP/PID tariff archives in the donor screening) | **IN, treated 2016** (flagged) |
| **Brno** | DPMB annual reports 2002–2025 ([dpmb.cz/o-nas](https://www.dpmb.cz/o-nas)), three-year tables, so 2003–2020 complete; counts calculated from tickets sold, no documented change. **Pass**, flagged: ticket-sales method and regional tickets valid in Brno | Joined IDS JMK on 1 Jan 2004 (before the window); IDS JMK stages 2005–2010 are regional, no documented change to DPMB's network. **Pass** | **Not treated before 2020.** Zones 100+101 annual pass 3 800 CZK (2006–07), 3 700 (2008, −2.6 %), 4 430 (Apr 2009), 4 750 (2012 to at least Jul 2019) (IDS JMK price lists, Wayback). Any cut after Jul 2019 would first treat 2020. Shared Czech concession scheme of 1 Sep 2018 (children, students, seniors) noted, adult pass unchanged | **IN, never-treated control** (flagged) |
| Ostrava | DPO reports online only from 2012; the earliest table starts in 2010, so 2005–2009 missing ([dpo.cz](https://www.dpo.cz/o-nas/vyrocni-zpravy.html)). **Fail** | ODIS regional extensions 2006–2008 (regional) | Not assessed | **OUT**: rule 1 (2005–2009 missing) |
| Plzeň | PMDP reports 2003–2024 listed ([pmdp.cz](https://www.pmdp.cz/o-nas/vyrocni-zpravy/)), but a passenger table appears only from the 2015 report. **Not verifiable** (2005–2014 missing) | IDP regional growth 1 Apr 2012 with the inner zone redrawn to the city; whole region from 1 Jul 2018. Doubtful | No cut found (3 460 CZK 2010 → 3 910 → 3 962 → 4 002); 2005, 2007–09, 2011, 2019 not verified | **OUT**: rule 1 not verifiable |
| Graz | Holding Graz publishes reports online only for 2021–2025 ("Unternehmensberichte", [holding-graz.at](https://www.holding-graz.at/de/unternehmen/unternehmensberichte/)); no operator series for 2005–2020 found. The operator also changed form in 2010 (Grazer Stadtwerke/GVB → Holding Graz Linien). **Not verifiable** | Extensions 2006–07 and 2016 inside the city; 2010 legal change. Pass | 2016 (would be): residents' zone 101 annual pass 399 € → 228 € (−43 %) from 7 Jan 2015 ([graz.at](https://www.graz.at/cms/dokumente/10260556_7768145/dcf1bad3/top27%2BBLG.pdf)) | **OUT**: rule 1 not verifiable (missing 2005–2020 series) |
| Linz | Linz in Zahlen lists Linz AG Linien 2003–2025 (design §2); not needed further | Tram into Leonding (2011, line 3 to Doblerholz), Pasching and Traun (25 Feb and 10 Sep 2016) ([de.wikipedia Straßenbahn Linz](https://de.wikipedia.org/wiki/Straßenbahn_Linz)). **Fail** | 365-euro-style resident pass by 2014 (Der Standard, 4 Jun 2014); start date not found | **OUT**: rule 3 |
| Salzburg | Doubtful: since 2005 no single operator for the city network (Albus and Salzburg AG) | City buses moved to Albus in 2005; trolleybus extension 1 Oct 2005; line 5 into Grödig 15 Dec 2019. **Fail** | 2015 (would be): City Ticket 494 € → 366 € (−26 %) from 1 Jul 2014 ([SN](https://www.sn.at/salzburg/chronik/das-oeffi-jahresticket-ist-ein-renner-und-wird-teurer-2643637)) | **OUT**: rule 3 (and rule 1 doubtful) |
| Innsbruck | No IVB report archive or annual series found on [ivb.at](https://www.ivb.at/unternehmen/ueber-uns/); Austrian open data not checked further. **Not verifiable** (no source for any year) | Tram extensions 2012 and 10 Dec 2017 inside the city; Regionalbahn to Rum only 4 Mar 2023 ([de.wikipedia Straßenbahn Innsbruck](https://de.wikipedia.org/wiki/Straßenbahn_Innsbruck)); O-Bus closed 2007. Pass | 2016 (would be): annual ticket 462 € → 330 € (−29 %), Feb 2015 ([presse.innsbruck.gv.at](https://presse.innsbruck.gv.at/news-ivb-tarifreform-steht-kurz-bevor?id=229628&menueid=34478&l=deutsch)) | **OUT**: rule 1 not verifiable |
| Budapest | KSH STADAT and BKV summaries not verified. **Not verifiable** | The HÉV suburban railway division left BKV on 7 Nov 2016 (BHÉV Zrt., later MÁV-HÉV) ([hu.wikipedia MÁV-HÉV](https://hu.wikipedia.org/wiki/MÁV-HÉV)); HÉV lines serve suburban municipalities. **Fail** | 2014 (would be): up-front annual pass 114 600 → 103 000 Ft (−10.1 %) from 2014 ([BKK, Wayback Dec 2013](https://web.archive.org/web/20131221131120/http://www.bkk.hu:80/tomegkozlekedes/jegyek-es-berletek/jegy-es-berletarak/)) | **OUT**: rule 3 (and rule 1 not verifiable) |
| Bratislava | No dpb.sk report archive (404); Slovak statistics office not checked. **Not verifiable** | DPB's own line to Wolfsthal (Austria) from 12 May 2008. **Fail** | Prices 2009–2015 not found; 10 % resident bonus, start unknown | **OUT**: rule 3 (and rule 1 not verifiable) |
| Warsaw | ZTM reports online only 2014–2025 ([ztm.waw.pl](https://www.ztm.waw.pl/raporty-roczne-ztm/)); the GUS BDL passenger variable (subject P3603) starts in 2009 and is not city-level. **Not verifiable** | ZTM "L" lines into suburban municipalities from 1 Apr 2009. **Fail** | No zone-1 cut of 10 % (90-day pass, no annual pass); resident card from 2014 flagged | **OUT**: rule 3 (and rule 1 not verifiable) |
| Kraków | No MPK report archive or annual series found ([mpk.krakow.pl](https://www.mpk.krakow.pl/pl/o-firmie/)); BDL passenger series from 2009 only (P3603). **Not verifiable** (no source for 2005–2019) | MPK runs lines inside and outside the city; organiser changed on 1 Aug 2006 ([pl.wikipedia MPK Kraków](https://pl.wikipedia.org/wiki/Miejskie_Przedsiębiorstwo_Komunikacyjne_w_Krakowie)); dates of suburban extensions not found. Not verifiable | Not assessed | **OUT**: rule 1 not verifiable (rule 3 not verifiable) |
| Wrocław | No MPK report archive or annual series found; BDL as above. **Not verifiable** | MPK runs suburban lines ([pl.wikipedia MPK Wrocław](https://pl.wikipedia.org/wiki/Miejskie_Przedsiębiorstwo_Komunikacyjne_we_Wrocławiu)); start dates not found. Not verifiable | Not assessed | **OUT**: rule 1 not verifiable (rule 3 not verifiable) |
| Munich | No MVG or city statistics series for every year reached (open data 503, MVG/SWM pages need JavaScript; Destatis Bavaria-wide only). **Not verifiable** | U6 extended into the separate municipality of Garching (Garching-Hochbrück, Garching-Forschungszentrum) in 2006 ([en.wikipedia U6](https://en.wikipedia.org/wiki/U6_(Munich_U-Bahn))). **Fail** | Not treated before 2020: Zone M from 15 Dec 2019, 750 € → 522 € (−30 %) from 1 Jan 2020 (first treated year 2020) | **OUT**: rule 3 (and rule 1 not verifiable) |
| Berlin | BVG reports online only from 2021; Destatis 46181 redraws the operator panel at each census and books figures at the headquarters state ([Destatis quality report](https://www.destatis.de/DE/Methoden/Qualitaet/Qualitaetsberichte/Transport-Verkehr/jaehrlich-5jaehrlich-personen-omnibusverkehr.pdf?__blob=publicationFile&v=6)). **Not verifiable or fail** | BVG one company since 1992. Pass | Not treated before 2020: VBB-Umweltkarte AB rises only, 650 € (2005) → 728 € (2016–19); free pupils' ticket and trainees' 365 € ticket from 1 Aug 2019 are group schemes (would first treat 2020) | **OUT**: rule 1 |
| Hamburg | Hochbahn report archive only 2016–2024 ([hochbahn.de](https://www.hochbahn.de/de/unternehmen/unternehmensbericht/archiv-unternehmensberichte)); Destatis problems as Berlin. **Not verifiable** | Hochbahn merged subsidiaries Jasper and SBG Süderelbe Bus with effect from 31 Dec 2019 (end of window). Borderline | Not treated before 2020: Großbereich subscription rises only, 67.40 €/month (2007) → 89.50 € (Jul 2019); 2005–06 not observed | **OUT**: rule 1 not verifiable |
| Other cities (AT, CZ, SK, HU, PL, DE) | Quick probes found no confirmable operator series for 2005–2019: Dresden DVB report page 404; Leipzig LVB facts page 403; Nuremberg VAG and Cologne KVB facts pages 404; Polish BDL city-transport passengers only from 2009. Other Czech, Slovak, Hungarian and Austrian operators were not checked | — | — | **OUT**: not verifiable quickly (no series confirmed) |

## Final lists

**Treated cities (first treated year):**

- Vienna — 2013 (−19 %, 1 May 2012)
- Prague — 2016 (−23 %, 1 Jul 2015)

**Never-treated / not-yet-treated controls:**

- Brno — never treated in 2005–2019

**Counts:** 3 units pass the rules (2 treated, 1 control); 14 of the 17 named candidates and the "other cities" group are out
(rule 1: Ostrava, Plzeň, Graz, Innsbruck, Kraków, Wrocław, Berlin, Hamburg; rule 3: Linz, Salzburg, Budapest,
Bratislava, Warsaw, Munich — four of these also fail rule 1 as not verifiable).

Under the design note this is **fewer than three treated and three control cities, so the staggered
difference-in-differences is not estimable** as pre-specified. Several "not verifiable" verdicts (Graz, Innsbruck,
Plzeň, Kraków, Wrocław, Berlin, Hamburg, and German cities generally) could change if an official operator series for
every year 2005–2019 were found, for example in a city statistical yearbook or a national statistics table. Any such
change, or any change to the rules to reach the threshold, is a dated deviation, made before any passenger value is
read. Note that even then Graz and Innsbruck would join as treated (2016), not as controls.

## Disclosures

- Vienna: when reading the header of the open-data file to list its years, the script also printed the first data
  row, which is for 1995 (outside the window). It was not recorded or used, and the local copy was deleted at once.
- Prague: keyword searches of the 2015–2019 reports printed short lines with every digit replaced by "#" and lines
  with direction words filtered out. One masked line mentioned a celebratory "seven-millionth passenger" at a museum
  event, which is not a series value. Nothing was recorded or used.
- Sources unreachable or without archives: Munich open data, GUS BDL city-level passengers before 2009, Holding Graz
  and IVB report archives, DVB, LVB, VAG and KVB fact pages. Web search was unavailable during this check (session
  limit), so only known URLs were probed.
