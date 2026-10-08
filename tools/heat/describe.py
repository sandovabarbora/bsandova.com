"""Descriptive numbers for the heat article; none is a registered test.

Raw means of delay gained in hot and mild dry hours by mode (no model), and hot hours per date.
Writes docs/research/heat-delays-describe.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with pyfixest python tools/heat/describe.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("heat_estimate", Path(__file__).resolve().parent / "estimate.py")
he = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(he)
OUT = ROOT / "docs/research/heat-delays-describe.json"


def main() -> None:
    units = pd.read_parquet(he.rx.D / "units.parquet")
    wx = he.weather()
    means = {}
    for mode in ("tram", "bus", "metro"):
        d = he.frame(units, wx, mode, rule1="rule1" if mode != "metro" else None)
        means[mode] = {k: {"mean_s": round(float(g["y"].mean()), 2), "units": int(len(g))}
                       for k, g in (("hot", d[d["hot"]]), ("mild", d[d["mild"]]))}
    days = wx.groupby("date").agg(hot=("hot", "sum"), tmax=("t", "max")).reset_index()
    res = {"raw_means": means,
           "hot_days": [{"date": str(r.date), "hot_hours": int(r.hot), "tmax": round(float(r.tmax), 1)}
                        for r in days.itertuples()],
           "tmax_window": round(float(wx["t"].max()), 1)}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(means, indent=1), "max", res["tmax_window"],
          [d for d in res["hot_days"] if d["hot_hours"]])


if __name__ == "__main__":
    main()
