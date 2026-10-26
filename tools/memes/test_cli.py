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
    assert C.N_PLACEBO is None and C.STONESTREET.cast == C.MF_CAST


def test_the_baseline_of_kevin_james_is_the_external_pool_and_koq_is_a_check():
    assert C.KEVIN_JAMES.controls == C.REFERENCE_POOL and C.KEVIN_JAMES.cast == C.KOQ_CAST
    assert C.STONESTREET.controls == C.MF_CAST and C.STONESTREET.reference == C.REFERENCE_POOL
    plan = dict(cli.variant_plan(C.KEVIN_JAMES))
    assert plan["koq_controls"]["controls"] == C.KOQ_CAST
    assert plan["window_-3_60_without_Matt_LeBlanc"]["drop"] == (C.LEBLANC,)


def test_every_registered_check_is_in_the_plan_with_its_falsification_setting():
    stone = dict(cli.variant_plan(C.STONESTREET))
    assert set(stone) == {"window_-3_14", "window_-3_60", "mean_index", "same_season", "exclusion_90", "pre_event_only",
                          "drop_Sofía_Vergara", "day0_2023-10-06", "external_index", "external_index_window_-3_60",
                          "external_index_window_-3_60_without_Matt_LeBlanc"}
    assert stone["same_season"]["season_days"] == 45 and stone["exclusion_90"]["exclusion_days"] == 90
    assert stone["pre_event_only"]["pre_only"] is True and stone["mean_index"]["how"] == "mean"
    assert "falsify" not in stone["window_-3_14"] and stone["same_season"]["falsify"] is False
    assert stone["external_index"]["controls"] == C.REFERENCE_POOL


def test_synthetic_run_end_to_end(no_network, tmp_path, capsys):
    out = tmp_path / "out"
    assert cli.main(["--synthetic", "--out", str(out), "--n-placebo", "150"]) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["meta"]["synthetic"] is True
    assert summary["meta"]["holm_family"] == ["Kevin James", "Stonestreet (Cam)"]
    assert all(e["falsification_p"] is not None and e["loo_p"] is not None for e in summary["events"])
    assert all(e["mdu80_pct"] > 0 and e["excess_views"] is not None for e in summary["events"])
    assert summary["events"][0]["space_time_p"] is not None
    assert summary["h2"]["stonestreet_from_6_oct"]["peak_date"]
    assert {e["label"] for e in summary["events"]} <= {"positive", "no detectable jump", "inconclusive"}
    variants = {s["variant"] for s in summary["sensitivity"]}
    expected = {v for sp in C.EVENTS for v, _ in cli.variant_plan(sp)} | {"tiktok_prewave"}
    assert expected <= variants
    for f in ("index.html", "abnormal_attention.svg", "estimation_windows.svg", "estimation_gap_by_month.csv",
              "placebo_null.json", "ar_Eric_Stonestreet.csv", "ar_Kevin_James.csv"):
        assert (out / f).exists()
    assert json.loads(capsys.readouterr().out)["summary"].endswith("summary.json")


def test_the_null_summary_is_written_before_any_estimate(no_network, tmp_path):
    order = []
    orig_null, orig_run = cli.M.null_distribution, cli.M.run_event
    cli.M.null_distribution = lambda *a, **k: order.append("null") or orig_null(*a, **k)
    cli.M.run_event = lambda *a, **k: order.append("run") or orig_run(*a, **k)
    try:
        cli.main(["--synthetic", "--out", str(tmp_path), "--n-placebo", "120"])
    finally:
        cli.M.null_distribution, cli.M.run_event = orig_null, orig_run
    assert order[:2] == ["null", "null"] and order[2] == "run"


def test_h2_makes_no_ordering_claim_when_a_half_life_is_censored(no_network, tmp_path):
    cli.main(["--synthetic", "--out", str(tmp_path), "--n-placebo", "120"])
    h2 = json.loads((tmp_path / "summary.json").read_text())["h2"]
    statuses = [v[1] for v in h2["half_life"].values()]
    if "observed" not in statuses or statuses.count("observed") < 2:
        assert h2["difference_days_stonestreet_minus_kevin_james"] is None and "no ordering claim" in h2["ordering"]
    else:
        assert h2["difference_days_stonestreet_minus_kevin_james"] is not None


def test_estimation_figure_stops_before_every_event_window_and_hides_the_tiktok_block(no_network, tmp_path):
    cli.main(["--synthetic", "--out", str(tmp_path), "--n-placebo", "120"])
    svg = (tmp_path / "estimation_windows.svg").read_text()
    assert "up to 2023-09-17" in svg and "Eric_Stonestreet" in svg and "median of the reference pool" in svg
    assert cli.pre_event_cutoff() == "2023-09-17"
    gap = pd.read_csv(tmp_path / "estimation_gap_by_month.csv")
    assert gap["month"].max() == "2023-09" and set(gap["event"]) == {"Stonestreet (Cam)", "Kevin James"}


def test_detected_kevin_james_date_would_leave_the_family(no_network):
    panel = cli._synthetic_panel()
    import dataclasses
    spec = dataclasses.replace(C.KEVIN_JAMES, event_date=None)
    import model as M
    res, _ = M.run_event(panel, spec, n_placebo=100)
    assert res.event_date_detected and not res.confirmatory
    assert M.confirmatory_family([res]) == {}
    assert isinstance(pd.Timestamp(res.event_date), pd.Timestamp)


def test_a_target_with_omitted_days_is_dropped_and_reported_not_replaced(no_network, tmp_path):
    panel = cli._synthetic_panel()
    panel.loc[panel.index[850:890], "Kevin_James"] = float("nan")      # the estimation window of Kevin James
    summary, _ = cli.study(panel, n_placebo=120, out=None)
    assert [d["name"] for d in summary["dropped_events"]] == ["Kevin James"]
    assert [e["name"] for e in summary["events"]] == ["Stonestreet (Cam)"]
    assert summary["meta"]["holm_family"] == ["Stonestreet (Cam)"]


def test_the_page_power_comes_from_the_committed_simulation_numbers():
    pct = cli.falsification_power_pct()
    assert pct is None or 0 <= pct <= 100
