"""Bus check added after the article review (not registered): amplification with the instrument two, three and four
stops back, and the autocorrelation of spacing changes. Writes docs/research/bunching-describe-bus.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with scipy python tools/bunch/describe_bus.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bunch_estimate", Path(__file__).with_name("estimate.py"))
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)


def main() -> None:
    allp = be.load("bus")
    ps = allp[allp["H0"] >= be.H_MIN].reset_index(drop=True)
    d = be.transitions(ps)
    out = {"note": "described after the results; not registered", "pairs": int(ps["pair"].nunique()),
           "timing_point_stops": len(be.timing_stops("bus"))}
    gammas = {}
    for lag in (2, 3, 4):
        t = ps[["pair", "k", "r"]].assign(k=ps["k"] + lag).rename(columns={"r": "vl"})
        dd = d.drop(columns="v2").merge(t, on=["pair", "k"]).rename(columns={"vl": "v2"}).reset_index(drop=True)
        dd = dd[dd["v2"].notna()].reset_index(drop=True)
        num, den = be.gamma_parts(dd, iv=True)
        gammas[str(lag)] = round(float(num.sum() / den.sum()), 4)
    out["gamma_iv_by_instrument_lag"] = gammas
    dr = (d["v"] - d["v1"]).to_numpy()
    prev = d.assign(k=d["k"] + 1)[["pair", "k"]].assign(x=dr).rename(columns={"x": "prev"})
    j = d[["pair", "k"]].assign(y=dr).merge(prev, on=["pair", "k"])
    out["autocorrelation_lag_1"] = round(float(np.corrcoef(j["y"], j["prev"])[0, 1]), 4)
    (ROOT / "docs/research/bunching-describe-bus.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
