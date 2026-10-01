"""Linking rule 4 (producer), blind to points and awards (design, Changes after registration (1)).

For each production application left unlinked by rules 1-3: LUMIERE films released in Czech
cinemas within 0-6 years of the call whose Wikidata production company matches the applicant
(normalized), and that share a distinctive title word with the application or are the company's
only such film in the window. Writes tools/data/film/rule4_review.csv for the blind hand review.

    uv run --no-project --with pandas --with pyarrow --with rapidfuzz python tools/film/rule4.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link import norm  # noqa: E402
from recall_audit import company  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "tools" / "data" / "film"
STOP = {"a", "i", "v", "na", "o", "s", "z", "do", "the", "of", "and", "aneb", "film", "pribeh", "pribehy"}


def main() -> None:
    links = pd.read_csv(DATA / "links_frozen.csv")
    lum = pd.read_parquet(DATA / "outcomes" / "lumiere_cz.parquet")
    lum = lum[lum.cz_date.ne("")].assign(year=lambda d: d.cz_date.str[-4:].astype(int))
    prod = pd.read_parquet(DATA / "outcomes" / "producers.parquet").assign(ckey=lambda d: d.company.map(company))
    rows = []
    for a in links[~links.linked_sens].itertuples():
        ck = company(a.applicant)
        if len(ck) < 4:
            continue
        mids = prod[prod.ckey.map(lambda k: ck in k or k in ck)].movie_id
        films = lum[lum.movie_id.isin(mids) & lum.year.between(a.call_year, a.call_year + 6)]
        words = {w for w in norm(a.title).split() if w not in STOP and len(w) > 2}
        for f in films.itertuples():
            fw = {w for w in norm(f"{f.title} {f.title_cz}").split() if w not in STOP and len(w) > 2}
            if words & fw or len(films) == 1:
                rows.append({"call": a.call, "app_id": a.app_id, "title": a.title, "applicant": a.applicant,
                             "call_year": a.call_year, "film": f.title_cz or f.title, "movie_id": f.movie_id,
                             "cz_date": f.cz_date, "decision": ""})
    pd.DataFrame(rows).to_csv(DATA / "rule4_review.csv", index=False)
    print(f"rule 4 candidates: {len(rows)}")
    for r in rows:
        print(f"  {r['title'][:40]} | {r['applicant'][:24]} {r['call_year']} => {r['film'][:40]} ({r['cz_date']})")


if __name__ == "__main__":
    main()
