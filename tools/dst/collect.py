"""Download the police's yearly accident-record archives (design §2) and hash them. Prints names, sizes and hashes
only; reads no record.

    python3 tools/dst/collect.py
"""
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "data" / "dst"
BASE = "https://archiv.policie.gov.cz/soubor/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
# Yearly files as listed on the archive pages on 2 Oct 2026 (2016 is the earliest with records).
FILES = {2016: "datagis2016-rar.aspx", 2017: "datagis-rok-2017-rar.aspx", 2018: "datagis-rok-2018-rar.aspx",
         2019: "datagis-rok-2019-rar.aspx", 2020: "data-gis-2020-rar.aspx", 2021: "data-web-2021-rar.aspx",
         2022: "data-gis-2022-rar.aspx", 2023: "data-na-web-2023-rar.aspx", 2024: "data-web-2024-rar.aspx",
         2025: "data-web-12-2025-rar.aspx"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for year, name in FILES.items():
        dest = OUT / f"{year}.rar"
        if not dest.exists():
            subprocess.run(["curl", "-s", "-L", "--max-time", "300", "-A", UA, "-o", str(dest), BASE + name],
                           check=True)
            time.sleep(2)
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest.append({"year": year, "url": BASE + name, "bytes": dest.stat().st_size, "sha256": sha})
        print(year, dest.stat().st_size, sha[:16])
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
