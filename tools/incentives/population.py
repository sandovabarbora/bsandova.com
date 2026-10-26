"""Population aged 15–64 by district from ČSÚ open data set 130149 (population by sex and basic age groups, 31
December 2000–2024), the denominator of Q3 and nothing else (design change log, second entry of 26 October 2026).
Population is not an outcome; no MPSV file is opened here.

ČSÚ districts (číselník 101) are mapped to the study's MPSV district codes by their LAU 1 code, the link projects.py
uses, and cross-checked against ČSÚ's own `kod_ruian` and the district name; any district that does not map, or a
study district without a population, stops the run.

    nice -n 20 uv run --no-project --with pandas python -I tools/incentives/population.py   # prints coverage only
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import CODES_DIR, CZSO_DIR, RAW

POP_ZIP = CZSO_DIR / "130149-25data052025.zip"
DISTRICT_LIST = CODES_DIR / "okresy_101.csv"
STAPRO = "2406"  # population with permanent or long-term residence
AGE_15_64 = "410015610065000"  # ČSÚ číselník 7700 interval "15 až 64"
DISTRICT_CIS = "101"
PRAGUE = "3100"  # outside the study (§2); ČSÚ publishes it as a region, not in the 101 rows of 130149


class DistrictMismatch(ValueError):
    pass


def mpsv_districts(raw: Path = RAW) -> dict[str, tuple[str, str]]:
    """MPSV district code → (LAU 1 code, name)."""
    out = {}
    for o in json.loads((raw / "mpsv_okresy.json").read_text(encoding="utf-8"))["polozky"]:
        if o["kod"] == "9999":  # "území Hlavního města Prahy", a second LAU entry for Prague
            continue
        out[o["kod"]] = (o["kodLau"], o["nazev"]["cs"])
    return out


def district_map(csu_rows: list[dict], mpsv: dict[str, tuple[str, str]]) -> dict[str, str]:
    """ČSÚ district code → MPSV district code. Two codes are cross-checked so that a near name (Brno-město and
    Brno-venkov, Praha and Praha-východ) can never be taken for another."""
    by_lau: dict[str, str] = {}
    for kod, (lau, _) in mpsv.items():
        if lau in by_lau:
            raise DistrictMismatch(f"two MPSV districts share LAU {lau}: {by_lau[lau]}, {kod}")
        by_lau[lau] = kod
    out, bad = {}, []
    for r in csu_rows:
        lau = r["okres_lau"]
        if lau == "CZZZZZ":  # Extra-Regio, no territory
            continue
        kod = by_lau.get(lau)
        if kod is None:
            bad.append(f"{r['chodnota']} {r['text']} (LAU {lau}): no MPSV district")
            continue
        if r["kod_ruian"] and r["kod_ruian"] != kod:
            bad.append(f"{r['chodnota']} {r['text']}: LAU gives {kod}, kod_ruian {r['kod_ruian']}")
            continue
        if not r["kod_ruian"] and kod != PRAGUE:  # only Prague's 101 entry lacks it
            bad.append(f"{r['chodnota']} {r['text']}: no kod_ruian")
            continue
        if r["text"] != mpsv[kod][1] and kod != PRAGUE:  # ČSÚ "Praha", MPSV "Hlavní město Praha"
            bad.append(f"{r['chodnota']} {r['text']}: name differs from MPSV {mpsv[kod][1]}")
            continue
        out[r["chodnota"]] = kod
    if bad:
        raise DistrictMismatch("ČSÚ districts that do not map: " + "; ".join(bad))
    return out


def read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def iter_csv(zip_path: Path):
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"{zip_path.name}: expected one CSV, found {names}")
        with z.open(names[0]) as raw:
            yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))


def year_end_15_64(rows, cmap: dict[str, str]) -> pd.DataFrame:
    """Years × MPSV district codes: both sexes aged 15–64 at 31 December. A 101 row that is not in the map fails."""
    vals: dict[tuple[int, str], float] = {}
    unmatched = set()
    for r in rows:
        if (r["uzemi_cis"] != DISTRICT_CIS or r["stapro_kod"] != STAPRO or r["vek_kod"] != AGE_15_64
                or r["pohlavi_kod"]):
            continue
        kod = cmap.get(r["uzemi_kod"])
        if kod is None:
            unmatched.add(f"{r['uzemi_kod']} {r['uzemi_txt']}")
            continue
        if not r["obdobi"].endswith("-12-31"):
            raise ValueError(f"not a 31 December stock: {r['obdobi']}")
        key = (int(r["obdobi"][:4]), kod)
        if key in vals:
            raise ValueError(f"two values for district {kod} in {key[0]}")
        vals[key] = float(r["hodnota"])
    if unmatched:
        raise DistrictMismatch(f"ČSÚ districts in the data with no study code: {sorted(unmatched)}")
    s = pd.Series(vals)
    return s.unstack() if len(s) else pd.DataFrame()


def monthly(year_end: pd.DataFrame, districts: list[str], first: int, last: int) -> pd.DataFrame:
    """Months × districts (months since year 0), linear between year-end stocks: the end of month m of year Y is
    P(Y−1) + m/12 × (P(Y) − P(Y−1)), so a mean over the 12 months of year −1 is the population over that year, not a
    year-end figure. A study district without any population fails; Prague is outside the study and refused."""
    if PRAGUE in districts:
        raise DistrictMismatch("Prague is outside the study (§2); no population is looked up for it")
    missing = sorted(set(districts) - set(year_end.columns))
    if missing:
        raise DistrictMismatch(f"study districts with no ČSÚ population: {missing}")
    idx = np.arange(first, last + 1)
    out = pd.DataFrame(np.nan, index=idx, columns=districts)
    for m in idx:
        y, mm = divmod(int(m), 12)  # mm 0..11 is January..December
        if y - 1 in year_end.index and y in year_end.index:
            a, b = year_end.loc[y - 1, districts], year_end.loc[y, districts]
            out.loc[m] = (a + (mm + 1) / 12 * (b - a)).to_numpy()
    return out


def load(districts: list[str], first: int, last: int, zip_path: Path = POP_ZIP, district_list: Path = DISTRICT_LIST,
         raw: Path = RAW) -> pd.DataFrame:
    cmap = district_map(read_rows(district_list), mpsv_districts(raw))
    return monthly(year_end_15_64(iter_csv(zip_path), cmap), districts, first, last)


def main() -> None:
    """Coverage of the real file and the mapping, without printing any population value."""
    mpsv = mpsv_districts()
    cmap = district_map(read_rows(DISTRICT_LIST), mpsv)
    ye = year_end_15_64(iter_csv(POP_ZIP), cmap)
    study = sorted(k for k in mpsv if k != PRAGUE)
    print("ČSÚ 101 entries mapped:", len(cmap), "| study districts outside Prague:", len(study))
    print("years:", int(ye.index.min()), "-", int(ye.index.max()), "| districts in data:", ye.shape[1])
    print("study districts without population:", sorted(set(study) - set(ye.columns)))
    print("Brno-město, Brno-venkov:", {c: k for c, k in cmap.items() if k in ("3702", "3703")})
    print("any missing value 2004-2021:", bool(ye.loc[2004:2021, study].isna().any().any()))


if __name__ == "__main__":
    main()
