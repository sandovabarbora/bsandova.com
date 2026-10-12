"""Made-up contract prices with known rounding and known bunching, for the tests and the power simulation."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from bunching import HI, LO, NEW, OLD


@dataclass
class World:
    n_pre: int = 200_000
    n_post: int = 50_000
    alpha: float = 1.65  # density ∝ v^−alpha, calibrated on the far bands (§9)
    authorities: int = 6_000
    size_sigma: float = 1.5  # lognormal spread of authority sizes
    tilt_sd: float = 0.0  # authority-specific value level: prices × exp(N(0, tilt_sd)) per authority
    round_100k: float = 0.15  # share rounded up to the next 100 000
    round_1m: dict = field(default_factory=lambda: {"pre": 0.02, "post": 0.02})  # share rounded to a whole million
    # rounding that drifts by magnitude: the probability is multiplied by (price / 3 M) ** drift[period]
    round_1m_drift: dict = field(default_factory=lambda: {"pre": 0.0, "post": 0.0})
    habit_shape: float | None = None  # gamma shape of an authority's round-million habit; None = same for all
    move: dict = field(default_factory=lambda: {"pre": 0.0, "post": 0.0})  # share moved from just above a limit
    move_from: float = 0.05  # moved contracts come from (T, (1 + move_from) T]
    move_exact: float = 0.0  # of the moved, the share placed at exactly T (the rest uniform in (0.95 T, T))
    relevant_share: float = 1.0  # share of contracts of the type the limit binds (the others never move)
    move_concentration: float = 0.5  # gamma shape of an authority's propensity to move


def pareto(rng, n: int, alpha: float, lo: float = LO, hi: float = HI) -> np.ndarray:
    a = 1 - alpha
    return (lo ** a + rng.random(n) * (hi ** a - lo ** a)) ** (1 / a)


def draw(world: World, seed: int = 1):
    rng = np.random.default_rng(seed)
    size = rng.lognormal(0, world.size_sigma, world.authorities)
    propensity = rng.gamma(world.move_concentration, 1 / world.move_concentration, world.authorities)
    tilt = np.exp(rng.normal(0, world.tilt_sd, world.authorities)) if world.tilt_sd else np.ones(world.authorities)
    habit = (rng.gamma(world.habit_shape, 1 / world.habit_shape, world.authorities) if world.habit_shape
             else np.ones(world.authorities))
    vals, auth, per = [], [], []
    e = 1 - world.alpha
    in_range = (LO ** e - HI ** e) / ((LO / 3) ** e - (HI * 3) ** e)
    for p, n_target in (("pre", world.n_pre), ("post", world.n_post)):
        n = int(n_target / in_range)  # about n_target land in the range
        a = rng.choice(world.authorities, n, p=size / size.sum())
        # draw on a wider support, then tilt, so the tilted prices still cover the range
        v = pareto(rng, n, world.alpha, LO / 3, HI * 3) * tilt[a]
        v = np.where(rng.random(n) < world.round_100k, np.ceil(v / 100_000) * 100_000, v)
        tilt_m = (np.maximum(v, 1.0) / 3_000_000) ** world.round_1m_drift[p]
        m = rng.random(n) < np.clip(world.round_1m[p] * habit[a] * tilt_m, 0, 1)
        v = np.where(m, np.maximum(np.round(v / 1_000_000), 1) * 1_000_000, v)
        for t in (OLD if p == "pre" else NEW).values():
            near = (v > t) & (v <= (1 + world.move_from) * t) & (rng.random(n) < world.relevant_share)
            moved = near & (rng.random(n) < np.clip(world.move[p] * propensity[a], 0, 1))
            exact = rng.random(n) < world.move_exact
            v = np.where(moved, np.where(exact, t, t - rng.uniform(1, 0.05 * t, n)), v)
        keep = (v > LO) & (v <= HI)
        vals.append(v[keep]), auth.append(a[keep]), per.append(np.full(keep.sum(), p))
    return np.concatenate(vals), np.concatenate(auth), np.concatenate(per)
