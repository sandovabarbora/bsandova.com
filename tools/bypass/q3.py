"""Q3 of the bypass accidents study (design §1, §2 "Q3 geometry"), descriptive and without a label: injury accidents
per kilometre and year on each bypass after opening and the share of them at junctions, with the old through road's
injury accidents per year before construction beside it.

A bypass is the chain of OpenStreetMap ways listed in the CSV (fetched by fetch.py), in S-JTSK, buffered by 50 m; its
accidents are those in the buffer, outside the built-up area (p5a), on the bypass's road number, from the January
after opening. A row without ways falls back to the straight line between its listed start and end points (the ends
of the OSM chain or of the ŘSD APDOS line, as the CSV notes say), and the method is reported per bypass. Kilometres are
the row's `length_km` (dual carriageways list both directions in OSM, so the geometry would count them twice), or the
line's length when the row has none. The old through road is taken as built-up-area accidents in the bypass's
municipalities on the road number the bypass took over, before the construction-start year; its length is not in the
list, so it is given per year, not per kilometre.

Run only from estimate.py behind its guard; the tests use made-up lines and accidents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

BUFFER_M = 50
WAYS = Path(__file__).resolve().parents[2] / "tools/data/bypass/raw/osm/ways.json"


def roads(s) -> set[str]:
    return {r.strip() for r in str(s or "").split(",") if r.strip()}


def to_sjtsk(lonlat: list[list[float]]) -> list[tuple[float, float]]:
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:5514", always_xy=True)
    xs, ys = tr.transform([p[0] for p in lonlat], [p[1] for p in lonlat])
    return list(zip(xs, ys))


def line(row: pd.Series, ways: dict):
    """The bypass in S-JTSK and how it was built: from its OSM ways, else from its start and end points."""
    from shapely.geometry import LineString, MultiLineString
    ids = re.findall(r"\d+", str(row.get("osm_ways") or ""))
    parts = [to_sjtsk(ways[i]["lonlat"]) for i in ids if i in ways and len(ways[i]["lonlat"]) >= 2]
    if parts:
        return MultiLineString(parts), "osm_ways"
    ends = [row.get(c) for c in ("start_lon", "start_lat", "end_lon", "end_lat")]
    if all(pd.notna(v) and str(v) != "" for v in ends):
        a, b = to_sjtsk([[float(ends[0]), float(ends[1])], [float(ends[2]), float(ends[3])]])
        return LineString([a, b]), "start_end_straight_line"
    return None, "no_geometry"


def on_bypass(acc: pd.DataFrame, geom, road_set: set[str], after: int, last: int) -> pd.DataFrame:
    import shapely
    zone = geom.buffer(BUFFER_M)
    a = acc[acc["injury"].fillna(False) & (acc["built_up"] == False) & acc["road"].isin(road_set)  # noqa: E712
            & acc["year"].between(after, last) & acc["x"].notna()]
    inside = shapely.contains_xy(zone, a["x"].to_numpy(float), a["y"].to_numpy(float))
    return a[inside]


def old_road(acc: pd.DataFrame, codes: list[int], road_set: set[str], first: int, before: int) -> pd.DataFrame:
    return acc[acc["injury"].fillna(False) & (acc["built_up"] == True) & acc["muni_polygon"].isin(codes)  # noqa: E712
               & acc["road"].isin(road_set) & acc["year"].between(first, before - 1)]


def q3(rows: pd.DataFrame, acc: pd.DataFrame, first: int, last: int, ways: dict | None = None) -> dict:
    """Per bypass and pooled. `rows` are list rows with id, road, codes, open_year, start_year, length_km, osm_ways and
    start/end points; `acc` has year, injury, built_up, road, junction, x, y, muni_polygon."""
    if ways is None:
        ways = json.loads(WAYS.read_text())["ways"]
    per, tot = [], {"bypass_accidents": 0, "km_years": 0.0, "at_junction": 0, "old_accidents": 0, "old_town_years": 0}
    for r in rows.itertuples():
        geom, method = line(pd.Series(r._asdict()), ways)
        rs = roads(r.road)
        rec = {"id": r.id, "road": r.road, "geometry": method}
        old = old_road(acc, list(r.codes), rs, first, int(r.start_year))
        pre_years = max(0, int(r.start_year) - first)
        rec.update({"old_road_accidents": int(len(old)), "old_road_years": pre_years,
                    "old_road_per_year": len(old) / pre_years if pre_years else None})
        tot["old_accidents"] += len(old)
        tot["old_town_years"] += pre_years
        years = max(0, last - int(r.open_year))
        if geom is None or years == 0:
            per.append(rec | {"bypass_accidents": None})
            continue
        km = float(r.length_km) if pd.notna(r.length_km) and float(r.length_km) > 0 else geom.length / 1000
        on = on_bypass(acc, geom, rs, int(r.open_year) + 1, last)
        rec.update({"km": km, "years": years, "bypass_accidents": int(len(on)),
                    "per_km_year": len(on) / (km * years), "at_junction": int(on["junction"].fillna(False).sum()),
                    "junction_share": float(on["junction"].fillna(False).mean()) if len(on) else None})
        tot["bypass_accidents"] += len(on)
        tot["km_years"] += km * years
        tot["at_junction"] += rec["at_junction"]
        per.append(rec)
    pooled = {"per_km_year": tot["bypass_accidents"] / tot["km_years"] if tot["km_years"] else None,
              "junction_share": tot["at_junction"] / tot["bypass_accidents"] if tot["bypass_accidents"] else None,
              "old_road_per_town_year": tot["old_accidents"] / tot["old_town_years"] if tot["old_town_years"] else None,
              **tot}
    return {"run": True, "label": None, "buffer_m": BUFFER_M, "pooled": pooled, "bypasses": per,
            "geometry_methods": pd.Series([p["geometry"] for p in per]).value_counts().to_dict(),
            "note": "different roads, length and traffic: not comparable with Q1 and carries no label (design §1)"}


def rows_for(towns: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """One list row per treated bypass, with the municipalities it treats."""
    tr = towns[towns["role"] == "treated"].groupby("row")["town"].agg(list).rename("codes")
    out = b.set_index("id").loc[tr.index].copy()
    out["codes"] = tr
    first = towns[towns["role"] == "treated"].drop_duplicates("row").set_index("row")
    out["open_year"], out["start_year"] = first["open_year"], first["start_year"]
    out["length_km"] = pd.to_numeric(out["length_km"], errors="coerce")
    out.index.name = "id"
    return out.reset_index()

