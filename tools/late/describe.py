"""Descriptive companions to the delay-origins estimate, computed after the results and not registered.

How much of the concentration S is traffic volume: the share of all tram passes on the tenth of segments with the
most passes, which is also the top-tenth share S would take if every segment had the same mean gain per pass. And
the delay gained arriving at and leaving the large stops, weighted by passes. Writes
docs/research/delay-origins-describe.json.

    uv run --with numpy --with pandas --with pyarrow python tools/late/describe.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/research/delay-origins-describe.json"
NODES = ["Václavské náměstí", "Anděl", "Hlavní nádraží", "Kobylisy", "Karlovo náměstí", "Palmovka"]


def main() -> None:
    s = pd.read_parquet(ROOT / "tools/data/late/segments.parquet")
    out = {"note": "computed after the results; descriptive, not registered"}
    for mode, g in s.groupby("mode"):
        t = g.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum()
        k = math.ceil(0.10 * len(t))
        busiest = t.sort_values("n", ascending=False).head(k)
        by_total = t.sort_values("gsum", ascending=False).head(k)
        out[mode] = {
            "segments": len(t),
            "top_tenth_pass_share": round(float(busiest["n"].sum() / t["n"].sum()), 4),
            "top_tenth_by_delay_pass_share": round(float(by_total["n"].sum() / t["n"].sum()), 4),
            "overlap_busiest_and_largest_producers": round(len(set(busiest.index) & set(by_total.index)) / k, 4),
        }
        if mode == "tram":
            t = t.reset_index()
            t["pp"] = t["gsum"] / t["n"]
            rows = []
            for node in NODES:
                for side, sub in (("arriving", t[t["seg_to"] == node]), ("leaving", t[t["seg_from"] == node])):
                    if len(sub):
                        rows.append({"stop": node, "side": side, "segments": len(sub), "passes": int(sub["n"].sum()),
                                     "per_pass_s": round(float(sub["gsum"].sum() / sub["n"].sum()), 2)})
            out["tram"]["large_stops"] = rows
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({m: {k: v for k, v in d.items() if k != "large_stops"} for m, d in out.items() if m != "note"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
