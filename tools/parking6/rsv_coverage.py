"""DS1 (Part 6 parking design): coverage of the RSV full export, read from stdin.

Counts only. Each row's length field is tested for missingness (empty, non-numeric or 0). No length value is kept,
summed or written. Keys: category, manufacture year, year of first registration, year of first registration in CZ,
status, length present, wheelbase present. The owner/operator dataset is never touched.

    curl -sS https://download.dataovozidlech.cz/vypiszregistru/vypisvozidel | tee RAW.csv | python rsv_coverage.py OUT.json
"""
from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter

CATS = {"M1", "M1G", "N1", "N1G"}


def present(field: str | None) -> int:
    if not field:
        return 0
    first = field.split("/")[0].strip()
    try:
        return int(float(first.replace(",", ".")) > 0)
    except ValueError:
        return 0


def year(d: str | None) -> str:
    return d[:4] if d and len(d) >= 4 and d[:4].isdigit() else ""


def main(out: str) -> None:
    csv.field_size_limit(10_000_000)
    stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", errors="replace", newline="")
    reader = csv.reader(stream)
    header = next(reader)
    ix = {name: i for i, name in enumerate(header)}
    c_cat, c_rv = ix["Kategorie vozidla"], ix["Rok výroby"]
    c_d1, c_dcz = ix["Datum 1. registrace"], ix["Datum 1. registrace v ČR"]
    c_st, c_dim, c_wb = ix["Status"], ix["Celková délka/šířka/výška [mm]"], ix["Rozvor [mm]"]
    n = len(header)
    counts: Counter = Counter()
    jan1: Counter = Counter()
    rows = short = 0
    for r in reader:
        rows += 1
        if len(r) < n:
            short += 1
            r = r + [""] * (n - len(r))
        cat = r[c_cat].strip().upper()
        cat = cat if cat in CATS else "other"
        dcz = r[c_dcz]
        key = (cat, r[c_rv].strip()[:4], year(r[c_d1]), year(dcz), r[c_st].strip(), present(r[c_dim]), present(r[c_wb]))
        counts[key] += 1
        if cat in ("M1", "M1G"):
            jan1[(year(dcz), dcz[5:10] == "01-01")] += 1
        if rows % 2_000_000 == 0:
            print(f"{rows:,} rows", file=sys.stderr, flush=True)
    with open(out, "w") as f:
        json.dump({
            "rows": rows, "short_rows": short, "header": header,
            "cells_keys": ["category", "rok_vyroby", "y_first_reg", "y_first_reg_cz", "status",
                           "length_present", "wheelbase_present", "n"],
            "cells": [list(k) + [v] for k, v in counts.items()],
            "jan1_first_reg_cz_m1": [list(k) + [v] for k, v in jan1.items()],
        }, f, ensure_ascii=False)
    print(f"done {rows:,} rows, {short:,} short", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
