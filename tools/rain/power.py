"""Power step of the rain-delays design (§7): precipitation only, no delay value.

Reads ČHMÚ hourly precipitation (SRA1H) for Ruzyně, Libuš, Kbely and Klementinum, 15 March – 8 September 2025, from
tools/data/rain/chmi/ (downloaded from opendata.chmi.cz/meteorology/climate/historical/data/1hour/2025/), classifies
every local service hour 05:00–23:59 as rain, dry or neither by the design's rules (§1), and simulates the standard
error of δ_tram under the model of §4 with that exact rain pattern.

ČHMÚ stamps an hourly total at the end of its hour in UTC: the value at 2025-06-01T10:00Z is 09:00–09:59 UTC.

Delay dispersion is not reported in seconds on the thesis page, so the simulation uses a grid of structure-only
assumptions (σ_e, the unit-level noise; σ_c, a city-wide date × hour shock that rain cannot be separated from; ρ, that
shock's hour-to-hour autocorrelation within a date, since the thesis found delays persist within a day) and
reports the minimum detectable δ (80 % power, two-sided 5 %, = 2.80 × SE) for each.

    uv run --with numpy,pandas python tools/rain/power.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CHMI = ROOT / "tools/data/rain/chmi"
OUT = ROOT / "docs/research/rain-delays-power.json"
STATIONS = ["0-20000-0-11518", "0-20000-0-11520", "0-20000-0-11567", "0-203-0-11514"]
START, END = date(2025, 3, 15), date(2025, 9, 8)
HOURS = range(5, 24)
RAIN_MM = 0.5
ROUTES = 50  # tram route-directions (about 25 day routes × 2); structure only
SEED = 20261006
SIMS = 200


def precipitation() -> pd.DataFrame:
    rows = []
    for f in sorted(CHMI.glob("1h-*.json")):
        d = json.loads(f.read_text())["data"]["data"]
        rows += [r for r in d["values"] if r[1] == "SRA1H"]
    p = pd.DataFrame(rows, columns=["station", "el", "dt", "val", "flag", "q"])
    p["end"] = pd.to_datetime(p["dt"], utc=True)
    p["start_local"] = (p["end"] - pd.Timedelta(hours=1)).dt.tz_convert(ZoneInfo("Europe/Prague"))
    p["val"] = pd.to_numeric(p["val"], errors="coerce")
    return p.pivot_table(index="start_local", columns="station", values="val", aggfunc="first")


def classify(w: pd.DataFrame) -> pd.DataFrame:
    w = w.reindex(columns=STATIONS).sort_index()
    mean = w.mean(axis=1, skipna=True)
    all_zero = (w == 0).all(axis=1) & w.notna().all(axis=1)
    dry = all_zero & all_zero.shift(1, fill_value=False) & all_zero.shift(2, fill_value=False)
    c = pd.DataFrame({"mean": mean, "rain": mean >= RAIN_MM, "dry": dry})
    c["date"] = c.index.date
    c["hour"] = c.index.hour
    keep = (c["date"] >= START) & (c["date"] <= END) & c["hour"].isin(HOURS)
    return c[keep]


def se_sim(c: pd.DataFrame, sigma_e: float, sigma_c: float, rho: float, rng: np.random.Generator) -> float:
    """SE of δ by within-cell OLS with route × hour × weekday and date effects, clustered by date, on rain and dry hours.

    Under the null the estimate's spread across draws is its SE; fixed effects are removed by demeaning, which with a
    balanced route panel equals the two-way FE estimator for a city-wide treatment."""
    keep = (c["rain"] | c["dry"]).to_numpy()
    s = c[keep].copy()
    full_date = pd.factorize(c["date"])[0]
    s["wd"] = pd.to_datetime(s["date"]).dt.weekday
    x = s["rain"].astype(float).to_numpy()
    date_id = pd.factorize(s["date"])[0]
    cell = pd.factorize(s["hour"].astype(str) + "-" + s["wd"].astype(str))[0]

    def demean(v: np.ndarray) -> np.ndarray:
        for _ in range(20):  # alternating projections onto date and hour × weekday effects
            v = v - pd.Series(v).groupby(date_id).transform("mean").to_numpy()
            v = v - pd.Series(v).groupby(cell).transform("mean").to_numpy()
        return v

    xt = demean(x)
    est = []
    for _ in range(SIMS):
        # route noise averaged over ROUTES route-directions per hour, plus a city-wide shock per date × hour
        # the city-wide shock follows an AR(1) over the hours of each date (delays persist within a day)
        z = rng.normal(0, sigma_c, len(c))
        shock = np.empty(len(c))
        for i in range(len(c)):
            same = i > 0 and full_date[i] == full_date[i - 1]
            shock[i] = rho * shock[i - 1] + np.sqrt(1 - rho ** 2) * z[i] if same else z[i]
        y = shock[keep] + rng.normal(0, sigma_e / np.sqrt(ROUTES), len(s))
        yt = demean(y)
        est.append((xt @ yt) / (xt @ xt))
    return float(np.std(est))


def main() -> None:
    c = classify(precipitation())
    rain_dates = sorted({d for d, r in zip(c["date"], c["rain"]) if r})
    days = (END - START).days + 1
    rng = np.random.default_rng(SEED)
    grid = []
    for sigma_e in (60, 120, 180):
        for sigma_c in (10, 20, 30):
            for rho in (0.0, 0.5, 0.8):
                se = se_sim(c, sigma_e, sigma_c, rho, rng)
                grid.append({"sigma_e_s": sigma_e, "sigma_c_s": sigma_c, "rho": rho, "se_s": round(se, 2),
                             "mde_s": round(2.80 * se, 1)})
    res = {
        "window": f"{START} – {END}, service hours 05:00–23:59 local",
        "dates_in_window": days,
        "service_hours": int(len(c)),
        "station_hours_missing": int(c["mean"].isna().sum()),
        "rain_hours": int(c["rain"].sum()),
        "dry_hours": int(c["dry"].sum()),
        "neither_hours": int((~c["rain"] & ~c["dry"]).sum()),
        "rain_dates": len(rain_dates),
        "bootstrap_if_rain_dates_below_30": len(rain_dates) < 30,
        "routes_assumed": ROUTES,
        "sims": SIMS,
        "grid": grid,
        "mde_max_s": max(g["mde_s"] for g in grid),
        "passes_30s_rule_all_scenarios": all(g["mde_s"] <= 30 for g in grid),
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
