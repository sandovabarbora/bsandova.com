"""Part 3 extended, the grantor side: the city's closing accounts (závěrečný účet) 2014-2025 and its approved budgets
2015-2026, every document on their pages, downloaded as published (docs/research/prague-districts-design.md, §4).

The per-grant lists by district live in part III of each closing account (DZ III, "městské části"; section 5,
"vybrané ekonomické údaje", and the part III tables). The allocation tables ("finanční vztahy k MČ") are annexes of
each approved budget and of the budget proposal. The year-end settlement with the districts is an annex of each
closing account.

praha.eu renders its listing pages in the browser, so the year pages were found once with a headless browser and are
listed here; each /w/ page itself is plain HTML and is read directly.

Writes tools/data/praha3x/city/{kind}_{year}/{slug}.{ext} and tools/data/praha3x/city/manifest.csv. Downloads only;
nothing is aggregated.

Usage:
    uv run --with pandas python tools/praha/districts_city.py
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import hashlib
import html
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get("PRAHA3X", ROOT / "tools" / "data" / "praha3x")) / "city"
W = "https://praha.eu/w/"
CLOSING = {  # závěrečný účet, by year of the accounts
    2014: "index_2048529", 2015: "index_2190869", 2016: "index_2451056",
    2017: "zprava_o_plneni_rozpoctu_za_rok_2017_2541133", 2018: "zprava_o_plneni_rozpoctu_a_vyuctovani_2945683",
    2019: "zprava_o_plneni_rozpoctu_a_vyuctovani_3130974", 2020: "zprava_o_plneni_rozpoctu_a_vyuctovani_3274099",
    2021: "zprava_o_plneni_rozpoctu_a_vyuctovani_3426307", 2022: "zprava_o_plneni_rozpoctu_a_vyuctovani_3486610",
    2023: "zprava-o-plneni-rozpoctu-a-vyuctovani-vysledku-hospodareni-hl-m-prahy-za-rok-2023-zaverecny-ucet-1",
    2024: "zprava-o-plneni-rozpoctu-a-vyuctovani-vysledku-hospodareni-hl-m-prahy-za-rok-2024-zaverecny-ucet",
    2025: "zprava-o-plneni-rozpoctu-a-vyuctovani-vysledku-hospodareni-hl-m-prahy-za-rok-2025-zaverecny-ucet",
}
APPROVED = {  # schválený rozpočet vlastního hl. m. Prahy, by budget year
    2015: "schvaleny_rozpocet_vlastniho_hlavniho_2046802", 2016: "schvaleny_rozpocet_vlastniho_hlavniho_2118028",
    2017: "schvaleny_rozpocet_vlastniho_hlavniho_2345928", 2018: "schvaleny_rozpocet_vlastniho_hlavniho_2558030",
    2019: "schvaleny_rozpocet_vlastniho_hlavniho_2892718", 2020: "schvaleny_rozpocet_vlastniho_hlavniho_3093165",
    2021: "schvaleny_rozpocet_vlastniho_hlavniho_3218562", 2022: "schvaleny_rozpocet_vlastniho_hlavniho_3366145",
    2023: "schvaleny_rozpocet_vlastniho_hlavniho_2023_3550122",
    2024: "schvaleny_rozpocet_vlastniho_hlavniho_2024_3653389",
    2025: "schvaleny-rozpocet-vlastniho-hlavniho-mesta-prahy-na-rok-2025",
    2026: "schvaleny-rozpocet-vlastniho-hlavniho-mesta-prahy-na-rok-2026",
}
PROPOSAL = {  # návrh rozpočtu vlastního hl. m. Prahy a finančních vztahů k MČ, by budget year
    2015: "k_navrhu_rozpoctu_vlastniho_hl_m_prahy_2008220", 2016: "k_navrhu_rozpoctu_vlastniho_hl_m_prahy_2108153",
    2017: "k_navrhu_rozpoctu_vlastniho_hl_m_prahy_2017_2325123",
    2018: "k_navrhu_rozpoctu_vlastniho_hl_m_prahy_2018_2546516",
    2019: "k_navrhu_rozpoctu_vlastniho_hl_m_prahy_2019_2853552",
    2020: "navrh_rozpoctu_vlastniho_hl_m_prahy_2020_3055947", 2021: "navrh_rozpoctu_vlastniho_hmp_2021_3207591",
    2022: "navrh_rozpoctu_vlastniho_hmp_2022_3339003", 2023: "navrh_rozpoctu_vlastniho_hmp_2023_3532035",
    2024: "navrh_rozpoctu_hl_m_prahy_2024_3653386",
    2025: "navrh-rozpoctu-vlastniho-hl-m-prahy-na-rok-2025-financnich-vztahu-k-mestskym-castem-hl-m-prahy-na-rok-2025"
          "-a-strednedobeho-vyhledu-hl-m-prahy-do-roku-2030",
    2026: "navrh-rozpoctu-vlastniho-hl-m-prahy-na-rok-2026-financnich-vztahu-k-mestskym-castem-hl-m-prahy-z-rozpoctu-vl"
          "-hl-m-prahy-na-rok-2026-a-strednedobeho-vyhledu-rozpoctu-vlastniho-hl-m-prahy-do-roku-2031",
}
SKIP = ("koalicni_smlouva", "kompetence-rady", "manual_pro_interpelujici", "programove_prohlaseni")
EXT = {"application/pdf": "pdf", "application/vnd.ms-excel": "xls", "application/zip": "zip",
       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
       "application/msword": "doc", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}
AGENT = {"User-Agent": "Mozilla/5.0 (bsandova.com research)"}


def fetch(url: str) -> tuple[bytes, str]:
    """The body and content type; ('', 'missing') if the portal answers 404 (some linked files are gone)."""
    for attempt in range(5):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=300)
            return r.read(), r.headers.get_content_type()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b"", "missing"
            time.sleep(4 * (attempt + 1))
        except Exception:  # noqa: BLE001 - the portal drops the odd request
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(url)


def documents(page: str) -> list[tuple[str, str]]:
    text = fetch(W + page)[0].decode("utf-8", "replace")
    out = {}
    for href, label in re.findall(r'href="([^"]*/documents/d/praha/[^"]+)"[^>]*>([^<]*)', text):
        slug = href.rstrip("/").split("/")[-1]
        if not slug.startswith(SKIP):
            out.setdefault(slug, html.unescape(label).strip())
            out[slug] = out[slug] or html.unescape(label).strip()
    return sorted(out.items())


def main() -> None:
    rows = []
    for kind, pages in [("closing", CLOSING), ("approved", APPROVED), ("proposal", PROPOSAL)]:
        for year, page in pages.items():
            folder = RAW / f"{kind}_{year}"
            folder.mkdir(parents=True, exist_ok=True)
            for slug, label in documents(page):
                done = list(folder.glob(slug + ".*"))
                if done:
                    path, ctype = done[0], ""
                else:
                    body, ctype = fetch(f"https://praha.eu/documents/d/praha/{slug}")
                    path = folder / f"{slug}.{'missing' if ctype == 'missing' else EXT.get(ctype, 'bin')}"
                    path.write_bytes(body)
                    time.sleep(0.3)
                data = path.read_bytes()
                rows.append({"kind": kind, "year": year, "page": W + page, "label": label, "slug": slug,
                             "file": str(path.relative_to(RAW)), "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
    m = pd.DataFrame(rows)
    m.to_csv(RAW / "manifest.csv", index=False)
    print(m.groupby("kind").size().to_dict(), round(m.bytes.sum() / 1e6), "MB")


if __name__ == "__main__":
    main()
