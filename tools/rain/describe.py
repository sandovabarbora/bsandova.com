"""Descriptive and post-hoc numbers for the rain-delays article; none of them is a registered test.

- raw means of delay gained in rain and dry hours, by mode (no model);
- a post-hoc placebo, added 8 October 2026 after the registered placebo came out at +5.8 s: next-hour rain among hours
  that are dry now, so that rain persisting from the current hour cannot carry into it;
- δ per tram route (§8, descriptive map): y ~ rain × route | cell + date, clustered by date;
- tram route segments with stop coordinates, for the map.

Writes docs/research/rain-delays-describe.json and tools/data/rain/segments.parquet.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow --with pyfixest python tools/rain/describe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import power  # noqa: E402
from estimate import D, coef, drop_singletons, fit, frame, weather  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/research/rain-delays-describe.json"
MIN_RAIN_UNITS = 60  # routes with fewer rain units get no estimate of their own


def raw_means(units: pd.DataFrame, wx: pd.DataFrame) -> dict:
    out = {}
    for mode in ("tram", "bus", "metro"):
        d = frame(units, wx, mode, rule1="rule1" if mode != "metro" else None)
        out[mode] = {k: {"mean_s": round(float(g["y"].mean()), 2), "units": int(len(g))}
                     for k, g in (("rain", d[d["rain"]]), ("dry", d[d["dry"]]))}
    return out


def placebo_posthoc(units: pd.DataFrame, wx: pd.DataFrame) -> dict:
    d = frame(units, wx, "tram")
    s = d[d["dry"] & (d["rain_next"] | d["dry_next"])].assign(rain_next=lambda x: x["rain_next"].astype(int))
    return {**coef(fit(s, "rain_next"), ["rain_next"]), "units": int(len(s)),
            "next_rain_units": int(s["rain_next"].sum())}


def by_route(units: pd.DataFrame, wx: pd.DataFrame) -> list[dict]:
    d = frame(units, wx, "tram")
    d = drop_singletons(d[d["rain"] | d["dry"]].assign(rain=lambda x: x["rain"].astype(int)))
    counts = d[d["rain"] == 1].groupby("route").size()
    keep = counts[counts >= MIN_RAIN_UNITS].index
    d = d[d["route"].isin(keep)]
    m = pf.feols("y ~ i(route, rain) | cell + date_s", data=d, vcov={"CRV1": "date_s"})
    ci = m.confint()
    rows = []
    for term, est in m.coef().items():
        route = term.split("::")[1].split(":")[0]
        rows.append({"route": route, "est_s": round(float(est), 2), "lo": round(float(ci.loc[term].iloc[0]), 2),
                     "hi": round(float(ci.loc[term].iloc[1]), 2), "rain_units": int(counts[route])})
    return sorted(rows, key=lambda r: int(r["route"]))


def segments() -> pd.DataFrame:
    con = duckdb.connect(str(D / "prague_transit.duckdb"), read_only=True)
    con.execute("SET threads = 2")
    return con.execute("""
        SELECT DISTINCT gtfs_route_short_name AS route, ze_zastavky_lat AS lat0, ze_zastavky_lon AS lon0,
               do_zastavky_lat AS lat1, do_zastavky_lon AS lon1
        FROM stop_times_history_intermediate_stops
        WHERE route_type = 'tramvaj' AND ze_zastavky_lat IS NOT NULL AND do_zastavky_lat IS NOT NULL
    """).df()


def main() -> None:
    units = pd.read_parquet(D / "units.parquet")
    wx = weather(power.precipitation())
    res = {"raw_means": raw_means(units, wx), "placebo_posthoc": placebo_posthoc(units, wx),
           "by_route": by_route(units, wx), "min_rain_units_per_route": MIN_RAIN_UNITS}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    segments().to_parquet(D / "segments.parquet", index=False)
    print(json.dumps({k: v for k, v in res.items() if k != "by_route"}, indent=1))
    print(pd.DataFrame(res["by_route"]).to_string())


if __name__ == "__main__":
    main()
