"""hlidac.py against mocked responses only: no request leaves the machine.

    uv run --with pytest==9.1.1 pytest -q tools/procurement/test_hlidac.py
"""
from __future__ import annotations

import io
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hlidac  # noqa: E402

SECRET = "tok-not-a-real-token-123"


def test_token_comes_from_the_environment_or_the_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv(hlidac.TOKEN_VAR, raising=False)
    assert hlidac.load_token(tmp_path / "missing.env") is None
    env = tmp_path / ".env"
    env.write_text(f"OTHER=x\n{hlidac.TOKEN_VAR}=\"{SECRET}\"\n")
    assert hlidac.load_token(env) == SECRET
    monkeypatch.setenv(hlidac.TOKEN_VAR, SECRET + "-env")
    assert hlidac.load_token(env) == SECRET + "-env"


def test_requests_are_polite_and_carry_the_token_only_in_a_header():
    req = hlidac.request("123", SECRET)
    assert req.get_header("User-agent") == "bsandova.com research" and "@" not in req.get_header("User-agent")
    assert req.get_header("Authorization") == f"Token {SECRET}"
    assert SECRET not in req.full_url and req.full_url.endswith("/smlouvy/123")


def test_classification_parsing():
    assert hlidac.works_from({"Classification": {"Types": [{"TypeValue": "stav_silnice"}]}}) is True
    assert hlidac.works_from({"Classification": {"Types": [{"TypeValue": "it_sw"}]}}) is False
    assert hlidac.works_from({"Classification": {"Types": []}}) is None
    assert hlidac.works_from({}) is None


def test_classify_pauses_counts_and_never_echoes_the_token(capsys):
    responses = {"1": {"Classification": {"Types": [{"TypeValue": "stav_budovy"}]}}, "2": {}}
    seen, slept = [], []

    def fake_fetch(req):
        seen.append(req)
        cid = req.full_url.rsplit("/", 1)[1]
        if cid == "3":
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(b""))
        return responses[cid]

    types, tally = hlidac.classify(["1", "2", "3"], SECRET, fetch=fake_fetch, sleep=slept.append)
    assert types == {"1": True, "2": None, "3": None}
    assert tally == {"classified": 1, "unclassified": 1, "failed": 1, "HTTP 429": 1}
    assert slept == [hlidac.PAUSE_S, hlidac.PAUSE_S] and len(seen) == 3
    assert SECRET not in str(types) + str(tally) + capsys.readouterr().out


def test_without_a_token_the_classification_is_skipped_and_says_so(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv(hlidac.TOKEN_VAR, raising=False)
    monkeypatch.setattr(hlidac, "ROOT", tmp_path)
    monkeypatch.setattr(hlidac, "load_token", lambda env_file=tmp_path / ".env": None)

    def no_network(*a, **k):
        raise AssertionError("no request may be made without a token")

    monkeypatch.setattr(hlidac.urllib.request, "urlopen", no_network)
    hlidac.main([])
    assert "skipped" in capsys.readouterr().out
