"""The licence-fee study: the article, every number from docs/research/fees-results.json.

Writes texts/licence-fees.html from tools/fees_article/template.html, assets/licence-fees/charts.json and copies the
results file to assets/licence-fees/. With --figures it also draws the static fallback 01-burden.svg (needs
matplotlib). The study code in tools/fees is frozen at the tag fees-code-2 and is not imported.

    uv run --no-project python -I tools/fees_article/article.py
    uv run --no-project --with matplotlib python -I tools/fees_article/article.py --figures
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, LIGHT, NB, n, render

SLUG = "licence-fees"
RESULTS = ROOT / "docs" / "research" / "fees-results.json"
PAGE = ROOT / "texts" / f"{SLUG}.html"
ASSETS = ROOT / "assets" / SLUG
# tag objects are not in the results file, and CI checks out without tags
TAG_OBJECTS = {"fees-design": "70c452705e44f7f91cdf661bc942ee6eb9bcd64c",
               "fees-data-step": "ac458a9bd4e3474ac929f49643e903506598b992",
               "fees-code-2": "d766c746824d9380cbc5aca1ac20ef30bce9ae20"}
RESULTS_COMMIT = "592caa7"
CORAL = "#c0503f"
DEPENDS = "depends on the assumption"
HIGHER_TODAY = "the poorest tenth carries a higher share of its income than the richest tenth"
SHOCK = {-1: "−1 pp", 0: "forecast", 1: "+1 pp"}
READING = {"R1": "sum", "R2": "compounded"}
BASELINE = {"A": "A, 2026 budgets", "B": "B, 2025 outturn indexed"}
LABEL_CHECKS = [  # key in checks_reported, label in the table
    ("3_vat_uniform_rate", "3 · VAT at one uniform effective rate"),
    ("3_other_taxes_like_vat", "3 · other taxes allocated like VAT"),
    ("9a_social_insurance_in_pool", "9a · social insurance in the pool"),
    ("9b_cit_half_to_households", "9b · half of CIT on households"),
    ("9c_interpolated_consumption", "9c · consumption interpolated within quintiles"),
]


def bn(v: float, dp: int = 2) -> str:
    return n(v / 1e9, dp) + NB + "bn" + NB + "CZK"


def bnx(v: float, dp: int = 2) -> str:  # a figure already in bn
    return n(v, dp) + NB + "bn" + NB + "CZK"


def czk(v: float) -> str:
    return n(v) + NB + "CZK"


def pct(v: float, dp: int = 2) -> str:  # v is already in per cent
    return n(v, dp) + NB + "%"


def times(v: float) -> str:
    return n(v, 2)


def ratio_d1_d10(burden: list[float]) -> float:
    return burden[0] / burden[-1]


def law_rises(steps: list[int]) -> str:
    return ", ".join(f"1 July {y + 1}" for y in steps if y + 1 <= 2030) or "none by 2030"


def bill_rises(m: dict) -> str:
    years = sorted({t["raised_from"] for b in ("CT", "CRO") for t in m["bill_triggers"][b]})
    return ", ".join(f"from {y}" for y in years) or "none by 2030"


def num_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    refs = render((HERE / "refs.html").read_text(encoding="utf-8"), values)
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', refs, re.DOTALL))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) == set(entries), set(order) ^ set(entries)
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]",
                  lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


# ---------------------------------------------------------------- tables

def members_table(qa: dict) -> str:
    out = []
    for m in qa["members"]:
        primary = (m["shock"], m["reading"], m["baseline"]) == (0, "R1", "A")
        lab = f'{SHOCK[m["shock"]]} · {READING[m["reading"]]} · {BASELINE[m["baseline"]]}'
        lab += " <small>primary</small>" if primary else ""
        x = f'<b>{bnx(m["x"])}</b>' if primary else bnx(m["x"])
        out.append(f'  <tr><td>{lab}</td><td class="v">{x}</td><td class="v">{law_rises(m["current_law_steps"])}</td>'
                   f'<td class="v">{bill_rises(m)}</td></tr>')
    return "\n".join(out)


def paths_table(pr: dict) -> str:
    nom, lvl = pr["nominal"], pr["price_level"]
    out = []
    for y in ("2027", "2028", "2029", "2030"):
        p1 = nom["p1"]["CT"][y] + nom["p1"]["CRO"][y]
        p2 = nom["p2"]["CT"][y] + nom["p2"]["CRO"][y]
        out.append(f'  <tr><td>{y}</td><td class="v">{bn(p1, 3)}</td><td class="v">{bn(p2, 3)}</td>'
                   f'<td class="v">{n(lvl[y], 4)}</td><td class="v">{pct(float(pr["inflation"][y]), 2)}</td></tr>')
    out.append(f'  <tr><td>2027–2030, 2026 prices</td><td class="v"><b>{bn(pr["real"]["p1"])}</b></td>'
               f'<td class="v"><b>{bn(pr["real"]["p2"])}</b></td><td class="v">–</td><td class="v">–</td></tr>')
    return "\n".join(out)


def decile_table(qb: dict) -> str:
    t, a = qb["today"], qb["after"]
    out = []
    for i in range(10):
        cells = [czk(qb["income_hh_annual"][i])]
        for pay, bur in ((t["e0"]["pay_hh"], t["e0"]["burden_pct"]), (t["e1"]["pay_hh"], t["e1"]["burden_pct"]),
                         (a["per_hh"], a["burden_pct"])):
            cells.append(f'{czk(pay[i])}<small>{pct(bur[i])}</small>')
        out.append(f'  <tr><td>{i + 1}</td>' + "".join(f'<td class="v">{c}</td>' for c in cells) + "</tr>")
    return "\n".join(out)


def checks_table(res: dict) -> str:
    qb, cr = res["qb"], res["checks_reported"]
    prim = qb["labels"]
    rows = []
    c1 = cr["1_window_from_2026"]
    rows.append(("1 · current-law window from 2026", (f'X {bnx(c1["x_primary_bn"])}<small>range {n(c1["x_min_bn"], 2)} to '
                 f'{n(c1["x_max_bn"], 2)}</small>'), c1["label"], "same as primary"))
    c2 = cr["2_total_in_2026_prices"]
    rows.append(("2 · bill's total in 2026 prices", (f'Z {times(ratio_d1_d10(c2["burden_after_pct"]))}<small>total '
                 f'{bn(c2["bill_total_czk"])}</small>'), "–", "ratio unchanged"))
    for key, lab in LABEL_CHECKS[:2]:
        c = cr[key]
        rows.append((lab, f'Z {times(c["ratio_z"])}<small>firms {bn(c["firms_czk"])}</small>',
                     c["labels"]["after"], "same as primary"))
    for k, lab in (("work", "4 · PIT by employment and self-employment income"), ("net", "4 · PIT by net income")):
        c = cr["4_pit_basis"][k]
        rows.append((lab, f'Z {times(c["ratio_z"])}', c["labels"]["after"], "same as primary"))
    c5 = cr["5_payer_share_one"]
    rows.append(("5 · every household a payer (π = 1)", f'Y {times(c5["y_lo"])} to {times(c5["y_hi"])}',
                 c5["labels"]["today"], "same as primary"))
    rows.append(("6 · mean of household ratios", "not computable", "–", cr["6_mean_of_household_ratios"]["reason"]))
    rows.append(("7 · sharing percentages of 2026–2027", "not computable", "–", cr["7_sharing_2026_2027"]["reason"]))
    rows.append(("8 · seniors' cut", "described in the text", "–", "no label"))
    for key, lab in LABEL_CHECKS[2:]:
        c = cr[key]
        firms = f'<small>firms {bn(c["firms_czk"])}</small>' if c["firms_czk"] != qb["after"]["firms_czk"] else ""
        rows.append((lab, f'Z {times(c["ratio_z"])}{firms}', c["labels"]["after"], "same as primary"))
    d = cr["9d_no_exemption"]
    rows.append(("9d · no exemption for any decile", f'Y {times(d["y"])}',
                 f'today: {d["labels"]["today"]}; change: {d["labels"]["change"]} <b>≠</b>',
                 f'primary: today {prim["today"]}, change {prim["change"]}; both reported'))
    return "\n".join(f'  <tr><td>{a}</td><td class="v">{b}</td><td>{c}</td><td><small>{d}</small></td></tr>'
                     for a, b, c, d in rows)


# ---------------------------------------------------------------- the figure

def chart(res: dict) -> dict:
    qb = res["qb"]
    series = [("Today, nobody exempt (E0)", qb["today"]["e0"]["burden_pct"], GREY, "dash"),
              ("Today, poorest tenth exempt (E1)", qb["today"]["e1"]["burden_pct"], LIGHT, "dot"),
              ("After, average tax structure", qb["after"]["burden_pct"], HELD, None)]
    marks = []
    for name, ys, c, dash in series:
        m = {"type": "line", "pts": [[i + 1, round(y, 3)] for i, y in enumerate(ys)], "c": c, "w": 2, "name": name,
             "dots": True, "fmt": {"dp": 2, "unit": " %"}}
        if dash:
            m["dash"] = dash
        marks.append(m)
    return {"alt": "Payment as a share of mean net household income, by income decile. Today with nobody exempt the "
                   f"share falls from {pct(qb['today']['e0']['burden_pct'][0])} in decile 1 to "
                   f"{pct(qb['today']['e0']['burden_pct'][9])} in decile 10; with the poorest tenth exempt decile 1 pays "
                   f"nothing; funded from the state budget it falls from {pct(qb['after']['burden_pct'][0])} to "
                   f"{pct(qb['after']['burden_pct'][9])}.",
            "panels": [{"h": 280,
                        "x": {"kind": "linear", "domain": [0.6, 10.4], "ticks": list(range(1, 11)), "fmt": {"dp": 0},
                              "label": "income decile (1 = poorest tenth of households)"},
                        "y": {"kind": "linear", "domain": [0, 0.8], "ticks": [0, 0.2, 0.4, 0.6, 0.8],
                              "fmt": {"dp": 1, "unit": " %"}, "label": "payment, % of mean net household income"},
                        "marks": marks}],
            "legend": [{"label": name, "c": c, **({"dash": dash} if dash else {})} for name, _, c, dash in series],
            "table": {"cols": ["decile", *[f"{name}, %" for name, *_ in series]],
                      "rows": [[i + 1, *[round(ys[i], 3) for _, ys, *_ in series]] for i in range(10)]},
            "data": ["results.json"]}


def static_chart(res: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY,
                         "svg.fonttype": "none", "svg.hashsalt": SLUG})
    spec = chart(res)
    f, ax = plt.subplots(figsize=(7.2, 3.4))
    ls = {"dash": (0, (5, 3)), "dot": (0, (1.5, 2.5)), None: "-"}
    for m in spec["panels"][0]["marks"]:
        xs, ys = zip(*m["pts"])
        ax.plot(xs, ys, color=m["c"], lw=1.6, ls=ls[m.get("dash")], marker="o", ms=3.5, label=m["name"])
    ax.set_xticks(range(1, 11))
    ax.set_ylim(0, 0.8)
    ax.set_xlabel("income decile (1 = poorest tenth of households)")
    ax.set_ylabel("% of mean net household income")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    f.tight_layout()
    f.savefig(path, metadata={"Date": None})
    plt.close(f)


# ---------------------------------------------------------------- the values

def values(res: dict) -> dict:
    qa, qb, rc, fi = res["qa"], res["qb"], res["reading_c"], res["firms"]
    pr, members = qa["primary"], qa["members"]
    cr, cf = res["checks_reported"], res["checks_flag"]
    inf = {y: Decimal(v) for y, v in pr["inflation"].items()}

    # the text states these; fail loudly if a re-run changed them
    assert qa["label"] == "bill lower" and len(members) == 12 and all(m["x"] >= 0.1 for m in members)
    assert qa["x_min_bn"] == min(m["x"] for m in members) and qa["x_max_bn"] == qa["x_primary_bn"]
    assert pr["current_law_steps"] == [2027] and pr["bill_triggers"] == {"CT": [], "CRO": []}
    assert qa["paths_2_and_3_coincide_in_primary"] and pr["x_23"] == 0
    for m in members:
        assert m["current_law_steps"] == {-1: [2028], 0: [2027], 1: [2027, 2029]}[m["shock"]]
        raised = {t["raised_from"] for b in ("CT", "CRO") for t in m["bill_triggers"][b]}
        assert raised == (set() if m["shock"] != 1 else {2030} if m["reading"] == "R1" else {2029})
        assert m["paths_2_and_3_coincide"] == (m["shock"] != 1)
    assert qb["labels"] == {"today": DEPENDS, "after": "higher", "change": DEPENDS}
    assert qb["y_lo"] == 0 and qb["exempt_deciles_e1"] == [1] and qb["y_order_ok"]
    assert qb["e1_payer_shortfall"] == {"tv": 0, "radio": 0} and not qb["payer_share"]["above_one"]
    mono = qb["monotonicity"]
    assert mono["today_e0"]["steps_where_burden_rises"] == 0
    assert mono["today_e1"]["into_deciles"] == [2] and mono["after_base"]["into_deciles"] == [7]
    assert qb["after"]["burden_pct"][0] == max(qb["after"]["burden_pct"])
    assert cf["1_fee_revenue_today"]["identity_holds_by_construction"] and cf["2_allocation_to_the_crown"]["passed"]
    assert cf["2_allocation_to_the_crown"]["total_czk"] == rc["bill_2027_czk"] == 7807592000
    assert sum(qb["after"]["parts_by_tax_czk"].values()) == rc["bill_2027_czk"]
    assert sum(qb["after"]["decile_total_czk"]) + qb["after"]["firms_czk"] == rc["bill_2027_czk"]
    assert cr["1_window_from_2026"]["label"] == "bill lower" and not cr["1_window_from_2026"]["primary_label_differs"]
    assert all(not cr[k]["differs_from_primary"] and cr[k]["labels"] == qb["labels"] for k, _ in LABEL_CHECKS)
    assert all(not c["differs_from_primary"] for c in cr["4_pit_basis"].values())
    assert cr["4_pit_basis"]["tax"]["ratio_z"] == qb["after"]["ratio_z"]
    assert cr["5_payer_share_one"]["labels"] == qb["labels"]
    assert not cr["6_mean_of_household_ratios"]["computable"] and not cr["7_sharing_2026_2027"]["computable"]
    d9 = cr["9d_no_exemption"]["labels"]
    assert d9 == {"today": HIGHER_TODAY, "after": "higher", "change": "lower after"}
    assert cr["9d_no_exemption"]["y"] == qb["y_hi"]
    assert all(not s["exempt_by_rule"] for s in res["seniors"]) and res["seniors"] == cr["8_seniors"]
    assert res["qb"]["income_year"] == 2024 and qb["survey_year"] == 2025
    assert fi["household_revenue"] + fi["remainder"] == fi["budgeted_fee_revenue"] == rc["budgeted_fee_revenue_2026_czk"]
    assert qb["after"]["firms_czk"] == qb["after"]["parts_by_tax_czk"]["cit"] == fi["after_czk"]
    stamp = res["design"]["stamp"]["tag_commits"]
    assert stamp["fees-code-2"].startswith("7c6b692") and stamp["fees-design"].startswith("325cc53")

    real_bill = rc["bill_2027_in_2026_prices_czk"]
    v = {
        "x": bnx(qa["x_primary_bn"]), "x_min": n(qa["x_min_bn"], 2), "x_max": n(qa["x_max_bn"], 2),
        "x_b": bnx(next(m["x"] for m in members if (m["shock"], m["reading"], m["baseline"]) == (0, "R1", "B"))),
        "p1_real": bn(pr["real"]["p1"]), "p2_real": bn(pr["real"]["p2"]),
        "inf25": n(float(inf["2025"]), 1), "inf26": n(float(inf["2026"]), 2), "inf27": n(float(inf["2027"]), 2),
        "inf28": n(float(inf["2028"]), 2), "inf29": n(float(inf["2029"]), 1),
        "law_sum": n(float(inf["2025"] + inf["2026"] + inf["2027"]), 2),
        "bill_sum": n(float(inf["2026"] + inf["2027"] + inf["2028"] + inf["2029"]), 2),
        "ct26": bn(pr["baseline_2026"]["CT"]), "cro26": bn(pr["baseline_2026"]["CRO"], 3),
        "ct25": bn(res["inputs"]["realised_2025_czk"]["CT"]), "cro25": bn(res["inputs"]["realised_2025_czk"]["CRO"]),
        "members_table": members_table(qa), "paths_table": paths_table(pr),
        # reading C
        "b_today": bn(rc["budgeted_fee_revenue_2026_czk"]), "bill27": bn(rc["bill_2027_czk"], 3),
        "bill27_real": bn(real_bill), "d_level": bn(rc["budgeted_fee_revenue_2026_czk"] - real_bill),
        # Q-B
        "y_lo": times(qb["y_lo"]), "y_hi": times(qb["y_hi"]), "z": times(qb["after"]["ratio_z"]),
        "z_vat": times(qb["after"]["ratio_z_vat_only"]), "z_pit": times(qb["after"]["ratio_z_pit_only"]),
        "z_over_y": times(qb["after"]["ratio_z"] / qb["y_hi"]),
        "payers_tv": n(res["inputs"]["household_payers"]["tv"]), "payers_r": n(res["inputs"]["household_payers"]["radio"]),
        "households": n(qb["households_total"]),
        "pi_tv": pct(100 * qb["payer_share"]["tv"], 1), "pi_r": pct(100 * qb["payer_share"]["radio"], 1),
        "pay_e0": czk(qb["today"]["e0"]["pay_hh"][0]), "pay_e1": czk(qb["today"]["e1"]["pay_hh"][1]),
        "b0_d1": pct(qb["today"]["e0"]["burden_pct"][0]), "b0_d10": pct(qb["today"]["e0"]["burden_pct"][9]),
        "ba_d1": pct(qb["after"]["burden_pct"][0]), "ba_d10": pct(qb["after"]["burden_pct"][9]),
        "ba_d6": pct(qb["after"]["burden_pct"][5]), "ba_d7": pct(qb["after"]["burden_pct"][6]),
        "pa_d1": czk(qb["after"]["per_hh"][0]), "pa_d10": czk(qb["after"]["per_hh"][9]),
        "vat": bn(qb["after"]["parts_by_tax_czk"]["vat"]), "excise": bn(qb["after"]["parts_by_tax_czk"]["excise"]),
        "pit": bn(qb["after"]["parts_by_tax_czk"]["pit"]), "cit": bn(qb["after"]["parts_by_tax_czk"]["cit"]),
        "hh_after": bn(sum(qb["after"]["decile_total_czk"])),
        "out_pool": pct(100 * qb["after"]["out_of_pool_share_of_state_tax_lines"], 1),
        "inc_d1": czk(qb["income_hh_annual"][0]), "inc_d10": czk(qb["income_hh_annual"][9]),
        "decile_table": decile_table(qb),
        # firms
        "hh_rev": bn(fi["household_revenue"]), "f_today": bn(fi["remainder"]), "f_sched": bn(fi["schedule_implied"]),
        "f_ratio": times(fi["ratio_remainder_to_schedule"]), "f_after": bn(fi["after_czk"]),
        # seniors
        **{f"s{i}_{k}": f for i, s in enumerate(res["seniors"], 1) for k, f in (
            ("hh", n(s["households"])), ("inc", czk(s["net_income_hh"])),
            ("b0", pct(100 * s["burden_e0"])), ("b1", pct(100 * s["burden_e1"])))},
        # checks
        "checks_table": checks_table(res),
        "c1_x": bnx(cr["1_window_from_2026"]["x_primary_bn"]), "c1_min": n(cr["1_window_from_2026"]["x_min_bn"], 2),
        "c9a": times(cr["9a_social_insurance_in_pool"]["ratio_z"]), "c9b": times(cr["9b_cit_half_to_households"]["ratio_z"]),
        "c9c": times(cr["9c_interpolated_consumption"]["ratio_z"]),
        "c4w": times(cr["4_pit_basis"]["work"]["ratio_z"]), "c4n": times(cr["4_pit_basis"]["net"]["ratio_z"]),
        "c3u": times(cr["3_vat_uniform_rate"]["ratio_z"]), "c3o": times(cr["3_other_taxes_like_vat"]["ratio_z"]),
        "n_alloc": len(cf["2_allocation_to_the_crown"]["allocations_checked"]),
        "lbl_9d_today": d9["today"], "lbl_9d_change": d9["change"],
        # metadata
        "tag_design": stamp["fees-design"], "tag_data": stamp["fees-data-step"], "tag_code": stamp["fees-code-2"],
        "obj_design": TAG_OBJECTS["fees-design"], "obj_data": TAG_OBJECTS["fees-data-step"],
        "obj_code": TAG_OBJECTS["fees-code-2"], "results_commit": RESULTS_COMMIT,
        "v_python": res["versions"]["python"], "v_pdftotext": res["versions"]["pdftotext"].split()[-1],
    }
    # the pre-written readings of design §1, as the study code filled them, carry the same numbers
    assert f"receive {v['x']} less (2026 prices)".replace(NB, " ") in qa["reading_a"].replace(NB, " ")
    rb = qb["reading_b"]
    for k in ("z", "z_vat", "z_pit"):
        assert f"{v[k]} times" in rb, k
    assert f"between {n(qb['y_lo'], 2)} and {v['y_hi']} times" in rb
    for k in ("f_today", "f_sched", "f_after"):
        assert v[k].replace(NB, " ") in rb, k
    assert f"which is {v['d_level'].replace(NB, ' ')} (2026 prices) less" in rc["text"]
    assert f"get {v['b_today'].replace(NB, ' ')} a year" in rc["text"]
    return v


def build(res: dict) -> str:
    v = values(res)
    return num_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}), v)


def charts_json(res: dict) -> str:
    return json.dumps({"burden": chart(res)}, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    PAGE.write_text(build(res), encoding="utf-8")
    ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy(RESULTS, ASSETS / "results.json")
    (ASSETS / "charts.json").write_text(charts_json(res), encoding="utf-8")
    if "--figures" in sys.argv:
        static_chart(res, ASSETS / "01-burden.svg")
    print(f"wrote {PAGE.relative_to(ROOT)} and assets/{SLUG}/")


if __name__ == "__main__":
    main()
