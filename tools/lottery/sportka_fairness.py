"""Is the Sportka draw uniform? Goodness of fit on the full 1994-2026 history, with a Monte Carlo null.

    uv run --with numpy --with pandas --with scipy --with statsmodels python tools/lottery/sportka_fairness.py

Reads assets/lottery/sportka.csv (and sportka_check_2025_2026.csv for a cross-check), writes the "fairness" key of
assets/lottery/results.json and assets/lottery/sportka_counts.csv.

1. Validation: every draw holds seven different numbers in 1..49; the 2025-26 draws agree with a second transcription.
2. Chi-square statistic of the 45 300 main numbers (6 x 2 draws x 3 775 days) against uniform. Six numbers are drawn
   without replacement, so the counts are negatively correlated and the statistic's null is not chi-square with 48 df
   (its mean is 49 x 43/49 = 43, not 48). The p-value comes from 10 000 simulated fair histories of the same size.
3. Per-number two-sided tests on the exact Binomial(7 550, 6/49) margin, Benjamini-Hochberg at 5 %.
4. The same test in three periods, with the most frequent number in each.
5. Four simulated fair histories with four seeds: the most frequent number changes with the seed.
6. Power: fair histories in which one number's weight is raised, tested with the same Monte Carlo critical value.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).parent))
from common import A, BONUS, MAIN_T1, MAIN_T2, N_NUMBERS, PER_DRAW, load_sportka, write_results  # noqa: E402

SEED = 20260929
N_NULL = 10_000
SEEDS = (42, 1957, 2026, 7)
PERIODS = [(1994, 2003), (2004, 2013), (2014, 2026)]


def counts(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return np.bincount(df[cols].to_numpy().ravel(), minlength=N_NUMBERS + 1)[1:]


def chi2(c: np.ndarray) -> float:
    e = c.sum() / N_NUMBERS
    return float(((c - e) ** 2 / e).sum())


def fair_counts(n_draws: int, rng: np.random.Generator, logw: np.ndarray | None = None) -> np.ndarray:
    """Counts of n_draws draws of 6 of 49 without replacement; with logw, weighted (Gumbel top-k) sampling."""
    out = np.zeros(N_NUMBERS, dtype=np.int64)
    for lo in range(0, n_draws, 2000):
        k = min(2000, n_draws - lo)
        key = rng.gumbel(size=(k, N_NUMBERS)) if logw is not None else rng.random((k, N_NUMBERS))
        if logw is not None:
            key = -(key + logw)
        idx = np.argpartition(key, PER_DRAW, axis=1)[:, :PER_DRAW]
        out += np.bincount(idx.ravel(), minlength=N_NUMBERS)
    return out


def null_stats(n_draws: int, n_sim: int, rng: np.random.Generator) -> np.ndarray:
    return np.array([chi2(fair_counts(n_draws, rng)) for _ in range(n_sim)])


def mc_p(obs: float, null: np.ndarray) -> dict:
    p = (1 + (null >= obs).sum()) / (1 + len(null))
    se = np.sqrt(p * (1 - p) / len(null))
    return {"p": p, "mc_se": se}


def validate(df: pd.DataFrame) -> dict:
    for cols in (MAIN_T1 + BONUS[:1], MAIN_T2 + BONUS[1:]):
        v = df[cols].to_numpy()
        assert v.min() >= 1 and v.max() <= N_NUMBERS
        assert all(len(set(r)) == 7 for r in v), "a draw without seven different numbers"
    chk = pd.read_csv(A / "sportka_check_2025_2026.csv", parse_dates=["date"])
    chk["date"] = chk["date"].dt.date
    by = {d: g for d, g in df.groupby("date")}
    agree = over = 0
    for (d, t), g in chk.groupby(["date", "draw"]):
        if d not in by:
            continue
        over += 1
        row = by[d].iloc[0]
        main = MAIN_T1 if t == 1 else MAIN_T2
        same = sorted(row[main]) == sorted(g.iloc[0][["n1", "n2", "n3", "n4", "n5", "n6"]]) and \
            row[BONUS[t - 1]] == g.iloc[0]["bonus"]
        agree += same
    return {"days": len(df), "first": df["date"].min(), "last": df["date"].max(),
            "check_draws_overlap": over, "check_draws_agree": agree,
            "check_first": chk["date"].min(), "check_last": chk["date"].max()}


def main() -> None:
    rng = np.random.default_rng(SEED)
    df = load_sportka()
    val = validate(df)
    n_days = len(df)
    n_draws = 2 * n_days
    c = counts(df, MAIN_T1 + MAIN_T2)
    obs = chi2(c)
    null = null_stats(n_draws, N_NULL, rng)
    res = {"validation": val, "n_draws": n_draws, "n_numbers": int(c.sum()), "expected": c.sum() / N_NUMBERS,
           "chi2": obs, "p_asymptotic_df48": float(stats.chi2.sf(obs, N_NUMBERS - 1)),
           "null_mean": float(null.mean()), "null_median": float(np.median(null)), "null_q95": float(np.quantile(null, 0.95)),
           "n_null": N_NULL, **{f"mc_{k}": v for k, v in mc_p(obs, null).items()},
           "cramers_v": float(np.sqrt(obs / (c.sum() * (N_NUMBERS - 1))))}

    # per number, exact binomial margin
    p0 = PER_DRAW / N_NUMBERS
    praw = np.array([stats.binomtest(int(k), n_draws, p0).pvalue for k in c])
    rej, pfdr, _, _ = multipletests(praw, alpha=0.05, method="fdr_bh")
    z = (c - n_draws * p0) / np.sqrt(n_draws * p0 * (1 - p0))
    lo, hi = stats.binom.ppf(0.025, n_draws, p0), stats.binom.ppf(0.975, n_draws, p0)
    order = np.argsort(-np.abs(z))
    res["per_number"] = {"fdr_rejections": int(rej.sum()), "min_p_fdr": float(pfdr.min()),
                         "outside_95_band": int(((c < lo) | (c > hi)).sum()), "band": [lo, hi],
                         "extremes": [{"number": int(i + 1), "count": int(c[i]), "z": float(z[i]),
                                       "p_raw": float(praw[i]), "p_fdr": float(pfdr[i])} for i in order[:4]]}
    pd.DataFrame({"number": np.arange(1, 50), "count": c, "expected": n_draws * p0, "z": z,
                  "p_raw": praw, "p_fdr": pfdr}).to_csv(A / "sportka_counts.csv", index=False, float_format="%.6g")

    # draw 1, draw 2, bonus
    groups = {}
    for name, cols in [("draw1", MAIN_T1), ("draw2", MAIN_T2)]:
        cc = counts(df, cols)
        s = chi2(cc)
        groups[name] = {"chi2": s, **mc_p(s, null_stats(n_days, 2000, rng)), "n_null": 2000}
    cb = counts(df, BONUS)
    sb = chi2(cb)  # one bonus number per draw: an exact multinomial, the chi-square null holds
    groups["bonus"] = {"chi2": sb, "p": float(stats.chi2.sf(sb, N_NUMBERS - 1)), "n": int(cb.sum())}
    res["groups"] = groups

    # periods and the most frequent number
    per = []
    for a, b in PERIODS:
        sub = df[(df["rok"] >= a) & (df["rok"] <= b)]
        cc = counts(sub, MAIN_T1 + MAIN_T2)
        s = chi2(cc)
        per.append({"from": a, "to": b, "days": len(sub), "chi2": s,
                    **mc_p(s, null_stats(2 * len(sub), 2000, rng)), "n_null": 2000,
                    "hottest": int(np.argmax(cc) + 1), "hottest_count": int(cc.max()), "expected": cc.sum() / 49})
    res["periods"] = per
    res["hottest_overall"] = {"number": int(np.argmax(c) + 1), "count": int(c.max())}

    # four fair histories, four seeds
    seeds = []
    for sd in SEEDS:
        r = np.random.default_rng(sd)
        cc = fair_counts(n_draws, r)
        seeds.append({"seed": sd, "chi2": chi2(cc), "hottest": int(np.argmax(cc) + 1), "hottest_count": int(cc.max()),
                      "p_real_vs_seed_null": mc_p(obs, null_stats(n_draws, 2000, np.random.default_rng(sd + 1)))["p"]})
    res["seeds"] = seeds

    # power against one favoured number
    crit = res["null_q95"]
    power = []
    for ratio in (1.05, 1.10, 1.20):
        logw = np.zeros(N_NUMBERS)
        logw[0] = np.log(ratio)
        hits, incl = 0, []
        for _ in range(1000):
            cc = fair_counts(n_draws, rng, logw)
            hits += chi2(cc) > crit
            incl.append(cc[0] / (n_draws * p0))
        power.append({"weight": ratio, "inclusion_ratio": float(np.mean(incl)), "power": hits / 1000, "sims": 1000})
    res["power"] = power
    write_results("fairness", res)


if __name__ == "__main__":
    main()
