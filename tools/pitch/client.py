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


def cli_command(system: str, schema: dict) -> list[str]:
    """One isolated print-mode call: the pinned model and effort, the study's system prompt in place of the CLI's own,
    the schema as structured output, and no tools, settings, CLAUDE.md, MCP servers, skills or saved session."""
    return ["claude", "-p", "--model", C.MODEL, "--effort", C.EFFORT, "--system-prompt", system,
            "--json-schema", json.dumps(schema, sort_keys=True), "--output-format", "json", "--tools", "",
            "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]


def parse_cli_result(raw: str, model: str = C.MODEL) -> Reply:
    """The CLI's JSON result as a Reply. A completed call with a structured output from the pinned model alone is
    recorded as stop reason end_turn (the CLI reports the schema as a tool call); anything else is a failed attempt."""
    try:
        res = json.loads(raw)
    except ValueError:
        raise CallFailed("the CLI returned no JSON result") from None
    if res.get("is_error") or res.get("subtype") != "success" or res.get("structured_output") is None:
        raise CallFailed(f"CLI call failed: {res.get('subtype')} {res.get('api_error_status') or ''}".strip())
    used = sorted(res.get("modelUsage") or {})
    if used != [model]:
        raise CallFailed(f"CLI call used {used}, not {model}")
    usage = res.get("usage") or {}
    tokens_in = sum(int(usage.get(k) or 0) for k in
                    ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return Reply(json.dumps(res["structured_output"], ensure_ascii=False), model, "end_turn", tokens_in,
                 int(usage.get("output_tokens") or 0))


class ClaudeCliClient:
    """claude-sonnet-5-5 through the Claude Code CLI in print mode, signed in with the author's account. Each call
    is a fresh process in an empty folder; max_tokens is passed as the CLI's output-token limit."""

    def __init__(self, model: str = C.MODEL, timeout: int = C.CLI_TIMEOUT_S):
        self.model, self.timeout = model, timeout
        try:
            out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60, check=True)
        except (OSError, subprocess.SubprocessError):
            raise CallFailed("the claude CLI is not available") from None
        self.sdk_version = "claude-cli " + out.stdout.strip()

    def call(self, system: str, user: str, max_tokens: int, schema: dict) -> Reply:
        env = {k: v for k, v in os.environ.items() if k != KEY_NAME}
        env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_tokens)
        with tempfile.TemporaryDirectory(prefix="pitch-call-") as cwd:
            try:
                proc = subprocess.run(cli_command(system, schema), input=user, capture_output=True, text=True,
                                      cwd=cwd, env=env, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                raise CallFailed(f"CLI call timed out after {self.timeout} s") from None
        if proc.returncode != 0 and not proc.stdout.strip():
            raise CallFailed(f"CLI exited with {proc.returncode}")
        return parse_cli_result(proc.stdout, self.model)


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
