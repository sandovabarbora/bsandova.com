"""Pop, measured: collect the kworb.net chart pages once (part 1 design §2), politely, and hash them.

Sources: kworb.net daily totals and current daily charts (global and every country) and the track pages of the global
number ones. Raw pages go to tools/data/pop/raw/ (not committed). Tour pages, World Bank income and artist song
lists come from collect_extra.py. Then `hashes.py` writes the published hash list.

    python3 tools/pop/collect.py
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "pop" / "raw"
UA = {"User-Agent": "bsandova.com research (contact via bsandova.com)"}
KW = "https://kworb.net/spotify/"


def get(url: str) -> bytes:
    for wait in (0, 30, 90):
        time.sleep(wait)
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            time.sleep(3)
            return data
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
    raise RuntimeError(f"gave up: {url}")


def save(name: str, url: str) -> bytes | None:
    path = RAW / name
    if path.exists():
        return path.read_bytes()
    try:
        data = get(url)
    except urllib.error.HTTPError as e:   # a few small markets have no totals page; they are listed as missing
        if e.code != 404:
            raise
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    index = save("kworb-index.html", KW).decode("utf-8", "replace")
    countries = sorted(set(re.findall(r"country/([a-z]+)_daily\.html", index)))
    missing = []
    for cc in countries:
        if save(f"totals/{cc}.html", f"{KW}country/{cc}_daily_totals.html") is None or \
                save(f"daily/{cc}.html", f"{KW}country/{cc}_daily.html") is None:
            missing.append(cc)
    countries = [c for c in countries if c not in missing]
    countries = countries if "global" in countries else ["global", *countries]
    save("totals/global.html", f"{KW}country/global_daily_totals.html")
    save("daily/global.html", f"{KW}country/global_daily.html")
    glob = (RAW / "totals" / "global.html").read_text(encoding="utf-8")
    ones = re.findall(r'href="\.\./track/([A-Za-z0-9]+)\.html">[^<]*</a></div></td>\s*<td>\d+</td>\s*<td>\d+</td>\s*<td>1</td>', glob)
    for tid in ones:
        save(f"tracks/{tid}.html", f"{KW}track/{tid}.html")
    (RAW / "collected.json").write_text(json.dumps({"date": date.today().isoformat(), "countries": countries,
                                                    "missing": missing, "global_number_ones": len(ones)}, indent=1))
    print(len(countries), "charts,", len(ones), "number ones")


if __name__ == "__main__":
    main()
