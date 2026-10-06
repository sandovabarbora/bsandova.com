"""Story layer for the Prague, measured charts: entity colours, labels at line ends and notes at key points.

Run after the chart generators (tools/charts/prague_*.py, parking.py), which write the numbers; this script only
changes colours, adds end labels and callouts, and never touches a value. Parties and cities take their colour from
assets/palette.json, the same in every article; the rest keeps the article's own accent or recedes to grey. Idempotent.

    python3 tools/charts/story_prague.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"
PAL = json.loads((A / "palette.json").read_text())
CITY, PARTY = PAL["entity"], PAL["party"]
ANO, PIR, PSOBE = PARTY["ANO"], PARTY["Pirates"], PARTY["Praha sobě"]
PRG, VIE, WAW = CITY["Prague"], CITY["Vienna"], CITY["Warsaw"]

# file -> (json dump style, {chart id -> story})
# story: recolor {old: new} over every "c" in the chart; rows {row y -> colour} for row-level colours;
# end [line names] (or {name: label}) with padRight; callouts [(panel, mark)]; legend [entries] replaces the legend.
STORY = {
    "zhmp/charts-council.json": ("compact", {
        "with-spolu": {"recolor": {"#a8201a": PSOBE}},
        "within": {"callouts": [(0, {"x": 0.2009, "y": "2010–14 → 2014–18", "dx": 0, "dy": -16, "anchor": "middle",
                                     "s": "most of the fall: × 0.20", "narrow": {"dy": 30}})]},
        "abstain-sittings": {"callouts": [(0, {"x": 2018.8329, "y": 62, "dx": 10, "dy": -26, "anchor": "start",
                                               "s": "new term, 2018: a further step down",
                                               "narrow": {"s": "2018: a further\nstep down", "dy": -34}})]},
    }),
    "praha/charts-rings.json": ("indent", {
        "three-rulers": {"recolor": {"#9a7b0a": ANO, "ink": PIR}, "end": {2: ["ANO", "Pirates"]}, "padRight": {2: 64},
                         "callouts": [(2, {"x": "<10", "y": 16.04, "dx": 0, "dy": 26, "anchor": "middle", "s": "16 %"}),
                                      (2, {"x": ">70", "y": 26.01, "dx": -6, "dy": -16, "anchor": "end", "s": "26 %"})]},
        "attenuation": {"rows": {"ANO 2025": ANO, "ANO 2025, + age": ANO, "ANO 2021": ANO,
                                 "SPOLU 2025": "grey", "SPOLU 2021": "grey"},
                        "legend_recolor": {"#9a7b0a": ANO},
                        "legend_after": {"education and citizenship held equal":
                                         {"label": "the same for SPOLU", "c": "grey"}}},
        "metro-equivalence": {"recolor": {"#9a7b0a": ANO}},
        "steepening": {"recolor": {"#9a7b0a": ANO}},
        "spec-curve": {"recolor": {"#9a7b0a": ANO}},
    }),
    "praha/charts-districts.json": ("compact-nonl", {
        "event-study": {"callouts": [(0, {"x": 0, "y": 70.14, "dx": 14, "dy": -6, "anchor": "start",
                                          "s": "2018 change: +70 % in its first year",
                                          "narrow": {"s": "2018: +70 %\nfirst year"}}),
                                     (0, {"x": 0, "y": -59.0, "dx": -14, "dy": 4, "anchor": "end",
                                          "s": "2023 change: −59 %",
                                          "narrow": {"s": "2023: −59 %"}})]},
    }),
    "praha/charts-housing.json": ("compact", {
        "completions": {"recolor": {"#1f5fa8": PRG, "ink": VIE, "light": WAW},
                        "end": {0: {"Prague": "Prague", "Vienna (new buildings)": "Vienna", "Warsaw": "Warsaw"}},
                        "padRight": {0: 70},
                        "callouts": [(0, {"x": 2021, "y": 8.45, "dx": -10, "dy": -22, "anchor": "end",
                                          "s": "Vienna's peak, 8.5 (2021)", "narrow": {"s": "Vienna 8.5\n(2021)", "dy": -30}})]},
        "benchmark": {"pts": {"Vienna metro region": VIE, "Warsaw metro region": WAW},
                      "recolor": {"#1f5fa8": PRG},
                      "legend": [{"label": "Prague", "c": PRG, "shape": "o"}, {"label": "Vienna", "c": VIE, "shape": "o"},
                                 {"label": "Warsaw", "c": WAW, "shape": "o"},
                                 {"label": "other metropolitan regions", "c": "light", "shape": "o"}]},
        "lag-profile": {"recolor": {"#1f5fa8": PRG}, "end": {0: ["Prague", "rest of Czechia"]}, "padRight": {0: 104},
                        "callouts": [(0, {"x": 16, "y": 0, "dx": 10, "dy": -12, "anchor": "start",
                                          "s": "Prague's best fit: 16 months", "narrow": {"s": "Prague:\n16 months"}})]},
        "metro": {"recolor": {"#1f5fa8": PRG}},
        "builders-2024": {"recolor": {"#1f5fa8": "ink", "ink": "grey", "grey": "#e6e6e3"}},
    }),
    "parking6/charts.json": ("compact-nonl", {
        "new-cars": {"end": {0: {"register": "register", "T&E pace": "T&E pace"}}, "padRight": {0: 78},
                     "callouts": [(0, {"x": 2022, "y": 4.5006045048311005, "dx": -12, "dy": -22, "anchor": "end",
                                       "s": "2022 → 2025: +2.3 cm", "narrow": {"s": "+2.3 cm\nto 2025"}})]},
    }),
}


def recolor(o, mp: dict) -> None:
    if isinstance(o, dict):
        if o.get("c") in mp:
            o["c"] = mp[o["c"]]
        for v in o.values():
            recolor(v, mp)
    elif isinstance(o, list):
        for v in o:
            recolor(v, mp)


def apply(chart: dict, st: dict) -> None:
    if "recolor" in st:
        recolor(chart["panels"], st["recolor"])
        recolor(chart.get("legend", []), st["recolor"])
    if "legend_recolor" in st:
        recolor(chart.get("legend", []), st["legend_recolor"])
    for p in chart["panels"]:
        for m in p["marks"]:
            for r in m.get("rows", []) if isinstance(m.get("rows"), list) else []:
                if isinstance(r, dict) and r.get("y") in st.get("rows", {}):
                    r["c"] = st["rows"][r["y"]]
            if m["type"] == "dots":
                for q in m["pts"]:
                    for key, c in st.get("pts", {}).items():
                        if isinstance(q, dict) and q.get("tip", "").startswith(key):
                            q["c"] = c
    for i, names in st.get("end", {}).items():
        labels = names if isinstance(names, dict) else {n: True for n in names}
        for m in chart["panels"][i]["marks"]:
            if m["type"] == "line" and m.get("name") in labels:
                m["end"] = labels[m["name"]]
    for i, pad in st.get("padRight", {}).items():
        chart["panels"][i]["padRight"] = pad
    for i, co in st.get("callouts", []):
        marks = chart["panels"][i]["marks"]
        marks[:] = [m for m in marks if not (m["type"] == "callout" and m["s"] == co["s"])]
        marks.append({"type": "callout", **co})
    if "legend" in st:
        chart["legend"] = st["legend"]
    for after, entry in st.get("legend_after", {}).items():
        leg = chart["legend"]
        if not any(e["label"] == entry["label"] for e in leg):
            k = next(j for j, e in enumerate(leg) if e["label"] == after)
            leg.insert(k + 1, entry)


def main() -> None:
    for rel, (style, stories) in STORY.items():
        f = A / rel
        charts = json.loads(f.read_text())
        for cid, st in stories.items():
            apply(charts[cid], st)
        if style == "indent":
            s = json.dumps(charts, ensure_ascii=False, indent=1) + "\n"
        else:
            s = json.dumps(charts, ensure_ascii=False, separators=(",", ":")) + ("\n" if style == "compact" else "")
        f.write_text(s)
        print(f"{rel}: {len(stories)} charts")


if __name__ == "__main__":
    main()
