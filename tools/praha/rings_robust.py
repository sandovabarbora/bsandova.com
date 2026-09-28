"""Part 2 extended, §6: robustness, placebo and specification checks, the precinct-level models, the spatial
diagnostics, and the 2021 replication (H5). None of these is in the confirmatory family.

Reads the design frame (rings_data.py) and reuses the estimators of rings_extended.py; writes
assets/praha/rings_robust.json.

Usage:
    uv run --with pandas --with numpy --with scipy --with statsmodels --with pyarrow --with shapely \
        python tools/praha/rings_robust.py
"""

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from shapely import STRtree, wkb
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from rings_extended import (  # noqa: E402
    BASE, COMP, RAW, ROOT, SEED, Fit, contrast, design, frame, h1, h2, results, to_clusters,
)

OUT = ROOT / "assets" / "praha" / "rings_robust.json"
COUNTS = ["000", "011", "013", "050", "021", "022", "023", "024", "025", "051", "053", "054"]


def precincts_2025() -> pd.DataFrame:
    d = frame()
    geo = pd.read_parquet(RAW / "design.parquet", columns=["geom_wkb"])
    polys = [wkb.loads(g) for g in geo.geom_wkb]
    d["cx"], d["cy"] = [p.centroid.x for p in polys], [p.centroid.y for p in polys]
    d["poly"] = polys
    d = d.merge(results(2025), on=["momc", "cislo"], how="left")
    return d[d.V.notna()].reset_index(drop=True)


def summary(u: pd.DataFrame, rng, x: pd.DataFrame | None = None, weight: str = "V") -> dict:
    a, s, m = h1(u, "ANO", rng, x, weight), h1(u, "SPOLU", rng, x, weight), h2(u, rng, x=x, weight=weight)
    return {"n": a["n"],
            "ANO": {"theta": a["theta"], "beta1": a["beta1_per10pp"], "ci": a["beta1_ci95_per10pp"],
                    "outcome": a["outcome_unadjusted"], "p_comp": a["p_confirmatory"]},
            "SPOLU": {"theta": s["theta"], "beta1": s["beta1_per10pp"], "ci": s["beta1_ci95_per10pp"],
                      "outcome": s["outcome_unadjusted"], "p_comp": s["p_confirmatory"]},
            "metro": {"gamma": round(m["estimate"], 3), "ci90": m["ci90_used"], "outcome": m["outcome"]}}


def with_area(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    for k in COUNTS:
        d[k] = d[f"area_{k}"]
    return d


def point(u: pd.DataFrame, x: pd.DataFrame, party: str = "ANO") -> tuple[float, float, float]:
    """β0, β1 per 10 pp and the metro coefficient, point estimates only."""
    ok = x[BASE + COMP].notna().all(axis=1) & (u.V > 0) & (u.flats > 0)
    y, xx, w = 100 * u.loc[ok, party] / u.loc[ok, "V"], x.loc[ok], u.loc[ok, "V"]
    comp = [k for k in COMP if xx[k].std() > 0]
    f0, f1 = Fit(y, xx[BASE], w), Fit(y, xx[BASE + comp], w)
    return 10 * f0.coef("panel"), 10 * f1.coef("panel"), f1.coef("log2_metro")


def frac_logit(u: pd.DataFrame, party: str) -> dict:
    """Papke-Wooldridge fractional logit (quasi-binomial GLM, frequency = valid votes), average marginal effects
    of panel share in pp per 10 pp."""
    x = design(u)
    ok = x[BASE + COMP].notna().all(axis=1) & (u.V > 0)
    y, w = u.loc[ok, party] / u.loc[ok, "V"], u.loc[ok, "V"]
    out = {}
    for name, cols in [("beta0", BASE), ("beta1", BASE + COMP)]:
        X = sm.add_constant(x.loc[ok, cols])
        f = sm.GLM(y, X, family=sm.families.Binomial(), var_weights=w).fit()
        p = f.predict(X)
        out[name] = round(float(1000 * np.average(p * (1 - p), weights=w) * f.params["panel"]), 3)
    out["theta"] = round(1 - out["beta1"] / out["beta0"], 3)
    return out


def lodo(u: pd.DataFrame) -> dict:
    x = design(u)
    b0, b1, g = point(u, x)
    rows = []
    for dist in u.district.unique():
        k = u.district != dist
        c0, c1, cg = point(u[k], x[k])
        rows.append((dist, c1 - b1, (1 - c1 / c0) - (1 - b1 / b0), cg - g))
    r = pd.DataFrame(rows, columns=["district", "d_beta1", "d_theta", "d_metro"])
    return {k: {"max_abs": round(float(r[k].abs().max()), 3), "district": int(r.loc[r[k].abs().idxmax(), "district"])}
            for k in ["d_beta1", "d_theta", "d_metro"]}


def shuffle(u: pd.DataFrame, rng, draws: int = 1000) -> dict:
    """Panel share permuted within districts; the attenuation β0 - β1 (pp per 10 pp) under the permutation."""
    x = design(u)
    b0, b1, _ = point(u, x)
    stats = []
    for _ in range(draws):
        xs = x.copy()
        xs["panel"] = x.groupby(u.district).panel.transform(lambda s: s.sample(frac=1, random_state=rng).values)
        c0, c1, _ = point(u, xs)
        stats.append(c0 - c1)
    s = np.array(stats)
    return {"observed": round(b0 - b1, 3), "null_mean": round(float(s.mean()), 3),
            "null_q025_q975": [round(float(np.quantile(s, 0.025)), 3), round(float(np.quantile(s, 0.975)), 3)],
            "p_two_sided": round(float((1 + np.sum(np.abs(s - s.mean()) >= abs(b0 - b1 - s.mean()))) / (draws + 1)), 4)}


def spec_curve(d: pd.DataFrame, rng) -> dict:
    rows = []
    for weighted, alloc, panel, sample, se in itertools.product(
            [True, False], ["flats", "area"], ["4+41", "4"], ["all", ">=300", "homogeneous"], ["wild", "conley"]):
        dd = with_area(d) if alloc == "area" else d
        if sample == ">=300":
            dd = dd[dd.R >= 300]
        u = to_clusters(dd).assign(one=1.0)
        x = design(u, "panel_flats" if panel == "4+41" else "panel4_flats")
        if sample == "homogeneous":
            k = (x.panel < 20) | (x.panel > 80)
            u, x = u[k], x[k]
        wt = "V" if weighted else "one"
        a, s, m = h1(u, "ANO", rng, x, wt), h1(u, "SPOLU", rng, x, wt), h2(u, rng, x=x, weight=wt)
        key = "wild" if se == "wild" else "conley_1.5km"
        z = 1.6449

        def outcome(h):
            dl = h["delta"]
            t = dl["estimate"] / dl["se"]["wild_equiv" if se == "wild" else key]
            b1 = h["beta1"]
            tb = b1["estimate"] / b1["se"]["wild_equiv" if se == "wild" else key]
            pos = np.sign(h["beta0_per10pp"]) * tb > z
            return "composition" if t < -z else "place beyond composition" if t > z and pos else "indeterminate"

        gse = max(m["se"]["hc1"], m["se"][key if se == "conley" else "wild_equiv"])
        eq = (m["estimate"] - 1.6449 * gse > -0.25) and (m["estimate"] + 1.6449 * gse < 0.25)
        rows.append({"weighted": weighted, "alloc": alloc, "panel": panel, "sample": sample, "se": se,
                     "n": a["n"], "ANO_theta": a["theta"], "ANO_beta1": a["beta1_per10pp"], "ANO": outcome(a),
                     "SPOLU_theta": s["theta"], "SPOLU": outcome(s), "metro": round(m["estimate"], 3),
                     "metro_equivalent": bool(eq)})
    r = pd.DataFrame(rows)
    return {"specs": len(r),
            "share": {"ANO": r.ANO.value_counts(normalize=True).round(3).to_dict(),
                      "SPOLU": r.SPOLU.value_counts(normalize=True).round(3).to_dict(),
                      "metro_equivalent": round(float(r.metro_equivalent.mean()), 3)},
            "ANO_theta_range": [float(r.ANO_theta.min()), float(r.ANO_theta.max())],
            "ANO_beta1_range": [float(r.ANO_beta1.min()), float(r.ANO_beta1.max())],
            "rows": r.to_dict(orient="records")}


def spatial(d: pd.DataFrame, u: pd.DataFrame, rng) -> dict:
    """Moran's I of the full ANO model's cluster residuals (queen contiguity of cluster polygons, 4 nearest
    neighbours for islands, 999 permutations), and an unweighted spatial error model by ML with the Pace-LeSage
    Hausman test."""
    x = design(u)
    ok = x[BASE + COMP].notna().all(axis=1) & (u.V > 0)
    uu, xx = u[ok], x.loc[ok, BASE + COMP]
    polys = d.groupby("cell").poly.apply(lambda p: unary_union(list(p)).buffer(1))
    polys = polys.loc[uu.index]
    n = len(uu)
    tree = STRtree(list(polys))
    W = np.zeros((n, n))
    for i, p in enumerate(polys):
        for j in tree.query(p, predicate="intersects"):
            if j != i:
                W[i, j] = 1
    xy = uu[["cx", "cy"]].values
    for i in np.where(W.sum(axis=1) == 0)[0]:
        dd = np.hypot(*(xy - xy[i]).T)
        W[i, np.argsort(dd)[1:5]] = 1
    W = W / W.sum(axis=1, keepdims=True)
    y = 100 * uu.ANO / uu.V
    f = Fit(y, xx, uu.V)
    e = f.e - np.average(f.e, weights=f.w)

    def moran(z):
        z = z - z.mean()
        return n / W.sum() * (z @ W @ z) / (z @ z)

    i_obs = moran(e)
    perms = np.array([moran(rng.permutation(e)) for _ in range(999)])
    # spatial error model, unweighted, concentrated ML over λ on a grid then refined
    X = np.c_[np.ones(n), xx.values]
    Y = y.values
    ev = np.linalg.eigvals(W).real

    def negll(lam):
        Bm = np.eye(n) - lam * W
        Xs, Ys = Bm @ X, Bm @ Y
        b = np.linalg.lstsq(Xs, Ys, rcond=None)[0]
        r = Ys - Xs @ b
        s2 = r @ r / n
        return n / 2 * np.log(s2) - np.sum(np.log(np.abs(1 - lam * ev))), b, s2

    grid = np.linspace(-0.9, 0.95, 186)
    lam = grid[np.argmin([negll(v)[0] for v in grid])]
    from scipy.optimize import minimize_scalar
    lam = minimize_scalar(lambda v: negll(v)[0], bounds=(lam - 0.02, lam + 0.02), method="bounded").x
    _, b_sem, s2 = negll(lam)
    Bm = np.eye(n) - lam * W
    Xs = Bm @ X
    v_sem = s2 * np.linalg.inv(Xs.T @ Xs)
    b_ols = np.linalg.lstsq(X, Y, rcond=None)[0]
    xtx = np.linalg.inv(X.T @ X)
    omega = s2 * np.linalg.inv(Bm.T @ Bm)
    v_ols = xtx @ X.T @ omega @ X @ xtx
    dlt = (b_ols - b_sem)[1:]
    dv = (v_ols - v_sem)[1:, 1:]
    haus = float(dlt @ np.linalg.pinv(dv) @ dlt)
    from scipy.stats import chi2
    cols = ["const", *xx.columns]
    return {"moran_I": round(float(i_obs), 3), "moran_p": round(float((1 + np.sum(perms >= i_obs)) / 1000), 4),
            "sem_lambda": round(float(lam), 3),
            "sem_panel_per10pp": round(float(10 * b_sem[cols.index("panel")]), 3),
            "ols_unweighted_panel_per10pp": round(float(10 * b_ols[cols.index("panel")]), 3),
            "sem_metro": round(float(b_sem[cols.index("log2_metro")]), 3),
            "sem_se_metro": round(float(np.sqrt(v_sem[cols.index("log2_metro"), cols.index("log2_metro")])), 3),
            "hausman": round(haus, 2), "hausman_df": len(dlt), "hausman_p": round(float(chi2.sf(haus, len(dlt))), 4)}


def precinct_level(d: pd.DataFrame, rng) -> dict:
    """The same models on precincts; SEs clustered by dominant grid cell (as 'district')."""
    p = d.assign(district=d.cell)
    p = p[p.flats > 0]
    out = {}
    for party in ["ANO", "SPOLU"]:
        h = h1(p, party, rng)
        out[party] = {"n": h["n"], "beta0": h["beta0_per10pp"], "beta1": h["beta1_per10pp"], "theta": h["theta"],
                      "ci": h["beta1_ci95_per10pp"], "outcome": h["outcome_unadjusted"]}
    m = h2(p, rng)
    out["metro"] = {"gamma": round(m["estimate"], 3), "ci90": m["ci90_used"], "se_used": m["se_used"],
                    "outcome": m["outcome"]}
    return out


def replication_2021(d25: pd.DataFrame, rng) -> dict:
    """H5: H1a, H1b, H1b′, H2 on 2021, precinct results joined to the current polygons by (district, number),
    summed to the same grid clusters."""
    base = d25.drop(columns=["R", "E", "V", "ANO", "SPOLU", "PirSTAN", "Pirates"])
    d21 = base.merge(results(2021), on=["momc", "cislo"], how="inner")
    u = to_clusters(d21)
    a, s, m = h1(u, "ANO", rng), h1(u, "SPOLU", rng), h2(u, rng)
    return {"precincts_joined": len(d21), "clusters": len(u),
            "H1a_tertiary": a["tertiary"]["estimate"], "H1a_p": a["tertiary"]["p"]["wild"]["less"],
            "ANO": {"beta0": a["beta0_per10pp"], "beta1": a["beta1_per10pp"], "theta": a["theta"],
                    "ci": a["beta1_ci95_per10pp"], "outcome": a["outcome_unadjusted"]},
            "SPOLU": {"beta0": s["beta0_per10pp"], "beta1": s["beta1_per10pp"], "theta": s["theta"],
                      "ci": s["beta1_ci95_per10pp"], "outcome": s["outcome_unadjusted"]},
            "metro": {"gamma": round(m["estimate"], 3), "ci90": m["ci90_used"], "outcome": m["outcome"]}}


def main() -> None:
    rng = np.random.default_rng(SEED + 1)
    d = precincts_2025()
    u = to_clusters(d).assign(one=1.0)
    x = design(u)
    zsj_bad = (d["000"] - d.zsj_residents).abs() > 0.25 * d.zsj_residents
    homog = (x.panel < 20) | (x.panel > 80)
    trim = ~((x.not_stated > 10) | (u["000"] < 50))
    out = {"main": summary(u, rng)}
    out["robustness"] = {
        "1_unweighted": summary(u, rng, weight="one"),
        "2_fractional_logit": {"ANO": frac_logit(u, "ANO"), "SPOLU": frac_logit(u, "SPOLU")},
        "3_without_redrawn": summary(to_clusters(d[~d.redrawn]), rng),
        "4_min_300_registered": summary(to_clusters(d[d.R >= 300]), rng),
        "5_leave_one_district_out": lodo(u),
        "6_panel_code_4": summary(u, rng, x=design(u, "panel4_flats")),
        "7_area_allocation": summary(to_clusters(with_area(d)), rng),
        "8_stated_and_populated": summary(u[trim], rng, x=x[trim]),
        "9_without_foreigners": summary(u, rng, x=design(u, without_foreign=True)),
        "10_without_zsj_flagged": summary(to_clusters(d[~zsj_bad]), rng),
        "11_homogeneous": summary(u[homog], rng, x=x[homog]),
        "12_placebo_line_d": "not run: official coordinates of the line D stations were not located in open data (IPR geoportal searched 2026-09-28)",
        "13_placebo_shuffle": shuffle(u, rng),
        "14_specification_curve": spec_curve(d, rng),
    }
    out["precinct_level"] = precinct_level(d, rng)
    out["spatial"] = spatial(d, u, rng)
    out["H5_2021"] = replication_2021(d, rng)
    out["n_zsj_flagged"] = int(zsj_bad.sum())
    out["n_homogeneous_clusters"] = int(homog.sum())
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n")
    brief = {k: v for k, v in out["robustness"].items() if k != "14_specification_curve"}
    brief["14"] = {k: v for k, v in out["robustness"]["14_specification_curve"].items() if k != "rows"}
    print(json.dumps({"main": out["main"], "robustness": brief, "precinct_level": out["precinct_level"],
                      "spatial": out["spatial"], "H5_2021": out["H5_2021"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
