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
