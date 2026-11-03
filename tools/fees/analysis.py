"""Assembles the registered results (aggregates only) from parsed inputs: Q-A, Q-B, readings B and C, firms, the
seniors' cut and the checks, numbered as the design numbers them. Pure: no file is read here."""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Any

import config as C
import legal as L
import model as M
import readings as R


def jsonable(x: Any) -> Any:
    """Floats appear only here, for display; exact values stay integers or decimal strings."""
    if isinstance(x, Fraction):
        return x.numerator if x.denominator == 1 else float(x)
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def pct(xs):
    return [x * 100 for x in xs]


def qa_section(qa: L.QaInputs, window_start: int) -> dict[str, Any]:
    ms = L.qa_members(qa, window_start)
    xs = [m["x"] for m in ms]
    prim = next(m for m in ms if (m["shock"], m["reading"], m["baseline"]) == tuple(C.PRIMARY.values()))
    return {"window_start": window_start, "label": L.qa_label(xs), "x_primary_bn": prim["x"], "x_min_bn": min(xs),
            "x_max_bn": max(xs), "primary": prim, "members": ms,
            "paths_2_and_3_coincide_in_primary": prim["paths_2_and_3_coincide"],
            "reading_a": R.reading_a(L.qa_label(xs), prim["x"], xs)}


def qa_compact(sec: dict) -> dict:
    return {"window_start": sec["window_start"], "label": sec["label"], "x_primary_bn": sec["x_primary_bn"],
            "x_min_bn": sec["x_min_bn"], "x_max_bn": sec["x_max_bn"],
            "members": [{k: m[k] for k in ("shock", "reading", "baseline", "x", "x_13", "x_23", "current_law_steps",
                                           "bill_triggers", "paths_2_and_3_coincide")} for m in sec["members"]]}


def qb_labels(y_lo, y_hi, z) -> dict[str, str]:
    return {"today": M.label_today(y_lo, y_hi), "after": M.label_after(z), "change": M.label_change(z, y_lo, y_hi)}


def y_range(inp: M.QbInputs, pi_one: bool = False):
    e1 = M.fee_today(inp, M.exempt_flags(inp.silc), pi_one)
    e0 = M.fee_today(inp, None, pi_one)
    return e0, e1


def run(inp: M.QbInputs, qa: L.QaInputs, gross_labels: dict[str, bool] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    # ------------------------------------------------------------ Q-A
    qa_main = qa_section(qa, C.CURRENT_WINDOW_START)
    out["qa"] = {k: v for k, v in qa_main.items() if k != "members"} | {"members": qa_compact(qa_main)["members"]}
    prim = qa_main["primary"]
    pl27 = prim["price_level"][2027]
    # ------------------------------------------------------------ Q-B today
    e0, e1 = y_range(inp)
    flags = M.exempt_flags(inp.silc)
    y_lo, y_hi = e1["ratio"], e0["ratio"]
    base = M.after(inp)
    z = base["ratio"]
    z_vat = M.after(inp, scenario="vat_only")["ratio"]
    z_pit = M.after(inp, scenario="pit_only")["ratio"]
    checked = ["base", "vat_only", "pit_only"]
    labels = qb_labels(y_lo, y_hi, z)
    hh = M.households(inp)
    out["qb"] = {
        "income_year": inp.silc.income_year, "survey_year": inp.silc.survey_year,
        "ranking": "net money income per modified OECD consumption unit (Tab. 3a); consumption quintiles per person",
        "households": hh, "households_total": sum(hh), "mean_equivalent_size_cu": [Fraction(x) for x in inp.silc.cu],
        "mean_members": [Fraction(x) for x in inp.silc.members], "income_hh_annual": e0["income_hh"],
        "payer_share": {"tv": e0["pi_tv"], "radio": e0["pi_r"],
                        "above_one": bool(e0["pi_tv"] > 1 or e0["pi_r"] > 1)},
        "exempt_deciles_e1": [i + 1 for i, f in enumerate(flags) if f],
        "e1_payer_shortfall": {"tv": e1["shortfall_tv"], "radio": e1["shortfall_r"]},
        "today": {"e0": {"pay_hh": e0["pay_hh"], "burden_pct": pct(e0["burden"]), "ratio_y": y_hi},
                  "e1": {"pay_hh": e1["pay_hh"], "burden_pct": pct(e1["burden"]), "ratio_y": y_lo}},
        "y_lo": y_lo, "y_hi": y_hi, "y_order_ok": (y_lo is not None and y_hi is not None and y_lo <= y_hi),
        "after": {"per_hh": base["per_hh"], "burden_pct": pct(base["burden"]), "ratio_z": z,
                  "parts_by_tax_czk": base["parts"], "firms_czk": base["firms"],
                  "decile_total_czk": base["decile_total"],
                  "ratio_z_vat_only": z_vat, "ratio_z_pit_only": z_pit,
                  "out_of_pool_share_of_state_tax_lines": M.out_of_pool_share(inp.pool),
                  "pool_lines_czk": {k: v for k, v in inp.pool.items()}},
        "labels": labels,
        "monotonicity": {"today_e0": M.monotonicity(e0["burden"]), "today_e1": M.monotonicity(e1["burden"]),
                         "after_base": M.monotonicity(base["burden"])},
        "reading_b": R.reading_b(y_lo, y_hi, z, z_vat, z_pit),
        "debt_scenario": "if the amount is borrowed, current households carry nothing now",
    }
    # ------------------------------------------------------------ reading C and firms
    budget = inp.fee_revenue_2026
    out["reading_c"] = {"budgeted_fee_revenue_2026_czk": budget, "bill_2027_czk": C.BILL_TOTAL,
                        "bill_2027_in_2026_prices_czk": Fraction(C.BILL_TOTAL) / pl27,
                        "text": R.reading_c(budget, C.BILL_TOTAL, Fraction(C.BILL_TOTAL) / pl27)}
    firms = M.firms_today(inp)
    out["firms"] = {**firms, "after_czk": base["firms"], "reading": R.reading_firms(firms, base["firms"])}
    # ------------------------------------------------------------ seniors
    out["seniors"] = M.seniors_cut(inp, e1)
    # ------------------------------------------------------------ checks of §3 (flag the run)
    out["checks_flag"] = {
        "1_fee_revenue_today": {"identity_holds_by_construction": True, "remainder_plausible": firms["plausible"],
                                "range_czk": firms["range"], "response": firms["response"],
                                "household_payments_unvalidated": not firms["validated"]},
        "2_allocation_to_the_crown": {"passed": True, "total_czk": C.BILL_TOTAL, "allocations_checked": checked},
    }
    # ------------------------------------------------------------ checks of §7 (reported, never relabel)
    rep: dict[str, Any] = {}
    cw = qa_section(qa, C.CHECK_WINDOW_START)
    rep["1_window_from_2026"] = {**qa_compact(cw), "primary_label_differs": cw["label"] != qa_main["label"]}
    rep["2_total_in_2026_prices"] = {"bill_total_czk": Fraction(C.BILL_TOTAL) / pl27, "price_level_2027": pl27,
                                     "burden_after_pct": [b / pl27 * 100 for b in base["burden"]],
                                     "per_hh_after": [p / pl27 for p in base["per_hh"]]}

    def variant(spec: M.AfterSpec, name: str, y_pair=None) -> dict[str, Any]:
        res = M.after(inp, spec)
        checked.append(name)
        yl, yh = y_pair or (y_lo, y_hi)
        lab = qb_labels(yl, yh, res["ratio"])
        return {"ratio_z": res["ratio"], "burden_pct": pct(res["burden"]), "firms_czk": res["firms"], "labels": lab,
                "differs_from_primary": lab != labels}

    rep["3_vat_uniform_rate"] = variant(M.AfterSpec(vat_mode="uniform"), "check3_uniform_vat")
    rep["3_other_taxes_like_vat"] = variant(M.AfterSpec(other_like_vat=True), "check3_other_like_vat")
    rep["4_pit_basis"] = {b: variant(M.AfterSpec(pit_basis=b), f"check4_{b}") for b in ("tax", "work", "net")}
    f0, f1 = y_range(inp, pi_one=True)
    rep["5_payer_share_one"] = {"y_lo": f1["ratio"], "y_hi": f0["ratio"], "burden_e0_pct": pct(f0["burden"]),
                                "burden_e1_pct": pct(f1["burden"]),
                                "labels": qb_labels(f1["ratio"], f0["ratio"], z)}
    rep["6_mean_of_household_ratios"] = {"computable": False,
                                         "reason": "the SILC and consumption tables give decile and quintile means only"}
    if inp.gross_lines is not None:
        gl = variant(M.AfterSpec(lines="gross_v17"), "check7_gross_v17")
        rep["7_sharing_2026_2027"] = {"computable": True, **gl,
                                      "gross_with_2025_shares_v15": variant(M.AfterSpec(lines="gross_v15"), "check7_gross_v15")}
    else:
        rep["7_sharing_2026_2027"] = {"computable": False, "gross_lines_in_part_c_by_label": gross_labels,
                                      "reason": "Part C has no national (gross) line for every taxed item of the pool"}
    rep["8_seniors"] = out["seniors"]
    rep["9a_social_insurance_in_pool"] = variant(M.AfterSpec(include_social=True), "check9a")
    rep["9b_cit_half_to_households"] = variant(M.AfterSpec(cit_household_share=Fraction(1, 2)), "check9b")
    rep["9c_interpolated_consumption"] = variant(M.AfterSpec(interpolate=True), "check9c")
    rep["9d_no_exemption"] = {"y": y_hi, "labels": qb_labels(y_hi, y_hi, z)}
    out["checks_reported"] = rep
    out["checks_flag"]["2_allocation_to_the_crown"]["allocations_checked"] = checked
    return out
