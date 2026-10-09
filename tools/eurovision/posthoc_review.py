"""Checks added 9 October 2026 after a review of the frozen code; not registered.

1. prepare.py's in_eu counts Croatia as a member at the 2013 contest (May); it joined on 1 July 2013. H3 is refitted
   with Croatia's entry year set to 2014, the rest of estimate.py's H3 steps unchanged.
2. estimate.py takes x90 over the distinct values of x; the design says "among dyads". x90 and R = exp(β · x90) are
   recomputed with one x per directed dyad (its mean over the dyad's rows), with the published β and interval.

Writes docs/research/eurovision-posthoc-review.json.

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest python tools/eurovision/posthoc_review.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "eurovision"))
import prepare  # noqa: E402
from estimate import D, coef  # noqa: E402

OUT = ROOT / "docs/research/eurovision-posthoc-review.json"
PUBLISHED = ROOT / "docs/research/eurovision-results.json"


def h3_fit(h3: pd.DataFrame) -> dict:
    """estimate.py's H3 steps, lines 96–126, as frozen."""
    h3 = h3[~h3.i.eq("GB") & ~h3.j.eq("GB")].copy()
    h3["pair"] = h3.i + ">" + h3.j
    h3["upair"] = [">".join(sorted(p)) for p in zip(h3.i, h3.j)]
    g = h3[h3.both_eu].groupby("pair").year.min()
    h3["g"] = h3.pair.map(g)
    h3 = h3[~(h3.g <= 1975)]
    h3["e"] = h3.year - h3.g
    pre = h3[h3.e < 0].groupby("pair").year.nunique()
    keep = set(pre[pre >= 3].index)
    h3 = h3[h3.g.isna() | h3.pair.isin(keep)].copy()
    h3["treat"] = (h3.e >= 0).astype(int)
    while True:
        n0 = len(h3)
        un = h3[h3.treat == 0]
        h3 = h3[h3.pair.isin(un.pair) & h3.year.isin(un.year)]
        h3 = h3[h3.groupby("pair").year.transform("size") > 1]
        if len(h3) == n0:
            break
    h3["w05"] = ((h3.e >= 0) & (h3.e <= 5)).astype(int)
    h3["w6"] = (h3.e >= 6).astype(int)
    fit = pf.did2s(h3, yname="share", first_stage="~ 0 | pair + year", second_stage="~ w05 + w6",
                   treatment="treat", cluster="upair")
    c = coef(fit, "w05")
    base = float(h3[(h3.e >= -5) & (h3.e <= -1)].share.mean())
    lab = ("supported" if c["lo"] > 0 else
           "not supported" if -0.1 * base <= c["lo"] and c["hi"] <= 0.1 * base else "inconclusive")
    return {"b": round(c["b"], 5), "ci95": [round(c["lo"], 5), round(c["hi"], 5)], "pre_mean": round(base, 5),
            "label": lab, "treated_pairs": len(keep), "n": c["n"]}


def ratio(b: dict, x90: float) -> dict:
    return {"x90": round(x90, 4), "per_1000": round(math.expm1(x90), 2),
            **{k: round(math.exp(b[s] * x90), 3) for k, s in (("R", "b"), ("R_lo", "lo"), ("R_hi", "hi"))}}


def main() -> None:
    pub = json.loads(PUBLISHED.read_text())
    h3 = pd.read_parquet(D / "h3.parquet")
    both = lambda: [prepare.in_eu(i, y) and prepare.in_eu(j, y) for i, j, y in zip(h3.i, h3.j, h3.year)]  # noqa: E731
    stored_matches = bool((np.array(both()) == h3.both_eu.to_numpy()).all())
    prepare.EU["HR"] = 2014
    fixed = h3.assign(both_eu=both())
    h1 = pd.read_parquet(D / "h1.parquet")
    pos = h1[h1.x > 0]
    res = {
        "note": "added 9 October 2026 after a review of the frozen code; not registered",
        "h3": {"stored_both_eu_matches_in_eu": stored_matches,
               "rows_changed": int((fixed.both_eu != h3.both_eu).sum()),
               "published": {"b": round(pub["H3"]["b"], 5), "ci95": [round(pub["H3"]["lo"], 5),
                                                                     round(pub["H3"]["hi"], 5)],
                             "label": pub["H3"]["label"]},
               "as_frozen": h3_fit(h3), "croatia_from_2014": h3_fit(fixed)},
        "h1_x90": {"published_distinct_x": ratio(pub["H1"], float(np.quantile(pos.x.drop_duplicates(), 0.9))),
                   "by_dyad_mean": ratio(pub["H1"], float(np.quantile(pos.groupby(["i", "j"]).x.mean(), 0.9))),
                   "dyads": int(pos.groupby(["i", "j"]).ngroups), "h1_label_set_by_beta_alone": pub["H1"]["label"]},
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
