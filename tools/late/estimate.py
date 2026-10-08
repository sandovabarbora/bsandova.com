"""Estimates of the delay-origins design (§4–§6) from the screened segment × date × hour sums.

S (concentration): the share of all producers' delay made by the top 10 % of segments by total delay produced.
ρ (stability): Spearman's correlation across segments of mean gain per pass in odd and in even ISO weeks.
Both with a bootstrap over service dates (999 draws), the ranking recomputed in each draw.

Writes docs/research/delay-origins-results.json and assets/late/segments.json (per-segment values for the map).

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with scipy python tools/late/estimate.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/late"
OUT = ROOT / "docs/research/delay-origins-results.json"
REPS, SEED, TOP = 999, 20261008, 0.10
PEAK = set(range(7, 9)) | set(range(15, 18))
MIDDAY = set(range(10, 14))


def matrix(seg: pd.DataFrame, g: str = "gsum", n: str = "n") -> tuple[pd.Index, pd.Index, np.ndarray, np.ndarray]:
    """Segments × dates arrays of summed gain and passes."""
    key = seg["seg_from"] + " → " + seg["seg_to"]
    t = seg.assign(key=key).groupby(["key", "date"])[[g, n]].sum()
    G = t[g].unstack(fill_value=0.0)
    N = t[n].unstack(fill_value=0).reindex_like(G).fillna(0)
    return G.index, G.columns, G.to_numpy(float), N.to_numpy(float)


def concentration(total: np.ndarray, top: float = TOP) -> float:
    k = max(1, math.ceil(top * len(total)))
    producers = total[total > 0].sum()
    return float(np.sort(total)[::-1][:k].sum() / producers) if producers > 0 else float("nan")


def stability(G: np.ndarray, N: np.ndarray, odd: np.ndarray) -> float:
    with np.errstate(invalid="ignore", divide="ignore"):
        a = G[:, odd].sum(1) / N[:, odd].sum(1)
        b = G[:, ~odd].sum(1) / N[:, ~odd].sum(1)
    ok = np.isfinite(a) & np.isfinite(b)
    return float(spearmanr(a[ok], b[ok]).statistic)


def per_pass(G: np.ndarray, N: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        m = G.sum(1) / N.sum(1)
    return np.nan_to_num(m)


def boot(stat, G: np.ndarray, N: np.ndarray, dates: pd.Index, rng) -> tuple[float, list, list]:
    est = stat(G, N, np.arange(len(dates)))
    draws = []
    for _ in range(REPS):
        idx = rng.integers(0, len(dates), len(dates))
        draws.append(stat(G[:, idx], N[:, idx], idx))
    draws = np.array(draws)
    q = lambda lv: [round(float(x), 4) for x in np.nanquantile(draws, [(1 - lv) / 2, 1 - (1 - lv) / 2])]  # noqa: E731
    return round(est, 4), q(0.95), q(0.90)


def label(ci95: list, line: float, at_or_above: bool = False) -> str:
    lo, hi = ci95
    if (lo >= line) if at_or_above else (lo > line):
        return "supported"
    if hi < line:
        return "not supported"
    return "inconclusive"


def primary(seg: pd.DataFrame, rng) -> dict:
    keys, dates, G, N = matrix(seg)
    iso_week = np.array([pd.Timestamp(d).isocalendar().week for d in dates])

    def s_stat(G, N, idx):
        return concentration(G.sum(1))

    def r_stat(G, N, idx):
        return stability(G, N, iso_week[idx] % 2 == 1)

    s, s95, s90 = boot(s_stat, G, N, dates, rng)
    r, r95, r90 = boot(r_stat, G, N, dates, rng)
    total = G.sum(1)
    res = {"segments": len(keys), "dates": len(dates), "passes": int(N.sum()),
           "S": {"est": s, "ci95": s95, "ci90": s90, "label": label(s95, 0.50),
                 "imprecise": s95[1] - s95[0] > 0.20},
           "rho": {"est": r, "ci95": r95, "ci90": r90, "label": label(r95, 0.70, at_or_above=True),
                   "imprecise": r95[1] - r95[0] > 0.20},
           "producers": int((total > 0).sum()), "recoverers": int((total < 0).sum()),
           "produced_s": round(float(total[total > 0].sum())), "recovered_s": round(float(total[total < 0].sum()))}
    return res


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else float("nan")


def top_set(seg: pd.DataFrame, hours: set) -> set:
    s = seg[seg["hour"].isin(hours) & (pd.to_datetime(seg["date"]).dt.weekday < 5)]
    keys, _, G, N = matrix(s)
    m = per_pass(G, N)
    k = max(1, math.ceil(TOP * len(keys)))
    return set(keys[np.argsort(m)[::-1][:k]])


def checks(seg: pd.DataFrame) -> dict:
    keys, dates, G, N = matrix(seg)
    out = {"per_pass": round(concentration(per_pass(G, N)), 4),
           "top_5": round(concentration(G.sum(1), 0.05), 4), "top_20": round(concentration(G.sum(1), 0.20), 4)}
    _, _, Gt, _ = matrix(seg[~seg["terminal"]])
    out["without_terminal_segments"] = round(concentration(Gt.sum(1)), 4)
    _, _, G3, _ = matrix(seg, "gsum300", "n300")
    out["gain_within_300s"] = round(concentration(G3.sum(1)), 4)
    _, _, Gr, _ = matrix(seg, "gsum_run", "n_run")
    out["running_time_only"] = round(concentration(Gr.sum(1)), 4)
    month = pd.to_datetime(seg["date"]).dt.month
    out["by_month"] = {int(m): round(concentration(matrix(seg[month == m])[2].sum(1)), 4) for m in sorted(month.unique())}
    out["peak_midday_jaccard"] = round(jaccard(top_set(seg, PEAK), top_set(seg, MIDDAY)), 4)
    return out


def segments_for_map(seg: pd.DataFrame, stops: pd.DataFrame) -> list:
    rows = []
    view = {"all": seg, "peak": seg[seg["hour"].isin(PEAK) & (pd.to_datetime(seg["date"]).dt.weekday < 5)],
            "midday": seg[seg["hour"].isin(MIDDAY) & (pd.to_datetime(seg["date"]).dt.weekday < 5)]}
    xy = {r.name: (round(r.lon, 5), round(r.lat, 5)) for r in stops.itertuples()}
    base = None
    for name, s in view.items():
        t = s.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum()
        t[name + "_per_pass"] = (t["gsum"] / t["n"]).round(2)
        t[name + "_total_h"] = (t["gsum"] / 3600).round(1)
        base = t[[name + "_per_pass", name + "_total_h"]] if base is None else base.join(
            t[[name + "_per_pass", name + "_total_h"]], how="left")
    for (a, b), r in base.iterrows():
        if a in xy and b in xy:
            rows.append({"from": a, "to": b, "line": [xy[a], xy[b]], **{k: (None if pd.isna(v) else v)
                                                                         for k, v in r.items()}})
    return rows


def main() -> None:
    seg = pd.read_parquet(DATA / "segments.parquet")
    rng = np.random.default_rng(SEED)
    res = {"top_share": TOP}
    for mode in ("tram", "bus"):
        s = seg[seg["mode"] == mode]
        res[mode if mode == "tram" else "bus_secondary"] = {**primary(s, rng), "checks": checks(s)}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    stops = pd.read_parquet(DATA / "stops.parquet")
    (ROOT / "assets/late").mkdir(parents=True, exist_ok=True)
    (ROOT / "assets/late/segments.json").write_text(
        json.dumps(segments_for_map(seg[seg["mode"] == "tram"], stops), ensure_ascii=False))
    print(json.dumps({k: {kk: v[kk] for kk in ("S", "rho")} for k, v in res.items() if k != "top_share"}, indent=1))


if __name__ == "__main__":
    main()
