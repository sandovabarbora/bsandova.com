"""Part 3 extended, the treatment: which districts were governed by a party of the city coalition, and when
(docs/research/prague-districts-design.md, §4). Covariates only; no budget or grant file is read.

Inputs (tools/data/praha3x/, not committed):
  - alignment/coder_A.csv, alignment/coder_B.csv: two independent, blind hand codings of every mayoral spell in the
    57 districts from the 2014 constituent sessions to September 2026, with sources (one row per spell).
  - kv2014/, kv2018/, kv2022/: ČSÚ candidate registers, for the parties that nominated the elected mayor and for
    the mechanical seat-based variants.
  - mc_ico.csv, mc_pop.xlsx: district names, tier and population.

Rules (registered):
  - City coalition C(d), by date d: 26 Nov 2014 - 14 Nov 2018 ANO, ČSSD, SZ, KDU-ČSL, STAN (10 Nov 2015 - 27 Apr 2016
    flagged as the interregnum, same parties); 15 Nov 2018 - 15 Feb 2023 Piráti, Praha Sobě, TOP 09, STAN, KDU-ČSL;
    from 16 Feb 2023 ODS, TOP 09, KDU-ČSL, Piráti, STAN.
  - Primary alignment A(i, d) = 1 if district i's mayor on date d is a member of a party in C(d), or, if a member of
    no party, was nominated by one (candidate register NSTRANA). Local lists and independents on them are not
    aligned.
  - The regime-year r runs 1 Jan - 31 Dec, except that 15 Nov - 31 Dec 2018 belongs to r = 2019 and 1 Jan - 15 Feb
    2023 to r = 2022; A(i, r) is A on 30 June of r.
  - Mechanical variants from the registers: seat majority of candidates whose NSTRANA or PSTRANA is in C;
    the largest list contains a coalition party; the continuous aligned seat share.

Writes:
  - tools/data/praha3x/alignment/frozen.csv (reconciled spells, with names) and its SHA-256;
  - docs/research/prague-districts-alignment.csv (the same without names), panel and event counts in
    docs/research/prague-districts-alignment.json.

Usage:
    uv run --with pandas --with openpyxl python tools/praha/districts_alignment.py
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import hashlib
import io
import json
import os
import re
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get("PRAHA3X", ROOT / "tools" / "data" / "praha3x"))
DOCS = ROOT / "docs" / "research"
YEARS = list(range(2015, 2026))
COALITIONS = [  # (from, to inclusive, parties)
    ("2014-11-26", "2018-11-14", {"ANO", "ČSSD", "SZ", "KDU-ČSL", "STAN"}),
    ("2018-11-15", "2023-02-15", {"Piráti", "PRAHA SOBĚ", "TOP 09", "STAN", "KDU-ČSL"}),
    ("2023-02-16", "2099-12-31", {"ODS", "TOP 09", "KDU-ČSL", "Piráti", "STAN"}),
]
INTERREGNUM = ("2015-11-10", "2016-04-27")
EVENTS = {"2018": (2018, 2019), "2023": (2022, 2023)}
PARTY_CODES = {1: "KDU-ČSL", 5: "SZ", 7: "ČSSD", 47: "KSČM", 53: "ODS", 166: "STAN", 720: "Piráti", 721: "TOP 09",
               768: "ANO", 1114: "SPD", 1180: "PRAHA SOBĚ", 99: "BEZPP"}
PATTERNS = [  # free-text party names in the codings -> canonical
    (r"praha\s*sob", "PRAHA SOBĚ"), (r"pir[aá]t", "Piráti"), (r"top\s*0?9", "TOP 09"), (r"\bods\b", "ODS"),
    (r"kdu", "KDU-ČSL"), (r"\bstan\b|starostov", "STAN"), (r"čssd|cssd|socdem|sociáln", "ČSSD"),
    (r"\bano\b", "ANO"), (r"\bsz\b|zelen", "SZ"), (r"\bspd\b", "SPD"), (r"kscm|kšcm|komunist", "KSČM"),
    (r"bez\s*pp|bezpp|nestran|non-?member|independent|none", "BEZPP"),
]
REGISTERS = {2014: "kv2014/KV2014_reg_20230224_csv.zip", 2018: "kv2018/KV2018_reg_20230224_csv.zip",
             2022: "kv2022/KV2022reg20260328_csv.zip"}


def party(text) -> str | None:
    t = str(text).lower()
    for pat, name in PATTERNS:
        if re.search(pat, t):
            return name
    return None


def coalition(day: str) -> set[str]:
    return next(p for a, b, p in COALITIONS if a <= day <= b)


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def registers() -> pd.DataFrame:
    out = []
    for year, f in REGISTERS.items():
        z = zipfile.ZipFile(RAW / f)
        rk = pd.read_csv(io.BytesIO(z.read("csv_od/kvrk.csv")))
        rk = rk[(rk.OKRES == 1100) & (rk.MANDAT == "A")]
        out.append(rk.assign(term=year, surname=rk.PRIJMENI.map(fold), first=rk.JMENO.map(fold)))
    return pd.concat(out)


def spells(path: Path) -> pd.DataFrame:
    s = pd.read_csv(path, dtype=str).fillna("")
    s["district"] = s.district.str.strip().str.replace(r"\s*-\s*", "-", regex=True)
    s["vacant"] = s.mayor_name.str.lower().str.startswith(("vacant", "vacancy"))
    s["member"] = s.mayor_party_member.map(party)
    s["nominated"] = s.mayor_nominated_by.map(party)
    s["spell_end"] = s.spell_end.replace("", "2099-12-31")
    return s


def mayor_on(s: pd.DataFrame, district: str, day: str) -> pd.Series | None:
    """The mayoral spell covering the day. A vacancy carries the last mayor's party (registered rule): the rada
    elected with that mayor stays in office until a new mayor is elected."""
    d = s[s.district == district].sort_values("spell_start")
    m = d[(d.spell_start <= day) & (d.spell_end >= day)]
    if not len(m):
        return None
    row = m.iloc[-1]
    if row.vacant:
        before = d[(d.spell_start < row.spell_start) & ~d.vacant]
        return before.iloc[-1] if len(before) else None
    return row


def surname(row) -> str | None:
    names = re.sub(r"\(.*?\)|,.*$", "", str(row.mayor_name)).split() if row is not None else []
    names = [n for n in names if not re.fullmatch(r"(?i)(ing|mgr|bc|judr|mudr|phdr|rndr|doc|prof|ph\.?d|mba)\.?", n)]
    return fold(names[-1]) if names else None


def register_party(row, reg: pd.DataFrame, code: int, day: str) -> str | None:
    """The mayor's party from the candidate register of the assembly in force: membership (PSTRANA) at candidacy,
    or, for a non-member, the nominating party (NSTRANA). 'LOCAL' for a local list or movement; None if the mayor
    is not found among the elected (flagged for adjudication)."""
    if row is None:
        return None
    seats = in_force(reg[(reg.KODZASTUP == code) & (reg.term == int(row.term))], int(day.replace("-", "")))
    tokens = set(fold(re.sub(r"\(.*?\)", "", str(row.mayor_name))).replace("-", " ").split())
    # a register surname matches if any of its words is in the coded name (double and married surnames), and
    # the first name decides between several matches
    sur = seats.surname.str.replace("-", " ").str.split().map(lambda w: bool(set(w) & tokens))
    hit = seats[sur]
    if len(hit) > 1:
        hit = hit[hit["first"].isin(tokens)] if hit["first"].isin(tokens).any() else hit
    if len(hit) != 1:
        return None
    member = PARTY_CODES.get(int(hit.PSTRANA.iloc[0]))
    if member and member != "BEZPP":
        return member
    return PARTY_CODES.get(int(hit.NSTRANA.iloc[0])) or "LOCAL"


def aligned(row, day: str, reg: pd.DataFrame, code: int) -> int | None:
    p = register_party(row, reg, code, day)
    return None if p is None else int(p in coalition(day))


def seat_variants(reg: pd.DataFrame, ros: pd.DataFrame, code: int, term: int, day: str) -> dict:
    """Mechanical variants from the register: seat majority, largest list with a coalition party, seat share."""
    c = coalition(day)
    stamp = int(day.replace("-", ""))
    seats = in_force(reg[(reg.KODZASTUP == code) & (reg.term == term)], stamp)
    ok = seats.NSTRANA.map(PARTY_CODES).isin(c) | seats.PSTRANA.map(PARTY_CODES).isin(c)
    top = in_force(ros[(ros.KODZASTUP == code) & (ros.term == term)], stamp).sort_values("MAND_STR", ascending=False)
    comp = [PARTY_CODES.get(int(x)) for x in re.findall(r"\d+", str(top.SLOZENI.iloc[0]))] if len(top) else []
    return {"seat_share": round(float(ok.mean()), 3) if len(seats) else None,
            "seat_majority": int(ok.mean() > 0.5) if len(seats) else None,
            "largest_list_has_coalition_party": int(any(p in c for p in comp))}


def lists() -> pd.DataFrame:
    out = []
    for year, f in REGISTERS.items():
        ros = pd.read_csv(io.BytesIO(zipfile.ZipFile(RAW / f).read("csv_od/kvros.csv")))
        ros = ros[ros.OKRES == 1100]
        # wards (Praha 9 in 2014 and 2018, Praha 4 in 2014) form one assembly: seats summed over wards. A
        # court-corrected result or a new election is a complete later record; in_force picks the one that applies
        ros = ros.groupby(["KODZASTUP", "NAZEVZAST", "VSTRANA", "DATUMVOLEB"], as_index=False).agg(
            MAND_STR=("MAND_STR", "sum"), SLOZENI=("SLOZENI", "first"))
        out.append(ros.assign(term=year))
    return pd.concat(out)


def in_force(records: pd.DataFrame, stamp: int) -> pd.DataFrame:
    """The latest record of an assembly dated on or before the day (YYYYMMDD)."""
    ok = records[records.DATUMVOLEB <= stamp]
    return ok[ok.DATUMVOLEB == ok.DATUMVOLEB.max()] if len(ok) else ok


def main() -> None:
    reg, ros = registers(), lists()
    names = ros[ros.KODZASTUP != 554782].groupby("NAZEVZAST").KODZASTUP.first()
    coders = {c: spells(RAW / "alignment" / f"coder_{c}.csv") for c in "AB"}
    adj_path = RAW / "alignment" / "adjudication.csv"
    adj = pd.read_csv(adj_path) if adj_path.exists() else pd.DataFrame(columns=["district", "r", "A"])
    rows, disagreements = [], []
    for district, code in names.items():
        tier = int(bool(re.fullmatch(r"Praha \d+", district)) and int(district.split()[-1]) <= 22)
        for r in YEARS:
            day = f"{r}-06-30"
            term = 2014 if r <= 2018 else 2018 if r <= 2022 else 2022
            who = {c: mayor_on(s, district, day) for c, s in coders.items()}
            same = who["A"] is not None and who["B"] is not None and surname(who["A"]) == surname(who["B"])
            a = {c: aligned(m, day, reg, int(code)) for c, m in who.items()}
            man = adj[(adj.district == district) & (adj.r == r)]
            final = int(man.A.iloc[0]) if len(man) else a["A"] if same and a["A"] is not None else None
            if not same or a["A"] is None:
                disagreements.append({"district": district, "r": r, "same_mayor": same, "A_coder": a["A"],
                                      "B_coder": a["B"], "resolved": final})  # no names in committed output
            # the coders' free-text party membership, kept for the robustness variant (mid-term party switches)
            member = {c: (m.member if m is not None else None) for c, m in who.items()}
            hand = int(member["A"] in coalition(day)) if member["A"] and member["A"] == member["B"] \
                and member["A"] != "BEZPP" else final
            rows.append({"district": district, "code": int(code), "tier": tier, "r": r, "A": final,
                         "A_coderA": a["A"], "A_coderB": a["B"], "same_mayor": int(same), "A_hand_member": hand,
                         "interregnum": int(INTERREGNUM[0] <= day <= INTERREGNUM[1]),
                         **seat_variants(reg, ros, int(code), term, day)})
    panel = pd.DataFrame(rows)
    events = {}
    for name, (pre, post) in EVENTS.items():
        w = panel[panel.r.isin([pre, post])].pivot(index="district", columns="r", values="A")
        tier = panel[panel.r == pre].set_index("district").tier
        up = (w[pre] == 0) & (w[post] == 1)
        events[name] = {"up": int(up.sum()), "down": int(((w[pre] == 1) & (w[post] == 0)).sum()),
                        "always": int(((w[pre] == 1) & (w[post] == 1)).sum()),
                        "never": int(((w[pre] == 0) & (w[post] == 0)).sum()),
                        "unresolved": int(w.isna().any(axis=1).sum()),
                        "up_by_tier": {"numbered": int((up & (tier == 1)).sum()), "other": int((up & (tier == 0)).sum())}}
    p = panel.sort_values(["district", "r"])
    p = p.assign(prev=p.groupby("district").A.shift())
    other = p[p.prev.notna() & p.A.notna() & (p.A != p.prev) & ~p.r.isin([2019, 2023])]
    variants = {v: {str(r): int(panel[panel.r == r][v].sum()) for r in (2018, 2019, 2022, 2023)}
                for v in ["A", "seat_majority", "largest_list_has_coalition_party"]}
    agree = panel.assign(A_coderA=panel.same_mayor)  # agreement = same mayor on 30 June
    agree = agree.assign(A_coderB=1)
    frozen = pd.concat(list(coders.values()))
    frozen_path = RAW / "alignment" / "frozen.csv"
    frozen.to_csv(frozen_path, index=False)
    frozen.drop(columns=["mayor_name", "notes"]).to_csv(DOCS / "prague-districts-alignment.csv", index=False)
    panel.to_csv(RAW / "alignment" / "panel.csv", index=False)
    out = {"events": events, "other_switches": other[["district", "r", "prev", "A"]].to_dict("records"),
           "aligned_count_by_rule": variants,
           "coder_agreement": round(float((agree.A_coderA == agree.A_coderB).mean()), 3),
           "coder_agreement_n": len(agree), "disagreements": disagreements,
           "frozen_sha256": hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
           "panel_sha256": hashlib.sha256((RAW / "alignment" / "panel.csv").read_bytes()).hexdigest()}
    (DOCS / "prague-districts-alignment.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps({k: out[k] for k in ["events", "coder_agreement", "aligned_count_by_rule"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
