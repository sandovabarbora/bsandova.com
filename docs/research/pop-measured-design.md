# Pop, measured: a series design for parts 2–5 (Taylor Swift, BTS, Bad Bunny, Billie Eilish)

**Status: design committed 1 October 2026, before any result of part 1 (Harry Styles) has been computed or seen,
and before any data of parts 2–5 are collected.** Registration is self-timestamped, as for part 1
(`docs/research/harry-styles-design.md`). Deviations are listed, dated, under "Changes after registration".

## 0. Series and what has already been seen

- **Series.** Five parts, one artist each, the same three questions, so parts can be compared: 1 Harry Styles
  (registered separately), 2 Taylor Swift, 3 BTS, 4 Bad Bunny, 5 Billie Eilish. BTS is chosen for the K-pop part
  over BLACKPINK because its tours are better documented on Wikipedia; this choice was made before any chart figure
  of either group was seen.
- **Shared data.** All parts use the same kworb.net collection made for part 1 (global and country daily totals,
  current daily charts, track pages of the global number ones). Its structure is described in the part 1 design.
  No figure from it has been read beyond what that design lists.
- **Wikipedia tour pages (structure only).** Counted on 1 October 2026, without reading any figure: The Eras Tour,
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

## 4. Two more questions, for all five parts (added before any data of the series were read)

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

None yet.
