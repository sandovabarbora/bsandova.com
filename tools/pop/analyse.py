"""Pop, measured: one part's registered estimates (part 1 design §3; series design §2 and §4), written to
docs/research/<slug>-results.json.

    uv run --with numpy python tools/pop/analyse.py harry-styles
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
RNG = np.random.default_rng(20261001)
B = 2000


def rows(name: str) -> list[dict]:
    with open(R / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def km(days: np.ndarray, event: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Kaplan–Meier survival S(t) at each distinct event time."""
    times = np.unique(days[event])
    s, out = 1.0, []
    for t in times:
        at_risk = (days >= t).sum()
        s *= 1 - ((days == t) & event).sum() / at_risk
        out.append(s)
    return times, np.array(out)


def surv_at(days: np.ndarray, event: np.ndarray, t: float) -> float:
    """Share of songs still in the chart after t days: S(t)."""
    times, s = km(days, event)
    i = np.searchsorted(times, t, side="right") - 1
    return 1.0 if i < 0 else float(s[i])


def q1() -> dict:
    ones = [r for r in rows(f"{SLUG}-ones.csv") if r["kept"] == "True"]
    days = np.array([int(r["days"]) for r in ones])
    event = np.array([r["still_charting"] == "False" for r in ones])
    times, s = km(days, event)
    median = float(times[np.argmax(s <= 0.5)]) if (s <= 0.5).any() else None
    placed = []
    for r in ones:
        if r["own"] != "True":
            continue
        t = int(r["days"])
        boot = []
        for _ in range(B):
            i = RNG.integers(0, len(days), len(days))
            boot.append(surv_at(days[i], event[i], t))
        placed.append({"label": r["label"], "focal": r["focal"] == "True", "days": t, "still_charting": r["still_charting"] == "True",
                       "share_longer": surv_at(days, event, t),
                       "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]})
    return {"n_number_ones": len(ones), "excluded_before_2017": sum(r["kept"] != "True" for r in rows(f"{SLUG}-ones.csv")),
            "censored": int((~event).sum()), "median_days": median,
            "curve": [[int(t), float(v)] for t, v in zip(times, s)], "own": placed,
            "small_reference_set": len(ones) < 20}


def q2() -> dict:
    out = []
    for r in rows(f"{SLUG}-countries.csv"):
        ones = np.array([int(x) for x in r["ones_days"].split()]) if r["ones_days"] else np.array([])
        d = int(r["focal_days"])
        if len(ones) == 0:
            continue
        med = float(np.median(ones))
        boot = [d / np.median(RNG.choice(ones, len(ones))) for _ in range(B)]
        out.append({"country": r["country"], "days": d, "ones": len(ones), "median_ones_days": med, "ratio": d / med,
                    "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                    "still_charting": r["still_charting"] == "True", "ranked": len(ones) >= 20})
    ranked = sorted((c for c in out if c["ranked"]), key=lambda c: -c["ratio"])
    for i, c in enumerate(ranked, 1):
        c["rank"] = i
    cz = next((c for c in out if c["country"] == "cz"), None)
    # added after the results were seen (labelled so in the article): rank by days alone, without the country's
    # own number ones, because small markets with many one-day number ones inflate the registered ratio
    by_days = sorted(out, key=lambda c: -c["days"])
    for i, c in enumerate(by_days, 1):
        c["rank_by_days_post_hoc"] = i
    return {"countries": sorted(out, key=lambda c: -c["ratio"]), "n_ranked": len(ranked), "czechia": cz}


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = (np.argsort(np.argsort(v, kind="stable"), kind="stable").astype(float) for v in (x, y))
    # average ranks for ties
    for v, r in ((x, rx), (y, ry)):
        for u in np.unique(v):
            m = v == u
            r[m] = r[m].mean()
    return float(np.corrcoef(rx, ry)[0, 1])


def q3() -> dict:
    if not (R / f"{SLUG}-tour.csv").exists():
        return {"answerable": False}
    t = rows(f"{SLUG}-tour.csv")
    nights = np.array([int(r["nights"]) for r in t])
    sell = np.array([int(r["sold"]) / int(r["available"]) for r in t])
    rho = spearman(nights, sell) if sell.std() > 0 else None
    boot = []
    for _ in range(B):
        i = RNG.integers(0, len(t), len(t))
        if sell[i].std() > 0 and nights[i].std() > 0:
            boot.append(spearman(nights[i], sell[i]))
    full = float((sell >= 0.995).mean())
    rev = [int(r["revenue_usd"]) / int(r["nights"]) for r in t if r["revenue_usd"]]
    return {"answerable": True, "entries": len(t), "tours": sorted({r["tour"] for r in t}), "shows": int(nights.sum()), "share_sold_out": full,
            "demand_at_capacity": full >= 0.9, "spearman_rho": rho,
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))] if boot else None,
            "sell_through_min": float(sell.min()), "nights_max": int(nights.max()),
            "revenue_per_night_median_usd": float(np.median(rev)) if rev else None}


def q4() -> dict:
    songs = rows(f"{SLUG}-songs.csv")
    x = np.sort(np.array([int(r["streams"]) for r in songs], dtype=float))[::-1]
    total = x.sum()
    asc = np.sort(x)
    n = len(asc)
    gini = float((2 * np.arange(1, n + 1) - n - 1).dot(asc) / (n * asc.sum()))
    lorenz = np.concatenate([[0], np.cumsum(asc) / total])
    pick = np.linspace(0, n, 101).round().astype(int)
    return {"songs": n, "top_song": songs[0]["title"] if songs else None, "top_share": float(x[0] / total),
            "top3_share": float(x[:3].sum() / total), "gini": gini,
            "lorenz": [[float(i / n), float(lorenz[i])] for i in pick]}


def q5() -> dict:
    if not (R / f"{SLUG}-tour.csv").exists():
        return {"answerable": False}
    t = [r for r in rows(f"{SLUG}-tour.csv") if r["revenue_usd"] and r["iso3"] and r["gdppc_usd"]]
    by: dict[str, dict] = {}
    for r in t:
        name = {"GBR": "United Kingdom", "USA": "United States"}.get(r["iso3"], r["country"])
        c = by.setdefault(r["iso3"], {"country": name, "revenue": 0, "sold": 0, "income_day_weighted": 0.0})
        c["revenue"] += int(r["revenue_usd"])
        c["sold"] += int(r["sold"])
        c["income_day_weighted"] += int(r["sold"]) * float(r["gdppc_usd"]) / 365
    out = []
    for iso, c in by.items():
        price = c["revenue"] / c["sold"]
        day = c["income_day_weighted"] / c["sold"]
        out.append({"iso3": iso, "country": c["country"], "price_usd": price, "days_of_income": price / day,
                    "sold": c["sold"]})
    return {"answerable": bool(out), "entries_used": len(t), "countries": sorted(out, key=lambda c: -c["days_of_income"])}


if __name__ == "__main__":
    SLUG = sys.argv[1]
    res = {"q1": q1(), "q2": q2(), "q3": q3(), "q4": q4(), "q5": q5()}
    (R / f"{SLUG}-results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("written", f"{SLUG}-results.json")
