"""Prague City Assembly (ZHMP) roll-call votes, 2022-2026: who votes with whom.

Sources (downloaded into tools/data/zhmp/, not committed):
  - Výsledky hlasování ZHMP 2022-2026, Prague open data (lkod.cz catalogue, MHMP):
    https://storage.golemio.cz/ckan/obis/Vysledky_hlasovani_ZHMP_2022_-_2026.csv
    One row per vote, one column per member with his or her vote. Per the dataset's documentation it holds votes
    on substantive items only (no agenda or ad hoc procedural votes), and in practice one final vote per
    resolution: rejected proposals and amendments are almost absent.
  - Candidate lists, municipal elections 2022, Prague (volby.cz, ČSÚ): the list each member was elected from.

Club = the candidate list a member was elected from, checked against the clubs on praha.eu/seznam-zastupitelu
(its API gives each member's current club only). One member differs: Hana Kordová Marvanová, elected for SPOLU,
was expelled from the SPOLU club on 17 February 2023 and sits as non-affiliated ("Nezařazení"); she is counted
on her own for the whole term, so her votes never move SPOLU's position. A replacement takes a vacant seat from the same list
(zákon 491/2001 Sb., § 56), so the dataset's unnamed column "neurčeno", which votes from April 2025, after
David Procházka (STAN) left in March 2025, is counted with STAN.

A club's position on a vote: yes if more than half of its members present ("Hlas pro", "Hlas proti",
"Zdržel se", "Nehlasoval") voted "Hlas pro"; missing if none was present. "Chyběl" (absent) is not present.

Usage:
    uv run --with pandas python tools/zhmp/votes.py
"""

import html
import json
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "zhmp"
OUT = ROOT / "assets" / "zhmp" / "votes2022.json"
VOTES_URL = "https://storage.golemio.cz/ckan/obis/Vysledky_hlasovani_ZHMP_2022_-_2026.csv"
CANDIDATES_URL = (
    "https://volby.gov.cz/pls/kv2022/kv21111?xjazyk=CZ&xid=1&xv=11&xdz=4&xnumnuts=1100&xobec=554782&xstrana=0"
)
PRESENT = ["Hlas pro", "Hlas proti", "Zdržel se", "Nehlasoval"]
SHORT = {
    "SPOLU pro Prahu": "SPOLU",
    "Česká pirátská strana": "Piráti",
    "STAROSTOVÉ A NEZÁVISLÍ": "STAN",
    "PRAHA SOBĚ": "Praha sobě",
    "ANO 2011": "ANO",
    "SPD,Trik.,PES a nez. pro Prahu": "SPD",
    "Nezařazení": "Nezařazená",
}
COALITION = ["SPOLU", "Piráti", "STAN"]  # agreement signed 15 February 2023
# names that differ between the vote file and the candidate list, or occur on more than one list;
# resolved by hand against the candidate list (elected candidates are marked "*")
OVERRIDES = {
    "Freitas Zuzana": "Česká pirátská strana",  # on the list as Freitas Lopesová Zuzana
    "Marvanová Hana": "Nezařazení",  # elected for SPOLU as Kordová Marvanová Hana; expelled from its club 17 Feb 2023
    "Mareš Pavel": "SPOLU pro Prahu",  # elected; a namesake ran for KONS
    "Zeman Petr": "PRAHA SOBĚ",  # elected; namesakes ran for SPOLU (not elected) and KSČM
    "neurčeno": "STAROSTOVÉ A NEZÁVISLÍ",  # unnamed replacement for Procházka David (STAN), see above
}


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "bsandova.com research"})
        path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    return path


def name_key(name: str) -> str:
    """'Mareš  Pavel Mgr.' -> 'mareš pavel': surname and first name without degrees."""
    words = [w for w in re.split(r"[\s,]+", name) if w and not re.search(r"\.|^(MBA|MSc|PhD|CSc|DiS)$", w)]
    return " ".join(words[:2]).lower()


def candidate_lists(path: Path) -> dict[str, list[str]]:
    rows = {}
    s = path.read_text(encoding="utf-8")
    for tr in re.findall(r"<tr>(.*?)</tr>", s, re.S):
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) >= 9:
            rows.setdefault(name_key(c[3]), []).append(c[1])
    return rows


def clubs(members: list[str], cands: dict[str, list[str]]) -> dict[str, str]:
    over = {name_key(k) if k != "neurčeno" else k: v for k, v in OVERRIDES.items()}
    out = {}
    for m in members:
        k = "neurčeno" if m == "neurčeno" else name_key(m)
        lists = [over[k]] if k in over else cands.get(k, [])
        if len(lists) != 1:
            raise ValueError(f"no single candidate list for {m!r}: {lists}")
        out[m] = SHORT[lists[0]]
    return out


def positions(d: pd.DataFrame, club: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    yes, pos = {}, {}
    for c in SHORT.values():
        ms = [m for m in club if club[m] == c]
        present = d[ms].isin(PRESENT).sum(axis=1)
        share = (d[ms] == "Hlas pro").sum(axis=1) / present.replace(0, np.nan)
        yes[c], pos[c] = share, (share > 0.5).where(share.notna())
    return pd.DataFrame(pos), pd.DataFrame(yes)


def agreement(p: pd.DataFrame, a: str, b: str) -> float:
    both = p[a].notna() & p[b].notna()
    return float((p.loc[both, a] == p.loc[both, b]).mean())


def main() -> None:
    d = pd.read_csv(fetch(VOTES_URL, RAW / "votes2022.csv"))
    d.columns = [c.strip() for c in d.columns]
    empty = int(d.datumcas.isna().sum())
    d = d[d.datumcas.notna()].copy()
    d["t"] = pd.to_datetime(d.datumcas)
    members = list(d.columns[17:-1])
    club = clubs(members, candidate_lists(fetch(CANDIDATES_URL, RAW / "candidates2022.html")))
    p, y = positions(d, club)
    names = list(SHORT.values())

    counted = (d[members] == "Hlas pro").sum(axis=1)
    checks = {
        "rows_dropped_empty": empty,
        "votes": len(d),
        "share_rows_yes_count_matches": round(float((counted == d.pocetpro).mean()), 4),
        "rows_yes_count_short_by": {int(k): int(v) for k, v in (d.pocetpro - counted).value_counts().items()},
        "short_rows_from": str(d.loc[counted != d.pocetpro, "t"].min().date()),
        "votes_per_resolution_max": int(d.groupby("cislousneseni").size().max()),
        "votes_failed": int((d.pocetpro < 33).sum()),
    }
    values = d[members].stack().value_counts()
    q = d.t.dt.to_period("Q").astype(str)
    out = {
        "source": VOTES_URL,
        "term": "2022-2026",
        "from": str(d.t.min().date()),
        "to": str(d.t.max().date()),
        "sessions": int(d.datumjednani.nunique()),
        "checks": checks,
        "seats_by_club": pd.Series(club).value_counts().to_dict(),
        "vote_values": {k: int(v) for k, v in values.items()},
        "agreement": {a: {b: round(agreement(p, a, b), 3) for b in names} for a in names},
        "yes_share_present": {c: round(float(y[c].mean()), 3) for c in names},
        "agreement_with_spolu_by_quarter": {
            k: {c: round(agreement(g, c, "SPOLU"), 3) for c in names if c != "SPOLU"} | {"votes": len(g)}
            for k, g in p.groupby(q)
        },
        "coalition": COALITION,
    }
    # members against their own club: votes where the member was present and his vote (yes / not yes)
    # differed from the club's position
    rebels = []
    for m, c in club.items():
        present = d[m].isin(PRESENT) & p[c].notna()
        yes = d[m] == "Hlas pro"
        n = int(present.sum())
        if n >= 100:
            rebels.append(
                {"member": re.sub(r"\s+", " ", m).strip(), "club": c, "votes": n,
                 "against_club": round(float((yes[present] != p.loc[present, c]).mean()), 3)}
            )
    out["rebels"] = sorted(rebels, key=lambda r: -r["against_club"])
    # how each club says no: shares of its members' non-yes votes while present
    out["how_clubs_say_no"] = {
        c: {v: round(float(s), 3) for v, s in d[[m for m in club if club[m] == c]].stack()
            .loc[lambda x: x.isin(PRESENT[1:])].value_counts(normalize=True).items()}
        for c in names
    }
    # every councillor: what they did while seated (a cell is empty when the member did not hold the seat)
    members = []
    for m, c in club.items():
        seated = d[m].notna()
        v = d.loc[seated, m]
        present = v.isin(PRESENT)
        both = present & p.loc[seated, c].notna()
        yes = v == "Hlas pro"
        members.append({
            "name": re.sub(r"\s+", " ", m).strip(),
            "club": c,
            "first": str(d.loc[seated, "t"].min().date()),
            "last": str(d.loc[seated, "t"].max().date()),
            "seated_votes": int(seated.sum()),
            "attendance": round(float(present.mean()), 3),
            "yes": round(float((v[present] == "Hlas pro").mean()), 3),
            "no_vote": round(float((v[present] == "Nehlasoval").mean()), 3),
            "abstained": int((v == "Zdržel se").sum()),
            "against": int((v == "Hlas proti").sum()),
            "with_club": round(float((yes[both] == p.loc[seated, c][both]).mean()), 3) if c != "Nezařazená" else None,
            "with_spolu": round(float((yes[present & p.loc[seated, "SPOLU"].notna()]
                                       == p.loc[seated, "SPOLU"][present & p.loc[seated, "SPOLU"].notna()]).mean()), 3),
        })
    (OUT.parent / "members2022.json").write_text(json.dumps(members, ensure_ascii=False, indent=0) + "\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(checks, ensure_ascii=False))
    print(pd.DataFrame(out["agreement"]).round(2).to_string())


if __name__ == "__main__":
    main()
