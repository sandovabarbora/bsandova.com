"""CLI tests: the blinding refusal, the synthetic dry run end to end, and the Holm family wiring. No network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cli
import config as C
import fetch as F


@pytest.fixture
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(F.urllib.request, "urlopen", boom)


def test_real_data_needs_unblind_and_touches_nothing_without_it(no_network, tmp_path, capsys):
    csv = tmp_path / "panel.csv"
    csv.write_text("date,A\n2023-01-01,1\n")
    for argv in (["--download"], ["--panel-csv", str(csv)]):
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        assert "--unblind" in str(e.value)
    assert not (tmp_path / "out").exists()


def test_one_source_must_be_chosen():
    with pytest.raises(SystemExit):
        cli.main([])


def test_config_holds_the_registered_events_and_no_blocked_redirect():
    assert [e.event_date for e in C.EVENTS] == ["2023-09-27", "2023-09-21"]
    assert C.SENSITIVITY_DAY0 == {"Stonestreet (Cam)": "2023-10-06"} and "Rico_Rodriguez_(actor)" in C.MF_CAST
    assert "Gary_Valentine" not in C.ARTICLES and len(C.MF_CAST) == 9
    assert C.STONESTREET.blocked == (("2023-06-06", "2023-07-13"),)
    assert all(e.source_note for e in (*C.EVENTS, *C.SENSITIVITY_EVENTS))


def test_synthetic_run_end_to_end(no_network, tmp_path, capsys):
    out = tmp_path / "out"
    assert cli.main(["--synthetic", "--out", str(out), "--n-placebo", "100"]) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["meta"]["synthetic"] is True
    assert summary["meta"]["holm_family"] == ["Kevin James", "Stonestreet (Cam)"]
    assert all(e["falsification_p"] is not None and e["loo_p"] is not None for e in summary["events"])
    assert summary["h2"]["stonestreet_from_6_oct"]["peak_date"]
    assert {e["label"] for e in summary["events"]} <= {"positive", "no detectable jump", "inconclusive"}
    variants = {s["variant"] for s in summary["sensitivity"]}
    assert {"window_-3_14", "window_-3_60", "mean_index", "drop_Sofía_Vergara", "tiktok_prewave", "external_index",
            "day0_2023-10-06"} <= variants
    for f in ("index.html", "abnormal_attention.svg", "estimation_windows.svg", "ar_Eric_Stonestreet.csv", "ar_Kevin_James.csv"):
        assert (out / f).exists()
    assert json.loads(capsys.readouterr().out)["summary"].endswith("summary.json")


def test_estimation_figure_shows_no_event_window_days(no_network, tmp_path):
    cli.main(["--synthetic", "--out", str(tmp_path), "--n-placebo", "100"])
    svg = (tmp_path / "estimation_windows.svg").read_text()
    assert "up to 2023-09-23" in svg and "up to 2023-09-17" in svg


def test_detected_kevin_james_date_would_leave_the_family(no_network):
    panel = cli._synthetic_panel()
    import dataclasses
    spec = dataclasses.replace(C.KEVIN_JAMES, event_date=None)
    import model as M
    res, _ = M.run_event(panel, spec, n_placebo=100)
    assert res.event_date_detected and not res.confirmatory
    assert M.confirmatory_family([res]) == {}
    assert isinstance(pd.Timestamp(res.event_date), pd.Timestamp)


def test_panel_with_many_zero_days_stops_the_run():
    panel = cli._synthetic_panel()
    assert cli.screen_panel(panel)["Eric_Stonestreet"] == 0
    panel.loc[panel.index[:30], "Julie_Bowen"] = 0.0
    with pytest.raises(SystemExit, match="Julie_Bowen"):
        cli.screen_panel(panel)
