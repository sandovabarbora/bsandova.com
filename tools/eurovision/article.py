"""Eurovision: figures, the map, the table and the article, every number from the results and the published tables.

Reads docs/research/eurovision-results.json and tools/data/eurovision/{h1,h1_absent_zero}.parquet; writes
assets/eurovision/ (charts.json, 01-gap.svg, 02-checks.svg, 03-map.svg, 04-eu.svg, pairs.csv, results.json) and
texts/eurovision.html from tools/eurovision/template.html.

    uv run --with matplotlib --with pandas --with pyarrow --with shapely python tools/eurovision/article.py
"""
from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Polygon as MPoly  # noqa: E402
from shapely.geometry import shape  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "eurovision"
D = ROOT / "tools" / "data" / "eurovision"
HELD, INK, GREY, LIGHT, CORAL = "#34507c", "#111111", "#666666", "#b5b5b0", "#b4532a"
NB = " "
NAMES = {"AL": "Albania", "AD": "Andorra", "AM": "Armenia", "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan",
         "BY": "Belarus", "BE": "Belgium", "BA": "Bosnia and Herzegovina", "BG": "Bulgaria", "HR": "Croatia",
         "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France",
         "GE": "Georgia", "DE": "Germany", "GR": "Greece", "HU": "Hungary", "IS": "Iceland", "IE": "Ireland",
         "IL": "Israel", "IT": "Italy", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta",
         "MD": "Moldova", "MC": "Monaco", "ME": "Montenegro", "MA": "Morocco", "NL": "the Netherlands",
         "MK": "North Macedonia", "NO": "Norway", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "RU": "Russia",
         "SM": "San Marino", "RS": "Serbia", "SK": "Slovakia", "SI": "Slovenia", "ES": "Spain", "SE": "Sweden",
         "CH": "Switzerland", "TR": "Turkey", "UA": "Ukraine", "GB": "the United Kingdom"}
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})
BINS = [-0.001, 0.01, 0.1, 1, 5, 1e9]
BIN_LABELS = ["under 0.01", "0.01–0.1", "0.1–1", "1–5", "over 5"]


def n(v: float, dp: int = 0) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 and round(abs(v), dp) else "") + s


def wide(h: pd.DataFrame) -> pd.DataFrame:
    w = h.pivot_table(index=["year", "r", "i", "j"], columns="aud", values="points").reset_index()
    w["gap"] = w.tele - w.jury
    return w


def figures(res: dict) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "eurovision-results.json", A / "results.json")
    h1 = pd.read_parquet(D / "h1.parquet")
    w = wide(h1).merge(h1[["year", "r", "i", "j", "per1000"]].drop_duplicates(), on=["year", "r", "i", "j"])
    w["bin"] = pd.cut(w.per1000, BINS, labels=BIN_LABELS)
    b = w.groupby("bin", observed=True).agg(n=("gap", "size"), gap=("gap", "mean"), tele=("tele", "mean"),
                                            jury=("jury", "mean"))
    allp = wide(pd.read_parquet(D / "h1_absent_zero.parquet"))
    pairs = allp.groupby(["i", "j"]).agg(n=("gap", "size"), gap=("gap", "mean"), tele=("tele", "mean"),
                                         jury=("jury", "mean")).reset_index()
    per = h1.groupby(["i", "j"]).per1000.mean()
    pairs["per1000"] = [per.get((i, j)) for i, j in zip(pairs.i, pairs.j)]
    pairs.round(3).to_csv(A / "pairs.csv", index=False)

    charts = {"gap": {
        "alt": "Average televote minus jury points from a voter to a performer, by the size of the performer's "
               "diaspora in the voting country: negative for tiny diasporas, about +3 points for the largest.",
        "panels": [{"h": 240, "x": {"kind": "cat", "domain": BIN_LABELS,
                                    "label": "people born in the performing country per 1 000 inhabitants of the voting country"},
                    "y": {"kind": "linear", "domain": [min(-1.2, float(b.gap.min()) - 0.3), float(b.gap.max()) + 0.6],
                          "fmt": {"dp": 1}, "label": "televote minus jury points, average"},
                    "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                              {"type": "vbar", "rows": [{"x": k, "y1": float(r.gap), "c": "held" if r.gap > 0 else "grey",
                                                         "label": f"{r.gap:+.1f}",
                                                         "tip": f"{k} per 1 000: televote {r.tele:.1f}, jury {r.jury:.1f} points on average, {int(r.n)} cells"}
                                                        for k, r in b.iterrows()]}]}],
        "table": {"cols": ["diaspora per 1 000", "cells", "televote", "jury", "difference"],
                  "rows": [[k, int(r.n), round(r.tele, 2), round(r.jury, 2), round(r.gap, 2)] for k, r in b.iterrows()]},
        "data": ["pairs.csv"]}}

    x90 = res["H1"]["x90"]
    rows = [("registered estimate", res["H1"])] + [(lab, res["H1_checks"][k]) for k, lab in (
        ("no_2022", "without 2022"), ("finals_only", "finals only"), ("semis_only", "semi-finals only"),
        ("individual_jurors", "against each juror"), ("absent_origin_as_zero", "absent origins as zero"))]
    rows.append(("with neighbours and language", res["H1_checks"]["with_contiguity_language"]["xt"]))
    fr = [{"y": lab, "mid": math.exp(v["b"] * x90), "lo": math.exp(v["lo"] * x90), "hi": math.exp(v["hi"] * x90),
           "c": "held" if lab == "registered estimate" else "ink",
           "tip": f"{lab}: ×{math.exp(v['b'] * x90):.2f} ({math.exp(v['lo'] * x90):.2f}–{math.exp(v['hi'] * x90):.2f})"}
          for lab, v in rows]
    for t, lab in (("ct", "neighbours (shared border)"), ("lt", "shared official language")):
        v = res["H1_checks"]["with_contiguity_language"][t]
        fr.append({"y": lab, "mid": math.exp(v["b"]), "lo": math.exp(v["lo"]), "hi": math.exp(v["hi"]), "c": "grey",
                   "tip": f"{lab}: ×{math.exp(v['b']):.2f} ({math.exp(v['lo']):.2f}–{math.exp(v['hi']):.2f})"})
    charts["checks"] = {
        "alt": "Televote-to-jury ratio of points for a large diaspora, registered estimate and checks, all near 2; "
               "neighbours and a shared language near 1.",
        "panels": [{"h": 28 * len(fr), "x": {"kind": "log", "domain": [0.5, 3.2], "ticks": [0.5, 1, 1.5, 2, 3],
                                             "fmt": {"dp": 1}, "label": "televote points relative to jury points"},
                    "y": {"kind": "cat", "domain": [r["y"] for r in fr]},
                    "marks": [{"type": "rule", "axis": "x", "v": 1, "c": "grey"}, {"type": "range", "rows": fr}]}],
        "table": {"cols": ["model", "ratio", "95 % interval"],
                  "rows": [[r["y"], round(r["mid"], 3), f"{r['lo']:.3f} to {r['hi']:.3f}"] for r in fr]},
        "data": ["results.json"]}

    ev = res["H3_event"]
    pts = []
    for k, v in ev.items():
        e = (-1 if k[2] == "m" else 1) * int(k[3:])
        pts.append({"x": e, "lo": 100 * v["lo"], "hi": 100 * v["hi"], "mid": 100 * v["b"], "c": "held" if e >= 0 else "ink",
                    "tip": f"year {e:+d}: {100 * v['b']:+.2f} pp ({100 * v['lo']:+.2f} to {100 * v['hi']:+.2f})"})
    pts.append({"x": -1, "mid": 0, "c": "grey", "tip": "reference year −1"})
    pts.sort(key=lambda p: p["x"])
    lo_, hi_ = min(p.get("lo", 0) for p in pts), max(p.get("hi", 0) for p in pts)
    charts["eu"] = {
        "alt": "Share of points two countries give each other, relative to comparison pairs, by contest year from the "
               "first year both were in the EU; no lasting rise after joining. Before joining, the 95 % intervals exclude "
               "zero in years " + ", ".join(f"{p['x']:+d} ({p['mid']:+.2f} pp)".replace("-", "−") for p in pts
                                             if p["x"] < 0 and (p.get("lo", 0) > 0 or p.get("hi", 0) < 0))
               + ", so the pre-accession trends are not flat.",
        "panels": [{"h": 260, "x": {"kind": "linear", "domain": [-10.5, 10.5], "ticks": list(range(-10, 11, 2)),
                                    "fmt": {"dp": 0}, "label": "contest years from the first year both were in the EU"},
                    "y": {"kind": "linear", "domain": [lo_ * 1.1, hi_ * 1.1], "fmt": {"dp": 1},
                          "label": "difference in the share of points, percentage points"},
                    "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                              {"type": "rule", "axis": "x", "v": -0.5, "c": "grey", "dash": "dash", "label": "both in the EU"},
                              {"type": "vrange", "rows": pts, "w": 2}]}],
        "table": {"cols": ["year", "difference, pp", "95 % interval"],
                  "rows": [[p["x"], round(p["mid"], 3), f"{p.get('lo', 0):.3f} to {p.get('hi', 0):.3f}"] for p in pts]},
        "data": ["results.json"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))

    f, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.bar(range(len(b)), b.gap, color=[HELD if g > 0 else LIGHT for g in b.gap], width=0.6)
    ax.axhline(0, color=GREY, lw=0.8); ax.set_xticks(range(len(b))); ax.set_xticklabels(BIN_LABELS)
    ax.set_xlabel("people born in the performing country per 1 000 inhabitants of the voting country")
    ax.set_ylabel("televote − jury points")
    for k, g in enumerate(b.gap):
        ax.text(k, g + (0.12 if g > 0 else -0.32), f"{g:+.1f}".replace("-", "−"), ha="center", fontsize=8, color=INK)
    ax.set_ylim(float(b.gap.min()) - 0.7, float(b.gap.max()) + 0.5)
    f.tight_layout(); f.savefig(A / "01-gap.svg"); plt.close(f)

    f, ax = plt.subplots(figsize=(7.2, 3.3))
    for k, r in enumerate(reversed(fr)):
        c = HELD if r["c"] == "held" else INK if r["c"] == "ink" else GREY
        ax.plot([r["lo"], r["hi"]], [k, k], color=c, lw=2.5, solid_capstyle="round")
        ax.plot(r["mid"], k, "o", color=c, ms=6, mec="white")
    ax.axvline(1, color=GREY, lw=0.8); ax.set_xscale("log"); ax.set_xticks([0.5, 1, 1.5, 2, 3])
    ax.set_xticklabels(["0.5", "1", "1.5", "2", "3"]); ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_yticks(range(len(fr))); ax.set_yticklabels([r["y"] for r in reversed(fr)])
    ax.set_xlabel("televote points relative to jury points")
    f.tight_layout(); f.savefig(A / "02-checks.svg"); plt.close(f)

    gj = json.loads((D / "geo" / "ne_50m_admin_0_countries.geojson").read_text())
    geo = {}
    for ft in gj["features"]:
        iso = ft["properties"].get("ISO_A2_EH") or ft["properties"].get("ISO_A2")
        if iso in NAMES:
            geo[iso] = shape(ft["geometry"])
    cmap = plt.get_cmap("RdBu_r")
    f, axs = plt.subplots(1, 2, figsize=(7.2, 3.4))
    maps = {}
    for ax, voter in zip(axs, ("CZ", "DE")):
        g = pairs[(pairs.i == voter) & (pairs.n >= 3)].set_index("j").gap
        maps[voter] = g.round(2).to_dict()
        for iso, geom in geo.items():
            polys = getattr(geom, "geoms", [geom])
            if iso == voter:
                fc = "#222222"
            elif iso in g:
                fc = cmap(0.5 + max(-1, min(1, g[iso] / 8)) / 2)
            else:
                fc = "#e8e8e4"
            for p in polys:
                ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fc=fc, ec="white", lw=0.4))
        ax.set_xlim(-12, 45); ax.set_ylim(34, 68); ax.set_aspect(1.6); ax.axis("off")
        ax.set_title(f"{NAMES[voter]}'s televote minus its jury", fontsize=9, color=GREY)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(-8, 8))
    cb = f.colorbar(sm, ax=axs, orientation="horizontal", fraction=0.05, pad=0.04, shrink=0.5)
    cb.set_label("average points, televote − jury, 2016–2025", fontsize=8, color=GREY)
    f.savefig(A / "03-map.svg", bbox_inches="tight"); plt.close(f)

    f, ax = plt.subplots(figsize=(7.2, 2.6))
    for p in pts:
        c = HELD if p["x"] >= 0 else INK
        if "lo" in p:
            ax.plot([p["x"], p["x"]], [p["lo"], p["hi"]], color=c, lw=2)
        ax.plot(p["x"], p["mid"], "o", color=c if "lo" in p else GREY, ms=4)
    ax.axhline(0, color=GREY, lw=0.8); ax.axvline(-0.5, color=GREY, lw=0.8, ls="--")
    ax.set_xticks(range(-10, 11, 2))
    ax.set_xlabel("contest years from the first year both were in the EU"); ax.set_ylabel("share of points, pp")
    f.tight_layout(); f.savefig(A / "04-eu.svg"); plt.close(f)
    return {"bins": b, "pairs": pairs, "maps": maps, "w": w}


def values(res: dict, fig: dict) -> dict:
    h1, c, h3 = res["H1"], res["H1_checks"], res["H3"]
    b, pairs, w = fig["bins"], fig["pairs"], fig["w"]
    x90 = h1["x90"]
    per90 = math.expm1(x90)
    top = pairs[(pairs.n >= 5) & pairs.per1000.notna()].sort_values("gap", ascending=False).head(8)
    neg = pairs[(pairs.n >= 5)].sort_values("gap").head(3)
    rows = "".join(f"<tr><td>{NAMES[r.i]}</td><td>{NAMES[r.j]}</td><td>{n(r.per1000, 1)}</td><td>{n(r.tele, 1)}</td>"
                   f"<td>{n(r.jury, 1)}</td><td>{int(r.n)}</td></tr>" for r in top.itertuples())
    cz = fig["maps"]["CZ"]
    cz_top = sorted(cz.items(), key=lambda kv: -kv[1])[:3]
    de_top = sorted(fig["maps"]["DE"].items(), key=lambda kv: -kv[1])[:3]
    R = lambda v: math.exp(v["b"] * x90)  # noqa: E731
    v = {
        "R": f"{h1['R']:.2f}", "R_lo": f"{h1['R_lo']:.2f}", "R_hi": f"{h1['R_hi']:.2f}", "label": h1["label"],
        "b": f"{h1['b']:.2f}", "b_lo": f"{h1['lo']:.2f}", "b_hi": f"{h1['hi']:.2f}", "n_cells": n(h1["n"]),
        "per90": n(per90, 1), "n_voters": str(w.i.nunique()), "n_pairs": n(len(pairs)),
        "bin_lo_gap": f"{b.gap.iloc[0]:+.2f}".replace("-", "−"), "bin_hi_gap": f"+{b.gap.iloc[-1]:.2f}",
        "bin_hi_tele": n(b.tele.iloc[-1], 2), "bin_hi_jury": n(b.jury.iloc[-1], 2),
        "bin_lo_tele": n(b.tele.iloc[0], 2), "bin_lo_jury": n(b.jury.iloc[0], 2),
        "bin_lo_gap2": n(b.gap.iloc[0], 2), "bin_hi_gap2": f"+{b.gap.iloc[-1]:.2f}",
        "tele_mult": n(b.tele.iloc[-1] / b.tele.iloc[0], 1), "n_pr": n(h1["n"] / 2),
        "r_no22": f"{R(c['no_2022']):.2f}", "r_fin": f"{R(c['finals_only']):.2f}", "r_sf": f"{R(c['semis_only']):.2f}",
        "r_jur": f"{R(c['individual_jurors']):.2f}", "r_zero": f"{R(c['absent_origin_as_zero']):.2f}",
        "r_cl": f"{R(c['with_contiguity_language']['xt']):.2f}",
        "ct": f"{math.exp(c['with_contiguity_language']['ct']['b']):.2f}",
        "ct_lo": f"{math.exp(c['with_contiguity_language']['ct']['lo']):.2f}",
        "ct_hi": f"{math.exp(c['with_contiguity_language']['ct']['hi']):.2f}",
        "lt": f"{math.exp(c['with_contiguity_language']['lt']['b']):.2f}",
        "lt_lo": f"{math.exp(c['with_contiguity_language']['lt']['lo']):.2f}",
        "lt_hi": f"{math.exp(c['with_contiguity_language']['lt']['hi']):.2f}",
        "h2": f"{res['H2']['b']:+.2f}".replace("-", "−"), "h2_lo": n(res["H2"]["lo"], 2), "h2_hi": n(res["H2"]["hi"], 2),
        "h2_label": res["H2"]["label"], "h2_voters": str(res["H2"]["voters"]),
        "h3_pp": n(100 * h3["b"], 2), "h3_pp_abs": n(abs(100 * h3["b"]), 2), "h3_lo": n(100 * h3["lo"], 2), "h3_hi": n(100 * h3["hi"], 2),
        "h3_pct": n(h3["pct"]), "h3_base": n(100 * h3["pre_mean"], 1), "h3_label": h3["label"],
        "h3_pairs": str(h3["treated_pairs"]), "h3_dropped": str(h3["dropped_pairs"]),
        "h3_fin": n(100 * res["H3_checks"]["finals_only"]["b"], 2), "h3_margin": n(10 * h3["pre_mean"], 2),
        "h3_no04_share": n(100 * (1 - res["H3_checks"]["without_2004_cohort"]["b"] / h3["b"])),
        **{f"ev_m{k}{s}": ("+" if f == "b" and res["H3_event"][f"evm{k}"][f] > 0 else "") + n(100 * res["H3_event"][f"evm{k}"][f], 2)
           for k in (2, 5) for s, f in (("", "b"), ("_lo", "lo"), ("_hi", "hi"))},
        "h3_no04": n(100 * res["H3_checks"]["without_2004_cohort"]["b"], 2),
        "h3_no04_lo": n(100 * res["H3_checks"]["without_2004_cohort"]["lo"], 2),
        "h3_no04_hi": n(100 * res["H3_checks"]["without_2004_cohort"]["hi"], 2),
        "bx": n(100 * res["brexit"]["b"], 2), "bx_lo": n(100 * res["brexit"]["lo"], 2), "bx_hi": n(100 * res["brexit"]["hi"], 2),
        "top_rows": rows,
        "top1": f"{NAMES[top.iloc[0].i]}'s televote gave {NAMES[top.iloc[0].j]} {n(top.iloc[0].tele, 1)} points on average and its jury {n(top.iloc[0].jury, 1)}",
        "neg1": f"{NAMES[neg.iloc[0].i]} to {NAMES[neg.iloc[0].j]}", "neg1_tele": n(neg.iloc[0].tele, 1), "neg1_jury": n(neg.iloc[0].jury, 1),
        "cz_top": ", ".join(f"{NAMES[k]} ({v:+.1f})" for k, v in cz_top).replace("-", "−"),
        "de_top": ", ".join(f"{NAMES[k]} ({v:+.1f})" for k, v in de_top).replace("-", "−"),
        "pyfixest": res["versions"]["pyfixest"],
    }
    photo = next(x for x in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if x["slug"] == "eurovision")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-eurovision;'
                  '--bg:url(../assets/photo/eurovision.jpg);--bg-s:url(../assets/photo/eurovision-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, toned</p></section>')
    pre = [e for k, e in res["H3_event"].items() if k.startswith("evm")]
    v |= {"ev_pre_n": str(len(pre)), "ev_pre_excl": str(sum(e["lo"] > 0 or e["hi"] < 0 for e in pre))}
    excl = sorted(((-int(k[3:]), e) for k, e in res["H3_event"].items() if k.startswith("evm") and (e["lo"] > 0 or e["hi"] < 0)), key=lambda t: t[0])
    parts = [f"{x} ({100 * e['b']:+.2f} pp)".replace("-", "−") for x, e in excl]
    v["ev_pre_list"] = ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else "".join(parts)
    h2 = pd.read_parquet(D / "h2.parquet")
    f22 = h2[h2.year == 2022]   # the 2022 final: how many publics gave Ukraine their 12 points
    v |= {"ua_12": str(int((f22.tele == 12).sum())), "ua_n": str(len(f22))}
    log = json.loads((D / "prepare_log.json").read_text())   # H1 cells without a UN figure, dropped as registered
    miss, cells = log["h1_missing_x_cells"], log["h1_missing_x_cells"] + log["h1_cells"]
    v |= {"miss_cells": n(miss), "all_cells": n(cells), "miss_pct": n(100 * miss / cells)}
    v["bin_hi_abs"], v["bin_lo_abs"] = v["bin_hi_gap"].lstrip("+"), v["bin_lo_gap"].lstrip("−")  # for the chart headline
    return v


def main() -> None:
    res = json.loads((R / "eurovision-results.json").read_text())
    fig = figures(res)
    v = values(res, fig)
    t = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), t)
    assert not re.findall(r"\{\{\w+\}\}", out)
    (ROOT / "texts" / "eurovision.html").write_text(out, encoding="utf-8")
    print(f"written texts/eurovision.html, {len(v)} values")


if __name__ == "__main__":
    main()
