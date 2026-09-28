"""Part 6: compact extract of the RSV full export (M1, M1G, N1, N1G) to parquet. It writes, it computes nothing.

The file keeps vehicle-level technical fields only. There is no VIN, no PČV and no owner data. Lengths are written to
disk; no statistic of them is computed here.

    uv run --no-project --with pyarrow python tools/parking6/rsv_extract.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")
SRC = RAW / "RSV_vypis_vozidel_20260901.csv"
OUT = RAW / "rsv_m1n1_20260901.parquet"
CATS = {"M1", "M1G", "N1", "N1G"}

SCHEMA = pa.schema([
    ("cat", pa.string()), ("make", pa.string()), ("obch", pa.string()), ("typ", pa.string()),
    ("rv", pa.int16()), ("y1", pa.int16()), ("ycz", pa.int16()), ("status", pa.string()),
    ("L", pa.int32()), ("W", pa.int32()), ("H", pa.int32()), ("WB", pa.int32()),
])


def num(s: str) -> int | None:
    s = s.strip().replace(",", ".")
    if not s:
        return None
    try:
        v = int(float(s))
    except (ValueError, OverflowError):
        return None
    return v if 0 < v < 100_000 else None


def yr(s: str) -> int | None:
    v = int(s[:4]) if len(s) >= 4 and s[:4].isdigit() else None
    return v if v is not None and 1900 <= v <= 2030 else None


def main() -> None:
    csv.field_size_limit(10_000_000)
    with SRC.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.reader(f)
        h = next(r)
        ix = {n: i for i, n in enumerate(h)}
        c = {k: ix[v] for k, v in {
            "cat": "Kategorie vozidla", "make": "Tovární značka", "obch": "Obchodní označení", "typ": "Typ",
            "rv": "Rok výroby", "d1": "Datum 1. registrace", "dcz": "Datum 1. registrace v ČR", "st": "Status",
            "dim": "Celková délka/šířka/výška [mm]", "wb": "Rozvor [mm]"}.items()}
        writer = pq.ParquetWriter(OUT, SCHEMA, compression="zstd")
        buf = {n: [] for n in SCHEMA.names}
        n = 0
        for row in r:
            cat = row[c["cat"]].strip().upper()
            if cat not in CATS:
                continue
            dims = (row[c["dim"]].split("/") + ["", "", ""])[:3]
            rv = row[c["rv"]].strip()
            buf["cat"].append(cat)
            buf["make"].append(row[c["make"]].strip())
            buf["obch"].append(row[c["obch"]].strip())
            buf["typ"].append(row[c["typ"]].strip())
            buf["rv"].append(yr(rv))
            buf["y1"].append(yr(row[c["d1"]]))
            buf["ycz"].append(yr(row[c["dcz"]]))
            buf["status"].append(row[c["st"]].strip())
            buf["L"].append(num(dims[0]))
            buf["W"].append(num(dims[1]))
            buf["H"].append(num(dims[2]))
            buf["WB"].append(num(row[c["wb"]].split("/")[0]))
            n += 1
            if n % 500_000 == 0:
                writer.write_table(pa.table(buf, schema=SCHEMA))
                buf = {k: [] for k in SCHEMA.names}
                print(f"{n:,}", file=sys.stderr, flush=True)
        writer.write_table(pa.table(buf, schema=SCHEMA))
        writer.close()
    print(f"done {n:,} rows -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
