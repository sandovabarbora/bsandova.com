import numpy as np

from nhl.analysis import fit_prior, longest, streak


def test_longest_run():
    assert longest([1, 1, 0, 1, 1, 1, 0]) == 3
    assert longest([]) == 0


def test_beta_binomial_prior_recovers_a_planted_rate():
    rng = np.random.default_rng(1)
    shots = rng.integers(40, 250, 2000)
    rates = rng.beta(25, 175, 2000)
    goals = rng.binomial(shots, rates)
    hist = {"skaters": {"s": [[i, "C", int(g), int(s)] for i, (g, s) in enumerate(zip(goals, shots))]}}
    a, b, n = fit_prior(hist, 30)
    assert n == 2000
    assert abs(a / (a + b) - 0.125) < 0.005
    assert 120 < a + b < 300


def test_a_planted_streak_is_rarer_than_a_shuffled_one():
    log = [{"gameDate": f"2026-10-{d:02d}", "points": int(d <= 10)} for d in range(1, 31)]
    s = streak(log, np.random.default_rng(0))
    assert s["longest"] == 10
    assert s["p_ge"] < 0.01
