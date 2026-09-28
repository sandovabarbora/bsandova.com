"""Part 4 extended, §5a: design-stage power, sealed. This script was committed before it was first run, and it
writes only power tables and covariate-side design statistics (docs/research/prague-housing-power.json).

Outcome information enters only through pre-window series, used inside the simulations and never written out:
  - H2: permitted dwellings in new multi-dwelling buildings, 2007-01 to 2014-12 (Prague; the rest without
    Středočeský kraj), to fit an AR(2) on log(1 + x) with month effects. Synthetic permitted-dwelling series are drawn
    from that process for 2007-2024; completions are generated from them. No completion series is read.
  - H4: Polish starts by builder group, 2005-2011, for powiat means and overdispersion. The window is 2012-2024.
  - H5: flats completed 2000-2011 (RÚIAN), for the baseline surface and overdispersion. The confirmatory window is
    1 Jan 2012 - 25 Mar 2021.
H1 needs no outcome: its power depends only on n and α. H3 is not in the family; only its covariate-side design
statistics are reported.

Usage (from a worktree, point DATA at the main checkout's gitignored tools/data):
    DATA=/path/to/bsandova.com/tools/data uv run --with pandas --with numpy --with scipy --with statsmodels \
        --with pyarrow --with openpyxl --with shapely --with pyfixest python tools/praha/housing_power.py
"""

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize
from scipy.stats import gamma as gamma_dist, norm, t as tdist
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("DATA", ROOT / "tools" / "data"))
RAW = DATA / "praha4x"
OUT = ROOT / "docs" / "research" / "prague-housing-power.json"
SEED = 20260929
ALPHAS = {"holm_first_step_family_3": 0.05 / 3, "nominal": 0.05}
PRAGUE, CENTRAL = "CZ010", "CZ020"


# ---------------------------------------------------------------- H1: conformal rank test, n and α only
def h1(rng: np.random.Generator, n: int) -> dict:
    reps, out = 100_000, {}
    z_others = rng.standard_normal((reps, n))
    z_p = rng.standard_normal(reps)
    for gap in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
        p = (1 + (z_others <= (z_p - gap)[:, None]).sum(axis=1)) / (n + 1)
        out[f"gap_{gap}_sd"] = {k: round(float((p <= a).mean()), 3) for k, a in ALPHAS.items()}
    return {"n": n, "smallest_p": round(1 / (n + 1), 4), "power_by_gap_in_residual_sd": out}


# ---------------------------------------------------------------- H2: distributed lag, synthetic permits
def kernel(mu: float, phi: float, k: int) -> np.ndarray:
    """Discretised gamma weights on lags 0..k, not renormalised (the tail mass beyond k is lost)."""
    edges = np.arange(k + 2)
    return np.diff(gamma_dist.cdf(edges, a=phi, scale=mu / phi))


def fit_lag(c: np.ndarray, s: np.ndarray, months: np.ndarray, k: int) -> float:
    """Profile NLS: for (μ, φ), OLS of C on the convolved permits and month effects; returns μ̂."""
    d = pd.get_dummies(months).to_numpy(float)

    def sse(par):
        mu, phi = np.exp(par)
        conv = np.convolve(s, kernel(mu, phi, k))[k:len(s)]
        x = np.column_stack([conv, d])
        b, res, *_ = np.linalg.lstsq(x, c, rcond=None)
        return float(((c - x @ b) ** 2).sum())

    best = min((minimize(sse, np.log([m0, 4.0]), method="Nelder-Mead",
                         options={"xatol": 1e-3, "fatol": 1e-6, "maxiter": 400}) for m0 in (18, 30)),
               key=lambda r: r.fun)
    return float(np.exp(best.x[0]))


def ar_fit(y: pd.Series) -> dict:
    """AR(2) on log(1 + permitted dwellings) with month effects, 2007-2014 only."""
    z = np.log1p(y.to_numpy())
    mo = y.index.month
    x = np.column_stack([pd.get_dummies(mo).to_numpy(float)[2:], z[1:-1], z[:-2]])
    b, *_ = np.linalg.lstsq(x, z[2:], rcond=None)
    resid = z[2:] - x @ b
    return {"month": b[:12], "ar": b[12:], "sd": float(resid.std(ddof=x.shape[1])), "z0": z[:2]}


def ar_draw(p: dict, months: np.ndarray, rng) -> np.ndarray:
    z = list(p["z0"])
    for m in months[2:]:
        z.append(p["month"][m - 1] + p["ar"][0] * z[-1] + p["ar"][1] * z[-2] + rng.normal(0, p["sd"]))
    return np.maximum(np.expm1(np.array(z)), 0)


def h2(rng: np.random.Generator, reps: int = 200) -> dict:
    m = pd.read_parquet(RAW / "czech_monthly.parquet")
    pre = m[(m.date >= "2007-01-01") & (m.date <= "2014-12-01")]
    series = {"prague": pre[pre.kraj == PRAGUE].set_index("date").permitted_multi,
              "rest": pre[~pre.kraj.isin([PRAGUE, CENTRAL])].groupby("date").permitted_multi.sum()}
    fits = {u: ar_fit(s) for u, s in series.items()}
    dates = pd.date_range("2007-01-01", "2024-12-01", freq="MS")
    months = dates.month.to_numpy()
    k, theta, phi, mu_r = 72, 0.8, 4.0, 24.0
    win = dates >= "2013-01-01"
    out = {}
    for noise in (0.25, 0.5, 1.0):
        est = {}
        for delta in (0, 3, 6, 12):
            d = []
            for _ in range(reps):
                mu_hat = {}
                for u, mu in (("prague", mu_r + delta), ("rest", mu_r)):
                    s = ar_draw(fits[u], months, rng)
                    signal = theta * np.convolve(s, kernel(mu, phi, k))[:len(s)]
                    e = np.zeros(len(s))
                    sd = noise * signal[win].std()
                    for i in range(1, len(s)):
                        e[i] = 0.3 * e[i - 1] + rng.normal(0, sd * np.sqrt(1 - 0.09))
                    c = signal + e
                    mu_hat[u] = fit_lag(c[win], s[np.argmax(win) - k:], months[win], k)
                d.append(mu_hat["prague"] - mu_hat["rest"])
            est[delta] = np.array(d)
        crit = {a_name: np.quantile(est[0], 1 - a) for a_name, a in ALPHAS.items()}
        out[f"noise_{noise}_x_signal_sd"] = {
            f"delta_{delta}_months": {a_name: round(float((est[delta] > crit[a_name]).mean()), 3)
                                      for a_name in ALPHAS}
            for delta in (3, 6, 12)} | {"null_sd_of_contrast_months": round(float(est[0].std()), 2)}
    return {"reps": reps, "kernel": {"k": k, "theta": theta, "phi": phi, "mu_rest": mu_r},
            "critical_value": "simulated null quantile of the contrast", "power": out}


# ---------------------------------------------------------------- H3: covariate-side statistics only
def h3() -> dict:
    t = pd.read_excel(RAW / "csu" / "icncr.xlsx", header=None)
    head = t.iloc[0].ffill()
    q = t.iloc[1]
    cols = [(int(float(y)), int(str(v)[-1])) for y, v in zip(head, q)
            if isinstance(v, str) and v.startswith("Čtv") and str(y)[:2] in ("20",)]
    idx = [i for i, (y, v) in enumerate(zip(head, q)) if isinstance(v, str) and v.startswith("Čtv")
           and str(y)[:2] == "20"]
    block = t.iloc[2:18]  # base 2010 = 100 block
    p = pd.DataFrame(block.iloc[:, idx].apply(pd.to_numeric, errors="coerce").to_numpy(float),
                     index=block.iloc[:, 0].str.strip(),
                     columns=pd.MultiIndex.from_tuples(cols))
    lp = np.log(p)
    g = lp.shift(1, axis=1) - lp.shift(5, axis=1)
    g = g.loc[:, [c for c in g.columns if (c[0], c[1]) >= (2016, 2)]]
    kraje = [r for r in g.index if r not in ("ČR", "ČR bez Prahy", "Středočeský kraj")]
    within = g.loc[kraje].sub(g.loc[kraje].mean(axis=1), axis=0)
    return {"quarters": int(g.shape[1]), "first": "2016 Q2",
            "within_sd_price_growth_prague": round(float(within.loc["Hlavní město Praha"].std()), 4),
            "within_sd_price_growth_rest_median": round(float(within.drop("Hlavní město Praha").std(axis=1)
                                                              .median()), 4),
            "inference": "not in the family; EWC interval (ν ≈ 4), no power computed"}


# ---------------------------------------------------------------- H4: Polish powiats
def bdl(var: int) -> pd.DataFrame:
    r = json.loads((RAW / "bdl" / f"{var}_L5.json").read_text())["results"]
    rows = [{"unit": x["id"], "name": x["name"], "year": int(v["year"]), "val": v["val"],
             "attr": v.get("attrId")} for x in r for v in x["values"]]
    d = pd.DataFrame(rows)
    d.loc[(d.attr == 91) | ((d.val == 0) & (var in (633677, 633682, 633687))), "val"] = np.nan
    # powiat wałbrzyski merged with Wałbrzych city in all years (registered)
    walb = d.name.str.contains("wałbrzyski|Wałbrzych", case=False)
    d.loc[walb, "unit"] = "walbrzych_merged"
    agg = "mean" if var in (633677, 633682, 633687) else "sum"
    return d.groupby(["unit", "year"]).val.agg(agg).reset_index()


def h4(rng: np.random.Generator, reps: int = 200) -> dict:
    import pyfixest as pf

    mkt = bdl(747732).rename(columns={"val": "S"})
    nm = bdl(747734).merge(bdl(747735), on=["unit", "year"], suffixes=("_m", "_t"))
    nm["S"] = nm.val_m.fillna(0) + nm.val_t.fillna(0)
    price = bdl(633677).rename(columns={"val": "P"})
    pre = {"M": mkt[mkt.year.between(2005, 2011)], "NM": nm[nm.year.between(2005, 2011)][["unit", "year", "S"]]}
    share_nm = float((pre["NM"].S > 0).mean())
    support = set(pre["NM"].groupby("unit").S.sum().pipe(lambda s: s[s > 0]).index)
    price = price.sort_values(["unit", "year"])
    price["g"] = price.groupby("unit").P.transform(lambda s: np.log(s).diff()).groupby(price.unit).shift(1)
    grid = price[price.year.between(2012, 2024) & price.g.notna() & price.unit.isin(support)][["unit", "year", "g"]]
    base, disp = {}, {}
    for b, d in pre.items():
        d = d[d.unit.isin(support)]
        mean = d.groupby("unit").S.mean().clip(lower=0.05)
        var = d.groupby("unit").S.var()
        disp[b] = float(max(((var - mean) / mean ** 2).replace([np.inf, -np.inf], np.nan).median(), 0.01))
        base[b] = mean
    out = {}
    for gap in (0.0, 0.5, 1.0):
        rej = {a: 0 for a in ALPHAS}
        for _ in range(reps):
            frames = []
            for b, beta in (("M", 1.0), ("NM", 1.0 - gap)):
                f = grid.copy()
                mu = f.unit.map(base[b]).to_numpy() * np.exp(beta * f.g.to_numpy())
                lam = rng.gamma(1 / disp[b], disp[b] * mu)
                f["S"], f["nm"], f["fe"] = rng.poisson(lam), int(b == "NM"), f.unit + b
                f["ye"] = f.year.astype(str) + b
                frames.append(f)
            f = pd.concat(frames)
            f["g_nm"] = f.g * f.nm
            fit = pf.fepois("S ~ g + g_nm | fe + ye", data=f, vcov={"CRV1": "unit"})
            coef, se = fit.coef()["g_nm"], fit.se()["g_nm"]
            for a_name, a in ALPHAS.items():
                rej[a_name] += coef / se < norm.ppf(a)
        out[f"gap_{gap}"] = {a: round(r / reps, 3) for a, r in rej.items()}
    return {"reps": reps, "powiats_in_support": len(support), "powiat_years": int(len(grid)),
            "share_powiat_years_with_non_market_start_2005_2011": round(share_nm, 3),
            "within_sd_price_growth": round(float((grid.g - grid.groupby("unit").g.transform("mean")).std()), 4),
            "power_beta_nm_minus_beta_m": out}


# ---------------------------------------------------------------- H5: Prague cells
def spline(x: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Restricted cubic spline basis (Harrell), k knots -> k - 1 columns."""
    k = knots
    cols = [x]
    for j in range(len(k) - 2):
        cols.append(np.maximum(x - k[j], 0) ** 3 - np.maximum(x - k[-2], 0) ** 3 * (k[-1] - k[j]) / (k[-1] - k[-2])
                    + np.maximum(x - k[-1], 0) ** 3 * (k[-2] - k[j]) / (k[-1] - k[-2]))
    return np.column_stack(cols) / 1.0


def h5(rng: np.random.Generator, reps: int = 500) -> dict:
    from shapely import STRtree, wkb
    from shapely.geometry import Point

    c = pd.read_parquet(RAW / "prague_cells.parquet")
    b = pd.read_parquet(RAW / "prague" / "buildings.parquet")
    done = pd.to_datetime(b.dokonceni, unit="ms", errors="coerce")
    pre = b[(done >= "2000-01-01") & (done <= "2011-12-31")]
    polys = [wkb.loads(g) for g in c.geom_wkb]
    tree = STRtree(polys)
    hit = [tree.query(Point(x, y), predicate="within") for x, y in zip(pre.x, pre.y)]
    cell_of = np.array([h[0] if len(h) else -1 for h in hit])
    n_pre = np.bincount(cell_of[cell_of >= 0], weights=pre.pocetbytu.to_numpy()[cell_of >= 0], minlength=len(c))
    dens = np.log1p(c.pop2011 / c.area_km2).to_numpy()
    knots = np.quantile(dens, [0.05, 0.35, 0.65, 0.95])
    x = np.column_stack([c.log2_metro_km, c.log2_centre_km, spline(dens, knots)])
    vif = {n: round(float(variance_inflation_factor(sm.add_constant(x), i + 1)), 2)
           for i, n in enumerate(["log2_metro", "log2_centre"])}
    offset = np.log(c.area_km2.to_numpy())
    # overdispersion by profile likelihood over α, baseline surface from the 2000-2011 fit (γ replaced below)
    best = max(((a, sm.GLM(np.round(n_pre), sm.add_constant(x), family=sm.families.NegativeBinomial(alpha=a),
                           offset=offset).fit().llf) for a in np.exp(np.linspace(-2, 3, 26))), key=lambda t: t[1])
    alpha = best[0]
    fit = sm.GLM(np.round(n_pre), sm.add_constant(x), family=sm.families.NegativeBinomial(alpha=alpha),
                 offset=offset).fit()
    beta = fit.params.copy()
    beta[0] += np.log((pd.Timestamp("2021-03-25") - pd.Timestamp("2012-01-01")).days / 365.25 / 12)
    groups = c.admin_district.astype(str).to_numpy()
    out = {}
    for gamma_true in (0.0, -0.25, -0.5):
        b_true = beta.copy()
        b_true[1] = gamma_true
        mu = np.exp(sm.add_constant(x) @ b_true + offset)
        rej = {a: 0 for a in ALPHAS}
        for _ in range(reps):
            y = rng.poisson(rng.gamma(1 / alpha, alpha * mu))
            r = sm.GLM(y, sm.add_constant(x), family=sm.families.Poisson(), offset=offset).fit(
                cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]})
            tstat = r.params[1] / r.bse[1]
            for a_name, a in ALPHAS.items():
                rej[a_name] += tstat < tdist.ppf(a, 21)
        out[f"gamma_{gamma_true}"] = {a: round(v / reps, 3) for a, v in rej.items()}
    return {"reps": reps, "cells": int(len(c)), "vif": vif, "clusters": int(pd.Series(groups).nunique()),
            "inference_in_simulation": "PPML, CR1 by 22 administrative districts, t(21); the registered decision "
                                       "uses max(p_Conley, p_WCR), which can only lower power",
            "power_gamma_per_doubling": out}


def main() -> None:
    rng = np.random.default_rng(SEED)
    report = json.loads((RAW / "design_report.json").read_text())
    out = {"seed": SEED, "alphas": ALPHAS,
           "H1": h1(rng, report["h1_n_primary"]),
           "H2": h2(rng), "H3": h3(), "H4": h4(rng), "H5": h5(rng)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
