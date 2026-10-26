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
the code is frozen by tag.

**Stage 1** downloads the panel, screens it, chooses Kevin James's baseline, computes the placebo null and the minimum
detectable uplifts from non-event dates only, and writes the files below into `docs/research/`. It computes no CAR or
AR at any event.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project $P \
        python -I tools/memes/cli.py --null-stage --unblind

Then commit `memes-placebo-null.json`, `memes-null-files.sha256`, `memes-estimation-windows.svg` and
`memes-estimation-gap-by-month.csv` and tag that commit `memes-null` (no tag is made by the code).

**Stage 2** refuses unless those files match the hashes, the panel matches the hash of stage 1, the files are committed
and unmodified, and the tag is on HEAD:

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

To be filled after the download, from `estimation_windows.svg` (design §3.3). Recorded, not acted upon.
