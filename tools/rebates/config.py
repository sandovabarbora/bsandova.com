"""Frozen settings of the film incentive study (docs/research/rebates-design.md). No threshold, amount, date or path is
written anywhere else. Money is integers or Fractions; nothing here is a binary float."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TOOL = "tools/rebates"
DATA = ROOT / "tools/data/rebates"                  # gitignored
SNAP = DATA / "2026-11-05"
DESIGN = ROOT / "docs/research/rebates-design.md"
MANIFEST = ROOT / "docs/research/rebates-files.sha256"
STRUCTURE = ROOT / "docs/research/rebates-structure.json"
RESULTS = ROOT / "docs/research/rebates-results.json"

DESIGN_TAG = "rebates-design"
DATA_TAG = "rebates-data-step"                      # sits on the commit of this data-step code, before any outcome is read
CODE_TAG = "rebates-code"                           # freezes tools/rebates (design "Running and verification")
STAMP_TAGS = (DESIGN_TAG, DATA_TAG, CODE_TAG)


@dataclass(frozen=True)
class ListSpec:
    name: str
    path: Path
    list_date: dt.date                              # the state date printed in the file name and title (§2.1)
    years: tuple[int, int]                          # the stated suffix years, inclusive (§3 check 3)
    expected_rows: int                              # evidence numbers counted at the design step (§0, §3 check 6)


LISTS = (
    ListSpec("A", SNAP / "list-A-2016-2021-30012026.pdf", dt.date(2026, 1, 30), (2016, 2021), 507),
    ListSpec("B", SNAP / "list-B-2023-2026-07102026.pdf", dt.date(2026, 10, 7), (2023, 2026), 462),
)
NO_REGISTRATION_YEAR = 2022                         # §0, §3 check 3: a suffix 2022 stops the run

# ---- §2.8: the 2026 incentive subsidy (the Fund's notice of 27 March 2026) ----
S2026 = 1_611_972_229

# ---- §2.9, pinned in the change log of 5 November 2026 ----
# 20 % for registration requests before 1 Jan 2025 (act 496/2012 as promulgated, §43(4)(a); act 139/2016 point 74,
# transitional provision 3, for requests from 6 May 2016); 25 %, or 35 % for animation, from 1 Jan 2025 (act 480/2024,
# points 201-202, transitional provision 24). The withholding-tax rebate is not a rate on eligible costs and is not used.
RATE_SWITCH = dt.date(2025, 1, 1)
HEADLINE_RATE_BEFORE = Fraction(20, 100)
HEADLINE_RATE_FROM = Fraction(25, 100)
HIGHEST_RATE_BEFORE = Fraction(20, 100)             # the Q5 range collapses before 2025
HIGHEST_RATE_FROM = Fraction(35, 100)


def headline_rate(request: dt.date) -> Fraction:
    return HEADLINE_RATE_BEFORE if request < RATE_SWITCH else HEADLINE_RATE_FROM


def highest_rate(request: dt.date) -> Fraction:
    return HIGHEST_RATE_BEFORE if request < RATE_SWITCH else HIGHEST_RATE_FROM


# ---- §2.4, §2.5, §2.10, §6 check 8 ----
MARGIN_DAYS = 180
MARGIN_CHECK_DAYS = (90, 365)
SECOND_PART_DAYS = 365                              # D_eff for a project with a 1st-instalment decision
DEADLINE_YEARS = 4                                  # §49(2): the ŽOP within 4 years of the registration certificate

# ---- §3 thresholds ----
DEADLINE_TOLERANCE_DAYS = 31                        # check 7: 4 years ± 31 days
DEADLINE_FLAG_SHARE = Fraction(5, 100)              # check 7: more than 5 % deviating flags
DATE_ORDER_FLAG_SHARE = Fraction(2, 100)            # check 4 (estimation step)
PAID_FLAG_SHARE = Fraction(2, 100)                  # check 5 (estimation step)

# Printed cells that do not read as their column's kind, pinned at the data step from their masked shape alone (the
# value stays unread): (list, evidence number, column). Such a cell counts as listed and has no value. Any other
# unreadable cell stops the run (§3 check 1). 24P/2019: a change date printed as "##.##.####/####.####".
UNREADABLE_CELLS = frozenset({("A", "24P/2019", "change_date")})

# ---- §2.10 ----
DAYS_PER_YEAR = Fraction(36525, 100)
HORIZON_YEARS = (1, 2, 3, 4, 5)
MIN_AT_RISK = 30

# ---- §5: label bands on R_low and R_high (never loosened) ----
NEARLY_ALL = Fraction(95, 100)
MOST = Fraction(80, 100)

# ---- §1 Q4 ----
TOP_N = 5

# ---- §2.11: official planned-cost figures for Q5, pinned in the change log of 5 November 2026 and read at the
# estimation-code step (published aggregates, not outcome columns). Year -> (CZK, basis, source). ----
OFFICIAL_Q5 = {
    2020: (6_957_401_841, "evidence year",
           ("annual report 2020, p. 38: Součet uznatelných nákladů, tj. předpokládaná investice všech projektů, "
            "které se v roce 2020 alokovaly")),
    2021: (6_244_202_515, "evidence year",
           ("annual report 2021, p. 35: Součet uznatelných nákladů, tj. předpokládaná investice všech projektů, "
            "které se v roce 2021 alokovaly")),
    2025: (9_376_844_134, "year the evidence application was filed",
           ("annual report 2025, annex p. 84: Žádosti o evidenci podané v 2025 – uznatelné náklady = investice v "
            "ČR celkem")),
}
