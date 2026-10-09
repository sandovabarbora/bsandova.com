"""Chart specs for Part 2, Prague votes in rings (texts/prague-rings.html), read by assets/charts.js.

Every number comes from a published data file, taken exactly as the static figures take it:
assets/praha/metro2025.json (fig. 2, as tools/praha/figures_metro.py draws it) and assets/praha/rings_extended.json
with assets/praha/rings_robust.json (figs. 3-6, as tools/praha/figures_rings_extended.py draws them).
Fig. 1 is already an interactive map and is left alone. Reads the static figures' alt text from texts/prague-rings.html. Writes assets/praha/charts-rings.json.

    python3 tools/charts/prague_rings.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets" / "praha"
M = json.loads((A / "metro2025.json").read_text())
E = json.loads((A / "rings_extended.json").read_text())
R = json.loads((A / "rings_robust.json").read_text())

HELD = "#9a7b0a"  # the ochre the Part 2 figures use (figures_rings_extended.py, figures_metro.py)
NB = " "
DM = "../assets/praha/metro2025.json"
DE = "../assets/praha/rings_extended.json"
DR = "../assets/praha/rings_robust.json"


def n(v: float, dp: int = 2, sign: bool = False) -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign, + where asked."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else ("+" if sign and v > 0 else "")) + s


def pct(v: float, dp: int = 1) -> str:
    return n(v, dp) + " %"


def bin_label(b: str) -> str:
    return b.replace("-", "–")


charts = {}
# spec.alt is the static <img>'s alt, read from the article so the two cannot drift apart
HTML = (ROOT / "texts" / "prague-rings.html").read_text()
SVG = {"three-rulers": "02-three-rulers.svg", "attenuation": "07-attenuation.svg", "metro-equivalence": "09-metro-equivalence.svg",
       "steepening": "08-steepening.svg", "spec-curve": "10-spec-curve.svg"}
IMG_ALT = {k: re.search(r'<img[^>]*src="\.\./assets/praha/' + re.escape(f) + r'"[^>]*alt="([^"]*)"', HTML).group(1).replace("&amp;", "&")
           for k, f in SVG.items()}

# fig. 2 · three rulers: ANO and the Pirates by metro distance, centre distance and panel share
rulers = [("by_metro_distance", "distance to the metro", "km", "km"), ("by_centre_distance", "distance from Můstek", "km", "km"),
          ("by_panel_share", "flats in panel buildings", "%", "%")]
parties = [("ANO", "ANO", HELD, None, None), ("Piráti", "Pirates", "ink", "dash", "d")]
panels, trows = [], []
for i, (key, title, xlab, unit) in enumerate(rulers):
    bins = list(M[key])
    cats = [bin_label(b.replace(" km", "").replace(" %", "")) for b in bins]
    marks = []
    for p, name, c, dash, shape in parties:
        marks.append({"type": "line", "name": name, "c": c, "dash": dash, "notip": True,
                      "pts": [[cat, round(100 * M[key][b][p], 2)] for cat, b in zip(cats, bins)]})
    for p, name, c, dash, shape in parties:
        marks.append({"type": "dots", "c": c, "shape": shape, "r": 3.5,
                      "pts": [{"x": cat, "y": round(100 * M[key][b][p], 2),
                               "tip": f"{title}: {bin_label(b)}\n{name} {pct(100 * M[key][b][p])}\n"
                                      f"{n(M[key][b]['precincts'], 0)} precincts"}
                              for cat, b in zip(cats, bins)]})
    panels.append({"title": title, "h": 250,
                   "x": {"kind": "cat", "domain": cats, "label": xlab},
                   "y": {"kind": "linear", "domain": [0, 30], "ticks": [0, 5, 10, 15, 20, 25, 30],
                         "label": "% of valid votes" if i == 0 else None},
                   "marks": marks})
    for b in bins:
        trows.append([title, bin_label(b), n(M[key][b]["precincts"], 0), pct(100 * M[key][b]["ANO"]),
                      pct(100 * M[key][b]["Piráti"])])
charts["three-rulers"] = {
    "alt": IMG_ALT["three-rulers"],
    "legend": [{"label": "ANO", "c": HELD}, {"label": "Pirates", "c": "ink", "dash": "dash"}],
    "panels": panels,
    "table": {"cols": ["ruler", "group", "precincts", "ANO", "Pirates"], "rows": trows},
    "data": [DM],
}

# fig. 3 · attenuation: the estate gradient before and after holding education and citizenship equal.
# Gradients (and fig. 4's coefficients) show three decimals, the published precision: several sit exactly on a
# rounding tie (0.985, 0.565, 0.075) that the article's two-decimal figures resolve from the unrounded estimates.
h5 = R["H5_2021"]
att = [
    ("ANO 2025", E["H1_ANO"]["beta0_per10pp"], E["H1_ANO"]["beta1_per10pp"], E["H1_ANO"]["theta"]),
    ("ANO 2025, + age", E["H1_ANO_with_age"]["beta0_per10pp"], E["H1_ANO_with_age"]["beta1_per10pp"], E["H1_ANO_with_age"]["theta"]),
    ("ANO 2021", h5["ANO"]["beta0"], h5["ANO"]["beta1"], h5["ANO"]["theta"]),
    ("SPOLU 2025", E["H1_SPOLU"]["beta0_per10pp"], E["H1_SPOLU"]["beta1_per10pp"], E["H1_SPOLU"]["theta"]),
    ("SPOLU 2021", h5["SPOLU"]["beta0"], h5["SPOLU"]["beta1"], h5["SPOLU"]["theta"]),
]


def att_tip(lab, b0, b1, th):
    return (f"{lab}\nwithout composition {n(b0, 3)}\nwith education and citizenship {n(b1, 3)}\n"
            f"half the original {n(b0 / 2)}\ngoes with composition {pct(100 * th, 0)}")


charts["attenuation"] = {
    "alt": IMG_ALT["attenuation"],
    "legend": [{"label": "without composition", "c": "light", "shape": "o"},
               {"label": "education and citizenship held equal", "c": HELD},
               {"label": "half the original gradient", "c": "grey", "shape": "d"}],
    "panels": [{"h": 250,
                "x": {"kind": "linear", "domain": [-1.0, 1.3], "ticks": [-1.0, -0.5, 0, 0.5, 1.0],
                      "label": "party points per 10 pp more panel flats", "tickfmt": {"dp": 1}},
                "y": {"kind": "cat", "domain": [r[0] for r in att]},
                "marks": [
                    {"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                    {"type": "range", "rows": [{"y": lab, "mid": b0 / 2, "shape": "d", "fill": "grey", "tip": att_tip(lab, b0, b1, th)}
                                               for lab, b0, b1, th in att]},
                    {"type": "arrow", "c": HELD, "rows": [{"y": lab, "from": b0, "to": b1, "tip": att_tip(lab, b0, b1, th)}
                                                         for lab, b0, b1, th in att]},
                    *[{"type": "text", "x": 1.28, "y": lab, "anchor": "end", "c": "ink", "s": pct(100 * th, 0)} for lab, b0, b1, th in att],
                ]}],
    "table": {"cols": ["", "without composition", "with education and citizenship", "half the original", "share going with composition"],
              "rows": [[lab, n(b0, 3), n(b1, 3), n(b0 / 2), pct(100 * th, 0)] for lab, b0, b1, th in att]},
    "data": [DE, DR],
}

# fig. 4 · the metro's coefficient with its 90 % interval against the equivalence band
sp = R["spatial"]
met = [("grid clusters, 2025", E["H2"]["estimate"], *E["H2"]["ci90_used"]),
       ("precincts, 2025", R["precinct_level"]["metro"]["gamma"], *R["precinct_level"]["metro"]["ci90"]),
       ("grid clusters, 2021", h5["metro"]["gamma"], *h5["metro"]["ci90"]),
       ("spatial error model", sp["sem_metro"], sp["sem_metro"] - 1.645 * sp["sem_se_metro"], sp["sem_metro"] + 1.645 * sp["sem_se_metro"])]
margin = E["H2"]["margin"]
charts["metro-equivalence"] = {
    "alt": IMG_ALT["metro-equivalence"],
    "legend": [{"label": "estimate and 90 % interval", "c": HELD, "shape": "o"},
               {"label": f"± {n(margin)}: too small to matter", "c": "grey", "shape": "box", "o": 0.14}],
    "panels": [{"h": 220,
                "x": {"kind": "linear", "domain": [-0.6, 0.4], "ticks": [-0.6, -0.4, -0.2, 0, 0.2, 0.4],
                      "label": "ANO points per doubling of metro distance", "tickfmt": {"dp": 1}},
                "y": {"kind": "cat", "domain": [r[0] for r in met]},
                "marks": [
                    {"type": "span", "v0": -margin, "v1": margin, "c": "grey", "o": 0.14},
                    {"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                    {"type": "range", "c": HELD, "w": 2,
                     "rows": [{"y": lab, "mid": est, "lo": lo, "hi": hi,
                               "tip": f"{lab}\n{n(est, 3, True)} per doubling\n90 % interval {n(lo, 3, True)} to {n(hi, 3, True)}"}
                              for lab, est, lo, hi in met]},
                ]}],
    "table": {"cols": ["", "estimate", "90 % interval, low", "90 % interval, high"],
              "rows": [[lab, n(est, 3, True), n(lo, 3, True), n(hi, 3, True)] for lab, est, lo, hi in met]},
    "data": [DE, DR],
}

# fig. 5 · ANO's estate gradient by election, matched precincts, with the 5 % and 20 % matching rules as a band
yrs = [2017, 2021, 2025]
ys = E["H3"]["panel_slope_per10pp_by_year"]
s5, s20 = E["H3_sensitivity"]["tol_5pct"]["by_year"], E["H3_sensitivity"]["tol_20pct"]["by_year"]
f2 = {"dp": 2}
charts["steepening"] = {
    "alt": IMG_ALT["steepening"],
    "legend": [{"label": f"{n(E['H3']['n_precincts'], 0)} matched precincts", "c": HELD},
               {"label": f"5 % ({E['H3_sensitivity']['tol_5pct']['n']}) and 20 % ({E['H3_sensitivity']['tol_20pct']['n']}) matching rules",
                "c": HELD, "shape": "box", "o": 0.25}],
    "panels": [{"h": 240,
                "x": {"kind": "linear", "domain": [2016, 2026], "ticks": yrs, "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [0, 1.0], "ticks": [0, 0.2, 0.4, 0.6, 0.8, 1.0], "tickfmt": {"dp": 1},
                      "label": "ANO points per 10 pp panel"},
                "marks": [
                    {"type": "area", "name": "5 %–20 % rules", "c": HELD, "o": 0.15, "fmt": f2,
                     "pts": [[y, s5[str(y)], s20[str(y)]] for y in yrs]},
                    {"type": "line", "name": "matched", "c": HELD, "w": 2.4, "dots": True, "fmt": f2,
                     "pts": [[y, ys[str(y)]] for y in yrs]},
                    *[{"type": "text", "x": y, "y": ys[str(y)] + 0.06, "anchor": "middle", "c": "ink", "s": n(ys[str(y)])} for y in yrs],
                ]}],
    "table": {"cols": ["election", "matched (10 % rule)", "5 % rule", "20 % rule"],
              "rows": [[str(y), n(ys[str(y)]), n(s5[str(y)]), n(s20[str(y)])] for y in yrs]},
    "data": [DE],
}

# fig. 6 · specification curve: share of ANO's estate gradient going with composition, 48 specifications sorted
spec = sorted(R["robustness"]["14_specification_curve"]["rows"], key=lambda x: x["ANO_theta"])
SAMPLE = {"all": "all clusters", ">=300": "precincts with 300+ registered voters", "homogeneous": "homogeneous squares only"}
PANEL = {"4+41": "panel broad", "4": "panel narrow"}
SE = {"wild": "bootstrap errors", "conley": "spatial errors"}
VERDICT = {"place beyond composition": "significantly less than half", "indeterminate": "indeterminate"}


def spec_desc(x: dict) -> str:
    return (f"{'weighted' if x['weighted'] else 'unweighted'}, by {x['alloc']}, {PANEL[x['panel']]},\n"
            f"{SAMPLE[x['sample']]}, {SE[x['se']]}")


charts["spec-curve"] = {
    "alt": IMG_ALT["spec-curve"],
    "legend": [{"label": "significantly less than half going with composition", "c": HELD, "shape": "o"},
               {"label": "indeterminate", "c": "light", "shape": "o"},
               {"label": "half", "c": "ink", "dash": "dash"}],
    "panels": [{"h": 240,
                "x": {"kind": "linear", "domain": [0, len(spec) + 1], "ticks": [], "nogrid": True,
                      "label": f"{len(spec)} specifications, sorted"},
                "y": {"kind": "linear", "domain": [0, 60], "ticks": [0, 10, 20, 30, 40, 50, 60], "label": "share going with composition (%)"},
                "marks": [
                    {"type": "rule", "axis": "y", "v": 50, "c": "ink", "dash": "dash", "label": "half", "anchor": "end"},
                    {"type": "dots", "r": 3.5,
                     "pts": [{"x": i + 1, "y": round(100 * x["ANO_theta"], 1), "c": HELD if x["ANO"] == "place beyond composition" else "light",
                              "tip": f"{spec_desc(x)}\n{n(x['n'], 0)} clusters\ngoes with composition {pct(100 * x['ANO_theta'], 0)}\n{VERDICT[x['ANO']]}"}
                             for i, x in enumerate(spec)]},
                ]}],
    "table": {"cols": ["#", "weights", "allocation", "panel", "sample", "errors", "clusters", "share going with composition", "verdict"],
              "rows": [[str(i + 1), "votes" if x["weighted"] else "none", x["alloc"], PANEL[x["panel"]].split()[1], SAMPLE[x["sample"]],
                        SE[x["se"]].split()[0], n(x["n"], 0), pct(100 * x["ANO_theta"], 0), VERDICT[x["ANO"]]]
                       for i, x in enumerate(spec)]},
    "data": [DR],
}

(A / "charts-rings.json").write_text(json.dumps(charts, ensure_ascii=False, indent=1) + "\n")
print(f"wrote assets/praha/charts-rings.json ({len(charts)} charts)")
