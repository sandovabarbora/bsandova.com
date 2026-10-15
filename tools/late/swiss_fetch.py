"""Download the Swiss Ist-Daten (version 1) for the window of the swiss-trams design and keep the tram rows only.

One monthly ZIP at a time: every daily CSV inside it within the window is filtered to PRODUKT_ID = 'Tram' and written
to tools/data/late/swiss/<date>.parquet as text columns, then the ZIP is deleted. No delay is computed here.

    nice -n 20 uv run --no-project --with pandas --with pyarrow python tools/late/swiss_fetch.py
"""
from __future__ import annotations

import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/data/late/swiss"
URL = "https://archive.opentransportdata.swiss/istdaten/2025/ist-daten-2025-{m:02d}.zip"
START, END = date(2025, 3, 15), date(2025, 9, 8)


def fetch(month: int) -> Path:
    zp = OUT / f"ist-daten-2025-{month:02d}.zip"
    if not zp.exists():
        req = urllib.request.Request(URL.format(m=month), headers={"User-Agent": "bsandova.com research"})
        part = zp.with_suffix(".part")
        with urllib.request.urlopen(req, timeout=120) as r, part.open("wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        part.rename(zp)
    return zp


def day_of(name: str) -> date | None:
    try:
        return date.fromisoformat(Path(name).name[:10])
    except ValueError:
        return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for month in range(START.month, END.month + 1):
        zp = fetch(month)
        with zipfile.ZipFile(zp) as z:
            for name in sorted(z.namelist()):
                d = day_of(name)
                if d is None or not START <= d <= END or (OUT / f"{d}.parquet").exists():
                    continue
                with z.open(name) as f:
                    parts = [c[c.PRODUKT_ID == "Tram"] for c in
                             pd.read_csv(f, sep=";", dtype=str, chunksize=500_000, keep_default_na=False)]
                pd.concat(parts).to_parquet(OUT / f"{d}.parquet", index=False)
                print(d, flush=True)
        zp.unlink()


if __name__ == "__main__":
    main()
