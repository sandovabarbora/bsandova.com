"""Chart specs for the Brand Reflection article (texts/brand-reflection.html), read by assets/charts.js.

Reads the two studies' spot-level metrics (CC-BY-4.0), joined exactly as tools/figures/brand_figures.py joins them
(colour table's brand_id = audio table's spot_id, 47 of 47). The join is published as assets/brand/spots.json:
with --dump the script rebuilds that file from tools/data/br-spots.parquet and tools/data/br-spots-audio.parquet
(needs pandas + pyarrow; the parquet files are not in the repository). Without --dump it only reads spots.json
(stdlib only) and writes assets/brand/charts.json.

    /usr/bin/python3 tools/charts/brand_reflection.py --dump   # refresh spots.json from the parquet files
    python3 tools/charts/brand_reflection.py                   # charts.json from spots.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets/brand"
SPOTS = A / "spots.json"

if "--dump" in sys.argv:
    import pandas as pd

    c = pd.read_parquet(ROOT / "tools/data/br-spots.parquet")
    s = pd.read_parquet(ROOT / "tools/data/br-spots-audio.parquet")
    d = c.merge(s[["spot_id", "music_fraction", "voice_fraction", "tempo_bpm", "mode"]], left_on="brand_id", right_on="spot_id")
    rows = [{"spot_id": r.spot_id, "brand": r.brand, "sector": r.sector, "color_gap_deg": round(float(r.color_gap_deg), 3),
             "brand_anchor_share": round(float(r.brand_anchor), 6), "voice_fraction": round(float(r.voice_fraction), 5),
             "music_fraction": round(float(r.music_fraction), 5), "tempo_bpm": round(float(r.tempo_bpm), 1), "mode": r["mode"]}
            for _, r in d.iterrows()]
    SPOTS.write_text(json.dumps({"source": "color-fingerprint-cz spots.parquet + sound-fingerprint-cz spots_audio.parquet, CC-BY-4.0; "
                                           "joined on spot id by tools/figures/brand_figures.py", "spots": rows}, ensure_ascii=False, indent=1))
    print(len(rows), "spots →", SPOTS)

D = json.loads(SPOTS.read_text())["spots"]
DATA = ["../assets/brand/spots.json"]


def name(r: dict) -> str:
    """'Albert · 03' from the spot id; the two manually added spots carry the brand only."""
    for tok in r["spot_id"].split("_"):
        if tok.isdigit() and len(tok) == 2:
            return f"{r['brand']} · {tok}"
    return r["brand"]


def pct(v: float, dp: int = 0) -> str:
    return f"{v * 100:.{dp}f} %"


def deg(v: float) -> str:
    return f"{v:.0f}°"


def camp(g: float) -> str:
    return "brand-led (under 20°)" if g < 20 else ("world-led (over 100°)" if g > 100 else "in between")


charts = {}

# fig. 1 · hue distance per spot, sorted, coloured by camp
by_gap = sorted(D, key=lambda r: r["color_gap_deg"])
ccol = lambda g: "held" if g < 20 else ("ink" if g > 100 else "light")  # noqa: E731
charts["hue-distance"] = {
    "alt": "47 bars sorted by hue distance from the brand anchor: brand-led spots under 20 degrees, world-led spots over 100 and the rest in between, with a 90-degree reference line.",
    "legend": [{"label": "brand-led, under 20°", "c": "held", "shape": "box", "o": 0.85}, {"label": "in between", "c": "light", "shape": "box", "o": 0.85},
               {"label": "world-led, over 100°", "c": "ink", "shape": "box", "o": 0.85}],
    "panels": [{"h": 260, "x": {"kind": "cat", "domain": [r["spot_id"] for r in by_gap], "labels": False, "label": "47 spots, sorted"},
                "y": {"kind": "linear", "domain": [0, 180], "ticks": [0, 45, 90, 135, 180], "label": "hue distance (°)", "tickfmt": {"dp": 0}},
                "marks": [{"type": "rule", "axis": "y", "v": 90, "c": "ink", "dash": "dot", "label": "90° (no stated rationale)"},
                          {"type": "vbar", "rows": [{"x": r["spot_id"], "y1": r["color_gap_deg"], "c": ccol(r["color_gap_deg"]),
                                                     "tip": f"{name(r)} · {r['sector']}\nhue distance {deg(r['color_gap_deg'])}\n{camp(r['color_gap_deg'])}"}
                                                    for r in by_gap]}]}],
    "table": {"cols": ["spot", "sector", "hue distance (°)", "camp"],
              "rows": [[name(r), r["sector"], f"{r['color_gap_deg']:.0f}", camp(r["color_gap_deg"])] for r in by_gap]},
    "data": DATA,
}

# fig. 2 · voice and music share per spot, sorted by music share, stacked (voice below, music on top)
by_music = sorted(D, key=lambda r: -r["music_fraction"])
rows = []
for r in by_music:
    v, m = r["voice_fraction"] * 100, r["music_fraction"] * 100
    tip = f"{name(r)} · {r['sector']}\nvoice {pct(r['voice_fraction'])} · non-speech {pct(r['music_fraction'])}\n{'music-led' if r['music_fraction'] > .5 else 'voice-led'}"
    rows.append({"x": r["spot_id"], "y0": 0, "y1": round(v, 2), "c": "light", "tip": tip})
    rows.append({"x": r["spot_id"], "y0": round(v, 2), "y1": round(v + m, 2), "c": "held" if r["music_fraction"] > .5 else "grey", "tip": tip})
charts["voice-music"] = {
    "alt": "47 stacked bars of voice share and non-speech (music and effects) share sorted by non-speech share; three bars cross the 50 percent line.",
    "legend": [{"label": "voice", "c": "light", "shape": "box", "o": 0.85}, {"label": "non-speech (music, effects)", "c": "grey", "shape": "box", "o": 0.85},
               {"label": "non-speech, music-led spot (over 50 %)", "c": "held", "shape": "box", "o": 0.85}],
    "panels": [{"h": 240, "x": {"kind": "cat", "domain": [r["spot_id"] for r in by_music], "labels": False, "label": "47 spots, sorted by non-speech share"},
                "y": {"kind": "linear", "domain": [0, 100], "ticks": [0, 25, 50, 75, 100], "label": "share of runtime (%)", "tickfmt": {"dp": 0}},
                "marks": [{"type": "vbar", "rows": rows},
                          {"type": "rule", "axis": "y", "v": 50, "c": "ink", "dash": "dot"}]}],
    "table": {"cols": ["spot", "sector", "voice (%)", "non-speech (%)"],
              "rows": [[name(r), r["sector"], f"{r['voice_fraction'] * 100:.0f}", f"{r['music_fraction'] * 100:.0f}"] for r in by_music]},
    "data": DATA,
}

# fig. 3 · the two commitments on one plane
alb = [r for r in D if r["brand"] == "Albert"]
alb_first = min(alb, key=lambda r: r["spot_id"])["spot_id"]
pts = []
for r in D:
    hl = {"Pilsner Urquell": "held", "Albert": "ink"}.get(r["brand"])
    p = {"x": round(r["color_gap_deg"], 2), "y": round(r["music_fraction"] * 100, 2), "c": hl or "light", "r": 5.5 if hl else 4.5,
         "tip": f"{name(r)} · {r['sector']}\nhue distance {deg(r['color_gap_deg'])} · non-speech {pct(r['music_fraction'])}"}
    if r["brand"] == "Pilsner Urquell":
        p["label"] = "Pilsner Urquell"
    elif r["spot_id"] == alb_first:
        p["label"], p["dy"] = "Albert ×5", 15
    pts.append(p)
pts.sort(key=lambda p: p["c"] != "light")  # highlighted spots on top
charts["two-commitments"] = {
    "alt": "Scatter of 47 spots: hue distance on the x axis, non-speech share on the y axis; Pilsner Urquell alone in the top right, Albert's five spots at the far right and bottom.",
    "legend": [{"label": "Pilsner Urquell", "c": "held", "shape": "o"}, {"label": "Albert, five spots", "c": "ink", "shape": "o"},
               {"label": "other spots", "c": "light", "shape": "o"}],
    "panels": [{"h": 340, "x": {"kind": "linear", "domain": [0, 180], "ticks": [0, 30, 60, 90, 120, 150, 180], "label": "hue distance to the brand anchor (°)", "tickfmt": {"dp": 0}},
                "y": {"kind": "linear", "domain": [0, 100], "ticks": [0, 25, 50, 75, 100], "label": "non-speech share of the soundtrack (%)", "tickfmt": {"dp": 0}},
                "marks": [{"type": "span", "v0": 0, "v1": 20, "c": "held", "o": 0.07, "label": "brand-colour camp"},
                          {"type": "span", "v0": 100, "v1": 180, "c": "ink", "o": 0.05, "label": "world-colour camp"},
                          {"type": "area", "name": "music-led", "c": "grey", "o": 0.07, "notip": True, "pts": [[0, 50, 100], [180, 50, 100]]},
                          {"type": "rule", "axis": "x", "v": 90, "c": "grey", "dash": "dot"},
                          {"type": "rule", "axis": "y", "v": 50, "c": "grey", "dash": "dot", "label": "music-led"},
                          {"type": "dots", "pts": pts}]}],
    "table": {"cols": ["spot", "sector", "hue distance (°)", "non-speech (%)"],
              "rows": [[name(r), r["sector"], f"{r['color_gap_deg']:.0f}", f"{r['music_fraction'] * 100:.0f}"] for r in sorted(D, key=lambda r: r["color_gap_deg"])]},
    "data": DATA,
}

n_brand, n_world, n_music = (sum(r["color_gap_deg"] < 20 for r in D), sum(r["color_gap_deg"] > 100 for r in D), sum(r["music_fraction"] > .5 for r in D))
(A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
print(len(D), "spots; brand-led", n_brand, "world-led", n_world, "music-led", n_music, ";", len(charts), "charts →", A / "charts.json")
