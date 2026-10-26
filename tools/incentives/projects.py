"""Treatment side of the investment incentives study (design §2): places, events, blockers and comparison pools.

Matches each `lokalita_mesto` of an incentive row to municipalities and so to districts as of 2024 (ČSÚ code lists
fetched by fetch.py), writes the matching table tools/incentives/places.csv, and builds the events of §2: an incentive
decision with at least 300 promised jobs naming one place in one district outside Prague, decided 1 July 2006 – 31
January 2021, with no other incentive decision of at least 300 jobs in its district from 24 months before to 47 after
(a multi-place or ambiguous project blocks every district it could be in) and at least 10 comparison districts, under
the 26 October 2026 amendment of the design change log. Districts with a 2007/2016 boundary change stay in; each
event lists the ones inside its years −2 to 3 for check 6. Reads only the project list and code lists.

    uv run --no-project --with pandas python -I tools/incentives/projects.py   # rewrites places.csv, prints counts
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import CODES_DIR, PROJECTS_CSV, RAW

HERE = Path(__file__).resolve().parent
PLACES_CSV = HERE / "places.csv"

EVENT_JOBS = 300
BLOCK_JOBS = 300  # amended 26 October 2026 (registered: 200)
WIN_BEFORE, WIN_AFTER = 24, 47  # clean window in months around the decision month (amended; registered: 48 and 47)
FIRST_DECISION, LAST_DECISION = dt.date(2006, 7, 1), dt.date(2021, 1, 31)
MIN_COMPARISONS = 10
PRAGUE = "3100"
BOUNDARY_DATES = {"2007": (2007, 1), "2016": (2016, 1)}

# Place strings the rules below cannot resolve, read by hand from the string itself (no outcome involved).
# Value: municipality names as they appear in the ČSÚ list, or a qualifying district name after "okres:".
OVERRIDES: dict[str, list[str]] = {
    "Kadaň (Klášterec/Ohří)": ["Kadaň", "Klášterec nad Ohří"],
}


def ym(d: dt.date) -> int:
    """Months since year 0, so a difference of two is a number of months."""
    return d.year * 12 + d.month - 1


def ym_of(y: int, m: int) -> int:
    return y * 12 + m - 1


# ---------- code lists ----------

def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@dataclass
class Geo:
    muni_district: dict[str, str]  # municipality code → MPSV district code (2024)
    muni_name: dict[str, str]
    district_name: dict[str, str]
    district_kraj: dict[str, str]  # MPSV district code → region name
    names: dict[str, set[str]] = field(default_factory=dict)  # normalised municipality name → codes
    parts: dict[str, set[str]] = field(default_factory=dict)  # normalised part or cadastre name → municipality codes
    plain_parts: dict[str, set[str]] = field(default_factory=dict)  # the same without accents

    @property
    def districts(self) -> list[str]:
        return sorted(self.district_name)

    def kraj_districts(self, kraj: str) -> set[str]:
        return {d for d, k in self.district_kraj.items() if k == kraj}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower().strip()
    s = re.sub(r"\bn\.\s*l\.?", "nad labem", s)
    s = re.sub(r"[–—-]", " ", s)
    s = re.sub(r"[.\s]+", " ", s)
    return s.strip(" ,;")


def load_geo(codes: Path = CODES_DIR, raw: Path = RAW) -> Geo:
    okresy = json.loads((raw / "mpsv_okresy.json").read_text(encoding="utf-8"))["polozky"]
    kraje = {k["id"]: k["nazev"]["cs"] for k in json.loads((codes / "mpsv_kraje.json").read_text(encoding="utf-8"))["polozky"]}
    lau_to_mpsv, dname, dkraj = {}, {}, {}
    for o in okresy:
        if o["kod"] == "9999":  # "území Hlavního města Prahy", a duplicate LAU entry for Prague
            continue
        lau_to_mpsv[o["kodLau"]] = o["kod"]
        dname[o["kod"]] = o["nazev"]["cs"]
        dkraj[o["kod"]] = kraje[o["kraj"]]
    md, mn = {}, {}
    for r in read_csv(codes / "obce_okres_lau_2024-12-31.csv"):
        md[r["chodnota1"]] = lau_to_mpsv[r["chodnota2"]]
        mn[r["chodnota1"]] = r["text1"]
    g = Geo(md, mn, dname, dkraj)
    for code, name in mn.items():
        g.names.setdefault(norm(name), set()).add(code)
    for name in ("casti_obce_2024-12-31.csv", "katastry_2024-12-31.csv"):
        for r in read_csv(codes / name):
            if r["chodnota2"] in md:
                g.parts.setdefault(norm(r["text1"]), set()).add(r["chodnota2"])
                g.plain_parts.setdefault(plain(r["text1"]), set()).add(r["chodnota2"])
    return g


def boundary_districts(codes: Path = CODES_DIR, geo: Geo | None = None) -> dict[str, list[str]]:
    """MPSV codes of districts that gained or lost a municipality on 1 January 2007 and 1 January 2016 (§2).

    A municipality counts as moved if its NUTS 4 district differs between the day before and the day itself, or if it
    exists on only one of the two days (the military area Brdy was abolished on 1 January 2016).
    """
    geo = geo or load_geo(codes)
    by_name = {v: k for k, v in geo.district_name.items()}
    out = {}
    for label, before, after in (("2007", "2006-12-31", "2007-01-01"), ("2016", "2015-12-31", "2016-01-01")):
        a = {r["chodnota1"]: r["text2"] for r in read_csv(codes / f"obce_okres_nuts_{before}.csv")}
        b = {r["chodnota1"]: r["text2"] for r in read_csv(codes / f"obce_okres_nuts_{after}.csv")}
        names = set()
        for m in a.keys() | b.keys():
            if a.get(m) != b.get(m):
                names |= {n for n in (a.get(m), b.get(m)) if n}
        out[label] = sorted(by_name[n] for n in names)
    return out


# ---------- matching ----------

QUAL_DISTRICT = re.compile(r"^(?:orp|okres[yu]?|obec s rozšířenou působností)\s+(.+)$")
QUAL_SITE = re.compile(r"^(?:obec|část|spz|průmyslová zóna)\s+(.+)$")
SPLIT = re.compile(r"\s*(?:[,;/+]|\sa\s)\s*")


@dataclass
class Place:
    text: str
    districts: set[str]
    munis: set[str]
    how: str
    several: bool = False  # "Town - Town" naming two municipalities, not a town and its part


def plain(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", norm(s)) if not unicodedata.combining(ch))


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def seat_first(munis: set[str], geo: Geo) -> set[str]:
    """A name shared by municipalities in different districts goes to the one that gives its district its name."""
    seats = {c for c in munis if norm(geo.muni_name[c]) == norm(geo.district_name[geo.muni_district[c]])}
    return seats if len(seats) == 1 else munis


Cands = tuple[set[str], set[str], str]  # municipality codes, districts, rule used


def found(munis: set[str], how: str, geo: Geo, seat: bool = True) -> Cands:
    munis = seat_first(munis, geo) if seat else munis
    return munis, {geo.muni_district[c] for c in munis}, how


def candidates(name: str, geo: Geo, kraj: str | None, broad: bool = False) -> Cands:
    """Municipalities a name can stand for, by the first rule that finds any (recorded in places.csv):
    a municipality in the row's region (a district seat first when the name is shared), a district's own name, a part
    of a municipality or cadastral area in the region, the same outside the region, 'Town Part' written together,
    the name without its 'u X' suffix, a spelling one letter (or only accents) away from exactly one name in the
    region, a unique name
    that begins with it. With `broad` (a place with a qualifier), municipalities and parts in the region together, so
    the qualifier can choose among them."""
    n = norm(name)
    if not n:
        return set(), set(), "empty"
    in_kraj = geo.kraj_districts(kraj) if kraj else set()
    local = lambda pool: {c for c in pool.get(n, set()) if geo.muni_district[c] in in_kraj}
    if broad and (local(geo.names) | local(geo.parts)):
        return found(local(geo.names) | local(geo.parts), "municipality or part in region", geo, seat=False)
    if local(geo.names):
        return found(local(geo.names), "municipality in region", geo)
    dist = {d for d, dn in geo.district_name.items() if norm(dn) == n}
    if dist:
        return set(), dist, "district name"
    if local(geo.parts):
        return found(local(geo.parts), "part or cadastre in region", geo)
    for label, pool in (("municipality", geo.names), ("part or cadastre", geo.parts)):
        if pool.get(n):
            return found(set(pool[n]), f"{label} outside region", geo)
    words = n.split()
    for i in range(1, len(words)):
        town, part = " ".join(words[:i]), plain(" ".join(words[i:]))
        both = {c for c in geo.names.get(town, set()) if c in geo.plain_parts.get(part, set())}
        if both:
            return found(both, "town and its part", geo)
    if " u " in f" {n} ":
        head = n.split(" u ")[0]
        hit = {c for pool in (geo.names, geo.parts) for c in pool.get(head, set()) if geo.muni_district[c] in in_kraj}
        if hit:
            return found(hit, "name without 'u' suffix", geo)
    pn = plain(n)
    for label, pool in (("municipality", geo.names), ("part or cadastre", geo.parts)):
        near = {k for k, cs in pool.items() if any(geo.muni_district[c] in in_kraj for c in cs)
                and abs(len(plain(k)) - len(pn)) <= 1 and edit_distance(plain(k), pn) <= 1}
        if len(near) == 1:
            (k,) = near
            return found({c for c in pool[k] if geo.muni_district[c] in in_kraj}, f"spelling ({label} {k})", geo)
    pref = {c for k, cs in geo.names.items() if k.startswith(n + " ") for c in cs}
    if pref:
        loc = {c for c in pref if geo.muni_district[c] in in_kraj}
        return found(loc or pref, "name prefix", geo)
    return set(), set(), "no match"


def district_qualifier(name: str, geo: Geo) -> set[str]:
    """Districts named by an 'okres/ORP X' qualifier: the district called X, else the district of municipality X."""
    n = norm(name)
    hit = {d for d, dn in geo.district_name.items() if norm(dn) == n}
    return hit or {geo.muni_district[c] for c in geo.names.get(n, set())}


def resolve_one(token: str, quals: list[str], geo: Geo, kraj: str | None) -> Place:
    """One place: its name, narrowed by parenthetical qualifiers when they agree on a district."""
    sets, hows, several = [], [], False
    for piece in [token] + quals:
        p = piece.strip()
        if not p:
            continue
        md = QUAL_DISTRICT.match(norm(p))
        if md:
            sets.append((set(), district_qualifier(md.group(1), geo)))
            hows.append(f"{p}: district qualifier")
            continue
        ms = QUAL_SITE.match(norm(p))
        name = ms.group(1) if ms else p
        munis, ds, how = candidates(name, geo, kraj, broad=bool(quals))
        if not ds:
            pieces = split_pieces(name, geo)
            sub = [x for x in (candidates(x, geo, kraj) for x in pieces) if x[1]]
            if sub:
                munis, ds, how = set().union(*[x[0] for x in sub]), set().union(*[x[1] for x in sub]), "pieces"
                several = several or sum(1 for x in sub if x[2].startswith("municipality")) > 1
        sets.append((munis, ds))
        hows.append(f"{p}: {how}")
    hit = [x for x in sets if x[1]]
    if not hit:
        return Place(token, set(), set(), "; ".join(hows), several)
    common = set.intersection(*[x[1] for x in hit])
    ds = common or set.union(*[x[1] for x in hit])
    munis = {c for x in hit for c in x[0] if geo.muni_district[c] in ds}
    return Place(token, ds, munis, "; ".join(hows) + ("" if common or len(hit) == 1 else "; qualifiers disagree"),
                 several)


def split_pieces(name: str, geo: Geo) -> list[str]:
    """An unmatched name cut at hyphens, or after a leading municipality name ("Ostrava Mošnov")."""
    if re.search(r"[-–]", name):
        return [x for x in re.split(r"\s*[-–]\s*", name) if x.strip()]
    words = norm(name).split()
    for i in range(len(words) - 1, 0, -1):
        if " ".join(words[:i]) in geo.names:
            return [" ".join(words[:i]), " ".join(words[i:])]
    return []


def split_string(s: str) -> tuple[list[tuple[str, list[str]]], bool]:
    """Places named by a string, each with its parenthetical qualifiers; and whether it ends in 'atd.' (etc.)."""
    etc = bool(re.search(r"\batd\.?\s*$", s.strip()))
    s = re.sub(r",?\s*\batd\.?\s*$", "", s.strip())
    depth, buf, quals, qbuf = 0, "", [], ""
    tokens: list[tuple[str, list[str]]] = []

    def flush():
        nonlocal buf, quals
        for i, t in enumerate(x for x in SPLIT.split(buf) if x.strip()):
            tokens.append((t.strip(), quals if i == 0 else []))
        if not buf.strip() and quals and tokens:
            tokens[-1][1].extend(quals)
        buf, quals = "", []

    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "(":
            depth += 1
            qbuf = ""
        elif ch == ")" and depth:
            depth -= 1
            quals.extend(x.strip() for x in SPLIT.split(qbuf) if x.strip())
        elif depth:
            qbuf += ch
        elif ch in ",;/+":
            flush()
        else:
            buf += ch
        i += 1
    flush()
    # a district qualifier written as its own list item ("Dolní Teplice, okres Náchod") qualifies the place before it
    merged: list[tuple[str, list[str]]] = []
    for t, q in tokens:
        if QUAL_DISTRICT.match(norm(t)) and merged:
            merged[-1][1].append(t)
        else:
            merged.append((t, list(q)))
    return merged, etc


@dataclass
class Match:
    kraj: str
    text: str
    places: list[Place]
    etc: bool
    override: bool

    @property
    def multi(self) -> bool:
        return len(self.places) > 1 or self.etc or any(p.several for p in self.places)

    @property
    def districts(self) -> set[str]:
        """Every district the string could be in: a place with no match could be anywhere in its region."""
        return set().union(*[p.districts for p in self.places]) if self.places else set()

    def blocking(self, geo: Geo) -> set[str]:
        ds = set(self.districts)
        if any(not p.districts for p in self.places) or not self.places or self.etc:
            ds |= geo.kraj_districts(self.kraj)
        return ds

    @property
    def status(self) -> str:
        if self.multi:
            return "multi"
        if not self.places or not self.places[0].districts:
            return "unmatched"
        return "matched" if len(self.places[0].districts) == 1 else "ambiguous"


def match(kraj: str, text: str, geo: Geo) -> Match:
    if text in OVERRIDES:
        munis = set()
        for nm in OVERRIDES[text]:
            munis |= geo.names.get(norm(nm), set())
        ds = {geo.muni_district[c] for c in munis}
        place = Place(text, ds, munis, "override: " + ", ".join(OVERRIDES[text]))
        return Match(kraj, text, [place], False, True)
    toks, etc = split_string(text or "")
    places = [resolve_one(t, q, geo, kraj) for t, q in toks]
    return Match(kraj, text or "", places, etc, False)


def places_table(projects: pd.DataFrame, geo: Geo) -> pd.DataFrame:
    rows = []
    pairs = projects[["lokalita_kraj", "lokalita_mesto"]].fillna("").drop_duplicates()
    for kraj, text in sorted(pairs.itertuples(index=False), key=lambda x: (x[1], x[0])):
        m = match(kraj, text, geo)
        rows.append({
            "lokalita_kraj": kraj, "lokalita_mesto": text, "status": m.status, "n_places": len(m.places),
            "etc": int(m.etc), "override": int(m.override),
            "districts": ";".join(sorted(m.districts)),
            "district_names": ";".join(geo.district_name[d] for d in sorted(m.districts)),
            "blocks": ";".join(sorted(m.blocking(geo))),
            "places": " | ".join(f"{p.text} → {','.join(sorted(geo.district_name[d] for d in p.districts)) or '?'}"
                                 for p in m.places),
            "how": " | ".join(p.how for p in m.places),
        })
    return pd.DataFrame(rows)


# ---------- projects, events, pools ----------

def load_projects(path: Path = PROJECTS_CSV) -> pd.DataFrame:
    d = pd.read_csv(path, dtype=str, keep_default_na=False)
    d = d[d["ipo"] == "true"].copy()
    d["jobs"] = pd.to_numeric(d["pracovni_mista"], errors="coerce").fillna(0)
    d["date"] = pd.to_datetime(d["rozhodnuti_datum"], format="%d.%m.%Y").dt.date
    d["month"] = d["date"].map(ym)
    return d.reset_index(drop=True)


def attach_places(projects: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
    p = projects.merge(places, on=["lokalita_kraj", "lokalita_mesto"], how="left", validate="many_to_one")
    p["district_set"] = p["districts"].fillna("").map(lambda s: frozenset(x for x in s.split(";") if x))
    p["block_set"] = p["blocks"].fillna("").map(lambda s: frozenset(x for x in s.split(";") if x))
    return p


def in_window(month: int, m0: int, before: int = WIN_BEFORE, after: int = WIN_AFTER) -> bool:
    return m0 - before <= month <= m0 + after


def blockers_near(projects: pd.DataFrame, district: str, m0: int, skip: int | None = None,
                  block_jobs: float = BLOCK_JOBS) -> list[str]:
    """IDs of incentive decisions of at least `block_jobs` that block `district` inside the clean window of month m0."""
    out = []
    for r in projects.itertuples():
        if r.Index == skip or r.jobs < block_jobs or district not in r.block_set:
            continue
        if in_window(r.month, m0):
            out.append(r.id_projekt)
    return out


def years_cover(m0: int, y: int, m: int) -> bool:
    """Whether event years −2 to 3 (months m0−24 to m0+47) contain the given calendar month. A span that starts in
    that month counts as covering it: conservative, so check 6 removes slightly more."""
    return m0 - 24 <= ym_of(y, m) <= m0 + 47


def build_events(projects: pd.DataFrame, geo: Geo, boundaries: dict[str, list[str]], *,
                 event_jobs: float = EVENT_JOBS, block_jobs: float = BLOCK_JOBS,
                 first: dt.date = FIRST_DECISION, last: dt.date = LAST_DECISION,
                 min_comparisons: int = MIN_COMPARISONS) -> tuple[list[dict], list[dict]]:
    """Events kept and events dropped (with the first failing reason, in the order of §3.1). `moved` on a kept event
    are the districts with a boundary change inside its years −2 to 3 (headline keeps them; check 6 removes them)."""
    universe = [d for d in geo.districts if d != PRAGUE]
    kept, dropped = [], []
    for r in projects.itertuples():
        if r.jobs < event_jobs:
            continue
        base = {"id_projekt": r.id_projekt, "date": r.date.isoformat(), "month": r.month, "jobs": r.jobs,
                "lokalita_mesto": r.lokalita_mesto, "lokalita_kraj": r.lokalita_kraj,
                "cancelled": r.ipo_zruseni, "regime": r.ipo_rezim}
        if not (first <= r.date <= last):
            dropped.append(base | {"reason": "window"})
            continue
        if r.status == "multi":
            dropped.append(base | {"reason": "matching: several places"})
            continue
        if r.status != "matched":
            dropped.append(base | {"reason": f"matching: {r.status}"})
            continue
        (d,) = tuple(r.district_set)
        base |= {"district": d, "district_name": geo.district_name[d]}
        if d == PRAGUE:
            dropped.append(base | {"reason": "Prague"})
            continue
        block = blockers_near(projects, d, r.month, skip=r.Index, block_jobs=block_jobs)
        if block:
            dropped.append(base | {"reason": "clean window", "blocked_by": block})
            continue
        moved = {x for lab, (y, m) in BOUNDARY_DATES.items() if years_cover(r.month, y, m) for x in boundaries[lab]}
        comps = [c for c in universe if c != d and not blockers_near(projects, c, r.month, block_jobs=block_jobs)]
        if len(comps) < min_comparisons:
            dropped.append(base | {"reason": "fewer than 10 comparison districts", "n_comparisons": len(comps)})
            continue
        kept.append(base | {"comparisons": comps, "n_comparisons": len(comps),
                            "moved": sorted(moved)})
    return kept, dropped


def write_places(places: pd.DataFrame, path: Path = PLACES_CSV) -> None:
    places.to_csv(path, index=False, lineterminator="\n")


def main() -> None:
    geo = load_geo()
    projects = load_projects()
    places = places_table(projects, geo)
    write_places(places)
    p = attach_places(projects, places)
    events, dropped = build_events(p, geo, boundary_districts(geo=geo))
    print("place strings:", len(places), places["status"].value_counts().to_dict())
    print("events:", len(events), "distinct treated districts:", len({e["district"] for e in events}))
    print("dropped:", pd.Series([x["reason"] for x in dropped]).value_counts().to_dict())


if __name__ == "__main__":
    main()
