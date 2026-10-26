# Did two actor memes send people to Wikipedia? — research design

**Status: pre-specified analysis, design committed 26 October 2026, before any pageview number for any article was
downloaded.** An event study of daily English-Wikipedia pageviews around two memes of autumn 2023. The steps follow in
dated commits: design → code and tests on made-up data (frozen by tag before it runs) → real data and screening →
results → page. Commit times are self-reported; the signed tag `memes-design` will fix this text. Deviations are
listed, dated, in the change log. The study replaces the author's own pre-registration file (`PREREG.md` in her spec).

## 0. What has already been seen

- **The spec** was written by the author on 26 October 2026 (Czech original, condensed faithfully into English by the
  drafting assistant). A prototype of the method ran on **simulated data only**. She has seen **no pageview result** for
  these actors, in Wikipedia or anywhere else (stated 26 October 2026).
- **The author knows both memes** (the "Cameron Tucker Smiling" photo of Eric Stonestreet, and the Kevin James photo
  from The King of Queens). **Prior expectation**, stated 26 October 2026: "I honestly don't know what to expect, rather
  b", meaning option b: a jump, but a small one that fades within a few days. She has no guess on Cam against Kevin
  James.
- **The drafting assistant** is an AI model with general training knowledge. It may have seen coverage of these memes
  and of the actors. As far as it knows it has seen no Wikipedia pageview number for them, but it cannot rule that out
  and cannot audit its own training data. **This is a limit on blinding**: the design was written by something that may
  carry a vague idea of how big these jumps were.
- **What was read while building the design (26 October 2026).** Pageview numbers were not downloaded, not even one
  test request, for any article. The spec's "verify all article names with one test request" is replaced by a title
  check through the MediaWiki API (§3), which returns existence and normalised titles and no views. The sources of
  event dates were read, and so were the API's documentation and rate limits. No article, chart or post that reports
  Wikipedia views or search interest for these actors was read; the Know Your Meme "Search Interest" sections hold a
  chart only, and no figure from them was read. Every address opened:
  - MediaWiki API, `https://en.wikipedia.org/w/api.php`: `action=query&prop=info` for the 14 titles of the spec; the
    same with `redirects=1&prop=extracts|pageprops&exintro` for Gary Valentine, Victor Williams and Kevin James (the
    first 200 characters of the introduction of each were read, to see who the redirect and the page are about);
    `list=search` for "Gary Valentine King of Queens comedian" (five titles and snippets); `prop=info` for the four
    titles `Gary_Valentine_(comedian)`, `_(actor)`, `_(disambiguation)` and `_(Blondie)` (all missing, none adopted);
    and `https://en.wikipedia.org/w/index.php?title=Gary_Valentine&redirect=no&action=raw` (the redirect's wikitext).
  - Know Your Meme: `https://knowyourmeme.com/memes/cameron-tucker-smiling` (read in full),
    `https://knowyourmeme.com/memes/kevin-james-smirking-getty-image` (read to the paragraph on 23 January 2024, about
    the first 3 500 characters), and two guessed addresses that returned 404 and were not used,
    `.../memes/kevin-james-smiling` and `.../memes/kevin-james-smirking`. Know Your Meme did not block the requests.
  - Wikimedia Analytics API documentation, `https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/` with
    `documentation/getting-started.html`, `documentation/access-policy.html`, `documentation/troubleshooting.html`,
    `concepts/page-views.html` and `reference/page-views.html` (404, not used: `documentation/api-etiquette.html`,
    `documentation/rate-limits.html`).
  - Rate limits and client policy: `https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits` (read),
    `https://api.wikimedia.org/wiki/Rate_limits` and
    `https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy` (searched for the terms
    "rate limit", "per minute" and "User-Agent" only).
- **Facts from those pages that shaped the design.** Know Your Meme dates the first known post of the Kevin James
  meme to 21 September 2023 and the first notable TikTok of the Cam meme to 13 June 2023. Of the Cam meme it says the
  first X post it lists is of 27 September 2023 and that the image "grew popular on X in late September and early
  October 2023", with its most-liked listed post on 6 October (300 000 likes on X, an engagement figure, not a view
  of any Wikipedia page). It also says Leah Remini, a King of Queens co-star and one of the controls of Kevin James,
  reacted to the Kevin James memes on X on 26 September 2023. This was read before the controls, windows and labels
  below were fixed, so those choices are not blind to the chronology. They are blind to every attention measure.
- **Not read:** the Rolling Stone India piece of 10 October 2023 that the spec cites for Kevin James ("last month");
  Know Your Meme made it unnecessary.
- **The external reference pool (26 October 2026, after the author's decisions).** Built by `tools/memes/pool.py` from
  Wikipedia text and page existence only, with no pageview number: `list=categorymembers` for the four categories of
  §2 (484 show articles); `prop=revisions&rvprop=content` for those articles, for the Modern Family and King of Queens
  articles and for the candidate actors (read by code for the infobox fields `network`, `last_aired`, `starring` and
  `death_date` only); `prop=info|pageprops` for every candidate title. I read the Modern Family infobox, the starring
  list of The King of Queens and the first lines of the "Rico Rodriguez" disambiguation page. The final list of actors
  was seen only after the rule had been fixed and applied. As actors they are known to the drafting assistant (§0
  above).
- **Review.** Nothing yet. The code is reviewed before the freeze tag (change log).

## 1. Questions and hypotheses

Associations around dated events, not causal effects of a meme: other things happen to actors in the same weeks (§8).
**Day 0** is the calendar day, UTC as in the API, of the event date in §2. **Attention** is log(1 + daily views) of an
English-Wikipedia article, all access methods, `agent=user`.

- **H1, Stonestreet (confirmatory).** The cumulative abnormal attention CAR(−3, +30) of `Eric_Stonestreet` is positive
  and its placebo p-value (§4) is below 0.05 after the Holm correction. Event date 27 September 2023. Baseline: the
  daily median of attention over the nine articles of the Modern Family cast (`MF_CAST`, §2).
- **H1, Kevin James (confirmatory).** The same for `Kevin_James`, event date 21 September 2023, baseline the daily
  median of attention over the King of Queens controls (§2). It enters the Holm family because its date is **found in a
  source** (Know Your Meme). Had it been detected from the data (the spec's fallback), it would be exploratory, carry
  `event_date_detected: true`, and stay out of H1 and Holm.
- **H1-falsification (separate, uncorrected; deviation A, revised 26 October 2026).** A jump that the cast shares is
  news about the show, not the meme. The statistic is the cumulative abnormal attention CAR(−3, +30) of the **cast
  series**, the daily median of attention over the cast's control articles, against an **external index**, the daily
  median of attention over the reference pool of actors outside both shows (§2). Same market model, same estimation
  window and blocked days, same 300 pseudo-dates and same p = (k + 1)/(n + 1) as H1 (§4). It is run for both events
  and **gates the label of Stonestreet only** (§6): "p < 0.05" is read there as "the cast moved too". For Kevin James
  it is **descriptive only and carries no label**, because the meme itself reached his co-stars (Leah Remini's public
  reaction, §0), so the exposure of the controls is part of that meme and the test cannot separate the two. It is not
  corrected for multiplicity: the thesis is the more demanding the more often this test fires. **Leave-one-out stays
  as a reported check only**: each control against the median of the other controls, median of the CARs, same
  pseudo-dates (`loo_car`, `loo_p`). It cannot see a jump that all controls share (§5), which is why it no longer
  gates anything.
- **H2 (descriptive, no p).** Half-life of abnormal attention, Stonestreet against Kevin James: days from the peak
  abnormal attention (searched from day 0 to day +30) to the first day it is below half the peak. `None` if the peak is
  not positive or it does not halve by day +30. The difference in days is reported with both numbers and the peak
  dates. The raw daily series is used, so a single noisy peak can set the number (§8). A **sensitivity check** repeats
  the Stonestreet half-life with day 0 moved to 6 October 2023, the day of the most-liked post Know Your Meme lists
  (§7); the registered day 0 stays 27 September.

**Holm family (deviation B).** The confirmatory tests: H1 Stonestreet and H1 Kevin James, two tests: the smaller raw p
must be below 0.025, the larger below 0.05 once the smaller has passed. Adjusted p-values are reported. Falsification,
sensitivity runs and the TikTok run never enter the family.

### Deviations from the author's spec

Agreed with the author on 26 October 2026:

- **A.** Falsification does not use the controls' own median, against which the median control AR is about 0 by
  construction. First agreed as a leave-one-out index; **revised the same day by the author to an external index**
  (§1), because a leave-one-out median hides a jump that every control shares. Leave-one-out stays as a reported
  check.
- **B.** Holm-Bonferroni only across the confirmatory tests, H1 Stonestreet and H1 Kevin James (the second only
  because its date is found in a source). The falsification test is separate and uncorrected.
- **C.** The TikTok pre-wave, 13 June 2023, with a window around it, is excluded from the estimation window of the
  September event and from the placebo pool. **The window is −7 to +30 days, 6 June to 13 July 2023**, chosen by the
  drafting assistant before any data (a week for build-up, a month as long as the event window; Know Your Meme says the
  first TikTok had 590 000 plays in four months, so a longer tail cannot be excluded). Its 38 days leave 82 of the 120
  estimation days (30 are needed). **Confirmed by the author, 26 October 2026.**
- **D.** The study lives in this repository (`tools/memes/`, this design in the site's registered-study format) and its
  article is in English with the spec's style rules.
- **E (accepted by the author, 26 October 2026). The King of Queens controls.** The spec lists `Leah_Remini`,
  `Victor_Williams` and `Gary_Valentine`. The title check (§3) found that `Gary_Valentine` exists but is a redirect to
  **Gary Lachman**, the Blondie bassist, not the comedian of The King of Queens, and the comedian has no article of
  his own (four candidate titles are missing). The API does not count a redirect title as views of its target page, so
  downloading it would give the views of a title that is hardly visited. The spec says to stop and never guess a
  replacement. The code stops on any redirect. The registered controls of Kevin James are therefore `Leah_Remini` and
  `Victor_Williams`, with two controls the "median" is their mean, the leave-one-out index is the one other control,
  and noise in the baseline is larger than with nine (§5 gives the effect on power). Kevin James stays in H1 and in
  the Holm family with these two controls. His falsification is descriptive only, because Remini reacted to the meme
  herself (§1).

Made by the drafting assistant and **to be confirmed by the author before the freeze**:

- **F.** A title that is a redirect or missing stops the run (above), and the check is code, run before the download.
- **G.** Day 0 and the window offsets are calendar days. The pseudo-event rule (§4) is read as: the whole span of a
  pseudo event (estimation plus event window) must lie at least 30 days away from the real event window, which is
  stricter than the spec's "its window is farther than event_window[1] + 30 days". Without it a placebo estimation
  window could contain the real spike.
- **H.** Half-life: the peak is searched from day 0, not from day −3, so a pre-event wiggle cannot set it.
- **I.** `EventResult` has extra fields with defaults (`confirmatory`, `falsification_car`, `falsification_p`,
  `holm_p`, `label`, `variant`); `run_event` takes keyword options for sensitivity runs (`how`, `drop`, windows);
  `control_index` takes `how="median"|"mean"`. Binding signatures are otherwise unchanged. Extra modules: `synth.py`
  (made-up panels), `simulate.py` (§5). No `pyproject.toml`: the site's tools run through `uv run --no-project --with`.
- **J.** Retry-After is honoured on 429 and 503, as the rate-limit page asks; otherwise the spec's exponential backoff.
- **K.** The CLI refuses to read real pageviews without `--unblind` (§2). `--synthetic` runs the whole pipeline on
  made-up data.
- **L.** The confounder check of the spec's §8.1 draws raw series up to day −4 only, so event windows cannot be seen
  before the results are written (§3).
- **M.** The README of the spec is `tools/memes/README.md`; the page's style test also forbids semicolons in the
  visible prose.
- **N. `Rico_Rodriguez` is a disambiguation page, not the actor.** The spec's title lists a Cuban-born Jamaican
  trombonist (1934–2015), the actor (born 1998) and a fictional character. The Modern Family infobox links the actor as
  `Rico_Rodriguez_(actor)`, which `MF_CAST` now uses: a title taken from the show's own infobox, by the same rule as the
  reference pool, not a guess. The title check now also stops on disambiguation pages. Without the author's
  agreement the alternative is to drop him (eight cast controls).
- **O.** The external reference pool and the pool rule (§2) are the assistant's reading of the author's decision of
  26 October 2026, applied mechanically; the lists are frozen in `config.py`.
- **P.** `EventResult` also carries `loo_car` and `loo_p` (the leave-one-out check); the extra sensitivity runs are
  `external_index` (Stonestreet H1 against the external index) and the 6 October day 0 (§7).

## 2. Data and definitions

- **Source.** Wikimedia Analytics API, per-article daily pageviews
  (`https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/<title>/daily/<from>/<to>`),
  data under CC0, available from 1 July 2015. Range **1 January 2021 to 31 December 2024**, 1 461 days. A one-year
  range left about 29 placebo dates and a 30 % false-positive rate in the prototype; hence four years and a hard
  minimum of 100 admissible placebo dates (§4).
- **Requests.** One article per request, one at a time, 0.2 s apart (49 requests; the limit for a client that sends a
  compliant User-Agent is 200 requests a minute, at most 3 at once). User-Agent `bsandova-meme-event-study/0.1
  (https://bsandova.com)`, never an e-mail address. Titles are URL-encoded (`quote(title, safe="")`). Retries on 429,
  500, 502 and 503, at most 3 attempts, exponential backoff. A 404 stops the run at once: the API answers 404 both for
  zero views and for data not yet loaded, and for these articles over four years neither is plausible. Days the API
  omits are reindexed to the full daily range and filled with 0, and the count is logged.
- **Panel.** `tools/data/memes/raw/pageviews.csv` (gitignored), never edited by hand; its sha256, the range and the
  download date go to `docs/research/memes-files.sha256`. `--panel-csv` reruns without downloading.
- **Articles (49).** Targets `Eric_Stonestreet`, `Kevin_James`. `MF_CAST`: `Ed_O'Neill`, `Sofía_Vergara`,
  `Julie_Bowen`, `Ty_Burrell`, `Jesse_Tyler_Ferguson`, `Sarah_Hyland`, `Ariel_Winter`, `Nolan_Gould`,
  `Rico_Rodriguez_(actor)` (deviation N). `KOQ_CAST`: `Leah_Remini`, `Victor_Williams` (deviation E). The 36 actors of
  the reference pool below.
- **Reference pool (author's decision of 26 October 2026; rule fixed before any data).** Actors outside both shows, for
  the external index of the falsification and one sensitivity run. The rule, applied as written by `pool.py` to
  Wikipedia text only:
  1. Shows: the articles in the categories 2010s and 2020s American multi-camera sitcoms and 2010s and 2020s American
     single-camera sitcoms (484 articles, read 26 October 2026).
  2. Keep a show whose infobox `network` is ABC, CBS, NBC, Fox or The CW and whose infobox `last_aired` year is from
     2016 to 2021 (the original run ended then), that is not animated (no category with "animated"), and that is not
     Modern Family or The King of Queens.
  3. Drop a show that lists any actor of the infobox `starring` field of Modern Family or The King of Queens (this
     removes A.P. Bio, Happy Together and Kevin Can Wait). Drop a show with a starring actor whose article gives a
     death date in 2023 (this removes Brooklyn Nine-Nine and The Odd Couple (2015); Friends, which would be dropped
     for Matthew Perry's death on 28 October 2023, is out anyway because it ended in 2004). Imaginary Mary was dropped
     as animated. No other show was dropped on a judgement.
  4. Candidates: the links of the infobox `starring` field of each kept show, in billing order, deduplicated, minus any
     actor of the two excluded shows. Every candidate title is checked with `prop=info|pageprops`; **a missing title,
     a redirect or a disambiguation page is dropped and not replaced**: `Ella_Allan`, `Mia_Allan`, `Odessa_Adlon` and
     `Sarayu_Blue` (redirects), and `MOS:TV` (a stray link in an infobox, a redirect). 310 eligible actors remain.
  5. Cap at 36 (`CAP`): shows in alphabetical order, first-billed actor of each show, then second-billed, and so on,
     until 36 distinct actors are taken.
  The 53 shows: `2_Broke_Girls`, `9JKL`, `Abby's`, `Alex,_Inc.`, `American_Housewife`, `Bless_This_Mess_(TV_series)`,
  `Broke_(2020_TV_series)`, `Call_Your_Mother`, `Carol's_Second_Act`, `Champions_(American_TV_series)`, `Connecting`,
  `Downward_Dog_(TV_series)`, `Dr._Ken`, `Fam_(TV_series)`, `Fresh_Off_the_Boat`, `Ghosted_(TV_series)`, `I_Feel_Bad`,
  `Indebted`, `LA_to_Vegas`, `Last_Man_Standing_(American_TV_series)`, `Life_in_Pieces`, `Living_Biblically`,
  `Man_with_a_Plan_(TV_series)`, `Marlon_(TV_series)`, `Me,_Myself_&_I_(TV_series)`, `Mike_&_Molly`, `Mixed-ish`,
  `Mom_(TV_series)`, `New_Girl`, `Outmatched`, `Perfect_Harmony_(TV_series)`, `Powerless_(TV_series)`,
  `Rel_(TV_series)`, `Schooled_(TV_series)`, `Single_Parents_(TV_series)`, `Speechless_(TV_series)`,
  `Splitting_Up_Together`, `Sunnyside_(American_TV_series)`, `Superior_Donuts_(TV_series)`, `The_Big_Bang_Theory`,
  `The_Carmichael_Show`, `The_Cool_Kids_(TV_series)`, `The_Good_Place`, `The_Great_Indoors_(TV_series)`,
  `The_Kids_Are_Alright_(TV_series)`, `The_Last_Man_on_Earth_(TV_series)`, `The_Mick_(TV_series)`,
  `The_Middle_(TV_series)`, `The_Real_O'Neals`, `The_Unicorn_(TV_series)`, `Trial_&_Error_(TV_series)`, `Undateable`,
  `United_We_Fall_(TV_series)`.
  The 36 actors, in the order taken: `Kat_Dennings`, `Linda_Lavin`, `Natalie_Morales_(actress)`, `Zach_Braff`,
  `Katy_Mixon`, `Dax_Shepard`, `Jaime_Camil`, `Kyra_Sedgwick`, `Patricia_Heaton`, `Anders_Holm`, `Otmara_Marrero`,
  `Allison_Tolman`, `Suzy_Nakamura`, `Nina_Dobrev`, `Randall_Park`, `Adam_Scott`, `Paul_Adelstein`, `Adam_Pally`,
  `Kim_Matula`, `Tim_Allen`, `Colin_Hanks`, `Jay_R._Ferguson`, `Matt_LeBlanc`, `Essence_Atkins`, `Bobby_Moynihan`,
  `Billy_Gardell`, `Tika_Sumpter`, `Anna_Faris`, `Zooey_Deschanel`, `Jason_Biggs`, `Bradley_Whitford`,
  `Vanessa_Hudgens`, `Sinbad_(comedian)`, `AJ_Michalka`, `Taran_Killam`, `Minnie_Driver`.
  The index is the daily median of log(1 + views) of these 36.
- **Events** (in `tools/memes/config.py`, with their sources, not in code):

  | Event | Target | Controls | Day 0 | Role | Source |
  |---|---|---|---|---|---|
  | Stonestreet (Cam) | `Eric_Stonestreet` | `MF_CAST` | 2023-09-27 | H1, Holm family | Know Your Meme, "Cameron Tucker Smiling": first X post it lists |
  | Kevin James | `Kevin_James` | `KOQ_CAST` | 2023-09-21 | H1, Holm family | Know Your Meme, "Kevin James Smirking Getty Image": first known meme post on X |
  | Stonestreet TikTok pre-wave | `Eric_Stonestreet` | `MF_CAST` | 2023-06-13 | sensitivity | Know Your Meme, "Cameron Tucker Smiling": first notable TikTok |

The Cam date is the first post Know Your Meme lists, not the day the meme took off (it names 6 October for that), and
a date from a meme database can be a day off in either direction. Both are limits (§8), not choices: the event window
reaches 30 days past day 0.
- **Blocked days (deviation C).** For Stonestreet, 6 June to 13 July 2023 are dropped from the estimation window and
  no placebo span may touch them. For the TikTok run, the September wave (24 September to 27 October 2023) is kept
  out of the placebo pool the same way.
- **Windows.** Estimation days −150 to −31, event window −3 to +30. For Stonestreet the estimation window is 30 April to
  27 August 2023 less the blocked days, 82 days; for Kevin James 24 April to 21 August 2023, 120 days.

## 3. Screening (before any estimate is read)

1. **Title check, done 26 October 2026, no views.** All 14 titles of the spec exist and normalise only by underscores
   to spaces (`Eric_Stonestreet` is `Eric Stonestreet`, and so on; `Sofía_Vergara` keeps its accent, `Ed_O'Neill` its
   apostrophe). **`Gary_Valentine` is a redirect to Gary Lachman** (deviation E) and **`Rico_Rodriguez` is a
   disambiguation page** (deviation N). `Victor_Williams` is the King of Queens actor (introduction read). After the
   two decisions the check was repeated on the **49 titles of §2**: all exist, none is a redirect or a disambiguation
   page, none normalises beyond underscores. The code (`cli.py --verify-titles`) repeats the check before a download
   and stops on a missing title, a redirect or a disambiguation page.
2. **Structure of the panel.** Rows per article (1 461), days filled with 0, the first and last date. The run stops, and
   the change log records the decision before any estimate, if an article has zeros on more than 1 % of days.
3. **Confounders in the estimation windows.** `estimation_windows.svg` draws the raw series of every article **up to
   day −4 of each event only**. Spikes are recorded in the README with what is known of them (a death, a wedding, a new
   show). **Nothing in the analysis is changed because of what is seen there**; the median baseline is the registered
   defence, and a spike in the target's own estimation window is stated next to the result.
None of it compares attention across events or after day −4.

## 4. Estimation (MacKinlay 1997, *Journal of Economic Literature* 35(1))

1. y = log(1 + views). Baseline x = daily median of y over the controls. (For the falsification, y is the cast's
   daily median and x the daily median over the reference pool.)
2. Market model: OLS of y_target on x over the estimation window less blocked days: y = a + b·x.
3. AR_t = y_t − (a + b·x_t) for t = −3 … +30. **CAR** = ΣAR_t. Mean uplift in per cent = (exp(mean AR) − 1)·100.
4. Half-life and peak as in §1 (H2), on AR from day 0.
5. **Placebo test.** A pseudo event date d is admissible if its span, days d−150 to d+30, lies fully in the data; ends
   or begins at least 30 days (`exclusion_days`) away from the real event window (days −3 to +30), that is, at least
   30 days lie between the two; and does not touch any blocked interval at all. From the admissible dates 300 are
   drawn without replacement (`numpy.random.default_rng(42)`); for each, the same model and the same CAR are computed.
   One-sided **p = (k + 1)/(n + 1)**, k the number of placebo CARs at least as large as the true one, n = 300. With
   fewer than 100 admissible dates the run stops with an error that recommends a longer range. Admissible dates: 927
   for Stonestreet and 1 007 for Kevin James.
6. **Falsification** (§1): the cast series against the external index with steps 1 to 5 unchanged (same windows, same
   blocked days, same 300 dates, same p). The leave-one-out check: per control, the same steps against the median of
   the other controls; the statistic is the median over controls of the CARs; the same 300 dates.
7. Errors stop the run with a clear message: an estimation window under 30 usable days, a constant baseline, an
   estimation window not ending before the event window, a window outside the data (both ranges are named), a
   missing target or control (listed), no controls, too few placebo dates, a gap in the daily index.
8. Versions of Python, numpy and pandas are recorded in `memes-results.json`. Outputs: `summary.json`,
   `ar_<target>.csv`, `abnormal_attention.svg`, `estimation_windows.svg`, `index.html` under `tools/data/memes/out/`
   (gitignored), and the results copy `docs/research/memes-results.json`. The page is copied to the site by the
   author.

## 5. Power

Computed on **made-up panels only** (an AR(1) factor with φ 0.8 and innovation sd 0.1 shared by all articles, a second
such factor for each group of articles, idiosyncratic noise sd 0.1, target beta 1), with the registered geometry: 9
cast controls, the 36-actor reference pool and the blocked days for Stonestreet; 2 controls and the same pool for
Kevin James; 300 placebo dates; the 4-year range; 300 simulated panels per cell. A shock *s* adds s·exp(−t/5) to the
target's attention from day 0 (so *s* = 0.3 is +35 % on day 0 and about +5 % on average over the window; the CAR is
about 5.5·*s*). The numbers below come from `tools/memes/simulate.py` (`docs/research/memes-power.json`), run once
niced on 26 October 2026.

| | no shock (false positives) | s = 0.3 | s = 0.5 | s = 1.0 |
|---|---|---|---|---|
| Stonestreet H1, share with p < 0.05 | 5.7 % | 56 % | 87 % | 100 % |
| Stonestreet H1, share with p < 0.025 | | 46 % | 83 % | 100 % |
| Kevin James H1, share with p < 0.05 | 5.0 % | 57 % | 95 % | 100 % |
| Kevin James H1, share with p < 0.025 | | 43 % | 86 % | 100 % |

False positives of the falsification statistics without any jump, at the 5 % level: external 7.3 % (Stonestreet) and
7.0 % (Kevin James); leave-one-out 7.7 % and 6.0 %. Detection of a jump of the cast controls, share of panels with
p < 0.05 (Stonestreet, nine controls; Kevin James has two):

| Cast controls that jump | external, s = 0.5 | external, s = 1.0 | leave-one-out, s = 0.5 | leave-one-out, s = 1.0 |
|---|---|---|---|---|
| 3 of 9 | 11 % | 14 % | 4 % | 0 % |
| 5 of 9 (a majority) | 13 % | 20 % | 40 % | 89 % |
| 9 of 9 (all) | 20 % | 42 % | 14 % | 24 % |
| Kevin James, 2 of 2 | 20 % | 42 % | 17 % | 32 % |

The prototype's one-off figures were 4.3 % false positives and power 67, 97 and 100 % for 0.3, 0.5 and 1.0. Here the
estimation window is shorter (82 days with the exclusion), and the test goes through Holm. At the Holm level 0.025 the
power of H1 is about 83 to 86 % for a shock of 0.5 (a CAR of about 2.7, which is about +9 % on average over the 34
days) and under half for 0.3, so the smallest jump the design can tell from chance is about **0.5**. The H1 false-
positive rates are close to 5 %. **The falsification is much weaker than H1**: with these made-up panels the external
index sees a jump of all nine cast controls in 20 % of panels at s = 0.5 and in 42 % at s = 1.0, and a majority jump
in 13 % and 20 %, because the cast's own factor, which the external index does not explain, is noisy. Leave-one-out
sees a majority jump much better and a unanimous one worse, which is why it is kept as a check. A quiet falsification
is therefore weak evidence that the cast did not move. Real attention series carry spikes and news that these panels
lack, so **real power is lower**, and a "no detectable jump" will be read as "none larger than about 0.5 would have
been seen".

## 6. Labels

For each confirmatory event (Stonestreet and Kevin James), in this order:

1. **positive** — Holm-adjusted p < 0.05 and CAR > 0, and, for Stonestreet, the external falsification p ≥ 0.05.
2. **inconclusive** — the Holm-adjusted p is below 0.05 but, for Stonestreet, the external falsification p is below
   0.05 (the cast moved too); or the raw p is below 0.05 and the Holm-adjusted p is not.
3. **no detectable jump** — otherwise (raw p ≥ 0.05). Failure to reject is not evidence of no jump: the §5 power says
   what size would have been seen.

H2 has no label. The sensitivity runs (§7) do not relabel; if one of them has a raw p ≥ 0.05 where the primary has p <
0.05, the article says so next to the label. If the pages show a jump in neither actor, that is a result, and the page
says the memes spread by scrolling without searching.

## 7. Checks (reported; none relabels a primary result)

1. Event window (−3, +14) and (−3, +60), for both events (the pseudo-event pool is recomputed: 975 and 837 dates for
   Stonestreet).
2. Mean instead of median baseline.
3. Stonestreet without `Sofía_Vergara` (the spec: own news in 2023).
4. The TikTok pre-wave as its own event (13 June 2023, windows as primary, the September wave blocked), raw p only.
5. Stonestreet H1 against the **external index** instead of the cast (the 36 actors of §2 as controls; falsification
   not run in this variant). Raw p only.
6. Stonestreet with **day 0 on 6 October 2023**, the day of the most-liked post Know Your Meme lists (the estimation
   window moves with it, the blocked days stay): CAR, peak date and half-life, for H2 only. Registered day 0 stays 27
   September.
7. The falsification for Kevin James and the leave-one-out check for both events (reported, not label-bearing, §1).

Each is a `variant` in `summary.json`. Raw placebo p only; no correction.

## 8. Limits stated now

- **Attention is not meme exposure.** Pageviews measure looking something up. A meme that spreads by scrolling leaves no
  trace here, so no detectable jump says nothing against the meme having spread.
- **Event dates.** Day 0 is the first post a database lists, not the take-off (Know Your Meme names 6 October 2023 for
  the Cam meme). The window (−3, +30) covers both, and CAR is a sum over the window, but half-lives (H2) counted from
  day 0 are not comparable with a peak that comes later. Dates can be one day off, and the API counts UTC days.
- **Controls have news and are exposed.** An actor's own news or a show anniversary moves a control. Leah Remini
  reacted to the Kevin James memes on 26 September 2023 (day +5), so her page may rise with the meme, which pulls
  Kevin James's abnormal attention toward zero: this biases against a positive label. With two controls the baseline
  is noisier than with nine. Events that move all actors alike, such as the 2023 actors' strike, enter the baseline
  and drop out.
- **The external index is not a clean baseline either.** The 36 reference actors are other TV actors of one kind of
  show, not a sample of all actors. They have their own news in the same weeks; the median blunts it. The rule
  excludes a show with a starring actor who died in 2023 and nothing else about 2023: it is a mechanical stand-in for
  "a widely known event in 2023", not the thing itself, and a cast event of another kind is not caught. For instance
  Matt LeBlanc, a Friends actor, is in the pool through Man with a Plan, and Matthew Perry died on 28 October 2023, the
  day after the Stonestreet event window ends (the (−3, +60) check includes it). The infobox lists miss actors and may
  carry stray links. If the pool is wrong in a way the control actors do not share, the falsification can fire or stay
  quiet for the wrong reason, and the check reports it either way.
- **Falsification power is limited** (§5): even against an external index a modest cast-wide jump is seen only in some
  panels, and leave-one-out is blind to a jump that every control shares. A cast-wide rise does not give a false
  positive for H1, though: it pulls the baseline up with the target, and the CAR shrinks.
- **A common wave.** The two memes belong to the same autumn 2023 run of "actor stock photo" posts (Know Your Meme calls
  the Cam meme similar to the Kevin James trend), so shared drivers (a platform trend, the same news) are possible and
  the comparison of the two is descriptive.
- **Half-life from raw days.** The peak is the largest single day of noisy daily AR, so the number can jump with one
  day. The peak date is reported beside it.
- **Power was computed on made-up data** (§5). Real series are spikier. The estimation window (April to August 2023) was
  not looked at before registration, so unknown spikes in it are possible (§3).
- **Pseudo-events are not independent.** Spans of the 300 placebos overlap, as the prototype showed for a short range;
  four years and the minimum of 100 dates are the registered answer, and the false-positive rates in §5 are
  the check, on data that have the same AR(1) structure but not real news.
- **The assistant's prior knowledge** (§0) cannot be audited.
- **Gary Valentine** is not in the controls (deviation E), and `Rico_Rodriguez` was replaced by the infobox's
  `Rico_Rodriguez_(actor)` (deviation N).

## Running and verification

Commands, the verified API facts and their dates are in `tools/memes/README.md`.

## Change log

- 26 October 2026: design committed, before any pageview number was downloaded.
- 26 October 2026, decisions of the author, before any pageview number was downloaded: (1) deviation E is accepted:
  Kevin James stays in H1 and in the Holm family with `Leah_Remini` and `Victor_Williams`, and his falsification is
  descriptive only; (2) the TikTok exclusion window, 6 June to 13 July 2023, is confirmed; (3) the falsification uses an
  external reference group, with leave-one-out kept as a reported check, the pool defined by the mechanical rule of §2
  and frozen as 36 actors from 53 shows, and Stonestreet H1 against the external index is a sensitivity check; (4) day 0
  stays 27 September 2023 for Cam, and 6 October 2023 is a sensitivity check for H2; (5) the check is wired into CI.
  Found while applying them: `Rico_Rodriguez` is a disambiguation page and is replaced by the infobox's
  `Rico_Rodriguez_(actor)` (deviation N, awaiting the author's confirmation). The power numbers of §5 come from the
  simulation committed after this design.


