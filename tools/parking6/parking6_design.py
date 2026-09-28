"""Design-stage checks for Part 6 (parking), run before registration. No outcome is computed here.

    uv run --no-project --with numpy --with scipy --with pyproj python tools/parking6/parking6_design.py [kappa|classifier|layer3|ds10|all]

- kappa: the fleet transfer coefficient κ and the consequence-based margin δ, from constants only (mean ages, Part II's
  published fleet lengths, the reference pitch). No register value is read.
- classifier: the band-width rule for parallel stalls, validated on the labelled 2019 segments (TYPSTANI). This is
  stall-type geometry, not an outcome.
- layer3: snapshot of the live segment layer (ArcGIS MapServer/3, S-JTSK), written and hashed.
- ds10: the route (b) stock model against the published 2016–2019 fleet counts and mean ages. Its inputs are the
  entry counts by year of first registration in CZ and by manufacture year, from the DS1 coverage file (counts only).

Results are written to docs/research/prague-parking-ds.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")
OUT = ROOT / "docs/research/prague-parking-ds.json"

# ---- constants (all published before this design; see §0) ----------------------------------------
MEAN_AGE = {2012: 13.62, 2025: 16.68}            # 2012 extrapolated (Parts I–II), 2025 SDA
SDA = {2016: (14.5, 5_368_661), 2017: (14.6, 5_592_738), 2018: (14.8, 5_802_521), 2019: (14.9, 5_989_538)}
FLEET_L = {2012: 4.098, 2025: 4.195}              # Part II published fleet lengths, m
PITCH_REF = 5.20                                  # T&E / Berlin, observed on the parked fleet
S_CENTRAL = 0.68
MAX_AGE = 45


def load() -> dict:
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def save(res: dict) -> None:
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- κ and δ --------------------------------------------------------------------------------------

def weibull_weights(mean_age: float, k: float = 2.0, max_age: int = MAX_AGE) -> np.ndarray:
    """Discrete survival weights S(a) = exp(-(a/λ)^k), λ solved so the discrete mean equals mean_age."""
    ages = np.arange(max_age + 1, dtype=float)
    lo, hi = 1e-3, 500.0
    for _ in range(200):
        lam = 0.5 * (lo + hi)
        w = np.exp(-((ages / lam) ** k))
        if (ages * w).sum() / w.sum() < mean_age:
            lo = lam
        else:
            hi = lam
    return w / w.sum()


def ramp(years: np.ndarray, start: int = 2012, end: int = 2022) -> np.ndarray:
    """New-car perturbation: 0 up to 2012, linear to 1 in 2022, held at 1 afterwards."""
    return np.clip((years - start) / (end - start), 0.0, 1.0)


def kappa(k: float = 2.0, entry: dict[int, float] | None = None) -> float:
    """∂(fleet length 2025 − fleet length 2012) / ∂(new-car change 2012→2022) under route (b)."""
    out = {}
    for t in (2012, 2025):
        ages = np.arange(MAX_AGE + 1)
        w = weibull_weights(MEAN_AGE[t], k)
        if entry:
            e = np.array([entry.get(t - a, entry[min(entry)] if t - a < min(entry) else entry[max(entry)]) for a in ages])
            w = w * e / (w * e).sum()
        out[t] = float((w * ramp(t - ages)).sum())
    return out[2025] - out[2012]


def theta1(dLf: float, s: float, L12: float, g: float) -> float:
    rho = (L12 + dLf + g) / (L12 + g)
    return s * (rho - 1) / (1 + s * (rho - 1))


def run_kappa() -> dict:
    g = PITCH_REF - FLEET_L[2025]
    L12 = FLEET_L[2012]
    base = FLEET_L[2025] - FLEET_L[2012]
    eps = 1e-4
    grid = {}
    for s in (0.50, S_CENTRAL, 0.85, 1.0):
        d = (theta1(base + eps, s, L12, g) - theta1(base - eps, s, L12, g)) / (2 * eps)
        grid[str(s)] = d
    eea_regs = {2010: 164618, 2011: 169259, 2012: 169576, 2013: 161155, 2014: 174562, 2015: 221289, 2016: 214408,
                2017: 213542, 2018: 229002, 2019: 233603, 2020: 186262, 2021: 189449, 2022: 174323}
    kap = {f"weibull_k{k}": kappa(k) for k in (1.5, 2.0, 3.0)}
    kap["weibull_k2.0_entry_weighted_eea"] = kappa(2.0, eea_regs)
    kap_c = kap["weibull_k1.5"]   # k = 1.5: centre of the DS10b-admissible range [1.4, 1.6] (was k = 2 before DS10)
    dtheta = grid[str(S_CENTRAL)]
    delta = 0.0025 / (kap_c * dtheta)
    delta_fixed = float(np.floor(delta * 1000) / 1000)   # rounded down to the millimetre, conservative
    # B.2: fleet-mean growth needed for θ1 = 3.7 %
    need = {}
    for s in (0.68, 0.85, 1.0):
        for gg in (0.82, round(g, 3)):
            lo, hi = 0.0, 1.0
            for _ in range(100):
                m = 0.5 * (lo + hi)
                lo, hi = (m, hi) if theta1(m, s, L12, gg) < 0.037 else (lo, m)
            need[f"s{s}_g{gg}"] = round(lo * 100, 1)
    return {
        "inputs": {"mean_age": MEAN_AGE, "fleet_length_m": FLEET_L, "pitch_ref_m": PITCH_REF,
                   "g_derived_m": round(g, 4), "s": S_CENTRAL, "perturbation": "ramp 0 (≤2012) → 1 (2022), held after"},
        "kappa": {k: round(v, 4) for k, v in kap.items()},
        "dtheta1_dfleetlength_per_m": {k: round(v, 5) for k, v in grid.items()},
        "delta_newcar_cm_exact": round(delta * 100, 3),
        "delta_newcar_cm_registered": round(delta_fixed * 100, 1),
        "delta_by_s_cm": {s: round(0.0025 / (kap_c * v) * 100, 2) for s, v in grid.items()},
        # primary estimand θ1u is per unmarked parallel kerb (s = 1): that sets the registered margin
        "delta_H2a_cm": float(np.floor(0.0025 / (kap_c * grid["1.0"]) * 1000) / 10),
        "fleet_growth_needed_for_theta1_3.7pct_cm": need,
    }


# ---- width classifier -----------------------------------------------------------------------------

def band_width(xy: np.ndarray) -> tuple[float, float, float]:
    x, y = xy[:, 0], xy[:, 1]
    area = 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
    per = float(np.hypot(np.diff(x), np.diff(y)).sum())
    h = per / 2
    disc = h * h - 4 * area
    w = (h - np.sqrt(disc)) / 2 if disc > 0 else h / 2
    return area, per, w


def classify(w: float) -> str:
    if 1.6 <= w <= 3.2:
        return "parallel"
    if 4.0 <= w <= 6.5:
        return "non_parallel"
    return "unclassified"


def run_classifier() -> dict:
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:4326", "EPSG:5514", always_xy=True)
    src = RAW / "zpsmap/ZPS251_USEKY.json"
    feats = json.loads(src.read_text())["features"]
    truth_map = {1: "parallel", 2: "non_parallel", 3: "non_parallel"}
    conf = defaultdict(lambda: [0, 0])  # (truth, pred) -> [segments, stalls]
    widths = defaultdict(list)
    n_used = n_skip = 0
    for f in feats:
        p = f["properties"]
        t = truth_map.get(p["TYPSTANI"])
        if t is None:
            n_skip += 1
            continue
        ring = np.array(f["geometry"]["coordinates"][0])
        X, Y = tr.transform(ring[:, 0], ring[:, 1])
        _, _, w = band_width(np.column_stack([X, Y]))
        pred = classify(w)
        stalls = int(p["PS_ZPS"] or 0)
        conf[(t, pred)][0] += 1
        conf[(t, pred)][1] += stalls
        widths[p["TYPSTANI_T"]].append(w)
        n_used += 1

    def tot(idx, cond):
        return sum(v[idx] for k, v in conf.items() if cond(k))

    res = {"source": str(src.name), "sha256": sha256(src), "segments_labelled_used": n_used,
           "segments_skipped_unlabelled": n_skip,
           "confusion_segments": {f"{t}->{p}": v[0] for (t, p), v in sorted(conf.items())},
           "confusion_stalls": {f"{t}->{p}": v[1] for (t, p), v in sorted(conf.items())},
           "width_quantiles_m": {k: [round(float(q), 2) for q in np.quantile(v, [0.05, 0.25, 0.5, 0.75, 0.95])]
                                 for k, v in widths.items()}}
    for idx, unit in ((0, "segments"), (1, "stalls")):
        classified = tot(idx, lambda k: k[1] != "unclassified")
        correct = tot(idx, lambda k: k[0] == k[1])
        allv = tot(idx, lambda k: True)
        ppv_par = conf[("parallel", "parallel")][idx] / max(1, tot(idx, lambda k: k[1] == "parallel"))
        ppv_non = conf[("non_parallel", "non_parallel")][idx] / max(1, tot(idx, lambda k: k[1] == "non_parallel"))
        res[unit] = {"accuracy_among_classified": round(correct / classified, 4),
                     "accuracy_unclassified_as_wrong": round(correct / allv, 4),
                     "unclassified_share": round(1 - classified / allv, 4),
                     "ppv_parallel": round(ppv_par, 4), "ppv_non_parallel": round(ppv_non, 4),
                     "true_parallel_share": round(tot(idx, lambda k: k[0] == "parallel") / allv, 4)}
    # PPV ratio estimator of s, in sample (optimistic by construction), stall-weighted, unclassified by label rate
    st = lambda t, p: conf[(t, p)][1]
    pred_par = st("parallel", "parallel") + st("non_parallel", "parallel")
    pred_non = st("parallel", "non_parallel") + st("non_parallel", "non_parallel")
    uncl = st("parallel", "unclassified") + st("non_parallel", "unclassified")
    s_hat = (pred_par * res["stalls"]["ppv_parallel"] + pred_non * (1 - res["stalls"]["ppv_non_parallel"])
             + st("parallel", "unclassified")) / (pred_par + pred_non + uncl)
    res["s_hat_ppv_in_sample"] = round(s_hat, 4)
    res["pre_committed_rule"] = "accuracy (stalls, unclassified counted as wrong) >= 0.80 -> classifier used; else prior"
    res["passes"] = res["stalls"]["accuracy_unclassified_as_wrong"] >= 0.80
    return res


# ---- layer 3 snapshot -----------------------------------------------------------------------------

def run_layer3() -> dict:
    base = "https://gs-pub.praha.eu/arcgis/rest/services/dop/zony_placeneho_stani/MapServer/3/query"
    feats, off = [], 0
    while True:
        q = {"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "5514", "f": "json",
             "orderByFields": "OBJECTID", "resultOffset": off, "resultRecordCount": 1000}
        with urllib.request.urlopen(base + "?" + urllib.parse.urlencode(q), timeout=300) as r:
            page = json.load(r)
        got = page.get("features", [])
        feats += got
        if len(got) < 1000:
            break
        off += 1000
    from datetime import date
    out = RAW / f"zps_layer3_snapshot_{date.today():%Y%m%d}.json"
    out.write_text(json.dumps({"source": base, "outSR": 5514, "features": feats}, ensure_ascii=False))
    stalls = sum(int(f["attributes"].get("PS_ZPS") or 0) for f in feats)
    return {"file": out.name, "sha256": sha256(out), "features": len(feats), "ps_zps_sum": stalls,
            "unique_objectid": len({f["attributes"]["OBJECTID"] for f in feats})}


# ---- DS10 -----------------------------------------------------------------------------------------

def run_ds10() -> dict:
    """Route (b) stock model against SDA 2016–2019 counts and mean ages.

    Entries E[(y_entry, y_manuf)] = M1+M1G rows by year of first CZ registration and manufacture year (all statuses).
    Survival on age since manufacture, Weibull (k, λ), conditional on survival to the age at entry.
    Calibration: λ so the modelled 2016 mean age equals 14.5 (k = 2 primary; 1.5 and 3 reported).
    Prediction: 2017–2019 mean age and 2016–2019 stock counts (the counts are never used in calibration).
    Pre-committed tolerances: |age error| <= 0.3 years and |count error| <= 5 % in every year.
    """
    cov = json.loads((RAW / "rsv_coverage_20260901.json").read_text())
    E = defaultdict(float)
    for cat, rv, y1, ycz, st, lp, wp, n in cov["cells"]:
        if cat not in ("M1", "M1G"):
            continue
        ye = int(ycz) if ycz else (int(y1) if y1 else None)
        ym = int(rv) if rv.isdigit() else (int(y1) if y1 else ye)
        if ye is None or ym is None or ye < 1950 or ye > 2026:
            continue
        ym = min(ym, ye)
        E[(ye, ym)] += n

    def stock(t: int, k: float, lam: float) -> tuple[float, float]:
        tot = agesum = 0.0
        for (ye, ym), n in E.items():
            if ye > t:
                continue
            a_e, a_t = max(ye - ym, 0), t - ym
            surv = np.exp(-((a_t / lam) ** k) + (a_e / lam) ** k)
            tot += n * surv
            agesum += n * surv * (t - ym + 0.5)
        return tot, agesum / tot

    res = {"entries_m1_m1g_total": sum(E.values()), "tolerances": {"age_years": 0.3, "count_pct": 5.0}, "fits": {}}
    for k in (1.5, 2.0, 3.0):
        lo, hi = 1.0, 200.0
        for _ in range(80):
            lam = 0.5 * (lo + hi)
            lo, hi = (lam, hi) if stock(2016, k, lam)[1] < SDA[2016][0] else (lo, lam)
        rows = {}
        ok = True
        for t, (age, cnt) in SDA.items():
            n_hat, a_hat = stock(t, k, lam)
            ea, ec = a_hat - age, 100 * (n_hat - cnt) / cnt
            ok &= abs(ea) <= 0.3 and abs(ec) <= 5.0
            rows[t] = {"age_model": round(a_hat, 2), "age_sda": age, "count_model": round(n_hat), "count_sda": cnt,
                       "age_err": round(ea, 2), "count_err_pct": round(ec, 2)}
        res["fits"][f"k{k}"] = {"lambda": round(lam, 3), "years": rows, "passes": bool(ok)}
    res["passes_primary_k2"] = res["fits"]["k2.0"]["passes"]

    # DS10b (added after DS10 failed, before any length is read): the registered route (b) calibrates λ_t per year
    # to that year's mean age, so ages fit by construction. The counts decide which k are admissible (±5 % in every
    # year 2016–2019). The k prior of §4 becomes uniform over the admissible range.
    grid = {}
    for k in np.round(np.arange(0.8, 3.01, 0.1), 2):
        errs = {}
        for t, (age, cnt) in SDA.items():
            lo, hi = 1.0, 400.0
            for _ in range(70):
                lam = 0.5 * (lo + hi)
                lo, hi = (lam, hi) if stock(t, float(k), lam)[1] < age else (lo, lam)
            errs[t] = round(100 * (stock(t, float(k), lam)[0] - cnt) / cnt, 2)
        grid[f"{k:.1f}"] = {"count_err_pct": errs, "admissible": all(abs(e) <= 5.0 for e in errs.values())}
    adm = [float(k) for k, v in grid.items() if v["admissible"]]
    res["ds10b_per_year_lambda"] = {"grid": grid, "admissible_k": [min(adm), max(adm)] if adm else None}
    return res


# ---- DS1: register coverage (counts and missingness only) ----------------------------------------

def run_ds1() -> dict:
    src = RAW / "rsv_coverage_20260901.json"
    cov = json.loads(src.read_text())
    eea = {2010: 164618, 2011: 169259, 2012: 169576, 2013: 161155, 2014: 174562, 2015: 221289, 2016: 214408,
           2017: 213542, 2018: 229002, 2019: 233603, 2020: 186262, 2021: 189449, 2022: 174323}
    m1g = load().get("eea_m1g", {}).get("m1g_share_by_year", {})
    by_rv = defaultdict(lambda: [0, 0, 0])      # manufacture year -> [rows, length present, wheelbase present]
    new_cz = defaultdict(lambda: [0, 0])         # entry year -> [new to CZ rows, of which length present]
    entries = defaultdict(int)                   # entry year -> all M1+M1G entries (new + used import)
    status = defaultdict(int)
    cats = defaultdict(int)
    for cat, rv, y1, ycz, st, lp, wp, n in cov["cells"]:
        cats[cat] += n
        if cat not in ("M1", "M1G"):
            continue
        status[st or "(empty)"] += n
        if rv.isdigit():
            by_rv[int(rv)][0] += n
            by_rv[int(rv)][1] += n * lp
            by_rv[int(rv)][2] += n * wp
        else:
            by_rv["missing"][0] += n
            by_rv["missing"][1] += n * lp
            by_rv["missing"][2] += n * wp
        if ycz.isdigit():
            entries[int(ycz)] += n
            if y1 == ycz and (not rv.isdigit() or int(rv) >= int(ycz) - 1):
                new_cz[int(ycz)][0] += n
                new_cz[int(ycz)][1] += n * lp
    jan = defaultdict(lambda: [0, 0])
    for y, is_jan, n in cov["jan1_first_reg_cz_m1"]:
        jan[y][0] += n
        jan[y][1] += n * bool(is_jan)
    out = {"source": src.name, "rows_total": cov["rows"], "short_rows": cov["short_rows"],
           "rows_by_category": dict(cats), "m1_m1g_status": dict(sorted(status.items(), key=lambda kv: -kv[1])),
           "coverage_by_manufacture_year": {}, "new_to_cz_vs_eea": {}, "jan1_share_first_reg_cz": {}}
    for k in sorted(by_rv, key=lambda x: (isinstance(x, str), x)):
        if isinstance(k, int) and not (1990 <= k <= 2026):
            continue
        r, lp, wp = by_rv[k]
        out["coverage_by_manufacture_year"][str(k)] = {"rows": r, "length_present": round(lp / r, 4),
                                                       "wheelbase_present": round(wp / r, 4)}
    pre1990 = [by_rv[k] for k in by_rv if isinstance(k, int) and k < 1990]
    out["coverage_pre1990"] = {"rows": sum(x[0] for x in pre1990),
                               "length_present": round(sum(x[1] for x in pre1990) / max(1, sum(x[0] for x in pre1990)), 4)}
    for y in range(2010, 2026):
        nn, lp = new_cz.get(y, [0, 0])
        ref = eea.get(y)
        ref_m1g = ref / (1 - float(m1g.get(str(y), 0))) if ref else None   # Part II counts are M1 only
        out["new_to_cz_vs_eea"][str(y)] = {
            "rsv_new_to_cz": nn, "rsv_entries_all": entries.get(y, 0),
            "length_present_new": round(lp / nn, 4) if nn else None,
            "eea_m1_m1g_approx": round(ref_m1g) if ref_m1g else None,
            "ratio_rsv_to_eea": round(nn / ref_m1g, 3) if ref_m1g else None}
    for y in sorted(jan):
        if y and 2000 <= int(y) <= 2026:
            out["jan1_share_first_reg_cz"][y] = round(jan[y][1] / jan[y][0], 4)
    out["rule"] = ("coverage (length present) < 0.90 in any year 2012–2025 -> H2a/H2b reweight to EEA / register "
                   "entry counts and are flagged")
    out["years_below_0.90_new_to_cz_2012_2025"] = [y for y, v in out["new_to_cz_vs_eea"].items()
                                                   if 2012 <= int(y) <= 2025 and v["length_present_new"] is not None
                                                   and v["length_present_new"] < 0.90]
    return out


# ---- DS8: precision and prior-predictive probability for H2a / H2b ---------------------------------

def run_ds8(B: int = 4000, seed: int = 20260928) -> dict:
    """SE proxies from the EEA model-level wheelbase file (already seen; no register value).

    SE of 10×trend slope 2012–2022 and of 3×trend slope 2019–2022 (proxy for 2022–2025), by cluster bootstrap over
    make × commercial name, converted to length at 1/0.618. Prior-predictive P(supported):
      H2a: d = Δ_RSV − C ~ N(0, 1.7²) cm (Part II's ratio half-band taken as one SD), TOST at margin δ.
      H2b: Δ_22→25 ~ Uniform(3.0, 6.0) cm (between Part II's and T&E's forecasts), one-sided test against 6.0.
    """
    import csv
    from statistics import NormalDist

    N = NormalDist()
    rows = list(csv.DictReader((RAW / "eea_cz_by_model_m1_m1g.csv").open()))
    cl = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))  # cluster -> year -> [n_w, sum_w]
    for r in rows:
        k = (r["Mk"], r["Cn"])
        y = int(r["Year"])
        cl[k][y][0] += float(r["n_w"] or 0)
        cl[k][y][1] += float(r["sum_w"] or 0)
    keys = list(cl)
    tot_w = np.array([sum(v[0] for v in cl[k].values()) for k in keys])
    kish = float(tot_w.sum() ** 2 / (tot_w ** 2).sum())

    def slope(sample, years):
        num = defaultdict(float)
        den = defaultdict(float)
        for k in sample:
            for y, (n, s) in cl[k].items():
                num[y] += s
                den[y] += n
        ys = [y for y in years if den[y] > 0]
        return float(np.polyfit(ys, [num[y] / den[y] for y in ys], 1)[0])

    rng = np.random.default_rng(seed)
    y1, y2 = list(range(2012, 2023)), list(range(2019, 2023))
    b1, b2 = [], []
    for _ in range(B):
        idx = rng.integers(0, len(keys), len(keys))
        smp = [keys[i] for i in idx]
        b1.append(10 * slope(smp, y1))
        b2.append(3 * slope(smp, y2))
    se1 = float(np.std(b1, ddof=1)) / 0.618 / 10   # cm
    se2 = float(np.std(b2, ddof=1)) / 0.618 / 10
    res = {"clusters": len(keys), "kish_effective_clusters": round(kish, 1),
           "se_length_change_2012_2022_cm": round(se1, 3), "se_length_change_2019_2022_x3_cm_proxy": round(se2, 3)}
    z = 1.6448536
    delta = load().get("kappa", {}).get("delta_H2a_cm")
    if delta:
        ds = np.linspace(-4 * 1.7, 4 * 1.7, 2001)
        dens = np.array([N.pdf(d / 1.7) for d in ds])
        dens /= dens.sum()
        lim = delta - z * se1
        pp = [N.cdf((lim - d) / se1) - N.cdf((-lim - d) / se1) if lim > 0 else 0.0 for d in ds]
        res["H2a_prior_predictive_P_supported"] = round(float(np.dot(dens, pp)), 4)
        res["H2a_power_at_d0"] = round(N.cdf(lim / se1) - N.cdf(-lim / se1) if lim > 0 else 0.0, 4)
        res["H2a_mde_margin_80pct_at_d0_cm"] = round((z + 1.2816) * se1, 2)
    grid = np.linspace(3.0, 6.0, 601)
    res["H2b_prior_predictive_P_supported"] = round(float(np.mean([N.cdf((6.0 - g) / se2 - z) for g in grid])), 4)
    res["H2b_power_at_3cm"] = round(N.cdf((6.0 - 3.0) / se2 - z), 4)
    res["rule"] = "A.4: prior-predictive P(supported) > 0.95 -> reported as descriptive, outside the family"
    return res


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = load()
    for name, fn in (("kappa", run_kappa), ("classifier", run_classifier), ("layer3", run_layer3), ("ds1", run_ds1), ("ds8", run_ds8),
                     ("ds10", run_ds10)):
        if what in (name, "all"):
            res[name] = fn()
            print(name, json.dumps(res[name], ensure_ascii=False, indent=1)[:4000])
    save(res)
