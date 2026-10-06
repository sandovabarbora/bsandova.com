"""Verify every stored forecast against what the station measured; write weather/data.json.

    python weather/verify.py

Pairs: (station, model, lead, target date) with the observation of the target date. Per station,
model and lead: MAE, bias and RMSE of daily max and min temperature; MAE of precipitation; the rain
contingency table (≥ 1.0 mm), probability of detection and false-alarm ratio; the Brier score of the
rain share of the distinct models against day-of-year climatology (1991–2020) and against
persistence (rain on the day before the issue); MAE of temperature against the same two baselines. Intervals by block bootstrap over ISO
weeks: on the daily-maximum MAE and bias, and on the quantities the protocol's reading rules need
(texts/forecast-verification): the Brier skill score against climatology and the Brier score of
persistence minus that of climatology (Prague 2), the paired MAE differences between models (Prague 3)
and between the two stations (Prague 1). Gates as on the surf page: nothing shown under MIN_PAIRS,
"descriptive" under DESCRIPTIVE, and an interval is read only with at least DESCRIPTIVE pairs in at
least READ_WEEKS distinct ISO weeks ("readable").
Protocol corrections of 29 September 2026: persistence is the last observation available at issue
time (issue - 1 day), not the day before the target; precipitation is not scored at lead 0, whose
06:00 UTC window has already closed when the collector runs at 06:40 UTC; the ensemble rain
probability counts the distinct models only (best_match resolves to ICON and is left out of it).
Quality: issues stored against expected, nulls per model, observation gaps, days the models disagree
by more than 4 °C.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "data.json"
RAIN_MM = 1.0
MIN_PAIRS, DESCRIPTIVE, BOOT, READ_WEEKS = 14, 30, 500, 8
PAIRED_MODELS = [("ecmwf_ifs025", "icon_seamless"), ("ecmwf_ifs025", "gfs_seamless"), ("icon_seamless", "ecmwf_ifs025")]
LEADS = range(0, 7)
NOT_IN_ENSEMBLE = {"best_match"}  # resolves to ICON for Prague; a duplicate member, kept as its own column


def block_bootstrap(items, stat, key, reps=BOOT, seed=7):
    rng = random.Random(seed)
    blocks: dict[str, list] = defaultdict(list)
    for it in items:
        blocks[key(it)].append(it)
    keys = list(blocks)
    if len(keys) < 3:
        return None
    vals = []
    for _ in range(reps):
        v = stat([x for k in rng.choices(keys, k=len(keys)) for x in blocks[k]])
        if v is not None:
            vals.append(v)
    if len(vals) < 10:
        return None
    vals.sort()
    return [round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals)) - 1], 3)]


def week_of(d: str) -> str:
    y, w, _ = date.fromisoformat(d).isocalendar()
    return f"{y}-W{w:02d}"


def doy(d: str) -> str:
    return str(date.fromisoformat(d).timetuple().tm_yday)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def read_gate(dates) -> dict:
    """Pairs, the distinct ISO weeks they fall in, and whether an interval may be read."""
    n, weeks = len(dates), len({week_of(d) for d in dates})
    return {"n": n, "weeks": weeks, "descriptive": n < DESCRIPTIVE, "readable": n >= DESCRIPTIVE and weeks >= READ_WEEKS}


def paired_mae_difference(a: list, b: list) -> dict:
    """a, b: (target, obs, fc) of two series; MAE of a minus MAE of b over the target dates both have."""
    fb = {t: (o, f) for t, o, f in b}
    rows = [(t, abs(f["tmax"] - o["tmax"]), abs(fb[t][1]["tmax"] - fb[t][0]["tmax"])) for t, o, f in a if t in fb]
    entry = read_gate([t for t, _, _ in rows])
    if entry["n"] >= MIN_PAIRS:
        d = lambda xs: mean([x - y for _, x, y in xs])
        entry["mae_difference"] = round(d(rows), 3)
        entry["mae_difference_ci95"] = block_bootstrap(rows, d, lambda it: week_of(it[0]))
    return entry


def contingency(pairs):
    """pairs: (obs_precip, fc_precip). Returns counts and rates for rain ≥ RAIN_MM."""
    h = m = f = c = 0
    for o, p in pairs:
        oy, py = o >= RAIN_MM, p >= RAIN_MM
        h += oy and py; m += oy and not py; f += (not oy) and py; c += (not oy) and (not py)
    return {"n": len(pairs), "hits": h, "misses": m, "false_alarms": f, "correct_negatives": c,
            "pod": round(h / (h + m), 3) if h + m else None, "far": round(f / (h + f), 3) if h + f else None,
            "p_rain_given_yes": round(h / (h + f), 3) if h + f else None,
            "p_rain_given_no": round(m / (m + c), 3) if m + c else None,
            "obs_rain_share": round((h + m) / len(pairs), 3) if pairs else None}


def bss_clim(rows):
    bc = mean([(r["pc"] - r["o"]) ** 2 for r in rows])
    return 1 - mean([(r["p"] - r["o"]) ** 2 for r in rows]) / bc if bc else None


def pers_minus_clim(rows):
    return mean([(r["pp"] - r["o"]) ** 2 for r in rows]) - mean([(r["pc"] - r["o"]) ** 2 for r in rows])


def main() -> None:
    obs = json.loads((DATA / "observations.json").read_text())["stations"]
    # defensive: a value that is not a number (older files, or a string from the source) is a missing value
    for s in obs:
        for d in list(obs[s]):
            obs[s][d] = {k: v for k, v in obs[s][d].items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
            if not obs[s][d]:
                del obs[s][d]
    clim = json.loads((DATA / "climatology.json").read_text())["stations"] if (DATA / "climatology.json").exists() else {}
    issues = sorted(p.stem for p in (DATA / "forecasts").glob("*.json"))
    fcs = {i: json.loads((DATA / "forecasts" / f"{i}.json").read_text()) for i in issues}
    models = fcs[issues[-1]]["models"] if issues else []
    stations = list(obs)
    # pairs[(station, model, lead)] = list of (target, obs, fc)
    pairs: dict[tuple, list] = defaultdict(list)
    nulls: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for issue, fc in fcs.items():
        for s, by_model in fc["stations"].items():
            for m, days in by_model.items():
                for target, f in days.items():
                    lead = (date.fromisoformat(target) - date.fromisoformat(issue)).days
                    if lead not in LEADS:
                        continue
                    nulls[m][1] += 1
                    if f.get("tmax") is None or f.get("precip") is None:
                        nulls[m][0] += 1
                        continue
                    o = obs.get(s, {}).get(target)
                    if o and all(k in o for k in ("tmax", "tmin", "precip")):
                        pairs[(s, m, lead)].append((target, o, f))
    # multi-model rain share per (station, lead, target) for the Brier score
    share: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for (s, m, lead), ps in pairs.items():
        if lead == 0 or m in NOT_IN_ENSEMBLE:
            continue
        for target, o, f in ps:
            share[(s, lead)][target].append(f["precip"] >= RAIN_MM)

    skill: dict = {}
    for s in stations:
        skill[s] = {}
        for m in models:
            skill[s][m] = {}
            for lead in LEADS:
                ps = pairs.get((s, m, lead), [])
                n = len(ps)
                entry = read_gate([t for t, _, _ in ps])
                if n >= MIN_PAIRS:
                    et = [f["tmax"] - o["tmax"] for _, o, f in ps]; en = [f["tmin"] - o["tmin"] for _, o, f in ps]
                    entry.update({
                        "mae_tmax": round(mean([abs(e) for e in et]), 2), "bias_tmax": round(mean(et), 2), "rmse_tmax": round((mean([e * e for e in et])) ** 0.5, 2),
                        "mae_tmin": round(mean([abs(e) for e in en]), 2), "bias_tmin": round(mean(en), 2),
                        "mae_tmax_ci": block_bootstrap(ps, lambda xs: mean([abs(f["tmax"] - o["tmax"]) for _, o, f in xs]), lambda it: week_of(it[0])),
                        "bias_tmax_ci": block_bootstrap(ps, lambda xs: mean([f["tmax"] - o["tmax"] for _, o, f in xs]), lambda it: week_of(it[0])),
                    })
                    if lead == 0:
                        # the rain window (D-1 06:00, D 06:00] has closed before the 06:40 UTC run: a hindcast, not scored;
                        # the temperature windows are partly past at lead 0, so lead 0 is flagged
                        entry["lead0_window_partly_past"] = True
                    else:
                        ep = [f["precip"] - o["precip"] for _, o, f in ps]
                        entry.update({"mae_precip": round(mean([abs(e) for e in ep]), 2), "bias_precip": round(mean(ep), 2)})
                        entry.update(contingency([(o["precip"], f["precip"]) for _, o, f in ps]))
                    # baselines for temperature: climatology mean of the day; persistence = the last observation
                    # available at issue time (issue - 1 day = target - lead - 1), never one from after the issue
                    cl = [abs(clim[s][doy(t)]["tmax_mean"] - o["tmax"]) for t, o, _ in ps if s in clim and doy(t) in clim[s]]
                    pe = []
                    for t, o, _ in ps:
                        y = (date.fromisoformat(t) - timedelta(days=lead + 1)).isoformat()
                        if y in obs[s] and "tmax" in obs[s][y]:
                            pe.append(abs(obs[s][y]["tmax"] - o["tmax"]))
                    entry["mae_tmax_climatology"] = round(mean(cl), 2) if cl else None
                    entry["mae_tmax_persistence"] = round(mean(pe), 2) if pe else None
                skill[s][m][str(lead)] = entry
        # probabilistic rain, per lead, using the share of models
        skill[s]["ensemble"] = {}
        for lead in LEADS:
            rows = []
            for target, votes in share[(s, lead)].items():
                o = obs[s].get(target)
                if o is None or "precip" not in o or not votes:
                    continue
                y = (date.fromisoformat(target) - timedelta(days=lead + 1)).isoformat()  # issue - 1 day
                rows.append({"target": target, "p": sum(votes) / len(votes), "o": int(o["precip"] >= RAIN_MM),
                             "pc": clim.get(s, {}).get(doy(target), {}).get("rain1_freq"),
                             "pp": int(obs[s][y]["precip"] >= RAIN_MM) if y in obs[s] and "precip" in obs[s][y] else None})
            e = read_gate([r["target"] for r in rows])
            if len(rows) >= MIN_PAIRS:
                bs = mean([(r["p"] - r["o"]) ** 2 for r in rows])
                bc = mean([(r["pc"] - r["o"]) ** 2 for r in rows if r["pc"] is not None])
                bp = mean([(r["pp"] - r["o"]) ** 2 for r in rows if r["pp"] is not None])
                e.update({"brier": round(bs, 4), "brier_climatology": round(bc, 4) if bc is not None else None,
                          "bss_vs_climatology": round(1 - bs / bc, 3) if bc else None,
                          "brier_persistence": round(bp, 4) if bp is not None else None,
                          "bss_vs_persistence": round(1 - bs / bp, 3) if bp else None,
                          "bss_vs_climatology_ci95": block_bootstrap([r for r in rows if r["pc"] is not None], bss_clim, lambda r: week_of(r["target"])),
                          "brier_persistence_minus_climatology": round(bp - bc, 4) if bp is not None and bc is not None else None,
                          "brier_persistence_minus_climatology_ci95": block_bootstrap([r for r in rows if r["pc"] is not None and r["pp"] is not None], pers_minus_clim, lambda r: week_of(r["target"])),
                          "reliability": {str(k): {"n": len(g), "obs": round(mean([r["o"] for r in g]), 3)}
                                          for k, g in sorted({round(r["p"], 2): [x for x in rows if round(x["p"], 2) == round(r["p"], 2)] for r in rows}.items())}})
            skill[s]["ensemble"][str(lead)] = e

    # the reading rules' paired comparisons: models against each other at one station (Prague 3), and the
    # same model at the two stations (Prague 1), each over the target dates both series have
    comparisons: dict = {"models": {}, "stations": {}}
    for s in stations:
        comparisons["models"][s] = {f"{a} - {b}": {str(lead): paired_mae_difference(pairs.get((s, a, lead), []), pairs.get((s, b, lead), []))
                                                    for lead in LEADS} for a, b in PAIRED_MODELS if a in models and b in models}
    if {"klementinum", "ruzyne"} <= set(stations):
        comparisons["stations"]["klementinum - ruzyne"] = {m: {str(lead): paired_mae_difference(pairs.get(("klementinum", m, lead), []), pairs.get(("ruzyne", m, lead), []))
                                                               for lead in LEADS} for m in models}

    # quality
    expected = ((date.fromisoformat(issues[-1]) - date.fromisoformat(issues[0])).days + 1) if issues else 0
    have = set(issues); missing = [(date.fromisoformat(issues[0]) + timedelta(days=i)).isoformat() for i in range(expected)] if issues else []
    disagree = {s: 0 for s in stations}; days_checked = {s: 0 for s in stations}
    for (s, lead), targets in share.items():
        if lead != 1:
            continue
        for target in targets:
            vals = [pairs[(s, m, 1)] for m in models]
            tm = [f["tmax"] for m in models for t, o, f in pairs.get((s, m, 1), []) if t == target]
            if len(tm) >= 2:
                days_checked[s] += 1
                if max(tm) - min(tm) > 4:
                    disagree[s] += 1
    obs_gaps = {}
    for s in stations:
        ds = sorted(obs[s])
        obs_gaps[s] = [(date.fromisoformat(ds[0]) + timedelta(days=i)).isoformat() for i in range((date.fromisoformat(ds[-1]) - date.fromisoformat(ds[0])).days + 1)
                       if (date.fromisoformat(ds[0]) + timedelta(days=i)).isoformat() not in obs[s]] if ds else []
    quality = {"issues": len(issues), "expected_issues": expected, "missing_issue_dates": [d for d in missing if d not in have],
               "null_share_by_model": {m: round(v[0] / v[1], 3) if v[1] else None for m, v in nulls.items()},
               "disagreement_gt_4c_lead1": {s: {"share": round(disagree[s] / days_checked[s], 3) if days_checked[s] else None, "n": days_checked[s]} for s in stations},
               "observation_days": {s: len(obs[s]) for s in stations}, "observation_gaps": obs_gaps}
    latest = {s: {m: fcs[issues[-1]]["stations"][s][m] for m in models} for s in stations} if issues else {}
    out = {"generated": date.today().isoformat(), "truth": "ČHMÚ station observations (TMA/TMI 20:00 UTC windows, SRA 06:00 UTC window)",
           "stations": stations, "models": models, "issues": issues, "rain_mm": RAIN_MM,
           "gates": {"min_pairs": MIN_PAIRS, "descriptive_below": DESCRIPTIVE, "read_weeks": READ_WEEKS, "bootstrap_reps": BOOT, "bootstrap_block": "ISO week"},
           "climatology_reference": "1991–2020 ±15 days by day of year", "latest": latest, "recent_obs": {s: dict(sorted(obs[s].items())[-14:]) for s in stations},
           "skill": skill, "comparisons": comparisons, "quality": quality}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"weather: {len(issues)} issues, pairs per (station, model, lead): {sum(len(v) for v in pairs.values())} total; quality {quality['null_share_by_model']}")


if __name__ == "__main__":
    main()
