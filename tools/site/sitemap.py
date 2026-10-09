"""Write sitemap.xml and robots.txt from the pages' own canonical URLs, at build time.

A page is listed if it declares <link rel="canonical"> and is not marked noindex. lastmod is the date of the last
commit that touched the file, so the sitemap cannot drift from the site.

Usage:
    python3 tools/site/sitemap.py
"""

from shared import ROOT, SITE, canonical, last_commit, noindex, tracked_html, write

SKIP = ("tools/", "assets/", "404.html")


def entries() -> list[tuple[str, str]]:
    rows = []
    for f in tracked_html():
        if f.startswith(SKIP) or f in SKIP:
            continue
        html = (ROOT / f).read_text(encoding="utf-8")
        url = canonical(html)
        if not url or noindex(html):
            continue
        rows.append((url, last_commit(f, "%cs")))
    return sorted(set(rows))


def main() -> None:
    rows = entries()
    urls = "".join(f"  <url><loc>{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>\n" for u, d in rows)
    write(
        ROOT / "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'
    )
    write(ROOT / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    print(f"sitemap.xml: {len(rows)} urls")


if __name__ == "__main__":
    main()
