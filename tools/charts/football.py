"""Chart specs for the football atlas article (texts/football.html), read by assets/charts.js.

Every number comes from the atlas's own data (github.com/sandovabarbora/czefootball-player-pool-atlas), copied into
assets/football/ so the page links what it draws:
  per-head.json   data/snapshot/cze/per_capita.parquet (players in the nine strongest leagues per million, 2025/26)
  big5.json       docs/charts/big5.json (players with 450+ Big-5 minutes per season, 1995/96-2025/26)
  atlas-mf.json   docs/charts/atlas_MF.json, the home-eligible midfielders of 2025/26 (style and quality projections)
Writes assets/football/charts.json and the static fallback assets/football/per-head.svg (the other fallbacks are the
atlas's own renders). Rungs use the one palette of the atlas list: top-9 league in the held green, stepping-stone
league ink, other covered league grey, home league light grey, no minutes hairline.

    python3 tools/charts/football.py                         # build from the copies in assets/football/
    <atlas>/.venv/bin/python tools/charts/football.py --refresh <atlas>   # recopy from the atlas repository first
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets" / "football"
HTML = ROOT / "texts" / "football.html"
NB = " "

HELD = "#2f7a36"  # the pitch green the article's photograph holds
RUNG = {  # one rung palette for every chart and list of the atlas
    "top9": (HELD, "top-9 league"),
    "stepping_stone": ("#111111", "stepping-stone league"),
    "other": ("#8a8a8a", "other covered league"),
    "domestic": ("#c9c9c4", "home league"),
    "none": ("#e6e6e3", "no minutes"),
}
INK, GREY, LIGHT = "#111111", "#8a8a8a", "#c9c9c4"
D_HEAD, D_BIG5, D_MF = "../assets/football/per-head.json", "../assets/football/big5.json", "../assets/football/atlas-mf.json"


def refresh(atlas: Path) -> None:
    """Copy the minimal slices of the atlas's data that the charts draw."""
    import pandas as pd

    pc = pd.read_parquet(atlas / "data/snapshot/cze/per_capita.parquet")
    (A / "per-head.json").write_text(json.dumps({
        "source": "czefootball-player-pool-atlas, data/snapshot/cze/per_capita.parquet",
        "season": "2025-2026",
        "measure": "distinct players of each nationality who played in one of the nine strongest leagues, per million (Eurostat 1 January 2024)",
        "rows": [{"country": r.country, "name": r.name, "n": int(r.n_players), "population_m": float(r.population_m),
                  "per_million": float(r.per_million), "rank": int(r.rank)} for r in pc.itertuples()],
    }, ensure_ascii=False, indent=1) + "\n")
    (A / "big5.json").write_text((atlas / "docs/charts/big5.json").read_text())
    mf = json.loads((atlas / "docs/charts/atlas_MF.json").read_text())
    keep = ("k", "n", "lg", "t", "x", "y", "qx", "qy", "c", "cq", "nt", "m", "a", "tier")
    pts = [{k: p[k] for k in keep} for p in mf["points"] if p["h"]]
    names = sorted({t["text"] for pn in json.loads((atlas / "docs/atlas_meta.json").read_text())["atlas_MF.svg"]["panels"]
                    for t in pn["names"]})
    (A / "atlas-mf.json").write_text(json.dumps({
        "source": "czefootball-player-pool-atlas, docs/charts/atlas_MF.json, home-eligible rows only",
        "group": "MF", "season": mf["season"], "labelled": names,
        "fields": {"x, y": "style projection, PC1 and PC2", "qx, qy": "quality projection, PC1 and PC2",
                   "c, cq": "K-means cluster in each projection", "nt": "national-team call-up 2024-26",
                   "m": "minutes", "a": "age", "tier": "rung of the league"},
        "points": pts,
    }, ensure_ascii=False, separators=(",", ":")) + "\n")


def n(v: float, dp: int = 2) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "") + s


def season(s: str) -> str:
    return f"{s[:4]}/{s[7:9]}"


def img_alt(src: str) -> str:
    """spec.alt is the static <img>'s alt, read from the article so the two cannot drift apart."""
    m = re.search(r'<img[^>]*src="\.\./assets/football/' + re.escape(src) + r'"[^>]*alt="([^"]*)"', HTML.read_text())
    return m.group(1).replace("&amp;", "&") if m else ""


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


def per_head_svg(rows: list[dict]) -> str:
    """The static fallback: the same bars, drawn once."""
    w, top, rh, lab, bar = 640, 8, 26, 110, 440
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


def build() -> dict:
    charts = {}

    # fig. 1 · players in the nine strongest leagues per million, 2025/26
    H = json.loads((A / "per-head.json").read_text())
    rows = sorted(H["rows"], key=lambda r: r["rank"])
    (A / "per-head.svg").write_text(per_head_svg(rows))
    charts["per-head"] = {
        "alt": img_alt("per-head.svg"),
        "legend": [{"label": "Czechia", "c": HELD, "shape": "box", "o": 1}, {"label": "peer", "c": GREY, "shape": "box", "o": 1}],
        "panels": [{"h": 30 * len(rows),
                    "x": {"kind": "linear", "domain": [0, 14], "ticks": [0, 2, 4, 6, 8, 10, 12, 14], "label": "players per million, 2025/26"},
                    "y": {"kind": "cat", "domain": [r["name"] for r in rows]},
                    "marks": [{"type": "hbar", "o": 1, "rows": [
                        {"y": r["name"], "x1": r["per_million"], "c": HELD if r["country"] == "CZE" else GREY, "label": f"{r['per_million']:.2f}",
                         "tip": f"{r['name']}\n{r['per_million']:.2f} per million, {r['rank']} of {len(rows)}\n{r['n']} players · population {r['population_m']:.2f} m"}
                        for r in rows]}]}],
        "table": {"cols": ["country", "players", "population, m", "per million", "rank"],
                  "rows": [[r["name"], str(r["n"]), f"{r['population_m']:.2f}", f"{r['per_million']:.2f}", str(r["rank"])] for r in rows]},
        "data": [D_HEAD],
    }

    # fig. 2 · the Big-5 series, 2000/01-2025/26, as the atlas render draws it
    B = json.loads((A / "big5.json").read_text())
    i0 = B["seasons"].index("2000-2001")
    seasons = B["seasons"][i0:]
    years = [int(s[:4]) for s in seasons]
    home, contrast = B["home"], B["contrast"]
    others = [c for c in B["countries"] if c != home and c not in contrast]
    order = [home, *contrast, *others]

    def series(c: str, key: str) -> list:
        return [[y, v] for y, v in zip(years, B["countries"][c][key][i0:])]

    def style(c: str) -> dict:
        if c == home:
            return {"c": HELD, "w": 2.6}
        if c in contrast:
            return {"c": INK, "w": 1.5}
        return {"c": LIGHT, "w": 1.2}

    ticks = [2000, 2005, 2010, 2015, 2020, 2025]
    xax = {"kind": "linear", "domain": [2000, 2025], "ticks": ticks, "tickLabels": {t: f"{t}/{(t + 1) % 100:02d}" for t in ticks},
           "fmt": {"dp": 0, "nogroup": True, "pre": "season starting "}}
    cz = B["countries"][home]["n"][i0:]
    marks = [{"type": "line", "name": B["countries"][c]["name"], "pts": series(c, "n"), "fmt": {"dp": 0}, **style(c)} for c in reversed(order)]
    notes = [("2007-2008", -1), ("2015-2016", 1), ("2025-2026", 1)]
    marks.append({"type": "dots", "c": HELD, "r": 3.5, "pts": [
        {"x": int(s[:4]), "y": cz[seasons.index(s)], "label": f"{season(s)}: {cz[seasons.index(s)]}" if s != seasons[-1] else None,
         "dy": -8 if d < 0 else 16, "tip": f"Czechia, {season(s)}\n{cz[seasons.index(s)]} players with 450+ Big-5 minutes"} for s, d in notes]})
    # the last season's label cannot sit right of its dot, so it goes above it, ending at the dot
    marks.append({"type": "text", "x": years[-1], "y": cz[-1] + 2.4, "anchor": "end", "c": HELD, "s": f"{season(seasons[-1])}: {cz[-1]}"})
    per = [{"type": "line", "name": B["countries"][c]["name"], "pts": series(c, "per_million"), "fmt": {"dp": 2}, **style(c)}
           for c in reversed([home, *contrast])]
    charts["big5"] = {
        "alt": img_alt("big5-series.svg"),
        "layout": "rows",
        "legend": [{"label": "Czechia", "c": HELD}, {"label": " and ".join(B["countries"][c]["name"] for c in contrast), "c": INK},
                   {"label": "other peers: " + ", ".join(B["countries"][c]["name"] for c in others), "c": LIGHT}],
        "panels": [
            {"title": "Czech players in the Big-5 leagues, 2000/01–2025/26", "h": 300, "padRight": 34, "x": {**xax}, "marks": marks,
             "y": {"kind": "linear", "domain": [0, 40], "ticks": [0, 10, 20, 30, 40], "label": "players, 450+ minutes"}},
            {"title": "per million population", "h": 190, "padRight": 34, "x": {**xax, "label": "season"}, "marks": per,
             "y": {"kind": "linear", "domain": [0, 10], "ticks": [0, 2, 4, 6, 8, 10], "label": "players per million"}},
        ],
        "table": {"cols": ["season", *[B["countries"][c]["name"] for c in order], *[f"{B['countries'][c]['name']} per million" for c in [home, *contrast]]],
                  "rows": [[season(s), *[str(B["countries"][c]["n"][i0 + i]) for c in order],
                            *[f"{B['countries'][c]['per_million'][i0 + i]:.2f}" for c in [home, *contrast]]] for i, s in enumerate(seasons)]},
        "data": [D_BIG5],
    }

    # fig. 3 · midfielders 2025/26 in the style and the quality projection, coloured by the rung of the league
    M = json.loads((A / "atlas-mf.json").read_text())
    rank = {"domestic": 0, "other": 1, "stepping_stone": 2, "top9": 3}
    pts = sorted(M["points"], key=lambda p: (rank.get(p["tier"], 0), p["n"]))
    named = set(M["labelled"])

    def tip(p: dict, proj: str) -> str:
        x, y, cl = (p["x"], p["y"], p["c"]) if proj == "style" else (p["qx"], p["qy"], p["cq"])
        nt = "\nnational-team call-up 2024–26" if p["nt"] else ""
        return (f"{p['n']}, {p['t']}\n{p['lg'].split('-', 1)[1]} · {RUNG[p['tier']][1]}\n{n(p['m'], 0)} minutes · age {p['a']}" +
                f"\n{proj} projection: PC1 {n(x)}, PC2 {n(y)} · cluster {cl}{nt}")

    def panel(proj: str, title: str) -> dict:
        kx, ky = ("x", "y") if proj == "style" else ("qx", "qy")
        xs, ys = [p[kx] for p in pts], [p[ky] for p in pts]
        pad = lambda lo, hi: [float(math.floor(lo - 0.3)), float(math.ceil(hi + 0.3))]
        dots = [{"x": p[kx], "y": p[ky], "c": RUNG[p["tier"]][0], "ring": bool(p["nt"]),
                 "label": p["n"].split()[-1] if p["n"].split()[-1] in named else None, "tip": tip(p, proj)} for p in pts]
        xd, yd = pad(min(xs), max(xs)), pad(min(ys), max(ys))
        place_labels(dots, xd, yd)
        return {"title": title, "h": 340,
                "x": {"kind": "linear", "domain": xd, "label": "PC1", "tickfmt": {"dp": 0}},
                "y": {"kind": "linear", "domain": yd, "label": "PC2", "tickfmt": {"dp": 0}},
                "marks": [{"type": "dots", "r": 4.5, "pts": dots}]}

    present = [t for t in ("top9", "stepping_stone", "other", "domestic") if any(p["tier"] == t for p in pts)]
    charts["atlas-mf"] = {
        "alt": img_alt("atlas-mf.svg"),
        "legend": [*[{"label": RUNG[t][1], "c": RUNG[t][0], "shape": "o"} for t in present],
                   {"label": "○ ringed: national-team call-up 2024–26", "c": "#ffffff", "shape": "box", "o": 0}],
        "panels": [panel("style", "style projection, raw rates"), panel("quality", "quality projection, UEFA multipliers applied")],
        "table": {"cols": ["player", "club", "league", "rung", "minutes", "age", "style PC1", "style PC2", "cluster", "quality PC1", "quality PC2", "cluster", "call-up"],
                  "rows": [[p["n"], p["t"], p["lg"].split("-", 1)[1], RUNG[p["tier"]][1], str(p["m"]), str(p["a"]), n(p["x"]), n(p["y"]), p["c"],
                            n(p["qx"]), n(p["qy"]), p["cq"], "yes" if p["nt"] else ""] for p in sorted(pts, key=lambda p: p["n"])]},
        "data": [D_MF],
    }
    return charts


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--refresh":
        refresh(Path(sys.argv[2]))
    out = build()
    (A / "charts.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {A / 'charts.json'}: {', '.join(out)}")
