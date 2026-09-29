"""Chart specs for the parking article (texts/prague-parking.html), read by assets/charts.js.

Every number comes from a published data file: assets/parking/figures-data.json (the first estimate's model run,
written by parking_text01_data.py), assets/parking2/eea_cz.json (the wheelbase estimate) and assets/parking6/*.json
(this study). Writes assets/parking6/charts.json.

    python3 tools/charts/parking.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"
T1 = json.loads((A / "parking/figures-data.json").read_text())
EEA = json.loads((A / "parking2/eea_cz.json").read_text())
H = json.loads((A / "parking6/h2.json").read_text())
E1 = json.loads((A / "parking6/e1.json").read_text())
E4 = json.loads((A / "parking6/e4.json").read_text())
P2 = json.loads((A / "parking6/part2_correction.json").read_text())

NB = " "


def n(v: float, dp: int = 0, unit: str = "") -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "") + s + unit


def pct(v: float, dp: int = 1) -> str:
    return n(v, dp, " %")


D1 = "assets/parking/figures-data.json"
DE = "assets/parking2/eea_cz.json"
charts = {}

# fig. 1 · length model against area model (first estimate)
mc = T1["model_comparison"]
rows = [("length model (only length grows)", mc["length"], "held"), ("area model (length and width grow)", mc["area"], "grey")]
charts["model-comparison"] = {
    "alt": "Horizontal bars: stalls lost 2012–2025 under the length model and the area model, with ranges across assumptions.",
    "panels": [{"h": 150, "x": {"kind": "linear", "domain": [0, 12000], "ticks": [0, 3000, 6000, 9000, 12000], "label": "stalls lost 2012–2025", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": [r[0] for r in rows]},
                "marks": [{"type": "hbar", "rows": [{"y": lab, "x1": d["central"], "lo": d["lo"], "hi": d["hi"], "c": c,
                                                     "label": f"{n(d['central'])} ({n(d['lo'])}–{n(d['hi'])})",
                                                     "tip": f"{lab}\ncentral {n(d['central'])} stalls\nrange {n(d['lo'])}–{n(d['hi'])}"}
                                                    for lab, d, c in rows]}]}],
    "table": {"cols": ["model", "central", "low", "high"], "rows": [[lab, n(d["central"]), n(d["lo"]), n(d["hi"])] for lab, d, _ in rows]},
    "data": [D1],
}

# fig. 2 · new cars in the register
ys = sorted(int(y) for y in H["annual_means_mm"])
v = [H["annual_means_mm"][str(y)] / 1000 for y in ys]
y0 = sum(v[:11]) / 11
c = H["estimates"]["comparator_C_cm"] / 100 / 10
v22 = v[ys.index(2022)]
lf = {"dp": 3, "unit": " m"}
charts["new-cars"] = {
    "alt": "Line chart of the mean length of a new car registered in Czechia, 2012 to 2025, with the slope of the EEA wheelbase route and two extrapolations after 2022.",
    "legend": [{"label": "register, cars new to CZ (post-stratified)", "c": "held"}, {"label": "EEA wheelbase route (comparator slope)", "c": "grey", "dash": "dash"},
               {"label": "T&E pace 2022→2025 (+6.0 cm)", "c": "light", "dash": "dot"}, {"label": "wheelbase estimate, extrapolated (+3.0 cm)", "c": "ink", "dash": "long"}],
    "panels": [{"h": 270, "x": {"kind": "linear", "domain": [2011.5, 2025.5], "ticks": list(range(2012, 2026, 2)), "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [4.34, 4.54], "label": "mean length of a new car · m", "tickfmt": {"dp": 2}},
                "marks": [
                    {"type": "line", "name": "comparator slope", "c": "grey", "dash": "dash", "w": 1.4, "fmt": lf, "notip": True,
                     "pts": [[2012, y0 - 5 * c], [2022, y0 + 5 * c]]},
                    {"type": "line", "name": "T&E pace", "c": "light", "dash": "dot", "w": 1.6, "fmt": lf, "pts": [[2022, v22], [2025, v22 + 0.06]]},
                    {"type": "line", "name": "wheelbase est.", "c": "ink", "dash": "long", "w": 1.2, "fmt": lf, "pts": [[2022, v22], [2025, v22 + 0.03]]},
                    {"type": "line", "name": "register", "c": "held", "dots": True, "fmt": lf, "pts": [[y, round(x, 4)] for y, x in zip(ys, v)]},
                ]}],
    "table": {"cols": ["year", "mean length of a new car (m)"], "rows": [[str(y), f"{x:.3f}"] for y, x in zip(ys, v)]},
    "data": ["assets/parking6/h2.json"],
}

# fig. 3 · the two registered tests
T = H["tests"]
d = H["estimates"]["delta_margin_cm"]
cmf = {"dp": 1, "unit": " cm", "sign": True}
charts["tests"] = {
    "alt": "Left: the difference between the register and the wheelbase route with its 90 % interval against the ±4.4 cm margin. Right: new-car growth 2022 to 2025 with its 95 % interval against 3.0, 4.5 and 6.0 cm.",
    "panels": [
        {"w": 1.1, "h": 130, "title": "H2a · register − EEA route, cm (90 % interval)",
         "x": {"kind": "linear", "domain": [-8, 12], "fmt": {"dp": 0}}, "y": {"kind": "linear", "domain": [-1, 1], "ticks": [], "nogrid": True},
         "marks": [{"type": "span", "v0": -d, "v1": d, "c": "held", "label": f"±{d:.1f} cm margin"},
                   {"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                   {"type": "range", "c": "held", "rows": [{"y": 0, "lo": T["ci90_d"][0], "hi": T["ci90_d"][1], "mid": T["d_cm"],
                                                            "tip": f"H2a · register − wheelbase route\n{n(T['d_cm'], 1, ' cm')} apart\n90 %: {n(T['ci90_d'][0], 1)} to {n(T['ci90_d'][1], 1, ' cm')}\nmargin ±{d:.1f} cm · p = {T['p_tost']:.2f}\ninconclusive (underpowered)"}]}]},
        {"w": 1, "h": 130, "title": "H2b · new-car length 2022→2025, cm (95 %)",
         "x": {"kind": "linear", "domain": [-1, 7.5], "fmt": {"dp": 0}}, "y": {"kind": "linear", "domain": [-1, 1], "ticks": [], "nogrid": True},
         "marks": [{"type": "rule", "axis": "x", "v": 3.0, "c": "grey", "dash": "dash", "label": "wheelbase est. +3.0", "anchor": "end"},
                   {"type": "rule", "axis": "x", "v": 4.5, "c": "light", "dash": "dash", "label": "midpoint", "dy": 118},
                   {"type": "rule", "axis": "x", "v": 6.0, "c": "ink", "dash": "dash", "label": "T&E +6.0"},
                   {"type": "range", "c": "held", "rows": [{"y": 0, "lo": T["ci95_delta2"][0], "hi": T["ci95_delta2"][1], "mid": T["delta2_cm"],
                                                            "tip": f"H2b · new cars 2022→2025\n{n(T['delta2_cm'], 1, ' cm')}\n95 %: {n(T['ci95_delta2'][0], 1)} to {n(T['ci95_delta2'][1], 1, ' cm')}\nagainst T&E's 6.0 cm: p = {T['p_h2b']:.3f}\nsupported"}]}]},
    ],
    "table": {"cols": ["test", "estimate (cm)", "interval (cm)", "p", "result"],
              "rows": [["H2a register − wheelbase route", f"{T['d_cm']:+.1f}", f"{T['ci90_d'][0]:.1f} to {T['ci90_d'][1]:.1f} (90 %)", f"{T['p_tost']:.2f}", "inconclusive (underpowered)"],
                       ["H2b growth 2022→2025", f"{T['delta2_cm']:+.1f}", f"{T['ci95_delta2'][0]:.1f} to {T['ci95_delta2'][1]:.1f} (95 %)", f"{T['p_h2b']:.3f}", "supported"]]},
    "data": ["assets/parking6/h2.json"],
}

# fig. 4 · wheelbase and implied length (wheelbase estimate, M1 only)
yrs = [int(y) for y in EEA["years"]]
w = [EEA["wheelbase_mm"][str(y)]["mean"] for y in yrs]
cov = [EEA["wheelbase_mm"][str(y)]["coverage"] for y in yrs]
w19 = EEA["wheelbase_mm"]["2019"]["mean"]
n_ = len(yrs)
mx, my = sum(yrs) / n_, sum(w) / n_
slope = sum((a - mx) * (b - my) for a, b in zip(yrs, w)) / sum((a - mx) ** 2 for a in yrs)
icpt = my - slope * mx
ally = list(range(2010, 2026))
wall = [w[yrs.index(y)] if y <= 2022 else slope * y + icpt for y in ally]
L = lambda r, wv: 4.30 + (wv - w19) / r / 1000  # noqa: E731
TE = {2010: 4.19, 2015: 4.24, 2020: 4.28, 2025: 4.38}
charts["wheelbase"] = {
    "alt": "Left: mean wheelbase of new cars registered in Czechia, 2010 to 2022. Right: the length it implies at ratio 0.618 with a band for 0.52 to 0.70, against the T&E EU series.",
    "legend": [{"label": "CZ wheelbase → length, ratio 0.618", "c": "held"}, {"label": "ratio 0.52–0.70", "c": "held", "shape": "box", "o": 0.25},
               {"label": "CZ, extrapolated after 2022", "c": "held", "dash": "dash"}, {"label": "T&E, EU top-100 new cars", "c": "ink"},
               {"label": "Závadská 2019 (anchor)", "c": "grey", "shape": "o"}],
    "panels": [
        {"h": 250, "title": "wheelbase of new cars registered in CZ · mm (M1 only)",
         "x": {"kind": "linear", "domain": [2009.5, 2022.5], "ticks": [2010, 2014, 2018, 2022], "fmt": {"dp": 0, "nogroup": True}},
         "y": {"kind": "linear", "domain": [2580, 2710], "tickfmt": {"dp": 0, "nogroup": True}},
         "marks": [{"type": "line", "name": "wheelbase", "c": "held", "dots": True, "fmt": {"dp": 0, "unit": " mm", "nogroup": True},
                    "pts": [[y, round(x, 1)] for y, x in zip(yrs, w)]},
                   {"type": "dots", "c": "grey", "pts": [{"x": y, "y": x, "label": f"{round(100 * (1 - cv))} % imputed", "dy": -9,
                                                           "tip": f"{y}: {x:.0f} mm\n{round(100 * (1 - cv))} % of cars imputed from the model's other years"}
                                                          for y, x, cv in zip(yrs, w, cov) if cv <= 0.99]}]},
        {"h": 250, "title": "length of a new car · m",
         "x": {"kind": "linear", "domain": [2009.5, 2025.5], "ticks": [2010, 2015, 2020, 2025], "fmt": {"dp": 0, "nogroup": True}},
         "y": {"kind": "linear", "domain": [4.12, 4.46], "tickfmt": {"dp": 2}},
         "marks": [{"type": "area", "name": "ratio 0.52–0.70", "c": "held", "fmt": {"dp": 3, "unit": " m"},
                    "pts": [[y, round(L(0.70, x), 4), round(L(0.52, x), 4)] for y, x in zip(ally, wall)]},
                   {"type": "line", "name": "CZ, ratio 0.618", "c": "held", "fmt": {"dp": 3, "unit": " m"},
                    "pts": [[y, round(L(0.618, x), 4)] for y, x in zip(ally, wall) if y <= 2022]},
                   {"type": "line", "name": "CZ, extrapolated", "c": "held", "dash": "dash", "fmt": {"dp": 3, "unit": " m"},
                    "pts": [[y, round(L(0.618, x), 4)] for y, x in zip(ally, wall) if y >= 2022]},
                   {"type": "line", "name": "T&E", "c": "ink", "w": 1.4, "dots": True, "fmt": {"dp": 2, "unit": " m"}, "pts": [[y, x] for y, x in TE.items()]},
                   {"type": "dots", "c": "grey", "pts": [{"x": 2019, "y": 4.30, "r": 5.5, "tip": "Závadská 2019: 4.30 m\n111 best-selling new cars in Czechia (anchor)"}]}]},
    ],
    "table": {"cols": ["year", "wheelbase (mm)", "share imputed", "length at 0.618 (m)"],
              "rows": [[str(y), f"{x:.0f}", f"{round(100 * (1 - cv))} %", f"{L(0.618, x):.3f}"] for y, x, cv in zip(yrs, w, cov)]},
    "data": [DE],
}

# fig. 5 · the eight best-selling models
def model_name(m: str) -> str:
    return m.title().replace("Skoda ", "Š ").replace("I 30", "i30")


comp = []
for key, cc, yr in (("top_2012", "grey", "2012"), ("top_2022", "held", "2022")):
    for r in EEA["composition"][key]:
        if r["wheelbase_mm"]:
            comp.append((yr, model_name(r["model"]), r["wheelbase_mm"], r["share_pct"], cc))
charts["models"] = {
    "alt": "Scatter of the eight best-selling models in Czechia in 2012 and 2022, wheelbase against share of registrations.",
    "legend": [{"label": "2012", "c": "grey", "shape": "o"}, {"label": "2022", "c": "held", "shape": "o"}],
    "panels": [{"h": 300, "x": {"kind": "linear", "domain": [2420, 2860], "label": "wheelbase · mm", "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [0, 14], "ticks": [0, 2, 4, 6, 8, 10, 12, 14], "label": "share of CZ registrations · %", "tickfmt": {"dp": 0}},
                "marks": [{"type": "dots", "pts": [{"x": round(wb, 1), "y": round(sh, 2), "c": cc, "label": nm,
                                                    "tip": f"{nm}, {yr}\n{sh:.1f} % of registrations\nwheelbase {wb:.0f} mm"} for yr, nm, wb, sh, cc in comp]}]}],
    "table": {"cols": ["year", "model", "share (%)", "wheelbase (mm)"], "rows": [[yr, nm, f"{sh:.1f}", f"{wb:.0f}"] for yr, nm, wb, sh, _ in comp]},
    "data": [DE],
}

# fig. 6 · new car against fleet (first estimate)
lag = T1["fleet_lag"]
fl = lag["fleet"]
charts["fleet-lag"] = {
    "alt": "Top: new-car length rising faster than fleet length, 2005–2025. Bottom: mean fleet age rising from 13.6 to 16.7 years.",
    "legend": [{"label": "new car (T&E, top 100 EU)", "c": "ink"}, {"label": "Czech fleet (Weibull, main case)", "c": "held"},
               {"label": "fleet under other age distributions", "c": "held", "shape": "box", "o": 0.25}],
    "panels": [
        {"h": 240, "title": "mean car length · m",
         "x": {"kind": "linear", "domain": [2004.5, 2025.5], "ticks": [2005, 2012, 2015, 2020, 2025], "fmt": {"dp": 0, "nogroup": True}},
         "y": {"kind": "linear", "domain": [3.95, 4.42], "tickfmt": {"dp": 2}},
         "marks": [{"type": "area", "name": "other age distributions", "c": "held", "fmt": {"dp": 3, "unit": " m"},
                    "pts": [[y, min(fl[s][i] for s in fl), max(fl[s][i] for s in fl)] for i, y in enumerate(lag["years"])]},
                   {"type": "rule", "axis": "x", "v": 2012, "c": "grey", "dash": "dot"}, {"type": "rule", "axis": "x", "v": 2025, "c": "grey", "dash": "dot"},
                   {"type": "line", "name": "new car", "c": "ink", "fmt": {"dp": 3, "unit": " m"}, "pts": [[y, x] for y, x in zip(lag["years"], lag["new_car"])]},
                   {"type": "line", "name": "fleet", "c": "held", "fmt": {"dp": 3, "unit": " m"}, "pts": [[y, x] for y, x in zip(lag["years"], fl["weibull"])]}]},
        {"h": 130, "title": "mean fleet age · years",
         "x": {"kind": "linear", "domain": [2004.5, 2025.5], "ticks": [2005, 2012, 2015, 2020, 2025], "fmt": {"dp": 0, "nogroup": True}},
         "y": {"kind": "linear", "domain": [11.5, 17.5], "ticks": [12, 14, 16], "tickfmt": {"dp": 0}},
         "marks": [{"type": "rule", "axis": "x", "v": 2012, "c": "grey", "dash": "dot"}, {"type": "rule", "axis": "x", "v": 2025, "c": "grey", "dash": "dot"},
                   {"type": "line", "name": "mean age", "c": "grey", "fmt": {"dp": 1, "unit": " years"}, "pts": [[y, x] for y, x in zip(lag["years"], lag["age"])]}]},
    ],
    "table": {"cols": ["year", "new car (m)", "fleet, Weibull (m)", "fleet, exponential (m)", "fleet, uniform (m)", "mean age (years)"],
              "rows": [[str(y), f"{lag['new_car'][i]:.3f}", f"{fl['weibull'][i]:.3f}", f"{fl['exponential'][i]:.3f}", f"{fl['uniform'][i]:.3f}", f"{lag['age'][i]:.1f}"]
                       for i, y in enumerate(lag["years"])]},
    "data": [D1],
}

# fig. 7 · the estimates
lossrows = [("this study, all parallel unmarked (θ₁)", E1["theta"], "held"), ("a quarter of parallel bays painted", E1["theta_painted_share_0.25"], "held"),
            ("half of parallel bays painted", E1["theta_painted_share_0.5"], "held"), ("per parallel space (θ₁ᵘ)", E1["theta_u"], "ink"),
            ("per parallel space, gap ∝ length", E1["theta_u_prop"], "ink")]
pts = [("first estimate (T&E series)", 1.60), ("wheelbase estimate, M1 only", 1.325),
       ("wheelbase estimate, M1 + M1G", P2["m1_m1g"]["scenarios"]["central"]["loss_pct"])]
charts["loss"] = {
    "alt": "Dot and interval chart in per cent: this study's estimates with their intervals, and the two earlier estimates as diamonds, against dashed band edges at 1 and 2.5 per cent.",
    "panels": [{"h": 300, "x": {"kind": "linear", "domain": [0, 4.6], "ticks": [0, 1, 2, 3, 4], "label": "more cars today's kerb would hold with 2012's cars · %", "fmt": {"dp": 1}},
                "y": {"kind": "cat", "domain": [r[0] for r in lossrows] + [p[0] for p in pts]},
                "marks": [{"type": "rule", "axis": "x", "v": 1.0, "c": "light", "dash": "dash"}, {"type": "rule", "axis": "x", "v": 2.5, "c": "light", "dash": "dash"},
                          {"type": "range", "rows": [{"y": lab, "lo": 100 * r["q025"], "hi": 100 * r["q975"], "mid": 100 * r["median"], "c": cc,
                                                      "label": pct(100 * r["median"]),
                                                      "tip": f"{lab}\nmedian {pct(100 * r['median'])}\n2.5–97.5 %: {100 * r['q025']:.1f}–{pct(100 * r['q975'])}"}
                                                     for lab, r, cc in lossrows]
                           + [{"y": lab, "mid": val, "shape": "d", "label": pct(val), "tip": f"{lab}\npoint estimate {pct(val)}"} for lab, val in pts]}]}],
    "table": {"cols": ["estimate", "median (%)", "2.5 % (%)", "97.5 % (%)"],
              "rows": [[lab, f"{100 * r['median']:.1f}", f"{100 * r['q025']:.1f}", f"{100 * r['q975']:.1f}"] for lab, r, _ in lossrows]
              + [[lab, f"{val:.1f}", "", ""] for lab, val in pts]},
    "data": ["assets/parking6/e1.json", "assets/parking6/part2_correction.json"],
}

# fig. 8 · width against the stall (first estimate)
W = T1["width"]
wy = W["years"]
charts["width"] = {
    "alt": "Car width 2005–2040 against the 2.00 m marked stall and the 1.75 m design vehicle of ČSN 73 6056.",
    "legend": [{"label": "new car, no mirrors (T&E)", "c": "ink"}, {"label": "T&E extrapolation", "c": "ink", "dash": "dash"},
               {"label": "new car with mirrors (+20 cm)", "c": "ink", "dash": "dot"}, {"label": "Czech fleet, no mirrors", "c": "held"}],
    "panels": [{"h": 280, "x": {"kind": "linear", "domain": [2004.5, 2040.5], "ticks": [2005, 2010, 2015, 2020, 2025, 2030, 2035, 2040], "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [1.62, 2.06], "label": "car width · m", "tickfmt": {"dp": 2}},
                "marks": [{"type": "rule", "axis": "y", "v": 2.00, "c": "ink", "w": 1.2, "label": "marked parallel stall, ČSN 73 6056: 2.00 m", "anchor": "end"},
                          {"type": "rule", "axis": "y", "v": 1.75, "c": "grey", "dash": "dash", "label": "design vehicle, ČSN 73 6056 (2011): 1.75 m", "anchor": "end"},
                          {"type": "line", "name": "new car", "c": "ink", "fmt": {"dp": 3, "unit": " m"}, "pts": [[y, x] for y, x in zip(wy, W["new_car"]) if y <= 2025]},
                          {"type": "line", "name": "T&E extrapolation", "c": "ink", "dash": "dash", "w": 1.6, "fmt": {"dp": 3, "unit": " m"}, "pts": [[y, x] for y, x in zip(wy, W["new_car"]) if y >= 2025]},
                          {"type": "line", "name": "with mirrors", "c": "ink", "dash": "dot", "w": 1.4, "fmt": {"dp": 3, "unit": " m"}, "pts": [[y, round(x + 0.20, 4)] for y, x in zip(wy, W["new_car"]) if y <= 2025]},
                          {"type": "line", "name": "fleet", "c": "held", "fmt": {"dp": 3, "unit": " m"}, "pts": [[y, x] for y, x in zip(wy, W["fleet"]) if y <= 2025]}]}],
    "table": {"cols": ["year", "new car (m)", "with mirrors (m)", "fleet (m)"],
              "rows": [[str(y), f"{a:.3f}", f"{a + 0.2:.3f}" if y <= 2025 else "", f"{b:.3f}" if y <= 2025 else ""] for y, a, b in zip(wy, W["new_car"], W["fleet"])]},
    "data": [D1],
}

# fig. 9 · subsidy
cz = E4["size"]["central"]
lv = E4["level_bracket_kc_per_year"]
sub = [("size: long vs short car, at today's 1 200 Kč", cz["X_p90_minus_p10_kc"], "held"),
       ("size: the same, at the second-car price", E4["size_at_bracket_ends_kc"]["at_second_car_price"], "held"),
       ("size: the same, at the reserved-bay fee", E4["size_at_bracket_ends_kc"]["at_OZV"], "held"),
       ("level: second-car price − 1 200", lv["lower_second_car_price"]["subsidy"], "ink"),
       ("level: reserved-bay fee − 1 200", lv["upper_OZV_10kc_m2_day"]["subsidy"], "ink")]
rnd = lambda x: round(x, -1) if x < 1000 else round(x, -2)  # noqa: E731
charts["subsidy"] = {
    "alt": "Horizontal bars on a log scale in Kč a year: the size component of the implicit subsidy at three price levels, and the two ends of the level bracket.",
    "legend": [{"label": "size component (long − short car)", "c": "held", "shape": "box", "o": 0.85}, {"label": "level of the implicit subsidy (forgone rent)", "c": "ink", "shape": "box", "o": 0.85}],
    "panels": [{"h": 240, "x": {"kind": "log", "domain": [50, 200000], "ticks": [100, 1000, 10000, 100000], "label": "Kč a year per car, log scale", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": [s[0] for s in sub]},
                "marks": [{"type": "hbar", "rows": [{"y": lab, "x0": 50, "x1": val, "c": cc, "label": n(rnd(val), 0, " Kč"),
                                                     "tip": f"{lab}\nabout {n(rnd(val), 0, ' Kč')} a year"} for lab, val, cc in sub]}]}],
    "table": {"cols": ["component", "Kč a year"], "rows": [[lab, n(rnd(val))] for lab, val, _ in sub]},
    "data": ["assets/parking6/e4.json"],
}

# fig. 10 · size effect against Praha 7's permits
sc = P2["m1_m1g"]["scenarios"]
per = {k: sc[k]["stalls_lost"] / 13 for k in ("central", "ratio_high", "ratio_low")}
charts["size-vs-permits"] = {
    "alt": "Two bars: stalls lost to longer cars a year across all paid zones, with a whisker for the ratio's spread, against 280 new residential permits a year in Praha 7 alone.",
    "panels": [{"h": 130, "x": {"kind": "linear", "domain": [0, 420], "label": "a year", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": ["Prague, all zones: stalls lost to longer cars", "Praha 7 alone: new parking permits"]},
                "marks": [{"type": "hbar", "rows": [
                    {"y": "Prague, all zones: stalls lost to longer cars", "x1": per["central"], "lo": per["ratio_high"], "hi": per["ratio_low"], "c": "held",
                     "label": f"{per['central']:.0f} ({per['ratio_high']:.0f}–{per['ratio_low']:.0f})",
                     "tip": f"stalls lost to longer cars, all paid zones\n{per['central']:.0f} a year ({per['ratio_high']:.0f}–{per['ratio_low']:.0f})\n{n(sc['central']['stalls_lost'])} over 2012–2025, spread evenly"},
                    {"y": "Praha 7 alone: new parking permits", "x1": 280, "c": "grey", "label": "280",
                     "tip": "new residential permits in Praha 7\n280 a year on average since 2018\nDeník N, from Praha 7's data"}]}]}],
    "table": {"cols": ["", "a year", "range"], "rows": [["stalls lost to longer cars, all zones", f"{per['central']:.0f}", f"{per['ratio_high']:.0f}–{per['ratio_low']:.0f}"],
                                                    ["new permits, Praha 7", "280", ""]]},
    "data": ["assets/parking6/part2_correction.json"],
}

# fig. 11 · tornado
mv = E1["tipping"]["moves"]
base = 100 * E1["tipping"]["central_theta"]
lab = {"u": "pre-2010 cars' lengths (±1)", "p": "reference pitch 4.9–5.5 m", "a12": "2012 mean age 13.3–14.1",
       "e": "age definition ±0.5 yr", "k": "survival shape k 1.4–1.6"}
order = sorted(lab, key=lambda k: -abs(max(mv[k]["theta_at_ends"].values()) - min(mv[k]["theta_at_ends"].values())))
torn = [(lab[k], sorted(100 * x for x in mv[k]["theta_at_ends"].values())) for k in order]
charts["tornado"] = {
    "legend": [{"label": f"central θ₁ {base:.2f} %", "c": "ink"}, {"label": "band edges 1.0 and 2.5 %", "c": "light", "dash": "dash"}],
    "alt": f"Tornado chart of θ₁ at the ends of each input's range, others held central, around a central {base:.2f} per cent; none crosses the band edges at 1.0 and 2.5.",
    "panels": [{"h": 220, "x": {"kind": "linear", "domain": [0.8, 2.7], "label": "θ₁ at each end of the input's range · %", "fmt": {"dp": 1}},
                "y": {"kind": "cat", "domain": [t[0] for t in torn]},
                "marks": [{"type": "rule", "axis": "x", "v": 1.0, "c": "light", "dash": "dash"}, {"type": "rule", "axis": "x", "v": 2.5, "c": "light", "dash": "dash"},
                          {"type": "hbar", "o": 0.8, "rows": [{"y": t, "x0": a, "x1": b, "c": "held", "label": f"{a:.2f}–{b:.2f}",
                                                                "tip": f"{t}\nθ₁ from {a:.2f} % to {b:.2f} %"} for t, (a, b) in torn]},
                          {"type": "rule", "axis": "x", "v": base, "c": "ink", "tip": f"central θ₁ {base:.2f} %"}]}],
    "table": {"cols": ["input", "θ₁ low (%)", "θ₁ high (%)"], "rows": [[t, f"{a:.2f}", f"{b:.2f}"] for t, (a, b) in torn]},
    "data": ["assets/parking6/e1.json"],
}

# fig. 12 · gap sensitivity (first estimate)
gs = T1["gap_sensitivity"]
gl = {"te_park": ("Czech fleet, T&E series (main case)", "held"), "te_novy": ("new registrations EU, T&E series", "grey"),
      "cr_tempo_2cm": ("+2 cm a year (Czech media rate, upper bound)", "ink")}
g = T1["gaps_m"]
gmarks = []
for k, (name, cc) in list(gl.items())[:1]:
    gmarks.append({"type": "area", "name": f"{name.split(',')[0]} · parallel 50–85 %", "c": cc, "o": 0.14, "fmt": {"dp": 0, "unit": " stalls"},
                   "pts": [[x, lo, hi] for x, lo, hi in zip(g, gs[k]["share_050"], gs[k]["share_085"])], "notip": True})
for k, (name, cc) in gl.items():
    gmarks.append({"type": "line", "name": name.split(",")[0].split(" (")[0], "c": cc, "fmt": {"dp": 0, "unit": " stalls"}, "pts": [[x, y] for x, y in zip(g, gs[k]["central"])]})
gmarks.append({"type": "rule", "axis": "x", "v": 0.82, "c": "ink", "dash": "dot", "label": "0.82 m (Berlin, T&E)"})
charts["gap"] = {
    "alt": "Lost stalls as a function of the manoeuvring gap, three growth scenarios, with bands for a parallel share of 50–85 %.",
    "legend": [{"label": gl[k][0], "c": gl[k][1]} for k in gl] + [{"label": "main case with a parallel share of 50–85 %", "c": "held", "shape": "box", "o": 0.25}],
    "panels": [{"h": 280, "x": {"kind": "linear", "domain": [0.5, 1.0], "ticks": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "label": "manoeuvring gap between cars · m", "fmt": {"dp": 2, "unit": " m"}, "tickfmt": {"dp": 1}},
                "y": {"kind": "linear", "domain": [0, 9000], "label": "stalls lost 2012–2025", "tickfmt": {"dp": 0}},
                "marks": gmarks}],
    "table": {"cols": ["gap (m)"] + [gl[k][0] for k in gl], "rows": [[f"{x:.2f}"] + [n(gs[k]["central"][i]) for k in gl] for i, x in enumerate(g) if i % 5 == 0]},
    "data": [D1],
}

# fig. 13 · districts (first estimate)
dist = T1["districts"]
charts["districts"] = {
    "alt": "Gross zone area per stall by district, 13.7 to 16.0 m², against the city mean.",
    "panels": [{"h": 300, "x": {"kind": "linear", "domain": [12.5, 16.5], "label": "gross zone area per stall · m²", "fmt": {"dp": 1}},
                "y": {"kind": "cat", "domain": [r["district"] for r in dist["rows"]]},
                "marks": [{"type": "rule", "axis": "x", "v": dist["city_mean"], "c": "ink", "dash": "dash", "label": f"city mean {dist['city_mean']:.2f} m²",
                           "tip": f"city mean {dist['city_mean']:.2f} m² per stall"},
                          {"type": "range", "c": "held", "rows": [{"y": r["district"], "mid": r["m2_per_stall"], "label": f"{r['m2_per_stall']:.1f}",
                                                                   "tip": f"{r['district']}\n{r['m2_per_stall']:.2f} m² per stall\n{n(r['stalls'])} stalls"} for r in dist["rows"]]}]}],
    "table": {"cols": ["district", "m² per stall", "stalls"], "rows": [[r["district"], f"{r['m2_per_stall']:.2f}", n(r["stalls"])] for r in dist["rows"]]},
    "data": [D1],
}

# data links are relative to the article (texts/)
for spec in charts.values():
    spec["data"] = ["../" + p for p in spec["data"]]
(A / "parking6/charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
print(len(charts), "charts →", A / "parking6/charts.json")
