"""Screening addendum of the gehl-trams design: does weather change which tram passes have a measured dwell?

Dwell exists only where a departure was detected (about half of the passes, varying by stop). If detection depended on
rain or heat, the units' mix of stops would shift with the weather. This counts, per date and hour, the non-terminal
tram passes and those with both observed times, and compares the share across rain, dry, hot and mild hours, overall
and within dates. No dwell value is selected.

    nice -n 20 uv run --with duckdb --with pandas --with pyarrow python tools/gehl/coverage.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
OUT = ROOT / "docs/research/gehl-trams-coverage.json"

COUNTS = """
WITH p AS (
    SELECT rt_trip_id, gtfs_stop_sequence AS seq, timezone('Europe/Prague', real_current_stop_arrival) AS t,
           real_current_stop_departure IS NOT NULL AS has_dep
    FROM stop_times_history_modeling
    WHERE route_type = 'tramvaj' AND year = 2025 AND month = {month} AND real_current_stop_arrival IS NOT NULL
),
trip AS (SELECT rt_trip_id, min(seq) AS s0, max(seq) AS s1 FROM p GROUP BY 1)
SELECT CAST(t AS DATE) AS date, hour(t) AS hour, count(*) AS passes, count(*) FILTER (WHERE has_dep) AS measured
FROM p JOIN trip USING (rt_trip_id)
WHERE seq <> s0 AND seq <> s1
GROUP BY ALL
"""


def main() -> None:
    spec = importlib.util.spec_from_file_location("heat_power", ROOT / "tools/heat/power.py")
    hp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hp)
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("SET threads = 2")
    n = pd.concat([con.execute(COUNTS.format(month=m)).df() for m in range(3, 10)])
    n = n.groupby(["date", "hour"], as_index=False).sum()
    n["date"] = pd.to_datetime(n["date"]).dt.date
    w = hp.classify().reset_index(drop=True)[["date", "hour", "rain", "dry", "hot", "mild"]]
    d = n.merge(w, on=["date", "hour"])
    d["share"] = d["measured"] / d["passes"]

    def pooled(mask: pd.Series) -> dict:
        s = d[mask]
        return {"hours": int(len(s)), "share": round(float(s["measured"].sum() / s["passes"].sum()), 4)}

    def within(a: str, b: str) -> dict:
        s = d[d[a] | d[b]].copy()
        s["dev"] = s["share"] - s.groupby("date")["share"].transform("mean")
        both = s.groupby("date")[a].transform("any") & s.groupby("date")[b].transform("any")
        s = s[both]
        diff = s[s[a]]["dev"].mean() - s[s[b]]["dev"].mean()
        return {"dates": int(s["date"].nunique()), "difference_points": round(100 * float(diff), 2)}

    out = {"rain": pooled(d["rain"]), "dry": pooled(d["dry"]), "hot": pooled(d["hot"]), "mild": pooled(d["mild"]),
           "rain_minus_dry_within_dates": within("rain", "dry"), "hot_minus_mild_within_dates": within("hot", "mild")}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
