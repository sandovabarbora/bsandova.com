"""Shared paths, constants, loaders and the results writer for the lottery study (texts/lottery.html).

Every script in tools/lottery/ reads its data from assets/lottery/ and merges its numbers into
assets/lottery/results.json under its own key, so the article, the chart specs and the static figures all read one
file. Not run on its own.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets" / "lottery"
RESULTS = A / "results.json"

# Sportka: 6 of 49 plus one bonus number, two independent draws on every drawing day
N_NUMBERS = 49
PER_DRAW = 6
MAIN_T1 = [f"{i}. cislo 1. tah" for i in range(1, 7)]
MAIN_T2 = [f"{i}. cislo 2. tah" for i in range(1, 7)]
BONUS = ["dodatkove cislo 1. tah", "dodatkove cislo 2. tah"]

# Eurojackpot since 25 March 2022: 5 of 50 and 2 of 12
EJ_COMBINATIONS = 139_838_160          # C(50,5) * C(12,2)
EJ_J_MIN = 10_000_000                  # minimum jackpot, EUR
EJ_PRICE = 2.0                         # EUR per column in euro countries
EJ_POOL_PER_COLUMN = 1.0               # 50 % of the stake goes to the prize fund
# (tier, share of the prize fund, winning combinations out of EJ_COMBINATIONS); the booster fund takes 9 %
EJ_TIERS = [
    ("5+2", 0.36, 1), ("5+1", 0.086, 20), ("5+0", 0.0485, 45), ("4+2", 0.008, 225), ("4+1", 0.010, 4_500),
    ("3+2", 0.011, 9_900), ("4+0", 0.008, 10_125), ("2+2", 0.0255, 141_900), ("3+1", 0.0285, 198_000),
    ("3+0", 0.054, 445_500), ("1+2", 0.0674, 744_975), ("2+1", 0.203, 2_838_000),
]
EJ_BOOSTER = 0.09
assert abs(sum(t[1] for t in EJ_TIERS) + EJ_BOOSTER - 1) < 5e-4  # the published shares add up to 99.99 %


def czdate(s: str) -> date:
    d, m, y = (int(x) for x in s.replace(" ", "").split(".") if x)
    return date(y, m, d)


def load_sportka() -> pd.DataFrame:
    """The Sazka (Allwyn) Sportka history, oldest draw first, with a parsed date column."""
    df = pd.read_csv(A / "sportka.csv", sep=";", encoding="ascii")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df["date"] = df["datum"].map(czdate)
    return df.sort_values("date", kind="stable").reset_index(drop=True)


def load_eurojackpot(with_jackpot: bool = True) -> pd.DataFrame:
    """Eurojackpot draws; with_jackpot keeps the 124 draws since 28 February 2025 that carry jackpot and win flag."""
    df = pd.read_csv(A / "eurojackpot.csv", parse_dates=["draw_date"])
    if with_jackpot:
        df = df[df["jackpot_eur"].notna()].copy()
        df["won"] = df["won"].astype(str).eq("True").astype(int)
    return df.sort_values("draw_date").reset_index(drop=True)


def share_if_won(m: np.ndarray | float) -> np.ndarray | float:
    """E[1/(1+K)] for K ~ Poisson(m) other winners: the expected share of a pari-mutuel prize, (1 - e^-m) / m."""
    m = np.asarray(m, dtype=float)
    out = np.where(m > 1e-12, -np.expm1(-m) / np.where(m > 1e-12, m, 1.0), 1.0 - m / 2)
    return out if out.ndim else float(out)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, date):
        return o.isoformat()
    return o


def write_results(key: str, payload: dict) -> None:
    """Merge one script's numbers into assets/lottery/results.json under `key`."""
    cur = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    cur[key] = _clean(payload)
    RESULTS.write_text(json.dumps(dict(sorted(cur.items())), ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {RESULTS.relative_to(ROOT)} [{key}]")
