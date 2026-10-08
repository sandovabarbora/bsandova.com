"""Screening of the transfers design (§4), and the connection tables the estimate reads.

Reads tram stop passes month by month, finds the hubs and platform pairs (§1), builds every planned connection of
line A to line B at a hub (§1), and writes tools/data/transfer/ (never committed). docs/research/transfers-screen.json
holds counts and shares only: no connection is scored as made or missed here, and no delay is summarised.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow --with numpy python tools/transfer/screen.py
"""
from __future__ import annotations

import json
import logging
import math
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
GTFS = ROOT / "tools/data/praha2/gtfs/stops.txt"
DATA = ROOT / "tools/data/transfer"
OUT = ROOT / "docs/research/transfers-screen.json"
START, END = date(2025, 3, 15), date(2025, 9, 8)
HOLIDAYS = {date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 1), date(2025, 5, 8), date(2025, 7, 5),
            date(2025, 9, 28)}
SUMMER = (date(2025, 6, 28), date(2025, 8, 31))
MAX_PAIR_M, WALK, BASE_M = 250.0, 1.2, 60.0
MIN_LINES, MIN_PASSES = 4, 20
MAX_SLACK = 10 * 60  # the roulette's longest slack; connections planned further apart are not kept
FILL_AGREE = 0.95
EARLY_S, EARLY_SHARE = 30, 0.05
log = logging.getLogger("transfer.screen")

# One row per arrival or departure of a tram at a stop. A trip's terminal arrival is not a row of its own in the
# table: it is the last row's "next stop", so it is added from there (an A that ends at a hub is kept, §4.5).
PASSES = """
WITH r AS (
    SELECT rt_trip_id AS trip, split_part(rt_trip_id, '_', 2) AS route,
           CAST(substr(rt_trip_id, 1, 10) AS DATE) AS sdate, gtfs_stop_sequence AS seq,
           gtfs_stop_id AS stop_id, stop_name, next_gtfs_stop_id AS next_stop_id, next_stop_name,
           epoch(current_stop_arrival) AS sa, epoch(real_current_stop_arrival) AS oa,
           epoch(current_stop_departure) AS sd, epoch(real_current_stop_departure) AS od,
           epoch(next_stop_arrival) AS nsa, epoch(real_next_stop_arrival) AS ona
    FROM stop_times_history_modeling
    WHERE route_type = 'tramvaj' AND year = 2025 AND month IN ({m}, {m1}) AND rt_trip_id LIKE '2025-{mm}-%'
),
d AS (SELECT DISTINCT ON (trip, seq) * FROM r),
w AS (
    SELECT *, lag(stop_name) OVER t AS prev_name, lag(ona) OVER t AS prev_ona, lag(sa) OVER t AS prev_sa,
           lag(oa) OVER t AS prev_oa, seq = min(seq) OVER a AS first_row, seq = max(seq) OVER a AS last_row,
           last_value(next_stop_name) OVER (PARTITION BY trip ORDER BY seq
               ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS terminal
    FROM d WINDOW t AS (PARTITION BY trip ORDER BY seq), a AS (PARTITION BY trip)
)
SELECT trip, route, sdate, stop_id, stop_name, prev_name, next_stop_name, terminal,
       sa, oa, sd, od, prev_ona, prev_sa, prev_oa, first_row, FALSE AS terminal_arrival
FROM w
UNION ALL
SELECT trip, route, sdate, next_stop_id, next_stop_name, stop_name, NULL, terminal,
       nsa, ona, NULL, NULL, NULL, sa, oa, FALSE, TRUE
FROM w WHERE last_row
"""


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


def day_type(d: date) -> str:
    if d.weekday() == 6 or d in HOLIDAYS:
        return "sunday"
    return "saturday" if d.weekday() == 5 else "weekday"


def period(d: date) -> str:
    """Timetable period for the missing-trip count (§4.3): the day type, in or out of the summer timetable."""
    summer = SUMMER[0] <= d <= SUMMER[1]
    return f"{day_type(d)}|{'summer' if summer else 'term'}"


def hour_band(d: date, hour: int) -> str:
    if hour >= 20 or hour < 5:
        return "evening"
    if day_type(d) != "weekday":
        return "weekend"
    if hour in (7, 8, 15, 16, 17):
        return "peak"
    return "daytime"


def connect() -> tuple[duckdb.DuckDBPyConnection, set, set]:
    con = duckdb.connect(str(DB), read_only=True)
    for s in ("threads = 2", "memory_limit = '4GB'", "preserve_insertion_order = false",
              "max_temp_directory_size = '4GB'"):
        con.execute(f"SET {s}")
    rs = json.loads((ROOT / "docs/research/rain-delays-screen.json").read_text())
    closed = {(ln, d) for ln, ds in rs["exclusions"].get("tram", {}).items() for d in ds}
    gaps = set(json.loads((ROOT / "docs/research/rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])
    return con, closed, gaps


def read_month(con, m: int, closed: set, gaps: set) -> tuple[pd.DataFrame, dict]:
    p = con.execute(PASSES.format(m=m, m1=min(m + 1, 12), mm=f"{m:02d}")).df()
    p = p[(p["sdate"] >= pd.Timestamp(START)) & (p["sdate"] <= pd.Timestamp(END))]
    ds = p["sdate"].dt.strftime("%Y-%m-%d")
    out = np.array([(r, d) in closed for r, d in zip(p["route"], ds)]) | ds.isin(gaps).to_numpy()
    rec = {"rows": int(len(p)), "rows_closure_or_feed_gap": int(out.sum())}
    p = p[~out].copy()
    both = p["oa"].notna() & p["prev_ona"].notna() & ~p["terminal_arrival"]
    diff = (p.loc[both, "oa"] - p.loc[both, "prev_ona"]).abs()
    agree = float((diff <= 5).mean()) if len(diff) else 0.0
    rec["fill_check"] = {"compared": int(both.sum()), "share_within_5s": round(agree, 4)}
    fill = p["oa"].isna() & p["prev_ona"].notna() & ~p["terminal_arrival"]
    rec["filled"] = agree >= FILL_AGREE
    if rec["filled"]:
        p.loc[fill, "oa"] = p.loc[fill, "prev_ona"]
        rec["arrivals_filled"] = int(fill.sum())
    return p, rec


def scheduled_counts(p: pd.DataFrame) -> pd.DataFrame:
    """Scheduled passes per stop name × line × date (departures, and terminal arrivals), for the hub rule."""
    return p.groupby(["stop_name", "route", "sdate"]).size().rename("n").reset_index()


def find_hubs(counts: pd.DataFrame) -> dict[str, list[str]]:
    weekdays = [d for d in (START + timedelta(i) for i in range((END - START).days + 1)) if day_type(d) == "weekday"]
    c = counts[counts["sdate"].dt.date.map(day_type) == "weekday"]
    full = c.set_index(["stop_name", "route", "sdate"])["n"].unstack(fill_value=0)
    full = full.reindex(columns=pd.to_datetime(weekdays), fill_value=0)
    med = full.median(axis=1)
    lines = med[med >= MIN_PASSES].reset_index().groupby("stop_name")["route"].apply(sorted)
    return {k: v for k, v in lines.items() if len(v) >= MIN_LINES}


def platforms() -> pd.DataFrame:
    s = pd.read_csv(GTFS, dtype=str)
    s = s[s["location_type"].fillna("0") == "0"]
    return s.set_index("stop_id")[["stop_name", "stop_lat", "stop_lon"]].astype({"stop_lat": float, "stop_lon": float})


def build_connections(p: pd.DataFrame, hubs: dict, plat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Planned connections of §1, plus each B line's trips at its platform, for one month of passes.

    Returns the connections, the B trips (for the donors of §2), and counts for the screen."""
    p = p[p["stop_name"].isin(hubs.keys())].copy()
    p["date"] = p["sdate"].dt.date
    known = p["stop_id"].isin(plat.index)
    cnt = defaultdict(int)
    cnt["hub_rows"] = int(len(p))
    cnt["hub_rows_platform_unknown"] = int((~known).sum())
    p = p[known]
    xy = {k: (r.stop_lat, r.stop_lon) for k, r in plat.iterrows()}
    dist_cache: dict[tuple[str, str], float] = {}

    def dist(a: str, b: str) -> float:
        if (a, b) not in dist_cache:
            dist_cache[(a, b)] = 0.0 if a == b else haversine(*xy[a], *xy[b])
        return dist_cache[(a, b)]

    arrivals = p[~p["first_row"] & p["sa"].notna()]  # an A that starts at the hub has not arrived from anywhere
    departures = p[~p["terminal_arrival"] & p["sd"].notna()].copy()  # a B ending at the hub does not leave from it
    departures["starts_here"] = departures["first_row"]
    departures["dep_hat"] = np.where(
        departures["starts_here"],
        departures["od"].fillna(departures["sd"]),
        np.fmax(departures["oa"], departures["sd"]).where(departures["oa"].notna()))
    departures["early"] = departures["od"] < departures["sd"] - EARLY_S
    a_cols = ["sa", "oa", "prev_sa", "prev_oa", "terminal_arrival"]
    a_groups = {}
    for (d, hub, route, term, stop), a in arrivals.groupby(["date", "stop_name", "route", "terminal", "stop_id"],
                                                         sort=False):
        a_groups.setdefault((d, hub), []).append(
            ((route, term, stop, a["prev_name"].iloc[0], a["next_stop_name"].iloc[0]),
             {k: a[k].to_numpy() for k in a_cols}))
    parts: dict[str, list] = defaultdict(list)
    meta: list[tuple] = []
    btrips = []
    for (d, hub, broute, bterm, bstop), b in departures.groupby(["date", "stop_name", "route", "terminal", "stop_id"],
                                                               sort=False):
        b = b.sort_values("sd")
        bsd, bdh, boa, bod = (b[c].to_numpy() for c in ("sd", "dep_hat", "oa", "od"))
        bstart = b["starts_here"].to_numpy()
        bnext = b["next_stop_name"].iloc[0]
        bkey = f"{broute}|{bterm}|{bstop}"
        btrips.append(pd.DataFrame({"date": d, "hub": hub, "bkey": bkey, "sd": bsd, "dep_hat": bdh, "od": bod,
                                    "starts_here": bstart}))
        for (aroute, aterm, astop, aprev, anext), a in a_groups.get((d, hub), []):
            if aroute == broute:
                continue
            excluded = bnext is not None and (bnext == aprev or bnext == anext)  # kept, flagged (§7)
            dd = dist(astop, bstop)
            if dd > MAX_PAIR_M:
                continue
            m = BASE_M + dd / WALK
            sa = a["sa"]
            j = np.searchsorted(bsd, sa + m, side="left")
            ok = j < len(bsd)
            jj = np.where(ok, j, 0)
            slack = np.where(ok, bsd[jj] - sa, np.nan)
            k = np.flatnonzero(ok & (slack <= MAX_SLACK))
            if not len(k):
                continue
            n = len(k)
            if excluded:
                cnt["excluded_return_or_trunk"] += n
                cnt[f"excluded|{hub}|{aroute}>{broute}"] += n
            meta.append((d, hub, f"{aroute}|{aterm}|{astop}", bkey, aroute, broute, n))
            for col, val in (("dist_m", np.full(n, dd)), ("m", np.full(n, m)), ("a_sa", sa[k]), ("a_oa", a["oa"][k]),
                             ("a_prev_sa", a["prev_sa"][k]), ("a_prev_oa", a["prev_oa"][k]),
                             ("a_terminal_arrival", a["terminal_arrival"][k]), ("b_idx", jj[k]),
                             ("b_sd", bsd[jj[k]]), ("b_dep_hat", bdh[jj[k]]), ("b_oa", boa[jj[k]]),
                             ("b_od", bod[jj[k]]), ("b_starts_here", bstart[jj[k]]), ("slack", slack[k]),
                             ("excluded", np.full(n, excluded))):
                parts[col].append(val)
    if parts:
        reps = np.array([x[-1] for x in meta])
        text = {c: np.repeat(np.array([x[i] for x in meta], dtype=object), reps)
                for i, c in enumerate(("date", "hub", "akey", "bkey", "aroute", "broute"))}
        conns = pd.DataFrame({**text, **{c: np.concatenate(v) for c, v in parts.items()}})
    else:
        conns = pd.DataFrame()
    bt = pd.concat(btrips, ignore_index=True) if btrips else pd.DataFrame()
    early = departures[departures["od"].notna() & ~departures["starts_here"]].groupby("stop_name")["early"].agg(
        ["sum", "count"])
    return conns, bt, {"counts": dict(cnt), "early": early}


def missing_trips(counts_hour: pd.DataFrame) -> pd.DataFrame:
    """§4.3: trips per hub × line × hour × date against the modal count in the same period; returns the shortfalls."""
    c = counts_hour.copy()
    c["period"] = c["sdate"].dt.date.map(period)
    mode = c.groupby(["stop_name", "route", "hour", "period"])["n"].agg(lambda s: s.mode().max()).rename("expected")
    c = c.merge(mode.reset_index(), on=["stop_name", "route", "hour", "period"])
    c["missing"] = (c["expected"] - c["n"]).clip(lower=0)
    return c


def precision(per_week: pd.Series, icc: float = 0.01) -> dict:
    """§4.8 from counts alone. Δp_within is a mean of per-connection differences made − p_within, each with variance
    at most 0.25 (p = 0.5, the worst case); connections in the same ISO week share conditions, so the variance is
    inflated by 1 + (n̄ − 1) · ICC with an assumed intraclass correlation of 0.01, stated here because counts alone
    cannot give it."""
    n = int(per_week.sum())
    nbar = float((per_week ** 2).sum() / n)
    se = (0.25 / n * (1 + (nbar - 1) * icc)) ** 0.5
    return {"connections": n, "weeks": int(len(per_week)), "assumed_icc": icc, "se_points": round(100 * se, 3),
            "ci95_width_points": round(100 * 3.92 * se, 3), "mde_points_80pct": round(100 * 2.80 * se, 3),
            "underpowered": 2.80 * se > 0.03}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    con, closed, gaps = connect()
    DATA.mkdir(parents=True, exist_ok=True)
    rep: dict = {"window": [str(START), str(END)], "months": {}}
    counts, hourly = [], []
    for m in range(3, 10):
        p, rec = read_month(con, m, closed, gaps)
        counts.append(scheduled_counts(p))
        t = pd.to_datetime(p["sd"].fillna(p["sa"]), unit="s", utc=True).dt.tz_convert("Europe/Prague")
        hourly.append(p.assign(hour=t.dt.hour).groupby(["stop_name", "route", "sdate", "hour"]).size()
                      .rename("n").reset_index())
        p.to_parquet(DATA / f"passes_{m:02d}.parquet", index=False)
        rep["months"][m] = rec
        log.info("month %s read", m)
    counts = pd.concat(counts).groupby(["stop_name", "route", "sdate"], as_index=False)["n"].sum()
    hubs = find_hubs(counts)
    plat = platforms()
    rep["hubs"] = {h: {"lines": v} for h, v in sorted(hubs.items())}
    hub_counts = pd.concat(hourly).groupby(["stop_name", "route", "sdate", "hour"], as_index=False)["n"].sum()
    hub_counts = hub_counts[hub_counts["stop_name"].isin(hubs)]
    miss = missing_trips(hub_counts)
    miss.to_parquet(DATA / "missing.parquet", index=False)
    miss["month"] = miss["sdate"].dt.month
    by = miss.groupby(["stop_name", "month"])[["missing", "expected"]].sum()
    rep["missing_trip_share_by_hub_month"] = {f"{h}|{mo}": round(float(r.missing / r.expected), 4)
                                              for (h, mo), r in by.iterrows() if r.expected}
    rep["missing_trip_share"] = round(float(miss["missing"].sum() / miss["expected"].sum()), 4)
    totals, early, weekly = defaultdict(int), [], []
    platform_pairs: dict = defaultdict(set)
    for m in range(3, 10):
        p = pd.read_parquet(DATA / f"passes_{m:02d}.parquet")
        t0 = time.monotonic()
        conns, bt, info = build_connections(p, hubs, plat)
        for k, v in info["counts"].items():
            totals[k] += v
        early.append(info["early"])
        if not conns.empty:
            for (h, a, b, dist), _ in conns.groupby(["hub", "akey", "bkey", "dist_m"]):
                platform_pairs[h].add((a.split("|")[2], b.split("|")[2], round(dist), round(BASE_M + dist / WALK)))
            conns.to_parquet(DATA / f"connections_{m:02d}.parquet", index=False)
            bt.to_parquet(DATA / f"btrips_{m:02d}.parquet", index=False)
            weekly.append(conns[~conns["excluded"] & conns["slack"].between(120, 240) & conns["a_oa"].notna()]
                          .assign(week=pd.to_datetime(conns["date"]).dt.isocalendar().week)[["hub", "week"]])
            totals["connections"] += int((~conns["excluded"]).sum())
            totals["connections_slack_2_4"] += int((~conns["excluded"] & conns["slack"].between(120, 240)).sum())
            totals["connections_a_unobserved"] += int(conns["a_oa"].isna().sum())
            totals["connections_b_unobserved"] += int(conns["b_dep_hat"].isna().sum())
            totals["connections_b_starts_here"] += int(conns["b_starts_here"].sum())
            totals["connections_a_ends_here"] += int(conns["a_terminal_arrival"].sum())
        log.info("month %s: %s connections in %.0f s", m, len(conns), time.monotonic() - t0)
    e = pd.concat(early).groupby(level=0).sum()
    e["share"] = e["sum"] / e["count"]
    rep["early_departure_share_by_hub"] = {h: {"observed_departures": int(r["count"]), "share": round(float(r.share), 4)}
                                           for h, r in e.iterrows()}
    rep["hubs_removed_early_departures"] = sorted(h for h, r in e.iterrows() if r.share > EARLY_SHARE)
    rep["platform_pairs"] = {h: sorted(v) for h, v in platform_pairs.items()}
    wk = pd.concat(weekly)
    wk = wk[~wk["hub"].isin(rep["hubs_removed_early_departures"])].groupby("week").size()
    rep["precision"] = precision(wk)
    rep["excluded_return_or_trunk_by_hub_pair"] = {k.split("|", 1)[1]: v for k, v in totals.items()
                                                   if k.startswith("excluded|")}
    rep["counts"] = {k: v for k, v in totals.items() if not k.startswith("excluded|")}
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps({k: rep[k] for k in ("counts", "missing_trip_share", "hubs_removed_early_departures",
                                          "precision")},
                     ensure_ascii=False, indent=1))
    print("hubs:", len(hubs))


if __name__ == "__main__":
    main()
