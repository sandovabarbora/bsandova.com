"""Part 6 (parking): the registered analyses. See docs/research/prague-parking-design.md (v2, registered 29 Sep 2026).

    uv run --no-project --with numpy --with pandas --with pyarrow --with pyproj python tools/parking6/parking6_estimate.py [--dry]

--dry is the blind dry run (DS11). Register lengths (L and WB together) are permuted across cohorts within make before
anything else touches them, so every output is from scrambled data. Output then goes to assets/parking6/dryrun.json
only.

The real run writes assets/parking6/h2.json, e1.json, e4.json and diagnostics.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parking6_dict import line_key, make_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")
DSJ = json.loads((ROOT / "docs/research/prague-parking-ds.json").read_text())
OUT = ROOT / "assets/parking6"
SEED = 20260928

# registered constants
DELTA_CM = DSJ["kappa"]["delta_H2a_cm"]                    # 4.4
EEA_SLOPE_MM = DSJ["eea_m1g"]["wheelbase_trend_2012_2022_mm_per_year"]   # 7.072
TE_H2B_CM = 6.0
N_STALLS = DSJ["layer3"]["ps_zps_sum"]                     # 168 424, September 2026 state
AREA_PER_STALL = 13.49
P_PERMIT = 1200.0
B_OUT, B_IN = 9999, 50
M_MC = 20000
PLAUS = {"L": (2400, 6000), "W": (1400, 2300), "WB": (1800, 3800)}


# ---------------------------------------------------------------------------------------------------------------
def load(dry: bool) -> pd.DataFrame:
    t = pq.read_table(RAW / "rsv_m1n1_20260901.parquet").to_pandas()
    t = t[t.cat.isin(["M1", "M1G"])].copy()
    t["make_c"] = t.make.map(make_key)
    keys = t[["make_c", "obch", "typ"]].drop_duplicates()
    keys["line"] = [line_key(m, o, ty) for m, o, ty in zip(keys.make_c, keys.obch, keys.typ)]
    t = t.merge(keys, on=["make_c", "obch", "typ"], how="left")
    t["m"] = t.rv.fillna(t.y1).fillna(t.ycz)
    t.loc[t.m > t.ycz, "m"] = t.ycz
    if dry:  # DS11: permute (L, W, WB) jointly across cohorts within make, before any statistic
        rng = np.random.default_rng(SEED)
        idx = t.groupby("make_c").indices
        perm = np.arange(len(t))
        for _, ix in idx.items():
            perm[ix] = rng.permutation(ix)
        for c in ("L", "W", "WB"):
            t[c] = t[c].to_numpy()[perm]
    for c, (lo, hi) in PLAUS.items():
        t.loc[~t[c].between(lo, hi), c] = np.nan
    # shifted triplets: length far (> 1 000 mm) from the make × line median -> missing
    med = t.groupby(["make_c", "line"]).L.transform("median")
    t.loc[(t.L - med).abs() > 1000, "L"] = np.nan
    t["new_cz"] = (t.y1 == t.ycz) & (t.rv.isna() | (t.rv >= t.ycz - 1))
    return t


# ---------------------------------------------------------------------------------------------------------------
def slope(Y: np.ndarray, years: np.ndarray) -> np.ndarray:
    x = years - years.mean()
    return (Y * x).sum(-1) / (x * x).sum()


def h2(t: pd.DataFrame) -> dict:
    years = np.arange(2012, 2026)
    eea = pd.concat([pd.read_csv(RAW / "eea_cz_by_model_m1_m1g.csv", usecols=["Year", "Mk", "Cn", "regs"]),
                     pd.read_csv(RAW / "eea_cz_counts_2023_2025_m1_m1g.csv", usecols=["Year", "Mk", "Cn", "regs"])])
    eea = eea[eea.Year.between(2012, 2025)]
    eea["make_c"] = eea.Mk.map(make_key)
    eea["line"] = [line_key(m, c) for m, c in zip(eea.make_c, eea.Cn)]
    W = eea.groupby(["make_c", "line", "Year"]).regs.sum().unstack(fill_value=0).reindex(columns=years, fill_value=0)
    lines = list(W.index)
    Wm = W.to_numpy(float).copy()

    r = t[t.new_cz & t.ycz.between(2012, 2025)]
    cell = r.groupby(["make_c", "line", "ycz"]).agg(n=("L", "count"), s=("L", "sum"), ss=("L", lambda v: float((v ** 2).sum())),
                                                    tot=("L", "size"))
    mk = r.groupby(["make_c", "ycz"]).L.mean()
    fallback_years = set(DSJ["ds12"]["years_falling_back"])
    M = np.full(Wm.shape, np.nan)
    Mvar = np.zeros(Wm.shape)   # MI (hot-deck) variance of the cell mean, normal approximation
    status = np.zeros(Wm.shape, dtype=int)  # 0 observed, 1 adjacent-year imputed, 2 make-year fallback, 3 dropped
    cd = {k: v for k, v in zip(cell.index, cell.itertuples(index=False))}
    for i, (mkc, ln) in enumerate(lines):
        for j, y in enumerate(years):
            if Wm[i, j] == 0:
                continue
            c = cd.get((mkc, ln, y))
            if str(y) not in fallback_years and c is not None and c.n > 0:
                mu = c.s / c.n
                M[i, j] = mu
                var = max(c.ss / c.n - mu * mu, 0.0)
                k = c.tot - c.n
                Mvar[i, j] = var * k / (c.tot ** 2) if k > 0 else 0.0
                continue
            got = None
            if str(y) not in fallback_years:
                for dy in (1, 2):
                    vals = [cd[(mkc, ln, yy)] for yy in (y - dy, y + dy) if (mkc, ln, yy) in cd and cd[(mkc, ln, yy)].n > 0]
                    if vals:
                        got = np.mean([v.s / v.n for v in vals])
                        break
            if got is not None:
                M[i, j], status[i, j] = got, 1
            elif (mkc, y) in mk.index and not np.isnan(mk[(mkc, y)]):
                M[i, j], status[i, j] = mk[(mkc, y)], 2
            else:
                status[i, j] = 3
                Wm[i, j] = 0.0
    M = np.nan_to_num(M)
    imputed = {int(y): {"adjacent": round(float(Wm[status[:, j] == 1, j].sum() / max(Wm[:, j].sum(), 1)), 4),
                        "make_year": round(float(Wm[status[:, j] == 2, j].sum() / max(Wm[:, j].sum(), 1)), 4),
                        "dropped_regs": int(W.to_numpy()[status[:, j] == 3, j].sum())} for j, y in enumerate(years)}

    # within-line length-on-wheelbase sufficient statistics (new to CZ, 2012–2022)
    b = r[r.ycz.between(2012, 2022)].dropna(subset=["L", "WB"])
    g = b.groupby(["make_c", "line"])
    st = pd.DataFrame({"n": g.size(), "sx": g.WB.sum(), "sy": g.L.sum(), "sxx": g.WB.apply(lambda v: float((v ** 2).sum())),
                       "sxy": g.apply(lambda d: float((d.WB * d.L).sum()))})
    st["Sxx"] = st.sxx - st.sx ** 2 / st.n
    st["Sxy"] = st.sxy - st.sx * st.sy / st.n
    st = st.reindex(lines).fillna(0.0)
    Sxx, Sxy = st.Sxx.to_numpy(), st.Sxy.to_numpy()

    i12 = slice(0, 11)          # 2012..2022
    i22 = slice(10, 14)         # 2022..2025
    y12, y22 = years[i12].astype(float), years[i22].astype(float)

    def stats(K: np.ndarray, Mx: np.ndarray = M) -> np.ndarray:
        """K: (draws, lines) multiplicities -> (draws, 3): Δ1 − C, Δ2, Δ1 (cm)."""
        num = K @ (Wm * Mx)
        den = K @ Wm
        Y = num / np.where(den > 0, den, np.nan)
        d1 = 10 * slope(Y[:, i12], y12) / 10.0
        d2 = 3 * slope(Y[:, i22], y22) / 10.0
        bh = (K @ Sxy) / (K @ Sxx)
        C = 10 * EEA_SLOPE_MM * bh / 10.0
        return np.column_stack([d1 - C, d2, d1, C, bh])

    nL = len(lines)
    one = np.ones((1, nL))

    def counts(idx: np.ndarray) -> np.ndarray:
        rows = idx.shape[0]
        flat = (np.arange(rows)[:, None] * nL + idx).ravel()
        return np.bincount(flat, minlength=rows * nL).reshape(rows, nL).astype(float)
    est = stats(one)[0]
    kish = float(Wm[:, i12].sum(1).sum() ** 2 / (Wm[:, i12].sum(1) ** 2).sum())

    rng = np.random.default_rng(SEED)

    def boot(Mx: np.ndarray, B: int, Bin: int, rng) -> tuple[np.ndarray, np.ndarray]:
        outs, ses = [], []
        for start in range(0, B, 500):
            nb = min(500, B - start)
            idx = rng.integers(0, nL, (nb, nL))
            K = counts(idx)
            # MI noise: one normal draw of each cell mean per outer draw
            Mn = Mx + rng.standard_normal(Mx.shape) * np.sqrt(Mvar)
            o = stats(K, Mn)
            outs.append(o)
            se = np.zeros((nb, 2))
            for q in range(nb):
                inn = idx[q][rng.integers(0, nL, (Bin, nL))]
                K2 = counts(inn)
                s2 = stats(K2, Mn)
                se[q] = np.nanstd(s2[:, :2], axis=0, ddof=1)
            ses.append(se)
        return np.vstack(outs), np.vstack(ses)

    def tests(e: np.ndarray, O: np.ndarray, S: np.ndarray) -> dict:
        d, d2 = e[0], e[1]
        se_d, se_2 = np.nanstd(O[:, 0], ddof=1), np.nanstd(O[:, 1], ddof=1)
        t1 = (O[:, 0] - d) / S[:, 0]
        t2 = (O[:, 1] - d2) / S[:, 1]
        B = np.isfinite(t1).sum()
        pv = lambda cnt: (cnt + 1) / (B + 1)
        pL = pv(np.sum(t1 >= (d + DELTA_CM) / se_d))       # H0: d <= -δ
        pU = pv(np.sum(t1 <= (d - DELTA_CM) / se_d))       # H0: d >= +δ
        p_dis = pv(np.sum(t1 >= (abs(d) - DELTA_CM) / se_d))  # H0: |d| <= δ (disagreement direction)
        p2 = pv(np.sum(t2 <= (d2 - TE_H2B_CM) / se_2))     # H0: Δ2 >= 6.0
        q1 = np.nanquantile(t1, [0.025, 0.975, 0.05, 0.95])
        q2 = np.nanquantile(t2, [0.025, 0.975])
        return {"d_cm": d, "se_d": se_d, "p_tost": max(pL, pU), "p_lower": pL, "p_upper": pU, "p_disagreement": p_dis,
                "ci90_d": [d - q1[3] * se_d, d - q1[2] * se_d], "ci95_d": [d - q1[1] * se_d, d - q1[0] * se_d],
                "delta2_cm": d2, "se_delta2": se_2, "p_h2b": p2, "ci95_delta2": [d2 - q2[1] * se_2, d2 - q2[0] * se_2],
                "B": int(B)}

    O, S = boot(M, B_OUT, B_IN, rng)
    T = tests(est, O, S)
    # Holm over {H2a, H2b}
    ps = {"H2a": T["p_tost"], "H2b": T["p_h2b"]}
    order = sorted(ps, key=ps.get)
    holm, stop = {}, False
    for rank, h in enumerate(order):
        thr = 0.05 / (len(ps) - rank)
        rej = (not stop) and ps[h] <= thr
        stop = stop or not rej
        holm[h] = {"p": ps[h], "threshold": thr, "rejected": bool(rej)}
    lo2, hi2 = T["ci95_delta2"]
    contest = "closer to Part II's +3.0" if hi2 < 4.5 else ("closer to T&E's +6.0" if lo2 > 4.5 else "undecided")
    if holm["H2a"]["rejected"]:
        h2a_read = "supported"
    elif abs(T["d_cm"]) > DELTA_CM and T["p_disagreement"] <= 0.05:
        h2a_read = "not supported: disagreement"
    else:
        h2a_read = "not supported: inconclusive (underpowered)"

    # leave-one-line-out
    tot = Wm.sum(1)
    top = np.argsort(-tot)[:30]
    lomo = []
    for i in top:
        K = np.ones((1, nL)); K[0, i] = 0
        s = stats(K)[0]
        lomo.append({"line": " ".join(lines[i]), "weight_share": float(tot[i] / tot.sum()),
                     "d_change": float(s[0] - est[0]), "delta2_change": float(s[1] - est[1])})
    lomo.sort(key=lambda x: -abs(x["d_change"]))

    # size check by simulation (reduced B), shifting the cell means so the truth sits on the null boundary
    def shifted(a: float, which: str) -> np.ndarray:
        Mx = M.copy()
        if which == "h2a":
            Mx += (a * 10) * np.clip(years - 2012, 0, 10)[None, :]    # a in cm/yr of Δ1 slope -> mm
        else:
            Mx += (a * 10) * np.clip(years - 2022, 0, None)[None, :]
        return Mx

    size = {}
    rng2 = np.random.default_rng(SEED + 1)
    for name, which, target, col in (("H2a_upper(+δ)", "h2a", est[0] - DELTA_CM, 0), ("H2a_lower(−δ)", "h2a", est[0] + DELTA_CM, 0),
                                     ("H2b(6.0)", "h2b", est[1] - TE_H2B_CM, 1)):
        a = -target / (10 if which == "h2a" else 3)
        Mx = shifted(a, which)
        rej = 0
        nsim = 200
        for _ in range(nsim):
            idx = rng2.integers(0, nL, nL)
            Kd = np.bincount(idx, minlength=nL)[None, :].astype(float)
            e_sim = stats(Kd, Mx)[0]
            # bootstrap on the simulated sample (reduced)
            O2, S2 = [], []
            idxb = idx[rng2.integers(0, nL, (199, nL))]
            Kb = counts(idxb)
            Ob = stats(Kb, Mx)
            seb = np.nanstd(Ob[:, col], ddof=1)
            tb = (Ob[:, col] - e_sim[col]) / seb
            if name.startswith("H2a_upper"):
                p = (np.sum(tb <= (e_sim[0] - DELTA_CM) / seb) + 1) / 200
            elif name.startswith("H2a_lower"):
                p = (np.sum(tb >= (e_sim[0] + DELTA_CM) / seb) + 1) / 200
            else:
                p = (np.sum(tb <= (e_sim[1] - TE_H2B_CM) / seb) + 1) / 200
            rej += p <= 0.05
        size[name] = {"rejection_rate": rej / nsim, "nsim": nsim, "B_inner": 199, "note": "reduced B, non-studentised"}

    # R12 sensitivities (point estimates; normal-approximation p from the outer SE)
    def point(Mx=M, drop_year=None, endpoint=False, unweighted=False, drop_line=None):
        Wx = Wm.copy()
        if drop_line is not None:
            Wx[drop_line] = 0
        if unweighted:
            yy = r.groupby("ycz").L.mean().reindex(years).to_numpy()
            Y = yy[None, :]
        else:
            Y = ((Wx * Mx).sum(0) / Wx.sum(0))[None, :]
        keep = np.ones(len(years), bool)
        if drop_year:
            keep[years == drop_year] = False
        k12 = keep.copy(); k12[11:] = False
        k22 = keep.copy(); k22[:10] = False
        if endpoint:
            d1 = (Y[0, 10] - Y[0, 0]) / 10.0
            d2 = (Y[0, 13] - Y[0, 10]) / 10.0
        else:
            d1 = 10 * slope(Y[:, k12], years[k12].astype(float))[0] / 10.0
            d2 = 3 * slope(Y[:, k22], years[k22].astype(float))[0] / 10.0
        return {"delta1_cm": float(d1), "d_cm": float(d1 - est[3]), "delta2_cm": float(d2)}

    sens = {"drop_2018": point(drop_year=2018), "drop_2016": point(drop_year=2016), "endpoints": point(endpoint=True),
            "unweighted": point(unweighted=True), "drop_largest_line": point(drop_line=int(top[0]))}

    Y = (Wm * M).sum(0) / Wm.sum(0)
    return {
        "estimates": {"delta1_cm": float(est[2]), "comparator_C_cm": float(est[3]), "b_hat": float(est[4]),
                      "d_cm": float(est[0]), "delta2_cm": float(est[1]), "delta_margin_cm": DELTA_CM,
                      "eea_slope_mm_per_year": EEA_SLOPE_MM},
        "annual_means_mm": {int(y): float(v) for y, v in zip(years, Y)},
        "tests": T, "holm": holm, "h2a_reading": h2a_read, "h2b_reading": "supported" if holm["H2b"]["rejected"] else "not supported",
        "forecast_contest": contest, "te_rounding_note_cm": 0.7,
        "kish_effective_clusters": kish, "lines": nL, "wild_fallback_used": kish < 30,
        "imputed_weight_by_year": imputed, "lomo_top": lomo[:10], "size_check": size, "r12": sens,
    }


# ---------------------------------------------------------------------------------------------------------------
def fleet_cells(t: pd.DataFrame) -> pd.DataFrame:
    e = t[t.ycz.notna() & (t.ycz <= 2025) & t.m.notna()].copy()
    e["ae"] = (e.ycz - e.m).clip(lower=0)
    g = e.groupby(["m", "ae"])
    c = pd.DataFrame({"E": g.size(), "nL": g.L.count(), "Lmean": g.L.mean(), "share_le_525": g.L.apply(lambda v: float((v <= 5250).mean()) if v.notna().any() else np.nan)}).reset_index()
    # cells with no observed length: same manufacture year, else neighbouring years
    bym = e.groupby("m").L.mean()
    bym525 = e.groupby("m").L.apply(lambda v: float((v <= 5250).mean()) if v.notna().any() else np.nan)
    for col, ref in (("Lmean", bym), ("share_le_525", bym525)):
        miss = c[col].isna()
        c.loc[miss, col] = c.loc[miss, "m"].map(ref)
        c[col] = c[col].fillna(c[col].mean())
    c["ye"] = c.m + c.ae
    return c


def e1(t: pd.DataFrame) -> dict:
    c = fleet_cells(t)
    rng = np.random.default_rng(SEED + 2)
    m = c.m.to_numpy(float); ae = c.ae.to_numpy(float); E = c.E.to_numpy(float); Lm = c.Lmean.to_numpy(float) / 1000
    ye = c.ye.to_numpy(float); f525 = c.share_le_525.to_numpy(float)
    brk = np.where(m < 2010, 0.005 * np.minimum(2010 - m, 20), 0.0)   # metres, per unit u

    def fleet(tyear, k, age, u):
        """vectorised over draws: k, age, u shape (D,) -> mean length (D,), share <= 5.25 m (D,)"""
        inc = (ye <= tyear) & (m <= tyear)
        mm, aa, EE, LL, bb, ff = m[inc], ae[inc], E[inc], Lm[inc], brk[inc], f525[inc]
        a_t = (tyear - mm + 0.5)[None, :]
        a_e = aa[None, :]
        lo = np.full(k.shape, 1.0); hi = np.full(k.shape, 400.0)
        kk = k[:, None]
        for _ in range(60):
            lam = 0.5 * (lo + hi)
            S = EE[None, :] * np.exp(-((np.maximum(tyear - mm, 0)[None, :] / lam[:, None]) ** kk) + (a_e / lam[:, None]) ** kk)
            mean_age = (S * a_t).sum(1) / S.sum(1)
            up = mean_age < age
            lo = np.where(up, lam, lo); hi = np.where(up, hi, lam)
        w = S / S.sum(1, keepdims=True)
        Lbar = (w * (LL[None, :] + u[:, None] * bb[None, :])).sum(1)
        # painted-bay share: shift of the cohort distribution by u*bracket approximated at the threshold (1 cm ≈ 1 % no-op)
        F = (w * ff[None, :]).sum(1)
        return Lbar, F

    def draw(D, rng):
        k = rng.uniform(1.4, 1.6, D); a12 = rng.uniform(13.3, 14.1, D); e = rng.uniform(-0.5, 0.5, D)
        u = rng.uniform(-1, 1, D); p = rng.triangular(4.9, 5.2, 5.5, D)
        ppv_p = rng.beta(1301 + 1, 12 + 1, D); ppv_n = rng.beta(338 + 1, 15 + 1, D); pu = rng.beta(10 + 1, 30 + 1, D)
        return dict(k=k, a12=a12, e=e, u=u, p=p, ppv_p=ppv_p, ppv_n=ppv_n, pu=pu)

    snap = snapshot_classes()

    def model(P):
        D = len(P["k"])
        out = {}
        for s0 in range(0, D, 2000):
            sl = slice(s0, s0 + 2000)
            L12, F12 = fleet(2012, P["k"][sl], P["a12"][sl] + P["e"][sl], P["u"][sl])
            L25, F25 = fleet(2025, P["k"][sl], 16.68 + P["e"][sl], P["u"][sl])
            for k_, v in (("L12", L12), ("L25", L25), ("F12", F12), ("F25", F25)):
                out.setdefault(k_, []).append(v)
        o = {k_: np.concatenate(v) for k_, v in out.items()}
        g = P["p"] - o["L25"]
        s = (snap["par"] * P["ppv_p"] + snap["non"] * (1 - P["ppv_n"]) + snap["unc"] * P["pu"]) / snap["tot"]
        th_u = 1 - (o["L12"] + g) / (o["L25"] + g)
        th_u_prop = 1 - o["L12"] / o["L25"]
        th_p = o["F12"] - o["F25"]
        th = s * th_u / (1 - th_u + s * th_u)  # share of N2012cf: s(ρ−1)/(1+s(ρ−1)), ρ = 1/(1−θu)
        extra = N_STALLS * s * (1 / (1 - th_u) - 1)
        return dict(theta_u=th_u, theta_u_prop=th_u_prop, theta_p=th_p, theta=th, extra=extra, s=s, g=g, **o)

    P = draw(M_MC, rng)
    R = model(P)

    def summ(x):
        x = np.asarray(x)
        q = np.quantile(x, [0.025, 0.5, 0.975])
        b = x[: (len(x) // 20) * 20].reshape(20, -1)
        bq = np.quantile(b, [0.025, 0.5, 0.975], axis=1)
        return {"q025": float(q[0]), "median": float(q[1]), "q975": float(q[2]),
                "mcse": [float(v) for v in bq.std(axis=1, ddof=1) / np.sqrt(20)]}

    res = {k_: summ(v) for k_, v in R.items()}
    # painted-bay sensitivity: s_p/ŝ in {0.25, 0.5}
    for f in (0.25, 0.5):
        su, sp = R["s"] * (1 - f), R["s"] * f
        rho = 1 / (1 - R["theta_u"])
        tot = su * (rho - 1) + sp * np.maximum(R["theta_p"], 0)
        res[f"theta_painted_share_{f}"] = summ(tot / (1 + tot))

    def band(lo, hi):
        edges = [0.01, 0.025, 0.05]
        names = ["< 1 %", "1 – 2.5 %", "2.5 – 5 %", "≥ 5 %"]
        bl = names[int(np.searchsorted(edges, lo, side="right"))]
        bh = names[int(np.searchsorted(edges, hi, side="right"))]
        return bl if bl == bh else f"straddles: {bl} / {bh}"

    th = res["theta"]
    res["band_theta"] = band(th["q025"], th["q975"])
    res["band_theta_u"] = band(res["theta_u"]["q025"], res["theta_u"]["q975"])
    res["P_MC_theta_ge_2.5pct"] = float((np.sum(R["theta"] >= 0.025) + 1) / (M_MC + 1))
    res["te_comparison"] = {"te_prorated_13y_pct": [7.4, 12.1], "part1_reproduction_prorated_pct": [2.9, 3.4]}

    # tipping points: central inputs, each moved to its range ends
    cen = {k_: np.array([v]) for k_, v in dict(k=1.5, a12=13.7, e=0.0, u=0.0, p=5.2, ppv_p=0.9909, ppv_n=0.9575, pu=0.25).items()}
    base = model(cen)["theta"][0]
    rng_ = {"k": (1.4, 1.6), "a12": (13.3, 14.1), "e": (-0.5, 0.5), "u": (-1, 1), "p": (4.9, 5.5)}
    tip = {"central_theta": float(base), "central_band": band(base, base), "moves": {}}
    for k_, (a, b_) in rng_.items():
        vals = {}
        for v in (a, b_):
            P2 = {kk: vv.copy() for kk, vv in cen.items()}; P2[k_] = np.array([v])
            vals[str(v)] = float(model(P2)["theta"][0])
        tip["moves"][k_] = {"theta_at_ends": vals, "changes_band": any(band(x, x) != tip["central_band"] for x in vals.values())}
    # s: all parallel-share extremes (uniform prior bounds, not the estimator)
    for sv in (0.5, 0.85, 1.0):
        rho = 1 / (1 - model(cen)["theta_u"][0])
        x = sv * (rho - 1) / (1 + sv * (rho - 1))
        tip["moves"].setdefault("s", {"theta_at_ends": {}, "changes_band": False})
        tip["moves"]["s"]["theta_at_ends"][str(sv)] = float(x)
        tip["moves"]["s"]["changes_band"] |= band(x, x) != tip["central_band"]
    # fleet growth that would be needed to leave the central band upwards (all else central)
    res["tipping"] = tip

    # grouped first-order Sobol (pick-freeze), groups: ageing, cohort bracket, pitch, parallel share
    Ms = 4000
    A = draw(Ms, np.random.default_rng(SEED + 3)); Bd = draw(Ms, np.random.default_rng(SEED + 4))
    yA = model(A)["theta"]; groups = {"ageing": ["k", "a12", "e"], "cohort_bracket": ["u"], "pitch": ["p"], "parallel_share": ["ppv_p", "ppv_n", "pu"]}
    sob = {}
    for gname, keys in groups.items():
        C = {k_: (A[k_] if k_ in keys else Bd[k_]) for k_ in A}
        yC = model(C)["theta"]
        sob[gname] = float(np.cov(yA, yC)[0, 1] / np.var(yA, ddof=1))
    res["sobol_first_order_grouped"] = sob

    # calibration diagnostic (2025): measured active fleet vs modelled at central inputs
    act = t[(t.status == "PROVOZOVANÉ") & (t.ycz <= 2025)]
    meas = float(act.L.mean() / 1000)
    modl = float(model(cen)["L25"][0])
    res["calibration_2025"] = {"measured_active_m": meas, "modelled_m": modl, "diff_cm": (meas - modl) * 100,
                               "rule_triggered": abs(meas - modl) * 100 > 2}
    res["snapshot_classes"] = snap
    res["n_stalls_administrative"] = N_STALLS
    return res


def snapshot_classes() -> dict:
    from pyproj import Transformer  # noqa: F401  (snapshot is already S-JTSK)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from parking6_design import band_width, classify
    snap = json.loads((RAW / "zps_layer3_snapshot_20260928.json").read_text())
    out = {"par": 0.0, "non": 0.0, "unc": 0.0}
    for f in snap["features"]:
        st = int(f["attributes"].get("PS_ZPS") or 0)
        rings = f.get("geometry", {}).get("rings") or []
        if not rings or st == 0:
            continue
        ring = max(rings, key=len)
        _, _, w = band_width(np.array(ring, float))
        c = classify(w)
        out[{"parallel": "par", "non_parallel": "non", "unclassified": "unc"}[c]] += st
    out["tot"] = out["par"] + out["non"] + out["unc"]
    return out


# ---------------------------------------------------------------------------------------------------------------
def e4(t: pd.DataFrame, e1res: dict) -> dict:
    act = t[(t.status == "PROVOZOVANÉ") & t.L.notna()]
    L = act.L.to_numpy(float) / 1000
    q = np.quantile(L, [0.1, 0.5, 0.9])
    Lbar = float(L.mean())
    g = np.array([e1res["g"]["q025"], e1res["g"]["median"], e1res["g"]["q975"]])
    s = np.array([e1res["s"]["q025"], e1res["s"]["median"], e1res["s"]["q975"]])
    out = {"fleet": "national active M1+M1G (status PROVOZOVANÉ), register snapshot 2026-09-01",
           "n": int(len(L)), "L_p10_p50_p90_m": [float(x) for x in q], "L_mean_m": Lbar}
    rows = {}
    for lab, gg, ss in (("central", g[1], s[1]), ("g_low", g[0], s[1]), ("g_high", g[2], s[1]), ("s_low", g[1], s[0]), ("s_high", g[1], s[2])):
        kc = P_PERMIT / (q + gg)
        rho = ss * (q + gg) / (Lbar + gg) + (1 - ss)
        sched = P_PERMIT * rho
        thr = 0.10 * (Lbar + gg) / ss
        share = float(np.mean(np.abs(L - Lbar) > thr))
        rows[lab] = {"g_m": float(gg), "s": float(ss), "kc_per_kerb_m_p10_p50_p90": [float(x) for x in kc],
                     "schedule_p10_p50_p90_kc": [float(x) for x in sched], "X_p90_minus_p10_kc": float(sched[2] - sched[0]),
                     "share_moving_more_than_10pct": share}
    out["size"] = rows
    A = AREA_PER_STALL
    out["level_bracket_kc_per_year"] = {
        "lower_second_car_price": {"value_B_A": 7000.0, "subsidy": 7000.0 - P_PERMIT},
        "central_land_rent_4pct": None,
        "upper_middle_garage_rents": None,
        "upper_OZV_10kc_m2_day": {"value_B_A": 10 * 365 * A, "subsidy": 10 * 365 * A - P_PERMIT},
    }
    out["size_at_bracket_ends_kc"] = {
        "at_second_car_price": float(7000.0 * s[1] * (q[2] - q[0]) / (Lbar + g[1])),
        "at_OZV": float(10 * 365 * A * s[1] * (q[2] - q[0]) / (Lbar + g[1])),
    }
    return out


# ---------------------------------------------------------------------------------------------------------------
def main() -> None:
    dry = "--dry" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    t = load(dry)
    res = {"dry_run": dry, "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    res["h2"] = h2(t)
    r1 = e1(t)
    res["e1"] = r1
    res["e4"] = e4(t, r1)
    if dry:
        (OUT / "dryrun.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
        print("dry run ok")
        return
    for k in ("h2", "e1", "e4"):
        (OUT / f"{k}.json").write_text(json.dumps({"code_sha256": res["code_sha256"], **res[k]}, indent=1, ensure_ascii=False, default=float))
    print("real run written")


if __name__ == "__main__":
    main()
