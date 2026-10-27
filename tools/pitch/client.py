"""The model client, the cache of raw replies and the call log (design §3.6, §4.1). All network I/O of the study.

The API key is read from the environment (or from .env into the environment) by the SDK itself; this module never
returns, prints or logs it.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
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
    def call(self, system: str, user: str, max_tokens: int) -> Reply: ...


def load_env_key(env_file: Path = C.ENV_FILE) -> bool:
    """Put the API key from .env into the environment unless it is already there. Says only whether a key is set."""
    if os.environ.get(KEY_NAME):
        return True
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and name.strip() == KEY_NAME and value.strip():
                os.environ[KEY_NAME] = value.strip().strip("'\"")
                break
    return bool(os.environ.get(KEY_NAME))


class AnthropicClient:
    """claude-sonnet-5-5 at the registered settings, through the official SDK (imported only for a real run)."""

    def __init__(self, model: str = C.MODEL, temperature: float | None = C.TEMPERATURE):
        import anthropic
        if not load_env_key():
            raise CallFailed(f"no {KEY_NAME} in the environment or in .env")
        self._sdk = anthropic
        self._client = anthropic.Anthropic(max_retries=4)
        self.model, self.temperature = model, temperature

    @property
    def sdk_version(self) -> str:
        return self._sdk.__version__

    def call(self, system: str, user: str, max_tokens: int) -> Reply:
        # SDK 2.x has no temperature argument, so the registered value goes in the body as written (see config)
        extra = {} if self.temperature is None else {"extra_body": {"temperature": self.temperature}}
        try:
            msg = self._client.messages.create(
                model=self.model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}],
                **extra)
        except self._sdk.APIError as err:
            # the status and type only: the SDK's message can echo request details
            raise CallFailed(f"{type(err).__name__} {getattr(err, 'status_code', '')}".strip()) from None
        text = "".join(b.text for b in msg.content if b.type == "text")
        return Reply(text, msg.model, msg.stop_reason, msg.usage.input_tokens, msg.usage.output_tokens)


class Cache:
    """Raw replies by the hash of everything that defines a request (run and attempt included, so run 2 and a retry
    are fresh calls). Lives under tools/data/pitch/out (gitignored): replies hold subtitle-derived text."""

    def __init__(self, root: Path):
        self.root = root

    @staticmethod
    def key(request: dict) -> str:
        return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def get(self, request: dict) -> Reply | None:
        path = self.root / f"{self.key(request)}.json"
        if not path.exists():
            return None
        return Reply(**json.loads(path.read_text(encoding="utf-8"))["reply"])

    def put(self, request: dict, reply: Reply) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{self.key(request)}.json"
        path.write_text(json.dumps({"request": request, "reply": dataclasses.asdict(reply)}, ensure_ascii=False,
                                   indent=1), encoding="utf-8")


class CallLog:
    """One line per call: film, pass, unit, attempt, status, tokens (design §3.6). No text."""

    def __init__(self, path: Path):
        self.path = path

    def write(self, **row) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
