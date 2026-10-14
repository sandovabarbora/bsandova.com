"""Downloads of the priorities design (§2): Eurobarometer Volume A, ParlaCAP-CZ speeches, Eurostat gov_10a_exp.

Writes the raw files under tools/data/priorities/ (eb/, parlacap/, eurostat/) and their URL, size and SHA-256 to
docs/research/priorities-manifest.json. Files already present are kept, not fetched again; nothing in them is read
here beyond the bytes hashed.

    nice -n 20 uv run --no-project --with certifi python -I tools/priorities/fetch.py
"""
from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.request
from datetime import date
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools/data/priorities"
MANIFEST = ROOT / "docs/research/priorities-manifest.json"
UA = {"User-Agent": "bsandova.com research"}
TLS = ssl.create_default_context(cafile=certifi.where())

EB_URL = "https://webgate.ec.europa.eu/eurobarometer/api/public/odp/download?key={key}"
# Volume A of each Standard Eurobarometer wave on data.europa.eu (feasibility inventory, 14 October 2026). Every wave
# from EB62 has a Czech column in Volume A, so no Volume C file is needed. True: the download is a zip of an .xls/.xlsx.
EB = {
    62: ("6972D6E2B0D388EC310E6D718B4F2927", True), 63: ("4223C8D7661B30AFB7834EC33D33D3FF", True),
    64: ("30225C7330B9F451768C04BCA13F35B1", True), 65: ("43D32D1E78A7137E67328AB6AEFB0EB7", True),
    66: ("DD7995DC59122A1F34430155EB67B616", True), 67: ("4ACA4EF215CDE67C7CE6F0593141B754", True),
    68: ("E0D8E5ED087B5403CBD9F53BB2C7220E", True), 69: ("503E113F9B79B73D0E676002376CA1FC", True),
    70: ("BB8AF4966270A2772B6718DA53FA587A", True), 71: ("5B493019D2771CB3835DA26F2E5B8DDD", True),
    72: ("EDAF5DE6E375CE9271EEB6F8C854EFEE", True), 73: ("8421775A8B1E12A04F124BB7C86F13DF", True),
    74: ("DA6AD785FBBCF420F2E7B95B24965BC7", True), 75: ("C6350E8249A3DE7CE09B2DEE9B3C5F50", True),
    76: ("DF67813612DE969F4D50752DC5BBF0C8", True), 77: ("24464CF53F8F579341CA8A859F406846", True),
    78: ("6EF76676DFD366222F2C207F8203DAB5", True), 79: ("B9900837DFA241A7C7BFD96D505FF6B3", True),
    80: ("16BE61B137D0A53B5329F17F8BB3C76E", True), 81: ("5DBA0562EF6C2AB930EF7347E81310E8", True),
    82: ("AEC01074111729CC73EEFF1C9340D41C", True), 83: ("546421185E5D70B523A194E58C3AACD1", True),
    84: ("DD0D0511ADA485576EDBCFB34FA84F62", True), 85: ("E7795D544EC9141DE2B3F718F1C69E80", True),
    86: ("0DFE05B6D69DACACAF2CBDAC57B4ED37", True), 87: ("F01145E536AAFD4E292E91165A232CA5", True),
    88: ("E84CDFA31A2687A1864EC02078F99BEA", True), 89: ("ED91B120BAF1F44FFD008C77E9BA34FE", True),
    90: ("AA59CDC91B966A9A7064F4F700A916C3", True), 91: ("BD32911BEED333EC8E89A49A4EE084F5", True),
    92: ("3A3D4A80BC3648F6E1BF5F2157F58A1E", True), 93: ("30C0FB6220D55B50B2DBE9A093B20A11", True),
    94: ("ACD89D783A5E2C6E54B6B9BA1C5751EF", False), 95: ("3DBFC38A29B12076FF0CF68FE03E83CF", False),
    96: ("380C6267C97A89EEC7117E72F4948595", False), 97: ("BFB9C0CCD4CDFA7AE9B5828600C2BCC7", False),
    98: ("8B1605BC8964BBFFEC49C32E79FF9A63", False), 99: ("0CCD7D6A9EDFF30E68F80A00649E91B6", False),
    100: ("63ACA1A088544CA14E217226F8E32A1F", False), 101: ("202289A0E60356141402B692C20F5193", False),
    102: ("A2534D981B6C0CF8878DEB8447FB08F4", False), 103: ("AF452C0A6DD70E5D13273C5DF2086956", False),
    104: ("A68C45C80315C6F37BBA366C32491DED", False),
}

CROSSDA = "https://data.crossda.hr"
PARLACAP_DOI = "doi:10.23669/1ZTELP"
PARLACAP_FILE = "ParlaCAP-CZ_speeches.tsv.zip"

EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_exp"
            "?format=JSON&lang=EN&geo=CZ&sector=S13&na_item=TE&unit=MIO_NAC")


def get(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600, context=TLS) as r:
                return r.read()
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))
    raise AssertionError


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, path: Path, md5: str | None = None) -> bool:
    """Download url to path unless present; return whether it was downloaded now."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    body = get(url)
    if md5 is not None and hashlib.md5(body).hexdigest() != md5:
        raise ValueError(f"MD5 mismatch for {url}")
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(body)
    tmp.rename(path)
    return True


def parlacap_file() -> tuple[str, str]:
    """The CROSSDA download URL and MD5 of the Czech speech file, looked up in the dataset's latest version."""
    meta = json.loads(get(f"{CROSSDA}/api/datasets/:persistentId/?persistentId={PARLACAP_DOI}"))["data"]
    version = meta["latestVersion"]
    for f in version["files"]:
        df = f["dataFile"]
        if df["filename"].endswith(PARLACAP_FILE):
            return f"{CROSSDA}/api/access/datafile/{df['id']}", df["md5"]
    raise LookupError(PARLACAP_FILE)


def main() -> None:
    old = {e["path"]: e for e in json.loads(MANIFEST.read_text())["files"]} if MANIFEST.exists() else {}
    jobs = [(f"eb{w}", EB_URL.format(key=key), RAW / "eb" / f"eb{w}.{'zip' if zipped else 'xlsx'}", None)
            for w, (key, zipped) in EB.items()]
    url, md5 = parlacap_file()
    jobs.append(("parlacap_cz", url, RAW / "parlacap" / PARLACAP_FILE, md5))
    jobs.append(("eurostat_gov_10a_exp_cz", EUROSTAT, RAW / "eurostat/gov_10a_exp_CZ.json", None))

    files, failed = [], []
    for name, url, path, md5 in jobs:
        rel = str(path.relative_to(ROOT))
        try:
            new = fetch(url, path, md5)
        except (OSError, ValueError) as e:
            failed.append({"name": name, "url": url, "error": str(e)})
            print(f"{name}: FAILED {e}")
            continue
        retrieved = date.today().isoformat() if new or rel not in old else old[rel]["retrieved"]
        files.append({"name": name, "url": url, "path": rel, "bytes": path.stat().st_size,
                      "sha256": sha256(path), "retrieved": retrieved})
        print(f"{name}: {path.stat().st_size:,} bytes{' (new)' if new else ''}")

    MANIFEST.write_text(json.dumps({
        "design": "docs/research/priorities-design.md",
        "note": "Raw files of the data step; tools/data/priorities/ is not committed. "
                "EB105 was not on data.europa.eu on 14 October 2026, so EB104 is the latest wave.",
        "parlacap_source": f"CROSSDA {PARLACAP_DOI}, MD5 checked against the repository",
        "files": files, "failed": failed}, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(files)} files, {len(failed)} failed -> {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
