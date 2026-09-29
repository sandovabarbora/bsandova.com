"""Figures for Part 6 (parking), the long version, drawn onto paper. The accent is the blue the Part 6 photograph
holds (Lipanská, the police sign).

Reads assets/parking6/{h2,e1,e4,part2_correction}.json; writes SVGs to assets/parking6/.

    uv run --no-project --with matplotlib python tools/parking6/figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "parking6"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#34507c"
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})
H = json.loads((DIR / "h2.json").read_text())
E1 = json.loads((DIR / "e1.json").read_text())
E4 = json.loads((DIR / "e4.json").read_text())
P2 = json.loads((DIR / "part2_correction.json").read_text())


def new_cars() -> None:
    ys = sorted(int(y) for y in H["annual_means_mm"])
    v = [H["annual_means_mm"][str(y)] / 1000 for y in ys]
    est = H["estimates"]
    fig, ax = plt.subplots(figsize=(8, 3.3))
    ax.plot(ys, v, color=HELD, lw=2.2, marker="o", ms=4, label="register, cars new to CZ (post-stratified)")
    y0 = sum(v[:11]) / 11
    # comparator slope through the 2012–2022 mean: EEA wheelbase trend × within-line slope b̂
    c = est["comparator_C_cm"] / 100 / 10
    ax.plot([2012, 2022], [y0 - 5 * c, y0 + 5 * c], color=GREY, lw=1.2, ls=(0, (3, 2)), label="EEA wheelbase route (comparator)")
    v22 = v[10]
    ax.plot([2022, 2025], [v22, v22 + 0.06], color=LIGHT, lw=1.4, ls=(0, (1, 1.5)), label="T&E pace 2022→2025 (+6.0 cm)")
    ax.plot([2022, 2025], [v22, v22 + 0.03], color=INK, lw=1.0, ls=(0, (4, 2)), label="wheelbase estimate, extrapolated (+3.0 cm)")
    ax.set_xlim(2011.5, 2025.5)
    ax.set_ylabel("mean length of a new car · m")
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "01-new-cars.svg")
    plt.close(fig)


def tests() -> None:
    T = H["tests"]
    d = H["estimates"]["delta_margin_cm"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 2.6), gridspec_kw={"width_ratios": [1.1, 1]})
    a.axvspan(-d, d, color=HELD, alpha=0.10, lw=0)
    a.plot(T["ci90_d"], [0, 0], color=HELD, lw=2.4)
    a.plot(T["d_cm"], 0, "o", color=HELD, ms=7)
    a.axvline(0, color=GREY, lw=0.8)
    a.set_yticks([])
    a.set_xlim(-8, 12)
    a.set_title("H2a · register − EEA route, cm (90 % interval)", loc="left", color=GREY, fontsize=8.5)
    a.text(-d + 0.2, 0.3, f"±{d:.1f} cm margin", color=HELD, fontsize=8)
    a.set_ylim(-0.6, 0.6)
    lo, hi = T["ci95_delta2"]
    b.plot([lo, hi], [0, 0], color=HELD, lw=2.4)
    b.plot(T["delta2_cm"], 0, "o", color=HELD, ms=7)
    for x, lab, c, yy, ha in ((6.0, "T&E +6.0", INK, 0.42, "left"), (3.0, "wheelbase estimate +3.0", GREY, 0.42, "right"),
                              (4.5, "midpoint", LIGHT, -0.5, "left")):
        b.axvline(x, color=c, lw=1, ls=(0, (3, 2)))
        b.text(x + (0.1 if ha == "left" else -0.1), yy, lab, color=c, fontsize=7.5, ha=ha)
    b.set_yticks([])
    b.set_ylim(-0.6, 0.6)
    b.set_xlim(-1, 7.5)
    b.set_title("H2b · new-car length 2022→2025, cm (95 %)", loc="left", color=GREY, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(DIR / "02-tests.svg")
    plt.close(fig)


def loss() -> None:
    rows = [
        ("this study, all parallel unmarked (θ₁)", E1["theta"], HELD),
        ("  a quarter of parallel bays painted", E1["theta_painted_share_0.25"], HELD),
        ("  half painted", E1["theta_painted_share_0.5"], HELD),
        ("per parallel space (θ₁ᵘ)", E1["theta_u"], INK),
        ("per parallel space, gap ∝ length", E1["theta_u_prop"], INK),
    ]
    pts = [("first estimate (T&E series)", 1.60), ("wheelbase estimate, M1 only", 1.325),
           ("wheelbase estimate, M1 + M1G", P2["m1_m1g"]["scenarios"]["central"]["loss_pct"])]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for x in (1.0, 2.5):
        ax.axvline(x, color=LIGHT, lw=1, ls=(0, (2, 2)))
    n = len(rows) + len(pts)
    for i, (lab, r, c) in enumerate(rows):
        y = n - 1 - i
        ax.plot([100 * r["q025"], 100 * r["q975"]], [y, y], color=c, lw=2.4)
        ax.plot(100 * r["median"], y, "o", color=c, ms=6)
        ax.text(100 * r["q975"] + 0.08, y, f"{100 * r['median']:.1f} %", va="center", color=INK, fontsize=8)
    for j, (lab, v) in enumerate(pts):
        y = len(pts) - 1 - j
        ax.plot(v, y, "D", color=LIGHT, ms=5, mec=GREY)
        ax.text(v + 0.08, y, f"{v:.1f} %", va="center", color=GREY, fontsize=8)
    ax.set_yticks(range(n), [p[0] for p in pts][::-1] + [r[0] for r in rows][::-1], color=INK)
    ax.set_xlim(0, 4)
    ax.set_xlabel("more cars today's kerb would hold with 2012's cars · %")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "03-loss.svg")
    plt.close(fig)


def tornado() -> None:
    mv = E1["tipping"]["moves"]
    base = 100 * E1["tipping"]["central_theta"]
    lab = {"u": "pre-2010 cars' lengths (±1)", "p": "reference pitch 4.9–5.5 m", "a12": "2012 mean age 13.3–14.1",
           "e": "age definition ±0.5 yr", "k": "survival shape k 1.4–1.6"}
    order = sorted(lab, key=lambda k: -abs(max(mv[k]["theta_at_ends"].values()) - min(mv[k]["theta_at_ends"].values())))
    fig, ax = plt.subplots(figsize=(8, 2.8))
    for i, k in enumerate(order[::-1]):
        vals = [100 * x for x in mv[k]["theta_at_ends"].values()]
        ax.barh(i, max(vals) - min(vals), left=min(vals), color=HELD, alpha=0.8, height=0.5)
    ax.axvline(base, color=INK, lw=1)
    for x in (1.0, 2.5):
        ax.axvline(x, color=LIGHT, lw=1, ls=(0, (2, 2)))
    ax.set_yticks(range(len(order)), [lab[k] for k in order[::-1]], color=INK)
    ax.set_xlim(0.8, 2.7)
    ax.set_xlabel("θ₁ at the ends of each input's registered range, others central · %")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "04-tornado.svg")
    plt.close(fig)


def subsidy() -> None:
    c = E4["size"]["central"]
    lv = E4["level_bracket_kc_per_year"]
    rows = [
        ("size: long vs short car, at today's 1 200 Kč", c["X_p90_minus_p10_kc"], HELD),
        ("size: the same, at the second-car price", E4["size_at_bracket_ends_kc"]["at_second_car_price"], HELD),
        ("size: the same, at the city's reserved-bay fee", E4["size_at_bracket_ends_kc"]["at_OZV"], HELD),
        ("level: second-car price − 1 200", lv["lower_second_car_price"]["subsidy"], INK),
        ("level: reserved-bay fee − 1 200", lv["upper_OZV_10kc_m2_day"]["subsidy"], INK),
    ]
    fig, ax = plt.subplots(figsize=(8, 2.8))
    for i, (lab, v, col) in enumerate(rows[::-1]):
        ax.barh(i, v, color=col, alpha=0.85, height=0.5)
        r = round(v, -1) if v < 1000 else round(v, -2)
        ax.text(v * 1.08, i, f"{r:,.0f} Kč".replace(",", " "), va="center", color=INK, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(50, 200000)
    ax.set_xticks([100, 1000, 10000, 100000], ["100", "1 000", "10 000", "100 000"])
    ax.minorticks_off()
    ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], color=INK)
    ax.set_xlabel("Kč a year per car, log scale")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "05-subsidy.svg")
    plt.close(fig)


new_cars(); tests(); loss(); tornado(); subsidy()
print("ok")
