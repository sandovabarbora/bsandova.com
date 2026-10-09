"""Chart specs for Part 3, one city, 57 budgets (texts/prague-districts.html), read by assets/charts.js.

Every number comes from the published data the static figures are drawn from, recomputed as
tools/praha/figures_districts.py and tools/praha/figures_districts_extended.py compute it:
assets/praha/districts.json (figs. 1–2), assets/praha/districts_extended.json (figs. 3–5) and
assets/praha/districts_extended_robust.json (fig. 6). Writes assets/praha/charts-districts.json.

    python3 tools/charts/prague_districts.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"
DIR = A / "praha"
D = json.loads((DIR / "districts.json").read_text())["districts"]
E = json.loads((DIR / "districts_extended.json").read_text())
R = json.loads((DIR / "districts_extended_robust.json").read_text())

HELD = "#3f6b2a"  # the green of the article's photograph, as in the figure scripts
BIG = 40000
NB = " "


def n(v: float, dp: int = 0, unit: str = "", sign: bool = False) -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    if s.strip("0.") == "":
        v = 0
    return ("−" if v < 0 else ("+" if sign and v > 0 else "")) + s + unit


def pct(v: float, dp: int = 0, sign: bool = True) -> str:
    return n(v, dp, " %", sign)


DD = "assets/praha/districts.json"
DE = "assets/praha/districts_extended.json"
DR = "assets/praha/districts_extended_robust.json"
charts = {}
alt = {}  # the <img> alt texts, set as each spec's alt
alt["per-head"] = ("Scatter of Prague's 57 districts, spending per resident against population on a log scale. The thirteen large districts cluster "
                   "between about 8 and 18 thousand crowns; Praha 1 sits at 35 thousand; small districts scatter from 8 to 35 thousand, with "
                   "Praha-Lysolaje at 73 thousand.")
alt["income"] = ("Stacked bars of income per resident for Praha 1 and the thirteen large districts: taxes and local fees in black, other non-tax "
                 "income in grey, transfers in green. Transfers are the largest part everywhere; Praha 1 has the most of all three.")
alt["city-grants"] = ("Stacked bars of the city's own in-year grants to all districts by year, 2015 to 2023, in CZK billion: 2015 about 2.2 (not "
                      "split), 2016 2.9, 2017 5.4, 2018 4.6, 2019 4.7, 2020 4.1, 2021 3.4, 2022 3.7, 2023 4.2. Investment grants, in green, "
                      "are about half to three quarters of each year.")
alt["event-study"] = ("Two lines of the difference between districts that became aligned and districts that did not, relative to the year before "
                      "each change, in percent of usual grants. Before both changes the lines run within about 20 % of zero. After November "
                      "2018: +70 % in the first year, about 0 in the second, +19 % in the third. After February 2023: −59 % in the first year; "
                      "the next two years, dashed, −95 % and +46 %.")
alt["estimate"] = ("Interval chart. The pooled estimate, −37 %, with a 95 % Conley–Taber interval from −115 to +21 %, and a wider simplified "
                   "HonestDiD interval from −143 to +69 %. The 2018 change alone at +20 %, the 2023 change alone at −67 %. A grey band marks "
                   "±20 %, a green band the published premiums of 36–47 %, and a dashed line at +100 % the smallest change the design could "
                   "detect.")
alt["spec-curve"] = ("Thirty-six dots sorted from about −81 % to +1 %. Six are above zero. The registered alignment rule gives estimates between "
                     "about −60 % and 0 %, the seat-majority rule between −81 % and −4 %, and the largest-list rule between −21 % and +1 %.")

# fig. 1 · spending per resident against size (figures_districts.per_head_vs_size)
big = lambda r: r["population"] > BIG or r["district"] == "Praha 1"  # noqa: E731
pts = []
for r in D:
    b = big(r)
    pts.append({"x": r["population"], "y": round(r["per_head"] / 1000, 3), "c": HELD if b else "light", "r": 5 if b else 3.5,
                "tip": f"{r['district']}\n{n(r['per_head'])} CZK per resident a year\n{n(r['population'])} residents"})
notes = []
for name, side, dy in [("Praha 1", 1, 0), ("Praha 4", -1, -1.6), ("Praha 2", 1, 0.8), ("Praha-Lysolaje", 1, 0)]:
    r = next(x for x in D if x["district"] == name)
    # the figure script's offsets: 6 points sideways, dy·6 points up; here a sixth of a log decade sideways
    notes.append({"type": "text", "x": round(r["population"] * (1.12 if side > 0 else 1 / 1.12)), "y": round(r["per_head"] / 1000 + dy * 1.3 - 1.2, 2),
                  "s": name, "c": "ink", "anchor": "start" if side > 0 else "end"})
charts["per-head"] = {
    "legend": [{"label": "over 40 000 residents, and Praha 1", "c": HELD, "shape": "o"}, {"label": "smaller districts", "c": "light", "shape": "o"}],
    "panels": [{"h": 300, "x": {"kind": "log", "domain": [300, 170000], "ticks": [500, 2000, 10000, 50000, 130000], "label": "residents, end of 2024 · log scale", "fmt": {"dp": 0}},
                "y": {"kind": "linear", "domain": [0, 80], "ticks": [0, 20, 40, 60, 80], "label": "spent per resident · CZK thousand", "tickfmt": {"dp": 0}},
                "marks": [{"type": "dots", "pts": [p for p in pts if p["c"] != HELD]}, {"type": "dots", "pts": [p for p in pts if p["c"] == HELD]}] + notes}],
    "table": {"cols": ["district", "residents, end of 2024", "spent per resident (CZK)"],
              "rows": [[r["district"], n(r["population"]), n(r["per_head"])] for r in sorted(D, key=lambda r: -r["per_head"])]},
    "data": [DD],
}

# fig. 2 · income per resident (figures_districts.income_per_head); largest income at the top, as in the figure
rows = sorted([r for r in D if big(r)], key=lambda r: -r["income_per_head"]["income"])
parts = [("taxes", "taxes and local fees", "ink"), ("non_tax", "fees, rents, other non-tax", "light"), ("transfers", "transfers (city, state)", HELD)]
bars = []
for r in rows:
    ih, left = r["income_per_head"], 0.0
    for key, lab, c in parts:
        v = ih[key] / 1000
        bars.append({"y": r["district"], "x0": round(left, 3), "x1": round(left + v, 3), "c": c,
                     "tip": f"{r['district']} · {lab}\n{n(ih[key])} CZK per resident\n{n(ih['income'])} income in all"})
        left += v
charts["income"] = {
    "legend": [{"label": lab, "c": c, "shape": "box", "o": 0.85} for _, lab, c in parts],
    "panels": [{"h": 400, "x": {"kind": "linear", "domain": [0, 40], "ticks": [0, 10, 20, 30, 40], "label": "income per resident · CZK thousand, 2022–2024 mean", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": [r["district"] for r in rows]},
                "marks": [{"type": "hbar", "o": 0.85, "rows": bars}]}],
    "table": {"cols": ["district", "taxes and local fees (CZK)", "other non-tax (CZK)", "transfers (CZK)", "income (CZK)"],
              "rows": [[r["district"]] + [n(r["income_per_head"][k]) for k in ("taxes", "non_tax", "transfers", "income")] for r in rows]},
    "data": [DD],
}

# fig. 3 · the city's grants by year (figures_districts_extended.grants_by_year)
tot = E["levels"]["grants_total_czk_by_year"]
share = E["levels"]["share_investment_by_year"]
yrs = sorted(int(y) for y in tot)
scaled = {2018, 2019, 2022, 2023}  # the caption: cut at the coalition changes and scaled to a full year
gb, grow = [], []
for y in yrs:
    t = tot[str(y)] / 1e9
    note = "\ncut at the coalition change, scaled to a full year" if y in scaled else ""
    if y == 2015:  # the 2015 list cannot be split
        gb.append({"x": str(y), "y1": round(t, 4), "c": "light", "o": 0.3, "label": n(t, 1),
                   "tip": f"{y}\n{n(t, 1)} bn CZK\nthe 2015 list cannot be split"})
        grow.append([str(y), n(t, 1), "", "", ""])
        continue
    inv = t * share[str(y)]
    tip = f"{y}\n{n(t, 1)} bn CZK in all\ninvestment {n(inv, 1)} bn ({pct(100 * share[str(y)], sign=False)})\nnon-investment {n(t - inv, 1)} bn{note}"
    gb.append({"x": str(y), "y1": round(inv, 4), "c": HELD, "tip": tip})
    gb.append({"x": str(y), "y0": round(inv, 4), "y1": round(t, 4), "c": "light", "label": n(t, 1), "tip": tip})
    grow.append([str(y), n(t, 1), n(inv, 1), n(t - inv, 1), pct(100 * share[str(y)], sign=False)])
charts["city-grants"] = {
    "legend": [{"label": "investment", "c": HELD, "shape": "box", "o": 0.85}, {"label": "non-investment", "c": "light", "shape": "box", "o": 0.85},
               {"label": "2015, not split", "c": "light", "shape": "box", "o": 0.3}],
    "panels": [{"h": 260, "x": {"kind": "cat", "domain": [str(y) for y in yrs]},
                "y": {"kind": "linear", "domain": [0, 6], "ticks": [0, 1, 2, 3, 4, 5, 6], "label": "CZK billion a year", "tickfmt": {"dp": 0}},
                "marks": [{"type": "vbar", "o": 0.85, "rows": gb}]}],
    "table": {"cols": ["year", "all (bn CZK)", "investment (bn CZK)", "non-investment (bn CZK)", "investment share"], "rows": grow},
    "data": [DE],
}

# fig. 4 · event study (figures_districts_extended.event_study): each event against its own controls' usual level
es = E["event_study"]
ev_marks, ev_rel = [], {}
ev_style = {"2018": ("light", "coalition change of Nov 2018"), "2023": (HELD, "coalition change of Feb 2023")}
pf = {"dp": 0, "unit": " %", "sign": True}
for ev, (c, lab) in ev_style.items():
    cm = E["H1"]["by_event"][ev]["pre_level_ctrl"]
    by = {int(k): v / cm * 100 for k, v in es[ev]["by_year"].items()}
    desc = set(es[ev]["descriptive_years"])
    seq = [(y - es[ev]["first_post"], by[y], y) for y in sorted(by)]
    ev_rel[ev] = seq
    ev_marks.append({"type": "line", "name": lab.replace("coalition change of ", ""), "c": c, "dots": True, "fmt": pf,
                     "pts": [[r, round(v, 2)] for r, v, y in seq if y not in desc]})
    dash = [(r, v, y) for r, v, y in seq if y in desc or y == max(set(by) - desc)]
    if len(dash) > 1:
        ev_marks.append({"type": "line", "name": "drawdown lists", "c": c, "dash": "dash", "w": 1.4, "notip": True, "pts": [[r, round(v, 2)] for r, v, _ in dash]})
        ev_marks.append({"type": "dots", "c": c, "o": 0.3, "r": 4, "pts": [
            {"x": r, "y": round(v, 2), "tip": f"{lab.replace('coalition change of ', '')} · year {n(r, sign=True)} ({y})\n{pct(v)} of usual\nfrom the city's drawdown lists: shown, not tested"}
            for r, v, y in dash[1:]]})
ev_rows = []
for i in range(len(ev_rel["2018"])):
    (r1, v1, y1), (_, v2, y2) = ev_rel["2018"][i], ev_rel["2023"][i]
    ev_rows.append([n(r1, sign=True), str(y1), pct(v1), str(y2), pct(v2) + (" (drawdown lists)" if y2 in es["2023"]["descriptive_years"] else "")])
charts["event-study"] = {
    "legend": [{"label": "coalition change of Nov 2018", "c": "light"}, {"label": "coalition change of Feb 2023", "c": HELD},
               {"label": "2023, from the drawdown lists (shown, not tested)", "c": HELD, "dash": "dash"}],
    "panels": [{"h": 280, "x": {"kind": "linear", "domain": [-3.3, 2.3], "ticks": [-3, -2, -1, 0, 1, 2], "label": "years from the coalition change (regime-years)",
                                "tickfmt": {"dp": 0, "sign": True}, "fmt": {"dp": 0, "sign": True, "pre": "year "}, "nogrid": True},
                "y": {"kind": "linear", "domain": [-110, 90], "ticks": [-100, -50, 0, 50], "label": "switch-in minus control · % of usual", "tickfmt": {"dp": 0, "sign": True}},
                "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"}, {"type": "rule", "axis": "x", "v": -0.5, "c": "ink", "dash": "dot"}] + ev_marks}],
    "table": {"cols": ["year from change", "2018 change: year", "aligned − unaligned", "2023 change: year", "aligned − unaligned"], "rows": ev_rows},
    "data": [DE],
}

# fig. 5 · the estimate (figures_districts_extended.estimate)
cm = sum(v["pre_level_ctrl"] for v in E["H1"]["by_event"].values()) / len(E["H1"]["by_event"])
h = E["H1"]
est = h["estimate"] / cm * 100
ct = [v / cm * 100 for v in h["conley_taber_95"]]
hon = [v / cm * 100 for v in E["honest"]["1.0"]]
hon5 = [v / cm * 100 for v in E["honest"]["0.5"]]
by = {k: v["estimate"] / v["pre_level_ctrl"] * 100 for k, v in h["by_event"].items()}
L_CT, L_HON, L_EV = "pooled · 95 % Conley–Taber", "pooled · HonestDiD (simplified), M̄ = 1", "by event · 2018, 2023"
iv = lambda a, b: f"{n(a)} to {pct(b)}"  # noqa: E731
charts["estimate"] = {
    "legend": [{"label": "published premiums 36–47 %", "c": HELD, "shape": "box", "o": 0.2}, {"label": "equivalence margin ±20 %", "c": "grey", "shape": "box", "o": 0.15},
               {"label": "detectable at 80 % power", "c": "ink", "dash": "dash"},
               {"label": "2018 change", "c": "light", "shape": "o"}, {"label": "2023 change", "c": HELD, "shape": "o"}],
    "panels": [{"h": 230, "x": {"kind": "linear", "domain": [-160, 150], "ticks": [-150, -100, -50, 0, 50, 100],
                                "label": "on becoming aligned · % of controls' usual grants", "tickfmt": {"dp": 0, "sign": True}},
                "y": {"kind": "cat", "domain": ["", L_CT, L_HON, L_EV]},
                "marks": [{"type": "span", "v0": 36, "v1": 47, "c": HELD, "o": 0.14, "label": "published 36–47 %"},
                          {"type": "span", "v0": -20, "v1": 20, "c": "grey", "o": 0.12, "label": "±20 %"},
                          {"type": "rule", "axis": "x", "v": 100, "c": "ink", "dash": "dash", "label": "detectable at 80 % power", "anchor": "end", "dy": 26,
                           "tip": "about +100 %: the smallest change\nthe design could detect at 80 % power"},
                          {"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                          {"type": "range", "rows": [
                              {"y": L_CT, "lo": ct[0], "hi": ct[1], "mid": est, "c": "ink", "label": f"{pct(est)} ({iv(*ct)})",
                               "tip": f"{L_CT}\n{pct(est)} of the controls' usual grants\n95 %: {iv(*ct)}"},
                              {"y": L_HON, "lo": hon[0], "hi": hon[1], "mid": est, "c": "grey", "label": f"{n(hon[0])} to {pct(hon[1])}",
                               "tip": f"{L_HON}\n{pct(est)}\ninterval {iv(*hon)}\nat half the bound: {iv(*hon5)}"},
                              {"y": L_EV, "mid": by["2018"], "c": "light", "label": f"2018 {pct(by['2018'])}",
                               "tip": f"the 2018 change alone\n{pct(by['2018'])} of its controls' usual grants\n{h['by_event']['2018']['switch_in']} turned aligned, {h['by_event']['2018']['controls']} controls"},
                              {"y": L_EV, "mid": by["2023"], "c": HELD, "label": f"2023 {pct(by['2023'])}",
                               "tip": f"the 2023 change alone\n{pct(by['2023'])} of its controls' usual grants\n{h['by_event']['2023']['switch_in']} turned aligned, {h['by_event']['2023']['controls']} controls"}]}]}],
    "table": {"cols": ["", "estimate", "interval"],
              "rows": [[L_CT, pct(est), iv(*ct)], [L_HON, pct(est), iv(*hon)], ["pooled · HonestDiD (simplified), M̄ = 0.5", pct(est), iv(*hon5)],
                       ["2018 change alone", pct(by["2018"]), ""], ["2023 change alone", pct(by["2023"]), ""],
                       ["published premiums", "36 to 47 %", ""], ["equivalence margin", "±20 %", ""], ["detectable at 80 % power", "about +100 %", ""]]},
    "data": [DE],
}

# fig. 6 · specification curve (figures_districts_extended.spec_curve)
specs = sorted(R["specification_curve"]["specs"], key=lambda s: s["relative"])
RULE = {"A": ("mayor's party (registered)", HELD), "seat_majority": ("seat majority", "ink"), "largest_list_has_coalition_party": ("largest list", "light")}
SCALE = {"total_R": "against 2016 formula money", "total_pc": "per resident", "total_log": "log"}
SAMPLE = {"all": "all districts", "no_under_1000": "without districts under 1 000 residents"}


def spec_desc(s: dict) -> list[str]:
    return [RULE[s["rule"]][0], SCALE[s["scale"]], "without the 2015–16 interregnum" if s["without_interregnum"] else "with the 2015–16 interregnum", SAMPLE[s["sample"]]]


charts["spec-curve"] = {
    "legend": [{"label": lab, "c": c, "shape": "o"} for lab, c in RULE.values()],
    "panels": [{"h": 260, "x": {"kind": "linear", "domain": [-1, len(specs)], "ticks": [], "nogrid": True, "label": f"{len(specs)} specifications, sorted"},
                "y": {"kind": "linear", "domain": [-90, 10], "ticks": [-80, -60, -40, -20, 0], "label": "% of the controls' usual level", "tickfmt": {"dp": 0, "sign": True}},
                "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                          {"type": "dots", "r": 4, "pts": [{"x": i, "y": round(100 * s["relative"], 2), "c": RULE[s["rule"]][1],
                                                            "tip": "\n".join([f"{pct(100 * s['relative'])} of the controls' usual level"] + spec_desc(s) + [f"p = {s['p_ri']:.2f} (randomisation)"])}
                                                           for i, s in enumerate(specs)]}]}],
    "table": {"cols": ["estimate", "alignment", "scaling", "interregnum", "districts", "p (randomisation)"],
              "rows": [[pct(100 * s["relative"])] + spec_desc(s)[:2] + ["left out" if s["without_interregnum"] else "kept", SAMPLE[s["sample"]], f"{s['p_ri']:.2f}"] for s in specs]},
    "data": [DR],
}

for k, spec in charts.items():
    spec["alt"] = alt[k]
    spec["data"] = ["../" + p for p in spec["data"]]  # data links are relative to the article (texts/)
out = DIR / "charts-districts.json"
out.write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
print(len(charts), "charts →", out)
