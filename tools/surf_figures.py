"""92 days of Ericeira from the analysis file: daily max swell, period, wind, and which days clear the rule."""
import json, pathlib, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from datetime import date
R = pathlib.Path(__file__).resolve().parent.parent; OUT = R / "assets/surf"; OUT.mkdir(exist_ok=True)
BG, FG, FG2, LINE, ACID, BUS, MINT, VIOLET = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36", "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": LINE, "axes.labelcolor": FG2,
  "xtick.color": FG2, "ytick.color": FG2, "text.color": FG, "grid.color": LINE, "grid.alpha": .5, "axes.grid": True, "axes.spines.top": False,
  "axes.spines.right": False, "font.family": "monospace", "font.size": 8, "legend.frameon": False, "figure.constrained_layout.use": True, "svg.fonttype": "none"})
A = json.load(open(R / "surf/data/analysis.json"))["spots"]
rule = json.load(open(R / "surf/data.json"))["surfable_rule"]
def surf(r):
    if r["swell_max"] is None or r["period_mean"] is None: return False
    off = r.get("wind_dir") is not None and abs(((r["wind_dir"] - rule["offshore_deg"][0] + 180) % 360) - 180) <= rule["offshore_deg"][1]
    wind_ok = r.get("wind_mean") is None or r["wind_mean"] <= rule["wind_max_kmh"] or off
    return rule["swell_max_m"][0] <= r["swell_max"] <= rule["swell_max_m"][1] and r["period_mean"] >= rule["period_min_s"] and wind_ok
for spot in ["ericeira"]:
    days = sorted(A[spot].items()); t = [date.fromisoformat(d) for d, _ in days]
    h = [r["swell_max"] for _, r in days]; p = [r["period_mean"] for _, r in days]; w = [r["wind_mean"] for _, r in days]
    ok = [surf(r) for _, r in days]
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8, 6.2), sharex=True, gridspec_kw={"height_ratios": [2, 1, 1]})
    a1.axhspan(rule["swell_max_m"][0], rule["swell_max_m"][1], color=ACID, alpha=.07, lw=0)
    a1.plot(t, h, color=FG, lw=1.2); a1.scatter([x for x, o in zip(t, ok) if o], [y for y, o in zip(h, ok) if o], s=28, color=ACID, zorder=3, label="clears the rule")
    a1.set_ylabel("daily max swell (m)"); a1.legend(loc="upper left")
    a2.axhline(rule["period_min_s"], color=LINE, ls=":", lw=1); a2.plot(t, p, color=VIOLET, lw=1.2); a2.set_ylabel("mean period (s)")
    a3.axhline(rule["wind_max_kmh"], color=LINE, ls=":", lw=1); a3.plot(t, w, color=BUS, lw=1.2); a3.set_ylabel("wind (km/h)")
    fig.savefig(OUT / f"01-{spot}-92-days.svg"); plt.close(fig)
    print(spot, "surfable", sum(ok), "of", len(ok), "· max swell", max(h), "· days with period ≥ 8:", sum(1 for x in p if x and x >= 8))
