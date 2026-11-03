"""Largest-remainder allocation (design §2.1): whole crowns that sum to the whole."""
from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction


def largest_remainder(total: int, weights: Sequence[Fraction | int]) -> list[int]:
    if total < 0 or any(w < 0 for w in weights):
        raise ValueError("negative total or weight")
    w = [Fraction(x) for x in weights]
    s = sum(w)
    if s == 0:
        raise ValueError("weights sum to zero")
    exact = [total * x / s for x in w]
    parts = [int(e.numerator // e.denominator) for e in exact]
    left = total - sum(parts)
    # largest fractional part first; ties go to the lower index so the result is deterministic
    order = sorted(range(len(w)), key=lambda i: (-(exact[i] - parts[i]), i))
    for i in order[:left]:
        parts[i] += 1
    return parts
