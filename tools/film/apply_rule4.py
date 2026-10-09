"""Add the hand-reviewed rule-4 links (docs/research/film-fund-rule4.csv) to tools/data/film/links_frozen.csv.

Run after freeze_links.py and before analyse.py. This step was run by hand on 1 October 2026 and
committed on 9 October 2026; with the frozen inputs it reproduces docs/research/film-fund-results.json exactly.

    uv run --no-project --with pandas --with pyarrow python tools/film/apply_rule4.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "film"
COLS = ["rule", "src", "src_id", "matched_label", "decision", "linked", "linked_sens"]


def main() -> None:
    out = DATA / "links_frozen.csv"
    # read as text so untouched rows are written back byte for byte
    links = pd.read_csv(out, dtype=object)
    review = pd.read_csv(ROOT / "docs" / "research" / "film-fund-rule4.csv", dtype=object)
    lum = pd.read_parquet(DATA / "outcomes" / "lumiere_cz.parquet")
    title = dict(zip(lum.movie_id.astype(str), lum.title))
    for r in review[review.decision == "yes"].itertuples():
        row = (links.call == r.call) & (links.app_id == r.app_id) & (links.title == r.title)
        links.loc[row, COLS] = ["4", "lumiere", r.movie_id, title[r.movie_id], "yes", "True", "True"]
    links.to_csv(out, index=False)
    print("links_frozen.csv sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
