"""Part 2 extended, the design frame: census composition, housing and flags for every Prague precinct and grid
cluster, built before any election result is joined (docs/research/prague-rings-design.md, §3 and §5).

Everything geometric is in EPSG:5514 (S-JTSK / Krovak East North). RÚIAN layers are requested in 5514 from the
ČÚZK service itself, so no client-side datum transformation is involved. The census grid (ČSÚ, 1 km INSPIRE cells)
is distributed in 5514.

Sources (downloaded into tools/data/praha2x/, not committed):
  - grid_obyvatelstvo_sldb2021_20210326.geojson: Census 2021 on the 1 km grid, fields g131620xxx (usual residents).
  - obyv_zsj.csv: Census 2021 usual residents and flats by basic settlement unit (ZSJ), for the allocation check.
  - RÚIAN (ČÚZK ArcGIS REST): layer 20 precincts, 2 building points, 6 ZSJ, 12 municipality, 1 address points.
  - ovm.xml: register of public authorities (Seznam OVM); the 57 Prague district offices and their RÚIAN
    address points. A citizen with no real address has the permanent residence registered at the district office.
  - institutions.csv: inpatient hospitals, residential social services and prisons (see its own sources).

Usage:
    uv run --with pandas --with numpy --with shapely --with pyarrow --with pyproj --with statsmodels \
        python tools/praha/rings_data.py
"""

import gzip
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import STRtree
from shapely.geometry import Point, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha2x"
OUT = RAW / "design.parquet"
RUIAN = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/MapServer/{}/query"
PRAGUE_OBEC = 554782
CENSUS_DAY = pd.Timestamp("2021-03-26")
ELECTION_2025 = pd.Timestamp("2025-10-03")
PANEL = [4, 41]
FAMILY_HOUSE = 7
G = "g131620{}".format
COUNTS = ["000", "011", "012", "013", "050", "051", "053", "054", "021", "022", "023", "024", "025", "026"]


def ruian(layer: int, where: str = "1=1", fields: str = "*", geometry: dict | None = None) -> list[dict]:
    """All features of a RÚIAN layer, in EPSG:5514, paged; an optional envelope filter."""
    out, off = [], 0
    while True:
        q = {"where": where, "outFields": fields, "returnGeometry": "true", "outSR": "5514", "f": "json",
             "resultOffset": off, "resultRecordCount": 5000}
        if geometry:
            q |= {"geometry": json.dumps(geometry), "geometryType": "esriGeometryEnvelope", "inSR": "5514",
                  "spatialRel": "esriSpatialRelIntersects"}
        for attempt in range(5):
            try:
                req = urllib.request.Request(RUIAN.format(layer), data=urllib.parse.urlencode(q).encode())
                page = json.load(urllib.request.urlopen(req, timeout=300))
                if "error" in page:
                    raise RuntimeError(page["error"])
                break
            except Exception:  # noqa: BLE001 - the service drops the odd request; retry
                if attempt == 4:
                    raise
                time.sleep(4 * (attempt + 1))
        feats = page.get("features", [])
        out += feats
        if not page.get("exceededTransferLimit") and len(feats) < 5000:
            return out
        off += len(feats)


def esri_polygon(g: dict):
    """An Esri JSON polygon (rings, outer clockwise) as a shapely geometry."""
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient

    polys, holes = [], []
    for ring in g["rings"]:
        p = Polygon(ring)
        (holes if p.exterior.is_ccw else polys).append(p)
    out = unary_union(polys) if polys else Polygon()
    for h in holes:
        out = out.difference(h)
    return orient(out) if out.geom_type == "Polygon" else out


def cached(name: str, build):
    """Our own downloads, pickled locally (never third-party pickles)."""
    path = RAW / name
    if path.exists():
        return pd.read_pickle(path)
    obj = build()
    pd.to_pickle(obj, path)
    return obj


def prague():
    feats = ruian(12, f"kod={PRAGUE_OBEC}", "kod")
    return esri_polygon(feats[0]["geometry"])


def precincts() -> pd.DataFrame:
    feats = ruian(20, f"obec={PRAGUE_OBEC}", "kod,cislo,momc,platiod")
    return pd.DataFrame([{**f["attributes"], "geom": esri_polygon(f["geometry"])} for f in feats])


def buildings(where: str, envelope: dict | None = None) -> pd.DataFrame:
    feats = ruian(2, where, "kod,pocetbytu,dokonceni,druhkonstrukcekod,zpusobvyuzitikod,momc", envelope)
    return pd.DataFrame([{**f["attributes"], "x": f["geometry"]["x"], "y": f["geometry"]["y"]}
                         for f in feats if f.get("geometry")])


def grid(city) -> pd.DataFrame:
    raw = json.loads((RAW / "grid_obyvatelstvo_sldb2021_20210326.geojson").read_text())
    rows = []
    for f in raw["features"]:
        g = shape(f["geometry"])
        if g.intersects(city):
            rows.append({"cell": f["properties"]["kod"], "geom": g, "in_prague": g.intersection(city).area / g.area,
                         **{c: f["properties"][G(c)] for c in COUNTS}})
    return pd.DataFrame(rows)


def district_offices() -> pd.DataFrame:
    s = gzip.open(RAW / "ovm.xml", "rt", encoding="utf-8").read()
    rows = []
    for b in re.findall(r"<Subjekt>(.*?)</Subjekt>", s, re.S):
        if '<PravniForma type="811">' in b and "<StavSubjektu>1<" in b:
            rows.append({"office": re.search(r"<Nazev>(.*?)</Nazev>", b).group(1),
                         "adm": int(re.search(r"<AdresniBod>(\d+)", b).group(1))})
    d = pd.DataFrame(rows)
    pts = ruian(1, f"kod IN ({','.join(map(str, d.adm))})", "kod")
    xy = {f["attributes"]["kod"]: (f["geometry"]["x"], f["geometry"]["y"]) for f in pts}
    d["x"], d["y"] = zip(*(xy[a] for a in d.adm))
    return d


def allocate(cells: pd.DataFrame, prec: pd.DataFrame, b: pd.DataFrame, by_area: bool = False
             ) -> tuple[pd.DataFrame, dict]:
    """Census counts from cells to precincts: by pre-census flats; by area where a cell has no flats or fewer than
    one flat per four residents. Flats outside Prague stay in the denominator of boundary cells. `by_area`
    allocates every cell by area (robustness 7)."""
    tree = STRtree(list(prec.geom))
    pts = [Point(x, y) for x, y in zip(b.x, b.y)]
    ctree = STRtree(list(cells.geom))
    hit_c = ctree.query(pts, predicate="within")
    b = b.assign(ci=-1, pi=-1)
    b.loc[b.index[hit_c[0]], "ci"] = hit_c[1]
    hit_p = tree.query(pts, predicate="within")
    b.loc[b.index[hit_p[0]], "pi"] = hit_p[1]
    pre = b[b.pre_census & (b.ci >= 0)]
    w = pre.groupby(["ci", "pi"]).pocetbytu.sum().rename("flats").reset_index()
    tot = w.groupby("ci").flats.sum()
    rows, how = [], {"flats": 0, "area": 0, "area_residents": 0, "outside_residents": 0}
    for ci, c in cells.iterrows():
        res = c["000"]
        cw = w[w.ci == ci]
        use_flats = not by_area and tot.get(ci, 0) > 0 and tot.get(ci, 0) >= res / 4
        if use_flats:
            shares = cw.set_index("pi").flats / tot[ci]
            how["flats"] += 1
        else:
            near = tree.query(c.geom, predicate="intersects")
            parts = {int(pi): c.geom.intersection(prec.geom[pi]).area for pi in near}
            area = c.geom.area  # the whole cell, so the part outside Prague stays unallocated
            shares = pd.Series(parts) / area
            how["area"] += 1
            how["area_residents"] += int(res)
        inside = shares[shares.index >= 0]
        how["outside_residents"] += float(res * (1 - inside.sum()))
        for pi, s in inside.items():
            rows.append({"pi": int(pi), "ci": ci, "w": float(s), **{k: float(c[k]) * float(s) for k in COUNTS}})
    a = pd.DataFrame(rows)
    return a, how


def zsj(city) -> pd.DataFrame:
    x0, y0, x1, y1 = city.bounds
    feats = ruian(6, "1=1", "kod,nazev", {"xmin": x0, "ymin": y0, "xmax": x1, "ymax": y1,
                                          "spatialReference": {"wkid": 5514}})
    z = pd.DataFrame([{**f["attributes"], "geom": esri_polygon(f["geometry"])} for f in feats])
    return z[[city.contains(g.representative_point()) for g in z.geom]].reset_index(drop=True)


def zsj_check(z: pd.DataFrame, b: pd.DataFrame, prec: pd.DataFrame) -> pd.Series:
    """Census usual residents by ZSJ, spread over precincts by pre-census flats: an independent allocation of the
    same population, to compare with the grid allocation precinct by precinct."""
    c = pd.read_csv(RAW / "obyv_zsj.csv", dtype={"uzemi_kod": int})
    c = c[(c.uzemi_typ == "základní sídelní jednotka") & (c.ukaz_txt == "Počet obyvatel s obvyklým pobytem")]
    res = c.set_index("uzemi_kod").hodnota
    pts = [Point(x, y) for x, y in zip(b.x, b.y)]
    hit = STRtree(list(z.geom)).query(pts, predicate="within")
    bz = b.iloc[hit[0]].assign(zi=hit[1])
    bz = bz[bz.pre_census & (bz.pi >= 0)]
    w = bz.groupby(["zi", "pi"]).pocetbytu.sum()
    w = w / w.groupby(level=0).transform("sum")
    alloc = w.mul(pd.Series(z.kod.map(res).fillna(0).values, index=z.index), level=0)
    return alloc.groupby(level=1).sum().reindex(prec.index, fill_value=0)


def metro_5514() -> np.ndarray:
    import sys

    from pyproj import Transformer

    sys.path.insert(0, str(Path(__file__).parent))
    from metro import metro_stations

    st = metro_stations()
    x, y = Transformer.from_crs(4326, 5514, always_xy=True).transform(st.stop_lon.values, st.stop_lat.values)
    return np.c_[x, y]


def main() -> None:
    from pyproj import Transformer

    city = cached("prague_5514.pkl", prague)
    prec = cached("precincts_5514.pkl", precincts)
    b = cached("buildings_5514.pkl", lambda: buildings("pocetbytu>0 AND momc IS NOT NULL"))
    b = b[b.momc.isin(set(prec.momc))]  # Brno, Ostrava and other statutory cities have districts (momc) too
    cells = grid(city)
    edge = cells[cells.in_prague < 0.999]
    outside = cached("buildings_outside_5514.pkl", lambda: pd.concat(
        [buildings("pocetbytu>0 AND momc IS NULL", dict(zip(["xmin", "ymin", "xmax", "ymax"], g.bounds),
                                                             spatialReference={"wkid": 5514}))
         for g in edge.geom], ignore_index=True).drop_duplicates("kod"))
    b = pd.concat([b.assign(prague=True), outside.assign(prague=False)], ignore_index=True)
    done = pd.to_datetime(b.dokonceni, unit="ms", errors="coerce")
    b["pre_census"] = done.isna() | (done <= CENSUS_DAY)
    b["post_census"] = (done > CENSUS_DAY) & (done <= ELECTION_2025)
    b["built_2016_21"] = (done >= pd.Timestamp("2016-01-01")) & (done <= CENSUS_DAY)
    b["standing_2025"] = done.isna() | (done <= ELECTION_2025)
    a, how = allocate(cells, prec, b)
    b = b.assign(pi=-1)
    hit = STRtree(list(prec.geom)).query([Point(x, y) for x, y in zip(b.x, b.y)], predicate="within")
    b.loc[b.index[hit[0]], "pi"] = hit[1]

    # composition, per precinct
    d = a.groupby("pi")[COUNTS].sum().reindex(prec.index, fill_value=0)
    area, _ = allocate(cells, prec, b, by_area=True)
    d = d.join(area.groupby("pi")[COUNTS].sum().reindex(prec.index, fill_value=0).add_prefix("area_"))
    d = prec[["kod", "momc", "cislo", "platiod"]].join(d)
    # housing standing at the 2025 election, per precinct
    s = b[(b.pi >= 0) & b.standing_2025].assign(
        panel=lambda t: t.pocetbytu * t.druhkonstrukcekod.isin(PANEL),
        panel4=lambda t: t.pocetbytu * (t.druhkonstrukcekod == 4),
        house=lambda t: t.pocetbytu * (t.zpusobvyuzitikod == FAMILY_HOUSE),
        post=lambda t: t.pocetbytu * t.post_census, pre=lambda t: t.pocetbytu * t.pre_census)
    d = d.join(s.groupby("pi")[["pocetbytu", "panel", "panel4", "house", "post", "pre"]].sum())
    d = d.rename(columns={"pocetbytu": "flats", "panel": "panel_flats", "panel4": "panel4_flats",
                          "house": "house_flats", "post": "post_flats", "pre": "pre_flats"})
    # dominant grid cell: the cell holding most of the precinct's pre-census flats, else most of its area
    pre = b[b.pre_census & (b.pi >= 0)]
    pts = [Point(x, y) for x, y in zip(pre.x, pre.y)]
    hc = STRtree(list(cells.geom)).query(pts, predicate="within")
    byc = pre.iloc[hc[0]].assign(ci=hc[1]).groupby(["pi", "ci"]).pocetbytu.sum()
    dom = byc.groupby(level=0).idxmax().map(lambda t: t[1])
    ctree = STRtree(list(cells.geom))
    for pi in d.index.difference(dom.index):
        g = prec.geom[pi]
        cand = ctree.query(g, predicate="intersects")
        dom.loc[pi] = max(cand, key=lambda ci: g.intersection(cells.geom[ci]).area)
    d["cell"] = cells.cell.values[dom.reindex(d.index).astype(int).values]
    # distances from the polygon centroid, metres
    cx, cy = np.array([g.centroid.x for g in prec.geom]), np.array([g.centroid.y for g in prec.geom])
    mx, my = Transformer.from_crs(4326, 5514, always_xy=True).transform(14.4225, 50.0835)  # Můstek
    st = metro_5514()
    d["centre_m"] = np.hypot(cx - mx, cy - my)
    d["metro_m"] = np.hypot(cx[:, None] - st[None, :, 0], cy[:, None] - st[None, :, 1]).min(axis=1)
    d["area_km2"] = [g.area / 1e6 for g in prec.geom]
    # flags from RÚIAN and official lists, never from outcomes
    off = district_offices()
    ho = STRtree(list(prec.geom)).query([Point(x, y) for x, y in zip(off.x, off.y)], predicate="within")
    d["registration_office"] = d.index.isin(ho[1])
    d["new_build"] = d.post_flats / d.flats > 0.10
    inst = pd.read_csv(RAW / "institutions.csv")
    core = inst.type.isin(["hospital_inpatient", "prison"]) | inst.name.str.contains(
        "domovy? (?:pro seniory|se zvláštním režimem|pro osoby se zdravotním postižením)", case=False)
    inst = inst[core]
    ix, iy = Transformer.from_crs(4326, 5514, always_xy=True).transform(inst.lon.values, inst.lat.values)
    hi = STRtree(list(prec.geom)).query([Point(x, y) for x, y in zip(ix, iy)], predicate="within")
    d["institution"] = d.index.isin(hi[1])
    d["zsj_residents"] = zsj_check(cached("zsj_5514.pkl", lambda: zsj(city)), b, prec)
    # resident Czech adults, Â: Czech citizens x adult share of the cell, less 15-17 year olds (3/5 of 15-19,
    # Census 2021 SLD21A011, Prague, Czech citizens: 0.6 x 43 065 / 933 243)
    s1517 = 0.6 * 43065 / 933243
    d["czech_adults_2021"] = d["050"] * (d["012"] + d["013"]) / d["000"].where(d["000"] > 0) * (1 - s1517)
    newb = b[b.built_2016_21 & b.prague]
    hn = ctree.query([Point(x, y) for x, y in zip(newb.x, newb.y)], predicate="within")
    nb = newb.iloc[hn[0]].assign(ci=hn[1]).groupby("ci").pocetbytu.sum()
    allflats = pre.iloc[hc[0]].assign(ci=hc[1]).groupby("ci").pocetbytu.sum()
    young = cells.index[(nb.reindex(cells.index, fill_value=0) / allflats.reindex(cells.index)).fillna(0) >= 0.5]
    ca = cells.loc[young]
    per_flat = float((ca["050"] * (ca["012"] + ca["013"]) / ca["000"] * (1 - s1517)).sum()
                     / allflats.reindex(young).sum())
    d["A_hat"] = d.czech_adults_2021.fillna(0) + d.post_flats.fillna(0) * per_flat
    d["geom_wkb"] = [g.wkb for g in prec.geom]
    d.to_parquet(OUT)
    report = {
        "cells": len(cells), "edge_cells": len(edge), "precincts": len(d),
        "allocation": how, "residents_allocated": round(float(d["000"].sum())),
        "residents_prague_census": 1301432,
        "clusters": int(d.cell.nunique()),
        "registration_office_precincts": int(d.registration_office.sum()),
        "new_build_precincts": int(d.new_build.sum()),
        "institution_precincts": int(d.institution.sum()), "institutions_used": int(core.sum()),
        "post_census_flat_share": round(float(d.post_flats.sum() / d.flats.sum()), 4),
        "czech_adults_per_new_flat": round(per_flat, 3), "young_cells": len(young),
        "zsj_total": round(float(d.zsj_residents.sum())),
        "zsj_deviation_over_25pct": int(((d["000"] - d.zsj_residents).abs() > 0.25 * d.zsj_residents).sum()),
    }
    (RAW / "design_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
