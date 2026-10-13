"""Registered keyword stems on the contract subject (design §4), shared by structure.py and prepare.py.

All stems are lower-case substrings of the lower-cased `predmet`. They were written without reading any subject.
"""
import re

# §4.5: not a purchase by the publishing authority.
NOT_PURCHASE = ["dodatk", "dotac", "grant", "příspěvek", "příspěvku", "darovac", "nájem", "nájm", "pacht", "výpůjč",
                "úvěr", "zápůjč", "půjčk", "věcné břemen", "věcného břemen", "služebnost", "budoucí", "memorand",
                "o spolupráci", "partnersk", "prodej", "směnn", "veřejnoprávní smlouv", "finanční podpor",
                "poskytnutí podpory", "dohoda o provedení práce", "dohoda o pracovní činnosti", "pracovní smlouv"]
# §4.6: contracts whose recorded price is not the price of one award.
FRAMEWORK = ["rámcov"]
CALL_OFF = ["objednávk", "objednávka"]
PERIODIC = ["za měsíc", "měsíčn", "za rok", "ročn", "paušál", "hodinov"]
# §4.7, secondary only: a works contract by its subject.
WORKS = re.compile(r"stavb|stavební|rekonstrukc|výstavb|přístavb|nástavb|zateplen|demolic|kanalizac|vodovod|"
                   r"chodník|silnic|místní komunikac|pozemní komunikac")


def flags(subject: str) -> dict[str, bool]:
    s = subject.lower()
    return {"not_purchase": any(k in s for k in NOT_PURCHASE), "framework": any(k in s for k in FRAMEWORK),
            "call_off": any(k in s for k in CALL_OFF), "periodic": any(k in s for k in PERIODIC),
            "works": bool(WORKS.search(s))}


def stem_hits(subject: str) -> list[str]:
    s = subject.lower()
    return [k for k in (*NOT_PURCHASE, *FRAMEWORK, *CALL_OFF, *PERIODIC) if k in s] + (
        ["WORKS"] if WORKS.search(s) else [])
