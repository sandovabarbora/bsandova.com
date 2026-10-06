"""Figures for Part 4, the long version, drawn onto paper; accent = the blue Part 4's photograph holds.

Reads assets/praha/housing_extended.json and housing_extended_robust.json; writes SVGs to assets/praha/.

Usage:
    uv run --with matplotlib python tools/praha/figures_housing_extended.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "praha"
INK, GREY, LIGHT, GRID = "#111111", "#666666", "#b5b5b0", "#e6e6e3"
PAL = json.loads((Path(__file__).resolve().parents[2] / "assets" / "palette.json").read_text())  # entity colours, as the live charts
HELD = PAL["entity"]["Prague"]
CITY = {"CZ001MC": HELD, "AT001MC": PAL["entity"]["Vienna"], "PL001MC": PAL["entity"]["Warsaw"]}
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})
LABEL = {"CZ001MC": "Prague", "AT001MC": "Vienna", "PL001MC": "Warsaw"}


def benchmark(e: dict) -> None:
    """Studentised leave-one-country-out scores of 208 metro regions, sorted."""
    pts = e["H1"]["plot"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    xs = list(range(1, len(pts) + 1))
    ax.scatter(xs, [p["score"] for p in pts], s=7, color=LIGHT, lw=0)
    for x, p in zip(xs, pts):
        if p["id"] in LABEL:
            col = CITY[p["id"]]
            ax.scatter([x], [p["score"]], s=26, color=col, zorder=3)
            off, ha, va = {"CZ001MC": ((0, 12), "center", "bottom"), "AT001MC": ((0, -12), "center", "top"),
                           "PL001MC": ((-10, 0), "right", "center")}[p["id"]]
            ax.annotate(f"{LABEL[p['id']]}\n{p['rate']:.1f} per 1 000 a year", (x, p["score"]), xytext=off,
                        textcoords="offset points", ha=ha, va=va, color=col, fontsize=8)
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_xlim(0, len(pts) + 1)
    ax.set_xlabel("208 European metropolitan regions, from the lowest score to the highest")
    ax.set_ylabel("dwellings built 2011–2021,\nagainst prediction (score)")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "11-benchmark.svg")
    plt.close(fig)


def lag_profile(e: dict) -> None:
    """Profile log-likelihood of the mean permit-to-house-number lag, Prague and the rest."""
    prof = e["H2"]["profile"]
    fig, ax = plt.subplots(figsize=(8, 3.0))
    for key, lab, col in [("rest", "rest of Czechia", INK), ("prague", "Prague", HELD)]:
        ax.plot(prof[key]["mu"], prof[key]["rel_loglik"], color=col, lw=2 if key == "prague" else 1.6)
    h = e["H2"]
    ax.text(17, 0.35, f"Prague: μ̂ = {h['mu_prague']:.1f} months", color=HELD, fontsize=8)
    ax.text(21, -7.4, f"rest of Czechia: μ̂ = {h['mu_rest']:.1f} months (grid starts at 6)", color=INK, fontsize=8)
    ax.axhline(-1.92, color=GREY, lw=0.8, ls="--")
    ax.text(60, -1.7, "95 % profile cut-off", color=GREY, ha="right", fontsize=8)
    ax.set_ylim(-8, 1.2)
    ax.set_xlim(4, 61)
    ax.set_xlabel("mean lag from permit to house number (months)")
    ax.set_ylabel("relative log-likelihood")
    fig.tight_layout()
    fig.savefig(DIR / "12-lag-profile.svg")
    plt.close(fig)


def spec_rows(ax, rows, xlabel, zero=0.0, margin=None):
    for i, (lab, est, lo, hi, p) in enumerate(rows[::-1]):
        col = HELD if lab.startswith("main") else (INK if p < 0.05 else GREY)
        if lo is not None:
            ax.plot([lo, hi], [i, i], color=col, lw=1.6)
        ax.scatter([est], [i], color=col, s=22, zorder=3)
    ax.axvline(zero, color=GREY, lw=0.8)
    if margin is not None:
        ax.axvline(margin, color=GREY, lw=0.8, ls="--")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], color=INK, fontsize=8)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)


def builders(e: dict, r: dict) -> None:
    h = e["H4"]
    rows = [("main: municipal + TBS vs for sale or rent", h["difference"], *h["ci90_cr1"], h["p"])]
    names = {"a_completions": "completions, not starts", "b_with_cooperatives": "cooperatives counted as non-market",
             "c_primary_market_price": "primary-market prices", "d_voivodeship_clusters": "16 voivodeship clusters",
             "e_without_five_largest_cities": "without the five largest cities", "f_2012_2019": "2012–2019 only"}
    for k, lab in names.items():
        v = r["H4"][k]
        rows.append((lab, v["difference"], v["difference"] - 1.645 * v["se_cr1"],
                     v["difference"] + 1.645 * v["se_cr1"], v["p"]))
    nb = r["H4"]["g_negative_binomial"]
    rows.append(("negative binomial", nb["difference"], nb["difference"] - 1.645 * nb["se"],
                 nb["difference"] + 1.645 * nb["se"], nb["p"]))
    fig, ax = plt.subplots(figsize=(8, 3.3))
    spec_rows(ax, rows, "non-market minus market response to price growth (90 % interval)",
              margin=-1)
    fig.tight_layout()
    fig.savefig(DIR / "13-builders.svg")
    plt.close(fig)


def metro(e: dict, r: dict) -> None:
    h = e["H5"]
    rows = [("main: 2012 – March 2021", h["gamma"], *h["ci90_conley"], h["p"])]
    names = {"a_2012_2024": "2012–2024", "c_500m_cells": "500 m cells",
             "d_stations_with_2015_extension": "stations incl. 2015 extension",
             "g_ruian_pre2012_density": "pre-2012 flats as density", "h_implausible_types_excluded":
             "implausible new-build types excluded", "j_rail_tram_distance_added": "rail and tram distance added"}
    for k, lab in names.items():
        v = r["H5"][k]
        rows.append((lab, v["gamma"], v["gamma"] - 1.645 * v["se_conley_1_5km"],
                     v["gamma"] + 1.645 * v["se_conley_1_5km"], v["p"]))
    rows.insert(1, ("Conley 3 km", h["gamma"], h["gamma"] - 1.645 * h["se_conley_3km"],
                    h["gamma"] + 1.645 * h["se_conley_3km"], h["p_conley3_negative"]))
    nb = r["H5"]["i_negative_binomial"]
    rows.append(("negative binomial", nb["gamma"], nb["gamma"] - 1.645 * nb["se_cluster"],
                 nb["gamma"] + 1.645 * nb["se_cluster"], nb["p"]))
    old = h["H6_2000_2011"]
    rows.append(("replication: 2000–2011", old["gamma"], *old["ci90_conley"], old["p"]))
    fig, ax = plt.subplots(figsize=(8, 3.7))
    spec_rows(ax, rows, "γ: log density of new flats per doubling of metro distance (90 %)",
              margin=-0.25)
    fig.tight_layout()
    fig.savefig(DIR / "14-metro.svg")
    plt.close(fig)


def main() -> None:
    e = json.loads((DIR / "housing_extended.json").read_text())
    r = json.loads((DIR / "housing_extended_robust.json").read_text())
    benchmark(e)
    lag_profile(e)
    builders(e, r)
    metro(e, r)
    print("wrote 11-benchmark.svg, 12-lag-profile.svg, 13-builders.svg, 14-metro.svg")


if __name__ == "__main__":
    main()
