# Pop, measured, part 6: what the five parts say together — design

**Status: design committed 2 October 2026, before either model below was estimated. The analysis is exploratory:
the inputs to both models were already seen as descriptive results in parts 1–5.** The design fixes the models,
the coding of languages and the reporting so that the estimates cannot be chosen after the fact, but it cannot
make them confirmatory. In the article this is "exploratory; models committed at `<hash>` before estimation".

## 0. What has already been seen

- Every result of parts 1–5: each artist's focal song's days in each national chart (Q2), and the average ticket
  price and GDP per capita of each country in each artist's tours (Q5), including the rankings and the countries at
  the top and bottom. No regression on these data has been run.

## 1. Questions

- **M1 (language).** Holding fixed how long hits last in each country and how strong each artist's song is, does a
  song last longer in a country whose main language is the song's?
- **M2 (prices and income).** Across all five artists' tours, how far does the average ticket price follow the
  host country's income? An elasticity of 0 means one price everywhere; 1 means prices in proportion to income.

## 2. Data

- **M1.** One row per artist and country where the focal song entered the national Top 200 (parts 1–5, Q2):
  outcome log(days of the focal song in that chart). Pairs where the song never charted are not in the data; the
  article states this selection.
- **Language coding, fixed here.** Song languages: English (Harry Styles, Taylor Swift, Billie Eilish), Spanish
  (Bad Bunny), Korean (BTS; *Dynamite* is sung in English, so a second coding treats it as English, see §4).
  Country languages by official national language:
  - English: au, ca, gb, hk, ie, in, mt, ng, nz, ph, pk, sg, us, za.
  - Spanish: ar, bo, cl, co, cr, do, ec, es, gt, hn, mx, ni, pa, pe, py, sv, uy, ve.
  - Korean: kr.
  - `same` = 1 when the song's language is the country's.
- **M2.** One row per Boxscore entry with revenue and tickets sold, across all five parts, hybrid entries excluded
  (as in Q5): outcome log(revenue / tickets sold); regressor log(GDP per capita, current US$, the entry's year).

## 3. Models

- **M1:** log(days_ac) = α_a + γ_c + β · same_ac + ε_ac, with artist and country fixed effects. β is the language
  premium; reported as exp(β) − 1 in percent. Standard errors clustered by country. The country effects absorb how
  long hits last there in general (and so the median number one of parts 1–5); the artist effects absorb how strong
  each focal song is.
- **M1b:** M1 plus same × artist-language group, to see whether the premium is driven by one language.
- **M2:** log(price_e) = δ_t + θ · log(GDPpc_e) + ε_e, with tour fixed effects; θ is the income elasticity of the
  average ticket. Standard errors clustered by country. **M2b:** adds log(tickets available per night) as a control
  for venue size. **M2c:** θ estimated separately for each artist (tour effects within artist).

## 4. Checks

- M1 without the pairs where the song is still charting (their days are lower bounds).
- M1 with *Dynamite* coded as English.
- M1 with the United States coded as Spanish-speaking for Bad Bunny (its Spanish-speaking minority is large).
- M1 dropping Luxembourg (the small-market effect of parts 1–5).
- M2 dropping each artist in turn.

## 5. Reporting

- Every estimate with its 95 % interval; no p-value thresholds and no "supported" labels, as the analysis is
  exploratory. The article reports β and θ, and the per-artist θ, whatever their size or sign.
- Czechia is placed on M1's residuals: how much longer or shorter than predicted the five songs lasted there.

## 6. What this will not show

- Why language matters, if it does: radio, playlists, lyrics comprehension and local promotion are not separated.
- Prices set by anyone but the tours' promoters, or prices on resale markets.
- Anything beyond five artists chosen for the series, not at random.

## Changes after registration

None yet.
