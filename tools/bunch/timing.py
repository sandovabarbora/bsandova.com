"""Timing points for the §7 check, by the rule fixed on 8 October 2026: a stop whose median observed dwell (where a
departure is observed) is at least 1.5 times the network median and at least 20 s longer than it, or whose median
planned dwell is at least 60 s. Writes tools/data/bunch/timing_<mode>.parquet; dwell only, no headway.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow python tools/bunch/timing.py [bus]
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
MODE = {"tram": "route_type = 'tramvaj'",
        "bus": "route_type = 'autobus' AND try_cast(split_part(rt_trip_id, '_', 2) AS INT) BETWEEN 100 AND 299"}


def main(mode: str = "tram") -> None:
    con = duckdb.connect(str(ROOT / "tools/data/rain/prague_transit.duckdb"), read_only=True)
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '4GB'")
    d = con.execute(f"""
        SELECT gtfs_stop_id AS stop_id, median(real_dwell_time) FILTER (WHERE real_current_stop_departure IS NOT NULL)
               AS rdw, median(planned_dwell_time) AS pdw, count(*) AS n
        FROM stop_times_history_modeling
        WHERE {MODE[mode]} AND rt_trip_id >= '2025-03-15' AND rt_trip_id < '2025-09-09'
        GROUP BY 1""").df()
    net = d["rdw"].median()
    t = d[((d["rdw"] >= 1.5 * net) & (d["rdw"] >= net + 20)) | (d["pdw"] >= 60)]
    t[["stop_id"]].to_parquet(ROOT / f"tools/data/bunch/timing_{mode}.parquet", index=False)
    print(f"{mode}: network median dwell {net:.0f} s; {len(t)} of {len(d)} stops are timing points")


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["tram"]))
