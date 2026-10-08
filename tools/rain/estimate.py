"""Estimates of the rain-delays design (§4–§6) from tools/data/rain/units.parquet and ČHMÚ hourly precipitation.

Primary (§4), separately for trams (primary estimand) and city buses (secondary, own label):
    y ~ rain | cell + date,   cell = route × direction × hour × weekday,   OLS, clustered by date,
on rain and dry hours only, units with at least 2 trips (§3 rule 3), planned-closure line-days (§3 rule 1) and
feed-gap dates (§3 rule 2) removed. If fewer than 30 dates hold a rain hour, a wild cluster bootstrap by date (999
Rademacher draws, percentile-t) replaces the analytic interval.

Labels (§5): supported if the 95 % interval lies wholly above 0; not supported if the 90 % interval lies wholly within
±10 s; otherwise inconclusive.

Checks (§6, none relabels the primary): placebo lead, lags, dose bands, nearest station, metro, level instead of gain,
disruption days kept, literal rule 1.

Writes docs/research/rain-delays-results.json.

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest python tools/rain/estimate.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from power import CHMI, END, HOURS, RAIN_MM, START, STATIONS, precipitation  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = Path(os.environ.get("RAIN_DATA", ROOT / "tools/data/rain"))
OUT = ROOT / "docs/research/rain-delays-results.json"
MARGIN_S = 10.0
BOOT_BELOW = 30
BOOT_REPS = 999
SEED = 20261008
# ČHMÚ station metadata (meta1.json, positions valid in 2025): longitude, latitude.
STATION_LONLAT = {"0-20000-0-11518": (14.255556, 50.100278), "0-20000-0-11520": (14.446944, 50.007778),
                  "0-20000-0-11567": (14.538056, 50.123333), "0-203-0-11514": (14.416923, 50.086634)}
DOSE = [("p0_1_0_5", 0.1, 0.5), ("p0_5_2", 0.5, 2.0), ("p2_5", 2.0, 5.0), ("p5_up", 5.0, math.inf)]


def weather(w: pd.DataFrame) -> pd.DataFrame:
    """Per local date × hour: the §1 classes for the four-station mean and for each station, plus lead, lags, dose."""
    w = w.reindex(columns=STATIONS).sort_index()
    out = pd.DataFrame(index=w.index)
    out["p"] = w.mean(axis=1, skipna=True)
    zero = (w == 0).all(axis=1) & w.notna().all(axis=1)
    out["rain"] = out["p"] >= RAIN_MM
    out["dry"] = zero & zero.shift(1, fill_value=False) & zero.shift(2, fill_value=False)
    out["rain_next"], out["dry_next"] = out["rain"].shift(-1, fill_value=False), out["dry"].shift(-1, fill_value=False)
    out["rain_l1"], out["rain_l2"] = out["rain"].shift(1, fill_value=False), out["rain"].shift(2, fill_value=False)
    for st in STATIONS:
        z = w[st] == 0
        out[f"rain_{st}"] = w[st] >= RAIN_MM
        out[f"dry_{st}"] = z & z.shift(1, fill_value=False) & z.shift(2, fill_value=False)
    out["date"], out["hour"] = out.index.date, out.index.hour
    return out.reset_index(drop=True)


def nearest_station(centroids: pd.DataFrame) -> dict[str, str]:
    def dist(lon, lat, st):
        slon, slat = STATION_LONLAT[st]
        return ((lon - slon) * math.cos(math.radians(50.08))) ** 2 + (lat - slat) ** 2
    return {r.route: min(STATIONS, key=lambda st: dist(r.lon, r.lat, st)) for r in centroids.itertuples()}


def frame(units: pd.DataFrame, wx: pd.DataFrame, mode: str, rule1: str | None = "rule1") -> pd.DataFrame:
    u = units[(units["mode"] == mode) & (units["trips"] >= 2) & units["y"].notna() & ~units["rule2"]].copy()
    if rule1:
        u = u[~u[rule1]]
    u["date"] = pd.to_datetime(u["date"]).dt.date
    u = u[(u["date"] >= START) & (u["date"] <= END) & u["hour"].isin(HOURS)]
    u = u.merge(wx, on=["date", "hour"], how="inner")
    u["weekday"] = pd.to_datetime(u["date"]).dt.weekday
    u["cell"] = u["route"] + "|" + u["direction"] + "|" + u["hour"].astype(str) + "|" + u["weekday"].astype(str)
    u["date_s"] = u["date"].astype(str)
    return u


def fit(d: pd.DataFrame, rhs: str, y: str = "y"):
    return pf.feols(f"{y} ~ {rhs} | cell + date_s", data=d, vcov={"CRV1": "date_s"})


def interval(m, term: str, level: float) -> tuple[float, float]:
    ci = m.confint(alpha=1 - level).loc[term]
    return float(ci.iloc[0]), float(ci.iloc[1])


def wild_interval(d: pd.DataFrame, term: str, level: float, rng: np.random.Generator) -> tuple[float, float]:
    """Wild cluster bootstrap by date, Rademacher, unrestricted, percentile-t (Cameron, Gelbach and Miller 2008)."""
    m = fit(d, term)
    b, se = float(m.coef()[term]), float(m.se()[term])
    resid = d["y"].to_numpy() - m.predict()
    fitted = d["y"].to_numpy() - resid
    groups = pd.factorize(d["date_s"])[0]
    t = []
    for _ in range(BOOT_REPS):
        flip = rng.choice([-1.0, 1.0], size=groups.max() + 1)[groups]
        db = d.assign(y=fitted + flip * resid)
        mb = fit(db, term)
        t.append((float(mb.coef()[term]) - b) / float(mb.se()[term]))
    lo_q, hi_q = np.quantile(t, [(1 - level) / 2, 1 - (1 - level) / 2])
    return b - hi_q * se, b - lo_q * se


def label(ci95: tuple[float, float], ci90: tuple[float, float]) -> str:
    if ci95[0] > 0:
        return "supported"
    if -MARGIN_S <= ci90[0] and ci90[1] <= MARGIN_S:
        return "not supported"
    return "inconclusive"


def primary(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    s = d[d["rain"] | d["dry"]].assign(rain=lambda x: x["rain"].astype(int))
    rain_dates = int(s.loc[s["rain"] == 1, "date"].nunique())
    m = fit(s, "rain")
    boot = rain_dates < BOOT_BELOW
    ci95 = wild_interval(s, "rain", 0.95, rng) if boot else interval(m, "rain", 0.95)
    ci90 = wild_interval(s, "rain", 0.90, rng) if boot else interval(m, "rain", 0.90)
    return {"delta_s": round(float(m.coef()["rain"]), 2), "se_s": round(float(m.se()["rain"]), 2),
            "ci95": [round(x, 2) for x in ci95], "ci90": [round(x, 2) for x in ci90],
            "label": label(ci95, ci90), "inference": "wild cluster bootstrap" if boot else "clustered by date",
            "n_units": int(len(s)), "dates": int(s["date"].nunique()), "rain_dates": rain_dates,
            "rain_units": int(s["rain"].sum())}


def coef(m, terms: list[str]) -> dict:
    """Estimates per term; a term the data cannot identify (e.g. an empty dose band) is listed as such, not skipped."""
    return {t: {"est_s": round(float(m.coef()[t]), 2), "ci95": [round(x, 2) for x in interval(m, t, 0.95)]}
            if t in m.coef().index else {"est_s": None, "note": "no variation in the data (dropped by the fit)"}
            for t in terms}


def checks(units: pd.DataFrame, wx: pd.DataFrame, near: dict[str, str]) -> dict:
    d = frame(units, wx, "tram")
    base = d[d["rain"] | d["dry"]]
    out = {}
    lead = d[d["rain_next"] | d["dry_next"]].assign(rain_next=lambda x: x["rain_next"].astype(int))
    out["placebo_lead"] = coef(fit(lead, "rain_next"), ["rain_next"])
    lags = base.assign(**{c: base[c].astype(int) for c in ("rain", "rain_l1", "rain_l2")})
    out["lags"] = coef(fit(lags, "rain + rain_l1 + rain_l2"), ["rain", "rain_l1", "rain_l2"])
    dose = d[d["dry"] | (d["p"] >= 0.1)].copy()
    for name, lo, hi in DOSE:
        dose[name] = ((dose["p"] >= lo) & (dose["p"] < hi) & ~dose["dry"]).astype(int)
    out["dose"] = coef(fit(dose, " + ".join(n for n, _, _ in DOSE)), [n for n, _, _ in DOSE])
    st = d.assign(station=d["route"].map(near)).dropna(subset=["station"])
    st["rain_st"] = [r[f"rain_{s}"] for r, s in zip(st.to_dict("records"), st["station"])]
    st["dry_st"] = [r[f"dry_{s}"] for r, s in zip(st.to_dict("records"), st["station"])]
    st = st[st["rain_st"] | st["dry_st"]].assign(rain_st=lambda x: x["rain_st"].astype(int))
    out["nearest_station"] = coef(fit(st, "rain_st"), ["rain_st"])
    metro = frame(units, wx, "metro", rule1=None)
    metro = metro[metro["rain"] | metro["dry"]].assign(rain=lambda x: x["rain"].astype(int))
    out["metro"] = coef(fit(metro, "rain"), ["rain"])
    lvl = base.assign(rain=base["rain"].astype(int))
    out["level_instead_of_gain"] = coef(fit(lvl, "rain", y="level"), ["rain"])
    for name, rule in (("disruption_days_kept", None), ("rule1_literal", "rule1_literal")):
        k = frame(units, wx, "tram", rule1=rule)
        k = k[k["rain"] | k["dry"]].assign(rain=lambda x: x["rain"].astype(int))
        out[name] = coef(fit(k, "rain"), ["rain"])
    return out


def main() -> None:
    units = pd.read_parquet(D / "units.parquet")
    wx = weather(precipitation())
    near = nearest_station(pd.read_parquet(D / "centroids.parquet"))
    rng = np.random.default_rng(SEED)
    res = {
        "window": [START.isoformat(), END.isoformat()],
        "precipitation_source": str(CHMI.relative_to(ROOT)),
        "tram": primary(frame(units, wx, "tram"), rng),
        "bus_secondary": primary(frame(units, wx, "bus"), rng),
        "checks_tram": checks(units, wx, near),
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
