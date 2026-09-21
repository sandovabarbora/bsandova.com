"""The verifier must recover what was planted: error growing with lead, a warm bias, rain skill
above climatology, the 14-pair gate, and the quality counts matching the files."""

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pytest

import weather.verify as V
from weather.collect import windows


def build_world(tmp: Path, n_issues=45, seed=3):
    rng = random.Random(seed)
    start = date(2026, 6, 1)
    stations = ["ruzyne", "klementinum"]
    models = ["best_match", "icon_seamless"]
    # truth: a smooth seasonal tmax + noise, rain on ~30 % of days
    truth = {}
    for i in range(n_issues + 8):
        d = start + timedelta(days=i)
        tmax = 22 + 4 * ((i % 10) / 10) + rng.gauss(0, 1.5)
        truth[d.isoformat()] = {"tmax": round(tmax, 1), "tmin": round(tmax - 9 + rng.gauss(0, 1), 1),
                                "precip": round(rng.choice([0, 0, 0, 0, 0, 0, 0, 2.5, 6.0, 12.0]), 1)}
    (tmp / "forecasts").mkdir(parents=True)
    for i in range(n_issues):
        issue = start + timedelta(days=i)
        fc = {"issued": issue.isoformat(), "models": models, "stations": {}}
        for s in stations:
            fc["stations"][s] = {}
            for m in models:
                days = {}
                for lead in range(7):
                    t = (issue + timedelta(days=lead)).isoformat()
                    o = truth[t]
                    err = rng.gauss(0, 0.6 + 0.5 * lead)          # error grows with lead
                    days[t] = {"tmax": round(o["tmax"] + 1.0 + err, 1),  # planted +1.0 °C warm bias
                               "tmin": round(o["tmin"] + err / 2, 1),
                               "precip": round(o["precip"] if rng.random() < 0.85 - 0.06 * lead else rng.choice([0.0, 4.0]), 1)}
                fc["stations"][s][m] = days
        (tmp / "forecasts" / f"{issue.isoformat()}.json").write_text(json.dumps(fc))
    obs = {"stations": {s: {d: v for d, v in truth.items() if d < (start + timedelta(days=n_issues)).isoformat()} for s in stations}}
    (tmp / "observations.json").write_text(json.dumps(obs))
    clim = {"stations": {s: {str(doy): {"tmax_mean": 24.0, "tmax_sd": 4, "tmin_mean": 15, "tmin_sd": 3, "rain1_freq": 0.3, "rain01_freq": 0.45, "n": 900} for doy in range(1, 367)} for s in stations}}
    (tmp / "climatology.json").write_text(json.dumps(clim))
    return truth


@pytest.fixture
def world(tmp_path, monkeypatch):
    build_world(tmp_path)
    monkeypatch.setattr(V, "DATA", tmp_path)
    monkeypatch.setattr(V, "OUT", tmp_path / "data.json")
    V.main()
    return json.loads((tmp_path / "data.json").read_text())


def test_error_grows_with_lead_and_bias_is_recovered(world):
    sk = world["skill"]["ruzyne"]["best_match"]
    maes = [sk[str(lead)]["mae_tmax"] for lead in range(1, 7)]
    assert all(b >= a - 0.15 for a, b in zip(maes, maes[1:])), maes   # monotone up to noise
    assert 0.6 < sk["1"]["bias_tmax"] < 1.4                           # +1.0 planted
    lo, hi = sk["1"]["mae_tmax_ci"]
    assert lo <= sk["1"]["mae_tmax"] <= hi


def test_rain_skill_beats_climatology_at_short_lead(world):
    e = world["skill"]["ruzyne"]["ensemble"]["1"]
    assert e["n"] >= 30 and e["bss_vs_climatology"] > 0


def test_gate_holds_when_pairs_are_few(tmp_path, monkeypatch):
    build_world(tmp_path, n_issues=10)
    monkeypatch.setattr(V, "DATA", tmp_path); monkeypatch.setattr(V, "OUT", tmp_path / "data.json")
    V.main()
    d = json.loads((tmp_path / "data.json").read_text())
    e = d["skill"]["ruzyne"]["best_match"]["6"]
    assert e["n"] < V.MIN_PAIRS and "mae_tmax" not in e


def test_quality_counts_match_the_files(world):
    q = world["quality"]
    assert q["issues"] == 45 and q["expected_issues"] == 45 and q["missing_issue_dates"] == []
    assert q["null_share_by_model"]["best_match"] == 0.0
    assert q["observation_gaps"]["ruzyne"] == []


def test_windows_follow_chmi_definitions():
    times = [f"2026-09-{d:02d}T{h:02d}:00" for d in (14, 15, 16) for h in range(24)]
    vals = [float(i) for i in range(len(times))]
    assert windows(times, vals, "max") == {"2026-09-15": 43.0, "2026-09-16": 67.0}   # (14 20:00, 15 20:00]
    assert windows(times, vals, "sum")["2026-09-15"] == sum(range(6, 30))              # (14 06:00, 15 06:00]


def test_string_values_from_the_source_are_missing_not_crashes(tmp_path, monkeypatch):
    from weather.collect import as_number

    assert as_number("12,4") == 12.4 and as_number("") is None and as_number("-") is None and as_number(None) is None
    build_world(tmp_path)
    obs = json.loads((tmp_path / "observations.json").read_text())
    day = sorted(obs["stations"]["ruzyne"])[5]
    obs["stations"]["ruzyne"][day]["precip"] = "0,0"        # a string that once crashed the verifier
    (tmp_path / "observations.json").write_text(json.dumps(obs))
    monkeypatch.setattr(V, "DATA", tmp_path); monkeypatch.setattr(V, "OUT", tmp_path / "data.json")
    V.main()                                                  # must not raise
