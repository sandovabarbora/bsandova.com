"""Frozen settings of the licence-fee study (docs/research/fees-design.md). No threshold, amount or path is written
anywhere else. Legal amounts are integers or Fractions; nothing here is a binary float."""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TOOL = "tools/fees"
DATA = ROOT / "tools/data/fees"                    # gitignored
SNAP = DATA / "2026-11-03"
DESIGN = ROOT / "docs/research/fees-design.md"
MANIFEST = ROOT / "docs/research/fees-files.sha256"
RESULTS = ROOT / "docs/research/fees-results.json"
VAT_MAP = HERE / "vat_map.csv"
EXCISE_MAP = HERE / "excise_map.csv"

DESIGN_TAG = "fees-design"
DATA_TAG = "fees-data-step"
CODE_TAG = "fees-code"                              # freezes tools/fees (design "Running and verification")
STAMP_TAGS = (DESIGN_TAG, DATA_TAG, CODE_TAG)

BROADCASTERS = ("CT", "CRO")
YEARS = (2027, 2028, 2029, 2030)                    # Q-A window
PATH_YEARS = (2025, 2026) + YEARS                   # years the fee and inflation paths are run for

# ---- the bill (Sněmovní tisk 231/0, Čl. I and II, new §10a(2) of acts 483/1991 and 484/1991) ----
BILL_2027 = {"CT": 5_741_826_000, "CRO": 2_065_766_000}
BILL_TOTAL = sum(BILL_2027.values())                # 7 807 592 000 (design §2.3)
BILL_THRESHOLD_PP = Decimal(10)                     # §10a(3): "překročí 10 procentních bodů"
BILL_STEP = (11, 10)                                # +10 %, ceiling to a whole crown
BILL_WINDOW_START = 2026                            # "od roku 2026"
READINGS = ("R1", "R2")                             # R1 sum (primary), R2 compounded

# ---- current law (act 348/2005, version 14, from 1 Jan 2026) ----
MONTHLY_BEFORE_MAY_2025 = {"CT": 135, "CRO": 45}    # §6 before act 119/2025
MONTHLY_FROM_MAY_2025 = {"CT": 150, "CRO": 55}      # §6(1), act 119/2025 Čl. VI point 9
LAST_INCREASE = (2025, 5)                           # (year, month) the new amounts took effect
VALORISATION_THRESHOLD_PCT = Decimal(6)             # §6(2): sum of inflation since the last increase exceeds 6 %
VALORISATION_STEP = (106, 100)                      # +6 %, each broadcaster's amount ceiled to a whole crown
VALORISATION_MONTH = 7                              # "vždy k 1. červenci" of the year after the crossing
CURRENT_WINDOW_START = 2025                         # primary; 2026 is check 1 of §7
CHECK_WINDOW_START = 2026

# Notice of the Ministry of Culture under §6(3), if one has been published (design §2.10 item 2). Maps a
# broadcaster to {(year, month): monthly amount in CZK that applies from that month on}. None was found at snapshot
# (version 14 states 55 and 150 CZK, "Souvislosti" lists no notice); the author found none announced for 2027:
# none found as of 3 Nov 2026. A non-empty entry overrides the §6(2) path of that broadcaster from its first month on.
NOTICE_OVERRIDE: dict[str, dict[tuple[int, int], int]] = {}

HOUSEHOLD_ANNUAL = {"TV": 150 * 12, "R": 55 * 12}   # §6(1) x 12 (design §2.1)
EXEMPTION_MULTIPLE = Fraction(215, 100)             # §4(2): 2.15 x životní minimum

# Životní minimum, monthly CZK. Source: act 110/2006 Coll., §2 and §3(2)-(3), amounts in force on 1 Jan 2026 (the
# design pins that date); the text was checked in version 28 (31 Mar - 30 Sep 2026), and the author confirmed that the
# single-person amount of 4 860 CZK was in force on 1 Jan 2026 (unchanged from Jan 2023 to 30 Sep 2026). The rise to
# 5 500 CZK for a single person from 1 Oct 2026 does NOT apply under the pinned rule and is not used.
LIVING_MINIMUM = {
    "single": 4860,                                 # §2: a person not assessed with others
    "first": 4470,                                  # §3(2): person assessed first in the order
    "further_adult": 4040,                          # §3(3)a
    "child_bands": (3490, 3050, 2480),              # §3(3)b-d: 15-26, 6-15, under 6 years
}

# ---- sharing of taxes (act 243/2000 Coll.), percent of the national gross yield ----
SHARES = {
    "v15": {"regions": Fraction(945, 100), "municipalities": Fraction(2416, 100),       # in force 1 Jan - 31 Dec 2025
            "source": "act 243/2000, version 15 (act 349/2023), §3(1)(b)-(g), §4(1)(b)-(f),(i)"},
    "v17": {"regions": Fraction(1023, 100), "municipalities": Fraction(2593, 100),       # in force 29 Aug 2026 - 2027
            "source": "act 243/2000, versions 16-17 (acts 267/2025, 155/2026)"},
}
MUNICIPAL_PIT_EMPLOYMENT = Fraction(15, 10)         # §4(1)(h), both versions
FUND_MINERAL_OIL = Fraction(91, 10)                 # §5: State Fund for Transport Infrastructure, mineral-oil excise

# ---- state-budget items (Státní závěrečný účet 2025, Part G, Tab. 2a, column "Skutečnost" 2025) ----
ITEM_VAT = (1211,)
ITEM_EXCISE = tuple(range(1220, 1230)) + (1231, 1232, 1233)
ITEM_PIT = (1111, 1112, 1113)
ITEM_CIT = (1121,)
OUT_OF_POOL_PREFIXES = ("1131", "1234", "132", "133", "135", "136", "137", "138", "140", "152", "170")
ITEM_SOCIAL_PREFIXES = ("161", "162")
BUDGET_YEAR = 2025
# Pool items whose label does not occur in Tab. 2a (the structure stage found 1226 and 1227 absent, 3 Nov 2026). Any other
# absent pool item, or a pool item with an empty cell, stops the run.
POOL_ABSENT = frozenset({1226, 1227})

# ---- Q-A and Q-B rules ----
SHOCKS = (-1, 0, 1)                                 # inflation path, percentage points
BASELINES = ("A", "B")
PRIMARY = {"shock": 0, "reading": "R1", "baseline": "A"}
TIE_BN = Fraction(1, 10)                            # §6 tie threshold, bn CZK
SIMILAR_BAND = (Fraction(9, 10), Fraction(11, 10))  # §6 band for a ratio
CNB_TARGET = Decimal("2.0")                         # fill for missing quarters and years after the horizon
CNB_NOISE_DP = 6                                    # quarterly cells are rounded here only to drop spreadsheet float noise

# firm schedule, §5(3)-(4): (lowest employees, highest employees or None, multiple of the monthly household fee).
# 500 employees fall in the class of 100 ("the higher", design §2.2).
SCHEDULE = ((0, 24, 0), (25, 49, 5), (50, 99, 10), (100, 199, 20), (200, 249, 30), (250, 499, 70), (500, None, 100))
FIRM_FEE_MONTHLY = 150 + 55

# size bands of the RES field KATPO (code list 579) whose label is not a numeric range
BAND_LABELS_ZERO = ("Neuvedeno", "Bez zaměstnanců")
