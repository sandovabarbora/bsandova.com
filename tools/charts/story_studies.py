"""Story layer for the stand-alone studies' charts: notes at key points, read from each chart's own data.

Covers Eurovision, the clock change (DST), the film fund, the lottery and the silent-wrong-number detector. Run after
their generators (tools/eurovision/article.py, tools/dst/article.py, tools/film/figures.py, tools/charts/lottery.py,
tools/charts/silent_detector.py), which write the numbers; these charts keep their role colours (the article's accent for
the result, grey for context), so this script only adds callouts and never changes a value. Idempotent.

    python3 tools/charts/story_studies.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"
MINUS = str.maketrans({"-": "−"})


def load(name: str) -> dict:
    return json.loads((A / name / "charts.json").read_text())


def save(name: str, charts: dict, indent: int | None) -> None:
    s = json.dumps(charts, ensure_ascii=False, indent=indent) + ("\n" if indent else "")
    (A / name / "charts.json").write_text(s)


def clear(panel: dict) -> None:
    panel["marks"][:] = [m for m in panel["marks"] if m["type"] != "callout" and not m.get("story")]


def callout(panel: dict, **co) -> None:
    panel["marks"].append({"type": "callout", **co})


def note(panel: dict, x: float, y: str, s: str, narrow: dict | None = None, left: bool = False) -> None:
    """A label beside a row's interval, without a leader: a callout's ring would read as a data point there. left puts
    it before the interval's low end, where the right of the plot has no room."""
    m = {"type": "text", "x": x, "y": y, "dx": -8 if left else 8, "anchor": "end" if left else "start", "c": "ink", "s": s,
         "story": True}
    if narrow:
        m["narrow"] = narrow
    panel["marks"].append(m)


def rows(panel: dict, kind: str) -> list[dict]:
    return next(m for m in panel["marks"] if m["type"] == kind)["rows"]


def eurovision() -> None:
    charts = load("eurovision")
    p = charts["gap"]["panels"][0]
    clear(p)
    tiny = rows(p, "vbar")[0]
    callout(p, x=tiny["x"], y=tiny["y1"], dx=22, dy=4, anchor="start", s="tiny diaspora: the jury gives more",
            narrow={"s": "jury gives more", "dx": 12, "dy": 4})

    p = charts["checks"]["panels"][0]
    clear(p)
    reg = rows(p, "range")[0]
    note(p, reg["lo"], reg["y"], f"×{reg['mid']:.2f}, supported", narrow={"s": "supported"}, left=True)

    p = charts["eu"]["panels"][0]
    clear(p)
    pre = next(r for r in rows(p, "vrange") if r["x"] == -2)
    callout(p, x=-2, y=pre["mid"], dx=-14, dy=-6, anchor="end",
            s=f"not flat before joining: {pre['mid']:+.2f} two contests before".translate(MINUS),
            narrow={"s": f"before joining:\n{pre['mid']:+.2f} at −2".translate(MINUS), "dy": -14})
    save("eurovision", charts, None)


def dst() -> None:
    charts = load("dst")
    p = charts["hours"]["panels"][0]
    clear(p)
    before, after = [m for m in p["marks"] if m["type"] == "line"]
    x, y = after["pts"][17]
    callout(p, x=x, y=y, dx=-30, dy=34, anchor="end",
            s=f"17:00 after the change: {y:.2f} a day, {before['pts'][17][1]:.2f} before",
            narrow={"s": f"17:00: {y:.2f} a day\n({before['pts'][17][1]:.2f} before)"})

    p = charts["checks"]["panels"][0]
    clear(p)
    rs = rows(p, "range")
    reg = rs[0]
    orig = next(r for r in rs if r["y"].startswith("original specification"))
    note(p, reg["lo"], reg["y"], f"×{reg['mid']:.2f}, supported", narrow={"s": "supported"}, left=True)
    note(p, orig["hi"], orig["y"], "inconclusive")

    p = charts["event"]["panels"][0]
    clear(p)
    day = next(r for r in rows(p, "vrange") if r["lo"] > 1)
    callout(p, x=day["x"], y=day["mid"], dx=14, dy=-10, anchor="start",
            s=f"day {day['x']}: ×{day['mid']:.2f}, the only interval above 1",
            narrow={"s": f"day {day['x']}: ×{day['mid']:.2f},\nonly interval above 1", "dx": -14, "anchor": "end"})
    save("dst", charts, None)


def film() -> None:
    charts = load("film")
    p = charts["release"]["panels"][0]
    clear(p)
    lines = [m for m in p["marks"] if m["type"] == "line"]
    above = next(m for m in lines if m["pts"][0][0] == 0)
    below = next(m for m in lines if m["pts"][-1][0] == 0)
    jump = above["pts"][0][1] - below["pts"][-1][1]
    callout(p, x=0, y=above["pts"][0][1], dx=16, dy=-14, anchor="start",
            s=f"difference at the cut-off: {jump:+.0f} points, underpowered",
            narrow={"s": f"difference {jump:+.0f} points,\nunderpowered", "dy": -22})
    save("film", charts, None)


def lottery() -> None:
    charts = load("lottery")
    p = charts["counts"]["panels"][0]
    clear(p)
    out = [r for r in rows(p, "vbar") if r["c"] == "ink"]
    low = min(out, key=lambda r: r["y1"])
    callout(p, x=low["x"], y=low["y1"], dx=16, dy=16, anchor="start",
            s=f"{len(out)} numbers outside the band; about 2.5 would be by chance",
            narrow={"s": f"{len(out)} outside the band;\n~2.5 by chance"})

    p = charts["ppc"]["panels"][0]
    clear(p)
    top = next(m for m in p["marks"] if m["type"] == "dots")["pts"][-1]
    pred = rows(p, "vrange")[-1]
    callout(p, x=top["x"], y=top["y"], dx=-14, dy=-30, anchor="end",
            s=f"top range: {top['label']} draws, {pred['mid']:.1f} predicted",
            narrow={"s": f"{top['label']},\n{pred['mid']:.1f} predicted", "dy": -36})

    p = charts["ev"]["panels"][0]
    clear(p)
    x, y = next(m for m in p["marks"] if m["type"] == "line" and m.get("name") == "expected payout")["pts"][-1]
    callout(p, x=x, y=y, dx=-14, dy=-30, anchor="end", s=f"at the €{x:.0f} M cap: €{y:.2f}, below the €2 price",
            narrow={"s": f"cap: €{y:.2f},\nbelow €2", "dy": -36})

    p = charts["importance"]["panels"][0]
    clear(p)
    paired = next(r for r in rows(p, "range") if r["y"].startswith("naive, paired"))
    callout(p, x=paired["mid"], y=paired["y"], dx=-16, dy=-14, anchor="end",
            s="0 ± 0: no jackpot sampled", narrow={"s": "0 ± 0: no jackpot\nin the sample", "dy": 4})
    save("lottery", charts, 1)


def detector() -> None:
    charts = load("detector")
    # no note: the bars carry their values, there is no room beside the best one, and the headline names it
    clear(charts["auc"]["panels"][0])
    save("detector", charts, 1)


def main() -> None:
    eurovision()
    dst()
    film()
    lottery()
    detector()
    print("story layer: eurovision, dst, film, lottery, detector")


if __name__ == "__main__":
    main()
