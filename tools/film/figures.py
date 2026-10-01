"""Published data, chart specs and static figures for texts/film-fund.html.

Reads the parsed applications and frozen links through tools/film/analyse.py's loader and
tools/data/film/results.json, and writes to assets/film/:
- applications.csv: one row per production application in the study (2016-2021, not shorts) with
  points, distance to the cut-off, award, release link and Czech admissions;
- results.json: the registered estimates;
- charts.json: the specs read by assets/charts.js;
- 01-points.svg, 02-release.svg, 03-audience.svg: static fallbacks.

    uv run --no-project --with pandas --with pyarrow --with numpy --with scipy --with rdrobust \
        --with rddensity --with rapidfuzz --with matplotlib python tools/film/figures.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets" / "film"
DATA = ROOT / "tools" / "data" / "film"
HELD, INK, GREY, LIGHT = "#34507c", "#111111", "#666666", "#b5b5b0"


def local_fit(s: pd.DataFrame, y: str, side: int, h: float) -> list[list[float]]:
    """Triangular-kernel local linear fit on one side of the cut-off, for drawing only."""
    t = s[(np.sign(s.dist) == side) & (s.dist.abs() <= h) & s[y].notna()]
    w = np.clip(1 - t.dist.abs() / h, 0, None)
    b = np.polyfit(t.dist, t[y], 1, w=np.sqrt(w))
    xs = np.linspace(0, side * h, 20) if side > 0 else np.linspace(side * h, 0, 20)
    return [[round(float(x), 2), round(float(np.polyval(b, x)), 4)] for x in xs]


def main() -> None:
    A.mkdir(parents=True, exist_ok=True)
    R = json.loads((DATA / "results.json").read_text(encoding="utf-8"))
    d = load()
    prim = d[(d.year <= 2021) & d["first"]].copy()
    kind = prim.call_title.str.lower()
    prim["kind"] = np.select([kind.str.contains("dokument"), kind.str.contains("animov"), kind.str.contains("minorit")],
                             ["documentary", "animation", "minority co-production"], "fiction")
    out = prim[["call", "year", "kind", "app_id", "title", "applicant", "total", "dist", "funded", "award", "linked",
                "linked_sens", "adm"]].rename(columns={"year": "call_year", "total": "points", "dist": "points_from_cutoff",
                                                       "adm": "cz_admissions"})
    out.sort_values(["call", "points"], ascending=[True, False]).to_csv(A / "applications.csv", index=False)
    shutil.copy(DATA / "results.json", A / "results.json")

    charts = {}
    # fig. 1 · points from the cut-off, funded and not
    bins = list(range(-25, 26))
    cnt = prim.assign(b=np.floor(prim.dist).astype(int).clip(-25, 25)).groupby(["b", "funded"]).size().unstack(fill_value=0)
    cats = ["≤ −25" if b == -25 else "≥ 25" if b == 25 else str(b) for b in bins]
    rows_f = [{"x": cats[i], "y1": int(cnt.at[b, True]) if b in cnt.index else 0, "c": "held"} for i, b in enumerate(bins)]
    rows_u = [{"x": cats[i], "y1": int(cnt.at[b, False]) if b in cnt.index else 0, "c": "light"} for i, b in enumerate(bins)]
    ymax = int(cnt.max().max()) + 5
    charts["points"] = {
        "alt": f"Histogram of {len(prim)} production applications, 2016–2021, by points from their call's cut-off: every funded application lies above it and every unfunded one below.",
        "legend": [{"label": "funded", "c": "held", "shape": "box"}, {"label": "not funded", "c": "light", "shape": "box"}],
        "panels": [{"h": 260, "title": "applications per 1-point bin",
                    "x": {"kind": "cat", "domain": cats, "label": "points from the call's cut-off"},
                    "y": {"kind": "linear", "domain": [0, ymax], "fmt": {"dp": 0}},
                    "marks": [{"type": "vbar", "rows": rows_u}, {"type": "vbar", "rows": rows_f}]}],
        "table": {"cols": ["points from cut-off", "funded", "not funded"],
                  "rows": [[b, r1["y1"], r0["y1"]] for b, r1, r0 in zip(cats, rows_f, rows_u)]},
        "data": ["../assets/film/applications.csv"],
    }
    # fig. 2 · share reaching Czech cinemas around the cut-off
    h = R["Q1"]["O1_release"]["h"]
    win = prim[prim.dist.abs() < 12]
    g = win.assign(b=np.floor(win.dist) + 0.5).groupby("b").agg(share=("linked", "mean"), n=("linked", "size")).reset_index()
    pts = [{"x": float(r.b), "y": round(float(r.share) * 100, 1), "c": "held" if r.b > 0 else "grey", "r": 2.5 + min(r.n, 30) / 6,
            "tip": f"{r.b - 0.5:+.0f} to {r.b + 0.5:+.0f} points: {r.share * 100:.0f} % of {int(r.n)} reached cinemas"} for r in g.itertuples()]
    o1 = R["Q1"]["O1_release"]
    charts["release"] = {
        "alt": f"Share of applications that reached Czech cinemas by 30 September 2026, in 1-point bins around the cut-off, with local linear fits within {h:.1f} points on each side; the estimated jump at the cut-off is {o1['coef'] * 100:+.0f} percentage points (95 % CI {o1['lo'] * 100:+.0f} to {o1['hi'] * 100:+.0f}).",
        "legend": [{"label": "funded side", "c": "held", "shape": "dot"}, {"label": "unfunded side", "c": "grey", "shape": "dot"},
                   {"label": f"local linear fit, {h:.1f} points each side", "c": "ink"}],
        "panels": [{"h": 280, "title": "share released in Czech cinemas by 30 Sep 2026",
                    "x": {"kind": "linear", "domain": [-12, 12], "label": "points from the call's cut-off", "fmt": {"dp": 0, "sign": True}},
                    "y": {"kind": "linear", "domain": [0, 100], "fmt": {"dp": 0, "unit": " %"}},
                    "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey", "dash": "dash", "label": "cut-off"},
                              {"type": "line", "pts": [[x, y * 100] for x, y in local_fit(prim, "linked", -1, h)], "c": "ink"},
                              {"type": "line", "pts": [[x, y * 100] for x, y in local_fit(prim, "linked", 1, h)], "c": "ink"},
                              {"type": "dots", "pts": pts}]}],
        "table": {"cols": ["bin centre", "share released", "applications"],
                  "rows": [[f"{r.b:+.1f}", f"{r.share * 100:.0f} %", int(r.n)] for r in g.itertuples()]},
        "data": ["../assets/film/applications.csv"],
    }
    # fig. 3 · points and admissions among released projects (within call)
    rel = d[(d.year <= 2021) & d.linked & (d.adm > 0)].copy()
    rel = rel[rel.groupby("call").call.transform("size") >= 2]
    rel["dx"] = rel.total - rel.groupby("call").total.transform("mean")
    q2 = R["Q2"]
    charts["audience"] = {
        "alt": f"Scatter of {q2['n']} released projects: points relative to their call's mean against Czech admissions on a log scale; Spearman rho within call {q2['rho']:+.2f} (95 % CI {q2['lo']:+.2f} to {q2['hi']:+.2f}).",
        "legend": [{"label": "funded", "c": "held", "shape": "dot"}, {"label": "not funded", "c": "grey", "shape": "dot"}],
        "panels": [{"h": 300, "title": "Czech admissions (log scale)",
                    "x": {"kind": "linear", "domain": [-30, 25], "label": "points relative to the call's mean", "fmt": {"dp": 0, "sign": True}},
                    "y": {"kind": "log", "domain": [10, 2_000_000], "fmt": {"dp": 0}},
                    "marks": [{"type": "dots", "pts": [{"x": round(float(r.dx), 1), "y": max(10, float(r.adm)), "r": 3.2, "o": 0.75,
                                                        "c": "held" if r.funded else "grey",
                                                        "tip": f"{r.title}: {r.dx:+.1f} points, {int(r.adm):,} admissions".replace(",", " ")}
                                                       for r in rel.itertuples()]}]}],
        "table": {"cols": ["title", "points vs call mean", "Czech admissions", "funded"],
                  "rows": [[r.title, round(float(r.dx), 1), int(r.adm), "yes" if r.funded else "no"] for r in rel.sort_values("adm", ascending=False).itertuples()]},
        "data": ["../assets/film/applications.csv"],
    }
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    f, ax = plt.subplots(figsize=(7.2, 3.2))
    xs = np.array(bins)
    ax.bar(xs + 0.5, [r["y1"] for r in rows_u], width=0.85, color=LIGHT, label="not funded")
    ax.bar(xs + 0.5, [r["y1"] for r in rows_f], width=0.85, color=HELD, label="funded")
    ax.axvline(0, color=GREY, ls="--", lw=1); ax.set_xlabel("points from the call's cut-off"); ax.legend(frameon=False)
    f.tight_layout(); f.savefig(A / "01-points.svg"); plt.close(f)
    f, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.scatter(g.b, g.share, s=10 + g.n * 3, c=[HELD if b > 0 else GREY for b in g.b])
    for side in (-1, 1):
        p = np.array(local_fit(prim, "linked", side, h)); ax.plot(p[:, 0], p[:, 1], color=INK, lw=1.6)
    ax.axvline(0, color=GREY, ls="--", lw=1); ax.set_ylim(0, 1); ax.set_xlabel("points from the call's cut-off")
    ax.set_ylabel("share released in Czech cinemas"); f.tight_layout(); f.savefig(A / "02-release.svg"); plt.close(f)
    f, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.scatter(rel.dx, rel.adm, s=12, alpha=0.75, c=[HELD if x else GREY for x in rel.funded]); ax.set_yscale("log")
    ax.set_xlabel("points relative to the call's mean"); ax.set_ylabel("Czech admissions")
    f.tight_layout(); f.savefig(A / "03-audience.svg"); plt.close(f)
    print(f"wrote {A}: {len(out)} applications, charts {list(charts)}")


if __name__ == "__main__":
    main()
