"""The film-incentive study: the article, every number from docs/research/rebates-results.json.

Writes texts/film-rebates.html from tools/rebates_article/template.html, assets/film-rebates/charts.json and copies the
results file to assets/film-rebates/. With --figures it also draws the static fallbacks 01-paid.svg to 05-base.svg
(needs matplotlib). The study code in tools/rebates is frozen at the tag rebates-code and is not imported.

    uv run --no-project python -I tools/rebates_article/article.py
    uv run --no-project --with matplotlib python -I tools/rebates_article/article.py --figures
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, INK, NB, n, render

SLUG = "film-rebates"
RESULTS = ROOT / "docs" / "research" / "rebates-results.json"
PAGE = ROOT / "texts" / f"{SLUG}.html"
ASSETS = ROOT / "assets" / SLUG
# tag objects are not in the results file, and CI checks out without tags
TAG_OBJECTS = {"rebates-design": "388c23bd25d79f5c7d82d9e4e3b91c82642cb175",
               "rebates-data-step": "caf65e0b6dd3c08ae6e11d6518e7ab4a9d51a5d3",
               "rebates-code": "f63901cc27ad51f936d144d2928789aa1774ee44"}
RESULTS_COMMIT = "01ebf1c"
CORAL = "#c0503f"
# from the run entry of the design change log (a descriptive look after the run, not in the results file)
OVER_P1 = {"within_both": 198, "over_5_pct": 3, "excess_m": 27.8, "largest_m": 0.87}


def bn(v: float, dp: int = 2) -> str:
    return n(v / 1e9, dp) + NB + "bn" + NB + "CZK"


def m(v: float, dp: int = 0) -> str:
    return n(v / 1e6, dp) + NB + "m" + NB + "CZK"


def pct(r: float, dp: int = 1) -> str:  # r is a ratio
    return n(100 * r, dp) + NB + "%"


def pct_range(lo: float, hi: float, dp: int = 1) -> str:
    return f"{n(100 * lo, dp)}–{n(100 * hi, dp)}" + NB + "%"


def years(y: float) -> str:
    return n(y, 1) + NB + "years"


# ---------------------------------------------------------------- the figures

def paid_rows(res: dict) -> list[dict]:
    q1 = res["q1"]
    p = q1["decomposition"]["parts"]
    promised, paid = q1["promised"], q1["paid"]
    below, above = p["c_decided_paid_below_p0"], -p["f_decided_paid_above_p0"]
    undecided = sum(v for k, v in p.items() if k.startswith("d_"))
    cancelled = p["a_cancelled_paid_0"] + p["b_cancelled_paid_above_0"]
    assert p["e_decided_payout_pending"] == 0
    steps = [("decided, paid below the allocation", -below, CORAL),
             ("decided, paid above the allocation", above, HELD),
             ("no final decision past the deadline", -undecided, GREY),
             ("cancelled", -cancelled, GREY)]
    rows = [{"y": "allocated", "x1": round(promised / 1e9, 4), "c": INK, "label": bn(promised),
             "tip": f"allocated to the {q1['projects']} projects: {bn(promised)}"}]
    at = promised
    for lab, d, c in steps:
        rows.append({"y": lab, "x0": round(at / 1e9, 4), "x1": round((at + d) / 1e9, 4), "c": c,
                     "label": n(d / 1e6, 0, sign=True) + NB + "m",
                     "tip": f"{lab}: {n(d / 1e6, 0, sign=True)} m CZK"})
        at += d
    assert at == paid, (at, paid)
    rows.append({"y": "paid", "x1": round(paid / 1e9, 4), "c": HELD, "label": bn(paid),
                 "tip": f"paid so far: {bn(paid)}, {pct(q1['r_low'])} of the allocation"})
    return rows


def paid_chart(res: dict) -> dict:
    rows = paid_rows(res)
    q1 = res["q1"]
    return {"alt": f"The {q1['projects']} projects whose deadline has passed were allocated {rows[0]['label']} and "
                   f"paid {rows[-1]['label']}. Decided projects paid below their allocation take off "
                   f"{rows[1]['label'].lstrip('−')} CZK, those paid above it add back {rows[2]['label'].lstrip('+')} CZK, "
                   f"projects with no final decision take off {rows[3]['label'].lstrip('−')} CZK and cancelled ones "
                   f"{rows[4]['label'].lstrip('−')} CZK.",
            "panels": [{"h": 230, "padRight": 70,
                        "x": {"kind": "linear", "domain": [0, 7], "ticks": [0, 1, 2, 3, 4, 5, 6, 7], "fmt": {"dp": 0},
                              "label": "bn CZK"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "hbar", "rows": rows}]}],
            "table": {"cols": ["", "from, bn CZK", "to, bn CZK"],
                      "rows": [[r["y"], r.get("x0", 0), r["x1"]] for r in rows]},
            "data": ["results.json"]}


def time_series(res: dict) -> list[tuple[str, list[list[float]], str, str | None]]:
    out = []
    for key, name, c, dash in (("q2", "from the evidence certificate", HELD, None),
                               ("q2_from_request", "from the registration request", GREY, "dash")):
        h = res[key]["horizons_years"]
        pts = [[0, 0.0]] + [[int(y), round(100 * e["cumulative_incidence"]["decision"], 2)]
                            for y, e in h.items() if e["estimable"]]
        out.append((name, pts, c, dash))
    return out


def time_chart(res: dict) -> dict:
    series = time_series(res)
    marks = [{"type": "rule", "axis": "y", "v": 50, "c": "grey", "dash": "dot", "label": "half", "anchor": "end"}]
    for name, pts, c, dash in series:
        mk = {"type": "line", "pts": pts, "c": c, "w": 2, "name": name, "dots": True,
              "fmt": {"dp": 0, "unit": " %"}}
        if dash:
            mk["dash"] = dash
        marks.append(mk)
    ev, rq = series[0][1], series[1][1]
    return {"alt": f"Share of projects with a final incentive decision. Counted from the evidence certificate: "
                   f"{n(ev[1][1], 0)} % after 1 year, {n(ev[2][1], 0)} % after 2 and {n(ev[3][1], 0)} % after 3. "
                   f"Counted from the registration request: {n(rq[1][1], 0)} %, {n(rq[2][1], 0)} %, "
                   f"{n(rq[3][1], 0)} % and {n(rq[4][1], 0)} % after 1 to 4 years. Later years have too few projects "
                   "still waiting to estimate.",
            "panels": [{"h": 260, "padRight": 24,
                        "x": {"kind": "linear", "domain": [0, 4.2], "ticks": [0, 1, 2, 3, 4], "fmt": {"dp": 0},
                              "label": "years"},
                        "y": {"kind": "linear", "domain": [0, 100], "ticks": [0, 25, 50, 75, 100], "fmt": {"dp": 0},
                              "label": "% with a final decision"},
                        "marks": marks}],
            "legend": [{"label": name, "c": c, **({"dash": dash} if dash else {})} for name, _, c, dash in series],
            "table": {"cols": ["years", *[f"{name}, %" for name, *_ in series]],
                      "rows": [[y, *[next((p[1] for p in pts if p[0] == y), None) for _, pts, *_ in series]]
                               for y in range(5)]},
            "data": ["results.json"]}


def committed_rows(res: dict) -> list[dict]:
    b, s = res["q3"]["lists"]["B"], res["q3"]["s2026"]
    return [{"y": "still allocated, not yet paid", "x1": round(b["o"] / 1e9, 4), "c": CORAL, "label": bn(b["o"]),
             "tip": f"{b['open_projects']} projects registered 2023–2026 still waiting: {bn(b['o'])}"},
            {"y": "the Fund's whole 2026 incentive budget", "x1": round(s / 1e9, 4), "c": INK, "label": bn(s),
             "tip": f"the 2026 incentive subsidy: {bn(s)}"}]


def committed_chart(res: dict) -> dict:
    rows = committed_rows(res)
    b = res["q3"]["lists"]["B"]
    return {"alt": f"Projects registered 2023–2026 still had {rows[0]['label']} allocated and not yet paid on "
                   f"7 October 2026, {n(b['o_ratio_to_s2026'], 2)} times the Fund's whole 2026 incentive budget of "
                   f"{rows[1]['label']}.",
            "panels": [{"h": 120, "padRight": 24,
                        "x": {"kind": "linear", "domain": [0, 2.5], "ticks": [0, 0.5, 1, 1.5, 2, 2.5],
                              "fmt": {"dp": 1}, "label": "bn CZK"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "hbar", "rows": rows}]}],
            "table": {"cols": ["", "bn CZK"], "rows": [[r["y"], r["x1"]] for r in rows]},
            "data": ["results.json"]}


def size_rows(res: dict) -> list[dict]:
    q1, q4 = res["q1"], res["q4"]
    items = [("all projects past the deadline", q1, INK),
             ("larger half by allocation", q4["above_median"], CORAL),
             ("smaller half by allocation", q4["at_or_below_median"], HELD),
             ("all but the largest project", q4["without_largest"], GREY)]
    return [{"y": lab, "lo": round(100 * e["r_low"], 2), "hi": round(100 * e["r_high"], 2),
             "mid": round(50 * (e["r_low"] + e["r_high"]), 2), "c": c, "label": pct_range(e["r_low"], e["r_high"]),
             "tip": f"{lab}: {pct_range(e['r_low'], e['r_high'])} of the allocation paid, {e['projects']} projects"}
            for lab, e, c in items]


def size_chart(res: dict) -> dict:
    rows = size_rows(res)
    return {"alt": f"Share of the allocation paid: all projects past the deadline {rows[0]['label']}; the larger half "
                   f"by allocation {rows[1]['label']}; the smaller half {rows[2]['label']}; all but the single "
                   f"largest project {rows[3]['label']}. Each range runs from counting projects without a final "
                   "decision as paid what they have been paid so far to counting them as paid in full.",
            "panels": [{"h": 200, "padRight": 90,
                        "x": {"kind": "linear", "domain": [90, 102], "ticks": [90, 92, 94, 96, 98, 100, 102],
                              "fmt": {"dp": 0, "unit": " %"}, "label": "% of the allocation paid"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 95, "c": "grey", "dash": "dot"},
                                  {"type": "rule", "axis": "x", "v": 100, "c": "grey"},
                                  {"type": "range", "rows": rows}]}],
            "table": {"cols": ["projects", "low, %", "high, %"], "rows": [[r["y"], r["lo"], r["hi"]] for r in rows]},
            "data": ["results.json"]}


def base_rows(res: dict) -> list[dict]:
    q5 = res["q5"]
    ev, reg, off = q5["by_evidence_year"]["main"], q5["by_registration_year"]["main"], q5["official"]
    rows = []
    for y in ("2020", "2021"):
        rows.append({"y": f"{y} · from the lists", "x1": round(ev[y]["base"] / 1e9, 4), "c": HELD,
                     "label": bn(ev[y]["base"]),
                     "tip": f"{y}, projects allocated that year: allocation ÷ 20 %, {bn(ev[y]['base'])}"})
        rows.append({"y": f"{y} · Fund's annual report", "x1": round(off[y]["czk"] / 1e9, 4), "c": INK,
                     "label": bn(off[y]["czk"]), "tip": f"{y}, the Fund's planned costs: {bn(off[y]['czk'])}"})
    for lab, e, how in (("2025 · lists, registered that year", reg["2025"], "registered in 2025"),
                        ("2025 · lists, allocated that year", ev["2025"], "allocated in 2025")):
        rows.append({"y": lab, "x0": round(e["base_low"] / 1e9, 4), "x1": round(e["base"] / 1e9, 4), "c": HELD,
                     "o": 0.5, "label": f"{n(e['base_low'] / 1e9, 2)}–{bn(e['base'])}",
                     "tip": f"projects {how}: {n(e['base_low'] / 1e9, 2)} to {bn(e['base'])}, at 35 % to the headline rate"})
    rows.append({"y": "2025 · Fund's annual report", "x1": round(off["2025"]["czk"] / 1e9, 4), "c": INK,
                 "label": bn(off["2025"]["czk"]),
                 "tip": f"2025, evidence applications filed that year: {bn(off['2025']['czk'])}"})
    return rows


def base_chart(res: dict) -> dict:
    rows = base_rows(res)
    return {"alt": f"Planned costs implied by the allocations against the Fund's own figures, bn CZK. 2020: "
                   f"{rows[0]['label']} from the lists, {rows[1]['label']} in the annual report. 2021: "
                   f"{rows[2]['label']} against {rows[3]['label']}. 2025: {rows[4]['label']} for projects registered "
                   f"that year and {rows[5]['label']} for projects allocated that year, against {rows[6]['label']} "
                   "for evidence applications filed that year.",
            "panels": [{"h": 300, "padRight": 110,
                        "x": {"kind": "linear", "domain": [0, 12], "ticks": [0, 2, 4, 6, 8, 10, 12], "fmt": {"dp": 0},
                              "label": "bn CZK of planned eligible costs"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "hbar", "rows": [{k: v for k, v in r.items() if k != "o"}
                                                             for r in rows if "o" not in r]},
                                  {"type": "hbar", "o": 0.5, "rows": [{k: v for k, v in r.items() if k != "o"}
                                                                      for r in rows if "o" in r]}]}],
            "legend": [{"label": "from the Fund's lists: allocation ÷ rate", "c": HELD, "shape": "box", "o": 0.85},
                       {"label": "range between the two rates of 2025", "c": HELD, "shape": "box", "o": 0.5},
                       {"label": "the Fund's annual reports", "c": INK, "shape": "box", "o": 0.85}],
            "table": {"cols": ["", "from, bn CZK", "to, bn CZK"],
                      "rows": [[r["y"], r.get("x0", 0), r["x1"]] for r in rows]},
            "data": ["results.json"]}


# id, spec, static file; in the order of the figures on the page
CHARTS = {"paid": (paid_chart, "01-paid.svg"), "time": (time_chart, "02-time.svg"),
          "committed": (committed_chart, "03-committed.svg"), "size": (size_chart, "04-size.svg"),
          "base": (base_chart, "05-base.svg")}


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
    specs = {k: fn(res) for k, (fn, _) in CHARTS.items()}

    def save(f, key: str) -> None:
        f.tight_layout()
        f.savefig(ASSETS / CHARTS[key][1], metadata={"Date": None, "Description": f"data sha256 {chart_hash(specs[key])}"})
        plt.close(f)

    def bars(key: str, h: float, pad: float) -> None:
        p = specs[key]["panels"][0]
        order = p["y"]["domain"]
        f, ax = plt.subplots(figsize=(7.2, h))
        for mk in p["marks"]:
            for r in mk["rows"]:
                i = len(order) - 1 - order.index(r["y"])
                x0 = r.get("x0", 0)
                ax.barh(i, r["x1"] - x0, left=x0, height=0.5, color=r["c"], alpha=mk.get("o", 0.85))
                ax.text(max(x0, r["x1"]) + pad, i, r["label"].replace(NB, " "), va="center", fontsize=8)
        ax.set_yticks(range(len(order)), list(reversed(order)))
        ax.set_xlim(*p["x"]["domain"])
        ax.set_xticks(p["x"]["ticks"])
        ax.set_xlabel(p["x"]["label"])
        save(f, key)

    bars("paid", 2.6, 0.08)
    bars("committed", 1.5, 0.03)
    bars("base", 3.2, 0.12)

    p = specs["time"]["panels"][0]
    f, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.axhline(50, color=GREY, lw=0.8, ls=(0, (1.5, 2.5)))
    for mk in p["marks"][1:]:
        ax.plot(*zip(*mk["pts"]), color=mk["c"], lw=1.6, ls=(0, (5, 3)) if mk.get("dash") else "-", marker="o", ms=3.5,
                label=mk["name"])
    ax.set_xticks(p["x"]["ticks"])
    ax.set_ylim(0, 100)
    ax.set_xlabel(p["x"]["label"])
    ax.set_ylabel(p["y"]["label"])
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    save(f, "time")

    p = specs["size"]["panels"][0]
    rows = p["marks"][2]["rows"]
    f, ax = plt.subplots(figsize=(7.2, 2.4))
    for i, r in enumerate(reversed(rows)):
        ax.plot([r["lo"], r["hi"]], [i, i], color=r["c"], lw=3, solid_capstyle="round")
        ax.plot(r["mid"], i, "o", color=r["c"], ms=6, mec="white")
        ax.text(r["hi"] + 0.3, i, r["label"].replace(NB, " "), va="center", fontsize=8)
    ax.axvline(95, color=GREY, lw=0.8, ls=(0, (1.5, 2.5)))
    ax.axvline(100, color=GREY, lw=0.8)
    ax.set_yticks(range(len(rows)), [r["y"] for r in reversed(rows)])
    ax.set_xlim(*p["x"]["domain"])
    ax.set_xticks(p["x"]["ticks"])
    ax.set_xlabel(p["x"]["label"])
    save(f, "size")


# ---------------------------------------------------------------- the values

def values(res: dict) -> dict:
    q1, q2, q2r, q3, q4, q5 = res["q1"], res["q2"], res["q2_from_request"], res["q3"], res["q4"], res["q5"]
    c3, c6 = res["checks_3"], res["checks_6"]
    a, b = q3["lists"]["A"], q3["lists"]["B"]
    sc = q1["status_counts"]

    # the text states these; fail loudly if a re-run changed them
    assert res["label"] == q1["label"] == "nearly all paid" and 0.95 <= q1["r_low"] < 0.96 and q1["r_high"] < 0.96
    assert c6["3_by_list"]["B"]["projects"] == 0 and c6["3_by_list"]["A"]["projects"] == q1["projects"]
    assert sc["decided_payout_pending"] == 0 and sc["cancelled"] == 2
    assert all(c6[k]["band"] == "nearly all paid" for k in ("1_on_p1", "2_without_cancelled"))
    assert all(c6["8_margin"][k]["q1"]["band"] == "nearly all paid" for k in ("90", "365"))
    assert res["flags"] == ["check_6", "check_5"] and not c3["check_4_date_order"]["flag"]
    assert c3["check_5_paid_above_p1"]["decided_paid_above_p1"] == OVER_P1["within_both"] + OVER_P1["over_5_pct"]
    assert c3["data_step"]["check_6_counts"]["A"]["rows"] == 509
    for h, ok in (("1", True), ("2", True), ("3", True), ("4", False)):
        assert q2["horizons_years"][h]["estimable"] is ok, h
    assert q2r["horizons_years"]["4"]["estimable"] and not q2r["horizons_years"]["5"]["estimable"]
    assert q4["above_median"]["r_high"] < q4["at_or_below_median"]["r_low"]
    assert q5["by_registration_year"]["cancelled"] == {"2019": q5["by_registration_year"]["cancelled"]["2019"]}
    off, ev, reg = q5["official"], q5["by_evidence_year"]["main"], q5["by_registration_year"]["main"]
    assert all(ev[y]["base"] < off[y]["czk"] for y in ("2020", "2021"))
    assert reg["2025"]["base_low"] < off["2025"]["czk"] < reg["2025"]["base"] and ev["2025"]["base"] < off["2025"]["czk"]
    by_year = c6["4_by_registration_year"]
    assert min(by_year, key=lambda y: by_year[y]["r_low"]) == "2018" and max(by_year, key=lambda y: by_year[y]["r_low"]) == "2017"
    assert by_year["2017"]["r_low"] == by_year["2017"]["r_high"] > 1 and c3["check_4_date_order"]["breaches"] == 1
    assert all(c6[k]["r_low"] >= 0.95 for k in ("1_on_p1", "2_without_cancelled"))
    assert all(c6["8_margin"][k]["q1"]["r_low"] >= 0.95 for k in ("90", "365"))
    stamp = res["design"]["stamp"]["tag_commits"]
    assert stamp["rebates-code"].startswith("dd30f23") and stamp["rebates-design"].startswith("df6e654")

    p = q1["decomposition"]["parts"]
    undecided = sum(v for k, v in p.items() if k.startswith("d_"))
    h, hr = q2["horizons_years"], q2r["horizons_years"]
    ci = lambda e: n(100 * e["cumulative_incidence"]["decision"], 0) + NB + "%"
    v = {
        # paid
        "n_mature": q1["projects"], "promised": bn(q1["promised"]), "paid": bn(q1["paid"]),
        "r": pct_range(q1["r_low"], q1["r_high"]), "r_low": pct(q1["r_low"]), "r_high": pct(q1["r_high"]),
        "short": m(q1["promised"] - q1["paid"]), "below": m(p["c_decided_paid_below_p0"]),
        "above": m(-p["f_decided_paid_above_p0"]), "undecided": m(undecided),
        "cancelled": m(p["a_cancelled_paid_0"] + p["b_cancelled_paid_above_0"]),
        "n_decided": sc["decided"], "n_undecided": sc["lapsed_or_undecided"], "n_cancelled": sc["cancelled"],
        "decided_share": pct(q1["status_shares"]["decided"], 0), "median": pct(q1["median_paid_over_p0"]),
        "all_decided": pct(c6["5_all_decided"]["r"]), "n_all_decided": c6["5_all_decided"]["projects"],
        "floor": pct(c6["6_r_floor"]["r"]), "n_floor": c6["6_r_floor"]["projects"],
        "on_p1": pct_range(c6["1_on_p1"]["r_low"], c6["1_on_p1"]["r_high"]),
        "no_cancel": pct_range(c6["2_without_cancelled"]["r_low"], c6["2_without_cancelled"]["r_high"]),
        "m90": pct_range(c6["8_margin"]["90"]["q1"]["r_low"], c6["8_margin"]["90"]["q1"]["r_high"]),
        "m365": pct_range(c6["8_margin"]["365"]["q1"]["r_low"], c6["8_margin"]["365"]["q1"]["r_high"]),
        "y2018": pct_range(c6["4_by_registration_year"]["2018"]["r_low"], c6["4_by_registration_year"]["2018"]["r_high"]),
        "y2017": pct(c6["4_by_registration_year"]["2017"]["r_low"]),
        # time
        "n_q2": q2["projects"], "t50": years(q2["years_to_50_percent_decided"]),
        "t50_months": n(12 * q2["years_to_50_percent_decided"], 0), "t50r": years(q2r["years_to_50_percent_decided"]),
        "ci1": ci(h["1"]), "ci2": ci(h["2"]), "ci3": ci(h["3"]),
        "cir2": ci(hr["2"]), "cir4": ci(hr["4"]), "risk3": h["3"]["at_risk"], "risk4": h["4"]["at_risk"],
        "ci_a3": ci(c6["7_q2_list_a"]["horizons_years"]["3"]),
        # committed
        "o_b": bn(b["o"]), "n_open_b": b["open_projects"], "o_ratio": n(b["o_ratio_to_s2026"], 2),
        "o_r": f"{n(b['o_r_low'] / 1e9, 2)}–{bn(b['o_r_high'])}", "s2026": bn(q3["s2026"]),
        "o_a": m(a["o"], 1), "n_open_a": a["open_projects"], "lapsed_a": m(a["mature_lapsed_remainder"], 1),
        "n_lapsed_a": a["mature_lapsed_projects"],
        # size
        "big": pct_range(q4["above_median"]["r_low"], q4["above_median"]["r_high"]),
        "small": pct_range(q4["at_or_below_median"]["r_low"], q4["at_or_below_median"]["r_high"]),
        "median_p0": m(q4["median_p0"], 1), "big_share": pct(q4["above_median"]["promised"] / q1["promised"], 0),
        "top5": pct(q4["top_share"]["share_of_p0"], 0), "no_largest": pct_range(q4["without_largest"]["r_low"],
                                                                              q4["without_largest"]["r_high"]),
        # base
        "b20": bn(ev["2020"]["base"]), "o20": bn(off["2020"]["czk"]), "b21": bn(ev["2021"]["base"]),
        "o21": bn(off["2021"]["czk"]), "o25": bn(off["2025"]["czk"]),
        "r25": f"{n(reg['2025']['base_low'] / 1e9, 1)}–{bn(reg['2025']['base'], 1)}",
        "e25": f"{n(ev['2025']['base_low'] / 1e9, 1)}–{bn(ev['2025']['base'], 1)}",
        "gap20": pct(1 - ev["2020"]["base"] / off["2020"]["czk"], 0), "gap21": pct(1 - ev["2021"]["base"] / off["2021"]["czk"], 0),
        # checks and flags
        "rows_a": c3["data_step"]["check_6_counts"]["A"]["rows"], "over_p1": c3["check_5_paid_above_p1"]["decided_paid_above_p1"],
        "n_decided_all": c3["check_5_paid_above_p1"]["decided_projects"], "within_both": OVER_P1["within_both"],
        "over_5": OVER_P1["over_5_pct"], "excess": n(OVER_P1["excess_m"], 1) + NB + "m" + NB + "CZK",
        "largest_excess": n(OVER_P1["largest_m"], 2) + NB + "m" + NB + "CZK",
        "n_breach": c3["check_4_date_order"]["breaches"], "n_both": len(res["counts"]["cancelled_and_decided"]),
        # metadata
        "tag_design": stamp["rebates-design"], "tag_data": stamp["rebates-data-step"], "tag_code": stamp["rebates-code"],
        "obj_design": TAG_OBJECTS["rebates-design"], "obj_data": TAG_OBJECTS["rebates-data-step"],
        "obj_code": TAG_OBJECTS["rebates-code"], "results_commit": RESULTS_COMMIT,
        "v_python": res["versions"]["python"], "v_pdftotext": res["versions"]["pdftotext"].split()[-1],
        **{f"alt_{k}": html.escape(fn(res)["alt"]) for k, (fn, _) in CHARTS.items()},
    }
    return v


def num_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    refs = render((HERE / "refs.html").read_text(encoding="utf-8"), values)
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', refs, re.DOTALL))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) == set(entries), set(order) ^ set(entries)
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]",
                  lambda mt: f'<sup class="cite"><a href="#r{num[mt.group(1)]}">{num[mt.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


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
