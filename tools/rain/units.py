"""Units of the rain-delays design (§1) from the thesis's stop-level records: the step that reads delay values.

One unit is a route x direction x date x clock hour (Prague time, 05:00-23:59) of trams, city buses (routes 100-299)
or the metro (negative control, §6). For each trip with at least two stop passes in the hour:
    gain = delay at its last pass in the hour - delay at its first pass in the hour   (seconds)
and the unit's outcome Y is the mean gain over those trips (§1). `level` is the mean delay over all of the unit's
passes (§6 "level instead of gain"). A pass's time is its observed arrival, or observed departure when arrival is
missing, and its delay is the delay that belongs to that same time. Route = second field of `rt_trip_id`;
direction = the trip's terminal (next stop of its highest-sequence segment). Definitions dated 8 October 2026 in
rain-delays-screen.md.

Screening flags are attached, not applied, so §6 can undo them: `rule1` (planned closure, rule as applied),
`rule1_literal` (whole-window closures too), `rule2` (feed-gap date). Rule 3 (fewer than 2 trips) is applied later,
in estimate.py, as `trips >= 2`.

Also writes route centroids from the stop coordinates (for the §6 nearest-station check).

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow python tools/rain/units.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = Path(os.environ.get("RAIN_DATA", ROOT / "tools/data/rain"))
DB = D / "prague_transit.duckdb"
SCREEN = ROOT / "docs/research/rain-delays-screen.json"
FEED = ROOT / "docs/research/rain-delays-screen-feed.json"
MONTHS = range(3, 10)

MODE = """CASE WHEN route_type = 'tramvaj' THEN 'tram'
               WHEN route_type = 'metro' THEN 'metro'
               WHEN route_type = 'autobus' AND try_cast(string_split(rt_trip_id, '_')[2] AS INT) BETWEEN 100 AND 299
                    THEN 'bus' END"""

UNITS = f"""
WITH ev AS (
    SELECT rt_trip_id,
           {MODE} AS mode,
           string_split(rt_trip_id, '_')[2] AS route,
           gtfs_stop_sequence AS seq,
           next_stop_name,
           timezone('Europe/Prague', coalesce(real_current_stop_arrival, real_current_stop_departure)) AS t,
           CASE WHEN real_current_stop_arrival IS NOT NULL THEN current_stop_arr_delay
                ELSE current_stop_dep_delay END AS delay
    FROM stop_times_history_modeling
    WHERE coalesce(real_current_stop_arrival, real_current_stop_departure) IS NOT NULL
      AND year = 2025 AND month = {{month}}
),
dir AS (SELECT rt_trip_id, arg_max(next_stop_name, seq) AS direction FROM ev GROUP BY 1),
th AS (
    SELECT e.mode, e.route, d.direction, CAST(e.t AS DATE) AS date, hour(e.t) AS hour, e.rt_trip_id,
           count(*) AS n, arg_max(e.delay, e.t) - arg_min(e.delay, e.t) AS gain, sum(e.delay) AS delay_sum
    FROM ev e JOIN dir d USING (rt_trip_id)
    WHERE e.mode IS NOT NULL AND hour(e.t) >= 5 AND e.delay IS NOT NULL
    GROUP BY ALL
)
SELECT mode, route, direction, date, hour,
       count(*) FILTER (WHERE n >= 2) AS trips,
       avg(gain) FILTER (WHERE n >= 2) AS y,
       sum(delay_sum) / sum(n) AS level
FROM th GROUP BY ALL
"""

CENTROIDS = """
SELECT gtfs_route_short_name AS route, avg(lat) AS lat, avg(lon) AS lon
FROM (SELECT DISTINCT gtfs_route_short_name, ze_zastavky, ze_zastavky_lat AS lat, ze_zastavky_lon AS lon
      FROM stop_times_history_intermediate_stops WHERE ze_zastavky_lat IS NOT NULL)
GROUP BY 1
"""


def flags(u: pd.DataFrame) -> pd.DataFrame:
    """Attach the screening flags. Rule 1 is by line and date (both directions, §3 as applied)."""
    s = json.loads(SCREEN.read_text())
    feed = json.loads(FEED.read_text())
    applied, literal = key_days(s["exclusions"]), key_days(s["exclusions_literal"])
    keys = list(zip(u["mode"], u["route"], u["date"].astype(str)))
    u["rule1"] = [k in applied for k in keys]
    u["rule1_literal"] = [k in literal for k in keys]
    u["rule2"] = u["date"].astype(str).isin(set(feed["rule2_dates_excluded"]))
    return u


def key_days(excl: dict) -> set[tuple[str, str, str]]:
    return {(m, ln, d) for m, lines in excl.items() for ln, ds in lines.items() for d in ds}


def build(db: Path = DB, months=MONTHS) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect(str(db), read_only=True)
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET preserve_insertion_order = false")
    con.execute("SET max_temp_directory_size = '4GB'")
    u = pd.concat([con.execute(UNITS.format(month=m)).df() for m in months], ignore_index=True)
    # A trip-hour split across two months' reads (midnight at a month's end) is summed back into one unit.
    u = (u.assign(ysum=u["y"].fillna(0) * u["trips"])
          .groupby(["mode", "route", "direction", "date", "hour"], as_index=False)
          .agg(trips=("trips", "sum"), ysum=("ysum", "sum"), level=("level", "mean")))
    u["y"] = u["ysum"] / u["trips"].where(u["trips"] > 0)
    u = flags(u.drop(columns="ysum"))
    return u, con.execute(CENTROIDS).df()


def main() -> None:
    u, c = build()
    u.to_parquet(D / "units.parquet", index=False)
    c.to_parquet(D / "centroids.parquet", index=False)
    print(u.groupby("mode").agg(units=("y", "size"), with_y=("y", "count")).to_string())


if __name__ == "__main__":
    main()
