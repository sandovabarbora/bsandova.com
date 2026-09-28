"""Prague, Vienna, Warsaw: how many new homes each city completes per 1 000 residents, and who builds them.

Sources (downloaded into tools/data/praha4/, not committed):
  - Prague: Czech Statistical Office, Prague office, "Bytová výstavba v Praze 1994-2024" (01_byt_vystavba.xlsx):
    dwellings completed, and completed per 1 000 mid-year residents as the office computes it. Includes
    dwellings made by extensions and conversions.
  - Warsaw: Statistics Poland, Local Data Bank (BDL API), unit 071412865000 (Capital City Warszawa): dwellings
    completed (var 748601), of them municipal (748616) and by public building societies, TBS (748619);
    population at 31 December (72305), averaged over consecutive year-ends for a mid-year figure. Includes
    extensions and conversions. The population series is revised upward from 2020 after the 2021 census.
  - Vienna: Statistik Austria, dwellings completed 2011-2024 by Bundesland (Whg11-24_Bdl_150925.ods): dwellings
    in new buildings, because extensions and conversions are counted for Vienna only from 2024; annual average
    population (JDBev_..._ab2004.ods, sheet W); builders in 2024 (Ergebnisse im Überblick 2024, Tabelle_2).
Vienna's series therefore leaves out extensions and conversions, which Prague's and Warsaw's include.

Usage:
    uv run --with pandas --with openpyxl --with odfpy python tools/praha/cities.py
"""

import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha4"
OUT = ROOT / "assets" / "praha" / "cities.json"
PRAGUE = "https://csu.gov.cz/docs/107839/1e1eb5e2-bf30-ade7-713a-19cfae536124/01_byt_vystavba.xlsx?version=1.6"
BDL = "https://bdl.stat.gov.pl/api/v1/data/by-unit/071412865000?var-id={}&format=json&lang=en"
VIENNA_DONE = "https://www.statistik.at/fileadmin/pages/353/Whg11-24_Bdl_150925.ods"
VIENNA_POP = "https://www.statistik.at/fileadmin/pages/404/JDBev_Alter_Geschlecht_Staatsangeh_Bundesl_ab2004.ods"
VIENNA_2024 = "https://www.statistik.at/fileadmin/pages/353/Ergebnisse_im_UEberblick_Baufertigstellungen_2024.ods"
YEARS = range(2012, 2025)


def get(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "bsandova.com research"})
        try:
            path.write_bytes(urllib.request.urlopen(req, timeout=300).read())
        except urllib.error.URLError:
            # bdl.stat.gov.pl serves a chain Python's bundle cannot complete; curl uses the system store
            subprocess.run(["curl", "-sSfL", "-m", "300", "-o", str(path), url], check=True)
    return path


def prague() -> dict:
    s = pd.read_excel(get(PRAGUE, RAW / "byt_vystavba.xlsx"), "data", header=None)
    years = s.iloc[3, 2:].tolist()
    rows = {str(s.iloc[i, 0]).strip(): s.iloc[i, 2:].tolist() for i in range(len(s))}
    done = dict(zip(years, rows["Dokončené byty celkem"]))
    per = dict(zip(years, next(v for k, v in rows.items() if k.startswith("Dokončené byty na 1 000"))))
    return {y: {"completed": int(done[y]), "per_1000": round(float(per[y]), 2)} for y in YEARS}


def warsaw() -> dict:
    def series(var: int) -> dict[int, float]:
        path = get(BDL.format(var), RAW / f"bdl_{var}.json")
        return {int(v["year"]): float(v["val"]) for v in json.loads(path.read_text())["results"][0]["values"]}

    done, municipal, tbs, pop = series(748601), series(748616), series(748619), series(72305)
    return {y: {"completed": int(done[y]), "municipal": int(municipal[y]), "tbs": int(tbs[y]),
                "per_1000": round(done[y] / ((pop[y - 1] + pop[y]) / 2) * 1000, 2)} for y in YEARS}


def vienna() -> tuple[dict, dict]:
    s = pd.read_excel(get(VIENNA_DONE, RAW / "whg11-24.ods"), engine="odf", header=None)
    wien = list(s.iloc[1]).index("Wien")
    new, year = {}, None
    for i in range(len(s)):
        a, b = str(s.iloc[i, 0]).strip(), str(s.iloc[i, 1])
        if a == "nan" and re.fullmatch(r"20\d\d\d?(\.0)?", b):
            year = int(b[:4])
        elif year and a == "in neuen Gebäuden":
            new[year] = float(s.iloc[i, wien])
    p = pd.read_excel(get(VIENNA_POP, RAW / "jdbev.ods"), "W", engine="odf", header=None)
    pop = {int(float(y)): float(v) for y, v in zip(p.iloc[1, 1:], p.iloc[3, 1:]) if pd.notna(y)}
    series = {y: {"completed_new_buildings": round(new[y]), "per_1000": round(new[y] / pop[y] * 1000, 2)}
              for y in YEARS}
    b = pd.read_excel(get(VIENNA_2024, RAW / "ueberblick2024.ods"), "Tabelle_2", engine="odf", header=None)
    col = list(b.iloc[1]).index("Wien")
    builders = {str(b.iloc[i, 0]).strip().rstrip("1"): float(b.iloc[i, col]) for i in range(2, 7)}
    return series, builders


def main() -> None:
    pr, wa = prague(), warsaw()
    vi, vi_builders = vienna()
    total = vi_builders["Wohnungen insgesamt"]
    out = {
        "years": list(YEARS),
        "prague": pr, "warsaw": wa, "vienna": vi,
        "builders_2024": {
            "vienna": {"total": round(total),
                       "non_profit_share": round(vi_builders["gemeinnützige Bauvereinigungen"] / total, 3),
                       "public_share": round(vi_builders["öffentlicher Sektor"] / total, 3),
                       "companies_share": round(vi_builders["sonstige juristische Rechtspersönlichkeiten"] / total, 3),
                       "private_persons_share": round(vi_builders["Privatpersonen"] / total, 3)},
            "warsaw": {"total": wa[2024]["completed"],
                       "municipal_and_tbs_share": round((wa[2024]["municipal"] + wa[2024]["tbs"]) / wa[2024]["completed"], 4)},
        },
        "mean_per_1000_2015_2024": {c: round(sum(d[y]["per_1000"] for y in range(2015, 2025)) / 10, 2)
                                    for c, d in [("prague", pr), ("warsaw", wa), ("vienna", vi)]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ["mean_per_1000_2015_2024", "builders_2024"]}, ensure_ascii=False))
    print({y: (pr[y]["per_1000"], vi[y]["per_1000"], wa[y]["per_1000"]) for y in YEARS})


if __name__ == "__main__":
    main()
