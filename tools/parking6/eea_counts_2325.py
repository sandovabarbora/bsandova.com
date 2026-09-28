"""Part 6: EEA registration counts by make × model for CZ, M1 + M1G, 2023–2025. They are the post-stratification
weights for H2b; the EEA files carry no dimensions for these years. 2025 is provisional.

    uv run --no-project --with truststore python tools/parking6/eea_counts_2325.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

sys.path.insert(0, "/Users/barbora.sandova/Downloads/parking/src")
import eea_cz  # noqa: E402

RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")
TABLES = ["[CO2Emission].[latest].[co2cars_2023Fv28]", "[CO2Emission].[latest].[co2cars_2024Fv30]",
          "[CO2Emission].[latest].[co2cars_2025Pv31]"]


def main() -> None:
    rows = []
    for t in TABLES:
        sql = (f"SELECT Year, Ct, Mk, Cn, SUM(R) AS regs FROM {t} WHERE MS='CZ' AND Ct IN ('M1','M1G') "
               "GROUP BY Year, Ct, Mk, Cn ORDER BY Year, regs DESC")
        got = eea_cz.query(sql)
        print(t, len(got), sum(int(r["regs"] or 0) for r in got), file=sys.stderr)
        rows += got
    for r in rows:
        r["Mk"], r["Cn"] = eea_cz.normalise(r["Mk"]), eea_cz.normalise(r["Cn"])
    out = RAW / "eea_cz_counts_2023_2025_m1_m1g.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Year", "Ct", "Mk", "Cn", "regs"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", out, file=sys.stderr)


if __name__ == "__main__":
    main()
