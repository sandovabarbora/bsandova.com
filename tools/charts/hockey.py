"""Chart specs for the hockey atlas article (texts/hockey.html), read by assets/charts.js.

Every number comes from the atlas's own outputs (github.com/sandovabarbora/czehockey-player-pool-atlas, outputs/*.json),
copied unchanged into assets/hockey/ so the page links what it draws:
  q1_per_million.json     players with at least the pro-rated games threshold per million, 2025/26, and the NHL series
                          1995/96-2025/26 per nation
  q2_break_model.json     the local-level model with two step changes on each NHL series: fitted level, 90 % interval,
                          step seasons and their probabilities
  q6_national_team.json   World Championship and Olympic rosters since 2010 by the league of each player's club
Writes assets/hockey/charts.json and the static fallbacks per-head.svg, nhl-series.svg and roster.svg. Rungs use the
atlas palette: NHL in the held jersey blue, rung 2 ink, Extraliga light grey; the KHL, which the atlas does not cover,
mid grey, other leagues pale.

    python3 tools/charts/hockey.py                    # build from the copies in assets/hockey/
    python3 tools/charts/hockey.py --refresh <atlas>  # recopy outputs/ from the atlas repository first
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets" / "hockey"
HTML = ROOT / "texts" / "hockey.html"
FILES = ("q1_per_million.json", "q2_break_model.json", "q6_national_team.json")
HELD = "#1F5FD6"  # the jersey blue the article's photograph holds and the atlas uses for rung 1
INK, GREY, LIGHT, PALE = "#111111", "#8a8a8a", "#c9c9c4", "#e6e6e3"
CATS = [("1", "NHL", HELD), ("2", "rung 2 (SHL, Liiga, NL, DEL)", INK), ("home", "Extraliga", LIGHT),
        ("khl", "KHL (not covered)", GREY), ("other", "other league", PALE)]
EVENT = {"WC": "World Championship", "OG": "Olympics"}


def refresh(atlas: Path) -> None:
    for f in FILES:
        shutil.copyfile(atlas / "outputs" / f, A / f)


def load(f: str) -> dict:
    return json.loads((A / f).read_text())


def img_alt(src: str) -> str:
    """spec.alt is the static <img>'s alt, read from the article so the two cannot drift apart."""
    m = re.search(r'<img[^>]*src="\.\./assets/hockey/' + re.escape(src) + r'"[^>]*alt="([^"]*)"', HTML.read_text())
    return m.group(1).replace("&amp;", "&") if m else ""


def year(season: str) -> int:
    return int(season[:4])


def svg_open(w: int, h: int) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="JetBrains Mono, monospace" font-size="12">',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>']


def per_head_svg(rows: list[dict], median: float) -> str:
    w, top, rh, lab, bar = 640, 8, 26, 100, 450
    mx = max(r["nhl_per_million"] for r in rows)
    h = top + rh * len(rows) + 8
    out = svg_open(w, h)
    for i, r in enumerate(rows):
        y = top + i * rh
        c = HELD if r["iso3"] == "CZE" else GREY
        out.append(f'<text x="0" y="{y + 16}" fill="{INK}">{r["name"]}</text>')
        out.append(f'<rect x="{lab}" y="{y + 4}" width="{bar * r["nhl_per_million"] / mx:.1f}" height="16" fill="{c}"/>')
        out.append(f'<text x="{lab + bar * r["nhl_per_million"] / mx + 8:.1f}" y="{y + 16}" fill="{INK}">{r["nhl_per_million"]:.2f}</text>')
    x = lab + bar * median / mx
    out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{h - 4}" stroke="{INK}" stroke-dasharray="5 3"/>')
    return "\n".join(out + ["</svg>"]) + "\n"


def series_svg(years: list[int], n: list, fit: dict) -> str:
    w, h, l, r, t, b = 640, 300, 40, 12, 12, 30
    X = lambda v: l + (v - years[0]) / (years[-1] - years[0]) * (w - l - r)
    Y = lambda v: h - b - v / 70 * (h - t - b)
    out = svg_open(w, h)
    for v in (0, 20, 40, 60):
        out.append(f'<line x1="{l}" x2="{w - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{PALE}"/><text x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" fill="{INK}">{v}</text>')
    for v in (1995, 2005, 2015, 2025):
        out.append(f'<text x="{X(v):.1f}" y="{h - 10}" text-anchor="middle" fill="{INK}">{v}/{(v + 1) % 100:02d}</text>')
    band = [f"{X(y):.1f},{Y(v):.1f}" for y, v in zip(years, fit["hi"])] + [f"{X(y):.1f},{Y(v):.1f}" for y, v in reversed(list(zip(years, fit["lo"])))]
    out.append(f'<polygon points="{" ".join(band)}" fill="{HELD}" fill-opacity="0.14"/>')
    out.append(f'<polyline points="{" ".join(f"{X(y):.1f},{Y(v):.1f}" for y, v in zip(years, fit["median"]))}" fill="none" stroke="{HELD}" stroke-width="2"/>')
    out += [f'<circle cx="{X(y):.1f}" cy="{Y(v):.1f}" r="3.5" fill="{INK}"/>' for y, v in zip(years, n) if v is not None]
    return "\n".join(out + ["</svg>"]) + "\n"


def roster_svg(events: list[dict]) -> str:
    w, h, l, t, b = 640, 260, 30, 10, 30
    step = (w - l) / len(events)
    Y = lambda v: h - b - v / 30 * (h - t - b)
    out = svg_open(w, h)
    for i, e in enumerate(events):
        x, y0 = l + i * step + step * 0.15, 0
        for k, _, c in CATS:
            v = e[k]
            if v:
                out.append(f'<rect x="{x:.1f}" y="{Y(y0 + v):.1f}" width="{step * 0.7:.1f}" height="{Y(y0) - Y(y0 + v):.1f}" fill="{c}"/>')
            y0 += v
    return "\n".join(out + ["</svg>"]) + "\n"


def per_head() -> dict:
    Q = load("q1_per_million.json")["headline"]
    rows = sorted(Q["nations"], key=lambda r: r["rank_nhl"])
    med = Q["peer_median"]["nhl_per_million"]
    (A / "per-head.svg").write_text(per_head_svg(rows, med))
    return {
        "alt": img_alt("per-head.svg"),
        "legend": [{"label": "Czechia", "c": HELD, "shape": "box", "o": 1}, {"label": "peer", "c": GREY, "shape": "box", "o": 1},
                   {"label": "median of the nine peers", "c": INK, "dash": "dash"}],
        "panels": [{"h": 30 * len(rows),
                    "x": {"kind": "linear", "domain": [0, 8], "ticks": [0, 1, 2, 3, 4, 5, 6, 7, 8], "label": f"NHL players per million, {Q['season']}"},
                    "y": {"kind": "cat", "domain": [r["name"] for r in rows]},
                    "marks": [
                        {"type": "hbar", "o": 1, "rows": [
                            {"y": r["name"], "x1": r["nhl_per_million"], "c": HELD if r["iso3"] == "CZE" else GREY, "label": f"{r['nhl_per_million']:.2f}",
                             "tip": f"{r['name']}\n{r['nhl_per_million']:.2f} NHL players per million, {r['rank_nhl']} of {len(rows)}\n"
                                    f"{r['nhl']} players · population {r['population'] / 1e6:.2f} m\nNHL + rung 2: {r['top5']} players, "
                                    f"{r['top5_per_million']:.2f} per million, {r['rank_top5']} of {len(rows)}"} for r in rows]},
                        {"type": "rule", "axis": "x", "v": med, "c": INK, "dash": "dash",
                         "tip": f"median of the nine peers\n{med:.2f} NHL players per million"}]}],
        "table": {"cols": ["nation", "NHL players", "per million", "rank", "NHL + rung 2", "per million", "rank", "population, m"],
                  "rows": [[r["name"], str(r["nhl"]), f"{r['nhl_per_million']:.2f}", str(r["rank_nhl"]), str(r["top5"]),
                            f"{r['top5_per_million']:.2f}", str(r["rank_top5"]), f"{r['population'] / 1e6:.2f}"] for r in rows]},
        "data": ["../assets/hockey/q1_per_million.json"],
    }


def nhl_series() -> dict:
    Q, M = load("q1_per_million.json")["nhl_series"], load("q2_break_model.json")
    seasons, years = Q["seasons"], [year(s) for s in Q["seasons"]]
    cz, fit = M["nations"]["CZE"], M["nations"]["CZE"]["fitted"]
    n = cz["n"]
    (A / "nhl-series.svg").write_text(series_svg(years, n, fit))
    fall = next(s for s in cz["break"]["steps"] if s["direction"] == "down")
    fy, fp, df = fall["modal"]["season"], fall["modal"]["prob"], fall["delta_factor"]
    ticks = [1995, 2000, 2005, 2010, 2015, 2020, 2025]
    xax = {"kind": "linear", "domain": [1995, 2025], "ticks": ticks, "tickLabels": {t: f"{t}/{(t + 1) % 100:02d}" for t in ticks},
           "fmt": {"dp": 0, "nogroup": True, "pre": "season starting "}}
    peak = max((v, s) for v, s in zip(n, seasons) if v is not None)
    top = [
        {"type": "area", "name": "fitted level, 90 % interval", "c": HELD, "o": 0.14, "fmt": {"dp": 1},
         "pts": [[y, lo, hi] for y, lo, hi in zip(years, fit["lo"], fit["hi"])]},
        {"type": "line", "name": "fitted level (median)", "c": HELD, "w": 2, "fmt": {"dp": 1}, "pts": [[y, v] for y, v in zip(years, fit["median"])]},
        {"type": "rule", "axis": "x", "v": year(fy), "c": INK, "dash": "dot", "label": f"fall {fy}, p {fp:.2f}",
         "tip": f"most probable season of the fall: {fy}\nposterior probability {fp:.2f}\nlevel ×{df['median']:.2f} (90 % HDI {df['lo']:.2f}–{df['hi']:.2f})"},
        {"type": "dots", "c": INK, "r": 3.2, "pts": [
            {"x": y, "y": v, "tip": f"Czechia, {s}\n{v} NHL players with at least {t} games\nfitted level {f:.1f} ({lo:.1f}–{hi:.1f})",
             "label": f"{s}: {v}" if s in (peak[1], seasons[-1]) else None, "dy": -8}
            for y, s, v, t, f, lo, hi in zip(years, seasons, n, Q["threshold"], fit["median"], fit["lo"], fit["hi"]) if v is not None]},
    ]
    style = {"CZE": {"c": HELD, "w": 2.6}, "FIN": {"c": INK, "w": 1.5}, "SWE": {"c": GREY, "w": 1.5}}
    names = {"CZE": "Czechia", "FIN": "Finland", "SWE": "Sweden"}
    per = []
    for c in ("SWE", "FIN", "CZE"):
        pm = Q["nations"][c]["per_million"]
        # 2004/05 was not played: two segments, so the line does not bridge the lockout
        for part in ([(y, v) for y, v in zip(years, pm) if y < 2004 and v is not None], [(y, v) for y, v in zip(years, pm) if y > 2004 and v is not None]):
            per.append({"type": "line", "name": names[c], "fmt": {"dp": 2}, "pts": [list(p) for p in part], **style[c]})
    return {
        "alt": img_alt("nhl-series.svg"),
        "layout": "rows",
        "legend": [{"label": "Czech NHL players, games threshold", "c": INK, "shape": "o"},
                   {"label": "fitted level and its 90 % interval", "c": HELD},
                   {"label": "Finland", "c": INK}, {"label": "Sweden", "c": GREY}],
        "panels": [
            {"title": "Czech NHL players per season, 1995/96–2025/26", "h": 300, "padRight": 34, "x": {**xax}, "marks": top,
             "y": {"kind": "linear", "domain": [0, 70], "ticks": [0, 10, 20, 30, 40, 50, 60, 70], "label": "players"}},
            {"title": "per million inhabitants: Czechia, Finland, Sweden", "h": 190, "padRight": 34, "x": {**xax, "label": "season"}, "marks": per,
             "y": {"kind": "linear", "domain": [0, 8], "ticks": [0, 2, 4, 6, 8], "label": "NHL players per million"}},
        ],
        "table": {"cols": ["season", "games threshold", "Czechia", "fitted level", "90 % interval", "Czechia per million", "Finland per million", "Sweden per million"],
                  "rows": [[s, "–" if t is None else str(t), "not played" if v is None else str(v), f"{f:.1f}", f"{lo:.1f}–{hi:.1f}",
                            *["–" if Q["nations"][c]["per_million"][i] is None else f"{Q['nations'][c]['per_million'][i]:.2f}" for c in ("CZE", "FIN", "SWE")]]
                           for i, (s, t, v, f, lo, hi) in enumerate(zip(seasons, Q["threshold"], n, fit["median"], fit["lo"], fit["hi"]))]},
        "data": ["../assets/hockey/q1_per_million.json", "../assets/hockey/q2_break_model.json"],
    }


def roster() -> dict:
    E = load("q6_national_team.json")["home_by_event"]
    (A / "roster.svg").write_text(roster_svg(E))
    label = lambda e: f"{e['event']}{e['year'] % 100:02d}"
    full = lambda e: f"{EVENT[e['event']]} {e['year']}"
    rows = []
    for e in E:
        y0 = 0
        for k, name, c in CATS:
            v = e[k]
            if v:
                rows.append({"x": label(e), "y0": y0, "y1": y0 + v, "c": c, "o": 1,
                             "tip": f"{full(e)}\n{name}: {v} of {e['players']} players"})
            y0 += v
    return {
        "alt": img_alt("roster.svg"),
        "legend": [{"label": name, "c": c, "shape": "box", "o": 1} for _, name, c in CATS],
        "panels": [{"h": 300,
                    "x": {"kind": "cat", "domain": [label(e) for e in E], "label": "21 tournaments, 2010 (left) to 2026 (right)"},
                    "y": {"kind": "linear", "domain": [0, 30], "ticks": [0, 5, 10, 15, 20, 25, 30], "label": "roster spots"},
                    "marks": [{"type": "vbar", "rows": rows}]}],
        "table": {"cols": ["tournament", *[name for _, name, _ in CATS], "unknown", "players"],
                  "rows": [[full(e), *[str(e[k]) for k, _, _ in CATS], str(e["unknown"]), str(e["players"])] for e in E]},
        "data": ["../assets/hockey/q6_national_team.json"],
    }


def build() -> dict:
    return {"per-head": per_head(), "nhl-series": nhl_series(), "roster": roster()}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--refresh":
        refresh(Path(sys.argv[2]))
    out = build()
    (A / "charts.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {A / 'charts.json'}: {', '.join(out)}")
