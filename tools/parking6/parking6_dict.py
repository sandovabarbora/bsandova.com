"""Part 6, DS12: the frozen model-line normalisation dictionary. It uses names and counts only; no dimension is read.

The same key function is applied to EEA (Mk, Cn) and to RSV (Tovární značka, Obchodní označení, falling back to Typ).
It writes `tools/data/parking6/dict_model_lines.csv` and the match report into `docs/research/prague-parking-ds.json`
(key "ds12"). The dictionary's hash is recorded there and in the freeze commit.

    uv run --no-project --with pyarrow --with pandas python tools/parking6/parking6_dict.py
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")
DS = ROOT / "docs/research/prague-parking-ds.json"
DICT = RAW / "dict_model_lines.csv"

MULTI = {"ALFA ROMEO": "ALFA ROMEO", "LAND ROVER": "LAND ROVER", "MERCEDES BENZ": "MERCEDES", "ROLLS ROYCE": "ROLLS ROYCE",
         "ASTON MARTIN": "ASTON MARTIN", "LYNK CO": "LYNK", "GREAT WALL": "GREAT WALL"}
MAKE_ALIAS = {"VW": "VOLKSWAGEN", "MERCEDESBENZ": "MERCEDES", "MERCEDES-BENZ": "MERCEDES", "MINI": "MINI",
              "BMW I": "BMW", "CITROËN": "CITROEN", "DS AUTOMOBILES": "DS", "MG ROVER": "MG"}


def norm(s: str | None) -> str:
    t = unicodedata.normalize("NFKD", (s if isinstance(s, str) else "").upper())
    t = "".join(c for c in t if not unicodedata.combining(c)).replace("?KODA", "SKODA")
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def make_key(make: str | None) -> str:
    m = norm(make)
    for k, v in MULTI.items():
        if m.startswith(k):
            return v
    first = m.split(" ")[0] if m else ""
    return MAKE_ALIAS.get(m, MAKE_ALIAS.get(first, first))


def line_key(make_c: str, name: str | None, typ: str | None = None) -> str:
    n = norm(name)
    for tok in (make_c, *make_c.split(" ")):
        if tok and n.startswith(tok + " "):
            n = n[len(tok) + 1:]
    toks = [t for t in n.split(" ") if t]
    if not toks:
        toks = [t for t in norm(typ).split(" ") if t]
    if not toks:
        return "?"
    t = toks[0]
    if make_c == "BMW" and re.fullmatch(r"\d{3}[A-Z]{0,3}", t):
        return t[0] + "ER"
    if make_c == "MERCEDES":
        m = re.fullmatch(r"([A-Z]{1,3})\d+[A-Z]*", t)
        if m:
            return m.group(1)
    return t


def main() -> None:
    eea = pd.read_csv(RAW / "eea_cz_by_model_m1_m1g.csv", usecols=["Year", "Mk", "Cn", "regs"])
    e23 = pd.read_csv(RAW / "eea_cz_counts_2023_2025_m1_m1g.csv", usecols=["Year", "Mk", "Cn", "regs"])
    eea = pd.concat([eea, e23])
    eea = eea[(eea.Year >= 2012) & (eea.Year <= 2025)]
    eea["make_c"] = eea.Mk.map(make_key)
    eea["line"] = [line_key(m, c) for m, c in zip(eea.make_c, eea.Cn)]

    t = pq.read_table(RAW / "rsv_m1n1_20260901.parquet", columns=["cat", "make", "obch", "typ", "rv", "y1", "ycz"]).to_pandas()
    t = t[t.cat.isin(["M1", "M1G"]) & t.ycz.between(2012, 2025)]
    t["new_cz"] = (t.y1 == t.ycz) & (t.rv.isna() | (t.rv >= t.ycz - 1))
    names = t.groupby(["make", "obch", "typ"], dropna=False).size().reset_index(name="n")
    names["make_c"] = names.make.map(make_key)
    names["line"] = [line_key(m, o, ty) for m, o, ty in zip(names.make_c, names.obch, names.typ)]

    d = pd.concat([
        eea.groupby(["Mk", "Cn", "make_c", "line"]).regs.sum().reset_index().rename(columns={"Mk": "raw_make", "Cn": "raw_name", "regs": "n"}).assign(source="EEA", raw_typ=""),
        names.rename(columns={"make": "raw_make", "obch": "raw_name", "typ": "raw_typ"}).assign(source="RSV"),
    ])[["source", "raw_make", "raw_name", "raw_typ", "make_c", "line", "n"]]
    d.to_csv(DICT, index=False)
    h = hashlib.sha256(DICT.read_bytes()).hexdigest()

    # match report (counts only): EEA weight whose (make_c, line, year) has RSV new-to-CZ entries
    rs = t[t.new_cz].merge(names[["make", "obch", "typ", "make_c", "line"]], on=["make", "obch", "typ"], how="left")
    have = set(zip(rs.make_c, rs.line, rs.ycz))
    have_make = set(zip(rs.make_c, rs.ycz))
    rep = {}
    for y, g in eea.groupby("Year"):
        w = g.regs.sum()
        ok = sum(r for m, l, r in zip(g.make_c, g.line, g.regs) if (m, l, int(y)) in have)
        okm = sum(r for m, r in zip(g.make_c, g.regs) if (m, int(y)) in have_make)
        rep[str(int(y))] = {"eea_regs": int(w), "matched_line_share": round(ok / w, 4), "matched_make_share": round(okm / w, 4)}
    res = json.loads(DS.read_text())
    res["ds12"] = {"dict_file": DICT.name, "sha256": h, "rows": len(d), "eea_lines": int(eea.groupby(["make_c", "line"]).ngroups),
                   "match_by_year": rep, "rule": "matched_line_share < 0.80 in a year -> that year uses make × year cells",
                   "years_falling_back": [y for y, v in rep.items() if v["matched_line_share"] < 0.80]}
    DS.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res["ds12"], indent=1))


if __name__ == "__main__":
    main()
