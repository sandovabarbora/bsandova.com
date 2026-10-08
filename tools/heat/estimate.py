"""Estimates of the heat-delays design (§3–§5) from the rain study's units and ČHMÚ 10-minute temperature.

Primary, separately for trams (primary) and city buses (secondary, own label):
    y ~ hot | cell + week,   cell = route × direction × hour × weekday,   OLS, clustered by date,
on dry hours that are hot (T_h ≥ 30 °C) or mild (15–25 °C), units with at least 2 trips, the rain study's screening
applied. With fewer than 30 hot dates the interval is a wild cluster bootstrap by date (999 Rademacher draws,
unrestricted, percentile-t). Labels as in the rain study: supported if the 95 % interval is wholly above 0, not
supported if the 90 % interval is wholly within ±10 s, otherwise inconclusive.

Checks (§5): date effects instead of week effects, dose bands, the metro, thresholds 28 and 32 °C, wet hours kept with a
rain indicator, level instead of gain, and a placebo with the heat of two days later.

Writes docs/research/heat-delays-results.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with pyfixest python tools/heat/estimate.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rain"))  # the rain study's power and estimate modules import each other
_spec = importlib.util.spec_from_file_location("rain_estimate", ROOT / "tools" / "rain" / "estimate.py")
rx = importlib.util.module_from_spec(_spec)  # the rain study's frame, labels and margin
_spec.loader.exec_module(rx)
_spec = importlib.util.spec_from_file_location("heat_power", Path(__file__).resolve().parent / "power.py")
hp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hp)
HOT, MILD, classify = hp.HOT, hp.MILD, hp.classify

OUT = ROOT / "docs/research/heat-delays-results.json"
BOOT_BELOW, BOOT_REPS, SEED = 30, 999, 20261008
DOSE = [("t25_28", 25.0, 28.0), ("t28_30", 28.0, 30.0), ("t30_32", 30.0, 32.0), ("t32_up", 32.0, math.inf)]


def weather() -> pd.DataFrame:
    c = classify().reset_index(drop=True)
    c["rain_any"] = ~c["dry"]
    c["hot_lead2"] = lead_two_days(c)
    return c[["date", "hour", "t", "dry", "hot", "mild", "rain_any", "hot_lead2"]]


def lead_two_days(c: pd.DataFrame) -> np.ndarray:
    """For the placebo: whether the same clock hour two days later is hot (False where that hour is not in the data)."""
    key = pd.to_datetime(c["date"]) + pd.to_timedelta(c["hour"], unit="h")
    later = pd.Series(c["hot"].to_numpy(), index=key - pd.Timedelta(days=2))
    return later.reindex(key).fillna(False).astype(bool).to_numpy()


def frame(units: pd.DataFrame, wx: pd.DataFrame, mode: str, rule1: str | None = "rule1") -> pd.DataFrame:
    d = rx.frame(units, wx, mode, rule1)
    d["week_s"] = pd.to_datetime(d["date"]).dt.isocalendar().week.astype(str).to_numpy()
    return d


def drop_singletons(d: pd.DataFrame, fe: str) -> pd.DataFrame:
    while True:
        keep = d.groupby("cell")["cell"].transform("size").gt(1) & d.groupby(fe)[fe].transform("size").gt(1)
        if keep.all():
            return d
        d = d[keep]


def fit(d: pd.DataFrame, rhs: str, fe: str = "week_s", y: str = "y"):
    return pf.feols(f"{y} ~ {rhs} | cell + {fe}", data=drop_singletons(d, fe), vcov={"CRV1": "date_s"})


def wild(d: pd.DataFrame, term: str, level: float, rng, fe: str = "week_s") -> tuple[float, float]:
    d = drop_singletons(d, fe)
    m = fit(d, term, fe)
    b, se = float(m.coef()[term]), float(m.se()[term])
    resid = d["y"].to_numpy() - m.predict()
    fitted = d["y"].to_numpy() - resid
    groups = pd.factorize(d["date_s"])[0]
    t = []
    for _ in range(BOOT_REPS):
        flip = rng.choice([-1.0, 1.0], size=groups.max() + 1)[groups]
        mb = fit(d.assign(y=fitted + flip * resid), term, fe)
        t.append((float(mb.coef()[term]) - b) / float(mb.se()[term]))
    lo_q, hi_q = np.quantile(t, [(1 - level) / 2, 1 - (1 - level) / 2])
    return b - hi_q * se, b - lo_q * se


def primary(d: pd.DataFrame, rng) -> dict:
    s = d[d["hot"] | d["mild"]].assign(hot=lambda x: x["hot"].astype(int))
    hot_dates = int(s.loc[s["hot"] == 1, "date"].nunique())
    m = fit(s, "hot")
    boot = hot_dates < BOOT_BELOW
    ci95 = wild(s, "hot", 0.95, rng) if boot else rx.interval(m, "hot", 0.95)
    ci90 = wild(s, "hot", 0.90, rng) if boot else rx.interval(m, "hot", 0.90)
    return {"delta_s": round(float(m.coef()["hot"]), 2), "se_s": round(float(m.se()["hot"]), 2),
            "ci95": [round(x, 2) for x in ci95], "ci90": [round(x, 2) for x in ci90], "label": rx.label(ci95, ci90),
            "inference": "wild cluster bootstrap by date" if boot else "clustered by date",
            "n_units": int(len(s)), "dates": int(s["date"].nunique()), "hot_dates": hot_dates,
            "hot_units": int(s["hot"].sum())}


def coef(m, terms: list[str]) -> dict:
    return rx.coef(m, terms)


def safe(d: pd.DataFrame, rhs: str, terms: list[str], **kw) -> dict:
    """A check whose regressors have no variation in the data is listed as not estimable, not dropped."""
    try:
        return coef(fit(d, rhs, **kw), terms)
    except ValueError as e:
        return {t: {"est_s": None, "note": f"not estimable: {str(e).split(chr(10))[1].strip()[:80]}"} for t in terms}


def checks(units: pd.DataFrame, wx: pd.DataFrame) -> dict:
    d = frame(units, wx, "tram")
    base = d[d["hot"] | d["mild"]].assign(hot=lambda x: x["hot"].astype(int))
    out = {"date_effects": safe(base, "hot", ["hot"], fe="date_s")}
    mild = d["mild"]
    dose = d[d["dry"] & (mild | (d["t"] >= DOSE[0][1]))].copy()
    for name, lo, hi in DOSE:
        dose[name] = ((dose["t"] >= lo) & (dose["t"] < hi)).astype(int)
    out["dose"] = safe(dose, " + ".join(n for n, _, _ in DOSE), [n for n, _, _ in DOSE])
    metro = frame(units, wx, "metro", rule1=None)
    metro = metro[metro["hot"] | metro["mild"]].assign(hot=lambda x: x["hot"].astype(int))
    out["metro"] = safe(metro, "hot", ["hot"])
    for name, thr in (("threshold_28", 28.0), ("threshold_32", 32.0)):
        k = d[d["dry"] & (mild | (d["t"] >= thr))].assign(hot=lambda x: (x["t"] >= thr).astype(int))
        out[name] = safe(k, "hot", ["hot"])
    wet = d[(d["t"] >= HOT) | d["t"].between(*MILD)].assign(hot=lambda x: (x["t"] >= HOT).astype(int),
                                                             rain_any=lambda x: x["rain_any"].astype(int))
    out["wet_hours_kept"] = safe(wet, "hot + rain_any", ["hot", "rain_any"])
    out["level_instead_of_gain"] = safe(base, "hot", ["hot"], y="level")
    pl = d[d["dry"] & ~d["hot"] & (d["mild"] | d["hot_lead2"])].assign(hot_lead2=lambda x: x["hot_lead2"].astype(int))
    out["placebo_two_days_later"] = safe(pl, "hot_lead2", ["hot_lead2"])
    return out


def main() -> None:
    units = pd.read_parquet(rx.D / "units.parquet")
    wx = weather()
    rng = np.random.default_rng(SEED)
    res = {"thresholds": {"hot": HOT, "mild": list(MILD)},
           "tram": primary(frame(units, wx, "tram"), rng),
           "bus_secondary": primary(frame(units, wx, "bus"), rng),
           "checks_tram": checks(units, wx)}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
