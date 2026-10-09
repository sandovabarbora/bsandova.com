"""Range and line charts of the bunching and transfers articles (parts 2 and 3 of Running late)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
from article_kit import GREY, INK, use_article_style  # noqa: E402

plt = use_article_style()
HELD = "#c0503f"


def line_chart(series: list[dict], alt: str, xlab: str, ylab: str, xdom: list, ydom: list, table: dict,
               data: list, yfmt: dict) -> dict:
    return {"alt": alt, "panels": [{"h": 240, "x": {"kind": "linear", "domain": xdom, "fmt": {"dp": 0}, "label": xlab},
                                    "y": {"kind": "linear", "domain": ydom, "fmt": yfmt, "label": ylab},
                                    "marks": [{"type": "line", "dots": True, **s} for s in series]}],
            "legend": [{"label": s["name"], "c": s["c"]} for s in series], "table": table, "data": data}


def static_lines(series: list[dict], path: Path, xlab: str, ylab: str) -> None:
    f, ax = plt.subplots(figsize=(7.2, 2.8))
    for s in series:
        ax.plot([p[0] for p in s["pts"]], [p[1] for p in s["pts"]], color=s["c"], lw=1.6, marker="o", ms=3,
                ls="--" if s.get("dash") else "-")
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def range_rows(rows: list[tuple]) -> list[dict]:
    out = []
    for lab, est, ci, col in rows:
        lo, hi = (ci if ci else (est, est))
        tip = f"{lab}: {est:+.4f}" + (f" ({lo:+.4f} to {hi:+.4f})" if ci else "")
        out.append({"y": lab, "lo": lo, "hi": hi, "mid": est, "c": col, "tip": tip})
    return out


def range_chart(rows: list[dict], alt: str, label: str, domain: list, band: float | None, line: float,
                fmt: dict, data: list) -> dict:
    marks = []
    if band:
        marks.append({"type": "span", "v0": -band, "v1": band, "c": "grey", "o": 0.08, "label": "the registered ±0.01"})
    marks += [{"type": "rule", "axis": "x", "v": line, "c": "grey"}, {"type": "range", "rows": rows}]
    return {"alt": alt, "panels": [{"h": 26 * len(rows) + 40, "x": {"kind": "linear", "domain": domain, "fmt": fmt,
                                                                   "label": label},
                                    "y": {"kind": "cat", "domain": [r["y"] for r in rows]}, "marks": marks}],
            "table": {"cols": ["version", "estimate", "95 % interval"],
                      "rows": [[r["y"], r["mid"], "" if r["lo"] == r["hi"] else f"{r['lo']} to {r['hi']}"] for r in rows]},
            "data": data}


def static_range(rows: list[dict], path: Path, label: str, xlim: tuple, line: float) -> None:
    f, ax = plt.subplots(figsize=(7.2, 0.3 * len(rows) + 0.9))
    for i, r in enumerate(reversed(rows)):
        ax.plot([r["lo"], r["hi"]], [i, i], color=INK, lw=1.2)
        ax.plot(r["mid"], i, "o", color=HELD if r["c"] == "held" else INK, ms=4)
    ax.axvline(line, color=GREY, lw=0.8)
    ax.set_yticks(range(len(rows)), [r["y"] for r in reversed(rows)], fontsize=7)
    ax.set_xlim(*xlim)
    ax.set_xlabel(label)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)
