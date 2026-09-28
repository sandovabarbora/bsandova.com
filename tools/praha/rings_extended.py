"""Part 2 extended: place or people, the metro, steepening, and turnout in the centre. Estimates every registered
hypothesis in docs/research/prague-rings-design.md on the design frame built by rings_data.py.

Inference, for every confirmatory contrast, is computed from the contrast's influence function ψ (one value per
unit, so that contrast - estimate = Σ ψ_i e_i-type linear form):
  - HC1:        n/(n-k) Σ ψ_i²
  - CR1:        G/(G-1) Σ_g (Σ_{i∈g} ψ_i)², by city district
  - CR2:        the same with Bell-McCaffrey adjusted residuals, t(G-1) reference
  - Conley:     Σ_i Σ_j K(d_ij) ψ_i ψ_j, Bartlett kernel, cut-offs 1, 1.5, 3 km
  - wild cluster bootstrap (unrestricted, Webb six-point weights, bootstrap-t, B = 9 999), by city district

Sources as in rings_data.py; election results from volby.gov.cz (PS 2017, 2021, 2025 precinct CSVs).

Usage:
    uv run --with pandas --with numpy --with scipy --with statsmodels --with pyarrow --with shapely \
        python tools/praha/rings_extended.py
"""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm, t as tdist

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha2x"
OUT = ROOT / "assets" / "praha" / "rings_extended.json"
B = 9999
SEED = 20260928
PRAGUE_OKRES = 1100
FILES = {
    2017: (RAW / "PS2017data20171122_csv.zip", "pst4.csv", "pst4p.csv"),
    2021: (RAW / "PS2021_data_20211010_csv.zip", "csv/pst4.csv", "csv/pst4p.csv"),
    2025: (ROOT / "tools" / "data" / "praha2" / "PS2025data_csv.zip", "csv/pst4.csv", "csv/pst4p.csv"),
}
# list codes per election (registration, "Resolved open points"); blocs sum lists
BLOCS = {
    2017: {"ANO": [21], "SPOLU": [1, 20, 24], "PirSTAN": [15, 7]},
    2021: {"ANO": [20], "SPOLU": [13], "PirSTAN": [17]},
    2025: {"ANO": [22], "SPOLU": [11], "PirSTAN": [16, 23], "Pirates": [16]},
}
ELECTION_DAY = {2017: "2017-10-21", 2021: "2021-10-09", 2025: "2025-10-04"}
BASE = ["panel", "house", "log2_centre", "log2_metro"]
EDU = ["tertiary", "vocational", "basic", "not_stated"]
COMP = EDU + ["foreign"]
AGE = ["old", "young"]
LABELS = {"panel": "panel share (pp)", "house": "family-house share (pp)", "log2_centre": "log2 km from Můstek",
          "log2_metro": "log2 km to metro", "tertiary": "tertiary incl. VOŠ (pp of stated, 25+)",
          "vocational": "vocational, no maturita", "basic": "basic or none", "not_stated": "education not stated",
          "foreign": "foreign citizens (pp)", "old": "65+ (pp)", "young": "0-14 (pp)"}


# ---------------------------------------------------------------------------------------------------------- data

def results(year: int) -> pd.DataFrame:
    path, t_name, p_name = FILES[year]
    z = zipfile.ZipFile(path)
    t = pd.read_csv(io.BytesIO(z.read(t_name)), sep=";", encoding="cp1250")
    p = pd.read_csv(io.BytesIO(z.read(p_name)), sep=";", encoding="cp1250")
    t, p = t[t.OKRES == PRAGUE_OKRES], p[p.OKRES == PRAGUE_OKRES]
    if t.duplicated(["OBEC", "OKRSEK"]).any():
        raise ValueError(f"{year}: duplicate precinct rows")
    v = p.pivot_table(index=["OBEC", "OKRSEK"], columns="KSTRANA", values="POC_HLASU", aggfunc="sum", fill_value=0)
    d = t.set_index(["OBEC", "OKRSEK"])[["VOL_SEZNAM", "VYD_OBALKY", "PL_HL_CELK"]]
    d.columns = ["R", "E", "V"]
    for name, codes in BLOCS[year].items():
        d[name] = v.reindex(columns=codes, fill_value=0).sum(axis=1).reindex(d.index, fill_value=0)
    return d.reset_index().rename(columns={"OBEC": "momc", "OKRSEK": "cislo"})


def frame() -> pd.DataFrame:
    d = pd.read_parquet(RAW / "design.parquet")
    d["log2_centre"] = np.log2(d.centre_m / 1000)
    d["log2_metro"] = np.log2(d.metro_m / 1000)
    d["redrawn"] = pd.to_datetime(d.platiod, unit="ms") >= pd.Timestamp("2025-12-01")
    return d


def composition(t: pd.DataFrame, without_foreign: bool = False) -> pd.DataFrame:
    """Shares in pp. Education of the 25+ with stated education; foreign = non-EU + EU + not stated citizenship."""
    t = t.copy()
    if without_foreign:  # remove foreign residents proportionally from every count
        keep = (t["050"] / t["000"].where(t["000"] > 0)).fillna(1)
        for k in ["021", "022", "023", "024", "025", "011", "013"]:
            t[k] = t[k] * keep
    stated = t[["021", "022", "023", "024"]].sum(axis=1)
    return pd.DataFrame({
        "tertiary": 100 * t["024"] / stated, "vocational": 100 * t["022"] / stated,
        "basic": 100 * t["021"] / stated, "not_stated": 100 * t["025"] / (stated + t["025"]),
        "foreign": 0.0 if without_foreign else 100 * (t["051"] + t["053"] + t["054"]) / t["000"],
        "old": 100 * t["013"] / t["000"], "young": 100 * t["011"] / t["000"],
    }, index=t.index)


def housing(t: pd.DataFrame, panel_col: str = "panel_flats") -> pd.DataFrame:
    return pd.DataFrame({"panel": 100 * t[panel_col] / t.flats, "house": 100 * t.house_flats / t.flats},
                        index=t.index)


COUNT_COLS = ["000", "011", "013", "050", "021", "022", "023", "024", "025", "051", "053", "054", "flats",
              "panel_flats", "panel4_flats", "house_flats", "A_hat", "R", "E", "V", "ANO", "SPOLU", "PirSTAN",
              "Pirates"]


def to_clusters(d: pd.DataFrame) -> pd.DataFrame:
    """Sum counts within grid clusters; distances as the flat-weighted mean of log2 distances; the district is the
    one holding most of the cluster's flats; the centroid is the flat-weighted mean of precinct centroids."""
    w = d.flats.fillna(0) + 1e-9
    cols = [c for c in COUNT_COLS if c in d]
    c = d.groupby("cell")[cols].sum()
    for k in ["log2_centre", "log2_metro", "cx", "cy"]:
        c[k] = (d[k] * w).groupby(d.cell).sum() / w.groupby(d.cell).sum()
    c["district"] = d.assign(w=w).sort_values("w").groupby("cell").momc.last()
    c["precincts"] = d.groupby("cell").size()
    return c


def design(u: pd.DataFrame, panel_col: str = "panel_flats", without_foreign: bool = False) -> pd.DataFrame:
    return pd.concat([housing(u, panel_col), u[["log2_centre", "log2_metro"]],
                      composition(u, without_foreign)], axis=1)


# ----------------------------------------------------------------------------------------------------- inference

def webb(rng, g: int, b: int) -> np.ndarray:
    return rng.choice(np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)]), size=(b, g))


class Fit:
    """WLS fit that keeps what the influence functions need."""

    def __init__(self, y: pd.Series, x: pd.DataFrame, w: pd.Series):
        self.cols = ["const", *x.columns]
        self.X = np.c_[np.ones(len(x)), x.values]
        self.y, self.w = y.values.astype(float), w.values.astype(float)
        XtW = self.X.T * self.w
        self.bread = np.linalg.inv(XtW @ self.X)
        self.A = self.bread @ XtW  # beta = A y
        self.beta = self.A @ self.y
        self.e = self.y - self.X @ self.beta
        self.n, self.k = self.X.shape

    def row(self, name: str) -> np.ndarray:
        return self.A[self.cols.index(name)]

    def coef(self, name: str) -> float:
        return float(self.beta[self.cols.index(name)])

    def cr2_psi(self, name: str, groups: np.ndarray) -> np.ndarray:
        """Per-unit contributions with Bell-McCaffrey CR2 residuals. In the √W-transformed (unweighted) problem the
        hat matrix is symmetric; residuals of group g are premultiplied by (I - H̃_gg)^(-1/2), a pseudo-inverse
        root where a unit has leverage 1."""
        sw = np.sqrt(self.w)
        xt, et = self.X * sw[:, None], self.e * sw
        at = self.bread @ xt.T  # beta = at @ (√w y)
        out = np.zeros(self.n)
        for g in np.unique(groups):
            ix = np.where(groups == g)[0]
            h = xt[ix] @ self.bread @ xt[ix].T
            vals, vecs = np.linalg.eigh(np.eye(len(ix)) - (h + h.T) / 2)
            inv = np.where(vals > 1e-10, 1 / np.sqrt(np.clip(vals, 1e-10, None)), 0.0)
            out[ix] = at[self.cols.index(name), ix] * ((vecs * inv) @ vecs.T @ et[ix])
        return out


def contrast(parts: list[tuple[Fit, str, float]], groups: np.ndarray, xy: np.ndarray, rng,
             null: float = 0.0) -> dict:
    """Inference for c = Σ weight · coef(fit, name), fits on the same units. Returns the estimate and SEs/p-values
    for H0: c = null by every method; one-sided p-values in both directions."""
    est = sum(wt * f.coef(nm) for f, nm, wt in parts)
    psi = sum(wt * f.row(nm) * f.e for f, nm, wt in parts)
    n = len(psi)
    k = max(f.k for f, _, _ in parts)
    se = {"hc1": np.sqrt(n / (n - k) * np.sum(psi ** 2))}
    gs = np.unique(groups)
    G = len(gs)
    sums = pd.Series(psi).groupby(groups).sum().values
    se["cr1"] = np.sqrt(G / (G - 1) * np.sum(sums ** 2))
    psi2 = sum(wt * f.cr2_psi(nm, groups) for f, nm, wt in parts)
    se["cr2"] = np.sqrt(np.sum(pd.Series(psi2).groupby(groups).sum().values ** 2))
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    for cut in [1000, 1500, 3000]:
        kern = np.clip(1 - d / cut, 0, None)
        se[f"conley_{cut // 100 / 10:g}km"] = np.sqrt(max(psi @ kern @ psi, 0) * n / (n - k))
    # wild cluster bootstrap-t, unrestricted: y* = Xb + e * v_g for every fit (same v), δ* - δ = Σ ψ_i v_g(i)
    gi = np.searchsorted(gs, groups)
    v = webb(rng, G, B)[:, gi]  # B x n
    num = (v * psi).sum(axis=1)
    # bootstrap SE (CR1) for each draw: residuals of refits are M(e*v); build the draw's ψ*
    psi_star = np.zeros((B, n))
    for f, nm, wt in parts:
        ev = f.e[None, :] * v
        e_star = ev - (ev @ f.A.T) @ f.X.T
        psi_star += wt * f.row(nm)[None, :] * e_star
    sums_star = psi_star @ np.eye(G)[gi]
    se_star = np.sqrt(G / (G - 1) * (sums_star ** 2).sum(axis=1))
    t_star = num / se_star
    t_obs = (est - null) / se["cr1"]
    se["wild_equiv"] = float(np.std(num))
    out = {"estimate": round(float(est), 4), "null": null,
           "se": {k: round(float(v_), 4) for k, v_ in se.items()}, "G": int(G), "n": int(n)}
    p = {}
    for kk in ["hc1", "conley_1.5km"]:
        z = (est - null) / se[kk]
        p[kk] = {"less": float(norm.cdf(z)), "greater": float(norm.sf(z))}
    z = (est - null) / se["cr2"]
    p["cr2"] = {"less": float(tdist.cdf(z, G - 1)), "greater": float(tdist.sf(z, G - 1))}
    p["wild"] = {"less": float((1 + np.sum(t_star <= t_obs)) / (B + 1)),
                 "greater": float((1 + np.sum(t_star >= t_obs)) / (B + 1))}
    out["p"] = {k: {s: round(x, 4) for s, x in d_.items()} for k, d_ in p.items()}
    out["_psi"] = psi
    return out


def ci(c: dict, method: str = "wild_equiv", level: float = 0.95) -> list[float]:
    z = norm.ppf(0.5 + level / 2)
    return [round(c["estimate"] - z * c["se"][method], 4), round(c["estimate"] + z * c["se"][method], 4)]


def clean(c: dict) -> dict:
    return {k: v for k, v in c.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------------------------------- hypotheses

def setup(u: pd.DataFrame, party: str, x: pd.DataFrame, weight: str = "V"):
    ok = x.notna().all(axis=1) & (u[weight] > 0) & (u.flats > 0)
    y = 100 * u.loc[ok, party] / u.loc[ok, "V"]
    return y, x.loc[ok], u.loc[ok, weight], u.loc[ok, "district"].values, u.loc[ok, ["cx", "cy"]].values


def h1(u: pd.DataFrame, party: str, rng, x: pd.DataFrame | None = None, weight: str = "V",
       with_age: bool = False) -> dict:
    """β0 (no composition) and β1 (education + citizenship) on the identical sample; δ = β1 - 0.5 β0; Gelbach."""
    x = design(u) if x is None else x
    y, xx, w, g, xy = setup(u, party, x[BASE + COMP + AGE], weight)
    comp = [k for k in COMP + (AGE if with_age else []) if xx[k].std() > 0]  # "foreign" is 0 without foreigners
    f0, f1 = Fit(y, xx[BASE], w), Fit(y, xx[BASE + comp], w)
    b0, b1 = f0.coef("panel"), f1.coef("panel")
    sgn = 1.0 if b0 >= 0 else -1.0  # H1b′: θ on the absolute value
    dl = contrast([(f1, "panel", sgn), (f0, "panel", -0.5 * sgn)], g, xy, rng)
    b1c = contrast([(f1, "panel", 1.0)], g, xy, rng)
    # Gelbach (2016): β0 - β1 = Σ_k π_k γ_k, π_k = panel coefficient of Z_k on the base regressors
    gel = {}
    for grp, ks in [("education", EDU), ("citizenship", ["foreign"])] + ([("age", AGE)] if with_age else []):
        ks = [k for k in ks if k in comp]
        gel[grp] = round(float(sum(Fit(xx[k], xx[BASE], w).coef("panel") * f1.coef(k) for k in ks)), 4)
    out = {
        "n": f0.n, "beta0_per10pp": round(10 * b0, 3), "beta1_per10pp": round(10 * b1, 3),
        "theta": round(1 - b1 / b0, 3), "delta": clean(dl), "beta1": clean(b1c),
        "beta1_ci95_per10pp": [round(10 * v, 3) for v in ci(b1c)],
        "gelbach_per10pp": {k: round(10 * v, 3) for k, v in gel.items()},
        "gelbach_check": round(10 * (b0 - b1 - sum(gel.values())), 5),
        "coefs_full": {k: round(f1.coef(k), 4) for k in BASE + comp},
        "tertiary": clean(contrast([(f1, "tertiary", 1.0)], g, xy, rng)),
        "metro": clean(contrast([(f1, "log2_metro", 1.0)], g, xy, rng)),
        "r2_base": round(r2(f0), 3), "r2_full": round(r2(f1), 3),
    }
    # decision rule, wild bootstrap p-values (one-sided)
    p_comp, p_place = dl["p"]["wild"]["less"], dl["p"]["wild"]["greater"]
    place_pos = b1c["p"]["wild"]["greater" if sgn > 0 else "less"] < 0.05
    out["p_confirmatory"] = round(p_comp, 4)
    out["outcome_unadjusted"] = ("composition" if p_comp < 0.05 else
                                 "place beyond composition" if p_place < 0.05 and place_pos else "indeterminate")
    return out


def r2(f: Fit) -> float:
    ybar = np.average(f.y, weights=f.w)
    return 1 - np.sum(f.w * f.e ** 2) / np.sum(f.w * (f.y - ybar) ** 2)


def h2(u: pd.DataFrame, rng, margin: float = 0.25, x: pd.DataFrame | None = None, weight: str = "V") -> dict:
    """TOST on log2 metro in the full ANO model, with the largest SE of HC1, Conley 1.5 km and wild bootstrap."""
    x = design(u) if x is None else x
    y, xx, w, g, xy = setup(u, "ANO", x[BASE + COMP], weight)
    xx = xx[[k for k in xx.columns if xx[k].std() > 0]]
    f = Fit(y, xx, w)
    c = contrast([(f, "log2_metro", 1.0)], g, xy, rng)
    se = max(c["se"]["hc1"], c["se"]["conley_1.5km"], c["se"]["wild_equiv"])
    p_lo = norm.sf((c["estimate"] + margin) / se)  # H0: γ <= -margin
    p_hi = norm.cdf((c["estimate"] - margin) / se)  # H0: γ >= +margin
    return {**clean(c), "se_used": round(float(se), 4), "margin": margin, "p_tost": round(float(max(p_lo, p_hi)), 4),
            "ci90_used": [round(c["estimate"] - 1.645 * se, 4), round(c["estimate"] + 1.645 * se, 4)],
            "outcome": "supported (equivalent to zero)" if max(p_lo, p_hi) < 0.05 else "not supported: inconclusive"}


def matched(d: pd.DataFrame, res: dict, b: pd.DataFrame, tol: float = 0.10) -> pd.DataFrame:
    """Precincts whose (district, number) exists in all three elections and whose register change between
    consecutive elections is within ±tol of the change predicted from new flats inside the current polygon."""
    m = d[["kod", "momc", "cislo", "flats", "panel_flats", "house_flats", "log2_centre", "log2_metro", "cell",
           "cx", "cy"]].copy()
    for yr, r in res.items():
        m = m.merge(r.rename(columns={c: f"{c}_{yr}" for c in r.columns if c not in ("momc", "cislo")}),
                    on=["momc", "cislo"], how="left")
    have = m[[f"R_{y}" for y in res]].notna().all(axis=1)
    done = pd.to_datetime(b.dokonceni, unit="ms", errors="coerce")
    ok = pd.Series(True, index=m.index)
    for y0, y1 in [(2017, 2021), (2021, 2025)]:
        t0, t1 = pd.Timestamp(ELECTION_DAY[y0]), pd.Timestamp(ELECTION_DAY[y1])
        pre = b[done.isna() | (done <= t0)].groupby("pi").pocetbytu.sum()
        new = b[(done > t0) & (done <= t1)].groupby("pi").pocetbytu.sum()
        pre, new = pre.reindex(m.index, fill_value=0), new.reindex(m.index, fill_value=0)
        city = m.loc[have, f"R_{y1}"].sum() / m.loc[have, f"R_{y0}"].sum()
        pred = (pre + new) / pre.where(pre > 0) * city
        obs = m[f"R_{y1}"] / m[f"R_{y0}"]
        m[f"dev_{y0}_{y1}"] = obs / pred - 1
        ok &= (obs / pred - 1).abs() <= tol
    m["have_all"] = have
    m["matched"] = have & ok.fillna(False)
    return m


def h3(m: pd.DataFrame, rng, weights: pd.Series | None = None) -> dict:
    """Pooled 2017 + 2025 ANO share on panel × year with year-specific controls; one-sided test of the panel ×
    2025 interaction > 0; clusters: city districts."""
    s = m[m.matched & (m.flats > 0)].copy()
    rows = []
    for yr in [2017, 2025]:
        t = pd.DataFrame({"y": 100 * s[f"ANO_{yr}"] / s[f"V_{yr}"], "w": s[f"V_{yr}"], "yr": int(yr == 2025),
                          "panel": 100 * s.panel_flats / s.flats, "house": 100 * s.house_flats / s.flats,
                          "log2_centre": s.log2_centre, "log2_metro": s.log2_metro, "g": s.momc,
                          "cx": s.cx, "cy": s.cy, "kod": s.kod})
        rows.append(t)
    p = pd.concat(rows, ignore_index=True)
    if weights is not None:
        p["w"] = p.w * p.kod.map(weights).values
    x = pd.DataFrame({"yr": p.yr})
    for k in BASE:
        x[k] = p[k]
        x[f"{k}_x"] = p[k] * p.yr
    f = Fit(p.y, x, p.w)
    c = contrast([(f, "panel_x", 1.0)], p.g.values, p[["cx", "cy"]].values, rng)
    by_year = {}
    for yr in [2017, 2021, 2025]:
        t = pd.DataFrame({"panel": 100 * s.panel_flats / s.flats, "house": 100 * s.house_flats / s.flats,
                          "log2_centre": s.log2_centre, "log2_metro": s.log2_metro})
        ff = Fit(100 * s[f"ANO_{yr}"] / s[f"V_{yr}"], t, s[f"V_{yr}"])
        by_year[yr] = round(10 * ff.coef("panel"), 3)
    return {**clean(c), "interaction_per10pp": round(10 * c["estimate"], 3), "n_precincts": len(s),
            "panel_slope_per10pp_by_year": by_year, "p_confirmatory": c["p"]["wild"]["greater"]}


def h4(u: pd.DataFrame, rng) -> dict:
    """H4a: centre gradient of resident vs registered turnout (stacked); H4b: log E on log R and log Â."""
    x = design(u)
    ok = x[BASE + COMP].notna().all(axis=1) & (u.A_hat > 0) & (u.R > 0) & (u.E > 0)
    uu, xx = u[ok], x.loc[ok, BASE + COMP]
    g, xy = uu.district.values, uu[["cx", "cy"]].values
    f_reg = Fit(100 * uu.E / uu.R, xx, uu.R)
    f_res = Fit(100 * uu.E / uu.A_hat, xx, uu.R)
    # |g_reg| - |g_res| > 0, signs taken from the estimates (registration §2, H4a)
    s_reg, s_res = np.sign(f_reg.coef("log2_centre")), np.sign(f_res.coef("log2_centre"))
    c4a = contrast([(f_reg, "log2_centre", s_reg), (f_res, "log2_centre", -s_res)], g, xy, rng)
    lx = xx.assign(log_R=np.log(uu.R), log_A=np.log(uu.A_hat))
    f4b = Fit(np.log(uu.E), lx, uu.R)
    c4b = contrast([(f4b, "log_R", 1.0)], g, xy, rng, null=1.0)
    ratio = (uu.R / uu.A_hat)
    return {
        "n": int(ok.sum()), "register_ratio_citywide": round(float(uu.R.sum() / uu.A_hat.sum()), 3),
        "register_ratio_quantiles": {q: round(float(ratio.quantile(q)), 3) for q in [0.05, 0.25, 0.5, 0.75, 0.95]},
        "gradient_registered_pp": round(f_reg.coef("log2_centre"), 3),
        "gradient_resident_pp": round(f_res.coef("log2_centre"), 3),
        "h4a": clean(c4a), "h4a_p": c4a["p"]["wild"]["greater"],
        "h4b": clean(c4b), "h4b_b": round(c4b["estimate"], 3), "h4b_c": round(f4b.coef("log_A"), 3),
        "h4b_p": c4b["p"]["wild"]["less"],
        "descriptive_E_R_on_R_A": round(Fit(uu.E / uu.R, pd.DataFrame({"ra": ratio}), uu.R).coef("ra"), 4),
    }


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m, out, stop = len(items), {}, False
    for i, (k, p) in enumerate(items):
        thr = 0.05 / (m - i)
        rej = (not stop) and p <= thr
        stop = stop or not rej
        out[k] = {"p": round(p, 4), "threshold": round(thr, 4), "reject": bool(rej)}
    return out


# --------------------------------------------------------------------------------------------------------- main

def main() -> None:
    rng = np.random.default_rng(SEED)
    d = frame()
    geo = pd.read_parquet(RAW / "design.parquet", columns=["geom_wkb"])
    from shapely import wkb
    cent = [wkb.loads(g).centroid for g in geo.geom_wkb]
    d["cx"], d["cy"] = [p.x for p in cent], [p.y for p in cent]
    res = {yr: results(yr) for yr in FILES}
    joined = {yr: d.merge(r, on=["momc", "cislo"], how="left", indicator=True) for yr, r in res.items()}
    n_acc = {yr: {"results_rows": len(r), "joined": int((j._merge == "both").sum()),
                  "results_without_polygon": int(len(r) - (j._merge == "both").sum())}
             for (yr, r), j in zip(res.items(), joined.values())}
    d25 = joined[2025].drop(columns="_merge")
    d25 = d25[d25.V.notna()]
    u = to_clusters(d25)
    out = {"n_accounting": n_acc, "clusters": len(u)}
    out["H1_ANO"] = h1(u, "ANO", rng)
    out["H1_SPOLU"] = h1(u, "SPOLU", rng)
    out["H1_ANO_with_age"] = h1(u, "ANO", rng, with_age=True)
    out["H2"] = h2(u, rng)
    b = pd.read_pickle(RAW / "buildings_5514.pkl")
    from shapely import STRtree
    from shapely.geometry import Point
    polys = [wkb.loads(g) for g in geo.geom_wkb]
    hit = STRtree(polys).query([Point(x, y) for x, y in zip(b.x, b.y)], predicate="within")
    b = b.iloc[hit[0]].assign(pi=hit[1])
    m = matched(d, res, b)
    out["matching"] = {"have_all_three": int(m.have_all.sum()), "matched_10pct": int(m.matched.sum())}
    out["H3"] = h3(m, rng)
    sens = {}
    for tol in [0.05, 0.20]:
        mt = matched(d, res, b, tol)
        r = h3(mt, rng)
        sens[f"tol_{int(tol * 100)}pct"] = {"n": r["n_precincts"], "interaction_per10pp": r["interaction_per10pp"],
                                            "p": r["p_confirmatory"], "by_year": r["panel_slope_per10pp_by_year"]}
    # inverse-probability weights for being matched, among precincts present in all three elections
    a = m[m.have_all & (m.flats > 0)].copy()
    a["panel"], a["house"] = 100 * a.panel_flats / a.flats, 100 * a.house_flats / a.flats
    lg = sm.Logit(a.matched.astype(float), sm.add_constant(a[["panel", "log2_centre", "house"]])).fit(disp=0)
    ipw = pd.Series(1 / lg.predict(sm.add_constant(a[["panel", "log2_centre", "house"]])).values, index=a.kod)
    r = h3(m, rng, weights=ipw)
    sens["ipw"] = {"n": r["n_precincts"], "interaction_per10pp": r["interaction_per10pp"], "p": r["p_confirmatory"]}
    cmp = a.groupby("matched").agg(n=("kod", "size"), panel=("panel", "mean"), log2_centre=("log2_centre", "mean"),
                                   ano_2025=("ANO_2025", "sum"), v_2025=("V_2025", "sum"))
    cmp["ano_2025_share"] = 100 * cmp.ano_2025 / cmp.v_2025
    sens["matched_vs_not"] = {str(k): {c: round(float(v), 3) for c, v in r_.items()}
                              for k, r_ in cmp[["n", "panel", "log2_centre", "ano_2025_share"]].iterrows()}
    out["H3_sensitivity"] = sens
    flagged = d25.registration_office | d25.institution
    u4 = to_clusters(d25[~flagged])
    out["H4"] = h4(u4, rng)
    out["H4_with_flagged"] = h4(u, rng)
    ps = {"H1b_ANO": out["H1_ANO"]["p_confirmatory"], "H1b_SPOLU": out["H1_SPOLU"]["p_confirmatory"],
          "H2": out["H2"]["p_tost"], "H3": out["H3"]["p_confirmatory"], "H4a": out["H4"]["h4a_p"],
          "H4b": out["H4"]["h4b_p"]}
    out["holm"] = holm(ps)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n")
    print(json.dumps({k: out[k] for k in ["n_accounting", "clusters", "matching", "holm"]}, indent=1))


if __name__ == "__main__":
    main()
