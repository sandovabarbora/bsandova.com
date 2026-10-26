"""The investment incentives study: figures and the article, every number from the result files.

Reads docs/research/incentives-{results,screening,districts}.json and the registered constants of the frozen code
(estimate.py; imported, nothing there is run or changed), writes assets/investment-incentives/ (charts.json, the
static fallbacks 01, 03 and 04 and a copy of results.json) and texts/investment-incentives.html from
tools/incentives/template.html. Run tools/incentives/districts.py first.

    uv run --no-project --with numpy --with pandas --with matplotlib python -I tools/incentives/article.py
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, NB, n, render, results_reader, use_article_style
from estimate import (
    BAND,
    DRAWS,
    EFFECT_MIN,
    MIN_DISTRICTS,
    MIN_EVENTS,
    SEED_BOOT,
    SEED_PERM,
    WIDTH_MAX,
)
from projects import (
    BLOCK_JOBS,
    EVENT_JOBS,
    FIRST_DECISION,
    LAST_DECISION,
    WIN_AFTER,
    WIN_BEFORE,
)

plt = use_article_style()
SLUG = "investment-incentives"
R, A = ROOT / "docs" / "research", ROOT / "assets" / SLUG
CORAL = "#c0503f"
YEARS = (-2, -1, 0, 1, 2, 3)
CHECKS = [  # key in results.json, label, name in the template
    ("1_jobs_500", "1 · at least 500 promised jobs", "k500"),
    ("1_jobs_1000", "1 · at least 1 000 promised jobs", "k1000"),
    ("1_without_largest", "1 · without the largest (Kutná Hora)", "klarge"),
    ("2_without_cancelled_or_unverified", "2 · without cancelled or unverified", "kcanc"),
    ("3_same_region", "3 · comparisons in the same region", "kregion"),
    ("4_same_tercile", "4 · comparisons in the same third of unemployment", "kterc"),
    ("5_without_2009_2020_21", "5 · without 2009 and 2020–21", "kcrisis"),
    ("6_without_boundary_districts", "6 · without boundary changes", "kbound"),
    ("7_years_1_to_5", "7 · years 1–5", "k15"),
    ("8_statutory_regime_only", "8 · statutory incentives only", "kstat"),
    ("9_placebo_two_years_earlier", "9 · placebo, two years earlier", "kplac"),
    ("10_reference_year_minus1", "10 · year −1 alone as reference", "kref"),
    ("11_control_change_minus3_to_minus2", "11 · control for years −3 to −2", "kctrl"),
    ("12_without_window_spanning_2013_01", "12 · without windows across Jan 2013", "k2013"),
]
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def pp(v: float, dp: int = 2) -> str:
    return n(v, dp, sign=True) + NB + "pp"


def one(v: float, dp: int) -> str:  # a bound that rounds to zero keeps one more decimal, so its sign shows
    d = dp + 1 if v and round(v, dp) == 0 else dp
    return n(v, d, sign=True)


def iv(ci, dp: int = 2, unit: str = NB + "pp") -> str:
    return f"{one(ci[0], dp)} to {one(ci[1], dp)}{unit}"


def names(es: list[dict]) -> str:
    xs = [f'{e["district_name"]} {e["year"]}' for e in es]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


FRACTION = {5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}


def names_big(es: list[dict]) -> str:
    xs = [f'{e["company"]} in {e["place"]}' + ("" if e["place"] == e["district_name"] else f' ({e["district_name"]} district)')
          + f', {n(e["jobs"])} jobs in {e["year"]}' for e in es]
    return "; ".join(xs[:-1]) + "; and " + xs[-1]


def nb(s: str) -> str:
    return s.replace(" ", NB)


def num_refs(page: str, values: dict) -> str:
    """[[key]] markers become citations numbered by first appearance; every entry of refs.html must be cited."""
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', render((HERE / "refs.html").read_text(encoding="utf-8"), values), re.DOTALL))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) <= set(entries), set(order) - set(entries)
    assert set(entries) <= set(order), f"uncited: {set(entries) - set(order)}"
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]", lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


# ---------------------------------------------------------------- fig. 1, the event-year coefficients

def path_rows(pr: dict) -> list[dict]:
    out = []
    for k in YEARS:
        b = pr["beta"][str(k)]
        ci = pr["beta_ci95"].get(str(k))
        tip = (f"year {n(k)}: reference, set to zero" if ci is None else
               f"year {n(k)}: {pp(b)}, 95 % {iv(ci)}")
        out.append({"x": k, "mid": round(b, 3), "lo": None if ci is None else round(ci[0], 3),
                    "hi": None if ci is None else round(ci[1], 3), "c": "grey" if k < 0 else "held", "tip": tip})
    return out


def path_chart(pr: dict) -> dict:
    rows = path_rows(pr)
    return {"alt": "Unemployment share in districts with a large incentive promise relative to comparison districts, by "
                   "year from the decision, in percentage points relative to year −1, with 95 % intervals: "
                   + ", ".join(f"year {r['x']} {pp(r['mid'])}" for r in rows if r["lo"] is not None)
                   + "; every interval includes zero.",
            "panels": [{"h": 280,
                        "x": {"kind": "linear", "domain": [-2.5, 3.5], "ticks": list(YEARS),
                              "tickLabels": {str(k): (f"year {n(k)}" if k else "year 0 · decision") for k in YEARS},
                              "fmt": {"dp": 0, "sign": True}, "label": "year from the incentive decision (12-month years)"},
                        "y": {"kind": "linear", "domain": [-0.3, 0.4], "ticks": [-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4],
                              "fmt": {"dp": 1, "sign": True}, "label": "relative to comparison districts and year −1, pp"},
                        "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                                  {"type": "span", "v0": 0.5, "v1": 3.5, "c": "held", "o": 0.06,
                                   "label": "years 1–3, Q1"},
                                  {"type": "line", "pts": [[r["x"], r["mid"]] for r in rows], "c": "held", "w": 1.2,
                                   "o": 0.45, "name": "path"},
                                  {"type": "vrange", "rows": rows, "w": 2.5}]}],
            "legend": [{"label": "before the decision (year −1 is the reference)", "c": "grey"},
                       {"label": "from the decision on, 95 % interval", "c": HELD}],
            "table": {"cols": ["event year", "coefficient, pp", "95 % interval"],
                      "rows": [[r["x"], r["mid"], "reference" if r["lo"] is None else iv([r["lo"], r["hi"]])]
                               for r in rows]},
            "data": ["results.json"]}


def static_path(pr: dict, path: Path) -> None:
    rows = path_rows(pr)
    f, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.axhline(0, color=GREY, lw=0.8)
    ax.axvspan(0.5, 3.5, color=HELD, alpha=0.06, lw=0)
    ax.plot([r["x"] for r in rows], [r["mid"] for r in rows], color=HELD, lw=1, alpha=0.45)
    for r in rows:
        c = GREY if r["x"] < 0 else HELD
        if r["lo"] is not None:
            ax.plot([r["x"], r["x"]], [r["lo"], r["hi"]], color=c, lw=2.2)
        ax.plot(r["x"], r["mid"], "o", color=c, ms=5, mec="white")
    ax.set_xticks(list(YEARS), [f"year {n(k)}" for k in YEARS])
    ax.set_ylim(-0.3, 0.4)
    ax.set_ylabel("pp, relative to year −1")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 3, the events one by one (descriptive)

def event_label(e: dict) -> str:
    return f'{e["district_name"]} {e["year"]}'


def events_chart(dist: dict) -> dict:
    ev = dist["events"]
    pts = []
    for e in ev:
        c = CORAL if e["spans_2013_01"] else HELD
        pts.append({"x": round(e["jobs_per_100"], 3), "y": round(e["change"], 3), "c": c,
                    "label": event_label(e) if e["id"] == dist["example"] else None,
                    "tip": f'{e["district_name"]} · {e["company"]}, {n(e["jobs"])} jobs, {MONTHS[e["month"] - 1]} '
                           f'{e["year"]}: {n(e["jobs_per_100"], 2)} per 100 aged 15–64, raw gap change {pp(e["change"])}'})
    bound = [[x, -x] for x in (0.12, 0.2, 0.3, 0.5, 0.7, 1, 1.5, 2, 2.5)]
    ex = next(e for e in ev if e["id"] == dist["example"])
    return {"alt": f"For each of the {len(ev)} promises, the promised jobs per 100 residents aged 15–64 of the district "
                   "(log scale) against the raw change in the district's unemployment share relative to its comparison "
                   f"districts: the changes scatter between {pp(min(e['change'] for e in ev))} and "
                   f"{pp(max(e['change'] for e in ev))} whatever the size of the promise; the promises whose window "
                   f"spans January 2013 lie mostly above zero; {ex['district_name']}, with {n(ex['jobs_per_100'], 1)} "
                   f"promised jobs per 100, lies at {pp(ex['change'])}.",
            "panels": [{"h": 300,
                        "x": {"kind": "log", "domain": [0.1, 20], "ticks": [0.1, 0.2, 0.5, 1, 2, 5, 10, 20],
                              "fmt": {"dp": 1}, "label": "promised jobs per 100 residents aged 15–64 (log scale)"},
                        "y": {"kind": "linear", "domain": [-2.5, 2], "ticks": [-2, -1, 0, 1, 2],
                              "fmt": {"dp": 0, "sign": True}, "label": "raw gap change, pp"},
                        "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                                  {"type": "line", "pts": bound, "c": "grey", "w": 1, "dash": "dash", "name": "bound"},
                                  {"type": "text", "x": 0.75, "y": -2.3, "s": "every promised job off the register",
                                   "c": "grey", "anchor": "start",
                                   "narrow": {"x": 0.11, "y": -2.3, "s": "dashed: every job off the register"}},
                                  {"type": "dots", "pts": pts, "r": 4.5}]}],
            "legend": [{"label": "window does not span January 2013", "c": HELD, "shape": "o"},
                       {"label": "window spans January 2013 (check 12 leaves these out)", "c": CORAL, "shape": "o"}],
            "table": {"cols": ["district", "company", "decision", "promised jobs", "per 100 aged 15–64",
                               "raw gap change, pp", "spans Jan 2013"],
                      "rows": [[e["district_name"], e["company"], f'{MONTHS[e["month"] - 1][:3]} {e["year"]}', e["jobs"],
                                round(e["jobs_per_100"], 2), round(e["change"], 2), "yes" if e["spans_2013_01"] else "no"]
                               for e in sorted(ev, key=lambda e: e["change"])]},
            "data": ["districts.json"]}


def static_events(dist: dict, path: Path) -> None:
    f, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.axhline(0, color=GREY, lw=0.8)
    xs = [0.12, 2.5]
    ax.plot(xs, [-x for x in xs], color=GREY, lw=0.8, ls="--")
    for e in dist["events"]:
        c = CORAL if e["spans_2013_01"] else HELD
        ax.plot(e["jobs_per_100"], e["change"], "o", color=c, ms=5.5, mec="white")
        if e["id"] == dist["example"]:
            ax.annotate(event_label(e), (e["jobs_per_100"], e["change"]), xytext=(-8, -12), textcoords="offset points",
                        ha="right", fontsize=7.5, color=c)
    ax.set_xscale("log")
    ax.set_xlim(0.1, 20)
    ax.set_ylim(-2.5, 2)
    ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 5, 10, 20], ["0.1", "0.2", "0.5", "1", "2", "5", "10", "20"])
    ax.set_xlabel("promised jobs per 100 residents aged 15–64 (log scale)")
    ax.set_ylabel("raw gap change, pp")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- fig. 4, Q1 and the checks

def check_rows(res: dict) -> list[tuple[str, dict, str]]:
    pr = res["primary"]
    return [("Q1 · registered", pr, "held")] + [(lab, res["checks"][k], "grey") for k, lab, _ in CHECKS]


def checks_chart(res: dict) -> dict:
    rows = check_rows(res)

    def r(lab, e, c, ci):
        return {"y": lab, "lo": round(e[ci][0], 3), "hi": round(e[ci][1], 3), "mid": round(e["estimate"], 3), "c": c,
                "tip": f"{lab}: {pp(e['estimate'])}, 90 % {iv(e['ci90'])}, 95 % {iv(e['ci95'])}, "
                       f"{e['n_events']} events in {e['n_treated_districts']} districts"}
    r95 = [r(*x, "ci95") for x in rows]
    r90 = [r(*x, "ci90") for x in rows]
    ch = res["checks"]
    return {"alt": "Q1 and the registered checks, change in the unemployment share relative to comparison districts in "
                   f"percentage points with 90 and 95 % intervals: Q1 {pp(res['primary']['estimate'])}; every interval "
                   "includes zero; without the promises whose window spans January 2013 the estimate is "
                   f"{pp(ch['12_without_window_spanning_2013_01']['estimate'])}, and with the "
                   f"{ch['1_jobs_1000']['n_events']} promises of at least 1 000 jobs {pp(ch['1_jobs_1000']['estimate'])} "
                   "with a very wide interval.",
            "panels": [{"h": 26 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": [-1.4, 0.9], "ticks": [-1.2, -0.8, -0.4, 0, 0.4, 0.8],
                              "fmt": {"dp": 1, "sign": True, "unit": " pp"},
                              "label": "change in the unemployment share, years 1–3 against −2 and −1, pp"},
                        "y": {"kind": "cat", "domain": [x[0] for x in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                                  {"type": "range", "rows": r95, "w": 1.5},
                                  {"type": "range", "rows": r90, "w": 4},
                                  {"type": "range", "rows": [{**x, "lo": None, "hi": None} for x in r90]}]}],
            "legend": [{"label": "registered Q1, 90 % interval (thick) and 95 % (thin)", "c": HELD},
                       {"label": "registered checks", "c": "grey"}],
            "table": {"cols": ["estimate", "change, pp", "90 % interval", "95 % interval", "events · districts"],
                      "rows": [[lab, round(e["estimate"], 3), iv(e["ci90"]), iv(e["ci95"]),
                                f'{e["n_events"]} · {e["n_treated_districts"]}'] for lab, e, _ in rows]},
            "data": ["results.json"]}


def static_checks(res: dict, path: Path) -> None:
    rows = check_rows(res)
    f, ax = plt.subplots(figsize=(7.2, 0.3 * len(rows) + 0.9))
    ax.axvline(0, color=GREY, lw=0.8)
    for i, (lab, e, c) in enumerate(reversed(rows)):
        col = HELD if c == "held" else GREY
        ax.plot(e["ci95"], [i, i], color=col, lw=1.2)
        ax.plot(e["ci90"], [i, i], color=col, lw=3.5, solid_capstyle="round")
        ax.plot(e["estimate"], i, "o", color=col, ms=5, mec="white")
    ax.set_yticks(range(len(rows)), [x[0] for x in reversed(rows)], fontsize=7.5)
    ax.set_xlim(-1.4, 0.9)
    ax.set_xlabel("change in the unemployment share, pp")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- tables in the text

def checks_table(res: dict) -> str:
    out = []
    for k, lab, _ in CHECKS:
        c = res["checks"][k]
        min_note = "" if c.get("minimum_met", True) else " <small>below the minimum of events</small>"
        out.append(f'  <tr><td>{lab}{min_note}</td><td class="v">{pp(c["estimate"])}</td>'
                   f'<td class="v">{nb(iv(c["ci90"]))}<small>{nb("95 % " + iv(c["ci95"]))}</small></td>'
                   f'<td class="v">{n(c["p_randomisation"], 2)}</td>'
                   f'<td class="v">{c["n_events"]} · {c["n_treated_districts"]}</td></tr>')
    return "\n".join(out)


def path_table(pr: dict) -> str:
    out = []
    for k in ("0", "1", "2", "3"):
        q = pr["q2"][k]
        out.append(f'  <tr><td>year {k}</td><td class="v">{pp(q["est"])}</td><td class="v">{nb(iv(q["ci95"]))}</td></tr>')
    return "\n".join(out)


# ---------------------------------------------------------------- the page

def main() -> None:
    j = results_reader("incentives")
    res, scr, dist = j("results"), j("screening"), j("districts")
    pr, ch = res["primary"], res["checks"]
    ev = dist["events"]
    ex = next(e for e in ev if e["id"] == dist["example"])
    span = [e for e in ev if e["spans_2013_01"]]
    rest = [e for e in ev if not e["spans_2013_01"]]
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "incentives-results.json", A / "results.json")
    charts = {"path": path_chart(pr), "events": events_chart(dist), "checks": checks_chart(res)}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    static_path(pr, A / "01-path.svg")
    static_events(dist, A / "03-events.svg")
    static_checks(res, A / "04-checks.svg")

    # the text states these; fail loudly if a re-run changed them
    assert pr["label"] == "underpowered" and pr["minimum_met"] and WIDTH_MAX < pr["width90"] < WIDTH_MAX + 0.02
    assert pr["ci90"][0] < 0 < pr["estimate"] and pr["ci95"][0] < 0 and pr["p_randomisation"] > 0.5
    assert pr["pre_diff_ci95"][0] < 0 < pr["pre_diff_ci95"][1]
    assert all(c["ci95"][0] < 0 < c["ci95"][1] for c in ch.values())
    assert all(c.get("label") is None for c in ch.values())
    assert ch["12_without_window_spanning_2013_01"]["estimate"] < 0 < ch["12_without_window_spanning_2013_01"]["ci90"][1]
    assert all(ch[k]["estimate"] > 0 for k, _, _ in CHECKS if k not in ("1_jobs_1000", "12_without_window_spanning_2013_01"))
    assert abs(ch["2_without_cancelled_or_unverified"]["estimate"]) < 0.01
    assert ex["change"] < 0 and not ex["spans_2013_01"] and len(span) == 10
    assert abs(statistics.mean(e["change"] for e in rest) - ch["12_without_window_spanning_2013_01"]["estimate"]) < 1e-9
    assert len({e["district"] for e in ev}) == pr["n_treated_districts"] == scr["n_treated_districts"]
    assert len(ev) == pr["n_events"] == scr["n_events"]

    pos_checks = [ch[k]["estimate"] for k, _, _ in CHECKS if ch[k]["estimate"] > 0]
    assert sum(ch[k]["estimate"] < 0 for k in ch) == 2 and ch["1_jobs_1000"]["estimate"] < 0
    assert ch["9_placebo_two_years_earlier"]["estimate"] / pr["estimate"] < 0.6
    assert max(pos_checks) <= 1 / 6 and all(abs(pr["beta"][str(k)]) <= 0.1 for k in YEARS)
    assert round(pr["ci90"][0], 1) == -0.1 and round(pr["ci90"][1], 1) == 0.3
    assert 0.05 < -ex["change"] / ex["jobs_per_100"] < 0.1 and (ex["year"], ex["month"]) == (2007, 3)
    assert ex["gap"]["-2"] > 0 and ex["gap"]["-1"] > 0 and statistics.mean(ex["gap"][k] for k in "123") < 0
    assert sum(e["jobs"] <= 600 for e in ev) > len(ev) / 2
    span_m = [e["year"] * 12 + e["month"] - 1 for e in span]
    imp = dist["implied_denominator"]
    assert imp["step"] == "2014-01" and all(e["spans_2014_01"] for e in span)
    extra14 = [e for e in ev if e["spans_2014_01"] and not e["spans_2013_01"]]
    drop = scr["dropped_by_reason"]
    cancelled = sum(e["cancelled"] == "ANO" for e in ev)
    unverified = sum(e["cancelled"] == "ověřit" for e in ev)
    per100 = sorted(e["jobs_per_100"] for e in ev)
    below = sorted((e for e in ev if e["change"] < -e["jobs_per_100"]), key=lambda e: e["change"])
    twice = sorted({e["district_name"] for e in ev if sum(x["district"] == e["district"] for x in ev) == 2})
    c = lambda k: ch[k]
    v = {
        "draws": n(DRAWS), "seed_boot": SEED_BOOT, "seed_perm": SEED_PERM,
        "width_max": n(WIDTH_MAX, 2), "band": n(BAND, 2), "effect_min": n(EFFECT_MIN, 2),
        "min_events": MIN_EVENTS, "min_districts": MIN_DISTRICTS,
        "events": pr["n_events"], "districts": pr["n_treated_districts"],
        "rows": n(scr["projects"]["rows"]), "rows_ipo": n(scr["projects"]["rows_ipo"]),
        "cand": len(scr["events"]) + len(scr["dropped"]),
        "drop_window": drop["window"], "drop_clean": drop["clean window"], "drop_prague": drop["Prague"],
        "drop_multi": drop["matching: several places"],
        "comp_min": min(e["comparisons"] for e in ev), "comp_max": max(e["comparisons"] for e in ev),
        "year_first": min(e["year"] for e in ev), "year_last": max(e["year"] for e in ev),
        "cancelled": cancelled, "unverified": unverified, "twice": ", ".join(twice[:-1]) + " and " + twice[-1],
        "n_twice": len(twice),
        "boundary_treated": sum(e["treated_in_boundary_list"] for e in scr["events"]),
        # Q1
        "q1": pp(pr["estimate"]), "q1_ci90": iv(pr["ci90"]), "q1_ci95": iv(pr["ci95"]),
        "q1_short": n(pr["estimate"], 2, sign=True), "q1_lo90": one(pr["ci90"][0], 2), "q1_hi90": one(pr["ci90"][1], 2),
        "p": n(pr["p_randomisation"], 2), "width": n(pr["width90"], 3),
        "sdc": n((pr["ci95"][1] - pr["ci95"][0]) / 2, 2),
        "pre": pp(pr["pre_diff"]), "pre_ci95": iv(pr["pre_diff_ci95"]), "pre_ci90": iv(pr["pre_diff_ci90"]),
        "b_m2": pp(pr["beta"]["-2"]),
        **{f"b{k}": pp(pr["beta"][str(k)]) for k in (0, 1, 2, 3)},
        **{f"q2_{k}": pp(pr["q2"][str(k)]["est"]) for k in (0, 1, 2, 3)},
        **{f"q2_{k}_ci": iv(pr["q2"][str(k)]["ci95"]) for k in (0, 1, 2, 3)},
        "events_per_draw": n(pr["bootstrap_events_per_draw_mean"], 1),
        "redrawn": n(pr["bootstrap_redrawn"]), "failed": n(pr["bootstrap_failed"] + pr["permutations_missing"]),
        # Q3
        "q3": n(pr["q3"]["est"], 2, sign=True), "q3_ci90": iv(pr["q3"]["ci90"], 2, ""),
        "q3_lo": n(pr["q3"]["ci90"][0], 2, sign=True),
        "q3_den": n(pr["q3"]["denominator"], 2), "q3_med": n(statistics.median(per100), 2),
        "q3_min": n(per100[0], 2), "q3_max_rest": n(per100[-2], 2),
        "q3_den_wo": n(c("1_without_largest")["q3"]["denominator"], 2),
        # checks
        **{a: pp(c(k)["estimate"]) for k, _, a in CHECKS},
        **{f"{a}_ci90": iv(c(k)["ci90"]) for k, _, a in CHECKS},
        **{f"{a}_n": c(k)["n_events"] for k, _, a in CHECKS},
        **{f"{a}_d": c(k)["n_treated_districts"] for k, _, a in CHECKS},
        **{f"{a}_p": n(c(k)["p_randomisation"], 2) for k, _, a in CHECKS},
        "kterc_w": n(c("4_same_tercile")["width90"], 2),
        "kplac_left": c("9_placebo_two_years_earlier")["left_out_before_2004_07"],
        "n_span": len(span), "below": names(below), "n_below": len(below),
        "span_pos": sum(e["change"] > 0 for e in span), "span_mean": pp(statistics.mean(e["change"] for e in span)),
        "rest_neg": sum(e["change"] < 0 for e in rest), "n_rest": len(rest),
        "neg": sum(e["change"] < 0 for e in ev), "pos": sum(e["change"] > 0 for e in ev),
        "chg_min": pp(min(e["change"] for e in ev)), "chg_max": pp(max(e["change"] for e in ev)),
        # the example
        "ex_name": ex["district_name"], "ex_company": ex["company"], "ex_jobs": n(ex["jobs"]),
        "ex_date": f'{int(ex["decision"][:2])} {MONTHS[ex["month"] - 1]} {ex["year"]}',
        "ex_pop": n(round(ex["pop_15_64_year_m1"], -2)), "ex_per100": n(ex["jobs_per_100"], 1),
        "ex_change": pp(ex["change"]), "ex_comp": ex["comparisons"],
        "ex_t_m1": n(ex["treated"]["-1"], 1), "ex_c_m1": n(ex["comparison_mean"]["-1"], 1),
        "ex_g_pre": n((ex["gap"]["-2"] + ex["gap"]["-1"]) / 2, 1, sign=True),
        "ex_g_post": n((ex["gap"]["1"] + ex["gap"]["2"] + ex["gap"]["3"]) / 3, 1, sign=True),
        "ex_t_3": n(ex["treated"]["3"], 1), "ex_c_3": n(ex["comparison_mean"]["3"], 1),
        "ex_share": n(-ex["change"] / ex["jobs_per_100"], 2),  # the text says less than a tenth
        "ex_last": f'{MONTHS[(ex["month"] - 1 + 47) % 12]} {ex["year"] + (ex["month"] - 1 + 47) // 12}',
        "ex_first": f'{MONTHS[(ex["month"] - 1 - 24) % 12]} {ex["year"] + (ex["month"] - 1 - 24) // 12}',
        "ex_g_pre_abs": n((ex["gap"]["-2"] + ex["gap"]["-1"]) / 2, 2),
        "ex_g_post_abs": n(-statistics.mean(ex["gap"][k] for k in "123"), 2),
        "span_from": (min(span_m) - WIN_BEFORE) // 12, "span_to": (max(span_m) + WIN_AFTER) // 12,
        "span_y0": min(e["year"] for e in span), "span_y1": max(e["year"] for e in span),
        "q3_lo_frac": FRACTION[round(1 / -pr["q3"]["ci90"][0])],
        "event_jobs": EVENT_JOBS, "block_jobs": BLOCK_JOBS,
        "first_decision": f"{FIRST_DECISION.day} {MONTHS[FIRST_DECISION.month - 1]} {FIRST_DECISION.year}",
        "last_decision": f"{LAST_DECISION.day} {MONTHS[LAST_DECISION.month - 1]} {LAST_DECISION.year}",
        "win_before": WIN_BEFORE, "win_after": WIN_AFTER,
        "base_before": n(imp["before"] / 1e6, 1), "base_after": n(imp["after"] / 1e6, 1),
        "base_ratio": n(imp["after"] / imp["before"], 2),
        "n_span14_extra": len(extra14), "span14_extra": names(extra14),
        "largest": names_big(sorted(ev, key=lambda e: -e["jobs"])[:3]),
        "checks_table": checks_table(res), "path_table": path_table(pr),
    }
    page = num_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}), v)
    (ROOT / "texts" / f"{SLUG}.html").write_text(page, encoding="utf-8")
    print(json.dumps({k: x for k, x in v.items() if not k.endswith("table")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
