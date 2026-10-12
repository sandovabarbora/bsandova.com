"""Registr smluv dumps → one row per contract, with the screening of design §4. Not run before registration.

    nice -n 20 uv run --with pandas==3.0.6 --with pyarrow==26.0.0 python tools/procurement/prepare.py

Writes tools/data/procurement/contracts.parquet and docs/research/procurement-bunching-screen.json (counts at each
screening step, over the whole value range; no count by value inside the analysis range).
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "procurement"
NS = "{http://portal.gov.cz/rejstriky/ISRS/1.2/}"
PRE = (date(2020, 1, 1), date(2024, 12, 31))
POST = (date(2025, 4, 3), date(2026, 6, 30))
# §4.3: subjects that are not purchases by the publishing authority (lower case, matched as substrings).
NOT_PURCHASE = ["dodatek", "dotac", "grant", "příspěvek", "příspěvku", "darovac", "nájem", "nájm", "pacht", "výpůjč",
                "úvěr", "zápůjč", "půjčk", "věcné břemen", "věcného břemen", "služebnost", "budoucí", "memorand",
                "o spolupráci", "partnersk", "prodej", "směnn", "veřejnoprávní smlouv", "finanční podpor",
                "poskytnutí podpory", "dohoda o provedení práce", "dohoda o pracovní činnosti", "pracovní smlouv"]
# §4.5, secondary only: a works contract by its subject.
WORKS = re.compile(r"stavb|stavební|rekonstrukc|výstavb|přístavb|nástavb|zateplen|demolic|kanalizac|vodovod|"
                   r"chodník|silnic|místní komunikac|pozemní komunikac")


def text(el, path: str) -> str | None:
    return el.findtext("/".join(f"{NS}{p}" for p in path.split("/")))


def records(path: Path):
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != f"{NS}zaznam":
            continue
        s = el.find(f"{NS}smlouva")
        subj = (text(s, "predmet") or "").lower()  # reduced to two flags below, so the table stays small
        yield {
            "id": text(el, "identifikator/idSmlouvy"), "version": text(el, "identifikator/idVerze"),
            "valid": text(el, "platnyZaznam") == "1", "published": text(el, "casZverejneni"),
            "concluded": text(s, "datumUzavreni"), "value": text(s, "hodnotaBezDph"),
            "value_vat": text(s, "hodnotaVcetneDph"), "no_price": s.find(f"{NS}cenaNeuvedena") is not None,
            "foreign": s.find(f"{NS}ciziMena") is not None,
            "linked": el.find(f"{NS}navazanyZaznam") is not None or s.find(f"{NS}navazanyZaznam") is not None,
            "excluded_subject": any(k in subj for k in NOT_PURCHASE),
            "works": bool(WORKS.search(subj)), "authority": text(s, "subjekt/ico"),
            "dump": path.name,
        }
        el.clear()


def main() -> None:
    rows = pd.DataFrame([r for p in sorted(DATA.glob("dump_20*.xml")) for r in records(p)])
    steps = {"records": len(rows)}
    rows = rows[rows["valid"]]
    steps["valid"] = len(rows)
    rows["version_n"] = pd.to_numeric(rows["version"], errors="coerce")
    rows = rows.sort_values("version_n").drop_duplicates("id", keep="last")
    steps["latest version per contract"] = len(rows)
    rows = rows[~rows["linked"]]
    steps["not linked to an earlier record (no amendment)"] = len(rows)
    rows = rows[~rows["foreign"] & ~rows["no_price"]]
    steps["CZK with a price"] = len(rows)
    rows["value"] = pd.to_numeric(rows["value"], errors="coerce")
    rows["value_vat"] = pd.to_numeric(rows["value_vat"], errors="coerce")
    steps["value without VAT present"] = int(rows["value"].gt(0).sum())
    steps["only value with VAT present (robustness R-VAT)"] = int((rows["value"].isna() & rows["value_vat"].gt(0)).sum())
    steps["subject excluded by §4.3"] = int(rows["excluded_subject"].sum())
    rows = rows[~rows["excluded_subject"]]
    d = pd.to_datetime(rows["concluded"].str[:10], errors="coerce").dt.date
    rows["period"] = None
    rows.loc[(d >= PRE[0]) & (d <= PRE[1]), "period"] = "pre"
    rows.loc[(d >= POST[0]) & (d <= POST[1]), "period"] = "post"
    steps["dated in pre"] = int((rows["period"] == "pre").sum())
    steps["dated in post"] = int((rows["period"] == "post").sum())
    rows = rows[rows["period"].notna()]
    rows[["id", "authority", "concluded", "period", "value", "value_vat", "works", "dump"]].to_parquet(
        DATA / "contracts.parquet", index=False)
    (ROOT / "docs" / "research" / "procurement-bunching-screen.json").write_text(json.dumps(steps, indent=1))
    print(json.dumps(steps, indent=1))


if __name__ == "__main__":
    main()
