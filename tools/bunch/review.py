"""Checks added after publication, following the independent review of 8 October 2026 (post hoc, not registered).

- Q2 against a line-stratified exposure null: births reassigned at random to eligible pair-stops within the same
  service pattern (and, as a second version, within the same line), then split, ranked and evaluated by the registered
  cross-fit; bootstrap over dates with fewer draws than the registered one (BOOT draws, NULLS nulls inside each).
  The unstratified null is recomputed by the same code as a check against the registered 2.40.
- γ_IV per tram line (lines with at least 1 000 instrumented transitions), fixed effects within the line.
- Q1's label recomputed from the stored intervals with the corrected label rule of estimate.py, and written back into
  docs/research/bunching-results.json (the version 1 label is kept there as "label_v1"); no estimate is rerun.

Writes docs/research/bunching-review.json.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy --with pandas --with pyarrow --with scipy python tools/bunch/review.py
"""
from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bunch_estimate", Path(__file__).with_name("estimate.py"))
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)
BOOT, NULLS, NULL_POINT = 199, 49, 199
log = logging.getLogger("bunch.review")


def strat_matrices(ev: pd.DataFrame, n_dates: int, stratum: str):
    """Exposure and births per (platform, stratum) × date, on the platforms Q2 ranks; the platform and stratum of each row."""
    _, E, _ = be.platform_matrix(ev, "stop_id", n_dates)
    keys = pd.factorize(ev["stop_id"])[1]
    keep, _ = be.min_exposure(E)
    kept = set(keys[keep])
    e = ev[ev["stop_id"].isin(kept)]
    combo = e["stop_id"].astype(str) + "#" + e[stratum].astype(str)
    cid, ckeys = pd.factorize(combo)
    shape = (len(ckeys), n_dates)
    Ec, Bc = np.zeros(shape), np.zeros(shape)
    np.add.at(Ec, (cid, e["date_id"].to_numpy()), e["eligible"].to_numpy(float))
    np.add.at(Bc, (cid, e["date_id"].to_numpy()), e["birth"].to_numpy(float))
    plat = pd.factorize(pd.Series(ckeys).str.split("#").str[0])[0]
    strat = pd.factorize(pd.Series(ckeys).str.split("#").str[1])[0]
    return Ec, Bc, plat, strat


def null_births(Ec: np.ndarray, Bc: np.ndarray, groups: list[np.ndarray], rng) -> np.ndarray:
    out = np.zeros(len(Ec))
    for g in groups:
        tot = int(round(Bc[g].sum()))
        if tot and Ec[g].sum() > 0:
            out[g] = rng.multinomial(tot, Ec[g] / Ec[g].sum())
    return out


def ratio(Ec, Bc, plat, strat, odd, w, rng, nulls: int) -> tuple[float, float, float]:
    """Cross-fitted share S_b, its mean under the stratified null S_b0, and the share under the plain null."""
    eo, ee = (Ec[:, odd] * w[odd]).sum(1), (Ec[:, ~odd] * w[~odd]).sum(1)
    bo, b_e = (Bc[:, odd] * w[odd]).sum(1), (Bc[:, ~odd] * w[~odd]).sum(1)
    npl = plat.max() + 1
    agg = lambda x: np.bincount(plat, x, npl)  # noqa: E731
    Eo, Ee = agg(eo), agg(ee)
    sb = be.crossfit(Eo, agg(bo), Ee, agg(b_e))
    groups = [np.where(strat == s)[0] for s in range(strat.max() + 1)]
    everything = [np.arange(len(Ec))]
    s_strat, s_plain = [], []
    for _ in range(nulls):
        s_strat.append(be.crossfit(Eo, agg(null_births(eo, bo, groups, rng)), Ee, agg(null_births(ee, b_e, groups, rng))))
        s_plain.append(be.crossfit(Eo, agg(null_births(eo, bo, everything, rng)), Ee,
                                   agg(null_births(ee, b_e, everything, rng))))
    return sb, float(np.mean(s_strat)), float(np.mean(s_plain))


def q2_stratified(ev: pd.DataFrame, n_dates: int, odd: np.ndarray, stratum: str, rng) -> dict:
    Ec, Bc, plat, strat = strat_matrices(ev, n_dates, stratum)
    sb, s0, s_plain = ratio(Ec, Bc, plat, strat, odd, np.ones(n_dates), rng, NULL_POINT)
    draws = []
    for i in range(BOOT):
        w = np.bincount(rng.integers(0, n_dates, n_dates), minlength=n_dates).astype(float)
        a, b, c = ratio(Ec, Bc, plat, strat, odd, w, rng, NULLS)
        draws.append((a / b if b else np.nan, a / c if c else np.nan))
        if i % 20 == 0:
            log.info("%s draw %d", stratum, i)
    draws = np.array(draws)
    return {"stratum": stratum, "strata": int(strat.max() + 1), "platforms": int(plat.max() + 1),
            "births": int(Bc.sum()), "S_b": round(sb, 4), "S_b0_stratified": round(s0, 4),
            "ratio": round(sb / s0, 4), "ratio_ci95": be.q(draws[:, 0], 0.95),
            "plain_null_same_code": {"S_b0": round(s_plain, 4), "ratio": round(sb / s_plain, 4),
                                     "ratio_ci95": be.q(draws[:, 1], 0.95)},
            "bootstrap_draws": BOOT, "null_draws_per_bootstrap_draw": NULLS, "null_draws_point": NULL_POINT}


def gamma_by_line(ps: pd.DataFrame) -> dict:
    d = be.transitions(ps)
    d = d[d["v2"].notna()].reset_index(drop=True)
    d["line"] = d["pattern"].astype(str).str.split("|").str[0]
    out = {}
    for line, g in d.groupby("line", sort=False):
        if len(g) < 1000:
            continue
        num, den = be.gamma_parts(g.reset_index(drop=True), iv=True)
        out[line] = {"gamma_iv": round(float(num.sum() / den.sum()), 4), "transitions": int(len(g))}
    return dict(sorted(out.items(), key=lambda kv: kv[1]["gamma_iv"]))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    allp = be.load("tram")
    ps = allp[allp["H0"] >= be.H_MIN].reset_index(drop=True)
    n_dates = int(ps["date_id"].max() + 1)
    dates = ps.drop_duplicates("date_id").sort_values("date_id")
    odd = np.zeros(n_dates, bool)
    odd[dates["date_id"].to_numpy()] = (dates["week"] % 2 == 1).to_numpy()
    res = json.loads((ROOT / "docs/research/bunching-results.json").read_text())
    q1 = res["Q1"]
    out = {"note": "checks added after publication, following the independent review of 8 October 2026; post hoc, "
                   "not registered",
           "q1_label": {"published": q1.get("label_v1", q1["label"]), "corrected": be.label_gamma(q1["ci95"], q1["ci90"])}}
    if q1["label"] != out["q1_label"]["corrected"]:
        q1["label_v1"], q1["label"] = q1["label"], out["q1_label"]["corrected"]
        (ROOT / "docs/research/bunching-results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    log.info("gamma by line")
    gl = gamma_by_line(ps)
    first, last = next(iter(gl)), next(reversed(gl))
    big = {k: v for k, v in gl.items() if v["transitions"] >= 50_000}
    bf, bl = next(iter(big)), next(reversed(big))
    out["gamma_iv_by_line"] = {"lines": gl, "min": {"line": first, **gl[first]}, "max": {"line": last, **gl[last]},
                               "at_least_50000_transitions": {"lines": len(big), "min": {"line": bf, **big[bf]},
                                                              "max": {"line": bl, **big[bl]}}}
    ev = be.events(ps)
    ev["line"] = ev["pattern"].astype(str).str.split("|").str[0]
    for stratum in ("pattern", "line"):
        log.info("Q2 within %s", stratum)
        out[f"q2_null_within_{stratum}"] = q2_stratified(ev, n_dates, odd, stratum, np.random.default_rng(be.SEED))
    (ROOT / "docs/research/bunching-review.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
