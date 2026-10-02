"""Download every input of design §2 and hash it. Prints names, sizes and hashes only; reads no value.

    python3 tools/eurovision/collect.py
"""
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "eurovision" / "raw"
UA = "bsandova.com research (sandovabarb@gmail.com)"
MIRO = "https://raw.githubusercontent.com/Amsterdam-Music-Lab/mirovision/d70e25d4871b84d1502dfe65c9713e217bfdd716/data/CSV"
SPIJ = "https://github.com/Spijkervet/eurovision-dataset/releases/download/2023"
UN = ("https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/"
      "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx")
WIKI = "https://en.wikipedia.org/w/api.php?action=parse&oldid={rev}&prop=text|revid&format=json&formatversion=2"
REVS = {2023: 1375641667, 2024: 1378019076, 2025: 1378018909}  # revisions fixed on 3 Oct 2026
FILES = {
    "mirovision_votes.csv": f"{MIRO}/votes.csv",
    "mirovision_jurors.csv": f"{MIRO}/jurors.csv",
    "mirovision_contestants.csv": f"{MIRO}/contestants.csv",
    "mirovision_countries.csv": f"{MIRO}/countries.csv",
    "spijkervet_votes.csv": f"{SPIJ}/votes.csv",
    "spijkervet_contestants.csv": f"{SPIJ}/contestants.csv",
    "undesa_ims_2024.xlsx": UN,
    "cepii_dist.zip": "https://www.cepii.fr/distance/dist_cepii.zip",
    "unhcr_ukr_2022.json": "https://api.unhcr.org/population/v1/population/?year=2022&coo=UKR&coa_all=true&limit=500",
    "unhcr_ukr_2024.json": "https://api.unhcr.org/population/v1/population/?year=2024&coo=UKR&coa_all=true&limit=500",
    "wb_population.json": "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?date=2015:2024&format=json&per_page=20000",
    **{f"wiki_{y}.json": WIKI.format(rev=r) for y, r in REVS.items()},
}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, url in FILES.items():
        dest = RAW / name
        if not dest.exists():
            subprocess.run(["curl", "-s", "-L", "--fail", "--max-time", "600", "-A", UA, "-o", str(dest), url], check=True)
            time.sleep(1)
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest.append({"file": name, "url": url, "bytes": dest.stat().st_size, "sha256": sha})
        print(f"{name:32s} {dest.stat().st_size:>10} {sha[:16]}")
    (RAW.parent / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
