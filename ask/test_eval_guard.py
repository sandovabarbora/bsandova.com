"""Tests for the weekly-evaluation guard, on made-up runs only.

    uv run --with pytest pytest -q ask/test_eval_guard.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("eval_guard", Path(__file__).resolve().parent / "eval_guard.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

GOOD = {"date": "2026-09-22", "n": 4, "correct": 4, "by_kind": {"number": {"n": 4, "ok": 4}}}


def _rows(errors: int, n: int = 4) -> list[dict]:
    return [{"q": f"q{i}", "answer": "", "error": "HTTP Error 502: Bad Gateway", "ok": False} if i < errors
            else {"q": f"q{i}", "answer": "6", "ok": True} for i in range(n)]


def _setup(tmp_path: Path, errors: int) -> tuple[Path, Path]:
    ask, run = tmp_path / "ask", tmp_path / "run"
    ask.mkdir(); run.mkdir()
    (ask / "eval.json").write_text(json.dumps({"summary": GOOD, "rows": _rows(0)}))
    (ask / "eval-history.json").write_text(json.dumps([GOOD]))
    new = {"date": "2026-10-05", "n": 4, "correct": 4 - errors, "by_kind": {"number": {"n": 4, "ok": 4 - errors}}}
    (run / "eval.json").write_text(json.dumps({"summary": new, "rows": _rows(errors)}))
    (run / "eval-history.json").write_text(json.dumps([GOOD, new]))
    return run, ask


def test_all_failed_requests_keep_the_last_good_run_and_fail(tmp_path):
    run, ask = _setup(tmp_path, errors=4)
    assert g.publish(run, ask) == 1
    assert json.loads((ask / "eval.json").read_text())["summary"]["date"] == "2026-09-22"
    hist = json.loads((ask / "eval-history.json").read_text())
    assert [h["date"] for h in hist] == ["2026-09-22", "2026-10-05"]
    assert hist[-1]["failed"] is True and hist[-1]["failed_requests"] == 4


def test_a_run_that_reached_the_agent_is_published(tmp_path):
    run, ask = _setup(tmp_path, errors=1)  # one of four is at the 25 % limit, not over it
    assert g.publish(run, ask) == 0
    assert json.loads((ask / "eval.json").read_text())["summary"]["date"] == "2026-10-05"
    assert not any(h.get("failed") for h in json.loads((ask / "eval-history.json").read_text()))


def test_failed_run_never_replaces_a_good_run_of_the_same_date(tmp_path):
    run, ask = _setup(tmp_path, errors=4)
    good_same_day = {**GOOD, "date": "2026-10-05"}
    (ask / "eval-history.json").write_text(json.dumps([GOOD, good_same_day]))
    assert g.publish(run, ask) == 1
    hist = json.loads((ask / "eval-history.json").read_text())
    assert hist == [GOOD, good_same_day]


def test_empty_run_is_failed():
    assert g.is_failed_run([])
