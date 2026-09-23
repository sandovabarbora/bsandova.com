"""Figure for texts/prague-parking-3.html. Size effect against permit growth: stalls lost to longer cars (Text 02, citywide) per year,
against new residential permits in Praha 7 per year (Deník N, 22 Sept 2026, from Praha 7 data).
Same palette as parking2_figures.py. PREVIEW=path.png also writes a PNG.

    .venv/bin/python tools/parking3_figures.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "assets/parking2/eea_cz.json").read_text())
OUT = ROOT / "assets/parking3"
BG, FG, FG2, LINE = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36"
ACID, BUS = "#D6FF3A", "#FF6A3D"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "axes.edgecolor": LINE, "axes.labelcolor": FG2, "xtick.color": FG2, "ytick.color": FG2,
    "text.color": FG, "grid.color": LINE, "grid.alpha": 0.6, "axes.grid": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "monospace", "font.size": 9, "legend.frameon": False,
    "figure.constrained_layout.use": True, "svg.fonttype": "none",
})
YEARS = 2025 - 2012
PREVIEW = os.environ.get("PREVIEW")
P7_PERMITS_PER_YEAR = 280  # Deník N (Vodrážka, 22 Sept 2026): average since 2018, source Praha 7


def fig():
    s = D["scenarios"]
    c, lo, hi = (s[k]["stalls_lost"] / YEARS for k in ("central", "ratio_high", "ratio_low"))
    fig, a = plt.subplots(figsize=(10.5, 2.6))
    labels = ["Prague, all zones:\nstalls lost to longer cars", "Praha 7 alone:\nnew parking permits"]
    a.barh(labels, [c, P7_PERMITS_PER_YEAR], color=[ACID, BUS], height=0.5)
    a.errorbar([c], [0], xerr=[[c - lo], [hi - c]], color=FG, capsize=4, lw=1.2)
    a.text(hi + 6, 0, f"{c:.0f} a year   (ratio 0.70 → {lo:.0f} · 0.52 → {hi:.0f})", va="center", color=FG, fontsize=8.5)
    a.text(P7_PERMITS_PER_YEAR + 6, 1, f"{P7_PERMITS_PER_YEAR} a year", va="center", color=FG, fontsize=8.5)
    a.set_xlim(0, 420)
    a.set_title("per year · size effect 2012→2025 (Text 02, spread evenly) vs permit growth since 2018",
                loc="left", color=FG2)
    a.invert_yaxis()
    fig.savefig(OUT / "01-size-vs-permits.svg", bbox_inches="tight")
    if PREVIEW:
        fig.savefig(PREVIEW, dpi=110, bbox_inches="tight")
    print(f"size effect {c:.0f}/yr ({lo:.0f}-{hi:.0f}); total {c * YEARS:.0f} = {c * YEARS / P7_PERMITS_PER_YEAR:.1f} yr of P7 permits")


fig()
