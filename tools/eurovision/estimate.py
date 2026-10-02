"""Registered estimates of design §3–§6 from tools/data/eurovision/{h1,h2,h3}.parquet.

H1: PPML, points ~ x·Televote | pair + voter×year×round×audience + performer×year×round×audience, clustered by
undirected pair. H2: OLS, televote − jury points to Ukraine ~ refugees·Post | voter + year, clustered by voter.
H3: Gardner's two-stage DiD (pyfixest did2s) on the share of a voter's points, dyad and year effects, clustered by
undirected pair; summary = event years 0 … +5. Labels as registered.

Writes tools/data/eurovision/results.json and prints the headline numbers.

    uv run --with pandas --with pyarrow --with pyfixest python tools/eurovision/estimate.py
"""
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
D = Path(os.environ.get("ESC_DATA", ROOT / "tools" / "data" / "eurovision"))


def h1_frame(h1: pd.DataFrame) -> pd.DataFrame:
    d = h1.copy()
    d["tele"] = (d.aud == "tele").astype(int)
    d["xt"] = d.x * d.tele
    d["pair"] = d.i + ">" + d.j
    d["upair"] = [">".join(sorted(p)) for p in zip(d.i, d.j)]
    d["vra"] = d.i + d.year.astype(str) + d.r + d.aud
    d["pra"] = d.j + d.year.astype(str) + d.r + d.aud
    return d


def h1_fit(d: pd.DataFrame, extra: str = ""):
    return pf.fepois(f"points ~ xt{extra} | pair + vra + pra", data=d, vcov={"CRV1": "upair"})


def coef(fit, term: str) -> dict:
    b, se = float(fit.coef()[term]), float(fit.se()[term])
    return {"b": b, "se": se, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "n": int(fit._N)}


def main() -> None:
    res = {}
    h1 = h1_frame(pd.read_parquet(D / "h1.parquet"))
    x90 = float(np.quantile(h1.loc[h1.x > 0, "x"].drop_duplicates(), 0.9))
    main_fit = coef(h1_fit(h1), "xt")
    R = {k: math.exp(main_fit[k] * x90) for k in ("b", "lo", "hi")}
    lab = ("supported" if main_fit["lo"] > 0 else
           "not supported" if 0.90 <= R["lo"] and R["hi"] <= 1.10 else "inconclusive")
    res["H1"] = {**main_fit, "x90": x90, "R": R["b"], "R_lo": R["lo"], "R_hi": R["hi"], "label": lab}

    checks = {"no_2022": h1[h1.year != 2022], "finals_only": h1[h1.r == "final"], "semis_only": h1[h1.r != "final"]}
    res["H1_checks"] = {k: coef(h1_fit(v), "xt") for k, v in checks.items()}
    h1["ct"], h1["lt"] = h1.contig.fillna(0) * h1.tele, h1.comlang.fillna(0) * h1.tele
    f = h1_fit(h1, " + ct + lt")
    res["H1_checks"]["with_contiguity_language"] = {t: coef(f, t) for t in ("xt", "ct", "lt")}

    # jurors (2016–2022): each juror's ranking to Eurovision points, in place of the jury's points
    jr = pd.read_csv(D / "raw" / "mirovision_jurors.csv")
    jr["r"] = jr["round"].map({"final": "final", "semi-final-1": "sf1", "semi-final-2": "sf2"})
    pts = dict(zip(range(1, 11), [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]))
    long = jr.melt(id_vars=["year", "r", "from_country", "to_country"], value_vars=list("ABCDE"),
                   var_name="juror", value_name="rank").dropna()
    long["points"] = long["rank"].astype(int).map(pts).fillna(0)
    long = long.rename(columns={"from_country": "i", "to_country": "j"})
    long["aud"] = "juror" + long.juror
    xs = h1[["year", "r", "i", "j", "x"]].drop_duplicates()
    jur = long.merge(xs, on=["year", "r", "i", "j"], how="inner")[["year", "r", "i", "j", "aud", "points", "x"]]
    tele = h1[(h1.aud == "tele") & h1.year.between(2016, 2022)][["year", "r", "i", "j", "aud", "points", "x"]]
    jd = h1_frame(pd.concat([tele, jur]))
    res["H1_checks"]["individual_jurors"] = coef(h1_fit(jd), "xt")

    # H2
    h2 = pd.read_parquet(D / "h2.parquet")
    h2["rp"] = h2.ref_x * h2.post
    f2 = pf.feols("diff ~ rp | i + year", data=h2, vcov={"CRV1": "i"})
    c2 = coef(f2, "rp")
    lab2 = "supported" if c2["lo"] > 0 else "not supported" if -0.5 <= c2["lo"] and c2["hi"] <= 0.5 else "inconclusive"
    res["H2"] = {**c2, "label": lab2, "voters": int(h2.i.nunique())}

    # H3
    h3 = pd.read_parquet(D / "h3.parquet")
    h3 = h3[~h3.i.eq("GB") & ~h3.j.eq("GB")].copy()
    h3["pair"] = h3.i + ">" + h3.j
    h3["upair"] = [">".join(sorted(p)) for p in zip(h3.i, h3.j)]
    g = h3[h3.both_eu].groupby("pair").year.min()
    h3["g"] = h3.pair.map(g)
    h3 = h3[~(h3.g <= 1975)]
    h3["e"] = h3.year - h3.g
    pre = h3[h3.e < 0].groupby("pair").year.nunique()
    keep = set(pre[pre >= 3].index)
    dropped = int(h3[h3.g.notna()].pair.nunique() - len(keep))
    h3 = h3[h3.g.isna() | h3.pair.isin(keep)].copy()
    h3["treat"] = (h3.e >= 0).astype(int)
    h3["w05"] = ((h3.e >= 0) & (h3.e <= 5)).astype(int)
    h3["w6"] = (h3.e >= 6).astype(int)
    fit = pf.did2s(h3, yname="share", first_stage="~ 0 | pair + year", second_stage="~ w05 + w6",
                   treatment="treat", cluster="upair")
    c3 = coef(fit, "w05")
    base = float(h3[(h3.e >= -5) & (h3.e <= -1)].share.mean())
    lab3 = ("supported" if c3["lo"] > 0 else
            "not supported" if -0.1 * base <= c3["lo"] and c3["hi"] <= 0.1 * base else "inconclusive")
    res["H3"] = {**c3, "pre_mean": base, "pct": 100 * c3["b"] / base, "label": lab3, "dropped_pairs": dropped,
                 "treated_pairs": len(keep)}
    h3["rel"] = h3.e.clip(-10, 10).fillna(-1000).astype(int)
    for k in range(-10, 11):
        if k != -1:
            h3[f"ev{'m' if k < 0 else 'p'}{abs(k)}"] = (h3.rel == k).astype(int)
    terms = [c for c in h3.columns if c.startswith("ev")]
    fe = pf.did2s(h3, yname="share", first_stage="~ 0 | pair + year", second_stage="~ " + " + ".join(terms),
                  treatment="treat", cluster="upair")
    res["H3_event"] = {t: coef(fe, t) for t in terms}
    res["versions"] = {"pyfixest": pf.__version__}
    (D / "results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("H1", "H2", "H3")}, indent=1))


if __name__ == "__main__":
    main()
