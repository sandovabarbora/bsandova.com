"""Estimates of the transfers design (§2 Q1–Q2, §5–§7) from the screened connection tables.

Every connection reduces to two numbers: A's arrival delay at the hub, d_A = observed − scheduled arrival, and B's
departure lateness δ_B = dep_hat − scheduled departure (≥ 0, since dep_hat is the later of B's observed arrival and its
scheduled departure). The planned B is caught when δ_B ≥ d_A + m − s, with m the walking margin and s the planned
slack. Q1 sets d_A against the δ of other B trips of the same line on the same day (p_within); Q1b against the δ of
the same scheduled B trip on other days (p_day).

Writes docs/research/transfers-results.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow python tools/transfer/estimate.py
"""
from __future__ import annotations

import importlib.util
import json
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/transfer"
R = ROOT / "docs/research"
OUT = R / "transfers-results.json"
REPS, CHECK_REPS, SEED = 999, 199, 20261008
WITHIN_S, DONOR_K = 3600, 40
KEY = 10**10  # > any epoch second in 2025, so line × day and time sort as one number
COSTLY_S, CENSOR_S = 300, 1800
LINE, BAND = 0.01, 0.01
SUMMER = (date(2025, 6, 28), date(2025, 8, 31))
log = logging.getLogger("transfer.estimate")

_spec = importlib.util.spec_from_file_location("transfer_screen", Path(__file__).with_name("screen.py"))
screen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(screen)


def label(ci95: tuple[float, float], ci90: tuple[float, float]) -> str:
    """§6 in the rule's literal order: supported, then not supported, then inconclusive.

    An interval wholly below 0 that also lies within ±1 point is therefore "not supported" (as good as independent),
    with its sign reported beside the label; one wholly below 0 that reaches past −1 point is "inconclusive"."""
    if ci95[0] > LINE:
        return "supported"
    if -BAND < ci90[0] and ci90[1] < BAND:
        return "not supported"
    return "inconclusive"


TEXT = ["hub", "akey", "bkey", "aroute", "broute"]
DROP = ["b_oa", "dist_m"]


def read_connections(path: Path, excluded: bool) -> pd.DataFrame:
    """One month's kept connections (all slacks), or its flagged returns and same-trunk pairs at slack 2–4 min only,
    which only the check without the exclusions (§7) reads; text columns as categories."""
    filters = ([("excluded", "==", True), ("slack", ">=", 120), ("slack", "<=", 240)] if excluded
               else [("excluded", "==", False)])
    t = pq.read_table(path, filters=filters, read_dictionary=TEXT)  # strings arrive as categories, not objects
    return t.drop_columns([x for x in DROP if x in t.column_names]).to_pandas()


def months() -> list[tuple[Path, Path]]:
    return [(f, f.with_name(f.name.replace("connections", "btrips"))) for f in sorted(DATA.glob("connections_*.parquet"))]


def prepare(c: pd.DataFrame, removed_hubs: set[str]) -> pd.DataFrame:
    c = c[c["a_oa"].notna()].copy()  # §4.4: connections with an unobserved A arrival are removed
    c["date"] = pd.to_datetime(c["date"]).dt.date
    c["d_a"] = c["a_oa"] - c["a_sa"]
    c["delta_b"] = c["b_dep_hat"] - c["b_sd"]
    c["b_observed"] = c["delta_b"].notna()
    midnight = pd.to_datetime(c["date"]).astype("int64") // 10**9
    c["hour"] = pd.to_datetime(c["a_sa"], unit="s", utc=True).dt.tz_convert("Europe/Prague").dt.hour
    c["week"] = pd.to_datetime(c["date"]).dt.isocalendar().week.to_numpy().astype(np.int16)
    c["tod_a"] = (c["a_sa"] - midnight) % 86400
    c["tod_b"] = (c["b_sd"] - midnight) % 86400
    days = pd.Series(c["date"].unique())
    dtype_of = dict(zip(days, days.map(screen.day_type)))
    c["daytype"] = c["date"].map(dtype_of).astype("category")
    h = c["hour"]
    c["band"] = np.select([(h >= 20) | (h < 5), c["daytype"] != "weekday", h.isin([7, 8, 15, 16, 17])],
                          ["evening", "weekend", "peak"], "daytime")
    c["band"] = c["band"].astype("category")  # the same bands as screen.hour_band, vectorised
    c["q1_hub"] = ~c["hub"].isin(removed_hubs)
    return score(c)


def score(c: pd.DataFrame, a_shift: float = 0.0, b_shift: float = 0.0, delta: str = "delta_b") -> pd.DataFrame:
    c = c.copy()
    c["req"] = c["d_a"] + a_shift + c["m"] - c["slack"]
    d = c[delta] + b_shift
    c["made"] = (d >= c["req"]).astype(float).where(d.notna())
    return c


def b_table(b: pd.DataFrame) -> pd.DataFrame:
    b = b.copy()
    b["date"] = pd.to_datetime(b["date"]).dt.date
    b["delta_b"] = b["dep_hat"] - b["sd"]
    b["delta_od"] = (b["od"] - b["sd"]).where(~b["starts_here"])
    return b.sort_values(["date", "hub", "bkey", "sd"]).reset_index(drop=True)


def group_index(b: pd.DataFrame) -> tuple[np.ndarray, dict]:
    gid = b.groupby(["date", "hub", "bkey"], sort=False, observed=True).ngroup().to_numpy()
    starts = np.r_[0, np.flatnonzero(np.diff(gid)) + 1]
    keys = list(zip(b["date"].to_numpy()[starts], b["hub"].to_numpy()[starts], b["bkey"].to_numpy()[starts]))
    return gid, dict(zip(keys, starts))


def within_donors(c: pd.DataFrame, b: pd.DataFrame, b_shift: float = 0.0, delta: str = "delta_b") -> tuple:
    """Same-day donors (§2 Q1): the other B trips of the line within ±60 min of the planned B, the planned B and the
    trips directly before and after it excluded. Returns made-count and count per connection, computed exactly."""
    gid, start = group_index(b)
    sd = b["sd"].to_numpy()
    dl = b[delta].to_numpy() + b_shift
    p = np.array([start[k] for k in zip(c["date"], c["hub"], c["bkey"])]) + c["b_idx"].to_numpy()
    req = c["req"].to_numpy()
    made, n = np.zeros(len(c)), np.zeros(len(c))
    for o in range(-DONOR_K, DONOR_K + 1):
        if o in (-1, 0, 1):
            continue
        q = np.clip(p + o, 0, len(b) - 1)
        ok = (p + o >= 0) & (p + o < len(b)) & (gid[q] == gid[p]) & (np.abs(sd[q] - sd[p]) <= WITHIN_S)
        ok &= ~np.isnan(dl[q])
        n += ok
        made += ok & (dl[q] >= req)
    return made, n


def extra_wait(c: pd.DataFrame, b: pd.DataFrame) -> np.ndarray:
    """w = dep_hat of the first catchable B of the line − scheduled departure of the planned B, censored at 30 min."""
    obs = b[b["dep_hat"].notna()].copy()
    gid_of = {k: i for i, k in enumerate(obs.groupby(["date", "hub", "bkey"], sort=False, observed=True).groups)}
    og = np.array([gid_of[k] for k in zip(obs["date"], obs["hub"], obs["bkey"])], dtype=np.int64)
    # one sorted key for every (line, day, departure): a single searchsorted finds each connection's first catchable B
    key = og * KEY + obs["dep_hat"].to_numpy()
    order = np.argsort(key)
    key, og = key[order], og[order]
    dh = obs["dep_hat"].to_numpy()[order]
    cg = np.array([gid_of.get(k, -1) for k in zip(c["date"], c["hub"], c["bkey"])], dtype=np.int64)
    j = np.searchsorted(key, cg * KEY + (c["a_oa"] + c["m"]).to_numpy(), side="left")
    jj = np.minimum(j, len(key) - 1)
    found = (cg >= 0) & (j < len(key)) & (og[jj] == cg)
    w = np.where(found, dh[jj] - c["b_sd"].to_numpy(), CENSOR_S)
    return np.minimum(w, CENSOR_S)


def signature(c: pd.DataFrame, b: pd.DataFrame) -> np.ndarray:
    """Timetable period of a line pair on a date (§2 Q1b): the set of A arrival and B departure times there."""
    a_sig = c.groupby(["hub", "akey", "bkey", "date"], observed=True)["tod_a"].agg(lambda s: hash(tuple(sorted(set(s)))))
    midnight = pd.to_datetime(b["date"]).astype("int64") // 10**9
    b_sig = b.assign(tod=(b["sd"] - midnight) % 86400).groupby(["hub", "bkey", "date"], observed=True)["tod"].agg(
        lambda s: hash(tuple(sorted(set(s)))))
    sa = a_sig.reindex(pd.MultiIndex.from_frame(c[["hub", "akey", "bkey", "date"]])).to_numpy()
    sb = b_sig.reindex(pd.MultiIndex.from_frame(c[["hub", "bkey", "date"]])).to_numpy()
    return np.array([hash((x, y)) for x, y in zip(sa, sb)])


def day_donors(c: pd.DataFrame, weeks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Other-day donors (§2 Q1b) per connection and donor ISO week: made-count and count; ±1 day never a donor.

    Counts are small (one donor date per week at most for a given weekday type), so they are stored as uint8."""
    wi = {w: i for i, w in enumerate(weeks)}
    S = np.zeros((len(c), len(weeks)), dtype=np.uint8)
    N = np.zeros((len(c), len(weeks)), dtype=np.uint8)
    ordinal = np.array([d.toordinal() for d in c["date"]])
    wk = np.array([wi[w] for w in c["week"]])
    dl, rq = c["delta_b"].to_numpy(), c["req"].to_numpy()
    for idx in c.groupby(["hub", "akey", "bkey", "daytype", "sig", "tod_a", "tod_b"], sort=False, observed=True).indices.values():
        if len(idx) < 2:
            continue
        donor = (np.abs(ordinal[idx][:, None] - ordinal[idx][None, :]) > 1) & ~np.isnan(dl[idx])[None, :]
        hit = donor & (dl[idx][None, :] >= rq[idx][:, None])
        onehot = np.zeros((len(idx), len(weeks)), dtype=np.uint8)
        onehot[np.arange(len(idx)), wk[idx]] = 1
        N[idx] += (donor.astype(np.uint8) @ onehot).astype(np.uint8)
        S[idx] += (hit.astype(np.uint8) @ onehot).astype(np.uint8)
    return S, N


def draws(n_weeks: int, reps: int, rng) -> np.ndarray:
    return np.vstack([np.ones(n_weeks)] + [rng.multinomial(n_weeks, np.full(n_weeks, 1 / n_weeks)).astype(float)
                                           for _ in range(reps)])


def interval(values: np.ndarray) -> dict:
    est, d = values[0], values[1:]
    ci95 = tuple(float(x) for x in np.nanquantile(d, [0.025, 0.975]))
    ci90 = tuple(float(x) for x in np.nanquantile(d, [0.05, 0.95]))
    return {"est": round(float(est), 4), "ci95": [round(x, 4) for x in ci95], "ci90": [round(x, 4) for x in ci90],
            "label": label(ci95, ci90), "wholly_below_zero": ci95[1] < 0}


def within_stat(q: pd.DataFrame, W: np.ndarray, weeks: np.ndarray) -> np.ndarray:
    """Δp_within under each row of week weights W (first row = the data); summed by week first, which is exact."""
    wi = {w: i for i, w in enumerate(weeks)}
    wk = np.array([wi[w] for w in q["week"]])
    diff = q["made"].to_numpy() - (q["within_made"] / q["within_n"]).to_numpy()
    num = np.bincount(wk, weights=diff, minlength=len(weeks))
    den = np.bincount(wk, minlength=len(weeks)).astype(float)
    return (W @ num) / (W @ den)


def day_stat(q: pd.DataFrame, S: np.ndarray, N: np.ndarray, W: np.ndarray, weeks: np.ndarray,
             chunk: int = 50_000) -> np.ndarray:
    """Δp_day under each row of W; donor weeks are re-weighted too, so donors come only from the drawn weeks."""
    wi = {w: i for i, w in enumerate(weeks)}
    wk = np.array([wi[w] for w in q["week"]])
    made = q["made"].to_numpy()
    num, den = np.zeros(len(W)), np.zeros(len(W))
    for a in range(0, len(q), chunk):
        sl = slice(a, a + chunk)
        ns = N[sl].astype(np.float32) @ W.T.astype(np.float32)  # rows × draws
        ss = S[sl].astype(np.float32) @ W.T.astype(np.float32)
        ok = ns > 0
        pday = np.divide(ss, ns, out=np.zeros_like(ss), where=ok)
        wt = W[:, wk[sl]].T * ok
        num += np.sum(wt * (made[sl][:, None] - pday), axis=0)
        den += np.sum(wt, axis=0)
    return num / den


def q1_frame(c: pd.DataFrame, b: pd.DataFrame, b_shift: float = 0.0, delta: str = "delta_b",
             keep_excluded: bool = False) -> pd.DataFrame:
    q = c[c["slack"].between(120, 240) & c["q1_hub"] & (keep_excluded | ~c["excluded"])].copy()
    q["within_made"], q["within_n"] = within_donors(q, b, b_shift, delta)
    return q[(q["within_n"] > 0) & q["made"].notna()]


def uncertain(q: pd.DataFrame, short: set) -> np.ndarray:
    """§4.4: planned B unobserved, or its line one trip short in that hour (possibly cancelled)."""
    hb = pd.to_datetime(q["b_sd"], unit="s", utc=True).dt.tz_convert("Europe/Prague").dt.hour
    return (~q["b_observed"]).to_numpy() | np.array([k in short for k in zip(
        q["hub"].astype(str), q["broute"].astype(str), q["date"], hb)])


def replan(c: pd.DataFrame, b: pd.DataFrame, m_new: np.ndarray) -> pd.DataFrame:
    """Planned B again under another walking margin (§7 margins): first B departing at least m after A's arrival."""
    gid, start = group_index(b)
    key = gid.astype(np.int64) * KEY + b["sd"].to_numpy()
    cg = np.array([gid[start[k]] for k in zip(c["date"], c["hub"], c["bkey"])], dtype=np.int64)
    j = np.searchsorted(key, cg * KEY + c["a_sa"].to_numpy() + m_new, side="left")
    jj = np.minimum(j, len(key) - 1)
    ok = (j < len(key)) & (gid[jj] == cg)
    out = c.assign(m=m_new, b_idx=jj - np.array([start[k] for k in zip(c["date"], c["hub"], c["bkey"])]),
                   b_sd=b["sd"].to_numpy()[jj], delta_b=b["delta_b"].to_numpy()[jj])[ok]
    out["slack"] = out["b_sd"] - out["a_sa"]
    return score(out)


SMALL = ["date", "week", "hub", "aroute", "broute", "band", "made", "within_made", "within_n"]


def month_checks(c: pd.DataFrame, b: pd.DataFrame, ex: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The §7 variants for one month, each reduced to the columns the week bootstrap needs."""
    small = lambda q: q[SMALL]  # noqa: E731
    cq = c[c["slack"].between(120, 240) & c["q1_hub"]]
    out = {"observed_departures": small(q1_frame(score(cq, delta="delta_od_c"), b, delta="delta_od"))}
    for name, kw in (("a_plus_30s", {"a_shift": 30}), ("a_minus_30s", {"a_shift": -30}),
                     ("b_plus_30s", {"b_shift": 30}), ("b_minus_30s", {"b_shift": -30})):
        out[f"timing_{name}"] = small(q1_frame(score(cq, **kw), b, b_shift=kw.get("b_shift", 0.0)))
    for name, f in (("m_minus_30s", lambda m: m - 30), ("m_plus_30s", lambda m: m + 30),
                    ("m_fixed_2min", lambda m: np.full_like(m, 120.0))):
        out[f"margin_{name}"] = small(q1_frame(replan(c, b, f(c["m"].to_numpy())), b))
    both = pd.concat([cq, ex], ignore_index=True) if len(ex) else cq
    out["without_exclusions"] = small(q1_frame(both, b, keep_excluded=True))
    return out


def summarise_checks(q: pd.DataFrame, var: dict[str, pd.DataFrame], weeks: np.ndarray, rng) -> dict:
    W = draws(len(weeks), CHECK_REPS, rng)

    def run(x: pd.DataFrame) -> dict:
        return interval(within_stat(x, W, weeks)) if len(x) else {"est": None, "note": "no connections"}

    out = {k: run(v) for k, v in var.items()}
    out["peaks_only"] = run(q[q["band"] == "peak"])
    summer = q["date"].map(lambda d: SUMMER[0] <= d <= SUMMER[1]).astype(bool)
    out["school_holidays"] = run(q[summer])
    out["term_time"] = run(q[~summer])
    out["by_line_pair"] = {f"{h} {a}>{bb}": run(g) for (h, a, bb), g in
                           q.groupby(["hub", "aroute", "broute"], observed=True) if len(g) >= 500}
    out["by_hub"] = {h: run(g) for h, g in q.groupby("hub", observed=True) if len(g) >= 500}
    out["hub_and_week_resampling"] = hub_week(q, weeks, rng)
    out["hub_definition_by_stop_name"] = ("identical to the primary: tram platforms have no parent station in the "
                                          "PID GTFS, so hubs are already keyed by stop name")
    return out


def hub_week(q: pd.DataFrame, weeks: np.ndarray, rng) -> dict:
    """§5 check: hubs resampled as well as weeks."""
    hubs = np.array(sorted(q["hub"].unique()))
    hi = {h: i for i, h in enumerate(hubs)}
    wi = {w: i for i, w in enumerate(weeks)}
    hk, wk = np.array([hi[h] for h in q["hub"]]), np.array([wi[w] for w in q["week"]])
    diff = q["made"].to_numpy() - (q["within_made"] / q["within_n"]).to_numpy()
    vals = []
    for r in range(CHECK_REPS + 1):
        ch = np.ones(len(hubs)) if r == 0 else rng.multinomial(len(hubs), np.full(len(hubs), 1 / len(hubs)))
        cw = np.ones(len(weeks)) if r == 0 else rng.multinomial(len(weeks), np.full(len(weeks), 1 / len(weeks)))
        wt = ch[hk] * cw[wk]
        vals.append(np.sum(wt * diff) / np.sum(wt))
    return interval(np.array(vals))


def cost(c: pd.DataFrame) -> dict:
    """Q2: for slack 2, 3 and 4 min, the share made, the share of costly misses and the median extra wait."""
    g0 = c[c["made"].notna() & ~c["excluded"]]
    out = {}
    for s in (2, 3, 4):
        g = g0[(g0["slack"] >= 60 * s) & (g0["slack"] < 60 * (s + 1))]
        if g.empty:
            continue
        rec = {"connections": int(len(g)), "made": round(float(g["made"].mean()), 4),
               "costly_miss": round(float((g["w"] > COSTLY_S).mean()), 4),
               "median_extra_wait_s": float(np.median(g["w"])),
               "censored_share": round(float((g["w"] >= CENSOR_S).mean()), 4)}
        rec["by_band"] = {k: {"connections": int(len(x)), "made": round(float(x["made"].mean()), 4),
                              "costly_miss": round(float((x["w"] > COSTLY_S).mean()), 4)}
                          for k, x in g.groupby("band", observed=True)}
        rec["by_hub"] = {k: {"connections": int(len(x)), "made": round(float(x["made"].mean()), 4)}
                         for k, x in g.groupby("hub", observed=True)}
        out[str(s)] = rec
    return out


DAY = ["date", "week", "hub", "akey", "bkey", "daytype", "sig", "tod_a", "tod_b", "delta_b", "req", "made",
       "aroute", "broute", "band", "within_made", "within_n"]


STAGE = DATA / "estimate"


def month_stage(fc: Path, fb: Path) -> None:
    """One month's same-day work (donors, checks, bounds, costs), written as small tables for the final stage; run in
    its own process so the memory a month needs is returned to the system before the next."""
    sc = json.loads((R / "transfers-screen.json").read_text())
    removed = set(sc["hubs_removed_early_departures"])
    miss = pd.read_parquet(DATA / "missing.parquet")
    miss = miss[miss["missing"] > 0]
    short = set(zip(miss["stop_name"].astype(str), miss["route"].astype(str), miss["sdate"].dt.date, miss["hour"]))
    tag = fc.stem.split("_")[1]
    b = b_table(pd.read_parquet(fb))
    c = prepare(read_connections(fc, False), removed)
    c["delta_od_c"] = (c["b_od"] - c["b_sd"]).where(~c["b_starts_here"])
    q = q1_frame(c, b)
    q["sig"] = signature(q, b)
    q[DAY].to_parquet(STAGE / f"q_{tag}.parquet", index=False)
    c2 = c[(c["slack"] >= 120) & (c["slack"] < 300)].copy()
    c2["w"] = extra_wait(c2, b)
    c2[["slack", "made", "w", "band", "hub"]].to_parquet(STAGE / f"cost_{tag}.parquet", index=False)
    u = c[c["slack"].between(120, 240) & c["q1_hub"]].copy()
    u["uncertain"] = uncertain(u, short)
    u["within_made"], u["within_n"] = within_donors(u, b)
    u.loc[u["within_n"] > 0, ["week", "made", "uncertain", "within_made", "within_n"]].to_parquet(
        STAGE / f"bound_{tag}.parquet", index=False)
    ex = prepare(read_connections(fc, True), removed)
    ex["delta_od_c"] = np.nan
    for k, v in month_checks(c, b, ex).items():
        v.to_parquet(STAGE / f"var-{k}_{tag}.parquet", index=False)
    log.info("%s: %s Q1 connections", fc.name, len(q))


def stage_table(prefix: str) -> pd.DataFrame:
    return pd.concat([pd.read_parquet(f) for f in sorted(STAGE.glob(f"{prefix}_*.parquet"))], ignore_index=True)


def main() -> None:
    """Month by month, each in its own process (same-day donors, checks and bounds need only their own day), then the
    week bootstrap on the reduced tables; other-day donors (Q1b) need every month and are formed here."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if "--month" in sys.argv:
        fc = Path(sys.argv[sys.argv.index("--month") + 1])
        month_stage(fc, fc.with_name(fc.name.replace("connections", "btrips")))
        return
    STAGE.mkdir(parents=True, exist_ok=True)
    if "--aggregate" not in sys.argv:  # --aggregate reuses the month tables already written
        for fc, _ in months():
            subprocess.run([sys.executable, __file__, "--month", str(fc)], check=True)
    q = stage_table("q")
    for k in ("hub", "akey", "bkey", "aroute", "broute", "band", "daytype"):
        q[k] = q[k].astype(str).astype("category")
    weeks = np.array(sorted(q["week"].unique()))
    rng = np.random.default_rng(SEED)
    S, N = day_donors(q, weeks)
    W = draws(len(weeks), REPS, rng)
    res = {"weeks": int(len(weeks)), "q1_connections": int(len(q)), "q1_dates": int(q["date"].nunique()),
           "q1_hubs": sorted(q["hub"].astype(str).unique()),
           "p_obs": round(float(q["made"].mean()), 4),
           "p_within": round(float((q["within_made"] / q["within_n"]).mean()), 4),
           "q1_within": interval(within_stat(q, W, weeks)),
           "q1b_day": interval(day_stat(q, S, N, W, weeks)),
           "q1b_connections_with_donors": int((N.sum(axis=1) > 0).sum())}
    del S, N
    bd = stage_table("bound")
    Wc = W[: CHECK_REPS + 1]
    res["bounds"] = {"uncertain_share": round(float(bd["uncertain"].mean()), 4)}
    for name, v in (("all_made", 1.0), ("all_missed", 0.0)):
        res["bounds"][name] = interval(within_stat(bd.assign(made=bd["made"].where(~bd["uncertain"], v)), Wc, weeks))
    res["q2_cost"] = cost(stage_table("cost").assign(excluded=False))
    names = sorted({f.stem.rsplit("_", 1)[0][4:] for f in STAGE.glob("var-*_*.parquet")})
    var = {k: stage_table(f"var-{k}").astype({"hub": str, "aroute": str, "broute": str, "band": str}) for k in names}
    res["checks"] = summarise_checks(q.astype({"hub": str, "aroute": str, "broute": str, "band": str}), var, weeks, rng)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps({k: res[k] for k in ("q1_connections", "p_obs", "p_within", "q1_within", "q1b_day")}, indent=1))


if __name__ == "__main__":
    main()
