"""Eurojackpot: how ticket sales respond to the jackpot, checked against the draws, and the expected value per column.

    uv run --with numpy --with pandas --with scipy python tools/lottery/eurojackpot_model.py

Reads the 124 draws with jackpot and win flag in assets/lottery/eurojackpot.csv (28 February 2025 to 5 May 2026) and
writes the "eurojackpot" key of assets/lottery/results.json and assets/lottery/ej_curves.csv.

Model. Columns sold N(J) = N0 (J / 10 M EUR)^beta; with N columns picked uniformly at random, the jackpot is won with
probability 1 - exp(-N / 139 838 160); y ~ Bernoulli. Priors log N0 ~ N(15, 3), beta ~ N(0.5, 1); the posterior is
computed on a 130 x 140 grid. Posterior predictive check: 4 000 parameter draws, simulated wins in six jackpot bins,
two-sided per-bin p-values and a global chi-square discrepancy. Expected value of one 2 EUR column: the jackpot
(J times the chance of hitting it times the expected share, E[1/(1+K)], K ~ Poisson(N/C) co-winners) plus eleven
lower tiers, each a_i x 1 EUR x (1 - exp(-N p_i)) with the published prize-fund shares a_i; the whole posterior of N
is carried through. Dilution: the expected jackpot share of a combination chosen by pi times as many players as
average, E[1/(1+K)] with K ~ Poisson(pi N/C); the gain over an average combination is also given for pi = 0.2, 0.4
and 0.7, since pi is assumed, not measured.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import logsumexp

sys.path.insert(0, str(Path(__file__).parent))
from common import (A, EJ_COMBINATIONS as C, EJ_J_MIN, EJ_POOL_PER_COLUMN, EJ_PRICE, EJ_TIERS,  # noqa: E402
                    load_eurojackpot, share_if_won, write_results)

SEED = 20260929
G_LOGN0 = np.linspace(13.0, 19.5, 130)
G_BETA = np.linspace(-0.5, 3.0, 140)
BINS = [10, 30, 50, 70, 90, 110, 121]
LEVELS = [10e6, 25e6, 50e6, 75e6, 100e6, 120e6]
PI = {"unpopular": 0.4, "average": 1.0, "popular": 2.5}
PI_SENSITIVITY = [0.2, 0.4, 0.7]  # popularity of the unpopular combination, varied for the gain over an average one


def log_post(log_j, y):
    ln = G_LOGN0[:, None, None] + G_BETA[None, :, None] * log_j[None, None, :]
    p = np.clip(-np.expm1(-np.exp(ln) / C), 1e-12, 1 - 1e-12)
    ll = (y * np.log(p) + (1 - y) * np.log1p(-p)).sum(-1)
    return ll + stats.norm.logpdf(G_LOGN0, 15, 3)[:, None] + stats.norm.logpdf(G_BETA, 0.5, 1)[None, :]


def summary(v, w=None):
    if w is None:
        return {"mean": float(np.mean(v)), "lo": float(np.quantile(v, 0.025)), "hi": float(np.quantile(v, 0.975))}
    o = np.argsort(v)
    cw = np.cumsum(w[o])
    q = lambda a: float(v[o][min(np.searchsorted(cw, a), len(v) - 1)])  # noqa: E731
    return {"mean": float((v * w).sum()), "lo": q(0.025), "hi": q(0.975)}


def ev_column(J, N):
    """Expected payout of one column (EUR), jackpot and lower tiers, for jackpot J and N columns sold."""
    p1 = EJ_TIERS[0][2] / C
    jack = J * p1 * share_if_won(N / C)
    lower = sum(a * EJ_POOL_PER_COLUMN * -np.expm1(-N * k / C) for _, a, k in EJ_TIERS[1:])
    return jack, lower


def main() -> None:
    rng = np.random.default_rng(SEED)
    df = load_eurojackpot()
    log_j = np.log(df["jackpot_eur"].to_numpy() / EJ_J_MIN)
    y = df["won"].to_numpy()
    lp = log_post(log_j, y)
    post = np.exp(lp - logsumexp(lp))
    mb, mn = post.sum(0), post.sum(1)
    beta = summary(G_BETA, mb)
    logn0 = summary(G_LOGN0, mn)
    res = {"draws": len(df), "wins": int(y.sum()), "from": df["draw_date"].min().date(), "to": df["draw_date"].max().date(),
           "jackpot_min": float(df["jackpot_eur"].min()), "jackpot_max": float(df["jackpot_eur"].max()),
           "draws_at_cap": int((df["jackpot_eur"] >= 110e6).sum()),
           "beta": beta, "p_beta_gt_0": float(mb[G_BETA > 0].sum()), "log_n0": logn0,
           "n0": {k: float(np.exp(v)) for k, v in logn0.items()}}

    # draws from the grid posterior
    S = 4000
    idx = rng.choice(post.size, size=S, p=post.ravel())
    s_ln0, s_b = G_LOGN0[idx // len(G_BETA)], G_BETA[idx % len(G_BETA)]
    s_ln0 = s_ln0 + rng.uniform(-0.5, 0.5, S) * (G_LOGN0[1] - G_LOGN0[0])  # jitter within the grid cell
    s_b = s_b + rng.uniform(-0.5, 0.5, S) * (G_BETA[1] - G_BETA[0])

    # posterior predictive check by jackpot bin
    jm = df["jackpot_eur"].to_numpy() / 1e6
    b = np.digitize(jm, BINS[1:-1])
    P = -np.expm1(-np.exp(s_ln0[:, None] + s_b[:, None] * log_j[None, :]) / C)
    sim = rng.random(P.shape) < P
    pred = np.stack([sim[:, b == k].sum(1) for k in range(len(BINS) - 1)], 1)
    obs = np.array([y[b == k].sum() for k in range(len(BINS) - 1)])
    mean = pred.mean(0)
    disc = lambda w: (((w - mean) ** 2) / mean).sum(-1)  # noqa: E731
    bins = []
    for k in range(len(BINS) - 1):
        pk = pred[:, k]
        bins.append({"bin": f"{BINS[k]}–{min(BINS[k + 1], 120)}", "draws": int((b == k).sum()), "observed": int(obs[k]),
                     "pred_mean": float(mean[k]), "pred_lo": float(np.quantile(pk, 0.025)), "pred_hi": float(np.quantile(pk, 0.975)),
                     "pp_p": float(min(1.0, 2 * min((pk >= obs[k]).mean(), (pk <= obs[k]).mean())))})
    res["ppc"] = {"draws_from_posterior": S, "bins": bins, "discrepancy_obs": float(disc(obs)),
                  "pp_p_global": float((disc(pred) >= disc(obs)).mean())}
    # calibration by quartile of the posterior-mean win probability
    pm = P.mean(0)
    o = np.argsort(pm)
    q = np.array_split(o, 4)
    res["calibration"] = [{"quartile": i + 1, "n": len(g), "predicted": float(pm[g].mean()), "observed": float(y[g].mean())}
                          for i, g in enumerate(q)]

    # columns sold, expected value and dilution by jackpot
    levels, curve = [], []
    for J in np.concatenate([LEVELS, np.linspace(10e6, 120e6, 45)]):
        N = np.exp(s_ln0 + s_b * np.log(J / EJ_J_MIN))
        jack, lower = ev_column(J, N)
        tot = jack + lower
        lam = N / C
        p1 = 1 / C
        gain = J * p1 * (share_if_won(PI["unpopular"] * lam) - share_if_won(lam))
        ratio = share_if_won(PI["unpopular"] * lam) / share_if_won(PI["popular"] * lam)
        row = {"jackpot": float(J), "N": summary(N), "p_win_draw": summary(-np.expm1(-lam)), "ev": summary(tot),
               "ev_jackpot": summary(jack), "ev_lower": summary(lower), "rtp": summary(tot / EJ_PRICE),
               "loss": summary(EJ_PRICE - tot),
               "share": {k: summary(share_if_won(v * lam)) for k, v in PI.items()},
               "ratio_unpop_pop": summary(ratio), "ev_gain_unpopular": summary(gain),
               "ev_gain_by_pi": {str(pi): summary(J * p1 * (share_if_won(pi * lam) - share_if_won(lam)))
                                 for pi in PI_SENSITIVITY}}
        (levels if len(levels) < len(LEVELS) else curve).append(row)
    res["levels"] = levels
    res["popularity"] = PI
    pd.DataFrame([{"jackpot_eur": r["jackpot"], "N_mean": r["N"]["mean"], "N_lo": r["N"]["lo"], "N_hi": r["N"]["hi"],
                   "ev_mean": r["ev"]["mean"], "ev_lo": r["ev"]["lo"], "ev_hi": r["ev"]["hi"],
                   "ev_jackpot_mean": r["ev_jackpot"]["mean"], "ev_lower_mean": r["ev_lower"]["mean"]}
                  for r in curve]).to_csv(A / "ej_curves.csv", index=False, float_format="%.6g")
    pd.DataFrame({"draw_date": df["draw_date"].dt.date, "jackpot_eur": df["jackpot_eur"], "won": y,
                  "bin": [bins[k]["bin"] for k in b]}).to_csv(A / "ej_draws_2025_2026.csv", index=False)
    for r in levels:
        print(f"{r['jackpot']/1e6:>5.0f}M N {r['N']['mean']/1e6:5.1f} [{r['N']['lo']/1e6:.1f},{r['N']['hi']/1e6:.1f}]  "
              f"EV {r['ev']['mean']:.3f} [{r['ev']['lo']:.3f},{r['ev']['hi']:.3f}]  ratio {r['ratio_unpop_pop']['mean']:.3f}  "
              f"gain {r['ev_gain_unpopular']['mean']:.4f}")
    print({k: res[k] for k in ("beta", "p_beta_gt_0", "n0")}, res["ppc"]["pp_p_global"])
    for x in bins:
        print(x)
    print(res["calibration"])
    write_results("eurojackpot", res)


if __name__ == "__main__":
    main()
