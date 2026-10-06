"""Annual pass note: figures and the numbers quoted in texts/annual-pass.html, from the two collected CSVs.

Reads docs/research/annual-pass-passengers.csv and annual-pass-prices.csv; writes assets/transit/ (charts.json,
01-cities.svg, 02-germany.svg, 03-prices.svg, passengers.csv, prices.csv) and prints the numbers the page quotes.
Descriptive only: no model, no effect, no label (design, change of 6 October 2026, "output").

    uv run --with matplotlib --with pandas python tools/transit/note.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "transit"
PAL = json.loads((ROOT / "assets" / "palette.json").read_text())
INK, GREY, LIGHT = PAL["ink"], PAL["grey"], PAL["light"]
# one colour per city, the same in every chart on the site (assets/palette.json); every line is also labelled at its end
STYLE = {c: (h, h, None) for c, h in PAL["entity"].items()}
CUTS = {"Vienna": 2012 + 4 / 12, "Prague": 2015.5}   # 1 May 2012, 1 July 2015, as decimal years
BASE = range(2005, 2012)                              # each city's own 2005–2011 mean = 100
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})


def passengers() -> pd.DataFrame:
    d = pd.read_csv(R / "annual-pass-passengers.csv")
    return d.pivot_table(index="year", columns="city", values="passengers_million")


def steps() -> dict[str, list[tuple[float, float]]]:
    """Annual-pass price per city as (decimal year, price), each change at its date, indexed to the 2011 price = 100.
    Only the adult annual pass of the core zone, paid at once; nominal prices."""
    d = pd.read_csv(R / "annual-pass-prices.csv", parse_dates=["date"])
    out = {}
    for city, base in (("Vienna", 449), ("Prague", 4750), ("Brno", 4430)):
        rows = d[(d.city == city) & ~d["product"].str.contains("Digital|digital")].sort_values("date")
        pts, last = [], None
        for _, r in rows.iterrows():
            if r.price != last:
                pts.append((r.date.year + (r.date.dayofyear - 1) / 365.25, round(r.price / base * 100, 1)))
                last = r.price
        out[city] = pts
    return out


def month(x: float) -> str:
    y = int(x)
    return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][min(11, int((x - y) * 12 + 0.01))]} {y}"


def stepline(pts: list[tuple[float, float]], end: float) -> list[list[float]]:
    line = []
    for (x, y), nxt in zip(pts, pts[1:] + [(end, None)]):
        line += [[round(x, 3), y], [round(nxt[0], 3), y]]
    return line


def figures(p: pd.DataFrame) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "annual-pass-passengers.csv", A / "passengers.csv")
    shutil.copy(R / "annual-pass-prices.csv", A / "prices.csv")
    idx = {c: (p[c] / p.loc[BASE, c].mean() * 100).dropna().loc[2005:] for c in ("Vienna", "Prague", "Brno")}
    marks = [{"type": "span", "v0": 2019.5, "v1": 2025.5, "c": "light", "o": 0.25, "label": "COVID"},
             {"type": "rule", "axis": "y", "v": 100, "c": "grey"},
             {"type": "rule", "axis": "x", "v": CUTS["Vienna"], "c": "light", "dash": "dot"},
             {"type": "rule", "axis": "x", "v": CUTS["Prague"], "c": "light", "dash": "dot"},
             {"type": "rule", "axis": "x", "v": 2013.5, "c": "light", "dash": "dash", "w": 0.8},
             {"type": "rule", "axis": "x", "v": 2019.5, "c": "light", "dash": "dash", "w": 0.8}]
    for c, s in idx.items():
        key, _, dash = STYLE[c]
        marks.append({"type": "line", "name": c, "pts": [[int(y), round(float(v), 1)] for y, v in s.items()],
                      "c": key, "dash": dash, "fmt": {"dp": 1}, "end": True})
    at = lambda c, x: round(float(idx[c].loc[int(x)]), 1)
    marks += [
        {"type": "callout", "x": 2012, "y": at("Vienna", 2012), "dx": -40, "dy": -34, "anchor": "end",
         "s": "Vienna's pass −19 %, May 2012", "narrow": {"s": "Vienna's pass\n−19 %, 2012", "dy": -40, "dx": -18}},
        {"type": "callout", "x": 2015, "y": at("Prague", 2015), "dx": 16, "dy": 44, "anchor": "start",
         "s": "Prague's pass −23 %\nJuly 2015", "narrow": {"s": "Prague's pass\n−23 %", "dx": 6, "dy": 40}},
        {"type": "callout", "x": 2014, "y": at("Prague", 2014), "dx": -16, "dy": 52, "anchor": "end",
         "s": "Prague counts by survey from 2014", "narrow": {"s": "counted by\nsurvey from 2014", "dx": -10, "dy": 44}},
        {"type": "callout", "x": 2020, "y": at("Prague", 2020), "dx": -14, "dy": 14, "anchor": "end",
         "s": "automatic counts from 2020", "narrow": {"s": "automatic\ncounts, 2020", "dy": 4}}]
    charts = {"cities": {
        "alt": "Annual passengers of the city operator in Vienna, Prague and Brno, 2005–2025, each indexed to its own "
               "2005–2011 mean: Vienna rises from 93 to 119 by 2019, Prague stays near 100 with a drop in 2011 and 2014, "
               "Brno rises slowly; all three fall in 2020.",
        "panels": [{"h": 300, "padRight": 74, "x": {"kind": "linear", "domain": [2004.5, 2025.5], "ticks": list(range(2005, 2026, 5)),
                                    "fmt": {"dp": 0, "nogroup": True}, "label": "year"},
                    "y": {"kind": "linear", "domain": [40, 136], "ticks": [40, 60, 80, 100, 120],
                          "fmt": {"dp": 0}, "label": "passengers, own 2005–2011 mean = 100"},
                    "marks": marks}],
        "legend": [{"label": c, "c": STYLE[c][0], "dash": STYLE[c][2]} for c in idx],
        "table": {"cols": ["year"] + [f"{c}, index" for c in idx] + [f"{c}, million" for c in idx],
                  "rows": [[int(y)] + [round(float(idx[c].get(y, float("nan"))), 1) if y in idx[c] else None for c in idx]
                           + [round(float(p.loc[y, c]), 1) if pd.notna(p.loc[y, c]) else None for c in idx]
                           for y in p.loc[2005:].index]},
        "data": ["passengers.csv"]}}
    de = {c: (p[c] / p.loc[2019, c] * 100).dropna() for c in ("Berlin", "Germany")}
    dm = [{"type": "span", "v0": 2022 + 5 / 12, "v1": 2022 + 8 / 12, "c": PAL["entity"]["Berlin"], "o": 0.14,
           "label": "9-euro"},
          {"type": "rule", "axis": "x", "v": 2023 + 4 / 12, "c": "grey", "dash": "dot", "label": "Deutschlandticket",
           "anchor": "end", "dy": 36},
          {"type": "rule", "axis": "y", "v": 100, "c": "grey"},
          {"type": "rule", "axis": "x", "v": 2018.5, "c": "light", "dash": "dot", "label": "← earlier basis", "anchor": "end", "dy": 196}]
    for c, s in de.items():
        key, _, dash = STYLE[c]
        dm.append({"type": "line", "name": c, "pts": [[int(y), round(float(v), 1)] for y, v in s.items()], "c": key,
                   "dash": dash, "fmt": {"dp": 1}, "end": True})
    dm.append({"type": "callout", "x": 2021, "y": round(float(de["Berlin"][2021]), 1), "dx": 48, "dy": 4,
               "anchor": "start", "s": "Berlin 2021: a third below 2019",
               "narrow": {"s": "a third\nbelow 2019", "dx": 22, "dy": -6}})
    charts["germany"] = {
        "alt": "Annual passengers of local scheduled public transport in Berlin and in Germany, 2012–2025, indexed to "
               "2019: both rise to 2019, fall by about 30 % in 2020–2021 and return to near the 2019 level by 2024–2025.",
        "panels": [{"h": 270, "padRight": 80, "x": {"kind": "linear", "domain": [2011.5, 2025.5], "ticks": list(range(2012, 2026, 2)),
                                    "fmt": {"dp": 0, "nogroup": True}, "label": "year"},
                    "y": {"kind": "linear", "domain": [60, 115], "ticks": [60, 70, 80, 90, 100, 110],
                          "fmt": {"dp": 0}, "label": "passengers, 2019 = 100"},
                    "marks": dm}],
        "legend": [{"label": c, "c": STYLE[c][0]} for c in de],
        "table": {"cols": ["year", "Berlin, index", "Germany, index", "Berlin, million", "Germany, million"],
                  "rows": [[int(y), round(float(de["Berlin"].get(y)), 1) if y in de["Berlin"] else None,
                            round(float(de["Germany"].get(y)), 1) if y in de["Germany"] else None,
                            round(float(p.loc[y, "Berlin"]), 1) if pd.notna(p.loc[y, "Berlin"]) else None,
                            round(float(p.loc[y, "Germany"]), 1) if pd.notna(p.loc[y, "Germany"]) else None]
                           for y in range(2012, 2026)]},
        "data": ["passengers.csv"]}
    st = steps()
    pm = [{"type": "rule", "axis": "y", "v": 100, "c": "grey"}]
    for c, pts in st.items():
        key, _, dash = STYLE[c]
        pm.append({"type": "line", "name": c, "pts": stepline(pts, 2026.75), "c": key, "dash": dash, "notip": True,
                   "end": True})
        pm.append({"type": "dots", "c": key, "r": 3.5,
                   "pts": [{"x": round(x, 3), "y": y, "tip": f"{c}: {y:.0f} from {month(x)}"} for x, y in pts]})
    pm += [{"type": "callout", "x": round(st["Vienna"][2][0], 3), "y": st["Vienna"][2][1], "dx": -14, "dy": 30,
            "anchor": "end", "s": "Vienna −19 %", "narrow": {"dx": -8}},
           {"type": "callout", "x": round(st["Prague"][3][0], 3), "y": st["Prague"][3][1], "dx": 0, "dy": 30,
            "s": "Prague −23 %"},
           {"type": "callout", "x": 2012, "y": st["Brno"][4][1], "dx": -14, "dy": -24, "anchor": "end",
            "s": "Brno +7 %", "narrow": {"dx": -8}}]
    charts["prices"] = {
        "alt": "Price of the adult annual pass in Vienna, Prague and Brno, 2004–2026, indexed to each city's 2011 "
               "price: Vienna drops to 81 in May 2012, Prague to 77 in July 2015, Brno rises to 107 in 2012.",
        "panels": [{"h": 260, "padRight": 74, "x": {"kind": "linear", "domain": [2004, 2027], "ticks": list(range(2005, 2027, 5)),
                                    "fmt": {"dp": 0, "nogroup": True}, "label": "year"},
                    "y": {"kind": "linear", "domain": [60, 120], "ticks": [60, 80, 100, 120], "fmt": {"dp": 0},
                          "label": "annual-pass price, nominal, 2011 = 100"},
                    "marks": pm}],
        "legend": [{"label": c, "c": STYLE[c][0], "dash": STYLE[c][2]} for c in st],
        "table": {"cols": ["city", "from", "price, 2011 = 100"],
                  "rows": [[c, month(x), y] for c, pts in st.items() for x, y in pts]},
        "data": ["prices.csv"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    static(idx, de, st)
    return {"idx": idx, "de": de, "steps": st}


def static(idx: dict, de: dict, st: dict) -> None:
    """The SVG fallbacks shown before charts.js draws the interactive versions."""
    f, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.axvspan(2019.5, 2025.5, color=LIGHT, alpha=0.25, lw=0)
    ax.axhline(100, color=GREY, lw=0.8)
    for c, s in idx.items():
        ax.plot(s.index, s.values, color=STYLE[c][1], lw=2, ls="--" if STYLE[c][2] else "-", label=c)
    for c, x in CUTS.items():
        ax.axvline(x, color=STYLE[c][1], lw=1, ls=":")
    ax.set_ylim(40, 130); ax.set_ylabel("passengers, own 2005–2011 mean = 100")
    ax.legend(frameon=False, ncol=3, loc="lower left"); f.tight_layout(); f.savefig(A / "01-cities.svg"); plt.close(f)
    f, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.axvspan(2022 + 5 / 12, 2022 + 8 / 12, color=PAL["entity"]["Berlin"], alpha=0.18, lw=0)
    ax.axvline(2023 + 4 / 12, color=GREY, lw=1, ls=":"); ax.axhline(100, color=GREY, lw=0.8)
    for c, s in de.items():
        ax.plot(s.index, s.values, color=STYLE[c][1], lw=2, label=c)
    ax.set_ylim(60, 115); ax.set_ylabel("passengers, 2019 = 100")
    ax.legend(frameon=False, loc="lower left"); f.tight_layout(); f.savefig(A / "02-germany.svg"); plt.close(f)
    f, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.axhline(100, color=GREY, lw=0.8)
    for c, pts in st.items():
        xs = [x for x, _ in pts] + [2026.75]
        ax.step(xs, [y for _, y in pts] + [pts[-1][1]], where="post", color=STYLE[c][1], lw=2,
                ls="--" if STYLE[c][2] else "-", label=c)
    ax.set_ylim(60, 120); ax.set_ylabel("annual-pass price, 2011 = 100")
    ax.legend(frameon=False, ncol=3, loc="lower left"); f.tight_layout(); f.savefig(A / "03-prices.svg"); plt.close(f)


def cagr(s: pd.Series, a: int, b: int) -> float:
    return ((s[b] / s[a]) ** (1 / (b - a)) - 1) * 100


def main() -> None:
    p = passengers()
    fig = figures(p)
    idx = fig["idx"]
    out = {
        "vienna_growth_2005_2011": cagr(p.Vienna, 2005, 2011), "vienna_growth_2012_2019": cagr(p.Vienna, 2012, 2019),
        "prague_growth_2005_2011": cagr(p.Prague, 2005, 2011), "prague_growth_2015_2019": cagr(p.Prague, 2015, 2019),
        "brno_growth_2005_2011": cagr(p.Brno, 2005, 2011), "brno_growth_2012_2019": cagr(p.Brno, 2012, 2019),
        "prague_2013_2014": (p.Prague[2014] / p.Prague[2013] - 1) * 100,
        "prague_2010_2011": (p.Prague[2011] / p.Prague[2010] - 1) * 100,
        "index_2019": {c: round(float(s[2019]), 1) for c, s in idx.items()},
        "vs_2019_latest": {"Vienna 2024": (p.Vienna[2024] / p.Vienna[2019] - 1) * 100,
                           "Prague 2025": (p.Prague[2025] / p.Prague[2019] - 1) * 100,
                           "Brno 2025": (p.Brno[2025] / p.Brno[2019] - 1) * 100,
                           "Berlin 2025": (p.Berlin[2025] / p.Berlin[2019] - 1) * 100,
                           "Germany 2024": (p.Germany[2024] / p.Germany[2019] - 1) * 100},
        "germany_2020_2021_vs_2019": {f"{c} {y}": round(float(fig["de"][c][y]), 1)
                                      for c in ("Berlin", "Germany") for y in (2020, 2021)},
        "price_steps": fig["steps"],
    }
    print(json.dumps(out, indent=1, default=lambda v: round(v, 2)))


if __name__ == "__main__":
    main()
