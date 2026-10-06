"""Story layer for the Pop, measured charts and the concert-effect study: notes at key points and labels at line ends.

Run after the generators (tools/pop/figures.py, tools/eras/figures.py, tools/pop/together_article.py,
tools/concerts/article.py), which write the numbers and take each artist's colour from assets/palette.json. This script
only adds callouts, reading every value it prints from the chart's own data, and never changes a value. Idempotent.

    python3 tools/charts/story_pop.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"
ARTISTS = ("harry-styles", "taylor-swift", "bts", "bad-bunny", "billie-eilish")
ORD = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else ORD.get(n % 10, 'th')}"


def callout(panel: dict, co: dict) -> None:
    marks = panel["marks"]
    marks[:] = [m for m in marks if not (m["type"] == "callout" and m["s"] == co["s"])]
    marks.append({"type": "callout", **co})


def note(panel: dict, x: float, y: str, s: str, left: bool = False) -> None:
    """A label beside a row's interval, without a leader: a callout's ring would read as a data point there."""
    panel["marks"].append({"type": "text", "x": x / 1.12 if left else x * 1.12, "y": y, "anchor": "end" if left else "start",
                           "c": "ink", "s": s, "story": True})


def clear(panel: dict) -> None:
    panel["marks"][:] = [m for m in panel["marks"] if m["type"] != "callout" and not m.get("story")]


def artist(slug: str) -> None:
    f = A / "pop" / slug / "charts.json"
    charts = json.loads(f.read_text())

    # countries: Czechia's ratio and rank, beside its own interval
    p = charts["countries"]["panels"][0]
    clear(p)
    rows = next(m for m in p["marks"] if m["type"] == "range")["rows"]
    k, cz = next((i, r) for i, r in enumerate(rows) if r["y"].startswith("Czechia"))
    note(p, cz["hi"], cz["y"], f"{cz['mid']:.1f}×, {ordinal(k + 1)} of {len(rows)}")

    # catalogue: the biggest song's share, and the top three together
    p = charts["catalogue"]["panels"][0]
    clear(p)
    segs = p["marks"][0]["rows"]
    top = segs[0]["tip"].rsplit(":", 1)[0]
    # both notes sit above the bar (below it is the axis); when the two points are close they share one note
    a, t3 = segs[0]["x1"] / 2, segs[2]["x1"]
    if t3 - a > 30:
        callout(p, {"x": a, "y": segs[0]["y"], "dx": 0, "dy": -26, "anchor": "start", "s": f"{top}: {segs[0]['x1']:.0f} %",
                    "narrow": {"s": f"{top}:\n{segs[0]['x1']:.0f} %", "dy": -34}})
        callout(p, {"x": t3, "y": segs[2]["y"], "dx": 0, "dy": -26, "anchor": "start", "s": f"top three together: {t3:.0f} %",
                    "narrow": {"s": f"top three:\n{t3:.0f} %", "dy": -34}})
    else:
        callout(p, {"x": a, "y": segs[0]["y"], "dx": 0, "dy": -26, "anchor": "start",
                    "s": f"{top}: {segs[0]['x1']:.0f} %; top three together: {t3:.0f} %",
                    "narrow": {"s": f"{top}: {segs[0]['x1']:.0f} %\ntop three: {t3:.0f} %", "dy": -34}})

    # tour: the longest run if it is the only one, and the lowest share if any entry fell short
    if "tour" in charts:
        p = charts["tour"]["panels"][0]
        clear(p)
        pts = p["marks"][0]["pts"]
        venue = lambda q: re.sub(r"\s+", " ", q["tip"].split(" (")[0]).split(",")[0].replace("The O 2", "The O2")
        city = lambda q: re.sub(r"\s+", " ", q["tip"].split(" (")[0]).split(", ")[-1].strip()
        longest = max(q["x"] for q in pts)
        runs = [q for q in pts if q["x"] == longest]
        if len(runs) == 1:
            q = runs[0]
            callout(p, {"x": q["x"], "y": q["y"], "dx": -10, "dy": 26, "anchor": "end",
                        "s": f"{venue(q)}, {q['x']} nights, {q['y']:.0f} % sold",
                        "narrow": {"s": f"{q['x']} nights,\n{venue(q)}"}})
        low = min(pts, key=lambda q: q["y"])
        if low["y"] < 99.5:
            callout(p, {"x": low["x"], "y": low["y"], "dx": 14, "dy": 4, "anchor": "start",
                        "s": f"lowest: {city(low)}, {low['y']:.0f} %"})

    # Eras Tour prices: the registered month, accommodation in the show month
    if "eras" in charts:
        p = charts["eras"]["panels"][0]
        clear(p)
        r = next(r for r in next(m for m in p["marks"] if m["type"] == "vrange")["rows"] if r["x"] < 0 and r["x"] > -0.5)
        callout(p, {"x": r["x"], "y": r["mid"], "dx": 30, "dy": 112, "anchor": "start",
                    "s": f"hotels, show month: {r['mid']:+.2f}, band {r['lo']:.1f} to {r['hi']:+.1f}".replace("-", "−"),
                    "narrow": {"s": f"hotels, show month\n{r['mid']:+.2f} ({r['lo']:.1f} to {r['hi']:+.1f})".replace("-", "−"), "dx": 18, "dy": 96}})

    f.write_text(json.dumps(charts, ensure_ascii=False))


def together() -> None:
    f = A / "pop" / "together" / "charts.json"
    charts = json.loads(f.read_text())
    p = charts["language"]["panels"][0]
    clear(p)
    rows = next(m for m in p["marks"] if m["type"] == "range")["rows"]
    es = next(r for r in rows if r["y"].startswith("Spanish"))
    note(p, es["lo"], es["y"], f"one song: {es['mid']:.1f}×", left=True)
    clear(charts["elasticity"]["panels"][0])  # the headline names Taylor Swift's interval; no room beside it
    f.write_text(json.dumps(charts, ensure_ascii=False))


def concerts() -> None:
    f = A / "concerts" / "charts.json"
    charts = json.loads(f.read_text())
    p = charts["raw"]["panels"][0]
    clear(p)
    pts = next(m for m in p["marks"] if m["type"] == "line")["pts"]
    y0 = next(y for x, y in pts if x == 0)
    callout(p, {"x": 0, "y": y0, "dx": 14, "dy": -6, "anchor": "start", "s": f"show week: {y0:.3f} %"})
    p = charts["event"]["panels"][0]
    clear(p)
    r = next(r for r in next(m for m in p["marks"] if m["type"] == "vrange")["rows"] if r["x"] == 0)
    callout(p, {"x": 0, "y": r["mid"], "dx": 70, "dy": -50, "anchor": "start", "s": f"show week: +{r['mid']:.3f} points",
                "narrow": {"s": f"show week:\n+{r['mid']:.3f} points", "dx": -16, "dy": -54, "anchor": "end"}})
    f.write_text(json.dumps(charts, ensure_ascii=False))


def main() -> None:
    for slug in ARTISTS:
        artist(slug)
    together()
    concerts()
    print("story layer: 5 parts, together, concerts")


if __name__ == "__main__":
    main()
