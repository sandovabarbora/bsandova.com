"""Small photo thumbnails for the front page's "All work" rows.

Each row gets the photograph of the page it links to: the article's film photo (its data-img) or, for the live pages,
assets/photo/page-<slug>.jpg. Thumbnails are 240x160 centre crops (shown at 96x64) in assets/photo/th/. Rows without
a data-img get one too, so the hover peek works on every row. Running it twice changes nothing.

Usage (needs Pillow):
    uv run --with pillow python tools/thumbs.py
"""

import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PHOTO = ROOT / "assets" / "photo"
TH = PHOTO / "th"
SIZE = (240, 160)
ROW = re.compile(r'<li data-tags="([^"]*)"(?: data-img="([^"]*)")?><a href="([^"]*)">(?:<img class="th"[^>]*>)?')


def source(data_img: str | None, href: str) -> str | None:
    """Photo name (without extension) for a row, or None if the linked page has no photograph."""
    if data_img:
        return Path(data_img).stem.removesuffix("-1200")
    slug = href.strip("/").split("/")[0]
    return f"page-{slug}" if (PHOTO / f"page-{slug}.jpg").exists() else None


def thumb(name: str) -> str:
    out = TH / f"{name}.jpg"
    if not out.exists():
        im = Image.open(PHOTO / f"{name}.jpg").convert("RGB")
        w, h = im.size
        scale = max(SIZE[0] / w, SIZE[1] / h)
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        left, top = (im.width - SIZE[0]) // 2, (im.height - SIZE[1]) // 2
        im.crop((left, top, left + SIZE[0], top + SIZE[1])).save(out, quality=78, optimize=True, progressive=True)
    return f"assets/photo/th/{name}.jpg"


def row(m: re.Match) -> str:
    tags, data_img, href = m.group(1), m.group(2), m.group(3)
    name = source(data_img, href)
    if name is None:
        return m.group(0)
    peek = data_img or f"assets/photo/{name}-1200.jpg"
    img = f'<img class="th" src="{thumb(name)}" alt="" loading="lazy" decoding="async" width="96" height="64">'
    return f'<li data-tags="{tags}" data-img="{peek}"><a href="{href}">{img}'


def main() -> None:
    TH.mkdir(exist_ok=True)
    page = ROOT / "index.html"
    s = page.read_text()
    t = ROW.sub(row, s)
    page.write_text(t)
    print(f"{len(list(TH.glob('*.jpg')))} thumbnails; index.html {'updated' if t != s else 'unchanged'}")


if __name__ == "__main__":
    main()
