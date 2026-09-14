"""Pair every stored forecast with the analysis of its target date and write surf/data.json.

    python surf/verify.py

Skill is computed per spot, per wave model and per lead day (0–6): mean absolute error and
bias of the daily maximum swell height and of the mean period, Spearman rank correlation,
and the hit / miss / false-alarm table for "surfable". Nothing is reported for a lead with
fewer than MIN_PAIRS pairs; the page shows the gap. The truth is the model's own analysis
(lead 0 of the default model), which is a proxy and is labelled as one.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "data.json"
MIN_PAIRS = 14

# "surfable", v1. Adjustable on the page for the decision table; fixed here for skill.
H_MIN, H_MAX, P_MIN, WIND_MAX, OFFSHORE = 1.0, 2.5, 8.0, 25.0, (90.0, 60.0)  # offshore = E ± 60°


def offshore(wind_dir: float | None) -> bool:
    if wind_dir is None:
        return False
    d = abs((wind_dir - OFFSHORE[0] + 180) % 360 - 180)
    return d <= OFFSHORE[1]


def surfable(r: dict) -> bool | None:
    if r.get("swell_max") is None or r.get("period_mean") is None:
        return None
    wind_ok = r.get("wind_mean") is None or r["wind_mean"] <= WIND_MAX or offshore(r.get("wind_dir"))
    return H_MIN <= r["swell_max"] <= H_MAX and r["period_mean"] >= P_MIN and wind_ok


def spearman(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 3:
        return None
    def ranks(x):
        order = sorted(range(n), key=lambda i: x[i]); r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and x[order[j + 1]] == x[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va, vb = sum((x - ma) ** 2 for x in ra), sum((y - mb) ** 2 for y in rb)
    return round(cov / math.sqrt(va * vb), 3) if va and vb else None


def main() -> None:
    analysis = json.loads((DATA / "analysis.json").read_text())
    issues = sorted((DATA / "forecasts").glob("*.json"))
    forecasts = [json.loads(p.read_text()) for p in issues]
    spots = list(analysis["spots"].keys())
    models = forecasts[-1]["models"] if forecasts else []
    out = {"generated": date.today().isoformat(), "truth": analysis["model"], "spots": spots, "models": models,
           "surfable_rule": {"swell_max_m": [H_MIN, H_MAX], "period_min_s": P_MIN, "wind_max_kmh": WIND_MAX, "offshore_deg": list(OFFSHORE)},
           "issues": [f["issued"] for f in forecasts], "min_pairs": MIN_PAIRS, "climatology": {}, "latest": {}, "skill": {}, "reliability": {}}

    # climatology: per spot, per ISO week, share of surfable days and mean of daily max swell
    for spot in spots:
        days = analysis["spots"][spot]
        weeks: dict[str, list] = {}
        for d, r in sorted(days.items()):
            y, w, _ = date.fromisoformat(d).isocalendar()
            weeks.setdefault(f"{y}-W{w:02d}", []).append(r)
        out["climatology"][spot] = {
            "days": len(days), "from": min(days), "to": max(days),
            "surfable_share": round(sum(1 for r in days.values() if surfable(r)) / len(days), 3) if days else None,
            "weeks": [{"week": w, "n": len(rs), "surfable": sum(1 for r in rs if surfable(r)),
                       "swell_max_mean": round(sum(r["swell_max"] for r in rs if r["swell_max"] is not None) / max(1, sum(1 for r in rs if r["swell_max"] is not None)), 2),
                       "period_mean": round(sum(r["period_mean"] for r in rs if r["period_mean"] is not None) / max(1, sum(1 for r in rs if r["period_mean"] is not None)), 1)}
                      for w, rs in sorted(weeks.items())],
        }

    # latest forecast: per spot, per target date, per model + consensus and spread
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

    # pairs: (spot, model, lead) → list of (forecast rec, truth rec)
    pairs: dict[tuple, list] = {}
    for f in forecasts:
        issued = date.fromisoformat(f["issued"])
        for spot in spots:
            truth = analysis["spots"].get(spot, {})
            for m in models:
                for t, rec in f["spots"][spot].get(m, {}).items():
                    if t in truth and rec.get("swell_max") is not None and truth[t].get("swell_max") is not None:
                        lead = (date.fromisoformat(t) - issued).days
                        pairs.setdefault((spot, m, lead), []).append((rec, truth[t]))
    for (spot, m, lead), ps in sorted(pairs.items()):
        n = len(ps)
        entry = {"n": n}
        if n >= MIN_PAIRS:
            eh = [a["swell_max"] - b["swell_max"] for a, b in ps]
            ep = [a["period_mean"] - b["period_mean"] for a, b in ps if a.get("period_mean") is not None and b.get("period_mean") is not None]
            hits = sum(1 for a, b in ps if surfable(a) and surfable(b)); miss = sum(1 for a, b in ps if not surfable(a) and surfable(b))
            fa = sum(1 for a, b in ps if surfable(a) and not surfable(b)); cn = n - hits - miss - fa
            entry.update({"mae_swell": round(sum(abs(e) for e in eh) / n, 3), "bias_swell": round(sum(eh) / n, 3),
                          "mae_period": round(sum(abs(e) for e in ep) / len(ep), 2) if ep else None,
                          "spearman_swell": spearman([a["swell_max"] for a, _ in ps], [b["swell_max"] for _, b in ps]),
                          "hits": hits, "misses": miss, "false_alarms": fa, "correct_negatives": cn,
                          "p_surfable_given_forecast": round(hits / (hits + fa), 3) if hits + fa else None,
                          "p_surfable_given_not": round(miss / (miss + cn), 3) if miss + cn else None})
        out["skill"].setdefault(spot, {}).setdefault(m, {})[str(lead)] = entry
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    leads = sorted({k[2] for k in pairs}); print(f"{len(forecasts)} issues · {sum(len(v) for v in pairs.values())} pairs · leads {leads} · wrote {OUT.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
