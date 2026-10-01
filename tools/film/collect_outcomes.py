"""Release and admissions sources for the film fund study (docs/research/film-fund-design.md §2).

- UFD premiere lists 2016-2025: every film released in Czech cinemas, with date, distributor,
  original and Czech title.
- LUMIERE (European Audiovisual Observatory): every film with Czech (co-)production by production
  year 2014-2026, and from each film's page its Czech release (distributor, date, admissions),
  total European admissions and its release titles by market.

This only collects the sources. It reads no fund data and joins nothing (tools/film/link.py does,
blind to points and awards).

    uv run --no-project --with requests --with pandas --with openpyxl --with xlrd --with pyarrow \
        python tools/film/collect_outcomes.py
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "data" / "film" / "outcomes"
UA = {"User-Agent": "bsandova.com research (film fund study; contact via bsandova.com)"}
PAUSE_S = 1.0
UFD = {y: f"https://www.ufd.cz/files/article/53/{f}" for y, f in {
    2016: "premiery2016.xlsx", 2017: "premiery2017.xlsx", 2018: "premiery2018-seznam.xlsx",
    2019: "premiery2019.xlsx", 2020: "premiery2020.xlsx", 2021: "premiery2021.xlsx",
    2022: "premiery2022327.xlsx", 2023: "premiery2023358.xlsx", 2024: "premiery2024376.xlsx",
    2025: "2025368.xlsx"}.items()}
LUM = "https://lumiere.obs.coe.int"
YEARS = range(2014, 2027)


def text(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def num(s: str) -> int:
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else 0


def ufd(session: requests.Session) -> pd.DataFrame:
    rows = []
    for year, url in UFD.items():
        dest = OUT / f"ufd_premiery_{year}.xlsx"
        if not dest.exists():
            dest.write_bytes(session.get(url, timeout=60).content)
            time.sleep(PAUSE_S)
        v = pd.read_excel(dest, header=None, dtype=object)
        hdr = next(i for i in range(15) if any("originální" in str(c).lower() for c in v.iloc[i]))
        head = [str(c).lower() for c in v.iloc[hdr]]
        col = lambda key: next(k for k, h in enumerate(head) if key in h)   # noqa: E731
        c_date, c_dist, c_orig, c_cz = col("datum"), col("distributor"), col("originální"), col("český")
        for i in range(hdr + 1, len(v)):
            r = v.iloc[i]
            orig, cz = str(r.iat[c_orig]).strip(), str(r.iat[c_cz]).strip()
            if orig in ("nan", "") and cz in ("nan", ""):
                continue
            rows.append({"source": "ufd", "year": year, "date": str(r.iat[c_date])[:10], "distributor": str(r.iat[c_dist]),
                         "title_orig": orig, "title_cz": cz})
    return pd.DataFrame(rows)


def lumiere(session: requests.Session) -> pd.DataFrame:
    session.get(LUM + "/search", timeout=60)
    ids: dict[str, int] = {}
    for y in YEARS:
        r = session.post(LUM + "/search", timeout=120, data={
            "title": "", "director": "", "production_country": "CZ", "include_minority_coproducing_country": "y",
            "prod_start_year": str(y), "prod_end_year": str(y), "exp_start_year": "", "exp_end_year": ""})
        found = re.findall(r'href="/movie/(\d+)"', r.text)
        for m in found:
            ids.setdefault(m, y)
        print(f"LUMIERE {y}: {len(set(found))} films")
        time.sleep(PAUSE_S)
    rows = []
    for k, (mid, y) in enumerate(sorted(ids.items()), 1):
        dest = OUT / "lumiere" / f"{mid}.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_text(session.get(f"{LUM}/movie/{mid}", timeout=60).text, encoding="utf-8")
            time.sleep(PAUSE_S)
        s = dest.read_text(encoding="utf-8")
        t = text(re.sub(r"<(script|style).*?</\1>", "", s, flags=re.S))
        title = text(re.search(r"<h\d[^>]*>(.*?)</h\d>", s, re.S).group(1)) if re.search(r"<h\d[^>]*>(.*?)</h\d>", s, re.S) else ""
        # the market table: one row per market, "CZ <distributor> dd/mm/yyyy <total> ..."
        cz = None
        for tr in re.findall(r"<tr.*?</tr>", s, re.S):
            cells = [text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
            if cells and cells[0] == "CZ" and len(cells) >= 4 and re.match(r"\d\d/\d\d/\d{4}", cells[2]):
                cz = {"distributor": cells[1], "date": cells[2], "admissions": num(cells[3])}
        titles = {}
        for tr in re.findall(r"<tr.*?</tr>", s, re.S):
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) == 2 and re.fullmatch(r"[A-Z_,]+", cells[0]):
                for mk in cells[0].split(","):
                    titles[mk] = cells[1]
        m_tot = re.search(r"Total admissions:\s*EU 27\+GB:\s*([\d\s]+)", t)
        rows.append({"source": "lumiere", "movie_id": int(mid), "prod_year": y, "title": title,
                     "countries": (re.search(r"Producing country:\s*([A-Z, ]+?)\s+Production year", t) or [None, ""])[1],
                     "directors": (re.search(r"Director\(s\):\s*(.*?)\s+Producing country", t) or [None, ""])[1],
                     "title_cz": titles.get("CZ", ""), "titles": json.dumps(titles, ensure_ascii=False),
                     "cz_distributor": cz["distributor"] if cz else "", "cz_date": cz["date"] if cz else "",
                     "cz_admissions": cz["admissions"] if cz else 0,
                     "eu_admissions": num(m_tot.group(1)) if m_tot else 0})
        if k % 100 == 0:
            print(f"  {k}/{len(ids)} film pages")
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers.update(UA)
    u = ufd(s)
    u.to_parquet(OUT / "ufd_premieres.parquet", index=False)
    print(f"UFD: {len(u)} premieres 2016-2025")
    lum = lumiere(s)
    lum.to_parquet(OUT / "lumiere_cz.parquet", index=False)
    print(f"LUMIERE: {len(lum)} films with Czech (co-)production, {int((lum.cz_admissions > 0).sum())} with Czech admissions")
    with (OUT / "outcome-files.sha256").open("w") as f:
        for p in sorted(OUT.glob("*.xlsx")):
            f.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n")


if __name__ == "__main__":
    main()
