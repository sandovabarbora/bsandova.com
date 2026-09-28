"""Part 4 extended: every registered estimate of docs/research/prague-housing-design.md (v2, 503ef06).

  - H2, H4, H5: the confirmatory family, Holm at 5 %.
  - H1: Prague's rank among European metro regions (and core regions), studentised leave-one-country-out conformal
    scores, under the Eurostat and the ČSÚ-rebuilt numerators, with the pre-written statements.
  - H3: the cumulative relative response of permitted dwellings to price growth, 90 % EWC interval, placebo, rank.
  - Relevance checks R1-R4, and the H6 replications that need no robustness machinery.

Reads the design frames of housing_data.py and the raw files of housing_fetch.py; writes
assets/praha/housing_extended.json.

Usage (from a worktree, point DATA at the main checkout's gitignored tools/data):
    DATA=/path/to/bsandova.com/tools/data uv run --with pandas --with numpy --with scipy --with statsmodels \
        --with pyarrow --with openpyxl --with shapely --with pyproj --with pyfixest --with arch \
        python tools/praha/housing_extended.py
"""

import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from arch.bootstrap import optimal_block_length
from scipy.optimize import minimize
from scipy.stats import gamma as gamma_dist, norm, t as tdist

sys.path.insert(0, str(Path(__file__).parent))
from housing_data import WARSAW, back_codes, jsonstat, lookup  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("DATA", ROOT / "tools" / "data"))
RAW = DATA / "praha4x"
OUT = ROOT / "assets" / "praha" / "housing_extended.json"
SEED = 20260929
B = int(os.environ.get("B", 9999))  # override only for debugging runs
PRAGUE, CENTRAL = "CZ010", "CZ020"
WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
# census 2021 reference dates. CZ, PL, AT registered; DE, IE [verify]; the rest from national census documentation,
# not from Eurostat metadata (deviation, 29 Sep 2026); each marked in the change log.
REF_DATE = {"CZ": "2021-03-26", "PL": "2021-03-31", "AT": "2021-10-31", "DE": "2022-05-15", "IE": "2022-04-03",
            "HU": "2022-10-01", "IT": "2021-12-31", "RO": "2021-12-01", "BG": "2021-09-07", "HR": "2021-08-31",
            "PT": "2021-04-19", "EL": "2021-10-22", "CY": "2021-10-19", "LU": "2021-11-08", "MT": "2021-11-21",
            "SE": "2021-12-31", "FI": "2021-12-31", "EE": "2021-12-31", "CH": "2021-12-31"}
DEFAULT_REF = "2021-01-01"  # register-based censuses: BE, DK, ES, FR, LT, LV, NL, NO, SI, SK


# ------------------------------------------------------------------------------------------------ helpers
def webb(rng, g: int, b: int) -> np.ndarray:
    return WEBB[rng.integers(0, 6, size=(b, g))]


def holm(p: dict, alpha: float = 0.05) -> dict:
    order = sorted(p, key=p.get)
    out, stop = {}, False
    for i, k in enumerate(order):
        thr = alpha / (len(order) - i)
        ok = (not stop) and p[k] <= thr
        stop = stop or not ok
        out[k] = {"p": p[k], "threshold": thr, "supported": bool(ok)}
    return out


def ppml_if(X: np.ndarray, y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """Influence functions ψ_i = H⁻¹ x_i (y_i − μ_i) of a Poisson pseudo-ML fit (rows: observations)."""
    H = X.T @ (X * mu[:, None])
    return (np.linalg.solve(H, X.T) * (y - mu)).T


def score_wcr(y, X_restricted, offset, x_test, clusters, rng, b=B, weights=None):
    """Kline-Santos score bootstrap for one coefficient of a Poisson model, restricted estimate under γ = 0.
    Returns the one-sided p-values for 'negative' and 'positive' and the effective number of clusters."""
    fam = sm.families.Poisson()
    r = sm.GLM(y, X_restricted, family=fam, offset=offset).fit()
    mu = np.asarray(r.mu)
    w = mu if weights is None else mu * weights
    beta = np.linalg.lstsq(X_restricted * np.sqrt(w)[:, None], x_test * np.sqrt(w), rcond=None)[0]
    xt = x_test - X_restricted @ beta
    s = xt * (y - mu)
    codes, gidx = np.unique(clusters, return_inverse=True)
    sg = np.bincount(gidx, weights=s)
    stat = sg.sum()
    draws = webb(rng, len(codes), b) @ sg
    gam = np.bincount(gidx, weights=xt ** 2 * mu)
    g_eff = len(codes) / (1 + ((gam - gam.mean()) ** 2).mean() / gam.mean() ** 2)
    return {"p_negative": float((1 + (draws <= stat).sum()) / (b + 1)),
            "p_positive": float((1 + (draws >= stat).sum()) / (b + 1)),
            "clusters": int(len(codes)), "effective_clusters": round(float(g_eff), 1)}


# ------------------------------------------------------------------------------------------------ H1
def h1_regions() -> dict:
    """Covariates and both numerators for metro regions and their core NUTS 3 regions."""
    chain = back_codes()
    m = pd.read_parquet(RAW / "h1_frame.parquet")
    pop = jsonstat("demo_r_pjanaggr3", sex="T", age="TOTAL", unit="NR").pivot(index="geo", columns="time",
                                                                              values="value")
    area = jsonstat("demo_r_d3area", landuse="TOTAL", unit="KM2").pivot(index="geo", columns="time", values="value")
    bdl = {x["id"]: {int(v["year"]): v["val"] for v in x["values"]}
           for x in json.loads((RAW / "bdl" / "72305_L5.json").read_text())["results"]}
    stock = {x["id"]: {int(v["year"]): v["val"] for v in x["values"]}
             for x in json.loads((RAW / "bdl" / "60811_L5.json").read_text())["results"]}
    for nuts, units in WARSAW.items():
        for year in range(2001, 2023):
            vals = [bdl[u].get(year - 1) for u in units if bdl[u].get(year - 1) is not None]
            pop.loc[nuts, str(year)] = sum(vals)
    gdp = jsonstat("nama_10r_3gdp", unit="MIO_PPS_EU27_2020").pivot(index="geo", columns="time", values="value")
    d11 = jsonstat("cens_11dwob_r3", housing="DW", building="TOTAL").set_index("geo").value
    for nuts, units in WARSAW.items():
        d11[nuts] = sum(stock[u][2010] for u in units if 2010 in stock[u])
    num = sum(jsonstat("cens_21dwop_r3", housing="DW", y_const=c).set_index("geo").value
              for c in ["Y2011-2015", "Y_GE2016"])
    num16 = jsonstat("cens_21dwop_r3", housing="DW", y_const="Y_GE2016").set_index("geo").value
    total = jsonstat("cens_21dwop_r3", housing="DW", y_const="TOTAL").set_index("geo").value
    unk = jsonstat("cens_21dwop_r3", housing="DW", y_const="UNK").set_index("geo").value
    # ČSÚ-rebuilt Czech numerator: dwellings completed in new family and multi-dwelling houses, 2011-01 to census day
    cm = pd.read_parquet(RAW / "czech_monthly.parquet")
    cm = cm[(cm.date >= "2011-01-01") & (cm.date <= "2021-03-01")].copy()
    cm["w"] = np.where(cm.date == "2021-03-01", 26 / 31, 1.0)
    csu = (cm.w * (cm.completed_family + cm.completed_multi)).groupby(cm.kraj).sum()
    sectors = ["A", "B-E", "F", "G-I", "J", "K", "L", "M_N", "O-Q", "R-U"]
    emp = pd.concat([jsonstat("nama_10r_3empers", unit="THS", wstatus="EMP", nace_r2=k).assign(nace_r2=k)
                     for k in sectors]).rename(columns={"value": "v"})

    def one(members: list, country: str) -> dict:
        def growth(y1: int, first: int = 2001, last: int = 2007, min_len: int = 4):
            for t0 in range(first, last + 1):
                v0 = [lookup(pop[str(t0)], chain, g) for g in members]
                v1 = [lookup(pop[str(y1)], chain, g) for g in members]
                if not any(np.isnan(v0 + v1)) and y1 - t0 >= min_len:
                    return t0, sum(v1), (np.log(sum(v1)) - np.log(sum(v0))) / (y1 - t0)
            return None, np.nan, np.nan
        t0, p11, g = growth(2011)
        _, p21, g21 = growth(2021, 2011, 2011, 10)
        gd = [lookup(gdp["2012" if x.startswith("RO") else "2011"], chain, x) for x in members]
        dw = [lookup(d11, chain, x) for x in members]
        ar = [lookup(area["2011"], chain, x) for x in members]
        ref = pd.Timestamp(REF_DATE.get(country, DEFAULT_REF))
        years = (ref - pd.Timestamp("2011-01-01")).days / 365.25
        years16 = (ref - pd.Timestamp("2016-01-01")).days / 365.25
        n_eu = sum(num.get(x, np.nan) for x in members)
        n16 = sum(num16.get(x, np.nan) for x in members)
        n_csu = sum(csu.get(x, np.nan) for x in members) if country == "CZ" else np.nan
        # Bartik: 2001 (or first year to 2007) NACE shares x national log employment growth to 2011
        bart = np.nan
        for b0 in range(2001, 2008):
            sh = emp[(emp.time == str(b0)) & emp.geo.isin(members) & emp.nace_r2.isin(sectors)]
            if sh.geo.nunique() == len(members) and sh.nace_r2.nunique() == len(sectors):
                nat = emp[emp.geo == country].pivot(index="nace_r2", columns="time", values="v")
                if str(b0) in nat and "2011" in nat:
                    s = sh.groupby("nace_r2").v.sum()
                    gr = np.log(nat.loc[sectors, "2011"] / nat.loc[sectors, str(b0)])
                    bart = float((s / s.sum() * gr).sum() / (2011 - b0))
                break
        return {"pop2011": p11, "g": g, "t0": t0, "g21": g21, "gdp": np.sum(gd), "dw2011": np.sum(dw),
                "area": np.sum(ar), "num_eu": n_eu, "num16": n16, "num_csu": n_csu, "years": years,
                "years16": years16, "unk": sum(unk.get(x, 0) for x in members) / sum(total.get(x, np.nan)
                                                                                   for x in members),
                "bartik": bart}

    metros, cores = [], []
    for code, r in m.iterrows():
        mem = r.members.split(",")
        rec = one(mem, r.country)
        metros.append({"id": code, "country": r.country, "capital": bool(r.capital), **rec,
                       "in_primary": bool(r.in_primary)})
        dens = {x: lookup(pop["2011"], chain, x) / lookup(area["2011"], chain, x) for x in mem}
        core = max(mem, key=lambda x: -np.inf if np.isnan(dens[x]) else dens[x])
        cores.append({"id": core, "metro": code, "country": r.country, "capital": bool(r.capital),
                      **one([core], r.country), "in_primary": bool(r.in_primary)})
    return {"metro": pd.DataFrame(metros).set_index("id"), "core": pd.DataFrame(cores).set_index("id")}


def h1_design(d: pd.DataFrame, numerator: str = "num_eu", growth: str = "g", years: str = "years") -> tuple:
    y = np.log(d[numerator] / d[years] / d.pop2011 * 1000)
    g = d[growth]
    if growth == "bartik":
        X = pd.DataFrame({"g": g}, index=d.index)
    else:
        X = pd.DataFrame({"g_pos": np.maximum(g, 0), "g_neg": np.minimum(g, 0)}, index=d.index)
    X["ln_pop"] = np.log(d.pop2011)
    if "gdp" in d and d.gdp.notna().all():
        X["ln_gdppc"] = np.log(d.gdp * 1e6 / d.pop2011)
    X["ln_dw"] = np.log(d.dw2011 / d.pop2011 * 1000)
    X["capital"] = d.capital.astype(float)
    return y, sm.add_constant(X)


def loco_scores(y: pd.Series, X: pd.DataFrame, country: pd.Series, w: pd.Series | None = None) -> pd.Series:
    """Studentised leave-one-country-out residuals (locally weighted split conformal, Lei et al. 2018)."""
    s = pd.Series(np.nan, index=y.index)
    for c in country.unique():
        tr, te = country != c, country == c
        ww = None if w is None else w[tr]
        f = (sm.WLS(y[tr], X[tr], weights=ww) if ww is not None else sm.OLS(y[tr], X[tr])).fit()
        a = np.abs(f.resid)
        fs = (sm.WLS(a, X[tr], weights=ww) if ww is not None else sm.OLS(a, X[tr])).fit()
        sig = np.maximum(fs.predict(X[te]), 0.25 * np.median(a))
        s[te] = (y[te] - f.predict(X[te])) / sig
    return s


def h1_rank(d: pd.DataFrame, prague: str, weighted: bool = False, **kw) -> dict:
    y, X = h1_design(d, **kw)
    ok = y.notna() & X.notna().all(axis=1)
    y, X, dd = y[ok], X[ok], d[ok]
    s = loco_scores(y, X, dd.country, dd.pop2011 if weighted else None)
    others = s.drop(prague)
    rank = int(1 + (others < s[prague]).sum())
    p = float((1 + (others <= s[prague]).sum()) / (len(others) + 1))
    cz = dd.country == "CZ"
    by_country = s.groupby(dd.country).mean().sort_values()
    out = {"n": int(len(s)), "score": round(float(s[prague]), 3), "rank_from_lowest": rank, "p": round(p, 4),
           "czechia_mean_score": round(float(s[cz].mean()), 3),
           "prague_minus_other_czech": round(float(s[prague] - s[cz].drop(prague).mean()), 3)
           if cz.sum() > 1 else None,
           "country_rank_from_lowest": int(list(by_country.index).index("CZ") + 1),
           "countries": int(len(by_country)),
           "observed_per_1000_year": round(float(np.exp(y[prague])), 2)}
    for city, key in [("vienna", "AT"), ("warsaw", "PL")]:
        ids = [i for i in s.index if i.startswith(key) and (i.endswith("001MC") or i in ("AT130", "PL911"))]
        if ids:
            out[city] = {"id": ids[0], "score": round(float(s[ids[0]]), 3),
                         "rank_from_lowest": int(1 + (s.drop(ids[0]) < s[ids[0]]).sum()),
                         "observed_per_1000_year": round(float(np.exp(y[ids[0]])), 2)}
    out["_scores"] = s
    out["_fit"] = sm.OLS(y, X).fit(cov_type="HC1")
    return out


def h1_statement(p_metro: float, p_core: float) -> str:
    if p_metro <= 0.05 and p_core <= 0.05:
        return "Prague builds less than peers with its demand"
    if p_core <= 0.05 < p_metro:
        return "Prague builds little in the city but normally across its metropolitan region"
    return "Within the range of European peers"


def h1() -> dict:
    reg = h1_regions()
    met = reg["metro"][reg["metro"].in_primary]
    core = reg["core"][reg["core"].in_primary]
    core = core[~core.index.duplicated()]
    res = {}
    for label, num in [("eurostat", "num_eu"), ("csu_rebuilt", "num_csu")]:
        mm, cc = met.copy(), core.copy()
        if num == "num_csu":
            mm.loc[mm.country == "CZ", "num_eu"] = mm.loc[mm.country == "CZ", "num_csu"]
            cc.loc[cc.country == "CZ", "num_eu"] = cc.loc[cc.country == "CZ", "num_csu"]
        rm, rc = h1_rank(mm, "CZ001MC"), h1_rank(cc, PRAGUE)
        res[label] = {"metro": {k: v for k, v in rm.items() if not k.startswith("_")},
                      "core": {k: v for k, v in rc.items() if not k.startswith("_")},
                      "statement": h1_statement(rm["p"], rc["p"])}
        if label == "eurostat":
            fit = rm["_fit"]
            res["R1"] = {"b_growth_positive": round(float(fit.params["g_pos"]), 3),
                         "p_one_sided": round(float(1 - norm.cdf(fit.tvalues["g_pos"])), 4),
                         "passed": bool(fit.params["g_pos"] > 0 and fit.tvalues["g_pos"] > 1.645)}
            res["coefficients_full_sample"] = {k: round(float(v), 3) for k, v in fit.params.items()}
            res["_frames"] = {"metro": mm, "core": cc}
            res["_scores"] = {"metro": rm["_scores"], "core": rc["_scores"]}
    # H6: Prague among the 14 kraje, raw annualised ČSÚ rate (no model)
    pop = jsonstat("demo_r_pjanaggr3", sex="T", age="TOTAL", unit="NR").pivot(index="geo", columns="time",
                                                                              values="value")["2011"]
    cm = pd.read_parquet(RAW / "czech_monthly.parquet")
    cm = cm[(cm.date >= "2011-01-01") & (cm.date <= "2021-03-01")].copy()
    cm["w"] = np.where(cm.date == "2021-03-01", 26 / 31, 1.0)
    rate = ((cm.w * (cm.completed_family + cm.completed_multi)).groupby(cm.kraj).sum()
            / ((pd.Timestamp("2021-03-26") - pd.Timestamp("2011-01-01")).days / 365.25) / pop.reindex(
                cm.kraj.unique()) * 1000)
    res["H6_czech_kraje"] = {"prague_rate": round(float(rate[PRAGUE]), 2),
                             "rank_from_lowest_of_14": int((rate < rate[PRAGUE]).sum() + 1),
                             "median_other": round(float(rate.drop(PRAGUE).median()), 2)}
    return res


# ------------------------------------------------------------------------------------------------ H2
def kernel(mu: float, phi: float, k: int, kind: str = "gamma") -> np.ndarray:
    edges = np.arange(k + 2)
    if kind == "exponential":
        return np.diff(1 - np.exp(-edges / mu))
    return np.diff(gamma_dist.cdf(edges, a=phi, scale=mu / phi))


def lag_fit(c, s, months, k, kind="gamma", start=None, keep=None):
    """Profile NLS of C on θ·(w ∗ S) + month effects. `keep` masks months excluded from the fit (robustness)."""
    d = pd.get_dummies(months).to_numpy(float)
    keep = np.ones(len(c), bool) if keep is None else keep

    def design(par):
        mu = np.exp(par[0])
        phi = np.exp(par[1]) if kind == "gamma" else 1.0
        conv = np.convolve(s, kernel(mu, phi, k, kind))[k:len(s)]
        return np.column_stack([conv, d])

    def sse(par):
        x = design(par)
        b = np.linalg.lstsq(x[keep], c[keep], rcond=None)[0]
        return float(((c[keep] - x[keep] @ b) ** 2).sum())

    # point estimates: best of a grid of starting values; bootstrap draws: warm start at the point estimate
    starts = [start] if start is not None else [(m0, p0) for m0 in (6, 12, 24, 36, 48) for p0 in (2, 8)]
    best = None
    for st in starts:
        x0 = np.log(st) if kind == "gamma" else np.r_[np.log(st[0]), 0.0]
        r = minimize(sse, x0, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-8, "maxiter": 600})
        best = r if best is None or r.fun < best.fun else best
    r = best
    x = design(r.x)
    b = np.linalg.lstsq(x[keep], c[keep], rcond=None)[0]
    mu, phi = float(np.exp(r.x[0])), float(np.exp(r.x[1])) if kind == "gamma" else 1.0
    fitted = x @ b
    return {"mu": mu, "phi": phi, "theta": float(b[0]), "fitted": fitted, "resid": c - fitted,
            "signal": x[:, 0] * b[0], "sse": r.fun, "tail": float(1 - kernel(mu, phi, k, kind).sum())}


def h2_series(treated=(PRAGUE,), reference=None, series=("permitted_multi", "completed_multi")):
    m = pd.read_parquet(RAW / "czech_monthly.parquet")
    ref = reference or [k for k in m.kraj.unique() if k not in (PRAGUE, CENTRAL)]
    get = lambda ks, col: m[m.kraj.isin(ks)].groupby("date")[col].sum()  # noqa: E731
    sp = sum(get(treated, c) for c in series[0].split("+"))
    cp = sum(get(treated, c) for c in series[1].split("+"))
    sr = sum(get(ref, c) for c in series[0].split("+"))
    cr = sum(get(ref, c) for c in series[1].split("+"))
    return sp, cp, sr, cr


def h2(rng, treated=(PRAGUE,), reference=None, series=("permitted_multi", "completed_multi"), k=72,
       kind="gamma", block=None, b=B, exclude_covid=False) -> dict:
    sp, cp, sr, cr = h2_series(treated, reference, series)
    first = pd.Timestamp("2013-01-01") if k == 72 else pd.Timestamp("2015-01-01")
    start_s = first - pd.DateOffset(months=k)
    win = (cp.index >= first) & (cp.index <= "2024-12-01")
    sidx = (sp.index >= start_s) & (sp.index <= "2024-12-01")
    months = cp.index[win].month.to_numpy()
    keep = None
    if exclude_covid:
        dts = cp.index[win]
        keep = ~((dts >= "2020-03-01") & (dts <= "2021-06-01"))
    fits = {}
    for u, s, c in (("prague", sp, cp), ("rest", sr, cr)):
        fits[u] = lag_fit(c[win].to_numpy(float), s[sidx].to_numpy(float), months, k, kind, keep=keep)
        fits[u]["s"], fits[u]["c"] = s[sidx].to_numpy(float), c[win].to_numpy(float)
    delta = fits["prague"]["mu"] - fits["rest"]["mu"]
    if block is None:
        block = float(np.mean([optimal_block_length(fits[u]["resid"])["stationary"].iloc[0] for u in fits]))
    n = len(months)
    draws, thetas, mus = [], [], []
    for _ in range(b):
        idx = np.empty(n, int)
        idx[0] = rng.integers(n)
        new = rng.random(n) < 1 / block
        jumps = rng.integers(n, size=n)
        for i in range(1, n):
            idx[i] = jumps[i] if new[i] else (idx[i - 1] + 1) % n
        est = {}
        for u in fits:
            f = fits[u]
            ystar = f["fitted"] + f["resid"][idx]
            r = lag_fit(ystar, f["s"], months, k, kind, start=(f["mu"], f["phi"]), keep=keep)
            est[u] = r
        draws.append(est["prague"]["mu"] - est["rest"]["mu"])
        thetas.append(est["prague"]["theta"])
        mus.append(est["prague"]["mu"])
    draws = np.array(draws)
    se = float(draws.std(ddof=1))
    out = {"mu_prague": round(fits["prague"]["mu"], 2), "mu_rest": round(fits["rest"]["mu"], 2),
           "phi_prague": round(fits["prague"]["phi"], 2), "phi_rest": round(fits["rest"]["phi"], 2),
           "theta_prague": round(fits["prague"]["theta"], 3), "theta_rest": round(fits["rest"]["theta"], 3),
           "tail_mass_prague": round(fits["prague"]["tail"], 4), "tail_mass_rest": round(fits["rest"]["tail"], 4),
           "delta_months": round(delta, 2), "se_boot": round(se, 2),
           "ci90": [round(float(np.quantile(draws, 0.05)), 2), round(float(np.quantile(draws, 0.95)), 2)],
           "p": float(1 - norm.cdf(delta / se)), "block_length": round(block, 1), "reps": b,
           "noise_ratio": {u: round(float(fits[u]["resid"].std() / fits[u]["signal"].std()), 2) for u in fits},
           "corr_theta_mu_prague": round(float(np.corrcoef(thetas, mus)[0, 1]), 3)}
    out["_fits"] = fits
    out["_months"] = months
    return out


def h2_profile(fits, months, k=72) -> dict:
    prof = {}
    for u, f in fits.items():
        rows = []
        for mu in np.arange(6, 61, 1.0):
            d = pd.get_dummies(months).to_numpy(float)

            def sse(lphi):
                conv = np.convolve(f["s"], kernel(mu, np.exp(lphi[0]), k))[k:len(f["s"])]
                x = np.column_stack([conv, d])
                b = np.linalg.lstsq(x, f["c"], rcond=None)[0]
                return float(((f["c"] - x @ b) ** 2).sum())
            r = minimize(sse, [np.log(4.0)], method="Nelder-Mead")
            rows.append((mu, r.fun))
        t = len(f["c"])
        ll = np.array([-t / 2 * np.log(v / t) for _, v in rows])
        prof[u] = {"mu": [r[0] for r in rows], "rel_loglik": [round(float(v), 3) for v in ll - ll.max()]}
    return prof


def little_band() -> dict:
    s = pd.read_excel(DATA / "praha4" / "byt_vystavba.xlsx", "data", header=None)
    years = s.iloc[3, 2:].tolist()
    rows = {str(s.iloc[i, 0]).strip(): s.iloc[i, 2:].tolist() for i in range(len(s))}
    years = [int(float(y)) for y in years]
    u = pd.to_numeric(pd.Series(rows["Rozestavěné byty k 31.12. 3)"], index=years), errors="coerce")
    c = pd.to_numeric(pd.Series(rows["Dokončené byty celkem"], index=years), errors="coerce")
    win = list(range(2013, 2025))
    if u[win].isna().all():
        return {"run": False, "reason": "the Prague file shows '.' for dwellings under construction in every year "
                                        "of the window (not published since 2009, its note 3)"}
    ratios = [float(u[y] / c[y] * 12) for y in win]
    return {"months_mean_ratio_2013_2024": round(float(u[win].mean() / c[win].mean() * 12), 1),
            "annual_range": [round(min(ratios), 1), round(max(ratios), 1)],
            "note": "all dwellings, Prague file; stock computed by ČSÚ from permitted and completed dwellings"}


# ------------------------------------------------------------------------------------------------ H3
def icncr_prices(block_title: str) -> pd.DataFrame:
    t = pd.read_excel(RAW / "csu" / "icncr.xlsx", header=None)
    head = t.iloc[0].ffill()
    q = t.iloc[1]
    idx = [i for i, (y, v) in enumerate(zip(head, q)) if isinstance(v, str) and v.startswith("Čtv")]
    cols = [pd.Period(f"{int(float(head[i]))}Q{str(q[i])[-1]}", "Q") for i in idx]
    start = next(i for i in range(len(t)) if str(t.iloc[i, 0]).startswith(block_title))
    rows = [i for i in range(start + 1, len(t)) if pd.notna(t.iloc[i, 0])][:16]
    block = t.iloc[rows]
    return pd.DataFrame(block.iloc[:, idx].apply(pd.to_numeric, errors="coerce").to_numpy(float),
                        index=block.iloc[:, 0].str.strip(), columns=cols)


def h3_frame(series="permitted_multi", price_block="Index cen bytů o základu 2010"):
    m = pd.read_parquet(RAW / "czech_monthly.parquet")
    names = pd.read_csv(RAW / "csu" / "STA09B.csv", usecols=["Kraje", "Uz2"], dtype=str).drop_duplicates()
    code = dict(zip(names.Kraje.str.strip(), names.Uz2))
    m["q"] = m.date.dt.to_period("Q")
    y = sum(m.groupby(["kraj", "q"])[c].sum() for c in series.split("+")).rename("S").reset_index()
    p = icncr_prices(price_block)
    p = p[p.index.isin(code)]
    p.index = [code[i] for i in p.index]
    dlp = np.log(p).diff(axis=1)
    d11 = jsonstat("cens_11dwob_r3", housing="DW", building="TOTAL").set_index("geo").value
    d21 = jsonstat("cens_21dwob_r3", housing="DW", building="TOTAL").set_index("geo").value
    t11, t21 = pd.Timestamp("2011-03-26"), pd.Timestamp("2021-03-26")
    y["stock"] = [d11[k] * (d21[k] / d11[k]) ** (((q.start_time + pd.Timedelta(days=45)) - t11).days
                                                 / (t21 - t11).days) for k, q in zip(y.kraj, y.q)]
    return y[y.kraj != CENTRAL], dlp


def h3_fit(y, dlp, treated=PRAGUE, lags=12, first=None, last=pd.Period("2024Q4", "Q"), exclude=None):
    first = first or (dlp.columns[1] + lags)
    d = y[(y.q >= first) & (y.q <= last)].copy()
    if exclude is not None:
        d = d[~d.q.isin(exclude)]
    for kk in range(3):
        d[f"z{kk}"] = [sum((lag ** kk) * dlp.loc[r, q - lag] for lag in range(1, lags + 1))
                       for r, q in zip(d.kraj, d.q)]
        d[f"zp{kk}"] = d[f"z{kk}"] * (d.kraj == treated)
    X = pd.concat([pd.get_dummies(d.kraj, prefix="k", drop_first=True, dtype=float),
                   pd.get_dummies(d.q.astype(str), prefix="q", drop_first=True, dtype=float),
                   d[["z0", "z1", "z2", "zp0", "zp1", "zp2"]]], axis=1)
    X = sm.add_constant(X)
    off = np.log(d.stock.to_numpy())
    r = sm.GLM(d.S.to_numpy(float), X, family=sm.families.Poisson(), offset=off).fit()
    lv = np.arange(1, lags + 1)
    cvec = np.array([lags, lv.sum(), (lv ** 2).sum()], float)
    psi = ppml_if(X.to_numpy(float), d.S.to_numpy(float), np.asarray(r.mu))
    cols = list(X.columns)
    rel_idx = [cols.index(c) for c in ("zp0", "zp1", "zp2")]
    rest_idx = [cols.index(c) for c in ("z0", "z1", "z2")]
    rel = float(cvec @ r.params.iloc[rel_idx])
    rest = float(cvec @ r.params.iloc[rest_idx])
    psi_rel = pd.Series(psi[:, rel_idx] @ cvec).groupby(d.q.to_numpy()).sum().to_numpy()
    psi_rest = pd.Series(psi[:, rest_idx] @ cvec).groupby(d.q.to_numpy()).sum().to_numpy()
    prof = lambda idx: np.array([r.params.iloc[idx[0]] + r.params.iloc[idx[1]] * lag + r.params.iloc[idx[2]] * lag ** 2  # noqa: E731
                                 for lag in lv])
    b_rest, b_rel = prof(rest_idx), prof(rel_idx)
    com = lambda b: float((lv * b).sum() / b.sum()) if abs(b.sum()) > 1e-9 else np.nan  # noqa: E731
    return {"rel": rel, "rest": rest, "psi_rel": psi_rel, "psi_rest": psi_rest, "T": int(d.q.nunique()),
            "profile_rest": b_rest, "profile_prague": b_rest + b_rel,
            "com_rest": com(b_rest), "com_prague": com(b_rest + b_rel)}


def ewc(est: float, psi: np.ndarray, nu: int, level=0.90) -> dict:
    t = len(psi)
    j = np.arange(1, nu + 1)
    lam = np.sqrt(2 / t) * np.array([(psi * np.cos(np.pi * k * (np.arange(1, t + 1) - 0.5) / t)).sum() for k in j])
    se = float(np.sqrt(t * (lam ** 2).mean()))
    cv = tdist.ppf(0.5 + level / 2, nu)
    return {"estimate": round(est, 3), "se": round(se, 3), "ci90": [round(est - cv * se, 3), round(est + cv * se, 3)],
            "p_below_zero": float(tdist.cdf(est / se, nu)), "p_above_zero": float(1 - tdist.cdf(est / se, nu)),
            "nu": nu}


def fixed_b(est: float, psi: np.ndarray, rng, reps=20_000) -> dict:
    """Bartlett kernel with bandwidth T (b = 1); critical value simulated under the fixed-b limit."""
    t = len(psi)

    def lrv(x):
        k = 1 - np.abs(np.subtract.outer(np.arange(t), np.arange(t))) / t
        return float(x @ k @ x) / t
    u = rng.standard_normal((reps, t))
    stats = np.array([u_.sum() / np.sqrt(t * lrv(u_ - u_.mean())) for u_ in u])
    cv = float(np.quantile(np.abs(stats), 0.90))
    se = float(np.sqrt(t * lrv(psi)))
    return {"estimate": round(est, 3), "ci90": [round(est - cv * se, 3), round(est + cv * se, 3)],
            "critical_value": round(cv, 3)}


def h3(rng) -> dict:
    y, dlp = h3_frame()
    f = h3_fit(y, dlp)
    nu = int(round(0.4 * f["T"] ** (2 / 3)))
    rel = ewc(f["rel"], f["psi_rel"], nu)
    rest = ewc(f["rest"], f["psi_rest"], nu)
    ratio = (f["rest"] + f["rel"]) / f["rest"] if f["rest"] != 0 else np.nan
    later = (f["com_prague"] - f["com_rest"]) >= 2
    if rel["ci90"][1] < 0 and ratio <= 0.5:
        statement = "Prague's permitting responds less"
    elif f["rel"] >= 0 and later:
        statement = "Prague's permitting responds later"
    else:
        statement = "Cannot be told apart"
    ranks = {}
    for k in y.kraj.unique():
        ranks[k] = h3_fit(y, dlp, treated=k)["rel"]
    rs = pd.Series(ranks)
    yf, dlf = h3_frame(price_block="Index cen rodinných domů o základu 2010")
    fp = h3_fit(yf, dlf)
    f4 = h3_fit(y, dlp, lags=4)
    out = {"quarters": f["T"], "first_quarter": str(y.q[y.q >= dlp.columns[1] + 12].min()),
           "relative_cumulative": rel, "rest_cumulative": rest,
           "ratio_prague_to_rest": round(float(ratio), 3),
           "centre_of_mass_quarters": {"rest": round(f["com_rest"], 2), "prague": round(f["com_prague"], 2)},
           "profile_rest": [round(float(v), 4) for v in f["profile_rest"]],
           "profile_prague": [round(float(v), 4) for v in f["profile_prague"]],
           "statement": statement,
           "fixed_b": fixed_b(f["rel"], f["psi_rel"], rng),
           "rank_of_prague_from_lowest": int((rs < rs[PRAGUE]).sum() + 1), "kraje": int(len(rs)),
           "placebo_family_house_index": ewc(fp["rel"], fp["psi_rel"], int(round(0.4 * fp["T"] ** (2 / 3)))),
           "four_lags_35_quarters": {**ewc(f4["rel"], f4["psi_rel"], int(round(0.4 * f4["T"] ** (2 / 3)))),
                                     "quarters": f4["T"]}}
    out["R3"] = {"rest_cumulative": rest["estimate"], "p_one_sided": round(rest["p_above_zero"], 4),
                 "passed": bool(rest["p_above_zero"] < 0.05)}
    return out


# ------------------------------------------------------------------------------------------------ H4
def bdl(var: int) -> pd.DataFrame:
    r = json.loads((RAW / "bdl" / f"{var}_L5.json").read_text())["results"]
    rows = [{"unit": x["id"], "name": x["name"], "year": int(v["year"]), "val": v["val"], "attr": v.get("attrId")}
            for x in r for v in x["values"]]
    d = pd.DataFrame(rows)
    price = var in (633677, 633682, 633687)
    if price:
        d.loc[(d.attr == 91) | (d.val == 0), "val"] = np.nan
    walb = d.name.str.contains("wałbrzyski|Wałbrzych", case=False)
    d.loc[walb, "unit"] = "070200000000"  # powiat wałbrzyski + Wałbrzych, merged (voivodeship 02 kept)
    return d.groupby(["unit", "year"]).val.agg("mean" if price else "sum").reset_index()


def h4_frame(market=(747732,), nonmarket=(747734, 747735), price=633677, years=(2012, 2024)):
    parts = []
    for grp, vars_ in (("M", market), ("NM", nonmarket)):
        s = None
        for v in vars_:
            x = bdl(v).set_index(["unit", "year"]).val.fillna(0)
            s = x if s is None else s.add(x, fill_value=0)
        parts.append(s.rename("S").reset_index().assign(nm=int(grp == "NM")))
    d = pd.concat(parts)
    p = bdl(price).sort_values(["unit", "year"])
    p["g"] = p.groupby("unit").val.transform(lambda s: np.log(s).diff())
    p["g_lag"] = p.groupby("unit").g.shift(1)
    st = bdl(60811).sort_values(["unit", "year"])
    st["stock_lag"] = st.groupby("unit").val.shift(1)
    d = d.merge(p[["unit", "year", "g_lag"]], on=["unit", "year"]).merge(st[["unit", "year", "stock_lag"]],
                                                                       on=["unit", "year"])
    d = d[d.year.between(*years) & d.g_lag.notna() & (d.stock_lag > 0)]
    support = d[(d.nm == 1)].groupby("unit").S.sum().pipe(lambda s: s[s > 0]).index
    d = d[d.unit.isin(support)].copy()
    d["g_nm"] = d.g_lag * d.nm
    d["fe"] = d.unit + "_" + d.nm.astype(str)
    d["ye"] = d.year.astype(str) + "_" + d.nm.astype(str)
    d["lnstock"] = np.log(d.stock_lag)
    d["voiv"] = d.unit.str[2:4]
    # all-zero powiat-by-group cells carry no information in PPML and break the restricted fit (no-op in the main
    # frame, which has none)
    return d[d.groupby("fe").S.transform("sum") > 0]


def fe_matrix(d: pd.DataFrame, cols: list) -> np.ndarray:
    return np.column_stack([pd.get_dummies(d[c], drop_first=(i > 0), dtype=float).to_numpy() for i, c in
                            enumerate(cols)])


def h4(rng, d=None, cluster="unit", b=B) -> dict:
    import pyfixest as pf

    d = h4_frame() if d is None else d
    fit = pf.fepois("S ~ g_lag + g_nm | fe + ye", data=d, offset="lnstock", vcov={"CRV1": cluster})
    coef, se = fit.coef(), fit.se()
    FE = fe_matrix(d, ["fe", "ye"])
    Xr = np.column_stack([FE, d.g_lag.to_numpy()])
    wcr = score_wcr(d.S.to_numpy(float), Xr, d.lnstock.to_numpy(), d.g_nm.to_numpy(), d[cluster].to_numpy(),
                    rng, b)
    out = {"beta_market": round(float(coef["g_lag"]), 3), "beta_nonmarket": round(float(coef["g_lag"]
                                                                                   + coef["g_nm"]), 3),
           "difference": round(float(coef["g_nm"]), 3), "se_cr1": round(float(se["g_nm"]), 3),
           "p_cr1": float(norm.cdf(coef["g_nm"] / se["g_nm"])), "p_wcr": wcr["p_negative"],
           "p": wcr["p_negative"], "clusters": wcr["clusters"], "effective_clusters": wcr["effective_clusters"],
           "powiats": int(d.unit.nunique()), "rows": int(len(d)),
           "ci90_cr1": [round(float(coef["g_nm"] - 1.645 * se["g_nm"]), 3),
                        round(float(coef["g_nm"] + 1.645 * se["g_nm"]), 3)]}
    out["R4"] = {"beta_market": out["beta_market"], "p_one_sided": float(1 - norm.cdf(coef["g_lag"] / se["g_lag"])),
                 "passed": bool(coef["g_lag"] / se["g_lag"] > 1.645)}
    return out


def h4_cyclical(d=None) -> dict:
    import pyfixest as pf

    d = h4_frame() if d is None else d
    w = d[d.nm == 0].groupby("year").apply(lambda t: np.average(t.g_lag, weights=np.exp(t.lnstock)))
    d = d.assign(gn=d.year.map(w), trend=d.year - 2012)
    d["gn_nm"], d["trend_nm"] = d.gn * d.nm, d.trend * d.nm
    fit = pf.fepois("S ~ gn + gn_nm + trend + trend_nm | fe", data=d, offset="lnstock", vcov={"CRV1": "unit"})
    c, s = fit.coef(), fit.se()
    return {"beta_market_national": round(float(c["gn"]), 3), "se_market": round(float(s["gn"]), 3),
            "beta_nonmarket_national": round(float(c["gn"] + c["gn_nm"]), 3),
            "difference": round(float(c["gn_nm"]), 3), "se_difference": round(float(s["gn_nm"]), 3),
            "note": "descriptive; no year effects; group trends"}


# ------------------------------------------------------------------------------------------------ H5
def spline(x: np.ndarray, knots: np.ndarray) -> np.ndarray:
    k = knots
    cols = [x]
    for j in range(len(k) - 2):
        cols.append(np.maximum(x - k[j], 0) ** 3 - np.maximum(x - k[-2], 0) ** 3 * (k[-1] - k[j]) / (k[-1] - k[-2])
                    + np.maximum(x - k[-1], 0) ** 3 * (k[-2] - k[j]) / (k[-1] - k[-2]))
    return np.column_stack(cols)


def h5_counts(cells: pd.DataFrame, start: str, end: str, drop_types=False) -> np.ndarray:
    from shapely import STRtree, wkb
    from shapely.geometry import Point

    b = pd.read_parquet(RAW / "prague" / "buildings.parquet")
    b = b[b.nespravny.isna() | (b.nespravny.astype(str).str.strip() == "")]
    if drop_types:
        b = b[~b.druhkonstrukcekod.isin([10, 4])]
    done = pd.to_datetime(b.dokonceni, unit="ms", errors="coerce")
    b = b[(done >= start) & (done <= end)]
    polys = [wkb.loads(g) for g in cells.geom_wkb]
    tree = STRtree(polys)
    cell_of = np.array([(h[0] if len(h) else -1) for h in (tree.query(Point(x, y), predicate="within")
                                                           for x, y in zip(b.x, b.y))])
    ok = cell_of >= 0
    return np.bincount(cell_of[ok], weights=b.pocetbytu.to_numpy()[ok], minlength=len(cells))


def h5_design(cells: pd.DataFrame, dens=None, metro_col="log2_metro_km"):
    dens = np.log1p(cells.pop2011 / cells.area_km2).to_numpy() if dens is None else dens
    knots = np.quantile(dens, [0.05, 0.35, 0.65, 0.95])
    X = np.column_stack([np.ones(len(cells)), cells[metro_col], cells.log2_centre_km, spline(dens, knots)])
    return X, np.log(cells.area_km2.to_numpy())


def conley(psi: np.ndarray, xy: np.ndarray, h: float) -> np.ndarray:
    d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1))
    k = np.clip(1 - d / h, 0, None)
    return psi.T @ k @ psi


def h5(rng, cells=None, y=None, X=None, offset=None, clusters=None, b=B, family="poisson") -> dict:
    from shapely import wkb

    cells = pd.read_parquet(RAW / "prague_cells.parquet") if cells is None else cells
    if y is None:
        y = h5_counts(cells, "2012-01-01", "2021-03-25")
    if X is None:
        X, offset = h5_design(cells)
    clusters = cells.admin_district.to_numpy() if clusters is None else clusters
    r = sm.GLM(y, X, family=sm.families.Poisson() if family == "poisson" else family, offset=offset).fit()
    mu = np.asarray(r.mu)
    psi = ppml_if(X, y, mu)
    xy = np.array([[wkb.loads(g).centroid.x, wkb.loads(g).centroid.y] for g in cells.geom_wkb])
    g = float(r.params[1])
    se15 = float(np.sqrt(conley(psi, xy, 1500)[1, 1]))
    se3 = float(np.sqrt(conley(psi, xy, 3000)[1, 1]))
    wcr = score_wcr(y, np.delete(X, 1, axis=1), offset, X[:, 1], clusters, rng, b)
    p_neg = max(float(norm.cdf(g / se15)), wcr["p_negative"])
    p_pos = max(float(1 - norm.cdf(g / se15)), wcr["p_positive"])
    return {"gamma": round(g, 3), "se_conley_1_5km": round(se15, 3), "se_conley_3km": round(se3, 3),
            "ci90_conley": [round(g - 1.645 * se15, 3), round(g + 1.645 * se15, 3)],
            "p_conley_negative": float(norm.cdf(g / se15)), "p_wcr_negative": wcr["p_negative"],
            "p": p_neg, "p_positive": p_pos, "p_conley3_negative": float(norm.cdf(g / se3)),
            "effective_clusters": wcr["effective_clusters"], "clusters": wcr["clusters"],
            "density_ratio_per_doubling": round(float(np.exp(g)), 3), "cells": int(len(y)),
            "flats": int(y.sum()), "delta_centre": round(float(r.params[2]), 3)}


# ------------------------------------------------------------------------------------------------ main
def main() -> None:
    rng = np.random.default_rng(SEED)
    out: dict = {"design": "docs/research/prague-housing-design.md (v2, 503ef06)", "seed": SEED}

    h1r = h1()
    out["H1"] = {k: v for k, v in h1r.items() if not k.startswith("_")}
    for num in ("eurostat", "csu_rebuilt"):
        st = out["H1"][num]["statement"]
        out["H1"][num]["label"] = st if out["H1"]["R1"]["passed"] else f"uninformative (R1 failed); rule gives: {st}"
    scores = h1r["_scores"]["metro"]
    frame = h1r["_frames"]["metro"]
    y1, _ = h1_design(frame)
    out["H1"]["plot"] = [{"id": i, "country": frame.country[i], "score": round(float(s), 3),
                          "rate": round(float(np.exp(y1[i])), 2)} for i, s in scores.sort_values().items()]
    print("H1", json.dumps(out["H1"]["eurostat"]["metro"]), out["H1"]["eurostat"]["statement"], flush=True)

    h2r = h2(rng)
    out["H2"] = {k: v for k, v in h2r.items() if not k.startswith("_")}
    out["H2"]["profile"] = h2_profile(h2r["_fits"], h2r["_months"])
    out["H2"]["little_band_prague"] = little_band()
    rest = h2r["_fits"]["rest"]
    out["H2"]["R2"] = {"theta_rest": round(rest["theta"], 3), "mu_rest": round(rest["mu"], 2),
                       "passed": bool(0 < rest["theta"] <= 1.2 and 3 <= rest["mu"] <= 60)}
    out["H2"]["underpowered_rule_triggered"] = bool(max(out["H2"]["noise_ratio"].values()) >= 1)
    print("H2", json.dumps({k: out["H2"][k] for k in ("delta_months", "se_boot", "p", "mu_prague", "mu_rest")}),
          flush=True)

    out["H3"] = h3(rng)
    out["H3"]["label"] = out["H3"]["statement"] if out["H3"]["R3"]["passed"] else "uninformative (R3 failed)"
    print("H3", json.dumps(out["H3"]["relative_cumulative"]), out["H3"]["statement"], flush=True)

    d4 = h4_frame()
    out["H4"] = h4(rng, d4)
    out["H4"]["cyclicality"] = h4_cyclical(d4)
    print("H4", json.dumps({k: out["H4"][k] for k in ("difference", "p_wcr", "p_cr1")}), flush=True)

    cells = pd.read_parquet(RAW / "prague_cells.parquet")
    out["H5"] = h5(rng, cells)
    for label, (a, bnd) in {"2000_2011": ("2000-01-01", "2011-12-31"),
                            "2012_2024": ("2012-01-01", "2024-12-31")}.items():
        out["H5"][f"H6_{label}"] = h5(rng, cells, y=h5_counts(cells, a, bnd), b=999)
    print("H5", json.dumps({k: out["H5"][k] for k in ("gamma", "p_conley_negative", "p_wcr_negative", "p")}),
          flush=True)

    fam = holm({"H2": out["H2"]["p"], "H4": out["H4"]["p"], "H5": out["H5"]["p"]})
    out["holm"] = fam
    relevance = {"H2": out["H2"]["R2"]["passed"], "H4": out["H4"]["R4"]["passed"]}
    for k in fam:
        fam[k]["relevance_passed"] = relevance.get(k, True)
        fam[k]["label"] = ("supported" if fam[k]["supported"] else "not supported") if fam[k]["relevance_passed"] \
            else "uninformative"
    h5r = out["H5"]
    if not fam["H5"]["supported"]:
        h5r["reading"] = ("new construction is sparser near the metro" if h5r["p_positive"] <= 0.05
                          else "indeterminate")
    else:
        h5r["reading"] = "denser near the metro"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.tolist()
                              if hasattr(o, "tolist") else str(o)) + "\n")
    print(json.dumps(fam))


if __name__ == "__main__":
    main()
