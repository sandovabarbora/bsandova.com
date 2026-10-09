# Does a concert move the charts? Harry Styles: Live on Tour, 2017–2018 — research design

**Status: analysis plan committed 2 October 2026, before this analysis was run; the author had worked with these data
since March 2026.** Registration is
self-timestamped, as for the film fund study and Pop, measured. In the article this is a "pre-specified
analysis: analysis plan committed at `<hash>` on 2 October 2026, before this analysis was run; commit times are
self-reported".
Deviations are listed, dated, under "Changes after registration".

## 0. What has already been seen

- **Tour schedule.** The Wikipedia article *Harry Styles: Live on Tour* (revision 1342196247) was parsed for Pop,
  measured, part 1: 74 Boxscore entries in 24 countries (England and Scotland counted as the United Kingdom), their
  dates, venues, tickets sold and gross. Their sell-through and ticket prices were seen.
- **Chart data.** The author has worked with these data since March 2026; the plan fixes the analysis, not
  ignorance of the data.
- **Pop, measured, part 1.** Its kworb.net totals (days in the chart up to 2026) were seen; they contain no daily
  series and no date-level figure.
- **Prior expectation.** The author expects a concert to raise an artist's streams in the host country for a few
  weeks.

## 1. Question

**Q (effect).** In a country where Harry Styles played on *Live on Tour*, did his share of that country's Spotify
Top 200 rise in the weeks after his first show there, compared with countries he had not yet played or never
played?

The estimand is the average effect on the treated countries, by week relative to the first show (event time).

## 2. Data

- **Charts.** Spotify Charts, daily Top 200 by region, 2017–2021, as collected on Kaggle by Dhruvil Dave (ODbL)
  [D1]. One file, `charts.csv`, hashed on arrival; its hash is published. Rows used: chart "top200", regions that
  are countries, dates 1 March 2017 to 31 December 2018.
- **Harry Styles's songs.** Rows whose artist field contains "Harry Styles", by exact match after Unicode
  normalisation. The list of matched titles is published.
- **Tour.** Every show row (not cancelled or postponed) in the concert tables of the same Wikipedia revision,
  whether or not it has Boxscore figures. Treatment date = the date of the first show in the country. Countries with
  a chart and no show are never treated.
- **Window.** The tour ran from 19 September 2017 to 14 July 2018. Event time runs from 12 weeks before to 12
  weeks after the first show. The album *Harry Styles* was released on 12 May 2017, before the window's first
  treated date; no album was released inside it.

## 3. Outcomes

- **Y1 (primary).** His share of the country's Top-200 streams that week: the streams of his songs in the
  country's daily Top 200, summed over the week, divided by the week's total Top-200 streams in that country. Zero
  when none of his songs charts. The share removes market size and Spotify's growth.
- **Y2.** The average number of his songs in the country's daily Top 200 that week.
- **Y3 (exploratory).** Y1 for his three most-streamed songs of the window together, excluding the rest.

Because only the Top 200 is published, streams below the 200th place are invisible. A country where he never
reaches the chart contributes zeros before and after; the article states that Y1 measures chart presence, not all
listening.

## 4. Estimation

- **Estimator.** Callaway and Sant'Anna's group-time average treatment effects for staggered adoption [R1], with
  groups = the week of the first show. Comparison units: not-yet-treated and never-treated countries (primary);
  never-treated only (sensitivity). No covariates in the primary analysis. Weekly data, weeks starting Monday.
- **Aggregation.** The dynamic (event-study) aggregation for event weeks −12 to +12, and one summary: the average
  effect over weeks 0 to +4.
- **Inference.** 95 % uniform confidence bands from the multiplier bootstrap clustered by country (999 draws), as
  implemented in the `csdid` package; the seed is fixed.
- **Software.** Python `csdid` (version recorded at run time). If it fails on these data, the R `did` package is
  used with the same settings, and this is logged.
- **Units.** A country enters if its Top-200 chart has data for every week of the window. Countries with fewer than
  12 pre-treatment weeks in the data are dropped from the dynamic aggregation and listed.

## 5. Validity checks

- **Pre-trends.** The event-study coefficients for weeks −12 to −2 are reported with their band. Anticipation is
  allowed for: week −1 is reported separately, because ticket sales and announcements precede the show.
- **Placebo.** Every country's first-show date is moved 26 weeks earlier, and the summary effect is re-estimated.
- **Leave-one-out.** The summary effect is re-estimated dropping each treated country in turn; the range is
  reported. The United States and the United Kingdom, the two largest markets and the first shows, are named.
- **Never-treated comparison.** As in §4.

## 6. Labels

- The summary effect over weeks 0 to +4 is **supported** if its 95 % interval excludes zero, and the pre-trend
  coefficients' band includes zero at every week from −12 to −2.
- It is **not supported** if the interval includes zero and lies within ±10 % of the treated countries' mean Y1 in
  weeks −12 to −2.
- Anything else is **inconclusive**, and the article says which condition failed.
- Y2 and Y3 are reported with the same rule but do not change the headline.

## 7. What this will not show

- Listening outside the Top 200, on other services, on radio or at the show itself.
- Whether the concert caused the effect through the show, the press around it, or ticket-holders preparing;
  the estimate bundles these.
- Effects of later tours: *Love On Tour* (2021–2023) is mostly outside the data (which end in 2021) and its 2021 leg
  is in one country only.
- Revenue or welfare.

## References

- [R1] Callaway, B., Sant'Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. *Journal of
  Econometrics* 225(2), 200–230. doi:10.1016/j.jeconom.2020.12.001
- [D1] Dave, D. (2022). Spotify Charts. Kaggle, ODbL. https://www.kaggle.com/datasets/dhruvildave/spotify-charts
- Wikipedia contributors, *Harry Styles: Live on Tour*, revision 1342196247.

## Changes after registration

None yet.

- **9 October 2026, correction to the record, after publication.** On 5 October 2026 (commit `c953c92`) the status
  line and §0 of this file were rewritten in place; registered text should not have been edited. As committed at
  `54fe975` on 2 October 2026 they read: "**Status: design committed 2 October 2026, before the chart data were
  downloaded or opened.** Registration is self-timestamped, as for the film fund study and Pop, measured. In the
  article this is a "registered analysis plan: design committed at `<hash>` on 2 October 2026, before the results
  commit; commit times are self-reported"." In §0, the tour bullet ended "Their sell-through and ticket prices were
  seen. No streaming figure for any date before 2026 was seen.", and the chart bullet read "**Chart data.** Only the
  dataset's metadata was read (title, size 3.48 GB, licence ODbL for the database, last updated 9 February 2022,
  description: Spotify's daily Top 200 and Viral 50 for every region, 2017–2021)." The 5 October wording ("the
  author had worked with these data since March 2026") does not say which data it covers, and the repository does
  not document it (private; not verifiable). The design commit `54fe975` and the results commit `b156dfb` are on
  the branch of pull request 33 and are kept by the tags `concert-effect-design` and `concert-effect-results`,
  created on 9 October 2026; on `main` both are in the squash commit `cdd9c4f` and are not independently
  timestamped there.
- **9 October 2026, reading of the registered labels, after publication.** The §6 condition for "supported"
  requires every pre-trend band from −12 to −2 to include zero; week −10 does not, so the pre-trend check failed.
  The article now reports the summary as a difference relative to countries not yet visited, with no causal reading,
  and the show-week coefficient, which §4 reports without a label, as descriptive.

**9 October 2026 (clarification of today's note).** "Worked with these data since March 2026" means the author has worked
with these sources continuously since March 2026, in work that led to this study, so the design was written with knowledge of
the sources, not blind to them. This replaces the reading given earlier today (that its extent was unrecorded, or a
list of what it covers). The registered text and the dated notes above are unchanged.
