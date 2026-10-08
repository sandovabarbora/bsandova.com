"""Screening of the gehl-trams design (§3): tram dwell alone, before any dwell value is joined to rain or heat.

Writes tools/data/gehl/units.parquet (route x direction x date x clock hour, mean dwell of kept passes) and
docs/research/gehl-trams-screen.json. The only weather read is the dry-hour flag, used for the margin m (§3.6), the
mean dwell of dry necessary hours; no rain or hot hour is joined to dwell.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow --with pyfixest python tools/gehl/screen.py
"""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get("RAIN_DATA", ROOT / "tools/data/rain")) / "prague_transit.duckdb"
OUT_DATA = ROOT / "tools/data/gehl"
OUT = ROOT / "docs/research/gehl-trams-screen.json"
START, END = date(2025, 3, 15), date(2025, 9, 8)
MAX_DWELL, MIN_PASSES = 180, 10
HOLIDAYS = {date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 1), date(2025, 5, 8), date(2025, 7, 5),
            date(2025, 9, 28)}


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PASSES = """
WITH p AS (
    SELECT rt_trip_id, gtfs_stop_sequence AS seq, gtfs_stop_id AS stop, next_stop_name,
           stop_name IN (SELECT name FROM centre) AS centre,
           string_split(rt_trip_id, '_')[2] AS route,
           timezone('Europe/Prague', real_current_stop_arrival) AS t,
           real_dwell_time AS d,
           epoch(real_current_stop_departure - real_current_stop_arrival) AS d_ts,
           real_current_stop_arrival IS NOT NULL AND real_current_stop_departure IS NOT NULL AS both_times
    FROM stop_times_history_modeling
    WHERE route_type = 'tramvaj' AND year = 2025 AND month = {month}
),
trip AS (SELECT rt_trip_id, min(seq) AS s0, max(seq) AS s1, arg_max(next_stop_name, seq) AS direction
         FROM p GROUP BY 1)
SELECT p.*, trip.direction, p.seq = trip.s0 OR p.seq = trip.s1 AS terminal
FROM p JOIN trip USING (rt_trip_id)
"""


def month_read(con: duckdb.DuckDBPyConnection, month: int) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    con.execute(f"CREATE OR REPLACE TEMP TABLE m AS {PASSES.format(month=month)}")
    check = con.execute("""
        SELECT count(*) AS n, count(*) FILTER (WHERE abs(d - d_ts) > 1) AS off
        FROM (SELECT d, d_ts FROM m WHERE both_times AND d IS NOT NULL) USING SAMPLE 0.1 PERCENT (bernoulli, 20261008)""").df().iloc[0].to_dict()
    rules = con.execute(f"""
        SELECT hour(t) AS hour, count(*) AS passes,
               count(*) FILTER (WHERE terminal) AS terminal,
               count(*) FILTER (WHERE NOT terminal AND NOT both_times) AS no_times,
               count(*) FILTER (WHERE NOT terminal AND both_times AND (d < 0 OR d > {MAX_DWELL} OR d IS NULL))
                   AS out_of_range,
               count(*) FILTER (WHERE NOT terminal AND both_times AND d = 0) AS zero
        FROM m WHERE t IS NOT NULL GROUP BY 1""").df().assign(month=month)
    units = con.execute(f"""
        SELECT route, direction, CAST(t AS DATE) AS date, hour(t) AS hour,
               count(*) AS passes, sum(d) AS dsum, count(*) FILTER (WHERE d > 0) AS stopped,
               sum(d) FILTER (WHERE d > 0) AS dsum_stopped,
               count(*) FILTER (WHERE centre) AS passes_centre, sum(d) FILTER (WHERE centre) AS dsum_centre
        FROM m
        WHERE NOT terminal AND both_times AND d BETWEEN 0 AND {MAX_DWELL} AND hour(t) >= 5
        GROUP BY ALL""").df()
    return units, check, rules


def inside(x: float, y: float, ring: list) -> bool:
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def centre_stops(con: duckdb.DuckDBPyConnection) -> set[str]:
    """Tram stop names whose coordinates fall in Praha 1 or Praha 2 (district outlines from the site's own map)."""
    m = json.loads((ROOT / "assets/praha/map-districts.json").read_text())
    rings = [r for f in m["features"] if f["name"] in ("Praha 1", "Praha 2") for r in f["r"]]
    stops = con.execute("""SELECT ze_zastavky AS name, avg(ze_zastavky_lat) AS lat, avg(ze_zastavky_lon) AS lon
                           FROM stop_times_history_intermediate_stops WHERE route_type = 'tramvaj'
                             AND ze_zastavky_lat IS NOT NULL GROUP BY 1""").df()
    return {n for n, la, lo in zip(stops["name"], stops["lat"], stops["lon"]) if any(inside(lo, la, r) for r in rings)}


def dispersion(u: pd.DataFrame) -> dict:
    import pyfixest as pf

    est = load("rain_estimate", "tools/rain/estimate.py")
    f = u.assign(cell=u["route"] + "|" + u["direction"] + "|" + u["hour"].astype(str) + "|" + u["weekday"].astype(str),
                 date_s=u["date"].astype(str))
    f = est.drop_singletons(f)
    fit = pf.feols("y ~ 1 | cell + date_s", data=f, weights="passes")
    f = f.assign(r=np.asarray(fit.resid()))
    c = f.groupby(["date", "hour"])["r"].mean()
    lag = c.groupby(level=0).shift(1)
    ok = lag.notna()
    return {"sigma_e_s": round(float((f["r"] - f.set_index(["date", "hour"]).index.map(c)).std()), 2),
            "sigma_c_s": round(float(c.std()), 2), "rho": round(float(np.corrcoef(c[ok], lag[ok])[0, 1]), 2),
            "units_fitted": len(f), "median_units_per_date_hour": int(f.groupby(["date", "hour"]).size().median())}


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    for s in ("threads = 2", "memory_limit = '4GB'", "preserve_insertion_order = false",
              "max_temp_directory_size = '4GB'"):
        con.execute(f"SET {s}")
    names = centre_stops(con)
    con.register("centre", pd.DataFrame({"name": sorted(names)}))
    parts, checks, rules = [], [], []
    for month in range(3, 10):
        u, c, r = month_read(con, month)
        parts.append(u), checks.append({"month": month, **c}), rules.append(r)
    u = pd.concat(parts, ignore_index=True)
    # A unit split across two months' reads (a trip crossing midnight at a month's end) is summed back into one.
    u = u.groupby(["route", "direction", "date", "hour"], as_index=False).sum(numeric_only=True)
    u["date"] = pd.to_datetime(u["date"]).dt.date
    u = u[(u["date"] >= START) & (u["date"] <= END)]
    u["y"] = u["dsum"] / u["passes"]
    u["y_stopped"] = u["dsum_stopped"] / u["stopped"].where(u["stopped"] > 0)
    u["y_centre"] = u["dsum_centre"] / u["passes_centre"].where(u["passes_centre"] > 0)
    rest = u["passes"] - u["passes_centre"]
    u["y_outer"] = (u["dsum"] - u["dsum_centre"].fillna(0)) / rest.where(rest > 0)
    u["weekday"] = [d.weekday() for d in u["date"]]
    u["holiday"] = u["date"].isin(HOLIDAYS)

    rain_units = load("rain_units", "tools/rain/units.py")
    u = rain_units.flags(u.assign(mode="tram"))
    before = len(u)
    u = u[~u["rule1"] & ~u["rule2"]]
    screened_service = before - len(u)
    small = int((u["passes"] < MIN_PASSES).sum())
    u = u[u["passes"] >= MIN_PASSES].drop(columns=["mode", "rule1_literal"])

    off = sum(c["off"] for c in checks) / max(1, sum(c["n"] for c in checks))
    r = pd.concat(rules).groupby("month").sum(numeric_only=True).drop(columns="hour")
    r_hour = pd.concat(rules).groupby("hour").sum(numeric_only=True).drop(columns="month")
    share = lambda t: {str(k): {c: round(v / row["passes"], 4) for c, v in row.items() if c != "passes"}  # noqa: E731
                       for k, row in t.iterrows()}

    power = load("rain_power", "tools/rain/power.py")
    w = power.classify(power.precipitation())
    dry = {(d, h) for d, h, x in zip(w["date"], w["hour"], w["dry"]) if x}
    nec = u[(u["weekday"] < 5) & ~u["holiday"] & u["hour"].between(6, 8)]
    nec_dry = nec[[(d, h) in dry for d, h in zip(nec["date"], nec["hour"])]]
    mean_nec_dry = float(np.average(nec_dry["y"], weights=nec_dry["passes"]))

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    u.to_parquet(OUT_DATA / "units.parquet", index=False)
    out = {
        "window": [str(START), str(END)],
        "definition_check": {"sampled": int(sum(c["n"] for c in checks)), "share_off_by_more_than_1s": round(off, 4),
                             "recomputed": off > 0.01, "by_month": checks},
        "pass_rules_share_by_month": share(r), "pass_rules_share_by_hour": share(r_hour),
        "units": {"kept": len(u), "removed_by_rain_study_screening": int(screened_service),
                  "removed_fewer_than_10_passes": small, "routes": int(u["route"].nunique()),
                  "route_directions": int(u.groupby(["route", "direction"]).ngroups), "dates": int(u["date"].nunique())},
        "centre_stops": {"rule": "stop coordinates inside the Praha 1 or Praha 2 district", "n": len(names),
                         "names": sorted(names)},
        "dispersion": dispersion(u),
        "margin": {"mean_dwell_dry_necessary_s": round(mean_nec_dry, 2), "m_s": round(0.05 * mean_nec_dry, 1),
                   "units": len(nec_dry)},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps({k: out[k] for k in ("units", "dispersion", "margin")}, indent=1, default=str))
    print("definition check:", out["definition_check"]["share_off_by_more_than_1s"])


if __name__ == "__main__":
    main()
