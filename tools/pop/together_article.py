"""Pop, measured, part 6: chart specs, static figures and the article, every number read from the results.

Reads docs/research/pop-measured-part6-results.json, -panel.csv and -tickets.csv; writes assets/pop/together/
(charts.json, five static SVGs, the published CSVs) and texts/pop-together.html from tools/pop/templates/together.html.

    uv run --with matplotlib --with pandas --with numpy python tools/pop/together_article.py
"""

from __future__ import annotations

import json
import math
import re
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "pop" / "together"
HELD, INK, GREY, LIGHT = "#34507c", "#111111", "#666666", "#b5b5b0"
NAME = {"harry-styles": "Harry Styles", "taylor-swift": "Taylor Swift", "bts": "BTS", "bad-bunny": "Bad Bunny",
        "billie-eilish": "Billie Eilish"}
COL = {"harry-styles": "#34507c", "taylor-swift": "#b5651d", "bts": "#7b5ea7", "bad-bunny": "#2f7d4f", "billie-eilish": "#111111"}
NB = " "
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})


def n(v: float, dp: int = 0) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 and round(abs(v), dp) else "") + s


def pct(v: float, dp: int = 0) -> str:
    return f"{'+' if v > 0 else ''}{n(100 * v, dp)} %"


def figures(res: dict) -> None:
    A.mkdir(parents=True, exist_ok=True)
    for f in ("panel", "tickets", "results"):
        src = R / f"pop-measured-part6-{f}.{'json' if f == 'results' else 'csv'}"
        shutil.copy(src, A / src.name.replace("pop-measured-part6-", ""))
    m1, m1b = res["m1"], res["m1b"]
    lang = [("all three languages", m1["coef"], m1["lo"], m1["hi"], "held"),
            ("English songs", m1b["en"]["coef"], m1b["en"]["lo"], m1b["en"]["hi"], "ink"),
            ("Spanish songs", m1b["es"]["coef"], m1b["es"]["lo"], m1b["es"]["hi"], "ink"),
            ("Korean song (one country)", m1b["ko"]["coef"], m1b["ko"]["lo"], m1b["ko"]["hi"], "light")]
    charts = {"language": {
        "alt": "How many times as long a song lasted in a country speaking its language, with 95 % intervals: all languages, English, Spanish, Korean.",
        "panels": [{"h": 150, "x": {"kind": "log", "domain": [0.8, 10], "ticks": [1, 2, 3, 5, 8], "fmt": {"dp": 1, "unit": "×"},
                                    "label": "days in the chart, same language against other languages (log scale)"},
                    "y": {"kind": "cat", "domain": [l[0] for l in lang]},
                    "marks": [{"type": "rule", "axis": "x", "v": 1, "c": "grey", "dash": "dash"},
                              {"type": "range", "rows": [{"y": t, "lo": math.exp(lo), "mid": math.exp(b), "hi": math.exp(hi), "c": c,
                                                          "tip": f"{t}: {math.exp(b):.2f}× ({math.exp(lo):.2f}–{math.exp(hi):.2f})"}
                                                         for t, b, lo, hi, c in lang], "w": 3}]}],
        "table": {"cols": ["songs", "multiple", "95 % interval"],
                  "rows": [[t, round(math.exp(b), 2), f"{math.exp(lo):.2f}–{math.exp(hi):.2f}"] for t, b, lo, hi, _ in lang]},
        "data": ["results.json", "panel.csv"]}}
    checks = [("registered model", m1)] + [(k.replace("_", " "), v) for k, v in res["m1_checks"].items()]
    charts["checks"] = {
        "alt": "The language effect under each check: every estimate above 1, all intervals above 1.",
        "panels": [{"h": 180, "x": {"kind": "log", "domain": [0.8, 10], "ticks": [1, 2, 3, 5, 8], "fmt": {"dp": 1, "unit": "×"},
                                    "label": "same-language multiple (log scale)"},
                    "y": {"kind": "cat", "domain": [c for c, _ in checks]},
                    "marks": [{"type": "rule", "axis": "x", "v": 1, "c": "grey", "dash": "dash"},
                              {"type": "range", "rows": [{"y": c, "lo": 1 + v["pct_lo"], "mid": 1 + v["pct"], "hi": 1 + v["pct_hi"],
                                                          "c": "held" if i == 0 else "ink",
                                                          "tip": f"{c}: {1 + v['pct']:.2f}× ({1 + v['pct_lo']:.2f}–{1 + v['pct_hi']:.2f}), n = {v['n']}"}
                                                         for i, (c, v) in enumerate(checks)], "w": 3}]}],
        "table": {"cols": ["check", "multiple", "95 % interval", "pairs"],
                  "rows": [[c, round(1 + v["pct"], 2), f"{1 + v['pct_lo']:.2f}–{1 + v['pct_hi']:.2f}", v["n"]] for c, v in checks]},
        "data": ["results.json"]}
    cz = sorted(res["czechia_residuals"].items(), key=lambda kv: kv[1])
    charts["czechia"] = {
        "alt": "How much longer or shorter than the model predicts each artist's song lasted in Czechia.",
        "panels": [{"h": 150, "x": {"kind": "linear", "domain": [-60, 80], "ticks": [-50, -25, 0, 25, 50, 75], "fmt": {"dp": 0, "unit": " %", "sign": True},
                                    "label": "days in the Czech chart against the model's prediction"},
                    "y": {"kind": "cat", "domain": [NAME[a] for a, _ in cz]},
                    "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                              {"type": "hbar", "rows": [{"y": NAME[a], "x0": 0, "x1": 100 * v, "c": "held" if v > 0 else "light",
                                                         "tip": f"{NAME[a]}: {100 * v:+.0f} %"} for a, v in cz]}]}],
        "table": {"cols": ["artist", "against prediction"], "rows": [[NAME[a], f"{100 * v:+.0f} %"] for a, v in cz]},
        "data": ["results.json"]}
    t = pd.read_csv(R / "pop-measured-part6-tickets.csv")
    x0, y0 = t.log_gdppc.mean(), t.log_price.mean()
    th = res["m2"]["coef"]
    xs = [t.gdppc.min(), t.gdppc.max()]
    # the proportional-income line, clipped to the plotted price range so it does not run off the panel
    ylo, yhi = t.price.min() * 0.8, t.price.max() * 1.2
    xa = math.exp(x0 + (math.log(ylo) - y0)); xb = math.exp(x0 + (math.log(yhi) - y0))
    xa, xb = max(xa, xs[0]), min(xb, xs[1])
    prop = [[x, math.exp(y0 + (math.log(x) - x0))] for x in (xa, xb)]
    charts["prices"] = {
        "alt": f"Each tour entry's average ticket against the host country's GDP per capita, both on log scales; the fitted slope is {th:.2f}, far flatter than prices in proportion to income.",
        "panels": [{"h": 300, "x": {"kind": "log", "domain": [xs[0] * 0.8, xs[1] * 1.2], "ticks": [2000, 5000, 10000, 20000, 50000, 100000],
                                    "fmt": {"dp": 0, "pre": "$"}, "label": "host country's GDP per capita (log scale)"},
                    "y": {"kind": "log", "domain": [t.price.min() * 0.8, t.price.max() * 1.2], "ticks": [25, 50, 100, 200, 400],
                          "fmt": {"dp": 0, "pre": "$"}, "label": "average ticket (log scale)"},
                    "marks": [{"type": "dots", "pts": [{"x": r.gdppc, "y": r.price, "c": COL[r.artist], "r": 2.6, "o": .65,
                                                        "tip": f"{NAME[r.artist]}, {r.tour}, {r.country} {int(r.year)}: ${r.price:.0f}"}
                                                       for r in t.itertuples()]},
                              {"type": "line", "pts": [[x, math.exp(y0 + th * (math.log(x) - x0))] for x in xs], "c": "ink", "w": 2},
                              {"type": "line", "pts": prop, "c": "grey", "dash": "dash", "w": 1.5}]}],
        "legend": [{"label": NAME[a], "c": c} for a, c in COL.items()] + [{"label": f"fitted, slope {th:.2f}", "c": "ink"},
                                                                         {"label": "prices in proportion to income", "c": "grey", "dash": "dash"}],
        "table": {"cols": ["artist", "tour", "country", "year", "price, $", "GDP per capita, $"],
                  "rows": [[NAME[r.artist], r.tour, r.country, int(r.year), round(r.price), round(r.gdppc)] for r in t.itertuples()]},
        "data": ["tickets.csv"]}
    m2c = res["m2c"]
    charts["elasticity"] = {
        "alt": "Income elasticity of the average ticket for each artist, with 95 % intervals, against 0 (one price everywhere) and 1 (prices in proportion to income).",
        "panels": [{"h": 170, "x": {"kind": "linear", "domain": [-1, 1.4], "ticks": [-1, -0.5, 0, 0.5, 1], "fmt": {"dp": 1},
                                    "label": "income elasticity of the average ticket"},
                    "y": {"kind": "cat", "domain": ["all five"] + [NAME[a] for a in m2c]},
                    "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey", "dash": "dash", "label": "one price everywhere"},
                              {"type": "rule", "axis": "x", "v": 1, "c": "grey", "dash": "dash", "label": "in proportion to income"},
                              {"type": "range", "rows": [{"y": "all five", "lo": res["m2"]["lo"], "mid": res["m2"]["coef"], "hi": res["m2"]["hi"], "c": "held",
                                                          "tip": f"all five: {res['m2']['coef']:.2f} ({res['m2']['lo']:.2f} to {res['m2']['hi']:.2f})"}] +
                                                        [{"y": NAME[a], "lo": v["lo"], "mid": v["coef"], "hi": v["hi"], "c": "ink",
                                                          "tip": f"{NAME[a]}: {v['coef']:.2f} ({v['lo']:.2f} to {v['hi']:.2f}), {v['n']} entries in {v['countries']} countries"}
                                                          for a, v in m2c.items()], "w": 3}]}],
        "table": {"cols": ["artist", "elasticity", "95 % interval", "entries", "countries"],
                  "rows": [["all five", round(res["m2"]["coef"], 2), f"{res['m2']['lo']:.2f} to {res['m2']['hi']:.2f}", res["m2"]["n"], res["m2"]["clusters"]]] +
                          [[NAME[a], round(v["coef"], 2), f"{v['lo']:.2f} to {v['hi']:.2f}", v["n"], v["countries"]] for a, v in m2c.items()]},
        "data": ["results.json", "tickets.csv"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))

    def ranges(name, rows, xlabel, log=True, ref=1):
        f, ax = plt.subplots(figsize=(6.4, 0.38 * len(rows) + 0.9))
        for i, (lab, mid, lo, hi) in enumerate(reversed(rows)):
            ax.plot([lo, hi], [i, i], color=INK, lw=2); ax.scatter(mid, i, color=HELD, s=24, zorder=3)
        ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in reversed(rows)])
        if log:
            ax.set_xscale("log")
        ax.axvline(ref, color=GREY, ls="--", lw=.8); ax.set_xlabel(xlabel)
        f.tight_layout(); f.savefig(A / name); plt.close(f)
    ranges("01-language.svg", [(l[0], math.exp(l[1]), math.exp(l[2]), math.exp(l[3])) for l in lang], "same-language multiple (log scale)")
    ranges("02-checks.svg", [(c, 1 + v["pct"], 1 + v["pct_lo"], 1 + v["pct_hi"]) for c, v in checks], "same-language multiple (log scale)")
    f, ax = plt.subplots(figsize=(6.4, 2.2))
    ax.barh([NAME[a] for a, _ in cz], [100 * v for _, v in cz], color=[HELD if v > 0 else LIGHT for _, v in cz])
    ax.axvline(0, color=GREY, lw=.8); ax.set_xlabel("days in the Czech chart against the model's prediction, %")
    f.tight_layout(); f.savefig(A / "03-czechia.svg"); plt.close(f)
    f, ax = plt.subplots(figsize=(6.4, 3.4))
    for a, c in COL.items():
        s = t[t.artist == a]; ax.scatter(s.gdppc, s.price, s=10, color=c, alpha=.6, label=NAME[a])
    ax.plot(xs, [math.exp(y0 + th * (math.log(x) - x0)) for x in xs], color=INK, lw=1.6)
    ax.plot(xs, [math.exp(y0 + (math.log(x) - x0)) for x in xs], color=GREY, lw=1, ls="--")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("GDP per capita, $ (log)"); ax.set_ylabel("average ticket, $ (log)")
    ax.legend(fontsize=7, frameon=False); f.tight_layout(); f.savefig(A / "04-prices.svg"); plt.close(f)
    ranges("05-elasticity.svg", [("all five", res["m2"]["coef"], res["m2"]["lo"], res["m2"]["hi"])] +
           [(NAME[a], v["coef"], v["lo"], v["hi"]) for a, v in m2c.items()], "income elasticity of the average ticket", log=False, ref=0)


def values(res: dict) -> dict:
    m1, m1b, ck, m2 = res["m1"], res["m1b"], res["m1_checks"], res["m2"]
    v = {"m1_x": n(1 + m1["pct"], 1), "m1_lo": n(1 + m1["pct_lo"], 1), "m1_hi": n(1 + m1["pct_hi"], 1), "m1_pct": pct(m1["pct"]),
         "m1_n": n(m1["n"]), "m1_clusters": n(m1["clusters"]), "m1_same": n(res["m1_pairs"]["same"]), "m1_still": n(res["m1_pairs"]["still"]),
         "en_x": n(math.exp(m1b["en"]["coef"]), 1), "en_lo": n(math.exp(m1b["en"]["lo"]), 2), "en_hi": n(math.exp(m1b["en"]["hi"]), 1),
         "es_x": n(math.exp(m1b["es"]["coef"]), 1), "es_lo": n(math.exp(m1b["es"]["lo"]), 1), "es_hi": n(math.exp(m1b["es"]["hi"]), 1),
         "en_pairs": n(m1b["en"]["pairs"]), "es_pairs": n(m1b["es"]["pairs"]),
         "ko_x": n(math.exp(m1b["ko"]["coef"]), 1),
         "m2_th": n(m2["coef"], 2), "m2_lo": n(m2["lo"], 2), "m2_hi": n(m2["hi"], 2), "m2_n": n(m2["n"]), "m2_clusters": n(m2["clusters"]),
         "m2_tours": n(res["m2_entries"]["tours"]), "m2b_th": n(res["m2b"]["coef"], 2),
         "ten_x": n(10 ** m2["coef"], 2), "ten_pct": n(100 * (1 - 10 ** (-m2["coef"]))),
         "burden_x": n(10 ** (1 - m2["coef"]), 1)}
    for k, c in ck.items():
        v[f"ck_{k}"] = n(1 + c["pct"], 1)
        v[f"ck_{k}_lo"] = n(1 + c["pct_lo"], 2)
        v[f"ck_{k}_hi"] = n(1 + c["pct_hi"], 1)
    for a, c in res["m2c"].items():
        k = a.replace("-", "_")
        v |= {f"e_{k}": n(c["coef"], 2), f"e_{k}_lo": n(c["lo"], 2), f"e_{k}_hi": n(c["hi"], 2),
              f"e_{k}_n": n(c["n"]), f"e_{k}_c": n(c["countries"])}
    for a, r in res["czechia_residuals"].items():
        v[f"cz_{a.replace('-', '_')}"] = pct(r)
    d = res["m2_drop_artist"]
    v |= {"drop_min": n(min(d.values()), 2), "drop_max": n(max(d.values()), 2),
          "drop_min_a": {"harry-styles": "Harry Styles", "taylor-swift": "Taylor Swift", "bts": "BTS", "bad-bunny": "Bad Bunny",
                         "billie-eilish": "Billie Eilish"}[min(d, key=d.get)]}
    pan = pd.read_csv(R / "pop-measured-part6-panel.csv")
    for r in pan.itertuples():   # d_<country>_<artist>: every pair's days, for the worked examples
        v[f"d_{r.country}_{r.artist.replace('-', '_')}"] = n(r.days)
    v |= {"es_still": n(int((pan.same.eq(1) & pan.song_lang.eq("es") & pan.still).sum())),
          "en_countries": n(pan[pan.country_lang == "en"].country.nunique())}
    # post-hoc, added after the audit of 3 October 2026: M1's residuals (OLS with artist and country dummies, as in
    # together.py) in the countries that speak none of the five languages, English songs against the others
    X = pd.get_dummies(pan[["artist", "country"]], drop_first=True).astype(float)
    X.insert(0, "same", pan.same.astype(float)); X.insert(0, "const", 1.0)
    beta = np.linalg.lstsq(X.values, pan.log_days.values, rcond=None)[0]
    oth = pan.assign(r=pan.log_days.values - X.values @ beta, en=pan.song_lang.eq("en"))
    oth = oth[oth.country_lang == "other"].groupby(["country", "en"]).r.mean().unstack().dropna()
    v |= {"oth_n": n(len(oth)), "oth_en_wins": n(int((oth[True] > oth[False]).sum()))}
    tk = pd.read_csv(R / "pop-measured-part6-tickets.csv").groupby("country").gdppc.mean()
    lo_c, hi_c = tk.idxmin(), tk.idxmax()
    span = tk.max() / tk.min()
    names = {"HND": "Honduras", "PHL": "the Philippines", "IRL": "Ireland", "NOR": "Norway", "CHE": "Switzerland",
             "NLD": "the Netherlands"}
    bb = pd.read_csv(R / "pop-measured-part6-tickets.csv").query("artist == 'bad-bunny'").groupby("country").gdppc.mean()
    v |= {"bb_lo_c": names.get(bb.idxmin(), bb.idxmin()), "bb_hi_c": names.get(bb.idxmax(), bb.idxmax())}
    v |= {"inc_lo_c": names.get(lo_c, lo_c), "inc_hi_c": names.get(hi_c, hi_c), "inc_lo": n(tk.min()), "inc_hi": n(tk.max()),
          "inc_span": n(span), "span_price": n(span ** m2["coef"], 1), "span_burden": n(span ** (1 - m2["coef"])),
          "example_price": n(100 * (tk.min() / tk.max()) ** m2["coef"])}
    photo = next(p for p in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if p["slug"] == "pop-together")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-pop-together;'
                  '--bg:url(../assets/photo/pop-together.jpg);--bg-s:url(../assets/photo/pop-together-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    res = json.loads((R / "pop-measured-part6-results.json").read_text())
    figures(res)
    t = (Path(__file__).with_name("templates") / "together.html").read_text(encoding="utf-8")
    v = values(res)
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", t)) - set(v))
    if missing:
        sys.exit(f"keys not computed: {missing}")
    (ROOT / "texts" / "pop-together.html").write_text(re.sub(r"\{\{(\w+)\}\}", lambda m: v[m.group(1)], t), encoding="utf-8")
    print("written texts/pop-together.html")


if __name__ == "__main__":
    main()
