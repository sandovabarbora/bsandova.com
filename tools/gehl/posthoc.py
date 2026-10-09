"""Checks of the rain-dwell article run after publication, 9 October 2026.

- Delay held (design §6, registered, not run before publication): the primary model with the unit's delay gained,
  the rain study's outcome for the same route, direction, date and hour, added as a control.
- Morning rain effect with a wild cluster bootstrap by date (post-hoc): the article gave the weekday-morning rain
  coefficient an analytic interval clustered by date, which rests on few rain dates; this redoes it with the house
  bootstrap (999 Rademacher draws, percentile-t).

Writes docs/research/gehl-trams-posthoc.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with duckdb --with pyfixest python tools/gehl/posthoc.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gehl_estimate", ROOT / "tools" / "gehl" / "estimate.py")
ge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ge)

OUT = ROOT / "docs/research/gehl-trams-posthoc.json"


def delay_gained() -> pd.DataFrame:
    u = pd.read_parquet(ROOT / "tools/data/rain/units.parquet")
    u = u[(u["mode"] == "tram") & u["y"].notna()]
    return pd.DataFrame({"route": u["route"], "direction": u["direction"], "date": pd.to_datetime(u["date"]).dt.date,
                         "hour": u["hour"], "gain": u["y"]})


def main() -> None:
    units = pd.read_parquet(ROOT / "tools/data/gehl/units.parquet")
    wx, rng = ge.weather(), np.random.default_rng(ge.SEED)
    base = ge.frame(units, wx)
    g = delay_gained()
    held = base.merge(g, on=["route", "direction", "date", "hour"], how="left")
    matched = float(held["gain"].notna().mean())
    held = held[held["gain"].notna()]
    terms = ["rain_opt", "rain", "gain"]
    res = {
        "note": "run 9 October 2026, after publication",
        "delay_held": {"registered": "design §6, not run before publication", "units": int(len(held)),
                       "share_of_units_with_delay_gained": round(matched, 4),
                       "same_sample_without_control": ge.coef(held, ge.PRIMARY, ["rain_opt", "rain"]),
                       "with_delay_gained": ge.coef(held, ge.PRIMARY + " + gain", terms)},
    }
    nec_dates = int(base.loc[(base["rain"] == 1) & (base["optional"] == 0), "date"].nunique())
    (ci95, ci90) = ge.wild(base, ge.PRIMARY, "rain", (0.95, 0.90), rng)
    fitted = ge.fit(base, ge.PRIMARY)
    res["morning_rain_bootstrap"] = {
        "registered": "post-hoc", "rain_dates_weekday_morning": nec_dates,
        "est_s": round(float(fitted.coef()["rain"]), 2),
        "analytic_ci95": [round(x, 2) for x in ge.interval(fitted, "rain", 0.95)],
        "wild_bootstrap_ci95": [round(x, 2) for x in ci95], "wild_bootstrap_ci90": [round(x, 2) for x in ci90],
        "inference": "wild cluster bootstrap by date, 999 Rademacher draws, percentile-t"}
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
