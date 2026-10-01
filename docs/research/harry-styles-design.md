# Harry Styles in numbers: how long a hit lasts, where, and how many nights a city can fill — research design

**Status: design committed 1 October 2026, before any chart days or ticket counts are collected.**
Registration is self-timestamped, as for the film fund study. In the article this is a "registered analysis plan:
design committed at `<hash>` on 1 October 2026, before the results commit; commit times are self-reported".
Deviations are listed, dated, under "Changes after registration".

## 0. What has already been seen

- **kworb.net, Spotify chart totals (structure only).** The global, Czech and US "daily totals" pages were opened
  to read their columns: artist and title, Days (days in the Top 200), T10, Pk (peak), (x?) (days at peak),
  PkStreams, Total. The first row of the global page was seen (The Weeknd, *Blinding Lights*, 2 494 days, peak 1).
  The number of global rows with peak 1 was counted: 194. No other row was read.
- **kworb.net, track page of *As It Was*.** Its column headers and dates were read, to learn that the page shows
  only selected dates (first weeks, then recent weeks and days), not the full daily history. Its first listed date is
  7 April 2022, and on 30 September 2026 it was at position 80 in the global chart, so it is still charting. No
  country value was read.
- **Wikipedia, *Love On Tour* (structure only).** The page has four concert tables. In the largest (2022), 78 show
  rows share 36 attendance and revenue cells; runs of several nights are reported as one Boxscore entry (row spans
  of 2, 6, 12 and 15 nights). One entry was seen: Glasgow, Ibrox Stadium, 11 June 2022, 43 637 / 43 637,
  $4 229 885.
- **Prior expectation.** The author expects *As It Was* to last longer than most global number ones. She has no
  stated expectation about countries or about residencies.

## 1. Questions

- **Q1 (how long).** Among songs that reached number 1 in Spotify's global daily chart, how long did they stay in
  the global Top 200, and where does *As It Was* stand?
- **Q2 (where).** In which countries did *As It Was* stay in the national Top 200 longest, relative to that
  country's own number ones?
- **Q3 (how many nights).** On Love On Tour, did longer runs in one venue sell a smaller share of their tickets?

All three are descriptive. None says why a song lasted or why a run sold.

## 2. Data

- **Source A, kworb.net daily totals** (one page per chart: global and each country), collected once, on one day,
  with a named user agent and at least 3 s between requests. The collection date is the censoring date.
- **Source B, kworb.net track pages**, only to find each global number one's first listed date (§3, Q1).
- **Source C, kworb.net current global and country daily charts** on the collection date, to mark songs still
  charting.
- **Source D, Wikipedia, *Love On Tour***, the four concert tables, at a revision fixed by its id at collection.
- Raw pages are hashed; the hash list is published as `docs/research/harry-styles-files.sha256`. Parsed tables are
  published as CSV. Code is in `tools/harry/`.

## 3. Measures and estimation

**Q1.**
- Units: the 194 songs with peak 1 in the global daily totals. Songs whose first listed date is before 8 January
  2017 are excluded: the chart begins on 1 January 2017, so their start is not seen. The excluded list is published.
- Outcome: Days, the total days in the global Top 200. This counts all days, not days in a row; a song that left
  and came back counts both spells.
- Censoring: a song on the global chart on the collection date is censored at its current Days.
- Estimate: the Kaplan–Meier curve of Days. *As It Was* is placed on it as the share of number ones that stayed
  longer, with a 95 % interval from 2 000 bootstrap resamples of songs. If *As It Was* is censored, its place is a
  lower bound and is labelled so.
- Any other Harry Styles song with peak 1 is placed the same way.

**Q2.**
- Units: every country chart on kworb where *As It Was* appears.
- Measure: R = Days of *As It Was* in that country / the median Days of that country's songs with peak 1.
  Interval: 95 % from 2 000 bootstrap resamples of the country's number ones (the median moves; *As It Was*'s
  Days do not).
- Countries with fewer than 20 number ones are reported but not ranked. A country where *As It Was* still charts
  has R as a lower bound, labelled so.
- Output: a ranked list, with the Czech Republic marked. No country is singled out in advance except Czechia.

**Q3.**
- Units: Boxscore entries on Love On Tour (one entry may cover one night or a run). Nights per entry = the number
  of show rows it spans.
- Measure: sell-through = tickets sold / tickets available.
- Estimate: Spearman's ρ between nights and sell-through, with a 95 % interval from 2 000 bootstrap resamples of
  entries; the share of entries at 99.5 % or more; a strip chart of sell-through by nights.
- If 90 % or more of entries are at 99.5 % or more, the article says the data show demand at or above capacity
  everywhere and cannot measure how far above; ρ is then reported but not interpreted.
- Revenue is shown only as revenue per night, as context, not tested: venue size and ticket prices differ by city.

## 4. Labels

- All results are labelled **descriptive**. Q1 and Q2 rest on Spotify only, not on the whole music market.
- Lower bounds (censored songs) are labelled "still charting, at least".

## 5. What this will not show

- Why a song lasted: release timing, promotion, TikTok and playlists are not measured.
- Days in a row, or how fast a song fell.
- What a single night of a residency earned: Boxscore reports runs together.
- Demand beyond capacity: a sold-out show hides how many more would have bought.

## References

- kworb.net, Spotify charts (daily totals and track pages), collected on the date stated in the results.
- Wikipedia contributors, "Love On Tour", revision stated in the results; Boxscore figures as cited there.
- Kaplan, E. L. and Meier, P. (1958). Nonparametric estimation from incomplete observations. *Journal of the
  American Statistical Association*, 53(282), 457–481.

## Changes after registration

None yet.
