"""Render a 1200x630 share card per article: its photograph, its title, the site mark.

Reads each article's og:title and its film photograph (assets/photo/<name>.jpg), writes assets/og/<slug>.jpg,
and points the article's og:image / twitter:image at it. The front page gets assets/og/home.jpg.

Usage (needs Playwright's Chromium; run from the repo root):
    uv run --with playwright python tools/site/og_cards.py
"""

import argparse
import html
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "og"
SITE = "https://bsandova.com"

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500&family=JetBrains+Mono&family=Fraunces:opsz,wght@9..144,500&display=swap" rel="stylesheet">
<style>
*{{margin:0;box-sizing:border-box}}
body{{width:1200px;height:630px;position:relative;overflow:hidden;background:#000;color:#fff;font-family:"Inter Tight",Helvetica,sans-serif}}
.ph{{position:absolute;inset:0;background:url({photo}) center/cover}}
.sh{{position:absolute;inset:0;background:linear-gradient(0deg,rgba(0,0,0,.82) 0%,rgba(0,0,0,.35) 50%,rgba(0,0,0,.15) 100%)}}
.mark{{position:absolute;top:40px;left:56px;font:500 34px/1 "Fraunces",serif;letter-spacing:-.02em}}
.site{{position:absolute;top:48px;right:56px;font:400 17px "JetBrains Mono",monospace;color:rgba(255,255,255,.8)}}
.lbl{{position:absolute;left:56px;bottom:{lbl_bottom}px;font:500 20px/1 "Inter Tight";text-transform:uppercase;letter-spacing:.02em;color:rgba(255,255,255,.75)}}
h1{{position:absolute;left:56px;right:56px;bottom:52px;font:500 {size}px/.95 "Inter Tight";letter-spacing:-.05em}}
</style></head><body><div class="ph"></div><div class="sh"></div>
<div class="mark">bŠ</div><div class="site">bsandova.com</div>
<div class="lbl">{label}</div><h1>{title}</h1></body></html>"""


def fit(title: str) -> tuple[int, int]:
    """Font size and label offset so that long titles stay on at most three lines."""
    n = len(title)
    size = 96 if n <= 28 else 80 if n <= 48 else 64 if n <= 70 else 54
    lines = 1 if n * size * 0.5 < 1088 else 2 if n * size * 0.5 < 2176 else 3
    return size, 52 + int(lines * size * 0.95) + 22


def article_info(page: Path) -> tuple[str, str, str] | None:
    """(og:title, photo file name, kicker) for an article with a film photograph, else None."""
    s = page.read_text()
    title = re.search(r'<meta property="og:title" content="([^"]+)"', s)
    photo = re.search(r'class="film film-page"[^>]*><div class="shot" style="[^"]*assets/photo/([a-z0-9-]+)\.jpg', s)
    kicker = re.search(r'<p class="kicker">(.*?)</p>', s, re.S)
    if not (title and photo):
        return None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    if " — " in title.group(1) and h1:  # a site-suffixed og:title: the headline reads better on a card
        return html.unescape(re.sub(r"<[^>]+>", "", h1.group(1)).strip()), photo.group(1), \
            (re.sub(r"<[^>]+>", "", kicker.group(1)).split("·")[0].strip() if kicker else "bsandova.com")
    label = re.sub(r"<[^>]+>", "", kicker.group(1)).split("·")[0].strip() if kicker else "bsandova.com"
    return html.unescape(title.group(1)), photo.group(1), label


def set_meta(page: Path, url: str) -> None:
    old = s = page.read_text()
    s = re.sub(r'(<meta property="og:image" content=")[^"]+(")', rf"\g<1>{url}\2", s)
    if 'name="twitter:image"' in s:
        s = re.sub(r'(<meta name="twitter:image" content=")[^"]+(")', rf"\g<1>{url}\2", s)
    else:
        s = s.replace('<meta name="twitter:card" content="summary_large_image">',
                      f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="{url}">', 1)
    if s != old:
        page.write_text(s)


def render(pw_page, title: str, photo: str, label: str, out: Path) -> None:
    if re.fullmatch(r"(?i)text\s*\d+", label):  # numbered kickers say nothing on a card
        label = ""
    size, lbl_bottom = fit(title)
    doc = TEMPLATE.format(photo=(ROOT / "assets" / "photo" / f"{photo}.jpg").as_uri(), title=html.escape(title),
                          label=html.escape(label), size=size, lbl_bottom=lbl_bottom)
    tmp = OUT / "_card.html"
    tmp.write_text(doc)
    pw_page.goto(tmp.as_uri(), wait_until="networkidle")
    pw_page.wait_for_timeout(300)
    pw_page.screenshot(path=str(out), type="jpeg", quality=82)
    tmp.unlink()


def main(executable: str | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = sorted((ROOT / "texts").glob("*.html")) + [ROOT / "texts" / "quaesitor" / "index.html"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        pw_page = browser.new_page(viewport={"width": 1200, "height": 630})
        for page in pages:
            info = article_info(page)
            if not info:
                continue
            slug = "quaesitor" if page.parent.name == "quaesitor" else page.stem
            render(pw_page, *info, OUT / f"{slug}.jpg")
            set_meta(page, f"{SITE}/assets/og/{slug}.jpg")
            print(f"assets/og/{slug}.jpg  {info[0]}")
        render(pw_page, "Things made out of data", "delayed-red", "Barbora Šandová", OUT / "home.jpg")
        set_meta(ROOT / "index.html", f"{SITE}/assets/og/home.jpg")
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render the share card of every article and set its og:image.")
    ap.add_argument("chrome", nargs="?", help="path to a Chrome executable (default: Playwright's own)")
    main(ap.parse_args().chrome)
