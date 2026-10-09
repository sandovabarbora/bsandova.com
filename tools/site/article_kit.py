"""Shared pieces of the research-article generators: number formatting, the static chart style and range charts."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "docs" / "research"
NB = " "
HELD, INK, GREY, LIGHT = "#34507c", "#111111", "#666666", "#b5b5b0"
TOKEN = re.compile(r"\{\{(\w+)\}\}")


def use_article_style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY,
                         "svg.fonttype": "none"})
    return plt


def n(v: float, dp: int = 0, *, sign: bool = False, unit: str = "") -> str:
    """Thin-space thousands and a true minus, shown only when the value does not round to zero."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    neg = v < 0 and round(abs(v), dp) != 0
    return ("−" if neg else ("+" if sign and v > 0 else "")) + s + unit


def ci(lo: float, hi: float, dp: int = 1) -> str:
    return f"{n(lo, dp)} to {n(hi, dp)}"


def results_reader(prefix: str):
    def read(name: str) -> dict:
        return json.loads((RESEARCH / f"{prefix}-{name}.json").read_text())
    return read


def render(template: str, values: dict) -> str:
    missing = sorted(set(TOKEN.findall(template)) - set(values))
    if missing:
        raise KeyError(f"no value for {', '.join(missing)}")
    return TOKEN.sub(lambda m: str(values[m.group(1)]), template)


def photo_section(slug: str, image: str | None = None) -> str:
    """The page's film still and its credit; `image` names another page's photograph when the page has none of its own."""
    image = image or slug
    photo = next(p for p in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if p["slug"] == image)
    return (f'<section class="film film-page"><div class="shot" style="view-transition-name:ph-{slug};'
            f'--bg:url(../assets/photo/{image}.jpg);--bg-s:url(../assets/photo/{image}-1200.jpg)"></div>'
            f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · '
            f'{photo["licence"]}, toned</p></section>')


def part_item(slug: str, k: int, title: str, kicker: str, text: str, image: str | None = None, *,
              label: str | None = None) -> str:
    """One part on a series hub; `label` is the screen-reader name when the visible title is longer."""
    image = image or slug
    return (f'  <li>\n    <a class="still" href="{slug}" aria-label="Part {k}, {label or title}"><span class="shot" '
            f'style="view-transition-name:ph-{slug};--bg:url(../assets/photo/{image}.jpg);'
            f'--bg-s:url(../assets/photo/{image}-1200.jpg)"></span></a>\n'
            f'    <div>\n      <p class="n">{kicker}</p>\n      <h2><a href="{slug}">{title}</a></h2>\n'
            f'      <p>{text}</p>\n    </div>\n  </li>')


def range_rows(items: list[tuple[str, dict, str]], held: str = "held") -> list[dict]:
    return [{"y": lab, "lo": e["ci95"][0], "hi": e["ci95"][1], "mid": e["est_s"], "c": held if c == "held" else c,
             "tip": f"{lab}: {n(e['est_s'], 1, sign=True)} s ({ci(*e['ci95'])})"} for lab, e, c in items]


def range_chart(rows: list[dict], alt: str, label: str, domain: list[float], ticks: list[float]) -> dict:
    return {"alt": alt,
            "panels": [{"h": 34 * len(rows) + 20,
                        "x": {"kind": "linear", "domain": domain, "ticks": ticks, "fmt": {"dp": 0, "sign": True},
                              "label": label},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"}, {"type": "range", "rows": rows}]}],
            "table": {"cols": ["estimate", "seconds", "95 % interval"],
                      "rows": [[r["y"], round(r["mid"], 2), f"{r['lo']:.2f} to {r['hi']:.2f}"] for r in rows]},
            "data": ["results.json"]}


def static_range(rows: list[dict], path: Path, label: str, xlim: tuple[float, float], held: str = HELD) -> None:
    import matplotlib.pyplot as plt

    f, ax = plt.subplots(figsize=(7.2, 0.42 * len(rows) + 0.8))
    for i, r in enumerate(reversed(rows)):
        c = {"ink": INK, "grey": GREY}.get(r["c"], held)  # the static fallback draws every accent in one colour
        ax.plot([r["lo"], r["hi"]], [i, i], color=c, lw=2.5, solid_capstyle="round")
        ax.plot(r["mid"], i, "o", color=c, ms=6, mec="white")
    ax.axvline(0, color=GREY, lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["y"] for r in reversed(rows)])
    ax.set_xlim(*xlim)
    ax.set_xlabel(label)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)
