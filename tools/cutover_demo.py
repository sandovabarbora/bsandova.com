"""Demo for texts/cutover.html: a 'legacy' pandas daily aggregate vs a 'new' SQL one over NYC yellow taxi, January 2025.

    .venv/bin/python tools/cutover_demo.py

Downloads one public parquet (~50 MB) into tools/data/, builds both aggregates, runs cutover,
writes assets/cutover/report.{html,json} and prints the text report. Whatever it finds is reported as found.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

import cutover

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "data" / "yellow_tripdata_2025-01.parquet"
URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-01.parquet"
OUT = ROOT / "assets" / "cutover"
MILE = 1.609344


def legacy(path: Path) -> pd.DataFrame:
    """The old way: pandas, calendar day of pickup, float sums, drop rows with no fare."""
    df = pd.read_parquet(path, columns=["tpep_pickup_datetime", "PULocationID", "fare_amount", "trip_distance"])
    df = df[df.fare_amount > 0]
    df["day"] = df.tpep_pickup_datetime.dt.date
    g = df.groupby(["day", "PULocationID"]).agg(
        trips=("fare_amount", "size"), fare=("fare_amount", "sum"), km=("trip_distance", "sum")
    )
    g["km"] = g["km"] * MILE
    return g.reset_index().rename(columns={"PULocationID": "zone"})


def new(path: Path) -> pd.DataFrame:
    """The new way: SQL in DuckDB. Same intent; independently written."""
    return duckdb.sql(
        f"""
        SELECT CAST(tpep_pickup_datetime AS DATE) AS day, PULocationID AS zone,
               count(*) AS trips, round(sum(fare_amount), 2) AS fare, sum(trip_distance) * {MILE} AS km
        FROM read_parquet('{path}')
        WHERE fare_amount > 0
        GROUP BY 1, 2
        """
    ).df()


def main() -> None:
    SRC.parent.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        print("downloading", URL)
        urllib.request.urlretrieve(URL, SRC)
    OUT.mkdir(parents=True, exist_ok=True)
    old, nw = legacy(SRC), new(SRC)
    old.name, nw.name = "legacy (pandas)", "new (SQL)"

    # run 1: as written
    r1 = cutover.compare(old, nw, key=["day", "zone"], partition="day", tolerance={"km": 1e-6})
    (OUT / "report-1.html").write_text(r1.to_html())
    (OUT / "report-1.json").write_text(r1.to_json())
    print("--- run 1\n" + r1.to_text())

    # run 2: the new side fixes its partition type (DuckDB DATE came back as datetime64 in pandas),
    # and fare gets a half-cent tolerance because the legacy never rounded its float sums
    nw2 = nw.assign(day=nw.day.dt.date)
    nw2.name = "new (SQL), day cast to date"
    r2 = cutover.compare(old, nw2, key=["day", "zone"], partition="day", tolerance={"km": 1e-6, "fare": 0.005})
    (OUT / "report-2.html").write_text(r2.to_html())
    (OUT / "report-2.json").write_text(r2.to_json())
    print("--- run 2\n" + r2.to_text())


if __name__ == "__main__":
    main()
