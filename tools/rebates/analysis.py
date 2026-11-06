"""Q1 to Q5 and the checks of §3 (4, 5) and §6 (design §2.3 to §2.10, §4, §5), on the rows of parse.py. Written after
the data-step tag, so that no estimation rule can follow from the structure report. All arithmetic is exact (int and
Fraction), the Q2 curve included; only the JSON output is rounded."""
from __future__ import annotations

import datetime as dt
import itertools
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

import config as C
import parse as P
import structure as S

Money = int | Fraction

DECIDED = "decided"
PENDING = "decided_payout_pending"
CANCELLED = "cancelled"
LAPSED = "lapsed_or_undecided"
STATUSES = (DECIDED, PENDING, CANCELLED, LAPSED)

NEARLY_ALL_PAID = "nearly all paid"
MOST_PAID = "most paid"
SUBSTANTIALLY_LESS = "substantially less than allocated"
DEPENDS = "depends on the undecided projects"


@dataclass(frozen=True)
class Project:
    row: P.Row
    list_date: dt.date

    @property
    def evidence(self) -> str:
        return self.row.evidence

    @property
    def p0(self) -> Money:
        return self.row.allocation

    @property
    def p1(self) -> Money:
        # change log, 5 November 2026: the new allocation where one is printed, else the allocation
        return self.row.new_allocation if "new_allocation" in self.row.listed else self.row.allocation

    @property
    def v(self) -> Money:
        return self.row.paid

    @property
    def has_allocation(self) -> bool:
        return self.p0 > 0

    @property
    def start(self) -> dt.date | None:
        # change log: of two evidence-certificate dates in one cell, the earlier
        return min(self.row.evidence_date, default=None)

    @property
    def deadline(self) -> dt.date | None:
        if self.row.deadline is not None:
            return self.row.deadline
        if self.row.registration_date is not None:
            return S.plus_years(self.row.registration_date, C.DEADLINE_YEARS)
        return None

    @property
    def d_eff(self) -> dt.date | None:
        d = self.deadline
        if d is None:
            return None
        return d + dt.timedelta(days=C.SECOND_PART_DAYS) if self.row.decision_1_date else d

    def mature(self, margin: int) -> bool:
        d = self.d_eff
        return d is not None and d + dt.timedelta(days=margin) <= self.list_date

    def status(self, margin: int) -> str:
        d2 = self.row.decision_2_date
        if d2 is not None:                                   # §2.5: a cancelled project with a decision is decided
            return DECIDED if (self.list_date - d2).days >= margin else PENDING
        return CANCELLED if self.row.cancellation_date is not None else LAPSED


def projects(lists: Mapping[str, Sequence[P.Row]], specs: Sequence[C.ListSpec] | None = None) -> list[Project]:
    dates = {s.name: s.list_date for s in specs or C.LISTS}
    return [Project(r, dates[name]) for name, rows in lists.items() for r in rows]


def ratio(num: Money, den: Money) -> Fraction | None:
    return Fraction(num) / den if den else None


def exact(r: Fraction | None) -> dict | None:
    # the ratios that decide the label, unrounded, so that a value at a band edge can be read as it is
    return None if r is None else {"num": r.numerator, "den": r.denominator}


def rank_key(p: Project) -> tuple:
    # largest P0 first; among equal P0 the earlier-registered project first, by (registration year, number), so that
    # 9P/2016 comes before 10P/2016 and both before 1P/2017
    return -p.p0, p.row.year, int(re.match(r"\d+", p.evidence)[0])


def median(xs: Iterable[Money]) -> Fraction | None:
    # exact: statistics.median turns the mean of two ints into a float, and Q4 splits on "strictly greater"
    s = sorted(xs)
    if not s:
        return None
    mid = len(s) // 2
    return Fraction(s[mid]) if len(s) % 2 else Fraction(s[mid - 1] + s[mid], 2)


# ---------------------------------------------------------------- Q1 (§2.6) and its variants (§6)

Promise = Callable[[Project], Money]


def on_p0(p: Project) -> Money:
    return p.p0


def on_p1(p: Project) -> Money:
    return p.p1


def bounds(ps: Iterable[Project], margin: int = C.MARGIN_DAYS, promise: Promise = on_p0) -> dict:
    ps = list(ps)
    den = sum((promise(p) for p in ps), 0)
    low = sum((p.v for p in ps), 0)
    high = sum((max(p.v, promise(p)) if p.status(margin) in (PENDING, LAPSED) else p.v for p in ps), 0)
    return {"projects": len(ps), "promised": den, "paid": low, "r_low": ratio(low, den), "r_high": ratio(high, den)}


def band(r: Fraction) -> str:
    if r >= C.NEARLY_ALL:
        return NEARLY_ALL_PAID
    return MOST_PAID if r >= C.MOST else SUBSTANTIALLY_LESS


def label(r_low: Fraction | None, r_high: Fraction | None) -> str | None:
    if r_low is None or r_high is None:
        return None
    lo, hi = band(r_low), band(r_high)
    return lo if lo == hi else DEPENDS


PARTS = ("a_cancelled_paid_0", "b_cancelled_paid_above_0", "c_decided_paid_below_p0",
         "d_lapsed_paid_0_no_1st_decision", "d_lapsed_paid_0_with_1st_decision",
         "d_lapsed_paid_above_0_no_1st_decision", "d_lapsed_paid_above_0_with_1st_decision",
         "e_decided_payout_pending", "f_decided_paid_above_p0")


def part(p: Project, margin: int) -> str | None:
    s = p.status(margin)
    if s == CANCELLED:
        return "a_cancelled_paid_0" if p.v == 0 else "b_cancelled_paid_above_0"
    if s == DECIDED:
        return None if p.v == p.p0 else "c_decided_paid_below_p0" if p.v < p.p0 else "f_decided_paid_above_p0"
    if s == PENDING:
        return "e_decided_payout_pending"
    paid = "paid_0" if p.v == 0 else "paid_above_0"
    first = "with_1st_decision" if p.row.decision_1_date else "no_1st_decision"
    return f"d_lapsed_{paid}_{first}"


def decomposition(mature: Sequence[Project], margin: int = C.MARGIN_DAYS) -> dict:
    parts: dict[str, Money] = dict.fromkeys(PARTS, 0)
    for p in mature:
        k = part(p, margin)
        if k is not None:
            parts[k] += p.p0 - p.v
    total = sum((p.p0 - p.v for p in mature), 0)
    assert sum(parts.values(), 0) == total
    return {"shortfall": total, "parts": parts, "shares": {k: ratio(v, total) for k, v in parts.items()}}


def q1(ps: Sequence[Project], margin: int = C.MARGIN_DAYS) -> dict:
    mature = [p for p in ps if p.has_allocation and p.mature(margin)]
    b = bounds(mature, margin)
    n = Counter(p.status(margin) for p in mature)
    return {**b, "r_low_exact": exact(b["r_low"]), "r_high_exact": exact(b["r_high"]),
            "label": label(b["r_low"], b["r_high"]), "decomposition": decomposition(mature, margin),
            "status_counts": {s: n[s] for s in STATUSES},
            "status_shares": {s: ratio(n[s], len(mature)) for s in STATUSES},
            "median_paid_over_p0": median(Fraction(p.v) / p.p0 for p in mature)}


# ---------------------------------------------------------------- Q2 (§2.10)

DECISION, CANCELLATION, LAPSE = "decision", "cancellation", "lapse"
KINDS = (DECISION, CANCELLATION, LAPSE)
Obs = tuple[int, str | None]


def observation(p: Project, start: dt.date, margin: int) -> Obs:
    """(days from start, event kind, or None when censored at the list date). The kind follows the §2.5 status: a
    decision after D_eff + margin is still a decision, and a project with both dates is decided."""
    r = p.row
    if r.decision_2_date is not None:
        return (r.decision_2_date - start).days, DECISION
    if r.cancellation_date is not None:
        return (r.cancellation_date - start).days, CANCELLATION
    if p.mature(margin):
        return (p.d_eff + dt.timedelta(days=margin) - start).days, LAPSE
    return (p.list_date - start).days, None


def aalen_johansen(obs: Sequence[Obs]) -> list[tuple[int, int, dict[str, Fraction]]]:
    """(time, at risk, cumulative incidence by kind) at each event time. Censorings on an event day are still at risk
    on that day."""
    surv, cif, steps = Fraction(1), dict.fromkeys(KINDS, Fraction(0)), []
    for t in sorted({t for t, k in obs if k is not None}):
        n = at_risk(obs, t)
        d = Counter(k for x, k in obs if x == t and k is not None)
        for k, m in d.items():
            cif[k] += surv * Fraction(m, n)
        surv *= 1 - Fraction(d.total(), n)
        steps.append((t, n, dict(cif)))
    return steps


def at_risk(obs: Sequence[Obs], t: Money) -> int:
    return sum(1 for x, _ in obs if x >= t)


def q2(ps: Sequence[Project], margin: int = C.MARGIN_DAYS, start: str = "evidence") -> dict:
    obs, no_start, negative = [], [], []
    for p in ps:
        if not p.has_allocation:
            continue
        s = p.start if start == "evidence" else p.row.request_date
        if s is None:
            no_start.append(p.evidence)
            continue
        o = observation(p, s, margin)
        if o[0] < 0:                                         # a date-order breach (§3 check 4): listed, not estimated
            negative.append(p.evidence)
            continue
        obs.append(o)
    steps = aalen_johansen(obs)
    horizons = {}
    for y in C.HORIZON_YEARS:
        h = y * C.DAYS_PER_YEAR
        n = at_risk(obs, h)
        cif = next((c for t, _, c in reversed(steps) if t <= h), dict.fromkeys(KINDS, Fraction(0)))
        horizons[y] = {"at_risk": n, "estimable": n >= C.MIN_AT_RISK,
                       "cumulative_incidence": cif if n >= C.MIN_AT_RISK else "not estimable"}
    half = next((t for t, _, c in steps if c[DECISION] >= Fraction(1, 2)), None)
    reached = half is not None and at_risk(obs, half) >= C.MIN_AT_RISK
    return {"start": start, "margin_days": margin, "projects": len(obs),
            "events": {k: sum(1 for _, x in obs if x == k) for k in KINDS},
            "censored": sum(1 for _, k in obs if k is None), "without_start_date": sorted(no_start),
            "event_before_start": sorted(negative), "horizons_years": horizons,
            "years_to_50_percent_decided": Fraction(half) / C.DAYS_PER_YEAR if reached else "not reached"}


# ---------------------------------------------------------------- Q3 (§2.7)

def q3(ps: Sequence[Project], r1: dict, margin: int = C.MARGIN_DAYS) -> dict:
    out = {}
    for name in sorted({p.row.list_name for p in ps}):
        mine = [p for p in ps if p.row.list_name == name and p.has_allocation]
        open_ = [p for p in mine if not p.mature(margin) and p.row.cancellation_date is None
                 and p.status(margin) != DECIDED]
        lapsed = [p for p in mine if p.mature(margin) and p.status(margin) == LAPSED]
        o = sum((max(p.p1 - p.v, 0) for p in open_), 0)
        fig = {"open_projects": len(open_), "o": o, "o_ratio_to_s2026": ratio(o, C.S2026)}
        for bound in ("r_low", "r_high"):
            r = r1[bound]
            o_r = None if r is None else sum((max(r * p.p1 - p.v, 0) for p in open_), 0)
            fig[f"o_{bound}"] = o_r
            fig[f"o_{bound}_ratio_to_s2026"] = None if o_r is None else ratio(o_r, C.S2026)
        m = sum((max(p.p1 - p.v, 0) for p in lapsed), 0)
        fig |= {"mature_lapsed_projects": len(lapsed), "mature_lapsed_remainder": m,
                "mature_lapsed_ratio_to_s2026": ratio(m, C.S2026)}
        out[name] = fig
    r1_out = {k: r1[k] for k in ("r_low", "r_high")} | {f"{k}_exact": exact(r1[k]) for k in ("r_low", "r_high")}
    return {"s2026": C.S2026, "r1": r1_out, "lists": out}


# ---------------------------------------------------------------- Q4

def q4(ps: Sequence[Project], margin: int = C.MARGIN_DAYS) -> dict:
    mature = [p for p in ps if p.has_allocation and p.mature(margin)]
    if not mature:
        return {"projects": 0}
    med = median(p.p0 for p in mature)
    ranked = sorted(mature, key=rank_key)
    total = sum((p.p0 for p in mature), 0)
    return {"projects": len(mature), "median_p0": med,
            "above_median": bounds((p for p in mature if p.p0 > med), margin),
            "at_or_below_median": bounds((p for p in mature if p.p0 <= med), margin),
            "top_share": {"n": C.TOP_N, "share_of_p0": ratio(sum((p.p0 for p in ranked[:C.TOP_N]), 0), total)},
            "without_largest": {"left_out": ranked[0].evidence, **bounds(ranked[1:], margin)}}


# ---------------------------------------------------------------- Q5 (§2.9, §2.11)

def q5(ps: Sequence[Project], margin: int = C.MARGIN_DAYS) -> dict:
    def series(year_of: Callable[[Project], int | None]) -> dict:
        out: dict = {"main": {}, "cancelled": {}, "skipped_without_year": 0}
        for p in ps:
            if not p.has_allocation:
                continue
            y = year_of(p)
            if y is None:
                out["skipped_without_year"] += 1
                continue
            cell = out[CANCELLED if p.status(margin) == CANCELLED else "main"].setdefault(
                y, {"projects": 0, "p0": 0, "base": 0, "base_low": 0})
            cell["projects"] += 1
            cell["p0"] += p.p0
            cell["base"] += Fraction(p.p0) / C.headline_rate(p.row.request_date)
            cell["base_low"] += Fraction(p.p0) / C.highest_rate(p.row.request_date)
        return {k: dict(sorted(v.items())) if isinstance(v, dict) else v for k, v in out.items()}

    return {"by_registration_year": series(lambda p: p.row.year),
            "by_evidence_year": series(lambda p: p.start.year if p.start else None),
            "official": {y: {"czk": v, "basis": b, "source": s} for y, (v, b, s) in C.OFFICIAL_Q5.items()}}


# ---------------------------------------------------------------- §3 checks 4 and 5

def check_4(ps: Sequence[Project]) -> dict:
    breaches = []
    for p in ps:
        r = p.row
        chain = [d for d in (r.request_date, r.registration_date, p.start, r.decision_1_date, r.decision_2_date) if d]
        if any(a > b for a, b in itertools.pairwise(chain)):
            breaches.append(p.evidence)
    no_d = sorted(p.evidence for p in ps if p.deadline is None)
    # §3 check 4: "Projects without a D are counted here", so they count towards the 2 % beside the breaches
    counted = len(breaches) + len(no_d)
    return {"projects": len(ps), "breaches": len(breaches), "breach_numbers": sorted(breaches),
            "without_deadline": no_d, "counted": counted, "flag": counted > C.DATE_ORDER_FLAG_SHARE * len(ps)}


def check_5(ps: Sequence[Project]) -> dict:
    decided = [p for p in ps if p.row.decision_2_date is not None]
    over_decided = sum(1 for p in decided if p.v > p.p1)
    return {"paid_above_p1": sorted(p.evidence for p in ps if p.v > p.p1), "decided_projects": len(decided),
            "decided_paid_above_p1": over_decided, "flag": over_decided > C.PAID_FLAG_SHARE * len(decided)}


# ---------------------------------------------------------------- counts and §6

def counts(ps: Sequence[Project], margin: int = C.MARGIN_DAYS) -> dict:
    out: dict = {}
    for name in sorted({p.row.list_name for p in ps}):
        mine = [p for p in ps if p.row.list_name == name]
        c = {"mature": Counter(), "open": Counter(), "without_allocation": Counter()}
        for p in mine:
            group = "without_allocation" if not p.has_allocation else "mature" if p.mature(margin) else "open"
            c[group][p.status(margin)] += 1
        out[name] = {"rows": len(mine)} | {g: {s: v[s] for s in STATUSES} for g, v in c.items()}
    out["cancelled_and_decided"] = sorted(p.evidence for p in ps
                                          if p.row.cancellation_date is not None and p.row.decision_2_date is not None)
    return out


def banded(b: dict) -> dict:
    # the band a variant would get; reported beside the headline, never relabelling it (§6)
    return b | {"band": label(b["r_low"], b["r_high"])}


def section_6(ps: Sequence[Project]) -> dict:
    m = C.MARGIN_DAYS
    alloc = [p for p in ps if p.has_allocation]
    mature = [p for p in alloc if p.mature(m)]
    decided = [p for p in alloc if p.status(m) == DECIDED]
    lists = sorted({p.row.list_name for p in ps})

    def at_margin(k: int) -> dict:
        mk = [p for p in alloc if p.mature(k)]
        return {"q1": banded(bounds(mk, k)), "q2": q2(ps, k)["horizons_years"],
                "q3": q3(ps, bounds(mk, k, on_p1), k)["lists"]}

    return {
        "1_on_p1": banded(bounds(mature, m, on_p1)),
        "2_without_cancelled": banded(bounds((p for p in mature if p.status(m) != CANCELLED), m)),
        "3_by_list": {n: banded(bounds((p for p in mature if p.row.list_name == n), m)) for n in lists},
        "4_by_registration_year": {y: bounds((p for p in mature if p.row.year == y), m)
                                   for y in sorted({p.row.year for p in mature})},
        "5_all_decided": {"projects": len(decided),
                          "r": ratio(sum((p.v for p in decided), 0), sum((p.p0 for p in decided), 0))},
        "6_r_floor": {"projects": len(alloc), "r": ratio(sum((p.v for p in alloc), 0), sum((p.p0 for p in alloc), 0))},
        "7_q2_list_a": q2([p for p in ps if p.row.list_name == "A"], m),
        "8_margin": {k: at_margin(k) for k in C.MARGIN_CHECK_DAYS},
    }


# ---------------------------------------------------------------- the run

def plain(x):
    """JSON-ready: Fractions as floats to 6 places, keys as strings."""
    if isinstance(x, Fraction):
        return float(round(x, 6))
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    return x


def run(lists: Mapping[str, Sequence[P.Row]], specs: Sequence[C.ListSpec] | None = None) -> dict:
    structure = S.report(lists, specs)
    if structure["stops"]:
        raise SystemExit(f"refusing to estimate: the data-step checks stop the run: {structure['stops']}")
    ps = projects(lists, specs)
    c4, c5 = check_4(ps), check_5(ps)
    headline = q1(ps)
    mature = [p for p in ps if p.has_allocation and p.mature(C.MARGIN_DAYS)]
    return plain({
        "label": headline["label"], "q1": headline,
        "q2": q2(ps), "q2_from_request": q2(ps, start="request"),
        "q3": q3(ps, bounds(mature, C.MARGIN_DAYS, on_p1)),
        "q4": q4(ps), "q5": q5(ps),
        "counts": counts(ps),
        "checks_3": {"check_4_date_order": c4, "check_5_paid_above_p1": c5,
                     "data_step": {k: structure[k] for k in ("check_3_year_coverage", "check_6_counts",
                                                             "check_7_deadline")}},
        "checks_6": section_6(ps),
        "flags": structure["flags"] + [k for k, c in (("check_4", c4), ("check_5", c5)) if c["flag"]],
    })
