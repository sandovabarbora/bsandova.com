"""Write sitemap.xml and robots.txt from the pages' own canonical URLs, at build time.

A page is listed if it declares <link rel="canonical"> and is not marked noindex. lastmod is the date of the last
commit that touched the file, so the sitemap cannot drift from the site.

Usage:
    python3 tools/sitemap.py
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://bsandova.com"
SKIP = ("variants/", "tools/", "a24/", "assets/", "classic.html", "404.html")


def last_commit_date(path: str) -> str:
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip()


def entries() -> list[tuple[str, str]]:
    files = subprocess.run(["git", "ls-files", "*.html"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    rows = []
    for f in files:
        if f.startswith(SKIP) or f in SKIP:
            continue
        html = (ROOT / f).read_text()
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        if not canon or re.search(r'<meta name="robots" content="[^"]*noindex', html):
            continue
        rows.append((canon.group(1), last_commit_date(f)))
    return sorted(set(rows))


def main() -> None:
    rows = entries()
    urls = "".join(f"  <url><loc>{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>\n" for u, d in rows)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'
    )
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    print(f"sitemap.xml: {len(rows)} urls")


if __name__ == "__main__":
    main()
