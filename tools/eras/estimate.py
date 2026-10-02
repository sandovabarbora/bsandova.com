"""Eras Tour and prices: the registered estimates (design §3–5), written to docs/research/eras-inflation-results.json.

    uv run --with csdid --with pandas --with numpy python tools/eras/estimate.py
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
SEED, BITERS, PERMS = 20261002, 999, 2000
FIRST_SHOW = {"FR": "2024-05", "SE": "2024-05", "PT": "2024-05", "ES": "2024-05", "IE": "2024-06",
              "NL": "2024-07", "CH": "2024-07", "IT": "2024-07", "DE": "2024-07", "PL": "2024-08"}
Q = {"accommodation": "CP112", "restaurants": "CP111", "all_items": "CP00"}


def month_no(m: str) -> int:
    y, mo = map(int, m.split("-"))
    return (y - 2023) * 12 + mo          # January 2023 = 1


def panel(coicop: str) -> pd.DataFrame:
    h = pd.read_csv(R / "eras-inflation-hicp.csv")
    h = h[h.coicop == coicop].copy()
    h["t"] = h.month.map(month_no)
    h = h.sort_values(["geo", "t"])
    h["lag"] = h.groupby("geo")["index"].shift(12)
    h["lag_t"] = h.groupby("geo")["t"].shift(12)
    h = h[(h.lag_t == h.t - 12) & (h.t >= 1) & (h.t <= 30)]
    h["y"] = 100 * (np.log(h["index"]) - np.log(h["lag"]))
    full = h.groupby("geo").t.nunique()
    h = h[h.geo.isin(full[full == 30].index) & (h.geo != "AT")].copy()
    h["g"] = h.geo.map(lambda g: month_no(FIRST_SHOW[g]) if g in FIRST_SHOW else 0)
    h["id"] = h.geo.astype("category").cat.codes + 1
    return h[["geo", "id", "t", "g", "y"]]


def fit(p: pd.DataFrame, control: str = "notyettreated", g: str = "g") -> dict:
    np.random.seed(SEED)
    with contextlib.redirect_stdout(io.StringIO()):
        m = ATTgt(yname="y", tname="t", idname="id", gname=g, data=p, control_group=control, cband=True,
                  biters=BITERS, clustervar="id").fit(est_method="reg")
        m.aggte(typec="dynamic", min_e=-6, max_e=6)
    a = m.atte
    e, att = np.asarray(a["egt"], float), np.asarray(a["att_egt"], float)
    se, c = np.asarray(a["se_egt"], float).ravel(), float(a["crit_val_egt"])
    ev = [{"e": int(k), "att": float(x), "lo": float(x - c * s), "hi": float(x + c * s), "se": float(s)}
          for k, x, s in zip(e, att, se)]
    return {"event": ev, "month0": next(r for r in ev if r["e"] == 0)}


def att0(p: pd.DataFrame, g: str = "g") -> float:
    """The event-month-0 effect computed directly: for each group, its change from month g−1 to g minus the change
    of the not-yet-treated and never-treated countries, weighted by group size (the estimator csdid aggregates)."""
    w = p.pivot(index="geo", columns="t", values="y")
    gg = p.groupby("geo")[g].first()
    num = den = 0.0
    for grp, members in gg[gg > 0].groupby(gg[gg > 0]):
        if grp - 1 not in w.columns:
            continue
        ctrl = gg[(gg == 0) | (gg > grp)].index
        d_t = (w.loc[members.index, grp] - w.loc[members.index, grp - 1]).mean()
        d_c = (w.loc[ctrl, grp] - w.loc[ctrl, grp - 1]).mean()
        num += len(members) * (d_t - d_c)
        den += len(members)
    return num / den


def label(r: dict, p_perm: float) -> dict:
    m = r["month0"]
    pre_ok = all(x["lo"] <= 0 <= x["hi"] for x in r["event"] if -6 <= x["e"] <= -2)
    excl = m["lo"] > 0 or m["hi"] < 0
    if excl and pre_ok and p_perm < 0.05:
        return {"label": "supported", "why": "interval excludes zero, pre-trends include zero, permutation p < 0.05"}
    if not excl and -1 <= m["lo"] and m["hi"] <= 1:
        return {"label": "not supported", "why": "interval includes zero and lies within ±1 percentage point"}
    why = [w for w, bad in (("a pre-trend band excludes zero", not pre_ok), ("permutation p ≥ 0.05", p_perm >= 0.05),
                            ("interval wider than ±1 point", not excl)) if bad]
    return {"label": "inconclusive", "why": "; ".join(why)}


def main() -> None:
    out = {"csdid_version": version("csdid"), "seed": SEED, "biters": BITERS, "permutations": PERMS}
    rng = np.random.default_rng(SEED)
    for name, code in Q.items():
        p = panel(code)
        r = fit(p)
        real = att0(p)
        geos = sorted(p.geo.unique())
        gs = [month_no(v) for v in FIRST_SHOW.values()]
        perm = []
        for _ in range(PERMS):
            pick = rng.choice(geos, len(gs), replace=False)
            q = p.copy()
            q["gp"] = q.geo.map(dict(zip(pick, rng.permutation(gs)))).fillna(0).astype(int)
            perm.append(att0(q, "gp"))
        p_perm = float(np.mean(np.abs(perm) >= abs(real)))
        out[name] = r | {"att0_direct": real, "permutation_p": p_perm, "countries": len(geos),
                         "treated": sorted(p[p.g > 0].geo.unique())} | label(r, p_perm)
        if name == "accommodation":
            out["never_treated_only"] = fit(p, control="nevertreated")["month0"]
            q = p.copy()
            q["g12"] = np.where(q.g > 0, q.g - 12, 0)
            out["placebo_2023"] = fit(q, g="g12")["month0"]
            out["leave_one_out"] = {c: fit(p[p.geo != c])["month0"]["att"] for c in sorted(p[p.g > 0].geo.unique())}
            h = pd.read_csv(R / "eras-inflation-hicp.csv")
            h = h[h.coicop == code].set_index(["geo", "month"])["index"]
            yoy = {g: 100 * (np.log(h[(g, "2024-08")]) - np.log(h[(g, "2023-08")]))
                   for g in set(h.index.get_level_values(0)) if (g, "2024-08") in h and (g, "2023-08") in h}
            ctrl = [v for g, v in yoy.items() if g not in FIRST_SHOW and g != "AT"]
            out["austria_aug2024"] = {"yoy": yoy.get("AT"), "percentile_among_controls": float(np.mean(np.array(ctrl) < yoy["AT"]))}
    (R / "eras-inflation-results.json").write_text(json.dumps(out, indent=1))
    print("written eras-inflation-results.json")


if __name__ == "__main__":
    main()
