# Rain-delays study — screening (§3)

**Date: 8 October 2026. Written before any delay value was read.** Rule 1 was applied from PID announcements only. No
vehicle position, delay value or GTFS file was opened for this file. Rules 2 and 3 need record timestamps and trip
counts from the thesis files, which have not been copied yet; they are applied when the files arrive, from timestamps
and counts only, before any delay value is read.

Code: `tools/rain/screen_pid.py`. Output: `rain-delays-screen.json` (every announcement used, its source and the
line × date exclusions).

## Source

pid.cz removes a change page once the change is over, and its REST API does not expose them, so the announcements
were read from the Internet Archive:

- **Change pages.** Every archived page under `pid.cz/zmena/` captured between September 2024 and October 2025:
  2 234 planned-change pages. Each page gives the category, the affected lines, the first and last day and the kind
  of event. 190 pages could not be read (no date, or the archive did not serve them).
- **List snapshots.** The 8 archived snapshots of `pid.cz/zmeny/` inside the window (16 Apr, 26 Apr, 15 Jun, 2 Jul,
  5 Jul, 27 Jul, 13 Aug and 14 Aug 2025). Each lists every current and upcoming change with its lines and days. They
  measure coverage and fill the pages' gaps.

**Coverage.** The snapshots list 173 distinct planned closures on a tram or city bus line; 125 of them have an
archived change page. The other 48 enter from the snapshot alone (lines, first and last day). For trams these are
about ten short closures of hours to one day. Closures that started and ended between two snapshots and whose page
was never archived are missed; their number is unknown. The §6 check "disruption days kept" bounds what they can do
to the estimate.

## How the rule was applied

- **Planned changes only (clarification, 8 October 2026).** Pages in the incident series (`-1`, *mimořádnost*) are not
  used. An accident or a breakdown can be caused by rain, so excluding incidents would remove part of the effect being
  measured. Only *výluka* (planned) entries count.
- **Closure, diversion or replacement service.** An entry counts if its kind is a route change, diversion, suspension
  of service, replacement service, service restriction or line withdrawal. A stop moved or skipped on an unchanged
  route does not count. Snapshot entries without a kind are read by their title.
- **Trams and city buses.** Tram numbers are 1–39 (day) and 90–99 (night); city buses 100–299. Tram numbers count
  only from Prague announcements (series `-3`, or a snapshot title naming trams), because towns in the region reuse
  1–39 for their own buses.
- **Days.** From the first to the last day the announcement gives, clipped to the window. An entry known only as
  "service restored: day D" covers day D. "Until further notice" with an expected end uses that end; without one it
  runs to the end of the window (68 spans).
- **Direction.** Announcements rarely name a direction, and most closures are both ways, so an entry excludes both
  directions of each line it names.
- **Closures in force for the whole window (clarification, 8 October 2026, author's decision).** A closure in force
  on every day of 15 March – 8 September 2025 is the line's regular pattern for this study and does not exclude: the
  route × hour × weekday effect of §4 absorbs a route that is the same on every date. Three tram closures are of this
  kind: Dělnická – Palmovka (from 25 Nov 2024, until further notice; the Libeň bridge is closed to trams),
  Výstaviště – Nádraží Holešovice (1 Feb – 10 Oct 2025) and Kotorská – Pankrác (from 29 Apr 2024), together with the
  closure of Pankrác C metro station (from 6 Jan 2025), whose replacement runs on tram line 19. Closures that start or
  end inside the window exclude their days as written. The literal reading (whole-window closures excluded too) is
  reported as a further check next to "disruption days kept".

## Result

| | Tram line-days | City bus line-days |
|---|---|---|
| Excluded (rule as applied) | 1 320 | 4 076 |
| Excluded, literal reading | 2 832 | 7 287 |

37 tram lines appear in the announcements (26 day, 9 night and 2 special lines), about 6 600 line-days in all, so the rule
removes about a fifth of tram line-days. The largest partial closures:

| Days | Lines | Closure |
|---|---|---|
| 14 Jun – 8 Sep | 11, 13 | I. P. Pavlova – Muzeum |
| 30 Jun – 30 Aug | 22, 25, 97 | Vypich – Bílá Hora |
| 12 Jul – 30 Aug | 4, 21 | Service restriction in Plzeňská street |
| 1 – 30 May | 22, 26, 97 | Zahradní Město – Nádraží Hostivař |
| 5 – 30 Apr | 1, 2, 25, 96, 97 | Vozovna Střešovice area |
| 31 May – 13 Jun | 2, 12, 15, 17, 18, 20, 22, 23, 97 | Klárov (Malostranská) |
| 30 Jun – 11 Jul | 4, 7, 9, 10, 15, 16, 21, 98, 99 | Anděl (Plzeňská) and Na Knížecí – Radlická |

The full list of 70 partial tram closures, with sources, is in `rain-delays-screen.json` under `spans`; the
line × date exclusions are under `exclusions`.

## Rules 2 and 3 (8 October 2026, from record timestamps and trip counts only)

Code: `tools/rain/screen_feed.py`. Output: `rain-delays-screen-feed.json`. The thesis's records arrived as
`prague_transit.duckdb`; the study uses its table `stop_times_history_modeling` (121 197 794 rows, the count on the
thesis page). Only trip ids, route types, stop sequence, stop names and observed times were selected; no delay, dwell
or travel-time column was read.

- **Rule 2, feed gaps.** 8 of 178 dates are excluded: 15 March (records start at 21:48) and 8 September (records end
  at 01:00), the edges of the window; 3 April, 5 April and 2–4 May, with no records in 05:00–23:00; 9 July, with a
  1 050-minute gap. No other date has a gap over 41 minutes. 170 dates remain.
- **Rule 3, thin units.** Trams: 266 247 route × direction × date × hour units, of which 66 874 have fewer than 2
  trips; they hold 4.2 % of tram trip-hours (66 874 of 1 591 861). City buses: 160 207 of 759 089 units, 5.3 % of
  trip-hours. The thin units are mostly short turns and diverted trips, which end at a terminal of their own and so
  form their own direction.

How the records were read (definitions, dated 8 October 2026, before any delay value was read):

- **Records are stop passes, not raw positions.** Each row is a segment from a stop to the next stop, with observed
  times. "Position" in §1 is read as a stop pass: delay gained in an hour is the trip's delay at its last stop pass in
  the hour minus its delay at its first.
- **A record's time** is its observed arrival at the stop, or observed departure when arrival is missing.
- **Route** is the second field of `rt_trip_id` (`<start time>_<route>_<trip>_<feed date>_<n>`), which parses for
  every tram record. **Direction** is the trip's terminal: the next stop of its highest-sequence segment.
- **Modes.** Trams are `route_type = 'tramvaj'`; city buses are `autobus` with routes 100–299.
