"""Post-hoc check of the rain-delays article, added 9 October 2026 after publication; not registered.

The registered tram model (y ~ rain | cell + date, clustered by date) with the hour's air temperature added as a
control: the four-station hourly mean of ČHMÚ ten-minute temperature, read for part 2 (tools/heat/power.py). Rain
hours are cooler than dry hours of the same date, and part 2 found less delay gained in hot hours, so temperature could
carry part of the rain contrast. Two forms: a linear term, and 2 °C bands as an extra fixed effect.

Writes docs/research/rain-delays-posthoc.json.

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest python tools/rain/posthoc.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rain"))
from estimate import D, drop_singletons, frame, interval, weather  # noqa: E402
from power import precipitation  # noqa: E402

_spec = importlib.util.spec_from_file_location("heat_power", ROOT / "tools" / "heat" / "power.py")
hp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hp)

OUT = ROOT / "docs/research/rain-delays-posthoc.json"
BAND_C = 2.0


def temperature() -> pd.DataFrame:
    t = hp.hourly_temperature()
    return pd.DataFrame({"date": t.index.date, "hour": t.index.hour, "t": t.to_numpy()})


def est(m, term: str = "rain") -> dict:
    lo, hi = interval(m, term, 0.95)
    return {"est_s": round(float(m.coef()[term]), 2), "ci95": [round(lo, 2), round(hi, 2)]}


def main() -> None:
    units = pd.read_parquet(D / "units.parquet")
    d = frame(units, weather(precipitation()), "tram")
    d = d[d["rain"] | d["dry"]].merge(temperature(), on=["date", "hour"], how="left")
    missing = int(d["t"].isna().sum())
    d = d[d["t"].notna()].assign(rain=lambda x: x["rain"].astype(int))
    d["tband"] = np.floor(d["t"] / BAND_C).astype(int).astype(str)
    d = drop_singletons(d)
    vc = {"CRV1": "date_s"}
    base = pf.feols("y ~ rain | cell + date_s", data=d, vcov=vc)
    lin = pf.feols("y ~ rain + t | cell + date_s", data=d, vcov=vc)
    band = pf.feols("y ~ rain | cell + date_s + tband", data=d, vcov=vc)
    means = d.groupby("rain")["t"].mean()
    res = {
        "note": "post-hoc, added 9 October 2026 after publication; not registered",
        "sample": {"units": int(len(d)), "units_without_temperature_dropped": missing,
                   "rain_units": int(d["rain"].sum()), "dates": int(d["date_s"].nunique())},
        "mean_temperature_c": {"rain_hours": round(float(means[1]), 1), "dry_hours": round(float(means[0]), 1)},
        "registered_model_same_sample": est(base),
        "linear_temperature": {**est(lin), "per_degree_s": est(lin, "t")},
        "temperature_bands_2c": est(band),
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
