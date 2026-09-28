"""Classify ZHMP items by subject from their titles (Part 1 extended, H4). The dictionary is fixed here before any
title is joined to a vote outcome; its SHA-256 is written to the design file (Appendix B).

Rules: lowercase; leading boilerplate ("k návrhu na", "k ", ...) stripped; regex stems for Czech inflection; the first
category in PRECEDENCE whose pattern matches wins; revocations are classified by the rest of the title.

Usage:
    uv run --with pandas python tools/zhmp/topics.py            # counts per term and category (titles only)
"""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "zhmp"
PRECEDENCE = ["planning", "regulation", "budget", "property", "grants", "appointments", "companies",
              "organisational", "strategy", "other"]
DICTIONARY = {
    "planning": [r"územní\w* plán", r"\búp\b", r"\búp sú", r"metropolitní\w* plán", r"změn\w* (z[- ]?\d+|č\.)",
                 r"\bvln\w* \d+", r"úprav\w* úp", r"zadání\w* změn", r"pořízení\w* změn", r"celoměstsky významn",
                 r"zásad\w* územního rozvoje", r"\bzúr\b", r"aktualizac\w* zúr", r"územní\w* studi",
                 r"regulační\w* plán", r"stavební\w* uzávěr", r"územně analytick"],
    "regulation": [r"obecně závazn\w* vyhlášk", r"\bozv\b", r"\bnařízení\b", r"(změn|doplň)\w*[^,]{0,40}statut",
                   r"návrh\w* zákona", r"zákonodárn\w* iniciativ"],
    "budget": [r"rozpoč", r"závěrečn\w* účt", r"střednědob\w* výhled", r"\búvěr", r"zápůjčk", r"půjčk",
               r"dluhopis", r"návratn\w* finanční\w* výpomoc", r"přezkum\w* hospodaření", r"finanční\w* vypořádání",
               r"\bkapitol\w* \d{3,4}", r"nevyčerpan\w* finančn", r"\bdaň", r"\bdaně\b", r"daňov"],
    "property": [r"pozem", r"parc\.? ?č", r"k\.? ?ú\.", r"(bez)?úplatn\w* (převod|nabyt)", r"\bnabyt", r"prodej",
                 r"směn", r"koupě", r"výkup", r"vyvlastn", r"služebnost", r"věcn\w* břemen", r"předkupn\w* práv",
                 r"nájem", r"nájm", r"pacht", r"svěř", r"nepeněžit\w* vklad", r"majetkoprávn", r"bytov\w* jednot",
                 r"vodovod", r"kanalizac", r"plynárensk\w* zaříz", r"vlastnick\w* práv", r"darovac", r"darován",
                 r"správ\w* majetku", r"práv\w* stavby"],
    "grants": [r"dotac", r"grant", r"finanční\w* podpor", r"účelov\w* finanční\w* prostředk", r"přidělení\w* finančních prostředků", r"finanční\w* dar", r"program\w* partnerství",
               r"stipendi", r"operační\w* program", r"příspěv(?!\w* organizac)"],
    "appointments": [r"personální\w* změn", r"\bvolb", r"\bvolí", r"zvolen", r"odvolán", r"jmenován", r"přísed", r"člen\w* (rady|výboru|komise|dozorčí)",
                     r"předsed\w* výboru", r"náměst(ek|k|kyn|ci)", r"primátor(a|em|ovi)?\b", r"valn\w* hromad", r"zástupc\w* hl\.? ?m"],
    "companies": [r"technick\w* správ\w* komunikac", r"dopravní\w* podnik", r"\bdpp\b", r"\btsk\b", r"\bpvs\b",
                  r"pražsk\w* (plynárensk|služb|vodohospodář)", r"operátor ict", r"kolektor", r"ropid",
                  r"založení\w* (obchodní\w* )?společnost", r"technologie hlavního města", r"letiště praha",
                  r"pražská energetika|\bpre\b", r"městsk\w* (firm|společnost)"],
    "organisational": [r"zřizovací\w* listin", r"příspěvkov\w* organizac", r"\bstanov", r"jednací\w* řád",
                       r"zpráv\w* o (činnosti|plnění)", r"\binformac", r"oprav\w* usnesení", r"technick\w* chyb",
                       r"odměn", r"delegov", r"inventarizac", r"aktuální\w* stav", r"stavu (projektu|administrace|přípravy|realizace)", r"členství v", r"revokac"],
    "strategy": [r"strategi", r"koncepc", r"plán\w* udržitelné mobility", r"klimatick", r"petic", r"memorand"],
}
BUDGET_AMENDMENT = r"úprav\w* rozpočt|rozpočtov\w* opatřen|návrh\w* rozpočtu|rozpoč\w* hl\w*\.? ?m\w*\.? prahy na rok"
BOILERPLATE = re.compile(r"^\s*(k návrhům? na|k návrhu|ke|k)\s+")


def classify(title: str) -> str:
    t = BOILERPLATE.sub("", str(title).lower().strip())
    t = re.sub(r"^revokac\w*\s+(usnesení\s+)?", "", t) if not re.match(r"^revokac\w* usnesení zastupitelstva$", t) else t
    # budget amendments are budget even when they also grant money; other grants beat the generic budget stems
    if re.search(BUDGET_AMENDMENT, t):
        return "budget"
    order = [c for c in PRECEDENCE[:-1] if c != "grants"]
    order.insert(order.index("budget"), "grants")
    for cat in order:
        if any(re.search(p, t) for p in DICTIONARY[cat]):
            return cat
    return "other"


def digest() -> str:
    blob = json.dumps({"precedence": PRECEDENCE, "dictionary": DICTIONARY, "boilerplate": BOILERPLATE.pattern,
                       "budget_amendment": BUDGET_AMENDMENT},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def titles() -> pd.DataFrame:
    rows = []
    for term, sep in [("2010", ";"), ("2014", ";"), ("2018", ",")]:
        d = pd.read_csv(RAW / f"votes{term}.csv", sep=sep, encoding="utf-8-sig", dtype=str, keep_default_na=False,
                        usecols=lambda c: c.strip() in ("cislousneseni", "cislotisku", "nazevtisku", "datumcas"))
        d.columns = [c.strip() for c in d.columns]
        d = d[d.datumcas != ""]
        rows.append(pd.DataFrame({"term": term, "cislousneseni": d.cislousneseni, "title": d.nazevtisku}))
    t = pd.read_csv(RAW / "titles2022.csv", dtype=str, keep_default_na=False)
    rows.append(pd.DataFrame({"term": "2022", "cislousneseni": t.cislousneseni, "title": t.title}))
    out = pd.concat(rows, ignore_index=True)
    out["category"] = out.title.map(classify)
    return out


def main() -> None:
    t = titles()
    print("dictionary sha256", digest())
    print(pd.crosstab(t.category, t.term, margins=True))


if __name__ == "__main__":
    main()
