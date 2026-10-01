"""Apply the blind hand-review decisions to the links and freeze them (design §3).

Decisions are by row of tools/data/film/review.csv (written by link.py); they were made seeing only
the application's title, applicant and call year and the candidate's title and release data.
yes = same film; no = not; unsure = counted as not released in the primary analysis and as
released in the sensitivity check (design §6). Writes docs/research/film-fund-links.csv (the
reviewed rows with their decisions) and tools/data/film/links_frozen.csv, and prints the hash
that the results commit cites.

    uv run --no-project --with pandas python tools/film/freeze_links.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "film"
UNSURE = {22, 42, 57, 63, 65, 70, 78, 95, 96, 105, 123}
YES = set(range(0, 32)) - UNSURE | {35, 36, 37, 38, 39, 45, 55, 59, 60, 64, 66, 67, 75, 79, 80, 82, 84, 85, 91,
                                    97, 98, 103, 104, 107, 115, 125, 127, 129, 133, 136, 139}


def main() -> None:
    review = pd.read_csv(DATA / "review.csv")
    review["decision"] = ["unsure" if i in UNSURE else "yes" if i in YES else "no" for i in review.index]
    review.drop(columns=["note"]).to_csv(ROOT / "docs" / "research" / "film-fund-links.csv", index=False)
    links = pd.read_csv(DATA / "links.csv")
    key = ["call", "app_id", "title"]
    dec = review.set_index(key)["decision"]
    links["decision"] = [dec.get(tuple(r), "yes" if r_rule == 1 else "none")
                         for r, r_rule in zip(links[key].itertuples(index=False), links.rule)]
    links["linked"] = links.decision.eq("yes")
    links["linked_sens"] = links.decision.isin(["yes", "unsure"])
    out = DATA / "links_frozen.csv"
    links.to_csv(out, index=False)
    print(links.decision.value_counts().to_string())
    print("links_frozen.csv sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
