"""Film fund study: the registered analysis (docs/research/film-fund-design.md §4-§6).

Joins the Council's points to the frozen links (tools/data/film/links_frozen.csv) and estimates:
- Q1: the effect of production support at each call's cut-off on release in Czech cinemas (O1) and
  on log(1 + Czech admissions) (O2); pooled normalized RD, local linear, triangular kernel,
  MSE-optimal bandwidth, robust bias-corrected 95 % CI clustered by call (rdrobust);
- the density test at the cut-off (rddensity) and covariate balance;
- Q2: within-call Spearman rho between points and log admissions among released projects, with a
  bootstrap over calls;
- the §6 sensitivity checks.
Writes tools/data/film/results.json.

    uv run --no-project --with pandas --with pyarrow --with numpy --with scipy --with rdrobust \
        --with rddensity --with rapidfuzz python tools/film/analyse.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rddensity import rddensity
from rdrobust import rdrobust
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link import norm  # noqa: E402
from recall_audit import company  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "tools" / "data" / "film"
SEED, BOOT = 20261001, 2000


def load() -> pd.DataFrame:
    apps = pd.read_parquet(DATA / "applications.parquet")
    links = pd.read_csv(DATA / "links_frozen.csv")
    d = apps.merge(links[["call", "app_id", "title", "rule", "src", "src_id", "matched_label", "linked", "linked_sens"]],
                   on=["call", "app_id", "title"], how="inner")
    t = d.call_title.str.lower()
    d = d[t.str.contains("výrob") & ~t.str.contains("krátkometr|kratkometr")].copy()
    d["year"] = d.call.str[:4].astype(int)
    cuts = {}
    for c, g in d.groupby("call"):
        f, u = g[g.funded], g[~g.funded]
        if len(f) and len(u) and f.total.min() > u.total.max():
            cuts[c] = (f.total.min() + u.total.max()) / 2
    d = d[d.call.isin(cuts)].copy()
    d["dist"] = d.total - d.call.map(cuts)
    # admissions: LUMIERE links carry them; a UFD-only link takes the LUMIERE film of the same title, if any
    lum = pd.read_parquet(DATA / "outcomes" / "lumiere_cz.parquet")
    by_id = lum.set_index(lum.movie_id.astype(str)).cz_admissions
    by_title = {}
    for r in lum.itertuples():
        for n in (r.title, r.title_cz):
            if norm(n):
                by_title.setdefault(norm(n), r.cz_admissions)
    def adm(r):
        if not r.linked:
            return 0.0
        if r.src == "lumiere" and str(r.src_id) in by_id.index:
            return float(by_id[str(r.src_id)])
        return float(by_title[norm(r.matched_label)]) if norm(r.matched_label) in by_title else np.nan
    d["adm"] = d.apply(adm, axis=1)
    d["log_adm"] = np.log1p(d.adm)
    d["project"] = d.title.map(norm) + "|" + d.applicant.map(company)
    d = d.sort_values(["project", "year", "call"])
    d["first"] = ~d.duplicated("project")
    d["prior_funded"] = d.groupby(d.applicant.map(company)).funded.transform(lambda s: s.shift().fillna(0).cumsum())
    d["log_budget"] = np.log(d.budget.where(d.budget > 0))
    d["log_requested"] = np.log(d.requested.where(d.requested > 0))
    d["share_requested"] = d.requested / d.budget.where(d.budget > 0)
    return d


def rd(s: pd.DataFrame, y: str, h: float | None = None, donut: float = 0.0, cluster: str = "call") -> dict:
    s = s[s[y].notna() & (s.dist.abs() >= donut)]
    kw = {"h": h} if h else {}
    r = rdrobust(s[y].to_numpy(float), s.dist.to_numpy(float), c=0, cluster=s[cluster].astype("category").cat.codes.to_numpy(), **kw)
    coef = float(np.asarray(r.coef).ravel()[0])
    ci = np.asarray(r.ci)
    lo, hi = float(ci[2, 0]), float(ci[2, 1])          # robust bias-corrected
    bw = float(np.asarray(r.bws).ravel()[0])
    inside = s[s.dist.abs() <= bw]
    return {"coef": round(coef, 4), "lo": round(lo, 4), "hi": round(hi, 4), "h": round(bw, 2),
            "n_left": int((inside.dist < 0).sum()), "n_right": int((inside.dist > 0).sum()),
            "calls": int(inside.call.nunique()), "pv": round(float(np.asarray(r.pv).ravel()[2]), 4)}


def label(r: dict, band: float, mde: float) -> str:
    if r["lo"] > 0 or r["hi"] < 0:
        return "supported"
    if -band <= r["lo"] and r["hi"] <= band:
        return "not supported"
    return "underpowered"


def q2(s: pd.DataFrame) -> dict:
    s = s[s.linked & s.adm.notna() & (s.adm > 0)].copy()
    s = s[s.groupby("call").call.transform("size") >= 2]
    def rho(x: pd.DataFrame) -> float:
        a = x.total - x.groupby("call").total.transform("mean")
        b = x.log_adm - x.groupby("call").log_adm.transform("mean")
        return float(spearmanr(a, b).correlation)
    point = rho(s)
    rng = np.random.default_rng(SEED)
    calls = s.call.unique()
    boots = []
    for _ in range(BOOT):
        pick = rng.choice(calls, size=len(calls), replace=True)
        b = pd.concat([s[s.call == c].assign(call=f"{c}#{i}") for i, c in enumerate(pick)])
        boots.append(rho(b))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"rho": round(point, 3), "lo": round(float(lo), 3), "hi": round(float(hi), 3),
            "n": int(len(s)), "calls": int(s.call.nunique()), "median_admissions": int(s.adm.median())}


def main() -> None:
    d = load()
    prim = d[(d.year <= 2021) & d["first"]]
    res = {"sample": {"applications": int(len(prim)), "calls": int(prim.call.nunique()), "funded": int(prim.funded.sum()),
                      "linked_share_funded": round(float(prim[prim.funded].linked.mean()), 3),
                      "linked_share_unfunded": round(float(prim[~prim.funded].linked.mean()), 3),
                      "o2_missing_admissions": int(prim.adm.isna().sum())}}
    dens = rddensity(X=prim.dist.to_numpy(float), c=0)
    res["density_p"] = round(float(np.asarray(dens.test["p_jk"]).ravel()[0]), 4)
    res["balance"] = {v: rd(prim, v) for v in ("log_budget", "log_requested", "share_requested", "prior_funded")}
    o1, o2 = rd(prim, "linked"), rd(prim, "log_adm")
    o1["label"], o2["label"] = label(o1, 0.10, 0.25), label(o2, 0.25, 0.0)
    res["Q1"] = {"O1_release": o1, "O2_log_admissions": o2}
    h1 = o1["h"]
    res["sensitivity"] = {
        "O1_half_bw": rd(prim, "linked", h=h1 / 2), "O1_double_bw": rd(prim, "linked", h=h1 * 2),
        "O1_donut": rd(prim, "linked", donut=0.5),
        "O1_unsure_as_released": rd(prim, "linked_sens"),
        "O1_2016_2022": rd(d[(d.year <= 2022) & d["first"]], "linked"),
        "O1_all_applications_cluster_project": rd(d[d.year <= 2021], "linked", cluster="project"),
        "O2_half_bw": rd(prim, "log_adm", h=o2["h"] / 2), "O2_double_bw": rd(prim, "log_adm", h=o2["h"] * 2),
    }
    near = prim[(prim.dist.abs() <= h1) & ~prim.funded]
    later = d[d.funded & d.project.isin(near.project)]
    res["rejected_near_cut_later_funded"] = {"rejected_in_bw": int(len(near)), "later_funded": int(later.project.nunique())}
    res["Q2"] = q2(d[d.year <= 2021])
    (DATA / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
