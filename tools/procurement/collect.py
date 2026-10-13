"""Download Registr smluv monthly dumps (design §3) and record a manifest. Reads no contract.

    nice -n 20 python3 tools/procurement/collect.py 2020-01 2026-09
    nice -n 20 python3 tools/procurement/collect.py --only 2024-05 2025-10   # the two structure dumps of §11

The index at https://data.smlouvy.gov.cz/ lists each dump with its SHA-1 and generation time. Dumps are regenerated
(the index shows 2026 generation times for 2017 months), so the manifest keeps the hash of the file actually
downloaded, its SHA-256, and the index entry seen at download time; hashed_at is when the file was hashed, after it arrived.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "data" / "procurement"
INDEX = "https://data.smlouvy.gov.cz/"
UA = "bsandova.com research"  # no e-mail address in any request (design §3.4)
NS = "{http://portal.gov.cz/rejstriky/ISRS/1.2/}"
PAUSE_S = 5


def fetch(url: str, dest: Path) -> None:
    subprocess.run(["curl", "-s", "-f", "-L", "--max-time", "1800", "-A", UA, "-o", str(dest), url], check=True)


def read_index(path: Path) -> dict[str, dict]:
    out = {}
    for d in ET.parse(path).getroot().iter(f"{NS}dump"):
        if d.find(f"{NS}den") is not None:
            continue
        get = {el.tag.removeprefix(NS): el.text or "" for el in d}.get
        key = f"{int(get('rok')):04d}-{int(get('mesic')):02d}"
        out[key] = {"url": get("odkaz"), "sha1_index": get("hashDumpu"), "bytes_index": int(get("velikostDumpu")),
                    "generated": get("casGenerovani"), "complete_month": get("dokoncenyMesic") == "1"}
    return out


def months(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    res = []
    while (y, m) <= (ly, lm):
        res.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return res


def digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("first")
    ap.add_argument("last")
    ap.add_argument("--only", action="store_true", help="download only the two months given, not the range")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / "index.xml"
    fetch(INDEX, idx_path)
    index = read_index(idx_path)
    wanted = [a.first, a.last] if a.only else months(a.first, a.last)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for key in wanted:
        entry = index[key]
        if not entry["complete_month"]:
            raise SystemExit(f"{key}: the index marks the month as incomplete; the freeze of §3.3 is not met")
        dest = OUT / f"dump_{key.replace('-', '_')}.xml"
        if not dest.exists():
            fetch(entry["url"], dest)
            time.sleep(PAUSE_S)
        sha1 = digest(dest, "sha1")
        manifest[key] = {**entry, "file": dest.name, "bytes": dest.stat().st_size, "sha1": sha1,
                         "sha256": digest(dest, "sha256"), "sha1_matches_index": sha1 == entry["sha1_index"],
                         "hashed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        print(key, dest.stat().st_size, sha1[:12], "index match" if sha1 == entry["sha1_index"] else "INDEX DIFFERS")
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
