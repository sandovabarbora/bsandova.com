"""Screening of the delay-origins design (§3), and the segment × date × hour sums the estimate resamples.

The column delay_gain turned out to be running time against schedule (real − planned travel time), not the change in
delay, so by §3.1 the gain is recomputed as delay_to − delay_from; running time is kept as a check (gsum_run).

Writes tools/data/late/segments.parquet and docs/research/delay-origins-screen.json. The JSON holds counts and shares
of passes only; no segment's delay is summarised here.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow python tools/late/screen.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
OUT_DATA = ROOT / "tools/data/late"
OUT = ROOT / "docs/research/delay-origins-screen.json"
START, END = date(2025, 3, 15), date(2025, 9, 8)
MAX_GAIN, MIN_PASSES = 600, 1000

MODE = """CASE WHEN route_type = 'tramvaj' THEN 'tram'
               WHEN route_type = 'autobus' AND try_cast(string_split(rt_trip_id, '_')[2] AS INT) BETWEEN 100 AND 299
                    THEN 'bus' END"""

PASSES = f"""
CREATE OR REPLACE TEMP TABLE p AS
WITH c AS (
    SELECT rt_trip_id, {MODE} AS mode, string_split(rt_trip_id, '_')[2] AS route,
           gtfs_stop_sequence AS seq, stop_name AS seg_from, next_stop_name AS seg_to,
           delay_from, delay_to, delay_gain, delay_to - delay_from AS g,
           real_travel_time - planned_travel_time AS g_run, planned_travel_time, real_travel_time,
           timezone('Europe/Prague', current_stop_arrival) AS t
    FROM prague_cascade
    WHERE year = 2025 AND month = {{month}}
)
SELECT c.*, CAST(t AS DATE) AS date, hour(t) AS hour,
       seq = min(seq) OVER w OR seq = max(seq) OVER w AS terminal
FROM c
WHERE mode IS NOT NULL AND t IS NOT NULL
WINDOW w AS (PARTITION BY rt_trip_id)
"""


def excluded() -> pd.DataFrame:
    s = json.loads((ROOT / "docs/research/rain-delays-screen.json").read_text())
    rows = [(m, ln, d) for m, lines in s["exclusions"].items() for ln, ds in lines.items() for d in ds]
    return pd.DataFrame(rows, columns=["mode", "route", "date_s"])


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    for s in ("threads = 2", "memory_limit = '4GB'", "preserve_insertion_order = false",
              "max_temp_directory_size = '4GB'"):
        con.execute(f"SET {s}")
    con.register("closed", excluded())
    feed = set(json.loads((ROOT / "docs/research/rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])
    con.register("feed", pd.DataFrame({"date_s": sorted(feed)}))
    checks, months, parts = [], [], []
    for month in range(3, 10):
        con.execute(PASSES.format(month=month))
        checks.append({"month": month, **con.execute("""
            SELECT count(*) AS n,
                   count(*) FILTER (WHERE abs(delay_gain - (delay_to - delay_from)) > 1) AS off_delay,
                   count(*) FILTER (WHERE abs(delay_gain - (real_travel_time - planned_travel_time)) > 1) AS off_travel
            FROM (SELECT * FROM p WHERE delay_gain IS NOT NULL AND g IS NOT NULL) USING SAMPLE 0.1 PERCENT (bernoulli, 20261008)
        """).df().iloc[0].to_dict()})
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE k AS
            SELECT p.*, closed.route IS NOT NULL AS closure, feed.date_s IS NOT NULL AS feed_gap,
                   p.g IS NULL AS no_gain, abs(p.g) > {MAX_GAIN} AS implausible
            FROM p
            LEFT JOIN closed ON closed.mode = p.mode AND closed.route = p.route AND closed.date_s = CAST(p.date AS VARCHAR)
            LEFT JOIN feed ON feed.date_s = CAST(p.date AS VARCHAR)
            WHERE p.date BETWEEN DATE '{START}' AND DATE '{END}'""")
        months.append(con.execute("""
            SELECT mode, count(*) AS passes, avg(closure::INT) AS closure, avg(feed_gap::INT) AS feed_gap,
                   avg(no_gain::INT) AS no_gain,
                   avg(implausible::INT) FILTER (WHERE NOT closure AND NOT feed_gap AND NOT no_gain) AS implausible
            FROM k GROUP BY 1""").df().assign(month=month))
        parts.append(con.execute("""
            SELECT mode, seg_from, seg_to, date, hour, terminal,
                   count(*) AS n, sum(g) AS gsum,
                   count(*) FILTER (WHERE abs(g) <= 300) AS n300, sum(g) FILTER (WHERE abs(g) <= 300) AS gsum300,
                   count(g_run) AS n_run, sum(g_run) AS gsum_run
            FROM k WHERE NOT closure AND NOT feed_gap AND NOT no_gain AND NOT implausible
            GROUP BY ALL""").df())
    seg = pd.concat(parts, ignore_index=True)
    totals = seg.groupby(["mode", "seg_from", "seg_to"])["n"].sum()
    keep = totals[totals >= MIN_PASSES].index
    key = pd.MultiIndex.from_frame(seg[["mode", "seg_from", "seg_to"]])
    rare = seg[~key.isin(keep)]
    seg = seg[key.isin(keep)]
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    seg.to_parquet(OUT_DATA / "segments.parquet", index=False)

    stops = con.execute("""SELECT ze_zastavky AS name, avg(ze_zastavky_lat) AS lat, avg(ze_zastavky_lon) AS lon
                           FROM stop_times_history_intermediate_stops WHERE ze_zastavky_lat IS NOT NULL
                           GROUP BY 1""").df()
    stops.to_parquet(OUT_DATA / "stops.parquet", index=False)

    m = pd.concat(months)
    n = sum(c["n"] for c in checks)
    out = {
        "window": [str(START), str(END)],
        "definition_check": {"sampled": int(n),
                             "share_delay_gain_not_delay_difference": round(sum(c["off_delay"] for c in checks) / n, 4),
                             "share_delay_gain_not_travel_time_difference": round(sum(c["off_travel"] for c in checks) / n, 4),
                             "by_month": checks},
        "removed_share_by_month": {f"{r.mode} {r.month}": {"passes": int(r.passes), "closure": round(r.closure, 4),
                                                         "feed_gap": round(r.feed_gap, 4), "no_gain": round(r.no_gain, 4),
                                                         "implausible": round(r.implausible, 4)}
                                   for r in m.itertuples()},
        "rare_segments": {mode: {"segments": int(g.groupby(["seg_from", "seg_to"]).ngroups), "passes": int(g["n"].sum())}
                          for mode, g in rare.groupby("mode")},
        "kept": {mode: {"segments": int(g.groupby(["seg_from", "seg_to"]).ngroups), "passes": int(g["n"].sum()),
                        "dates": int(g["date"].nunique()),
                        "segments_with_coordinates": int(len(set(g["seg_from"]) & set(stops["name"])))}
                 for mode, g in seg.groupby("mode")},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps({k: out[k] for k in ("definition_check", "rare_segments", "kept")}, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
