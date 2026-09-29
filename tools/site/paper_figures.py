"""Recolour the article charts from the old dark theme to paper, with each article's held colour as its accent.

The figure generators (tools/figures/*_figures.py and the atlas builds) draw for the dark theme. This maps their palette to
the A24 layer: paper background, ink text, light grid, and the article's main accent replaced by the colour its
photograph holds (police-car blue for parking, tram red for Delayed, ...). Other accents map to the validated light
categorical palette, or to ink when they would clash with the held colour. The mapped colours are not keys of the
map, so running this twice changes nothing; build.sh runs it after every generator.

Usage:
    python3 tools/site/paper_figures.py
"""

import colorsys
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NEUTRAL = {
    "#161616": "#ffffff",  # background
    "#1f1f1f": "#f4f4f2",  # panel
    "#3a3a36": "#e6e6e3",  # grid
    "#8a8a84": "#666666",  # axes and secondary text
    "#dcdcd6": "#111111",  # text
    "#f2f2ee": "#000000",  # emphasis
}
ACCENT = {  # dark-theme accents -> light categorical slots of the same hue
    "#d6ff3a": "#008300",
    "#ff6a3d": "#eb6834",
    "#7ed9a6": "#1baf7a",
    "#b78cff": "#4a3aa7",
    "#ffb347": "#eda100",
    "#5fb3c9": "#2a78d6",
    "#7e6678": "#e87ba4",
    "#1f77b4": "#2a78d6",
}
# the colour each article's photograph holds; None keeps the categorical palette (multi-series atlases)
HELD = {
    "brand": "#a8780f",
    "delayed": "#b3202c",
    "football": None,
    "hockey": None,
    "icu": "#1f4fad",
    "parking": "#1f4fad",
    "parking2": "#ad4a1f",
    "parking3": "#1f64ad",
    "detector": "#1f7fad",
    "surf": "#1f64ad",
}
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def hue(c: str) -> float:
    r, g, b = (int(c[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


def palette(folder: Path, held: str | None) -> dict[str, str]:
    """Colour map for one article's charts: its most used dark accent becomes the held colour."""
    m = {**NEUTRAL, **ACCENT}
    if held is None:
        return m
    used = Counter(
        c.lower() for f in folder.glob("*.svg") for c in HEX.findall(f.read_text()) if c.lower() in ACCENT
    )
    if not used:
        return m
    main = used.most_common(1)[0][0]
    m[main] = held
    for dark, light in ACCENT.items():
        if dark != main and min(abs(hue(light) - hue(held)), 360 - abs(hue(light) - hue(held))) < 30:
            m[dark] = "#111111"  # would read as a second shade of the held colour
    return m


def main() -> None:
    for name, held in HELD.items():
        folder = ROOT / "assets" / name
        m = palette(folder, held)
        n = 0
        for f in sorted(folder.glob("*.svg")):
            s = f.read_text()
            t = HEX.sub(lambda x: m.get(x.group(0).lower(), x.group(0)), s)
            if t != s:
                f.write_text(t)
                n += 1
        print(f"{name}: {n} recoloured")


if __name__ == "__main__":
    main()
