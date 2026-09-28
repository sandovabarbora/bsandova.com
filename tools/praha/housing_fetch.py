"""Part 4 extended: download every raw file the registered design needs (docs/research/prague-housing-design.md),
and nothing else. Computes no statistic: it writes the files and their SHA-256 list, so that the design can be
committed against a fixed set of inputs.

Sources (downloaded into tools/data/praha4x/, not committed):
  - Czech Statistical Office (ČSÚ), open data (data.csu.gov.cz): building permits by kraj, monthly 2005-2025 (STA08)
    and 2026 (STA08A2); dwellings started and completed, Czechia 1990- (STA09A), by kraj monthly 2006-2025 (STA09B)
    and 2026 (STA09A1, STA09B2); dwellings completed by municipality 1997-2024 (200068-25); price indices of flats
    by kraj, quarterly (icncr); property prices 2022-2024 by kraj and okres (01401625).
  - Statistik Austria (Baumaßnahmenstatistik): dwellings permitted by Bundesland, quarterly 2010-2026 and 2005-2009;
    dwellings completed by Bundesland 2005-2010 and 2011-2024; demolitions 2011-2024; results 2024 (completions by
    builder, construction time by builder) and 2025 (permits by builder).
  - Eurostat: Census 2021 dwellings by period of construction (cens_21dwop_r3) and by building type
    (cens_21dwob_r3); Census 2011 dwellings (cens_11dwob_r3); population by NUTS 3 (demo_r_pjanaggr3); GDP by
    NUTS 3 (nama_10r_3gdp).
  - Statistics Poland, Local Data Bank (BDL API): powiat level (380 units) dwellings permitted, started and completed
    by form of construction; median price per m2 of flats sold in market transactions; population; dwelling stock;
    and, at gmina level, the average construction period of new residential buildings.

Part 2's RÚIAN building points (tools/data/praha2x/buildings_5514.pkl, built by rings_data.py) are reused for the
Prague-internal analysis and are hashed here too.

Usage (from a worktree, point DATA at the main checkout's gitignored tools/data):
    DATA=/path/to/bsandova.com/tools/data uv run python tools/praha/housing_fetch.py
"""

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("DATA", ROOT / "tools" / "data"))
RAW = DATA / "praha4x"
SHA = ROOT / "docs" / "research" / "prague-housing-files.sha256"
REUSED = [DATA / "praha4" / "byt_vystavba.xlsx", DATA / "praha2x" / "buildings_5514.pkl"]

CSU_OD = "https://data.csu.gov.cz/opendata/sady/{}/distribuce/csv"
CSU_SCHEMA = "https://data.csu.gov.cz/opendata/sady/{}/schema/csv"
CSU_SETS = ["STA08", "STA08A1", "STA08A2", "STA09A", "STA09A1", "STA09A2", "STA09B", "STA09B1", "STA09B2"]
CSU_DOCS = "https://csu.gov.cz/docs/107508/"
CSU_FILES = {
    "icncr.xlsx": "ff9d20f8-11cd-883e-f31e-04bca2e37ea8/icncr071525.xlsx?version=1.1",
    "ceny_nemovitosti_2022_2024_data.zip": "ca28fbfa-ec68-d9d7-b3a8-ede5ad4f0969/01401625_data.zip?version=1.0",
    "dokoncene_byty_obce.zip": "f1c51fa3-594b-4cc2-c61d-3511620fed26/200068-25data090825.zip?version=1.0",
}
AT = "https://www.statistik.at/fileadmin/pages/"
AT_FILES = ["352/WhgJ10-J26_150626_Q1.ods", "352/Whg05-09_150621.ods",
            "352/Ergebnisse_im_UEberblick_Baubewilligungen_2025.ods", "353/Whg05-10_Bdl_150924.ods",
            "353/Whg11-24_Bdl_150925.ods", "353/Ergebnisse_im_UEberblick_Baufertigstellungen_2024.ods",
            "353/WhgAbgang011111-311224_Bdl_150925.ods"]
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{}?format=JSON&lang=EN"
EUROSTAT_SETS = ["cens_21dwop_r3", "cens_21dwob_r3", "cens_11dwob_r3", "demo_r_pjanaggr3", "nama_10r_3gdp"]
BDL = "https://bdl.stat.gov.pl/api/v1/data/by-variable/{}?unit-level={}&format=json&lang=en&page-size=100&page={}"
# powiat level (5): completions by form (P3824), starts Jan-Dec by form (P3822), permits Jan-Dec by form (P3816),
# median price per m2, market transactions (P3787: total, primary, secondary), population, dwelling stock
BDL_POWIAT = {
    "completed": [748601, 748604, 748607, 748610, 748616, 748619, 748622],
    "started": [747729, 747730, 747731, 747732, 747733, 747734, 747735, 747736],
    "permitted": [747633, 747634, 747635, 747636, 747638, 747639, 747640],
    "price_m2": [633677, 633682, 633687],
    "population": [72305],
    "stock": [60811],
}
# gmina level (6): average construction period, single- and multi-family (months)
BDL_GMINA = {"construction_months": [747069, 747070]}


def get(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "bsandova.com research"})
        try:
            path.write_bytes(urllib.request.urlopen(req, timeout=300).read())
        except urllib.error.URLError:
            # bdl.stat.gov.pl serves a chain Python's bundle cannot complete; curl uses the system store
            subprocess.run(["curl", "-sSfL", "-m", "300", "-A", "bsandova.com research", "-o", str(path), url],
                           check=True)
    return path


def bdl(var: int, level: int, tries: int = 6) -> Path:
    """All pages of one BDL variable at one unit level, merged into one JSON file."""
    path = RAW / "bdl" / f"{var}_L{level}.json"
    if path.exists():
        return path
    results, page = [], 0
    while True:
        for attempt in range(tries):  # the anonymous BDL quota drops connections when exceeded; wait it out
            try:
                part = get(BDL.format(var, level, page), RAW / "bdl" / "pages" / f"{var}_L{level}_{page}.json")
                break
            except subprocess.CalledProcessError:
                time.sleep(60 * (attempt + 1))
        else:
            raise RuntimeError(f"BDL variable {var}, page {page}: no response")
        d = json.loads(part.read_text())
        results += d["results"]
        if "next" not in d.get("links", {}):
            break
        page += 1
        time.sleep(0.4)
    path.write_text(json.dumps({"variableId": var, "level": level, "results": results}, ensure_ascii=False))
    return path


def main() -> None:
    files = []
    for s in CSU_SETS:
        files += [get(CSU_OD.format(s), RAW / "csu" / f"{s}.csv"),
                  get(CSU_SCHEMA.format(s), RAW / "csu" / f"{s}.schema.json")]
    files += [get(CSU_DOCS + u, RAW / "csu" / name) for name, u in CSU_FILES.items()]
    files += [get(AT + f, RAW / "at" / Path(f).name) for f in AT_FILES]
    files += [get(EUROSTAT.format(s), RAW / "eurostat" / f"{s}.json") for s in EUROSTAT_SETS]
    for ids in BDL_POWIAT.values():
        files += [bdl(v, 5) for v in ids]
    for ids in BDL_GMINA.values():  # replication only (H6): recorded as missing if the quota blocks it
        for v in ids:
            try:
                files.append(bdl(v, 6, tries=1))
            except RuntimeError as e:
                print(f"missing: {e}")
    files += [p for p in REUSED if p.exists()]
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  tools/data/{p.relative_to(DATA)}" for p in files]
    SHA.write_text("\n".join(lines) + "\n")
    print(f"{len(files)} files, hashes in {SHA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
