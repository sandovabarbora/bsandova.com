"""Concert effect: the country × week panel and the tour's first show per country (design §2–3).

Reads tools/data/concerts/charts.csv (Spotify Charts on Kaggle, ODbL) in chunks, keeps the daily Top 200 of
countries from 1 March 2017 to 31 December 2018, and sums by country and week (weeks start on Monday):
the week's Top-200 streams, Harry Styles's streams, his songs per day, and his three most-streamed songs of the window.
Reads the tour's show rows from the Wikipedia revision collected for Pop, measured.

Writes docs/research/concert-effect-panel.csv (ODbL, derived from Spotify Charts), concert-effect-shows.csv,
concert-effect-songs.csv and the hash of charts.csv to docs/research/concert-effect-files.sha256.

    uv run --with pandas --with beautifulsoup4 python tools/concerts/prepare.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pop"))
from parse import grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "concerts"
OUT = ROOT / "docs" / "research"
START, END = pd.Timestamp("2017-03-01"), pd.Timestamp("2018-12-31")
WEEK0 = START - pd.Timedelta(days=START.weekday())          # the Monday on or before the start
ALIAS = {"England": "United Kingdom", "Scotland": "United Kingdom", "Wales": "United Kingdom",
         "Northern Ireland": "United Kingdom"}


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s)).casefold()


def week(d: pd.Series) -> pd.Series:
    return ((d - WEEK0).dt.days // 7 + 1).astype(int)


def shows() -> pd.DataFrame:
    """Every show row of the tour article (revision fixed in Pop, measured): date and country. The table is expanded
    with the row spans carried, by the same grid as tools/pop/parse.py."""
    page = json.loads((ROOT / "tools" / "data" / "pop" / "raw" / "wiki" / "harry-styles-live-on-tour.json").read_text())
    soup = BeautifulSoup(page["parse"]["text"]["*"], "html.parser")
    rows = []
    for table in soup.select("table.wikitable"):
        head, body = grid(table)
        if "Country" not in head:
            continue
        c = head.index("Country")
        for row in body:
            if len(row) > c and re.search(r"\b20\d\d\b", row[0][1]):
                rows.append({"date": pd.to_datetime(row[0][1], dayfirst=True), "country": ALIAS.get(row[c][1], row[c][1])})
    return pd.DataFrame(rows)


def main() -> None:
    path = DATA / "charts.csv"
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            digest.update(block)
    (OUT / "concert-effect-files.sha256").write_text(f"{digest.hexdigest()}  charts.csv\n")

    parts = []
    for chunk in pd.read_csv(path, chunksize=2_000_000, usecols=["title", "date", "artist", "region", "chart", "streams"]):
        chunk = chunk[(chunk.chart == "top200") & (chunk.region != "Global")]
        chunk["date"] = pd.to_datetime(chunk.date)
        chunk = chunk[(chunk.date >= START) & (chunk.date <= END)]
        chunk["hs"] = chunk.artist.map(lambda a: "harry styles" in norm(a))
        parts.append(chunk)
    d = pd.concat(parts)
    d["week"] = week(d.date)

    hs = d[d.hs]
    songs = hs.groupby(["title", "artist"]).streams.sum().sort_values(ascending=False).reset_index()
    songs.to_csv(OUT / "concert-effect-songs.csv", index=False)
    top3 = set(songs.title.head(3))

    g = d.groupby(["region", "week"])
    panel = pd.DataFrame({
        "days": g.date.nunique(),
        "total_streams": g.streams.sum(),
        "hs_streams": d[d.hs].groupby(["region", "week"]).streams.sum(),
        "hs_rows": d[d.hs].groupby(["region", "week"]).size(),
        "top3_streams": d[d.hs & d.title.isin(top3)].groupby(["region", "week"]).streams.sum(),
    }).fillna(0).reset_index().rename(columns={"region": "country"})
    panel["y1_share"] = panel.hs_streams / panel.total_streams
    panel["y2_songs"] = panel.hs_rows / panel.days
    panel["y3_share_top3"] = panel.top3_streams / panel.total_streams

    s = shows()
    s.to_csv(OUT / "concert-effect-shows.csv", index=False)
    first = s.groupby("country").date.min()
    panel["first_show"] = panel.country.map(first)
    panel["g"] = panel.first_show.map(lambda x: 0 if pd.isna(x) else int((x - WEEK0).days // 7 + 1))
    panel["week_start"] = (WEEK0 + pd.to_timedelta((panel.week - 1) * 7, unit="D")).dt.date
    panel.to_csv(OUT / "concert-effect-panel.csv", index=False)
    unmatched = sorted(set(first.index) - set(panel.country))
    print(f"{panel.country.nunique()} countries, {panel.week.nunique()} weeks; tour countries without a chart: {unmatched}")
    print("Harry Styles songs in the window:", len(songs), "| top three:", sorted(top3))


if __name__ == "__main__":
    main()
