"""Q-A: the two valorisation rules and the three revenue paths (design §2.2, §2.3, §2.6, §2.7, §4, §6).
Integers and Fractions only; Decimal for the published inflation rates."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

import config as C


def step_up(amount: int, num: int, den: int) -> int:
    return -((-amount * num) // den)                    # ceiling in integers


def compound_exceeds(window: list[Decimal], threshold: Fraction) -> bool:
    prod = Fraction(1)
    for p in window:
        prod *= 1 + Fraction(p) / 100
    return prod - 1 > threshold


def inflation_series(csu_2025: Decimal, cnb_annual: Mapping[int, Decimal], shock: int = 0) -> dict[int, Decimal]:
    """2025 is ČSÚ's published figure; 2026 on is the ČNB path, else 2.0 %, all shifted by the shock (§2.6)."""
    out = {2025: Decimal(csu_2025)}
    for y in C.PATH_YEARS[1:]:
        out[y] = Decimal(cnb_annual.get(y, C.CNB_TARGET)) + shock
    return out


def price_levels(infl: Mapping[int, Decimal]) -> dict[int, Fraction]:
    lvl, out = Fraction(1), {2026: Fraction(1)}
    for y in C.YEARS:
        lvl *= 1 + Fraction(infl[y]) / 100
        out[y] = lvl
    return out


def current_law_steps(infl: Mapping[int, Decimal], window_start: int) -> list[int]:
    """Years Y in which the sum since the last increase exceeds 6; the step is on 1 July of Y+1. The window restarts
    with Y+1 (§2.2). Only steps that fall inside the path are returned."""
    steps, total = [], Decimal(0)
    for y in range(window_start, C.PATH_YEARS[-1]):
        total += infl[y]
        if total > C.VALORISATION_THRESHOLD_PCT:
            steps.append(y)
            total = Decimal(0)
    return steps


def monthly_amounts(b: str, infl: Mapping[int, Decimal], window_start: int = C.CURRENT_WINDOW_START,
                    notice: Mapping[str, Mapping[tuple[int, int], int]] | None = None) -> dict[int, list[int]]:
    """Monthly fee in force in each month of each path year for broadcaster b, from the statutory change of May 2025."""
    notice = C.NOTICE_OVERRIDE if notice is None else notice
    old, new = C.MONTHLY_BEFORE_MAY_2025[b], C.MONTHLY_FROM_MAY_2025[b]
    ly, lm = C.LAST_INCREASE
    cells = {}                                          # (year, month) -> amount
    for y in C.PATH_YEARS:
        for m in range(1, 13):
            if y < 2025:
                continue
            cells[(y, m)] = new if (y, m) >= (ly, lm) else old
    amount = new
    for y in current_law_steps(infl, window_start):
        amount = step_up(amount, *C.VALORISATION_STEP)
        for (yy, mm) in cells:
            if (yy, mm) >= (y + 1, C.VALORISATION_MONTH):
                cells[(yy, mm)] = amount
    own = notice.get(b)
    if own:
        first = min(own)
        current = None
        for key in sorted(cells):
            if key >= first:
                current = own[max(k for k in own if k <= key)]
                cells[key] = current
    return {y: [cells[(y, m)] for m in range(1, 13)] for y in C.PATH_YEARS}


def year_sums(months: Mapping[int, list[int]]) -> dict[int, int]:
    return {y: sum(v) for y, v in months.items()}


def bill_exceeds(window: list[Decimal], reading: str) -> bool:
    if reading == "R1":
        return sum(window, Decimal(0)) > C.BILL_THRESHOLD_PP
    if reading == "R2":
        return compound_exceeds(window, Fraction(C.BILL_THRESHOLD_PP) / 100)
    raise ValueError(reading)


def bill_path(base: int, infl: Mapping[int, Decimal], reading: str) -> tuple[dict[int, int], list[dict]]:
    """Amounts for 2027-2030 and the trigger records. A crossing in Y raises the amount from Y+1 and the next window
    starts at Y (the year before the increase, counted again), as §10a(3) is worded (design §2.3, L2)."""
    amounts = {C.YEARS[0]: base}
    triggers: list[dict] = []
    start = C.BILL_WINDOW_START
    for t in C.YEARS[1:]:
        y = t - 1
        window = [infl[k] for k in range(start, y + 1)]
        amount = amounts[t - 1]
        if bill_exceeds(window, reading):
            amount = step_up(amount, *C.BILL_STEP)
            triggers.append({"crossed_in": y, "raised_from": t, "window": [start, y]})
            start = y
        amounts[t] = amount
    return amounts, triggers


@dataclass(frozen=True)
class QaInputs:
    csu_2025: Decimal
    cnb_annual: Mapping[int, Decimal]
    fee_line_2026: Mapping[str, Fraction | None]       # CZK; None if a budget has no separate fee line
    realised_2025: Mapping[str, Fraction]              # CZK, annual report


def baseline_2026(inp: QaInputs, b: str, baseline: str, sums: Mapping[int, int]) -> Fraction:
    line = inp.fee_line_2026.get(b)
    if baseline == "A" and line is not None:
        return Fraction(line)                          # a broadcaster without a fee line falls back to B
    s25 = 4 * C.MONTHLY_BEFORE_MAY_2025[b] + 8 * C.MONTHLY_FROM_MAY_2025[b]
    return Fraction(inp.realised_2025[b]) * sums[2026] / s25


def qa_member(inp: QaInputs, shock: int, reading: str, baseline: str,
              window_start: int = C.CURRENT_WINDOW_START) -> dict:
    infl = inflation_series(inp.csu_2025, inp.cnb_annual, shock)
    pl = price_levels(infl)
    nominal: dict[str, dict[str, dict[int, Fraction]]] = {"p1": {}, "p2": {}, "p3": {}}
    triggers: dict[str, list[dict]] = {}
    steps = current_law_steps(infl, window_start)
    base_used = {}
    for b in C.BROADCASTERS:
        sums = year_sums(monthly_amounts(b, infl, window_start))
        r26 = baseline_2026(inp, b, baseline, sums)
        base_used[b] = r26
        nominal["p1"][b] = {t: r26 * sums[t] / sums[2026] for t in C.YEARS}
        amounts, triggers[b] = bill_path(C.BILL_2027[b], infl, reading)
        nominal["p2"][b] = {t: Fraction(amounts[t]) for t in C.YEARS}
        nominal["p3"][b] = {t: Fraction(C.BILL_2027[b]) for t in C.YEARS}
    real = {p: sum(v / pl[t] for per in nominal[p].values() for t, v in per.items()) for p in nominal}
    return {
        "shock": shock, "reading": reading, "baseline": baseline,
        "inflation": infl, "price_level": pl, "current_law_steps": steps, "bill_triggers": triggers,
        "baseline_2026": base_used, "nominal": nominal, "real": real,
        "x": (real["p1"] - real["p2"]) / 10**9,
        "x_13": (real["p1"] - real["p3"]) / 10**9, "x_23": (real["p2"] - real["p3"]) / 10**9,
        "paths_2_and_3_coincide": all(not t for t in triggers.values()),
    }


def qa_members(inp: QaInputs, window_start: int = C.CURRENT_WINDOW_START) -> list[dict]:
    return [qa_member(inp, s, r, bl, window_start) for s in C.SHOCKS for r in C.READINGS for bl in C.BASELINES]


def qa_label(xs: list[Fraction]) -> str:
    tie = C.TIE_BN
    if all(x >= tie for x in xs):
        return "bill lower"
    if all(x <= -tie for x in xs):
        return "bill higher"
    if all(abs(x) < tie for x in xs):
        return "about equal"
    return "depends on the assumption"
