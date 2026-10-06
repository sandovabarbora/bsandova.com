"""Story layer for the remaining charts: the two atlases, the sonification note, Brand Reflection and the surf base rate.

Run after their generators (tools/charts/football.py, hockey.py, delayed.py, brand_reflection.py, surf.py), which write
the numbers. The atlases keep their own palette (Czechia in the atlas's held colour, peers in ink and grey), which is a
role colour, not an entity colour, so this script only adds labels at line ends and notes at key points; every value in
a note is read from the chart's own data. It never changes a value. Idempotent.

    python3 tools/charts/story_rest.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"


def load(name: str) -> dict:
    return json.loads((A / name / "charts.json").read_text())


def save(name: str, charts: dict, indent: int | None) -> None:
    """Write in the generator's own style (compact or indented) and keep its trailing newline, so diffs stay small."""
    f = A / name / "charts.json"
    nl = "\n" if f.read_text().endswith("\n") else ""
    f.write_text(json.dumps(charts, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")) + nl)


def clear(panel: dict) -> None:
    panel["marks"][:] = [m for m in panel["marks"] if m["type"] != "callout"]
    for m in panel["marks"]:
        m.pop("end", None)


def callout(panel: dict, **co) -> None:
    panel["marks"].append({"type": "callout", **co})


def mark(panel: dict, kind: str, name: str | None = None, last: bool = False) -> dict:
    ms = [m for m in panel["marks"] if m["type"] == kind and (name is None or m.get("name") == name)]
    return ms[-1] if last else ms[0]


def ends(panel: dict, names: list[str], pad: int) -> None:
    """Label each named line at its last point; a line drawn in two segments (a gap season) is labelled once."""
    for n in names:
        mark(panel, "line", n, last=True)["end"] = True
    panel["padRight"] = pad


def football() -> None:
    c = load("football")
    p = c["per-head"]["panels"][0]
    clear(p)
    rows = mark(p, "hbar")["rows"]
    cz = next(r for r in rows if r["y"] == "Czechia")
    rank = [r["y"] for r in sorted(rows, key=lambda r: -r["x1"])].index("Czechia") + 1
    callout(p, x=cz["x1"], y="Czechia", dx=44, dy=4, anchor="start", s=f"{rank}th of {len(rows)}",
            narrow={"dx": 36})
    top, low = c["big5"]["panels"]
    clear(top)
    clear(low)
    # the generator already labels 2007/08, 2015/16 and 2025/26 on the Czech line; only names at the line ends here
    ends(top, ["Czechia", "Denmark", "Croatia"], 76)
    ends(low, ["Czechia", "Denmark", "Croatia"], 76)
    save("football", c, None)


def hockey() -> None:
    c = load("hockey")
    p = c["per-head"]["panels"][0]
    clear(p)
    rows = mark(p, "hbar")["rows"]
    cz = next(r for r in rows if r["y"] == "Czechia")
    rank = [r["y"] for r in sorted(rows, key=lambda r: -r["x1"])].index("Czechia") + 1
    med = mark(p, "rule")["v"]
    callout(p, x=cz["x1"], y="Czechia", dx=44, dy=4, anchor="start",
            s=f"{rank}th of {len(rows)}, above the peer median {med:.2f}", narrow={"dx": 36, "s": f"{rank}th of {len(rows)}"})
    top, low = c["nhl-series"]["panels"]
    clear(top)
    clear(low)
    dots = mark(top, "dots")["pts"]
    peak = max(dots, key=lambda d: d["y"])
    callout(top, x=peak["x"], y=peak["y"], dx=12, dy=-6, anchor="start",
            s=f"{peak['y']} in {peak['x']}/{(peak['x'] + 1) % 100:02d}")
    # no end labels in the lower panel: at 390 px its season ticks need the width, and the legend names the three
    low["padRight"] = 34
    r = c["roster"]["panels"][0]
    clear(r)
    khl = [b for b in mark(r, "vbar")["rows"] if "KHL" in b["tip"]]
    last = khl[-1] if khl else None
    if last:
        callout(r, x=last["x"], y=last["y1"], dx=0, dy=-26, anchor="middle", s="last KHL player: WC 2022",
                narrow={"dy": -22, "s": "last KHL: 2022"})
    save("hockey", c, None)


def delayed() -> None:
    c = load("delayed")
    for p in c["five-days"]["panels"]:
        clear(p)
    p = c["five-days"]["panels"][4]
    line = mark(p, "line")["pts"]
    peak = max(line, key=lambda q: q[1])
    # the peak only: a mean of the plotted windows (302 s) is not the event-weighted 304 s the text gives
    hh, mm = int(peak[0]), round(peak[0] % 1 * 60)
    callout(p, x=peak[0], y=peak[1], dx=-14, dy=8, anchor="end", s=f"one afternoon: peak {peak[1]:.0f} s at {hh}:{mm:02d}",
            narrow={"s": f"peak {peak[1]:.0f} s at {hh}:{mm:02d}"})
    save("delayed", c, None)


def brand() -> None:
    c = load("brand")
    p = c["hue-distance"]["panels"][0]
    clear(p)
    bars = mark(p, "vbar")["rows"]
    albert = [b for b in bars if b["tip"].startswith("Albert")]
    far = min(albert, key=lambda b: b["y1"])
    callout(p, x=far["x"], y=far["y1"], dx=-16, dy=-14, anchor="end",
            s=f"Albert's {len(albert)} spots: {min(b['y1'] for b in albert):.0f}–{max(b['y1'] for b in albert):.0f}°",
            narrow={"s": f"Albert: {min(b['y1'] for b in albert):.0f}–{max(b['y1'] for b in albert):.0f}°"})
    p = c["voice-music"]["panels"][0]
    clear(p)
    led = [b for b in mark(p, "vbar")["rows"] if b["tip"].endswith("music-led") and b["y0"] > 0]
    first = led[0]
    callout(p, x=first["x"], y=first["y0"] + (first["y1"] - first["y0"]) / 2, dx=24, dy=-4, anchor="start",
            s=f"only {len(led)} of 47 music-led", narrow={"dx": 18})
    clear(c["two-commitments"]["panels"][0])  # the generator already names Pilsner Urquell's point
    save("brand", c, None)


def surf() -> None:
    c = load("surf")
    p = c["ericeira-92-days"]["panels"][0]
    clear(p)
    ok = mark(p, "dots", None, last=True)["pts"]
    n = len(mark(p, "dots")["pts"])
    best = max(ok, key=lambda d: d["y"])
    callout(p, x=best["x"], y=best["y"], dx=-16, dy=-20, anchor="end", s=f"{len(ok)} of {n} days clear the rule")
    save("surf", c, 1)


if __name__ == "__main__":
    football()
    hockey()
    delayed()
    brand()
    surf()
