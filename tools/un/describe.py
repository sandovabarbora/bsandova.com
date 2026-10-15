"""Post-hoc and descriptive, not registered: two descriptions drawn after the stage A results were read, with the
definitions of the frozen code (votes.py) and no change to it.

1. Agreement with the EU majority per calendar year, 2014 to 14 December 2025, for every EU-27 member: each member
   against the most common position of the other 26 that voted (a tie drops the vote). Czechia is set against the
   lowest, median and highest of the other members in each year. This is a level, not the registered β.
2. For the votes on which Czechia's position differed from that majority in each stage A period: Czechia's position
   against the majority's (yes, no or abstain), counted per pair.

Czech positions are read only up to 14 December 2025, through load(end=...), as in stage A. Writes
docs/research/un-votes-describe.json.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with numpy python tools/un/describe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from votes import EU27, POS, ROOT, agreement_eu, load, positions  # noqa: E402

END = "2025-12-14"
OUT = ROOT / "docs/research/un-votes-describe.json"
PERIODS = {"sobotka": ("2014-01-29", "2017-12-12"), "babis": ("2018-01-12", "2021-12-16"),
           "fiala": ("2022-01-16", END)}
NAME = {v: k for k, v in POS.items()} | {-1: "X"}


def majority(m, member: str) -> np.ndarray:
    """The position code of the most common position among the EU-27 members other than `member` (−1 on a tie)."""
    vals = m[[c for c in EU27 if c in m.columns and c != member]].to_numpy()
    counts = np.stack([(vals == k).sum(1) for k in range(3)], 1)
    top = counts.max(1)
    return np.where(((counts == top[:, None]).sum(1) == 1) & (top > 0), counts.argmax(1), -1)


def main() -> None:
    m, info, _ = positions(load(end=END))
    year = info["date"].dt.year
    agree = {c: agreement_eu(m, c) for c in EU27 if c in m.columns}
    years = {}
    for y in sorted(year.unique()):
        inside = year == y
        lv = {c: float(a[inside].mean()) for c, a in agree.items()}
        others = sorted(v for c, v in lv.items() if c != "CZE")
        years[str(int(y))] = {"votes": int(inside.sum()), "czechia": round(lv["CZE"], 4),
                              "others_min": round(others[0], 4), "others_median": round(float(np.median(others)), 4),
                              "others_max": round(others[-1], 4),
                              "czechia_rank_from_top": 1 + sum(v > lv["CZE"] for v in others),
                              "lowest_other": min((v, c) for c, v in lv.items() if c != "CZE")[1]}
    maj = majority(m, "CZE")
    cz = m["CZE"].to_numpy()
    pairs = {}
    for key, (a, b) in PERIODS.items():
        inside = ((info["date"] >= a) & (info["date"] <= b)).to_numpy()
        off = inside & (cz >= 0) & (maj >= 0) & (cz != maj)
        counts: dict[str, int] = {}
        for c, j in zip(cz[off], maj[off]):
            k = f"czechia {NAME[c]}, majority {NAME[j]}"
            counts[k] = counts.get(k, 0) + 1
        pairs[key] = {"departures": int(off.sum()), "pairs": dict(sorted(counts.items(), key=lambda kv: -kv[1]))}
    out = {"note": "post-hoc, descriptive: drawn after the stage A results were read; Czech positions to " + END,
           "years": years, "departure_positions": pairs}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
