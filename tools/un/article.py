"""The UN votes study, stage A: figures and the article, every number from the result files.

Reads docs/research/un-votes-{results-a,screen,power,departures,describe,positions}.json and the registered constants of the
frozen code (votes.py, estimate.py; nothing there is run), writes assets/un-votes/ (charts.json, 01-beta.svg,
02-yearly.svg, 03-departures.svg, results.json, departures.json, describe.json, positions.json) and texts/un-votes.html from
tools/un/template.html. Run tools/un/departures.py, describe.py and positions.py first.

    uv run --no-project --with numpy --with pandas --with duckdb --with matplotlib python tools/un/article.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import statistics
from collections import Counter
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, INK, LIGHT, n, render, results_reader, use_article_style  # noqa: E402
from estimate import CABINET, CHANGES, CONFIDENCE, US_CHANGE  # noqa: E402
from votes import BUFFER_DAYS, DRAWS, EU27, MIN_AFTER, SEED, label  # noqa: E402

plt = use_article_style()
R, A = ROOT / "docs" / "research", ROOT / "assets" / "un-votes"
CORAL, TEAL = "#c0503f", "#2a7f86"
MARGIN, MINIMUM = label.__defaults__  # §6: the equivalence margin and the smallest β called a shift
P_CUT = 0.10  # §6: the placebo rank a shift needs
PARTNERS = {"EU": "EU majority", "USA": "United States", "RUS": "Russia", "HUN": "Hungary", "SVK": "Slovakia"}
CHANGE = {"q2a": "2017", "q2b": "2021"}
TOPIC_C = {"israel_palestine": HELD, "nuclear": CORAL, "racism": TEAL, "other": LIGHT}
CHECKS = {"split_votes_only": "split votes only (§7.1)", "no_partial_credit": "no half point for an abstention (§7.2)",
          "no_buffer": "after period from the cabinet date, no buffer (§7.3)",
          "without_hungary_slovakia": "comparison without Hungary and Slovakia (§7.4)",
          "regular_sessions_only": "regular sessions only (§7.5)",
          "confidence_dates": "after period from the confidence vote (§7.6)",
          "usa_before_us_change": "with the United States, Fiala period before 20 January 2025 (§7.7)"}


def day(s: str) -> str:
    d = dt.date.fromisoformat(s)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def pts(v: float, sign: bool = True) -> str:
    return n(100 * v, 1, sign=sign)


def pct(v: float, dp: int = 1) -> str:
    return n(100 * v, dp)


def iv(lo_hi: list[float]) -> str:
    return f"{pts(lo_hi[0])} to {pts(lo_hi[1])}"


def lowest(k: int) -> str:
    return {1: "the lowest", 2: "the second lowest", 3: "the third lowest"}.get(k, f"number {k} from the bottom")


def nb(s: str) -> str:
    return s.replace(" ", "&nbsp;")


def short(title: str) -> str:
    return title.split(" : ")[0].strip()


# ---------------------------------------------------------------- fig. 1, β per change and partner

def beta_rows(res: dict) -> list[tuple[str, str, str, dict]]:
    return [(q, p, f"{PARTNERS[p]} · {CHANGE[q]}", res["questions"][q]["by_partner"][p]) for p in PARTNERS for q in CHANGE]


def beta_chart(res: dict) -> tuple[dict, float]:
    rows = beta_rows(res)
    allv = [100 * x for _, _, _, b in rows for x in (*b["ci95"], *[v["est"] for v in b["placebo"].values()])]
    lim = float(2 * int(max(abs(min(allv)), abs(max(allv))) / 2 + 1))
    placebo, r95, r90 = [], [], []
    for q, p, lab, b in rows:
        for c, v in b["placebo"].items():
            placebo.append({"x": round(100 * v["est"], 2), "y": lab, "c": "light", "r": 3.5,
                            "tip": f"{lab}: {c} as focal member, {pts(v['est'])} points"})
        tip = (f"{lab}: Czechia {pts(b['est'])} points, 90 % {iv(b['ci90'])}, 95 % {iv(b['ci95'])}, "
               f"rank p {n(b['p'], 2)} of {b['members_ranked']}, {b['label']}")
        r95.append({"y": lab, "lo": round(100 * b["ci95"][0], 2), "hi": round(100 * b["ci95"][1], 2),
                    "mid": round(100 * b["est"], 2), "tip": tip})
        r90.append({"y": lab, "lo": round(100 * b["ci90"][0], 2), "hi": round(100 * b["ci90"][1], 2),
                    "mid": round(100 * b["est"], 2), "tip": tip})
    for _, _, lab, b in rows:  # the alt text and the figure head say so
        xs = [v["est"] for v in b["placebo"].values()]
        assert b["ci95"][0] < 0 < b["ci95"][1], lab
    ticks = [t for t in range(-int(lim), int(lim) + 1, 2)]
    spec = {"alt": "For the changes of government in 2017 and 2021 and for agreement with the EU majority, the United "
                   "States, Russia, Hungary and Slovakia: Czechia's change in agreement relative to the other EU members, "
                   "in points, with 90 and 95 % intervals, and the same estimate for each other EU member as grey dots. "
                   "Every Czech interval includes zero; in 2021 the Czech estimates with the EU majority and with Russia lie at "
                   "the low end of the grey dots.",
            "panels": [{"h": 30 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": [-lim, lim], "ticks": ticks, "fmt": {"dp": 0, "sign": True},
                              "label": "change relative to the other EU members, points of agreement"},
                        "y": {"kind": "cat", "domain": [r[2] for r in rows]},
                        "marks": [{"type": "span", "v0": -100 * MARGIN, "v1": 100 * MARGIN, "c": "grey", "o": 0.07},
                                  {"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                                  {"type": "range", "rows": r95, "w": 1.5},
                                  {"type": "range", "rows": r90, "w": 4},
                                  {"type": "dots", "pts": placebo},
                                  {"type": "range", "rows": [{**r, "lo": None, "hi": None} for r in r90]}]}],
            "legend": [{"label": "Czechia, 90 % interval (thick) and 95 % (thin)", "c": HELD},
                       {"label": "each other EU member as focal", "c": "light", "shape": "o"},
                       {"label": f"±{n(100 * MARGIN)} points, the registered margin", "c": "grey", "shape": "box"}],
            "table": {"cols": ["change · partner", "β, points", "90 % interval", "95 % interval", "rank p", "members",
                               "label"],
                      "rows": [[lab, round(100 * b["est"], 2), iv(b["ci90"]), iv(b["ci95"]), b["p"], b["members_ranked"],
                                b["label"]] for _, _, lab, b in rows]},
            "data": ["results.json"]}
    return spec, lim


def static_beta(res: dict, path: Path, lim: float) -> None:
    rows = beta_rows(res)
    f, ax = plt.subplots(figsize=(7.2, 0.36 * len(rows) + 0.9))
    ax.axvspan(-100 * MARGIN, 100 * MARGIN, color=LIGHT, alpha=0.18, lw=0)
    ax.axvline(0, color=GREY, lw=0.8)
    for i, (_, _, lab, b) in enumerate(reversed(rows)):
        xs = [100 * v["est"] for v in b["placebo"].values()]
        ax.plot([100 * x for x in b["ci95"]], [i, i], color=HELD, lw=1.2)
        ax.plot([100 * x for x in b["ci90"]], [i, i], color=HELD, lw=3.5, solid_capstyle="round")
        ax.plot(xs, [i] * len(xs), "o", color=LIGHT, ms=3.5, mec="white", mew=0.5)
        ax.plot(100 * b["est"], i, "o", color=HELD, ms=6, mec="white")
    ax.set_yticks(range(len(rows)), [r[2] for r in reversed(rows)])
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("change relative to the other EU members, points of agreement")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 2, departures by topic

def departures_chart(dep: dict) -> dict:
    periods = dep["periods"]
    cats = [f"{p['label']} · {p['votes']} votes" for p in periods.values()]
    rows = []
    for cat, p in zip(cats, periods.values()):
        y = 0
        for k, lab in dep["topics"].items():
            c = p["by_topic"][k]
            if c:
                rows.append({"x": cat, "y0": y, "y1": y + c, "c": TOPIC_C[k],
                             "tip": f"{p['label']} period: {c} of {p['departures']} departures on {lab}, "
                                    f"{p['opposite_by_topic'][k]} of them yes against no"})
            y += c
    table = [[p["label"], v["date"], dep["topics"][v["topic"]], short(v["title"]),
              "opposite (yes against no)" if v["agreement"] == 0 else "one side abstained"]
             for p in periods.values() for v in p["list"]]
    top = max(p["departures"] for p in periods.values())
    s, b, f = (periods[k]["departures"] for k in ("sobotka", "babis", "fiala"))
    return {"alt": f"Votes on which Czechia's position differed from the majority of the other EU members, per period, "
                   f"stacked by topic: {s} in the Sobotka period, most on nuclear weapons; {b} in the Babiš period, "
                   f"spread over the topics; {f} in the Fiala period, most of them on Israel and Palestine.",
            "panels": [{"h": 240, "x": {"kind": "cat", "domain": cats},
                        "y": {"kind": "linear", "domain": [0, 5 * (top // 5 + 2)], "fmt": {"dp": 0},
                              "label": "votes on which Czechia left the EU majority"},
                        "marks": [{"type": "vbar", "rows": rows}]}],
            "legend": [{"label": lab, "c": TOPIC_C[k], "shape": "box", "o": 0.85} for k, lab in dep["topics"].items()],
            "table": {"cols": ["period", "date", "topic", "resolution", "Czechia and the EU majority"], "rows": table},
            "data": ["departures.json"]}


def static_departures(dep: dict, path: Path) -> None:
    periods = list(dep["periods"].values())
    f, ax = plt.subplots(figsize=(7.2, 2.8))
    bottom = [0] * len(periods)
    for k, lab in dep["topics"].items():
        vals = [p["by_topic"][k] for p in periods]
        ax.bar(range(len(periods)), vals, bottom=bottom, color=TOPIC_C[k], width=0.55, label=lab)
        bottom = [a + b for a, b in zip(bottom, vals)]
    ax.set_xticks(range(len(periods)), [f"{p['label']} · {p['votes']} votes" for p in periods])
    ax.set_ylabel("votes leaving the EU majority")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 3, yearly levels

def yearly_chart(desc: dict) -> dict:
    ys = desc["years"]
    yrs = sorted(int(y) for y in ys)
    p = lambda k: [[y, round(100 * ys[str(y)][k], 2)] for y in yrs]  # noqa: E731
    band = [[y, round(100 * ys[str(y)]["others_min"], 2), round(100 * ys[str(y)]["others_max"], 2)] for y in yrs]
    lo = 5 * int(min(100 * ys[str(y)]["others_min"] for y in yrs) / 5)
    cab = [(CABINET["babis_2017"], "Babiš"), (CABINET["fiala_2021"], "Fiala")]
    rules = [{"type": "rule", "axis": "x", "v": round(int(d[:4]) + (dt.date.fromisoformat(d).timetuple().tm_yday - 1) / 365
                                                    - 0.5, 2),
              "c": "grey", "dash": "dot", "label": lab} for d, lab in cab]
    cz = [100 * ys[str(y)]["czechia"] for y in yrs]
    inside = all(ys[str(y)]["others_min"] <= ys[str(y)]["czechia"] <= ys[str(y)]["others_max"] for y in yrs)
    return {"alt": f"Agreement with the majority of the other EU members per calendar year, {yrs[0]}–{yrs[-1]}: Czechia "
                   f"between {n(min(cz), 0)} and {n(max(cz), 0)} %"
                   + (", inside the range of the other 26 members every year" if inside else "")
                   + "; dashed, the other members' median.",
            "panels": [{"h": 260, "padRight": 70,
                        "x": {"kind": "linear", "domain": [yrs[0] - 0.3, yrs[-1] + 0.3], "ticks": yrs,
                              "tickLabels": {str(y): f"’{str(y)[2:]}" for y in yrs},
                              "fmt": {"dp": 0, "nogroup": True}, "label": "calendar year (2025 to 14 December)"},
                        "y": {"kind": "linear", "domain": [lo, 100], "ticks": list(range(lo, 101, 5)),
                              "fmt": {"dp": 1, "unit": " %"}, "label": "agreement with the EU majority"},
                        "marks": [*rules,
                                  {"type": "area", "pts": band, "c": "grey", "name": "other members, lowest–highest",
                                   "fmt": {"dp": 1, "unit": " %"}},
                                  {"type": "line", "pts": p("others_median"), "c": "grey", "w": 1.5, "dash": "dash",
                                   "name": "other members, median", "end": "median", "fmt": {"dp": 1, "unit": " %"}},
                                  {"type": "line", "pts": p("czechia"), "c": HELD, "name": "Czechia", "end": "Czechia",
                                   "dots": True, "fmt": {"dp": 1, "unit": " %"}}]}],
            "legend": [{"label": "Czechia", "c": HELD}, {"label": "other 26 members, median", "c": "grey", "dash": "dash"},
                       {"label": "other 26 members, lowest to highest", "c": "grey", "shape": "box"}],
            "table": {"cols": ["year", "votes", "Czechia, %", "others lowest, %", "others median, %", "others highest, %",
                               "Czechia's place of 27"],
                      "rows": [[y, ys[str(y)]["votes"], round(100 * ys[str(y)]["czechia"], 1),
                                round(100 * ys[str(y)]["others_min"], 1), round(100 * ys[str(y)]["others_median"], 1),
                                round(100 * ys[str(y)]["others_max"], 1), ys[str(y)]["czechia_rank_from_top"]]
                               for y in yrs]},
            "data": ["describe.json"]}


def static_yearly(desc: dict, path: Path) -> None:
    ys = desc["years"]
    yrs = sorted(int(y) for y in ys)
    g = lambda k: [100 * ys[str(y)][k] for y in yrs]  # noqa: E731
    f, ax = plt.subplots(figsize=(7.2, 2.9))
    ax.fill_between(yrs, g("others_min"), g("others_max"), color=LIGHT, alpha=0.4, lw=0, label="other 26, lowest–highest")
    ax.plot(yrs, g("others_median"), color=GREY, lw=1.2, ls="--", label="other 26, median")
    ax.plot(yrs, g("czechia"), color=HELD, lw=2, marker="o", ms=4, label="Czechia")
    for d in (CABINET["babis_2017"], CABINET["fiala_2021"]):
        ax.axvline(int(d[:4]) + 0.45, color=GREY, lw=0.8, ls=":")
    ax.set_xticks(yrs, [f"’{str(y)[2:]}" for y in yrs])
    ax.set_ylabel("% agreement with the EU majority")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- tables in the text

def tests_table(res: dict) -> str:
    out = []
    for q in CHANGE:
        ch = res["questions"][q]
        span = f"{day(ch['before'][0])} – {day(ch['before'][1])} → {day(ch['after'][0])} – {day(ch['after'][1])}"
        for i, p in enumerate(PARTNERS):
            b = ch["by_partner"][p]
            head = (f'<td rowspan="{len(PARTNERS)}">{"Q2a" if q == "q2a" else "Q2b"} · {CHANGE[q]}<br><small>{span}</small></td>'
                    if i == 0 else "")
            out.append(f"  <tr>{head}<td>{PARTNERS[p]}{' (Q3)' if p != 'EU' else ''}</td>"
                       f'<td class="v">{pts(b["est"])} <small>{nb("90 % " + iv(b["ci90"]))}<br>'
                       f'{nb("95 % " + iv(b["ci95"]))}</small></td>'
                       f'<td class="v">{n(b["p"], 2)} <small>of {b["members_ranked"]}</small></td>'
                       f'<td class="v"><b>{b["label"]}</b></td></tr>')
    q1 = CHANGES["q1"]
    out.append(f'  <tr><td>Q1 · 2025<br><small>{day(q1["before"][0])} – {day(q1["before"][1])} → '
               f'{day(q1["after"][0])} – {day(q1["after"][1])}</small></td><td>EU majority; partners (Q3)</td>'
               f'<td class="v" colspan="3"><b>pending</b> <small>votes not yet cast or not yet released</small></td></tr>')
    return "\n".join(out)


def check_label(res: dict, q: str, key: str) -> tuple[str, str]:
    """The §6 rule applied to a check's interval, with the primary estimate's rank p (checks have no placebo rank);
    reported beside the primary label, never replacing it (§7)."""
    partner = "USA" if key == "usa_before_us_change" else "EU"
    prim = res["questions"][q]["by_partner"][partner]
    return label(res["questions"][q]["checks"][key], prim["p"]), prim["label"]


def checks_table(res: dict) -> str:
    out = []
    prim = {q: res["questions"][q]["by_partner"]["EU"] for q in CHANGE}

    def cell(q, k=None):
        b = prim[q] if k is None else res["questions"][q]["checks"].get(k)
        if not b:
            return '<td class="v">–</td>'
        lab = b["label"] if k is None else check_label(res, q, k)[0]
        return (f'<td class="v">{pts(b["est"])} <small>{nb(iv(b["ci90"]))}<br>'
                f'{nb(str(b["n_before"]) + " / " + str(b["n_after"]) + " votes")}<br>{nb(lab)}</small></td>')
    out.append(f"  <tr><td>registered estimate, EU majority</td>{cell('q2a')}{cell('q2b')}</tr>")
    for k, lab in CHECKS.items():
        out.append(f"  <tr><td>{lab}</td>{cell('q2a', k)}{cell('q2b', k)}</tr>")
    return "\n".join(out)


def relabelled(res: dict) -> list[str]:
    out = []
    assert not any(check_label(res, q, k)[0].startswith(("lower", "higher")) for q in CHANGE for k in CHECKS
                   if k in res["questions"][q]["checks"])  # the text says no check would meet the rule for a shift
    for q in CHANGE:
        for k, lab in CHECKS.items():
            if k in res["questions"][q]["checks"]:
                new, old = check_label(res, q, k)
                if new != old:
                    out.append(f"the {CHANGE[q]} change on {lab.split(' (§')[0]} would be {new} (registered: {old})")
    return out


def positions_table(pos: dict) -> str:
    out = []
    for key, name in (("sobotka", "Sobotka"), ("babis", "Babiš"), ("fiala", "Fiala")):
        p = pos["periods"][key]
        c, o, mj = p["ip_czechia"], p["ip_others_shares"], p["ip_majority"]
        out.append(f'  <tr><td>{name}</td><td class="v">{p["ip_votes"]} <small>of {p["votes"]}</small></td>'
                   f'<td class="v">{c["Y"]} / {c["A"]} / {c["N"]}<small>{pct(c["Y"] / p["ip_votes"], 0)} % yes</small></td>'
                   f'<td class="v">{pct(o["Y"], 0)} / {pct(o["A"], 0)} / {pct(o["N"], 0)} %</td>'
                   f'<td class="v">{mj["Y"]} / {mj["A"]} / {mj["N"]}</td></tr>')
    return "\n".join(out)


def number_refs(page: str) -> str:
    """[[key]] markers become citations numbered by first appearance; the list is built from refs.html in that order,
    so every reference is cited and numbered r1..rN."""
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', (HERE / "refs.html").read_text(encoding="utf-8")))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) <= set(entries), set(order) - set(entries)
    assert set(entries) <= set(order), f"uncited: {set(entries) - set(order)}"
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]", lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    items = "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order)
    return page.replace("{{refs}}", items)


def word(k: int) -> str:
    return "none" if k == 0 else str(k)


def opposite_table(dep: dict) -> str:
    rows = [v for v in dep["periods"]["fiala"]["list"] if v["agreement"] == 0]
    return "\n".join(f'  <tr><td class="v">{day(v["date"])}</td><td>{html.escape(short(v["title"]))}</td></tr>'
                     for v in rows)


# ---------------------------------------------------------------- the page

def main() -> None:
    j = results_reader("un-votes")
    res, scr, pw, dep, desc = j("results-a"), j("screen"), j("power"), j("departures"), j("describe")
    posj = j("positions")
    A.mkdir(parents=True, exist_ok=True)
    for src, dst in (("results-a", "results"), ("departures", "departures"), ("describe", "describe"),
                     ("positions", "positions")):
        shutil.copy(R / f"un-votes-{src}.json", A / f"{dst}.json")

    charts = {}
    charts["beta"], lim = beta_chart(res)
    charts["departures"] = departures_chart(dep)
    charts["yearly"] = yearly_chart(desc)
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    static_beta(res, A / "01-beta.svg", lim)
    static_departures(dep, A / "03-departures.svg")
    static_yearly(desc, A / "02-yearly.svg")

    qa, qb = res["questions"]["q2a"], res["questions"]["q2b"]
    a, b = qa["by_partner"], qb["by_partner"]
    per, dp = scr["periods"], dep["periods"]
    pos = desc["departure_positions"]
    # each opposite vote of the Fiala period is Czechia no against an EU-majority yes, by the positions in describe.json
    opp = [v for v in dp["fiala"]["list"] if v["agreement"] == 0]
    assert len(opp) == pos["fiala"]["pairs"].get("czechia N, majority Y", 0) and \
        not pos["fiala"]["pairs"].get("czechia Y, majority N")
    assert len(opp) == dp["fiala"]["opposite_by_topic"]["israel_palestine"]
    bopp = [v for v in dp["babis"]["list"] if v["agreement"] == 0]
    assert len(bopp) == pos["babis"]["pairs"].get("czechia N, majority Y", 0) and \
        not pos["babis"]["pairs"].get("czechia Y, majority N")
    ys = desc["years"]
    yrs = sorted(ys)
    below = [y for y in yrs if ys[y]["czechia"] < ys[y]["others_median"]]
    first_below = next(y for y in yrs if all(ys[z]["czechia"] < ys[z]["others_median"] for z in yrs if z >= y))
    cz_levels = [ys[y]["czechia"] for y in yrs]
    stand = {q: max(res["questions"][q]["by_partner"]["EU"]["placebo"].items(), key=lambda kv: abs(kv[1]["est"] / kv[1]["se"]))
             for q in CHANGE}
    names = {"HUN": "Hungary", "FRA": "France", "ESP": "Spain", "AUT": "Austria", "CYP": "Cyprus", "SVK": "Slovakia",
             "POL": "Poland", "IRL": "Ireland", "MLT": "Malta", "SWE": "Sweden", "DEU": "Germany", "ITA": "Italy"}
    u = res["ungadm"]
    q2pw = pw["pseudo"]["q2_like"]
    q1pw = [pw["pseudo"]["q1_like_2022"], pw["pseudo"]["q1_like_2023"]]
    absn = res["absences"]
    labels = [res["questions"][q]["by_partner"][p]["label"] for q in CHANGE for p in PARTNERS]
    pp = posj["periods"]
    assert pp["fiala"]["departures_by_session"] == {"10emsp": pp["fiala"]["departures_emergency"]}  # the text says so
    assert absn["q2b"] == 0 and absn["q1"] == 0  # the text says Czechia voted on every vote of these periods

    def nearest(x: dict) -> float:
        return min(abs(v["est"] - x["est"]) for v in x["placebo"].values())
    # a rough projection for Q1, not registered: the median member's 90 % width in the Q1-like pseudo changes, scaled
    # by how much wider Czechia's standard error was than the median member's in the two stage A changes
    cz_se = [res["questions"][q]["by_partner"]["EU"]["se"] for q in CHANGE]
    med_se = [statistics.median(v["se"] for v in res["questions"][q]["by_partner"]["EU"]["placebo"].values())
              for q in CHANGE]
    ratios = [c / m_ for c, m_ in zip(cz_se, med_se)]
    q1w = statistics.mean(x["width90_median"] for x in q1pw)
    yrs_ = sorted(desc["years"])
    gaps = [desc["years"][y]["others_median"] - desc["years"][y]["czechia"] for y in yrs_
            if y >= next(z for z in yrs_ if all(desc["years"][w]["czechia"] < desc["years"][w]["others_median"]
                                                for w in yrs_ if w >= z))]

    v = {
        # registered constants of the frozen code
        "draws": n(DRAWS), "seed": SEED, "buffer": BUFFER_DAYS, "min_after": MIN_AFTER, "eu_n": len(EU27),
        "eu_others": len(EU27) - 1, "margin": n(100 * MARGIN), "minimum": n(100 * MINIMUM), "p_cut": n(P_CUT, 2),
        "margin2": n(200 * MARGIN),
        "cab_17": day(CABINET["babis_2017"]), "cab_21": day(CABINET["fiala_2021"]), "cab_25": day(CABINET["babis_2025"]),
        "conf_17": day(CONFIDENCE["babis_2017"]), "conf_21": day(CONFIDENCE["fiala_2021"]), "us_change": day(US_CHANGE),
        "sob_from": day(CHANGES["q2a"]["before"][0]), "sob_to": day(CHANGES["q2a"]["before"][1]),
        "bab_from": day(CHANGES["q2a"]["after"][0]), "bab_to": day(CHANGES["q2a"]["after"][1]),
        "fia_from": day(CHANGES["q2b"]["after"][0]), "fia_to": day(CHANGES["q2b"]["after"][1]),
        "q1_from": day(CHANGES["q1"]["after"][0]), "q1_to": day(CHANGES["q1"]["after"][1]),
        # screening and power
        "votes_all": n(scr["votes"]), "sob_votes": n(per["sobotka"]["votes"]), "bab_votes": n(per["babis"]["votes"]),
        "fia_votes": n(per["fiala"]["votes"]), "sob_split": n(per["sobotka"]["split_without_czechia"]),
        "bab_split": n(per["babis"]["split_without_czechia"]), "fia_split": n(per["fiala"]["split_without_czechia"]),
        "buf17_votes": n(per["buffer_2017"]["votes"]), "buf21_votes": n(per["buffer_2021"]["votes"]),
        "pw_q2_width": pts(q2pw["width90_median"], False), "pw_q2_beta": pts(q2pw["abs_beta_q90"], False),
        "pw_q1_votes_lo": n(min(x["votes_after"] for x in q1pw)), "pw_q1_votes_hi": n(max(x["votes_after"] for x in q1pw)),
        "pw_q1_width": pts(max(x["width90_median"] for x in q1pw), False),
        # Q2, EU majority
        "a_est": pts(a["EU"]["est"]), "a_ci90": iv(a["EU"]["ci90"]), "a_ci95": iv(a["EU"]["ci95"]),
        "a_p": n(a["EU"]["p"], 2), "a_m": a["EU"]["members_ranked"], "a_label": a["EU"]["label"],
        "a_width": pts(a["EU"]["ci90"][1] - a["EU"]["ci90"][0], False),
        "b_est": pts(b["EU"]["est"]), "b_ci90": iv(b["EU"]["ci90"]), "b_ci95": iv(b["EU"]["ci95"]),
        "b_p": n(b["EU"]["p"], 2), "b_m": b["EU"]["members_ranked"], "b_label": b["EU"]["label"],
        "b_width": pts(b["EU"]["ci90"][1] - b["EU"]["ci90"][0], False),
        "cz_sob": pct(a["EU"]["czechia_before"]), "cz_bab": pct(a["EU"]["czechia_after"]),
        "cz_fia": pct(b["EU"]["czechia_after"]), "co_sob": pct(a["EU"]["comparison_before"]),
        "co_bab": pct(a["EU"]["comparison_after"]), "co_fia": pct(b["EU"]["comparison_after"]),
        "cz_lo": pct(min(a["EU"]["czechia_before"], a["EU"]["czechia_after"], b["EU"]["czechia_after"]), 0),
        "cz_hi": pct(max(a["EU"]["czechia_before"], a["EU"]["czechia_after"], b["EU"]["czechia_after"]), 0),
        "a_n_before": n(a["EU"]["n_before"]), "a_n_after": n(a["EU"]["n_after"]), "b_n_after": n(b["EU"]["n_after"]),
        "a_clusters": n(a["EU"]["clusters_after"]), "b_clusters": n(b["EU"]["clusters_after"]),
        "stand_a": names.get(stand["q2a"][0], stand["q2a"][0]), "stand_a_est": pts(stand["q2a"][1]["est"]),
        "stand_b": names.get(stand["q2b"][0], stand["q2b"][0]), "stand_b_est": pts(stand["q2b"][1]["est"]),
        "n_labels": len(labels), "n_inconclusive": sum(x == "inconclusive" for x in labels),
        "n_underpowered": sum(x == "underpowered" for x in labels),
        "n_nochange": sum(x.startswith("no change") for x in labels),
        "p_min": n(min(res["questions"][q]["by_partner"][p]["p"] for q in CHANGE for p in PARTNERS), 2),
        "p_max": n(max(res["questions"][q]["by_partner"][p]["p"] for q in CHANGE for p in PARTNERS), 2),
        # Q3 levels
        **{f"{k}_{p.lower()}": val for p in ("USA", "RUS", "HUN", "SVK") for k, val in (
            ("cs", pct(a[p]["czechia_before"])), ("cb", pct(a[p]["czechia_after"])), ("cf", pct(b[p]["czechia_after"])),
            ("os", pct(a[p]["comparison_before"])), ("ob", pct(a[p]["comparison_after"])),
            ("of", pct(b[p]["comparison_after"])), ("ea", pts(a[p]["est"])), ("eb", pts(b[p]["est"])),
            ("la", a[p]["label"]), ("lb", b[p]["label"]), ("pa", n(a[p]["p"], 2)), ("pb", n(b[p]["p"], 2)))},
        # checks
        "split_a": pts(qa["checks"]["split_votes_only"]["est"]), "split_b": pts(qb["checks"]["split_votes_only"]["est"]),
        "split_a_ci": iv(qa["checks"]["split_votes_only"]["ci90"]), "split_b_ci": iv(qb["checks"]["split_votes_only"]["ci90"]),
        "split_a_n": n(qa["checks"]["split_votes_only"]["n_after"]), "split_b_n": n(qb["checks"]["split_votes_only"]["n_after"]),
        "reg_b": pts(qb["checks"]["regular_sessions_only"]["est"]),
        "usa_cut": pts(qb["checks"]["usa_before_us_change"]["est"]),
        "usa_cut_ci": iv(qb["checks"]["usa_before_us_change"]["ci90"]),
        "abs_sob": pct(absn["q2a"]), "abs_sob_n": n(absn["q2a"] * per["sobotka"]["votes"]),
        "abs_bab": pct(absn["q2b"]), "abs_fia": pct(absn["q1"]),
        "ties_sob": qa["departures_before"]["ties_dropped"], "ties_bab": qa["departures_after"]["ties_dropped"],
        "ties_fia": qb["departures_after"]["ties_dropped"],
        "ung_pairs": n(u["pairs"]), "ung_matched": n(u["matched_with_positions"]), "ung_same": pct(u["same_position"], 2),
        "ung_share": pct(u["matched_with_positions"] / u["pairs"], 0),
        # Q4
        **{f"d_{k}": n(p["departures"]) for k, p in dp.items()}, **{f"v_{k}": n(p["votes"]) for k, p in dp.items()},
        **{f"t_{k}_{t}": n(c) for k, p in dp.items() for t, c in p["by_topic"].items()},
        **{f"o_{k}": n(pos[k]["pairs"].get("czechia N, majority Y", 0)) for k in dp},
        **{f"ay_{k}": n(pos[k]["pairs"].get("czechia A, majority Y", 0)) for k in dp},
        **{f"na_{k}": n(pos[k]["pairs"].get("czechia N, majority A", 0)) for k in dp},
        "opp_table": opposite_table(dep),
        "bab_opp": " and ".join(f"{short(x['title'])} ({day(x['date'])})" for x in bopp),
        "headroom": pts(1 - b["EU"]["czechia_after"], False),
        "fia_ip_share": pct(dp["fiala"]["by_topic"]["israel_palestine"] / dp["fiala"]["departures"], 0),
        "rate_sob": pct(dp["sobotka"]["departures"] / dp["sobotka"]["votes"]),
        "rate_bab": pct(dp["babis"]["departures"] / dp["babis"]["votes"]),
        "rate_fia": pct(dp["fiala"]["departures"] / dp["fiala"]["votes"]),
        # yearly, descriptive
        "yr_lo": pct(min(cz_levels)), "yr_hi": pct(max(cz_levels)), "yr_first_below": first_below,
        "yr_last": yrs[-1], "yr_n_below": len(below), "yr_n": len(yrs),
        "yr_rank_worst": max(ys[y]["czechia_rank_from_top"] for y in yrs),
        "yr_rank_worst_years": " and ".join(y for y in yrs if ys[y]["czechia_rank_from_top"] ==
                                            max(ys[z]["czechia_rank_from_top"] for z in yrs)),
        "low_b_eu": lowest(1 + sum(x["est"] < b["EU"]["est"] for x in b["EU"]["placebo"].values())),
        "low_b_rus": lowest(1 + sum(x["est"] < b["RUS"]["est"] for x in b["RUS"]["placebo"].values())),
        "se_b_eu": pts(b["EU"]["se"], False),
        "se_b_med": pts(statistics.median(x["se"] for x in b["EU"]["placebo"].values()), False),
        "low_members": " and ".join(names.get(c, c) for c, _ in Counter(ys[y]["lowest_other"] for y in yrs).most_common(2)),
        "ranked_partner": a["HUN"]["members_ranked"], "ranked_eu": a["EU"]["members_ranked"],
        "reg_b": pts(qb["checks"]["regular_sessions_only"]["est"]),
        "es_fia": n(b["EU"]["n_after"] - qb["checks"]["regular_sessions_only"]["n_after"]),
        "chk_dev": pts(max(abs(c[k]["est"] - c0["est"]) for c, c0 in ((qa["checks"], a["EU"]), (qb["checks"], b["EU"]))
                           for k in ("no_partial_credit", "without_hungary_slovakia", "no_buffer", "confidence_dates",
                                     *(("regular_sessions_only",) if c is qa["checks"] else ()))), False),
        "tests_table": tests_table(res), "checks_table": checks_table(res), "pos_table": positions_table(posj),
        "relabelled": "; ".join(relabelled(res)) or "none would",
        "adm_date": day(next(x["date"] for x in opp if short(x["title"]).startswith("Admission of new Members"))),
        "co_lo": pct(min(a["EU"]["comparison_before"], a["EU"]["comparison_after"], b["EU"]["comparison_after"])),
        "co_hi": pct(max(a["EU"]["comparison_before"], a["EU"]["comparison_after"], b["EU"]["comparison_after"])),
        "es_dep_fia": n(pp["fiala"]["departures_emergency"]),
        "es10_fia": n(pp["fiala"]["emergency_by_session"].get("10emsp", 0)),
        "es11_fia": n(pp["fiala"]["emergency_by_session"].get("11emsp", 0)),
        "es_share": pct((b["EU"]["est"] - qb["checks"]["regular_sessions_only"]["est"]) / b["EU"]["est"], 0),
        "gap_b_eu": pts(nearest(b["EU"]), False), "gap_b_rus": pts(nearest(b["RUS"]), False),
        "proj_ratio_lo": n(min(ratios), 1), "proj_ratio_hi": n(max(ratios), 1),
        "cz_se_lo": pts(min(cz_se), False), "cz_se_hi": pts(max(cz_se), False),
        "med_se_lo": pts(min(med_se), False), "med_se_hi": pts(max(med_se), False),
        "proj_w_lo": pts(q1w * min(ratios), False), "proj_w_hi": pts(q1w * max(ratios), False),
        "yr_gap_lo": pts(min(gaps), False), "yr_gap_hi": pts(max(gaps), False),
        "cz_mean": pct(statistics.mean([a["EU"]["czechia_before"], a["EU"]["czechia_after"], b["EU"]["czechia_after"]]), 0),
        "ip_dep_sobotka": word(dp["sobotka"]["by_topic"]["israel_palestine"]),
        "tw_sobotka_ip": word(dp["sobotka"]["by_topic"]["israel_palestine"]),
        "o_sobotka_w": word(pos["sobotka"]["pairs"].get("czechia N, majority Y", 0)),
        **{f"ip_{k}_{x}": n(pp[k]["ip_czechia"][x]) for k in pp for x in ("Y", "A", "N")},
        **{f"ipv_{k}": n(pp[k]["ip_votes"]) for k in pp},
        **{f"ipy_{k}": pct(pp[k]["ip_czechia"]["Y"] / pp[k]["ip_votes"], 0) for k in pp},
        **{f"ipo_{k}": pct(pp[k]["ip_others_shares"]["Y"], 0) for k in pp},
        **{f"ipm_{k}": pct(pp[k]["ip_majority"]["Y"] / pp[k]["ip_votes"], 0) for k in pp},
    }
    page = number_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}))
    (ROOT / "texts" / "un-votes.html").write_text(page, encoding="utf-8")
    print(json.dumps({k: x for k, x in v.items() if not k.endswith("table")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
