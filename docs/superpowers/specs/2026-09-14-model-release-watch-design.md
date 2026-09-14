# Model release watch — design

**Date:** 2026-09-14 · **Owner:** Barbora Šandová · **Status:** approved in chat ("oki"), building.

## Intent
Quaesitor's harness measured two frontier models once, in August 2026. The claim behind
the service, "trust grows faster than accuracy", is a claim about time. So run the same
measurement every month against the current frontier models and publish the series:
silent-failure rate and refusal rate, by model and by pack, with the actual model id,
tool version, fingerprints and cost of every run. One page, one growing chart.

## Scope, v1
- **Models:** `sonnet`, `opus`, `haiku` (Claude Code CLI aliases). The alias is what an
  operator types; the record stores what actually answered (`claude-opus-5`,
  `claude-haiku-4-5-20251001`, …). A new alias is one word in `MODELS`.
- **Packs:** `ecommerce` (26 traps; metric = silent-failure rate, refusal rate) and
  `abstention` (10 questions past the edge of the data; metric = declined rate, where
  declining is correct). Czech only (`LANGS=cs`), three repeats, as in August.
- **Cadence:** monthly, 1st of the month 03:00 local, via launchd on the operator's Mac
  (the CLI carries her login and the same tool as the August baseline; GitHub Actions
  would need an API key and a different tool path).
- **Budget:** ≈ 6 + 4 + 2 USD per pack sweep → 20–25 USD/month. `MAX_RUN_USD` guard.

## Data flow
1. `scripts/watch.sh` (quaesitor/method): for each pack, `LANGS=cs scripts/sweep.sh <pack> $MODELS`
   (the sweep strips the operator's hook and output style, restores them on exit).
2. `python -m src.watch_index`: parses every `outputs/agent_<model>_cs[_pack].md` written
   today, archives a copy to `outputs/watch/<YYYY-MM-DD>/`, appends one record per run to
   `outputs/watch/watch.json`:
   `{date, alias, model, cli, pack, lang, repeats, n, outcomes{correct,silently_wrong,
   implausible,refused,…}, unstable, cost_usd, sha{questions,warehouse,prompt,docs}}`.
   Records are append-only; a rerun on the same day replaces that day's record for the
   same (alias, pack).
3. The file is copied to `bsandova.com/watch/data.json`, committed and pushed. The page
   renders from it; no number on the page is typed.
4. August 2026 runs are backfilled from `outputs/` as the first point (dated by their
   own fingerprint).

## Page — `bsandova.com/watch/`
- Header: title, the claim, four facts (months measured · models · latest silent-failure
  rate opus/sonnet/haiku · cost of the last month).
- Chart 1: silent-failure rate on the ecommerce pack, one line per model, x = month.
- Chart 2: declined rate on the abstention pack, one line per model.
- Table: every run — date, alias → actual model, CLI version, pack, n, outcomes, unstable,
  cost, fingerprints. Links to the archived report.
- Method note and links to the three Quaesitor texts. Same register as the site.
- Vanilla JS over `data.json`; SVG drawn in the browser; no library.

## Not in v1
Other providers (the harness speaks Claude Code CLI and Ollama only); other languages;
documentation arm; automatic alerts. A run that fails leaves no record and logs to
`outputs/watch/log/`; the page shows the gap.

## Done when
`watch.sh` has produced the September records for 3 models × 2 packs, the page renders
the August baseline plus September, the launchd job is loaded, and the cost of the run
is on the page.
