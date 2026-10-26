"""CLI tests: the blinding refusal, the two stages and the gate between them, the synthetic dry run, the Holm family
wiring. No network."""
from __future__ import annotations

import hashlib
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
    for argv in (["--null-stage"], ["--panel-csv", str(csv)]):
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
    assert all(e["mdu80_q975_pct"] > 0 and e["excess_views"] is not None for e in summary["events"])
    assert summary["events"][0]["space_time_p"] is not None
    assert summary["h2"]["stonestreet_from_6_oct"]["peak_date"]
    assert {e["label"] for e in summary["events"]} <= set(cli.M.LABELS)
    variants = {s["variant"] for s in summary["sensitivity"]}
    expected = {v for sp in C.EVENTS for v, _ in cli.variant_plan(sp)} | {"tiktok_prewave"}
    assert expected <= variants
    for f in ("index.html", "abnormal_attention.svg", "estimation_windows.svg", "estimation_gap_by_month.csv",
              "placebo_null.json", "ar_Eric_Stonestreet.csv", "ar_Kevin_James.csv"):
        assert (out / f).exists()
    assert json.loads(capsys.readouterr().out)["summary"].endswith("summary.json")


def test_the_label_uses_the_null_files_minimum_detectable_uplift(no_network, tmp_path):
    cli.main(["--synthetic", "--out", str(tmp_path), "--n-placebo", "150"])
    summary = json.loads((tmp_path / "summary.json").read_text())
    for e in summary["events"]:
        stage1 = summary["meta"]["null"]["events"][e["name"]]["windows"]["window_-3_30"]["mdu80_q975_pct"]
        assert e["mdu80_q975_pct"] == pytest.approx(stage1)
        if e["label"] in ("no detectable jump", "uninformative"):
            assert (e["label"] == "uninformative") == (stage1 > 10.0)


def test_the_null_stage_computes_no_event_and_reports_both_windows_and_the_kevin_baseline(no_network):
    seen = []
    orig = cli.M.run_event
    cli.M.run_event = lambda *a, **k: seen.append("run") or orig(*a, **k)
    try:
        payload = cli.null_payload(cli._synthetic_panel(), None)
    finally:
        cli.M.run_event = orig
    assert seen == []                                                  # no AR or CAR at any event
    assert payload["pool_dropped"] == [] and payload["uninformative_threshold_pct"] == 10.0
    kevin = payload["events"]["Kevin James"]
    assert kevin["baseline"]["chosen"] in ("pool", "pool+second") and {"pool", "pool+second"} <= set(kevin["baseline"])
    for ev in payload["events"].values():
        w30, w14 = ev["windows"]["window_-3_30"], ev["windows"]["window_-3_14"]
        assert w30["mdu80_q975_pct"] > 0 and w14["mdu80_q975_pct"] > 0 and w14["n_dates"] > w30["n_dates"]


def test_the_null_summary_is_written_before_any_estimate(no_network, tmp_path):
    order = []
    orig_null, orig_run = cli.M.null_distribution, cli.M.run_event
    cli.M.null_distribution = lambda *a, **k: order.append("null") or orig_null(*a, **k)
    cli.M.run_event = lambda *a, **k: order.append("run") or orig_run(*a, **k)
    try:
        cli.main(["--synthetic", "--out", str(tmp_path), "--n-placebo", "120"])
    finally:
        cli.M.null_distribution, cli.M.run_event = orig_null, orig_run
    assert "run" in order and order.index("run") > max(i for i, o in enumerate(order) if o == "null")


# ---------------------------------------------------------------- the gate between the stages

@pytest.fixture
def staged(tmp_path, monkeypatch):
    """A stage 1 run on a made-up panel, written to a temporary docs folder, with git stubbed."""
    docs = tmp_path / "docs"
    docs.mkdir()
    for name, fn in (("NULL_JSON", "null.json"), ("NULL_SHA", "files.sha256"), ("NULL_SVG", "w.svg"), ("NULL_GAP", "g.csv")):
        monkeypatch.setattr(C, name, docs / fn)
    panel = cli._synthetic_panel()
    path = tmp_path / "pageviews.csv"
    F.save_panel(panel, path)
    state = {"tags": "memes-null\n", "dirty": ""}
    monkeypatch.setattr(cli, "_git", lambda *a: state["dirty"] if a[0] == "status" else state["tags"])
    cli.run_null_stage(panel, path, 150)
    return path, state, panel


def test_stage_two_runs_only_when_every_condition_holds(staged):
    path, _, _ = staged
    assert cli.verify_null_stage(path)["stage"].startswith("null")
    lines = C.NULL_SHA.read_text().splitlines()
    assert len(lines) == 4 and lines[3].endswith("(the panel, gitignored)")


def test_stage_two_refuses_without_the_tag_on_head(staged):
    path, state, _ = staged
    state["tags"] = "something-else\n"
    with pytest.raises(SystemExit, match="memes-null is not on HEAD"):
        cli.verify_null_stage(path)


def test_stage_two_refuses_if_the_null_file_was_changed_after_stage_one(staged):
    path, _, _ = staged
    C.NULL_JSON.write_text(C.NULL_JSON.read_text().replace('"seed": 42', '"seed": 43'))
    with pytest.raises(SystemExit, match="does not match the hash"):
        cli.verify_null_stage(path)


def test_stage_two_refuses_a_panel_other_than_the_one_of_stage_one(staged):
    path, _, panel = staged
    other = panel.copy()
    other.iloc[10, 0] += 1.0
    F.save_panel(other, path)
    with pytest.raises(SystemExit, match="panel file does not match"):
        cli.verify_null_stage(path)


def test_stage_two_refuses_uncommitted_stage_one_files_and_missing_ones(staged):
    path, state, _ = staged
    state["dirty"] = " M docs/research/memes-placebo-null.json"
    with pytest.raises(SystemExit, match="not committed"):
        cli.verify_null_stage(path)
    state["dirty"] = ""
    C.NULL_SVG.unlink()
    with pytest.raises(SystemExit, match="stage 1 has not been run"):
        cli.verify_null_stage(path)


def test_the_sha_file_hashes_what_was_written(staged):
    lines = {ln.split()[1]: ln.split()[0] for ln in C.NULL_SHA.read_text().splitlines()}
    assert lines["null.json"] == hashlib.sha256(C.NULL_JSON.read_bytes()).hexdigest()
    assert lines["w.svg"] == hashlib.sha256(C.NULL_SVG.read_bytes()).hexdigest()


def test_stage_two_estimates_on_the_checked_panel_and_labels_from_the_null_file(staged):
    path, _, panel = staged
    null = cli.verify_null_stage(path)
    summary, _ = cli.study(panel, null, 150)
    assert [e["name"] for e in summary["events"]] == ["Stonestreet (Cam)", "Kevin James"]
    assert summary["events"][1]["second_regressor"] == null["events"]["Kevin James"]["baseline"]["second_regressor"]
    panel2 = panel.copy()
    panel2.loc[panel2.index[50], "Kat_Dennings"] = float("nan")          # a pool actor gains a hole after stage 1
    with pytest.raises(SystemExit, match="pool actors dropped now differ"):
        cli.study(panel2, null, 150)


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


def test_a_target_with_omitted_days_is_dropped_and_reported_not_replaced(no_network):
    panel = cli._synthetic_panel()
    panel.loc[panel.index[850:890], "Kevin_James"] = float("nan")      # the estimation window of Kevin James
    null = cli.null_payload(panel, 120)
    assert "dropped_event" in null["events"]["Kevin James"]
    summary, _ = cli.study(panel, null, 120)
    assert [d["name"] for d in summary["dropped_events"]] == ["Kevin James"]
    assert [e["name"] for e in summary["events"]] == ["Stonestreet (Cam)"]
    assert summary["meta"]["holm_family"] == ["Stonestreet (Cam)"]


def test_the_page_power_comes_from_the_committed_runs_for_each_event():
    power = cli.falsification_power_pct()
    assert all(0 <= v <= 100 for v in power.values())


def test_kevin_jamess_later_waves_and_second_regressor_are_registered():
    assert C.KEVIN_JAMES.placebo_blocked == (("2024-01-01", "2024-02-29"),)
    assert C.KEVIN_JAMES.second_regressor == "Victor_Williams" and C.STONESTREET.second_regressor is None
    assert C.STONESTREET.placebo_blocked == () and C.NULL_TAG == "memes-null"
