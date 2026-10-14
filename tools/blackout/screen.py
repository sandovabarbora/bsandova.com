"""Screening of the blackout design (§3): baseline days, feed-alive flags for 4 July, rows with delay over an hour.

Writes tools/data/blackout/bins.parquet (passes per date × mode × 10-minute bin for the event and reference days, the
input of the estimate) and docs/research/blackout-screen.json. The JSON holds flags and counts only: no ratio, pass
count or delay of 4 July is written or printed.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with pyarrow python tools/blackout/screen.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
OUT_DATA = ROOT / "tools/data/blackout"
OUT = ROOT / "docs/research/blackout-screen.json"
EVENT = "2025-07-04"
BASELINE = ["2025-07-11", "2025-07-18", "2025-07-25"]
SPARE = ["2025-08-01", "2025-08-08"]
JUNE = ["2025-06-06", "2025-06-13", "2025-06-20", "2025-06-27"]
MODES = ("tramvaj", "metro", "autobus", "trolejbus", "vlak")
ALIVE = ("autobus",)  # trains dropped after registration: most Czech lines are electric (change log, 14 Oct 2026)
SUSPECT, FLAG = 0.5, 0.8

PASSES = """
CREATE OR REPLACE TEMP TABLE p AS
SELECT route_type AS mode, stop_name AS seg_from, next_stop_name AS seg_to,
       timezone('Europe/Prague', real_next_stop_arrival) AS t, next_stop_arr_delay AS delay
FROM stop_times_history_modeling
WHERE year = 2025 AND month IN (6, 7, 8) AND real_next_stop_arrival IS NOT NULL
  AND route_type IN {modes} AND stop_name <> next_stop_name
  AND CAST(timezone('Europe/Prague', real_next_stop_arrival) AS DATE) IN ({dates})
  AND hour(timezone('Europe/Prague', real_next_stop_arrival)) BETWEEN 10 AND 21
"""

BINS = """
SELECT CAST(t AS DATE)::VARCHAR AS date, mode,
       (hour(t) - 10) * 6 + minute(t) // 10 AS bin,
       count(*) AS n, median(delay) AS d_median, avg(delay) AS d_mean
FROM p GROUP BY ALL
"""


def ratio(bins: pd.DataFrame, day: str, ref: list[str], mode: str) -> pd.Series:
    """Passes of `day` per bin over the mean of `ref` in the same bin, for one mode."""
    m = bins[bins["mode"] == mode].pivot(index="bin", columns="date", values="n").reindex(range(72)).fillna(0)
    return m[day] / m[ref].mean(axis=1)


def baseline_ok(bins: pd.DataFrame, days: list[str]) -> dict:
    """§3.2 for each candidate day against the other two."""
    out = {}
    daily = bins.groupby(["date", "mode"])["n"].sum().unstack()
    for day in days:
        others = [d for d in days if d != day]
        off = (daily.loc[day] / daily.loc[days].mean() - 1).abs()
        low = {m: int((ratio(bins, day, others, m) < 0.7).sum()) for m in ("tramvaj", "autobus")}
        out[day] = {"max_daily_deviation": round(float(off[list(MODES[:4])].max()), 4), "bins_below_0_7": low,
                    "ok": bool(off[list(MODES[:4])].max() <= 0.20 and max(low.values()) <= 6)}
    return out


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    for s in ("threads = 2", "memory_limit = '4GB'"):
        con.execute(f"SET {s}")
    days = [EVENT, *BASELINE, *SPARE, *JUNE]
    con.execute(PASSES.format(modes=MODES, dates=", ".join(f"DATE '{d}'" for d in days)))
    bins = con.execute(BINS).df()
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    bins.to_parquet(OUT_DATA / "bins.parquet", index=False)

    # §3.2: replace a rejected baseline day by the spares in order, until three pass
    checked, base, pool = {}, list(BASELINE), list(SPARE)
    while True:
        checked.update(baseline_ok(bins, base))
        bad = [d for d in base if not checked[d]["ok"]]
        if not bad or not pool:
            break
        base = [d for d in base if d != bad[0]] + [pool.pop(0)]

    # §3.1: flags only
    worst = pd.concat([ratio(bins, EVENT, base, m) for m in ALIVE], axis=1).min(axis=1)
    flag = pd.Series("ok", index=worst.index).mask(worst < FLAG, "flagged").mask(worst < SUSPECT, "feed-suspect")
    label = [f"{10 + b // 6:02d}:{b % 6 * 10:02d}" for b in flag.index]
    long_delay = con.execute(f"""SELECT mode, count(*) FROM p WHERE abs(delay) > 3600
                                 AND CAST(t AS DATE) = DATE '{EVENT}' GROUP BY 1""").fetchall()
    out = {"event": EVENT, "baseline_days": base, "baseline_checks": checked,
           "feed_flags": {lb: f for lb, f in zip(label, flag) if f != "ok"},
           "feed_bins_ok": int((flag == "ok").sum()),
           "event_passes_delay_over_1h": {m: int(n) for m, n in long_delay}}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
