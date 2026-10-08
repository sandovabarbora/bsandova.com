"""Power step of the gehl-trams design (§7): weather and the screened dispersion only, no dwell read against weather.

Classifies every hour of the two windows (§1) as rain, dry or neither by the rain study's rules, and simulates the SE
of θ (rain × optional) under the model of §4 with that exact rain pattern and the dispersion measured in screening
(σ_e per unit, σ_c a date × hour shock with AR(1) ρ over the hours of a date, the median units per date × hour).

    uv run --with numpy,pandas python tools/gehl/power.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs/research"
SEED, SIMS = 20261008, 400


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def windows(c: pd.DataFrame, holidays: set) -> pd.DataFrame:
    c = c.reset_index(drop=True).copy()
    wd = pd.to_datetime(c["date"]).dt.weekday
    off = (wd >= 5) | c["date"].isin(holidays)
    c["necessary"] = ~off & c["hour"].between(6, 8)
    c["optional"] = off & c["hour"].between(10, 17)
    c["cell"] = c["hour"].astype(str) + "-" + np.where(off, "off", wd.astype(str))
    return c


def se_theta(c: pd.DataFrame, s_e: float, s_c: float, rho: float, units: int, rng) -> float:
    keep = ((c["necessary"] | c["optional"]) & (c["rain"] | c["dry"])).to_numpy()
    s = c[keep]
    date_id = pd.factorize(s["date"])[0]
    cell = pd.factorize(s["cell"])[0]

    def demean(v: np.ndarray) -> np.ndarray:
        for _ in range(30):
            v = v - pd.Series(v).groupby(date_id).transform("mean").to_numpy()
            v = v - pd.Series(v).groupby(cell).transform("mean").to_numpy()
        return v

    rain = demean(s["rain"].astype(float).to_numpy())
    inter = demean((s["rain"] & s["optional"]).astype(float).to_numpy())
    x = inter - rain * (rain @ inter) / (rain @ rain)  # θ net of the rain main effect (Frisch–Waugh)
    full_date = pd.factorize(c["date"])[0]
    est = []
    for _ in range(SIMS):
        z = rng.normal(0, s_c, len(c))
        shock = np.empty(len(c))
        for i in range(len(c)):
            same = i > 0 and full_date[i] == full_date[i - 1]
            shock[i] = rho * shock[i - 1] + np.sqrt(1 - rho ** 2) * z[i] if same else z[i]
        y = demean(shock[keep] + rng.normal(0, s_e / np.sqrt(units), keep.sum()))
        est.append((x @ y) / (x @ x))
    return float(np.std(est))


def main() -> None:
    screen = json.loads((R / "gehl-trams-screen.json").read_text())
    rp, sc = load("rain_power", "tools/rain/power.py"), load("gehl_screen", "tools/gehl/screen.py")
    c = rp.classify(rp.precipitation())
    excluded = set(json.loads((R / "rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])
    c = c[~pd.Series(c["date"]).astype(str).isin(excluded).to_numpy()]
    c = windows(c, sc.HOLIDAYS)
    disp, m = screen["dispersion"], screen["margin"]["m_s"]

    def count(win: str) -> dict:
        w = c[c[win]]
        both = w.groupby("date").agg(r=("rain", "any"), d=("dry", "any"))
        return {"rain_hours": int(w["rain"].sum()), "dry_hours": int(w["dry"].sum()),
                "rain_dates": int(w.loc[w["rain"], "date"].nunique()),
                "dates_with_rain_and_dry_hours": int((both["r"] & both["d"]).sum())}

    se = se_theta(c, disp["sigma_e_s"], disp["sigma_c_s"], disp["rho"], disp["median_units_per_date_hour"],
                  np.random.default_rng(SEED))
    opt = count("optional")
    res = {"necessary": count("necessary"), "optional": opt,
           "dispersion": disp, "margin_m_s": m, "sims": SIMS,
           "se_theta_s": round(se, 3), "mde_theta_s": round(2.80 * se, 2),
           "underpowered_rule_4m_s": round(4 * m, 1), "underpowered": 2.80 * se > 4 * m,
           "not_estimable": opt["rain_dates"] < 10, "bootstrap": opt["rain_dates"] < 30}
    (R / "gehl-trams-power.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
