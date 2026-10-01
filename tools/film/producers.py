"""Production companies of the LUMIERE films, from Wikidata (P272), for linking rule 4.

LUMIERE film pages link their Wikidata item; one SPARQL query returns the production companies
(and their labels in Czech and English). Writes tools/data/film/outcomes/producers.parquet.

    uv run --no-project --with requests --with pandas --with pyarrow python tools/film/producers.py
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "data" / "film" / "outcomes"
UA = {"User-Agent": "bsandova.com research (film fund study; contact via bsandova.com)",
      "Accept": "application/sparql-results+json"}


def main() -> None:
    qids = {}
    for p in (OUT / "lumiere").glob("*.html"):
        m = re.search(r"wikidata\.org/(?:wiki|entity)/(Q\d+)", p.read_text(encoding="utf-8"))
        if m:
            qids[m.group(1)] = int(p.stem)
    print(f"{len(qids)} of {len(list((OUT / 'lumiere').glob('*.html')))} films have a Wikidata item")
    rows = []
    items = sorted(qids)
    for i in range(0, len(items), 200):
        values = " ".join(f"wd:{q}" for q in items[i:i + 200])
        q = f"""SELECT ?film ?co ?coLabel WHERE {{ VALUES ?film {{ {values} }} ?film wdt:P272 ?co .
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "cs,en,sk". }} }}"""
        r = requests.get("https://query.wikidata.org/sparql", params={"query": q}, headers=UA, timeout=120)
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            qid = b["film"]["value"].rsplit("/", 1)[-1]
            rows.append({"movie_id": qids[qid], "qid": qid, "company_qid": b["co"]["value"].rsplit("/", 1)[-1],
                         "company": b["coLabel"]["value"]})
        time.sleep(1.0)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "producers.parquet", index=False)
    print(f"{len(df)} film-company pairs for {df.movie_id.nunique()} films, {df.company.nunique()} companies")


if __name__ == "__main__":
    main()
