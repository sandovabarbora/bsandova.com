"""The model clients, the cache of raw replies and the call log (design §3.6, §4.1). All network I/O of the study.

The API key is read from the environment (or from .env into the environment) by the SDK itself; this module never
returns, prints or logs it.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Protocol

import config as C

log = logging.getLogger(__name__)
KEY_NAME = "ANTHROPIC_API_KEY"


class CallFailed(RuntimeError):
    """The API returned an error or no reply. Counts as a failed attempt."""


@dataclasses.dataclass(frozen=True)
class Reply:
    text: str
    model: str
    stop_reason: str | None
    input_tokens: int
    output_tokens: int


class ModelClient(Protocol):
    def call(self, system: str, user: str, max_tokens: int, schema: dict) -> Reply: ...


def load_env_key(env_file: Path | None = None) -> bool:
    """Put the API key from .env into the environment unless it is already there. Says only whether a key is set."""
    env_file = env_file or C.ENV_FILE
    if os.environ.get(KEY_NAME):
        return True
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and name.strip() == KEY_NAME and value.strip():
                os.environ[KEY_NAME] = value.strip().strip("'\"")
                break
    return bool(os.environ.get(KEY_NAME))


def request_body(model: str, system: str, user: str, max_tokens: int, schema: dict) -> dict:
    """Every call: the pinned model, explicit adaptive thinking at the fixed effort, an enum-constrained JSON schema,
    and no sampling parameter (Claude 5 models reject them; design change log, 27 October 2026)."""
    return {"model": model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": user}], "thinking": dict(C.THINKING),
            "output_config": {"effort": C.EFFORT, "format": {"type": "json_schema", "schema": schema}}}


class AnthropicClient:
    """claude-sonnet-5-5 through the official SDK (imported only for a real run). Calls stream, since the SDK refuses
    a non-streaming call whose max_tokens could take over ten minutes."""

    def __init__(self, model: str = C.MODEL):
        import anthropic
        if not load_env_key():
            raise CallFailed(f"no {KEY_NAME} in the environment or in .env")
        self._sdk = anthropic
        self._client = anthropic.Anthropic(max_retries=4)
        self.model = model

    @property
    def sdk_version(self) -> str:
        return self._sdk.__version__

    def call(self, system: str, user: str, max_tokens: int, schema: dict) -> Reply:
        try:
            with self._client.messages.stream(**request_body(self.model, system, user, max_tokens, schema)) as stream:
                msg = stream.get_final_message()
        except self._sdk.APIError as err:
            # the status and type only: the SDK's message can echo request details
            raise CallFailed(f"{type(err).__name__} {getattr(err, 'status_code', '')}".strip()) from None
        text = "".join(b.text for b in msg.content if b.type == "text")
        return Reply(text, msg.model, msg.stop_reason, msg.usage.input_tokens, msg.usage.output_tokens)


CLI_SETTINGS = {"disableAllHooks": True, "autoMemoryEnabled": False}
CLI_ENV = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "DISABLE_AUTOUPDATER": "1",
           "DISABLE_TELEMETRY": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
LIMIT_STATUSES = (429, 529)   # rate or usage limit, and overloaded
CLI_TURNS = (2, 3)


class UsageLimit(RuntimeError):
    """The account's usage or rate limit: not a failed attempt; the client waits, then stops the run (it resumes from
    the cache)."""


def cli_command(system: str, schema: dict) -> list[str]:
    """One isolated print-mode call: the pinned model and effort, the study's system prompt in place of the CLI's own,
    the schema as structured output, and no tools, settings files, hooks, memory, CLAUDE.md, MCP servers, skills or
    saved session. The user prompt goes on stdin."""
    return ["claude", "-p", "--model", C.MODEL, "--effort", C.EFFORT, "--system-prompt", system,
            "--json-schema", json.dumps(schema, sort_keys=True), "--output-format", "json", "--tools", "",
            "--setting-sources", "", "--settings", json.dumps(CLI_SETTINGS), "--strict-mcp-config",
            "--disable-slash-commands", "--no-session-persistence"]


def cli_env(max_tokens: int = 0) -> dict[str, str]:
    """The caller's environment without any ANTHROPIC_ variable (the API key, a base URL or model override; the call
    runs on the signed-in account), with memory, CLAUDE.md, auto-update and telemetry off and max_tokens as the
    output-token limit."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
    env = {**env, **CLI_ENV}
    return {**env, "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(max_tokens)} if max_tokens else env


def parse_cli_result(raw: str, model: str = C.MODEL, max_tokens: int | None = None) -> Reply:
    """The CLI's JSON result as a Reply. A call counts only if it completed with the schema's tool call as its stop,
    in two turns (the tool call, then its acknowledgement) or three (the answer as plain text first, which the CLI
    then asks to be given through the tool, or a reply the tool's validation sent back), with no denied permission,
    a structured output from the pinned model alone and every request below max_tokens (no request cut at the limit;
    when the CLI does not list its requests, the model's total output over the call must be below it); it is then
    recorded with stop reason end_turn. Anything else, a refusal included, is a failed attempt; a usage or rate limit
    raises UsageLimit."""
    try:
        res = json.loads(raw)
    except ValueError:
        raise CallFailed("the CLI returned no JSON result") from None
    if not isinstance(res, dict):
        raise CallFailed("the CLI result is not a JSON object")
    if res.get("api_error_status") in LIMIT_STATUSES:
        raise UsageLimit(f"status {res.get('api_error_status')}")
    if res.get("is_error") or res.get("subtype") != "success":
        raise CallFailed(f"CLI call failed: subtype {res.get('subtype')!r}, is_error {res.get('is_error')!r}, "
                         f"status {res.get('api_error_status')!r}")
    for key, want in {"terminal_reason": "completed", "stop_reason": "tool_use"}.items():
        if res.get(key) != want:
            raise CallFailed(f"CLI call ended with {key} {res.get(key)!r}, not {want!r}")
    if res.get("num_turns") not in CLI_TURNS:
        raise CallFailed(f"CLI call took {res.get('num_turns')!r} turns")
    if res.get("permission_denials"):
        raise CallFailed("CLI call had a denied permission")
    if not isinstance(res.get("structured_output"), dict):
        raise CallFailed("CLI call has no structured output")
    used = sorted(res.get("modelUsage") or {})
    if used != [model]:
        raise CallFailed(f"CLI call used {used}, not {model}")
    usage = res.get("usage")
    if not isinstance(usage, dict):
        raise CallFailed("CLI call has no token usage")
    turns = usage.get("iterations") or []
    try:
        if not isinstance(turns, list) or not all(isinstance(t, dict) for t in turns):
            raise TypeError
        # per request when the CLI lists them, otherwise the model's total over the call (a stricter bound)
        per_turn = ([int(t["output_tokens"]) for t in turns] if turns
                    else [int(res["modelUsage"][model]["outputTokens"])])
        tokens_in = sum(int(usage.get(k) or 0) for k in
                        ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    except (KeyError, TypeError, ValueError):
        raise CallFailed("CLI call has malformed token usage") from None
    if min(per_turn) < 0 or sum(per_turn) == 0:
        raise CallFailed("CLI call reports no output tokens")
    if max_tokens is not None and max(per_turn) >= max_tokens:
        raise CallFailed("CLI call reached max_tokens")
    out_total = sum(per_turn)
    return Reply(json.dumps(res["structured_output"], ensure_ascii=False), model, "end_turn", tokens_in, out_total)


class ClaudeCliClient:
    """claude-sonnet-5-5 through the Claude Code CLI in print mode, signed in with the author's account. Each call
    is a fresh process in an empty folder. A usage or rate limit is waited out (doubling from one minute, at most
    LIMIT_WAIT_S in all); after that the run stops and resumes from the cache when started again."""

    def __init__(self, model: str = C.MODEL, timeout: int = C.CLI_TIMEOUT_S, sleep=time.sleep):
        self.model, self.timeout, self.sleep = model, timeout, sleep
        try:
            out = subprocess.run(["claude", "--version"], capture_output=True, text=True, encoding="utf-8",
                                 timeout=60, check=True, env=cli_env())
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise CallFailed("the claude CLI is not available") from None
        self.sdk_version = "claude-cli " + out.stdout.strip()

    def _once(self, system: str, user: str, max_tokens: int, schema: dict) -> Reply:
        with tempfile.TemporaryDirectory(prefix="call-") as cwd:
            try:
                proc = subprocess.run(cli_command(system, schema), input=user, capture_output=True, text=True,
                                      encoding="utf-8", cwd=cwd, env=cli_env(max_tokens), timeout=self.timeout)
            except subprocess.TimeoutExpired:
                raise CallFailed(f"CLI call timed out after {self.timeout} s") from None
            except (OSError, UnicodeError, subprocess.SubprocessError) as err:
                raise CallFailed(f"CLI call could not run: {type(err).__name__}") from None
        if proc.returncode != 0:
            try:
                parse_cli_result(proc.stdout, self.model, max_tokens)
            except UsageLimit:
                raise
            except CallFailed:
                pass
            raise CallFailed(f"CLI exited with {proc.returncode}")
        return parse_cli_result(proc.stdout, self.model, max_tokens)

    def call(self, system: str, user: str, max_tokens: int, schema: dict) -> Reply:
        waited, wait = 0, 60
        while True:
            try:
                return self._once(system, user, max_tokens, schema)
            except UsageLimit as err:
                if waited >= C.LIMIT_WAIT_S:
                    raise SystemExit(f"stopping: usage limit ({err}) after {waited} s of waiting; start the same "
                                     "run again later, it resumes from the cache") from None
                log.warning("usage limit (%s), waiting %d s", err, wait)
                self.sleep(wait)
                waited += wait
                wait = min(wait * 2, 900)


class Cache:
    """Raw replies by the hash of everything that defines a request (run and attempt included, so run 2 and a retry
    are fresh calls). Lives under tools/data/pitch/out (gitignored): replies hold subtitle-derived text."""

    def __init__(self, root: Path):
        self.root = root

    @staticmethod
    def key(request: dict) -> str:
        return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def get(self, request: dict) -> Reply | None:
        """The cached reply, or None; a file that does not read back as a reply (a crash mid-write) is a miss."""
        path = self.root / f"{self.key(request)}.json"
        try:
            return Reply(**json.loads(path.read_text(encoding="utf-8"))["reply"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def put(self, request: dict, reply: Reply) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{self.key(request)}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"request": request, "reply": dataclasses.asdict(reply)}, ensure_ascii=False,
                                  indent=1), encoding="utf-8")
        os.replace(tmp, path)


class CallLog:
    """One line per call: film, pass, unit, attempt, status, tokens (design §3.6). No text."""

    def __init__(self, path: Path):
        self.path = path

    def write(self, **row) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
