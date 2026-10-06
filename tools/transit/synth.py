"""Synthetic control (design §4): weights, gap, placebo-in-space inference, leave-one-out.

Weights are non-negative, sum to one, and minimise the squared distance between the treated unit's pre-period outcome
and the weighted donors' (outcome lags only, no other predictors). Solved as non-negative least squares (scipy nnls).

Checked against the California Proposition 99 example of Arkhangelsky et al. (2021), whose synthetic-control
estimate is −19.6 packs per capita: `python3 tools/transit/synth.py --test`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls


def weights(y_pre: np.ndarray, X_pre: np.ndarray) -> np.ndarray:
    """y_pre: (T0,) treated; X_pre: (T0, J) donors. Returns w (J,), w >= 0, sum 1.

    Non-negative least squares with the sum-to-one constraint added as a heavily weighted extra row; the result is
    renormalised (the constraint then holds to rounding)."""
    lam = 1e3 * max(1.0, float(np.abs(X_pre).max()))
    A = np.vstack([X_pre, lam * np.ones((1, X_pre.shape[1]))])
    b = np.concatenate([y_pre, [lam]])
    w, _ = nnls(A, b, maxiter=10_000)
    return w / w.sum()


def fit(panel: pd.DataFrame, treated: str, t0: int, post: list[int]) -> dict:
    """panel: index = year, columns = units, values = outcome. Pre-period: years < t0; post: listed years."""
    pre = panel.index[panel.index < t0]
    donors = [c for c in panel.columns if c != treated]
    w = weights(panel.loc[pre, treated].to_numpy(float), panel.loc[pre, donors].to_numpy(float))
    synth = panel[donors].to_numpy(float) @ w
    gap = panel[treated].to_numpy(float) - synth
    s = pd.Series(gap, index=panel.index)
    rmspe_pre = float(np.sqrt(np.mean(s.loc[pre] ** 2)))
    rmspe_post = float(np.sqrt(np.mean(s.loc[post] ** 2)))
    return {"weights": dict(zip(donors, w.round(4))), "gap": s, "avg_post_gap": float(s.loc[post].mean()),
            "rmspe_pre": rmspe_pre, "ratio": rmspe_post / rmspe_pre if rmspe_pre > 0 else float("inf")}


def placebo(panel: pd.DataFrame, treated: str, t0: int, post: list[int]) -> dict:
    """Placebo in space: every unit treated in turn; p = rank of the treated ratio / number of units."""
    ratios = {u: fit(panel, u, t0, post)["ratio"] for u in panel.columns}
    order = sorted(ratios, key=ratios.get, reverse=True)
    rank = order.index(treated) + 1
    return {"ratios": ratios, "rank": rank, "p": rank / len(order), "min_p": 1 / len(order)}


def leave_one_out(panel: pd.DataFrame, treated: str, t0: int, post: list[int]) -> dict:
    return {d: fit(panel.drop(columns=d), treated, t0, post)["avg_post_gap"] for d in panel.columns if d != treated}


def _test() -> None:
    p = Path(__file__).resolve().parents[2] / "tools" / "data" / "transit" / "california_prop99.csv"
    d = pd.read_csv(p, sep=";")
    panel = d.pivot(index="Year", columns="State", values="PacksPerCapita")
    r = fit(panel, "California", 1989, list(range(1989, 2001)))
    print(f"California SC estimate {r['avg_post_gap']:.1f} (published −19.6); pre-RMSPE {r['rmspe_pre']:.2f}")
    top = sorted(r["weights"].items(), key=lambda kv: -kv[1])[:5]
    print("largest weights", top)
    pl = placebo(panel, "California", 1989, list(range(1989, 2001)))
    print(f"placebo rank {pl['rank']} of {len(pl['ratios'])}, p = {pl['p']:.3f}")
    assert abs(r["avg_post_gap"] + 19.6) < 1.0, "does not reproduce the published estimate"


if __name__ == "__main__":
    if "--test" in sys.argv:
        _test()
