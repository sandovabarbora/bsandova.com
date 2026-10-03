"""Chart specs for the council article (texts/prague-council.html), read by assets/charts.js.

Every number comes from the files the static figures are drawn from (tools/zhmp/figures.py and
figures_extended.py), recomputed the same way: assets/zhmp/votes2022.json (figs 1–2), assets/zhmp/terms.json
(fig 3) and assets/zhmp/council_extended.json (figs 4–7). Writes assets/zhmp/charts-council.json.

    python3 tools/charts/prague_council.py
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"
V = json.loads((A / "zhmp/votes2022.json").read_text())
T = json.loads((A / "zhmp/terms.json").read_text())
O = json.loads((A / "zhmp/council_extended.json").read_text())

HELD = "#a8201a"  # the red of the article's photograph, as in tools/zhmp/figures.py
COALITION = {"SPOLU", "Piráti", "STAN"}
NB = " "
DV, DT, DO = "assets/zhmp/votes2022.json", "assets/zhmp/terms.json", "assets/zhmp/council_extended.json"


def n(v: float, dp: int = 0, unit: str = "") -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "") + s + unit


def pct(v: float, dp: int = 0) -> str:
    return n(v, dp, " %")


def wavg(xs: list[float], ws: list[float]) -> float:
    return sum(x * w for x, w in zip(xs, ws)) / sum(ws)


charts = {}
NVOTES = V["checks"]["votes"]

# fig. 1 · same side as SPOLU
rows = sorted(((c, a) for c, a in V["agreement"]["SPOLU"].items() if c != "SPOLU"), key=lambda r: -r[1])
lab = lambda c: f"{c}{' (coalition)' if c in COALITION else ''}"  # noqa: E731
colour = lambda c: "ink" if c in COALITION else (HELD if c == "Praha sobě" else "light")  # noqa: E731
charts["with-spolu"] = {
    "alt": "Horizontal bars: share of votes on which each club took the same side as SPOLU. STAN 98 %, Pirates 97 %, Praha sobě 88 %, ANO 64 %, SPD 52 %, the non-affiliated member 49 %.",
    "legend": [{"label": "coalition", "c": "ink", "shape": "box", "o": 0.85}, {"label": "Praha sobě, in opposition", "c": HELD, "shape": "box", "o": 0.85},
               {"label": "rest of the opposition, non-affiliated", "c": "light", "shape": "box", "o": 0.85}],
    "panels": [{"h": 240, "x": {"kind": "linear", "domain": [0, 108], "ticks": [0, 25, 50, 75, 100], "label": "votes on which the club took the same side as SPOLU (%)", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": [lab(c) for c, _ in rows]},
                "marks": [{"type": "hbar", "rows": [{"y": lab(c), "x1": round(100 * a, 1), "c": colour(c), "label": pct(100 * a),
                                                     "tip": f"{lab(c)}\n{pct(100 * a, 1)} of {n(NVOTES)} votes on the same side as SPOLU"} for c, a in rows]}]}],
    "table": {"cols": ["club", "same side as SPOLU (%)"], "rows": [[lab(c), f"{100 * a:.1f}"] for c, a in rows]},
    "data": [DV],
}

# fig. 2 · the opposition by quarter, from 2023
q = {k: x for k, x in V["agreement_with_spolu_by_quarter"].items() if k >= "2023Q1"}
qx = lambda k: int(k[:4]) + (int(k[5]) - 1) / 4  # noqa: E731
qlab = lambda k: f"{k[:4]} Q{k[5]}"  # noqa: E731
series = [("Praha sobě", HELD, None, 2.2), ("ANO", "ink", "dash", 1.6), ("SPD", "light", None, 1.8)]
last = list(q)[-1]
m2 = []
for c, cc, dash, w in series:
    m2.append({"type": "line", "name": c, "c": cc, "dash": dash, "w": w, "notip": True, "pts": [[qx(k), round(100 * x[c], 1)] for k, x in q.items()]})
for c, cc, dash, w in series:
    m2.append({"type": "dots", "c": cc, "r": 3, "pts": [{"x": qx(k), "y": round(100 * x[c], 1),
                                                          "tip": f"{c}, {qlab(k)}\n{pct(100 * x[c])} on the same side as SPOLU\n{n(x['votes'])} votes in the quarter"} for k, x in q.items()]})
for c, cc, dash, w in series:
    m2.append({"type": "text", "x": qx(last) + 0.12, "y": 100 * q[last][c] - 1.5, "s": c, "c": "grey" if cc == "light" else cc})
charts["opposition-by-quarter"] = {
    "alt": "Lines by quarter, 2023 to 2026: share of votes on the same side as SPOLU for Praha sobě (mostly 85–95 %, dips to 59 % and 68 %), ANO (43–87 %) and SPD (6–88 %).",
    "legend": [{"label": c, "c": cc, "dash": dash} for c, cc, dash, _ in series],
    "panels": [{"h": 280, "padRight": 70, "x": {"kind": "linear", "domain": [2022.9, qx(last) + 0.1], "ticks": [2023, 2024, 2025, 2026], "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [0, 105], "ticks": [0, 20, 40, 60, 80, 100], "label": "same side as SPOLU (%)", "tickfmt": {"dp": 0}},
                "marks": m2}],
    "table": {"cols": ["quarter", "votes", "Praha sobě (%)", "ANO (%)", "SPD (%)"],
              "rows": [[qlab(k), n(x["votes"])] + [f"{100 * x[c]:.1f}" for c, *_ in series] for k, x in q.items()]},
    "data": [DV],
}

# fig. 3 · against, abstained, pressed nothing, four terms
names = list(T)
short = lambda t: t[2:4] + "–" + t[7:9]  # noqa: E731
panels3 = []
for i, (title, key, cc) in enumerate([("against", "against_per_100_present", HELD), ("abstained", "abstain_per_100_present", "ink"),
                                      ("pressed nothing", "no_vote_per_100_present", "light")]):
    ys = [T[t]["passed"][key] for t in names]
    top = max(ys) * 1.25
    panels3.append({"h": 220, "title": title, "x": {"kind": "cat", "domain": [short(t) for t in names]},
                    "y": {"kind": "linear", "domain": [0, top], "label": "per 100 members present" if i == 0 else None},
                    "marks": [{"type": "vbar", "c": cc, "rows": [{"x": short(t), "y1": y, "label": f"{y:.1f}",
                                                                  "tip": f"{t.replace('-', '–')} · {title}\n{y:.2f} per 100 members present\n{n(T[t]['passed']['votes'])} passed votes"}
                                                                 for t, y in zip(names, ys)]}]})
    if i:
        panels3[-1]["y"].pop("label")
charts["dissent-by-term"] = {
    "alt": "Three bar charts across four terms, per 100 members present on passed votes: against 1.1, 0.6, 0.3, 0.3; abstained 5.0, 5.6, 0.8, 0.9; pressed nothing 12.0, 15.2, 17.0, 17.9.",
    "panels": panels3,
    "table": {"cols": ["term", "passed votes", "against", "abstained", "pressed nothing"],
              "rows": [[t.replace("-", "–"), n(T[t]["passed"]["votes"])] + [f"{T[t]['passed'][k]:.2f}" for k in
                                                                           ("against_per_100_present", "abstain_per_100_present", "no_vote_per_100_present")] for t in names]},
    "data": [DT],
}

# fig. 4 · within-person change, log scale
pairs = O["H1"]["by_pair"]
labs = {"2010->2014": "2010–14 → 2014–18", "2014->2018": "2014–18 → 2018–22", "2018->2022": "2018–22 → 2022–26"}
pooled = O["H1"]["ratio_per_term"]
r4 = []
for k, lb in labs.items():
    p = pairs[k]
    lo, hi, mid = (math.exp(x) for x in (*p["ci95"], p["mean"]))
    r4.append({"y": lb, "lo": round(lo, 4), "hi": round(hi, 4), "mid": round(mid, 4),
               "tip": f"{labs[k]}\n{p['n']} councillors\n× {mid:.2f} their earlier rate of voting against\n95 %: × {lo:.2f} to × {hi:.2f}"})
charts["within"] = {
    "alt": "Three horizontal intervals on a log scale. 2010–14 to 2014–18: the same 21 councillors voted against at 0.20 times their earlier rate. 2014–18 to 2018–22: 20 councillors, 0.96 times, interval crossing 1. 2018–22 to 2022–26: 32 councillors, 0.65 times. Pooled: 0.49.",
    "panels": [{"h": 200, "x": {"kind": "log", "domain": [0.09, 2.3], "ticks": [0.1, 0.25, 0.5, 1, 2],
                                "tickLabels": {"0.1": "× 0.1", "0.25": "× 0.25", "0.5": "× 0.5", "1": "× 1", "2": "× 2"},
                                "label": "votes against, next term vs this one (95 % interval)"},
                "y": {"kind": "cat", "domain": [r["y"] for r in r4]},
                "marks": [{"type": "rule", "axis": "x", "v": 1, "c": "grey", "w": 0.8},
                          {"type": "rule", "axis": "x", "v": pooled, "c": "ink", "dash": "dash", "label": f"all: × {pooled:.2f}",
                           "tip": f"all transitions pooled\n× {pooled:.2f} per term\n{O['H1']['persons']} people, {O['H1']['transitions']} pairs of terms"},
                          {"type": "range", "c": HELD, "w": 2, "rows": r4}]
                + [{"type": "text", "x": 2.25, "y": r["y"], "s": f"{pairs[k]['n']} people", "anchor": "end", "c": "grey"} for k, r in zip(labs, r4)]}],
    "table": {"cols": ["terms", "councillors", "ratio", "95 % interval"],
              "rows": [[labs[k], str(pairs[k]["n"]), f"{r['mid']:.2f}", f"{r['lo']:.2f}–{r['hi']:.2f}"] for k, r in zip(labs, r4)]
              + [["all, pooled", str(O["H1"]["persons"]), f"{pooled:.2f}", ""]]},
    "data": [DO],
}

# fig. 5 · yes share in the coalition and in opposition, weighted by votes, interregna left out
lists = ["Praha sobě", "ANO", "TOP 09", "ODS", "ČSSD", "Piráti"]
rq = [r for r in O["RQ5"] if r["status"] != "interregnum"]
roles = {}
for lst in lists:
    for st in ("coalition", "opposition"):
        h = [r for r in rq if r["list"] == lst and r["status"] == st]
        if h:
            roles[lst, st] = (wavg([r["yes_share"] for r in h], [r["votes"] for r in h]), sum(r["votes"] for r in h))
conn, pts5 = [], []
for lst in lists:
    c, o = roles.get((lst, "coalition")), roles.get((lst, "opposition"))
    if c and o:
        conn.append({"y": lst, "lo": round(100 * min(c[0], o[0]), 2), "hi": round(100 * max(c[0], o[0]), 2), "mid": round(100 * c[0], 2), "c": "ink",
                     "tip": f"{lst}\nin the coalition {pct(100 * c[0])}\nin opposition {pct(100 * o[0])}\n{n(100 * (c[0] - o[0]))} points apart"})
    for st, cc in (("coalition", HELD), ("opposition", "light")):
        if (lst, st) in roles:
            y, nv = roles[lst, st]
            pts5.append({"y": lst, "mid": round(100 * y, 2), "c": cc, "tip": f"{lst}, in {'the coalition' if st == 'coalition' else 'opposition'}\n{pct(100 * y)} of present members voted yes\n{n(nv)} votes"})
charts["roles"] = {
    "alt": "Dot chart for six lists: share of present members voting yes while in the coalition (red) and in opposition (grey). Praha sobě 95 and 77 %. ANO 95 and 59 %. TOP 09 91 and 47 %. ODS 87 and 58 %. ČSSD 97 and 79 %. Pirates 94 and 69 %.",
    "legend": [{"label": "while in the coalition", "c": HELD, "shape": "o"}, {"label": "in opposition", "c": "light", "shape": "o"}],
    "panels": [{"h": 250, "x": {"kind": "linear", "domain": [40, 100], "ticks": [40, 50, 60, 70, 80, 90, 100], "label": "share of present members voting yes, %", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": lists},
                "marks": [{"type": "range", "w": 1, "rows": conn}, {"type": "range", "rows": pts5}]}],
    "table": {"cols": ["list", "coalition, yes (%)", "coalition, votes", "opposition, yes (%)", "opposition, votes"],
              "rows": [[lst] + sum(([f"{100 * roles[lst, st][0]:.1f}", n(roles[lst, st][1])] if (lst, st) in roles else ["", ""]
                                    for st in ("coalition", "opposition")), []) for lst in lists]},
    "data": [DO],
}

# fig. 6 · who says no on contested votes
panels6, rows6 = [], []
for term, title in (("2018", "2018–22"), ("2022", "2022–26 (from Feb 2023)")):
    mc = O["H3_minority_clubs"][term]
    top = mc["top"][:5]
    hb = []
    for t in top:
        lb = t["clubs_not_yes"].replace("(no club; scattered)", "no club as a whole")
        s = 100 * t["share"]
        hb.append({"y": lb, "x1": round(s, 2), "c": "light" if "no club" in lb else HELD, "label": pct(s, 0 if s >= 10 else 1),
                   "tip": f"{title} · {lb}\n{pct(s, 1)} of {n(mc['contested'])} contested votes\n{n(t['votes'])} votes"})
        rows6.append([title, lb, n(t["votes"]), f"{s:.1f}"])
    panels6.append({"h": 210, "title": title, "x": {"kind": "linear", "domain": [0, 55], "ticks": [0, 10, 20, 30, 40, 50], "label": "% of contested votes", "fmt": {"dp": 0}},
                    "y": {"kind": "cat", "domain": [r["y"] for r in hb]}, "marks": [{"type": "hbar", "rows": hb}]})
charts["who-says-no"] = {
    "alt": "Two bar charts of contested votes by which clubs had a majority not voting yes. 2018–22: no club as a whole 49 %, ODS alone 23 %, ANO and ODS 15 %, ANO alone 12 %. 2022–26: no club as a whole 42 %, SPD alone 20 %, ANO and SPD 17 %, ANO alone 11 %, Praha sobě 2.5 %.",
    "legend": [{"label": "one or more clubs had a majority not voting yes", "c": HELD, "shape": "box", "o": 0.85}, {"label": "no club as a whole; the minority was scattered", "c": "light", "shape": "box", "o": 0.85}],
    "panels": panels6,
    "table": {"cols": ["term", "clubs with a majority not voting yes", "votes", "% of contested"], "rows": rows6},
    "data": [DO],
}

# fig. 7 · abstentions per sitting
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def dyear(s: str) -> float:
    d = datetime.fromisoformat(s)
    y0, y1 = datetime(d.year, 1, 1), datetime(d.year + 1, 1, 1)
    return d.year + (d - y0).total_seconds() / (y1 - y0).total_seconds()


def dlab(s: str) -> str:
    d = datetime.fromisoformat(s)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


ser = O["H2"]["series"]  # one sitting (24 Mar 2011) has no abstentions and no pressed-nothing: 0/0, left out of the plot as matplotlib does
charts["abstain-sittings"] = {
    "alt": "Scatter of sittings from 2010 to 2026: abstentions as a share of abstentions plus pressing nothing. Around 20 to 60 % in 2010–2018 with a downward drift in each term, falling to mostly under 10 % from late 2018, with a few sittings higher, and near zero by 2026. Dashed lines mark the term boundaries; a solid line marks October 2020.",
    "legend": [{"label": "sitting", "c": HELD, "shape": "o"}, {"label": "new term", "c": "grey", "dash": "dash"}, {"label": "file changes how it counts 'present'", "c": "ink"}],
    "panels": [{"h": 280, "x": {"kind": "linear", "domain": [2010.5, 2026.9], "ticks": [2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026], "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [0, 100], "ticks": [0, 20, 40, 60, 80, 100], "label": "abstentions, % of abstain + pressed nothing", "tickfmt": {"dp": 0}},
                "marks": [{"type": "rule", "axis": "x", "v": round(dyear(d), 4), "c": "grey", "w": 0.8, "dash": "dash"} for d in ("2014-11-01", "2018-11-01", "2022-11-01")]
                + [{"type": "rule", "axis": "x", "v": round(dyear("2020-10-15"), 4), "c": "ink", "w": 0.8,
                    "tip": "15 Oct 2020\nthe open data changes how it counts 'present'"},
                   {"type": "dots", "c": HELD, "r": 3, "pts": [{"x": round(dyear(s["t"]), 4), "y": round(100 * s["share"], 2),
                                                                "tip": f"sitting of {dlab(s['t'])}\nabstentions {pct(100 * s['share'])} of the two\n{n(s['ab'])} abstained, {n(s['nh'])} pressed nothing"}
                                                               for s in ser if not math.isnan(s["share"])]}]}],
    "table": {"cols": ["sitting", "term", "abstained", "pressed nothing", "abstentions (%)"],
              "rows": [[s["t"][:10], f"{s['term']}–{int(s['term']) + 4}", n(s["ab"]), n(s["nh"]), "–" if math.isnan(s["share"]) else f"{100 * s['share']:.1f}"] for s in ser]},
    "data": [DO],
}

# data links are relative to the article (texts/)
for spec in charts.values():
    spec["data"] = ["../" + p for p in spec["data"]]
out = A / "zhmp/charts-council.json"
out.write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
print(len(charts), "charts →", out)
