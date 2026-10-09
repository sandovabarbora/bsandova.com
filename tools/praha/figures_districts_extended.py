"""Figures for Part 3, the long version, drawn onto paper; accent = the green the Part 3 photograph holds.

Reads assets/praha/districts_extended.json and districts_extended_robust.json; writes SVGs to assets/praha/. No figure
shows a district by name next to its party.

Usage:
    uv run --with matplotlib python tools/praha/figures_districts_extended.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "praha"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#3f6b2a"
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def control_mean(e: dict) -> float:
    return sum(v["pre_level_ctrl"] for v in e["H1"]["by_event"].values()) / len(e["H1"]["by_event"])


def grants_by_year(e: dict) -> None:
    """The city's own in-year grants to all districts, by regime-year, investment and non-investment."""
    tot = e["levels"]["grants_total_czk_by_year"]
    share = e["levels"]["share_investment_by_year"]
    yrs = sorted(int(y) for y in tot)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for y in yrs:
        t = tot[str(y)] / 1e9
        if y == 2015:  # the 2015 list cannot be split
            ax.bar(y, t, color="white", edgecolor=LIGHT, hatch="///", width=0.62)
            continue
        inv = t * share[str(y)]
        ax.bar(y, inv, color=HELD, width=0.62, edgecolor="white")
        ax.bar(y, t - inv, bottom=inv, color=LIGHT, width=0.62, edgecolor="white")
    ax.set_xticks(yrs, [str(y) for y in yrs])
    ax.set_ylabel("CZK billion a year")
    ax.grid(axis="x", visible=False)
    ax.text(0.01, 0.95, "investment", transform=ax.transAxes, color=HELD, va="top")
    ax.text(0.01, 0.86, "non-investment", transform=ax.transAxes, color=GREY, va="top")
    fig.tight_layout()
    fig.savefig(DIR / "11-city-grants.svg")
    plt.close(fig)


def event_study(e: dict) -> None:
    """Switch-in districts minus clean controls, relative to the last year before each event, in % of the controls'
    usual level."""
    es = e["event_study"]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for ev, style, lab in [("2018", dict(color=LIGHT, marker="o"), "coalition change of Nov 2018"),
                           ("2023", dict(color=HELD, marker="o"), "coalition change of Feb 2023")]:
        cm = e["H1"]["by_event"][ev]["pre_level_ctrl"]  # each event against its own controls' usual level
        by = {int(k): v / cm * 100 for k, v in es[ev]["by_year"].items()}
        rel = [y - es[ev]["first_post"] for y in sorted(by)]
        vals = [by[y] for y in sorted(by)]
        desc = set(es[ev]["descriptive_years"])
        solid = [(r, v) for r, v, y in zip(rel, vals, sorted(by)) if y not in desc]
        ax.plot([r for r, _ in solid], [v for _, v in solid], lw=1.6, ms=5, label=lab, **style)
        dash = [(r, v) for r, v, y in zip(rel, vals, sorted(by)) if y in desc or y == max(set(by) - desc)]
        if len(dash) > 1:
            ax.plot([r for r, _ in dash], [v for _, v in dash], lw=1.2, ls=(0, (2, 2)), color=style["color"])
            ax.plot([r for r, _ in dash[1:]], [v for _, v in dash[1:]], "o", ms=4, mfc="white",
                    color=style["color"])
    ax.axhline(0, color=GREY, lw=0.8)
    ax.axvline(-0.5, color=INK, lw=0.8, ls=(0, (1, 2)))
    ax.set_xticks(range(-3, 3), ["−3", "−2", "−1", "0", "+1", "+2"])
    ax.set_xlabel("years from the coalition change (regime-years)")
    ax.set_ylabel("switch-in minus control, % of usual")
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(DIR / "12-event-study.svg")
    plt.close(fig)


def estimate(e: dict) -> None:
    """The registered estimate against what the design could detect and what the literature finds."""
    cm = control_mean(e)
    h = e["H1"]
    est = h["estimate"] / cm * 100
    ct = [v / cm * 100 for v in h["conley_taber_95"]]
    hon = [v / cm * 100 for v in e["honest"]["1.0"]]
    by = {k: v["estimate"] / v["pre_level_ctrl"] * 100 for k, v in h["by_event"].items()}  # each event, own level
    fig, ax = plt.subplots(figsize=(8, 3.1))
    ax.axvspan(36, 47, color=HELD, alpha=0.14, lw=0)  # Brazil about 40 %, Italy 36–47 % (Spain: no magnitude in the abstract)
    ax.text(49, 3.55, "published\n36–47 %", ha="left", va="top", color=HELD, fontsize=8)
    ax.axvspan(-20, 20, color=GRID, alpha=0.8, lw=0)
    ax.text(-22, 3.55, "±20 %", ha="right", va="top", color=GREY, fontsize=8)
    ax.axvline(100, color=INK, lw=0.8, ls=(0, (2, 2)))
    ax.text(104, 3.55, "detectable at\n80 % power", ha="left", va="top", color=INK, fontsize=8)
    lo, hi = -160, 150
    rows = [(est, ct, INK), (est, hon, GREY)]  # HonestDiD: the simplified interval (see the design)
    for i, (x, ci, col) in enumerate(rows):
        yv = 2.2 - i
        a, b = max(ci[0], lo), min(ci[1], hi)
        ax.plot([a, b], [yv, yv], color=col, lw=1.6)
        if ci[0] < lo:
            ax.annotate("", xy=(lo, yv), xytext=(lo + 12, yv), arrowprops=dict(arrowstyle="-|>", color=col, lw=1.2))
        ax.plot(x, yv, "o", color=col, ms=7)
    ax.plot(by["2018"], 0.5, "o", color=LIGHT, ms=6)
    ax.plot(by["2023"], 0.5, "o", color=HELD, ms=6)
    ax.set_xlim(lo, hi)
    ax.set_ylim(0, 3.6)
    ax.set_yticks([2.2, 1.2, 0.5], ["pooled · 95 % Conley–Taber", "pooled · HonestDiD (simplified), M̄ = 1",
                                   "by event · 2018 grey, 2023 green"], color=INK)
    ax.axvline(0, color=GREY, lw=0.8)
    ax.set_xlabel("change on becoming aligned, % of the controls' usual grants")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "13-estimate.svg")
    plt.close(fig)


def spec_curve(r: dict) -> None:
    specs = sorted(r["specification_curve"]["specs"], key=lambda s: s["relative"])
    fig, ax = plt.subplots(figsize=(8, 3.0))
    cols = {"A": HELD, "seat_majority": INK, "largest_list_has_coalition_party": LIGHT}
    for i, s in enumerate(specs):
        ax.plot(i, s["relative"] * 100, "o", color=cols[s["rule"]], ms=4.5)
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_xticks([])
    ax.set_ylabel("% of the controls' usual level")
    ax.set_xlabel(f"{len(specs)} specifications, sorted")
    ax.text(0.99, 0.23, "mayor's party (registered)", transform=ax.transAxes, color=HELD, ha="right", fontsize=8)
    ax.text(0.99, 0.14, "seat majority", transform=ax.transAxes, color=INK, ha="right", fontsize=8)
    ax.text(0.99, 0.05, "largest list", transform=ax.transAxes, color=GREY, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(DIR / "14-spec-curve.svg")
    plt.close(fig)


def main() -> None:
    e = json.loads((DIR / "districts_extended.json").read_text())
    r = json.loads((DIR / "districts_extended_robust.json").read_text())
    grants_by_year(e)
    event_study(e)
    estimate(e)
    spec_curve(r)
    print("wrote 11-city-grants.svg, 12-event-study.svg, 13-estimate.svg, 14-spec-curve.svg")


if __name__ == "__main__":
    main()
