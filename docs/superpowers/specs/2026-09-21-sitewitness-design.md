# sitewitness — an agent over your site that shows its work

Date: 2026-09-21 · Status: approved in chat · Owner: Barbora Šandová

## Purpose

A Python package that turns a folder of texts (HTML or Markdown) and JSON data files into a
question-answering agent with a **trust protocol enforced in code**, an evaluation runner, and a
static page that shows every answer's trace. bsandova.com/ask is the first instance; the package
replaces its hand-written Worker. Audience: authors of static sites and documentation who want an
assistant that cannot invent a number or a quotation about their own material.

Package `sitewitness` (free on PyPI). Apache-2.0. Repo `~/Documents/Coding/sitewitness`, GitHub
`sandovabarbora/sitewitness`. Python ≥ 3.10. Runtime deps: `anthropic`, `fastapi`, `uvicorn`,
`rank-bm25`, `quotecheck`, `tomli` (py<3.11). Extra `embed`: `sentence-transformers`.

## Non-goals (v1)

Streaming, multi-turn conversation, providers other than Anthropic (the client is behind one
interface so a second can be added), a UI for editing the golden set, Redis/remote limit stores.

## Configuration — `sitewitness.toml`

```toml
[site]
name = "bsandova.com"
base_url = "https://bsandova.com"          # used for Sources: validation and page links
texts = ["texts/**/*.html"]                # globs, relative to the config file
data = { "surf/data.json" = "Surf forecast verification …", "watch/data.json" = "…" }

[model]
name = "claude-sonnet-5"
max_output_tokens = 700
price_in_per_m = 3.0                        # configured list prices; the trace says so
price_out_per_m = 15.0

[limits]
max_tool_calls = 8
max_wall_seconds = 60
daily_budget_usd = 4.0
per_ip_per_hour = 12
store = "sqlite:.sitewitness/limits.db"     # or "memory"

[protocol]                                 # every rule on by default; off only here, never in a prompt
numbers_need_tool = true
quotes_need_verification = true
require_tool_use = true
forbid_code = true
sources_must_exist = true

[server]
allowed_origins = ["https://bsandova.com", "http://localhost:8791"]
eval_key_env = "SITEWITNESS_EVAL_KEY"       # header X-Eval-Key bypasses per-IP limit, never the budget
```

## Index — `sitewitness index`

Texts → passages: every `<p>`, `<li>`, `<figcaption>`, `<dd>` (HTML) or paragraph/list item
(Markdown) with ≥ 8 words, with `id = <file stem>#<n>`, `page` (URL path derived from the file
path, `.html` and `/index` stripped), `title` (first `<h1>` / `#`). Citations `<sup class="cite">`
stripped. Written to `.sitewitness/index.json`; BM25 built at load time; with `[embed]`, passage
embeddings (`all-MiniLM-L6-v2` by default, configurable) to `.sitewitness/embeddings.npy`.

Data files: read and summarised once at index time → `describe` schema per file: top-level keys,
for each key its type, and for arrays the length and the keys of the first item, recursively to
depth 3; numeric ranges for leaf arrays. Stored in `index.json` under `sources`.

## Tools (Anthropic tool schemas, one runner each)

| tool | input | output |
|---|---|---|
| `list_sources` | — | `{path: description}` for every data file |
| `describe_source` | `source` | the schema summary from the index |
| `read_data` | `source`, `path?` (dotted/indexed), `find?` (substring filter on arrays) | JSON, clipped to `max_bytes` (default 3000); when clipped, the keys present are listed |
| `search` | `query`, `k?` (default 6) | passages ranked by hybrid score: BM25 and, if embeddings exist, cosine, combined by reciprocal rank fusion |
| `quote` | `passage_id`, `phrase` | `found` with the passage, or `absent` with the passage's first 300 chars; folding via `quotecheck.fold` |

## Agent loop — `agent.py`

No framework. `ask(question) -> Answer(text, trace)`:
1. limits: budget and per-IP checks (before any model call), counter increment
2. loop up to `max_tool_calls`: model call with tools → run tool_use blocks → append results
3. when the cap is reached: one final call with no tools and an instruction to answer from the
   conversation or decline
4. protocol enforcement (below), cost from configured prices, trace assembled
5. budget updated with the run's cost

Trace fields: `model` (requested), `model_used` (from the response), `turns`, `tools[] {name,
input, ms, bytes}`, `input_tokens`, `output_tokens`, `cost_usd`, `prices`, `ms`, `stop`,
`declined`, `protocol {rule: bool}`, `enforced` (rule name or null), `budget_spent_usd`.

The system prompt states the rules, the site name and the decline sentence. It contains no
site content; everything comes through tools.

## Protocol — `protocol.py`

`enforce(answer: str, trace: Trace, config) -> tuple[str, Trace]`. Rules, checked in this order,
first violation wins and replaces the answer with the decline sentence plus one fixed sentence
about what the assistant does; `trace.enforced` names the rule:

1. `require_tool_use`: no tool was called and the answer is not a decline
2. `numbers_need_tool`: a digit in the answer (outside the `Sources:` line) and no `read_data` /
   `search` result in the conversation
3. `forbid_code`: fenced code, `def ` / `import ` at line start, or an HTML tag in the answer
4. `quotes_need_verification`: a quoted run of ≥ 40 characters and no `quote` call returned `found`
5. `sources_must_exist`: the `Sources:` line names a path that is neither a configured data file
   nor a page in the index

A decline (the exact sentence) is never enforced against. Rules are read from config only.

## Limits — `limits.py`

`LimitStore` interface: `get(key) -> float`, `add(key, delta, ttl)`. Implementations: `MemoryStore`
(tests, single process), `SqliteStore` (file path from config). Keys `budget:<UTC day>` and
`ip:<ip>:<UTC hour>`. Budget exceeded → decline with the reset time; rate exceeded → decline.

## Server — `server.py`

FastAPI. `POST /ask {question}` → `{answer, trace}`; `GET /health` → `{ok, model, budget_usd,
spent_today_usd, index: {passages, sources}}`; CORS from config; client IP from
`CF-Connecting-IP` / `X-Forwarded-For` / peer. `X-Eval-Key` bypasses the per-IP limit only.
Errors: 400 bad body, 502 upstream, with `{error}`.

## Eval — `sitewitness eval golden.json`

Golden item: `{q, kind: number|text|quote|decline, expect}`. Score: `ok` = expect substring in the
answer (case-insensitive, spaces normalised) and not declined, or declined when `expect ==
"DECLINE"`. Per run: `n`, `correct`, `by_kind`, `protocol_violations` (any `enforced` or flag),
`cost_usd`, `median_ms`, `model`. Writes `eval.json` and appends to `eval-history.json`. Exit 1
when `correct < n - allowed_misses` (default 0), so it can gate CI.

## Page — `sitewitness page`

Copies the static page (question box, example chips, answer, trace panel, eval table, history
table) into a target folder, with the API base URL, site name and example questions from config
inlined. Palette neutral; a site can override with its own stylesheet.

## CLI

`sitewitness index [--embed]` · `serve [--host --port]` · `ask "question"` (prints answer and
trace) · `eval golden.json [--api URL] [--allowed-misses N]` · `page OUT_DIR`.

## Tests (pytest, no network)

- protocol: one test per rule with a crafted answer/trace, plus "a decline is never enforced"
- agent: fake Anthropic client with scripted tool_use → tools run, trace counts right, cap → final
  no-tool turn, budget added; model_used taken from the response
- index: HTML and Markdown extraction (ids, pages, titles, citation stripping, min words);
  `describe` schema; search finds an exact term (BM25) and, with a stub embedder, a paraphrase;
  reciprocal rank fusion order
- tools: `read_data` path/find/clip, `quote` found/absent through quotecheck fold
- limits: memory and sqlite stores, day/hour keys, budget decline, eval-key bypass of rate only
- server: 400 / 200 / 502 with the fake client; CORS header
- eval: scoring rules, history append, exit code
- cli: `index` on a fixture site produces the files

Target ≥ 45 tests; CI matrix 3.10–3.13; publish on tag via trusted publishing.

## bsandova.com as instance 1

`sitewitness.toml` in the site repo; `ask/index.json` produced by `sitewitness index`; the golden
set unchanged; the Python server deployed to Fly.io (free tier) as `sitewitness-bsandova`; the
Cloudflare Worker `bsandova-ask` becomes a proxy to it (same URL `api.bsandova.com`, so nothing
on the site changes) — or stays as is until the server is up. The Ask page is regenerated by
`sitewitness page` with the site stylesheet. `texts/ask.html`? No: the existing `ask/` page gains
one section, "run this on your own site", with the five commands.
