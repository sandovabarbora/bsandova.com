"""Prague's tram stops from the PID GTFS, and segments drawn per direction, for the delay and bunching maps."""
from __future__ import annotations

import math
from pathlib import Path

import duckdb
import pandas as pd

GTFS = Path(__file__).resolve().parents[2] / "tools" / "data" / "praha2" / "gtfs"
OFFSET = 0.00011  # degrees: the two directions of a segment drawn side by side, each on its right


def tram_stops() -> pd.DataFrame:
    """Mean position of the platforms of each stop name that trams serve, from the PID GTFS."""
    con = duckdb.connect()
    return con.execute(f"""
        WITH tram AS (SELECT DISTINCT st.stop_id
                      FROM read_csv('{GTFS}/stop_times.txt', all_varchar = true) st
                      JOIN read_csv('{GTFS}/trips.txt', all_varchar = true) t USING (trip_id)
                      JOIN read_csv('{GTFS}/routes.txt', all_varchar = true) r USING (route_id)
                      WHERE r.route_type = '0')
        SELECT s.stop_name AS name, avg(CAST(s.stop_lat AS DOUBLE)) AS lat, avg(CAST(s.stop_lon AS DOUBLE)) AS lon
        FROM read_csv('{GTFS}/stops.txt', all_varchar = true) s JOIN tram USING (stop_id)
        GROUP BY 1""").df()


def offset_line(a: tuple, b: tuple) -> list:
    (x0, y0), (x1, y1) = a, b
    k = math.cos(math.radians(50.08))
    dx, dy = (x1 - x0) * k, y1 - y0
    L = math.hypot(dx, dy) or 1
    ox, oy = dy / L * OFFSET / k, -dx / L * OFFSET  # to the right of the direction of travel
    return [[round(x0 + ox, 5), round(y0 + oy, 5)], [round(x1 + ox, 5), round(y1 + oy, 5)]]
