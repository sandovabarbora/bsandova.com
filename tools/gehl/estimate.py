"""Estimates of the gehl-trams design (§4–§6, as changed on 8 October 2026) from the screened dwell units.

Primary, trams, rain and dry hours of the two windows only:
    y ~ rain + optional + rain_opt | cell + week,   cell = route × direction × hour × weekday,
weighted by kept passes, clustered by date; θ is the coefficient of rain_opt. `optional` is in the model because a
holiday on a weekday shares its cells with ordinary weekdays. With fewer than 30 optional rain dates the interval is a
wild cluster bootstrap by date (999 Rademacher draws, percentile-t). Labels (§5): supported if the 95 % interval is
wholly below 0, not supported if the 90 % interval is wholly within ±m, otherwise inconclusive.

Writes docs/research/gehl-trams-results.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with duckdb --with pyfixest python tools/gehl/estimate.py
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs/research"
OUT = R / "gehl-trams-results.json"
BOOT_BELOW, BOOT_REPS, SEED = 30, 999, 20261008
NECESSARY, OPTIONAL, EVENING, MIDDAY = (6, 8), (8, 20), (15, 18), (10, 14)
SCHOOL_OFF = [(date(2025, 4, 17), date(2025, 4, 17)), (date(2025, 6, 28), date(2025, 8, 31))]
DOSE = [("r0_2", 0.5, 2.0), ("r2_5", 2.0, 5.0), ("r5_up", 5.0, np.inf)]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def margin() -> float:
    return json.loads((R / "gehl-trams-screen.json").read_text())["margin"]["m_s"]


def weather() -> pd.DataFrame:
    c = load("heat_power", "tools/heat/power.py").classify().reset_index(drop=True)
    c["rain_lead2"] = lead_two_days(c)
    return c[["date", "hour", "mean", "t", "rain", "dry", "hot", "mild", "rain_lead2"]]


def lead_two_days(c: pd.DataFrame) -> np.ndarray:
    """For the placebo: whether the same clock hour two days later is a rain hour (False where it is not in the data)."""
    key = pd.to_datetime(c["date"]) + pd.to_timedelta(c["hour"], unit="h")
    later = pd.Series(c["rain"].to_numpy(), index=key - pd.Timedelta(days=2))
    return later.reindex(key).fillna(False).astype(bool).to_numpy()


def frame(units: pd.DataFrame, wx: pd.DataFrame, nec: tuple[int, int] = NECESSARY,
          opt: tuple[int, int] = OPTIONAL, y: str = "y") -> pd.DataFrame:
    d = units.merge(wx, on=["date", "hour"], how="inner")
    off = (d["weekday"] >= 5) | d["holiday"]
    d["necessary"] = ~off & d["hour"].between(*nec)
    d["optional"] = (off & d["hour"].between(*opt)).astype(int)
    d = d[(d["necessary"] | d["optional"].astype(bool)) & (d["rain"] | d["dry"])].copy()
    d["rain"] = d["rain"].astype(int)
    d["rain_opt"] = d["rain"] * d["optional"]
    d["cell"] = d["route"] + "|" + d["direction"] + "|" + d["hour"].astype(str) + "|" + d["weekday"].astype(str)
    d["date_s"] = d["date"].astype(str)
    d["week_s"] = pd.to_datetime(d["date"]).dt.isocalendar().week.astype(str).to_numpy()
    d["y"] = d[y]
    return d[d["y"].notna()]


def drop_singletons(d: pd.DataFrame, fe: str) -> pd.DataFrame:
    while True:
        keep = d.groupby("cell")["cell"].transform("size").gt(1) & d.groupby(fe)[fe].transform("size").gt(1)
        if keep.all():
            return d
        d = d[keep]


def fit(d: pd.DataFrame, rhs: str, fe: str = "week_s"):
    return pf.feols(f"y ~ {rhs} | cell + {fe}", data=drop_singletons(d, fe), weights="passes",
                    vcov={"CRV1": "date_s"})


def interval(m, term: str, level: float) -> tuple[float, float]:
    ci = m.confint(alpha=1 - level).loc[term]
    return float(ci.iloc[0]), float(ci.iloc[1])


def wild(d: pd.DataFrame, rhs: str, term: str, levels: tuple[float, ...], rng, fe: str = "week_s") -> list:
    d = drop_singletons(d, fe)
    m = fit(d, rhs, fe)
    b, se = float(m.coef()[term]), float(m.se()[term])
    resid = d["y"].to_numpy() - m.predict()
    fitted = d["y"].to_numpy() - resid
    groups = pd.factorize(d["date_s"])[0]
    t = []
    for _ in range(BOOT_REPS):
        flip = rng.choice([-1.0, 1.0], size=groups.max() + 1)[groups]
        mb = fit(d.assign(y=fitted + flip * resid), rhs, fe)
        t.append((float(mb.coef()[term]) - b) / float(mb.se()[term]))
    out = []
    for level in levels:
        lo_q, hi_q = np.quantile(t, [(1 - level) / 2, 1 - (1 - level) / 2])
        out.append((b - hi_q * se, b - lo_q * se))
    return out


def label(ci95: tuple[float, float], ci90: tuple[float, float], m: float, below: bool = True) -> str:
    if (ci95[1] < 0) if below else (ci95[0] > 0):
        return "supported"
    if -m < ci90[0] and ci90[1] < m:
        return "not supported"
    return "inconclusive"


def estimate(d: pd.DataFrame, rhs: str, term: str, treated: str, m: float, rng, fe: str = "week_s") -> dict:
    fitted = fit(d, rhs, fe)
    dates = int(d.loc[d[treated] == 1, "date"].nunique())
    boot = dates < BOOT_BELOW
    ci95, ci90 = (wild(d, rhs, term, (0.95, 0.90), rng, fe) if boot
                  else (interval(fitted, term, 0.95), interval(fitted, term, 0.90)))
    return {"est_s": round(float(fitted.coef()[term]), 2), "se_s": round(float(fitted.se()[term]), 2),
            "ci95": [round(x, 2) for x in ci95], "ci90": [round(x, 2) for x in ci90], "label": label(ci95, ci90, m),
            "inference": "wild cluster bootstrap by date" if boot else "clustered by date",
            "treated_dates": dates, "n_units": int(len(d)), "dates": int(d["date"].nunique())}


def coef(d: pd.DataFrame, rhs: str, terms: list[str], fe: str = "week_s") -> dict:
    """Checks: estimate and clustered 95 % interval; a term with no variation is listed as not estimable."""
    try:
        m = fit(d, rhs, fe)
    except ValueError as e:
        return {t: {"est_s": None, "note": f"not estimable: {str(e).splitlines()[0][:80]}"} for t in terms}
    out = {}
    for t in terms:
        if t not in m.coef().index:
            out[t] = {"est_s": None, "note": "not estimable: dropped as collinear"}
            continue
        lo, hi = interval(m, t, 0.95)
        out[t] = {"est_s": round(float(m.coef()[t]), 2), "ci95": [round(lo, 2), round(hi, 2)]}
    return out


PRIMARY = "rain + optional + rain_opt"


def heat_frame(units: pd.DataFrame, wx: pd.DataFrame) -> pd.DataFrame:
    d = units.merge(wx, on=["date", "hour"], how="inner")
    d = d[d["hot"] | d["mild"]].copy()
    d["hot"] = d["hot"].astype(int)
    off = (d["weekday"] >= 5) | d["holiday"]
    d["optional"] = off.astype(int)
    d["cell"] = d["route"] + "|" + d["direction"] + "|" + d["hour"].astype(str) + "|" + d["weekday"].astype(str)
    d["date_s"] = d["date"].astype(str)
    d["week_s"] = pd.to_datetime(d["date"]).dt.isocalendar().week.astype(str).to_numpy()
    return d


def checks(units: pd.DataFrame, wx: pd.DataFrame, m: float, rng) -> dict:
    base = frame(units, wx)
    out = {"date_effects": coef(base, PRIMARY, ["rain_opt", "rain"], fe="date_s"),
           "by_window": coef(base, PRIMARY, ["rain", "rain_opt"])}
    dose = base.copy()
    for name, lo, hi in DOSE:
        dose[name] = ((dose["mean"] >= lo) & (dose["mean"] < hi)).astype(int)
        dose[name + "_opt"] = dose[name] * dose["optional"]
    names = [n for n, _, _ in DOSE]
    out["dose"] = coef(dose, " + ".join(names + [n + "_opt" for n in names] + ["optional"]),
                       names + [n + "_opt" for n in names])
    out["evening"] = coef(frame(units, wx, nec=EVENING), PRIMARY, ["rain_opt", "rain"])
    school = base[~base["date"].apply(lambda x: any(a <= x <= b for a, b in SCHOOL_OFF))]
    out["school_holidays_out"] = coef(school, PRIMARY, ["rain_opt", "rain"])
    mid = units.merge(wx, on=["date", "hour"], how="inner")
    off = (mid["weekday"] >= 5) | mid["holiday"]
    mid["window"] = np.select([~off & mid["hour"].between(*NECESSARY), ~off & mid["hour"].between(*MIDDAY),
                               off & mid["hour"].between(*OPTIONAL)], ["necessary", "midday", "optional"], "")
    mid = mid[(mid["window"] != "") & (mid["rain"] | mid["dry"])].copy()
    mid["rain"] = mid["rain"].astype(int)
    mid["optional"] = (mid["window"] == "optional").astype(int)
    mid["rain_mid"] = mid["rain"] * (mid["window"] == "midday")
    mid["rain_opt"] = mid["rain"] * mid["optional"]
    mid["cell"] = mid["route"] + "|" + mid["direction"] + "|" + mid["hour"].astype(str) + "|" + mid["weekday"].astype(str)
    mid["date_s"] = mid["date"].astype(str)
    mid["week_s"] = pd.to_datetime(mid["date"]).dt.isocalendar().week.astype(str).to_numpy()
    out["weekday_midday"] = coef(mid, "rain + optional + rain_mid + rain_opt", ["rain", "rain_mid", "rain_opt"])
    for zone in ("centre", "outer"):
        z = units.assign(passes=units[f"passes_{zone}"] if zone == "centre" else units["passes"] - units["passes_centre"])
        out[zone] = coef(frame(z[z["passes"] > 0], wx, y=f"y_{zone}"), PRIMARY, ["rain_opt", "rain"])
    out["placebo_rain_two_days_later"] = placebo(units, wx)
    hd = heat_frame(units, wx)
    out["heat_gehl_contrast"] = coef(
        hd[(hd["optional"].astype(bool) & hd["hour"].between(12, 18)) |
           (~hd["optional"].astype(bool) & hd["hour"].between(*EVENING))].assign(hot_opt=lambda x: x["hot"] * x["optional"]),
        "hot + optional + hot_opt", ["hot", "hot_opt"])
    return out


def placebo(units: pd.DataFrame, wx: pd.DataFrame) -> dict:
    """Dry hours only, 'rain' replaced by rain in the same hour two days later; expected near 0."""
    w = wx.copy()
    w = w[w["dry"]].assign(rain=w["rain_lead2"], dry=~w["rain_lead2"])
    return coef(frame(units, w), PRIMARY, ["rain_opt", "rain"])


def main() -> None:
    units = pd.read_parquet(ROOT / "tools/data/gehl/units.parquet")
    wx, m, rng = weather(), margin(), np.random.default_rng(SEED)
    primary = estimate(frame(units, wx), PRIMARY, "rain_opt", "rain_opt", m, rng)
    hd = heat_frame(units, wx)
    heat = estimate(hd, "hot", "hot", "hot", m, rng)
    res = {"margin_m_s": m, "windows": {"necessary": NECESSARY, "optional": OPTIONAL},
           "primary_theta": primary, "heat_secondary": heat, "checks": checks(units, wx, m, rng)}
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps({k: res[k] for k in ("primary_theta", "heat_secondary")}, indent=1))


if __name__ == "__main__":
    main()
