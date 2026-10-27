"""The model client and the two passes with a mocked client: settings, caching, retries, the 2 % limit and the key
that is never printed or logged. No real call is made."""
from __future__ import annotations

import json
import logging
import sys
import types
from pathlib import Path

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
    return [S.Scene(k + 1, (S.Cue.secs(10 * k + 1, 30.0 * k, 30.0 * k + 2, (f"invented line {k}a",)),
                            S.Cue.secs(10 * k + 2, 30.0 * k + 3, 30.0 * k + 5, (f"invented line {k}b",))))
            for k in range(n)]


def _first(user):
    line = user.split("Scene to segment")[1].splitlines()[1]
    return int(line.split("]")[0].strip("["))


def jokes(spans):
    return json.dumps({"jokes": [{"first_cue": a, "last_cue": b, "kind": k} for a, b, k in spans]})


class FakeClient:
    """Answers by pass: a segment reply per scene and a code reply per joke, from scripted functions."""

    def __init__(self, segment=None, code=None):
        self.calls = []
        self.segment = segment or (lambda user, n: jokes([(_first(user), _first(user), "joke")]))
        self.code = code or (lambda user, n: '{"target": "group", "group_type": "weight", "group_other": "", '
                                             '"butt": "group"}')

    def call(self, system, user, max_tokens, schema):
        self.calls.append((system, user, max_tokens, schema))
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
    reqs = [json.loads(p.read_text())["request"] for p in cached]
    for req in reqs:
        assert req["model"] == "claude-sonnet-5-5" and req["run"] == 1 and "temperature" not in req
        assert req["thinking"] == {"type": "adaptive"} and req["effort"] == "high"
    assert {json.dumps(r["schema"], sort_keys=True) for r in reqs if r["pass"] == "code"} == {
        json.dumps(K.CODE_SCHEMA, sort_keys=True)}
    assert fake.calls[0][3] == K.SEGMENT_SCHEMA and fake.calls[3][3] == K.CODE_SCHEMA
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
            return jokes([(99, 99, "joke")])
        if first == 21 and seen[first] == 1:              # scene 3: malformed once, then fine
            return "Sure! Here you go"
        return jokes([(first, first, "joke")])
    out = run(tmp_path, FakeClient(segment=segment), scenes(60))
    assert out["failed_scenes"] == [2] and out["jokes_found"] == 59
    rows = log_rows(tmp_path)
    scene2 = [r for r in rows if r["pass"] == "segment" and r["unit"] == 2]
    assert [r["attempt"] for r in scene2] == [1, 2] and all(r["status"].startswith("failed") for r in scene2)
    scene3 = [r for r in rows if r["pass"] == "segment" and r["unit"] == 3]
    assert [r["status"] == "ok" for r in scene3] == [False, True]


def test_more_than_two_percent_failed_scenes_stops_the_run(tmp_path):
    def segment(user, n):
        return "not json" if _first(user) in (11, 21) else jokes([])
    with pytest.raises(P.RunStopped, match="2 of 60 failed"):
        run(tmp_path, FakeClient(segment=segment), scenes(60))
    one = run(tmp_path / "b", FakeClient(segment=lambda u, n: "x" if _first(u) == 11 else jokes([])), scenes(60))
    assert one["failed_scenes"] == [2]                                   # 1 of 60 = 1.7 %: under the limit


def test_failed_jokes_count_against_the_limit_of_pass_two(tmp_path):
    with pytest.raises(P.RunStopped, match=r"pass 2 \(jokes\): 3 of 3"):
        run(tmp_path, FakeClient(code=lambda u, n: '{"target": "x"}'))


def test_api_errors_refusals_and_truncated_replies_are_failed_attempts(tmp_path):
    class Odd:
        def __init__(self, script):
            self.script = list(script)

        def call(self, system, user, max_tokens, schema):
            step = self.script.pop(0)
            if step == "error":
                raise CL.CallFailed("RateLimitError 429")
            return CL.Reply(jokes([]), "m", step, 1, 0)        # valid JSON whatever the stop reason
    with pytest.raises(P.RunStopped, match="1 of 1"):
        run(tmp_path, Odd(["error", "refusal"]), scenes(1))
    assert [r["status"] for r in log_rows(tmp_path)] == ["failed: RateLimitError 429", "failed: stop reason refusal"]
    assert run(tmp_path / "b", Odd(["max_tokens", "end_turn"]), scenes(1))["failed_scenes"] == []
    with pytest.raises(P.RunStopped):
        run(tmp_path / "c", Odd(["max_tokens", "max_tokens"]), scenes(1))
    with pytest.raises(P.RunStopped):
        run(tmp_path / "d", Odd(["stop_sequence", "pause_turn"]), scenes(1))
    assert [r["status"] for r in log_rows(tmp_path / "c")] == ["failed: stop reason max_tokens"] * 2


# ---------------------------------------------------------------- the real client, with the SDK mocked

class FakeSDK(types.ModuleType):
    def __init__(self):
        super().__init__("anthropic")
        self.__version__ = "0.0-test"
        self.seen = []
        sdk = self

        class APIError(Exception):
            status_code = 500

        class Stream:
            def __init__(self, kw):
                self.kw = kw

            def __enter__(self):
                if self.kw["messages"][0]["content"] == "boom":
                    raise APIError(f"echo of the request with {FAKE_KEY}")
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                block = types.SimpleNamespace
                return block(content=[block(type="thinking", thinking=""), block(type="text", text='{"jokes": []}')],
                             model="claude-sonnet-5-5", stop_reason="end_turn",
                             usage=block(input_tokens=12, output_tokens=3))

        class Messages:
            def create(self, **kw):
                raise AssertionError("calls stream: a non-streaming call with this max_tokens is refused by the SDK")

            def stream(self, **kw):
                sdk.seen.append(kw)
                return Stream(kw)

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
    monkeypatch.setattr(C, "ENV_FILE", env)
    return fake


def test_the_client_sends_thinking_effort_and_schema_and_no_sampling_parameter(sdk):
    cl = CL.AnthropicClient()
    reply = cl.call("sys", "user text", C.MAX_TOKENS["code"], K.CODE_SCHEMA)
    kw = sdk.seen[0]
    assert set(kw) == {"model", "max_tokens", "system", "messages", "thinking", "output_config"}
    assert kw["model"] == "claude-sonnet-5-5" and kw["system"] == "sys" and kw["max_tokens"] == 16000
    assert kw["messages"] == [{"role": "user", "content": "user text"}]
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"] == {"effort": "high", "format": {"type": "json_schema", "schema": K.CODE_SCHEMA}}
    assert not {"temperature", "top_p", "top_k", "extra_body", "tool_choice"} & set(kw)
    assert reply == CL.Reply('{"jokes": []}', "claude-sonnet-5-5", "end_turn", 12, 3)
    assert cl.sdk_version == "0.0-test"


def test_the_pinned_settings():
    assert C.MODEL == "claude-sonnet-5-5" and C.SDK_PIN == "anthropic==2.3.0" and not hasattr(C, "TEMPERATURE")
    assert C.THINKING == {"type": "adaptive"} and C.EFFORT == "high"
    assert C.MAX_TOKENS == {"segment": 32000, "code": 16000}


def test_the_key_comes_from_env_and_is_never_printed_logged_or_in_errors(sdk, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    cl = CL.AnthropicClient()
    assert "api_key" not in sdk.client_kw                                  # the SDK reads it from the environment
    with pytest.raises(CL.CallFailed) as err:
        cl.call("sys", "boom", 10, K.CODE_SCHEMA)
    out = capsys.readouterr()
    for text in (str(err.value), repr(err.value), caplog.text, out.out, out.err):
        assert FAKE_KEY not in text
    assert str(err.value) == "APIError 500" and err.value.__cause__ is None


def test_no_key_anywhere_refuses_to_build_the_client(sdk, tmp_path, monkeypatch):
    empty = tmp_path / "empty.env"
    empty.write_text(f"{CL.KEY_NAME}=\n")
    monkeypatch.setattr(C, "ENV_FILE", empty)
    with pytest.raises(CL.CallFailed, match="no ANTHROPIC_API_KEY"):
        CL.AnthropicClient()


def test_cache_writes_are_atomic_and_a_corrupt_file_is_a_miss(tmp_path):
    cache = CL.Cache(tmp_path)
    req = {"system": "s", "user": "u", "attempt": 1}
    cache.put(req, CL.Reply("{}", "m", "end_turn", 1, 1))
    assert cache.get(req) == CL.Reply("{}", "m", "end_turn", 1, 1) and not list(tmp_path.glob("*.tmp"))
    path = tmp_path / f"{CL.Cache.key(req)}.json"
    for broken in ('{"request": {}, "rep', '{"request": {}}', '{"reply": {"text": 1}}', ""):
        path.write_text(broken)
        assert cache.get(req) is None


def test_failed_scenes_and_uncoded_jokes_are_recorded_for_the_analysis(tmp_path):
    seg = {11: "x"}                                                      # scene 2 never parses

    def code(user, n):
        return '{"target": "x"}' if ">> [21]" in user else ('{"target": "genre", "group_type": "", '
                                                             '"group_other": "", "butt": "group"}')
    out = run(tmp_path, FakeClient(segment=lambda u, n: seg.get(_first(u)) or jokes([(_first(u), _first(u) + 1,
                                                                                       "joke")]), code=code),
              scenes(60))
    assert out["failed_scenes"] == [2] and out["failed_scene_cues"] == [11, 12]
    assert out["failed_jokes"] == ["3-1"] and len(out["jokes"]) == 58
    assert {"first_cue": 21, "last_cue": 22, "kind": "joke"} in out["detected_spans"] and len(out["detected_spans"]) == 59


def test_cli_command_isolates_the_call():
    cmd = CL.cli_command("SYSTEM", {"type": "object"})
    assert cmd[:2] == ["claude", "-p"]
    for flag, value in (("--model", C.MODEL), ("--effort", C.EFFORT), ("--system-prompt", "SYSTEM"),
                        ("--output-format", "json"), ("--tools", ""), ("--setting-sources", "")):
        assert cmd[cmd.index(flag) + 1] == value
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence", "--json-schema"):
        assert flag in cmd


def _cli_result(**over):
    res = {"type": "result", "subtype": "success", "is_error": False, "structured_output": {"jokes": []},
           "terminal_reason": "completed", "stop_reason": "tool_use", "num_turns": 2, "permission_denials": [],
           "modelUsage": {C.MODEL: {}}, "usage": {"input_tokens": 2, "cache_creation_input_tokens": 10,
                                                  "cache_read_input_tokens": 3, "output_tokens": 7}}
    res.update(over)
    return json.dumps(res)


def test_parse_cli_result_success():
    r = CL.parse_cli_result(_cli_result())
    assert json.loads(r.text) == {"jokes": []}
    assert (r.model, r.stop_reason, r.input_tokens, r.output_tokens) == (C.MODEL, "end_turn", 15, 7)


@pytest.mark.parametrize("raw", [
    "not json",
    _cli_result(is_error=True),
    _cli_result(subtype="error_max_turns"),
    _cli_result(structured_output=None),
    _cli_result(modelUsage={"claude-haiku-4-5-20251001": {}}),
    _cli_result(modelUsage={C.MODEL: {}, "claude-haiku-4-5-20251001": {}}),
    _cli_result(stop_reason="max_tokens"),
    _cli_result(stop_reason="refusal"),
    _cli_result(terminal_reason="max_turns"),
    _cli_result(num_turns=1),
    _cli_result(num_turns=4),
    _cli_result(permission_denials=[{"tool": "x"}]),
    _cli_result(structured_output=["not", "a", "dict"]),
    "[1, 2]",
])
def test_parse_cli_result_failures(raw):
    with pytest.raises(CL.CallFailed):
        CL.parse_cli_result(raw)


def test_three_turns_are_accepted_and_the_token_limit_is_checked():
    assert CL.parse_cli_result(_cli_result(num_turns=3)).stop_reason == "end_turn"
    assert CL.parse_cli_result(_cli_result(), max_tokens=8).output_tokens == 7
    with pytest.raises(CL.CallFailed, match="max_tokens"):
        CL.parse_cli_result(_cli_result(), max_tokens=7)
    two = _cli_result(usage={"output_tokens": 5, "iterations": [{"output_tokens": 5}, {"output_tokens": 5}]})
    assert CL.parse_cli_result(two).output_tokens == 10
    with pytest.raises(CL.CallFailed, match="max_tokens"):
        CL.parse_cli_result(two, max_tokens=10)


def test_a_usage_limit_is_not_a_failed_attempt():
    with pytest.raises(CL.UsageLimit):
        CL.parse_cli_result(_cli_result(is_error=True, subtype="error", api_error_status=429))


class _Proc:
    def __init__(self, stdout, returncode=0):
        self.stdout, self.returncode, self.stderr = stdout, returncode, ""


def _cli_client(monkeypatch, replies, seen):
    def fake_run(cmd, **kw):
        seen.append((cmd, kw))
        if cmd[:2] == ["claude", "--version"]:
            return _Proc("9.9.9 (Claude Code)")
        reply = replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply
    monkeypatch.setattr(CL.subprocess, "run", fake_run)
    monkeypatch.setenv(CL.KEY_NAME, "sk-secret-do-not-pass")
    return CL.ClaudeCliClient(sleep=lambda s: seen.append(("slept", s)))


def test_the_cli_call_is_isolated(monkeypatch):
    seen = []
    cl = _cli_client(monkeypatch, [_Proc(_cli_result())], seen)
    assert cl.sdk_version == "claude-cli 9.9.9 (Claude Code)"
    r = cl.call("SYSTEM", "USER ♪ text", 123, {"type": "object"})
    assert r.stop_reason == "end_turn"
    cmd, kw = seen[-1]
    assert cmd == CL.cli_command("SYSTEM", {"type": "object"}) and "USER ♪ text" not in cmd
    assert kw["input"] == "USER ♪ text" and kw["encoding"] == "utf-8"
    assert Path(kw["cwd"]).name.startswith("call-")
    assert CL.KEY_NAME not in kw["env"] and kw["env"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "123"
    assert all(kw["env"][k] == v for k, v in CL.CLI_ENV.items())


@pytest.mark.parametrize("reply, match", [
    (CL.subprocess.TimeoutExpired(["claude", "SYSTEM"], 5), "timed out"),
    (OSError("boom"), "could not run"),
    (_Proc("", 1), "exited with 1"),
    (_Proc(_cli_result(), 1), "exited with 1"),
])
def test_cli_call_failures_echo_no_prompt(monkeypatch, reply, match):
    cl = _cli_client(monkeypatch, [reply], [])
    with pytest.raises(CL.CallFailed, match=match) as err:
        cl.call("SYSTEM", "USER", 10, {"type": "object"})
    assert "SYSTEM" not in str(err.value) and "USER" not in str(err.value)


def test_a_usage_limit_is_waited_out_then_stops_the_run(monkeypatch):
    seen = []
    limit = _Proc(_cli_result(is_error=True, subtype="error", api_error_status=429), 1)
    cl = _cli_client(monkeypatch, [limit, _Proc(_cli_result())], seen)
    assert cl.call("S", "U", 10, {}).stop_reason == "end_turn"
    assert ("slept", 60) in seen
    monkeypatch.setattr(C, "LIMIT_WAIT_S", 100)
    cl = _cli_client(monkeypatch, [limit] * 5, [])
    with pytest.raises(SystemExit, match="usage limit"):
        cl.call("S", "U", 10, {})


def test_a_missing_cli_is_a_failed_client(monkeypatch):
    def fake_run(cmd, **kw):
        raise OSError("no claude")
    monkeypatch.setattr(CL.subprocess, "run", fake_run)
    with pytest.raises(CL.CallFailed, match="not available"):
        CL.ClaudeCliClient()
