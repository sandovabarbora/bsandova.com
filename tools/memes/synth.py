"""Made-up pageview panels for the tests, the power simulations and the CLI's --synthetic dry run. Never real data.

Each group has its own AR(1) factor (phi 0.8, innovation sd 0.1) that moves its target and controls together,
plus white idiosyncratic noise (sd 0.1); the target loads on the factor with `beta`. `common_sd` adds one AR(1)
factor shared by all groups, the way actors in general move together.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

WEEK = np.array([0.4, 0.5, 0.5, 0.4, 0.2, -0.8, -1.0])  # a weekday pattern: weekends low
Bump = tuple[str, str, float, float]  # (column or "controls:<target>", date, size, decay in days)


def _ar1(rng: np.random.Generator, n: int, phi: float, sd: float) -> np.ndarray:
    x, shocks = np.zeros(n), rng.normal(0, sd, n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + shocks[t]
    return x


def synthetic_panel(seed: int, groups: Mapping[str, Sequence[str]], start: str = "2021-01-01", end: str = "2024-12-31",
                    bumps: Sequence[Bump] = (), beta: float = 1.0, level: float = 6.0, phi: float = 0.8,
                    sd: float = 0.1, common_sd: float = 0.0,
                    weekday: Mapping[str, float] | None = None) -> pd.DataFrame:
    """Daily views (not logs) for every article of `groups` ({target: controls}). A bump adds size * exp(-t / decay)
    to log1p views from its date on, to one column or to all controls of one target ("controls:<target>")."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    cols: dict[str, np.ndarray] = {}
    common = _ar1(rng, len(days), phi, common_sd) if common_sd else 0.0
    for target, controls in groups.items():
        factor = _ar1(rng, len(days), phi, sd) + common
        for name in controls:
            cols[name] = level + rng.uniform(-0.5, 0.5) + factor + rng.normal(0, sd, len(days))
        cols[target] = level + beta * factor + rng.normal(0, sd, len(days))
    logs = pd.DataFrame(cols, index=days)
    for col, date, size, decay in bumps:
        t = (days - pd.Timestamp(date)).days.to_numpy()
        shape = np.where(t >= 0, size * np.exp(-np.clip(t, 0, None) / decay), 0.0)
        targets = [c for c in groups[col.split(":", 1)[1]]] if col.startswith("controls:") else [col]
        for name in targets:
            logs[name] = logs[name] + shape
    for col, amp in (weekday or {}).items():
        logs[col] = logs[col] + amp * WEEK[days.dayofweek.to_numpy()]
    return np.expm1(logs)
