"""Part 2 extended, §5a: the design-stage checks, run on the covariates alone before any 2017, 2021 or new 2025
outcome enters the model frame (docs/research/prague-rings-design.md).

Reports VIFs and the condition number of the grid-cluster design, and minimum detectable effects at 80 % power.
The only outcome information used is the residual variance of Part 2's published 2025 precinct model, as the
design allows, taken as an upper bound for the cluster-level residual variance.

Usage:
    uv run --with pandas --with numpy --with statsmodels --with scipy --with pyarrow python tools/praha/rings_power.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from statsmodels.stats.outliers_influence import variance_inflation_factor

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha2x"
OUT = ROOT / "docs" / "research" / "prague-rings-power.json"
Z = 1.6449  # one-sided 5 %
Z80 = 0.8416


def shares(t: pd.DataFrame) -> pd.DataFrame:
    stated = t[["021", "022", "023", "024"]].sum(axis=1)
    return pd.DataFrame({
        "panel": 100 * t.panel_flats / t.flats, "house": 100 * t.house_flats / t.flats,
        "log2_centre": t.log2_centre, "log2_metro": t.log2_metro,
        "tertiary": 100 * t["024"] / stated, "basic": 100 * t["021"] / stated,
        "vocational": 100 * t["022"] / stated,
        "not_stated": 100 * t["025"] / (stated + t["025"]),
        "foreign": 100 * (t["051"] + t["053"] + t["054"]) / t["000"],
    }, index=t.index)


def clusters(d: pd.DataFrame) -> pd.DataFrame:
    d = d.assign(log2_centre=np.log2(d.centre_m / 1000), log2_metro=np.log2(d.metro_m / 1000))
    w = d.flats.fillna(0)
    counts = ["000", "021", "022", "023", "024", "025", "051", "053", "054", "flats", "panel_flats", "house_flats"]
    g = d.groupby("cell")
    c = g[counts].sum()
    for k in ["log2_centre", "log2_metro"]:
        c[k] = (d[k] * w).groupby(d.cell).sum() / w.groupby(d.cell).sum()
    c["district"] = d.assign(w=w).sort_values("w").groupby("cell").momc.last()
    c["precincts"] = g.size()
    return c[c.flats > 0]


def vifs(x: pd.DataFrame) -> dict:
    x = sm.add_constant(x.dropna())
    return {k: round(float(variance_inflation_factor(x.values, i)), 2) for i, k in enumerate(x.columns) if k != "const"}


def part2_residual_sd() -> dict:
    """Residual SD (pp) of Part 2's precinct models: ANO and SPOLU shares, and turnout."""
    import io
    import zipfile

    z = zipfile.ZipFile(ROOT / "tools" / "data" / "praha2" / "PS2025data_csv.zip")
    t = pd.read_csv(io.BytesIO(z.read("csv/pst4.csv")), sep=";", encoding="cp1250")
    t = t[t.OKRES == 1100].set_index(["OBEC", "OKRSEK"])
    p = pd.read_csv(ROOT / "tools" / "data" / "praha2" / "precincts.csv").set_index(["OBEC", "OKRSEK"])
    p = p.join(t[["VOL_SEZNAM", "VYD_OBALKY"]])
    x = sm.add_constant(pd.DataFrame({"panel": 100 * p.panel_share, "c": np.log2(p.centre_m / 1000),
                                      "m": np.log2(p.metro_m / 1000)}))
    out = {}
    for name, y, w in [("ANO", 100 * p.ANO / p.PL_HL_CELK, p.PL_HL_CELK),
                       ("SPOLU", 100 * p.SPOLU / p.PL_HL_CELK, p.PL_HL_CELK),
                       ("turnout", 100 * p.VYD_OBALKY / p.VOL_SEZNAM, p.VOL_SEZNAM)]:
        f = sm.WLS(y, x, weights=w).fit()
        out[name] = float(np.sqrt(np.sum(w * f.resid ** 2) / np.sum(w)))
    return out


def analytic_se(x: pd.DataFrame, e_sd: float, w: pd.Series, col: str) -> float:
    """SE of one WLS coefficient when cluster residuals are iid N(0, e_sd²): the sandwich
    e_sd² (X'WX)^-1 X'W²X (X'WX)^-1, a lower bound for the confirmatory SEs."""
    X = sm.add_constant(x).values
    W = w.values
    A = np.linalg.inv(X.T @ (W[:, None] * X))
    B = X.T @ ((W ** 2)[:, None] * X)
    V = e_sd ** 2 * A @ B @ A
    return float(np.sqrt(V[list(sm.add_constant(x).columns).index(col), list(sm.add_constant(x).columns).index(col)]))


def h1b_power(c: pd.DataFrame, s: pd.DataFrame, e_sd: float, beta0: float, reps: int = 2000) -> dict:
    """Simulated power of the one-sided δ test (H1b) against θ, with the unadjusted panel slope held at Part 2's
    value. Composition acts through tertiary share only; residuals iid N(0, e_sd²) per cluster, which is optimistic
    about spatial dependence and pessimistic about aggregation (a cluster averages several precincts)."""
    rng = np.random.default_rng(20260928)
    base = ["panel", "house", "log2_centre", "log2_metro"]
    comp = ["tertiary", "vocational", "basic", "not_stated", "foreign"]
    x0, x1 = sm.add_constant(s[base]), sm.add_constant(s[base + comp])
    w = c.loc[s.index, "000"].values
    pi = sm.WLS(s.tertiary, x0, weights=w).fit().params["panel"]
    out = {}
    for theta in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        b1 = (1 - theta) * beta0
        lam = (beta0 - b1) / pi if pi != 0 else 0
        mu = b1 * s.panel + lam * s.tertiary
        rej_comp = rej_place = 0
        for _ in range(reps):
            y = mu + rng.normal(0, e_sd, len(s))
            f0, f1 = sm.WLS(y, x0, weights=w).fit(), sm.WLS(y, x1, weights=w).fit()
            # δ = b1 - 0.5 b0, with its variance from the stacked residual bootstrap approximated by the delta
            # method on the two fits' HC1 covariances and their covariance through the shared residual
            e0, e1 = f0.resid.values, f1.resid.values
            a0 = np.linalg.pinv(x0.values.T @ (w[:, None] * x0.values)) @ (x0.values * w[:, None]).T
            a1 = np.linalg.pinv(x1.values.T @ (w[:, None] * x1.values)) @ (x1.values * w[:, None]).T
            g = a1[1] * e1 - 0.5 * a0[1] * e0
            se = np.sqrt(len(s) / (len(s) - x1.shape[1]) * np.sum(g ** 2))
            dlt = f1.params["panel"] - 0.5 * f0.params["panel"]
            rej_comp += dlt / se < -Z
            rej_place += dlt / se > Z
        out[f"{theta:.1f}"] = {"reject_toward_composition": round(rej_comp / reps, 3),
                               "reject_toward_place": round(rej_place / reps, 3)}
    return {"pi_tertiary_on_panel": round(float(pi), 3), "power_by_theta": out}


def main() -> None:
    d = pd.read_parquet(RAW / "design.parquet")
    c = clusters(d)
    s = shares(c).dropna()
    base = ["panel", "house", "log2_centre", "log2_metro"]
    comp = ["tertiary", "vocational", "basic", "not_stated", "foreign"]
    sd = part2_residual_sd()
    w = c.loc[s.index, "000"]
    x_full = s[base + comp]
    X = sm.add_constant(x_full).values
    Xs = X / np.linalg.norm(X, axis=0)
    se_metro = analytic_se(x_full, sd["ANO"], w / w.mean(), "log2_metro")
    se_centre_turn = analytic_se(x_full, sd["turnout"], w / w.mean(), "log2_centre")
    beta0 = 0.090  # Part 2: ANO +0.90 pp per 10 pp panel, i.e. 0.090 pp per pp
    report = {
        "clusters": len(s), "precincts_in_clusters": int(c.loc[s.index, "precincts"].sum()),
        "vif": vifs(x_full), "condition_number_scaled": round(float(np.linalg.cond(Xs)), 1),
        "residual_sd_part2_pp": {k: round(v, 2) for k, v in sd.items()},
        "h2": {"se_log2_metro_pp": round(se_metro, 3), "margin_pp": 0.25,
               "tost_power_at_true_zero": round(float(max(0.0, 2 * norm.cdf(0.25 / se_metro - Z) - 1)), 3),
               "mde_equivalence_margin_80pct": round(float((Z + norm.ppf(0.9)) * se_metro), 3)},
        "h4a_se_centre_gradient_turnout_pp": round(se_centre_turn, 3),
        "h1b": h1b_power(c, s, sd["ANO"], beta0),
        "notes": ["Residual SDs are precinct-level Part 2 values, an upper bound at the cluster level.",
                  "SEs assume independence across clusters; the confirmatory SEs (wild cluster bootstrap by "
                  "district, Conley) will be larger."],
    }
    report["h4a_mde_pp_per_doubling"] = round(float((Z + Z80) * np.sqrt(2) * se_centre_turn), 3)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
