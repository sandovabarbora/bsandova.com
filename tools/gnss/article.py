"""The GNSS study: figures and the article, every number from the result files.

Reads docs/research/gnss-{results,screen,describe}.json and the registered constants of the frozen code (estimate.py,
count.py; imported, nothing there is run or changed), writes assets/gnss-interference/ (charts.json, the static
fallbacks 02-05 and copies of the JSON files) and texts/gnss-interference.html from tools/gnss/template.html.
Run tools/gnss/describe.py and tools/gnss/map.py first.

    uv run --no-project --with numpy --with pandas --with pyarrow --with shapely --with matplotlib \
        python -I tools/gnss/article.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, LIGHT, NB, n, render, results_reader, use_article_style  # noqa: E402
from estimate import DRAWS, SEED  # noqa: E402

plt = use_article_style()
SLUG = "gnss-interference"
R, A = ROOT / "docs" / "research", ROOT / "assets" / SLUG
TEAL, CORAL = "#2a7f86", "#c0503f"
REG = {"CZ": ("Czechia", HELD), "PL": ("Poland", TEAL), "BALT": ("Baltic states", CORAL),
       "CTRL": ("control (Austria and Switzerland)", GREY)}
BANDS = ("0-300", "300-600", "600-900", "900+")
BAND_LAB = {"0-300": "0–300 km", "300-600": "300–600 km", "600-900": "600–900 km", "900+": "over 900 km"}
YEARS = {1: "Mar 2023 – Feb 2024", 2: "Mar 2024 – Feb 2025", 3: "Mar 2025 – Feb 2026", 4: "Mar – Oct 2026"}
CHECKS = [  # key in results.json, label
    ("c1_nic", "1 · NIC below 7 instead of NACp"),
    ("c1_nic_same", "1 · NIC, on the primary points"),
    ("c2_anyalt", "2 · any altitude"),
    ("c3_v12", "3 · ADS-B versions 1 and 2"),
    ("c4_screenable", "4 · screenable aircraft only"),
    ("c5_paired", "5 · paired within aircraft"),
    ("c6_austria", "6 · control: Austria alone"),
    ("c6_switzerland", "6 · control: Switzerland alone"),
    ("c6_germany_w10e", "6 · control: Germany west of 10° E"),
    ("c7_equal_days", "7 · equal day weights"),
    ("c8_nobuf", "8 · no entry buffer"),
    ("c9_without_storm_days", "9 · without days of Kp ≥ 5"),
    ("c9_kp_5_or_more", "9 · days of Kp ≥ 5 only"),
    ("c10_nacp7", "10 · NACp below 7"),
    ("c11_crossings", "11 · crossings instead of reports"),
    ("c12_cap40", "12 · at most 40 reports per aircraft and day"),
    ("c13_strict_airframes", "13 · strict airframe screen"),
]


def pp(v: float, dp: int = 2) -> str:
    return n(100 * v, dp, sign=True) + NB + "pp"


def one(v: float, dp: int) -> str:  # a bound that rounds to zero keeps one more decimal, so its sign shows
    d = dp + 1 if v and round(100 * v, dp) == 0 else dp
    return n(100 * v, d, sign=True)


def iv(ci, dp: int = 2) -> str:
    return f"{one(ci[0], dp)} to {one(ci[1], dp)}{NB}pp"


def pct(v: float, dp: int = 2) -> str:
    return n(100 * v, dp) + NB + "%"


def nb(s: str) -> str:
    return s.replace(" ", NB)


def num_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', render((HERE / "refs.html").read_text(encoding="utf-8"), values), re.S))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) <= set(entries), set(order) - set(entries)
    assert set(entries) <= set(order), f"uncited: {set(entries) - set(order)}"
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]", lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


# ---------------------------------------------------------------- fig. 2, E per region and study year

def years_chart(pr: dict) -> dict:
    off = {"CZ": -0.12, "PL": 0, "BALT": 0.12}
    marks = [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
             {"type": "rule", "axis": "y", "v": 1, "c": "light", "dash": "dash", "label": "one point", "anchor": "end"}]
    for x in ("CZ", "PL", "BALT"):
        name, c = REG[x]
        rows = []
        for y in range(1, 5):
            e = pr[f"E.{x}.y{y}"]
            rows.append({"x": y + off[x], "lo": round(100 * e["ci95"][0], 3), "hi": round(100 * e["ci95"][1], 3),
                         "mid": round(100 * e["est"], 3), "c": c,
                         "tip": f"{name}, year {y} ({YEARS[y]}): {pp(e['est'])}, 95 % {iv(e['ci95'])}, {e['label']}"})
        marks.append({"type": "line", "pts": [[r["x"], r["mid"]] for r in rows], "c": c, "w": 1.2, "o": 0.5,
                      "name": name, "end": name})
        marks.append({"type": "vrange", "rows": rows, "w": 2.5})
    return {"alt": "The share of degraded position reports minus control's, in percentage points, per study year with "
                   "95 % intervals: Czechia stays near zero in all four years, Poland rises to between 2 and 3 points "
                   "and the Baltic states from about 1 to about 12 to 13 points in years 3 and 4.",
            "panels": [{"h": 300, "padRight": 110,
                        "x": {"kind": "linear", "domain": [0.6, 4.4], "ticks": [1, 2, 3, 4],
                              "tickLabels": {str(y): f"year {y}" for y in range(1, 5)}, "fmt": {"dp": 0},
                              "label": "study year, March to February (year 4: March to October 2026)"},
                        "y": {"kind": "linear", "domain": [-1, 15], "ticks": [0, 2, 4, 6, 8, 10, 12, 14],
                              "fmt": {"dp": 0, "sign": True}, "label": "E, percentage points"},
                        "marks": marks}],
            "legend": [{"label": REG[x][0], "c": REG[x][1]} for x in ("CZ", "PL", "BALT")],
            "table": {"cols": ["region", "study year", "E, pp", "95 % interval", "label"],
                      "rows": [[REG[x][0], f"{y} · {YEARS[y]}", round(100 * pr[f"E.{x}.y{y}"]["est"], 2),
                                iv(pr[f"E.{x}.y{y}"]["ci95"]), pr[f"E.{x}.y{y}"]["label"]]
                               for x in ("CZ", "PL", "BALT") for y in range(1, 5)]},
            "data": ["results.json"]}


def static_years(pr: dict, path: Path) -> None:
    f, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.axhline(0, color=GREY, lw=0.8)
    ax.axhline(1, color=LIGHT, lw=0.8, ls="--")
    for x, o in (("CZ", -0.12), ("PL", 0), ("BALT", 0.12)):
        name, c = REG[x]
        es = [pr[f"E.{x}.y{y}"] for y in range(1, 5)]
        xs = [y + o for y in range(1, 5)]
        ax.plot(xs, [100 * e["est"] for e in es], color=c, lw=1, alpha=0.5)
        for xx, e in zip(xs, es):
            ax.plot([xx, xx], [100 * e["ci95"][0], 100 * e["ci95"][1]], color=c, lw=2.2)
        ax.plot(xs, [100 * e["est"] for e in es], "o", color=c, ms=5, mec="white", label=name)
    ax.set_xticks([1, 2, 3, 4], [f"year {y}" for y in range(1, 5)])
    ax.set_ylabel("E, percentage points")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 3, the share per sampled day (descriptive)

def decimal(d: str) -> float:
    t = dt.date.fromisoformat(d)
    start = dt.date(t.year, 1, 1)
    return round(t.year + (t - start).days / (dt.date(t.year + 1, 1, 1) - start).days, 4)


def days_chart(desc: dict) -> dict:
    days = desc["days"]
    ticks = [2023.5, 2024, 2024.5, 2025, 2025.5, 2026, 2026.5]
    tl = {str(t): (f"Jan {int(t)}" if t == int(t) else f"Jul {int(t)}") for t in ticks}
    tl = {k.replace(".0", ""): v for k, v in tl.items()}

    def series(x):
        return [[decimal(d["date_used"]), round(100 * d[x]["share"], 3)] for d in days if d[x]["share"] is not None]

    def panel(title, regs, dom, ticks_y):
        marks = [{"type": "rule", "axis": "y", "v": 2, "c": "light", "dash": "dash", "label": "2 %", "anchor": "end"}]
        for x in regs:
            name, c = REG[x]
            marks.append({"type": "line", "pts": series(x), "c": c, "w": 1.4, "name": name,
                          "end": name.split(" (")[0]})
        return {"title": title, "h": 200, "padRight": 90,
                "x": {"kind": "linear", "domain": [2023.15, 2026.85], "ticks": ticks, "tickLabels": tl,
                      "fmt": {"dp": 1, "nogroup": True}, "label": "sampled day (Wednesdays)"},
                "y": {"kind": "linear", "domain": dom, "ticks": ticks_y, "fmt": {"dp": 0, "unit": " %"},
                      "label": "degraded reports, % of usable reports"},
                "marks": marks}
    return {"alt": "Descriptive, added after the results: the share of degraded position reports per sampled day. Over "
                   "Czechia and the control it stays under 2 % on every day; over Poland it rises from 2024 and over "
                   "the Baltic states it climbs to between 10 and 47 % on most days from 2025.",
            "layout": "rows",
            "panels": [panel("Czechia and control", ("CZ", "CTRL"), [0, 3], [0, 1, 2, 3]),
                       panel("Poland and the Baltic states", ("PL", "BALT"), [0, 50], [0, 10, 20, 30, 40, 50])],
            "legend": [{"label": REG[x][0], "c": REG[x][1]} for x in REG],
            "table": {"cols": ["day used", "study year", *[f"{REG[x][0]}, %" for x in REG]],
                      "rows": [[d["date_used"], d["study_year"],
                                *[None if d[x]["share"] is None else round(100 * d[x]["share"], 2) for x in REG]]
                               for d in days]},
            "data": ["describe.json"]}


def static_days(desc: dict, path: Path) -> None:
    days = desc["days"]
    f, axes = plt.subplots(2, 1, figsize=(7.2, 4.4), sharex=True)
    for ax, regs, top in ((axes[0], ("CZ", "CTRL"), 3), (axes[1], ("PL", "BALT"), 50)):
        ax.axhline(2, color=LIGHT, lw=0.8, ls="--")
        for x in regs:
            pts = [(decimal(d["date_used"]), 100 * d[x]["share"]) for d in days if d[x]["share"] is not None]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=REG[x][1], lw=1.2, label=REG[x][0])
        ax.set_ylim(0, top)
        ax.set_ylabel("% degraded")
        ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 4, D per region and distance band

def bands_chart(q2: dict) -> dict:
    D = q2["D_by_region_and_band"]
    off = {"CZ": -0.18, "PL": -0.06, "BALT": 0.06, "CTRL": 0.18}
    marks = []
    rows_tbl = []
    for x in REG:
        name, c = REG[x]
        rows = []
        for i, b in enumerate(BANDS):
            e = D[x][b]
            if e["est"] is None:
                continue
            rows.append({"x": i + off[x], "lo": round(100 * e["ci95"][0], 3), "hi": round(100 * e["ci95"][1], 3),
                         "mid": round(100 * e["est"], 3), "c": c,
                         "tip": f"{name}, {BAND_LAB[b]} from Kaliningrad: {pct(e['est'])}, 95 % "
                                f"{pct(e['ci95'][0])} to {pct(e['ci95'][1])}"})
            rows_tbl.append([name, BAND_LAB[b], round(100 * e["est"], 2), f"{pct(e['ci95'][0])} to {pct(e['ci95'][1])}"])
        marks.append({"type": "vrange", "rows": rows, "w": 2.5})
    return {"alt": "The share of degraded position reports per region and band of distance from Kaliningrad city, on a "
                   "log scale, with 95 % intervals: Czechia about 0.5 % in both of its bands, like control; Poland "
                   "about 5 % within 300 km, 1.5 % at 300–600 km and 4 % at 600–900 km; the Baltic states 4 %, 9 % "
                   "and 50 %, the highest in their farthest band, north-eastern Estonia.",
            "panels": [{"h": 300,
                        "x": {"kind": "linear", "domain": [-0.5, 3.5], "ticks": [0, 1, 2, 3],
                              "tickLabels": {str(i): BAND_LAB[b] for i, b in enumerate(BANDS)}, "fmt": {"dp": 0},
                              "label": "distance from Kaliningrad city"},
                        "y": {"kind": "log", "domain": [0.2, 80], "ticks": [0.25, 0.5, 1, 2, 5, 10, 20, 50],
                              "tickLabels": {str(t): f"{t:g}" for t in (0.25, 0.5, 1, 2, 5, 10, 20, 50)}, "fmt": {"dp": 2, "unit": " %"},
                              "label": "degraded reports, % of usable reports (log scale)"},
                        "marks": marks}],
            "legend": [{"label": REG[x][0], "c": REG[x][1]} for x in REG],
            "table": {"cols": ["region", "band", "share, %", "95 % interval"], "rows": rows_tbl},
            "data": ["results.json"]}


def static_bands(q2: dict, path: Path) -> None:
    D = q2["D_by_region_and_band"]
    f, ax = plt.subplots(figsize=(7.2, 3.4))
    for x, o in (("CZ", -0.18), ("PL", -0.06), ("BALT", 0.06), ("CTRL", 0.18)):
        name, c = REG[x]
        for i, b in enumerate(BANDS):
            e = D[x][b]
            if e["est"] is None:
                continue
            ax.plot([i + o] * 2, [100 * e["ci95"][0], 100 * e["ci95"][1]], color=c, lw=2.2)
            ax.plot(i + o, 100 * e["est"], "o", color=c, ms=5, mec="white", label=name if i in (1, 2) and
                    not any(t.get_label() == name for t in ax.lines[:-1]) else None)
    ax.set_yscale("log")
    ax.set_yticks([0.25, 0.5, 1, 2, 5, 10, 20, 50], ["0.25", "0.5", "1", "2", "5", "10", "20", "50"])
    ax.set_xticks(range(4), [BAND_LAB[b] for b in BANDS])
    ax.set_ylabel("% degraded (log)")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 5, the checks on E_CZ

def check_rows(res: dict) -> list[tuple[str, dict, str]]:
    rows = [("Q1 · registered estimate", res["q1"], "held")]
    rows += [(lab, res["checks"][k]["E.CZ"], "grey") for k, lab in CHECKS]
    return rows


def checks_chart(res: dict) -> dict:
    rows = check_rows(res)

    def r(lab, e, c, k):
        return {"y": lab, "lo": round(100 * e[k][0], 3), "hi": round(100 * e[k][1], 3), "mid": round(100 * e["est"], 3),
                "c": "held" if c == "held" else ("#9a4a2b" if e["label"] != res["q1"]["label"] else "grey"),
                "tip": f"{lab}: {pp(e['est'])}, 90 % {iv(e['ci90'])}, 95 % {iv(e['ci95'])}, {e['label']}"}
    r95, r90 = [r(*x, "ci95") for x in rows], [r(*x, "ci90") for x in rows]
    return {"alt": "E for Czechia, in percentage points, with 90 and 95 % intervals, for the registered estimate and "
                   "each registered check: all lie below one point except the check at any altitude, whose interval "
                   "reaches above it, labelled inconclusive.",
            "panels": [{"h": 24 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": [-0.5, 2], "ticks": [-0.5, 0, 0.5, 1, 1.5, 2],
                              "fmt": {"dp": 1, "sign": True}, "label": "E for Czechia, percentage points"},
                        "y": {"kind": "cat", "domain": [x[0] for x in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                                  {"type": "rule", "axis": "x", "v": 1, "c": "light", "dash": "dash",
                                   "label": "one point"},
                                  {"type": "range", "rows": r95, "w": 1.5},
                                  {"type": "range", "rows": r90, "w": 4},
                                  {"type": "range", "rows": [{**x, "lo": None, "hi": None} for x in r90]}]}],
            "legend": [{"label": "registered Q1, 90 % (thick) and 95 % (thin)", "c": HELD},
                       {"label": "check, same label as Q1", "c": "grey"},
                       {"label": "check with a different label", "c": "#9a4a2b"}],
            "table": {"cols": ["estimate", "E, pp", "90 % interval", "95 % interval", "label"],
                      "rows": [[lab, round(100 * e["est"], 3), iv(e["ci90"]), iv(e["ci95"]), e["label"]]
                               for lab, e, _ in rows]},
            "data": ["results.json"]}


def static_checks(res: dict, path: Path) -> None:
    rows = check_rows(res)
    f, ax = plt.subplots(figsize=(7.2, 0.27 * len(rows) + 0.9))
    ax.axvline(0, color=GREY, lw=0.8)
    ax.axvline(1, color=LIGHT, lw=0.8, ls="--")
    for i, (lab, e, c) in enumerate(reversed(rows)):
        col = HELD if c == "held" else ("#9a4a2b" if e["label"] != res["q1"]["label"] else GREY)
        ax.plot([100 * x for x in e["ci95"]], [i, i], color=col, lw=1.2)
        ax.plot([100 * x for x in e["ci90"]], [i, i], color=col, lw=3.5, solid_capstyle="round")
        ax.plot(100 * e["est"], i, "o", color=col, ms=5, mec="white")
    ax.set_yticks(range(len(rows)), [x[0] for x in reversed(rows)], fontsize=7.5)
    ax.set_xlim(-0.5, 2)
    ax.set_xlabel("E for Czechia, percentage points")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- tables in the text

def tests_table(res: dict) -> str:
    q2 = res["q2"]
    rows = [("Q1 · Czechia minus control, E_CZ", res["q1"], "registered"),
            ("Q2 · Poland minus control, E_PL", q2["E_PL"], "descriptive"),
            ("Q2 · Baltic states minus control, E_BALT", q2["E_BALT"], "descriptive")]
    out = []
    for name, e, kind in rows:
        out.append(f'  <tr><td>{name} <small>{kind}</small></td><td class="v">{pp(e["est"])}</td>'
                   f'<td class="v">{nb(iv(e["ci90"]))}<small>{nb("95 % " + iv(e["ci95"]))}</small></td>'
                   f'<td class="v">{nb(iv(e["days_only_ci95"]))}</td><td class="v"><b>{e["label"]}</b></td></tr>')
    c = res["q3"]["change"]
    out.append(f'  <tr><td>Q3 · change in E_CZ, 2024 to 2026 window <small>registered</small></td>'
               f'<td class="v">{pp(c["est"])}</td><td class="v">{nb(iv(c["ci90"]))}<small>{nb("95 % " + iv(c["ci95"]))}'
               f'</small></td><td class="v">{nb(iv(c["days_only_ci95"]))}</td><td class="v"><b>{c["label"]}</b></td></tr>')
    return "\n".join(out)


def checks_table(res: dict) -> str:
    out = []
    for k, lab in CHECKS:
        c = res["checks"][k]
        cells = []
        for x in ("E.CZ", "E.PL", "E.BALT"):
            e = c[x]
            mark = " <b>≠</b>" if e["differs_from_primary"] else ""
            cells.append(f'<td class="v">{pp(e["est"])}<small>{nb("95 % " + iv(e["ci95"]))}<br>{e["label"]}{mark}</small></td>')
        out.append(f'  <tr><td>{lab}</td>{"".join(cells)}</tr>')
    return "\n".join(out)


def q3_table(res: dict) -> str:
    est = res["q3"]["estimators"]
    out = []
    for k, lab in [("primary", "registered Q3, paired aircraft draw"), *CHECKS]:
        e = est[k]
        mark = " <b>≠</b>" if e["differs_from_primary"] else ""
        miss = f' · {n(e["missing_draws"])} draws missing' if e["missing_draws"] else ""
        out.append(f'  <tr><td>{lab}</td><td class="v">{pp(e["E_CZ_2024"])}</td><td class="v">{pp(e["E_CZ_2026"])}</td>'
                   f'<td class="v">{pp(e["est"])}<small>{nb("95 % " + iv(e["ci95"]))}{miss}</small></td>'
                   f'<td class="v">{e["label"]}{mark}</td></tr>')
    ia = res["q3"]["independent_aircraft"]
    out.append(f'  <tr><td>aircraft redrawn per window</td><td class="v">{pp(ia["E_CZ_2024"])}</td>'
               f'<td class="v">{pp(ia["E_CZ_2026"])}</td><td class="v">{pp(ia["est"])}<small>{nb("95 % " + iv(ia["ci95"]))}'
               f'</small></td><td class="v">{ia["label"]}</td></tr>')
    return "\n".join(out)


def days_table(res: dict) -> str:
    dpd = res["degraded_position_days"]
    out = []
    for y in range(1, 5):
        cells = "".join(f'<td class="v">{dpd[x][str(y)]["degraded_position_days"]} <small>of '
                        f'{dpd[x][str(y)]["eligible_days"]}</small></td>' for x in ("CZ", "PL", "BALT"))
        out.append(f'  <tr><td>year {y} <small>{YEARS[y]}</small></td>{cells}</tr>')
    return "\n".join(out)


# ---------------------------------------------------------------- the page

def main() -> None:
    j = results_reader("gnss")
    res, scr, desc = j("results"), j("screen"), j("describe")
    A.mkdir(parents=True, exist_ok=True)
    for src in ("results", "describe"):
        shutil.copy(R / f"gnss-{src}.json", A / f"{src}.json")
    charts = {"years": years_chart(res["primary"]), "days": days_chart(desc), "bands": bands_chart(res["q2"]),
              "checks": checks_chart(res)}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    static_years(res["primary"], A / "02-years.svg")
    static_days(desc, A / "03-days.svg")
    static_bands(res["q2"], A / "04-bands.svg")
    static_checks(res, A / "05-checks.svg")

    pr, q1, q2, q3, q4 = res["primary"], res["q1"], res["q2"], res["q3"], res["q4"]
    ch, dpd, smp = res["checks"], res["degraded_position_days"], res["sample"]
    D = q2["D_by_region_and_band"]
    gr = q2["gradient"]
    days = scr["days"]
    NO, HI = "no excess larger than one point", "higher degraded share than control"
    # the text states these; fail loudly if a re-run changed them
    assert q1["label"] == NO and q1 == {k: v for k, v in pr["E.CZ"].items()}
    assert q2["E_PL"]["label"] == q2["E_BALT"]["label"] == HI
    assert all(pr[f"E.CZ.y{y}"]["label"] == NO for y in range(1, 5))
    assert all(dpd["CZ"][str(y)]["degraded_position_days"] == 0 for y in range(1, 5))
    assert q3["change"]["label"] == "no increase larger than one point"
    diff = [k for k, _ in CHECKS if ch[k]["E.CZ"]["differs_from_primary"]]
    assert diff == ["c2_anyalt"] and ch["c2_anyalt"]["E.CZ"]["label"] == "inconclusive"
    assert [k for k, _ in CHECKS if ch[k]["E.PL"]["differs_from_primary"]] == ["c2_anyalt"]
    assert not any(ch[k]["E.BALT"]["differs_from_primary"] for k, _ in CHECKS)
    q3diff = [k for k, e in q3["estimators"].items() if e["differs_from_primary"]]
    assert q3diff == ["c2_anyalt"] and not q3["independent_aircraft"]["differs_from_primary"]
    assert not gr[".y1"]["computed"] and all(gr[k]["computed"] for k in ("pooled", ".y2", ".y3", ".y4"))
    assert pr["E.BALT.y1"]["label"] == "inconclusive"
    assert res["draws_complete"] and res["redrawn"] == 0 and not res["estimator_errors"]
    assert all(abs(ch[k]["E.CZ"]["est"]) < 0.01 for k, _ in CHECKS)
    assert D["BALT"]["600-900"]["est"] == max(D["BALT"][b]["est"] for b in BANDS if D["BALT"][b]["est"] is not None)
    assert D["PL"]["300-600"]["est"] < D["PL"]["600-900"]["est"] < D["PL"]["0-300"]["est"]
    lost = days["lost"]
    assert len(lost) == 7 and days["sampled"] == 190 and smp["days"] == 183
    pts = desc["pooled_points"]
    cz_y = [pr[f"E.CZ.y{y}"]["est"] for y in range(1, 5)]
    balt_full = [y for y in range(1, 5) if dpd["BALT"][str(y)]["degraded_position_days"] == dpd["BALT"][str(y)]["eligible_days"]]
    assert balt_full == [3, 4]
    v12 = scr["version_and_source"]["1"]["adsb_icao_fl250_version_share"]
    month = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]
    fmt_day = lambda s: f"{int(s[8:])} {month[int(s[5:7]) - 1]} {s[:4]}"  # noqa: E731
    maxday = max(desc["days"], key=lambda d: d["CZ"]["share"] or 0)

    v = {
        "draws": n(DRAWS), "seed": SEED,
        "days": smp["days"], "sampled": days["sampled"], "lost": len(lost),
        "lost_list": ", ".join(fmt_day(x["wednesday"]) for x in lost),
        "thursdays": " and ".join(fmt_day(x["thursday"]) for x in days["replaced_by_thursday"]),
        "y_days": ", ".join(str(smp["per_year"][str(y)]) for y in range(1, 5)),
        "aircraft": n(smp["aircraft"]), "screenable": n(smp["screenable"]),
        "persistent": smp["persistently_degraded"], "persistent_strict": smp["persistently_degraded_strict_reading"],
        "storm_days": smp["days_kp_5_or_more"],
        "pts_cz": n(pts["CZ"]["usable"] / 1e6, 1), "pts_pl": n(pts["PL"]["usable"] / 1e6, 1),
        "pts_balt": n(pts["BALT"]["usable"] / 1e6, 1), "pts_ctrl": n(pts["CTRL"]["usable"] / 1e6, 1),
        "v2_y1": pct(v12["v2"], 1), "old_y1": pct(v12["v0"] + v12["v1"], 1),
        # Q1
        "d_cz": pct(pr["D.CZ"]["est"]), "d_ctrl": pct(pr["D.CTRL"]["est"]), "d_pl": pct(pr["D.PL"]["est"], 1),
        "d_balt": pct(pr["D.BALT"]["est"], 1),
        "e_cz": pp(q1["est"]), "e_cz_ci90": iv(q1["ci90"]), "e_cz_ci95": iv(q1["ci95"]),
        "e_cz_days95": iv(q1["days_only_ci95"]),
        "top10_cz": pct(res["repeat_airframes_top10_share"]["CZ"], 0),
        # Q2
        "e_pl": pp(q2["E_PL"]["est"], 1), "e_pl_ci95": iv(q2["E_PL"]["ci95"], 1),
        "e_balt": pp(q2["E_BALT"]["est"], 1), "e_balt_ci95": iv(q2["E_BALT"]["ci95"], 1),
        **{f"{x.lower()}_y{y}": pp(pr[f"E.{x}.y{y}"]["est"], 2 if x == "CZ" else 1)
           for x in ("CZ", "PL", "BALT") for y in range(1, 5)},
        "balt_y1_label": pr["E.BALT.y1"]["label"], "pl_y2_label": pr["E.PL.y2"]["label"],
        "pl_y1_label": pr["E.PL.y1"]["label"],
        "cz_ymin": pp(min(cz_y)), "cz_ymax": pp(max(cz_y)),
        **{f"{x.lower()}_days_y{y}": dpd[x][str(y)]["degraded_position_days"] for x in ("PL", "BALT") for y in range(1, 5)},
        **{f"{x.lower()}_elig_y{y}": dpd[x][str(y)]["eligible_days"] for x in ("CZ", "PL", "BALT") for y in range(1, 5)},
        "pl_days": sum(dpd["PL"][str(y)]["degraded_position_days"] for y in range(1, 5)),
        "balt_days": sum(dpd["BALT"][str(y)]["degraded_position_days"] for y in range(1, 5)),
        "cz_max_day": fmt_day(maxday["date_used"]), "cz_max_share": pct(maxday["CZ"]["share"], 1),
        **{f"band{i}": pp(q2["bands"][b]["est"], 1) for i, b in enumerate(BANDS)},
        **{f"{x.lower()}_b{i}": (pct(D[x][b]["est"], 1) if D[x][b]["est"] is not None else "–")
           for x in REG for i, b in enumerate(BANDS)},
        "cz_b1": pct(D["CZ"]["300-600"]["est"], 2), "cz_b2": pct(D["CZ"]["600-900"]["est"], 2),
        "ctrl_b2": pct(D["CTRL"]["600-900"]["est"], 2), "ctrl_b3": pct(D["CTRL"]["900+"]["est"], 2),
        "g": n(gr["pooled"]["est"], 3), "g_ci95": f'{n(gr["pooled"]["ci95"][0], 3)} to {n(gr["pooled"]["ci95"][1], 3)}',
        "g_pct": n(100 * gr["pooled"]["est"], 1) + NB + "%",
        "g_y2": n(gr[".y2"]["est"], 3), "g_y3": n(gr[".y3"]["est"], 3), "g_y4": n(gr[".y4"]["est"], 3),
        "g_y1_cz": pp(gr[".y1"]["E_CZ_minus_E_BALT"]["est"]), "g_y1_cz_ci": iv(gr[".y1"]["E_CZ_minus_E_BALT"]["ci95"]),
        "g_y1_pl": pp(gr[".y1"]["E_PL_minus_E_BALT"]["est"]), "g_y1_pl_ci": iv(gr[".y1"]["E_PL_minus_E_BALT"]["ci95"]),
        # Q3
        "q3_24": pp(q3["change"]["E_CZ_2024"]), "q3_26": pp(q3["change"]["E_CZ_2026"]),
        "q3": pp(q3["change"]["est"]), "q3_ci90": iv(q3["change"]["ci90"]), "q3_ci95": iv(q3["change"]["ci95"]),
        "q3_ind95": iv(q3["independent_aircraft"]["ci95"]),
        "q3_days24": q3["days"]["2024"], "q3_days26": q3["days"]["2026"],
        "q3_any": pp(q3["estimators"]["c2_anyalt"]["est"]), "q3_any_ci95": iv(q3["estimators"]["c2_anyalt"]["ci95"]),
        "q3_storm_missing": n(q3["estimators"]["c9_kp_5_or_more"]["missing_draws"]),
        # Q4
        **{f"s_{x.lower()}": pct(q4[f"S.{x}"]["est"], 2) for x in REG},
        "s_diff_cz": pp(q4["S.diff.CZ"]["est"], 2), "s_diff_cz_ci95": iv(q4["S.diff.CZ"]["ci95"], 3),
        "s_cz_y2": pct(q4["S.CZ.y2"]["est"], 2),
        "s_b0": pct(q4["S.band.0-300"]["est"], 2), "s_b3": pct(q4["S.band.900+"]["est"], 2),
        # checks
        **{f"c_{k}": pp(ch[k]["E.CZ"]["est"]) for k, _ in CHECKS},
        **{f"c_{k}_ci95": iv(ch[k]["E.CZ"]["ci95"]) for k, _ in CHECKS},
        "c_any_pl": pp(ch["c2_anyalt"]["E.PL"]["est"]), "c_any_pl_ci95": iv(ch["c2_anyalt"]["E.PL"]["ci95"]),
        "c_any_balt": pp(ch["c2_anyalt"]["E.BALT"]["est"], 1),
        "c_nic_pl": pp(ch["c1_nic"]["E.PL"]["est"], 1), "c_nic_balt": pp(ch["c1_nic"]["E.BALT"]["est"], 1),
        "n_checks": len(CHECKS), "n_checks_agree": len(CHECKS) - len(diff),
        **{f"v_{k}": x for k, x in res["versions"].items()},
        "tests_table": tests_table(res), "checks_table": checks_table(res), "q3_table": q3_table(res),
        "days_table": days_table(res),
    }
    page = num_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}), v)
    (ROOT / "texts" / f"{SLUG}.html").write_text(page, encoding="utf-8")
    print(json.dumps({k: x for k, x in v.items() if not k.endswith("table")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
