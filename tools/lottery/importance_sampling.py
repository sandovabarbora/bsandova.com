"""Why a plain Monte Carlo cannot see the value of an unpopular Eurojackpot combination, and importance sampling can.

    uv run --with numpy --with pandas --with scipy python tools/lottery/importance_sampling.py

Run after eurojackpot_model.py: reads its posterior-mean column sales at the 120 M EUR cap from
assets/lottery/results.json and writes the "importance" key.

Setting: one 2 EUR column at a 120 M EUR jackpot with N columns sold. Two combinations, A chosen by as many players as
the average combination (popularity 1) and B by 0.4 times as many. Both win every tier with the same probability.
A lower-tier win pays that tier's expected prize, the same for A and B (popularity in lower tiers is not modelled); a
jackpot win pays J / (1 + K) with K ~ Poisson(pi N / C) co-winners. The target is D = E[payout B] - E[payout A],
known in closed form. Estimators, 10^6 simulated columns each:
  naive, independent: A and B from separate random draws;
  naive, paired: common random numbers (the same tier outcome and the same uniform for K), so D comes only from
      jackpot draws;
  importance sampling, paired: the jackpot is drawn with probability b / C (b = 10^3 to 10^6) and every draw is
      reweighted by its likelihood ratio.
95 % intervals are normal intervals from the simulated standard error. The columns needed for the naive estimators
to reach 80 % power at a two-sided 5 % level are computed from their exact variances.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from common import EJ_COMBINATIONS as C, EJ_POOL_PER_COLUMN, EJ_TIERS, RESULTS, share_if_won, write_results  # noqa: E402

SEED = 20260929
J = 120e6
PI_A, PI_B = 1.0, 0.4
N_SIM = 1_000_000
BOOSTS = (1_000, 10_000, 100_000, 1_000_000)
Z = stats.norm.ppf(0.975)


def setting():
    lv = json.loads(RESULTS.read_text())["eurojackpot"]["levels"]
    N = next(r for r in lv if r["jackpot"] == J)["N"]["mean"]
    p = np.array([k / C for _, _, k in EJ_TIERS])
    prize = np.array([0.0] + [a * EJ_POOL_PER_COLUMN * N * share_if_won(N * k / C) for _, a, k in EJ_TIERS[1:]])
    return N, p, prize


def payouts(u_tier, u_k, p_cat, prize, lam):
    """Payouts of A and B from shared uniforms: category 0 is the jackpot, 1..11 lower tiers, 12 nothing."""
    cat = np.searchsorted(np.cumsum(p_cat), u_tier, side="right").clip(0, len(p_cat) - 1)
    lower = np.where(cat < len(prize), prize[np.minimum(cat, len(prize) - 1)], 0.0)
    jack = cat == 0
    ka = stats.poisson.ppf(u_k[jack], PI_A * lam)
    kb = stats.poisson.ppf(u_k[jack], PI_B * lam)
    a, b = lower.copy(), lower.copy()
    a[jack], b[jack] = J / (1 + ka), J / (1 + kb)
    return a, b, cat


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    return {"est": float(m), "se": float(se), "lo": float(m - Z * se), "hi": float(m + Z * se)}


def exact_moments(N, p, prize):
    lam = N / C
    k = np.arange(0, 60)
    fa, fb = stats.poisson.pmf(k, PI_A * lam), stats.poisson.pmf(k, PI_B * lam)
    u = (np.arange(200_000) + 0.5) / 200_000  # coupled K_A, K_B share one uniform
    da = J / (1 + stats.poisson.ppf(u, PI_A * lam))
    db = J / (1 + stats.poisson.ppf(u, PI_B * lam))
    p1 = p[0]
    delta = p1 * J * (share_if_won(PI_B * lam) - share_if_won(PI_A * lam))
    var_paired = p1 * np.mean((db - da) ** 2) - delta ** 2
    low2 = (p[1:] * prize[1:] ** 2).sum()
    low1 = (p[1:] * prize[1:]).sum()
    def var_one(f):
        m1 = low1 + p1 * (f * J / (1 + k)).sum()
        m2 = low2 + p1 * (f * (J / (1 + k)) ** 2).sum()
        return m2 - m1 ** 2, m1
    va, ea = var_one(fa)
    vb, eb = var_one(fb)
    return delta, var_paired, va + vb, ea, eb


def main() -> None:
    N, p, prize = setting()
    lam = N / C
    p_cat = np.append(p, 1 - p.sum())
    delta, var_p, var_i, ea, eb = exact_moments(N, p, prize)
    zz = (Z + stats.norm.ppf(0.8)) ** 2
    out = {"jackpot": J, "N": N, "pi_a": PI_A, "pi_b": PI_B, "n_sim": N_SIM, "delta": delta,
           "ev_a": ea, "ev_b": eb, "p_jackpot": float(p[0]),
           "p_no_jackpot_in_n": float(np.exp(N_SIM * np.log1p(-p[0]))),
           "n_needed_independent": float(zz * var_i / delta ** 2), "n_needed_paired": float(zz * var_p / delta ** 2),
           "estimators": []}
    rng = np.random.default_rng(SEED)
    # naive, independent
    a, _, ca = payouts(rng.random(N_SIM), rng.random(N_SIM), p_cat, prize, lam)
    _, b, cb = payouts(rng.random(N_SIM), rng.random(N_SIM), p_cat, prize, lam)
    m = a.mean(), b.mean()
    se = np.sqrt(a.var(ddof=1) / N_SIM + b.var(ddof=1) / N_SIM)
    out["estimators"].append({"name": "naive, independent", "est": float(m[1] - m[0]), "se": float(se),
                              "lo": float(m[1] - m[0] - Z * se), "hi": float(m[1] - m[0] + Z * se),
                              "jackpots": int((ca == 0).sum() + (cb == 0).sum())})
    # naive, paired
    a, b, cat = payouts(rng.random(N_SIM), rng.random(N_SIM), p_cat, prize, lam)
    out["estimators"].append({"name": "naive, paired", **ci(b - a), "jackpots": int((cat == 0).sum())})
    # importance sampling, paired
    for boost in BOOSTS:
        q = boost * p[0]
        prop = p_cat.copy()
        prop[0] = q
        prop[1:] = p_cat[1:] * (1 - q) / (1 - p[0])
        a, b, cat = payouts(rng.random(N_SIM), rng.random(N_SIM), prop, prize, lam)
        w = np.where(cat == 0, p[0] / q, (1 - p[0]) / (1 - q))
        out["estimators"].append({"name": "importance sampling, ×" + f"{boost:,}".replace(",", " "), "boost": boost,
                                  **ci(w * (b - a)), "jackpots": int((cat == 0).sum())})
    for e in out["estimators"]:
        e["covers"] = bool(e["lo"] <= delta <= e["hi"])
        print(e)
    print({k: v for k, v in out.items() if k != "estimators"})
    write_results("importance", out)


if __name__ == "__main__":
    main()
