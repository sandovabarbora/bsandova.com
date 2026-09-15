"""Figures for texts/prague-parking-2.html from assets/parking2/eea_cz.json (written by
~/Downloads/parking/src/eea_series.py). Site palette; nothing typed.

    .venv/bin/python tools/parking2_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "assets/parking2/eea_cz.json").read_text())
OUT = ROOT / "assets/parking2"
BG, FG, FG2, LINE = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36"
ACID, BUS, MINT, VIOLET = "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "axes.edgecolor": LINE, "axes.labelcolor": FG2, "xtick.color": FG2, "ytick.color": FG2,
    "text.color": FG, "grid.color": LINE, "grid.alpha": 0.6, "axes.grid": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "monospace", "font.size": 9, "legend.frameon": False,
    "figure.constrained_layout.use": True, "svg.fonttype": "none",
})
TE = {2000: 4.09, 2005: 4.17, 2010: 4.19, 2015: 4.24, 2020: 4.28, 2025: 4.38}  # T&E 2026, p. 26
RATIO, LO, HI = 0.618, 0.52, 0.70
ANCHOR = (2019, 4.30)


def fig1():
    years = [int(y) for y in D["years"]]
    w = np.array([D["wheelbase_mm"][str(y)]["mean"] for y in years])
    cov = np.array([D["wheelbase_mm"][str(y)]["coverage"] for y in years])
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 4.2))
    a.plot(years, w, color=ACID, lw=1.6)
    a.scatter(years, w, color=[ACID if c > 0.99 else BUS for c in cov], s=[26 if c > 0.99 else 44 for c in cov], zorder=3)
    for y, v, c in zip(years, w, cov):
        if c <= 0.99:
            a.annotate(f"{int(round(100 * (1 - c)))} % imputed", (y, v), xytext=(0, 9), textcoords="offset points", ha="center", color=BUS, fontsize=8)
    a.set_title("wheelbase of new cars registered in CZ · mm", loc="left", color=FG2)
    a.set_ylim(2580, 2710)
    a.text(years[0], 2586, f"+{D['wheelbase_change_2012_2022_mm']:.0f} mm 2012→2022 · {D['wheelbase_slope_mm_per_year']:.1f} mm/yr", color=FG2, fontsize=8)
    # b: length
    yrs = np.arange(2010, 2026)
    w19 = D["wheelbase_mm"]["2019"]["mean"]
    slope, icpt = np.polyfit(years, w, 1)
    w_all = np.where(yrs <= 2022, np.interp(yrs, years, w), slope * yrs + icpt)
    for r, col, lab in ((LO, None, None), (HI, None, None)):
        pass
    L = lambda r: ANCHOR[1] + (w_all - w19) / r / 1000
    b.fill_between(yrs, L(HI), L(LO), color=ACID, alpha=0.18, lw=0, label="CZ wheelbase → length, ratio 0.52–0.70")
    b.plot(yrs[yrs <= 2022], L(RATIO)[yrs <= 2022], color=ACID, lw=1.8, label="CZ, ratio 0.618")
    b.plot(yrs[yrs >= 2022], L(RATIO)[yrs >= 2022], color=ACID, lw=1.8, ls=(0, (3, 2)), label="CZ, extrapolated (no EEA dimensions after 2022)")
    tx = [y for y in TE if 2010 <= y <= 2025]
    b.plot(tx, [TE[y] for y in tx], color=VIOLET, lw=1.4, marker="o", ms=5, label="T&E, EU top-100 new cars")
    b.scatter([ANCHOR[0]], [ANCHOR[1]], color=BUS, s=60, zorder=4, label="Závadská 2019, CZ, 111 models (anchor)")
    b.set_title("length of a new car · m", loc="left", color=FG2)
    b.set_ylim(4.12, 4.46)
    b.legend(loc="upper left", fontsize=7.5)
    fig.savefig(OUT / "01-wheelbase-length.svg", bbox_inches="tight")


def fig2():
    te = D["te_park_reference"]["stalls_lost"]
    c = D["scenarios"]["central"]["stalls_lost"]
    lo, hi = D["scenarios"]["ratio_high"]["stalls_lost"], D["scenarios"]["ratio_low"]["stalls_lost"]
    fig, a = plt.subplots(figsize=(10.5, 2.6))
    a.barh(["T&E series (Text 01)", "EEA CZ series (this text)"], [te, c], color=[VIOLET, ACID], height=0.5)
    a.errorbar([c], [1], xerr=[[c - lo], [hi - c]], color=FG, capsize=4, lw=1.2)
    a.text(te + 40, 0, f"{te:,.0f}".replace(",", " "), va="center", color=FG)
    a.text(hi + 40, 1, f"{c:,.0f}".replace(",", " ") + f"   (ratio 0.70 → {lo:,.0f} · 0.52 → {hi:,.0f})".replace(",", " "), va="center", color=FG, fontsize=8.5)
    a.set_xlim(0, 3300)
    a.set_title("stalls lost 2012→2025 in Prague's paid zones, length model, gap 0.82 m, 68 % parallel", loc="left", color=FG2)
    a.invert_yaxis()
    fig.savefig(OUT / "02-stalls.svg", bbox_inches="tight")


def fig3():
    fig, a = plt.subplots(figsize=(10.5, 4.4))
    for key, col, dy in (("top_2012", FG2, -0.18), ("top_2022", ACID, 0.18)):
        rows = [r for r in D["composition"][key] if r["wheelbase_mm"]]
        seen = {}
        for r in rows:
            a.scatter(r["wheelbase_mm"], r["share_pct"], color=col, s=40, zorder=3)
            key = (round(r["wheelbase_mm"]), round(r["share_pct"], 1))
            bump = seen.get(key, 0); seen[key] = bump + 1   # two models on one point: stack the labels
            a.annotate(r["model"].title().replace("Skoda ", "Š ").replace("I 30", "i30"), (r["wheelbase_mm"], r["share_pct"]),
                       xytext=(5, dy * 20 - bump * 11), textcoords="offset points", color=col, fontsize=7.5)
        a.scatter([], [], color=col, label=key[-4:])
    a.set_xlabel("wheelbase · mm")
    a.set_ylabel("share of CZ registrations · %")
    a.set_title("the eight best-selling models, 2012 and 2022", loc="left", color=FG2)
    a.legend()
    fig.savefig(OUT / "03-models.svg", bbox_inches="tight")


fig1(); fig2(); fig3()
print("ok")
