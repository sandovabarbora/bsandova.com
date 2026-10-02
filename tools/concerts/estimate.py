"""Concert effect: the registered estimates (design §4–6), written to docs/research/concert-effect-results.json.

Callaway and Sant'Anna's group-time effects with the `csdid` package: groups are the week of a country's first show,
comparison units the not-yet-treated and never-treated countries, the multiplier bootstrap clustered by country with
uniform bands. The dynamic aggregation runs from 12 weeks before to 12 after; the summary is the average of weeks
0 to +4. Checks: never-treated comparison, a 26-week placebo, leave one treated country out.

    uv run --with csdid --with pandas --with numpy python tools/concerts/estimate.py
"""

from __future__ import annotations

import contextlib
import io
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from csdid.att_gt import ATTgt

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
SEED, BITERS, LO, HI = 20261002, 999, -12, 12


def panel() -> pd.DataFrame:
    """The balanced panel: countries with Top-200 data in every week of the window."""
    p = pd.read_csv(R / "concert-effect-panel.csv")
    weeks = p.week.nunique()
    full = p.groupby("country").week.nunique()
    keep = full[full == weeks].index
    p = p[p.country.isin(keep)].copy()
    p["id"] = p.country.astype("category").cat.codes + 1
    # a treated country needs 12 weeks before its first show inside the window (design §4)
    first_week = p.week.min()
    short = sorted(p[(p.g > 0) & (p.g - first_week < 12)].country.unique())
    p.loc[p.country.isin(short), "g"] = -1
    p = p[p.g >= 0]
    return p, sorted(set(full.index) - set(keep)), short


def fit(p: pd.DataFrame, y: str, control: str = "notyettreated", g: str = "g") -> dict:
    np.random.seed(SEED)
    with contextlib.redirect_stdout(io.StringIO()):
        m = ATTgt(yname=y, tname="week", idname="id", gname=g, data=p, control_group=control, cband=True,
                  biters=BITERS, clustervar="id").fit(est_method="reg")
        m.aggte(typec="dynamic", min_e=LO, max_e=HI)
        dyn = dict(m.atte)
        m.aggte(typec="dynamic", min_e=0, max_e=4)
        summ = dict(m.atte)
    e = np.asarray(dyn["egt"], dtype=float)
    att = np.asarray(dyn["att_egt"], dtype=float)
    se = np.asarray(dyn["se_egt"], dtype=float).ravel()
    c = float(dyn["crit_val_egt"])
    s_att, s_se = float(summ["overall_att"]), float(np.asarray(summ["overall_se"]).ravel()[0])
    return {"event": [{"e": int(k), "att": float(a), "lo": float(a - c * s), "hi": float(a + c * s)}
                      for k, a, s in zip(e, att, se)],
            "summary": {"att": s_att, "lo": s_att - 1.96 * s_se, "hi": s_att + 1.96 * s_se, "se": s_se},
            "crit": c}


def label(res: dict, base: float) -> dict:
    """Design §6: supported, not supported or inconclusive, and why."""
    s = res["summary"]
    pre_ok = all(r["lo"] <= 0 <= r["hi"] for r in res["event"] if -12 <= r["e"] <= -2)
    excludes = s["lo"] > 0 or s["hi"] < 0
    within = -0.1 * base <= s["lo"] and s["hi"] <= 0.1 * base
    if excludes and pre_ok:
        return {"label": "supported", "why": "interval excludes zero and every pre-trend band includes zero"}
    if not excludes and within:
        return {"label": "not supported", "why": "interval includes zero and lies within ±10 % of the pre-period mean"}
    why = ("a pre-trend band excludes zero" if excludes and not pre_ok
           else "interval includes zero but is wider than ±10 % of the pre-period mean")
    return {"label": "inconclusive", "why": why}


def main() -> None:
    p, unbalanced, short = panel()
    treated = p[p.g > 0]
    pre = treated[(treated.week - treated.g >= -12) & (treated.week - treated.g <= -2)]
    base = {y: float(pre[y].mean()) for y in ("y1_share", "y2_songs", "y3_share_top3")}
    out = {"csdid_version": version("csdid"), "seed": SEED, "biters": BITERS,
           "countries": int(p.country.nunique()), "treated": sorted(treated.country.unique()),
           "never_treated": sorted(p[p.g == 0].country.unique()), "dropped_unbalanced": unbalanced,
           "dropped_short_pre": short, "pre_mean": base}
    for y in ("y1_share", "y2_songs", "y3_share_top3"):
        r = fit(p, y)
        out[y] = r | label(r, base[y])
    out["never_treated_only"] = fit(p, "y1_share", control="nevertreated")["summary"]
    # placebo: every first show 26 weeks earlier; a group that falls before the window is dropped
    q = p.copy()
    q["g_placebo"] = np.where(q.g > 0, q.g - 26, 0)
    q = q[(q.g_placebo == 0) | (q.g_placebo > q.week.min())]
    out["placebo_26w"] = fit(q, "y1_share", g="g_placebo")["summary"]
    loo = {}
    for c in sorted(treated.country.unique()):
        loo[c] = fit(p[p.country != c], "y1_share")["summary"]["att"]
    out["leave_one_out"] = loo
    (R / "concert-effect-results.json").write_text(json.dumps(out, indent=1))
    print("written concert-effect-results.json")


if __name__ == "__main__":
    main()
