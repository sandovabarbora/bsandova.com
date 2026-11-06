"""The data-step checks of design §3 that need no outcome column: 1 (row parse, in parse.py), 2 (unique evidence
numbers, pairs across the lists), 3 (year coverage), 6 (counts) and 7 (the deadline column). The report holds counts,
booleans, day differences of the two non-outcome date columns and evidence numbers; no allocation, date of a decision,
cancellation or change, and no payout is read here. Checks 4 and 5 use outcome columns and come with the estimation."""
from __future__ import annotations

import datetime as dt
import re
import statistics
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence

import config as C
import parse as P

Rows = Sequence[P.Row]


def plus_years(d: dt.date, years: int) -> dt.date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:                                                    # 29 February
        return d.replace(year=d.year + years, day=28)


def check_2(lists: Mapping[str, Rows]) -> dict:
    seen = Counter(r.evidence for rows in lists.values() for r in rows)
    dup = sorted(e for e, n in seen.items() if n > 1)
    key = lambda r: (r.title.casefold(), r.tax_id, r.request_date)       # noqa: E731
    pairs = []
    if "A" in lists and "B" in lists:
        b = {}
        for r in lists["B"]:
            b.setdefault(key(r), []).append(r.evidence)
        pairs = sorted([a.evidence, e] for a in lists["A"] for e in b.get(key(a), []))
    return {"duplicates": dup, "stop": bool(dup), "pairs_same_title_tax_id_request": pairs}


def check_3(lists: Mapping[str, Rows], specs: Sequence[C.ListSpec] | None = None) -> dict:
    by_name = {s.name: s for s in specs or C.LISTS}
    stop, outside, req = [], {}, []
    for name, rows in lists.items():
        lo, hi = by_name[name].years
        stop += [r.evidence for r in rows if r.year == C.NO_REGISTRATION_YEAR]
        outside[name] = [r.evidence for r in rows if r.year != C.NO_REGISTRATION_YEAR and not lo <= r.year <= hi]
        req += [r.evidence for r in rows
                if r.request_date and r.request_date.year == C.NO_REGISTRATION_YEAR and r.year != C.NO_REGISTRATION_YEAR]
    return {"suffix_2022": sorted(stop), "suffix_outside_stated_years": outside, "request_2022_other_suffix": sorted(req),
            "stop": bool(stop), "flag": any(outside.values()) or bool(req)}


def check_6(lists: Mapping[str, Rows], specs: Sequence[C.ListSpec] | None = None) -> dict:
    by_name = {s.name: s for s in specs or C.LISTS}
    out = {}
    for name, rows in lists.items():
        n, distinct, expected = len(rows), len({r.evidence for r in rows}), by_name[name].expected_rows
        out[name] = {"rows": n, "distinct_numbers": distinct, "expected_rows": expected,
                     "rows_equal_distinct": n == distinct, "equals_expected": n == expected}
    out["stop"] = not all(v["rows_equal_distinct"] for v in out.values())
    out["flag"] = not all(v["equals_expected"] for k, v in out.items() if k != "stop")
    return out


def check_7(lists: Mapping[str, Rows]) -> dict:
    out, flag = {}, False
    for name, rows in lists.items():
        both = [r for r in rows if r.deadline and r.registration_date]
        days = [(r.deadline - r.registration_date).days for r in both]
        off = [r.evidence for r in both
               if abs((r.deadline - plus_years(r.registration_date, C.DEADLINE_YEARS)).days) > C.DEADLINE_TOLERANCE_DAYS]
        f = len(off) > C.DEADLINE_FLAG_SHARE * len(both)
        flag |= f
        out[name] = {"with_both_dates": len(both),
                     "days_min": min(days, default=None), "days_median": statistics.median(days) if days else None,
                     "days_max": max(days, default=None),
                     "deviating_from_4_years_pm_31_days": len(off), "deviating_numbers": sorted(off), "flag": f}
    out["flag"] = flag
    return out


def coverage(lists: Mapping[str, Rows]) -> dict:
    # non-outcome columns only (§2.4 needs D or a registration date)
    out = {}
    for name, rows in lists.items():
        out[name] = {
            "pages": len({r.page for r in rows}),
            "odd_format_numbers": sorted(r.evidence for r in rows if not re.fullmatch(r"\d{1,3}P/\d{4}", r.evidence)),
            "rows_without_tax_id": sorted(r.evidence for r in rows if not r.tax_id),
            "rows_without_applicant": sorted(r.evidence for r in rows if not r.applicant),
            "rows_without_registration_date": sorted(r.evidence for r in rows if r.registration_date is None),
            "rows_without_deadline": sorted(r.evidence for r in rows if r.deadline is None),
            "rows_without_deadline_or_registration_date": sorted(r.evidence for r in rows
                                                                 if r.deadline is None and r.registration_date is None),
            "rows_with_several_evidence_dates": sorted(r.evidence for r in rows if len(r.evidence_date) > 1),
            "numbers_per_suffix_year": dict(sorted(Counter(r.year for r in rows).items())),
        }
    return out


def report(lists: Mapping[str, Rows], specs: Sequence[C.ListSpec] | None = None) -> dict:
    c2, c3, c6, c7 = check_2(lists), check_3(lists, specs), check_6(lists, specs), check_7(lists)
    stops = [k for k, c in (("check_2", c2), ("check_3", c3), ("check_6", c6)) if c["stop"]]
    flags = [k for k, c in (("check_3", c3), ("check_6", c6), ("check_7", c7)) if c["flag"]]
    involved = set(c2["duplicates"]) | set(c3["suffix_2022"]) | set(c3["request_2022_other_suffix"])
    involved |= {e for v in c3["suffix_outside_stated_years"].values() for e in v}
    involved |= {e for k, v in c7.items() if k != "flag" and v["flag"] for e in v["deviating_numbers"]}
    return {"check_1_row_parse": {"passed": True, "rows": {k: len(v) for k, v in lists.items()},
                                  "unreadable_cells_pinned": sorted(list(t) for t in C.UNREADABLE_CELLS)},
            "check_2_unique_numbers": c2, "check_3_year_coverage": c3, "check_6_counts": c6, "check_7_deadline": c7,
            "coverage": coverage(lists), "stops": stops, "flags": flags,
            "evidence_numbers_in_a_flag_or_stop": sorted(involved)}


def failed_parse(error: P.ParseError) -> dict:
    return {"check_1_row_parse": {"passed": False, "error": str(error)}, "stops": ["check_1"], "flags": [],
            "evidence_numbers_in_a_flag_or_stop": []}


def describe(rep: dict) -> Iterator[str]:
    """The printed lines: counts, booleans and evidence numbers only."""
    c1 = rep["check_1_row_parse"]
    if not c1["passed"]:
        yield f"check 1 (row parse): STOP: {c1['error']}"
        return
    yield f"check 1 (row parse): passed; rows {c1['rows']}; pinned unreadable cells {c1['unreadable_cells_pinned']}"
    c2 = rep["check_2_unique_numbers"]
    yield (f"check 2 (unique numbers): duplicates {c2['duplicates'] or 'none'}; pairs across A and B with the same "
           f"title, tax ID and request date: {c2['pairs_same_title_tax_id_request'] or 'none'}")
    c3 = rep["check_3_year_coverage"]
    yield (f"check 3 (years): suffix 2022 {c3['suffix_2022'] or 'none'}; outside the stated years "
           f"{c3['suffix_outside_stated_years']}; request in 2022 with another suffix {c3['request_2022_other_suffix'] or 'none'}")
    c6 = rep["check_6_counts"]
    for k, v in c6.items():
        if k not in ("stop", "flag"):
            yield (f"check 6 (counts) list {k}: rows {v['rows']}, distinct {v['distinct_numbers']}, expected "
                   f"{v['expected_rows']}; rows = distinct {v['rows_equal_distinct']}; = expected {v['equals_expected']}")
    c7 = rep["check_7_deadline"]
    for k, v in c7.items():
        if k != "flag":
            yield (f"check 7 (deadline) list {k}: {v['with_both_dates']} with both dates; D - registration "
                   f"{v['days_min']} / {v['days_median']} / {v['days_max']} days (min / median / max); "
                   f"{v['deviating_from_4_years_pm_31_days']} outside 4 years ± 31 days {v['deviating_numbers']}; flag {v['flag']}")
    for k, v in rep["coverage"].items():
        yield f"coverage list {k}: " + "; ".join(f"{a} {b}" for a, b in v.items())
    yield f"stops: {rep['stops'] or 'none'}; flags: {rep['flags'] or 'none'}"
