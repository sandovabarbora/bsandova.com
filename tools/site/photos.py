"""Site photographs: fetch each source in assets/photo/sources.json and tone it like a film still.

The tone: darker mid-tones, colour muted to half, a vignette, blacks lifted and highlights softened (a faded
print), teal in the shadows and warm in the highlights, and a fixed-seed grain. Writes assets/photo/<slug>.jpg (1920 px wide) and <slug>-1200.jpg.
Originals are cached in tools/data/photos/ (not committed). Commons files come through the API at 2400 px.

    uv run --with numpy --with pillow python tools/site/photos.py [slug ...]
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "photo"
CACHE = ROOT / "tools" / "data" / "photos"
UA = {"User-Agent": "bsandova.com photo build (contact via bsandova.com)"}


def get(url: str) -> bytes:
    for wait in (0, 20, 60, 120):   # Commons answers 429 when asked too fast
        time.sleep(wait)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise RuntimeError(f"rate-limited: {url}")


def source(row: dict) -> bytes:
    path = CACHE / f"{row['slug']}.src"
    if path.exists():
        return path.read_bytes()
    url = row.get("url")
    if not url:
        q = urllib.parse.urlencode({"action": "query", "titles": row["commons"], "prop": "imageinfo",
                                    "iiprop": "url", "iiurlwidth": 2400, "format": "json"})
        page = next(iter(json.loads(get(f"https://commons.wikimedia.org/w/api.php?{q}"))["query"]["pages"].values()))
        url = page["imageinfo"][0]["thumburl"]
    data = get(url)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    time.sleep(5)
    return data


def tone(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    a = a ** 1.25                                                   # darker mid-tones: dusk rather than noon
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * 0.5
    h, w = a.shape[:2]
    y, x = np.ogrid[-1:1:h * 1j, -1:1:w * 1j]
    a *= (1 - 0.35 * np.clip(x * x * 0.6 + y * y, 0, 1))[..., None]   # vignette
    a = 0.05 + a * 0.88
    lum = a.mean(2, keepdims=True)
    a += (1 - lum) * np.array([-0.025, 0.02, 0.035]) + lum * np.array([0.045, 0.015, -0.035])
    a += np.random.default_rng(0).normal(0, 0.03, (h, w))[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def build(row: dict) -> None:
    im = Image.open(io.BytesIO(source(row)))
    for width, name in ((1920, f"{row['slug']}.jpg"), (1200, f"{row['slug']}-1200.jpg")):
        r = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        tone(r).save(OUT / name, quality=82, optimize=True, progressive=True)
    print(row["slug"], f"{im.width}x{im.height}")


if __name__ == "__main__":
    rows = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    want = set(sys.argv[1:])
    for row in rows:
        if not want or row["slug"] in want:
            try:
                build(row)
            except RuntimeError as e:   # a source still rate-limited keeps its current file; rerun later
                print(row["slug"], "skipped:", e)
