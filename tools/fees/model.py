"""Q-B and the firm figures (design §2.1, §2.4, §2.5, §3, §6, §7). Exact arithmetic (Fraction, int); allocations
are whole crowns by the largest-remainder method and check 2 of §3 stops the run if they do not sum."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import alloc
import config as C
import parse as P

N = 10


class CheckFailure(Exception):
    """Check 2 of §3: a coding or rounding error. Stops the run."""


def quintile_of(d: int) -> int:
    return d // 2                                   # d is the 0-based decile; deciles 0,1 -> quintile 0


@dataclass(frozen=True)
class QbInputs:
    silc: P.SilcDeciles
    hbs: P.Hbs
    vat_map: list[dict]
    excise_map: list[dict]
    pool: dict[str, Fraction]                       # CZK, net lines as they stand (design change log, open item 4)
    payers_tv: Fraction                             # household payers, year-end 2025 report
    payers_r: Fraction
    fee_revenue_2026: Fraction                      # budgeted fee revenue of ČT + ČRo for 2026 (baseline in use)
    seniors: list[P.SeniorCut] | None = None
    employer_counts: dict[str, int] | None = None
    band_labels: dict[str, str] | None = None
    gross_lines: dict[str, Fraction] | None = None  # national yields from Part C, if available (check 7)


@dataclass(frozen=True)
class AfterSpec:
    pit_basis: str = "tax"                          # tax | work | net (§2.4, check 4)
    vat_mode: str = "map"                           # map | uniform (check 3)
    interpolate: bool = False                       # check 9(c)
    other_like_vat: bool = False                    # check 3
    include_social: bool = False                    # check 9(a)
    cit_household_share: Fraction = Fraction(0)     # check 9(b)
    lines: str = "net"                              # net | gross_v17 | gross_v15 (check 7)


# ---------------------------------------------------------------- today

def households(inp: QbInputs) -> list[Fraction]:
    return [Fraction(x) for x in inp.silc.households]


def per_household(per_cu: Sequence, cu: Sequence) -> list[Fraction]:
    return [Fraction(a) * Fraction(b) for a, b in zip(per_cu, cu, strict=True)]


def living_minimum(members: Fraction, children: Fraction, lm: dict = C.LIVING_MINIMUM) -> Fraction:
    """Monthly životní minimum of the mean household of a decile (design §2.4): first adult, further adults, children
    at the unweighted mean of the age-band amounts. A household of exactly one person takes the single-person amount."""
    members, children = Fraction(members), Fraction(children)
    if members == 1 and children == 0:
        return Fraction(lm["single"])
    adults = members - children
    child = Fraction(sum(lm["child_bands"]), len(lm["child_bands"]))
    return lm["first"] + max(adults - 1, Fraction(0)) * lm["further_adult"] + children * child


def exempt_flags(silc: P.SilcDeciles) -> list[bool]:
    """E1: a decile is exempt if its mean net monthly household income is below 2.15 x the životní minimum of its mean
    household; if none is, decile 1 is (§2.4)."""
    net = per_household(silc.net, silc.cu)
    flags = [n / 12 < C.EXEMPTION_MULTIPLE * living_minimum(m, c)
             for n, m, c in zip(net, silc.members, silc.children, strict=True)]
    if not any(flags):
        flags[0] = True
    return flags


def payer_shares(hh: Sequence[Fraction], exempt: Sequence[bool] | None, pi: Fraction) -> tuple[list[Fraction], Fraction]:
    """Share of paying households per decile, and the shortfall of payers caused by the cap at 1 (§2.4)."""
    if exempt is None or not any(exempt):
        return [pi] * N, Fraction(0)
    ne = sum(h for h, e in zip(hh, exempt, strict=True) if not e)
    share = min(Fraction(1), pi * sum(hh) / ne)
    out = [Fraction(0) if e else share for e in exempt]
    return out, pi * sum(hh) - share * ne


def ratio(burdens: Sequence[Fraction]) -> Fraction | None:
    return None if burdens[-1] == 0 else burdens[0] / burdens[-1]


def fee_today(inp: QbInputs, exempt: Sequence[bool] | None, pi_one: bool = False) -> dict[str, Any]:
    hh = households(inp)
    total_hh = sum(hh)
    pi_tv = Fraction(1) if pi_one else inp.payers_tv / total_hh
    pi_r = Fraction(1) if pi_one else inp.payers_r / total_hh
    s_tv, short_tv = payer_shares(hh, exempt, pi_tv)
    s_r, short_r = payer_shares(hh, exempt, pi_r)
    pay = [C.HOUSEHOLD_ANNUAL["TV"] * a + C.HOUSEHOLD_ANNUAL["R"] * b for a, b in zip(s_tv, s_r, strict=True)]
    income = per_household(inp.silc.net, inp.silc.cu)
    burden = [p / i for p, i in zip(pay, income, strict=True)]
    return {"pi_tv": pi_tv, "pi_r": pi_r, "shortfall_tv": short_tv, "shortfall_r": short_r, "pay_hh": pay,
            "income_hh": income, "burden": burden, "ratio": ratio(burden),
            "household_revenue": sum(h * p for h, p in zip(hh, pay, strict=True)), "share_tv": s_tv, "share_r": s_r}


# ---------------------------------------------------------------- decile weights from quintile tables

def interpolate_pairs(q: Sequence[Fraction]) -> list[Fraction]:
    """Check 9(c): each quintile's value sits at its midpoint (decile positions 1.5, 3.5, ...), linear in between, flat
    beyond the ends, then rescaled so that each pair of deciles averages to its quintile's value."""
    pts = [Fraction(3, 2) + 2 * k for k in range(5)]
    raw = []
    for d in range(1, N + 1):
        x = Fraction(d)
        if x <= pts[0]:
            raw.append(Fraction(q[0]))
        elif x >= pts[-1]:
            raw.append(Fraction(q[-1]))
        else:
            k = int((x - pts[0]) // 2)
            t = (x - pts[k]) / 2
            raw.append(Fraction(q[k]) * (1 - t) + Fraction(q[k + 1]) * t)
    out = []
    for k in range(5):
        a, b = raw[2 * k], raw[2 * k + 1]
        f = 2 * Fraction(q[k]) / (a + b) if a + b else Fraction(1)
        out += [a * f, b * f]
    return out


def to_deciles(q: Sequence[Fraction], interpolate: bool) -> list[Fraction]:
    return interpolate_pairs(q) if interpolate else [Fraction(q[quintile_of(d)]) for d in range(N)]


def spending_parts(inp: QbInputs) -> dict[str, list[Fraction]]:
    """Per household and year, by quintile: VAT content of spending, spending on excised categories, total spending."""
    spend = {c: [Fraction(x) for x in v] for c, v in inp.hbs.spend_pp.items()}
    vat_vals = P.map_partition(spend, inp.vat_map)
    exc_vals = P.map_partition(spend, inp.excise_map)
    members = [Fraction(m) for m in inp.hbs.members]
    rate = {e["coicop"]: Fraction(e["vat_rate_pct"]) for e in inp.vat_map}
    excised = {e["coicop"] for e in inp.excise_map if e["excised"] == "1"}
    vat, exc, tot = [], [], []
    for q in range(5):
        vat.append(members[q] * sum(vals[q] * rate[c] / (100 + rate[c]) for c, vals in vat_vals.items()))
        exc.append(members[q] * sum(vals[q] for c, vals in exc_vals.items() if c in excised))
        tot.append(members[q] * sum(vals[q] for vals in vat_vals.values()))
    return {"vat": vat, "excise": exc, "total": tot}


def tax_weights(inp: QbInputs, spec: AfterSpec) -> dict[str, list[Fraction]]:
    hh = households(inp)
    sp = spending_parts(inp)
    vat_q = sp["total"] if spec.vat_mode == "uniform" else sp["vat"]
    s = inp.silc
    work = [Fraction(a) + Fraction(b) for a, b in zip(s.emp, s.self_emp, strict=True)]
    pit_cu = {"tax": s.tax, "work": work, "net": s.net}[spec.pit_basis]
    out = {
        "vat": [h * v for h, v in zip(hh, to_deciles(vat_q, spec.interpolate), strict=True)],
        "excise": [h * v for h, v in zip(hh, to_deciles(sp["excise"], spec.interpolate), strict=True)],
        "pit": [h * v for h, v in zip(hh, per_household(pit_cu, s.cu), strict=True)],
        "net": [h * v for h, v in zip(hh, per_household(s.net, s.cu), strict=True)],
        "gross": [h * v for h, v in zip(hh, per_household(s.gross, s.cu), strict=True)],
    }
    return out


# ---------------------------------------------------------------- after

def state_lines(inp: QbInputs, spec: AfterSpec) -> dict[str, Fraction]:
    if spec.lines == "net":
        return {k: Fraction(v) for k, v in inp.pool.items()}
    g = inp.gross_lines
    if g is None:
        raise P.ParseError("gross lines are not available")
    sh = C.SHARES[spec.lines.removeprefix("gross_")]
    state = 1 - sh["regions"] / 100 - sh["municipalities"] / 100
    state_pit_work = state - C.MUNICIPAL_PIT_EMPLOYMENT / 100
    out = {"vat": g["vat"] * state, "cit": g["cit"] * state,
           "pit": g["pit_employment"] * state_pit_work + g["pit_other"] * state,
           "excise": g["excise_mineral_oils"] * (1 - C.FUND_MINERAL_OIL / 100) + g["excise_other"]}      # excise is not shared with regions or municipalities
    out["other"], out["social"] = inp.pool["other"], inp.pool["social"]
    return out


def after(inp: QbInputs, spec: AfterSpec | None = None, scenario: str = "base", total: int = C.BILL_TOTAL) -> dict[str, Any]:
    spec = spec or AfterSpec()
    w = tax_weights(inp, spec)
    hh = households(inp)
    lines = state_lines(inp, spec)
    comps: list[tuple[str, Fraction, str]]
    if scenario == "base":
        comps = [("vat", lines["vat"], "vat"), ("excise", lines["excise"], "excise"), ("pit", lines["pit"], "pit"),
                 ("cit", lines["cit"], "cit")]
        if spec.other_like_vat:
            comps.append(("other", lines["other"], "vat"))
        if spec.include_social:
            comps.append(("social", lines["social"], "gross"))
    elif scenario == "vat_only":
        comps = [("vat", Fraction(1), "vat")]
    elif scenario == "pit_only":
        comps = [("pit", Fraction(1), "pit")]
    else:
        raise ValueError(scenario)
    parts = alloc.largest_remainder(total, [c[1] for c in comps])
    dec = [0] * N
    firms = 0
    by_tax: dict[str, list[int]] = {}
    for (name, _, wkey), part in zip(comps, parts, strict=True):
        if name == "cit":
            hh_part, firm_part = alloc.largest_remainder(part, [spec.cit_household_share, 1 - spec.cit_household_share]) \
                if spec.cit_household_share else (0, part)
            firms += firm_part
            a = alloc.largest_remainder(hh_part, w["net"]) if hh_part else [0] * N
        else:
            a = alloc.largest_remainder(part, w[wkey])
        by_tax[name] = a
        dec = [x + y for x, y in zip(dec, a, strict=True)]
    if sum(dec) + firms != total:
        raise CheckFailure("allocation over households and firms does not equal the total to the crown")
    per_hh = [Fraction(a) / h for a, h in zip(dec, hh, strict=True)]
    income = per_household(inp.silc.net, inp.silc.cu)
    burden = [p / i for p, i in zip(per_hh, income, strict=True)]
    return {"scenario": scenario, "total": total, "parts": dict(zip((c[0] for c in comps), parts, strict=True)),
            "by_tax": by_tax, "decile_total": dec, "firms": firms, "per_hh": per_hh, "burden": burden,
            "ratio": ratio(burden)}


def out_of_pool_share(pool: dict[str, Fraction]) -> Fraction:
    """Share of the other (out-of-pool) tax lines in the state's tax lines, social insurance excluded (§2.4)."""
    pooled = pool["vat"] + pool["excise"] + pool["pit"] + pool["cit"]
    return pool["other"] / (pooled + pool["other"])


# ---------------------------------------------------------------- labels (§6)

def _band(r: Fraction | None) -> str:
    """An undefined ratio (the richest tenth's burden is 0) is read as above the band, everywhere."""
    lo, hi = C.SIMILAR_BAND
    if r is None:
        return "higher"
    return "higher" if r > hi else "lower" if r < lo else "similar"


def label_today(y_lo: Fraction | None, y_hi: Fraction | None) -> str:
    bands = {_band(y_lo), _band(y_hi)}
    if len(bands) > 1:
        return "depends on the assumption"
    b = bands.pop()
    return {"higher": "the poorest tenth carries a higher share of its income than the richest tenth",
            "lower": "the poorest tenth carries a lower share of its income than the richest tenth",
            "similar": "the poorest tenth carries a similar share of its income as the richest tenth"}[b]


def label_after(z: Fraction | None) -> str:
    return {"higher": "higher", "lower": "lower", "similar": "similar"}[_band(z)]


def change_ratio(z: Fraction | None, y: Fraction | None) -> Fraction | None:
    if z is None or y is None or y == 0:
        return None                                 # an undefined or infinite ratio: read as "above the band"
    return z / y


def label_change(z: Fraction | None, y_lo: Fraction | None, y_hi: Fraction | None) -> str:
    bands = {_band(change_ratio(z, y)) for y in (y_lo, y_hi)}
    if len(bands) > 1:
        return "depends on the assumption"
    return {"higher": "higher after", "lower": "lower after", "similar": "about the same"}[bands.pop()]


def monotonicity(burden: Sequence[Fraction]) -> dict[str, Any]:
    steps = [d + 2 for d in range(N - 1) if burden[d + 1] > burden[d]]      # 1-based number of the higher decile
    return {"steps_total": N - 1, "steps_where_burden_rises": len(steps), "into_deciles": steps}


# ---------------------------------------------------------------- firms, today (§2.4, §3 check 1)

def firm_range(counts: dict[str, int], labels: dict[str, str]) -> tuple[int, int]:
    low = high = 0
    for code, n in counts.items():
        lo, hi = P.band_bounds(labels[code])
        m_min, m_max = P.schedule_multiples(lo, hi)
        low += n * m_min
        high += n * m_max
    k = C.FIRM_FEE_MONTHLY * 12
    return low * k, high * k


def firms_today(inp: QbInputs) -> dict[str, Any]:
    """Descriptive, no pass or fail (design change log, before the code tag): the remainder of the budgeted fee revenue
    after modelled household payments, the schedule-implied amount from RES counts, and their ratio."""
    household_rev = C.HOUSEHOLD_ANNUAL["TV"] * inp.payers_tv + C.HOUSEHOLD_ANNUAL["R"] * inp.payers_r
    out: dict[str, Any] = {"household_revenue": household_rev, "budgeted_fee_revenue": inp.fee_revenue_2026,
                           "remainder": inp.fee_revenue_2026 - household_rev, "schedule_implied": None,
                           "schedule_implied_low": None, "ratio_remainder_to_schedule": None}
    if inp.employer_counts is None or inp.band_labels is None:
        return out
    low, high = firm_range(inp.employer_counts, inp.band_labels)
    out.update(schedule_implied=high, schedule_implied_low=low)
    if low == high and high:
        out["ratio_remainder_to_schedule"] = out["remainder"] / high
    return out


# ---------------------------------------------------------------- seniors (§7 check 8, descriptive)

def seniors_cut(inp: QbInputs, e1: dict[str, Any]) -> list[dict[str, Any]] | None:
    if not inp.seniors:
        return None
    e0 = fee_today(inp, None)
    first_ne = next((i for i in range(N) if e1["share_tv"][i] > 0), 0)
    s_tv, s_r = e1["share_tv"][first_ne], e1["share_r"][first_ne]
    out = []
    for s in inp.seniors:
        income = Fraction(s.net_per_person) * Fraction(s.members)
        exempt = income / 12 < C.EXEMPTION_MULTIPLE * living_minimum(s.members, s.children)
        pay0 = C.HOUSEHOLD_ANNUAL["TV"] * e0["pi_tv"] + C.HOUSEHOLD_ANNUAL["R"] * e0["pi_r"]
        pay1 = 0 if exempt else C.HOUSEHOLD_ANNUAL["TV"] * s_tv + C.HOUSEHOLD_ANNUAL["R"] * s_r
        out.append({"group": s.label, "households": Fraction(s.households), "mean_size": Fraction(s.members),
                    "net_income_hh": income, "exempt_by_rule": exempt, "pay_hh_e0": pay0, "pay_hh_e1": pay1,
                    "burden_e0": pay0 / income, "burden_e1": pay1 / income})
    return out
