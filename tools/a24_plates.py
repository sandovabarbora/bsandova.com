"""Turn the project figures (matplotlib SVGs) into "plates" for the /a24/ front page.

A plate keeps only the data marks of a figure: text, axes with their ticks and grid, legends, the axes background and
spines are removed, and every colour becomes a grey of the same luminance, lifted so it reads as light on black.
The data are unchanged; only the chart furniture goes.

Usage:
    python3 tools/a24_plates.py            # writes assets/a24/<name>.svg for every entry in PLATES
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "a24"
SVG = "{http://www.w3.org/2000/svg}"
DROP = re.compile(r"^(text|matplotlib\.axis|legend|xtick|ytick)_?\d*")
PLATES = {
    "delayed": "assets/delayed/01-five-days.svg",
    "football": "assets/football/atlas-fw.svg",
    "hockey": "assets/hockey/atlas-forwards.svg",
    "parking": "assets/parking/04-districts.svg",
    "parking2": "assets/parking2/01-wheelbase-length.svg",
    "icu": "assets/icu/01-trajectories.svg",
    "surf": "assets/surf/01-ericeira-92-days.svg",
    "brand": "assets/brand/02-hue-distance.svg",
    "parking3": "assets/parking3/01-size-vs-permits.svg",
}
LIFT = 1.35  # brighten greys so data reads as light on black


def grey(hexcol: str) -> str:
    h = hexcol.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    v = min(255, round((0.2126 * r + 0.7152 * g + 0.0722 * b) * LIFT))
    return f"#{v:02x}{v:02x}{v:02x}"


def regrey(text: str) -> str:
    return re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", lambda m: grey(m.group(0)), text)


def points(d: str) -> list[tuple[float, float]]:
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", d)]
    return list(zip(nums[0::2], nums[1::2]))


def is_furniture(g: ET.Element, width: float) -> bool:
    """Axes/figure backgrounds (rectangles wider than a quarter of the figure) and spines (two-point paths)."""
    path = g.find(f"{SVG}path")
    if path is None or "d" not in path.attrib:
        return False
    pts = points(path.attrib["d"])
    if len(pts) <= 2:
        return True
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return len(pts) <= 6 and (max(xs) - min(xs)) > 0.25 * width


def plate(src: Path, dst: Path) -> None:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    tree = ET.parse(src)
    root = tree.getroot()
    vb = [float(x) for x in root.attrib["viewBox"].split()]
    parents = {c: p for p in root.iter() for c in p}
    for g in list(root.iter(f"{SVG}g")):
        gid = g.attrib.get("id", "")
        if DROP.match(gid) or (gid.startswith("patch") and is_furniture(g, vb[2])):
            parents[g].remove(g)
    for el in root.iter():
        for key in ("style", "fill", "stroke"):
            if key in el.attrib:
                el.attrib[key] = regrey(el.attrib[key])
    root.attrib.pop("width", None)
    root.attrib.pop("height", None)
    root.attrib["preserveAspectRatio"] = "xMidYMid meet"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tree.write(dst, xml_declaration=True, encoding="utf-8")


if __name__ == "__main__":
    for name, src in PLATES.items():
        plate(ROOT / src, OUT / f"{name}.svg")
        print(f"assets/a24/{name}.svg")
