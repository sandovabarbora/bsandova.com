"""The bypass accidents study, stage A: figures and the article, every number from the result files.

Reads docs/research/bypass-{results-a,screening,describe}.json and the registered constants of the frozen code
(estimate.py, towns.py; imported, nothing there is run or changed), writes assets/bypass-accidents/ (charts.json,
01-estimates.svg, 02-damage-only.svg and copies of the JSON files) and texts/bypass-accidents.html from
tools/bypass/template.html. Run tools/bypass/describe.py first.

    uv run --no-project --with numpy --with pandas --with statsmodels --with scipy --with matplotlib \
        python tools/bypass/article.py
"""
from __future__ import annotations

import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, INK, LIGHT, NB, n, render, results_reader, use_article_style  # noqa: E402
from estimate import DRAWS, MIN_LEAD_TOWNS, SEED  # noqa: E402
from towns import COHORTS  # noqa: E402

plt = use_article_style()
SLUG = "bypass-accidents"
R, A = ROOT / "docs" / "research", ROOT / "assets" / SLUG
CORAL, TEAL = "#c0503f", "#2a7f86"
GROUPS = {"treated": ("towns with a new bypass", HELD, "bypass towns"), "prague": ("Prague", CORAL, "Prague"),
          "other_comparison": ("other comparison towns", TEAL, "other")}
CHECKS = [  # key in results.json, label, outcome note
    ("1_all_accidents_q1", "1 · all accidents, damage-only included, Q1"),
    ("1_all_accidents_q2", "1 · all accidents, damage-only included, Q2"),
    ("2_killed_seriously_injured_q1", "2 · killed or seriously injured, Q1"),
    ("2_killed_seriously_injured_q2", "2 · killed or seriously injured, Q2"),
    ("3_without_2020_2021_q1", "3 · without 2020 and 2021"),
    ("4_plain_event_study_q1", "4 · construction years not kept apart"),
    ("5_callaway_santanna_q1", "5 · Callaway and Sant’Anna, counts in levels"),
    ("6_post_1_2_q1", "6 · post years 1–2"),
    ("6_post_1_5_q1", "6 · post years 1–5"),
    ("7_comparison_planned_only", "7 · comparison towns from the planned list only"),
    ("8_opening_year_dose_q1", "8 · opening year included as a dose"),
    ("9_town_trends_q1", "9 · town-specific linear trends"),
    ("10_old_through_road_q1", "10 · old through road only"),
    ("11_smaller_towns", "11 · smaller towns"),
    ("11_larger_towns", "11 · larger towns"),
    ("12_class_III_added", "12 · class III bypasses added"),
    ("13_class_I", "13 · class I roads"),
    ("13_class_II", "13 · class II roads"),
]


def p(v: float, dp: int = 0, sign: bool = True) -> str:
    return n(100 * v, dp, sign=sign) + NB + "%"


def iv(ci, dp: int = 0) -> str:
    def one(v: float) -> str:  # a bound that rounds to zero keeps one more decimal, so its sign shows
        d = dp + 1 if v and round(100 * v, dp) == 0 else dp
        return n(100 * v, d, sign=True)
    return f"{one(ci[0])} to {one(ci[1])}{NB}%"


def acc(v: float, dp: int = 2, sign: bool = True) -> str:
    return n(v, dp, sign=sign)


def nb(s: str) -> str:
    return s.replace(" ", NB)


def used(c: dict) -> int:
    return DRAWS - c.get("draws_missing", 0) if "draws_missing" in c else DRAWS


# ---------------------------------------------------------------- fig. 1, Q1, Q2 and the checks

def estimate_rows(res: dict) -> list[tuple[str, dict, str]]:
    q = res["questions"]
    rows = [("Q1 · town, inside the built-up area", q["q1"], "held"), ("Q2 · whole municipality", q["q2"], "held")]
    rows += [(lab, res["checks"][k], "grey") for k, lab in CHECKS]
    return rows


def estimates_chart(res: dict) -> dict:
    rows = estimate_rows(res)

    def r(lab, e, c, ci):
        return {"y": lab, "lo": round(100 * e[ci][0], 1), "hi": round(100 * e[ci][1], 1),
                "mid": round(100 * e["est"], 1), "c": c,
                "tip": f"{lab}: {p(e['est'], 1)}, 90 % {iv(e['ci90'])}, 95 % {iv(e['ci95'])}, "
                       f"{used(e)} of {DRAWS} draws"}
    r95 = [r(*x, "ci95") for x in rows]
    r90 = [r(*x, "ci90") for x in rows]
    return {"alt": "Change in police-recorded accidents in years 1–3 after a bypass opened, relative to towns still "
                   "waiting for theirs, in per cent, with 90 and 95 % intervals: Q1 inside the town and Q2 for the "
                   "whole municipality, then each registered check. Q1 and Q2 have intervals that include zero; the "
                   "check on all accidents with damage-only included lies on the positive side, the checks on killed "
                   "or seriously injured, the old through road and class I roads lie below zero.",
            "panels": [{"h": 26 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": [-130, 100], "ticks": list(range(-125, 101, 25)),
                              "fmt": {"dp": 0, "sign": True, "unit": " %"},
                              "label": "change in accidents, years 1–3 after opening, % (bootstrap by bypass)"},
                        "y": {"kind": "cat", "domain": [x[0] for x in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                                  {"type": "range", "rows": r95, "w": 1.5},
                                  {"type": "range", "rows": r90, "w": 4},
                                  {"type": "range", "rows": [{**x, "lo": None, "hi": None} for x in r90]}]}],
            "legend": [{"label": "registered questions, 90 % interval (thick) and 95 % (thin)", "c": HELD},
                       {"label": "registered checks", "c": "grey"}],
            "table": {"cols": ["estimate", "change, %", "90 % interval", "95 % interval", "draws used"],
                      "rows": [[lab, round(100 * e["est"], 1), iv(e["ci90"], 1), iv(e["ci95"], 1), used(e)]
                               for lab, e, _ in rows]},
            "data": ["results.json"]}


def static_estimates(res: dict, path: Path) -> None:
    rows = estimate_rows(res)
    f, ax = plt.subplots(figsize=(7.2, 0.3 * len(rows) + 0.9))
    ax.axvline(0, color=GREY, lw=0.8)
    for i, (lab, e, c) in enumerate(reversed(rows)):
        col = HELD if c == "held" else GREY
        ax.plot([100 * x for x in e["ci95"]], [i, i], color=col, lw=1.2)
        ax.plot([100 * x for x in e["ci90"]], [i, i], color=col, lw=3.5, solid_capstyle="round")
        ax.plot(100 * e["est"], i, "o", color=col, ms=5, mec="white")
    ax.set_yticks(range(len(rows)), [x[0] for x in reversed(rows)], fontsize=7.5)
    ax.set_xlim(-130, 100)
    ax.set_xlabel("change in accidents, years 1–3 after opening, %")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 2, damage-only and injury accidents by year

def index(series: dict) -> list[list[float]]:
    base = sum(series[str(y)] for y in range(2016, 2020)) / 4
    return [[int(y), round(100 * v / base, 1)] for y, v in sorted(series.items())]


def damage_chart(desc: dict) -> dict:
    s = desc["inside_built_up"]
    panels = []
    for kind, title in (("damage_only", "damage-only accidents"), ("injury", "injury accidents")):
        marks = [{"type": "rule", "axis": "y", "v": 100, "c": "grey"}]
        for g, (name, c, end) in GROUPS.items():
            marks.append({"type": "line", "pts": index(s[f"{g}_{kind}"]), "c": c, "name": name, "dots": True,
                          "end": end, "fmt": {"dp": 0}})
        panels.append({"title": title, "h": 210, "padRight": 80,
                       "x": {"kind": "linear", "domain": [2015.7, 2025.3], "ticks": list(range(2016, 2026)),
                             "tickLabels": {str(y): f"’{str(y)[2:]}" for y in range(2016, 2026)},
                             "fmt": {"dp": 0, "nogroup": True}, "label": "year"},
                       "y": {"kind": "linear", "domain": [40, 140], "ticks": [40, 60, 80, 100, 120, 140],
                             "fmt": {"dp": 0}, "label": "index, mean of 2016–2019 = 100"},
                       "marks": marks})
    yrs = range(2016, 2026)
    return {"alt": "Police-recorded accidents inside the built-up area per year, 2016–2025, indexed to the mean of "
                   "2016–2019: damage-only accidents in Prague fell to about half, while in the towns with a new bypass "
                   "and in the other comparison towns they stayed near or above the base; injury accidents moved "
                   "little in all three groups.",
            "panels": panels,
            "legend": [{"label": name, "c": c} for name, c, _ in GROUPS.values()],
            "table": {"cols": ["year", *[f"{GROUPS[g][0]}, {k.replace('_', '-')}" for k in ("damage_only", "injury")
                                         for g in GROUPS]],
                      "rows": [[y, *[s[f"{g}_{k}"][str(y)] for k in ("damage_only", "injury") for g in GROUPS]]
                               for y in yrs]},
            "data": ["describe.json"]}


def static_damage(desc: dict, path: Path) -> None:
    s = desc["inside_built_up"]
    f, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    for ax, (kind, title) in zip(axes, (("damage_only", "damage-only"), ("injury", "injury"))):
        ax.axhline(100, color=LIGHT, lw=0.8)
        for g, (name, c, _) in GROUPS.items():
            pts = index(s[f"{g}_{kind}"])
            ax.plot([x for x, _ in pts], [y for _, y in pts], color=c, lw=1.8, marker="o", ms=3, label=name)
        ax.set_title(title, fontsize=9, color=INK)
        ax.set_xticks(range(2016, 2026, 2), [f"’{str(y)[2:]}" for y in range(2016, 2026, 2)])
        ax.set_ylim(40, 140)
    axes[0].set_ylabel("index, 2016–2019 = 100")
    axes[0].legend(frameon=False, fontsize=7, loc="lower left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- where the crashes went

def where_rows(res: dict) -> list[tuple[str, float, list[float], str]]:
    q1, q2, c10 = res["questions"]["q1"], res["questions"]["q2"], res["checks"]["10_old_through_road_q1"]
    return [("inside town · Q1", q1["delta_per_town_year"], q1["delta_ci95"], "held"),
            ("old road · check 10", c10["delta_per_town_year"], c10["delta_ci95"], "grey"),
            ("outside · Q2 split", q2["change_outside_built_up_per_town_year"],
             q2["change_outside_ci95"], "held"),
            ("municipality · Q2", q2["delta_per_town_year"], q2["delta_ci95"], "held")]


def where_chart(res: dict) -> dict:
    rows = where_rows(res)
    q3 = res["questions"]["q3"]
    geo = [b for b in q3["bypasses"] if b.get("bypass_accidents") is not None]
    pooled = q3["pooled"]["per_km_year"]
    r = [{"y": lab, "lo": round(ci[0], 2), "hi": round(ci[1], 2), "mid": round(e, 2), "c": c,
          "tip": f"{lab}: {acc(e)} injury accidents per town and year, 95 % {acc(ci[0])} to {acc(ci[1])}"}
         for lab, e, ci, c in rows]
    q3lab = "bypass · Q3"
    dots = [{"x": round(b["per_km_year"], 2), "y": q3lab, "c": "light", "r": 3.5,
             "tip": f'{b["id"]} · {b["road"]}: {n(b["per_km_year"], 2)} per km and year, {b["bypass_accidents"]} accidents'}
            for b in geo]
    return {"alt": "Changes in police-recorded injury accidents per town and year in years 1–3 after a bypass opened, "
                   "relative to towns still waiting, with 95 % intervals: fewer inside the town, on all roads and on "
                   "the old through road, more outside the built-up area, and about no change for the whole "
                   "municipality; below, the injury accidents per kilometre and year on 17 bypass roads, descriptive.",
            "panels": [{"title": "change per town and year",
                        "h": 30 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": [-3.5, 2.5], "ticks": [-3, -2, -1, 0, 1, 2],
                              "fmt": {"dp": 0, "sign": True}, "label": "injury accidents, 95 % interval"},
                        "y": {"kind": "cat", "domain": [x[0] for x in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                                  {"type": "range", "rows": r, "w": 3}]},
                       {"title": "on the bypass, per km and year",
                        "h": 70,
                        "x": {"kind": "linear", "domain": [0, 1.5], "ticks": [0, 0.5, 1, 1.5],
                              "fmt": {"dp": 1}, "label": "injury accidents per km and year"},
                        "y": {"kind": "cat", "domain": [q3lab]},
                        "marks": [{"type": "dots", "pts": dots},
                                  {"type": "range", "rows": [{"y": q3lab, "lo": None, "hi": None, "mid": round(pooled, 2),
                                                              "c": "ink", "tip": f"all {len(geo)} bypasses: {n(pooled, 2)} per km and year"}]}]}],
            "legend": [{"label": "registered, 95 % interval", "c": HELD}, {"label": "check, 95 % interval", "c": "grey"},
                       {"label": "one bypass road (grey dots) and all of them (black)", "c": "light", "shape": "o"}],
            "table": {"cols": ["where", "injury accidents per town and year", "95 % interval"],
                      "rows": [[lab, round(e, 2), f"{acc(ci[0])} to {acc(ci[1])}"] for lab, e, ci, _ in rows]
                      + [[f"{q3lab} (per km and year, {len(geo)} bypasses)", round(pooled, 2), "descriptive, no interval"]]},
            "data": ["results.json"]}


def static_where(res: dict, path: Path) -> None:
    rows = where_rows(res)
    f, ax = plt.subplots(figsize=(7.2, 2.2))
    ax.axvline(0, color=GREY, lw=0.8)
    for i, (lab, e, ci, c) in enumerate(reversed(rows)):
        col = HELD if c == "held" else GREY
        ax.plot(ci, [i, i], color=col, lw=3, solid_capstyle="round")
        ax.plot(e, i, "o", color=col, ms=6, mec="white")
    ax.set_yticks(range(len(rows)), [x[0] for x in reversed(rows)], fontsize=8)
    ax.set_xlabel("change in injury accidents per town and year, 95 % interval")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- tables in the text

def tests_table(res: dict) -> str:
    out = []
    for q, name in (("q1", "Q1 · injury accidents inside the built-up area of the town"),
                    ("q2", "Q2 · injury accidents on the whole territory of the municipality")):
        r = res["questions"][q]
        out.append(f'  <tr><td>{name}</td><td class="v">{p(r["est"], 1)} <small>{nb("90 % " + iv(r["ci90"], 1))}<br>'
                   f'{nb("95 % " + iv(r["ci95"], 1))}</small></td>'
                   f'<td class="v">{acc(r["delta_per_town_year"])} <small>{nb("95 % " + acc(r["delta_ci95"][0]) + " to " + acc(r["delta_ci95"][1]))}</small></td>'
                   f'<td class="v">{n(100 * r["power"]["ci90_width"], 0)}{NB}pp <small>smallest detectable change '
                   f'{n(100 * r["power"]["smallest_detectable_change"], 0)}{NB}%</small></td>'
                   f'<td class="v"><b>{r["label"]}</b></td></tr>')
    return "\n".join(out)


def checks_table(res: dict) -> str:
    out = []
    for k, lab in CHECKS:
        c = res["checks"][k]
        towns = f"{c['treated_towns']} towns · " if "treated_towns" in c else ""
        out.append(f'  <tr><td>{lab}</td><td class="v">{p(c["est"], 1)}</td>'
                   f'<td class="v">{nb(iv(c["ci90"], 1))}<small>{nb("95 % " + iv(c["ci95"], 1))}</small></td>'
                   f'<td class="v">{towns}{n(used(c))} of {n(DRAWS)}</td></tr>')
    return "\n".join(out)


def q3_table(q3: dict) -> str:
    out = []
    for b in q3["bypasses"]:
        if b.get("bypass_accidents") is None:
            continue
        js = "–" if b["junction_share"] is None else f'{n(100 * b["junction_share"], 0)}{NB}%'
        out.append(f'  <tr><td>{b["id"]} · {b["road"]}</td><td class="v">{n(b["km"], 1)}</td>'
                   f'<td class="v">{b["years"]}</td><td class="v">{b["bypass_accidents"]}</td>'
                   f'<td class="v">{n(b["per_km_year"], 2)}</td><td class="v">{js}</td>'
                   f'<td class="v">{n(b["old_road_per_year"], 1)} <small>{b["old_road_years"]} years</small></td></tr>')
    return "\n".join(out)


WP_ROWS = (("q1", "Q1 · injury accidents inside the town"), ("q2", "Q2 · injury accidents, whole municipality"),
           ("1_all_accidents_q1", "check 1 · all accidents, inside the town"),
           ("1_all_accidents_q2", "check 1 · all accidents, whole municipality"))


def wp_table(wp: dict) -> str:
    out = []
    for k, lab in WP_ROWS:
        r, reg = wp["results"][k], wp["results"][k]["registered"]
        lbl = r["label_by_registered_rule"] if k in ("q1", "q2") else "–"
        out.append(f'  <tr><td>{lab}</td><td class="v">{p(reg["est"], 1)} <small>{nb("95 % " + iv(reg["ci95"], 1))}</small></td>'
                   f'<td class="v">{p(r["est"], 1)} <small>{nb("90 % " + iv(r["ci90"], 1))}<br>{nb("95 % " + iv(r["ci95"], 1))}</small></td>'
                   f'<td class="v">{lbl}</td></tr>')
    return "\n".join(out)


def number_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', render((HERE / "refs.html").read_text(encoding="utf-8"), values)))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) <= set(entries), set(order) - set(entries)
    assert set(entries) <= set(order), f"uncited: {set(entries) - set(order)}"
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]", lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


# ---------------------------------------------------------------- the page

def main() -> None:
    j = results_reader("bypass")
    res, scr, desc, wp = j("results-a"), j("screening"), j("describe"), j("without-prague")
    tj = j("towns")
    ex = next(t for t in tj["towns"] if t["town"] == tj["example"])
    exq3 = next(b for b in res["questions"]["q3"]["bypasses"] if b["id"] == ex["row"])
    em = ex["yearly_injury_municipality"]
    assert tj["example_tied"] == 1 and not any(ex["yearly_injury_inside"].values())  # the text says so
    assert sum(1 for t in tj["towns"] if t["class"] == "I" and t["open_year"] == ex["open_year"]) == 1
    A.mkdir(parents=True, exist_ok=True)
    for src, dst in (("results-a", "results"), ("describe", "describe"), ("without-prague", "without-prague")):
        shutil.copy(R / f"bypass-{src}.json", A / f"{dst}.json")
    charts = {"estimates": estimates_chart(res), "damage": damage_chart(desc), "where": where_chart(res)}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    static_estimates(res, A / "01-estimates.svg")
    static_damage(desc, A / "02-damage-only.svg")
    static_where(res, A / "00-where.svg")

    q1, q2, q3 = res["questions"]["q1"], res["questions"]["q2"], res["questions"]["q3"]
    ch, pt, pl = res["checks"], res["pre_trends"], res["placebo"]
    tw = scr["towns"]
    pooled = q3["pooled"]
    cg = desc["change_2016_19_to_2023_25"]
    nat, bands = desc["national"], desc["damage_bands_czk_nominal"]
    ph = desc["treated_by_phase_per_town_year"]
    share = desc["prague_share_of_comparison_inside_2016_to_last_year"]
    small = lambda b: sum(v for k, v in b.items() if k != "over 100 000")  # noqa: E731
    # the text states these orderings; fail loudly if a re-run changed them
    assert q1["label"] == q2["label"] == "underpowered" and not res["offset_share"]["reported"]
    assert q1["ci95"][0] < 0 < q1["ci95"][1] and q1["ci90"][1] < 0
    assert ch["1_all_accidents_q1"]["est"] > 0 and ch["1_all_accidents_q2"]["est"] > 0
    assert ch["2_killed_seriously_injured_q1"]["ci95"][1] < 0 and ch["10_old_through_road_q1"]["ci95"][1] < 0
    assert ch["13_class_I"]["ci95"][1] < 0 and ch["13_class_II"]["ci95"][0] < 0 < ch["13_class_II"]["ci95"][1]
    assert q1["sign_sentence"] is None and pt["uninformative_by_rule"] and not pt["rejects_5pct"]
    assert all(ch[k]["ci95"][0] < 0 for k, _ in CHECKS if not k.startswith("1_"))
    geo = [b for b in q3["bypasses"] if b.get("bypass_accidents") is not None]
    mid = ("3_without_2020_2021_q1", "4_plain_event_study_q1", "6_post_1_2_q1", "7_comparison_planned_only",
           "12_class_III_added")
    assert all(ch["6_post_1_5_q1"]["est"] > ch[k]["est"] > ch["8_opening_year_dose_q1"]["est"] for k in mid)
    assert ch["9_town_trends_q1"]["shift_against_primary"] < 0
    assert len(q3["bypasses"]) == tw["treated_bypasses"]

    v = {
        "draws": n(DRAWS), "seed": SEED, "min_lead": MIN_LEAD_TOWNS,
        "cohorts": ", ".join(f"{a}–{str(b)[2:]}" for a, b in COHORTS),
        "treated": tw["treated_towns"], "bypasses": tw["treated_bypasses"], "comparison": tw["comparison_towns"],
        "comparison_byp": tw["comparison_bypasses"],
        "class_i": tw["treated_by_class"]["I"], "class_ii": tw["treated_by_class"]["II"],
        "open_years": ", ".join(f"{int(float(y))} ({c})" for y, c in sorted(tw["treated_by_open_year"].items())),
        "post1": q1["treated_towns_per_post_year"]["1"], "post2": q1["treated_towns_per_post_year"]["2"],
        "post3": q1["treated_towns_per_post_year"]["3"],
        "redrawn_sep": res["redrawn"]["separated"],
        # Q1, Q2
        "q1_est": p(q1["est"], 1), "q1_ci90": iv(q1["ci90"], 1), "q1_ci95": iv(q1["ci95"], 1),
        "q1_est0": p(q1["est"]), "q1_lo0": p(q1["ci95"][0]), "q1_hi0": p(q1["ci95"][1]),
        "q1_d": acc(q1["delta_per_town_year"]), "q1_d_ci": f'{acc(q1["delta_ci95"][0])} to {acc(q1["delta_ci95"][1])}',
        "q1_w": n(100 * q1["power"]["ci90_width"], 0), "q1_sdc": n(100 * q1["power"]["smallest_detectable_change"], 0),
        "q2_est": p(q2["est"], 1), "q2_ci90": iv(q2["ci90"], 1), "q2_ci95": iv(q2["ci95"], 1), "q2_est0": p(q2["est"]),
        "q2_d": acc(q2["delta_per_town_year"]), "q2_d_ci": f'{acc(q2["delta_ci95"][0])} to {acc(q2["delta_ci95"][1])}',
        "q2_w": n(100 * q2["power"]["ci90_width"], 0), "q2_sdc": n(100 * q2["power"]["smallest_detectable_change"], 0),
        "q2_in": acc(q2["change_inside_built_up_per_town_year"]),
        "q2_out": acc(q2["change_outside_built_up_per_town_year"]),
        "q2_out_ci": f'{acc(q2["change_outside_ci95"][0])} to {acc(q2["change_outside_ci95"][1])}',
        "label": q1["label"],
        # pre-trends and placebo
        "lead3": pt["towns_per_lead"]["lead|-3"], "lead2": pt["towns_per_lead"]["lead|-2"],
        "lead_any": pt["towns_any_lead"], "wald_p": n(pt["p"], 2),
        "lead3_b": p(math.exp(pt["coefficients"]["lead|-3"]) - 1, 0),
        "lead2_b": p(math.exp(pt["coefficients"]["lead|-2"]) - 1, 0),
        "pl_est": p(pl["est"], 1), "pl_ci": iv(pl["ci95"], 1), "pl_towns": pl["treated_towns_with_earlier_years"],
        # checks
        **{f"c_{k}": p(ch[k]["est"]) for k, _ in CHECKS},
        **{f"c_{k}_ci": iv(ch[k]["ci95"]) for k, _ in CHECKS},
        **{f"c_{k}_used": n(used(ch[k])) for k, _ in CHECKS},
        **{f"c_{k}_d": acc(ch[k]["delta_per_town_year"], 1) for k, _ in CHECKS if "delta_per_town_year" in ch[k]},
        "c9_shift": n(100 * ch["9_town_trends_q1"]["shift_against_primary"], 0, sign=True),
        "c11s_sep": n(ch["11_smaller_towns"]["redrawn"]["separated"]),
        "c11_small_n": ch["11_smaller_towns"]["treated_towns"], "c11_large_n": ch["11_larger_towns"]["treated_towns"],
        "c13i_n": ch["13_class_I"]["treated_towns"], "c13ii_n": ch["13_class_II"]["treated_towns"],
        "c12_n": ch["12_class_III_added"]["treated_towns"],
        # Q3
        "q3_geo": len(geo), "q3_nogeo": q3["geometry_methods"]["no_geometry"],
        "q3_acc": pooled["bypass_accidents"], "q3_kmy": n(pooled["km_years"], 0), "q3_rate": n(pooled["per_km_year"], 2),
        "q3_junc": n(100 * pooled["junction_share"], 0), "q3_junc_n": pooled["at_junction"],
        "q3_old": n(pooled["old_road_per_town_year"], 1), "q3_old_acc": pooled["old_accidents"],
        "q3_old_ty": pooled["old_town_years"],
        "q3_min": n(min(b["per_km_year"] for b in geo), 2), "q3_max": n(max(b["per_km_year"] for b in geo), 2),
        "q3_buffer": q3["buffer_m"],
        # the note on check 1, after the results
        "prague_row": desc["prague_row"], "prague_last": desc["prague_last_comparison_year"],
        "pr_share_dmg": n(100 * share["damage_only"], 0), "pr_share_inj": n(100 * share["injury"], 0),
        "pr_dmg_ch": p(cg["inside_prague_damage_only"]), "pr_inj_ch": p(cg["inside_prague_injury"]),
        "tr_dmg_ch": p(cg["inside_treated_damage_only"]), "tr_inj_ch": p(cg["inside_treated_injury"]),
        "oc_dmg_ch": p(cg["inside_other_comparison_damage_only"]), "oc_inj_ch": p(cg["inside_other_comparison_injury"]),
        "rest_dmg_ch": p(cg["national_damage_only_rest"]), "nat_dmg_ch": p(cg["national_damage_only"]),
        "pr_small_16": n(small(bands["prague"]["2016"])), "pr_small_25": n(small(bands["prague"]["2025"])),
        "pr_big_16": n(bands["prague"]["2016"]["over 100 000"]), "pr_big_25": n(bands["prague"]["2025"]["over 100 000"]),
        "pr_small_ch": p(small(bands["prague"]["2025"]) / small(bands["prague"]["2016"]) - 1),
        "rest_small_ch": p(small(bands["rest"]["2025"]) / small(bands["rest"]["2016"]) - 1),
        "rest_big_ch": p(bands["rest"]["2025"]["over 100 000"] / bands["rest"]["2016"]["over 100 000"] - 1),
        "pr_small_22": n(small(bands["prague"]["2022"])),
        "wild_22": n(nat["damage_only_wildlife"]["2022"]), "wild_25": n(nat["damage_only_wildlife"]["2025"]),
        "wild_19": n(nat["damage_only_wildlife"]["2019"]),
        "ph_pre_dmg": n(ph["pre-construction"]["damage_only"], 1), "ph_post_dmg": n(ph["post years 1–3"]["damage_only"], 1),
        "ph_pre_old": n(ph["pre-construction"]["damage_only_old_road"], 1),
        "ph_post_old": n(ph["post years 1–3"]["damage_only_old_road"], 1),
        "ph_pre_inj": n(ph["pre-construction"]["injury"], 1), "ph_post_inj": n(ph["post years 1–3"]["injury"], 1),
        **{f"v_{k}": x for k, x in res["versions"].items()},
        "map_i": sum(t["class"] == "I" for t in tj["towns"]), "map_ii": sum(t["class"] == "II" for t in tj["towns"]),
        "map_median_pre": n(sorted(t["pre_mean"] for t in tj["towns"])[len(tj["towns"]) // 2], 1),
        "ex_post_n": ex["post_years"],
        "ex_name": ex["name"], "ex_road": ex["road"], "ex_row": ex["row"], "ex_start": ex["start_year"],
        "ex_opened": f'{int(ex["opened"][8:])} {["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][int(ex["opened"][5:7]) - 1]} {ex["opened"][:4]}',
        "ex_muni_pre": ", ".join(str(em[str(y)]) for y in range(2016, ex["open_year"])) + f" in 2016–{ex['open_year'] - 1}",
        "ex_muni_post": ", ".join(str(em[str(y)]) for y in range(ex["open_year"] + 1, 2026)),
        "ex_q3": f'{exq3["bypass_accidents"]}',
        "wp_table": wp_table(wp), "wp_comp": wp["comparison_towns"], "wp_units": wp["comparison_units"],
        "wp_left": " and ".join(wp["dropped"]["left_in_unit"]), "wp_unit": wp["dropped"]["unit"],
        **{f"wp_{k}": p(wp["results"][k]["est"], 1) for k, _ in WP_ROWS},
        **{f"wp_{k}_ci90": iv(wp["results"][k]["ci90"], 1) for k, _ in WP_ROWS},
        **{f"wp_{k}_ci95": iv(wp["results"][k]["ci95"], 1) for k, _ in WP_ROWS},
        "wp_q1_label": wp["results"]["q1"]["label_by_registered_rule"],
        "wp_q2_label": wp["results"]["q2"]["label_by_registered_rule"],
        "wp_q1_w": n(100 * wp["results"]["q1"]["power"]["ci90_width"], 0),
        "wp_q1_d": acc(wp["results"]["q1"]["delta_per_town_year"]),
        "wp_q2_out": acc(wp["results"]["q2"]["change_outside_built_up_per_town_year"]),
        "wp_q2_out_ci": f'{acc(wp["results"]["q2"]["change_outside_ci95"][0])} to {acc(wp["results"]["q2"]["change_outside_ci95"][1])}',
        "wp_redrawn": n(sum(wp["redrawn"].values())),
        "tests_table": tests_table(res), "checks_table": checks_table(res), "q3_table": q3_table(q3),
    }
    page = number_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}), v)
    (ROOT / "texts" / f"{SLUG}.html").write_text(page, encoding="utf-8")
    print(json.dumps({k: x for k, x in v.items() if not k.endswith("table")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
