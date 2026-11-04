"""The licence-fee study: the article, every number from docs/research/fees-results.json.

Writes texts/licence-fees.html from tools/fees_article/template.html, assets/licence-fees/charts.json and copies the
results file to assets/licence-fees/. With --figures it also draws the static fallbacks 01-money.svg to 05-burden.svg
(needs matplotlib). The study code in tools/fees is frozen at the tag fees-code-2 and is not imported.

    uv run --no-project python -I tools/fees_article/article.py
    uv run --no-project --with matplotlib python -I tools/fees_article/article.py --figures
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, INK, LIGHT, NB, n, render

SLUG = "licence-fees"
RESULTS = ROOT / "docs" / "research" / "fees-results.json"
PAGE = ROOT / "texts" / f"{SLUG}.html"
ASSETS = ROOT / "assets" / SLUG
# tag objects are not in the results file, and CI checks out without tags
TAG_OBJECTS = {"fees-design": "70c452705e44f7f91cdf661bc942ee6eb9bcd64c",
               "fees-code": "ceee4784cd96db5ccc3070b2d11530eb7320d848",
               "fees-data-step": "ac458a9bd4e3474ac929f49643e903506598b992",
               "fees-code-2": "d766c746824d9380cbc5aca1ac20ef30bce9ae20"}
RESULTS_COMMIT = "592caa7"
FIRST_CODE_COMMIT = "a6e005e"  # fees-code, superseded by fees-code-2
CORAL = "#c0503f"
DEPENDS = "depends on the assumption"
HIGHER_TODAY = "the poorest tenth carries a higher share of its income than the richest tenth"
SHOCK = {-1: "−1 pp", 0: "forecast", 1: "+1 pp"}
READING = {"R1": "sum", "R2": "compounded"}
BASELINE = {"A": "2026 budgets", "B": "2025 outturn, indexed"}
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
        rows.append((lab, (f'Z {times(c["ratio_z"])}<small>firms {bn(c["firms_czk"])} after, not like for like with '
                           f"today's remainder</small>"), c["labels"]["after"], "same as primary"))
    for k, lab in (("work", "4 · PIT by employment and self-employment income"), ("net", "4 · PIT by net income")):
        c = cr["4_pit_basis"][k]
        rows.append((lab, f'Z {times(c["ratio_z"])}', c["labels"]["after"], "same as primary"))
    c5 = cr["5_payer_share_one"]
    rows.append(("5 · every household a payer (π = 1)", (f'Y {times(c5["y_lo"])} to {times(c5["y_hi"])}<small>exemptions '
                                                          'counted by entitlement</small>'),
                 c5["labels"]["today"], "same as primary"))
    rows.append(("6 · mean of household ratios", "not computable", "–", cr["6_mean_of_household_ratios"]["reason"]))
    rows.append(("7 · sharing percentages of 2026–2027", "not computable", "–", cr["7_sharing_2026_2027"]["reason"]))
    rows.append(("8 · seniors' cut", "described in the text", "–", "no label"))
    for key, lab in LABEL_CHECKS[2:]:
        c = cr[key]
        firms = (f'<small>firms {bn(c["firms_czk"])} after, not like for like with today\'s remainder</small>'
                 if c["firms_czk"] != qb["after"]["firms_czk"] else "")
        rows.append((lab, f'Z {times(c["ratio_z"])}{firms}', c["labels"]["after"], "same as primary"))
    d = cr["9d_no_exemption"]
    rows.append(("9d · no exemption for any decile", f'Y {times(d["y"])}<small>the no-exemption bound of the range</small>',
                 f'today: {d["labels"]["today"]}; change: {d["labels"]["change"]} <b>≠</b>',
                 f'primary: today {prim["today"]}, change {prim["change"]}; both reported'))
    return "\n".join(f'  <tr><td>{a}</td><td class="v">{b}</td><td>{c}</td><td><small>{d}</small></td></tr>'
                     for a, b, c, d in rows)


# ---------------------------------------------------------------- the figures

YEARS = ("2027", "2028", "2029", "2030")


def money_paths(qa: dict) -> dict[str, list[float]]:
    """Current law (path 1) and the bill (path 2) for ČT and ČRo together, per year, in bn CZK of 2026 prices."""
    pr = qa["primary"]
    out = {p: [(pr["nominal"][p]["CT"][y] + pr["nominal"][p]["CRO"][y]) / pr["price_level"][y] / 1e9 for y in YEARS]
           for p in ("p1", "p2")}
    for p in ("p1", "p2"):  # the yearly real amounts reproduce the study's own four-year sums
        assert math.isclose(sum(out[p]), pr["real"][p] / 1e9, rel_tol=1e-12), p
    assert math.isclose(sum(out["p1"]) - sum(out["p2"]), qa["x_primary_bn"], rel_tol=1e-12)
    return out


def money_chart(res: dict) -> dict:
    qa = res["qa"]
    m = money_paths(qa)
    xs = [int(y) for y in YEARS]
    law, bill = [round(v, 4) for v in m["p1"]], [round(v, 4) for v in m["p2"]]
    unit = {"dp": 2, "unit": " bn CZK"}
    gap = f"gap over 2027–2030: {bnx(qa['x_primary_bn'])}, 2026 prices"
    mid = (law[1] + bill[1] + law[2] + bill[2]) / 4
    return {"alt": f"ČT and ČRo together, 2027 to 2030, in 2026 prices, at the forecast inflation: current law gives "
                   f"{bnx(law[0])} in 2027 and {bnx(law[3])} in 2030, the bill {bnx(bill[0])} and {bnx(bill[3])}; "
                   f"over the four years current law gives {bn(qa['primary']['real']['p1'])} and the bill "
                   f"{bn(qa['primary']['real']['p2'])}, a gap of {bnx(qa['x_primary_bn'])}.",
            "panels": [{"h": 280, "padRight": 96,
                        "x": {"kind": "linear", "domain": [2026.8, 2030.2], "ticks": xs, "fmt": {"dp": 0, "nogroup": True},
                              "label": "year (inflation as forecast, starting from the 2026 budgets)"},
                        "y": {"kind": "linear", "domain": [0, 10], "ticks": [0, 2, 4, 6, 8, 10],
                              "fmt": {"dp": 0}, "label": "bn CZK a year, 2026 prices"},
                        "marks": [{"type": "area", "pts": [[x, b, a] for x, a, b in zip(xs, law, bill)], "c": "light",
                                   "o": 0.45, "name": "gap", "notip": True},
                                  {"type": "line", "pts": [[x, v] for x, v in zip(xs, law)], "c": INK, "w": 2,
                                   "name": "current law", "end": "current law", "dots": True, "fmt": unit},
                                  {"type": "line", "pts": [[x, v] for x, v in zip(xs, bill)], "c": HELD, "w": 2,
                                   "name": "the bill", "end": "the bill", "dots": True, "fmt": unit},
                                  {"type": "text", "x": 2027.12, "y": round(mid, 3), "dy": 4, "s": gap, "c": INK,
                                   "narrow": {"s": f"gap {bnx(qa['x_primary_bn'])}"}}]}],
            "legend": [{"label": "current law, fees, payers held fixed", "c": INK},
                       {"label": "the bill as introduced", "c": HELD},
                       {"label": "gap", "c": "light", "shape": "box", "o": 0.45}],
            "table": {"cols": ["year", "current law, bn CZK (2026 prices)", "the bill, bn CZK (2026 prices)", "gap, bn CZK"],
                      "rows": [*[[x, a, b, round(a - b, 4)] for x, a, b in zip(xs, law, bill)],
                               ["2027–2030", round(qa["primary"]["real"]["p1"] / 1e9, 4),
                                round(qa["primary"]["real"]["p2"] / 1e9, 4), round(qa["x_primary_bn"], 4)]]},
            "data": ["results.json"]}


def first_year_rows(rc: dict) -> list[dict]:
    today, bill, real = (rc["budgeted_fee_revenue_2026_czk"] / 1e9, rc["bill_2027_czk"] / 1e9,
                         rc["bill_2027_in_2026_prices_czk"] / 1e9)
    return [{"y": "fee revenue today (2026 budgets)", "x1": round(today, 4), "c": INK, "label": bnx(today),
             "tip": f"fee revenue of ČT and ČRo in the 2026 budgets: {bnx(today)} a year"},
            {"y": "the bill for 2027", "x1": round(bill, 4), "c": HELD, "label": bnx(bill, 3),
             "tip": f"the bill's contribution for 2027: {bnx(bill, 3)}, or {bnx(real)} in 2026 prices"},
            {"y": "gap, 2026 prices", "x0": round(real, 4), "x1": round(today, 4), "c": GREY,
             "label": f"{bnx(today - real)} less",
             "tip": f"{bnx(today)} today against the 2027 amount in 2026 prices, {bnx(real)}: {bnx(today - real)} less"}]


def first_year_chart(res: dict) -> dict:
    rows = first_year_rows(res["reading_c"])
    return {"alt": f"Fee revenue of ČT and ČRo in the 2026 budgets, {rows[0]['label']} a year, against the bill's "
                   f"{rows[1]['label']} for 2027; in 2026 prices the 2027 amount is {rows[2]['label']} than today.",
            "panels": [{"h": 150, "padRight": 24,
                        "x": {"kind": "linear", "domain": [0, 12], "ticks": [0, 2, 4, 6, 8, 10], "fmt": {"dp": 0},
                              "label": "bn CZK a year"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "hbar", "rows": rows}]}],
            "table": {"cols": ["", "from, bn CZK", "to, bn CZK"],
                      "rows": [[r["y"], r.get("x0", 0), r["x1"]] for r in rows]},
            "data": ["results.json"]}


def ratio_rows(qb: dict) -> list[dict]:
    a = qb["after"]
    rows = [("fee today, nobody exempt", qb["y_hi"], INK, True),
            ("fee today, poorest tenth exempt by entitlement", qb["y_lo"], GREY, True),
            ("state budget, average tax mix", a["ratio_z"], HELD, True),
            ("state budget, VAT only", a["ratio_z_vat_only"], HELD, False),
            ("state budget, income tax only", a["ratio_z_pit_only"], HELD, False)]
    return [{"y": lab, "x1": round(v, 4), "c": c, "label": times(v), "in_label": inl,
             "tip": f"{lab}: {times(v)}" + ("" if inl else ", shown for comparison")} for lab, v, c, inl in rows]


def ratio_chart(res: dict) -> dict:
    rows = ratio_rows(res["qb"])
    strip = [{k: v for k, v in r.items() if k != "in_label"} for r in rows]
    return {"alt": "The poorest tenth's share of income paid divided by the richest tenth's: the fee today "
                   f"{rows[0]['label']} with nobody exempt and {rows[1]['label']} with the poorest tenth exempt by "
                   f"entitlement; funded from the state budget {rows[2]['label']} at the average tax mix, "
                   f"{rows[3]['label']} from VAT only and {rows[4]['label']} from income tax only. "
                   "Between 0.9 and 1.1 the shares count as similar.",
            "panels": [{"h": 230, "padRight": 40,
                        "x": {"kind": "linear", "domain": [0, 6], "ticks": [0, 1, 2, 3, 4, 5, 6], "fmt": {"dp": 0},
                              "label": "poorest tenth's share of income ÷ richest tenth's"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "span", "v0": 0.9, "v1": 1.1, "c": "grey", "o": 0.14},
                                  {"type": "rule", "axis": "x", "v": 1, "c": "ink"},
                                  {"type": "hbar", "rows": [r for r, x in zip(strip, rows) if x["in_label"]]},
                                  {"type": "hbar", "o": 0.4, "rows": [r for r, x in zip(strip, rows) if not x["in_label"]]}]}],
            "legend": [{"label": "fee today, nobody exempt", "c": INK, "shape": "box", "o": 0.85},
                       {"label": "fee today, poorest tenth exempt", "c": GREY, "shape": "box", "o": 0.85},
                       {"label": "state budget, average tax mix", "c": HELD, "shape": "box", "o": 0.85},
                       {"label": "state budget, one tax alone (for comparison)", "c": HELD, "shape": "box", "o": 0.4},
                       {"label": "similar, 0.9 to 1.1; the line marks 1, the same share", "c": GREY, "shape": "box",
                        "o": 0.14}],
            "table": {"cols": ["funding", "ratio, poorest ÷ richest tenth", "used for the registered result"],
                      "rows": [[r["y"], r["x1"], "yes" if r["in_label"] else "no"] for r in rows]},
            "data": ["results.json"]}


def pay_series(qb: dict) -> list[tuple[str, list[float], str, str | None]]:
    return [("Today, nobody exempt", qb["today"]["e0"]["pay_hh"], INK, "dash"),
            ("Today, poorest tenth exempt", qb["today"]["e1"]["pay_hh"], GREY, "dot"),
            ("After, average tax mix", qb["after"]["per_hh"], HELD, None)]


def burden_series(qb: dict) -> list[tuple[str, list[float], str, str | None]]:
    return [("Today, nobody exempt", qb["today"]["e0"]["burden_pct"], INK, "dash"),
            ("Today, poorest tenth exempt", qb["today"]["e1"]["burden_pct"], GREY, "dot"),
            ("After, average tax structure", qb["after"]["burden_pct"], HELD, None)]


def decile_chart(series, alt: str, y: dict, fmt: dict, dp: int, unit: str) -> dict:
    marks = []
    for name, ys, c, dash in series:
        m = {"type": "line", "pts": [[i + 1, round(v, dp)] for i, v in enumerate(ys)], "c": c, "w": 2, "name": name,
             "dots": True, "fmt": fmt}
        if dash:
            m["dash"] = dash
        marks.append(m)
    return {"alt": alt,
            "panels": [{"h": 280,
                        "x": {"kind": "linear", "domain": [0.6, 10.4], "ticks": list(range(1, 11)), "fmt": {"dp": 0},
                              "label": "income decile (1 = poorest tenth of households)"},
                        "y": y, "marks": marks}],
            "legend": [{"label": name, "c": c, **({"dash": dash} if dash else {})} for name, _, c, dash in series],
            "table": {"cols": ["decile", *[f"{name}, {unit}" for name, *_ in series]],
                      "rows": [[i + 1, *[round(ys[i], dp) for _, ys, *_ in series]] for i in range(10)]},
            "data": ["results.json"]}


def pay_chart(res: dict) -> dict:
    qb = res["qb"]
    e0, e1, a = (s[1] for s in pay_series(qb))
    alt = (f"Average payment per household in CZK a year, by income decile. Today with nobody exempt every decile pays "
           f"{czk(e0[0])}; with the poorest tenth exempt decile 1 pays nothing and the others {czk(e1[1])}; funded "
           f"from the state budget at the average tax mix the payment rises from {czk(a[0])} in decile 1 to "
           f"{czk(a[9])} in decile 10.")
    y = {"kind": "linear", "domain": [0, 2500], "ticks": [0, 500, 1000, 1500, 2000, 2500], "fmt": {"dp": 0},
         "label": "CZK a year per household"}
    return decile_chart(pay_series(qb), alt, y, {"dp": 0, "unit": " CZK"}, 0, "CZK a year")


def burden_chart(res: dict) -> dict:
    qb = res["qb"]
    alt = ("Payment as a share of mean net household income, by income decile. Today with nobody exempt the "
           f"share falls from {pct(qb['today']['e0']['burden_pct'][0])} in decile 1 to "
           f"{pct(qb['today']['e0']['burden_pct'][9])} in decile 10; with the poorest tenth exempt decile 1 pays "
           f"nothing; funded from the state budget it falls from {pct(qb['after']['burden_pct'][0])} to "
           f"{pct(qb['after']['burden_pct'][9])}.")
    y = {"kind": "linear", "domain": [0, 0.8], "ticks": [0, 0.2, 0.4, 0.6, 0.8], "fmt": {"dp": 1, "unit": " %"},
         "label": "payment, % of mean net household income"}
    return decile_chart(burden_series(qb), alt, y, {"dp": 2, "unit": " %"}, 3, "%")


# id, spec, static file; in the order of the figures on the page
CHARTS = {"money": (money_chart, "01-money.svg"), "first-year": (first_year_chart, "02-first-year.svg"),
          "pay": (pay_chart, "03-pay.svg"), "ratios": (ratio_chart, "04-ratios.svg"),
          "burden": (burden_chart, "05-burden.svg")}


def chart_hash(spec: dict) -> str:
    """Hash of the plotted numbers, written into the static SVG so a test can tell a stale figure."""
    return hashlib.sha256(json.dumps(spec["table"], sort_keys=True).encode()).hexdigest()


def static_charts(res: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY,
                         "svg.fonttype": "none", "svg.hashsalt": SLUG})
    ls = {"dash": (0, (5, 3)), "dot": (0, (1.5, 2.5)), None: "-"}

    def save(f, key: str) -> None:
        f.tight_layout()
        f.savefig(ASSETS / CHARTS[key][1], metadata={"Date": None, "Description": f"data sha256 {chart_hash(specs[key])}"})
        plt.close(f)

    specs = {k: fn(res) for k, (fn, _) in CHARTS.items()}

    p = specs["money"]["panels"][0]
    f, ax = plt.subplots(figsize=(7.2, 3.4))
    area, law, bill, note = p["marks"]
    xs = [q[0] for q in area["pts"]]
    ax.fill_between(xs, [q[1] for q in area["pts"]], [q[2] for q in area["pts"]], color=LIGHT, alpha=0.45, lw=0)
    for m in (law, bill):
        ax.plot(*zip(*m["pts"]), color=m["c"], lw=1.6, marker="o", ms=3.5, label=m["name"])
    ax.text(note["x"], note["y"], note["s"], fontsize=8, va="center")
    ax.set_xticks(xs, [str(x) for x in xs])
    ax.set_ylim(0, 10)
    ax.set_ylabel("bn CZK a year, 2026 prices")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    save(f, "money")

    for key, h in (("first-year", 1.9), ("ratios", 2.6)):
        p = specs[key]["panels"][0]
        rows = [(r, m.get("o", 0.85)) for m in p["marks"] if m["type"] == "hbar" for r in m["rows"]]
        order = p["y"]["domain"]
        f, ax = plt.subplots(figsize=(7.2, h))
        for m in p["marks"]:
            if m["type"] == "span":
                ax.axvspan(m["v0"], m["v1"], color=GREY, alpha=0.14, lw=0)
            elif m["type"] == "rule":
                ax.axvline(m["v"], color=INK, lw=0.8)
        for r, o in rows:
            i = len(order) - 1 - order.index(r["y"])
            x0 = r.get("x0", 0)
            ax.barh(i, r["x1"] - x0, left=x0, height=0.5, color=r["c"], alpha=o)
            ax.text(r["x1"] + 0.08, i, r["label"], va="center", fontsize=8)
        ax.set_yticks(range(len(order)), list(reversed(order)))
        ax.set_xlim(*p["x"]["domain"])
        ax.set_xticks(p["x"]["ticks"])
        ax.set_xlabel(p["x"]["label"])
        save(f, key)

    for key in ("pay", "burden"):
        p = specs[key]["panels"][0]
        f, ax = plt.subplots(figsize=(7.2, 3.4))
        for m in p["marks"]:
            ax.plot(*zip(*m["pts"]), color=m["c"], lw=1.6, ls=ls[m.get("dash")], marker="o", ms=3.5, label=m["name"])
        ax.set_xticks(range(1, 11))
        ax.set_ylim(*p["y"]["domain"])
        ax.set_xlabel(p["x"]["label"])
        ax.set_ylabel(p["y"]["label"])
        ax.legend(frameon=False, fontsize=8, loc="upper right" if key == "burden" else "lower right")
        save(f, key)


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
    z = qb["after"]["ratio_z"]
    # the observed directions of the reverse checks, stated in the text against design §8
    assert cr["9a_social_insurance_in_pool"]["ratio_z"] < z      # leaving social insurance out raises Z
    assert cr["9b_cit_half_to_households"]["ratio_z"] < z        # CIT on firms only raises Z, as expected
    assert cr["9c_interpolated_consumption"]["ratio_z"] > z      # the equal split lowers Z, against the expectation
    assert cr["3_vat_uniform_rate"]["ratio_z"] > z and cr["3_other_taxes_like_vat"]["ratio_z"] > z
    assert next(m["x"] for m in members if (m["shock"], m["reading"], m["baseline"]) == (0, "R1", "B")) < qa["x_primary_bn"]
    assert min(members, key=lambda m: m["x"])["baseline"] == "B"  # baseline B sets the low end of the range
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
        "ct25": bn(res["inputs"]["realised_2025_czk"]["CT"]), "cro25": bn(res["inputs"]["realised_2025_czk"]["CRO"], 3),
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
        "obj_code1": TAG_OBJECTS["fees-code"], "code1_commit": FIRST_CODE_COMMIT,
        "v_python": res["versions"]["python"], "v_pdftotext": res["versions"]["pdftotext"].split()[-1],
        **{f"alt_{k.replace('-', '_')}": html.escape(fn(res)["alt"]) for k, (fn, _) in CHARTS.items()},
        # the pre-written readings of design §1, quoted verbatim in the details
        "reading_a": html.escape(qa["reading_a"]), "reading_b": html.escape(qb["reading_b"]),
        "reading_c": html.escape(rc["text"]),
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
    return json.dumps({k: fn(res) for k, (fn, _) in CHARTS.items()}, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    PAGE.write_text(build(res), encoding="utf-8")
    ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy(RESULTS, ASSETS / "results.json")
    (ASSETS / "charts.json").write_text(charts_json(res), encoding="utf-8")
    if "--figures" in sys.argv:
        static_charts(res)
    print(f"wrote {PAGE.relative_to(ROOT)} and assets/{SLUG}/")


if __name__ == "__main__":
    main()
