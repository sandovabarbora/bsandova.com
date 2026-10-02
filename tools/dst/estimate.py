"""Estimates of design §3–§6 (with the change notes of 2 Oct 2026) from tools/data/dst/cells.parquet.

Primary (H1, H2): Poisson PML on region × date × hour cells of the evening (16–18), morning (06–07) and control
(10–13) hours, days −14 … +14 (day 0 dropped):
    ped ~ post + t + post:evening + post:morning | region×year + day of week + hour,  clustered by date.
Labels (§4): ratio exp(β) supported if its 95 % interval lies wholly beyond 1 in the expected direction, not
supported if it lies within 0.90–1.10, otherwise inconclusive.

Writes tools/data/dst/results.json and results.csv (copied to docs/research/dst-darkness-results.csv at the results
commit).

    uv run --with pandas --with pyarrow --with pyfixest python tools/dst/estimate.py
"""
import json
import os
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
D = Path(os.environ.get("DST_DATA", ROOT / "tools" / "data" / "dst"))
VCOV = {"CRV1": "date"}
FE = "ry + dow + hour"


def frame(cells: pd.DataFrame, lo: int, hi: int, outcome: str = "ped", cut: int = 0) -> pd.DataFrame:
    """Cells of the three hour groups, days lo … hi, with Post = day > cut (day `cut` itself dropped)."""
    d = cells[(cells.group != "other") & (cells.t >= lo) & (cells.t <= hi) & (cells.t != cut)].copy()
    d["y"] = d[outcome]
    d["post"] = (d.t > cut).astype(int)
    d["ev"] = (d.group == "evening").astype(int)
    d["mo"] = (d.group == "morning").astype(int)
    d["pe"], d["pm"] = d.post * d.ev, d.post * d.mo
    d["tt"] = d.t - cut
    d["te"], d["tm"] = d.tt * d.ev, d.tt * d.mo
    d["ry"] = d.region + "_" + d.year.astype(str)
    return d


def ratio(fit, term: str) -> dict:
    b, se = fit.coef()[term], fit.se()[term]
    return {"ratio": math.exp(b), "lo": math.exp(b - 1.96 * se), "hi": math.exp(b + 1.96 * se), "b": b, "se": se,
            "n": int(fit._N)}


def label(r: dict, direction: int) -> str:
    if (direction > 0 and r["lo"] > 1) or (direction < 0 and r["hi"] < 1):
        return "supported"
    if r["lo"] >= 0.90 and r["hi"] <= 1.10:
        return "not supported"
    return "inconclusive"


def poisson(d: pd.DataFrame, trends: bool = False):
    rhs = "post + tt + pe + pm" + (" + te + tm" if trends else "")
    return pf.fepois(f"y ~ {rhs} | {FE}", data=d, vcov=VCOV)


def main() -> None:
    cells = pd.read_parquet(D / "cells.parquet")
    res, rows = {}, []

    def add(name, fit, terms=("pe", "pm")):
        res[name] = {t: ratio(fit, t) for t in terms}
        for t in terms:
            rows.append({"model": name, "term": {"pe": "evening", "pm": "morning"}.get(t, t), **res[name][t]})

    prim = poisson(frame(cells, -14, 14))
    add("primary", prim)
    res["labels"] = {"H1": label(res["primary"]["pe"], +1), "H2": label(res["primary"]["pm"], -1)}

    # §6 checks and the registered sensitivity (original specification with group trends)
    add("group_trends", poisson(frame(cells, -14, 14), trends=True))
    add("placebo_day_-14", poisson(frame(cells, -28, -1, cut=-14)))
    add("window_7", poisson(frame(cells, -7, 7)))
    add("window_21", poisson(frame(cells, -21, 21)))
    add("no_2020_2021", poisson(frame(cells[~cells.year.isin([2020, 2021])], -14, 14)))
    add("other_crash_kinds", poisson(frame(cells, -14, 14, outcome="other")))

    # Event study: evening and morning relative to control, by day, reference day −1, region×date FE
    es = frame(cells, -14, 14)
    es["rd"] = es.region + "_" + es.date
    for g in ("ev", "mo"):
        for t in sorted(es.t.unique()):
            if t != -1:
                es[f"{g}_{'m' if t < 0 else 'p'}{abs(t)}"] = ((es.t == t) & (es[g] == 1)).astype(int)
    terms = [c for c in es.columns if c[:3] in ("ev_", "mo_")]
    fit = pf.fepois(f"y ~ {' + '.join(terms)} | rd + hour", data=es, vcov=VCOV)
    res["event_study"] = {t: ratio(fit, t) for t in terms}

    # H3 (§5): linear 2SLS, darkness instrumented by post × hour dummies of the shifted hours
    iv = frame(cells, -14, 14)
    for h in (6, 7, 16, 17, 18):
        iv[f"z{h}"] = iv.post * (iv.hour == h)
    z = " + ".join(f"z{h}" for h in (6, 7, 16, 17, 18))
    fit = pf.feols(f"y ~ post + tt | {FE} | dark ~ {z}", data=iv, vcov=VCOV)
    b, se = fit.coef()["dark"], fit.se()["dark"]
    base = iv[(iv.ev == 1) & (iv.post == 0)].y.mean()
    first = pf.feols(f"dark ~ post + tt + {z} | {FE}", data=iv, vcov=VCOV)
    zs = [f"z{h}" for h in (6, 7, 16, 17, 18)]
    bz = first.coef()[zs].to_numpy()
    vz = pd.DataFrame(first._vcov, index=first.coef().index, columns=first.coef().index).loc[zs, zs].to_numpy()
    fstat = float(bz @ np.linalg.solve(vz, bz))  # cluster-robust Wald; F = Wald / number of instruments
    res["H3"] = {"b_dark": b, "se": se, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "pre_evening_mean": base,
                 "pct_of_mean": 100 * b / base if base else None, "first_stage_F": fstat / 5,
                 "weak": fstat / 5 < 10}

    # Police-recorded light (p19 night codes) by group, before and after: share of all crashes
    chk = frame(cells, -14, 14)
    chk["all"] = chk.ped + chk.other
    g = chk.groupby(["group", "post"])[["police_dark", "all", "dark"]].sum()
    res["police_light"] = {f"{k[0]}_{'post' if k[1] else 'pre'}": {"police_dark_share": v.police_dark / v["all"]
                           if v["all"] else None} for k, v in g.iterrows()}
    res["sun_dark_share"] = {f"{k[0]}_{'post' if k[1] else 'pre'}": v
                             for k, v in chk.groupby(["group", "post"]).dark.mean().items()}
    res["versions"] = {"pyfixest": pf.__version__, "pandas": pd.__version__}

    (D / "results.json").write_text(json.dumps(res, indent=1, default=float))
    pd.DataFrame(rows).to_csv(D / "results.csv", index=False, float_format="%.4f")
    print(json.dumps({"labels": res["labels"], "primary": res["primary"], "H3": res["H3"]}, indent=1, default=float))


if __name__ == "__main__":
    main()
