"""Descriptive companions to the delay-origins estimate, computed after the results and not registered.

- Tram volume: the share of all tram passes on the tenth of segments with the most passes, which is also the top-tenth
  share S would take if every segment had the same mean gain per pass.
- Early and holding: a tram that reaches a stop early and waits for its scheduled departure gains delay (−60 → 0 s
  is +60 s) without ever being late. The cascade is read again with the screening rules (trams, closures, feed gaps,
  |g| ≤ 600 s, kept segments) to split each segment's gain into lateness made, max(delay_to, 0) − max(delay_from, 0),
  and the gain on passes that started early. Cached in tools/data/late/early.parquet.
- The concentration curve and its Gini; the overlap of the top tenth between odd and even ISO weeks; peaks against
  middays among the top producers; the six large stops (chosen after seeing the top list); running time; recoverers.

Writes docs/research/delay-origins-describe.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with duckdb python tools/late/describe.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/late"
OUT = ROOT / "docs/research/delay-origins-describe.json"
NODES = ["Václavské náměstí", "Anděl", "Hlavní nádraží", "Kobylisy", "Karlovo náměstí", "Palmovka"]
PEAK, MIDDAY = set(range(7, 9)) | set(range(15, 18)), set(range(10, 14))

EARLY = """
WITH c AS (
    SELECT string_split(rt_trip_id, '_')[2] AS route, stop_name AS seg_from, next_stop_name AS seg_to,
           delay_from, delay_to, delay_to - delay_from AS g,
           CAST(timezone('Europe/Prague', current_stop_arrival) AS DATE) AS date
    FROM prague_cascade
    WHERE year = 2025 AND month = {month} AND route_type = 'tramvaj' AND current_stop_arrival IS NOT NULL
)
SELECT c.seg_from, c.seg_to, count(*) AS n, sum(g) AS g,
       sum(greatest(delay_to, 0) - greatest(delay_from, 0)) AS late,
       sum(g) FILTER (WHERE delay_from < 0) AS g_early, count(*) FILTER (WHERE delay_from < 0) AS n_early,
       sum(delay_from) AS from_sum
FROM c
JOIN kept USING (seg_from, seg_to)
LEFT JOIN closed ON closed.route = c.route AND closed.date_s = CAST(c.date AS VARCHAR)
LEFT JOIN feed ON feed.date_s = CAST(c.date AS VARCHAR)
WHERE c.date BETWEEN DATE '2025-03-15' AND DATE '2025-09-08' AND closed.route IS NULL AND feed.date_s IS NULL
  AND g IS NOT NULL AND abs(g) <= 600
GROUP BY ALL
"""


def early_table(kept: pd.DataFrame) -> pd.DataFrame:
    cache = DATA / "early.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    s = json.loads((ROOT / "docs/research/rain-delays-screen.json").read_text())
    closed = pd.DataFrame([(ln, d) for ln, ds in s["exclusions"]["tram"].items() for d in ds], columns=["route", "date_s"])
    feed = json.loads((ROOT / "docs/research/rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"]
    con = duckdb.connect(str(ROOT / "tools/data/rain/prague_transit.duckdb"), read_only=True)
    for x in ("threads = 2", "memory_limit = '4GB'", "preserve_insertion_order = false"):
        con.execute(f"SET {x}")
    con.register("kept", kept)
    con.register("closed", closed)
    con.register("feed", pd.DataFrame({"date_s": feed}))
    parts = [con.execute(EARLY.format(month=m)).df() for m in range(3, 10)]
    e = pd.concat(parts).groupby(["seg_from", "seg_to"], as_index=False).sum(numeric_only=True)
    e.to_parquet(cache, index=False)
    return e


def top(series: pd.Series, k: int) -> set:
    return set(series.sort_values(ascending=False).head(k).index)


def main() -> None:
    s = pd.read_parquet(DATA / "segments.parquet")
    out = {"note": "computed after the results; descriptive, not registered"}
    for mode, g in s.groupby("mode"):
        t = g.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum()
        k = math.ceil(0.10 * len(t))
        busiest = t.sort_values("n", ascending=False).head(k)
        by_total = t.sort_values("gsum", ascending=False).head(k)
        out[mode] = {
            "segments": len(t),
            "top_tenth_pass_share": round(float(busiest["n"].sum() / t["n"].sum()), 4),
            "top_tenth_by_delay_pass_share": round(float(by_total["n"].sum() / t["n"].sum()), 4),
            "overlap_busiest_and_largest_producers": round(len(set(busiest.index) & set(by_total.index)) / k, 4),
        }
    g = s[s["mode"] == "tram"]
    t = g.groupby(["seg_from", "seg_to"])[["gsum", "n", "gsum_run", "n_run"]].sum()
    k = math.ceil(0.10 * len(t))
    tram = out["tram"]

    # concentration curve over all segments, recoverers counted as zero
    made = np.sort(np.clip(t["gsum"].to_numpy(), 0, None))[::-1]
    cum = np.concatenate([[0], np.cumsum(made) / made.sum()])
    x = np.arange(len(made) + 1) / len(made)
    asc = np.sort(np.clip(t["gsum"].to_numpy(), 0, None))
    gini = 1 - 2 * np.sum((np.cumsum(asc) - asc / 2) / asc.sum()) / len(asc)
    tram["curve"] = [[round(float(a), 4), round(float(b), 4)] for a, b in zip(x[::6], cum[::6])] + [[1.0, 1.0]]
    tram["gini_made"] = round(float(gini), 3)

    # overlap of the top tenth between odd and even ISO weeks
    wk = pd.to_datetime(g["date"]).dt.isocalendar().week.to_numpy() % 2 == 1
    half = {h: g[wk == (h == "odd")].groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum() for h in ("odd", "even")}
    tram["top_overlap_odd_even"] = {
        "by_total": round(len(top(half["odd"]["gsum"], k) & top(half["even"]["gsum"], k)) / k, 4),
        "by_per_pass": round(len(top(half["odd"]["gsum"] / half["odd"]["n"], k)
                                 & top(half["even"]["gsum"] / half["even"]["n"], k)) / k, 4)}

    # peaks against middays among the top producers by total
    wd = pd.to_datetime(g["date"]).dt.weekday < 5
    pk = g[wd & g["hour"].isin(PEAK)].groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum()
    md = g[wd & g["hour"].isin(MIDDAY)].groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum()
    tops = list(top(t["gsum"], k))
    tram["top_producers_peak_vs_midday_per_pass"] = {
        "peak": round(float(pk.loc[tops, "gsum"].sum() / pk.loc[tops, "n"].sum()), 2),
        "midday": round(float(md.loc[tops, "gsum"].sum() / md.loc[tops, "n"].sum()), 2)}
    a, b = top(pk["gsum"] / pk["n"], k), top(md["gsum"] / md["n"], k)
    tram["peak_midday_top_tenth_shared"] = round(len(a & b) / k, 4)

    # the six large stops, chosen after seeing the top list
    tt = t.reset_index()
    rows = []
    for node in NODES:
        for side, sub in (("arriving", tt[tt["seg_to"] == node]), ("leaving", tt[tt["seg_from"] == node])):
            if len(sub):
                rows.append({"stop": node, "side": side, "segments": len(sub), "passes": int(sub["n"].sum()),
                             "per_pass_s": round(float(sub["gsum"].sum() / sub["n"].sum()), 2)})
    tram["large_stops"] = rows
    tram["top_producers_leaving_the_six"] = int(sum(f in NODES for f, _ in tops))

    # running time, recoverers, net
    run = t[t["n_run"] > 0]
    tram["running_time"] = {"segments_with": len(run), "segments_without": int((t["n_run"] == 0).sum()),
                            "losing_time": int((run["gsum_run"] > 0).sum()),
                            "total_h": round(float(run["gsum_run"].sum() / 3600))}
    tram["recoverers"] = {"segments": int((t["gsum"] < 0).sum()), "share": round(float((t["gsum"] < 0).mean()), 4)}
    tram["september_dates"] = int(g.loc[pd.to_datetime(g["date"]).dt.month == 9, "date"].nunique())

    # early and holding
    e = early_table(t.reset_index()[["seg_from", "seg_to"]]).set_index(["seg_from", "seg_to"])
    et = e.loc[tops]
    late_made = np.sort(np.clip(e["late"].to_numpy(), 0, None))[::-1]
    tram["early_and_holding"] = {
        "passes": int(e["n"].sum()),
        "net_gain_h": round(float(e["g"].sum() / 3600)),
        "net_lateness_made_h": round(float(e["late"].sum() / 3600)),
        "share_of_passes_starting_early": round(float(e["n_early"].sum() / e["n"].sum()), 4),
        "top_producers_gain_from_early_passes": round(float(et["g_early"].sum() / et["g"].sum()), 4),
        "top_producers_lateness_share_of_gain": round(float(et["late"].sum() / et["g"].sum()), 4),
        "top_producers_mean_delay_from_s": round(float(et["from_sum"].sum() / et["n"].sum()), 1),
        "all_mean_delay_from_s": round(float(e["from_sum"].sum() / e["n"].sum()), 1),
        "S_on_lateness_made": round(float(late_made[:k].sum() / late_made.sum()), 4),
        "top_producers_on_lateness": [
            {"segment": f"{a} → {b}", "gain_h": round(float(r.g / 3600)), "lateness_h": round(float(r.late / 3600)),
             "early_share": round(float(r.g_early / r.g), 3) if r.g else None}
            for (a, b), r in et.sort_values("g", ascending=False).head(15).iterrows()],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({m: {k2: v for k2, v in d.items() if k2 not in ("large_stops", "curve")}
                      for m, d in out.items() if m != "note"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
