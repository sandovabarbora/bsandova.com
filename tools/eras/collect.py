"""Eras Tour and prices: download the HICP series once (design §2) and hash the response.

Eurostat `prc_hicp_midx`, unit I15, COICOP CP112, CP111 and CP00, EU and EEA countries and Switzerland,
January 2022 to December 2025. Writes tools/data/eras/hicp.json (not committed) and its SHA-256 to
docs/research/eras-inflation-files.sha256, and the long table docs/research/eras-inflation-hicp.csv.

    uv run --with certifi python tools/eras/collect.py
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "eras"
GEO = "AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK IS NO CH".split()
COICOP = ["CP112", "CP111", "CP00"]


def main() -> None:
    q = [("format", "JSON"), ("unit", "I15"), ("sinceTimePeriod", "2022-01"), ("untilTimePeriod", "2025-12")]
    q += [("coicop", c) for c in COICOP] + [("geo", g) for g in GEO]
    url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx?" + urllib.parse.urlencode(q)
    import certifi   # the system store lacks Eurostat's issuer on some machines
    ctx = ssl.create_default_context(cafile=certifi.where())
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bsandova.com research"}), timeout=120, context=ctx).read()
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "hicp.json").write_bytes(data)
    (ROOT / "docs" / "research" / "eras-inflation-files.sha256").write_text(f"{hashlib.sha256(data).hexdigest()}  hicp.json\n")
    d = json.loads(data)
    dims = d["id"]
    cats = [sorted(d["dimension"][k]["category"]["index"].items(), key=lambda x: x[1]) for k in dims]
    rows = []
    for pos, combo in enumerate(itertools.product(*cats)):
        v = d["value"].get(str(pos))
        if v is None:
            continue
        rec = {k: c[0] for k, c in zip(dims, combo)}
        rows.append({"geo": rec["geo"], "coicop": rec["coicop"], "month": rec["time"], "index": v})
    with open(ROOT / "docs" / "research" / "eras-inflation-hicp.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["geo", "coicop", "month", "index"])
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "values;", len({r["geo"] for r in rows}), "countries")


if __name__ == "__main__":
    main()
