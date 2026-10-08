"""Estimates of the bunching design (§2, §5–§7, as changed on 8 October 2026) from the screened pair tables.

Q1 (primary): γ_IV, the Anderson–Hsiao estimate of Δr_k on (r_{k−1} − 1) with r_{k−2} − 1 as instrument, fixed effects
pattern × stop and pattern × hour × weekday, interval from a bootstrap over dates. The registered γ − γ₀ is a check:
tests on made-up data showed that its shuffle also breaks the measurement noise it was meant to keep (see the design).
Q2 / Q2b (primary): cross-fitted birth-rate concentration against an exposure-only null, and its split-half stability.
Q3 (secondary): birth rate at a segment's second stop against the spread of part 1's gain on the segment.

Writes docs/research/bunching-results[-bus].json and assets/bunch/*.json for the article.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with scipy --with duckdb python tools/bunch/estimate.py
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/bunch"
REPS, NULL_POINT, NULL_DRAW, SHUFFLES, SEED = 999, 199, 49, 5, 20261008
BUNCH, GAP, ELIGIBLE, H_MIN = 0.25, 1.75, 0.5, 240.0
log = logging.getLogger("bunch.estimate")


# ---------------------------------------------------------------- data

def load(mode: str) -> pd.DataFrame:
    parts = [pd.read_parquet(f) for f in sorted(DATA.glob(f"pairs_{mode}_*.parquet"))]
    ps = pd.concat(parts, ignore_index=True)
    thin = set(pd.read_parquet(DATA / f"thin_{mode}.parquet")["pattern"])
    ps = ps[~ps["pattern"].isin(thin)]
    return prepare(ps)


def prepare(ps: pd.DataFrame) -> pd.DataFrame:
    ps = ps.copy()
    ps["sdate"] = pd.to_datetime(ps["sdate"])
    ps["pair"] = ps.groupby(["pattern", "sdate", "lead", "follow"], sort=False, observed=True).ngroup()
    for c in ("pattern", "stop_id", "prev_stop_id", "stop_name", "prev_name"):
        if c in ps:
            ps[c] = ps[c].astype("category")
    ps = ps.drop(columns=["lead", "follow"])
    ps["r"] = np.where(ps["status"] == 1, ps["h"] / ps["H"], np.nan)
    ps["weekday"] = ps["sdate"].dt.weekday
    ps["week"] = ps["sdate"].dt.isocalendar().week.astype(int)
    ps["date_id"] = pd.factorize(ps["sdate"])[0]
    return ps.sort_values(["pair", "k"]).reset_index(drop=True)


def transitions(ps: pd.DataFrame, value: str = "r") -> pd.DataFrame:
    """Rows with the same pair at consecutive stops k−1 and k, both observed; r_{k−2} where also observed."""
    t = ps[["pair", "k", value]].rename(columns={value: "v"})
    prev = t.assign(k=t["k"] + 1).rename(columns={"v": "v1"})
    prev2 = t.assign(k=t["k"] + 2).rename(columns={"v": "v2"})
    d = ps.merge(prev, on=["pair", "k"]).merge(prev2, on=["pair", "k"], how="left")
    d = d.rename(columns={value: "v"})
    return d[d["v"].notna() & d["v1"].notna()].reset_index(drop=True)


# ---------------------------------------------------------------- Q1

def demean(cols: list[np.ndarray], groups: list[np.ndarray], w: np.ndarray | None = None, iters: int = 30) -> list:
    w = np.ones(len(groups[0])) if w is None else w
    out = [c.astype(float).copy() for c in cols]
    for _ in range(iters):
        for g in groups:
            sw = np.bincount(g, weights=w)
            for c in out:
                c -= (np.bincount(g, weights=w * c) / np.where(sw > 0, sw, 1))[g]
    return out


def fe_groups(d: pd.DataFrame) -> list[np.ndarray]:
    return [d.groupby(["pattern", "k"], observed=True, sort=False).ngroup().to_numpy(),
            d.groupby(["pattern", "hour", "weekday"], observed=True, sort=False).ngroup().to_numpy()]


def gamma_parts(d: pd.DataFrame, iv: bool = True, weight: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Per-date numerator and denominator of γ after removing the fixed effects (fixed at the full-sample values)."""
    if iv:
        d = d[d["v2"].notna()]
    y = (d["v"] - d["v1"]).to_numpy()
    x = (d["v1"] - 1).to_numpy()
    z = (d["v2"] - 1).to_numpy() if iv else x
    w = None if weight is None else weight[d.index] if len(weight) != len(d) else weight
    yt, xt, zt = demean([y, x, z], fe_groups(d), w)
    ww = np.ones(len(d)) if w is None else w
    did = d["date_id"].to_numpy()
    n = did.max() + 1
    return np.bincount(did, ww * zt * yt, n), np.bincount(did, ww * zt * xt, n)


def boot_ratio(num: np.ndarray, den: np.ndarray, rng, blocks: np.ndarray | None = None) -> tuple[float, list, list]:
    est = num.sum() / den.sum()
    units = np.arange(len(num)) if blocks is None else blocks
    ids = np.unique(units)
    draws = []
    for _ in range(REPS):
        pick = rng.choice(ids, len(ids))
        w = np.bincount(np.searchsorted(ids, pick), minlength=len(ids))[np.searchsorted(ids, units)]
        draws.append((w * num).sum() / (w * den).sum())
    return round(float(est), 4), q(draws, 0.95), q(draws, 0.90)


def q(draws, level: float) -> list:
    return [round(float(x), 4) for x in np.nanquantile(draws, [(1 - level) / 2, 1 - (1 - level) / 2])]


def label_gamma(ci95: list, ci90: list, margin: float = 0.01) -> str:
    """§6: supported if the 95 % interval is wholly above 0; inconclusive, by the design's specific clause, if it is
    wholly below 0 (correction outweighs amplification); not supported if the 90 % interval is wholly within ±margin.
    The wholly-below-0 case is checked before the margin (corrected after publication, 8 October 2026)."""
    if ci95[0] > 0:
        return "supported"
    if ci95[1] < 0:
        return "inconclusive"
    if -margin < ci90[0] and ci90[1] < margin:
        return "not supported"
    return "inconclusive"


def shuffled(ps: pd.DataFrame, rng) -> pd.DataFrame:
    """Followers' stop-to-stop increments of h permuted across pairs within pattern × hour × date, at each stop."""
    o = ps[ps["status"] == 1][["pair", "k", "pattern", "hour", "sdate", "h", "H", "date_id", "weekday"]].copy()
    o = o.sort_values(["pair", "k"])
    o["inc"] = o.groupby("pair")["h"].diff()
    o.loc[o.groupby("pair")["k"].diff() != 1, "inc"] = np.nan
    codes = o.groupby(["pattern", "hour", "sdate", "k"], observed=True, sort=False).ngroup().to_numpy()
    has = o["inc"].notna().to_numpy()
    idx = np.where(has)[0]
    c = codes[idx]
    src = idx[np.argsort(c, kind="stable")]
    dst = idx[np.lexsort((rng.random(len(idx)), c))]  # same group blocks, random order within each block
    inc = o["inc"].to_numpy()
    inc_s = np.full(len(o), np.nan)
    inc_s[dst] = inc[src]
    o["inc_s"] = inc_s
    start = o.groupby("pair")["h"].transform("first")
    o["h_s"] = start + o.groupby("pair")["inc_s"].cumsum().fillna(0)
    run_break = (~has) & (o.groupby("pair").cumcount().to_numpy() > 0)
    o.loc[run_break, "h_s"] = np.nan  # a missing stop breaks the path, as in the observed differences
    o["r"] = o["h_s"] / o["H"]
    o["status"] = 1
    return o


def q1(ps: pd.DataFrame, rng) -> dict:
    d = transitions(ps)
    num, den = gamma_parts(d, iv=True)
    g, g95, g90 = boot_ratio(num, den, rng)
    res = {"gamma_iv": g, "ci95": g95, "ci90": g90, "label": label_gamma(g95, g90),
           "transitions": int(d["v2"].notna().sum()), "pairs": int(d["pair"].nunique()),
           "dates": int(d["date_id"].nunique())}
    weeks = d.drop_duplicates("date_id").set_index("date_id")["week"].reindex(range(len(num))).to_numpy()
    _, w95, _ = boot_ratio(num, den, rng, blocks=np.nan_to_num(weeks, nan=-1).astype(int))
    res["week_clustered_ci95"] = w95
    on, od_ = gamma_parts(d, iv=False)
    res["gamma_ols"] = round(float(on.sum() / od_.sum()), 4)
    g0 = []
    for _ in range(SHUFFLES):
        s = transitions(shuffled(ps, rng))
        sn, sd = gamma_parts(s, iv=False)
        g0.append(sn.sum() / sd.sum())
    res["gamma0_shuffle"] = round(float(np.mean(g0)), 4)
    res["gamma_minus_gamma0_registered"] = round(res["gamma_ols"] - res["gamma0_shuffle"], 4)
    return res


def q1_variants(ps: pd.DataFrame, rng, timing: set) -> dict:
    out = {}
    first_swap = ps[ps["r"] < 0].groupby("pair")["k"].min()
    cut = ps[ps["k"] <= ps["pair"].map(first_swap).fillna(np.inf)]
    out["cut_at_first_swap"] = gamma_point(cut)
    span = ps.groupby("pair")["status"].agg(lambda s: (s == 1).mean())
    out["balanced_80pct"] = gamma_point(ps[ps["pair"].map(span) >= 0.8])
    out["without_timing_points"] = gamma_point(ps[~ps["stop_id"].isin(timing)])
    d = transitions(ps)
    dd = d[d["v2"].notna()].reset_index(drop=True)
    num, den = gamma_parts(dd, iv=True, weight=dd["H"].to_numpy())
    out["weighted_by_H"] = round(float(num.sum() / den.sum()), 4)
    dep = ps.assign(r=np.where(ps["h_dep"].notna(), ps["h_dep"] / ps["H"], np.nan))
    out["departures"] = gamma_point(dep)
    return out


def gamma_point(ps: pd.DataFrame) -> float | None:
    d = transitions(ps)
    if d["v2"].notna().sum() < 1000:
        return None
    num, den = gamma_parts(d, iv=True)
    return round(float(num.sum() / den.sum()), 4)


# ---------------------------------------------------------------- Q2

def events(ps: pd.DataFrame, bunch: float = BUNCH, eligible: float = ELIGIBLE, reverse: bool = False) -> pd.DataFrame:
    """Eligible transitions into each pair-stop and whether a birth (or death) happened there."""
    d = transitions(ps)
    if reverse:  # births from k + 1 to k: the state downstream is the "before"
        t = ps[["pair", "k", "r"]].rename(columns={"r": "nxt"}).assign(k=lambda x: x["k"] - 1)
        d = ps.merge(t, on=["pair", "k"])
        d = d[d["r"].notna() & d["nxt"].notna()].rename(columns={"r": "v", "nxt": "v1"})
    d["eligible"] = d["v1"] >= eligible
    d["birth"] = d["eligible"] & (d["v"] >= 0) & (d["v"] < bunch)
    d["death"] = (d["v1"] >= 0) & (d["v1"] < bunch) & (d["v"] >= ELIGIBLE)
    d["swap_tr"] = d["eligible"] & (d["v"] < 0)
    return d


def platform_matrix(d: pd.DataFrame, key: str, n_dates: int, event: str = "birth", denom: str = "eligible"):
    plat = pd.factorize(d[key])[0]
    keys = pd.factorize(d[key])[1]
    shape = (plat.max() + 1, n_dates)
    E = np.zeros(shape)
    B = np.zeros(shape)
    np.add.at(E, (plat, d["date_id"].to_numpy()), d[denom].to_numpy().astype(float))
    np.add.at(B, (plat, d["date_id"].to_numpy()), d[event].to_numpy().astype(float))
    return keys, E, B


def top_share(rate_rank: np.ndarray, births_eval: np.ndarray) -> float:
    k = max(1, math.ceil(0.10 * len(rate_rank)))
    top = np.argsort(-rate_rank, kind="stable")[:k]
    tot = births_eval.sum()
    return float(births_eval[top].sum() / tot) if tot > 0 else float("nan")


def crossfit(Eo, Bo, Ee, Be) -> float:
    with np.errstate(invalid="ignore", divide="ignore"):
        ro, re = np.nan_to_num(Bo / Eo, nan=-1), np.nan_to_num(Be / Ee, nan=-1)
    return 0.5 * (top_share(ro, Be) + top_share(re, Bo))


def s_ratio(E: np.ndarray, B: np.ndarray, odd: np.ndarray, w: np.ndarray, rng, nulls: int) -> tuple[float, float, float]:
    Eo, Ee = (E[:, odd] * w[odd]).sum(1), (E[:, ~odd] * w[~odd]).sum(1)
    Bo, Be = (B[:, odd] * w[odd]).sum(1), (B[:, ~odd] * w[~odd]).sum(1)
    sb = crossfit(Eo, Bo, Ee, Be)
    s0 = []
    for _ in range(nulls):
        no = rng.multinomial(int(round(Bo.sum())), Eo / Eo.sum()) if Eo.sum() else Bo * 0
        ne = rng.multinomial(int(round(Be.sum())), Ee / Ee.sum()) if Ee.sum() else Be * 0
        s0.append(crossfit(Eo, no, Ee, ne))
    sb0 = float(np.mean(s0))
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = spearmanr(Bo / Eo, Be / Ee).statistic
    return sb, sb0, float(rho)


FLOOR, FLOOR_LOW, MIN_PLATFORMS = 2000, 1000, 50


def min_exposure(E: np.ndarray) -> tuple[np.ndarray, int]:
    tot = E.sum(1)
    floor = FLOOR if (tot >= FLOOR).sum() >= MIN_PLATFORMS else FLOOR_LOW
    return tot >= floor, floor


def q2(d: pd.DataFrame, n_dates: int, odd: np.ndarray, rng, event: str = "birth", reps: int = REPS) -> dict:
    keys, E, B = platform_matrix(d, "stop_id", n_dates, event)
    keep, floor = min_exposure(E)
    E, B, keys = E[keep], B[keep], keys[keep]
    ones = np.ones(n_dates)
    sb, sb0, rho = s_ratio(E, B, odd, ones, rng, NULL_POINT)
    draws = []
    for _ in range(reps):
        w = np.bincount(rng.integers(0, n_dates, n_dates), minlength=n_dates).astype(float)
        a, b, r = s_ratio(E, B, odd, w, rng, NULL_DRAW)
        draws.append((a / b if b else np.nan, a - b, r))
    draws = np.array(draws) if draws else np.full((1, 3), np.nan)
    res = {"platforms": int(len(keys)), "exposure_floor": floor, "S_b": round(sb, 4), "S_b0": round(sb0, 4),
           "ratio": round(sb / sb0, 4), "ratio_ci95": q(draws[:, 0], 0.95), "ratio_ci90": q(draws[:, 0], 0.90),
           "difference": round(sb - sb0, 4), "difference_ci95": q(draws[:, 1], 0.95),
           "rho_split_half": round(rho, 4), "rho_ci95": q(draws[:, 2], 0.95), "rho_ci90": q(draws[:, 2], 0.90),
           "births": int(B.sum()), "eligible": int(E.sum())}
    res["ratio_label"] = ("supported" if res["ratio_ci95"][0] > 1.25 else
                          "not supported" if res["ratio_ci95"][1] < 1.25 else "inconclusive")
    res["rho_label"] = ("supported" if res["rho_ci95"][0] >= 0.50 else
                        "not supported" if res["rho_ci95"][1] < 0.30 else "inconclusive")
    rates = B.sum(1) / E.sum(1)
    res["_rates"] = dict(zip(keys, rates.round(5)))
    res["_exposure"] = dict(zip(keys, E.sum(1).astype(int)))
    return res


# ---------------------------------------------------------------- Q3

def segment_gain_sd(dates: pd.Series) -> pd.DataFrame:
    """Per tram segment × date: n, Σg, Σg² of part 1's gain (delay_to − delay_from, |g| ≤ 600 s, screened)."""
    import duckdb
    late = ROOT / "tools/data/late/segments.parquet"
    keep = pd.read_parquet(late, columns=["mode", "seg_from", "seg_to"]).query("mode == 'tram'").drop_duplicates()
    s = json.loads((ROOT / "docs/research/rain-delays-screen.json").read_text())
    closed = pd.DataFrame([(ln, d) for ln, ds in s["exclusions"].get("tram", {}).items() for d in ds],
                          columns=["route", "date_s"])
    feed = json.loads((ROOT / "docs/research/rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"]
    con = duckdb.connect(str(ROOT / "tools/data/rain/prague_transit.duckdb"), read_only=True)
    for st in ("threads = 2", "memory_limit = '4GB'"):
        con.execute(f"SET {st}")
    con.register("closed", closed)
    con.register("keep", keep)
    con.register("feed", pd.DataFrame({"date_s": feed}))
    parts = []
    for m in range(3, 10):
        parts.append(con.execute(f"""
            WITH c AS (SELECT string_split(rt_trip_id, '_')[2] AS route, stop_name AS seg_from,
                              next_stop_name AS seg_to, delay_to - delay_from AS g,
                              CAST(timezone('Europe/Prague', current_stop_arrival) AS DATE) AS d
                       FROM prague_cascade WHERE route_type = 'tramvaj' AND year = 2025 AND month = {m})
            SELECT seg_from, seg_to, d AS sdate, count(*) AS n, sum(g) AS sg, sum(g * g) AS sg2
            FROM c JOIN keep USING (seg_from, seg_to)
            WHERE g IS NOT NULL AND abs(g) <= 600 AND d BETWEEN DATE '2025-03-15' AND DATE '2025-09-08'
              AND CAST(d AS VARCHAR) NOT IN (SELECT date_s FROM feed)
              AND NOT EXISTS (SELECT 1 FROM closed WHERE closed.route = c.route AND closed.date_s = CAST(d AS VARCHAR))
            GROUP BY ALL""").df())
    out = pd.concat(parts)
    out["sdate"] = pd.to_datetime(out["sdate"])
    return out[out["sdate"].isin(dates)]


def q3(d: pd.DataFrame, ps: pd.DataFrame, rng) -> dict:
    dates = ps.drop_duplicates("date_id").set_index("sdate")["date_id"]
    n_dates = len(dates)
    seg = segment_gain_sd(pd.Series(dates.index))
    seg["date_id"] = seg["sdate"].map(dates)
    d = d.assign(segkey=d["prev_name"].astype(str) + " → " + d["stop_name"].astype(str))
    keys, E, B = platform_matrix(d, "segkey", n_dates)
    seg["segkey"] = seg["seg_from"] + " → " + seg["seg_to"]
    idx = {k: i for i, k in enumerate(keys)}
    seg = seg[seg["segkey"].isin(idx)]
    N, S1, S2 = (np.zeros((len(keys), n_dates)) for _ in range(3))
    for arr, col in ((N, "n"), (S1, "sg"), (S2, "sg2")):
        np.add.at(arr, (seg["segkey"].map(idx).to_numpy(), seg["date_id"].to_numpy()), seg[col].to_numpy(float))
    keep = (E.sum(1) >= 500) & (N.sum(1) > 1)
    E, B, N, S1, S2 = E[keep], B[keep], N[keep], S1[keep], S2[keep]

    def stat(w):
        n, s1, s2 = (N * w).sum(1), (S1 * w).sum(1), (S2 * w).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            sd = np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 0))
            rate = (B * w).sum(1) / (E * w).sum(1)
            mean = s1 / n
        return spearmanr(rate, sd, nan_policy="omit").statistic, spearmanr(rate, mean, nan_policy="omit").statistic

    est, est_mean = stat(np.ones(n_dates))
    draws = np.array([stat(np.bincount(rng.integers(0, n_dates, n_dates), minlength=n_dates).astype(float))
                      for _ in range(REPS)])
    c95, c90 = q(draws[:, 0], 0.95), q(draws[:, 0], 0.90)
    lab = "supported" if c95[0] > 0 else "not supported" if (-0.10 < c90[0] and c90[1] < 0.10) else "inconclusive"
    return {"segments": int(keep.sum()), "rho_b": round(float(est), 4), "ci95": c95, "ci90": c90, "label": lab,
            "ci95_width": round(c95[1] - c95[0], 4), "rho_with_mean_gain": round(float(est_mean), 4)}


# ---------------------------------------------------------------- Q4 and checks

def shares(ps: pd.DataFrame, by: str, bunch: float = BUNCH, gap: float = GAP) -> dict:
    o = ps[ps["r"].notna()]
    g = o.groupby(by)["r"]
    return {str(k): {"bunched": round(float(((v >= 0) & (v < bunch)).mean()), 4),
                     "gap": round(float((v > gap).mean()), 4), "swap": round(float((v < 0).mean()), 4),
                     "var_r": round(float(v.var()), 4), "n": int(len(v))} for k, v in g}


def decile(ps: pd.DataFrame) -> pd.Series:
    inner = (ps["L"] - 2).clip(lower=1)
    return (np.floor(10 * ps["k"] / inner) + 1).clip(upper=10).astype(int)


def q4(ps: pd.DataFrame, rng) -> dict:
    ps = ps.assign(decile=decile(ps), daytype=np.where(ps["weekday"] >= 5, "weekend", "weekday"))
    sh = shuffled(ps, rng).merge(ps[["pair", "k", "L"]], on=["pair", "k"])
    sh = sh.assign(decile=decile(sh))
    return {"by_decile": shares(ps, "decile"), "by_decile_shuffled": shares(sh, "decile"),
            "by_hour_weekday": shares(ps[ps["daytype"] == "weekday"], "hour"),
            "by_hour_weekend": shares(ps[ps["daytype"] == "weekend"], "hour"),
            "overall": shares(ps.assign(all=1), "all")["1"]}


def checks(ps: pd.DataFrame, n_dates: int, odd: np.ndarray, rng, timing: set, reps: int) -> dict:
    out = {}
    for name, b in (("bunched_below_0.20", 0.20), ("bunched_below_0.33", 0.33)):
        out[name] = q2_short(events(ps, bunch=b), n_dates, odd, rng, reps)
    out["bunched_below_0.5_gap_above_1.5_shares"] = shares(ps.assign(all=1), "all", bunch=0.5, gap=1.5)["1"]
    out["bunched_below_0.5_births_prev_0.75"] = q2_short(events(ps, bunch=0.5, eligible=0.75), n_dates, odd, rng, reps)
    out["alternative_birth_rule_prev_0.75"] = q2_short(events(ps, eligible=0.75), n_dates, odd, rng, reps)
    ev = events(ps)
    out["deaths"] = q2_short(ev, n_dates, odd, rng, reps, event="death")
    ev["net"] = ev["birth"].astype(int) - ev["death"].astype(int)
    out["net_births_total"] = int(ev["net"].sum())
    rev = events(ps, reverse=True)
    out["reversed_order"] = q2_short(rev, n_dates, odd, rng, reps)
    fwd = q2(ev, n_dates, odd, rng, reps=0)
    bwd = q2(rev, n_dates, odd, rng, reps=0)
    common = sorted(set(fwd["_rates"]) & set(bwd["_rates"]))
    out["reversed_vs_forward_rank_correlation"] = round(float(spearmanr(
        [fwd["_rates"][k] for k in common], [bwd["_rates"][k] for k in common]).statistic), 4)
    out["without_timing_points"] = q2_short(ev[~ev["stop_id"].isin(timing)], n_dates, odd, rng, reps)
    per_date = ev.groupby("date_id")["birth"].sum()
    worst = set(per_date.sort_values().index[-max(1, len(per_date) // 100):])
    out["without_top_1pct_dates"] = q2_short(ev[~ev["date_id"].isin(worst)], n_dates, odd, rng, reps)
    capped = ev.copy()
    capped["birth"] = capped["birth"] & ~capped.duplicated(["pair", "birth"])  # the first birth of each pair
    out["births_capped_one_per_pair"] = q2_short(capped, n_dates, odd, rng, reps)
    return out


def q2_short(d, n_dates, odd, rng, reps, event="birth") -> dict:
    r = q2(d, n_dates, odd, rng, event=event, reps=reps)
    return {k: v for k, v in r.items() if not k.startswith("_")}


def timing_stops(mode: str) -> set:
    return set(pd.read_parquet(DATA / f"timing_{mode}.parquet")["stop_id"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["tram", "bus"], default="tram")
    ap.add_argument("--check-reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    allp = load(a.mode)
    ps = allp[allp["H0"] >= H_MIN].reset_index(drop=True)
    low = allp[allp["H0"] < H_MIN].reset_index(drop=True)
    timing = timing_stops(a.mode)
    dates = ps.drop_duplicates("date_id").sort_values("date_id")
    n_dates = int(ps["date_id"].max() + 1)
    odd = np.zeros(n_dates, bool)
    odd[dates["date_id"].to_numpy()] = (dates["week"] % 2 == 1).to_numpy()
    log.info("Q1")
    res = {"mode": a.mode, "pairs": int(ps["pair"].nunique()), "pair_stops_observed": int(ps["r"].notna().sum()),
           "Q1": q1(ps, rng)}
    res["Q1_variants"] = q1_variants(ps, rng, timing)
    log.info("Q2")
    ev = events(ps)
    q2full = q2(ev, n_dates, odd, rng)
    rates, expo = q2full.pop("_rates"), q2full.pop("_exposure")
    res["Q2"] = q2full
    res["Q2_difference"] = {"difference": q2full["difference"], "ci95": q2full["difference_ci95"]}
    res["transitions"] = {"births": int(ev["birth"].sum()), "deaths": int(ev["death"].sum()),
                          "swap_transitions": int(ev["swap_tr"].sum()), "eligible": int(ev["eligible"].sum())}
    if a.mode == "tram":
        log.info("Q3")
        res["Q3"] = q3(ev, ps, rng)
    log.info("Q4 and checks")
    res["Q4"] = q4(ps, rng)
    res["checks"] = checks(ps, n_dates, odd, rng, timing, a.check_reps)
    res["checks"]["H_3_4min_stratum"] = {"pairs": int(low["pair"].nunique()),
                                         "gamma_iv": gamma_point(low) if len(low) else None,
                                         "shares": shares(low.assign(all=1), "all")["1"] if len(low) else None}
    tt = prepare(pd.concat([pd.read_parquet(f) for f in sorted(DATA.glob(f"pairs_tt_{a.mode}_*.parquet"))]))
    tt = tt[tt["H0"] >= H_MIN]
    tt_r = tt["r"].dropna()
    res["checks"]["timetable_order_pairs"] = {"bunched_incl_swaps": round(float((tt_r < BUNCH).mean()), 4),
                                              "gap": round(float((tt_r > GAP).mean()), 4), "n": int(len(tt_r))}
    suffix = "" if a.mode == "tram" else f"-{a.mode}"
    (ROOT / f"docs/research/bunching-results{suffix}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    out = ROOT / "tools/data/bunch"
    pd.DataFrame({"stop_id": list(rates), "rate": list(rates.values()),
                  "exposure": [expo[k] for k in rates]}).to_parquet(out / f"platform_rates_{a.mode}.parquet", index=False)
    print(json.dumps({k: res[k] for k in ("Q1", "Q2")}, indent=1))


if __name__ == "__main__":
    main()
