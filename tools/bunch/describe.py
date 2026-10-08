"""Descriptions added after the results of the bunching study (not registered): how pairs become bunched, the IV's
first stage, and the shuffle benchmark with swaps counted. Writes docs/research/bunching-describe.json.

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with scipy python tools/bunch/describe.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bunch_estimate", Path(__file__).with_name("estimate.py"))
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)


def main() -> None:
    allp = be.load("tram")
    ps = allp[allp["H0"] >= be.H_MIN].reset_index(drop=True)
    o = ps[ps["r"].notna()]
    bunched = (o["r"] >= 0) & (o["r"] < be.BUNCH)
    ever = o[bunched].groupby("pair")["k"].min()
    first = o.merge(ever.rename("k_first"), left_on="pair", right_index=True)
    prev = o.assign(k=o["k"] + 1)[["pair", "k", "r"]].rename(columns={"r": "r_prev"})
    at_first = first[first["k"] == first["k_first"]].merge(prev, on=["pair", "k"], how="left")
    d = be.transitions(ps)
    d = d[d["v2"].notna()].reset_index(drop=True)
    x, z = (d["v1"] - 1).to_numpy(), (d["v2"] - 1).to_numpy()
    xt, zt = be.demean([x, z], be.fe_groups(d))
    b1 = (zt @ xt) / (zt @ zt)
    resid = xt - b1 * zt
    se = np.sqrt((resid @ resid) / (len(xt) - 2) / (zt @ zt))
    rng = np.random.default_rng(be.SEED)
    sh = be.shuffled(ps, rng).merge(ps[["pair", "k", "L"]], on=["pair", "k"])
    sh = sh.assign(decile=be.decile(sh))
    obs = ps.assign(decile=be.decile(ps))
    close = lambda t: t[t["r"].notna()].groupby("decile")["r"].apply(lambda r: round(float((r < be.BUNCH).mean()), 4))  # noqa: E731
    out = {
        "note": "described after the results; not registered",
        "pairs": int(o["pair"].nunique()),
        "pairs_ever_bunched": int(len(ever)),
        "share_pairs_ever_bunched": round(len(ever) / o["pair"].nunique(), 4),
        "first_bunched_from_r_ge_0.5": int((at_first["r_prev"] >= 0.5).sum()),
        "first_bunched_from_0.25_to_0.5": int(at_first["r_prev"].between(0.25, 0.5, inclusive="left").sum()),
        "first_bunched_at_first_observed_stop": int(at_first["r_prev"].isna().sum()),
        "iv_first_stage": {"coef": round(float(b1), 4), "t": round(float(b1 / se), 1), "n": int(len(xt))},
        "bunched_or_swapped_by_decile": {"observed": {str(k): v for k, v in close(obs).items()},
                                         "shuffled": {str(k): v for k, v in close(sh).items()}},
        "pairs_bunched_at_last_stop_share": round(float(
            o.sort_values("k").groupby("pair").tail(1)["r"].pipe(lambda r: ((r >= 0) & (r < be.BUNCH)).mean())), 4),
    }
    # IV with deeper lags, and intervals for the variants the review asked about
    t = be.transitions(ps)
    t3 = ps[["pair", "k", "r"]].assign(k=ps["k"] + 3).rename(columns={"r": "v3"})
    t4 = ps[["pair", "k", "r"]].assign(k=ps["k"] + 4).rename(columns={"r": "v4"})
    t = t.merge(t3, on=["pair", "k"], how="left").merge(t4, on=["pair", "k"], how="left")
    for lag in ("v3", "v4"):
        dd = t[t[lag].notna()].drop(columns="v2").rename(columns={lag: "v2"}).reset_index(drop=True)
        num, den = be.gamma_parts(dd, iv=True)
        out[f"gamma_iv_instrument_{lag[1]}_stops_back"] = round(float(num.sum() / den.sum()), 4)
    timing = be.timing_stops("tram")
    for name, sub in (("without_timing_points", ps[~ps["stop_id"].isin(timing)]),
                      ("departures", ps.assign(r=np.where(ps["h_dep"].notna(), ps["h_dep"] / ps["H"], np.nan)))):
        dd = be.transitions(sub)
        dd = dd[dd["v2"].notna()].reset_index(drop=True)
        num, den = be.gamma_parts(dd, iv=True)
        g, c95, _ = be.boot_ratio(num, den, rng)
        out[f"gamma_iv_{name}"] = {"est": g, "ci95": c95}
    # persistence of bunches, and volatility at platforms
    nxt = o.assign(k=o["k"] - 1)[["pair", "k", "r"]].rename(columns={"r": "r_next"})
    b = o[bunched].merge(nxt, on=["pair", "k"])
    out["bunched_still_bunched_next_stop"] = round(float(((b["r_next"] >= 0) & (b["r_next"] < be.BUNCH)).mean()), 4)
    ev = be.events(ps)
    ev["drop"] = (ev["v"] - ev["v1"]) < -0.25
    ev["rise"] = (ev["v"] - ev["v1"]) > 0.25
    g = ev.groupby("stop_id", observed=True).agg(n=("eligible", "size"), e=("eligible", "sum"), births=("birth", "sum"),
                                                  drops=("drop", "mean"), rises=("rise", "mean"))
    g = g[g["e"] >= be.FLOOR]
    from scipy.stats import spearmanr
    out["platforms_rank_corr_birth_rate_vs_large_steps"] = round(float(spearmanr(
        g["births"] / g["e"], g["drops"] + g["rises"]).statistic), 4)
    out["platforms_rank_corr_drops_vs_rises"] = round(float(spearmanr(g["drops"], g["rises"]).statistic), 4)
    rate = g["births"].sum() / g["e"].sum()
    g["expected"] = g["e"] * rate
    names = ps.drop_duplicates("stop_id").set_index("stop_id")["stop_name"].astype(str)
    top = g.sort_values("births", ascending=False).head(8)
    out["platforms_most_births"] = [{"stop_id": str(i), "stop": names.get(i, ""), "births": int(r.births),
                                     "expected": round(float(r.expected), 1)} for i, r in top.iterrows()]
    seg = ev[ev["birth"]].groupby(["prev_name", "stop_name"], observed=True).size().sort_values(ascending=False)
    out["segments_most_births"] = [{"segment": f"{a} → {b}", "births": int(v)} for (a, b), v in seg.head(5).items()]
    out["platforms_with_zero_births_share"] = round(float((g["births"] == 0).mean()), 4)
    (ROOT / "docs/research/bunching-describe.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
