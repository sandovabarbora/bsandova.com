"""Post-hoc completion of registered steps of the film-fund study, added 13 October 2026 after publication.

- Q2 on first applications only, as §2 of the design keeps them; the published Q2 counted every application.
- The §6 bound on linking errors for Q1 O1. Read literally ("unmatched projects in both groups counted as released")
  it makes release 1 for every application, so there is nothing to estimate. Instead, at the main bandwidth, each
  unmatched application counts as released with the probability the blind recall audit found for its group
  (docs/research/film-fund-recall-audit.csv: 3 of 30 funded, 2 of 30 unfunded plus 1 unsure), taken at the ends of
  the 95 % Clopper-Pearson intervals that favour and disfavour an effect; the local linear estimator is linear in
  the outcome, so this equals the mean over random imputations. The worst case (every unmatched funded application
  released and no unfunded one, and the reverse) is reported alongside.
- The rest of the steps the 3 October audit found not carried out: O3 (European admissions), call fixed effects,
  feature-length calls only, Q2 for each criterion scored in every call, short-film calls on their own, release within
  three years for 2016-2022, the producer's earlier funded applications in time order, and the five links with 0
  Czech admissions counted as not released.

Writes docs/research/film-fund-posthoc.json.

    nice -n 20 uv run --no-project --with pandas --with pyarrow --with numpy --with scipy --with rdrobust \
        --with rddensity --with rapidfuzz python tools/film/posthoc.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdrobust import rdrobust
from scipy.stats import beta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse import DATA, label, load, q2, rd  # noqa: E402
from link import norm  # noqa: E402
from recall_audit import company  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs" / "research" / "film-fund-posthoc.json"
AUDIT_N = 30
# the criteria scored in all 40 primary calls under the same name, so with a fixed meaning across the scheme years
CRITERIA = ("umělecká kvalita projektu", "personální zajištění projektu",
            "přínos a význam pro českou a evropskou kinematografii", "kredit žadatele")


def clopper_pearson(k: int, n: int) -> tuple[float, float]:
    lo = float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0
    return lo, float(beta.ppf(0.975, k + 1, n - k))


def rd_call_fe(s: pd.DataFrame, y: str) -> dict:
    s = s[s[y].notna()]
    fe = pd.get_dummies(s.call, drop_first=True, dtype=float).to_numpy()
    r = rdrobust(s[y].to_numpy(float), s.dist.to_numpy(float), c=0, covs=fe,
                 cluster=s.call.astype("category").cat.codes.to_numpy())
    ci = np.asarray(r.ci)
    bw = float(np.asarray(r.bws).ravel()[0])
    inside = s[s.dist.abs() <= bw]
    return {"coef": round(float(np.asarray(r.coef).ravel()[0]), 4), "lo": round(float(ci[2, 0]), 4),
            "hi": round(float(ci[2, 1]), 4), "h": round(bw, 2), "n_left": int((inside.dist < 0).sum()),
            "n_right": int((inside.dist > 0).sum()), "calls": int(inside.call.nunique())}


def eu_admissions(d: pd.DataFrame) -> pd.Series:
    """O3 the way analyse.py builds O2: by LUMIERE id, else by the title of a UFD-only link, 0 if not released."""
    lum = pd.read_parquet(DATA / "outcomes" / "lumiere_cz.parquet")
    by_id = lum.set_index(lum.movie_id.astype(str)).eu_admissions
    by_title = {}
    for r in lum.itertuples():
        for n in (r.title, r.title_cz):
            if norm(n):
                by_title.setdefault(norm(n), r.eu_admissions)

    def one(r) -> float:
        if not r.linked:
            return 0.0
        if r.src == "lumiere" and str(r.src_id) in by_id.index:
            return float(by_id[str(r.src_id)])
        return float(by_title.get(norm(r.matched_label), np.nan))
    return d.apply(one, axis=1)


def short_film_calls() -> pd.DataFrame:
    """The short-film production calls, with cut-offs as analyse.load() sets them for the rest."""
    apps = pd.read_parquet(DATA / "applications.parquet")
    links = pd.read_csv(DATA / "links_frozen.csv")
    d = apps.merge(links[["call", "app_id", "title", "linked"]], on=["call", "app_id", "title"], how="inner")
    t = d.call_title.str.lower()
    d = d[t.str.contains("výrob") & t.str.contains("krátkometr|kratkometr")].copy()
    d["year"] = d.call.str[:4].astype(int)
    cuts = {c: (g[g.funded].total.min() + g[~g.funded].total.max()) / 2 for c, g in d.groupby("call")
            if g.funded.any() and (~g.funded).any() and g[g.funded].total.min() > g[~g.funded].total.max()}
    d = d[d.call.isin(cuts) & (d.year <= 2021)].copy()
    d["dist"] = d.total - d.call.map(cuts)
    d["project"] = d.title.map(norm) + "|" + d.applicant.map(company)
    return d.sort_values(["project", "year", "call"]).drop_duplicates("project")


def criterion(d: pd.DataFrame, name: str) -> pd.Series:
    def one(raw: str) -> float:
        hit = [c["points"] for c in json.loads(raw) if c["name"] == name]
        return float(hit[0]) if hit else np.nan
    return d.criteria.map(one)


def main() -> None:
    d = load()
    prim = d[(d.year <= 2021) & d["first"]]
    h = rd(prim, "linked")["h"]

    def imputed(p_funded: float, p_unfunded: float) -> dict:
        p = np.where(prim.funded, p_funded, p_unfunded)
        return rd(prim.assign(y=prim.linked.astype(float) + (~prim.linked).astype(float) * p), "y", h=h)

    funded, unfunded_lo, unfunded_hi = clopper_pearson(3, AUDIT_N), clopper_pearson(2, AUDIT_N), clopper_pearson(3, AUDIT_N)
    released = prim[prim.linked]
    films = released.src.astype(str) + ":" + released.src_id.astype(str)
    res = {
        "note": "post-hoc, added 13 October 2026 after publication; completes registered steps, see the module docstring",
        "Q2_first_applications": q2(d[(d.year <= 2021) & d["first"]]),
        "Q2_first_applications_linked_to_a_film_already_counted": int(films.duplicated().sum()),
        "O1_linking_bounds": {
            "bandwidth": h,
            "audit_recall_95ci": {"funded_3_of_30": funded, "unfunded_2_of_30": unfunded_lo, "unfunded_3_of_30": unfunded_hi},
            # a fixed bandwidth also fixes the bias-correction bandwidth, so the intervals compare with this, not the main one
            "no_imputation_same_settings": rd(prim, "linked", h=h),
            "audit_point": imputed(3 / AUDIT_N, 2.5 / AUDIT_N),
            "favouring_an_effect": imputed(funded[1], unfunded_lo[0]),
            "against_an_effect": imputed(funded[0], unfunded_hi[1]),
            "worst_case_favouring": imputed(1.0, 0.0),
            "worst_case_against": imputed(0.0, 1.0),
        },
    }
    res.update(completed_steps(d, prim))
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


def completed_steps(d: pd.DataFrame, prim: pd.DataFrame) -> dict:
    out = {}
    d = d.assign(log_eu=np.log1p(eu_admissions(d)))
    p = d[(d.year <= 2021) & d["first"]]
    o3 = rd(p, "log_eu")
    o3["label"] = label(o3, 0.25, 0.0)
    out["O3_log_european_admissions"] = o3 | {"missing": int(p.log_eu.isna().sum())}

    out["O1_call_fixed_effects"] = rd_call_fe(prim, "linked")
    out["O2_call_fixed_effects"] = rd_call_fe(prim, "log_adm")

    t = prim.call_title.str.lower()
    feature = prim[t.str.contains("celovečer")]
    out["O1_feature_length_calls"] = rd(feature, "linked") | {
        "definition": "calls whose title names a feature-length film (celovečerní): fiction, debuts, minority co-productions"}
    out["O1_without_animation_and_experimental_calls"] = rd(prim[~t.str.contains("animov|experiment")], "linked")

    links = pd.read_csv(DATA / "links_frozen.csv", usecols=["call", "app_id", "title", "release_year"])
    win3 = d[(d.year <= 2022) & d["first"]].merge(links, on=["call", "app_id", "title"], how="left")
    win3 = win3.assign(linked3=win3.linked & (win3.release_year <= win3.year + 3))
    out["O1_2016_2022_release_within_three_years"] = rd(win3, "linked3")

    out["O1_zero_admission_links_not_released"] = rd(
        prim.assign(released=prim.linked & ~(prim.src.eq("lumiere") & prim.adm.eq(0))), "released") | {
        "links_moved": int((prim.linked & prim.src.eq("lumiere") & prim.adm.eq(0)).sum())}

    # earlier funded production applications of the same producer, counting only calls of earlier years
    co = d.applicant.map(company)
    funded_by = d[d.funded].assign(co=co[d.funded]).groupby("co").year.apply(list)
    earlier = [sum(y < yr for y in funded_by.get(c, [])) for c, yr in zip(co, d.year)]
    dd = d.assign(prior_funded_in_time=earlier)
    out["balance_prior_funded_in_time"] = rd(dd[(dd.year <= 2021) & dd["first"]], "prior_funded_in_time")

    q = {}
    for name in CRITERIA:
        s = d[(d.year <= 2021) & d["first"]].assign(total=lambda x, n=name: criterion(x, n))
        q[name] = q2(s[s.total.notna()])
    out["Q2_by_criterion_first_applications"] = q

    sh = short_film_calls()
    out["short_film_calls"] = {"applications": int(len(sh)), "calls": int(sh.call.nunique()), "funded": int(sh.funded.sum()),
                               "released_share_funded": round(float(sh[sh.funded].linked.mean()), 3),
                               "released_share_unfunded": round(float(sh[~sh.funded].linked.mean()), 3)}
    try:
        out["short_film_calls"]["O1"] = rd(sh, "linked")
    except Exception as e:  # rdrobust refuses samples this small; the refusal is the result
        out["short_film_calls"]["O1"] = f"not estimable: {type(e).__name__}: {e}"
    return out


if __name__ == "__main__":
    main()
