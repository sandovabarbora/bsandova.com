# Did two actor memes send people to Wikipedia? — research design

**Status: pre-specified analysis, design committed 26 October 2026 and revised the same day after two independent
reviews, before any pageview number for any article was downloaded.** An event study of daily English-Wikipedia
pageviews around two memes of autumn 2023. The steps follow in dated commits: design, code and tests on made-up data
(frozen by tag before it runs), real data and screening, results, page. Commit times are self-reported; the signed tag
`memes-design` will fix this text. Deviations are listed, dated, in the change log. The study replaces the author's
own pre-registration file (`PREREG.md` in her spec).

## 0. What has already been seen

- **The spec** was written by the author on 26 October 2026 (Czech original, condensed faithfully into English by the
  drafting assistant). A prototype of the method ran on **simulated data only**. She has seen **no pageview result** for
  these actors, in Wikipedia or anywhere else (stated 26 October 2026, the date of every statement of the author below).
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
    the first 3 500 characters, which contain the 21 September post), and two guessed addresses that returned 404 and
    were not used, `.../memes/kevin-james-smiling` and `.../memes/kevin-james-smirking`. Know Your Meme did not block
    the requests.
  - Wikimedia Analytics API documentation, `https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/` with
    `documentation/getting-started.html`, `documentation/access-policy.html`, `documentation/troubleshooting.html`,
    `concepts/page-views.html` and `reference/page-views.html` (404, not used: `documentation/api-etiquette.html`,
    `documentation/rate-limits.html`).
  - Rate limits and client policy: `https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits` (read),
    `https://api.wikimedia.org/wiki/Rate_limits` and
    `https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy` (searched for the terms
    "rate limit", "per minute" and "User-Agent" only).
  - For the reference pool of §2, the same MediaWiki API: `list=categorymembers` for the four categories (484 show
    articles); `prop=revisions&rvprop=content` for those articles, for the Modern Family and King of Queens articles
    and for the candidate actors (read by code for the infobox fields `network`, `last_aired`, `starring` and
    `death_date` only); `prop=info|pageprops` for every candidate title. I read the Modern Family infobox, the starring
    list of The King of Queens, the starring list of two other shows (to find a comment that held links) and the first
    lines of the "Rico Rodriguez" disambiguation page. The final list of actors was seen only after the rule had been
    fixed and applied. As actors they are known to the drafting assistant (above).
- **Facts from those pages that shaped the design.** Know Your Meme dates the first known meme post of the Kevin James
  image to 21 September 2023 (an X post: "the first known meme to use the image was posted by X user ... on September
  21st, 2023") and the first notable TikTok of the Cam meme to 13 June 2023. Of the Cam meme it lists an X post of 27
  September 2023 as the earliest and says the image "grew popular on X in late September and early October 2023", with
  its most-liked listed post on 6 October (300 000 likes on X, an engagement figure, not a view of any Wikipedia page).
  It also says Leah Remini, a King of Queens co-star and one of the control actors of Kevin James, reacted to the Kevin
  James memes on X on 26 September 2023. This was read before the controls, windows and labels below were fixed, so
  those choices are not blind to the chronology. They are blind to every attention measure.
- **Not read:** the Rolling Stone India piece of 10 October 2023 that the spec cites for Kevin James ("last month");
  Know Your Meme made it unnecessary.
- **Reviews.** Two independent reviews of this design (methods; data and consistency) were read on 26 October 2026,
  before any pageview number was downloaded. Their must-fix and should-fix points, and the author's decisions on the
  open ones, are in this text and in the change log. The code is reviewed again before the freeze tag.
- **Order of writing.** §5 was written after the code and the simulations it reports: the design was committed first,
  the code and the runs followed, and §5's numbers were copied in by a later commit, still before any real data.

## 1. Questions and hypotheses

Associations around dated events, not causal effects of a meme: other things happen to actors in the same weeks (§8).
**Day 0** is a calendar day, UTC as in the API (the time zone of a post on X is not given by Know Your Meme). **One
rule for day 0 in both memes: the date of the earliest post on X that Know Your Meme lists for the meme** (27 September
2023 for Cam, 21 September 2023 for Kevin James; the TikTok of 13 June 2023 is a different platform and is a
sensitivity event). **Attention** is log(1 + daily views) of an English-Wikipedia article, all access methods,
`agent=user`.

**Common definitions.** The market model of §4 fits attention of the target on the daily median attention of a baseline
set of articles, with weekday effects, on days −150 to −31, less the blocked and omitted days. The abnormal attention
AR_t is the target's attention minus the model's prediction, for days −3 to +30. **CAR is the sum of AR_t and is the
test statistic. The headline is the mean uplift**, (exp(mean AR) − 1)·100 per cent: because attention is log(1 + views),
exp(mean AR) − 1 is the proportional gap between 1 + views and the model's 1 + views, close to the proportional gap in
views when views are in the hundreds or more and smaller than it for a page with few views. It is reported with the
**excess views**, the sum over the window of views minus the model's predicted views, as a count. Every p-value is
**one-sided, upper tail**: p = (k + 1)/(n + 1), n the number of placebo statistics and k the number at least as large as
the true one, ties counted as at least as large; only a positive jump counts.

- **H1, Stonestreet (confirmatory).** The CAR(−3, +30) of `Eric_Stonestreet` is positive and its placebo p-value (§4)
  is below 0.05 after the Holm correction. Day 0 27 September 2023. Baseline: the daily median over the nine articles of
  the Modern Family cast (`MF_CAST`, §2).
- **H1, Kevin James (confirmatory).** The same for `Kevin_James`, day 0 21 September 2023. **Baseline: the daily median
  over the external reference pool of actors outside both shows (§2)**, not his own cast: Leah Remini reacted to the
  meme herself, and the median of two controls is their mean. The King of Queens controls, `Leah_Remini` and
  `Victor_Williams`, are a check (§7). It enters the Holm family because its date is **found in a source**. Had it been
  detected from the data (the spec's fallback), it would be exploratory, carry `event_date_detected: true`, and stay out
  of H1 and Holm.
- **Holm, and why.** The two H1 tests form the family: the smaller raw p must be below 0.025 and the larger below 0.05
  once the smaller has passed. The tests are positively dependent (the same calendar wave, overlapping windows, the same
  pool for one baseline and one diagnostic). Holm is valid under any dependence, so it controls the error rate without
  modelling that dependence, at the price of some conservatism that is accepted. The sensitivity checks, the TikTok
  run, the falsification and the space-time check are **outside the family**: reported with raw p, relabelling nothing.
- **H1-falsification (descriptive diagnostic only; deviation A, final 26 October 2026).** It no longer gates a label:
  **labels rest on H1 alone** (§6). The statistic is the CAR(−3, +30) of the **cast series**, the daily median
  attention of the cast's articles, against the **external index**, the daily median of the reference pool, with the
  same model, windows, blocked days, placebo dates and p as H1. It is run for both events and reported with its
  detection power (§5).
  The page carries a pre-written sentence: "No cast-wide move was seen, but the test's power is about X %." (X from §5,
  the detection of a cast-wide jump of 0.5), or, if the p-value is below 0.05, "The castmates' pages moved too, as a
  group. That may be spillover of the meme or news about the show." The reasons for a diagnostic and not a gate: a
  cast-wide jump shrinks H1 and cannot create it, because the baseline rises with the target; the test detects a
  cast-wide jump of 0.5 in about one panel in six against a false-positive rate of about 6 % (§5); and spillover to
  co-stars, such as Jesse Tyler Ferguson, is a plausible part of the meme, not necessarily a rival explanation.
  **Leave-one-out** (each control against the median of the other controls, median of the CARs, same dates) is reported
  as a second diagnostic, `loo_car` and `loo_p`.
- **H2 (descriptive, no p).** On the centred 7-day mean of AR (defined from day 0 on, where all seven days lie in the
  event window), the **peak** is the largest smoothed value and the **half-life** is the number of days from the peak to
  the first day from which the smoothed AR stays below half of the peak for 3 consecutive days. **Censored** if no such
  day exists by the last smoothed day; **no positive peak** if the peak is not above 0; in both cases the half-life is
  `None` and the status says which. **The difference is Stonestreet minus Kevin James in days; if either is `None` it is
  `None` and the article makes no claim about which fades faster.** The half-life of the raw series, as the spec defines
  it (first day below half the maximum), is reported as `half_life_raw_days`. In a variant with another event window the
  smoothing is defined to that window's end less 3 days, so the half-life of the (−3, +14) variant is censored earlier.
  Day 0 6 October 2023 for Stonestreet is a sensitivity check for H2 (§7).

### Deviations from the author's spec

Each is listed with its status. **Confirmed by the author on 26 October 2026** (in the decisions that follow the two
reviews, as they stand in this text): A to P. **Applied on the author's instruction the same day, as the review
fixes:** Q to W.

- **A. Falsification.** Not against the controls' own median, where the median control AR is about 0 by construction.
  Agreed first as leave-one-out, then as an external index, finally as a descriptive diagnostic that gates nothing (§1).
  The reasons are in §1 and §5. Confirmed.
- **B. Holm** only across the confirmatory tests, H1 Stonestreet and H1 Kevin James (the second only because its date is
  found in a source). Confirmed.
- **C. TikTok pre-wave.** 13 June 2023, with a window around it, is excluded from the estimation window of the September
  event and from the placebo pool. **The window is −7 to +30 days, 6 June to 13 July 2023**, chosen by the drafting
  assistant before any data (a week for build-up, a month as long as the event window; Know Your Meme says the first
  TikTok had 590 000 plays in four months, so a longer tail cannot be excluded). Its 38 days leave 82 of the 120
  estimation days. Confirmed.
- **D.** The study lives in this repository (`tools/memes/`, this design in the site's registered-study format) and its
  article is in English with the spec's style rules. Confirmed.
- **E. The King of Queens controls.** The spec lists `Leah_Remini`, `Victor_Williams` and `Gary_Valentine`.
  `Gary_Valentine` is a redirect to **Gary Lachman**, the Blondie bassist, not the comedian of The King of Queens, who
  has no article of his own (four candidate titles are missing). The API does not count a redirect title as views of
  its target. The spec says to stop and never guess a replacement. So the King of Queens cast is `Leah_Remini` and
  `Victor_Williams`. **Final (D2): they are the cast of the descriptive falsification and a check of Kevin James's H1,
  and his primary baseline is the external pool.** Confirmed.
- **F.** A title that is a redirect, a disambiguation page or missing stops the run, and the check is code, run before
  the download. Confirmed.
- **G. Pseudo-event rule.** The whole span of a pseudo event (estimation plus event window) must lie at least 30 days
  away from the real event window, stricter than the spec's "its window is farther than event_window[1] + 30 days".
  Without it a placebo estimation window could contain the real spike. Day 0 and the offsets are calendar days.
  Confirmed.
- **H. Half-life.** Primary on the 7-day smoothed series with a 3-day persistence rule and a defined censoring (§1), the
  spec's raw definition reported beside it; the peak is searched from day 0. Reason: the raw maximum of 34 noisy days
  sets the number. Confirmed.
- **I.** Interface changes against the spec's §6: listed in full under "Changes to the spec's interface" below.
  Confirmed.
- **J.** Retry-After is honoured on 429 and 503, as the rate-limit page asks; otherwise the spec's exponential backoff.
  Confirmed.
- **K.** The CLI refuses to read real pageviews without `--unblind`. `--synthetic` runs the whole pipeline on made-up
  data. Confirmed.
- **L.** The confounder figures of the spec's §8.1 are drawn from before every event window (§3). Confirmed.
- **M.** The README of the spec is `tools/memes/README.md`; the page's style test also forbids semicolons in the
  visible prose. Confirmed.
- **N. `Rico_Rodriguez` is a disambiguation page, not the actor.** The spec's title lists a Cuban-born Jamaican
  trombonist (1934–2015), the actor (born 1998) and a fictional character. The Modern Family infobox links the actor as
  `Rico_Rodriguez_(actor)`, which `MF_CAST` now uses: a title taken from the show's own infobox, not a guess. Confirmed.
- **O. The external reference pool and its rule** (§2), applied mechanically; the lists are frozen in `config.py` and
  the full candidate list is committed. Confirmed.
- **P.** Extra sensitivity runs and diagnostics beyond the spec's: §7. Confirmed.
- **Q. Every admissible pseudo date is used** (927 for Stonestreet, 1 007 for Kevin James), not 300 random draws, so
  the seed no longer matters for the p-value (§4). `n_placebo` can still draw a seeded subset.
- **R. Weekday effects** in the market model (§4), not in the spec.
- **S. Equal estimation days.** Each placebo fit leaves out a seeded contiguous block of estimation days so that it
  has as many usable days as the real fit (82 for Stonestreet), because a fit on more days is a different, less noisy
  fit (§4).
- **T. Omitted days are kept as missing**, not filled with 0 (the spec's §3), in the panel, with the exact rule of §3.
  `fetch_pageviews` still fills 0 by default, as the spec says; the panel does not.
- **U. The placebo spread and the minimum detectable uplift are computed and written before any estimate** (§5).
- **V. The spec's §7 shock-recovery test** holds as written for one seed (seed 1) and fails for others by up to 2.6
  because the noise of a median index pulls beta to about 0.8 (§8). The tests therefore also keep a looser version over
  nine seeds (median error under 2, worst under 4.5). The other tests of the spec's §7 are kept as written; the 100-seed
  null test runs in the ordinary suite.
- **W. Spec items not carried over.** (1) `data/raw`, `out`, `PREREG.md`, `README.md` and `pyproject.toml` become
  `tools/data/memes/raw` and `tools/data/memes/out` (gitignored), this design, `tools/memes/README.md`, and no
  `pyproject.toml` (the site's tools run through `uv run --no-project --with`); the results are also copied to
  `docs/research/memes-results.json`, which the spec does not have. (2) Rolling Stone India is not a source on the page,
  because it was not read. (3) The "exploratory" web note for a detected date is not built: the dates are sourced, and
  the code still warns and flags a detected date. (4) The page text is a skeleton for the author to rewrite.

### Changes to the spec's interface (§6 of the spec)

| Item | Spec | Here |
|---|---|---|
| `fetch_pageviews` | fills omitted days with 0 | same by default; new keyword-only `missing="nan"` keeps them missing |
| `fetch_panel` | zero-filled | keeps omitted days as missing (`missing="nan"`) |
| `control_index` | median of log1p | new `how="median"\|"mean"`; skips missing days |
| `fit_market_model` | OLS, returns (a, b, sd) | same; new `weekday=False` adds weekday terms |
| `abnormal_attention` | (y, x, event, est, ew) | new `blocked=()`, `weekday=True` (weekday terms, a behaviour change); omitted estimation days are left out; an omitted event-window day raises `EventDropped` |
| `half_life` | as spec | unchanged; the primary H2 is the new `half_life_smoothed` |
| `placebo_p_value` | `n_placebo=300` draws | default `n_placebo=None`, every admissible date; new `blocked`, `season_days`, `pre_only`, `weekday`; equal estimation days (S); returns n = number of finite placebo statistics |
| `detect_event_date` | as spec | unchanged |
| `run_event` | (panel, spec, ...) | new keyword-only options (`how`, `drop`, `controls`, `event_date`, `falsify`, `season_days`, `pre_only`, `weekday`, `space_time`, `variant`); raises `EventDropped` (a `ValueError`) |
| `EventSpec` | not given | frozen dataclass: name, target, controls (baseline), event_date, source_note, confirmatory, falsification, cast, reference, blocked, detect_window |
| `EventResult` | 14 fields | the 14 fields, with `peak_date`, `peak_ar`, `half_life_days` now from the smoothed series, plus `confirmatory`, `excess_views`, `half_life_status`, `half_life_raw_days`, `peak_date_raw`, `null_sd`, `null_p95`, `mdu_pct`, `mdu80_pct`, `falsification_car`, `falsification_p`, `loo_car`, `loo_p`, `space_time_p`, `n_space_time`, `dropped`, `holm_p`, `label`, `variant` |
| errors | the spec's list | all kept; added `EventDropped`, "series must be a gap-free daily index", and a message for a title that is a redirect or disambiguation page |
| added public functions | none | `model`: `excess_views`, `half_life_smoothed`, `placebo_candidates`, `external_falsification`, `falsification_test`, `space_time_p`, `monthly_gap`, `null_summary`, `null_distribution`, `holm_adjust`, `confirmatory_family`, `label_event`; `fetch`: `verify_titles`, `save_panel`, `load_panel`, `write_manifest`, `ArticleNotFound`; `cli`: `study`, `variant_plan`, `screening_outputs`, `write_outputs`; `report`: `ar_svg`, `estimation_svg`, `render_html`, `visible_text`, `write_summary`; modules `synth`, `simulate`, `pool` |

## 2. Data and definitions

- **Source.** Wikimedia Analytics API, per-article daily pageviews
  (`https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/<title>/daily/<from>/<to>`),
  data under CC0, available from 1 July 2015. Range **1 January 2021 to 31 December 2024**, 1 461 days. A one-year
  range left about 29 placebo dates and a 30 % false-positive rate in the prototype; hence four years and a hard
  minimum of 100 admissible placebo dates (§4).
- **Requests.** One article per request, one at a time, 0.2 s apart (57 requests; the limit for a client that sends a
  compliant User-Agent is 200 requests a minute, at most 3 at once). User-Agent `bsandova-meme-event-study/0.1
  (https://bsandova.com)`, never an e-mail address. Titles are URL-encoded (`quote(title, safe="")`). Retries on 429,
  500, 502 and 503, at most 3 attempts, exponential backoff. A 404 stops the run at once: the API answers 404 both for
  zero views and for data not yet loaded, and for these articles over four years neither is plausible. Days the API
  omits are kept as missing (T, §3).
- **Panel.** `tools/data/memes/raw/pageviews.csv` (gitignored), never edited by hand; its sha256, the range and the
  download date go to `docs/research/memes-files.sha256`. `--panel-csv` reruns without downloading.
- **Articles (57).** Targets `Eric_Stonestreet`, `Kevin_James`. `MF_CAST`: `Ed_O'Neill`, `Sofía_Vergara`,
  `Julie_Bowen`, `Ty_Burrell`, `Jesse_Tyler_Ferguson`, `Sarah_Hyland`, `Ariel_Winter`, `Nolan_Gould`,
  `Rico_Rodriguez_(actor)` (deviation N). `KOQ_CAST`: `Leah_Remini`, `Victor_Williams` (deviation E). The 44 actors of
  the reference pool below.
- **Reference pool (author's decisions of 26 October 2026; rule fixed before any data).** Actors outside both shows: the
  baseline of Kevin James, the external index of the falsification, and two sensitivity runs. The rule, applied as
  written by `pool.py` to Wikipedia text only:
  1. Shows: the articles in the categories 2010s and 2020s American multi-camera sitcoms and 2010s and 2020s American
     single-camera sitcoms (484 articles, read 26 October 2026).
  2. Keep a show whose infobox `network` is ABC, CBS, NBC, Fox or The CW and whose infobox `last_aired` year is from
     2016 to 2021 (the original run ended then), that is not animated (no category with "animated"), and that is not
     Modern Family or The King of Queens.
  3. Drop a show that lists any actor of the infobox `starring` field of Modern Family or The King of Queens (this
     removes A.P. Bio, Happy Together and Kevin Can Wait). Drop a show with a starring actor whose article gives a
     death date in 2023 (this removes Brooklyn Nine-Nine and The Odd Couple (2015); Friends, which would be dropped
     for Matthew Perry's death on 28 October 2023, is out anyway because it ended in 2004). Imaginary Mary was dropped
     as animated. No other show was dropped on a judgement. 53 shows are kept.
  4. **The pool is the first-billed actor of every kept show**: the first entry of the infobox `starring` list (comments
     and namespace links ignored). No cap and no ordering of shows. A first-billed entry with no article link, a title
     that is missing, a redirect or a disambiguation page, or an actor already taken from another show is **dropped
     and not replaced**, and the show adds nobody. Dropped: `9JKL`, `Dr._Ken`, `Marlon_(TV_series)`, `Rel_(TV_series)`,
     `Sunnyside_(American_TV_series)`, `The_Carmichael_Show` and `The_Last_Man_on_Earth_(TV_series)` (first-billed
     actor without a link), `I_Feel_Bad` (`Sarayu_Blue` is a redirect), `The_Middle_(TV_series)` (`Patricia_Heaton` was
     taken from an earlier show). The full candidate list, one row per show with its first-billed title and its fate,
     is `docs/research/memes-reference-pool.json`. 44 actors remain.
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
  The 44 actors, in alphabetical order of their shows: `Kat_Dennings`, `Natalie_Morales_(actress)`, `Zach_Braff`,
  `Katy_Mixon`, `Dax_Shepard`, `Jaime_Camil`, `Kyra_Sedgwick`, `Patricia_Heaton`, `Anders_Holm`, `Otmara_Marrero`,
  `Allison_Tolman`, `Nina_Dobrev`, `Randall_Park`, `Adam_Scott`, `Adam_Pally`, `Kim_Matula`, `Tim_Allen`,
  `Colin_Hanks`, `Jay_R._Ferguson`, `Matt_LeBlanc`, `Bobby_Moynihan`, `Billy_Gardell`, `Tika_Sumpter`, `Anna_Faris`,
  `Zooey_Deschanel`, `Jason_Biggs`, `Bradley_Whitford`, `Vanessa_Hudgens`, `AJ_Michalka`, `Taran_Killam`,
  `Minnie_Driver`, `Jenna_Fischer`, `Judd_Hirsch`, `Johnny_Galecki`, `David_Alan_Grier`, `Kristen_Bell`,
  `Joel_McHale`, `Mary_McCormack`, `Kaitlin_Olson`, `Martha_Plimpton`, `Walton_Goggins`, `Nicholas_D'Agosto`,
  `Chris_D'Elia`, `Will_Sasso`.
  The index is the daily median of log(1 + views) of these actors, over those that have a value that day.
- **Events** (in `tools/memes/config.py`, with their sources, not in code):

  | Event | Target | Baseline | Day 0 | Role | Source |
  |---|---|---|---|---|---|
  | Stonestreet (Cam) | `Eric_Stonestreet` | `MF_CAST` | 2023-09-27 | H1, Holm family | Know Your Meme, "Cameron Tucker Smiling": earliest X post it lists |
  | Kevin James | `Kevin_James` | reference pool | 2023-09-21 | H1, Holm family | Know Your Meme, "Kevin James Smirking Getty Image": earliest X post it lists |
  | Stonestreet TikTok pre-wave | `Eric_Stonestreet` | `MF_CAST` | 2023-06-13 | sensitivity | Know Your Meme, "Cameron Tucker Smiling": first notable TikTok |

  The Cam day 0 is the earliest X post Know Your Meme lists, not the day the meme took off (it names 6 October for
  that), and a date from a meme database can be a day off in either direction. Both are limits (§8): the event window
  reaches 30 days past day 0.
- **Blocked days (deviation C).** For Stonestreet, 6 June to 13 July 2023 are dropped from the estimation window and
  no placebo span may touch them. For the TikTok run, the September wave (24 September to 27 October 2023) is kept
  out of the placebo pool the same way.
- **Windows.** Estimation days −150 to −31, event window −3 to +30. For Stonestreet the estimation window is 30 April to
  27 August 2023 less the blocked days, 82 days; for Kevin James 24 April to 21 August 2023, 120 days.

## 3. Screening (before any estimate is read)

1. **Title check, done 26 October 2026, no views.** All 14 titles of the spec exist and normalise only by underscores
   to spaces. **`Gary_Valentine` is a redirect to Gary Lachman** (deviation E) and **`Rico_Rodriguez` is a
   disambiguation page** (deviation N). `Victor_Williams` is the King of Queens actor (introduction read). After the
   decisions the check was repeated on the **57 titles of §2**: all exist, none is a redirect or a disambiguation page,
   none normalises beyond underscores. The code (`cli.py --verify-titles`) repeats the check before a download and stops
   on a missing title, a redirect or a disambiguation page.
2. **Omitted days (deviation T), the exact rule.** The API leaves out a day without views, so a hole is either a day
   with no views or a day not loaded; for these articles over four years the second is the likelier. The panel keeps
   omitted days as **missing**, never 0. The rule is applied **per event and per window** (the estimation window less
   blocked days, and the event window):
   - **Target.** Dropped, and the event is not estimated, if any day of its event window is omitted or more than 5 % of
     its estimation days are omitted. With 5 % or fewer, the omitted days are left out of the fit.
   - **Cast or baseline article that is not a pool member.** Dropped if more than 5 % of its estimation days are
     omitted; otherwise its omitted days are skipped by the daily median.
   - **Pool member.** Dropped automatically on any omitted day in either window.
   - **Empty baseline.** If no baseline article is left, the event is not estimated.
   - **Continuation.** A dropped article or event is **never replaced**. It is listed (`dropped`, `dropped_events`), the
     other event is unaffected, and the Holm family is the remaining confirmatory events.
   - **Placebo windows.** Omitted days are left out of the fit. A pseudo date is admissible only if its event window has
     none and its estimation window still has at least as many usable days as the real fit.
3. **Confounders in the estimation windows (deviation L).** `estimation_windows.svg` is **one small panel per article**,
   raw log(1 + views) from 1 January 2021 to **17 September 2023**, which is day −4 of the earlier of the two events
   (Kevin James). No event window of either meme is drawn, and the **TikTok block (6 June to 13 July 2023) is blank in
   every panel**, so the TikTok window of `Eric_Stonestreet` and the event window of the TikTok sensitivity run are not
   shown. The panels are the two targets and their casts (`Eric_Stonestreet` and the nine of `MF_CAST`;
   `Kevin_James` and the two of `KOQ_CAST`) and one panel for the median of the reference pool; **the 44 pool actors are
   not drawn one by one**. Spikes are recorded in the README with what is known of them (a death, a wedding, a new
   show). **Nothing in the analysis is changed because of what is seen there.**
4. **Target minus baseline by month.** `estimation_gap_by_month.csv`: the mean of target attention minus baseline
   attention by calendar month in the same period (to 17 September 2023, blocked days left out), for each event, so a
   drift or a level shift in the estimation windows is visible before the estimates.
None of it compares attention across events or after day −4.

## 4. Estimation (MacKinlay 1997, *Journal of Economic Literature* 35(1))

1. y = log(1 + views). Baseline x = daily median of y over the baseline articles.
2. **Market model:** OLS of y_target on x and weekday dummies (Monday to Saturday against Sunday) over the estimation
   window less blocked and omitted days: y = a + b·x + weekday. **Why weekday terms (deviation R):** Wikipedia views
   have a strong weekly cycle, and the event window of 34 days is four weeks and six days, so an uneven count of
   weekdays leaks the cycle into the CAR if the target's cycle differs from the baseline's. Restricting pseudo dates
   to the same weekday would leave about 130 dates; weekday terms keep all of them. A test shows the bias without
   them.
3. AR_t = y_t − (a + b·x_t + weekday_t) for t = −3 … +30. **CAR** = ΣAR_t. **Mean uplift** in per cent =
   (exp(mean AR) − 1)·100, the headline; **excess views** = Σ(views_t − (exp(prediction_t) − 1)).
4. H2 as in §1, on AR from day 0.
5. **Placebo test.** A pseudo event date d is admissible if its span, days d−150 to d+30, lies fully in the data; is at
   least 30 days (`exclusion_days`) away from the real event window (at least 30 days lie between the two); touches no
   blocked interval; has no omitted day in its event window; and has at least as many usable estimation days as the
   real fit. **Every admissible date is used** (deviation Q): 927 for Stonestreet and 1 007 for Kevin James. For each,
   the same model and the same CAR are computed, **on exactly as many estimation days as the real fit** (deviation S):
   from the usable days of the placebo's estimation window a seeded contiguous block is left out until the count equals
   the real fit's (38 days for Stonestreet, none for Kevin James), the block's place drawn from
   `numpy.random.default_rng([42, 1])`. One-sided p as in §1. With fewer than 100 admissible dates the run stops with an
   error that recommends a longer range.
   **What the p-value is.** The 927 dates are not independent: windows of 34 days overlap, so there are about 27 non-
   overlapping windows, and the p-value is an **empirical-null calibration under stationarity**: it says how large a
   CAR of this kind is on other dates of the same series, assuming those dates are exchangeable with the event date.
   Its resolution is about 1/28, and **a p-value below about 0.04 is not to be presented as precise**; the Holm level
   of 0.025 for the smaller p is below that resolution and is read as "among the very largest of the placebo CARs".
6. **Falsification diagnostic** (§1): steps 1 to 5 with the cast series as the target and the external index as the
   baseline, on the same dates. Leave-one-out: per control, against the median of the other controls; the median of the
   CARs; the same dates.
7. **Placebo checks** (§7): same season (pseudo dates within ±45 days of the event's calendar date in the other
   years: 273 dates for each event), pre-event pseudo dates only (706 and 780), exclusion of 90 days (867 and 887), and
   the **space-time placebo**: the rank of the target's CAR among the CARs of the pool actors at the real date, each
   against the median of the other pool actors, p = (k + 1)/(n + 1), k the number of pool actors with a CAR at least as
   large as the target's, n the number of pool actors left.
8. Errors stop the run with a clear message: an estimation window under 30 usable days, a constant baseline, an
   estimation window not ending before the event window, a window outside the data (both ranges are named), a missing
   target or control (listed), no controls, too few placebo dates, a gap in the daily index; omitted days are handled
   by §3.
9. Versions of Python, numpy and pandas are recorded in `memes-results.json`. Outputs: `summary.json`,
   `placebo_null.json`, `ar_<target>.csv`, `abnormal_attention.svg`, `estimation_windows.svg`,
   `estimation_gap_by_month.csv`, `index.html` under `tools/data/memes/out/` (gitignored), and the results copy
   `docs/research/memes-results.json`. The page is copied to the site by the author.

## 5. Power

**This section was written after the code and the simulations it reports.** The design text above was committed first;
the code, the tests and the runs followed; the numbers below were copied in by a later commit, before any real data.

Computed on **made-up panels only**: an AR(1) factor with φ 0.8 and innovation sd 0.1 shared by all articles, a second
such factor for each group (the target with its cast, and the reference pool), idiosyncratic noise sd 0.1, target beta
1. The geometry is the registered one: for Stonestreet a baseline of the nine cast articles and the blocked days; for
Kevin James a baseline of the 44 pool actors; every admissible placebo date; the weekday terms; equal estimation days;
300 simulated panels per cell (`tools/memes/simulate.py`, `docs/research/memes-power.json`, run niced on 26 October
2026). A shock *s* adds s·exp(−t/5) to the target's attention from day 0, so *s* = 0.3 is +35 % on day 0 and about +5
% on average over the window, and the CAR is about 5.5·*s*. **In these panels Kevin James shares only the common
factor with the pool, not his own group's factor; that is an assumption, and if the real co-movement with the pool is
stronger his power is higher.** It is the price of the baseline decision (D2): his baseline is not exposed to the
meme, and is also less informative.

| Share of panels with p below | s = 0 (false positives) | s = 0.1 | s = 0.3 | s = 0.5 | s = 1.0 | s = 2.0 |
|---|---|---|---|---|---|---|
| Median mean uplift over the window | 0 % | 1.6 % | 5.0 % | 8.4 % | 17.6 % | 38 % |
| Stonestreet, 0.05 | 5.3 % | 17 % | 53 % | 86 % | 100 % | 100 % |
| Stonestreet, 0.025 | | 11 % | 41 % | 82 % | 100 % | 100 % |
| Kevin James, 0.05 | 6.7 % | 10 % | 13 % | 19 % | 41 % | 87 % |
| Kevin James, 0.025 | | 6 % | 9 % | 14 % | 31 % | 80 % |

False positives at the 5 % level are 5.3 to 6.7 % (prototype: 4.3 %).

**Minimum detectable uplift (method, deviation U).** Before any estimate, the run computes the placebo CARs of every
admissible pseudo date, from non-event dates only, and writes their standard deviation *sd* and 95th percentile *q95*
to `placebo_null.json`, then converts them to a mean uplift over the 34 days, (exp(*q*/34) − 1)·100. **The critical
uplift** uses *q95*: the smallest mean uplift that reaches p < 0.05. **The 80 % uplift** uses *q95* + 0.84·*sd*: the
mean uplift that a normal placebo distribution of that spread would flag in four cases in five. The "no detectable
jump" label is tied to the 80 % uplift (§6). In the made-up panels the medians of *sd* are 0.93 (Stonestreet) and 3.9
(Kevin James), the critical uplift is 4.6 % and 20 %, and the 80 % uplift is 7.0 % and 33 %. The real values will come
from the real series, which are likely spikier, and will replace these in the text.

**The design is likely underpowered for the author's prior.** A small jump that fades within a few days, say *s* of
0.1 to 0.2 (a mean uplift of 2 to 3 % over the window and a CAR of about 0.5 to 1), is far below the 80 % uplifts
above. In the made-up panels Stonestreet's H1 rejects such a jump in 17 % of panels at *s* = 0.1, and Kevin James's in
10 %, close to the false-positive rate. The likely outcome under the prior is therefore "no detectable jump", and that
outcome says little: it excludes only jumps above about 7 % (Stonestreet) or 33 % (Kevin James) on average over the
window. At the Holm level 0.025 power is lower still. The prototype's figures (4.3 % false positives, power 67, 97 and
100 % for 0.3, 0.5 and 1.0) were higher because the estimation window was longer and the baseline closer to the
target.

**Falsification diagnostic** (descriptive, §1). Share of panels with p < 0.05, external index and leave-one-out, when
all or some of the cast controls jump by *s* (Stonestreet has nine, Kevin James two):

| Cast controls that jump | external, s = 0.5 | external, s = 1.0 | leave-one-out, s = 0.5 | leave-one-out, s = 1.0 |
|---|---|---|---|---|
| none (false positives) | 5.7 % | | 6.3 % | |
| 3 of 9 | 10 % | 14 % | 3 % | 0 % |
| 5 of 9 (a majority) | 12 % | 21 % | 38 % | 88 % |
| 9 of 9 (all) | 17 % | 39 % | 12 % | 20 % |
| Kevin James, 2 of 2 (none: 6.3 % and 5.7 %) | 20 % | 41 % | 17 % | 33 % |

The external falsification sees a cast-wide jump of 0.5 in **about 17 % of panels against a false-positive rate of
about 6 %**, and a jump of 1.0 in 39 %: this is the "power" in the page's sentence ("about 17 %"). Leave-one-out sees
a majority jump much better and an all-cast jump worse. Neither can carry a label, which is why both are diagnostics.

Real attention series carry spikes and news that these panels lack, so **real power is lower**.

## 6. Labels

For each confirmatory event that was estimated (Stonestreet and Kevin James), in this order, **on H1 alone**:

1. **positive**: Holm-adjusted p < 0.05 and CAR > 0.
2. **no detectable jump**: raw p ≥ 0.05. This is failure to reject, not evidence of no jump: it reads as "no jump above
   about X % on average over the window, X being the uplift detected in four cases in five (`mdu80_pct`, §5), would have
   gone unseen", and the page says so with that number.
3. **inconclusive**: otherwise, that is, the raw p is below 0.05 and the Holm-adjusted p is not.

An event dropped by the omitted-day rule (§3) gets no label. H2 has no label. The sensitivity runs and the diagnostics
(§7) do not relabel; if one of them has a raw p ≥ 0.05 where the primary has p < 0.05, the article says so next to the
label. If the pages show a jump in neither actor, that is a result, and the page says the memes spread by scrolling
without searching.

## 7. Checks (reported; none relabels a primary result)

Each is a `variant` in `summary.json`, with raw placebo p and no correction, run on every admissible placebo date.
Unless stated, a variant changes one thing and keeps the rest of the primary run. **Falsification diagnostics (external
and leave-one-out) are reported** in the variants marked F and not computed in the others.

| Variant | Events | What changes | F |
|---|---|---|---|
| `window_-3_14`, `window_-3_60` | both | event window; pseudo dates recomputed (975 and 837 for Stonestreet, 1 055 and 917 for Kevin James); the smoothed half-life uses that window | F |
| `mean_index` | both | mean instead of median baseline (also in the diagnostics) | F |
| `drop_Sofía_Vergara` | Stonestreet | the spec's own-news article left out of the baseline | F |
| `day0_2023-10-06` | Stonestreet | day 0 on the most-liked listed post; estimation window moves with it, blocked days stay; **p is reported, for H2 only; no label** | F |
| `external_index` | Stonestreet | baseline: the reference pool, not the cast | |
| `external_index_window_-3_60`, `..._without_Matt_LeBlanc` | Stonestreet | the pool baseline with window (−3, +60), then also without `Matt_LeBlanc` (pre-declared: Matthew Perry died on 28 October 2023, inside that window) | |
| `koq_controls` | Kevin James | baseline: `Leah_Remini` and `Victor_Williams` | F |
| `window_-3_60_without_Matt_LeBlanc` | Kevin James | the primary pool baseline, window (−3, +60), without `Matt_LeBlanc` | |
| `same_season` | both | pseudo dates within ±45 days of the event's calendar date in the other years | |
| `pre_event_only` | both | pseudo dates before the real event only | |
| `exclusion_90` | both | at least 90 days between a pseudo span and the real event window | |
| `tiktok_prewave` | the 13 June 2023 event | windows as primary, the September wave blocked | |

Also reported for each primary event: the **space-time placebo** p (§4.7), `space_time_p`, and the leave-one-out and
external falsification of the primary run.

## 8. Limits stated now

- **Attention is not meme exposure.** Pageviews measure looking something up. A meme that spreads by scrolling leaves no
  trace here, so no detectable jump says nothing against the meme having spread. `agent=user` can still include
  automated traffic that is not labelled as such.
- **Event dates.** Day 0 is the earliest X post a database lists, not the take-off (Know Your Meme names 6 October
  2023 for the Cam meme). The window (−3, +30) covers both, and CAR is a sum over the window, but half-lives (H2)
  counted from day 0 are not comparable with a peak that comes later. Dates can be one day off, and the API counts UTC
  days.
- **Baselines have news and are exposed.** An actor's own news or a show anniversary moves a baseline article. Leah
  Remini reacted to the Kevin James memes on 26 September 2023 (day +5), which is why the pool and not his cast is the
  baseline. The pool actors are other TV actors of one kind of show, not a sample of all actors, they share an era
  (their shows ended in 2016 to 2021, so shared trends such as the ageing of those shows' audiences are in the
  baseline), and they have their own news in the same weeks; the median blunts it. The rule excludes a show with a
  starring actor who died in 2023 and nothing else about 2023: it is a mechanical stand-in for "a widely known event
  in 2023", not the thing itself. **Confounders named now:** the 2023 actors' strike (July to November) and the Emmy
  ceremony postponed to January 2024 move attention to actors in general and mostly enter the baseline; Matt LeBlanc,
  a Friends actor, is in the pool and Matthew Perry died on 28 October 2023, the day after the Stonestreet window ends
  (the (−3, +60) checks include it, with a variant without him). The infobox lists miss actors and may carry stray
  links.
- **Pages move and split.** A page rename or move splits its series between two titles; a redirect hides it. The title
  check catches only today's state.
- **The falsification is weak** (§5): against an external index a cast-wide jump of 0.5 is seen in about one panel in
  six and of 1.0 in two in five, and leave-one-out is blind to a jump that every control shares. It is a diagnostic. A
  cast-wide rise does not give a false positive for H1: it pulls the baseline up with the target, and the CAR shrinks.
- **A common wave.** The two memes belong to the same autumn 2023 run of "actor stock photo" posts (Know Your Meme calls
  the Cam meme similar to the Kevin James trend), so shared drivers (a platform trend, the same news) are possible and
  the comparison of the two is descriptive.
- **Half-life.** Even smoothed over 7 days and with a persistence rule, the half-life of a noisy series is a rough
  number; a censored half-life is a finding, not a failure.
- **Noise in the baseline attenuates beta.** A median over a few noisy articles measures the common factor with error,
  so the fitted slope b is below 1 (about 0.8 in the made-up panels, whose true beta is 1). The CAR then carries part of
  the baseline's movement, which is why the spec's shock-recovery tolerance of 2 fails for some seeds (deviation V). It
  is a property of the design, shared by the placebo dates, and it is not corrected.
- **Power was computed on made-up data** (§5); the noise structure is assumed, and real series are spikier. The
  estimation window (April to August 2023) was not looked at before registration, so unknown spikes in it are
  possible (§3).
- **Pseudo-events are not independent** (§4.5): about 27 non-overlapping windows; the p-value is an empirical-null
  calibration, not an exact test.
- **The assistant's prior knowledge** (§0) cannot be audited.
- **Gary Valentine** is not in the controls (deviation E), and `Rico_Rodriguez` is replaced by the infobox's
  `Rico_Rodriguez_(actor)` (deviation N).

## Running and verification

Commands, the verified API facts and their dates are in `tools/memes/README.md`.

## Change log

- 26 October 2026: design committed, before any pageview number was downloaded.
- 26 October 2026, first decisions of the author, before any pageview number was downloaded: deviation E accepted; the
  TikTok exclusion window, 6 June to 13 July 2023, confirmed; the falsification moved to an external reference group;
  day 0 kept at 27 September 2023 for Cam with 6 October 2023 as a sensitivity check for H2; the tests wired into CI.
  Found while applying them: `Rico_Rodriguez` is a disambiguation page, replaced by `Rico_Rodriguez_(actor)`.
- 26 October 2026, after two independent reviews (methods; data and consistency) and the author's second set of
  decisions, before any pageview number was downloaded: **D1** the falsification is a descriptive diagnostic and gates
  no label, with a pre-written page sentence and leave-one-out as a reported check; **D2** the baseline of Kevin James
  is the external pool, his King of Queens controls a check; **D3** `Rico_Rodriguez_(actor)` confirmed; **D4** Matt
  LeBlanc stays in the pool, with a pre-declared "without LeBlanc" variant of the (−3, +60) checks; **D5** the pool is
  the first-billed actor of each of the 53 shows, no cap, with the same drop rules and the full candidate list
  committed. Review fixes applied: placebo fits on as many estimation days as the real fit (M1); weekday terms,
  same-season, space-time and exclusion-90 or pre-event checks (M2); the placebo spread and minimum detectable uplift
  written before the estimates (M3); every admissible placebo date (S1); uplift and excess views as the headline (S2);
  one day-0 rule (S3); H2 on a smoothed series with persistence and defined censoring (S4); the monthly gap in the
  screening (S5); the exact omitted-day rule (S6); the Holm justification (S7); further limits (S8); the spec's §7
  tests restored where possible (R1); the full interface list (R2); the confounder figure restricted and drawn per
  article (R3); fully specified checks (R4); the status of every deviation (R5); dropped spec items (R6); an
  "otherwise" label and the half-life window of the variants (R7). §5 is written after the code and the simulations.
  The commits follow below.
- 26 October 2026, commits of the branch, one line each (the commit that adds this list is not in it):
  - `70dc8cf` design registered (first version, before the code).
  - `c88a98a` first version of the code, with the external falsification and the `--unblind` guard.
  - `7dbb87a` tests of that code on made-up data.
  - `18e5703` first runs of false positives, power and falsification detection on made-up panels.
  - `8d712b6` first power numbers in the design, and the README.
  - `8b9524c` the memes tests run in CI, matplotlib pinned.
  - `ab24398` design revised after the two reviews and the author's decisions D1 to D5.
  - `3ebc5d9` code: weekday terms, equal-day placebos, the omitted-day rule, the first-billed pool, the diagnostic
    falsification, the smoothed half-life, the checks and the page.
  - `3c74a59` tests: the review fixes, and the spec's §7 tests restored where possible.
  - `2a3f2db` the runs of power, minimum detectable uplift and falsification detection on made-up panels, rerun.
  - `c9c891e` §5 numbers and the minimum detectable uplift copied into the design: **§5 was written after the code and
    the simulations**.

