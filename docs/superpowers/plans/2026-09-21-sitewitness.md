# sitewitness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python package `sitewitness` that turns a folder of texts and JSON files into a question-answering agent with a trust protocol enforced in code, an eval runner, a static trace page, a FastAPI server and a CLI; bsandova.com/ask becomes its first instance.

**Architecture:** Config (`sitewitness.toml`) → `index` (passages + BM25 + optional embeddings + data schemas) → `tools` (five runners with Anthropic schemas) → `agent` (hand-written tool loop over an injectable client) → `protocol.enforce` → `limits` (budget/rate stores) → `server` (FastAPI) / `cli` / `evaluate` / `page`. Every module is importable and testable alone; the Anthropic client is an interface so tests never touch the network.

**Tech Stack:** Python ≥ 3.10, `anthropic`, `fastapi`, `uvicorn`, `rank-bm25`, `quotecheck`, `tomli` (py<3.11); extra `embed`: `sentence-transformers`. Dev: uv, ruff, pytest, httpx (FastAPI test client).

**Spec:** `docs/superpowers/specs/2026-09-21-sitewitness-design.md` (bsandova.com repo)

## Global Constraints

- Package `sitewitness`, Apache-2.0, repo `~/Documents/Coding/sitewitness`, GitHub `sandovabarbora/sitewitness`, Python 3.10–3.13.
- Runtime deps only: `anthropic`, `fastapi`, `uvicorn`, `rank-bm25`, `quotecheck`, `tomli; python_version < "3.11"`. Extra `embed = ["sentence-transformers"]`.
- Protocol rules are read from config only; a decline (the exact sentence `I can't answer that from this site.`) is never enforced against.
- `X-Eval-Key` bypasses the per-IP limit only, never the budget.
- Tests never call the network: the model client is an interface (`ModelClient.create(messages, tools) -> Response`) with a fake in tests; embeddings use a stub embedder in tests.
- Commits end with the attribution lines from the session reminder.

---

## File structure

```
sitewitness/
  pyproject.toml · LICENSE · README.md · CHANGELOG.md
  src/sitewitness/__init__.py       version, compare-style public API: load_config, build_index, Agent, evaluate
  src/sitewitness/config.py         Config dataclasses + load_config(path) (toml)
  src/sitewitness/index.py          extract passages (html/md), describe data files, build/load Index, search (BM25 + embed + RRF)
  src/sitewitness/tools.py          TOOL_SCHEMAS + run_tool(name, input, index, config) -> str
  src/sitewitness/protocol.py       DECLINE, Trace dataclass, enforce()
  src/sitewitness/limits.py         LimitStore, MemoryStore, SqliteStore, check_and_count()
  src/sitewitness/client.py         ModelClient protocol, AnthropicClient, Response/Block dataclasses
  src/sitewitness/agent.py          Agent.ask(question, ip, eval_run) -> Answer
  src/sitewitness/server.py         create_app(agent, config) FastAPI
  src/sitewitness/evaluate.py       run_eval(golden, ask_fn) -> summary, rows; write files; exit code
  src/sitewitness/page/index.html   static page template with {{placeholders}}
  src/sitewitness/page.py           render_page(config, out_dir)
  src/sitewitness/cli.py            index | serve | ask | eval | page
  tests/conftest.py                 fixture site (2 html, 1 md, 2 json), FakeClient, StubEmbedder
  tests/test_config.py · test_index.py · test_tools.py · test_protocol.py · test_limits.py
  tests/test_agent.py · test_server.py · test_evaluate.py · test_cli.py
  .github/workflows/ci.yml · publish.yml
```

---

### Task 1: Scaffold + config

**Files:** `pyproject.toml`, `LICENSE`, `README.md`, `CHANGELOG.md`, `.gitignore`, `src/sitewitness/__init__.py`, `src/sitewitness/config.py`, `tests/conftest.py`, `tests/test_config.py`

**Interfaces produced:**
- `Config` dataclass: `site: SiteConfig(name, base_url, texts: list[str], data: dict[str,str], root: Path)`, `model: ModelConfig(name, max_output_tokens, price_in_per_m, price_out_per_m)`, `limits: LimitsConfig(max_tool_calls, max_wall_seconds, daily_budget_usd, per_ip_per_hour, store)`, `protocol: ProtocolConfig(numbers_need_tool, quotes_need_verification, require_tool_use, forbid_code, sources_must_exist)`, `server: ServerConfig(allowed_origins, eval_key_env)`, `index_dir: Path` (`.sitewitness` next to the toml).
- `load_config(path: str | Path) -> Config`; missing sections take the defaults from the spec.

- [ ] Write `tests/conftest.py`: `site_dir` fixture builds a tmp site: `texts/a.html` (h1 "Alpha text", 3 `<p>` with ≥ 8 words, one `<sup class="cite">`), `texts/b.md` (`# Beta`, two paragraphs, one list item), `data/surf.json` (`{"generated":"2026-09-15","skill":{"x":{"m":{"1":{"n":14,"mae":0.42}}}},"list":[{"a":1},{"a":2}]}`), `data/watch.json` (a list of 2 dicts), and `sitewitness.toml` with all sections. Returns the path.
- [ ] Write `tests/test_config.py`: loads the fixture toml → fields as written; a toml with only `[site]` → defaults (model `claude-sonnet-5`, `max_tool_calls == 8`, all protocol flags true, store `sqlite:.sitewitness/limits.db`).
- [ ] Run: `uv run pytest tests/test_config.py -q` → import error.
- [ ] Write `pyproject.toml` (hatchling, deps as in Global Constraints, script `sitewitness = "sitewitness.cli:main"`, ruff line 110), `config.py` with dataclasses and `load_config` (tomllib / tomli), `__init__.py` with `__version__ = "0.1.0"`.
- [ ] `uv sync && uv run pytest tests/test_config.py -q` → pass. Commit `chore: scaffold sitewitness, config`.

### Task 2: Index — passages, schemas, search

**Files:** `src/sitewitness/index.py`, `tests/test_index.py`

**Interfaces produced:**
- `Passage(id, page, title, text)`; `extract_passages(path: Path, root: Path) -> list[Passage]` (HTML: p/li/figcaption/dd; MD: paragraphs and list items; ≥ 8 words; citations stripped; `page` = `/` + relative path without `.html`/`.md`, `/index` stripped; `title` = first h1/`#` else stem).
- `describe_json(obj, depth=3) -> dict` (type per key; arrays: `len`, `item_keys` of first item, numeric `min/max` for leaf numeric arrays).
- `build_index(config, embedder=None) -> Index`; `Index.save(dir)`, `Index.load(dir)`; `Index.search(query, k=6) -> list[Passage]` (BM25 over folded tokens; if embeddings present, cosine ranking too, combined by reciprocal rank fusion k=60); `Index.get(passage_id)`; `Index.sources -> dict[path, {description, schema}]`; `Index.pages -> set[str]`.
- `Embedder` protocol: `embed(texts: list[str]) -> list[list[float]]`; `SentenceTransformersEmbedder(model_name)` under try/except import.

- [ ] Tests: passages from fixture (count, ids `a#0..`, page `/texts/a`, title, citation stripped, short `<p>` skipped); md extraction; `describe_json` on the fixture data; `build_index` → `.sitewitness/index.json` exists and `Index.load` round-trips; `search("beta")` returns the md passage first (BM25); with `StubEmbedder` (returns a fixed vector per known word) a paraphrase query ranks the intended passage first; RRF combines two rankings deterministically.
- [ ] Run → fail; implement; run → pass; ruff; commit `feat: index — passages, schemas, hybrid search`.

### Task 3: Tools

**Files:** `src/sitewitness/tools.py`, `tests/test_tools.py`

**Interfaces produced:**
- `TOOL_SCHEMAS: list[dict]` (five tools per spec table).
- `run_tool(name: str, input: dict, index: Index, config: Config, max_bytes: int = 3000) -> str` (JSON string); `read_data` supports `path` (dotted/indexed) and `find`; clipped output lists the keys present; `quote` uses `quotecheck.fold` on both sides and returns `{"status": "found"|"absent", "passage": ...}`; unknown tool → `{"error": ...}`.

- [ ] Tests: list_sources returns configured descriptions; describe_source returns the schema; read_data path/find/clip/unknown path; search returns ids the index knows; quote found through a hyphen/case difference, absent otherwise; unknown tool error.
- [ ] Run → fail; implement; run → pass; commit `feat: tools`.

### Task 4: Protocol

**Files:** `src/sitewitness/protocol.py`, `tests/test_protocol.py`

**Interfaces produced:**
- `DECLINE = "I can't answer that from this site."`
- `Trace` dataclass with the fields from the spec (`tools: list[ToolCall(name, input, ms, bytes, result_status)]`, `quotes_verified`, `quotes_absent`, `numbers_from_tools`, `protocol: dict[str,bool]`, `enforced: str | None`, …) and `to_dict()`.
- `enforce(answer: str, trace: Trace, config: ProtocolConfig, index: Index) -> tuple[str, Trace]`.

- [ ] Tests, one per rule with a crafted answer/trace: no tool + not a decline → enforced `require_tool_use`; digits + no data/search result → `numbers_need_tool`; ```` ``` ```` / `def x` / `<b>` → `forbid_code`; 40+ char quote without a found quote → `quotes_need_verification`; `Sources: nope.json` → `sources_must_exist`; `Sources: /texts/a` and a data path both accepted; a decline is never enforced; a rule turned off in config is skipped; the replaced answer starts with `DECLINE`.
- [ ] Run → fail; implement; run → pass; commit `feat: protocol enforced in code`.

### Task 5: Limits

**Files:** `src/sitewitness/limits.py`, `tests/test_limits.py`

**Interfaces produced:**
- `LimitStore` protocol: `get(key) -> float`, `add(key, delta: float, ttl: int) -> float`.
- `MemoryStore()`, `SqliteStore(path)`; `store_from_config(spec: str) -> LimitStore` (`memory` | `sqlite:PATH`).
- `Gate(store, config).check(ip: str, eval_run: bool) -> str | None` (`"budget"` | `"rate"` | None; increments the IP counter when allowed), `Gate.spend(cost_usd) -> float` (new day total), `Gate.spent_today() -> float`.

- [ ] Tests for both stores (get/add/ttl expiry via injected clock), budget decline at the threshold, rate decline at `per_ip_per_hour`, eval_run bypasses rate but not budget, keys use UTC day/hour.
- [ ] Run → fail; implement; run → pass; commit `feat: limits`.

### Task 6: Client + agent loop

**Files:** `src/sitewitness/client.py`, `src/sitewitness/agent.py`, `tests/test_agent.py`, `tests/conftest.py` (add `FakeClient`)

**Interfaces produced:**
- `Block` (`type`, `text`, `id`, `name`, `input`), `Response(content: list[Block], stop_reason, usage_in, usage_out, model)`; `ModelClient` protocol `create(system, messages, tools, max_tokens) -> Response`; `AnthropicClient(model, api_key=None)` implementing it with the `anthropic` SDK.
- `Answer(text: str, trace: Trace)`; `Agent(config, index, client, gate).ask(question: str, ip: str = "0", eval_run: bool = False) -> Answer` (steps 1–5 of the spec; system prompt built from config; final no-tool turn at the cap).

- [ ] `FakeClient(script: list[Response])` returns responses in order and records the messages it received.
- [ ] Tests: text-only response → answer, 1 turn, tokens summed, cost from configured prices, budget spent; tool_use → tool ran (result visible in the next messages), trace.tools[0] name/bytes; cap of 2 → third call gets no `tools` and the final instruction; decline detection; `model_used` from the response; budget/rate decline before any client call (client not touched); protocol enforcement applied (a number without tool → enforced).
- [ ] Run → fail; implement; run → pass; commit `feat: agent loop`.

### Task 7: Server

**Files:** `src/sitewitness/server.py`, `tests/test_server.py`

**Interfaces produced:** `create_app(agent: Agent, config: Config) -> FastAPI` with `POST /ask`, `GET /health`, CORS, IP from `CF-Connecting-IP` / `X-Forwarded-For` / client host, `X-Eval-Key` compared to `os.environ[config.server.eval_key_env]`.

- [ ] Tests with `fastapi.testclient.TestClient` and `FakeClient`: 400 on missing question, 200 with `{answer, trace}`, 502 when the client raises, `/health` fields, CORS header for an allowed origin, eval key bypasses rate (two stores of hits).
- [ ] Run → fail; implement; run → pass; commit `feat: server`.

### Task 8: Evaluate

**Files:** `src/sitewitness/evaluate.py`, `tests/test_evaluate.py`

**Interfaces produced:** `score(item: dict, answer: str, trace: dict) -> bool`; `run_eval(golden: list[dict], ask: Callable[[str], dict], api: str, model_hint: str | None) -> tuple[dict, list[dict]]`; `write_eval(summary, rows, out_dir)` (eval.json + eval-history.json upsert by date); `exit_code(summary, allowed_misses=0) -> int`.

- [ ] Tests: substring match with spaces normalised; DECLINE kind; protocol violations counted from `enforced`/flags; history upsert; exit 0/1.
- [ ] Run → fail; implement; run → pass; commit `feat: eval runner`.

### Task 9: Page + CLI

**Files:** `src/sitewitness/page/index.html`, `src/sitewitness/page.py`, `src/sitewitness/cli.py`, `tests/test_cli.py`

**Interfaces produced:** `render_page(config: Config, api_url: str, examples: list[str], out_dir: Path) -> Path`; CLI `sitewitness index [--embed] [--config PATH]`, `serve [--host 0.0.0.0] [--port 8000]`, `ask "q"`, `eval GOLDEN [--api URL] [--allowed-misses N] [--out DIR]`, `page OUT_DIR [--api URL] [--example Q]...`.

- [ ] Page template = the current bsandova.com `ask/index.html` generalised: `{{SITE_NAME}}`, `{{API}}`, `{{EXAMPLES_JSON}}`, neutral palette in a `<style>` block, optional `{{EXTRA_CSS_HREF}}`.
- [ ] Tests: `index` on the fixture writes `.sitewitness/index.json`; `page` writes an html containing the api url and examples; `ask` with `SITEWITNESS_FAKE=1` env (cli wires FakeClient) prints an answer; `eval` exit code.
- [ ] Run → fail; implement; run → pass; commit `feat: page and cli`.

### Task 10: CI, README, publish

**Files:** `.github/workflows/ci.yml`, `.github/workflows/publish.yml`, `README.md`

- [ ] ci.yml (matrix 3.10–3.13, ruff, pytest), publish.yml (trusted publishing on `v*`), README with the five commands, the toml, the protocol table and a "what the trace shows" example. `gh repo create sandovabarbora/sitewitness --public --push`; `gh api -X PUT repos/sandovabarbora/sitewitness/environments/pypi`. Commit `ci + readme`.

### Task 11: bsandova.com as instance 1

**Files (site repo):** `sitewitness.toml`, `ask/golden.json` (unchanged), `ask/index.html` (regenerated + site stylesheet + "run this on your own site" section), `ask/worker/src/index.js` (proxy), `fly.toml` + `Dockerfile` in the sitewitness repo under `deploy/`, `.github/workflows/ask-eval.yml` (call `sitewitness eval`).

- [ ] Write `sitewitness.toml` for the site (texts glob `texts/**/*.html`, the nine data files with their descriptions, prices, limits as today, origins).
- [ ] `sitewitness index --embed` → `ask/index.json` + embeddings committed? No: index is built in the Docker image at deploy (texts are in the repo), embeddings computed there; the site keeps `ask/index.json` only for the page's passage count.
- [ ] Deploy: `deploy/Dockerfile` (uv, `sitewitness serve`), `fly launch --name sitewitness-bsandova --region ams`, secrets `ANTHROPIC_API_KEY`, `SITEWITNESS_EVAL_KEY`; the site repo is cloned in the image at build (or texts copied) — simplest: the Dockerfile in the **site** repo builds from the site checkout; `fly deploy` from the site repo in a GitHub Action on push to main (`deploy-ask.yml`), needs `FLY_API_TOKEN`.
- [ ] Worker `bsandova-ask` → proxy `POST /ask`, `GET /health` to `https://sitewitness-bsandova.fly.dev`, same CORS; deploy.
- [ ] Run `sitewitness eval ask/golden.json --api https://api.bsandova.com` → ≥ 28/30 expected; commit eval.json; page regenerated with the site's `style.css`/`text.css` and the new section. Deploy site.
- [ ] Update `texts/ai-over-data.html` §6 and the ask row with "pip install sitewitness".

---

## Self-review

- Spec coverage: config (1), index incl. describe/RRF/embedder (2), tools (3), protocol incl. sources_must_exist and decline exemption (4), limits with eval bypass (5), client interface + agent + final turn + cost (6), server (7), eval + history + exit (8), page + CLI (9), CI/publish/README (10), instance 1 with Fly + proxy + eval + page section (11). Non-goals untouched.
- Placeholders: none; each task names files, interfaces and tests. Code bodies are written at implementation with the interfaces fixed here.
- Types: `Config` sub-dataclass names consistent across tasks; `Trace`/`Answer`/`Agent.ask` signature identical in 6, 7, 8, 9; `Index.search/get/sources/pages` used by 3, 4, 6.
