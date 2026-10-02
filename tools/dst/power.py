"""Power for H1 (design §7), from published monthly aggregates only, by simulating the registered model.

Inputs (police monthly summaries, cumulative Jan–Oct and Jan–Nov 2025): 2 268 and 2 556 crashes with a pedestrian,
so about 9.6 a day in November. Hour shares are assumptions, not data: evening 16–18 = 25 %, morning 06–07 = 10 %,
control 10–13 = 22 % of a day's pedestrian crashes. Simulated at national level (district effects do not change
power for a ratio of hour groups much), years = 10 (2016–2025, the yearly record files available), overdispersion none, then 1.2× variance as a margin.

    uv run --with statsmodels --with numpy python tools/dst/power.py
"""
import numpy as np
import statsmodels.api as sm

RNG = np.random.default_rng(20261025)
PER_DAY, YEARS, SIMS = 9.6, 10, 1000
TRENDS = False  # registered primary after the change note of 2 Oct 2026; True = the original specification
SHARE = {"evening": 0.25 / 3, "morning": 0.10 / 2, "control": 0.22 / 4}  # per hour
HOURS = [("morning", 6), ("morning", 7), *[("control", h) for h in (10, 11, 12, 13)],
         *[("evening", h) for h in (16, 17, 18)]]
days = [d for d in range(-14, 15) if d != 0]


def design():
    rows = []
    for y in range(YEARS):
        for d in days:
            for g, h in HOURS:
                rows.append((y, d, g, h))
    return rows


def simulate(ratio, rows):
    post = np.array([d > 0 for _, d, _, _ in rows], float)
    ev = np.array([g == "evening" for _, _, g, _ in rows], float)
    mo = np.array([g == "morning" for _, _, g, _ in rows], float)
    t = np.array([d for _, d, _, _ in rows], float)
    hour = np.array([h for *_, h in rows])
    year = np.array([y for y, *_ in rows])
    dow = (np.array([d for _, d, _, _ in rows]) % 7)
    mu = PER_DAY * np.array([SHARE[g] for _, _, g, _ in rows]) * np.where((post == 1) & (ev == 1), ratio, 1.0)
    X = np.column_stack([post, post * ev, post * mo, t, *([t * ev, t * mo] if TRENDS else []),
                         *[(hour == h).astype(float) for h in sorted(set(hour))[1:]],
                         *[(year == k).astype(float) for k in range(1, YEARS)],
                         *[(dow == k).astype(float) for k in range(1, 7)], np.ones(len(rows))])
    hits = 0
    for _ in range(SIMS):
        y = RNG.poisson(mu)
        r = sm.GLM(y, X, family=sm.families.Poisson()).fit()
        b, se = r.params[1], r.bse[1] * np.sqrt(1.2)
        hits += (b - 1.96 * se) > 0
    return hits / SIMS, se


rows = design()
for ratio in (1.15, 1.25, 1.35, 1.5, 1.75):
    p, se = simulate(ratio, rows)
    print(f"ratio {ratio:.2f}: power {p:.2f} (SE of log ratio ≈ {se:.3f})")
