"""Prague City Assembly roll calls, 2010-2026: one loader for Part 1 extended (docs/research/prague-council-design.md).

Rules from the design (§3), all decided before any vote outcome was modelled:
  - explicit separator per file, utf-8-sig, text dtype; members are every column after the 17 metadata columns;
  - a row is a resolution with its final roll call; rows with no roll call are dropped (and counted); rows flagged
    "technická chyba" and the two rows whose totals disagree beyond missing seats are excluded; rows whose roll call
    predates the resolution's session and rows marked as repeat / procedural / amendment votes are flagged;
  - datumcas parsed with an explicit format per term; a sitting is a cluster of roll-call times separated by > 10 h;
  - present = hlas pro / hlas proti / zdržel se / nehlasoval; empty = not seated; passed = pocetpro >= 33;
  - identity = surname + first name (double-space rule), with the hand exceptions below.

Usage (design-stage structure report, no vote outcomes):
    uv run --with pandas python tools/zhmp/council.py
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "zhmp"
TERMS = {"2010": (";", "%d.%m.%Y %H:%M"), "2014": (";", "%d.%m.%Y %H:%M"), "2018": (",", "ISO8601"),
         "2022": (",", "ISO8601")}
PRESENT = ["Hlas pro", "Hlas proti", "Zdržel se", "Nehlasoval"]
ABSENT = "Chyběl"
EXCLUDE = {("2014", "1/2"), ("2022", "17/56")}  # totals disagree with the cells beyond missing seats
NAME_FIX = {"Dientsbier Jiří": "Dienstbier Jiří", "Bonhomme Hankeová Zuzana": "Bonhomme Hankeová Zuzana"}
ALIASES = {"Marvanová Hana": "Kordová Marvanová Hana", "Freitas Zuzana": "Freitas Lopesová Zuzana"}
UNVERIFIED_LINKS = [("Kloudová Gabriela", "Lněničková Gabriela"), ("Vorlíčková Eva", "Tylová Eva")]
FLAG = re.compile(r"opakovan|druhé hlasování|procedur|pozměňovac|zmatečn|opakovat", re.I)


def person(col: str) -> str:
    """'Surname␣␣First Degrees' -> 'Surname First'."""
    c = col.replace("\n", " ").strip()
    if c.startswith("Bonhomme Hankeová"):
        return "Bonhomme Hankeová Zuzana"
    if c == "neurčeno":
        return c
    parts = re.split(r"\s{2,}", c)
    surname, rest = parts[0].strip(), (parts[1] if len(parts) > 1 else "").strip()
    name = f"{surname} {rest.split(' ')[0]}".strip()
    name = NAME_FIX.get(name, name)
    return ALIASES.get(name, name)


def load(term: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(meta, votes): meta has one row per roll call; votes is roll calls x people with the cell values."""
    sep, fmt = TERMS[term]
    d = pd.read_csv(RAW / f"votes{term}.csv", sep=sep, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    d.columns = [c.strip() for c in d.columns]
    meta_cols, members = list(d.columns[:17]), list(d.columns[17:])
    d = d[d.datumcas.str.strip() != ""].copy()
    d["t"] = pd.to_datetime(d.datumcas.str.strip(), format=fmt)
    d["session_date"] = pd.to_datetime(d.datumjednani.str.split(" ").str[0], format="%d.%m.%Y")
    d = d.sort_values(["t", "poradi"]).reset_index(drop=True)
    for c in ["pocetpro", "pocetproti", "pocetzdrzel"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["sitting"] = (d.t.diff() > pd.Timedelta(hours=10)).cumsum()
    d["legal_session"] = d.cislousneseni.str.split("/").str[0]
    d["passed"] = d.pocetpro >= 33
    d["technical_error"] = d.kbodu.str.contains("technická chyba", case=False)
    d["excluded"] = d.technical_error | d.cislousneseni.map(lambda u: (term, u) in EXCLUDE).astype(bool)
    d["flag_early"] = d.t < d.session_date - pd.Timedelta(days=1)
    d["flag_kind"] = d.kbodu.str.contains(FLAG)
    d["council"] = d.predkladatel.str.strip().str.lower().isin({"rada hmp", "rada hl. m. prahy", "rada hl.m. prahy"})
    d["term"] = term
    v = d[members].copy()
    v.columns = [person(c) for c in members]
    if v.columns.duplicated().any():
        raise ValueError(f"{term}: duplicate people {list(v.columns[v.columns.duplicated()])}")
    meta = d[[c for c in d.columns if c not in members]].drop(columns=[c for c in meta_cols if c in (
        "orgjednotka", "volobd", "pritomno", "nepritomno")])
    return meta, v


def seats(v: pd.DataFrame) -> pd.DataFrame:
    """Seat period per person: first and last roll call with a non-empty cell, and seated votes."""
    s = v != ""
    return pd.DataFrame({"first": s.idxmax(), "last": s[::-1].idxmax(), "seated": s.sum()})


def structure() -> dict:
    out, people = {}, {}
    for term in TERMS:
        meta, v = load(term)
        st = seats(v)
        people[term] = st[st.seated >= 300].index.tolist()
        out[term] = {"roll_calls": len(meta), "excluded": int(meta.excluded.sum()),
                     "flag_early": int(meta.flag_early.sum()), "flag_kind": int(meta.flag_kind.sum()),
                     "sittings": int(meta.sitting.nunique()), "legal_sessions": int(meta.legal_session.nunique()),
                     "people": int(v.shape[1]), "people_300_seated": len(people[term]),
                     "council_proposed_share": round(float(meta.council.mean()), 3)}
    terms = list(TERMS)
    pairs = {f"{a}->{b}": sorted(set(people[a]) & set(people[b]) - {"neurčeno"}) for a, b in zip(terms, terms[1:])}
    out["h1_transitions"] = {k: len(v_) for k, v_ in pairs.items()}
    out["h1_persons"] = len(set().union(*pairs.values()))
    out["h1_pairs"] = pairs
    return out


if __name__ == "__main__":
    s = structure()
    print(json.dumps({k: v for k, v in s.items() if k != "h1_pairs"}, ensure_ascii=False, indent=1))
    (RAW / "structure.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
