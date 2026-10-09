"""Post-hoc check of the dst-darkness article, added 9 October 2026 after publication; not registered.

Leave one autumn out: the registered primary model (estimate.py) refitted ten times, each time without one of the
ten autumns, on the published cells (assets/dst/cells.parquet). Also the raw rise in evening pedestrian crashes by
autumn, which the article quotes.

Writes docs/research/dst-darkness-posthoc.json.

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest python tools/dst/posthoc.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import frame, poisson, ratio  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CELLS = ROOT / "assets" / "dst" / "cells.parquet"
OUT = ROOT / "docs" / "research" / "dst-darkness-posthoc.json"


def main() -> None:
    cells = pd.read_parquet(CELLS)
    out = {}
    for year in sorted(cells.year.unique()):
        r = ratio(poisson(frame(cells[cells.year != year], -14, 14)), "pe")
        out[str(int(year))] = {k: round(float(r[k]), 3) for k in ("ratio", "lo", "hi")}
    w = cells[(cells.t >= -14) & (cells.t <= 14) & (cells.t != 0) & (cells.group == "evening")]
    by = w.groupby(["year", w.t > 0]).ped.sum().unstack()
    rise = {str(int(y)): int(by.loc[y, True] - by.loc[y, False]) for y in by.index}
    ratios = [v["ratio"] for v in out.values()]
    res = {"note": "post-hoc, added 9 October 2026 after publication; not registered",
           "leave_one_autumn_out": out, "range": [min(ratios), max(ratios)],
           "lowest_lower_bound": min(v["lo"] for v in out.values()),
           "evening_rise_by_autumn": rise, "evening_rise_total": int(sum(rise.values()))}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
