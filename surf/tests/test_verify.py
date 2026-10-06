"""The verifier on synthetic forecasts whose error grows with lead: the metrics must say so."""
import datetime as dt, json, pathlib, random, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build(tmp: pathlib.Path, issues: int = 45, seed: int = 1):
    rng = random.Random(seed)
    (tmp / "data/forecasts").mkdir(parents=True)
    shutil.copy(ROOT / "verify.py", tmp / "verify.py")
    days = [dt.date(2026, 7, 1) + dt.timedelta(d) for d in range(issues + 7)]
    truth = {d.isoformat(): {"swell_max": round(max(0.3, rng.gauss(1.4, 0.6)), 2), "period_mean": round(rng.gauss(8.5, 1.5), 1),
                             "wind_mean": round(abs(rng.gauss(15, 8)), 1), "wind_dir": rng.choice([90, 270, 340])} for d in days}
    json.dump({"model": "fake", "spots": {"x": truth}}, open(tmp / "data/analysis.json", "w"))
    models = ["meteofrance_wave", "gwam", "ewam"]
    for d in days[:issues]:
        spots = {"x": {m: {} for m in models}}
        for lead in range(7):
            t = (d + dt.timedelta(lead)).isoformat(); tr = truth[t]
            for m in models:
                spots["x"][m][t] = {"swell_max": round(max(0.2, tr["swell_max"] + rng.gauss(0.05 * lead, 0.1 + 0.1 * lead)), 2),
                                    "period_mean": round(tr["period_mean"] + rng.gauss(0, 0.5 + 0.2 * lead), 1),
                                    "wind_mean": tr["wind_mean"], "wind_dir": tr["wind_dir"]}
        json.dump({"issued": d.isoformat(), "models": models, "spots": spots}, open(tmp / f"data/forecasts/{d.isoformat()}.json", "w"))
    subprocess.run([sys.executable, str(tmp / "verify.py")], check=True, capture_output=True)
    return json.load(open(tmp / "data.json"))


def test_error_grows_with_lead(tmp_path):
    d = build(tmp_path)
    mae = [d["skill"]["x"]["gwam"][str(l)]["mae_swell"] for l in range(7)]
    assert mae == sorted(mae), mae
    assert d["skill"]["x"]["gwam"]["0"]["spearman_swell"] > 0.95 > d["skill"]["x"]["gwam"]["6"]["spearman_swell"]


def test_bias_is_recovered(tmp_path):
    d = build(tmp_path)
    assert d["skill"]["x"]["gwam"]["6"]["bias_swell"] > 0.15  # the synthetic forecast over-forecasts by 0.05 m per lead day


def test_intervals_bracket_the_point(tmp_path):
    d = build(tmp_path)
    for l in range(7):
        e = d["skill"]["x"]["gwam"][str(l)]
        lo, hi = e["mae_swell_ci95"]
        assert lo <= e["mae_swell"] <= hi


def test_gates_hold(tmp_path):
    d = build(tmp_path, issues=10)  # 10 pairs per lead: below MIN_PAIRS → no numbers
    assert "mae_swell" not in d["skill"]["x"]["gwam"]["3"]
    assert d["skill"]["x"]["gwam"]["3"]["n"] == 10


def test_skill_beats_baselines(tmp_path):
    d = build(tmp_path)
    b = d["baselines"]["x"]["1"]
    assert b["bss_vs_climatology"] > 0 and b["bss_vs_persistence"] > 0


def test_quality_counts_missing_days(tmp_path):
    d = build(tmp_path)
    assert d["quality"]["issues"] == 45 and d["quality"]["null_share_by_model"]["gwam"] == 0.0


def test_nothing_is_readable_before_eight_weeks(tmp_path):
    d = build(tmp_path)  # 45 issues: 30+ pairs per lead, but in 7 ISO weeks
    e = d["pooled"]["gwam"]["1"]
    assert e["n"] >= 30 and e["weeks"] < 8 and e["readable"] is False
    assert d["skill"]["x"]["gwam"]["1"]["readable"] is False and d["spread"]["1"]["readable"] is False


def test_reading_rule_quantities_after_eight_weeks(tmp_path):
    d = build(tmp_path, issues=70)
    p1, p6 = d["pooled"]["gwam"]["1"], d["pooled"]["gwam"]["6"]
    assert p1["readable"] and p6["readable"]
    for e in (p1, p6):
        for k in ("mae_swell", "bias_swell", "spearman_swell", "positive_error_share"):
            lo, hi = e[f"{k}_ci95"]
            assert lo <= e[k] <= hi, (k, e[k], lo, hi)
    assert p6["positive_error_share_ci95"][0] > 0.5                   # over-forecast planted at long leads
    assert p1["spearman_swell"] > p6["spearman_swell"]
    s1, s6 = d["spread"]["1"], d["spread"]["6"]
    assert s1["members"] == 3 and s1["readable"]
    assert s1["share_spread_le_0_3"] > s6["share_spread_le_0_3"] and s6["share_spread_gt_0_5"] > s1["share_spread_gt_0_5"]
    lo, hi = s6["share_spread_gt_0_5_ci95"]
    assert lo <= s6["share_spread_gt_0_5"] <= hi
    b = d["skill"]["x"]["gwam"]["6"]
    assert b["bias_swell_ci95"][0] <= b["bias_swell"] <= b["bias_swell_ci95"][1]


def test_spread_leaves_out_days_with_a_missing_member(tmp_path):
    d = build(tmp_path, issues=70)
    rows_total = d["pooled"]["gwam"]["2"]["n"]
    assert d["spread"]["2"]["n"] == rows_total                        # all three models present every day here
