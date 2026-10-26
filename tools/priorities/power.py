"""Detectable elasticity of the priorities design (§3), on made-up series only: no Czech value is read.

Ten topics, waves as in the study (18 for ParlaCAP alone, 41 for 2004–2025), log concern an AR(1) per topic with a
shock shared within a wave, log attention responding to log concern with elasticity β plus its own AR(1) noise. For each
β on a grid and each noise level, the share of simulated panels whose 95 % interval from the static PPML model lies
wholly above 0.10 (supported) and the median width of the 90 % interval (the rule for underpowered is a width above
0.20). Intervals here are the wild cluster bootstrap's (199 draws, to keep the run short); the study uses 9 999 and a
randomisation interval as well, so these widths are a lower bound.

Writes docs/research/priorities-power.json.

    nice -n 20 uv run --no-project --with numpy --with pandas --with statsmodels python tools/priorities/power.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(__file__).resolve().parents[2] / "docs" / "research" / "priorities-power.json"
TOPICS, SIMS, BOOT, SEED = 10, 50, 199, 20261014
BETAS = (0.0, 0.1, 0.2, 0.4)
NOISE = (0.2, 0.4)          # sd of the attention noise on the log scale
RHO_C, RHO_A, SHARED = 0.7, 0.5, 0.15


def panel(waves: int, beta: float, noise: float, rng) -> pd.DataFrame:
    base_c = rng.uniform(np.log(0.02), np.log(0.4), TOPICS)
    base_a = rng.uniform(np.log(0.01), np.log(0.15), TOPICS)
    c = np.zeros((TOPICS, waves))
    e = np.zeros((TOPICS, waves))
    wave_shock = rng.normal(0, SHARED, waves)
    for t in range(waves):
        prev_c = c[:, t - 1] if t else 0
        prev_e = e[:, t - 1] if t else 0
        c[:, t] = RHO_C * prev_c + rng.normal(0, 0.3, TOPICS) + wave_shock[t]
        e[:, t] = RHO_A * prev_e + rng.normal(0, noise, TOPICS)
    log_c = base_c[:, None] + c
    log_a = base_a[:, None] + beta * c + e
    k, t = np.meshgrid(np.arange(TOPICS), np.arange(waves), indexing="ij")
    return pd.DataFrame({"topic": k.ravel(), "wave": t.ravel(), "log_c": log_c.ravel(), "a": np.exp(log_a.ravel())})


def design(df: pd.DataFrame) -> np.ndarray:
    fe = pd.get_dummies(df[["topic", "wave"]].astype(str), drop_first=True, dtype=float)
    return np.column_stack([df["log_c"], np.ones(len(df)), fe.to_numpy()])


def fit(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    return sm.GLM(y, X, family=sm.families.Poisson()).fit().params


def wild_interval(df: pd.DataFrame, rng) -> tuple[float, list[float], list[float]]:
    """Wild cluster bootstrap over topics with Webb weights, percentile of the bootstrap coefficients."""
    X, y = design(df), df["a"].to_numpy()
    b = fit(y, X)
    mu = np.exp(X @ b)
    resid = y - mu
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    draws = []
    for _ in range(BOOT):
        w = rng.choice(webb, TOPICS)[df["topic"].to_numpy()]
        draws.append(fit(np.clip(mu + w * resid, 1e-9, None), X)[0])
    d = np.array(draws)
    return b[0], list(np.quantile(d, [0.025, 0.975])), list(np.quantile(d, [0.05, 0.95]))


def main() -> None:
    rng = np.random.default_rng(SEED)
    out = []
    for waves in (18, 41):
        for noise in NOISE:
            for beta in BETAS:
                sup, widths = 0, []
                for _ in range(SIMS):
                    _, ci95, ci90 = wild_interval(panel(waves, beta, noise, rng), rng)
                    sup += ci95[0] > 0.10
                    widths.append(ci90[1] - ci90[0])
                out.append({"waves": waves, "noise": noise, "beta": beta, "share_supported": sup / SIMS,
                            "median_width_90": round(float(np.median(widths)), 3),
                            "share_underpowered": round(float(np.mean(np.array(widths) > 0.20)), 3)})
                print(out[-1], flush=True)
    OUT.write_text(json.dumps({"note": "made-up series only; see the module docstring", "settings": {
        "topics": TOPICS, "sims": SIMS, "boot": BOOT, "rho_concern": RHO_C, "rho_attention_noise": RHO_A,
        "shared_wave_shock": SHARED}, "grid": out}, indent=1) + "\n")


if __name__ == "__main__":
    main()
