"""Data for the animated comparison of part 4: for Prague, Zurich, Basel and Bern, the concentration curve, the curve
chance alone would give, and where the top tenth of segments lies on the map. A description drawn from the registered
study's passes after the results, not an estimate; S and S₀ are read from swiss-trams-results.json.

The chance curve is the mean, point by point, of the sorted curves from CURVE_PERMS permutations of segment labels
among passes within each date × hour, the permutation of §4 behind S₀.

Reads tools/data/late/{segments,swiss_segments,swiss_passes}.parquet and part 1's passes (rebuilt as in
swiss_estimate.py); writes assets/late-swiss/cities.json for assets/late-swiss/cities.js.

    nice -n 20 uv run --no-project --with numpy --with pandas --with pyarrow --with scipy --with matplotlib \
        --with duckdb python tools/late/swiss_animation.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
from swiss_article import curve, totals  # noqa: E402
from swiss_estimate import SEED_CH, TOP, codes, prague_passes, swiss_xy  # noqa: E402
from tram_geo import offset_line, tram_stops  # noqa: E402

CURVE_PERMS, POINTS = 19, 101
OUT = ROOT / "assets/late-swiss/cities.json"
LAT0 = {"Prague": 50.08, "Zurich": 47.38, "Basel": 47.56, "Bern": 46.95}


def chance_curve(p: pd.DataFrame, rng) -> list[list[float]]:
    seg = codes(p.seg_from, p.seg_to)
    group = codes(p.date.astype(str), p.hour)
    order = np.argsort(group, kind="stable")
    seg, group, g = seg[order], group[order], p.g.to_numpy(float)[order]
    xs = np.linspace(0, 1, POINTS)
    ys = np.zeros(POINTS)
    for _ in range(CURVE_PERMS):
        tot = np.sort(np.bincount(seg[np.lexsort((rng.random(len(group)), group))], weights=g, minlength=seg.max() + 1))[::-1]
        cum = np.concatenate([[0], np.cumsum(tot)]) / tot[tot > 0].sum()
        ys += np.minimum(1.0, cum[np.round(xs * len(tot)).astype(int)])
    return [[round(float(x), 3), round(float(y / CURVE_PERMS), 4)] for x, y in zip(xs, ys)]


def lines(t: pd.DataFrame, xy: dict) -> tuple[list, list]:
    """The top tenth of segments by delay made, and the rest, as stop-to-stop lines."""
    k = max(1, math.ceil(TOP * len(t)))
    t = t.sort_values("gsum", ascending=False).reset_index(drop=True)
    top, rest = [], []
    for i, r in enumerate(t.itertuples()):
        if r.seg_from in xy and r.seg_to in xy and r.seg_from != r.seg_to:
            (top if i < k else rest).append(offset_line(xy[r.seg_from], xy[r.seg_to]))
    return top, rest


def main() -> None:
    res = json.loads((ROOT / "docs/research/swiss-trams-results.json").read_text())
    tot = totals()
    rng = np.random.default_rng(SEED_CH + 100)
    passes = pd.read_parquet(ROOT / "tools/data/late/swiss_passes.parquet")
    xy_pr = {r.name: (r.lon, r.lat) for r in tram_stops().itertuples()}
    xy_sw = swiss_xy()
    out = []
    for city in ("Prague", "Zurich", "Basel", "Bern"):
        r = res["prague"] if city == "Prague" else res["cities"][city]
        p = prague_passes() if city == "Prague" else passes[passes.city == city]
        s, s0 = r["S"]["est"], r["S0"]["median"]
        top, rest = lines(tot[city], xy_pr if city == "Prague" else xy_sw)
        out.append({"name": city, "S": s, "S0": s0, "E": round(s - s0, 4), "segments": len(tot[city]),
                    "curve": curve(tot[city], POINTS), "chance": chance_curve(p, rng), "top": top, "rest": rest,
                    "lat0": LAT0[city],
                    "base": "../assets/praha-base.json" if city == "Prague" else f"../assets/late-swiss/base-{city.lower()}.json"})
        print(city, "S", s, "S0", s0, "chance curve at 0.1:", out[-1]["chance"][10][1], len(top), "top lines")
    notes = [f"{c['name']}: the top tenth of {c['segments']} segments makes {100 * c['S']:.1f} % of the delay; "
             f"chance alone, {100 * c['S0']:.1f} % · {100 * c['E']:.1f} points above chance" for c in out]
    OUT.write_text(json.dumps({"cities": out, "notes": notes, "top": TOP, "perms": CURVE_PERMS}, ensure_ascii=False, separators=(",", ":")))
    print(OUT.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
