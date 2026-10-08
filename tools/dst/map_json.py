"""The interactive region map of the clock-change article: minutes of the evening rush after civil dusk, by region.

Same numbers as fig. 4 (article.py's rush_minutes); writes assets/dst/map.json for assets/map.js.

    uv run --with pandas --with pyarrow --with shapely --with matplotlib python tools/dst/map_json.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from article import A, HELD, NAMES, rush_minutes  # noqa: E402


def rings(geom, tol: float = 0.01) -> list[list[list[float]]]:
    g = geom.simplify(tol, preserve_topology=True)
    return [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in getattr(g, "geoms", [g])]


def main() -> None:
    rm = rush_minutes()
    feats = [{"id": iso, "name": NAMES[iso], "r": rings(v["geom"]),
              "v": {"pre": round(v["pre"], 1), "post": round(v["post"], 1)}} for iso, v in sorted(rm.items())]
    dom = [0, max(round(v["post"]) for v in rm.values()) + 5]
    fmt = {"dp": 0, "unit": " min"}
    spec = {"held": HELD, "features": feats,
            "views": [{"key": "pre", "label": "two weeks before the change", "fmt": fmt, "scale": "seq", "domain": dom,
                       "note": "minutes of 16:00–18:59 after civil dusk"},
                      {"key": "post", "label": "two weeks after", "fmt": fmt, "scale": "seq", "domain": dom,
                       "note": "minutes of 16:00–18:59 after civil dusk"}],
            "hint": "hover, tap or use the arrow keys for a region", "data": ["results.json"]}
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    print({f["id"]: f["v"] for f in feats})


if __name__ == "__main__":
    main()
