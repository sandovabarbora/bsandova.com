"""Chart specs for the hockey atlas article (texts/hockey.html), read by assets/charts.js.

The hockey atlas (github.com/sandovabarbora/czehockey-player-pool-atlas) does not commit its fetched data, so the
charts take their numbers from what the atlas publishes, copied into assets/hockey/ so the page links what it draws:
  per-head.json         NHL players per million, 2025/26: the values of the atlas summary (docs/index.html) and the
                        population constants of src/international_benchmark.py
  atlas-forwards.json   every point of the atlas render site/source/figures/atlas_forwards.svg, read back to PC1 and PC2
  atlas-defense.json    with the axis calibration of docs/atlas_meta.json: cluster, World Championship ring, the ten
                        named players and their 2024/25 -> 2025/26 moves
Writes assets/hockey/charts.json and the static fallback assets/hockey/per-head.svg (the atlas fallbacks are the
atlas's own renders). The map data carry no league per point, so the maps are drawn in one colour, the held blue.

    python3 tools/charts/hockey.py                    # build from the copies in assets/hockey/
    python3 tools/charts/hockey.py --refresh <atlas>  # recopy from the atlas repository first
"""
from __future__ import annotations

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets" / "hockey"
HTML = ROOT / "texts" / "hockey.html"
NB = " "
HELD = "#1F5FD6"  # the blue the article's photograph holds
INK, GREY = "#111111", "#8a8a8a"
D_HEAD = "../assets/hockey/per-head.json"
SPELL = {"Pastrnak": "Pastrňák", "Necas": "Nečas", "Jasek": "Jašek"}  # the render drops the diacritics the article writes
SVGNS, XL = "{http://www.w3.org/2000/svg}", "{http://www.w3.org/1999/xlink}href"
PER_HEAD = [("CAN", "Canada", 8.05), ("SWE", "Sweden", 7.17), ("FIN", "Finland", 6.07), ("SVK", "Slovakia", 1.67),
            ("CZE", "Czechia", 1.38), ("USA", "USA", 0.67)]  # atlas summary, docs/index.html, render of 18 May 2026


def refresh(atlas: Path) -> None:
    src = (atlas / "src/international_benchmark.py").read_text()
    pop = {k: float(v) for k, v in re.findall(r'"([A-Z]{3})": ([\d.]+),', src.split("POPULATION_M", 1)[1].split("}", 1)[0])}
    (A / "per-head.json").write_text(json.dumps({
        "source": "czehockey-player-pool-atlas: per-million values from the atlas summary (docs/index.html, render of 18 May 2026); "
                  "populations from POPULATION_M in src/international_benchmark.py (about 2024, no source recorded)",
        "season": "2025-2026",
        "measure": "players born in the country with at least ten NHL games in 2025/26, per million population",
        "rows": [{"country": c, "name": nm, "per_million": v, "population_m": pop[c]} for c, nm, v in PER_HEAD],
    }, ensure_ascii=False, indent=1) + "\n")
    meta = json.loads((atlas / "docs/atlas_meta.json").read_text())
    for key in ("forwards", "defense"):
        (A / f"atlas-{key}.json").write_text(json.dumps(read_atlas(atlas / f"site/source/figures/atlas_{key}.svg", meta[f"atlas_{key}.svg"]),
                                                        ensure_ascii=False, separators=(",", ":")) + "\n")


def read_atlas(svg: Path, meta: dict) -> dict:
    """Points of the matplotlib render, mapped back to principal components with the atlas's own tick calibration."""
    root = ET.parse(svg).getroot()
    panels = []
    for ax, pm in zip([g for g in root.iter(SVGNS + "g") if (g.get("id") or "").startswith("axes_")], meta["panels"]):
        cx, cy = pm["cx"], pm["cy"]
        val = lambda px, py: (round(cx["a"] * px + cx["b"], 3), round(cy["a"] * py + cy["b"], 3))
        label = {c["id"]: c["label"] for c in pm["clusters"]}
        pts = []
        for g in ax:
            gid = g.get("id") or ""
            if gid in label:
                for u in g.iter(SVGNS + "use"):
                    px, py = float(u.get("x")), float(u.get("y"))
                    x, y = val(px, py)
                    pts.append({"x": x, "y": y, "c": label[gid], "px": px, "py": py})
        near = lambda qx, qy: min(pts, key=lambda p: math.hypot(p["px"] - qx, p["py"] - qy))
        for q in pm["ring"]["pts"]:
            near(*q)["wc"] = 1
        for t in pm["names"]:
            near(t["px"], t["py"])["name"] = SPELL.get(t["text"], t["text"])
        # the arrows: curved patches from a player's 2024/25 position to his 2025/26 point
        for g in ax:
            if not (g.get("id") or "").startswith("patch_"):
                continue
            p = next(g.iter(SVGNS + "path"), None)
            if p is None or "opacity: 0.85" not in (p.get("style") or ""):
                continue
            nums = [float(v) for v in re.findall(r"-?[\d.]+", p.get("d"))]
            end = near(nums[-2], nums[-1])
            gap = math.hypot(end["px"] - nums[-2], end["py"] - nums[-1])
            assert gap < 8 and "from" not in end, (end, gap)
            end["from"] = list(val(nums[0], nums[1]))
        for p in pts:
            del p["px"], p["py"]
        panels.append({"title": pm["title"], "clusters": [{"label": c["label"], "n": c["n"]} for c in pm["clusters"]], "points": pts})
    return {"source": f"czehockey-player-pool-atlas, {svg.parent.name}/{svg.name} with docs/atlas_meta.json (axis calibration)",
            "render": "18 May 2026", "panels": panels}


def n(v: float, dp: int = 2) -> str:
    return ("−" if v < 0 else "") + f"{abs(v):.{dp}f}"


def img_alt(src: str) -> str:
    m = re.search(r'<img[^>]*src="\.\./assets/hockey/' + re.escape(src) + r'"[^>]*alt="([^"]*)"', HTML.read_text())
    return m.group(1).replace("&amp;", "&") if m else ""


def per_head_svg(rows: list[dict]) -> str:
    w, top, rh, lab, bar = 640, 8, 26, 90, 460
    mx = max(r["per_million"] for r in rows)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {top + rh * len(rows) + 8}" font-family="JetBrains Mono, monospace" font-size="12">',
           f'<rect width="{w}" height="{top + rh * len(rows) + 8}" fill="#ffffff"/>']
    for i, r in enumerate(rows):
        y = top + i * rh
        c = HELD if r["country"] == "CZE" else GREY
        out.append(f'<text x="0" y="{y + 16}" fill="#111111">{r["name"]}</text>')
        out.append(f'<rect x="{lab}" y="{y + 4}" width="{bar * r["per_million"] / mx:.1f}" height="16" fill="{c}"/>')
        out.append(f'<text x="{lab + bar * r["per_million"] / mx + 8:.1f}" y="{y + 16}" fill="#111111">{r["per_million"]:.2f}</text>')
    return "\n".join(out + ["</svg>"]) + "\n"


def place_labels(dots: list[dict], xdom: list, ydom: list, obstacles: list | None = None, keep: tuple = ()) -> None:
    """Keep a direct label only where it overlaps no other label and at most two dots, at the narrowest two-panel size
    (a 752 px column: plot 333 x 276 px, 11 px mono labels at 6.6 px a character), and set its dy to the clearest of
    charts.js's right-hand spots; charts.js puts a label left of its dot when it does not fit on the right. Names in
    `keep` (the ones the text names) are placed first and always kept. A dropped name stays in the tooltip and the table."""
    pw, ph, cw = 333.0, 276.0, 6.6
    px = lambda x: (x - xdom[0]) / (xdom[1] - xdom[0]) * pw
    py = lambda y: (ydom[1] - y) / (ydom[1] - ydom[0]) * ph
    circles = [(px(d["x"]), py(d["y"]), 4.5 + (3 if d.get("ring") else 0), id(d)) for d in dots]
    circles += [(px(x), py(y), 2.2, None) for x, y in obstacles or []]
    placed: list[tuple] = []
    hit = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    cx, cy = (xdom[0] + xdom[1]) / 2, (ydom[0] + ydom[1]) / 2
    order = sorted((d for d in dots if d.get("label")),
                   key=lambda d: (d["label"] not in keep, not d.get("ring"), -abs(d["x"] - cx) - abs(d["y"] - cy)))
    for d in order:
        x, y, w = px(d["x"]), py(d["y"]), cw * len(d["label"])
        if x + 7 + 6.4 * len(d["label"]) > pw + 12:  # charts.js's own fit test: the label goes left of the dot
            spots = [(4, (x - 7 - w, y - 7, w, 14))]
        else:
            spots = [(dy, (x + 7, y + dy - 11, w, 14)) for dy in (4, -9, 15) if x + 7 + w <= pw + 12]
        best = None
        for dy, box in spots:
            if any(hit((box[0] - 4, box[1], w + 8, 14), q) for q in placed):
                continue
            covered = sum(hit(box, (c[0] - c[2], c[1] - c[2], 2 * c[2], 2 * c[2])) for c in circles if c[3] != id(d))
            if best is None or covered < best[0]:
                best = (covered, dy, box)
        if best is None or (best[0] > 2 and d["label"] not in keep):
            d["label"] = None
        else:
            d["dy"] = best[1]
            placed.append(best[2])


def atlas_chart(key: str, what: str) -> dict:
    D = json.loads((A / f"atlas-{key}.json").read_text())
    titles = ["style map, no league factors", "quality map, league factors applied"]
    panels, trows = [], []
    for P, title in zip(D["panels"], titles):
        proj = title.split(" ")[0]
        pts = sorted(P["points"], key=lambda p: ("name" in p, p.get("wc", 0)))
        xs, ys = [p["x"] for p in pts] + [p["from"][0] for p in pts if "from" in p], [p["y"] for p in pts] + [p["from"][1] for p in pts if "from" in p]
        marks = [{"type": "line", "name": p.get("name", "move"), "notip": True, "c": GREY, "w": 1.2, "pts": [p["from"], [p["x"], p["y"]]]}
                 for p in pts if "from" in p]
        marks.append({"type": "dots", "r": 2.2, "c": GREY, "pts": [
            {"x": p["from"][0], "y": p["from"][1], "tip": f"{p.get('name', 'a player')}, 2024/25\n{proj} map: PC1 {n(p['from'][0])}, PC2 {n(p['from'][1])}"}
            for p in pts if "from" in p]})

        def tip(p: dict) -> str:
            head = p.get("name", {"forwards": "a forward", "defencemen": "a defenceman"}[what] + " in the pool")
            extra = ("\nWorld Championship 2024/25" if p.get("wc") else "") + \
                    (f"\n2024/25 at PC1 {n(p['from'][0])}, PC2 {n(p['from'][1])}" if "from" in p else "")
            return f"{head}\n{proj} map: PC1 {n(p['x'])}, PC2 {n(p['y'])} · cluster {p['c']}{extra}"

        dots = [{"x": p["x"], "y": p["y"], "c": HELD, "o": 0.9 if ("name" in p or p.get("wc")) else 0.4, "ring": bool(p.get("wc")),
                 "label": p.get("name"), "tip": tip(p)} for p in pts]
        xd, yd = [math.floor(min(xs) - 0.3), math.ceil(max(xs) + 0.3)], [math.floor(min(ys) - 0.3), math.ceil(max(ys) + 0.3)]
        place_labels(dots, xd, yd, [p["from"] for p in pts if "from" in p], keep=("Pastrňák", "Červenka", "Kulich", "Nečas", "Zacha"))
        marks.append({"type": "dots", "r": 3.8, "pts": dots})
        panels.append({"title": title, "h": 340,
                       "x": {"kind": "linear", "domain": xd, "label": "PC1", "tickfmt": {"dp": 0}},
                       "y": {"kind": "linear", "domain": yd, "label": "PC2", "tickfmt": {"dp": 0}},
                       "marks": marks})
        for c in P["clusters"]:
            cp = [p for p in P["points"] if p["c"] == c["label"]]
            trows.append([f"{proj} map", c["label"], str(len(cp)), str(sum(p.get("wc", 0) for p in cp)),
                          ", ".join(sorted(p["name"] for p in cp if "name" in p)) or "–"])
    return {
        "alt": img_alt(f"atlas-{key}.svg"),
        "legend": [{"label": f"{what} in the mapped pool", "c": HELD, "shape": "o"},
                   {"label": "○ ringed: World Championship 2024/25", "c": "#ffffff", "shape": "box", "o": 0},
                   {"label": "move from the 2024/25 position (small grey dot) to 2025/26", "c": GREY}],
        "panels": panels,
        "table": {"cols": ["map", "cluster", "players", "World Championship 2024/25", "named"], "rows": trows},
        "data": [f"../assets/hockey/atlas-{key}.json"],
    }


def build() -> dict:
    charts = {}
    H = json.loads((A / "per-head.json").read_text())
    rows = H["rows"]
    (A / "per-head.svg").write_text(per_head_svg(rows))
    charts["per-head"] = {
        "alt": img_alt("per-head.svg"),
        "legend": [{"label": "Czechia", "c": HELD, "shape": "box", "o": 1}, {"label": "other country", "c": GREY, "shape": "box", "o": 1}],
        "panels": [{"h": 32 * len(rows),
                    "x": {"kind": "linear", "domain": [0, 9], "ticks": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "label": "NHL players per million, 2025/26"},
                    "y": {"kind": "cat", "domain": [r["name"] for r in rows]},
                    "marks": [{"type": "hbar", "o": 1, "rows": [
                        {"y": r["name"], "x1": r["per_million"], "c": HELD if r["country"] == "CZE" else GREY, "label": f"{r['per_million']:.2f}",
                         "tip": f"{r['name']}\n{r['per_million']:.2f} NHL players per million, {i + 1} of {len(rows)}\npopulation {r['population_m']:g} m (code constant)"}
                        for i, r in enumerate(rows)]}]}],
        "table": {"cols": ["country", "per million", "population, m (code constant)"],
                  "rows": [[r["name"], f"{r['per_million']:.2f}", f"{r['population_m']:g}"] for r in rows]},
        "data": [D_HEAD],
    }
    charts["atlas-forwards"] = atlas_chart("forwards", "forwards")
    charts["atlas-defense"] = atlas_chart("defense", "defencemen")
    return charts


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--refresh":
        refresh(Path(sys.argv[2]))
    out = build()
    (A / "charts.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {A / 'charts.json'}: {', '.join(out)}")
