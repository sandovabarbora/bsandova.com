# Pop, measured: a series design for parts 2–5 (Taylor Swift, BTS, Bad Bunny, Billie Eilish)

**Status: analysis plan committed 1 October 2026, before this analysis was run; the author had worked with these
data since March 2026.** Registration is self-timestamped, as for part 1
(`docs/research/harry-styles-design.md`). Deviations are listed, dated, under "Changes after registration".

## 0. Series and what has already been seen

- **Data.** The author has worked with these data since March 2026; the plan fixes the analysis, not ignorance of
  the data.
- **Series.** Five parts, one artist each, the same three questions, so parts can be compared: 1 Harry Styles
  (registered separately), 2 Taylor Swift, 3 BTS, 4 Bad Bunny, 5 Billie Eilish. BTS is chosen for the K-pop part
  over BLACKPINK because its tours are better documented on Wikipedia.
- **Shared data.** All parts use the same kworb.net collection made for part 1 (global and country daily totals,
  current daily charts, track pages of the global number ones). Its structure is described in the part 1 design.
- **Wikipedia tour pages.** Counted on 1 October 2026: The Eras Tour,
  5 tables, 152 show rows, 56 attendance cells; Hit Me Hard and Soft: The Tour, 2 tables, 106 show rows, 48 cells;
  Happier Than Ever, The World Tour, 3 tables, 56 cells; Love Yourself World Tour, 4 tables, 32 cells; Born Pink
  World Tour, 27 cells; Most Wanted Tour, no attendance cells; No Me Quiero Ir de Aquí (the 2025 San Juan
  residency), 31 show rows and no attendance cells. Other Bad Bunny tour pages could not be opened (rate limit).
- **Prior expectations.** None stated for parts 2–5.

## 1. Questions (identical in every part)

- **Q1 (how long).** Where does the artist's focal song stand among songs with the same global peak, in days in
  the global Top 200?
- **Q2 (where).** In which countries did the focal song stay in the national Top 200 longest, relative to that
  country's own number ones?
- **Q3 (how many nights).** On the artist's tours, did longer runs in one venue sell a smaller share of their
  tickets?

All three are descriptive.

## 2. Rules fixed for every part

- **Focal song.** The artist's song (as lead or credited artist) with the largest Total streams on the kworb.net
  global daily totals page. It is chosen by this rule, not by hand. Every other song of the artist with global
  peak 1 is also placed in Q1.
- **Q1 reference set.** Songs with the same global peak as the focal song, first listed on or after 8 January 2017.
  Days, censoring (still charting on the collection date), Kaplan–Meier and the bootstrap are as in part 1, §3.
  If the reference set has fewer than 20 songs, the place is reported without an interval.
- **Q2.** As in part 1, §3, with the focal song in place of *As It Was*: ratio to the median Days of each
  country's number ones, 2 000 bootstrap resamples, countries with fewer than 20 number ones not ranked, still
  charting = lower bound. Czechia is marked in every part.
- **Q3 tours.** Every tour of the artist that started on or after 1 January 2017 and whose English Wikipedia article
  has concert tables with attendance cells ("sold / available"). Entries, nights, sell-through, Spearman's ρ with
  2 000 bootstrap resamples, and the 90 %-sold-out rule are as in part 1, §3. Tours are pooled; each entry keeps
  its tour name.
- **If a source has no Boxscore.** A tour without attendance cells is listed and left out. If an artist has no
  tour with attendance cells, Q3 is reported as "not answerable from this source" for that part. No figure is
  taken from prose, press or other sites.
- **Labels and limits** as in part 1, §4–5. For BTS the article states that Spotify misses most of the Korean
  market (Melon, Genie) and YouTube, so Q1 and Q2 describe Spotify listeners only.

## 3. Comparison across parts

- After all five parts are published, a short note compares them: the focal songs' places in Q1 (with intervals),
  the top five countries in Q2 for each artist, and Q3's share sold out per artist. No test across artists is made.

## 4. Two more questions, for all five parts (added before this analysis was run)

These apply to part 1 as well; its design points here.

- **Q4 (one song or a catalogue).** How much of the artist's Spotify streams come from one song?
  - Source: the kworb.net artist songs page (`artist/<id>_songs.html`), every song listed there, collected once.
  - Measures: the top song's share of the artist's total streams; the top three songs' share; the Gini coefficient
    over songs, with its Lorenz curve. These are counts over the full list, so no interval is given.
  - Songs where the artist is featured count as listed on that page; the article states this.
- **Q5 (what a ticket costs where).** What does an average ticket cost, measured in days of the host country's
  income?
  - Units: Boxscore entries from Q3 with both revenue and tickets sold.
  - Average price = revenue / tickets sold (US dollars, as reported). Per country: the sum of revenue / the sum of
    tickets sold over that country's entries.
  - Income: World Bank GDP per capita, current US dollars (indicator NY.GDP.PCAP.CD), for the country and the
    entry's year; the latest earlier year if that year is missing. A day of income = GDP per capita / 365.
  - Output: countries ranked by days of income per ticket, with the ticket's price in dollars beside it.
  - Limits stated in the article: GDP per capita is not a fan's income; Boxscore's gross mixes all seat prices and
    fees; exchange rates are those used when the gross was reported.
- **Czechia across the series.** Each part reports Czechia's place in Q2 (ratio and rank, or "not ranked"). The
  comparison note (§3) lists the five places side by side.
- **Reading Q3.** The 90 %-sold-out rule in part 1, §3 is the only way a "sold out everywhere" result is read: the
  data show demand at or above capacity and cannot say how far above. No statement about which artist is "more in
  demand" is made from Q3.

## References

- As in part 1. Kaplan, E. L. and Meier, P. (1958), *JASA* 53(282), 457–481.

## Changes after registration

- **2 October 2026, after the part 2–5 results were first computed: a data definition.** An attendance cell that
  spans show rows in more than one venue is a leg's total, not a run in one venue, so it cannot answer Q3. Such
  entries are flagged (`multi_venue`) and left out of Q3; they stay in Q5, where the average price per ticket in the
  country is still defined. Only BTS has such entries (Los Angeles and Tokyo, 2018); part 1 is unaffected.
- **2 October 2026, same note.** Taylor Swift's focal song by the series rule, *Cruel Summer*, peaked at 2 in the
  global chart, so her Q1 reference set is the songs with global peak 2, as §2 fixes; their track pages were
  collected for this (`collect_extra.py peers`).
- **2 October 2026, same note.** An entry whose venue names an online platform (Weverse, YouTube and the like), or
  that reports more tickets sold than available, mixes online viewers with the hall. Its sell-through and its price
  per ticket are not a hall's, so it is flagged (`hybrid`) and left out of Q3 and Q5. This affects BTS's
  *Permission to Dance on Stage* (2021–2022).

**3 October 2026 (audit).** A third BTS leg total was found: the Taoyuan entry of 8 December 2018 reports 250 000
tickets for the whole Asian leg (8 December 2018 to 7 April 2019, footnoted in Wikipedia oldid 1375294102) against
the gross of two nights. The parser names one venue for it, so the multi-venue rule did not catch it; it is now
listed in `parse.py` (`LEG_TOTALS`) and left out of Q3 like Los Angeles and Tokyo. BTS Q3 was recomputed: 26
entries and 58 shows (were 27 and 60), 24 of 26 sold out, rho −0.21 (was −0.22).

**3 October 2026 (audit).** Two Bad Bunny tours in `artists.json` named the wrong Wikipedia pages ("El Último Tour
del Mundo" is his 2020 album; "Most Wanted Tour" a 2011 tour by another artist). They now name "El Último Tour del
Mundo 2022" and "Most Wanted Tour (Bad Bunny)", collected on 3 October 2026 at their current revisions. Bad Bunny's
Q3 and Q5 and part 6's M2 were recomputed: Q3 143 entries, 222 shows (were 87, 138); Q5 28 countries (were 27); M2
484 entries, 13 tours, elasticity 0.224 (95 % CI 0.102 to 0.347; was 0.218, 0.095 to 0.341).


**6 October 2026 (Q1 reference set, a correction).** kworb's track page for The Chainsmokers' *Closer* (2016) lists
dates only from 5 March 2026, fewer than the song's 1 952 days in the chart, so its first listed date was read as 2026
and the song was kept, against the rule that songs whose start is not seen are left out (part 1 design §3). It is now
listed in `parse.py` (`UNSEEN_START`) and left out; of the other 22 kept songs whose track pages are also truncated,
none was released before 2017. Q1 was recomputed for the four parts that use the peak-1 set (Taylor Swift's uses
peak 2 and does not contain it). Because one random stream serves every bootstrap in `analyse.py`, the intervals of
Q2 and Q3 are redrawn too, with unchanged data and point estimates.
