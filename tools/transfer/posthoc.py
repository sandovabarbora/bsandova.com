"""Analyses added after the results of the transfers design (8 October 2026), none of them registered.

The reviewer of the article found that the registered §4.4 bounds overwrite outcomes that were observed, that §4.4's
bounds for Q1b and Q2 and §7's timing check for Q2 had not been run, and that the roulette's calibration was in-sample.
This script runs those, on the same connection tables and the same code paths as estimate.py and describe.py:

- bounds for Q1 that set only connections whose planned B was unobserved to made / missed, and Δp_within on the
  observed connections by whether their line ran a trip short in that hour;
- §4.4 bounds for Q1b (registered and post-hoc definition) and for Q2's share made;
- §7 timing noise for Q2 (A's arrival, and separately B's, shifted by ±30 s);
- the out-of-sample slack test: Δd fitted on connections planned ≥ 5 min apart predicts the share made at 2–4 min;
- the share of all connections planned 2–4 min apart that arrive over one of part 1's top segments (Q4's baseline);
- the roulette's coverage, each cell's own range of planned slack, and its default cell.

Writes docs/research/transfers-posthoc.json and rewrites assets/transfers/roulette.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow python tools/transfer/posthoc.py
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
STAGE = DATA / "posthoc"
OUT = R / "transfers-posthoc.json"
REPS, SEED = 199, 20261009
FIT_MIN_S, FIT_MIN_N = 300, 30  # Δd fitted on connections planned ≥ 5 min apart, cells with at least 30 of them
log = logging.getLogger("transfer.posthoc")


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ds = _load("transfer_describe", "describe.py")
es = ds.es

U = ["date", "week", "hub", "akey", "bkey", "daytype", "sig", "tod_a", "tod_b", "delta_b", "req", "made",
     "uncertain", "within_made", "within_n"]


def signature_from(q: pd.DataFrame, u: pd.DataFrame, b: pd.DataFrame) -> np.ndarray:
    """es.signature with the A timetable taken from the observed connections only, as the primary Q1b took it, so the
    other-day donors of an observed connection are exactly the primary's."""
    a_sig = q.groupby(["hub", "akey", "bkey", "date"], observed=True)["tod_a"].agg(
        lambda s: hash(tuple(sorted(set(s)))))
    midnight = pd.to_datetime(b["date"]).astype("int64") // 10**9
    b_sig = b.assign(tod=(b["sd"] - midnight) % 86400).groupby(["hub", "bkey", "date"], observed=True)["tod"].agg(
        lambda s: hash(tuple(sorted(set(s)))))
    sa = a_sig.reindex(pd.MultiIndex.from_frame(u[["hub", "akey", "bkey", "date"]])).to_numpy()
    sb = b_sig.reindex(pd.MultiIndex.from_frame(u[["hub", "bkey", "date"]])).to_numpy()
    return np.array([hash((x, y)) for x, y in zip(sa, sb)])


def shifted_wait(c: pd.DataFrame, b: pd.DataFrame, a_shift: float = 0.0, b_shift: float = 0.0) -> np.ndarray:
    """Extra wait with A's arrival moved by a_shift, or every B moved by b_shift: B + x is catchable from A when
    B ≥ A − x + m, and the wait then grows by x."""
    w = es.extra_wait(c.assign(a_oa=c["a_oa"] + a_shift - b_shift), b)
    return np.where(w >= es.CENSOR_S, es.CENSOR_S, np.minimum(w + b_shift, es.CENSOR_S))


def month_stage(fc: Path, fb: Path) -> None:
    sc = json.loads((R / "transfers-screen.json").read_text())
    removed = set(sc["hubs_removed_early_departures"])
    miss = pd.read_parquet(DATA / "missing.parquet")
    miss = miss[miss["missing"] > 0]
    short = set(zip(miss["stop_name"].astype(str), miss["route"].astype(str), miss["sdate"].dt.date, miss["hour"]))
    tag = fc.stem.split("_")[1]
    b = es.b_table(pd.read_parquet(fb))
    c = es.prepare(es.read_connections(fc, False), removed)

    u = c[c["slack"].between(120, 240) & c["q1_hub"]].copy()  # the bound population of estimate.py
    u["uncertain"] = es.uncertain(u, short)
    u["within_made"], u["within_n"] = es.within_donors(u, b)
    u = u[u["within_n"] > 0].copy()
    u["sig"] = signature_from(u[u["made"].notna()], u, b)
    u[U].to_parquet(STAGE / f"u_{tag}.parquet", index=False)

    c2 = c[(c["slack"] >= 120) & (c["slack"] < 300)].copy()  # Q2's population (all hubs)
    c2["uncertain"] = es.uncertain(c2, short)
    c2["w"] = es.extra_wait(c2, b)
    for x in (30, -30):
        c2[f"made_a{x:+d}"] = es.score(c2, a_shift=x)["made"]
        c2[f"made_b{x:+d}"] = es.score(c2, b_shift=x)["made"]
        c2[f"w_a{x:+d}"] = shifted_wait(c2, b, a_shift=x)
        c2[f"w_b{x:+d}"] = shifted_wait(c2, b, b_shift=x)
    keep = ["slack", "made", "uncertain", "w", "hub", "akey", "week"] + [k for k in c2 if k[:2] in ("ma", "w_")
                                                                         and k != "made"]
    c2[keep].to_parquet(STAGE / f"q2_{tag}.parquet", index=False)
    log.info("%s: %s bound rows, %s Q2 rows", fc.name, len(u), len(c2))


def table(prefix: str, folder: Path = STAGE) -> pd.DataFrame:
    return pd.concat([pd.read_parquet(f) for f in sorted(folder.glob(f"{prefix}_*.parquet"))], ignore_index=True)


def within(u: pd.DataFrame, made: np.ndarray, W: np.ndarray, weeks: np.ndarray) -> dict:
    return es.interval(es.within_stat(u.assign(made=made), W, weeks))


def pp(d: dict) -> dict:
    return {k: d[k] for k in ("est", "ci95", "ci90", "label")}


def q1_bounds(u: pd.DataFrame, W: np.ndarray, weeks: np.ndarray) -> dict:
    made = u["made"].to_numpy()
    unobs = np.isnan(made)
    unc = u["uncertain"].to_numpy()
    obs = ~unobs
    out = {"rows_with_same_day_donors": int(len(u)), "observed_rows": int(obs.sum()),
           "unobserved_share": round(float(unobs.mean()), 4),
           "line_short_observed_share": round(float((unc & obs).mean()), 4),
           "check_primary_reproduced": pp(within(u[obs], made[obs], W, weeks)),
           "check_registered_all_made": pp(within(u, np.where(unc, 1.0, made), W, weeks)),
           "check_registered_all_missed": pp(within(u, np.where(unc, 0.0, made), W, weeks)),
           "unobserved_all_made": pp(within(u, np.where(unobs, 1.0, made), W, weeks)),
           "unobserved_all_missed": pp(within(u, np.where(unobs, 0.0, made), W, weeks))}
    for name, sel in (("observed_line_not_short", obs & ~unc), ("observed_line_short", obs & unc)):
        out[name] = {**pp(within(u[sel], made[sel], W, weeks)), "connections": int(sel.sum()),
                     "made": round(float(made[sel].mean()), 4)}
    return out


def q1b_bounds(u: pd.DataFrame, W: np.ndarray, weeks: np.ndarray) -> dict:
    for k in ("hub", "akey", "bkey", "daytype"):
        u[k] = u[k].astype(str).astype("category")
    S, N = es.day_donors(u, weeks)
    made = u["made"].to_numpy()
    unobs, unc = np.isnan(made), u["uncertain"].to_numpy()
    obs = ~unobs

    def run(m: np.ndarray, sel: np.ndarray) -> dict:
        idx = np.flatnonzero(sel)
        return pp(es.interval(es.day_stat(u.iloc[idx].assign(made=m[idx]), S[idx], N[idx], W, weeks)))

    return {"rows_with_other_day_donors": int((N.sum(axis=1) > 0).sum()),
            "unobserved_rows_with_other_day_donors": int(((N.sum(axis=1) > 0) & unobs).sum()),
            "check_primary_reproduced": run(made, obs),
            "registered_all_made": run(np.where(unc, 1.0, made), np.ones(len(u), bool)),
            "registered_all_missed": run(np.where(unc, 0.0, made), np.ones(len(u), bool)),
            "unobserved_all_made": run(np.where(unobs, 1.0, made), np.ones(len(u), bool)),
            "unobserved_all_missed": run(np.where(unobs, 0.0, made), np.ones(len(u), bool))}


def q2(t: pd.DataFrame) -> dict:
    out = {}
    for s in (2, 3, 4):
        g = t[(t["slack"] >= 60 * s) & (t["slack"] < 60 * (s + 1))]
        unobs = g["made"].isna()
        o = g[~unobs]
        rec = {"connections_all": int(len(g)), "unobserved_share": round(float(unobs.mean()), 4),
               "made_observed": round(float(o["made"].mean()), 4),
               "bound_unobserved_all_made": round(float(g["made"].fillna(1.0).mean()), 4),
               "bound_unobserved_all_missed": round(float(g["made"].fillna(0.0).mean()), 4),
               "registered_uncertain_all_made": round(float(g["made"].where(~g["uncertain"], 1.0).mean()), 4),
               "registered_uncertain_all_missed": round(float(g["made"].where(~g["uncertain"], 0.0).mean()), 4),
               "costly_observed": round(float((o["w"] > es.COSTLY_S).mean()), 4), "timing": {}}
        for k in ("a+30", "a-30", "b+30", "b-30"):
            rec["timing"][k] = {"made": round(float(o[f"made_{k}"].mean()), 4),
                                "costly_miss": round(float((o[f"w_{k}"] > es.COSTLY_S).mean()), 4),
                                "median_extra_wait_s": float(np.median(o[f"w_{k}"]))}
        out[str(s)] = rec
    return out


def q4_baseline(t: pd.DataFrame) -> dict:
    """Share of all observed connections planned 2–4 min apart whose A came over one of part 1's top tenth of
    segments, ranked on the other half of the weeks, as describe.misses ranks them."""
    g = t[t["slack"].between(120, 240) & t["made"].notna()]
    names = ds.prev_names()
    seg = [(names.get(k), h) for k, h in zip(g["akey"].astype(str), g["hub"].astype(str))]
    top_odd, top_even = ds.top_segments(True), ds.top_segments(False)
    odd = (g["week"] % 2 == 1).to_numpy()
    top = np.array([s in (top_even if o else top_odd) for s, o in zip(seg, odd)])
    costly = (g["w"] > es.COSTLY_S).to_numpy()
    return {"connections": int(len(g)), "after_a_top_producer": round(float(top.mean()), 4),
            "costly_after_a_top_producer": round(float(top[costly].mean()), 4),
            "not_costly_after_a_top_producer": round(float(top[~costly].mean()), 4)}


KEYS = ["hub", "aroute", "adir", "broute", "bdir", "band"]


def extrapolation(cells: pd.DataFrame, months: list[int] | None = None) -> dict:
    """Fit each cell's Δd on its connections planned ≥ 5 min apart; predict P(Δd ≥ m − s) for its connections planned
    2–4 min apart and compare with the share made. Assumes Δd does not depend on the planned slack."""
    c = cells if months is None else cells[pd.to_datetime(cells["date"]).dt.month.isin(months)]
    cid = c.groupby(KEYS, observed=True).ngroup().to_numpy().astype(np.int64)
    dd, slack = c["dd"].to_numpy(np.float64), c["slack"].to_numpy(np.float64)
    fit = slack >= FIT_MIN_S
    big = 10**6
    fk = np.sort(cid[fit] * big + np.clip(dd[fit], -big / 2 + 1, big / 2 - 1) + big / 2)
    nfit = np.bincount(cid[fit], minlength=cid.max() + 1)
    end = np.cumsum(nfit)
    tgt = (slack >= 120) & (slack < 300) & (nfit[cid] >= FIT_MIN_N)
    thr = cid[tgt] * big + np.clip(c["m"].to_numpy(np.float64)[tgt] - slack[tgt], -big / 2 + 1, big / 2 - 1) + big / 2
    pos = np.searchsorted(fk, thr, side="left")
    pred = (end[cid[tgt]] - pos) / nfit[cid[tgt]]
    obs = c["made"].to_numpy(np.float64)[tgt]
    smin = (slack[tgt] // 60).astype(int)
    out = {"connections_2_4": int(((slack >= 120) & (slack < 300)).sum()), "predicted": int(tgt.sum()),
           "cells_with_fit": int((nfit >= FIT_MIN_N).sum())}
    for s in (2, 3, 4):
        k = smin == s
        out[str(s)] = {"predicted": round(float(pred[k].mean()), 4), "observed": round(float(obs[k].mean()), 4),
                       "n": int(k.sum())}
    return out


def roulette(cells: pd.DataFrame) -> dict:
    allc = json.loads((DATA / "roulette-all.json").read_text())
    rng = cells.groupby(KEYS, observed=True)["slack"].agg(["min", "max"])
    ranges = {tuple(str(x) for x in k): (round(float(v["min"]) / 60, 1), round(float(v["max"]) / 60, 1))
              for k, v in rng.iterrows()}
    shown = [r for r in allc if not r["thin"]]
    key = lambda r: (r["hub"], r["a"], r["a_to"], r["b"], r["b_to"], r["band"])  # noqa: E731
    tight = [r for r in shown if 2 <= r["own_slack_median_min"] <= 4]
    tight.sort(key=lambda r: (next(k["p"] for k in r["curve"] if k["s"] == 3), key(r)))
    default = tight[(len(tight) - 1) // 2]
    s24 = cells[cells["slack"].between(120, 299.999)]
    ck = s24.groupby(KEYS, observed=True).size()
    shown_keys = {key(r) for r in shown}
    in_shown = sum(int(v) for k, v in ck.items() if tuple(str(x) for x in k) in shown_keys)
    ds.write_roulette(allc, ranges=ranges, default=key(default))
    return {"cells": len(allc), "cells_shown": len(shown), "hubs": len({r["hub"] for r in allc}),
            "hubs_shown": len({r["hub"] for r in shown}),
            "connections_share_all_slacks": round(sum(r["connections"] for r in shown) /
                                                  sum(r["connections"] for r in allc), 4),
            "connections_share_slack_2_4": round(in_shown / int(ck.sum()), 4),
            "default_rule": "median share made at 3 min among shown cells whose own median planned slack is 2–4 min",
            "tight_cells": len(tight),
            "default": {"hub": default["hub"], "a": default["a"], "a_to": default["a_to"], "b": default["b"],
                        "b_to": default["b_to"], "band": default["band"],
                        "p3": next(k for k in default["curve"] if k["s"] == 3),
                        "own_slack_median_min": default["own_slack_median_min"],
                        "connections": default["connections"]}}


def dwell() -> dict:
    """How far the stand-in dep_hat sits from B's observed departure, and the share made under each, on the
    connections planned 2–4 min apart whose planned B has an observed departure."""
    removed = set(json.loads((R / "transfers-screen.json").read_text())["hubs_removed_early_departures"])
    gaps, mh, mo = [], 0.0, 0.0
    for fc, _ in es.months():
        c = es.prepare(es.read_connections(fc, False), removed)
        c = c[c["slack"].between(120, 240) & c["q1_hub"] & c["b_od"].notna() & ~c["b_starts_here"]
              & c["made"].notna()]
        od = es.score(c.assign(delta_od=c["b_od"] - c["b_sd"]), delta="delta_od")["made"]
        gaps.append((c["b_od"] - c["b_dep_hat"]).to_numpy())
        mh += float(c["made"].sum())
        mo += float(od.sum())
    g = np.concatenate(gaps)
    return {"connections": int(len(g)), "median_od_minus_dep_hat_s": float(np.median(g)),
            "share_od_after_dep_hat": round(float((g > 0).mean()), 4),
            "made_dep_hat": round(mh / len(g), 4), "made_observed_departure": round(mo / len(g), 4)}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if "--dwell" in sys.argv:
        res = json.loads(OUT.read_text())
        res["dwell"] = dwell()
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
        print(res["dwell"])
        return
    if "--month" in sys.argv:
        fc = Path(sys.argv[sys.argv.index("--month") + 1])
        month_stage(fc, fc.with_name(fc.name.replace("connections", "btrips")))
        return
    STAGE.mkdir(parents=True, exist_ok=True)
    if "--aggregate" not in sys.argv:
        for fc, _ in es.months():
            subprocess.run([sys.executable, __file__, "--month", str(fc)], check=True)
    rng = np.random.default_rng(SEED)
    u = table("u")
    weeks = np.array(sorted(u["week"].unique()))
    W = es.draws(len(weeks), REPS, rng)
    res = {"note": "after the results, not registered (8 October 2026)", "bootstrap_draws": REPS,
           "q1_bounds": q1_bounds(u, W, weeks)}
    log.info("q1 bounds done")
    res["q1b_bounds"] = q1b_bounds(u, W, weeks)
    del u
    log.info("q1b bounds done")
    t = table("q2")
    res["q2"] = q2(t)
    res["q4_baseline"] = q4_baseline(t)
    del t
    cells = table("cells", DATA / "describe")
    for k in KEYS:
        cells[k] = cells[k].astype(str).astype("category")
    res["extrapolation"] = {"all_months": extrapolation(cells), "april_may": extrapolation(cells, [4, 5])}
    res["roulette"] = roulette(cells)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
