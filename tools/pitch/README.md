# Pitch Perfect joke-target study

Code for `docs/research/pitch-design.md`, frozen at the signed tag `pitch-design`. The design is the registration:
read it first. No subtitle file is in the repository, and none was read to write or test this code: every test and
the dry run use invented text and a scripted or mocked model.

- `config.py`: paths, seeds, thresholds, the model settings.
- `subtitles.py` (pure): `.srt` parsing, lyric lines (♪, ♫, a line beginning or ending with `#`), the italic-run
  fallback, sound cues and tags, empty cues, scenes (gap over 8 s), dialogue hours (design §2.2).
- `sample.py` (pure): the blind sample (50 kept cues per film, `default_rng(2012)`), the offline coding form, the
  check of the author's codes (§3.4).
- `coding.py` (pure): the prompts from `prompts/`, the structured-output schemas and the strict parsing of the model's
  replies (§2.3, §2.4).
- `prompts/`: the frozen prompts and codebook. Every example is invented; no prompt names the films.
- `stats.py` (pure): per-cue codes, Cohen's κ, the validation and its gate, the scene bootstrap (10 000 replicates,
  `default_rng(42)`), the estimands, the degenerate-replicate rule, the pre-written readings, the power formulas (§1,
  §4, §5).
- `analysis.py` (pure): counts, estimates, readings, self-agreement, validation and the checks of §7 in one results
  dictionary, with cue numbers and codes only.
- `client.py`: the model client (`claude-sonnet-5-5` through the official SDK, streaming, structured outputs), the
  cache of raw replies, the call log.
  The key is read from the environment or `.env` by the SDK and is never printed or logged.
- `passes.py`: one run of pass 1 and pass 2 over a film, one retry, the 2 % failure limit (§3.6).
- `files.py`: subtitle files (UTF-8, else cp1252), hashes and the manifest, song marks, JSON.
- `synth.py`: invented subtitle files and a scripted model for the dry run and the tests.
- `cli.py`: the stages and their gates.

## Running

    P="--with numpy==2.5.3"
    uv run --no-project $P python -I tools/pitch/cli.py --synthetic        # invented files, scripted model

Every stage on the real files needs `--unblind` and refuses unless the tag `pitch-code` exists and is an ancestor of
HEAD, `tools/pitch` at HEAD equals it, `tools/pitch` and the design text have no uncommitted changes, and both
subtitle files match the hashes in `docs/research/pitch-files.sha256`. The code makes no tag. After the author tags
`pitch-code` and puts `pp1.srt` and `pp2.srt` in `tools/data/pitch/raw/` (gitignored):

    uv run --no-project $P python -I tools/pitch/cli.py --hash-files --unblind
    # commit docs/research/pitch-files.sha256
    uv run --no-project $P python -I tools/pitch/cli.py --italic-runs --unblind   # if a file has no ♪, ♫ or # marker
    # mark each run "song" or "not song" in docs/research/pitch-song-marks.json (cue numbers and times only)
    uv run --no-project $P python -I tools/pitch/cli.py --draw-sample --unblind
    # open tools/data/pitch/validation/form.html offline, code every cue, save validation-human.json next to it
    uv run --no-project $P python -I tools/pitch/cli.py --hash-sample --unblind
    # commit the manifest (and the song marks, if the fallback applies) in one commit
    uv run --no-project $P --with anthropic==2.3.0 python -I tools/pitch/cli.py --run 1 --unblind
    uv run --no-project $P --with anthropic==2.3.0 python -I tools/pitch/cli.py --run 2 --unblind
    # commit validation-human.json
    uv run --no-project $P python -I tools/pitch/cli.py --analyse --unblind   # docs/research/pitch-results.json

`--hash-files` refuses a file whose name was hashed before with another hash. `--draw-sample` refuses if any model
output exists or the sample was drawn before, and stops if the fallback applies without complete song marks.
`--hash-sample` checks the codes against the sample and the codebook and refuses codes changed after their hash.

`--run` refuses unless, in addition, no tracked file differs from HEAD and nothing is untracked in `tools/pitch` or
`docs/research`, the manifest is committed, `validation-human.json` exists and matches its committed hash, and, if the
lyric fallback applies, the song marks are committed with their hash. Raw replies are cached under
`tools/data/pitch/out/run<n>/cache/` (a rerun resumes from the cache; run and attempt are part of the cache key, so run
2 and a retry are fresh calls), the call log is `calls.jsonl`, and the run's settings with the SHA-256 of every prompt
file are in `settings.json`. More than 2 % failed scenes or jokes in a film and pass stops the run.

`--analyse` refuses unless the code is frozen, the files and the codes match their hashes and both runs are complete.

Tests (invented data only), then the full 10 000-replicate bootstrap, then ruff:

    uv run --no-project $P --with pytest==9.1.1 python -m pytest -q -rs tools/pitch
    uv run --no-project $P --with pytest==9.1.1 python -m pytest -q tools/pitch -m slow
    uvx ruff check tools/pitch

A plain run skips the slow test. CI runs `tools/pitch` in its own step (`numpy` and `pytest` are pinned in
`tools/requirements-tests.txt`; the tests never import the SDK, which is pinned in the commands above).

## Model settings (deviation of 27 October 2026)

Temperature 0, as registered, cannot be sent: Claude 5 models reject sampling parameters with a 400 and SDK 2.3.0 has
no temperature argument. Every call instead sends, explicitly, `thinking={"type": "adaptive"}`,
`output_config={"effort": "high", "format": {"type": "json_schema", ...}}` and no sampling parameter. The pass 1
schema limits cue numbers to the scene's own and `kind` to the codebook (the reply is `{"jokes": [...]}`); the pass 2
schema limits target, group type and butt to the codebook. The strict parsing stays as a second guard. A reply whose
stop reason is anything other than `end_turn` (`max_tokens`, `refusal`, ...) is a failed attempt even if its JSON
parses. `max_tokens` is 32 000 for pass 1 and 16 000 for pass 2, with room for thinking, and the calls stream. The
model is pinned as `claude-sonnet-5-5`, the SDK as `anthropic==2.3.0`; both, with thinking, effort, the prompt hashes
and the schema hash, are in each run's `settings.json` and in every cached request. See the design's change log.
