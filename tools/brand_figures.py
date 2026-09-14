"""Brand Reflection synthesis figures from the two studies' spot-level parquet files (CC-BY-4.0 derived metrics)."""
import pathlib, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = pathlib.Path(__file__).resolve().parent.parent; OUT = R / "assets/brand"; OUT.mkdir(exist_ok=True)
BG, FG, FG2, LINE, ACID, BUS, MINT, VIOLET = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36", "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": LINE, "axes.labelcolor": FG2,
  "xtick.color": FG2, "ytick.color": FG2, "text.color": FG, "grid.color": LINE, "grid.alpha": .6, "axes.grid": True, "axes.spines.top": False,
  "axes.spines.right": False, "font.family": "monospace", "font.size": 9, "legend.frameon": False, "figure.constrained_layout.use": True, "svg.fonttype": "none"})
c = pd.read_parquet(R / "tools/data/br-spots.parquet"); s = pd.read_parquet(R / "tools/data/br-spots-audio.parquet")
d = c.merge(s[["spot_id", "music_fraction", "voice_fraction", "tempo_bpm", "mode"]], left_on="brand_id", right_on="spot_id")
print(len(d), "spots joined;", "brand-led <20°:", (d.color_gap_deg < 20).sum(), "world-led >100°:", (d.color_gap_deg > 100).sum(), "music-led:", (d.music_fraction > .5).sum())
# fig 1: the two commitments, one plane
fig, ax = plt.subplots(figsize=(8, 5))
ax.axvspan(0, 20, color=ACID, alpha=.06, lw=0); ax.axvspan(100, 180, color=VIOLET, alpha=.06, lw=0); ax.axhspan(50, 100, color=BUS, alpha=.06, lw=0)
ax.scatter(d.color_gap_deg, d.music_fraction * 100, s=34, c=[FG2] * len(d), edgecolors=BG, lw=.5, zorder=3)
for name, col in (("Pilsner Urquell", ACID), ("Albert", BUS)):
    m = d.brand == name; ax.scatter(d[m].color_gap_deg, d[m].music_fraction * 100, s=54, c=col, edgecolors=BG, lw=.5, zorder=4)
    for _, r in d[m].iterrows(): ax.annotate(name if name == "Pilsner Urquell" else "", (r.color_gap_deg, r.music_fraction * 100), xytext=(6, 4), textcoords="offset points", fontsize=8, color=col)
ax.annotate("Albert ×5", (d[d.brand == "Albert"].color_gap_deg.mean(), d[d.brand == "Albert"].music_fraction.mean() * 100), xytext=(-52, 10), textcoords="offset points", fontsize=8, color=BUS)
ax.axvline(90, color=LINE, ls=":", lw=1); ax.axhline(50, color=LINE, ls=":", lw=1)
ax.text(2, 96, "brand-colour camp", color=FG2, fontsize=8); ax.text(104, 96, "world-colour camp", color=FG2, fontsize=8); ax.text(2, 53, "music-led", color=FG2, fontsize=8)
ax.set_xlim(0, 180); ax.set_ylim(0, 100); ax.set_xlabel("hue distance, brand anchor → dominant on-screen colour (°)"); ax.set_ylabel("music share of the soundtrack (%)")
fig.savefig(OUT / "01-two-commitments.svg"); plt.close(fig)
# fig 2: hue distance per spot, sorted, coloured by camp
dd = d.sort_values("color_gap_deg"); cols = [ACID if g < 20 else (VIOLET if g > 100 else FG2) for g in dd.color_gap_deg]
fig, ax = plt.subplots(figsize=(8, 3.6)); ax.bar(range(len(dd)), dd.color_gap_deg, color=cols, width=.8)
ax.axhline(90, color=FG, ls=":", lw=1); ax.text(0.5, 92, "90°: reads as a different colour", color=FG2, fontsize=8)
ax.set_xticks([]); ax.set_xlabel("47 spots, sorted"); ax.set_ylabel("hue distance (°)")
fig.savefig(OUT / "02-hue-distance.svg"); plt.close(fig)
# fig 3: voice/music share per spot sorted
ds = d.sort_values("music_fraction", ascending=False)
fig, ax = plt.subplots(figsize=(8, 3.2)); ax.bar(range(len(ds)), ds.voice_fraction * 100, color=FG2, width=.8, label="voice"); ax.bar(range(len(ds)), ds.music_fraction * 100, bottom=ds.voice_fraction * 100, color=[ACID if m > .5 else BUS for m in ds.music_fraction], width=.8, label="music")
ax.axhline(50, color=FG, ls=":", lw=1); ax.set_xticks([]); ax.set_xlabel("47 spots, sorted by music share"); ax.set_ylabel("share of runtime (%)"); ax.legend(loc="lower right")
fig.savefig(OUT / "03-voice-music.svg"); plt.close(fig)
print("median tempo", d.tempo_bpm.median().round(0), "minor share", (d["mode"] == "minor").mean().round(2))
