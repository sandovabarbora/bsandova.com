"""Checks added 9 October 2026 after a review of the frozen code; not registered.

1. units.py takes a trip's direction from its highest-sequence row with an observed time, so a trip whose last row is
   unobserved gets an earlier stop as its terminal and route-directions fragment. The registered tram model is refitted
   on the two largest directions of each route, and without directions of fewer than 50 units.
2. power.py keeps ČHMÚ values with QUALITY 3 ("Estimated" in ČHMÚ's code list, metadata/meta4.json). The tram model,
   part 2's hot and mild hours and part 2's tram model are recomputed without them, the frozen readers pointed at
   filtered copies. A dry hour needs all four stations, so a dropped precipitation value also removes dry hours.

Writes docs/research/rain-delays-posthoc-review.json.

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest python tools/rain/posthoc_review.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rain"))
import power as rp  # noqa: E402
from estimate import D, SEED, frame, primary, weather  # noqa: E402

_spec = importlib.util.spec_from_file_location("heat_estimate", ROOT / "tools" / "heat" / "estimate.py")
he = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(he)
hp = he.hp

OUT = ROOT / "docs/research/rain-delays-posthoc-review.json"
MIN_UNITS = 50
KEEP = ("delta_s", "ci95", "ci90", "label", "n_units")


def tram(units: pd.DataFrame, precip: pd.DataFrame, keys: set | None = None) -> dict:
    d = frame(units, weather(precip), "tram")
    if keys is not None:
        d = d[[k in keys for k in zip(d["route"], d["direction"])]]
    r = primary(d, np.random.default_rng(SEED))
    return {k: r[k] for k in KEEP}


def without_quality3(src: Path, pattern: str, el: str, dst: Path) -> int:
    dropped = 0
    for f in sorted(src.glob(pattern)):
        j = json.loads(f.read_text())
        v = j["data"]["data"]["values"]
        keep = [r for r in v if r[5] != 3]
        dropped += sum(r[1] == el and r[5] == 3 for r in v)
        j["data"]["data"]["values"] = keep
        (dst / f.name).write_text(json.dumps(j))
    return dropped


def heat(c: pd.DataFrame) -> dict:
    return {"hot_hours": int(c["hot"].sum()), "hot_dates": int(pd.Series(c.loc[c["hot"], "date"]).nunique()),
            "mild_hours": int(c["mild"].sum())}


def main() -> None:
    units = pd.read_parquet(D / "units.parquet")
    precip = rp.precipitation()
    s = frame(units, weather(precip), "tram")
    s = s[s["rain"] | s["dry"]]
    g = s.groupby(["route", "direction"]).agg(units=("trips", "size"), trips=("trips", "sum"))
    top2 = set(g["trips"].groupby(level=0).rank(ascending=False, method="first").loc[lambda r: r <= 2].index)
    big = set(g.index[g["units"] >= MIN_UNITS])
    t = units[units["mode"] == "tram"]
    res = {
        "note": "added 9 October 2026 after a review of the frozen code; not registered",
        "directions": {"tram_route_directions": int(t.groupby(["route", "direction"]).ngroups),
                       "tram_routes": int(t["route"].nunique()),
                       "route_17_directions": int(t.loc[t["route"] == "17", "direction"].nunique()),
                       "sample_route_directions": len(g), "sample_route_directions_under_50_units":
                           int((g["units"] < MIN_UNITS).sum())},
        "registered": tram(units, precip),
        "top_2_directions_per_route": tram(units, precip, top2),
        "directions_with_50_units_or_more": tram(units, precip, big),
    }
    q3 = res["quality3"] = {"heat_registered": heat(hp.classify())}
    p0, t0 = rp.CHMI, hp.T10
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        q3["precipitation_values_dropped"] = without_quality3(p0, "1h-*.json", "SRA1H", Path(a))
        q3["temperature_values_dropped"] = without_quality3(t0, "10m-*.json", "T", Path(b))
        rp.CHMI = Path(a)
        q3["tram_without_quality3"] = tram(units, rp.precipitation())
        q3["heat_precipitation_only"] = heat(hp.classify())
        rp.CHMI, hp.T10 = p0, Path(b)
        q3["heat_temperature_only"] = heat(hp.classify())
        rp.CHMI = Path(a)
        q3["heat_both"] = heat(hp.classify())
        r = he.primary(he.frame(units, he.weather(), "tram"), np.random.default_rng(he.SEED))
        q3["heat_tram_both"] = {k: r[k] for k in KEEP + ("hot_dates",)}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
