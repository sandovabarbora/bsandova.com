"""Render a 1200x630 share card per article: its photograph, its title, the site mark.

Reads each article's og:title and its film photograph (assets/photo/<name>.jpg), writes assets/og/<slug>.jpg,
and points the article's og:image / twitter:image at it. The front page gets assets/og/home.jpg.

Usage (needs Playwright's Chromium; run from the repo root):
    uv run --with playwright python tools/site/og_cards.py           # only cards whose inputs changed
    uv run --with playwright python tools/site/og_cards.py --force   # every card
"""

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from shared import ROOT, SITE

OUT = ROOT / "assets" / "og"

TEMPLATE = (Path(__file__).parent / "og_card.html").read_text(encoding="utf-8")
MANIFEST = OUT / ".manifest.json"  # input hash per card; local only (gitignored), so a rerun skips unchanged cards


def fit(title: str) -> tuple[int, int]:
    """Font size and label offset so that long titles stay on at most three lines."""
    n = len(title)
    size = 96 if n <= 28 else 80 if n <= 48 else 64 if n <= 70 else 54
    lines = 1 if n * size * 0.5 < 1088 else 2 if n * size * 0.5 < 2176 else 3
    return size, 52 + int(lines * size * 0.95) + 22


def article_info(page: Path) -> tuple[str, str, str] | None:
    """(card title, photo file name, kicker) for an article with a film photograph, else None."""
    s = page.read_text(encoding="utf-8")
    title = re.search(r'<meta property="og:title" content="([^"]+)"', s)
    photo = re.search(r'class="film film-page"[^>]*><div class="shot" style="[^"]*assets/photo/([a-z0-9-]+)\.jpg', s)
    if not (title and photo):
        return None
    kicker = re.search(r'<p class="kicker">(.*?)</p>', s, re.S)
    label = re.sub(r"<[^>]+>", "", kicker.group(1)).split("·")[0].strip() if kicker else "bsandova.com"
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    if " — " in title.group(1) and h1:  # a site-suffixed og:title: the headline reads better on a card
        return html.unescape(re.sub(r"<[^>]+>", "", h1.group(1)).strip()), photo.group(1), label
    return html.unescape(title.group(1)), photo.group(1), label


def set_meta(page: Path, url: str) -> None:
    old = s = page.read_text(encoding="utf-8")
    s = re.sub(r'(<meta property="og:image" content=")[^"]+(")', rf"\g<1>{url}\2", s)
    if 'name="twitter:image"' in s:
        s = re.sub(r'(<meta name="twitter:image" content=")[^"]+(")', rf"\g<1>{url}\2", s)
    else:
        s = s.replace('<meta name="twitter:card" content="summary_large_image">',
                      f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="{url}">', 1)
    if s != old:
        page.write_text(s, encoding="utf-8")


def card(title: str, photo: str, label: str) -> tuple[str, str]:
    """The card's HTML and the hash of everything that decides its pixels."""
    if re.fullmatch(r"(?i)text\s*\d+", label):  # numbered kickers say nothing on a card
        label = ""
    size, lbl_bottom = fit(title)
    jpg = ROOT / "assets" / "photo" / f"{photo}.jpg"
    doc = TEMPLATE.format(photo=jpg.as_uri(), title=html.escape(title), label=html.escape(label), size=size,
                          lbl_bottom=lbl_bottom)
    h = hashlib.sha256(Path(__file__).read_bytes())
    for part in (TEMPLATE, title, label, photo):
        h.update(part.encode() + b"\0")
    h.update(jpg.read_bytes())
    return doc, h.hexdigest()


def write_atomic(out: Path, fill) -> None:
    """fill(path) writes a temporary sibling that replaces `out` in one rename: no half-written card on a crash."""
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=f".{out.stem}.", suffix=out.suffix)
    os.close(fd)
    try:
        fill(tmp)
        os.replace(tmp, out)
    finally:
        Path(tmp).unlink(missing_ok=True)


def render(pw_page, doc: str, out: Path) -> None:
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "card.html"
        src.write_text(doc, encoding="utf-8")
        pw_page.goto(src.as_uri(), wait_until="networkidle")
        pw_page.wait_for_timeout(300)
        write_atomic(out, lambda tmp: pw_page.screenshot(path=tmp, type="jpeg", quality=82))


def main(executable: str | None = None, force: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = sorted((ROOT / "texts").glob("*.html")) + [ROOT / "texts" / "quaesitor" / "index.html"]
    cards = []  # (out, page, card info)
    for page in pages:
        info = article_info(page)
        if info:
            slug = "quaesitor" if page.parent.name == "quaesitor" else page.stem
            cards.append((OUT / f"{slug}.jpg", page, info))
    cards.append((OUT / "home.jpg", ROOT / "index.html", ("Things made out of data", "delayed-red", "Barbora Šandová")))
    try:
        seen = {} if force else json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        seen = {}
    todo = []
    for out, page, info in cards:
        doc, key = card(*info)
        if seen.get(out.name) != key or not out.exists():
            todo.append((out, doc, key, info[0]))
        set_meta(page, f"{SITE}/assets/og/{out.name}")
    if todo:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=executable)
            pw_page = browser.new_page(viewport={"width": 1200, "height": 630})
            for out, doc, key, title in todo:
                render(pw_page, doc, out)
                seen[out.name] = key
                print(f"assets/og/{out.name}  {title}")
            browser.close()
        write_atomic(MANIFEST, lambda tmp: Path(tmp).write_text(json.dumps(seen, indent=1, sort_keys=True) + "\n",
                                                                 encoding="utf-8"))
    print(f"og cards: {len(todo)} rendered, {len(cards) - len(todo)} unchanged")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render the share card of every article and set its og:image.")
    ap.add_argument("chrome", nargs="?", help="path to a Chrome executable (default: Playwright's own)")
    ap.add_argument("--force", action="store_true", help="render every card, even those whose inputs are unchanged")
    args = ap.parse_args()
    main(args.chrome, args.force)
