"""One city, 57 budgets: what Prague's city districts (městské části) spend, per resident, on what, and who runs them.

Sources (downloaded into tools/data/praha3/, not committed):
  - Budgets, 2022-2024, from the Ministry of Finance's MONITOR (api/rozpocet...): each district's outgoings by
    function (odvětvové třídění) and by type, and incomes by type, "reality" (actual) at the end of each year.
    MONITOR's bulk FIN 2-12 M extract leaves the Prague districts out; its web API has them.
  - District ids (IČO): MONITOR's register of accounting units (ucjed.xml, ~390 MB), subtype 301, valid in the
    year; kept as mc_ico.csv once extracted.
  - Population at 31 December of each year: Czech Statistical Office, Prague office, "Obyvatelstvo Prahy podle
    městských částí 1991-2025" (CR_L3_MC.xlsx).
  - Municipal election 2022: Czech Statistical Office, district assemblies' lists with votes and seats (kvros.csv).

Functions are grouped by name, not code: education is coded 31 in most districts and 32 in some. "Town hall" is
section 61 (state power, administration, self-government); "debt and finance" (63) is kept apart.
Totals are MONITOR's, not consolidated: they include money a district moves between its own accounts. Class 4 items
4131, 4132 and 4140 (transfers from the district's own funds, mostly net business income such as rents) are counted
as own non-tax revenue, not as transfers (correction of 28 September 2026).
Amounts are per resident, averaged over 2022-2024 (each year's spending over that year's population), because
investment is lumpy: a district that builds a school in one year spends three times its usual budget.

Usage:
    uv run --with pandas --with openpyxl python tools/praha/districts.py
"""

import io
import json
import re
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha3"
OUT = ROOT / "assets" / "praha" / "districts.json"
API = "https://monitor.statnipokladna.gov.cz/api/"
UCJED = "https://monitor.statnipokladna.cz/data/xml/ucjed.xml"
POPULATION = "https://csu.gov.cz/docs/107839/3e786c03-ba36-95fb-f4ed-d78f947119e9/CR_L3_MC.xlsx?version=1.7"
ELECTION = "https://volby.gov.cz/opendata/kv2022/KV2022reg20260328_csv.zip"
YEARS = [2022, 2023, 2024]
OWN_FUNDS = ["4131", "4132", "4140"]  # class 4 items that move a district's own money into its budget
GROUPS = {  # level-2 function names -> reported group
    "Vzdělávání a školské služby": "education",
    "Sociální služby a společné činnosti v sociálním zabezpečení a politice zaměstnanosti": "social",
    "Bydlení, komunální služby a územní rozvoj": "housing & public space",
    "Ochrana životního prostředí": "environment",
    "Doprava": "transport",
    "Kultura, církve a sdělovací prostředky": "culture",
    "Sport a zájmová činnost": "sport & leisure",
    "Státní moc, státní správa, územní samospráva a politické strany": "town hall",
}


def get(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "bsandova.com research"})
        path.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    return path


def api(query: str, path: Path) -> dict:
    if not path.exists():
        for attempt in range(4):
            try:
                req = urllib.request.Request(API + query, headers={"User-Agent": "bsandova.com research"})
                path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                break
            except Exception:  # noqa: BLE001 - the API drops the odd request
                time.sleep(3 * (attempt + 1))
        time.sleep(0.3)
    return json.loads(path.read_text())


def district_icos() -> dict[str, str]:
    """District name ('Praha 1', 'Praha-Libuš') -> IČO, from MONITOR's register, subtype 301."""
    cache = RAW / "mc_ico.csv"
    if cache.exists():
        return dict(pd.read_csv(cache, dtype=str).values)
    out = {}
    text = get(UCJED, RAW / "ucjed.xml").read_text(encoding="utf-8")
    for row in re.findall(r"<row>(.*?)</row>", text, re.S):
        field = {k: v.strip() for k, v in re.findall(r"<(\w+)>(.*?)</\1>", row, re.S)}
        if field.get("poddruhuj_id") == "301" and field.get("nazev", "").startswith("Městská část Praha"):
            if field["start_date"] <= "2024-12-31" <= field["end_date"]:
                out[field["nazev"].removeprefix("Městská část ")] = field["ico"]
    pd.DataFrame(list(out.items()), columns=["district", "ico"]).to_csv(cache, index=False)
    return out


def population() -> pd.DataFrame:
    s = pd.read_excel(get(POPULATION, RAW / "mc_pop.xlsx"), header=None)
    cols = {}
    for i in range(s.shape[1]):
        m = re.search(r"31\.12\.(\d{4})", str(s.iloc[4, i]).replace("\n", ""))
        if m and int(m.group(1)) in YEARS:
            cols[int(m.group(1))] = i
    p = s.iloc[6:, [2, 3, *cols.values()]]
    p.columns = ["code", "district", *cols.keys()]
    p = p[p.code.astype(str).str.fullmatch(r"\d{6}")].copy()
    p["district"] = p.district.astype(str).str.strip()
    return p.set_index("district")


def flat(node: dict, depth: int = 1) -> list[dict]:
    out = []
    for c in node.get("children") or []:
        out.append({"code": c["code"], "name": c["name"], "depth": depth, "reality": c["budget"]["reality"]})
        out += flat(c, depth + 1)
    return out


def year_row(ico: str, year: int) -> dict:
    period = f"{str(year)[2:]}12"
    base = f"obdobi={period}&ic={ico}"
    tot = api(f"rozpocet?{base}", RAW / "api" / f"{ico}_{year}_tot.json")
    fn = pd.DataFrame(flat(api(f"rozpocet/odvetvovy?{base}&cast=v", RAW / "api" / f"{ico}_{year}_odv.json")))
    kind = pd.DataFrame(flat(api(f"rozpocet/druhovy?{base}&cast=v", RAW / "api" / f"{ico}_{year}_dru.json")))
    inc = pd.DataFrame(flat(api(f"rozpocet/druhovy?{base}&cast=p", RAW / "api" / f"{ico}_{year}_prij.json")))
    out, income = tot["outgoings"]["reality"], tot["incomes"]["reality"]
    level2 = fn[fn.depth == 2]
    own = float(inc[inc.code.isin(OWN_FUNDS)].reality.sum())
    row = {"spent": out, "income": income,
           "capital": float(kind[(kind.depth == 1) & (kind.code == "6")].reality.sum()),
           "taxes": float(inc[(inc.depth == 1) & (inc.code == "1")].reality.sum()),
           "non_tax": float(inc[(inc.depth == 1) & (inc.code == "2")].reality.sum()) + own,
           "transfers": float(inc[(inc.depth == 1) & (inc.code == "4")].reality.sum()) - own}
    for name, group in GROUPS.items():
        row[group] = row.get(group, 0.0) + float(level2[level2.name == name].reality.sum())
    return row


def election() -> pd.DataFrame:
    z = zipfile.ZipFile(get(ELECTION, RAW / "kv2022reg.zip"))
    lists = pd.read_csv(io.BytesIO(z.read("csv_od/kvros.csv")))
    return lists


def main() -> None:
    icos, pop, lists = district_icos(), population(), election()
    rows = []
    for name, ico in sorted(icos.items()):
        years = {y: year_row(ico, y) for y in YEARS}
        per_head = {y: years[y]["spent"] / pop.loc[name, y] for y in YEARS}
        total = {k: sum(years[y][k] for y in YEARS) for k in years[YEARS[0]]}
        code = int(pop.loc[name, "code"])
        mine = lists[lists.KODZASTUP == code].sort_values(["MAND_STR", "PROCHLSTR"], ascending=False)
        rows.append({
            "district": name, "code": code, "ico": ico, "population": int(pop.loc[name, 2024]),
            "per_head": round(sum(per_head.values()) / len(YEARS)),
            "per_head_by_year": {y: round(v) for y, v in per_head.items()},
            "shares": {g: round(total[g] / total["spent"], 3) for g in [*GROUPS.values(), "capital"]},
            "income_taxes": round(total["taxes"] / total["income"], 3),
            "income_non_tax": round(total["non_tax"] / total["income"], 3),
            "income_per_head": {k: round(sum(years[y][k] / pop.loc[name, y] for y in YEARS) / len(YEARS))
                                for k in ["taxes", "non_tax", "transfers", "income"]},
            "income_transfers": round(total["transfers"] / total["income"], 3),
            "seats": int(mine.MAND_STR.sum()),
            "lists_2022": [{"list": r.NAZEVCELK, "votes_pct": float(r.PROCHLSTR), "seats": int(r.MAND_STR)}
                           for r in mine.itertuples() if r.MAND_STR > 0],
        })
    d = pd.DataFrame(rows)
    big = d[d.population > 40000]
    out = {
        "years": YEARS,
        "districts": rows,
        "summary": {
            "districts": len(d),
            "population": int(d.population.sum()),
            "per_head_median": int(d.per_head.median()),
            "per_head_range": [int(d.per_head.min()), int(d.per_head.max())],
            "big_districts": len(big),
            "big_share_of_population": round(float(big.population.sum() / d.population.sum()), 3),
            "big_per_head_range": [int(big.per_head.min()), int(big.per_head.max())],
            "transfers_share_median": float(d.income_transfers.median()),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
