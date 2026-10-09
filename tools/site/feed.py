"""Write feed.xml (Atom) and each article's JSON-LD from the pages' own meta tags and git dates, at build time.

An article is a page under texts/ with og:type "article" and a canonical URL. Updated is the date of the last commit
that touched it, so it cannot drift from the site. No published date: most pages were added in one import commit, so
the first commit says when the site moved, not when the text appeared.
The JSON-LD block is replaced in place (between the ld markers), so running this twice changes nothing. Deploy-only:
committed pages carry no ld block (its dateModified has no fixed point in a commit); build.sh adds it on the way out.

Usage:
    python3 tools/site/feed.py
"""

import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://bsandova.com"
AUTHOR = {"@type": "Person", "name": "Barbora Šandová", "url": f"{SITE}/"}
LD = re.compile(r"\n?<!-- ld -->.*?<!-- /ld -->\n?", re.S)
ALTERNATE = '<link rel="alternate" type="application/atom+xml" title="Barbora Šandová" href="/feed.xml">'


def last_commit(path: str) -> str:
    args = ["git", "log", "-1", "--format=%cI", "--", path]
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def meta(s: str, key: str, attr: str = "property") -> str:
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', s)
    return html.unescape(m.group(1)) if m else ""


def articles() -> list[dict]:
    rows = []
    for page in sorted((ROOT / "texts").rglob("*.html")):
        s = page.read_text()
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if meta(s, "og:type") != "article" or not canon or "noindex" in meta(s, "robots", "name"):
            continue
        rel = str(page.relative_to(ROOT))
        rows.append(
            {
                "path": page,
                "url": canon.group(1),
                "title": meta(s, "og:title"),
                "summary": meta(s, "description", "name") or meta(s, "og:description"),
                "image": meta(s, "og:image"),
                "updated": last_commit(rel),
            }
        )
    return sorted(rows, key=lambda a: a["updated"], reverse=True)


def json_ld(a: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": a["title"],
        "description": a["summary"],
        "url": a["url"],
        "image": a["image"] or None,
        "dateModified": a["updated"],
        "author": AUTHOR,
    }
    body = json.dumps({k: v for k, v in data.items() if v}, ensure_ascii=False).replace("</", "<\\/")
    return f'\n<!-- ld -->{ALTERNATE}\n<script type="application/ld+json">{body}</script><!-- /ld -->'


def write(path: Path, text: str) -> bool:
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def stamp(a: dict) -> bool:
    s = LD.sub("", a["path"].read_text())
    return write(a["path"], s.replace("</head>", json_ld(a) + "\n</head>", 1))


def atom(rows: list[dict]) -> str:
    def esc(x: str) -> str:
        return html.escape(x, quote=True)

    entries = "".join(
        f"""  <entry>
    <title>{esc(a["title"])}</title>
    <link href="{esc(a["url"])}"/>
    <id>{esc(a["url"])}</id>
    <updated>{a["updated"]}</updated>
    <summary>{esc(a["summary"])}</summary>
  </entry>
"""
        for a in rows
    )
    updated = max((a["updated"] for a in rows), default="")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Barbora Šandová</title>
  <subtitle>Things made out of data</subtitle>
  <link href="{SITE}/"/>
  <link rel="self" href="{SITE}/feed.xml"/>
  <id>{SITE}/</id>
  <updated>{updated}</updated>
  <author><name>Barbora Šandová</name></author>
{entries}</feed>
"""


def main() -> None:
    rows = articles()
    n = sum(stamp(a) for a in rows)
    write(ROOT / "feed.xml", atom(rows))
    print(f"feed.xml + JSON-LD: {len(rows)} articles, {n} pages changed")


if __name__ == "__main__":
    main()
