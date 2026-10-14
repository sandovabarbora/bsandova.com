"""Data for the animated restart map of the blackout article: each tram segment's passes per ten minutes on 4 July 2025
against the ordinary Fridays, 11:00–17:00. A description drawn from the registered study's passes, not an estimate.

Reads tools/data/blackout/passes.parquet (estimate.py's cache) and the baseline days from blackout-screen.json; writes
assets/blackout/restart.json in the spec of assets/animap.js, v the ratio over the half hour ending with each bin (null
where the segment has no trams on ordinary Fridays then).

    uv run --no-project --with pandas --with pyarrow --with duckdb python tools/blackout/animation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from tram_geo import offset_line, tram_stops  # noqa: E402

EVENT, START, END, WIDTH = "2025-07-04", 11 * 60, 17 * 60, 10
OUT = ROOT / "assets/blackout/restart.json"


def main() -> None:
    base = json.loads((ROOT / "docs/research/blackout-screen.json").read_text())["baseline_days"]
    p = pd.read_parquet(ROOT / "tools/data/blackout/passes.parquet")
    p = p[(p["mode"] == "tramvaj") & (p.t >= START) & (p.t < END) & p.date.isin([EVENT, *base])]
    p = p.assign(bin=((p.t - START) // WIDTH).astype(int))
    nb = (END - START) // WIDTH
    c = p.groupby(["seg_from", "seg_to", "date", "bin"]).size().unstack("date", fill_value=0)
    # a trailing half hour (this bin and the two before), so a segment with a tram every ten minutes does not flicker
    wide = c.unstack("bin", fill_value=0).reindex(columns=pd.MultiIndex.from_product([c.columns, range(nb)]), fill_value=0)
    roll = {d: wide[d].T.rolling(3, min_periods=1).sum().T for d in c.columns}
    ev = roll[EVENT] if EVENT in roll else 0 * roll[base[0]]
    mean = sum(roll[d] for d in base) / len(base)
    ratio = (ev / mean).where(mean > 0)
    usual = c[base].mean(axis=1).groupby(level=[0, 1]).sum()
    xy = {r.name: (r.lon, r.lat) for r in tram_stops().itertuples()}
    feats = []
    for (a, b), row in ratio.iterrows():
        if a in xy and b in xy and a != b and usual[(a, b)] >= 3:
            feats.append({"id": f"{a} → {b}", "l": offset_line(xy[a], xy[b]),
                          "v": [None if np.isnan(v) else round(float(min(v, 2.0)), 2) for v in row.to_numpy(float)]})
    tot = p.groupby(["date", "bin"]).size().unstack("date", fill_value=0).reindex(range(nb), fill_value=0)
    network = (tot[EVENT] / tot[base].mean(axis=1)).round(3).tolist()
    bins = [f"{(START + WIDTH * i) // 60:02d}:{(START + WIDTH * i) % 60:02d}" for i in range(nb)]
    notes = [f"{sum(f['v'][i] == 0 for f in feats)} of {len(feats)} segments without a tram · network "
             f"{round(100 * network[i])} % of usual" for i in range(nb)]
    spec = {"bins": bins, "base": "../assets/praha-base.json", "features": feats,
            "colour": {"domain": [0, 0.5, 0.9], "range": ["#c0503f", "#e7b3a6", "#bdbdb6"]},
            "tip": {"mult": 100, "dp": 0, "unit": " % of usual trams", "empty": "no trams on ordinary Fridays"},
            "notes": notes, "series": {"values": network, "domain": [0, 1.2], "ref": 1, "refLabel": "1.0"},
            "ticks": [0, 6, 12, 18, 24, 30],
            "events": [{"at": "12:00", "label": "11:59 grid collapses"}, {"at": "13:00", "label": "13:01 Chodov back"}],
            "aria": "Prague tram segments coloured by the share of their usual trams, 4 July 2025, 11:00 to 17:00"}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    print(len(feats), "segments;", OUT.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
