"""The model client and the two passes with a mocked client: settings, caching, retries, the 2 % limit and the key
that is never printed or logged. No real call is made."""
from __future__ import annotations

import json
import logging
import sys
import types

import client as CL
import coding as K
import config as C
import passes as P
import pytest
import subtitles as S

FAKE_KEY = "not-a-real-key-" + "q" * 12


def prompts():
    return {name: (C.PROMPTS / name).read_text(encoding="utf-8") for name in K.PROMPT_FILES}


def scenes(n=3):
    return [S.Scene(k + 1, (S.Cue(10 * k + 1, 30.0 * k, 30.0 * k + 2, (f"invented line {k}a",)),
                            S.Cue(10 * k + 2, 30.0 * k + 3, 30.0 * k + 5, (f"invented line {k}b",))))
            for k in range(n)]


def _first(user):
    line = user.split("Scene to segment")[1].splitlines()[1]
    return int(line.split("]")[0].strip("["))


class FakeClient:
    """Answers by pass: a segment reply per scene and a code reply per joke, from scripted functions."""

    def __init__(self, segment=None, code=None):
        self.calls = []
        self.segment = segment or (lambda user, n: json.dumps([{"first_cue": _first(user), "last_cue": _first(user),
                                                                 "kind": "joke"}]))
        self.code = code or (lambda user, n: '{"target": "group", "group_type": "weight", "group_other": "", '
                                             '"butt": "group"}')

    def call(self, system, user, max_tokens):
        self.calls.append((system, user, max_tokens))
        n = len(self.calls)
        text = self.segment(user, n) if "Scene to segment" in user else self.code(user, n)
        return CL.Reply(text, "claude-sonnet-5-5-fake", "end_turn", 100, 10)


def run(tmp_path, client, sc=None, run_no=1):
    return P.run_film("pp1", sc or scenes(), prompts(), client, CL.Cache(tmp_path / f"cache{run_no}"),
                      CL.CallLog(tmp_path / "log.jsonl"), run_no)


def log_rows(tmp_path):
    return [json.loads(ln) for ln in (tmp_path / "log.jsonl").read_text().splitlines()]


def test_both_passes_return_cue_numbers_and_codes_only(tmp_path):
    out = run(tmp_path, FakeClient())
    assert out["scenes"] == 3 and out["jokes_found"] == 3 and out["failed_scenes"] == [] == out["failed_jokes"]
    assert out["jokes"][0] == {"id": "1-1", "scene": 1, "first_cue": 1, "last_cue": 1, "kind": "joke",
                               "target": "group", "group_type": "weight", "group_other": "", "butt": "group"}
    assert "invented" not in json.dumps(out) and out["model_versions"] == ["claude-sonnet-5-5-fake"]


def test_the_requests_use_the_registered_settings_and_the_log_holds_no_text(tmp_path):
    fake = FakeClient()
    run(tmp_path, fake)
    assert [c[2] for c in fake.calls] == [C.MAX_TOKENS["segment"]] * 3 + [C.MAX_TOKENS["code"]] * 3
    assert "(none: this is the first scene)" in fake.calls[0][1] and "[1] invented line 0a" in fake.calls[1][1]
    cached = list((tmp_path / "cache1").glob("*.json"))
    assert len(cached) == 6
    req = json.loads(cached[0].read_text())["request"]
    assert req["model"] == "claude-sonnet-5-5" and req["temperature"] == 0.0 and req["run"] == 1
    assert "invented" not in (tmp_path / "log.jsonl").read_text()
    assert set(log_rows(tmp_path)[0]) == {"film", "run", "pass", "unit", "attempt", "status", "cached", "input_tokens",
                                          "output_tokens"}


def test_a_rerun_uses_the_cache_and_run_two_calls_afresh(tmp_path):
    run(tmp_path, FakeClient())
    again = FakeClient()
    assert run(tmp_path, again)["jokes_found"] == 3 and again.calls == []
    second = FakeClient()
    run(tmp_path, second, run_no=2)
    assert len(second.calls) == 6
    rows = log_rows(tmp_path)
    assert sum(r["cached"] for r in rows) == 6 and {r["status"] for r in rows} == {"ok"}


def test_a_bad_reply_is_retried_once_and_then_counted_as_failed(tmp_path):
    seen = {}

    def segment(user, n):
        first = _first(user)
        seen[first] = seen.get(first, 0) + 1
        if first == 11:                                   # scene 2: always outside the scene
            return '[{"first_cue": 99, "last_cue": 99, "kind": "joke"}]'
        if first == 21 and seen[first] == 1:              # scene 3: malformed once, then fine
            return "Sure! Here you go"
        return json.dumps([{"first_cue": first, "last_cue": first, "kind": "joke"}])
    out = run(tmp_path, FakeClient(segment=segment), scenes(60))
    assert out["failed_scenes"] == [2] and out["jokes_found"] == 59
    rows = log_rows(tmp_path)
    scene2 = [r for r in rows if r["pass"] == "segment" and r["unit"] == 2]
    assert [r["attempt"] for r in scene2] == [1, 2] and all(r["status"].startswith("failed") for r in scene2)
    scene3 = [r for r in rows if r["pass"] == "segment" and r["unit"] == 3]
    assert [r["status"] == "ok" for r in scene3] == [False, True]


def test_more_than_two_percent_failed_scenes_stops_the_run(tmp_path):
    def segment(user, n):
        return "not json" if _first(user) in (11, 21) else "[]"
    with pytest.raises(P.RunStopped, match="2 of 60 failed"):
        run(tmp_path, FakeClient(segment=segment), scenes(60))
    one = run(tmp_path / "b", FakeClient(segment=lambda u, n: "x" if _first(u) == 11 else "[]"), scenes(60))
    assert one["failed_scenes"] == [2]                                   # 1 of 60 = 1.7 %: under the limit


def test_failed_jokes_count_against_the_limit_of_pass_two(tmp_path):
    with pytest.raises(P.RunStopped, match=r"pass 2 \(jokes\): 3 of 3"):
        run(tmp_path, FakeClient(code=lambda u, n: '{"target": "x"}'))


def test_api_errors_refusals_and_truncated_replies_are_failed_attempts(tmp_path):
    class Odd:
        def __init__(self, script):
            self.script = list(script)

        def call(self, system, user, max_tokens):
            step = self.script.pop(0)
            if step == "error":
                raise CL.CallFailed("RateLimitError 429")
            return CL.Reply("[]", "m", step, 1, 0)
    with pytest.raises(P.RunStopped, match="1 of 1"):
        run(tmp_path, Odd(["error", "refusal"]), scenes(1))
    assert [r["status"] for r in log_rows(tmp_path)] == ["failed: RateLimitError 429", "failed: stop reason refusal"]
    assert run(tmp_path / "b", Odd(["max_tokens", "end_turn"]), scenes(1))["failed_scenes"] == []


# ---------------------------------------------------------------- the real client, with the SDK mocked

class FakeSDK(types.ModuleType):
    def __init__(self):
        super().__init__("anthropic")
        self.__version__ = "0.0-test"
        self.seen = []
        sdk = self

        class APIError(Exception):
            status_code = 500

        class Messages:
            def create(self, **kw):
                sdk.seen.append(kw)
                if kw["messages"][0]["content"] == "boom":
                    raise APIError(f"echo of the request with {FAKE_KEY}")
                block = types.SimpleNamespace
                return block(content=[block(type="thinking", thinking=""), block(type="text", text="[]")],
                             model="claude-sonnet-5-5-20261001", stop_reason="end_turn",
                             usage=block(input_tokens=12, output_tokens=3))

        class Anthropic:
            def __init__(self, **kw):
                sdk.client_kw = kw
                self.messages = Messages()
        self.APIError, self.Anthropic = APIError, Anthropic


@pytest.fixture
def sdk(monkeypatch, tmp_path):
    fake = FakeSDK()
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.delenv(CL.KEY_NAME, raising=False)
    env = tmp_path / "dot.env"
    env.write_text(f"OTHER=1\nexport {CL.KEY_NAME}='{FAKE_KEY}'\n")
    monkeypatch.setattr(CL.load_env_key, "__defaults__", (env,))
    return fake


def test_the_client_sends_model_temperature_and_returns_text_only(sdk):
    cl = CL.AnthropicClient()
    reply = cl.call("sys", "user text", 100)
    kw = sdk.seen[0]
    assert kw["model"] == "claude-sonnet-5-5" and kw["extra_body"] == {"temperature": 0.0} and kw["system"] == "sys"
    assert kw["max_tokens"] == 100 and kw["messages"] == [{"role": "user", "content": "user text"}]
    assert reply == CL.Reply("[]", "claude-sonnet-5-5-20261001", "end_turn", 12, 3)
    assert cl.sdk_version == "0.0-test"


def test_temperature_none_leaves_the_field_out(sdk):
    CL.AnthropicClient(temperature=None).call("s", "u", 5)
    assert "extra_body" not in sdk.seen[0] and "temperature" not in sdk.seen[0]


def test_the_key_comes_from_env_and_is_never_printed_logged_or_in_errors(sdk, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    cl = CL.AnthropicClient()
    assert "api_key" not in sdk.client_kw                                  # the SDK reads it from the environment
    with pytest.raises(CL.CallFailed) as err:
        cl.call("sys", "boom", 10)
    out = capsys.readouterr()
    for text in (str(err.value), repr(err.value), caplog.text, out.out, out.err):
        assert FAKE_KEY not in text
    assert str(err.value) == "APIError 500" and err.value.__cause__ is None


def test_no_key_anywhere_refuses_to_build_the_client(sdk, tmp_path, monkeypatch):
    empty = tmp_path / "empty.env"
    empty.write_text(f"{CL.KEY_NAME}=\n")
    monkeypatch.setattr(CL.load_env_key, "__defaults__", (empty,))
    with pytest.raises(CL.CallFailed, match="no ANTHROPIC_API_KEY"):
        CL.AnthropicClient()
