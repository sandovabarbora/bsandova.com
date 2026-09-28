"""Part 4 extended, §6: robustness, placebo and specification checks, none of them in the confirmatory family.
Reuses the estimators of housing_extended.py; bootstraps in this script use B = 999 (the confirmatory tests use
9 999; deviation recorded 29 Sep 2026). Writes assets/praha/housing_extended_robust.json.

Usage (from a worktree, point DATA at the main checkout's gitignored tools/data):
    DATA=/path/to/bsandova.com/tools/data uv run --with pandas --with numpy --with scipy --with statsmodels \
        --with pyarrow --with openpyxl --with shapely --with pyproj --with pyfixest --with arch \
        python tools/praha/housing_robust.py
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pyproj import Transformer
from scipy.stats import norm
from shapely import wkb
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).parent))
from housing_extended import (  # noqa: E402
    CENTRAL, DATA, PRAGUE, RAW, ROOT, SEED, h1_rank, h1_regions, h2, h3_fit, h3_frame, ewc, h4, h4_frame, h5,
    h5_counts, h5_design,
)

warnings.filterwarnings("ignore")
OUT = ROOT / "assets" / "praha" / "housing_extended_robust.json"
BR = 999
MUSTEK = (14.4232, 50.0842)


def slim(d: dict, keys: list) -> dict:
    return {k: d[k] for k in keys if k in d}


def robust_h1() -> dict:
    reg = h1_regions()
    met = reg["metro"]
    prim = met[met.in_primary]
    out = {}
    keys = ["n", "score", "rank_from_lowest", "p", "observed_per_1000_year"]
    # c: reconstruction-concept countries dropped, Prague kept on the ČSÚ-rebuilt numerator
    c = prim[~prim.country.isin(["ES", "HR"]) & ((prim.country != "CZ") | (prim.index == "CZ001MC"))].copy()
    c.loc["CZ001MC", "num_eu"] = c.loc["CZ001MC", "num_csu"]
    out["c_reconstruction_countries_dropped"] = slim(h1_rank(c, "CZ001MC"), keys)
    out["d_bartik"] = slim(h1_rank(prim, "CZ001MC", growth="bartik"), keys)
    nog = met[met.dw2011.notna() & met.pop2011.notna() & met.g.notna() & met.num_eu.notna()
              & (met.unk <= 0.10)].drop(columns=["gdp"])
    out["e_without_gdp"] = slim(h1_rank(nog, "CZ001MC"), keys)
    out["f_2016_plus"] = slim(h1_rank(prim, "CZ001MC", numerator="num16", years="years16"), keys)
    out["g_unknown_5pc"] = slim(h1_rank(prim[prim.unk <= 0.05], "CZ001MC"), keys) \
        if "CZ001MC" in prim[prim.unk <= 0.05].index else {"run": False, "reason": "Prague above 5 %"}
    out["h_population_weighted"] = slim(h1_rank(prim, "CZ001MC", weighted=True), keys)
    out["i_contemporaneous_growth_2011_2021"] = slim(h1_rank(prim, "CZ001MC", growth="g21"), keys)
    return out


def robust_h2(rng) -> dict:
    keys = ["mu_prague", "mu_rest", "delta_months", "se_boot", "ci90", "p", "theta_prague", "theta_rest",
            "block_length"]
    runs = {
        "a_all_new_construction": dict(series=("permitted_family+permitted_multi",
                                               "completed_family+completed_multi")),
        "b_k96": dict(k=96),
        "c_block_12": dict(block=12.0), "c_block_24": dict(block=24.0),
        "d_exponential_kernel": dict(kind="exponential"),
        "e_without_covid_months": dict(exclude_covid=True),
        "f_prague_plus_stredocesky": dict(treated=(PRAGUE, CENTRAL)),
        "g_against_jihomoravsky": dict(reference=["CZ064"]),
    }
    out = {}
    for name, kw in runs.items():
        r = h2(rng, b=BR, **kw)
        out[name] = slim(r, keys)
        print("H2", name, out[name]["delta_months"], round(out[name]["p"], 4), flush=True)
    out["h_little_band"] = {"run": False, "reason": "dwellings under construction not published for the window"}
    return out


def robust_h3() -> dict:
    y, dlp = h3_frame()
    out = {}
    ya, dla = h3_frame(series="permitted_family+permitted_multi")
    fa = h3_fit(ya, dla)
    out["e_all_new_construction"] = ewc(fa["rel"], fa["psi_rel"], int(round(0.4 * fa["T"] ** (2 / 3))))
    excl = [q for q in y.q.unique() if q.year in (2020, 2021)]
    fg = h3_fit(y, dlp, exclude=excl)
    out["g_without_2020_2021"] = ewc(fg["rel"], fg["psi_rel"], int(round(0.4 * fg["T"] ** (2 / 3))))
    out["c_csu_realised_indices"] = {"run": False, "reason": "not downloaded before estimation"}
    out["f_annual"] = {"run": False, "reason": "9 annual observations cannot carry the registered lag structure"}
    return out


def city_units() -> dict:
    r = json.loads((RAW / "bdl" / "72305_L5.json").read_text())["results"]
    names = {x["id"]: x["name"] for x in r}
    want = ["Warszawa", "Kraków", "Wrocław", "Łódź", "Poznań"]
    return {w: [i for i, n in names.items() if "City with powiat status" in n and w in n][0] for w in want}


def robust_h4(rng) -> dict:
    keys = ["beta_market", "beta_nonmarket", "difference", "se_cr1", "p_cr1", "p_wcr", "p", "powiats",
            "effective_clusters"]
    out = {}
    runs = {
        "a_completions": dict(market=(748610,), nonmarket=(748616, 748619)),
        "b_with_cooperatives": dict(nonmarket=(747734, 747735, 747731)),
        "c_primary_market_price": dict(price=633682),
        "f_2012_2019": dict(years=(2012, 2019)),
    }
    for name, kw in runs.items():
        out[name] = slim(h4(rng, h4_frame(**kw), b=BR), keys)
        print("H4", name, out[name]["difference"], round(out[name]["p"], 4), flush=True)
    d = h4_frame()
    out["d_voivodeship_clusters"] = slim(h4(rng, d, cluster="voiv", b=9999), keys)
    cities = city_units()
    out["e_without_five_largest_cities"] = slim(h4(rng, d[~d.unit.isin(cities.values())], b=BR), keys)
    # g: negative binomial, α from Poisson residual moments, cluster-robust by powiat
    X = pd.concat([pd.get_dummies(d.fe, drop_first=True, dtype=float), pd.get_dummies(d.ye, drop_first=True,
                                                                                         dtype=float),
                   d[["g_lag", "g_nm"]]], axis=1)
    X = sm.add_constant(X)
    pois = sm.GLM(d.S, X, family=sm.families.Poisson(), offset=d.lnstock).fit()
    mu = pois.mu
    alpha = float(max((((d.S - mu) ** 2 - mu) / mu ** 2).mean(), 0.01))
    nb = sm.GLM(d.S, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=d.lnstock).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.unit)[0]})
    out["g_negative_binomial"] = {"difference": round(float(nb.params["g_nm"]), 3),
                                  "se": round(float(nb.bse["g_nm"]), 3),
                                  "p": float(norm.cdf(nb.params["g_nm"] / nb.bse["g_nm"])), "alpha": round(alpha, 3)}
    return out


def half_cells(cells: pd.DataFrame, city) -> pd.DataFrame:
    rows = []
    for _, c in cells.iterrows():
        g = wkb.loads(c.geom_wkb)
        p = np.array(g.exterior.coords)[:4]
        mid = lambda a, b: (a + b) / 2  # noqa: E731
        ctr = p.mean(axis=0)
        quads = [[p[0], mid(p[0], p[1]), ctr, mid(p[3], p[0])], [mid(p[0], p[1]), p[1], mid(p[1], p[2]), ctr],
                 [ctr, mid(p[1], p[2]), p[2], mid(p[2], p[3])], [mid(p[3], p[0]), ctr, mid(p[2], p[3]), p[3]]]
        for q in quads:
            poly = Polygon(q)
            a = poly.intersection(city).area / 1e6
            if a >= 0.0625:
                rows.append({"geom_wkb": poly.wkb, "area_km2": a, "pop2011": c.pop2011 / 4 * (a / 0.25),
                             "parent_density": c.pop2011 / c.area_km2, "admin_district": c.admin_district})
    return pd.DataFrame(rows)


def distances(cells: pd.DataFrame, stations: pd.DataFrame) -> tuple:
    to5514 = Transformer.from_crs("EPSG:4326", "EPSG:5514", always_xy=True)
    sx, sy = to5514.transform(stations.stop_lon.to_numpy(), stations.stop_lat.to_numpy())
    mx, my = to5514.transform(*MUSTEK)
    cen = np.array([[wkb.loads(g).centroid.x, wkb.loads(g).centroid.y] for g in cells.geom_wkb])
    dm = np.sqrt(((cen[:, None, 0] - sx) ** 2 + (cen[:, None, 1] - sy) ** 2)).min(axis=1)
    return (np.log2(np.maximum(dm, 100) / 1000),
            np.log2(np.maximum(np.hypot(cen[:, 0] - mx, cen[:, 1] - my), 100) / 1000))


def rail_tram_stops() -> pd.DataFrame:
    g = DATA / "praha2" / "gtfs"
    routes = pd.read_csv(g / "routes.txt", usecols=["route_id", "route_type"])
    keep = routes[routes.route_type.isin([0, 2])].route_id
    trips = pd.read_csv(g / "trips.txt", usecols=["route_id", "trip_id"])
    tids = set(trips[trips.route_id.isin(keep)].trip_id)
    st = pd.read_csv(g / "stop_times.txt", usecols=["trip_id", "stop_id"])
    sids = set(st[st.trip_id.isin(tids)].stop_id)
    stops = pd.read_csv(g / "stops.txt", usecols=["stop_id", "stop_lat", "stop_lon"])
    return stops[stops.stop_id.isin(sids)]


def robust_h5(rng) -> dict:
    keys = ["gamma", "se_conley_1_5km", "p_conley_negative", "p_wcr_negative", "p", "p_positive", "cells", "flats"]
    cells = pd.read_parquet(RAW / "prague_cells.parquet")
    city = wkb.loads(pd.read_parquet(RAW / "prague" / "prague.parquet").geom_wkb[0])
    y = h5_counts(cells, "2012-01-01", "2021-03-25")
    out = {}
    out["a_2012_2024"] = slim(h5(rng, cells, y=h5_counts(cells, "2012-01-01", "2024-12-31"), b=BR), keys)
    out["b_zsj"] = {"run": False, "reason": "no 2011 population by basic settlement unit in the registered inputs"}
    hc = half_cells(cells, city)
    st = pd.read_csv(DATA / "praha2" / "metro_stations.csv")
    st12 = st[~st.name.isin({"Bořislavka", "Nádraží Veleslavín", "Petřiny", "Nemocnice Motol"})]
    hc["log2_metro_km"], hc["log2_centre_km"] = distances(hc, st12)
    Xh, oh = h5_design(hc, dens=np.log1p(hc.parent_density).to_numpy())
    out["c_500m_cells"] = slim(h5(rng, hc, y=h5_counts(hc, "2012-01-01", "2021-03-25"), X=Xh, offset=oh, b=BR),
                               keys)
    c2 = cells.copy()
    c2["log2_metro_km"], _ = distances(cells, st)
    X2, o2 = h5_design(c2)
    out["d_stations_with_2015_extension"] = slim(h5(rng, c2, y=y, X=X2, offset=o2, b=BR), keys)
    out["e_heritage_reserve_excluded"] = {"run": False, "reason": "heritage polygon not obtained before estimation"}
    out["f_buildable_land"] = {"run": False, "reason": "Urban Atlas 2012 not obtained (login)"}
    pre = h5_counts(cells, "1000-01-01", "2011-12-31")
    X3, o3 = h5_design(cells, dens=np.log1p(pre / cells.area_km2.to_numpy()))
    out["g_ruian_pre2012_density"] = slim(h5(rng, cells, y=y, X=X3, offset=o3, b=BR), keys)
    out["h_implausible_types_excluded"] = slim(
        h5(rng, cells, y=h5_counts(cells, "2012-01-01", "2021-03-25", drop_types=True), b=BR), keys)
    X, off = h5_design(cells)
    pois = sm.GLM(y, X, family=sm.families.Poisson(), offset=off).fit()
    alpha = float(max((((y - pois.mu) ** 2 - pois.mu) / pois.mu ** 2).mean(), 0.01))
    nb = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=off).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(cells.admin_district)[0]})
    out["i_negative_binomial"] = {"gamma": round(float(nb.params[1]), 3), "se_cluster": round(float(nb.bse[1]), 3),
                                  "p": float(norm.cdf(nb.params[1] / nb.bse[1])), "alpha": round(alpha, 2)}
    rt = rail_tram_stops()
    dr, _ = distances(cells, rt.rename(columns={}))
    Xj = np.column_stack([X, dr])
    out["j_rail_tram_distance_added"] = slim(h5(rng, cells, y=y, X=Xj, offset=off, b=BR), keys)
    loo = {}
    for dist in cells.admin_district.unique():
        k = (cells.admin_district != dist).to_numpy()
        r = sm.GLM(y[k], X[k], family=sm.families.Poisson(), offset=off[k]).fit()
        loo[str(dist)] = round(float(r.params[1]), 3)
    out["k_leave_one_district_out"] = {"min": min(loo.values()), "max": max(loo.values()), "by_district": loo}
    out["l_line_d_excluded"] = {"run": False, "reason": "no official line D station coordinates obtained"}
    out["ladder_ii_iii"] = {"run": False, "reason": "developable-land and regulatory layers not obtained"}
    return out


def spec_curve(main: dict, rob: dict) -> dict:
    out = {}
    for h, est_key, sign in (("H2", "delta_months", 1), ("H4", "difference", -1), ("H5", "gamma", -1)):
        specs = [("main", main[h][est_key], main[h]["p"])]
        for k, v in rob[h].items():
            if isinstance(v, dict) and v.get("run", True) and est_key in v and "p" in v:
                specs.append((k, v[est_key], v["p"]))
        n = len(specs)
        same = sum(np.sign(e) == np.sign(main[h][est_key]) for _, e, _ in specs) / n
        sig = sum(p < 0.05 for _, _, p in specs) / n
        out[h] = {"specifications": [{"name": a, "estimate": b, "p": c} for a, b, c in specs],
                  "share_same_sign": round(float(same), 3), "share_p_below_005": round(float(sig), 3),
                  "robust": bool(same >= 0.75 and sig >= 0.5)}
    return out


def main() -> None:
    rng = np.random.default_rng(SEED + 1)
    main_res = json.loads((ROOT / "assets" / "praha" / "housing_extended.json").read_text())
    rob = {"H1": robust_h1()}
    print("H1 done", flush=True)
    rob["H3"] = robust_h3()
    rob["H4"] = robust_h4(rng)
    rob["H5"] = robust_h5(rng)
    print("H5 done", flush=True)
    rob["H2"] = robust_h2(rng)
    rob["spec_curve"] = spec_curve(main_res, rob)
    OUT.write_text(json.dumps(rob, ensure_ascii=False, indent=1, default=lambda o: o.tolist()
                              if hasattr(o, "tolist") else str(o)) + "\n")
    print(json.dumps(rob["spec_curve"], ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
