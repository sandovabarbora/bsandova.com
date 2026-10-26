# Do aircraft over Czechia broadcast degraded GNSS positions? — research design

**Status: pre-specified analysis, design committed 15 October 2026, before any aircraft's position quality was
summarised.** A descriptive measurement with registered rules. The steps follow in dated commits: design → data-step
code (tagged before it runs) → data and screening → estimation code (tagged) → results. Commit times are
self-reported; the signed tag `gnss-design` fixes this text. Deviations are listed, dated, in the change log.

## 0. What has already been seen

- **The author** has not looked at gpsjam.org or any other map or report of GNSS interference over Czechia (stated 15
  October 2026). She and the drafting assistant know, as general public background, that interference has been
  reported around the Baltic Sea and Kaliningrad, the Black Sea and the eastern Mediterranean.
- **Feasibility check (14 October 2026).** A separate agent read the schema of the adsb.lol daily archives (a 5 %
  slice of 13 October 2026: field names, field presence, aircraft counts in four boxes), one ADS-B Exchange snapshot of
  1 March 2022 (field presence only), and the header line and row count of one gpsjam.org daily file (12 October 2026);
  the row count says roughly how many map cells had any degraded aircraft that day, a mild exposure to the extent of the
  footprint, not to any region's level. The slices it kept hold NACp values; none was summarised. It also collected
  public statements: the Czech air navigation service (ŘLP, 25 September 2024: "units of cases" of crews at higher
  flight levels reporting GNSS problems) and the Civil Aviation Authority (ÚCL, 6 May 2026: a marked increase since
  February 2022 and a gradual spread into Central Europe); EASA's Safety Information Bulletin 2022-02 names the Baltic
  Sea region among the affected areas. These statements are the claims Q3 checks.
- **Review (15 October 2026), three rounds.** An independent methods reviewer read the draft and the trace structure (array layout,
  field presence) of the same slice, and counted aircraft per region from position, altitude and source type only; it
  read no quality value. A second round read readsb's source and the spacing of points that carry quality fields (one
  in four stored points; at cruise about one usable point a minute), from structure only; the unit of measurement is
  therefore the position report, not the aircraft-day (§2). These looks used a slice of 13 October 2026, inside study
  year 4. A third round counted, from structure only (positions, altitude, source, the stale flag, the ADS-B version
  and whether a `nac_p` key exists), usable points per aircraft and region and west of 5° E in the same slice. The
  version below takes in all three rounds.
- **Prior expectation.** Stated by the author on 15 October 2026: interference does not reach over Czechia ("podle
  mě to rušení nezasahuje").

## 1. Questions

All are descriptions of what aircraft broadcast. A degraded position here means only that the aircraft's own estimate
of its position uncertainty was poor (NACp below 8), whatever the cause; jamming is one cause, not the only one, and
nothing here says who or what caused it. The control region (Austria and Switzerland) lies farther from the Baltic
and Kaliningrad area than Czechia, though its traffic also comes from the Black Sea and eastern Mediterranean.

- **Q1, over Czechia (headline; the confirmatory estimates are Q1 and Q3).** E_CZ: the share of degraded position
  reports over Czechia minus the share over the control, pooled over the sample (§2), with its interval. It describes
  ADS-B version 2 aircraft at cruise over Czechia, not all traffic.
- **Q2, the gradient (descriptive).** E_PL and E_BALT (Estonia, Latvia and Lithuania together) the same way; E per
  band of distance from Kaliningrad (§2); and G = E_CZ / E_BALT, Czechia's position between control and the Baltic
  states, per year and pooled (rules in §4).
- **Q3, the official statements (planned second estimate).** The change in E_CZ from 1 March – 14 October 2024 to
  1 March – 14 October 2026, against the ÚCL statement of an increase; the ŘLP statement of September 2024 is set
  against the level of study year 2. The "since 2022" part of the ÚCL statement lies before the data and is not tested.
- **Q4, position jumps (descriptive).** The share of aircraft crossings of a region with a position jump (§2); spoofing
  can leave NACp good, so Q1–Q3 would miss it.

## 2. Data and definitions

- **Source.** adsb.lol `globe_history_<year>` archives (ODbL 1.0, attributed as the licence requires), the release
  tagged `v<YYYY.MM.DD>-planes-readsb-prod-0` of each day, in one or more parts (`.tar`, or `.tar.aa`, `.ab`, … in
  order). Only `prod-0` is used. Files are fetched by their direct release URLs, at most two at a time, with the
  User-Agent "bsandova.com research".
- **Sample of days.** Every Wednesday from 1 March 2023 to 14 October 2026 (190 days), fixed now. A day is
  **unreadable** if its release is missing, any part fails to download or extract, or it holds fewer than 70 % of the
  aircraft files of the median of the four nearest sampled days. An unreadable Wednesday is replaced by the Thursday
  after it, which counts in the study year of the Wednesday; if the Thursday is also unreadable or not yet published,
  the day is lost and counted. Public-holiday Wednesdays are kept and counted.
- **Study years.** Year 1: March 2023 – February 2024; year 2: March 2024 – February 2025; year 3: March 2025 –
  February 2026; year 4: March – October 2026.
- **Usable point.** A point of an aircraft's trace (`trace_full`; a 14-element array) with source `type` (index 9)
  `adsb_icao`; the stale flag (bit 0 of `flags`, index 6) unset; a details object (index 8) with ADS-B `version` 2 and
  a `nac_p` key; and numeric pressure altitude (`alt_baro`, index 3) at or above 25 000 ft (FL250). The top-level
  `version` (the receiver software) is not used. Addresses starting with `~` (non-ICAO) are dropped. readsb stores the
  details object on every fourth stored point by position in the trace, not by content, so usable points are a thinned
  but unselected sample: at cruise, roughly one a minute.
- **Regions.** Natural Earth 1:10 m admin 0 countries, version 5.1.2 (its file hash recorded in the data step):
  Czechia (CZ); Poland (PL); Estonia, Latvia and Lithuania (BALT, land plus a 22 km band of sea off their coasts not
  over another country's land); Austria and Switzerland (CTRL). A point on a boundary belongs to the first region in
  the order CZ, PL, BALT, CTRL. Kaliningrad and Belarus are not regions.
- **Entry buffer.** The usable points within the first 2 minutes after an aircraft enters a region (its first point in
  the region after a stored point outside it, or its first point of the day) are not used in the primary analysis, so that
  quality carried over from elsewhere is not counted there (the full-region version is check 8). Two minutes at cruise
  is about 28 km, a sixth to a third of a typical Czech crossing.
- **Degraded point.** A usable point with NACp below 8 (estimated position uncertainty of 0.05 NM, about 93 m, or
  more).
- **Persistently degraded airframes.** Over the whole sample, an aircraft (ICAO address) with at least 30 usable points
  west of 5° E on at least two sampled days (away from the Baltic, Black Sea and eastern Mediterranean areas named in
  public reports), at least half of them degraded, is dropped everywhere; this is treated as a property of its
  equipment. Aircraft with fewer than 30 such points
  cannot be screened and are kept; the share of usable points from screenable aircraft is reported per region and
  year (§3), and check 4 keeps only screenable aircraft.
- **Share.** D_r for a set of days: degraded points over usable points in region r, after the entry buffer and
  without persistently degraded airframes. **E_r = D_r − D_CTRL.** A margin of one point (§6) is one position report
  in a hundred.
- **Crossing.** One aircraft's consecutive stored points in one region on one day, from entry to exit. Entry and exit
  are judged on all stored non-stale points of the aircraft, whatever their source. A crossing also ends when two
  consecutive stored points are more than 10 minutes apart; the next one is a new crossing with its own entry buffer.
- **Regions for check 6.** Austria and Switzerland separately, and Germany west of 10° E (Natural Earth admin 0,
  clipped at 10° E).
- **Distance bands (Q2).** By each usable point's distance from Kaliningrad city (54.71° N, 20.51° E): 0–300,
  300–600, 600–900 and over 900 km, over the four regions' points. Czechia spans about 650–950 km, so bands partly
  stand in for regions and are read with them, not as a separate gradient.
- **Position jump (Q4).** Two consecutive stored non-stale points of one aircraft (source `adsb_icao`, with or
  without details), both inside the region, at most 60 s apart, not across a leg marker (bit 1 of `flags`), with an
  implied ground speed above 1 200 kt and a displacement of at least 2 NM; a crossing with at least one jump counts
  once.
- **Space weather.** The daily maximum of the planetary Kp index from GFZ Potsdam for each sampled day, read in the
  data step; it is not an outcome.

## 3. Data step and screening

The data-step code (the definitions of §2) is committed, with tests on made-up traces, and tagged before it runs on any
sampled day. It keeps one day on disk at a time, deletes it after counting, and writes per day only counts: (a) per
region (including the regions of check 6), aircraft and distance band: usable points, degraded points, crossings and
crossings with a jump (bands by the points in them); (b) per aircraft: usable and degraded points west of 5° E, and the
counts of (a) for the variants of checks 1, 2, 3, 8 and 10, each variant with its own usable-point definition except the
airframe screen, which always uses the primary one; (c) per crossing: aircraft, region, usable points after the buffer
and degraded points (check 11); and the screening counts. The degraded and jump counts are not opened until the screening
report is committed and the estimation code is tagged; the persistently degraded airframes are counted with the
estimation, not in screening. Screening reports:

1. Days fetched, replaced by Thursday and lost; the holiday Wednesdays.
2. Per region and day: crossings, usable points, usable points per crossing, the share of points with a details
   object, and the share of usable points from aircraft with at least 30 usable points west of 5° E (coverage, no
   quality value).
3. The number of aircraft that can be screened (§2), per region and year; not how many are dropped.
4. The share of points by ADS-B version and source type, per year.
5. Kp_max per sampled day and the number of days with Kp_max ≥ 5.

## 4. Estimation

- **Pooled and per year.** D_r over the usable points of the period (busy years and long crossings weigh more, as
  intended; equal day weights are check 7, crossing-level shares check 11).
- **Intervals.** A two-way bootstrap, 2 000 draws, seed 20261015: sampled days resampled in moving blocks within each
  study year (blocks of 4 consecutive sampled days, circular within the year, all regions of a day moving together),
  and, independently, aircraft (ICAO addresses) resampled with replacement, each draw weighting every point by the
  product of its day's and its aircraft's draw counts. The same airframes return on many Wednesdays, so days alone
  would understate the uncertainty. 90 % and 95 % percentile intervals for each E_r and for the change in E_CZ in Q3;
  for Q3 the blocks are circular within the 1 March – 14 October window of each year, and the two windows are resampled
  independently. The day-block interval alone is reported as well.
- **G.** Computed only if E_BALT's label (§6) is a higher degraded share than control; then per bootstrap draw only where that draw's E_BALT exceeds
  0.01, with the share of draws where it is undefined reported. Otherwise G is not reported and E_CZ and E_PL are
  shown against E_BALT as differences.
- **Degraded-position days (descriptive).** A region-day with at least 300 usable points in the region and in control
  counts as a degraded-position day if its day share is at least 2 % and at least 2 percentage points above control's
  share that day;
  per region and year.
- **Repeat airframes (descriptive).** Per region, after the persistent-airframe drop, the share of degraded points that
  come from the ten airframes with the most of them.

## 5. Power

Not computed: any number would need the quality values, which stay unread until the estimation code is tagged. The
margin of §6 is fixed in absolute share points from what the question needs and was not chosen from data: one point
is one position report in a hundred at cruise.

## 6. Labels

Confirmatory: pooled E_CZ (Q1) and the change in Q3. Every other label (per year, PL, BALT, bands) is descriptive and
read with the others, without a correction for multiplicity.

- E (in order): **higher degraded share than control** — the 95 % interval lies above +0.01; **no excess larger than one
  point** — the 90 % interval lies below +0.01 (it may include values below 0); **inconclusive** — anything else.
  Where the label of a check (§7), computed by the same rules, differs from the primary label, both are reported and
  the text does not choose.
- Q3 change (in order): **increase** — the 95 % interval lies above 0; **no increase larger than one point** — the
  90 % interval lies below +0.01; **inconclusive**.

"No excess" means no excess among aircraft still broadcasting a position (§8); it is not "no interference".

## 7. Checks (reported; none relabels a primary result)

1. **NIC instead of NACp**: a point is degraded if its NIC is below 7.
2. **Any altitude**: without the FL250 floor.
3. **ADS-B version 1 and 2.**
4. **Screenable aircraft only**: only aircraft with at least 30 usable points west of 5° E over the sample, in every
   region, so that every region is screened the same way.
5. **Paired within aircraft**: for screenable aircraft, the degraded share of an aircraft's usable points in region r
   minus its share west of 5° E, averaged over aircraft, minus the same for control.
6. **Control variants**: Austria alone; Germany west of 10° E.
7. **Equal day weights**: each region-day carrying equal weight.
8. **No entry buffer.**
9. **Without days of Kp_max ≥ 5**, and E_CZ separately for days with Kp_max below 5 and at or above 5.
10. **NACp below 7** instead of below 8.
11. **Crossings**: a crossing with at least 3 usable points after the buffer is degraded if at least 2 of them are;
    the share of degraded crossings, by the same rules.
12. **Airframe cap**: each aircraft-region-day contributes at most its first 40 usable points after the buffer.

## 8. Limits stated now

- An aircraft that loses its position altogether stops broadcasting one and leaves no usable point; the shares are a
  lower bound on affected aircraft.
- Where an aircraft reports degraded positions is not where the cause is: at cruise an aircraft sees a transmitter
  hundreds of kilometres away, and quality carried over from elsewhere is only partly removed by the entry buffer. A
  positive E_CZ means aircraft over Czechia broadcast a higher share of degraded positions than over the control, not
  that a source was on Czech ground.
- The whole-sample screen cannot remove equipment that became degraded late in the sample, which tilts the Q3 change
  upwards; check 5 limits it.
- Degraded NACp has other causes: faults, the aircraft's own equipment, ionospheric disturbance. Disturbance rises
  with latitude and was strong in the solar maximum of 2024–2025; it cannot be fully separated from the Baltic
  gradient (check 9 limits it), and it can mask a Q3 increase from 2024 to 2026.
- Receiver coverage grew over the period; the FL250 floor and the comparison with control limit, but do not remove,
  its effect. Aircraft that never fly far west cannot be screened for their own equipment, and they are more common in
  the east; checks 4 and 5 show how much that matters. Stale points, excluded everywhere, are more common at the edge of
  coverage.
- One day a week: short episodes can fall between sampled days. The sample estimates levels and trends, not every
  episode. No data before March 2023.
- readsb discards implausible positions before they reach the trace, so Q4 is a lower bound on jumps.

## Change log

- 15 October 2026: design committed.
- 15 October 2026, data-step code (`tools/gnss/`, tested on made-up traces only; to be tagged `gnss-data-step` before
  it runs). Choices the design left open, fixed here before any real day is counted: (1) the 10-minute crossing split is
  measured between consecutive non-stale stored points; (2) a point is in the entry buffer if it comes less than 120 s
  after entry; (3) band edges 0–300, 300–600, 600–900 km and 900 km or more (a boundary distance goes to the higher
  band), great-circle on a sphere of 6 371.0088 km; a crossing counts in every band where it has a point; (4) crossings
  are formed from points at any altitude and source; the Q4 denominator is the crossings with at least one usable point
  after the buffer; (5) a jump pair is consecutive among non-stale points, both `adsb_icao`, 0–60 s apart, and a leg
  marker on any stored point between them blocks it; (6) for check 6, Austria takes the Austria–Switzerland border and
  Germany west of 10° E only points outside the primary regions; each check-6 region has its own crossings and buffer;
  (7) a non-numeric `nac_p` makes a point unusable (counted); the ADS-B version must be the integer 2; (8) check 1 needs
  a numeric `nic`; check 2 keeps points on the ground or without altitude; (9) west of 5° E means longitude below 5
  anywhere, primary definition, no buffer; (10) **an airframe can be screened if it has at least 30 usable points west
  of 5° E in total over the sample, from at least two sampled days**; (11) the low-count rule counts every `trace_full`
  file, uses the four nearest sampled days with a count (ties to the earlier), is applied once after all days are in,
  and a Thursday is judged against the same median; (12) a corrupt single file is counted and the day kept; a broken
  archive, a missing release or a download failing five times makes the day unreadable, and a network outage stops the
  run instead; (13) Kp_max ≥ 5 is numeric (5− does not count), a day with a missing three-hour value has none, and Kp is
  taken for the day actually used; (14) holidays are Czech public holidays; (15) per-crossing rows are kept for crossings
  with at least one usable point after the buffer; (16) a day's archive is used as published, without a date filter;
  (17) only day folders whose status is counted or replaced are read. The archive starts in mid-March 2023: the releases
  of 1 and 8 March 2023 and their Thursdays do not exist, so by §2 both days are lost (188 days remain at most).
  After a code review (still before any real day): a day whose files fail to parse in more than 0.5 % of cases, or
  with no aircraft, stops the run (a schema change would be systematic, not a lost day); traces are put in time order
  before anything is counted, and the number that needed it is recorded; only an HTTP 404 makes a release or part
  missing (§2's "any part fails to download" is narrowed to that and to a broken archive), while any other persistent
  failure stops the run so that no day is lost for a transient reason; check 1 also gets a variant on the primary usable
  points (`c1_nic_same`). A structure-only preflight on one Wednesday per study year (key presence, no values) runs
  after the tag and before the full run.
- 26 October 2026, estimation code (`tools/gnss/estimate.py`, tested on made-up days only; to be tagged
  `gnss-estimation` before it opens `sealed/`), written before any degraded or jump count was opened. The data step has
  finished: 183 of the 190 sampled days are used (181 Wednesdays and the Thursdays 26 December 2024 and 12 June 2025),
  and 7 are lost, not 4: 1 and 8 March 2023 and 28 May and 4 June 2025 (no release for the Wednesday or the Thursday),
  24 December 2025 (Wednesday and Thursday both under 70 % of the median), 31 December 2025 and 6 May 2026 (no release
  for the Wednesday, the Thursday under 70 %). §2 sets no minimum number of days per year or region, so no rule is
  triggered: the years keep 51, 52, 48 and 32 days of 53, 52, 52 and 33, and the Q3 windows lose one day (6 May 2026).
  Choices made in the code where the design was silent or loose:
  - Opening the counts: only `merged_day` reads `sealed/`, and `main` calls it only with `--unblind`, on a tree whose
    HEAD carries the tag `gnss-estimation` and whose `tools/gnss` is unchanged since; a day whose sealed rows do not
    line up key by key with its screening rows stops the run.
  - Gate and failures: the gate is the pooled E_CZ of the primary estimate. A draw where it is undefined is redrawn and
    tallied (the run stops after 20 000 redraws). Any other estimate that fails or is undefined in a draw, whatever the
    error, is left missing for that draw and the missing draws are reported; nothing else stops a draw. Each accepted
    draw is appended to `tools/data/gnss/bootstrap-draws-<time>.jsonl` as it is made, and `--from-log` finishes the
    summary from a log without drawing again.
  - Seed: 20261015 for the main bootstrap and, as a separate stream, for the Q3 bootstrap; 2 000 accepted draws each.
  - Persistent airframes: the data step's choice 10 (at least 30 usable points west of 5° E in total, from at least
    two sampled days), "at least half" meaning 50 % or more. The set is fixed from the whole sample and not re-estimated
    inside bootstrap draws; Q3, Q4 and every check use the same set. The aircraft resampled are the kept aircraft with
    at least one point or crossing in the sample (in a Q3 window: in that window).
  - Day blocks: lost days are absent, so "consecutive" means consecutive among the days used (a replacement Thursday
    stands in its Wednesday's place); a year gets ceil(n / 4) blocks of 4, circular, cut to its n days. The day-block-only
    interval keeps every kept aircraft at weight 1.
  - Q3: windows by Wednesday, 1 March – 14 October inclusive (2024: 6 March – 9 October; 2026: 4 March – 14 October).
    "Resampled independently" is read to cover the aircraft too: each window has its own blocks and its own aircraft
    draw, which widens the interval for a change between windows that share airframes. The change is E_CZ pooled in the
    2026 window minus the same in the 2024 window, and is also computed for every check.
  - Intervals and labels: percentile intervals; "above" and "below" are strict; an interval is not computed from fewer
    than 20 finite draws and its label is then inconclusive. A share with no usable point in the period is undefined,
    not zero.
  - Q2: E per distance band is the degraded share of the four regions' points in the band (control's included) minus
    control's pooled share. G is decided period by period: pooled and each year on that period's own E_BALT label; where
    it is not computed, E_CZ − E_BALT and E_PL − E_BALT are given with intervals instead; G's interval is over the draws
    where E_BALT exceeds 0.01.
  - Checks: each gives E_CZ, E_PL and E_BALT with the §6 label, beside the primary label of the same quantity. Check 4
    uses the data step's screenable rule. Check 5 takes screenable, kept aircraft with a usable point in the region and
    west of 5° E, one weight per aircraft (times its draw count), shares pooled over days; control the same, E the
    difference. Check 7 takes each region's share per day, E per day as region minus control on days where both exist,
    averaged with equal weight per day (bootstrap day counts as weights). Check 9 uses the Kp of the day used; a day
    without Kp stays in "without storm days" and in neither split. Check 11 takes crossings with at least 3 usable
    points after the buffer, degraded if at least 2 of them are.
  - Q4: crossings with a jump over crossings with a usable point after the buffer, per region (pooled and per year), per
    distance band over the four regions, and the difference from control; same airframe drop and bootstrap draws,
    intervals but no label.
  - Descriptive counts without intervals: a degraded-position day is judged on the day used, on primary usable points
    after the airframe drop, both limits inclusive, with the eligible days reported beside the counts; the repeat-airframe
    share is pooled over the sample per region.
