"""Power step of the heat-delays design (§6): temperature and delay dispersion only, no delay read against temperature.

Reads ČHMÚ 10-minute air temperature (`T`) for the four Prague stations (tools/data/heat/chmi10/), builds the hourly
four-station mean T_h (a station counts in an hour with at least four of its six values), and classifies every service
hour 05:00–23:59 of 15 March – 8 September 2025, without the rain study's eight feed-gap dates, as hot (≥ 30 °C),
mild (15–25 °C) or neither; only dry hours (rain study's rule) count.

The simulation follows tools/rain/power.py with week effects instead of date effects (design §3). With week effects a
shock common to a whole date is no longer absorbed, so its size σ_day is measured from the rain study's tram units
without any temperature (dated note in the design's change log): residuals of y on cell and week effects, averaged by
date. σ_e, σ_c and ρ are the rain study's measured values.

Writes docs/research/heat-delays-power.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with pyfixest python tools/heat/power.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rain"))
import power as rp  # noqa: E402

T10 = ROOT / "tools/data/heat/chmi10"
OUT = ROOT / "docs/research/heat-delays-power.json"
FEED = ROOT / "docs/research/rain-delays-screen-feed.json"
RAIN_POWER = ROOT / "docs/research/rain-delays-power-rerun.json"
HOT, MILD = 30.0, (15.0, 25.0)
SEED, SIMS = 20261008, 200


def hourly_temperature() -> pd.Series:
    rows = []
    for f in sorted(T10.glob("10m-*.json")):
        d = json.loads(f.read_text())["data"]["data"]
        rows += [r for r in d["values"] if r[1] == "T"]
    t = pd.DataFrame(rows, columns=["station", "el", "dt", "val", "flag", "q"])
    t["val"] = pd.to_numeric(t["val"], errors="coerce")
    t["end"] = pd.to_datetime(t["dt"], utc=True)
    # a 10-minute value stamped hh:mm belongs to the interval ending then; hh:10 … (hh+1):00 is hour hh
    t["hour_start"] = (t["end"] - pd.Timedelta(minutes=10)).dt.tz_convert(ZoneInfo("Europe/Prague")).dt.floor("h")
    g = t.groupby(["hour_start", "station"])["val"].agg(["mean", "count"])
    g = g[g["count"] >= 4]["mean"].unstack()
    return g.reindex(columns=rp.STATIONS).mean(axis=1, skipna=True)


def classify() -> pd.DataFrame:
    th = hourly_temperature()
    rain = rp.classify(rp.precipitation())  # local hours, window and service hours already applied
    c = rain.join(th.rename("t"), how="left")
    excluded = set(json.loads(FEED.read_text())["rule2_dates_excluded"])
    c = c[~pd.Series(c["date"]).astype(str).isin(excluded).to_numpy()]
    c["hot"] = c["dry"] & (c["t"] >= HOT)
    c["mild"] = c["dry"] & c["t"].between(*MILD)
    c["week"] = pd.to_datetime(c["date"]).dt.isocalendar().week.to_numpy()
    return c


def sigma_day() -> float:
    import pyfixest as pf
    import importlib.util  # the rain study's estimate.py, by path: tools/heat has an estimate.py of its own
    spec = importlib.util.spec_from_file_location("rain_estimate", ROOT / "tools" / "rain" / "estimate.py")
    rx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rx)
    D, drop_singletons = rx.D, rx.drop_singletons
    u = pd.read_parquet(D / "units.parquet")
    u = u[(u["mode"] == "tram") & (u["trips"] >= 2) & u["y"].notna() & ~u["rule1"] & ~u["rule2"]].copy()
    u["date"] = pd.to_datetime(u["date"])
    u["week"] = u["date"].dt.isocalendar().week.astype(str)
    u["cell"] = u["route"] + "|" + u["direction"] + "|" + u["hour"].astype(str) + "|" + u["date"].dt.weekday.astype(str)
    u["date_s"] = u["date"].dt.date.astype(str)
    u = drop_singletons(u)
    m = pf.feols("y ~ 1 | cell + week", data=u)
    res = u["y"].to_numpy() - m.predict()
    return float(pd.Series(res).groupby(u["date_s"].to_numpy()).mean().std())


def se_week(c: pd.DataFrame, s_e: float, s_c: float, rho: float, s_d: float, units: int, rng) -> float:
    keep = (c["hot"] | c["mild"]).to_numpy()
    s = c[keep]
    x = s["hot"].astype(float).to_numpy()
    week = pd.factorize(s["week"])[0]
    cell = pd.factorize(s["hour"].astype(str) + "-" + pd.to_datetime(s["date"]).dt.weekday.astype(str))[0]
    full_date = pd.factorize(c["date"])[0]

    def demean(v):
        for _ in range(20):
            v = v - pd.Series(v).groupby(week).transform("mean").to_numpy()
            v = v - pd.Series(v).groupby(cell).transform("mean").to_numpy()
        return v

    xt = demean(x)
    est = []
    for _ in range(SIMS):
        day = rng.normal(0, s_d, full_date.max() + 1)[full_date]
        z = rng.normal(0, s_c, len(c))
        shock = np.empty(len(c))
        for i in range(len(c)):
            same = i > 0 and full_date[i] == full_date[i - 1]
            shock[i] = rho * shock[i - 1] + np.sqrt(1 - rho ** 2) * z[i] if same else z[i]
        y = (day + shock)[keep] + rng.normal(0, s_e / np.sqrt(units), len(s))
        est.append((xt @ demean(y)) / (xt @ xt))
    return float(np.std(est))


def main() -> None:
    c = classify()
    rp_rain = json.loads(RAIN_POWER.read_text())
    s_d = sigma_day()
    rng = np.random.default_rng(SEED)
    se = se_week(c, rp_rain["sigma_e_s"], rp_rain["sigma_c_s"], max(rp_rain["rho"], 0), s_d,
                 rp_rain["units_per_date_hour"], rng)
    hot_dates = int(pd.Series(c.loc[c["hot"], "date"]).nunique())
    res = {
        "dates": int(pd.Series(c["date"]).nunique()), "service_hours": int(len(c)),
        "hours_without_temperature": int(c["t"].isna().sum()),
        "hot_hours": int(c["hot"].sum()), "mild_hours": int(c["mild"].sum()),
        "hot_dates": hot_dates, "hot_weeks": int(pd.Series(c.loc[c["hot"], "week"]).nunique()),
        "dry_hours": int(c["dry"].sum()),
        "sigma_day_s": round(s_d, 2), "sigma_e_s": rp_rain["sigma_e_s"], "sigma_c_s": rp_rain["sigma_c_s"],
        "rho": rp_rain["rho"], "units_per_date_hour": rp_rain["units_per_date_hour"], "sims": SIMS,
        "se_s": round(se, 2), "mde_s": round(2.80 * se, 1),
        "estimable": hot_dates >= 10, "passes_30s_rule": 2.80 * se <= 30,
        "bootstrap_if_hot_dates_below_30": hot_dates < 30,
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
