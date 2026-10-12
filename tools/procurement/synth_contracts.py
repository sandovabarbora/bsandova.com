"""Made-up contract values with known rounding and known bunching, for the tests and the power simulation."""
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
    round_100k: float = 0.15  # share of contracts rounded up to the next 100 000
    round_1m: dict = field(default_factory=lambda: {"pre": 0.02, "post": 0.02})  # share rounded to the nearest million
    move: dict = field(default_factory=lambda: {"pre": 0.0, "post": 0.0})  # share moved from just above T into (0.95 T, T]
    move_from: float = 0.05  # moved contracts come from (T, (1 + move_from) T]
    move_concentration: float = 0.5  # gamma shape of authority propensity to move; small = few authorities do it


def pareto(rng, n: int, alpha: float) -> np.ndarray:
    a = 1 - alpha
    u = rng.random(n)
    return (LO ** a + u * (HI ** a - LO ** a)) ** (1 / a)


def draw(world: World, seed: int = 1):
    rng = np.random.default_rng(seed)
    size = rng.lognormal(0, world.size_sigma, world.authorities)
    propensity = rng.gamma(world.move_concentration, 1 / world.move_concentration, world.authorities)
    vals, auth, per = [], [], []
    for p, n in (("pre", world.n_pre), ("post", world.n_post)):
        v = pareto(rng, n, world.alpha)
        a = rng.choice(world.authorities, n, p=size / size.sum())
        r = rng.random(n)
        v = np.where(r < world.round_100k, np.ceil(v / 100_000) * 100_000, v)
        m = rng.random(n) < world.round_1m[p]
        v = np.where(m, np.maximum(np.round(v / 1_000_000), 1) * 1_000_000, v)
        limits = OLD if p == "pre" else NEW
        for t in limits.values():
            near = (v > t) & (v <= (1 + world.move_from) * t)
            moved = near & (rng.random(n) < np.clip(world.move[p] * propensity[a], 0, 1))
            v = np.where(moved, t - rng.random(n) * 0.05 * t, v)
        keep = (v > LO) & (v <= HI)
        vals.append(v[keep]), auth.append(a[keep]), per.append(np.full(keep.sum(), p))
    return np.concatenate(vals), np.concatenate(auth), np.concatenate(per)
