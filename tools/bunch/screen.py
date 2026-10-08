"""Screening of the bunching design (§4), and the pair-stop tables the estimate reads.

Builds, per service month, the stop passes of trams (and city buses with --mode bus), the modal service patterns, and
the pairs of §1, and writes them to tools/data/bunch/ (never committed). docs/research/bunching-screen[-bus].json holds
counts and shares only: no headway, relative headway or birth is summarised here.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow --with numpy python tools/bunch/screen.py [--mode bus]
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
DATA = ROOT / "tools/data/bunch"
START, END = date(2025, 3, 15), date(2025, 9, 8)
H_MIN, H_MAX, H_LOW = 240.0, 900.0, 180.0  # seconds; 3–4 min pairs are kept as their own stratum (§7)
MIN_PAIRS = 1000
FILL_AGREE = 0.95  # fill from the previous row only if it agrees within 5 s on at least this share (§4.5)
log = logging.getLogger("bunch.screen")

MODE_SQL = {
    "tram": "route_type = 'tramvaj'",
    "bus": "route_type = 'autobus' AND try_cast(split_part(rt_trip_id, '_', 2) AS INT) BETWEEN 100 AND 299",
}

PASSES = """
SELECT rt_trip_id AS trip, split_part(rt_trip_id, '_', 2) AS route,
       CAST(substr(rt_trip_id, 1, 10) AS DATE) AS sdate,
       gtfs_stop_sequence AS seq, gtfs_stop_id AS stop_id, stop_name, next_gtfs_stop_id AS next_stop_id,
       next_stop_name,
       epoch(current_stop_arrival) AS sa, epoch(real_current_stop_arrival) AS oa,
       epoch(real_next_stop_arrival) AS ona, epoch(current_stop_departure) AS sd,
       epoch(real_current_stop_departure) AS od, planned_dwell_time AS pdw, real_dwell_time AS rdw
FROM stop_times_history_modeling
WHERE {mode} AND year = 2025 AND month IN ({m}, {m1}) AND rt_trip_id LIKE '2025-{mm}-%'
"""


def closures(mode: str) -> set[tuple[str, str]]:
    s = json.loads((ROOT / "docs/research/rain-delays-screen.json").read_text())
    return {(ln, d) for ln, ds in s["exclusions"].get(mode, {}).items() for d in ds}


def feed_gaps() -> set[str]:
    return set(json.loads((ROOT / "docs/research/rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])


def read_month(con: duckdb.DuckDBPyConnection, mode: str, m: int) -> pd.DataFrame:
    q = PASSES.format(mode=MODE_SQL[mode], m=m, m1=min(m + 1, 12), mm=f"{m:02d}")
    return con.execute(q).df()


def fill_check(p: pd.DataFrame) -> dict:
    """Agreement of a row's observed arrival with the previous row's observed next arrival, where both exist."""
    p = p.sort_values(["trip", "seq"])
    prev = p.groupby("trip")["ona"].shift(1)
    both = p["oa"].notna() & prev.notna()
    d = (p.loc[both, "oa"] - prev[both]).abs()
    return {"pairs_compared": int(both.sum()), "share_equal": round(float((d == 0).mean()), 4) if len(d) else None,
            "share_over_5s": round(float((d > 5).mean()), 4) if len(d) else None,
            "fillable": int((p["oa"].isna() & prev.notna()).sum())}


def apply_fill(p: pd.DataFrame) -> pd.DataFrame:
    p = p.sort_values(["trip", "seq"])
    prev = p.groupby("trip")["ona"].shift(1)
    filled = p["oa"].isna() & prev.notna()
    p["oa"] = p["oa"].where(~filled, prev)
    p["filled"] = filled
    return p


def patterns(p: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Stop list per trip (its rows plus the terminal from the last row), the modal list per (route, first, last)."""
    p = p.sort_values(["trip", "seq"])
    lists = p.groupby("trip").agg(route=("route", "first"), stops=("stop_id", tuple), last_next=("next_stop_id", "last"))
    lists["stops"] = [s + (n,) for s, n in zip(lists["stops"], lists["last_next"])]
    lists["first"] = [s[0] for s in lists["stops"]]
    lists["last"] = [s[-1] for s in lists["stops"]]
    modal = (lists.groupby(["route", "first", "last"])["stops"].agg(lambda s: Counter(s).most_common(1)[0][0])
             .rename("modal").reset_index())
    lists = lists.reset_index().merge(modal, on=["route", "first", "last"])
    lists["on_modal"] = [a == b for a, b in zip(lists["stops"], lists["modal"])]
    by_dir = lists.groupby(["route", "last"]).agg(trips=("trip", "size"), modal=("on_modal", "mean"))
    # a line × direction may run several modal patterns (different first stops); the share is per line × direction
    top = lists[lists["on_modal"]].groupby(["route", "last", "first"]).size().groupby(["route", "last"]).max()
    by_dir["one_pattern_share"] = (top / by_dir["trips"]).fillna(0)
    lists["pattern"] = [f"{r}|{f}|{l}|{len(s)}" for r, f, l, s in zip(lists["route"], lists["first"], lists["last"],
                                                                        lists["modal"])]
    info = {"trips": int(len(lists)), "on_modal_pattern": int(lists["on_modal"].sum()),
            "line_directions": int(len(by_dir)),
            "line_directions_under_90pct_one_pattern": sorted(f"{r}→{l}" for (r, l), v in
                                                              by_dir["one_pattern_share"].items() if v < 0.9)}
    return lists[lists["on_modal"]][["trip", "pattern", "modal"]], info


def pairs_for_group(g: pd.DataFrame, stops: tuple, timetable: bool = False) -> list[tuple]:
    """Pairs of §1 for one pattern on one service date; terminals excluded, positions k = 1..L−2 of the stop list."""
    inner = list(stops[1:-1])
    K = len(inner)
    if K < 2:
        return []
    trips = g["trip"].unique()
    idx = {t: i for i, t in enumerate(trips)}
    col = {s: k for k, s in enumerate(inner)}
    n = len(trips)
    OA, SA, OD = (np.full((n, K), np.nan) for _ in range(3))
    for t, s, oa, sa, od in zip(g["trip"], g["stop_id"], g["oa"], g["sa"], g["od"]):
        k = col.get(s)
        if k is not None:
            OA[idx[t], k], SA[idx[t], k], OD[idx[t], k] = oa, sa, od
    pos = np.full((n, K), np.nan)
    for k in range(K):
        obs = np.where(~np.isnan(OA[:, k]))[0]
        pos[obs[np.argsort(OA[obs, k], kind="stable")], k] = np.arange(len(obs))
    out: list[tuple] = []
    seen: set[tuple[int, int]] = set()
    if timetable:
        order = np.argsort(np.nanmin(np.where(np.isnan(SA), np.inf, SA), axis=1))
        cands = [(order[i], order[i + 1], 0) for i in range(len(order) - 1)]
    else:
        cands = []
        for k in range(K):
            obs = np.where(~np.isnan(OA[:, k]))[0]
            o = obs[np.argsort(OA[obs, k], kind="stable")]
            for a, b in zip(o[:-1], o[1:]):
                key = (min(a, b), max(a, b))
                if key in seen or OA[a, k] == OA[b, k]:
                    continue
                seen.add(key)
                cands.append((a, b, k))
    for a, b, k0 in cands:
        if timetable:
            both = ~np.isnan(SA[a]) & ~np.isnan(SA[b])
            if not both.any():
                continue
            k0 = int(np.argmax(both))
        H0 = SA[b, k0] - SA[a, k0]
        if not (H_LOW <= H0 <= H_MAX):
            continue
        for k in range(k0, K):
            if np.isnan(OA[a, k]) or np.isnan(OA[b, k]):
                out.append((a, b, k, H0, np.nan, np.nan, np.nan, 0))
                continue
            if not timetable and abs(pos[a, k] - pos[b, k]) > 1:
                break  # a third trip arrived between them: the pair ends here
            H = SA[b, k] - SA[a, k]
            tie = OA[a, k] == OA[b, k]
            hd = OD[b, k] - OD[a, k] if not (np.isnan(OD[a, k]) or np.isnan(OD[b, k])) else np.nan
            out.append((a, b, k, H0, H, (OA[b, k] - OA[a, k]) if not tie else np.nan, hd, 1 if not tie else 2))
    return [(trips[a], trips[b], k, inner[k], (inner[k - 1] if k > 0 else None), H0, H, h, hd, st)
            for a, b, k, H0, H, h, hd, st in out]


def build(mode: str) -> None:
    con = duckdb.connect(str(DB), read_only=True)
    for s in ("threads = 2", "memory_limit = '4GB'", "preserve_insertion_order = false",
              "max_temp_directory_size = '4GB'"):
        con.execute(f"SET {s}")
    closed, gaps = closures(mode), feed_gaps()
    DATA.mkdir(parents=True, exist_ok=True)
    report: dict = {"mode": mode, "window": [str(START), str(END)], "months": {}}
    stop_dwell = []
    for m in range(3, 10):
        p = read_month(con, mode, m)
        rec: dict = {"rows": int(len(p)), "trips": int(p["trip"].nunique()),
                     "duplicate_trip_seq": int(p.duplicated(["trip", "seq"]).sum())}
        p = p.drop_duplicates(["trip", "seq"])
        p = p[(p["sdate"] >= pd.Timestamp(START)) & (p["sdate"] <= pd.Timestamp(END))]
        ds = p["sdate"].dt.strftime("%Y-%m-%d")
        out_closed = [(r, d) in closed for r, d in zip(p["route"], ds)]
        out_gap = ds.isin(gaps).to_numpy()
        rec["trips_closure"] = int(p.loc[out_closed, "trip"].nunique())
        rec["trips_feed_gap"] = int(p.loc[out_gap, "trip"].nunique())
        p = p[~np.array(out_closed) & ~out_gap]
        rec["fill_check"] = fc = fill_check(p)
        do_fill = fc["share_over_5s"] is not None and 1 - fc["share_over_5s"] >= FILL_AGREE
        rec["filled"] = do_fill
        if do_fill:
            p = apply_fill(p)
        lists, info = patterns(p)
        rec["patterns"] = info
        p = p.merge(lists[["trip", "pattern"]], on="trip")
        modal = dict(zip(lists["pattern"], lists["modal"]))
        obs = p["oa"].notna()
        rec["observed_arrival_share"] = round(float(obs.mean()), 4)
        rec["arrival_equal_to_schedule_share"] = round(float((p.loc[obs, "oa"] == p.loc[obs, "sa"]).mean()), 4)
        sec = (p.loc[obs, "oa"] % 60).astype(int)
        rec["seconds_digit_share"] = {int(k): round(float(v), 4) for k, v in sec.value_counts(normalize=True).sort_index().items()}
        stop_dwell.append(pd.concat([p.groupby("stop_id")["pdw"].median().rename("pdw"),
                                     p[p["od"].notna()].groupby("stop_id")["rdw"].median().rename("rdw"),
                                     p.groupby("stop_id").size().rename("n")], axis=1))
        rows, rows_tt = [], []
        for (pat, d), g in p.groupby(["pattern", "sdate"], sort=False):
            for r in pairs_for_group(g, modal[pat]):
                rows.append((pat, d) + r)
            for r in pairs_for_group(g, modal[pat], timetable=True):
                rows_tt.append((pat, d) + r)
        cols = ["pattern", "sdate", "lead", "follow", "k", "stop_id", "prev_stop_id", "H0", "H", "h", "h_dep", "status"]
        ps = pd.DataFrame(rows, columns=cols)
        tt = pd.DataFrame(rows_tt, columns=cols)
        sa = p.set_index(["trip", "stop_id"])["sa"]
        first = ps.drop_duplicates(["pattern", "sdate", "lead", "follow"])
        hour0 = pd.to_datetime(sa.reindex(list(zip(first["lead"], first["stop_id"]))).to_numpy(), unit="s", utc=True)
        first = first.assign(hour=hour0.tz_convert("Europe/Prague").hour)
        ps = ps.merge(first[["pattern", "sdate", "lead", "follow", "hour"]], on=["pattern", "sdate", "lead", "follow"])
        ps["L"] = ps["pattern"].map(lambda x: len(modal[x]))
        tt["L"] = tt["pattern"].map(lambda x: len(modal[x]))
        name = dict(zip(p["stop_id"], p["stop_name"]))
        ps["stop_name"] = ps["stop_id"].map(name)
        ps["prev_name"] = ps["prev_stop_id"].map(name)
        ps.to_parquet(DATA / f"pairs_{mode}_{m:02d}.parquet", index=False)
        tt.to_parquet(DATA / f"pairs_tt_{mode}_{m:02d}.parquet", index=False)
        observed = ps["status"] == 1
        rec["pairs"] = int(first.shape[0])
        rec["pairs_H_3_4min"] = int((first["H0"] < H_MIN).sum())
        rec["pair_stops"] = int(len(ps))
        rec["pair_stops_observed_share"] = round(float(observed.mean()), 4)
        rec["pair_stops_tie_share"] = round(float((ps["status"] == 2).sum() / max(1, (ps["status"] > 0).sum())), 4)
        rec["pair_stops_with_departures_share"] = round(float(ps.loc[observed, "h_dep"].notna().mean()), 4)
        rec["coverage_by_hour"] = {int(h): round(float(v), 4) for h, v in ps.groupby("hour")["status"].apply(
            lambda s: (s == 1).mean()).items()}
        cov = ps.groupby("stop_id")["status"].agg(lambda s: (s == 1).mean())
        rec["stops_under_50pct_coverage"] = sorted(cov[cov < 0.5].index.tolist())
        rec["pairs_per_pattern"] = {k: int(v) for k, v in first.groupby("pattern").size().items()}
        report["months"][m] = rec
        log.info("%s %02d: %d pair-stops", mode, m, len(ps))
    per_pattern = Counter()
    for rec in report["months"].values():
        per_pattern.update(rec.pop("pairs_per_pattern"))
    thin = sorted(k for k, v in per_pattern.items() if v < MIN_PAIRS)
    report["patterns_kept"] = len(per_pattern) - len(thin)
    report["patterns_thin_removed"] = thin
    report["pairs_total"] = int(sum(per_pattern.values()))
    report["pairs_in_thin_patterns"] = int(sum(per_pattern[k] for k in thin))
    dw = pd.concat(stop_dwell).groupby(level=0).agg(pdw=("pdw", "median"), rdw=("rdw", "median"), n=("n", "sum"))
    timing = dw[((dw["rdw"] >= 1.5 * dw["pdw"]) & (dw["rdw"] >= dw["pdw"] + 20)) | (dw["pdw"] >= 60)]
    report["timing_point_stops"] = sorted(timing.index.tolist())
    pd.Series(thin, dtype=str).to_frame("pattern").to_parquet(DATA / f"thin_{mode}.parquet", index=False)
    pd.Series(sorted(timing.index), dtype=str).to_frame("stop_id").to_parquet(DATA / f"timing_{mode}.parquet",
                                                                               index=False)
    suffix = "" if mode == "tram" else f"-{mode}"
    (ROOT / f"docs/research/bunching-screen{suffix}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1, default=str) + "\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(MODE_SQL), default="tram")
    build(ap.parse_args().mode)


if __name__ == "__main__":
    main()
