"""Delay atlas: aggregate the thesis DuckDB into one small JSON the site can draw from.

Run on the machine that holds the data. Nothing leaves that machine except the JSON.

    pip install duckdb numpy            # or: uv pip install duckdb numpy
    python aggregate.py thesis.duckdb --describe
    python aggregate.py thesis.duckdb --table stop_events --route route_id --stop stop_id \
        --time ts --delay delay_s --lat stop_lat --lon stop_lon --out delay-atlas.json

Step 1 (--describe) prints every table with its columns and row count, so the column
mapping for step 2 can be chosen without guessing.

Step 2 computes, per route and per stop:
    n, mean delay, median, p90, share of events later than 60 s and 180 s,
    AR(2) coefficient sum of the within-day delay series (5-minute bins of mean delay,
    OLS on d_t ~ d_{t-1} + d_{t-2}, days pooled with day fixed effects removed by
    demeaning), which is the persistence measure of the thesis, and the number of
    days and bins it rests on.
Rows with fewer than MIN_BINS bins are still written but flagged, so the atlas can
grey them out rather than pretend.
"""

from __future__ import annotations

import argparse
import json
import sys

import duckdb
import numpy as np

BIN_MIN = 5
MIN_BINS = 200          # bins needed before an AR(2) is shown as a number
DAY_HOURS = (5, 23)     # within-day window, local time; night service excluded


def describe(con: duckdb.DuckDBPyConnection) -> None:
    for (table,) in con.execute("SHOW TABLES").fetchall():
        n = con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
        cols = con.execute(f'DESCRIBE "{table}"').fetchall()
        print(f"\n{table}  ({n:,} rows)")
        for c in cols:
            print(f"  {c[0]:32s} {c[1]}")
        sample = con.execute(f'SELECT * FROM "{table}" LIMIT 2').fetchall()
        for row in sample:
            print("  e.g.", tuple(str(v)[:24] for v in row))


def ar2(series_by_day: list[np.ndarray]) -> tuple[float | None, int]:
    """Pooled within-day AR(2): demean each day, stack lagged triples, OLS. Returns (phi1+phi2, n_bins)."""
    X, y = [], []
    for s in series_by_day:
        if len(s) < 6:
            continue
        s = s - s.mean()
        X.append(np.column_stack([s[1:-1], s[:-2]]))
        y.append(s[2:])
    if not X:
        return None, 0
    X, y = np.vstack(X), np.concatenate(y)
    if len(y) < MIN_BINS:
        return None, int(len(y))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta.sum()), int(len(y))


def aggregate(con, a) -> dict:
    t, r, s, ts, d = a.table, a.route, a.stop, a.time, a.delay
    where = f"WHERE {d} IS NOT NULL AND extract(hour FROM {ts}) BETWEEN {DAY_HOURS[0]} AND {DAY_HOURS[1] - 1}"
    base = f'FROM "{t}" {where}'
    # binned within-day series: (key, day, bin) -> mean delay
    def binned(keycol: str) -> dict[str, list[np.ndarray]]:
        rows = con.execute(f"""
            SELECT {keycol} AS k, CAST({ts} AS DATE) AS day,
                   CAST(floor((extract(hour FROM {ts})*60 + extract(minute FROM {ts})) / {BIN_MIN}) AS INT) AS b,
                   avg({d}) AS m
            {base} GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
        """).fetchall()
        out: dict[str, list[np.ndarray]] = {}
        cur, cur_day, buf = None, None, []
        for k, day, b, m in rows:
            k = str(k)
            if (k, day) != (cur, cur_day):
                if buf:
                    out.setdefault(cur, []).append(np.array(buf, dtype=float))
                cur, cur_day, buf = k, day, []
            buf.append(m)
        if buf:
            out.setdefault(cur, []).append(np.array(buf, dtype=float))
        return out

    def stats(keycol: str, extra: str = "") -> dict[str, dict]:
        rows = con.execute(f"""
            SELECT {keycol} AS k, count(*) AS n, avg({d}) AS mean, median({d}) AS p50,
                   quantile_cont({d}, 0.9) AS p90,
                   avg(CASE WHEN {d} > 60 THEN 1 ELSE 0 END) AS late60,
                   avg(CASE WHEN {d} > 180 THEN 1 ELSE 0 END) AS late180,
                   count(DISTINCT CAST({ts} AS DATE)) AS days {extra}
            {base} GROUP BY 1
        """).fetchall()
        cols = ["n", "mean", "p50", "p90", "late60", "late180", "days"] + ([c.strip() for c in extra.replace(",", " ").split() if c.strip() and c.strip().lower() not in ("as",)][1::2] if extra else [])
        return {str(r[0]): dict(zip(cols, r[1:], strict=False)) for r in rows}

    print("routes…", file=sys.stderr)
    routes = stats(r)
    for k, series in binned(r).items():
        if k in routes:
            routes[k]["ar2"], routes[k]["ar2_bins"] = ar2(series)
    print("stops…", file=sys.stderr)
    extra = f", any_value({a.lat}) AS lat, any_value({a.lon}) AS lon" if a.lat and a.lon else ""
    extra += f", any_value({a.stop_name}) AS name" if a.stop_name else ""
    stops = stats(s, extra)
    for k, series in binned(s).items():
        if k in stops:
            stops[k]["ar2"], stops[k]["ar2_bins"] = ar2(series)
    span = con.execute(f"SELECT min({ts}), max({ts}), count(*) FROM \"{t}\" WHERE {d} IS NOT NULL").fetchone()
    return {
        "source": {"table": t, "from": str(span[0]), "to": str(span[1]), "events": span[2]},
        "method": {"bin_minutes": BIN_MIN, "min_bins": MIN_BINS, "day_hours": DAY_HOURS,
                   "ar2": "pooled within-day OLS on 5-minute mean-delay bins, day-demeaned; sum of the two coefficients"},
        "routes": routes, "stops": stops,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("db")
    p.add_argument("--describe", action="store_true")
    p.add_argument("--table"); p.add_argument("--route"); p.add_argument("--stop"); p.add_argument("--time"); p.add_argument("--delay")
    p.add_argument("--lat"); p.add_argument("--lon"); p.add_argument("--stop-name", dest="stop_name")
    p.add_argument("--out", default="delay-atlas.json")
    a = p.parse_args()
    con = duckdb.connect(a.db, read_only=True)
    if a.describe or not all([a.table, a.route, a.stop, a.time, a.delay]):
        describe(con)
        if not a.describe:
            print("\nnow run again with --table --route --stop --time --delay (and --lat --lon --stop-name if there)", file=sys.stderr)
        return
    out = aggregate(con, a)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=lambda x: None if x != x else float(x))
    print(f"wrote {a.out}: {len(out['routes'])} routes, {len(out['stops'])} stops, {out['source']['events']:,} events", file=sys.stderr)


if __name__ == "__main__":
    main()
