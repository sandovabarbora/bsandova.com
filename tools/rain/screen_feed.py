"""Screening step of the rain-delays design (§3, rules 2 and 3): record timestamps and trip counts only, no delay value.

Reads the thesis's stop-level records (`stop_times_history_modeling` in tools/data/rain/prague_transit.duckdb, one
row per vehicle passing a stop, 15 March - 8 September 2025). No delay, dwell or travel-time column is selected.

- Rule 2, feed gaps: a date is excluded if no record of any mode falls into more than 60 consecutive minutes between
  05:00 and 23:00 Prague time. A record's time is its observed arrival at the stop (observed departure if arrival is
  missing).
- Rule 3, thin units: a unit (route x direction x date x clock hour, trams and city buses) with fewer than 2 trips is
  dropped. A trip counts in an hour if it has at least two records in it, the minimum for delay gained (§1).
  Each record is a segment (stop -> next stop), so direction is the next stop of the trip's highest-sequence record,
  its terminal; short turns and diversions form their own units. The route is the second field of `rt_trip_id`.

Output: docs/research/rain-delays-screen-feed.json.

    nice -n 20 uv run --with duckdb python tools/rain/screen_feed.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
OUT = ROOT / "docs/research/rain-delays-screen-feed.json"
START, END = date(2025, 3, 15), date(2025, 9, 8)
GAP_MIN = 60

# Read per month, never materialised whole: the disk has too little room to spill 121 M rows.
EVENTS = """
SELECT rt_trip_id,
       route_type,
       string_split(rt_trip_id, '_')[2] AS route,
       gtfs_stop_sequence,
       next_stop_name,
       timezone('Europe/Prague', coalesce(real_current_stop_arrival, real_current_stop_departure)) AS t
FROM stop_times_history_modeling
WHERE coalesce(real_current_stop_arrival, real_current_stop_departure) IS NOT NULL
  AND year = 2025 AND month = {month}
"""
MONTHS = range(3, 10)


def feed_gaps(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Longest run of empty minutes in 05:00-23:00 per date, from the minutes that hold at least one record."""
    con.execute("CREATE TEMP TABLE minutes (d DATE, mi TIMESTAMP)")
    for month in MONTHS:
        con.execute(f"""INSERT INTO minutes SELECT DISTINCT CAST(t AS DATE), date_trunc('minute', t)
                        FROM ({EVENTS.format(month=month)}) WHERE hour(t) BETWEEN 5 AND 22""")
    rows = con.execute(f"""
        WITH m AS (SELECT * FROM minutes),
        g AS (SELECT d, mi, lag(mi) OVER (PARTITION BY d ORDER BY mi) AS prev FROM m),
        edges AS (SELECT d, max(mi) AS last_mi, min(mi) AS first_mi FROM m GROUP BY d)
        SELECT g.d,
               greatest(coalesce(max(date_diff('minute', g.prev, g.mi)) - 1, 0),
                        date_diff('minute', CAST(g.d AS TIMESTAMP) + INTERVAL 5 HOUR, any_value(e.first_mi)),
                        date_diff('minute', any_value(e.last_mi), CAST(g.d AS TIMESTAMP) + INTERVAL 23 HOUR) - 1)
                 AS longest_gap_min
        FROM g JOIN edges e USING (d) GROUP BY g.d ORDER BY g.d
    """).fetchall()
    seen = {d: gap for d, gap in rows}
    out, d = [], START
    while d <= END:
        gap = seen.get(d)
        out.append({"date": d.isoformat(), "longest_gap_min": 18 * 60 if gap is None else int(gap),
                    "excluded": gap is None or gap > GAP_MIN})
        d += timedelta(days=1)
    return out


def thin_units(con: duckdb.DuckDBPyConnection) -> dict:
    con.execute("CREATE TEMP TABLE u (route_type VARCHAR, route VARCHAR, direction VARCHAR, day DATE, h BIGINT, trips BIGINT)")
    for month in MONTHS:
        # A trip that crosses midnight at a month's end takes its direction from the part read in that month.
        con.execute(f"""
            INSERT INTO u
            WITH ev AS ({EVENTS.format(month=month)}),
            dir AS (SELECT rt_trip_id, arg_max(next_stop_name, gtfs_stop_sequence) AS direction FROM ev GROUP BY 1),
            th AS (
                SELECT e.route_type, e.route, d.direction, CAST(e.t AS DATE) AS day, hour(e.t) AS h, e.rt_trip_id
                FROM ev e JOIN dir d USING (rt_trip_id)
                WHERE e.route_type IN ('tramvaj', 'autobus') AND hour(e.t) BETWEEN 5 AND 23
                  AND (e.route_type = 'autobus') = coalesce(try_cast(e.route AS INT) BETWEEN 100 AND 299, false)
                GROUP BY ALL HAVING count(*) >= 2
            )
            SELECT route_type, route, direction, day, h, count(*) FROM th GROUP BY ALL
        """)
    rows = con.execute("""
        SELECT route_type, count(*) AS units, count(*) FILTER (WHERE trips < 2) AS thin,
               sum(trips) AS trip_hours, sum(trips) FILTER (WHERE trips < 2) AS thin_trip_hours,
               count(DISTINCT route) AS routes, count(DISTINCT route || '|' || direction) AS route_directions
        FROM u GROUP BY 1 ORDER BY 1
    """).fetchall()
    return {mode: {"units": units, "thin_dropped": thin, "trip_hours": th, "thin_trip_hours": tth,
                   "routes": routes, "route_directions": rd}
            for mode, units, thin, th, tth, routes, rd in rows}


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("SET threads = 2")
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET preserve_insertion_order = false")
    con.execute("SET max_temp_directory_size = '4GB'")  # never fill the disk
    gaps = feed_gaps(con)
    units = thin_units(con)
    OUT.write_text(json.dumps({
        "window": [START.isoformat(), END.isoformat()],
        "rule2_gap_threshold_min": GAP_MIN,
        "rule2_dates_excluded": [g["date"] for g in gaps if g["excluded"]],
        "rule2_by_date": gaps,
        "rule3_units": units,
    }, ensure_ascii=False, indent=1))
    print(f"rule 2: {sum(g['excluded'] for g in gaps)} of {len(gaps)} dates excluded; rule 3: {units}")


if __name__ == "__main__":
    main()
