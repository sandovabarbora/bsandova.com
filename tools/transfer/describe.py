"""Descriptive parts of the transfers design: Q3 (the curve, the roulette cells and their calibration) and Q4 (where
costly misses come from). No label; every number here is described, as §2 registers it.

Writes docs/research/transfers-describe.json and assets/transfers/roulette.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow python tools/transfer/describe.py
"""
from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs/research"
DATA = ROOT / "tools/data/transfer"
ASSETS = ROOT / "assets/transfers"
OUT = R / "transfers-describe.json"
MIN_CONN, MIN_DATES = 500, 30
SLACKS = list(range(1, 11))  # minutes shown in the roulette
CELL_REPS, SEED = 99, 20261008
log = logging.getLogger("transfer.describe")

_spec = importlib.util.spec_from_file_location("transfer_estimate", Path(__file__).with_name("estimate.py"))
es = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(es)


def direction(key: str) -> str:
    return key.split("|")[1]


def cells(c: pd.DataFrame, rng) -> tuple[list[dict], dict]:
    """Q3: one roulette cell per hub × A line × B line × B direction × hour band."""
    c = c[c["made"].notna() & ~c["excluded"]].copy()
    c["dd"] = c["delta_b"] - c["d_a"]  # made ⇔ dd ≥ m − s
    c["bdir"] = c["bkey"].map(direction)
    c["adir"] = c["akey"].map(direction)
    out, calib = [], []
    weeks = np.array(sorted(c["week"].unique()))
    wi = {w: i for i, w in enumerate(weeks)}
    W = es.draws(len(weeks), CELL_REPS, rng)
    for (hub, a, adir, b, bdir, band), g in c.groupby(["hub", "aroute", "adir", "broute", "bdir", "band"], observed=True):
        thin = len(g) < MIN_CONN or g["date"].nunique() < MIN_DATES
        rec = {"hub": hub, "a": str(a), "a_to": adir, "b": str(b), "b_to": bdir, "band": band,
               "connections": int(len(g)), "dates": int(g["date"].nunique()), "thin": bool(thin)}
        if not thin:
            dd, wk = g["dd"].to_numpy(), np.array([wi[w] for w in g["week"]])
            m = float(np.median(g["m"]))
            curve = []
            for s in SLACKS:
                hit = (dd >= m - 60 * s).astype(float)
                wt = W[:, wk]
                vals = (wt @ hit) / wt.sum(axis=1)
                curve.append({"s": s, "p": round(float(vals[0]), 3),
                              "lo": round(float(np.quantile(vals[1:], 0.025)), 3),
                              "hi": round(float(np.quantile(vals[1:], 0.975)), 3)})
            rec.update({"m_s": round(m), "curve": curve,
                        "costly_miss": round(float((g["w"] > es.COSTLY_S).mean()), 3),
                        "median_extra_wait_s": round(float(np.median(g["w"]))),
                        "own_slack_median_min": round(float(np.median(g["slack"])) / 60, 1),
                        "made_at_own_slacks": round(float(g["made"].mean()), 3)})
            pred = np.array([(dd >= mm - ss).mean() for mm, ss in zip(g["m"], g["slack"])])
            calib.append(pd.DataFrame({"pred": pred, "obs": g["made"].to_numpy()}))
        out.append(rec)
    cal = pd.concat(calib, ignore_index=True)
    cal["bin"] = pd.qcut(cal["pred"].rank(method="first"), 10, labels=False)
    table = cal.groupby("bin").agg(pred=("pred", "mean"), obs=("obs", "mean"), n=("obs", "size")).round(4)
    return out, {"calibration_deciles": table.reset_index().to_dict("records"),
                 "max_abs_gap": round(float((table["pred"] - table["obs"]).abs().max()), 4)}


def prev_names() -> dict:
    """akey (route|terminal|stop id at the hub) → the stop the A trip came from, its mode across passes."""
    names = {}
    for f in sorted(DATA.glob("passes_*.parquet")):
        p = pd.read_parquet(f, columns=["route", "terminal", "stop_id", "prev_name"])
        p = p.dropna(subset=["prev_name"])
        k = p["route"].astype(str) + "|" + p["terminal"].astype(str) + "|" + p["stop_id"].astype(str)
        for key, v in p.assign(k=k).groupby("k")["prev_name"].agg(lambda s: s.mode().iloc[0]).items():
            names.setdefault(key, v)
    return names


def top_segments(odd: bool) -> set[tuple[str, str]]:
    """Part 1's top tenth of tram segments by delay produced, ranked on odd (or even) ISO weeks only."""
    s = pd.read_parquet(ROOT / "tools/data/late/segments.parquet", columns=["mode", "seg_from", "seg_to", "date", "gsum"])
    s = s[s["mode"] == "tram"]
    wk = pd.to_datetime(s["date"]).dt.isocalendar().week
    s = s[(wk % 2 == 1) == odd]
    tot = s.groupby(["seg_from", "seg_to"])["gsum"].sum().sort_values(ascending=False)
    return set(tot.index[: int(np.ceil(0.1 * len(tot)))])


def misses(c: pd.DataFrame) -> dict:
    """Q4: among costly misses at slack 2–4 min, A already later than the slack at the stop before, or not."""
    q = c[c["slack"].between(120, 240) & c["made"].notna() & ~c["excluded"] & (c["w"] > es.COSTLY_S)].copy()
    prev_delay = q["a_prev_oa"] - q["a_prev_sa"]
    q["origin"] = np.select([prev_delay.isna(), prev_delay > q["slack"]], ["no_prior_arrival", "already_late"],
                            "lost_on_last_segment")
    names = prev_names()
    q["seg"] = [(names.get(k), h) for k, h in zip(q["akey"], q["hub"])]
    top_odd, top_even = top_segments(True), top_segments(False)
    odd = q["week"] % 2 == 1
    q["top_segment"] = [s in (top_even if o else top_odd) for s, o in zip(q["seg"], odd)]  # ranked on the other half
    last = q[q["origin"] == "lost_on_last_segment"]
    return {"costly_misses": int(len(q)),
            "origin_share": {k: round(float(v), 4) for k, v in q["origin"].value_counts(normalize=True).items()},
            "lost_on_last_segment_after_a_top_producer": round(float(last["top_segment"].mean()), 4)
            if len(last) else None,
            "all_costly_after_a_top_producer": round(float(q["top_segment"].mean()), 4)}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sc = json.loads((R / "transfers-screen.json").read_text())
    c, b = es.load()
    b = es.b_table(b)
    c = es.prepare(c, set(sc["hubs_removed_early_departures"]))
    c["w"] = es.extra_wait(c, b)
    rng = np.random.default_rng(SEED)
    roulette, calib = cells(c, rng)
    res = {"cells": len(roulette), "cells_shown": sum(not r["thin"] for r in roulette), **calib,
           "q4": misses(c)}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "roulette.json").write_text(json.dumps(roulette, ensure_ascii=False))
    print(json.dumps(res, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
