"""Data for the animated day of part 1: each tram segment's mean delay gained per pass in each weekday hour, 5:00–23:00,
over the season. A description drawn from part 1's screened sums after the results, not an estimate.

Reads tools/data/late/segments.parquet; writes assets/late/day.json in the spec of assets/animap.js.

    uv run --no-project --with pandas --with pyarrow --with duckdb python tools/late/day_animation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from tram_geo import offset_line, tram_stops  # noqa: E402

HOURS = range(5, 24)
MIN_PASSES, HOT = 200, 20  # a segment-hour needs this many passes over the season; "gaining" means over 20 s a pass
OUT = ROOT / "assets/late/day.json"


def main() -> None:
    s = pd.read_parquet(ROOT / "tools/data/late/segments.parquet").query("mode == 'tram'")
    s = s[(pd.to_datetime(s["date"]).dt.weekday < 5) & s["hour"].isin(HOURS)]
    t = s.groupby(["seg_from", "seg_to", "hour"])[["gsum", "n"]].sum()
    per = (t["gsum"] / t["n"]).where(t["n"] >= MIN_PASSES).unstack("hour").reindex(columns=list(HOURS))
    xy = {r.name: (r.lon, r.lat) for r in tram_stops().itertuples()}
    feats = [{"id": f"{a} → {b}", "l": offset_line(xy[a], xy[b]),
              "v": [None if pd.isna(v) else round(float(v), 1) for v in row]}
             for (a, b), row in per.iterrows() if a in xy and b in xy and a != b]
    days = s["date"].nunique()
    passes = (s.groupby("hour")["n"].sum() / days / 1000).reindex(list(HOURS)).round(1).tolist()
    bins = [f"{h:02d}:00" for h in HOURS]
    notes = [f"{sum((f['v'][i] or 0) > HOT for f in feats)} segments gaining over {HOT} s a pass · "
             f"{passes[i]:.1f} thousand tram passes in this hour on an average weekday" for i in range(len(bins))]
    spec = {"bins": bins, "base": "../assets/praha-base.json", "features": feats,
            "colour": {"domain": [-40, 0, 40], "range": ["#2a7f86", "#d9d9d4", "#c0503f"]},
            "tip": {"dp": 0, "unit": " s a pass", "sign": True, "empty": "too few trams in this hour"},
            "notes": notes, "series": {"values": passes, "domain": [0, max(passes) * 1.15]},
            "ticks": [0, 3, 6, 9, 12, 15, 18], "step": 700,
            "aria": "Prague tram segments coloured by the delay gained per pass, weekday by weekday hour, 5:00 to 23:00"}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    print(len(feats), "segments;", OUT.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
