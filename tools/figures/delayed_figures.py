"""Five days of Prague transit as the record hears them: surface delay per 5-minute bin, and the chorus as the player at 798f726 plays it
(smoothed delay above 68 % of the day's maximum, runs shorter than 4 windows dropped, gaps shorter than 3 windows between choruses filled,
windows before 05:00 or after 22:30 with no metro stop event set to night)."""
import json, pathlib, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = pathlib.Path(__file__).resolve().parents[2]; OUT = R / "assets/delayed"; OUT.mkdir(exist_ok=True)
BG, FG, FG2, LINE, ACID, BUS, MINT, VIOLET = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36", "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": LINE, "axes.labelcolor": FG2,
  "xtick.color": FG2, "ytick.color": FG2, "text.color": FG, "grid.color": LINE, "grid.alpha": .5, "axes.grid": True, "axes.spines.top": False,
  "axes.spines.right": False, "font.family": "monospace", "font.size": 8, "legend.frameon": False, "figure.constrained_layout.use": True, "svg.fonttype": "none"})
D = json.load(open(R / "tools/data/sonification_days.json"))
surf = ["autobus", "tramvaj", "trolejbus"]
def series(day):
    m = day["modes"]; n = np.array([sum(m[s]["n"][i] for s in surf) for i in range(288)], float)
    w = np.array([sum(m[s]["n"][i] * m[s]["delay"][i] for s in surf) for i in range(288)], float)
    d = np.where(n > 0, w / np.maximum(n, 1), 0.0)
    sm = np.array([d[max(0, i - 2):i + 3].mean() for i in range(288)])  # the player's smoothing: mean of the windows that exist
    return d, sm, n
def runs(s):
    out, a = [], 0
    for i in range(1, 289):
        if i == 288 or s[i] != s[a]: out.append((a, i, s[a])); a = i
    return out
def sections(day, sm):
    """The player's sections (index.html@798f726, computeDay): 0 night, 1 verse, 2 chorus."""
    sect = [2 if v > .68 * sm.max() else 1 for v in sm]
    for a, b, v in runs(sect):
        if v == 2 and b - a < 4: sect[a:b] = [1] * (b - a)
    for a, b, v in runs(sect):
        if v == 1 and b - a < 3 and a > 0 and b < 288 and sect[a - 1] == 2 and sect[b] == 2: sect[a:b] = [2] * (b - a)
    for i in range(288):
        if day["modes"]["metro"]["n"][i] == 0 and (i < 60 or i > 270): sect[i] = 0
    return np.array(sect)
order = ["easter", "summer", "school", "typical", "meltdown"]
days = sorted(D["days"], key=lambda d: order.index(next((o for o in order if o in d["id"]), "typical")) if any(o in d["id"] for o in order) else 9)
fig, axes = plt.subplots(len(days), 1, figsize=(8, 1.7 * len(days)), sharex=True)
t = np.arange(288) / 12
rows = []
for ax, day in zip(axes, days):
    d, sm, n = series(day); thr = .68 * sm.max(); chorus = sections(day, sm) == 2
    ax.fill_between(t, 0, d, where=chorus, color=BUS, alpha=.35, lw=0, step=None)
    ax.plot(t, d, color=FG, lw=1); ax.axhline(thr, color=LINE, lw=1, ls=":")
    key = day.get("key") or ""
    ax.text(0.2, d.max() * .92, f"{day['label']} · {day['disc']} · {int(day['total']):,} events".replace(",", " "), fontsize=8, color=FG, va="top")
    ax.set_ylabel("s late"); ax.set_xlim(0, 24)
    rows.append((day["label"], day["disc"], int(day["total"]), round(float(np.average(d, weights=n)), 0), int(chorus.sum()) * 5))
axes[-1].set_xticks(range(0, 25, 3)); axes[-1].set_xlabel("hour of day · red = chorus as played (smoothed delay above 68 % of the day's maximum, short runs and night dropped)")
fig.savefig(OUT / "01-five-days.svg"); plt.close(fig)
for r in rows: print(r)
