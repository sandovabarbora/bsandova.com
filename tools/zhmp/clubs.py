"""Who was elected for which list, and which party each councillor belonged to: the crosswalk behind Part 1 extended.

Sources (downloaded into tools/data/zhmp/, not committed):
  - 2010, 2014, 2018: ČSÚ open data, municipal elections, candidate registers (kvrk: every candidate with list order,
    party membership PSTRANA and mandate) and list registers (kvros), Prague = KODZASTUP 554782.
    https://www.volby.cz/opendata/kv{year}/KV{year}_reg_20230224_csv.zip
  - 2022: the ČSÚ candidate page for Prague already used by votes.py (list, nominating party, membership).
A councillor is matched by surname + first name among all candidates of the Prague assembly (replacements come from
the same lists). Party membership "BEZPP" / 99 = no party.

Writes docs/research/prague-council-crosswalk.csv (published: which list and party every councillor is counted with).

Usage:
    uv run --with pandas python tools/zhmp/clubs.py
"""

import html
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from council import ALIASES, NAME_FIX, TERMS, load  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "zhmp"
OUT = ROOT / "docs" / "research" / "prague-council-crosswalk.csv"
PRAGUE = 554782
LIST_SHORT = {
    "Občanská demokratická strana": "ODS", "TOP 09": "TOP 09", "Česká strana sociálně demokratická": "ČSSD",
    "Komunistická strana Čech a Moravy": "KSČM", "ANO 2011": "ANO", "Česká pirátská strana": "Piráti",
    "PRAHA SOBĚ": "Praha sobě", "SPOLU pro Prahu": "SPOLU", "STAROSTOVÉ A NEZÁVISLÍ": "STAN",
    "SPD,Trik.,PES a nez. pro Prahu": "SPD",
}
PARTY_CODE = {53: "ODS", 721: "TOP 09", 7: "ČSSD", 47: "KSČM", 768: "ANO", 720: "Piráti", 166: "STAN", 1: "KDU-ČSL",
              5: "SZ", 99: "BEZPP"}


def list_short(name: str) -> str:
    if name.startswith("TROJKOALICE"):
        return "Trojkoalice"
    if "Spojené síly" in name:
        return "Spojené síly"
    return LIST_SHORT.get(name, name)


def register(year: str) -> pd.DataFrame:
    z = zipfile.ZipFile(RAW / f"kv{year}_reg.zip")
    rd = lambda f: pd.read_csv(io.BytesIO(z.read(f"csv/{f}.csv")), sep=";", encoding="cp1250")  # noqa: E731
    k, s = rd("kvrk"), rd("kvros")
    k, s = k[k.KODZASTUP == PRAGUE], s[s.KODZASTUP == PRAGUE]
    names = s.drop_duplicates("OSTRANA").set_index("OSTRANA").NAZEVCELK  # 2010 had several electoral districts
    k = k.assign(list=k.OSTRANA.map(names).map(list_short),
                 party=k.PSTRANA.map(lambda c: "unknown" if pd.isna(c) else PARTY_CODE.get(int(c), f"code {int(c)}")),
                 person=(k.PRIJMENI.str.strip() + " " + k.JMENO.str.strip().str.split(" ").str[0]),
                 elected=k.MANDAT == "A")
    return k[["person", "list", "party", "elected"]]


def register_2022() -> pd.DataFrame:
    s = (RAW / "candidates2022.html").read_text(encoding="utf-8")
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", s, re.S):
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) >= 9:
            words = [w for w in c[3].split() if not re.search(r"\.|^(MBA|MSc|PhD|CSc|DiS)$", w)]
            rows.append({"person": " ".join(words[:2]), "person3": " ".join(words[:3]),
                         "list": list_short(c[1]), "party": {"BEZPP": "BEZPP"}.get(c[6], c[6]),
                         "elected": c[-1] == "*"})
    return pd.DataFrame(rows)


def crosswalk() -> pd.DataFrame:
    out = []
    for term in TERMS:
        _, v = load(term)
        reg = register_2022() if term == "2022" else register(term)
        reg = reg[reg.list.isin(reg.loc[reg.elected, "list"])]  # replacements come from lists that won seats
        rev = {a: b for b, a in ALIASES.items()} | {b: a for a, b in NAME_FIX.items()}
        for p in v.columns:
            if p == "neurčeno":
                out.append({"term": term, "person": p, "list": "STAN", "party": "unknown", "match": "replacement "
                            "for Procházka David (STAN), votes.py"})
                continue
            keys = {p, rev.get(p, "")}
            cand = reg[reg.person.isin(keys) | (reg.person3.isin(keys) if "person3" in reg else False)]
            if cand.empty:  # double surnames in the register ("Teska Arnoštová Lenka"), spelling variants
                sur, first = p.rsplit(" ", 1)
                norm = lambda x: x.replace("ű", "ü").replace("Aleksandra", "Alexandra")  # noqa: E731
                cand = reg[reg.person.map(norm).map(lambda x: x.rsplit(" ", 1)[0].endswith(norm(sur))
                                                 and x.rsplit(" ", 1)[-1] == norm(first))]
                match_note = "surname suffix / spelling"
            else:
                match_note = ""
            if len(cand) > 1 and cand.elected.any():
                cand = cand[cand.elected]
            lists = cand.list.unique()
            match = ("unique" if len(cand) == 1 else f"{len(cand)} candidates") + (f", {match_note}" if match_note else "")
            if len(lists) != 1:
                out.append({"term": term, "person": p, "list": None, "party": None, "match": f"unresolved {list(lists)}"})
                continue
            out.append({"term": term, "person": p, "list": lists[0], "party": cand.party.iloc[0], "match": match})
    return pd.DataFrame(out)


def main() -> None:
    c = crosswalk()
    OUT.write_text(c.to_csv(index=False))
    print(c.groupby(["term", "list"]).size().unstack(0).fillna(0).astype(int))
    print(c[c.list.isna() | c.match.str.startswith("unres")])


if __name__ == "__main__":
    main()
