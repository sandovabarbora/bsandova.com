"""Referee item C.6: re-pull Part II's EEA series with Ct IN ('M1','M1G') (Part II used M1 only).

Reuses the read-only parking repo (~/Downloads/parking/src), which is imported and never modified. It writes the raw
aggregates to tools/data/parking6/ and the wheelbase-only summary (no length conversion; that waits for the register
slope, C.2) to docs/research/prague-parking-ds.json under "eea_m1g".

    uv run --no-project --with numpy python tools/parking6/eea_m1g.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

try:  # system trust store (the EEA chain fails against certifi on this machine)
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

sys.path.insert(0, "/Users/barbora.sandova/Downloads/parking/src")
import eea_cz  # noqa: E402
from eea_series import yearly  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")
OUT = ROOT / "docs/research/prague-parking-ds.json"


def pull(cats: str) -> list[dict]:
    rows = []
    for _, table, where in eea_cz.SOURCES:
        sql = eea_cz.agg_sql(table, where).replace("Ct='M1'", f"Ct IN ({cats})")
        sql = sql.replace("SELECT Year, Mk, Cn,", "SELECT Year, Ct, Mk, Cn,").replace("GROUP BY Year, Mk, Cn", "GROUP BY Year, Ct, Mk, Cn")
        rows += eea_cz.query(sql)
    for r in rows:
        r["Mk"], r["Cn"] = eea_cz.normalise(r["Mk"]), eea_cz.normalise(r["Cn"])
    return rows


def main() -> None:
    rows = pull("'M1','M1G'")
    raw = RAW / "eea_cz_by_model_m1_m1g.csv"
    keys = ["Year", "Ct", "Mk", "Cn", "regs", "n_w", "sum_w", "n_at", "sum_at", "n_m", "sum_m"]
    with raw.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    conv = [{k: (r[k] if k in ("Ct", "Mk", "Cn") else int(float(r[k] or 0))) for k in keys} for r in rows]
    # M1G share by year
    share = {}
    for y in sorted({r["Year"] for r in conv}):
        tot = sum(r["regs"] for r in conv if r["Year"] == y)
        share[y] = round(sum(r["regs"] for r in conv if r["Year"] == y and r["Ct"] == "M1G") / tot, 4)
    # merge categories per model (same imputation rule as Part II)
    merged: dict = {}
    for r in conv:
        k = (r["Year"], r["Mk"], r["Cn"])
        m = merged.setdefault(k, {"Year": r["Year"], "Mk": r["Mk"], "Cn": r["Cn"], "regs": 0, "n_w": 0, "sum_w": 0})
        for c in ("regs", "n_w", "sum_w"):
            m[c] += r[c]
    wy = yearly(list(merged.values()), "n_w", "sum_w")
    years = sorted(wy)
    slope = float(np.polyfit(years, [wy[y]["mean"] for y in years], 1)[0])
    tr = [y for y in years if 2012 <= y <= 2022]
    slope_1222 = float(np.polyfit(tr, [wy[y]["mean"] for y in tr], 1)[0])
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    res["eea_m1g"] = {
        "raw_file": raw.name, "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "m1g_share_by_year": share,
        "wheelbase_mean_mm": {y: round(wy[y]["mean"], 1) for y in years},
        "wheelbase_change_2012_2022_mm_endpoints": round(wy[2022]["mean"] - wy[2012]["mean"], 1),
        "wheelbase_trend_2012_2022_mm_per_year": round(slope_1222, 3),
        "wheelbase_trend_2012_2022_mm_x10": round(slope_1222 * 10, 1),
        "wheelbase_trend_2010_2022_mm_per_year": round(slope, 3),
        "part2_m1_only": {"change_2012_2022_mm": 68, "slope_mm_per_year": 6.0},
    }
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res["eea_m1g"], indent=1))


if __name__ == "__main__":
    main()
