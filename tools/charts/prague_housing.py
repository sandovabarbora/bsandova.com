"""Chart specs for the housing article (texts/prague-housing.html), read by assets/charts.js.

Every number comes from the published data the static figures are drawn from, recomputed as their scripts do:
assets/praha/cities.json (tools/praha/figures_cities.py: fig. 1 and fig. 4) and assets/praha/housing_extended.json
with housing_extended_robust.json (tools/praha/figures_housing_extended.py: fig. 2, 3, 5 and 6).
Writes assets/praha/charts-housing.json.

    python3 tools/charts/prague_housing.py
"""
from __future__ import annotations

import json
import math
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "praha"
C = json.loads((DIR / "cities.json").read_text())
E = json.loads((DIR / "housing_extended.json").read_text())
R = json.loads((DIR / "housing_extended_robust.json").read_text())
HELD = "#1f5fa8"  # the accent of the article's figure scripts
NB = " "
DC = "../assets/praha/cities.json"
DE = "../assets/praha/housing_extended.json"
DR = "../assets/praha/housing_extended_robust.json"


def n(v: float, dp: int = 0, unit: str = "", sign: bool = False) -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    q = Decimal(repr(abs(v))).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)  # 0.345 → 0.35, as the text rounds
    s = f"{q:,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "+" if sign and v > 0 else "") + s + unit


def pval(p: float, sig: int = 2) -> str:
    """p to two significant digits (0.17, 0.046, 0.0011), or more where the article gives more."""
    dp = sig - 1 - math.floor(math.log10(p))
    return f"{p:.{max(dp, 2)}f}"


charts = {}

# fig. 1 · completions per 1 000 residents (figures_cities.per_1000)
ys = C["years"]
series = [("warsaw", "Warsaw", "light", 2, None, "completed"), ("vienna", "Vienna (new buildings)", "ink", 1.8, "dash", "completed_new_buildings"),
          ("prague", "Prague", HELD, 2.4, None, "completed")]
charts["completions"] = {
    "alt": "Lines of dwellings completed per 1 000 residents, 2012 to 2024. Warsaw between 7.6 and 13.2, peaking in 2018. Vienna rising from 3.6 to 8.5 in 2021, falling to 5.4 in 2024. Prague between 3.1 and 4.9, never higher.",
    "legend": [{"label": lab, "c": c, **({"dash": d} if d else {})} for _, lab, c, _, d, _ in series[::-1]],
    "panels": [{"h": 280, "padRight": 16,
                "x": {"kind": "linear", "domain": [ys[0] - 0.3, ys[-1] + 0.3], "ticks": ys[::2], "fmt": {"dp": 0, "nogroup": True}},
                "y": {"kind": "linear", "domain": [0, 14], "ticks": [0, 2, 4, 6, 8, 10, 12, 14], "label": "dwellings completed per 1 000 residents", "tickfmt": {"dp": 0}},
                "marks": [{"type": "line", "name": lab, "c": c, "w": w, "dots": True, **({"dash": d} if d else {}), "fmt": {"dp": 2},
                           "pts": [[y, C[k][str(y)]["per_1000"]] for y in ys]} for k, lab, c, w, d, _ in series]}],
    "table": {"cols": ["year", "Prague", "Vienna, new buildings", "Warsaw"],
              "rows": [[str(y)] + [f"{n(C[k][str(y)]['per_1000'], 1)} ({n(C[k][str(y)][cnt])})" for k, *_, cnt in series[::-1]] for y in ys]},
    "data": [DC],
}

# fig. 2 · 208 metro regions against the demand model (figures_housing_extended.benchmark)
pts = E["H1"]["plot"]
LABEL = {"CZ001MC": ("Prague", HELD), "AT001MC": ("Vienna", "ink"), "PL001MC": ("Warsaw", "ink")}
N = len(pts)
lo_s, hi_s = min(p["score"] for p in pts), max(p["score"] for p in pts)


def btip(i: int, p: dict) -> str:
    name = LABEL[p["id"]][0] + " metro region" if p["id"] in LABEL else f"{p['id']} ({p['country']})"
    return f"{name}\nrank {i} of {N} from the bottom\nscore {n(p['score'], 2)}\n{n(p['rate'], 2)} dwellings per 1 000 a year"


charts["benchmark"] = {
    "alt": "Dot chart of 208 metropolitan regions sorted by their score against a demand model for 2011–2021 construction. Prague, 5.3 dwellings per 1 000 residents a year, is 119th from the bottom, just above zero. Vienna, 6.2, is 155th. Warsaw, 10.0, is 205th, among the highest.",
    "legend": [{"label": "Prague", "c": HELD, "shape": "o"}, {"label": "Vienna, Warsaw", "c": "ink", "shape": "o"},
               {"label": "other metropolitan regions", "c": "light", "shape": "o"}],
    "panels": [{"h": 290,
                "x": {"kind": "linear", "domain": [0, N + 1], "ticks": [1, 50, 100, 150, 200], "nogrid": True,
                      "label": f"{N} metropolitan regions, lowest score to highest", "fmt": {"dp": 0}},
                "y": {"kind": "linear", "domain": [-5, 5], "ticks": [-4, -2, 0, 2, 4], "label": "dwellings built 2011–2021, against prediction (score)", "tickfmt": {"dp": 0}},
                "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                          {"type": "dots", "c": "light", "r": 2.6, "pts": [{"x": i, "y": p["score"], "tip": btip(i, p)}
                                                                          for i, p in enumerate(pts, 1) if p["id"] not in LABEL]},
                          {"type": "dots", "pts": [{"x": i, "y": p["score"], "c": LABEL[p["id"]][1], "r": 4.5, "ring": p["id"] == "CZ001MC",
                                                    "label": f"{LABEL[p['id']][0]} {n(p['rate'], 1)}", "dy": -9 if p["id"] != "AT001MC" else 15,
                                                    "tip": btip(i, p)} for i, p in enumerate(pts, 1) if p["id"] in LABEL]}]}],
    "table": {"cols": ["rank from the bottom", "region", "country", "score", "dwellings per 1 000 a year"],
              "rows": [[str(i), LABEL[p["id"]][0] if p["id"] in LABEL else p["id"], p["country"], n(p["score"], 2), n(p["rate"], 2)]
                       for i, p in enumerate(pts, 1)]},
    "data": [DE],
}
assert -5 < lo_s and hi_s < 5

# fig. 3 · profile likelihood of the mean lag (figures_housing_extended.lag_profile)
h2 = E["H2"]
prof = h2["profile"]
floor = min(min(prof[k]["rel_loglik"]) for k in prof)
charts["lag-profile"] = {
    "alt": "Two curves of relative log-likelihood against the mean lag in months. The rest of Czechia peaks at the left edge of the grid, 6 months (estimate 5.1), and falls steeply. Prague peaks at 16 months, but its curve stays close to the top from about 14 to 38 months, crossing the dashed 95 % line near 38.",
    "legend": [{"label": f"Prague: μ̂ = {h2['mu_prague']:.1f} months", "c": HELD},
               {"label": f"rest of Czechia: μ̂ = {h2['mu_rest']:.1f} months (grid starts at 6)", "c": "ink", "dash": "dot"},
               {"label": "95 % profile cut-off", "c": "grey", "dash": "dash"}],
    "panels": [{"h": 280,
                "x": {"kind": "linear", "domain": [4, 61], "ticks": [10, 20, 30, 40, 50, 60], "label": "mean lag from permit to house number (months)",
                      "fmt": {"dp": 0, "unit": " months"}},
                "y": {"kind": "linear", "domain": [-13, 1], "ticks": [-12, -10, -8, -6, -4, -2, 0], "label": "relative log-likelihood", "tickfmt": {"dp": 0}},
                "marks": [{"type": "rule", "axis": "y", "v": -1.92, "c": "grey", "dash": "dash", "label": "95 % profile cut-off", "anchor": "end"},
                          {"type": "line", "name": "rest of Czechia", "c": "ink", "w": 1.8, "dash": "dot", "fmt": {"dp": 2},
                           "pts": [[m, v] for m, v in zip(prof["rest"]["mu"], prof["rest"]["rel_loglik"])]},
                          {"type": "line", "name": "Prague", "c": HELD, "w": 2, "fmt": {"dp": 2},
                           "pts": [[m, v] for m, v in zip(prof["prague"]["mu"], prof["prague"]["rel_loglik"])]}]}],
    "table": {"cols": ["mean lag (months)", "Prague", "rest of Czechia"],
              "rows": [[n(m), n(a, 3), n(b, 3)] for m, a, b in zip(prof["prague"]["mu"], prof["prague"]["rel_loglik"], prof["rest"]["rel_loglik"])]},
    "data": [DE],
}
assert floor > -13 and prof["prague"]["mu"] == prof["rest"]["mu"]

# fig. 4 · who built in 2024 (figures_cities.builders)
v, w = C["builders_2024"]["vienna"], dict(C["builders_2024"]["warsaw"])
# the share from the counts, not from the 4-decimal share in cities.json: 96 / 14 873 = 0.645 %, which prints 0.6 %, not 0.7 %
w["municipal_and_tbs_share"] = (C["warsaw"]["2024"]["municipal"] + C["warsaw"]["2024"]["tbs"]) / C["warsaw"]["2024"]["completed"]
brows = [("Vienna", [(v["non_profit_share"], "limited-profit housing associations", HELD), (v["public_share"], "public sector", "ink"),
                     (v["companies_share"], "companies", "light"), (v["private_persons_share"], "private persons", "grey")]),
         ("Warsaw", [(w["municipal_and_tbs_share"], "the city and public building societies (TBS)", HELD),
                     (1 - w["municipal_and_tbs_share"], "everyone else", "light")])]
# the article rounds Warsaw's split as 0.6 % and 100 − 0.6 = 99.4 %, so the two printed shares add to 100
def pct(city: str, lab: str, share: float) -> str:
    if lab == "everyone else":
        return n(100 - float(n(100 * w["municipal_and_tbs_share"], 1)), 1, " %")
    return n(100 * share, 1, " %")


seg = []
for city, parts in brows:
    left = 0.0
    for share, lab, c in parts:
        seg.append({"y": city, "x0": round(left, 2), "x1": round(left + 100 * share, 2), "c": c,
                    "tip": f"{city}, 2024\n{lab}\n{pct(city, lab, share)} of completions"})
        left += 100 * share
charts["builders-2024"] = {
    "alt": "Two stacked bars for 2024. Vienna: limited-profit housing associations 25 %, public sector 2 %, companies 66 %, private persons 7 %. Warsaw: the city and public building societies 0.6 %, everyone else 99 %.",
    "legend": [{"label": "non-profit (Vienna) · municipal and TBS (Warsaw)", "c": HELD, "shape": "box", "o": 0.85},
               {"label": "public sector", "c": "ink", "shape": "box", "o": 0.85},
               {"label": "companies (Vienna) · everyone else (Warsaw)", "c": "light", "shape": "box", "o": 0.85},
               {"label": "private persons", "c": "grey", "shape": "box", "o": 0.85}],
    "panels": [{"h": 140,
                "x": {"kind": "linear", "domain": [0, 100], "ticks": [0, 20, 40, 60, 80, 100], "label": "dwellings completed in 2024, by builder (%)", "fmt": {"dp": 0}},
                "y": {"kind": "cat", "domain": [r[0] for r in brows]},
                "marks": [{"type": "hbar", "o": 0.85, "rows": seg}]}],
    "table": {"cols": ["city", "builder", "share of 2024 completions"],
              "rows": [[city, lab, pct(city, lab, share)] for city, parts in brows for share, lab, _ in parts]},
    "data": [DC],
}


# fig. 5 and 6 · intervals (figures_housing_extended.spec_rows)
def spec_chart(rows, xlabel, margin, dp, alt, domain, ticks, tipnote):
    def colour(lab, p):
        return HELD if lab.startswith("main") else ("ink" if p < 0.05 else "grey")

    rr = [{"y": lab, "lo": lo, "hi": hi, "mid": est, "c": colour(lab, p), "label": n(est, dp, sign=True),
           "tip": f"{lab}\n{n(est, dp, sign=True)}\n90 %: {n(lo, dp, sign=True)} to {n(hi, dp, sign=True)}\np = {pval(p, sig)}{tipnote.get(lab, '')}"}
          for lab, est, lo, hi, p, sig in rows]
    return {
        "alt": alt,
        "legend": [{"label": "main estimate", "c": HELD, "shape": "o"}, {"label": "variant, p < 0.05", "c": "ink", "shape": "o"},
                   {"label": "variant, p ≥ 0.05", "c": "grey", "shape": "o"}, {"label": "smallest difference of interest", "c": "grey", "dash": "dash"}],
        "panels": [{"h": 34 * len(rows) + 40,
                    "x": {"kind": "linear", "domain": domain, "ticks": ticks, "label": xlabel, "fmt": {"dp": dp}},
                    "y": {"kind": "cat", "domain": [r[0] for r in rows]},
                    "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"},
                              {"type": "rule", "axis": "x", "v": margin, "c": "grey", "dash": "dash"},
                              {"type": "range", "w": 2, "rows": rr}]}],
        "table": {"cols": ["specification", "estimate", "90 % low", "90 % high", "p"],
                  "rows": [[lab, n(est, dp, sign=True), n(lo, dp, sign=True), n(hi, dp, sign=True), pval(p, sig)] for lab, est, lo, hi, p, sig in rows]},
    }


h4 = E["H4"]
rows4 = [("main: municipal + TBS vs for sale or rent", h4["difference"], *h4["ci90_cr1"], h4["p"], 2)]
names4 = {"a_completions": "completions, not starts", "b_with_cooperatives": "cooperatives counted as non-market",
          "c_primary_market_price": "primary-market prices", "d_voivodeship_clusters": "16 voivodeship clusters",
          "e_without_five_largest_cities": "without the five largest cities", "f_2012_2019": "2012–2019 only"}
for k, lab in names4.items():
    x = R["H4"][k]
    rows4.append((lab, x["difference"], x["difference"] - 1.645 * x["se_cr1"], x["difference"] + 1.645 * x["se_cr1"], x["p"], 2))
nb = R["H4"]["g_negative_binomial"]
rows4.append(("negative binomial", nb["difference"], nb["difference"] - 1.645 * nb["se"], nb["difference"] + 1.645 * nb["se"], nb["p"], 2))
assert min(r[2] for r in rows4) > -3.2 and max(r[3] for r in rows4) < 1.6
charts["builders-poland"] = spec_chart(
    rows4, "non-market minus market response (90 % interval)", -1, 2,
    "Intervals of the difference between non-market and market responses to local price growth. Main −0.56, from −1.52 to +0.39. Completions −0.71, cooperatives counted as non-market −0.08, primary-market prices +0.35, voivodeship clusters −0.56, without the five largest cities −0.46, 2012–2019 −0.80, negative binomial −1.52 (the only interval that excludes zero). The dashed line at −1 is the smallest difference of interest.",
    [-3.2, 1.6], [-3, -2, -1, 0, 1], {})
charts["builders-poland"]["data"] = [DE, DR]

h5 = E["H5"]
rows5 = [("main: 2012 – March 2021", h5["gamma"], *h5["ci90_conley"], h5["p"], 3)]
names5 = {"a_2012_2024": "2012–2024", "c_500m_cells": "500 m cells", "d_stations_with_2015_extension": "stations incl. 2015 extension",
          "g_ruian_pre2012_density": "pre-2012 flats as density", "h_implausible_types_excluded": "implausible new-build types excluded",
          "j_rail_tram_distance_added": "rail and tram distance added"}
for k, lab in names5.items():
    x = R["H5"][k]
    rows5.append((lab, x["gamma"], x["gamma"] - 1.645 * x["se_conley_1_5km"], x["gamma"] + 1.645 * x["se_conley_1_5km"], x["p"], 2))
rows5.insert(1, ("Conley 3 km", h5["gamma"], h5["gamma"] - 1.645 * h5["se_conley_3km"], h5["gamma"] + 1.645 * h5["se_conley_3km"], h5["p_conley3_negative"], 2))
nb = R["H5"]["i_negative_binomial"]
rows5.append(("negative binomial", nb["gamma"], nb["gamma"] - 1.645 * nb["se_cluster"], nb["gamma"] + 1.645 * nb["se_cluster"], nb["p"], 2))
old = h5["H6_2000_2011"]
rows5.append(("replication: 2000–2011", old["gamma"], *old["ci90_conley"], old["p"], 2))
assert min(r[2] for r in rows5) > -0.7 and max(r[3] for r in rows5) < 0.1
charts["metro"] = spec_chart(
    rows5, "γ per doubling of metro distance (90 % interval)", -0.25, 3,
    "Intervals of the metro coefficient. Main −0.227, from −0.349 to −0.105. Conley 3 km −0.227. 2012–2024 −0.243. 500 m cells −0.229. Stations including the 2015 extension −0.185. Pre-2012 flats as density −0.206. Implausible new-build types excluded −0.246. Rail and tram distance added −0.241. Negative binomial −0.427. The 2000–2011 replication is −0.062, crossing zero. A dashed line marks −0.25.",
    [-0.7, 0.1], [-0.6, -0.4, -0.2, 0], {"main: 2012 – March 2021": " (larger of Conley and wild bootstrap)",
                                         "negative binomial": " (district-clustered interval)"})
charts["metro"]["data"] = [DE, DR]

# the ticks carry the axis' decimals: two for the metro axis is enough
charts["metro"]["panels"][0]["x"]["tickfmt"] = {"dp": 1}
charts["builders-poland"]["panels"][0]["x"]["tickfmt"] = {"dp": 0}

(DIR / "charts-housing.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")) + "\n")
print("wrote assets/praha/charts-housing.json:", ", ".join(charts))
