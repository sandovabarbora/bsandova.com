"""Descriptive parts of the transfers design: Q3 (the curve, the roulette cells and their calibration) and Q4 (where
costly misses come from). No label; every number here is described, as §2 registers it.

Writes docs/research/transfers-describe.json and assets/transfers/roulette.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow python tools/transfer/describe.py
"""
from __future__ import annotations

import importlib.util
import json
import logging
import subprocess
import sys
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
    """Q3: one roulette cell per hub × A line × A direction × B line × B direction × hour band."""
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
            den = W @ np.bincount(wk, minlength=len(weeks))
            for s in SLACKS:
                vals = (W @ np.bincount(wk, weights=(dd >= m - 60 * s), minlength=len(weeks))) / den
                curve.append({"s": s, "p": round(float(vals[0]), 3),
                              "lo": round(float(np.quantile(vals[1:], 0.025)), 3),
                              "hi": round(float(np.quantile(vals[1:], 0.975)), 3)})
            rec.update({"m_s": round(m), "curve": curve,
                        "costly_miss": round(float((g["w"] > es.COSTLY_S).mean()), 3),
                        "median_extra_wait_s": round(float(np.median(g["w"]))),
                        "own_slack_median_min": round(float(np.median(g["slack"])) / 60, 1),
                        "made_at_own_slacks": round(float(g["made"].mean()), 3)})
            srt = np.sort(dd)
            pred = 1 - np.searchsorted(srt, (g["m"] - g["slack"]).to_numpy(), side="left") / len(srt)
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
    q = c[c["slack"].between(120, 240) & (c["w"] > es.COSTLY_S)].copy()
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


CELL = ["hub", "aroute", "adir", "broute", "bdir", "band", "dd", "m", "slack", "made", "w", "date", "week"]
MISS = ["hub", "akey", "week", "slack", "w", "a_prev_oa", "a_prev_sa"]


STAGE = DATA / "describe"


def month_stage(fc: Path, fb: Path) -> None:
    sc = json.loads((R / "transfers-screen.json").read_text())
    removed = set(sc["hubs_removed_early_departures"])
    tag = fc.stem.split("_")[1]
    b = es.b_table(pd.read_parquet(fb))
    c = es.prepare(es.read_connections(fc, False), removed)
    c = c[c["made"].notna()].copy()
    c["w"] = es.extra_wait(c, b)
    c["dd"] = c["delta_b"] - c["d_a"]  # made ⇔ dd ≥ m − s
    c["adir"] = c["akey"].astype(str).map(direction)
    c["bdir"] = c["bkey"].astype(str).map(direction)
    part = c[CELL].copy()
    for k in ("dd", "m", "slack", "w"):
        part[k] = part[k].astype("float32")
    part.to_parquet(STAGE / f"cells_{tag}.parquet", index=False)
    c.loc[c["slack"].between(120, 240) & (c["w"] > es.COSTLY_S), MISS].to_parquet(STAGE / f"miss_{tag}.parquet",
                                                                                   index=False)
    log.info("%s read", fc.name)


def write_roulette(roulette: list[dict], ranges: dict | None = None, default: tuple | None = None) -> None:
    """Every cell to the data folder (never committed); only the cells the roulette shows to the page, since a thin
    cell is shown as "too few connections" whether or not its counts are known. posthoc.py adds each cell's own range
    of planned slack (so the page can flag extrapolation) and the default cell."""
    (DATA / "roulette-all.json").write_text(json.dumps(roulette, ensure_ascii=False))
    ASSETS.mkdir(parents=True, exist_ok=True)
    bands = ["peak", "daytime", "weekend", "evening"]
    key = lambda r: (r["hub"], r["a"], r["a_to"], r["b"], r["b_to"], r["band"])  # noqa: E731
    rows = [r for r in roulette if not r["thin"]]
    shown = {"keys": ["hub", "a", "a_to", "b", "b_to", "band", "connections", "dates", "walk_s", "own_slack_min",
                      "made_own", "costly", "median_wait_s", "curve: [slack min, share, lo, hi]",
                      "own slack range [min, max] min"],
             "bands": bands,
             "rows": [[r["hub"], r["a"], r["a_to"], r["b"], r["b_to"], bands.index(r["band"]), r["connections"],
                       r["dates"], r["m_s"], r["own_slack_median_min"], r["made_at_own_slacks"], r["costly_miss"],
                       r["median_extra_wait_s"], [[k["s"], k["p"], k["lo"], k["hi"]] for k in r["curve"]],
                       list(ranges[key(r)]) if ranges and key(r) in ranges else None]
                      for r in rows]}
    if default is not None:
        shown["default"] = next(i for i, r in enumerate(rows) if key(r) == default)
    (ASSETS / "roulette.json").write_text(json.dumps(shown, ensure_ascii=False, separators=(",", ":")))


def uncertain_breakdown() -> dict:
    """Described after the results, not registered: what the 'uncertain' class of the §4.4 bounds consists of."""
    b = pd.concat([pd.read_parquet(f) for f in sorted((DATA / "estimate").glob("bound_*.parquet"))])
    unobs = b["made"].isna()
    obs = b[~unobs]
    return {"connections": int(len(b)), "uncertain": round(float(b["uncertain"].mean()), 4),
            "planned_b_unobserved": round(float(unobs.mean()), 4),
            "line_short_that_hour_only": round(float((b["uncertain"] & ~unobs).mean()), 4),
            "made_certain": round(float(obs.loc[~obs["uncertain"], "made"].mean()), 4),
            "made_line_short_that_hour": round(float(obs.loc[obs["uncertain"], "made"].mean()), 4)}


def main() -> None:
    """Month by month, each in its own process, as in estimate.py; then the cells and the misses from the reduced
    tables."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if "--month" in sys.argv:
        fc = Path(sys.argv[sys.argv.index("--month") + 1])
        month_stage(fc, fc.with_name(fc.name.replace("connections", "btrips")))
        return
    if "--post-hoc" in sys.argv:  # the additions described after the results, on files already written
        res = json.loads(OUT.read_text())
        res["post_hoc_uncertain_breakdown"] = uncertain_breakdown()
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
        write_roulette(json.loads((DATA / "roulette-all.json").read_text()))
        print(json.dumps(res["post_hoc_uncertain_breakdown"], indent=1))
        return
    STAGE.mkdir(parents=True, exist_ok=True)
    if "--aggregate" not in sys.argv:
        for fc, _ in es.months():
            subprocess.run([sys.executable, __file__, "--month", str(fc)], check=True)
    cells_df = pd.concat([pd.read_parquet(f) for f in sorted(STAGE.glob("cells_*.parquet"))], ignore_index=True)
    for k in ("hub", "aroute", "adir", "broute", "bdir", "band"):
        cells_df[k] = cells_df[k].astype(str).astype("category")
    rng = np.random.default_rng(SEED)
    roulette, calib = cells(cells_df, rng)
    misses_df = pd.concat([pd.read_parquet(f) for f in sorted(STAGE.glob("miss_*.parquet"))], ignore_index=True)
    q4 = misses(misses_df.astype({"hub": str, "akey": str}))
    res = {"cells": len(roulette), "cells_shown": sum(not r["thin"] for r in roulette), **calib, "q4": q4}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    write_roulette(roulette)
    print(json.dumps(res, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
