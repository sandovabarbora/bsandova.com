"""Power for H1 (design §7), by simulation on the contest structure only: no vote, migrant or refugee data.

Structure from the rules: nine contests (2016–2019, 2021–2025); a final with 26 performers and 40 voters; two
semi-finals with 17 performers and 20 voters each, with both audiences in 2016–2022 only. Each audience ranks the
songs by a latent score and gives 12, 10, 8 … 1 to its top ten. Latent score = song appeal (per audience) + pair
affinity (shared by both audiences) + β_lat · x for the televote only + noise. The diaspora term x = log(1 + D) with
D = 0 for 40 % of pairs and otherwise log-normal (median 0.3 per 1 000, sd of log 1.5): assumptions, not data.
The registered model (PPML, pair + voter×round×audience + performer×round×audience effects, clustered by pair) is
fitted to each draw.

    uv run --with pyfixest --with pandas --with numpy python tools/eurovision/power.py
"""
import numpy as np
import pandas as pd
import pyfixest as pf

RNG = np.random.default_rng(20261003)
YEARS = [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
N_COUNTRIES, SIMS = 42, 60
POINTS = np.array([12, 10, 8, 7, 6, 5, 4, 3, 2, 1])
pair_aff = RNG.normal(0, 0.6, (N_COUNTRIES, N_COUNTRIES))
D = np.where(RNG.random((N_COUNTRIES, N_COUNTRIES)) < 0.4, 0.0,
             np.exp(RNG.normal(np.log(0.3), 1.5, (N_COUNTRIES, N_COUNTRIES))))
X = np.log1p(D)


def rounds():
    out = []
    for y in YEARS:
        perm = RNG.permutation(N_COUNTRIES)
        out.append((y, "final", perm[:40], perm[:26]))
        if y <= 2022:
            out.append((y, "sf1", perm[:20], perm[:17]))
            out.append((y, "sf2", perm[20:40], perm[20:37]))
    return out


def draw(beta: float, structure) -> pd.DataFrame:
    rows = []
    for y, r, voters, perf in structure:
        appeal = {a: RNG.normal(0, 1, N_COUNTRIES) for a in ("tele", "jury")}
        for i in voters:
            cand = [j for j in perf if j != i]
            for a in ("tele", "jury"):
                s = np.array([appeal[a][j] + pair_aff[i, j] + (beta * X[i, j] if a == "tele" else 0)
                              + RNG.normal(0, 1) for j in cand])
                pts = np.zeros(len(cand)); pts[np.argsort(-s)[:10]] = POINTS
                for j, p in zip(cand, pts):
                    rows.append((i, j, y, r, a, p, X[i, j]))
    d = pd.DataFrame(rows, columns=["i", "j", "y", "r", "a", "points", "x"])
    d["tele"] = (d.a == "tele").astype(int)
    d["xt"] = d.x * d.tele
    d["pair"] = d[["i", "j"]].astype(str).agg("-".join, axis=1)
    d["upair"] = [f"{min(a, b)}-{max(a, b)}" for a, b in zip(d.i, d.j)]
    d["vra"] = d.i.astype(str) + d.y.astype(str) + d.r + d.a
    d["pra"] = d.j.astype(str) + d.y.astype(str) + d.r + d.a
    return d


structure = rounds()
x90 = np.quantile(X[X > 0], 0.9)
print(f"x90 = {x90:.2f}")
for beta in (0.0, 0.1, 0.2, 0.3, 0.5):
    est, hits = [], 0
    for _ in range(SIMS):
        d = draw(beta, structure)
        f = pf.fepois("points ~ xt | pair + vra + pra", data=d, vcov={"CRV1": "upair"})
        b, se = f.coef()["xt"], f.se()["xt"]
        est.append(b); hits += (b - 1.96 * se) > 0
    b = float(np.mean(est))
    print(f"latent beta {beta:.1f}: mean PPML beta {b:.3f}, R at x90 {np.exp(b * x90):.2f}, power {hits / SIMS:.2f}")
