"""The pre-written readings of design §1, filled programmatically. The wording is the design's; only numbers, the
more/less choice and the conditional branches change, as the design says."""
from __future__ import annotations

from fractions import Fraction


def f2(x: Fraction | int) -> str:
    return f"{float(x):.2f}"


def _side(x: Fraction) -> str:
    return f"{f2(abs(x))} bn CZK " + ("less" if x >= 0 else "more")


def reading_a(label: str, x: Fraction, xs: list[Fraction]) -> str:
    head = "If the bill passes as introduced, ČT and ČRo would receive "
    tail = " over 2027–2030 than under current law."
    if label == "about equal":
        return head + "the same over 2027–2030 as under current law, within 0.1 bn CZK (2026 prices)."
    if label == "depends on the assumption":
        return ("Whether ČT and ČRo would receive more or less over 2027–2030 than under current law depends on the "
                f"assumption: across the range the bill gives between {_side(max(xs))} and {_side(min(xs))} (2026 prices).")
    return head + f"{_side(x)} (2026 prices)" + tail


def reading_b(y_lo: Fraction | None, y_hi: Fraction | None, z: Fraction | None, z_vat: Fraction | None,
              z_pit: Fraction | None) -> str:
    g = lambda v: "n/a" if v is None else f2(v)
    return ("Today the poorest tenth of households carries between "
            f"{g(y_lo)} and {g(y_hi)} times the share of its income that the richest tenth does (the range is the two "
            "exemption bounds; exemptions are counted by entitlement, not by actual take-up). Funded from the state "
            f"budget at the average tax structure it would be {g(z)} times; if the money came from VAT alone it would be "
            f"{g(z_vat)} times, and from personal income tax alone {g(z_pit)} times. If the amount is borrowed, "
            "current households carry nothing now.")


def reading_c(budget: Fraction, bill_2027: int, real_bill_2027: Fraction) -> str:
    d = real_bill_2027 / 10**9 - budget / 10**9
    return (f"Today ČT and ČRo get {f2(budget / 10**9)} bn CZK a year in fee revenue (2026 budgets). The bill gives "
            f"{bill_2027 / 10**9:.3f} bn CZK for 2027, which is {f2(abs(d))} bn CZK (2026 prices) "
            f"{'more' if d >= 0 else 'less'}.")


def reading_firms(firms: dict, f_after: int) -> str:
    after = (f"would carry {f2(Fraction(f_after) / 10**9)} bn CZK after (the corporate-income-tax share of the total); "
             "the two figures are not like for like.")
    if firms.get("plausible"):
        today = f"Firms and public bodies pay {f2(firms['remainder'] / 10**9)} bn CZK a year today (what remains of the " \
                "budgeted fee revenue after households, public bodies included) and "
    elif firms.get("range"):
        lo, hi = firms["range"]
        today = (f"Firms and public bodies pay between {f2(Fraction(lo) / 10**9)} and {f2(Fraction(hi) / 10**9)} bn CZK a "
                 "year today (the range from employer counts and the schedule of §5; the remainder of the budgeted fee "
                 "revenue failed the plausibility test) and ")
    else:
        today = ("Firms and public bodies pay an amount today that cannot be validated without employer counts (the "
                 "household payments are unvalidated) and ")
    return today + after
