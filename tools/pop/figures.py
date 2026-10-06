"""Pop, measured: published data, chart specs, widget data and static figures for one part.

Reads docs/research/<slug>-*.csv and <slug>-results.json and writes to assets/pop/<slug>/:
- charts.json: specs read by assets/charts.js (countries, residencies, catalogue);
- widgets.json: data read by assets/pop/pop.js (every number one as a dot; tickets in days of income);
- 01-ones.svg … 05-tour.svg: static fallbacks;
- the published CSVs.

    uv run --with numpy --with matplotlib python tools/pop/figures.py harry-styles
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
INK, GREY, LIGHT = "#111111", "#666666", "#b5b5b0"
# each artist keeps one colour in every chart of the series (assets/palette.json); a part's own songs and its Czech row wear it
NAME = {"harry-styles": "Harry Styles", "taylor-swift": "Taylor Swift", "bts": "BTS", "bad-bunny": "Bad Bunny",
        "billie-eilish": "Billie Eilish"}
ARTIST = json.loads((ROOT / "assets" / "palette.json").read_text())["artist"]
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})

COUNTRY = {"ae": "UAE", "ar": "Argentina", "at": "Austria", "au": "Australia", "be": "Belgium", "bg": "Bulgaria",
           "bo": "Bolivia", "br": "Brazil", "by": "Belarus", "ca": "Canada", "ch": "Switzerland", "cl": "Chile",
           "co": "Colombia", "cr": "Costa Rica", "cy": "Cyprus", "cz": "Czechia", "de": "Germany", "dk": "Denmark",
           "do": "Dominican Rep.", "ec": "Ecuador", "ee": "Estonia", "eg": "Egypt", "es": "Spain", "fi": "Finland",
           "fr": "France", "gb": "UK", "gr": "Greece", "gt": "Guatemala", "hk": "Hong Kong", "hn": "Honduras",
           "hu": "Hungary", "id": "Indonesia", "ie": "Ireland", "il": "Israel", "in": "India", "is": "Iceland",
           "it": "Italy", "jp": "Japan", "kr": "South Korea", "kz": "Kazakhstan", "lt": "Lithuania", "lu": "Luxembourg",
           "lv": "Latvia", "ma": "Morocco", "mx": "Mexico", "my": "Malaysia", "ng": "Nigeria", "ni": "Nicaragua",
           "nl": "Netherlands", "no": "Norway", "nz": "New Zealand", "pa": "Panama", "pe": "Peru", "ph": "Philippines",
           "pk": "Pakistan", "pl": "Poland", "pt": "Portugal", "py": "Paraguay", "ro": "Romania", "sa": "Saudi Arabia",
           "se": "Sweden", "sg": "Singapore", "sk": "Slovakia", "sv": "El Salvador", "th": "Thailand", "tr": "Turkey",
           "tw": "Taiwan", "ua": "Ukraine", "us": "United States", "uy": "Uruguay", "ve": "Venezuela", "vn": "Vietnam",
           "za": "South Africa"}


def rows(name: str) -> list[dict]:
    with open(R / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(slug: str) -> None:
    HELD = ARTIST[NAME[slug]]
    out = ROOT / "assets" / "pop" / slug
    out.mkdir(parents=True, exist_ok=True)
    res = json.loads((R / f"{slug}-results.json").read_text())
    for name in ("ones", "countries", "songs", "tour"):
        if (R / f"{slug}-{name}.csv").exists():
            shutil.copy(R / f"{slug}-{name}.csv", out / f"{name}.csv")
    shutil.copy(R / f"{slug}-results.json", out / "results.json")

    # 1 every number one as a dot (widget), static fallback a dot histogram
    ones = [r for r in rows(f"{slug}-ones.csv") if r["kept"] == "True"]
    dots = sorted(({"t": r["label"], "d": int(r["days"]), "c": r["still_charting"] == "True", "o": r["own"] == "True",
                    "f": r["focal"] == "True"}
                   for r in ones), key=lambda x: x["d"])
    q1 = res["q1"]
    f, ax = plt.subplots(figsize=(7.2, 2.6))
    bins: dict[int, int] = {}
    for x in dots:
        b = x["d"] // 50
        bins[b] = bins.get(b, 0) + 1
        ax.scatter(b * 50 + 25, bins[b], s=14, color=HELD if x["o"] else LIGHT, zorder=3 if x["o"] else 2)
    ax.set_xlabel("days in Spotify's global Top 200"); ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    f.tight_layout(); f.savefig(out / "01-ones.svg"); plt.close(f)

    # 2 countries: ratio with interval, log axis, Czechia held
    cs = [c for c in res["q2"]["countries"] if c["ranked"]]
    cs = sorted(cs, key=lambda c: -c["ratio"])
    names = [COUNTRY.get(c["country"], c["country"].upper()) + ("*" if c["still_charting"] else "") for c in cs]
    lo = min(c["ci95"][0] for c in cs)
    hi = max(c["ci95"][1] for c in cs)
    spec_countries = {
        "alt": f"The focal song's days in each of {len(cs)} national charts, divided by the median days of that country's "
               f"number ones, with 95 % intervals; Czechia highlighted.",
        "panels": [{"h": 14 * len(cs), "x": {"kind": "log", "domain": [max(lo * 0.8, 0.1), hi * 1.2],
                                             "ticks": [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64, 128], "fmt": {"dp": 2, "unit": "×"},
                                             "label": "times as long as the country's median number one (log scale)"},
                    "y": {"kind": "cat", "domain": names},
                    "marks": [{"type": "rule", "axis": "x", "v": 1, "c": "grey", "dash": "dash", "label": "as long as the median", "dy": -2},
                              {"type": "range", "rows": [{"y": n, "lo": c["ci95"][0], "hi": c["ci95"][1], "mid": c["ratio"],
                                                          "c": HELD if c["country"] == "cz" else "grey",
                                                          "tip": f"{n}: {c['days']} days; the median number one {c['median_ones_days']:g} days; "
                                                                 f"{c['ratio']:.2f}× ({c['ci95'][0]:.2f}–{c['ci95'][1]:.2f})"}
                                                         for n, c in zip(names, cs)], "w": 2}]}],
        "legend": [{"label": "Czechia", "c": HELD}, {"label": "other countries", "c": "grey"}, {"label": "95 % interval", "c": "light"}],
        "table": {"cols": ["country", "days", "median number one, days", "ratio", "95 % interval", "rank by days (added after results)"],
                  "rows": [[n, c["days"], c["median_ones_days"], round(c["ratio"], 2),
                            f"{c['ci95'][0]:.2f}–{c['ci95'][1]:.2f}", c["rank_by_days_post_hoc"]] for n, c in zip(names, cs)]},
        "data": ["countries.csv"]}
    f, ax = plt.subplots(figsize=(6.4, 0.16 * len(cs) + 0.8))
    ys = range(len(cs))[::-1]
    for y, c in zip(ys, cs):
        ax.plot(c["ci95"], [y, y], color=LIGHT, lw=1)
        ax.scatter(c["ratio"], y, s=12 if c["country"] != "cz" else 30, color=HELD if c["country"] == "cz" else GREY, zorder=3)
    ax.set_xscale("log"); ax.axvline(1, color=GREY, ls="--", lw=0.8)
    ax.set_yticks(list(ys)); ax.set_yticklabels(names, fontsize=6.5)
    ax.set_xlabel("times as long as the country's median number one (log scale)")
    f.tight_layout(); f.savefig(out / "02-countries.svg"); plt.close(f)

    # 3 tickets in days of income (widget), static fallback horizontal bars
    q5 = res["q5"]
    short = {"Czech Republic": "Czechia", "United Kingdom": "UK", "United States": "US"}
    tickets = [{"n": short.get(c["country"], c["country"]), "p": round(c["price_usd"]), "d": round(c["days_of_income"], 2), "s": c["sold"]}
               for c in q5.get("countries", [])]
    if tickets:
        f, ax = plt.subplots(figsize=(6.4, 0.18 * len(tickets) + 0.8))
        ys = range(len(tickets))[::-1]
        ax.barh(list(ys), [t["d"] for t in tickets], color=[HELD if t["n"] in ("Czech Republic", "Czechia") else LIGHT for t in tickets], height=0.7)
        ax.set_yticks(list(ys)); ax.set_yticklabels([t["n"] for t in tickets], fontsize=6.5)
        ax.set_xlabel("average ticket, in days of GDP per capita")
        f.tight_layout(); f.savefig(out / "03-tickets.svg"); plt.close(f)

    # 4 catalogue: one bar split by song
    songs = rows(f"{slug}-songs.csv")
    total = sum(int(s["streams"]) for s in songs)
    segs, x = [], 0.0
    for s in songs[:8]:
        w = int(s["streams"]) / total
        segs.append({"y": " ", "x0": 100 * x, "x1": 100 * (x + w), "tip": f"{s['title']}: {100 * w:.1f} % of streams"})
        x += w
    segs.append({"y": " ", "x0": 100 * x, "x1": 100.0, "tip": f"{len(songs) - 8} other songs: {100 * (1 - x):.1f} % of streams"})
    spec_catalogue = {
        "alt": f"Share of all Spotify streams by song: {songs[0]['title']} {100 * int(songs[0]['streams']) / total:.0f} %, "
               f"the top three {100 * res['q4']['top3_share']:.0f} %, {len(songs)} songs in all.",
        "panels": [{"h": 60, "x": {"kind": "linear", "domain": [0, 100], "ticks": [0, 25, 50, 75, 100], "fmt": {"dp": 0, "unit": " %"},
                                   "label": "share of the artist's streams"},
                    "y": {"kind": "cat", "domain": [" "]},
                    "marks": [{"type": "hbar", "rows": [dict(sg, c=HELD if i == 0 else ("ink" if i < 3 else "light")) for i, sg in enumerate(segs)]}]}],
        "table": {"cols": ["song", "streams", "share"],
                  "rows": [[s["title"], int(s["streams"]), f"{100 * int(s['streams']) / total:.1f} %"] for s in songs]},
        "data": ["songs.csv"]}
    f, ax = plt.subplots(figsize=(7.2, 0.9))
    for i, sg in enumerate(segs):
        ax.barh(0, (sg["x1"] - sg["x0"]) / 100, left=sg["x0"] / 100, color=HELD if i == 0 else (INK if i < 3 else LIGHT), edgecolor="white", height=0.6)
    ax.set_yticks([]); ax.set_xlim(0, 1); ax.set_xlabel("share of the artist's streams")
    f.tight_layout(); f.savefig(out / "04-catalogue.svg"); plt.close(f)

    # 5 residencies: sell-through by nights
    charts = {"countries": spec_countries, "catalogue": spec_catalogue}
    if res["q3"].get("answerable"):
        # the entries the analysis counts: multi-venue leg totals and hybrid online entries are left out, as in q3
        tour = [t for t in rows(f"{slug}-tour.csv") if t.get("multi_venue") != "True" and t.get("hybrid") != "True"]
        pts = [{"x": int(t["nights"]), "y": round(100 * int(t["sold"]) / int(t["available"]), 2),
                "tip": f"{t['venue']}, {t['city']} ({t['tour']}): {t['nights']} night(s), "
                         f"{100 * int(t['sold']) / int(t['available']):.1f} % sold"} for t in tour]
        charts["tour"] = {
            "alt": f"{len(tour)} Boxscore entries: share of tickets sold against nights in the run; "
                   f"{100 * res['q3']['share_sold_out']:.0f} % sold 99.5 % or more.",
            "panels": [{"h": 220, "x": {"kind": "linear", "domain": [0, max(p["x"] for p in pts) + 1], "fmt": {"dp": 0},
                                        "label": "nights in the run"},
                        "y": {"kind": "linear", "domain": [min(p["y"] for p in pts) - 2, 101],
                              "fmt": {"dp": 0, "unit": " %"}, "label": "tickets sold"},
                        "marks": [{"type": "dots", "pts": pts, "c": HELD, "r": 3, "o": 0.7}]}],
            "table": {"cols": ["tour", "venue", "city", "nights", "sold", "available"],
                      "rows": [[t["tour"], t["venue"], t["city"], int(t["nights"]), int(t["sold"]), int(t["available"])] for t in tour]},
            "data": ["tour.csv"]}
        f, ax = plt.subplots(figsize=(6.4, 2.6))
        ax.scatter([p["x"] for p in pts], [p["y"] for p in pts], s=10, color=HELD, alpha=0.7)
        ax.set_xlabel("nights in the run"); ax.set_ylabel("% of tickets sold")
        f.tight_layout(); f.savefig(out / "05-tour.svg"); plt.close(f)

    (out / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    (out / "widgets.json").write_text(json.dumps({"c": HELD, "ones": dots, "median": q1["median_days"], "tickets": tickets,
                                                  "peak": int(rows(f"{slug}-ones.csv")[0]["peak"])},
                                                 ensure_ascii=False))
    print("written", out.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1])
