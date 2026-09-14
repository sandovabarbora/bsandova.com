"""Pair every stored forecast with the analysis of its target date and write surf/data.json.

    python surf/verify.py

Verification, per spot × wave model × lead day (0–6), against the analysis of the target
date (lead 0 of the default model; a proxy, labelled as one):

  continuous   MAE, bias, RMSE of the daily maximum swell height; MAE of mean period;
               Spearman rank correlation.
  binary       "surfable" contingency table (hits, misses, false alarms, correct negatives)
               → probability of detection, false-alarm ratio, P(surfable | forecast yes/no).
  probabilistic the share of the three models that call the day surfable is the forecast
               probability; Brier score, and Brier skill score against climatology.
  baselines    climatology (the base rate over the analysis window) and persistence
               (forecast for lead d = the analysis d days before the target).
  uncertainty  block bootstrap by ISO week (consecutive days are not independent),
               95 % intervals on MAE and on P(surfable | forecast yes).
  robustness   the binary results recomputed under alternative rules: period 7/8/9 s,
               wind 20/25/30 km/h, height band 0.8–3.0 m; and self-verification (MFWAM
               against its own analysis) flagged separately from cross-model verification.

Gates: no number below MIN_PAIRS pairs per lead; below DESCRIPTIVE pairs the entry is
marked descriptive. Nothing here is typed; everything comes from the stored files.
"""

from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "data.json"
MIN_PAIRS, DESCRIPTIVE, BOOT = 14, 30, 500
TRUTH_MODEL = "meteofrance_wave"

RULE = {"h": (1.0, 2.5), "p": 8.0, "w": 25.0, "off": (90.0, 60.0)}
ALT_RULES = {
    "period 7 s": {**RULE, "p": 7.0}, "period 9 s": {**RULE, "p": 9.0},
    "wind 20": {**RULE, "w": 20.0}, "wind 30": {**RULE, "w": 30.0},
    "height 0.8–3.0": {**RULE, "h": (0.8, 3.0)},
}


def offshore(wind_dir, rule):
    if wind_dir is None:
        return False
    return abs((wind_dir - rule["off"][0] + 180) % 360 - 180) <= rule["off"][1]


def surfable(r: dict, rule=RULE):
    if not r or r.get("swell_max") is None or r.get("period_mean") is None:
        return None
    wind_ok = r.get("wind_mean") is None or r["wind_mean"] <= rule["w"] or offshore(r.get("wind_dir"), rule)
    return rule["h"][0] <= r["swell_max"] <= rule["h"][1] and r["period_mean"] >= rule["p"] and wind_ok


def spearman(a, b):
    n = len(a)
    if n < 3:
        return None
    def ranks(x):
        order = sorted(range(n), key=lambda i: x[i]); r = [0.0] * n; i = 0
        while i < n:
            j = i
            while j + 1 < n and x[order[j + 1]] == x[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b); ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va, vb = sum((x - ma) ** 2 for x in ra), sum((y - mb) ** 2 for y in rb)
    return round(cov / math.sqrt(va * vb), 3) if va and vb else None


def contingency(pairs, rule=RULE):
    h = m = f = c = 0
    for a, b in pairs:
        fa, tr = surfable(a, rule), surfable(b, rule)
        if fa is None or tr is None:
            continue
        if fa and tr: h += 1
        elif not fa and tr: m += 1
        elif fa and not tr: f += 1
        else: c += 1
    n = h + m + f + c
    return {"n": n, "hits": h, "misses": m, "false_alarms": f, "correct_negatives": c,
            "pod": round(h / (h + m), 3) if h + m else None, "far": round(f / (h + f), 3) if h + f else None,
            "p_surfable_given_yes": round(h / (h + f), 3) if h + f else None,
            "p_surfable_given_no": round(m / (m + c), 3) if m + c else None,
            "base_rate": round((h + m) / n, 3) if n else None}


def block_bootstrap(items, stat, key, reps=BOOT, seed=7):
    """items: list of (week_key, value...) grouped into blocks by key; stat(list)->float."""
    rng = random.Random(seed)
    blocks: dict[str, list] = {}
    for it in items:
        blocks.setdefault(key(it), []).append(it)
    keys = list(blocks)
    if len(keys) < 3:
        return None
    vals = []
    for _ in range(reps):
        sample = [x for k in rng.choices(keys, k=len(keys)) for x in blocks[k]]
        v = stat(sample)
        if v is not None:
            vals.append(v)
    if len(vals) < 10:
        return None
    vals.sort()
    return [round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals)) - 1], 3)]


def week_of(d: str) -> str:
    y, w, _ = date.fromisoformat(d).isocalendar(); return f"{y}-W{w:02d}"


def main() -> None:
    analysis = json.loads((DATA / "analysis.json").read_text())
    issues = sorted((DATA / "forecasts").glob("*.json"))
    forecasts = [json.loads(p.read_text()) for p in issues]
    spots = list(analysis["spots"].keys())
    models = forecasts[-1]["models"] if forecasts else []
    out = {"generated": date.today().isoformat(), "truth": f"{TRUTH_MODEL} analysis (lead 0) — a proxy, not a buoy",
           "spots": spots, "models": models, "issues": [f["issued"] for f in forecasts],
           "surfable_rule": {"swell_max_m": list(RULE["h"]), "period_min_s": RULE["p"], "wind_max_kmh": RULE["w"], "offshore_deg": list(RULE["off"])},
           "gates": {"min_pairs": MIN_PAIRS, "descriptive_below": DESCRIPTIVE, "bootstrap_reps": BOOT, "bootstrap_block": "ISO week"},
           "climatology": {}, "latest": {}, "skill": {}, "baselines": {}, "robustness": {}}

    for spot in spots:
        days = analysis["spots"][spot]
        weeks: dict[str, list] = {}
        for d, r in sorted(days.items()):
            weeks.setdefault(week_of(d), []).append(r)
        out["climatology"][spot] = {
            "days": len(days), "from": min(days), "to": max(days),
            "surfable_share": round(sum(1 for r in days.values() if surfable(r)) / len(days), 3) if days else None,
            "surfable_share_by_rule": {name: round(sum(1 for r in days.values() if surfable(r, rule)) / len(days), 3) for name, rule in ALT_RULES.items()},
            "weeks": [{"week": w, "n": len(rs), "surfable": sum(1 for r in rs if surfable(r)),
                       "swell_max_mean": round(sum(r["swell_max"] for r in rs if r["swell_max"] is not None) / max(1, sum(1 for r in rs if r["swell_max"] is not None)), 2),
                       "period_mean": round(sum(r["period_mean"] for r in rs if r["period_mean"] is not None) / max(1, sum(1 for r in rs if r["period_mean"] is not None)), 1)}
                      for w, rs in sorted(weeks.items())],
        }

    if forecasts:
        latest = forecasts[-1]
        for spot in spots:
            per_model = latest["spots"][spot]
            targets = sorted({t for m in per_model for t in per_model[m]})
            rows = []
            for t in targets:
                hs = [per_model[m][t]["swell_max"] for m in models if t in per_model[m] and per_model[m][t]["swell_max"] is not None]
                ps = [per_model[m][t]["period_mean"] for m in models if t in per_model[m] and per_model[m][t]["period_mean"] is not None]
                any_rec = next(per_model[m][t] for m in models if t in per_model[m])
                rows.append({"date": t, "lead": (date.fromisoformat(t) - date.fromisoformat(latest["issued"])).days,
                             "models": {m: per_model[m].get(t) for m in models},
                             "swell_max_mean": round(sum(hs) / len(hs), 2) if hs else None,
                             "swell_max_spread": round(max(hs) - min(hs), 2) if hs else None,
                             "period_mean": round(sum(ps) / len(ps), 1) if ps else None,
                             "wind_mean": any_rec.get("wind_mean"), "wind_dir": any_rec.get("wind_dir"),
                             "surfable_votes": sum(1 for m in models if t in per_model[m] and surfable(per_model[m][t]))})
            out["latest"][spot] = {"issued": latest["issued"], "days": rows}

    # ---- pairs: (spot, model, lead) → [(forecast, truth, target_date)]
    pairs: dict[tuple, list] = {}
    votes: dict[tuple, dict] = {}  # (spot, lead) → {target: [forecast recs of all models]}
    for f in forecasts:
        issued = date.fromisoformat(f["issued"])
        for spot in spots:
            truth = analysis["spots"].get(spot, {})
            for m in models:
                for t, rec in f["spots"][spot].get(m, {}).items():
                    if t in truth and rec.get("swell_max") is not None and truth[t].get("swell_max") is not None:
                        lead = (date.fromisoformat(t) - issued).days
                        pairs.setdefault((spot, m, lead), []).append((rec, truth[t], t))
                        votes.setdefault((spot, lead), {}).setdefault(t, []).append(rec)

    for (spot, m, lead), ps in sorted(pairs.items()):
        n = len(ps); entry = {"n": n, "descriptive": n < DESCRIPTIVE, "self_verification": m == TRUTH_MODEL}
        if n >= MIN_PAIRS:
            eh = [a["swell_max"] - b["swell_max"] for a, b, _ in ps]
            ep = [a["period_mean"] - b["period_mean"] for a, b, _ in ps if a.get("period_mean") is not None and b.get("period_mean") is not None]
            entry.update({"mae_swell": round(sum(abs(e) for e in eh) / n, 3), "bias_swell": round(sum(eh) / n, 3),
                          "rmse_swell": round(math.sqrt(sum(e * e for e in eh) / n), 3),
                          "mae_period": round(sum(abs(e) for e in ep) / len(ep), 2) if ep else None,
                          "spearman_swell": spearman([a["swell_max"] for a, _, _ in ps], [b["swell_max"] for _, b, _ in ps]),
                          "mae_swell_ci95": block_bootstrap(ps, lambda s: sum(abs(a["swell_max"] - b["swell_max"]) for a, b, _ in s) / len(s), lambda it: week_of(it[2]))})
            ct = contingency([(a, b) for a, b, _ in ps]); entry["binary"] = ct
            entry["binary"]["p_surfable_given_yes_ci95"] = block_bootstrap(ps, lambda s: (lambda c: c["p_surfable_given_yes"])(contingency([(a, b) for a, b, _ in s])), lambda it: week_of(it[2]))
            entry["robustness"] = {name: {k: v for k, v in contingency([(a, b) for a, b, _ in ps], rule).items() if k in ("n", "hits", "false_alarms", "pod", "far", "p_surfable_given_yes")} for name, rule in ALT_RULES.items()}
        out["skill"].setdefault(spot, {}).setdefault(m, {})[str(lead)] = entry

    # ---- probabilistic (model vote share) and baselines, per spot × lead
    for (spot, lead), by_target in sorted(votes.items()):
        truth = analysis["spots"][spot]
        items = [(t, sum(1 for r in recs if surfable(r)) / len(recs), 1.0 if surfable(truth[t]) else 0.0) for t, recs in by_target.items() if surfable(truth[t]) is not None]
        n = len(items); base = out["climatology"][spot]["surfable_share"] or 0.0
        entry = {"n": n}
        if n >= MIN_PAIRS:
            bs = sum((p - o) ** 2 for _, p, o in items) / n
            bs_clim = sum((base - o) ** 2 for _, _, o in items) / n
            # persistence: the analysis `lead` days before the target, as a 0/1 forecast
            pers = []
            for t, _, o in items:
                d0 = (date.fromisoformat(t) - timedelta(days=max(lead, 1))).isoformat()
                if d0 in truth and surfable(truth[d0]) is not None:
                    pers.append((1.0 if surfable(truth[d0]) else 0.0, o))
            bs_pers = sum((p - o) ** 2 for p, o in pers) / len(pers) if pers else None
            entry.update({"brier": round(bs, 4), "brier_climatology": round(bs_clim, 4),
                          "bss_vs_climatology": round(1 - bs / bs_clim, 3) if bs_clim else None,
                          "brier_persistence": round(bs_pers, 4) if bs_pers is not None else None,
                          "bss_vs_persistence": round(1 - bs / bs_pers, 3) if bs_pers else None,
                          "reliability": [{"forecast_p": p, "n": sum(1 for _, q, _ in items if q == p), "observed": round(sum(o for _, q, o in items if q == p) / max(1, sum(1 for _, q, _ in items if q == p)), 3)}
                                          for p in sorted({q for _, q, _ in items})]})
        out["baselines"].setdefault(spot, {})[str(lead)] = entry

    # ---- data quality: what the stored files look like, counted, not assumed
    q = {"issues": len(forecasts), "expected_issues": (date.today() - date.fromisoformat(forecasts[0]["issued"])).days + 1 if forecasts else 0,
         "missing_issue_dates": [], "null_share_by_model": {}, "dropout_days_by_model": {}, "disagreement_gt_1m": {}, "analysis_days": {s: len(analysis["spots"][s]) for s in spots},
         "analysis_gaps": {}}
    if forecasts:
        have = {f["issued"] for f in forecasts}; d = date.fromisoformat(forecasts[0]["issued"])
        while d < date.today():
            if d.isoformat() not in have:
                q["missing_issue_dates"].append(d.isoformat())
            d += timedelta(days=1)
        for m in models:
            cells = [rec for f in forecasts for spot in spots for rec in f["spots"][spot].get(m, {}).values()]
            nulls = sum(1 for r in cells if r.get("swell_max") is None or r.get("period_mean") is None)
            q["null_share_by_model"][m] = round(nulls / len(cells), 3) if cells else None
            q["dropout_days_by_model"][m] = sum(1 for f in forecasts for spot in spots if not f["spots"][spot].get(m))
        big = 0; tot = 0
        for f in forecasts:
            for spot in spots:
                targets = {t for m in models for t in f["spots"][spot].get(m, {})}
                for t in targets:
                    hs = [f["spots"][spot][m][t]["swell_max"] for m in models if t in f["spots"][spot].get(m, {}) and f["spots"][spot][m][t]["swell_max"] is not None]
                    if len(hs) >= 2:
                        tot += 1; big += (max(hs) - min(hs) > 1.0)
        q["disagreement_gt_1m"] = {"share": round(big / tot, 3) if tot else None, "n": tot}
        for spot in spots:
            ds = sorted(analysis["spots"][spot]); gaps = []
            for a, b in zip(ds, ds[1:]):
                if (date.fromisoformat(b) - date.fromisoformat(a)).days > 1:
                    gaps.append([a, b])
            q["analysis_gaps"][spot] = gaps
    out["quality"] = q
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    leads = sorted({k[2] for k in pairs}); print(f"{len(forecasts)} issues · {sum(len(v) for v in pairs.values())} pairs · leads {leads} · wrote {OUT.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
