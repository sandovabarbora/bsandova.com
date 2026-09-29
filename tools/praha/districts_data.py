"""Part 3 extended, the raw data: district budgets 2015-2025 (approved, amended, actual), population and age,
area, and the municipal elections of 2014, 2018 and 2022 (docs/research/prague-districts-design.md, §3).

Downloads only. The one report it writes, raw_report.json, holds structure: files, columns, codes and coverage
(which district-years have a report at all). It computes no statistic of any outcome the design tests.

Sources (downloaded into tools/data/praha3x/, not committed):
  - MONITOR (Ministry of Finance) web API, for each of the 57 districts and for the city itself (IČO 00064581),
    at December of each year 2015-2025: totals (rozpocet), incomes by type (druhovy, cast=p), outgoings by type
    (druhovy, cast=v) and outgoings by function (odvetvovy, cast=v). Every node carries four columns: approved
    (schválený), afterChanges (po změnách), finalBudget (konečný) and reality (skutečnost).
    Coverage found at download: the API answers every district-year, but the district reports for 2015-2021 are
    empty (all zeros); only 2022-2025 carry figures. The city's own reports are filled in every year.
  - MONITOR's bulk FIN 2-12 M extract for 2019, as a second route to the earlier years: it leaves the districts out,
    as the 2024 extract does (districts.py), so it is kept only as evidence of that.
  - District IČOs: mc_ico.csv, extracted by tools/praha/districts.py from MONITOR's register of accounting units
    (subtype 301), copied here.
  - Czech Statistical Office, Prague office: residents by district at 31 December 1991-2025 (CR_L3_MC.xlsx) and
    residents by district and age (1_PHA_VEK_obyv_mc.xlsx).
  - RÚIAN (ČÚZK map service): layer 8, city districts (městské části), and layer 10, Prague's 22 administrative
    districts (správní obvody), with geometry in EPSG:5514, for area and tier.
  - volby.gov.cz open data, municipal elections 2014, 2018 and 2022: lists (kvros), candidates (kvrk) and
    code lists, for the 57 district assemblies and the city assembly (ZHMP).

Usage:
    uv run --with pandas --with openpyxl python tools/praha/districts_data.py
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get("PRAHA3X", ROOT / "tools" / "data" / "praha3x"))
API = "https://monitor.statnipokladna.gov.cz/api/"
CITY_ICO = "00064581"
BULK_2019 = "https://monitor.statnipokladna.gov.cz/data/extrakty/csv/FinM/2019_12_Data_CSUIS_FINM.zip"
YEARS = list(range(2015, 2026))
CSU = "https://csu.gov.cz/docs/107839/"
POPULATION = CSU + "3e786c03-ba36-95fb-f4ed-d78f947119e9/CR_L3_MC.xlsx?version=1.7"
AGE = CSU + "afefbae8-c12f-7944-fe52-ce39f88da593/1_PHA_VEK_obyv_mc.xlsx?version=1.6"
RUIAN = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/MapServer/{}/query"
VOLBY = "https://volby.gov.cz/opendata/"
ELECTIONS = {
    2014: ["kv2014/KV2014_reg_20230224_csv.zip", "kv2014/KV2014_data_20230224_csv.zip",
           "kv2014/KV2014_cisel_20230224_csv.zip"],
    2018: ["kv2018/KV2018_reg_20230224_csv.zip", "kv2018/KV2018_data_20230224_csv.zip",
           "kv2018/KV2018_cisel_20230224_csv.zip"],
    2022: ["kv2022/KV2022reg20260328_csv.zip", "kv2022/KV2022_data_20260328_csv.zip",
           "kv2022/KV2022ciselniky20260328_csv.zip"],
}
QUERIES = {"tot": "rozpocet?{}", "prij": "rozpocet/druhovy?{}&cast=p", "dru": "rozpocet/druhovy?{}&cast=v",
           "odv": "rozpocet/odvetvovy?{}&cast=v"}
AGENT = {"User-Agent": "bsandova.com research"}


def get(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers=AGENT)
        path.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    return path


def api(query: str, path: Path) -> bool:
    """One MONITOR report, cached; False if the API never answered."""
    if path.exists():
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):
        try:
            req = urllib.request.Request(API + query, headers=AGENT)
            path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            time.sleep(0.3)
            return True
        except Exception:  # noqa: BLE001 - the API drops the odd request
            time.sleep(3 * (attempt + 1))
    return False


def budgets(icos: dict[str, str]) -> list[str]:
    failed = []
    for name, ico in [*sorted(icos.items()), ("city", CITY_ICO)]:
        for year in YEARS:
            base = f"obdobi={str(year)[2:]}12&ic={ico}"
            for kind, q in QUERIES.items():
                if not api(q.format(base), RAW / "api" / f"{ico}_{year}_{kind}.json"):
                    failed.append(f"{ico}_{year}_{kind}")
    return failed


def ruian(layer: int, name: str) -> Path:
    path = RAW / f"ruian_{name}.json"
    if not path.exists():
        q = {"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "5514", "f": "json",
             "geometry": json.dumps({"xmin": -760000, "ymin": -1060000, "xmax": -720000, "ymax": -1030000}),
             "geometryType": "esriGeometryEnvelope", "inSR": "5514", "spatialRel": "esriSpatialRelIntersects"}
        req = urllib.request.Request(RUIAN.format(layer), data=urllib.parse.urlencode(q).encode(), headers=AGENT)
        path.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    return path


def structure(icos: dict[str, str]) -> dict:
    """Coverage and codes only: which reports exist and are non-empty, which columns and codes they carry."""
    have, empty, columns, income_codes = 0, [], set(), set()
    for ico in [*icos.values(), CITY_ICO]:
        for year in YEARS:
            p = RAW / "api" / f"{ico}_{year}_tot.json"
            if not p.exists():
                continue
            have += 1
            t = json.loads(p.read_text())
            columns |= set(t["outgoings"])
            if not t["outgoings"]["reality"]:
                empty.append(f"{ico}_{year}")
            stack = json.loads((RAW / "api" / f"{ico}_{year}_prij.json").read_text()).get("children") or []
            while stack:
                c = stack.pop()
                if c["code"].startswith("4"):
                    income_codes.add((c["code"], c["name"]))
                stack += c.get("children") or []
    out = {"district_years_with_report": have, "reports_with_no_outgoings": empty, "budget_columns": sorted(columns),
           "transfer_income_codes": sorted(income_codes)}
    for year, files in ELECTIONS.items():
        for f in files:
            z = zipfile.ZipFile(RAW / f"kv{year}" / Path(f).name)
            out[f"kv{year}_{Path(f).stem}"] = sorted(z.namelist())
    for f in ["mc_pop.xlsx", "mc_age.xlsx"]:
        out[f] = {s: list(df.shape) for s, df in pd.read_excel(RAW / f, sheet_name=None, header=None).items()}
    for f in ["ruian_momc.json", "ruian_spravni.json"]:
        feats = json.loads((RAW / f).read_text()).get("features", [])
        out[f] = {"features": len(feats), "fields": sorted(feats[0]["attributes"]) if feats else []}
    z = zipfile.ZipFile(RAW / "finm" / "2019_12.zip")
    text = z.read(next(n for n in z.namelist() if n.startswith("FINM201"))).decode("utf-8", "replace")
    out["bulk_2019_district_icos_present"] = sum(ico in text for ico in icos.values())
    out["bulk_2019_city_present"] = CITY_ICO in text
    return out


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    icos = dict(pd.read_csv(get("file:" + str(RAW.parent / "praha3" / "mc_ico.csv"), RAW / "mc_ico.csv"),
                            dtype=str).values)
    get(POPULATION, RAW / "mc_pop.xlsx")
    get(AGE, RAW / "mc_age.xlsx")
    for year, files in ELECTIONS.items():
        for f in files:
            get(VOLBY + f, RAW / f"kv{year}" / Path(f).name)
    ruian(8, "momc")
    ruian(10, "spravni")
    get(BULK_2019, RAW / "finm" / "2019_12.zip")
    failed = budgets(icos)
    report = structure(icos) | {"failed_requests": failed, "districts": len(icos), "years": YEARS}
    (RAW / "raw_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ["districts", "district_years_with_report", "failed_requests"]}))


if __name__ == "__main__":
    main()
