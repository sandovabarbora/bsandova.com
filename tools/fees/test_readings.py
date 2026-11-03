"""The branches of the pre-written readings (design §1, §6)."""
from __future__ import annotations

from fractions import Fraction as F

import readings as R


def test_reading_a_branches():
    assert R.reading_a("bill lower", F(25, 10), [F(2), F(3)]) == (
        "If the bill passes as introduced, ČT and ČRo would receive 2.50 bn CZK less (2026 prices) over 2027–2030 "
        "than under current law.")
    assert "1.20 bn CZK more (2026 prices)" in R.reading_a("bill higher", F(-12, 10), [F(-1), F(-2)])   # the absolute value
    assert R.reading_a("about equal", F(1, 20), [F(1, 20)]).endswith("within 0.1 bn CZK (2026 prices).")
    dep = R.reading_a("depends on the assumption", F(1), [F(3), F(-1, 2), F(1)])
    assert "depends on the assumption: across the range the bill gives between 3.00 bn CZK less and 0.50 bn CZK more" in dep
    both_less = R.reading_a("depends on the assumption", F(1), [F(3), F(1, 20)])
    assert "between 3.00 bn CZK less and 0.05 bn CZK less" in both_less                # the sign of each end is its own


def test_reading_b_with_missing_ratios_and_the_firm_sentence():
    s = R.reading_b(None, F(3, 2), F(1, 2), None, F(1, 3), "FIRMS.")
    assert "between n/a and 1.50 times" in s and "it would be 0.50 times" in s and "alone it would be n/a times" in s
    assert "and from personal income tax alone 0.33 times" in s and s.endswith("current households carry nothing now. FIRMS.")


def test_reading_c_more_and_less():
    assert R.reading_c(F(5 * 10**9), 7_807_592_000, F(7 * 10**9)).endswith("which is 2.00 bn CZK (2026 prices) more.")
    assert "7.808 bn CZK for 2027" in R.reading_c(F(5 * 10**9), 7_807_592_000, F(7 * 10**9))
    assert R.reading_c(F(9 * 10**9), 7_807_592_000, F(7 * 10**9), "X.").endswith("2.00 bn CZK (2026 prices) less. X.")


def test_reading_firms_without_a_schedule_or_a_ratio():
    base = {"remainder": F(2 * 10**9), "schedule_implied": None, "ratio_remainder_to_schedule": None}
    s = R.reading_firms(base, 10**9)
    assert s.startswith("Firms and public bodies pay 2.00 bn CZK a year today") and "schedule" not in s
    assert s.endswith("the two figures are not like for like.")
    with_sched = R.reading_firms({**base, "schedule_implied": 10**9}, 10**9)
    assert "gives 1.00 bn CZK, and the two may differ" in with_sched and "times that" not in with_sched
    assert "(the remainder is 2.00 times that)" in R.reading_firms({**base, "schedule_implied": 10**9,
                                                                    "ratio_remainder_to_schedule": F(2)}, 10**9)
