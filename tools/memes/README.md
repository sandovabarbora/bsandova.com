# Meme event study on Wikipedia pageviews

Code for `docs/research/memes-design.md`. The design is the registration: read it first. `config.py` holds the events,
windows, seed and the frozen reference pool; `fetch.py` all I/O; `model.py` the pure logic; `report.py` the outputs;
`cli.py` the run. `pool.py` documents how the reference pool was built (MediaWiki text only, no pageviews) and is not
part of a run.

## Running

Versions are pinned (design deviation AD): `P="--with pandas==3.0.6 --with numpy==2.5.3 --with matplotlib==3.11.2"`.
Dry run on a made-up panel (no network, both stages in memory), and the title check (existence only, no pageviews):

    uv run --no-project $P python -I tools/memes/cli.py --synthetic
    uv run --no-project $P python -I tools/memes/cli.py --verify-titles

The registered run has two stages and reads real pageviews, so both refuse without `--unblind`. Run them only after
the code is frozen: tag the final code `memes-code` (the code makes no tag). Both stages refuse unless that tag exists,
`tools/memes` at HEAD equals it, and `tools/memes` and the design text have no uncommitted changes. `--n-placebo` is
only for `--synthetic`; the registered run uses every admissible placebo date and seed 42. A failed request is retried
up to three attempts (HTTP 429 and 5xx, timeouts, dropped connections); `--verify-titles` stops if a returned title is
not the article with underscores read as spaces.

**Stage 1** downloads the panel, screens it, chooses Kevin James's baseline, computes the placebo null and the minimum
detectable uplifts from non-event dates only, and writes the files below into `docs/research/`. It computes no CAR or
AR at any event.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project $P \
        python -I tools/memes/cli.py --null-stage --unblind

Then commit `memes-placebo-null.json`, `memes-null-files.sha256`, `memes-estimation-windows.svg` and
`memes-estimation-gap-by-month.csv` and tag that commit `memes-null` (no tag is made by the code). Stage 1 refuses if `memes-null` already exists.

**Stage 2** refuses unless those files match the hashes, the panel matches the hash of stage 1, the files are committed
and unmodified, the tag is on HEAD, `memes-code` is an ancestor of `memes-null`, and the null file used every admissible
date and seed 42. It then recomputes the stored null values of both windows and the baseline choice and stops on any
difference:

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project $P \
        python -I tools/memes/cli.py --panel-csv tools/data/memes/raw/pageviews.csv --unblind

Tests (made-up data only) and ruff, then the slow runs of design §5:

    uv run --no-project $P --with pytest==9.1.1 pytest -q tools/memes -m "not slow"
    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project $P --with pytest==9.1.1 \
        pytest -q tools/memes -m slow
    uvx ruff check tools/memes
    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with pandas==3.0.6 \
        --with numpy==2.5.3 python -I tools/memes/simulate.py   # rewrites memes-power.json

A plain `pytest tools/memes` skips the slow tests. CI runs `tools/memes` with the other study suites (fast tests only;
`matplotlib`, `pandas` and `numpy` are pinned in `tools/requirements-tests.txt`). Data and stage 2 outputs go to
`tools/data/memes/` (gitignored).

## What was verified, and when (26 October 2026)

- Wikimedia Analytics API documentation (access policy, troubleshooting, page views): a User-Agent is required; 404
  means zero views or data not loaded; zero days are omitted from a series; 429 is throttling at the storage layer;
  redirects are not counted as views of the page they point to; data start on 1 July 2015.
- Rate limits (mediawiki.org, Wikimedia APIs/Rate limits, "new in 2026 and subject to change"): 200 requests a minute for
  a client with a compliant User-Agent, at most 3 concurrent, honour Retry-After on 429 and 503. The run makes 57
  requests, one at a time, 0.2 s apart.
- Article titles (MediaWiki API, no pageview numbers): see design §3. `Gary_Valentine` is a redirect to another person
  and `Rico_Rodriguez` is a disambiguation page. The 57 titles in use were checked on 26 October 2026.
- Event dates: Know Your Meme, see design §2.
- **Not verified:** that the pageview endpoint returns what the documentation says (no request for pageviews has been made,
  by design); that Know Your Meme's dates are the true first posts; the sizes in design §5 on real series.

## Confounders in the estimation windows

Recorded after stage 2 from `docs/research/memes-estimation-windows.svg` (design §3.3) and from the spike list that
`describe.py` writes into `docs/research/memes-describe.json`: a day at least three times the centred 61-day median of
its own article, days under 14 apart counted as one episode and dated by its largest day, 1 January 2021 to 17 September
2023, the TikTok block left out. Described, not explained: no cause was looked up. **Recorded, not acted upon**; nothing
in the analysis changed.

Inside an estimation window (Stonestreet 30 April to 27 August 2023 less 6 June to 13 July, Kevin James 24 April to
21 August 2023):

- `Eric_Stonestreet` (target): 19 July 2023, 14 992 views against a 61-day median of about 2 900 (5.2 times). Also 28 and
  29 April 2023 (20 108 and 17 808 views, 5.6 times), the two days before his window opens, with 30 April still raised
  (4 828).
- `Sofía_Vergara` (Stonestreet's baseline): 18 July 2023, 117 926 views (8.0 times), raised from 17 to about 22 July.
- `Ed_O'Neill` (Stonestreet's baseline): 13 May 2023, 22 201 views (4.9 times), raised from about 10 to 15 May.
- `Victor_Williams` (Kevin James's second regressor): 19 July 2023, 2 841 views (3.7 times), then a raised level that
  decays over weeks: daily median 407 from 24 April to 18 July, 796 from 19 July to 21 August, 532 from 22 August to 17
  September.
- `Leah_Remini` (King of Queens cast, not in Kevin James's baseline): 1 June 2023 (11 445 views, 3.2 times) and 3 August
  2023 (19 012 views, 5.4 times).

Between the estimation and the event window: `Leah_Remini` on 8 September 2023 (28 671 views, 8.2 times), raised from
7 to 10 September, two weeks before the Kevin James meme. `Kevin_James` itself has no spike in 2023, and the medians of
the Modern Family cast and of the reference pool have none at all.

Earlier, outside every window (for the record): `Eric_Stonestreet` 23 August 2021 (56 580 views, 17.8 times), 22
February and 30 March 2022; `Ed_O'Neill` 15 November 2022; `Julie_Bowen` seven episodes from February 2021 to March
2023; `Ty_Burrell` 12 February 2022 (10.3 times); `Jesse_Tyler_Ferguson` four, the largest 13 June 2022 (8.9 times);
`Sarah_Hyland` 23 August 2022, 24 November 2022 and 15 March 2023; `Ariel_Winter` 11 June 2022; `Nolan_Gould` 13 July
2021 (14.6 times); `Rico_Rodriguez_(actor)` 16 September 2021; `Kevin_James` 16 February 2021 and 30 January 2022;
`Leah_Remini` four from August 2021 to November 2022; `Victor_Williams` 9 February and 26 May 2021.

## After the results (not registered)

    uv run --no-project $P python -I tools/memes/describe.py   # docs/research/memes-describe.json
    uv run --no-project $P python -I tools/memes/article.py    # assets/actor-memes/ and texts/actor-memes.html

`describe.py` reuses the frozen model on the stage 1 panel for the article's figures (daily views, expected views, AR and
the 5th to 95th percentile of the placebo AR and running CAR at each day) and the spike list above. It refuses unless the
panel hash, each primary CAR, the number of placebo dates and the 95th and 97.5th placebo percentiles reproduce
`memes-results.json`. `article.py` reads only the committed JSON files and asserts every statement of the text that a
rerun could change.
