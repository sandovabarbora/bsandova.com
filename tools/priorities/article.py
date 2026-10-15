"""The priorities study: figures and the article, every number from the result files.

Reads docs/research/priorities-{results,validation,overlap,power,data,describe}.json and the label rule of the frozen
code (estimate.py, imported; nothing there is run or changed), writes assets/czech-priorities/ (charts.json,
01-estimates.svg, 02-spending.svg, 03-attention.svg, 04-validation.svg and copies of the JSON files) and
texts/czech-priorities.html from tools/priorities/template.html. Run tools/priorities/describe.py first.

    uv run --no-project --with numpy --with pandas --with scipy --with pyarrow --with matplotlib \
        python tools/priorities/article.py
"""
from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
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
from article_kit import GREY, HELD, LIGHT, n, render, results_reader, use_article_style  # noqa: E402
from estimate import label  # noqa: E402

plt = use_article_style()
SLUG = "czech-priorities"
R, A = ROOT / "docs" / "research", ROOT / "assets" / SLUG
CORAL = "#c0503f"
DOMAIN = (-0.5, 0.7)
DESCRIBED = ("Unemployment", "Immigration", "Crime", "Pensions")  # see described_topics()


def num(v) -> float:
    return float(v) if not isinstance(v, str) else (math.inf if v == "inf" else -math.inf)


def e(v, dp: int = 2) -> str:
    return n(num(v), dp, sign=True)


def iv(ci, dp: int = 2) -> str:
    lo, hi = (num(x) for x in ci)
    a = "unbounded" if math.isinf(lo) else e(lo, dp)
    b = "unbounded" if math.isinf(hi) else e(hi, dp)
    return f"{a} to {b}"


def between(ci, dp: int = 2) -> str:
    return f"{e(ci[0], dp)} and {e(ci[1], dp)}"


def half_up(v: float, dp: int = 1) -> str:
    """Rounds the printed decimal half up (3.55 → 3.6), where binary floats would round it down."""
    return n(float(Decimal(repr(v)).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)), dp)


def pct(v: float, dp: int = 0) -> str:
    return n(100 * v, dp)


def nb(s: str) -> str:
    return s.replace(" ", "&nbsp;")


def year_of(d: str) -> float:
    x = dt.date.fromisoformat(d)
    return round(x.year + (x.timetuple().tm_yday - 1) / 365, 3)


# ---------------------------------------------------------------- what is plotted and tabled

def estimate_rows(res: dict) -> list[tuple[str, dict, str]]:
    p, q4 = res["primary"], res["q4"]["party_status"]
    rows = []
    for q, name in (("Q1", "Q1 attention"), ("Q1r", "Q1r reverse")):
        for corp, span in (("parlacap", "2013–23"), ("whole", "2004–25")):
            for m in ("static", "dynamic"):
                rows.append((f"{name}, {span}, {m}", p[corp][q][m], p[corp][q]["label"]))
    ys = {c: res["data"][c]["years_q3"] for c in ("parlacap", "whole")}
    for m in ("static", "dynamic"):
        rows.append((f"Q2 spending, {ys['whole'][0]}–{str(ys['whole'][-1])[2:]}, {m}", p["spending"]["Q2"][m],
                     p["spending"]["Q2"]["label"]))
    for corp in ("parlacap", "whole"):
        rows.append((f"Q3 attention − spending, {ys[corp][0]}–{str(ys[corp][-1])[2:]}", p[corp]["Q3"]["dynamic"],
                     p[corp]["Q3"]["label"]))
    for g, name in (("Coalition", "coalition"), ("Opposition", "opposition")):
        rows.append((f"Q4 {name}, 2013–23, static", q4[g], q4[g]["label_wild"]))
    return rows


def clip(v) -> float:
    return round(min(max(num(v), DOMAIN[0]), DOMAIN[1]), 4)


def estimates_chart(res: dict, sesoi: float) -> dict:
    rows = estimate_rows(res)
    r95, r90 = [], []
    for lab, x, reg in rows:
        own = x.get("label", x.get("label_wild"))
        tip = (f"{lab}: {e(x['estimate'])}, 90 % {iv(x['used']['90'])}, 95 % {iv(x['used']['95'])}; "
               f"this model {own}; registered label {reg}")
        r95.append({"y": lab, "lo": clip(x["used"]["95"][0]), "hi": clip(x["used"]["95"][1]),
                    "mid": round(x["estimate"], 4), "tip": tip})
        r90.append({"y": lab, "lo": clip(x["used"]["90"][0]), "hi": clip(x["used"]["90"][1]),
                    "mid": round(x["estimate"], 4), "tip": tip,
                    "c": CORAL if lab.startswith("Q2") else None})
    for r in r90:
        if r["c"] is None:
            del r["c"]
    ticks = [round(t / 10, 1) for t in range(int(DOMAIN[0] * 10), int(DOMAIN[1] * 10) + 1) if t % 2 == 0]
    return {"alt": "The registered elasticities with their 90 and 95 % intervals (the hull of the bootstrap and the "
                   "randomisation interval) for attention, the reverse direction, spending, the difference between "
                   "attention and spending, and coalition and opposition speeches; shaded, ±0.10. The spending "
                   "intervals lie inside the band in both models; the attention estimates are positive in the static "
                   "model, with wider intervals in the dynamic one.",
            "panels": [{"h": 30 * len(rows) + 40,
                        "x": {"kind": "linear", "domain": list(DOMAIN), "ticks": ticks, "fmt": {"dp": 1, "sign": True},
                              "label": "elasticity: % change in the share per 1 % change in concern"},
                        "y": {"kind": "cat", "domain": [r[0] for r in rows]},
                        "marks": [{"type": "span", "v0": -sesoi, "v1": sesoi, "c": "grey", "o": 0.09},
                                  {"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                                  {"type": "range", "rows": r95, "w": 1.5},
                                  {"type": "range", "rows": r90, "w": 4}]}],
            "legend": [{"label": "90 % interval (thick) and 95 % (thin), hull of both methods", "c": HELD},
                       {"label": "spending (Q2)", "c": CORAL},
                       {"label": f"±{n(sesoi, 2)}, the smallest elasticity of interest", "c": "grey", "shape": "box"}],
            "table": {"cols": ["estimate", "elasticity", "90 % interval", "95 % interval", "this model's label",
                               "registered label"],
                      "rows": [[lab, round(x["estimate"], 3), iv(x["used"]["90"]), iv(x["used"]["95"]),
                                x.get("label", x.get("label_wild")), reg] for lab, x, reg in rows]},
            "data": ["results.json"]}


def static_estimates(res: dict, path: Path, sesoi: float) -> None:
    rows = estimate_rows(res)
    f, ax = plt.subplots(figsize=(7.2, 0.33 * len(rows) + 0.9))
    ax.axvspan(-sesoi, sesoi, color=LIGHT, alpha=0.22, lw=0)
    ax.axvline(0, color=GREY, lw=0.8)
    for i, (lab, x, _) in enumerate(reversed(rows)):
        c = CORAL if lab.startswith("Q2") else HELD
        ax.plot([clip(v) for v in x["used"]["95"]], [i, i], color=c, lw=1.2)
        ax.plot([clip(v) for v in x["used"]["90"]], [i, i], color=c, lw=3.5, solid_capstyle="round")
        ax.plot(x["estimate"], i, "o", color=c, ms=6, mec="white")
    ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)])
    ax.set_xlim(*DOMAIN)
    ax.set_xlabel("elasticity: % change in the share per 1 % change in concern")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def spending_chart(desc: dict) -> dict:
    rows, cats = [], []
    for k, s in desc["year_series"].items():
        rg = desc["ranges"][k]
        yrs = [y for y, _, _ in s]
        for key, what, c in (("cbar", "concern", HELD), ("s", "spending", CORAL)):
            lo, hi = rg[key]
            lab = f"{k}, {what}"
            cats.append(lab)
            last = s[-1][1 if key == "cbar" else 2]
            rows.append({"y": lab, "lo": round(100 * lo, 3), "hi": round(100 * hi, 3),
                         "mid": round(100 * last, 3), "c": c,
                         "tip": f"{lab}, {yrs[0]}–{yrs[-1]}: lowest {pct(lo, 1)} %, highest {pct(hi, 1)} %, "
                                f"a factor of {n(hi / lo, 1)}; {yrs[-1]}: {pct(last, 1)} %"})
    table = [[k, y, round(100 * c, 1), round(100 * s_, 2)] for k, s in desc["year_series"].items() for y, c, s_ in s]
    last_year = next(iter(desc["year_series"].values()))[-1][0]
    return {"alt": "For each of the eight topics with a spending counterpart, the lowest and highest yearly concern "
                   "and the lowest and highest share of general government expenditure over the years of the spending "
                   "model, on a log scale: concern spans a wide range, spending shares a narrow one.",
            "panels": [{"h": 22 * len(cats) + 50,
                        "x": {"kind": "log", "domain": [0.15, 100], "ticks": [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100],
                              "fmt": {"dp": 1, "unit": " %"},
                              "tickLabels": {str(t): str(t) for t in [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100]},
                              "label": "per cent, log scale"},
                        "y": {"kind": "cat", "domain": cats},
                        "marks": [{"type": "range", "rows": [{**r, "mid": r["mid"]} for r in rows], "w": 5}]}],
            "legend": [{"label": "yearly concern, lowest to highest", "c": HELD},
                       {"label": "share of spending, lowest to highest", "c": CORAL},
                       {"label": f"dot: {last_year}", "c": "grey", "shape": "o"}],
            "table": {"cols": ["topic", "year", "concern C̄, %", "spending share, %"], "rows": table},
            "data": ["describe.json"]}


def static_spending(desc: dict, path: Path) -> None:
    items = list(desc["year_series"])
    f, ax = plt.subplots(figsize=(7.2, 0.5 * len(items) + 0.9))
    for i, k in enumerate(reversed(items)):
        rg = desc["ranges"][k]
        ax.plot([100 * v for v in rg["cbar"]], [i + 0.15] * 2, color=HELD, lw=4, solid_capstyle="round")
        ax.plot([100 * v for v in rg["s"]], [i - 0.15] * 2, color=CORAL, lw=4, solid_capstyle="round")
    ax.set_xscale("log")
    ax.set_xticks([0.2, 0.5, 1, 2, 5, 10, 20, 50, 100], ["0.2", "0.5", "1", "2", "5", "10", "20", "50", "100"])
    ax.set_yticks(range(len(items)), list(reversed(items)))
    ax.set_xlabel("per cent, log scale · blue: yearly concern · red: share of spending")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def described_topics(desc: dict) -> tuple[str, ...]:
    """The four topics whose item list never changed (no spell change, so no jump from a new wording) and whose
    concern ranged most widely, in points."""
    stable = [k for k, v in desc["spell_starts"].items() if not v]
    top = sorted(stable, key=lambda k: -(desc["ranges"][k]["c"][1] - desc["ranges"][k]["c"][0]))[:4]
    assert tuple(top) == DESCRIBED, top
    return tuple(top)


def attention_alt(desc: dict) -> str:
    ws, yr = desc["wave_series"], {w: v["start"][:4] for w, v in desc["waves"].items()}
    parts = []
    for k in DESCRIBED:
        s = ws[k]
        parts.append(f"{k}: concern from {pct(s[0][1])} % ({yr[str(s[0][0])]}) to {pct(s[-1][1])} % ({yr[str(s[-1][0])]}), "
                     f"between {pct(min(c for _, c, _ in s))} and {pct(max(c for _, c, _ in s))} %; attention from "
                     f"{pct(s[0][2], 1)} to {pct(s[-1][2], 1)} %, between {pct(min(a for _, _, a in s), 1)} and "
                     f"{pct(max(a for _, _, a in s), 1)} %")
    return ("Four panels per Eurobarometer wave, 2004–2025, with concern (share of respondents naming the topic) and "
            "attention (share of plenary words in the half year after the wave). " + ". ".join(parts) + ".")


def attention_chart(desc: dict) -> dict:
    when = {w: year_of(v["start"]) for w, v in desc["waves"].items()}
    top = max(max(c, a) for k in DESCRIBED for _, c, a in desc["wave_series"][k])
    hi = 10 * math.ceil(100 * top / 10)
    panels = []
    for k in DESCRIBED:
        s = desc["wave_series"][k]
        panels.append({"title": k, "h": 150,
                       "x": {"kind": "linear", "domain": [2004.5, 2025.5], "ticks": list(range(2005, 2026, 5)),
                             "fmt": {"dp": 0, "nogroup": True}, "tipLabels": {str(when[str(w)]): f"EB{w}" for w, _, _ in s}},
                       "y": {"kind": "linear", "domain": [0, hi], "ticks": list(range(0, hi + 1, 20)),
                             "fmt": {"dp": 0, "unit": " %"}},
                       "marks": [{"type": "line", "pts": [[when[str(w)], round(100 * c, 1)] for w, c, _ in s], "c": HELD,
                                  "name": "concern", "fmt": {"dp": 0, "unit": " %"}},
                                 {"type": "line", "pts": [[when[str(w)], round(100 * a, 1)] for w, _, a in s], "c": CORAL,
                                  "name": "attention", "fmt": {"dp": 1, "unit": " %"}}]})
    table = [[k, f"EB{w}", desc["waves"][str(w)]["start"], round(100 * c, 1), round(100 * a, 2)]
             for k, s in desc["wave_series"].items() for w, c, a in s]
    return {"alt": attention_alt(desc),
            "layout": "rows", "panels": panels,
            "legend": [{"label": "concern: share of respondents naming the topic", "c": HELD},
                       {"label": "attention: share of plenary words in the half year after the wave", "c": CORAL}],
            "table": {"cols": ["topic", "wave", "fieldwork start", "concern, %", "attention, %"], "rows": table},
            "data": ["describe.json"]}


def static_attention(desc: dict, path: Path) -> None:
    when = {w: year_of(v["start"]) for w, v in desc["waves"].items()}
    f, axs = plt.subplots(len(DESCRIBED), 1, figsize=(7.2, 1.6 * len(DESCRIBED) + 0.4), sharex=True)
    for ax, k in zip(axs, DESCRIBED):
        s = desc["wave_series"][k]
        x = [when[str(w)] for w, _, _ in s]
        ax.plot(x, [100 * c for _, c, _ in s], color=HELD, lw=1.8, label="concern")
        ax.plot(x, [100 * a for _, _, a in s], color=CORAL, lw=1.8, label="attention")
        ax.set_title(k, loc="left", fontsize=9)
        ax.set_ylabel("%")
    axs[0].legend(frameon=False, fontsize=8, loc="upper right")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def validation_chart(val: dict, bound: float) -> dict:
    topics = sorted(val["parlacap"]["by_topic"], key=lambda k: -val["parlacap"]["by_topic"][k]["f1"])
    pts = []
    for frame, name, c in (("parlacap", "ParlaCAP-CZ 2013–2023", HELD), ("psp_2004_2013", "psp.cz 2004–2013", "light")):
        for k in topics:
            b = val[frame]["by_topic"][k]
            pts.append({"x": b["f1"], "y": k, "c": c, "r": 5,
                        "tip": f"{k}, {name}: F1 {n(b['f1'], 2)}, precision {n(b['precision'], 2)}, recall "
                               f"{n(b['recall'], 2)}, word share {e(b['word_share_error'] * 100, 1)} points off"})
    return {"alt": "F1 of the topic classifier against the reference coding, per topic, on the ParlaCAP-CZ sample and "
                   "the psp.cz 2004–2013 sample, with the 0.60 line of the F1 check. Unemployment is lowest on "
                   "ParlaCAP-CZ.",
            "panels": [{"h": 28 * len(topics) + 40,
                        "x": {"kind": "linear", "domain": [0, 1], "ticks": [0, 0.2, 0.4, 0.6, 0.8, 1],
                              "fmt": {"dp": 1}, "label": "F1, weighted back to the corpus"},
                        "y": {"kind": "cat", "domain": topics},
                        "marks": [{"type": "rule", "axis": "x", "v": bound, "c": "grey", "dash": "dash",
                                   "label": "0.60 check"},
                                  {"type": "dots", "pts": pts}]}],
            "legend": [{"label": f"ParlaCAP-CZ, {val['parlacap']['speeches']} speeches", "c": HELD, "shape": "o"},
                       {"label": f"psp.cz 2004–2013, {val['psp_2004_2013']['speeches']} speeches", "c": "light", "shape": "o"}],
            "table": {"cols": ["topic", "sample", "precision", "recall", "F1", "word share error, points"],
                      "rows": [[k, fr, val[f]["by_topic"][k]["precision"], val[f]["by_topic"][k]["recall"],
                                val[f]["by_topic"][k]["f1"], round(100 * val[f]["by_topic"][k]["word_share_error"], 1)]
                               for k in topics for f, fr in (("parlacap", "ParlaCAP-CZ"), ("psp_2004_2013", "psp.cz"))]},
            "data": ["validation.json"]}


def static_validation(val: dict, path: Path, bound: float) -> None:
    topics = sorted(val["parlacap"]["by_topic"], key=lambda k: -val["parlacap"]["by_topic"][k]["f1"])
    f, ax = plt.subplots(figsize=(7.2, 0.3 * len(topics) + 0.9))
    ax.axvline(bound, color=GREY, lw=0.8, ls="--")
    for i, k in enumerate(reversed(topics)):
        ax.plot(val["psp_2004_2013"]["by_topic"][k]["f1"], i, "o", color=LIGHT, ms=7, mec="white")
        ax.plot(val["parlacap"]["by_topic"][k]["f1"], i, "o", color=HELD, ms=7, mec="white")
    ax.set_yticks(range(len(topics)), list(reversed(topics)))
    ax.set_xlim(0, 1)
    ax.set_xlabel("F1 · blue: ParlaCAP-CZ · grey: psp.cz 2004–2013 · dashed: 0.60")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


# ---------------------------------------------------------------- tables in the text

def tests_table(res: dict) -> str:
    p = res["primary"]
    ys = {c: res["data"][c]["years_q3"] for c in ("parlacap", "whole")}
    spec = [("Q1", "parlacap", "attention after concern", "ParlaCAP-CZ, 2013–2023"),
            ("Q1", "whole", "attention after concern", "whole series, 2004–2025"),
            ("Q1r", "parlacap", "concern after attention", "ParlaCAP-CZ, 2013–2023"),
            ("Q1r", "whole", "concern after attention", "whole series, 2004–2025"),
            ("Q2", "spending", "spending share after concern",
             f"{ys['whole'][0]}–{ys['whole'][-1]} (spending to {ys['whole'][-1] + 1})"),
            ("Q3", "parlacap", "attention minus spending", f"{ys['parlacap'][0]}–{ys['parlacap'][-1]}"),
            ("Q3", "whole", "attention minus spending", f"{ys['whole'][0]}–{ys['whole'][-1]}")]
    out = []

    def cell(x):
        if x is None:
            return '<td class="v">–</td>'
        return (f'<td class="v">{e(x["estimate"])} <small>{nb("90 % " + iv(x["used"]["90"]))}<br>'
                f'{nb(x["label"])}</small></td>')
    for q, corp, what, span in spec:
        b = p[corp][q]
        out.append(f"  <tr><td>{q} · {what}<br><small>{span}</small></td>{cell(b.get('static'))}{cell(b.get('dynamic'))}"
                   f'<td class="v"><b>{b["label"]}</b></td></tr>')
    q4 = res["q4"]["party_status"]
    for g, name in (("Coalition", "coalition MPs"), ("Opposition", "opposition MPs")):
        x = q4[g]
        out.append(f'  <tr><td>Q4 · {name}<br><small>ParlaCAP-CZ, 2013–2023</small></td>'
                   f'<td class="v">{e(x["estimate"])} <small>{nb("90 % " + iv(x["used"]["90"]))}<br>'
                   f'{nb(x["label_wild"])}</small></td><td class="v">–</td>'
                   f'<td class="v">{x["label_wild"]} by the code\'s rule <small>no registered label</small></td></tr>')
    return "\n".join(out)


CHECKS = [("speeches_instead_of_words", "speeches instead of words"), ("chair_kept", "chair's speeches kept"),
          ("mix_kept", "“Mix” speeches kept under their top topic"), ("window_one_year", "window of one year"),
          ("without_2020_2022", "without 2020–2022"), ("without_eb93_96", "without EB93–96 (interview mode)"),
          ("without_list_changes", "without waves in which an item list changed"),
          ("split_ballot_arm_b", "split-ballot arm B"), ("log_ols", "log model by OLS"),
          ("levels", "levels, as elasticity at the means"), ("weighted_mean_concern", "weighted by mean concern"),
          ("f1_at_least_0_60", "topics with F1 ≥ 0.60 only"), ("confusion_corrected", "attention corrected by the confusion matrix"),
          ("discretionary_topics", "discretionary topics only"),
          ("unemployment_and_old_age_dependency_controls", "unemployment and old-age dependency as controls"),
          ("spending_change_in_share", "spending as change in share, per mean share")]
COLS = [("parlacap", "Q1", "static"), ("parlacap", "Q1", "dynamic"), ("whole", "Q1", "static"),
        ("spending", "Q2", "static"), ("spending", "Q2", "dynamic")]


def check_entry(res: dict, corp: str, q: str, m: str, key: str) -> dict | None:
    """A check's estimate, 90 % interval and the §5 label, on the elasticity scale. The frozen code stores levels on
    the coefficient scale with an at-means conversion, and change in share as a coefficient with its mean share; both
    are put on the elasticity scale here and the rule applied to the converted interval (a reading aid, §6)."""
    c = res["checks"][corp].get(key)
    if c is None:
        return None
    x = c.get(m) if corp == "spending" else c.get(q, {}).get(m)
    if x is None or "estimate" not in x:
        return None
    if key == "levels":
        am = x["elasticity_at_means"]
        return {"est": am["estimate"], "ci90": am["wild"]["90"], "label": label(am["wild"]["90"], am["wild"]["95"])}
    if key == "spending_change_in_share":
        f = x["per_mean_share"] / x["estimate"]
        ci90, ci95 = [v * f for v in x["wild"]["90"]], [v * f for v in x["wild"]["95"]]
        return {"est": x["per_mean_share"], "ci90": ci90, "label": label(ci90, ci95)}
    return {"est": x["estimate"], "ci90": x["wild"]["90"], "label": x["label_wild"]}


def registered(res: dict, corp: str, q: str, m: str) -> dict:
    x = res["primary"][corp][q][m]
    return {"est": x["estimate"], "ci90": x["used"]["90"], "label": x["label"]}


def leave_range(res: dict, corp: str, q: str, m: str, kind: str) -> list[float] | None:
    c = res["checks"][corp]
    if corp == "spending":
        key = "leave_one_topic_out" if kind == "topic" else "leave_one_year_out"
        return c[key]["range"][m]
    key = "leave_one_topic_out" if kind == "topic" else "leave_one_wave_out"
    return c[key][q]["range"][m]


def checks_table(res: dict) -> str:
    def cell(x):
        if x is None:
            return '<td class="v">–</td>'
        return f'<td class="v">{e(x["est"])} <small>{nb(iv(x["ci90"]))}<br>{nb(x["label"])}</small></td>'
    out = ["  <tr><td><b>registered</b> <small>hull of both methods</small></td>"
           + "".join(cell(registered(res, *c)) for c in COLS) + "</tr>"]
    for key, lab in CHECKS:
        out.append(f"  <tr><td>{lab}</td>" + "".join(cell(check_entry(res, *c, key)) for c in COLS) + "</tr>")
    for kind, lab in (("topic", "leave one topic out, range"), ("wave", "leave one wave (year) out, range")):
        out.append(f"  <tr><td>{lab}</td>" + "".join(
            f'<td class="v">{nb(iv(leave_range(res, *c, kind)))}</td>' for c in COLS) + "</tr>")
    return "\n".join(out)


def differing(res: dict, col: tuple) -> list[str]:
    reg = registered(res, *col)["label"]
    out = []
    for key, lab in CHECKS:
        x = check_entry(res, *col, key)
        if x is not None and x["label"] != reg:
            out.append(f"{short(lab)} ({e(x['est'])}, {x['label']})")
    return out


def other_way(res: dict) -> dict:
    """Checks of Q1r and Q3 whose label is not underpowered (their registered label on both corpora)."""
    out = []
    names = dict(CHECKS)
    for corp, span in (("parlacap", "2013–2023"), ("whole", "2004–2025")):
        for key, lab in CHECKS:
            c = res["checks"][corp].get(key, {})
            for q in ("Q1r", "Q3"):
                for m, x in c.get(q, {}).items():
                    if isinstance(x, dict) and x.get("label_wild") not in (None, "underpowered") and key != "levels":
                        out.append(f"{'reverse' if q == 'Q1r' else 'difference'}, {m}, {span}, "
                                   f"{short(names[key])} ({e(x['estimate'])}, {x['label_wild']})")
    return out


def short(lab: str) -> str:
    return lab.split(" (")[0].split(",")[0]


def join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


# ---------------------------------------------------------------- the page

def number_refs(page: str) -> str:
    """[[key]] markers become citations numbered by first appearance; every reference in refs.html must be cited."""
    eb = json.loads((R / "priorities-eb-datasets.json").read_text(encoding="utf-8"))
    links = ", ".join(f'<a href="{eb["base"]}{i}">EB{w}</a>' for w, i in eb["datasets"].items())
    refs = render((HERE / "refs.html").read_text(encoding="utf-8"), {"eb_links": links})
    entries = dict(re.findall(r'<li data-key="([\w-]+)">(.*?)</li>', refs, flags=re.S))
    order = list(dict.fromkeys(re.findall(r"\[\[([\w-]+)\]\]", page)))
    assert set(order) <= set(entries), set(order) - set(entries)
    assert set(entries) <= set(order), f"uncited: {set(entries) - set(order)}"
    num = {k: i for i, k in enumerate(order, 1)}
    page = re.sub(r"\[\[([\w-]+)\]\]", lambda m: f'<sup class="cite"><a href="#r{num[m.group(1)]}">{num[m.group(1)]}</a></sup>', page)
    return page.replace("{{refs}}", "\n".join(f'<li id="r{num[k]}">{entries[k]}</li>' for k in order))


def main() -> None:
    j = results_reader("priorities")
    res, val, ovl, pw, data, desc = j("results"), j("validation"), j("overlap"), j("power"), j("data"), j("describe")
    desc["spell_starts"] = res["data"]["spell_starts"]
    A.mkdir(parents=True, exist_ok=True)
    for src in ("results", "validation", "describe"):
        shutil.copy(R / f"priorities-{src}.json", A / f"{src}.json")
    st = res["settings"]
    sesoi, maxw = st["sesoi"], st["max_width_90"]
    p = res["primary"]
    pc, wh, sp = p["parlacap"], p["whole"], p["spending"]["Q2"]
    q4 = res["q4"]["party_status"]
    gov = res["q4"]["government"]
    described_topics(desc)

    charts = {"estimates": estimates_chart(res, sesoi), "spending": spending_chart(desc),
              "attention": attention_chart(desc), "validation": validation_chart(val, 0.60)}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    static_estimates(res, A / "01-estimates.svg", sesoi)
    static_spending(desc, A / "02-spending.svg")
    static_attention(desc, A / "03-attention.svg")
    static_validation(val, A / "04-validation.svg", 0.60)

    # claims in the text and figure heads, checked against the numbers
    assert sp["label"] == "not supported" and all(abs(num(v)) <= sesoi for m in ("static", "dynamic") for v in sp[m]["used"]["90"])
    assert pc["Q1"]["label"] == "model-dependent" and pc["Q1"]["static"]["label"] == "positive, possibly small"
    assert pc["Q1"]["dynamic"]["label"] == "underpowered" and wh["Q1"]["label"] == "underpowered"
    wst = wh["Q1"]["static"]
    assert wst["used"]["90"][0] > 0 and wst["used"]["95"][0] > 0 and wst["used"]["90"][1] - wst["used"]["90"][0] > maxw
    assert all(x["label"] == "underpowered" for c in (pc, wh) for x in (c["Q1r"], c["Q3"]))
    assert q4["Coalition"]["label_wild"] == q4["Opposition"]["label_wild"] == "positive, possibly small"
    assert all(g["label_wild"] == "underpowered" for s in gov.values() for g in s.values())
    assert not any(x["label"] in ("supported", "positive, possibly small")
                   for key, _ in CHECKS for c in COLS[3:] for x in [check_entry(res, *c, key)] if x)
    assert res["diagnostics"]["irls_not_converged"] == 0
    dw = pc["Q1"]["dynamic"]["wild"]["90"]
    assert dw[1] - dw[0] > maxw  # the text says the bootstrap alone is already too wide
    rg = desc["ranges"]
    ws = desc["wave_series"]
    fac_c = [rg[k]["cbar"][1] / rg[k]["cbar"][0] for k in desc["year_series"]]
    fac_s = [rg[k]["s"][1] / rg[k]["s"][0] for k in desc["year_series"]]
    assert max(fac_s) < min(fac_c)  # the head says: every concern range is wider than any spending range
    att_ratio = {k: ws[k][-1][2] / ws[k][0][2] for k in ("Unemployment", "Crime")}
    assert all(0.5 <= r <= 2 for r in att_ratio.values())  # the head says: within a factor of two of 2004
    vp, vq = val["parlacap"]["by_topic"], val["psp_2004_2013"]["by_topic"]
    low_pc = [k for k, b in vp.items() if b["f1"] < 0.60]
    assert low_pc == ["Unemployment"]
    low_q = [k for k, b in vq.items() if b["f1"] < 0.60]
    terms = data["attention"]["by_term"]
    q2_years = sp["static"]["periods"]
    grid = pw["grid"]
    w18 = [g["median_width_90"] for g in grid if g["waves"] == 18 and g["noise"] == 0.2]
    w41 = [g["median_width_90"] for g in grid if g["waves"] == 41 and g["noise"] == 0.2]
    w18h = [g["median_width_90"] for g in grid if g["waves"] == 18 and g["noise"] == 0.4]
    s_checks = [check_entry(res, *c, key) for key, _ in CHECKS for c in COLS[3:]]
    s_checks = [x for x in s_checks if x]
    q2_hi = max(x["ci90"][1] for x in s_checks)
    diff_q1 = differing(res, COLS[0])
    diff_q2s, diff_q2d = differing(res, COLS[3]), differing(res, COLS[4])
    diff_wh = differing(res, COLS[2])
    diff_q1d = [f"{short(lab)} ({e(x['est'])}, {x['label']})" for key, lab in CHECKS
                for x in [check_entry(res, *COLS[1], key)] if x and x["label"] != "underpowered"]
    d1 = [x for key, _ in CHECKS for x in [check_entry(res, *COLS[0], key)]
          if x and x["label"] != pc["Q1"]["static"]["label"] and key != "without_2020_2022"]
    assert all(x["est"] > 0 for x in d1)
    disc = res["checks"]["spending"]["discretionary_topics"]
    ctrl = res["checks"]["spending"]["unemployment_and_old_age_dependency_controls"]
    assert all(c[m]["label_wild"] == sp["label"] for c in (disc, ctrl) for m in ("static", "dynamic"))
    q4c, q4o = q4["Coalition"], q4["Opposition"]
    wo = check_entry(res, "parlacap", "Q1", "static", "without_2020_2022")
    wwo = check_entry(res, "whole", "Q1", "static", "without_2020_2022")
    wo_n = len(res["checks"]["parlacap"]["without_2020_2022"]["Q1"]["static"]["periods"])
    wwo_n = len(res["checks"]["whole"]["without_2020_2022"]["Q1"]["static"]["periods"])
    assert wo["ci90"][0] < 0 and wwo["ci90"][0] < 0 and wwo["label"] == "underpowered"  # "cannot be told apart from zero"
    q2wo = check_entry(res, "spending", "Q2", "static", "without_2020_2022")
    assert q2wo["ci90"][1] > sesoi  # "can no longer exclude 0.10"
    design = (R / "priorities-design.md").read_text(encoding="utf-8")
    size = re.search(r"wild bootstrap alone rejecting ([\d.]+)–([\d.]+) % at a nominal 10 %", design)
    un, cr = ws["Unemployment"], ws["Crime"]
    nref_q = [b["n_reference"] for b in vq.values()]
    assert un[-1][2] < un[0][2] and cr[-1][2] > cr[0][2] and vq["Crime"]["word_share_error"] > 0  # "fell", "rose", "over-counts"
    assert vq["Crime"]["f1"] < vq["Pensions"]["f1"]
    lo_topic = max(desc["year_series"], key=lambda k: rg[k]["cbar"][1] / rg[k]["cbar"][0])

    v = {
        "sesoi": n(sesoi, 2), "sesoi1": n(sesoi, 1), "maxw": n(maxw, 2), "draws": n(st["bootstrap_draws"]),
        "perms": n(st["permutations"]), "window": st["window_days"], "coverage": pct(st["coverage"]),
        # data
        "n_waves_all": data["concern"]["n_waves"], "wave_first": min(data["concern"]["waves_read"]),
        "wave_last": max(data["concern"]["waves_read"]),
        "pc_speeches": n(data["attention"]["rows"]), "pc_kept": n(sum(t["kept"]["speeches"] for t in terms.values())),
        "pc_kept_words": n(sum(t["kept"]["words"] for t in terms.values()) / 1e6, 1),
        "pc_waves": len(res["data"]["parlacap"]["waves"]), "wh_waves": len(res["data"]["whole"]["waves"]),
        "pc_w0": min(res["data"]["parlacap"]["waves"]), "pc_w1": max(res["data"]["parlacap"]["waves"]),
        "wh_w0": min(res["data"]["whole"]["waves"]), "wh_w1": max(res["data"]["whole"]["waves"]),
        "q2_y0": min(q2_years), "q2_y1": max(q2_years), "q2_y2": max(q2_years) + 1,
        "q2_topics": sp["static"]["topics"],
        "q2_topics_w": {8: "eight", 10: "ten"}[sp["static"]["topics"]], "ovl": pct(ovl["label_agreement"], 2), "ovl_n": n(ovl["matched"]),
        # validation
        "val_n": val["coders"]["of"], "val_agree": val["coders"]["agree"],
        "val_raw": pct(val["coders"]["raw_agreement"], 1), "val_w": pct(val["coders"]["weighted_agreement"], 1),
        "adj_all": val["adjudicated"]["author"] + val["adjudicated"]["assistant"],
        "adj_author": val["adjudicated"]["author"], "adj_asst": val["adjudicated"]["assistant"],
        "adj_match": val["author_adjudicated_only"]["classifier_label_equals_author"],
        "f1_pc": n(val["parlacap"]["macro_f1"], 2), "f1_psp": n(val["psp_2004_2013"]["macro_f1"], 2),
        "f1_bound": n(val["bound_macro_f1"], 2), "val_pc_n": val["parlacap"]["speeches"],
        "val_psp_n": val["psp_2004_2013"]["speeches"],
        "f1_unemp": n(vp["Unemployment"]["f1"], 2), "rec_unemp": n(vp["Unemployment"]["recall"], 2),
        "f1_unemp_q": n(vq["Unemployment"]["f1"], 2),
        "f1_pens": n(vp["Pensions"]["f1"], 2), "rec_pens": n(vp["Pensions"]["recall"], 2),
        "rec_pens_q": n(vq["Pensions"]["recall"], 2),
        "ws_pens": half_up(-round(100 * vp["Pensions"]["word_share_error"], 6)),
        "ws_pens_q": half_up(-round(100 * vq["Pensions"]["word_share_error"], 6)),
        "n_ok_pc": sum(b["f1"] >= 0.60 for b in vp.values()), "n_topics": len(vp),
        "low_q": join(low_q), "n_low_q": len(low_q),
        # power
        "pw18_lo": n(min(w18), 2), "pw18_hi": n(max(w18), 2), "pw41": n(max(w41), 2),
        "pw18h_lo": n(min(w18h), 2), "pw18h_hi": n(max(w18h), 2),
        # Q2
        "q2s": e(sp["static"]["estimate"]), "q2s_90": iv(sp["static"]["used"]["90"]), "q2s_95": iv(sp["static"]["used"]["95"]),
        "q2d": e(sp["dynamic"]["estimate"]), "q2d_90": iv(sp["dynamic"]["used"]["90"]), "q2d_95": iv(sp["dynamic"]["used"]["95"]),
        "q2s_hi_pct": n(10 * sp["static"]["used"]["90"][1], 1), "q2_label": sp["label"],
        "q2_hi_check": e(q2_hi),
        "fac_c_lo": n(min(fac_c), 0), "fac_c_hi": n(max(fac_c), 0), "fac_s_lo": n(min(fac_s), 1), "fac_s_hi": n(max(fac_s), 1),
        "lt_q2s": between(leave_range(res, "spending", "Q2", "static", "topic")),
        "ly_q2s": between(leave_range(res, "spending", "Q2", "static", "wave")),
        "lt_q2d": iv(leave_range(res, "spending", "Q2", "dynamic", "topic")),
        # Q1
        "q1s": e(pc["Q1"]["static"]["estimate"]), "q1s_90": iv(pc["Q1"]["static"]["used"]["90"]),
        "q1s_95": iv(pc["Q1"]["static"]["used"]["95"]), "q1s_lab": pc["Q1"]["static"]["label"],
        "q1d": e(pc["Q1"]["dynamic"]["estimate"]), "q1d_90": iv(pc["Q1"]["dynamic"]["used"]["90"]),
        "q1d_w": n(num(pc["Q1"]["dynamic"]["used"]["90"][1]) - num(pc["Q1"]["dynamic"]["used"]["90"][0]), 2),
        "q1d_wild": iv(pc["Q1"]["dynamic"]["wild"]["90"]),
        "q1d_wild_w": n(pc["Q1"]["dynamic"]["wild"]["90"][1] - pc["Q1"]["dynamic"]["wild"]["90"][0], 2), "q1d_lab": pc["Q1"]["dynamic"]["label"],
        "q1d_unc": e(pc["Q1"]["dynamic"]["uncorrected"]),
        "q1_lab": pc["Q1"]["label"],
        "w1s": e(wst["estimate"]), "w1s_90": iv(wst["used"]["90"]), "w1s_95": iv(wst["used"]["95"]),
        "w1s_w": n(wst["used"]["90"][1] - wst["used"]["90"][0], 2),
        "w1d": e(wh["Q1"]["dynamic"]["estimate"]), "w1d_90": iv(wh["Q1"]["dynamic"]["used"]["90"]),
        "w1d_unc": e(wh["Q1"]["dynamic"]["uncorrected"]), "w1_lab": wh["Q1"]["label"],
        "q1rs": e(pc["Q1r"]["static"]["estimate"]), "q1rs_90": iv(pc["Q1r"]["static"]["used"]["90"]),
        "q1rd": e(pc["Q1r"]["dynamic"]["estimate"]),
        "w1rs": e(wh["Q1r"]["static"]["estimate"]), "w1rs_90": iv(wh["Q1r"]["static"]["used"]["90"]),
        "w1rd": e(wh["Q1r"]["dynamic"]["estimate"]),
        "q3p": e(pc["Q3"]["dynamic"]["estimate"]), "q3p_90": iv(pc["Q3"]["dynamic"]["used"]["90"]),
        "q3w": e(wh["Q3"]["dynamic"]["estimate"]), "q3w_90": iv(wh["Q3"]["dynamic"]["used"]["90"]),
        "q3p_att": e(pc["Q3"]["dynamic"]["components"][0]["estimate"]),
        "q3w_att": e(wh["Q3"]["dynamic"]["components"][0]["estimate"]),
        "q1_rows": pc["Q1"]["static"]["n"], "w1_rows": wst["n"],
        "lt_q1s": between(leave_range(res, "parlacap", "Q1", "static", "topic")),
        "lw_q1s": between(leave_range(res, "parlacap", "Q1", "static", "wave")),
        "wo_est": e(wo["est"]), "wo_90": iv(wo["ci90"]), "wo_lab": wo["label"],
        # Q4
        "q4c": e(q4c["estimate"]), "q4c_90": iv(q4c["used"]["90"]), "q4c_95": iv(q4c["used"]["95"]),
        "q4o": e(q4o["estimate"]), "q4o_90": iv(q4o["used"]["90"]), "q4o_95": iv(q4o["used"]["95"]),
        "q4_lab": q4c["label_wild"], "q4_gap": n(abs(q4c["estimate"] - q4o["estimate"]), 2),
        **{f"g_{k}_{c}": e(gov[c][k]["estimate"]) for c in gov for k in gov[c]},
        **{f"gn_{k}_{c}": len(gov[c][k]["periods"]) for c in gov for k in gov[c]},
        # checks
        "diff_q1": join(diff_q1) if diff_q1 else "none", "n_diff_q1": len(diff_q1),
        "diff_q2s": join(diff_q2s) if diff_q2s else "none", "diff_q2d": join(diff_q2d) if diff_q2d else "none",
        "diff_wh": join(diff_wh) if diff_wh else "none",
        "diff_q1d": join(diff_q1d) if diff_q1d else "none",
        "diff_q1_lo": e(min(x["est"] for x in d1)), "diff_q1_hi": e(max(x["est"] for x in d1)),
        "other_way": join(other_way(res)) or "none",
        "checks_table": checks_table(res), "tests_table": tests_table(res),
        # descriptive
        "un_c0": pct(ws["Unemployment"][0][1]), "un_c1": pct(ws["Unemployment"][-1][1]),
        "cr_c0": pct(ws["Crime"][0][1]), "cr_c1": pct(ws["Crime"][-1][1]),
        "un_a0": pct(ws["Unemployment"][0][2], 1), "un_a1": pct(ws["Unemployment"][-1][2], 1),
        "cr_a0": pct(ws["Crime"][0][2], 1), "cr_a1": pct(ws["Crime"][-1][2], 1),
        "im_cmax": pct(rg["Immigration"]["c"][1]), "im_amax": pct(rg["Immigration"]["a"][1], 1),
        "im_wmax": next(w for w, c, _ in ws["Immigration"] if c == rg["Immigration"]["c"][1]),
        "im_wamax": next(w for w, _, a in ws["Immigration"] if a == rg["Immigration"]["a"][1]),
        "ws_last": ws["Unemployment"][-1][0], "ws_first": ws["Unemployment"][0][0],
        "econ_cmax": pct(rg["Economy"]["c"][1]),
        "im_year": desc["waves"][str(next(w for w, c, _ in ws["Immigration"] if c == rg["Immigration"]["c"][1]))]["start"][:4],
        "wo_n": wo_n, "wwo_n": wwo_n, "wwo_est": e(wwo["est"]), "wwo_90": iv(wwo["ci90"]),
        "q2_wo": e(q2wo["est"]), "q2_wo_hi": e(q2wo["ci90"][1]),
        "n_q2_inc": sum(x["label"] == "inconclusive" for x in s_checks),
        "n_q2_inc_w": ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][
            sum(x["label"] == "inconclusive" for x in s_checks)],
        "size_lo": size.group(1), "size_hi": size.group(2),
        "pw_sims": pw["settings"]["sims"], "pw_boot": pw["settings"]["boot"],
        "fac_c_low": pct(rg[lo_topic]["cbar"][0]),
        "un_ach": pct(abs(un[-1][2] / un[0][2] - 1)), "cr_ach": pct(cr[-1][2] / cr[0][2] - 1),
        "cr_cfac": n(cr[0][1] / cr[-1][1], 0),
        "cr_ws_q": n(100 * vq["Crime"]["word_share_error"], 1), "cr_f1_q": n(vq["Crime"]["f1"], 2),
        "cr_nref_q": vq["Crime"]["n_reference"], "q_nref_lo": min(nref_q), "q_nref_hi": max(nref_q),
        "pens_f1_q": n(vq["Pensions"]["f1"], 2), "alt3": attention_alt(desc),
        "q2_chk_lo": e(min(x["est"] for x in s_checks)), "q2_chk_hi": e(max(x["est"] for x in s_checks)),
    }
    page = number_refs(render((HERE / "template.html").read_text(encoding="utf-8"), v | {"refs": "{{refs}}"}))
    (ROOT / "texts" / f"{SLUG}.html").write_text(page, encoding="utf-8")
    print(json.dumps({k: x for k, x in v.items() if not k.endswith("table")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
