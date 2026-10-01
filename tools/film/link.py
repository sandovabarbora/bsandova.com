"""Link fund applications to released films, blind to points and awards (design §3).

Reads from applications.parquet ONLY the columns call, call_title, app_id, applicant and title;
the points and the award are never loaded here. Writes:

- tools/data/film/links.csv: one row per production application, with its match (or none), the rule
  that made it, and the candidate's release data;
- tools/data/film/review.csv: every rule-2 link and a seeded 10 % of rule-1 links, for the blind
  hand review (decisions go to docs/research/film-fund-links.csv).

Rules, in order:
  1. exact normalized title (case, diacritics, punctuation), released within 0-6 years of the call year;
  2. token-set similarity >= 90 within the same window, unique best candidate;
  3. otherwise no match.

    uv run --no-project --with pandas --with pyarrow --with rapidfuzz python tools/film/link.py
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "film"
BLIND_COLS = ["call", "call_title", "app_id", "applicant", "title"]   # never the points or the award
WINDOW = (0, 6)
FUZZY_MIN = 90
REVIEW_SHARE, SEED = 0.10, 20261001


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)              # "(pracovní název)" and similar
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def candidates() -> pd.DataFrame:
    """Every released film with every title it is known by, and its release year and data."""
    out = []
    lum = pd.read_parquet(DATA / "outcomes" / "lumiere_cz.parquet")
    for r in lum.itertuples():
        released = r.cz_admissions > 0
        year = int(r.cz_date[-4:]) if r.cz_date else int(r.prod_year)
        names = {r.title, r.title_cz, *json.loads(r.titles).values()}
        for n in names:
            if norm(n):
                out.append({"key": norm(n), "src": "lumiere", "src_id": str(r.movie_id), "year": year,
                            "released_cz": released, "cz_admissions": int(r.cz_admissions),
                            "eu_admissions": int(r.eu_admissions), "label": r.title_cz or r.title,
                            "detail": f"{r.directors} · {r.countries} · {r.cz_distributor} {r.cz_date}"})
    ufd = pd.read_parquet(DATA / "outcomes" / "ufd_premieres.parquet")
    for i, r in enumerate(ufd.itertuples()):
        for n in {r.title_orig, r.title_cz}:
            if norm(n) and n != "nan":
                out.append({"key": norm(n), "src": "ufd", "src_id": f"ufd{r.year}-{i}", "year": int(r.year),
                            "released_cz": True, "cz_admissions": None, "eu_admissions": None,
                            "label": r.title_cz, "detail": f"{r.distributor} {r.date}"})
    return pd.DataFrame(out)


def main() -> None:
    apps = pd.read_parquet(DATA / "applications.parquet", columns=BLIND_COLS)
    apps = apps[apps.call_title.str.lower().str.contains("výrob") & apps.call.notna()].copy()
    apps["call_year"] = apps.call.str[:4].astype(int)
    apps["key"] = apps.title.map(norm)
    cand = candidates()
    by_key = cand.groupby("key")
    rows = []
    for a in apps.itertuples():
        lo, hi = a.call_year + WINDOW[0], a.call_year + WINDOW[1]
        rule, hit, score = 3, None, None
        if a.key in by_key.groups:
            c = by_key.get_group(a.key)
            c = c[(c.year >= lo) & (c.year <= hi)]
            if len(c):
                rule, hit, score = 1, c.sort_values("src").iloc[0], 100.0
        if hit is None and a.key:
            w = cand[(cand.year >= lo) & (cand.year <= hi)]
            sims = w.key.map(lambda k: fuzz.token_set_ratio(a.key, k))
            best = sims.max() if len(sims) else 0
            if best >= FUZZY_MIN:
                top = w[sims == best]
                if top.src_id.nunique() == 1 or top.label.map(norm).nunique() == 1:
                    rule, hit, score = 2, top.sort_values("src").iloc[0], float(best)
        rows.append({"call": a.call, "app_id": a.app_id, "applicant": a.applicant, "title": a.title,
                     "call_year": a.call_year, "rule": rule, "similarity": score,
                     "src": hit.src if hit is not None else "", "src_id": hit.src_id if hit is not None else "",
                     "matched_label": hit.label if hit is not None else "",
                     "matched_detail": hit.detail if hit is not None else "",
                     "release_year": int(hit.year) if hit is not None else None})
    links = pd.DataFrame(rows)
    links.to_csv(DATA / "links.csv", index=False)
    rng = random.Random(SEED)
    r1 = links[links.rule == 1]
    sample = r1.loc[sorted(rng.sample(list(r1.index), k=max(1, round(REVIEW_SHARE * len(r1)))))] if len(r1) else r1
    review = pd.concat([links[links.rule == 2], sample]).sort_values(["rule", "call"])
    review.assign(decision="", note="").to_csv(DATA / "review.csv", index=False)
    print(links.groupby("rule").size().rename({1: "exact", 2: "fuzzy", 3: "none"}).to_string())
    print(f"review sheet: {len(review)} links ({(review.rule == 2).sum()} fuzzy, {(review.rule == 1).sum()} exact sample)")


if __name__ == "__main__":
    main()
