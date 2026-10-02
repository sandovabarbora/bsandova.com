"""Power for H3 (design §7): EU accession on the share of a voter's points, by simulation on the participation
structure only (contestants.csv, columns year and to_country; no points read).

Simplification for power only: every participant votes in a final in which every other participant performs; the
voter gives 12, 10, 8 … 1 to its top ten by latent score = song appeal + pair affinity + δ·(both in the EU) + noise.
Outcome: share of the voter's points to the performer. Estimate: Gardner's two-stage DiD, average of event years
0 … +5, clustered by undirected pair (first-stage uncertainty ignored, so power is slightly optimistic).

    uv run --with pandas --with numpy --with pyfixest python tools/eurovision/power_h3.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

ROOT = Path(__file__).resolve().parents[2]
RNG = np.random.default_rng(20261003)
ALIAS = {"Czech Republic": "Czechia", "North MacedoniaN.Macedonia": "North Macedonia"}
EU = {"Belgium": 1958, "France": 1958, "Germany": 1958, "Italy": 1958, "Luxembourg": 1958, "Netherlands": 1958,
      "Denmark": 1973, "Ireland": 1973, "United Kingdom": 1973, "Greece": 1981, "Portugal": 1986, "Spain": 1986,
      "Austria": 1995, "Finland": 1995, "Sweden": 1995, "Cyprus": 2004, "Czechia": 2004, "Estonia": 2004,
      "Hungary": 2004, "Latvia": 2004, "Lithuania": 2004, "Malta": 2004, "Poland": 2004, "Slovakia": 2004,
      "Slovenia": 2004, "Bulgaria": 2007, "Romania": 2007, "Croatia": 2013}
part = {}
for k, v in json.loads((ROOT / "tools/data/eurovision/participation.json").read_text()).items():
    part.setdefault(ALIAS.get(k, k), set()).update(v)
years = [y for y in range(1975, 2024) if y != 2020]
countries = sorted(part)
aff = {(i, j): RNG.normal(0, 0.6) for i in countries for j in countries if i != j}


def eu(c, y):
    return c in EU and EU[c] <= y and not (c == "United Kingdom" and y >= 2020)


def draw(delta):
    rows = []
    for y in years:
        cs = [c for c in countries if y in part[c]]
        appeal = {c: RNG.normal() for c in cs}
        for i in cs:
            cand = [j for j in cs if j != i]
            s = np.array([appeal[j] + aff[i, j] + delta * (eu(i, y) and eu(j, y)) + RNG.normal() for j in cand])
            pts = np.zeros(len(cand)); pts[np.argsort(-s)[:10]] = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
            for j, p in zip(cand, pts):
                rows.append((i, j, y, p / 58))
    d = pd.DataFrame(rows, columns=["i", "j", "y", "share"])
    first = {}
    for (i, j), g in d.groupby(["i", "j"]):
        both = [y for y in g.y if eu(i, y) and eu(j, y)]
        first[(i, j)] = min(both) if both else None
    d["g"] = [first[(i, j)] for i, j in zip(d.i, d.j)]
    d = d[~((d.g.notna()) & (d.g <= 1975)) & ~(d.i.eq("United Kingdom") | d.j.eq("United Kingdom"))]
    d["e"] = d.y - d.g
    pre = d[d.g.notna() & (d.e < 0)].groupby(["i", "j"]).size()
    keep = set(pre[pre >= 3].index)
    d = d[d.g.isna() | np.array([(i, j) in keep for i, j in zip(d.i, d.j)])]
    d["pair"] = d.i + ">" + d.j
    d["upair"] = [">".join(sorted((a, b))) for a, b in zip(d.i, d.j)]
    d["treated"] = (d.e >= 0).astype(int)
    untreated = d[d.treated == 0]
    fe = pf.feols("share ~ 1 | pair + y", data=untreated)
    d = d[d.pair.isin(untreated.pair.unique()) & d.y.isin(untreated.y.unique())].copy()
    d["res"] = d.share - fe.predict(newdata=d)
    w = d[(d.treated == 0) | ((d.e >= 0) & (d.e <= 5))]
    w = w.dropna(subset=["res"])
    m = pf.feols("res ~ treated", data=w, vcov={"CRV1": "upair"})
    base = d[(d.e >= -5) & (d.e <= -1)].share.mean()
    return m.coef()["treated"], m.se()["treated"], base


for delta in (0.0, 0.1, 0.2, 0.3):
    out = [draw(delta) for _ in range(20)]
    b = np.array([o[0] for o in out]); se = np.array([o[1] for o in out]); base = np.mean([o[2] for o in out])
    print(f"delta {delta:.1f}: effect {b.mean():.4f} share points ({100 * b.mean() / base:.0f} % of pre mean {base:.3f}),"
          f" se {se.mean():.4f}, power {(b - 1.96 * se > 0).mean():.2f}")
