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


def windows(c: pd.DataFrame, holidays: set, opt: tuple[int, int] = (8, 20)) -> pd.DataFrame:
    c = c.reset_index(drop=True).copy()
    wd = pd.to_datetime(c["date"]).dt.weekday
    off = (wd >= 5) | c["date"].isin(holidays)
    c["necessary"] = ~off & c["hour"].between(6, 8)
    c["optional"] = off & c["hour"].between(*opt)
    c["week"] = pd.to_datetime(c["date"]).dt.isocalendar().week.to_numpy()
    c["cell"] = c["hour"].astype(str) + "-" + np.where(off, "off", wd.astype(str))
    return c


def se_theta(c: pd.DataFrame, s_e: float, s_c: float, rho: float, s_d: float, units: int, rng, fe: str = "week") -> float:
    keep = ((c["necessary"] | c["optional"]) & (c["rain"] | c["dry"])).to_numpy()
    s = c[keep]
    date_id = pd.factorize(s[fe])[0]
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
        day = rng.normal(0, s_d, full_date.max() + 1)[full_date]
        z = rng.normal(0, s_c, len(c))
        shock = np.empty(len(c))
        for i in range(len(c)):
            same = i > 0 and full_date[i] == full_date[i - 1]
            shock[i] = rho * shock[i - 1] + np.sqrt(1 - rho ** 2) * z[i] if same else z[i]
        y = demean((day + shock)[keep] + rng.normal(0, s_e / np.sqrt(units), keep.sum()))
        est.append((x @ y) / (x @ x))
    return float(np.std(est))


def sigma_day() -> float:
    import pyfixest as pf

    est = load("rain_estimate", "tools/rain/estimate.py")
    u = pd.read_parquet(ROOT / "tools/data/gehl/units.parquet")
    u["date_s"] = u["date"].astype(str)
    u["week"] = pd.to_datetime(u["date"]).dt.isocalendar().week.astype(str)
    u["cell"] = u["route"] + "|" + u["direction"] + "|" + u["hour"].astype(str) + "|" + u["weekday"].astype(str)
    u = est.drop_singletons(u)
    m = pf.feols("y ~ 1 | cell + week", data=u, weights="passes")
    return float(pd.Series(np.asarray(m.resid())).groupby(u["date_s"].to_numpy()).mean().std())


def main() -> None:
    screen = json.loads((R / "gehl-trams-screen.json").read_text())
    rp, sc = load("rain_power", "tools/rain/power.py"), load("gehl_screen", "tools/gehl/screen.py")
    c0 = rp.classify(rp.precipitation())
    excluded = set(json.loads((R / "rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])
    c0 = c0[~pd.Series(c0["date"]).astype(str).isin(excluded).to_numpy()]
    disp, m = screen["dispersion"], screen["margin"]["m_s"]
    s_d = sigma_day()

    def count(c: pd.DataFrame, win: str) -> dict:
        w = c[c[win]]
        both = w.groupby("date").agg(r=("rain", "any"), d=("dry", "any"))
        return {"rain_hours": int(w["rain"].sum()), "dry_hours": int(w["dry"].sum()),
                "rain_dates": int(w.loc[w["rain"], "date"].nunique()),
                "dates_with_rain_and_dry_hours": int((both["r"] & both["d"]).sum())}

    def run(opt: tuple[int, int], fe: str) -> dict:
        c = windows(c0, sc.HOLIDAYS, opt)
        se = se_theta(c, disp["sigma_e_s"], disp["sigma_c_s"], disp["rho"], s_d if fe == "week" else 0.0,
                      disp["median_units_per_date_hour"], np.random.default_rng(SEED), fe)
        o = count(c, "optional")
        return {"optional_hours": f"{opt[0]:02d}:00-{opt[1]:02d}:59", "effects": fe,
                "necessary": count(c, "necessary"), "optional": o, "se_theta_s": round(se, 3),
                "mde_theta_s": round(2.80 * se, 2), "underpowered": 2.80 * se > 4 * m,
                "not_estimable": o["rain_dates"] < 10, "bootstrap": o["rain_dates"] < 30}

    res = {"dispersion": disp, "sigma_day_s": round(s_d, 3), "margin_m_s": m, "underpowered_rule_4m_s": round(4 * m, 1),
           "sims": SIMS, "registered": run((10, 17), "date"), "after_deviation": run((8, 20), "week")}
    (R / "gehl-trams-power.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
