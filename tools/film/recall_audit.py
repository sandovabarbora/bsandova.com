"""Blind recall audit of the frozen links (design, Changes after registration, 1 October 2026 (1)).

Draws 30 funded and 30 unfunded unmatched applications from the primary sample (2016-2021, feature
length), seed 20261002, and writes:
- tools/data/film/audit_sheet.csv: shuffled, WITHOUT funding or points, with the top-5 title
  candidates and the producer candidates (Wikidata P272) for each, for the hand search;
- tools/data/film/audit_key.csv: the row -> funded key, read only after every row is decided.

    uv run --no-project --with pandas --with pyarrow --with rapidfuzz python tools/film/recall_audit.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link import candidates, norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "film"
SEED = 20261002


def company(s: str) -> str:
    s = norm(s)
    s = re.sub(r"\b(s r o|spol s r o|a s|ltd|production|productions|produkce|film|films|studio|studios)\b", " ", s)
    return " ".join(s.split())


def main() -> None:
    links = pd.read_csv(DATA / "links_frozen.csv")
    fund = pd.read_parquet(DATA / "applications.parquet", columns=["call", "app_id", "title", "funded", "call_title"])
    d = links.merge(fund, on=["call", "app_id", "title"], how="left")
    d["yr"] = d.call.str[:4].astype(int)
    prim = d[(d.yr <= 2021) & ~d.call_title.str.lower().str.contains("krátkometr|kratkometr") & ~d.linked]
    prim = prim.drop_duplicates(subset=["title", "applicant"])
    pick = pd.concat([prim[prim.funded].sample(30, random_state=SEED), prim[~prim.funded].sample(30, random_state=SEED)])
    pick = pick.sample(frac=1, random_state=SEED).reset_index(drop=True)
    pick[["call", "app_id", "title", "funded"]].rename_axis("row").to_csv(DATA / "audit_key.csv")
    cand = candidates()
    lum = pd.read_parquet(DATA / "outcomes" / "lumiere_cz.parquet")
    prod_path = DATA / "outcomes" / "producers.parquet"
    prod = pd.read_parquet(prod_path) if prod_path.exists() else pd.DataFrame(columns=["movie_id", "company"])
    prod["ckey"] = prod.company.map(company)
    rows = []
    for i, a in pick.iterrows():
        lo, hi = a.yr, a.yr + 6
        w = cand[(cand.year >= lo) & (cand.year <= hi)].drop_duplicates("src_id")
        top = process.extract(norm(a.title), dict(zip(w.src_id, w.key)), scorer=fuzz.WRatio, limit=5)
        tops = [f"{w.set_index('src_id').at[sid, 'label']} ({w.set_index('src_id').at[sid, 'detail']}) {int(sc)}" for _, sc, sid in top]
        ck = company(a.applicant)
        by_co = prod[prod.ckey.map(lambda k: bool(ck) and (ck in k or k in ck) and len(min(ck, k, key=len)) >= 4)]
        films = lum[lum.movie_id.isin(by_co.movie_id) & lum.cz_date.ne("")]
        films = films[films.cz_date.str[-4:].astype(int).between(lo, hi)]
        rows.append({"row": i, "title": a.title, "applicant": a.applicant, "call_year": a.yr,
                     "title_candidates": " | ".join(tops),
                     "producer_candidates": " | ".join(f"{r.title_cz or r.title} ({r.cz_date})" for r in films.itertuples()),
                     "found": "", "film": ""})
    pd.DataFrame(rows).to_csv(DATA / "audit_sheet.csv", index=False)
    print(f"audit sheet: {len(rows)} rows (key kept apart in audit_key.csv)")


if __name__ == "__main__":
    main()
