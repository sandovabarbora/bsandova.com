"""Does Prague vote along its metro lines? Precinct results of the 2025 Chamber election against the metro, the
distance to the centre and the housing stock.

Sources (downloaded into tools/data/praha2/, not committed):
  - Precinct results, Chamber of Deputies election 3-4 October 2025 (ČSÚ, volby.gov.cz open data, CSV):
    pst4.csv (turnout, valid votes) and pst4p.csv (votes per party). Prague is OKRES 1100; a precinct is
    (OBEC = city-district code, OKRSEK = number).
  - Precinct polygons, RÚIAN (ČÚZK), layer VolebníOkrsek, joined on (momc, cislo). RÚIAN keeps the current
    version only: every record is dated after the election, most from bulk updates on 10 October and
    4 November 2025; 22 were changed from December 2025 on and are dropped in a sensitivity check.
  - Residential buildings, RÚIAN definition points with number of flats and construction type: "panel" is
    wall panels (druhkonstrukcekod 4, 41). A precinct's panel share is the share of its flats in panel buildings.
  - Metro stations, Prague public transport GTFS (PID): stops served by routes of type 1. Flora is added by hand:
    closed for reconstruction from 2 February 2026, so missing from today's timetable, but open at the election.

Distances are from the precinct's polygon centroid, in metres (local equirectangular projection); the centre is
Můstek. Shares are of valid votes.

Usage:
    uv run --with pandas --with numpy --with shapely --with statsmodels python tools/praha/metro.py
"""

import io
import json
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from shapely import STRtree
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha2"
OUT = ROOT / "assets" / "praha" / "metro2025.json"
RESULTS = "https://volby.gov.cz/opendata/ps2025/PS2025data20251005_csv.zip"
RUIAN = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/MapServer/{}/query?"
GTFS = "https://data.pid.cz/PID_GTFS.zip"
PRAGUE_OBEC, PRAGUE_OKRES = 554782, 1100
MUSTEK = (14.4225, 50.0835)
FLORA = ("Flora", 50.078289, 14.462677)  # PID station U118S1
PANEL = [4, 41]  # RÚIAN druh konstrukce: stěnové panely; ... beton a železobeton
FAMILY_HOUSE = 7  # RÚIAN způsob využití: rodinný dům
PARTIES = {11: "SPOLU", 22: "ANO", 16: "Piráti", 23: "STAN", 6: "SPD", 20: "Motoristé", 25: "Stačilo!"}
ELECTION = pd.Timestamp("2025-10-04")
REDRAWN_FROM = pd.Timestamp("2025-12-01")


def get(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "bsandova.com research"})
        path.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    return path


def ruian(layer: int, where: str, fields: str, fmt: str) -> list[dict]:
    """All features of a RÚIAN layer matching `where`, paged."""
    out, off = [], 0
    while True:
        q = urllib.parse.urlencode({"where": where, "outFields": fields, "returnGeometry": "true", "outSR": "4326",
                                    "f": fmt, "resultOffset": off, "resultRecordCount": 5000})
        for attempt in range(4):
            try:
                page = json.load(urllib.request.urlopen(RUIAN.format(layer) + q, timeout=300))
                break
            except Exception:  # noqa: BLE001 - the service drops the odd request; retry
                time.sleep(3 * (attempt + 1))
        feats = page.get("features", [])
        out += feats
        if len(feats) < 5000:
            return out
        off += 5000


def results() -> pd.DataFrame:
    z = zipfile.ZipFile(get(RESULTS, RAW / "PS2025data_csv.zip"))
    t = pd.read_csv(io.BytesIO(z.read("csv/pst4.csv")), sep=";", encoding="cp1250")
    p = pd.read_csv(io.BytesIO(z.read("csv/pst4p.csv")), sep=";", encoding="cp1250")
    t, p = t[t.OKRES == PRAGUE_OKRES], p[p.OKRES == PRAGUE_OKRES]
    votes = p.pivot_table(index=["OBEC", "OKRSEK"], columns="KSTRANA", values="POC_HLASU", aggfunc="sum", fill_value=0)
    d = t.set_index(["OBEC", "OKRSEK"])[["VOL_SEZNAM", "VYD_OBALKY", "PL_HL_CELK"]]
    return d.join(votes[list(PARTIES)].rename(columns=PARTIES)).reset_index()


def metres(lon, lat, lon0, lat0):
    return np.hypot((lon - lon0) * 111320 * np.cos(np.radians(50.08)), (lat - lat0) * 110574)


def metro_stations() -> pd.DataFrame:
    z = zipfile.ZipFile(get(GTFS, RAW / "PID_GTFS.zip"))
    routes = pd.read_csv(z.open("routes.txt"))
    trips = pd.read_csv(z.open("trips.txt"), usecols=["trip_id", "route_id"])
    trips = trips[trips.route_id.isin(routes[routes.route_type == 1].route_id)]
    times = pd.read_csv(z.open("stop_times.txt"), usecols=["trip_id", "stop_id"])
    stops = pd.read_csv(z.open("stops.txt"), low_memory=False)
    s = stops[stops.stop_id.isin(set(times[times.trip_id.isin(trips.trip_id)].stop_id))]
    s = s.groupby("stop_name")[["stop_lat", "stop_lon"]].mean().reset_index()
    if FLORA[0] not in set(s.stop_name):
        s.loc[len(s)] = FLORA
    return s


def precincts(d: pd.DataFrame) -> pd.DataFrame:
    feats = ruian(20, f"obec={PRAGUE_OBEC}", "cislo,momc,platiod", "geojson")
    polys = [shape(f["geometry"]) for f in feats]
    meta = pd.DataFrame([f["properties"] for f in feats])
    meta["lon"] = [p.centroid.x for p in polys]
    meta["lat"] = [p.centroid.y for p in polys]
    meta["valid_from"] = pd.to_datetime(meta.platiod, unit="ms")
    st = metro_stations()
    dist = metres(meta.lon.values[:, None], meta.lat.values[:, None], st.stop_lon.values[None], st.stop_lat.values[None])
    meta["metro_m"], meta["centre_m"] = dist.min(axis=1), metres(meta.lon, meta.lat, *MUSTEK)

    buildings = ruian(2, "pocetbytu>0 AND momc IS NOT NULL", "druhkonstrukcekod,pocetbytu,zpusobvyuzitikod,momc", "json")
    b = pd.DataFrame([{**f["attributes"], "x": f["geometry"]["x"], "y": f["geometry"]["y"]}
                      for f in buildings if f.get("geometry")])
    b = b[b.momc.isin(set(d.OBEC))]
    hit = STRtree(polys).query([Point(x, y) for x, y in zip(b.x, b.y)], predicate="within")
    b = b.iloc[hit[0]].assign(pi=hit[1])
    b["panel_flats"] = b.pocetbytu * b.druhkonstrukcekod.isin(PANEL)
    b["house_flats"] = b.pocetbytu * (b.zpusobvyuzitikod == FAMILY_HOUSE)
    agg = b.groupby("pi")[["pocetbytu", "panel_flats", "house_flats"]].sum()
    meta = meta.join(agg)
    meta["panel_share"] = meta.panel_flats / meta.pocetbytu
    meta["house_share"] = meta.house_flats / meta.pocetbytu
    out = d.merge(meta, left_on=["OBEC", "OKRSEK"], right_on=["momc", "cislo"], how="left", validate="one_to_one")
    if out.momc.isna().any():
        raise ValueError(f"{int(out.momc.isna().sum())} precincts without a polygon")
    return out, polys, meta


def shares(g: pd.DataFrame) -> dict:
    return {"precincts": len(g), "voters": int(g.VOL_SEZNAM.sum()),
            "turnout": round(float(g.VYD_OBALKY.sum() / g.VOL_SEZNAM.sum()), 4),
            **{n: round(float(g[n].sum() / g.PL_HL_CELK.sum()), 4) for n in PARTIES.values()}}


def by_bins(d: pd.DataFrame, col: str, edges: list[float], labels: list[str]) -> dict:
    b = pd.cut(d[col], edges, labels=labels)
    return {str(k): shares(g) for k, g in d.groupby(b, observed=True)}


def model(d: pd.DataFrame, party: str) -> dict:
    """Party share (points) on panel share, family-house share, log distances; weighted by valid votes."""
    m = d.assign(y=100 * d[party] / d.PL_HL_CELK, panel=100 * d.panel_share, house=100 * d.house_share,
                 log_centre=np.log(d.centre_m / 1000), log_metro=np.log(d.metro_m / 1000))
    f = smf.wls("y ~ panel + house + log_centre + log_metro", data=m, weights=m.PL_HL_CELK).fit(cov_type="HC1")
    ci = f.conf_int()
    row = {"n": int(f.nobs), "r2": round(float(f.rsquared), 3)}
    for k, scale in [("panel", 10), ("house", 10), ("log_centre", 1), ("log_metro", 1)]:
        row[k] = [round(float(scale * v), 3) for v in (f.params[k], ci.loc[k, 0], ci.loc[k, 1])]
    return row


def district_names(codes: list[int]) -> dict[int, str]:
    feats = ruian(8, f"kod IN ({','.join(map(str, codes))})", "kod,nazev", "json")
    return {f["attributes"]["kod"]: f["attributes"]["nazev"] for f in feats}


def write_map(d: pd.DataFrame, polys: list, meta: pd.DataFrame) -> None:
    """Precinct shapes (simplified, rounded to ~10 m) with each precinct's numbers, for the interactive map."""
    names = district_names(sorted(d.OBEC.unique()))
    index = {(m, c): i for i, (m, c) in enumerate(zip(meta.momc, meta.cislo))}
    shares = d[list(PARTIES.values())].div(d.PL_HL_CELK, axis=0).round(3)
    feats = []
    for (_, r), (_, s) in zip(d.iterrows(), shares.iterrows()):
        geom = polys[index[(r.OBEC, r.OKRSEK)]].simplify(0.0002, preserve_topology=True)
        rings = [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in getattr(geom, "geoms", [geom])]
        feats.append({
            "d": names.get(r.OBEC, str(r.OBEC)), "n": int(r.OKRSEK), "r": rings,
            "t": round(r.VYD_OBALKY / r.VOL_SEZNAM, 3), "v": int(r.PL_HL_CELK),
            "p": round(float(r.panel_share), 2), "m": int(round(r.metro_m, -1)), "c": round(r.centre_m / 1000, 1),
            "s": s.to_dict(),
        })
    (OUT.parent / "precincts2025.json").write_text(json.dumps(feats, ensure_ascii=False, separators=(",", ":")))


def main() -> None:
    d = results()
    d, polys, meta = precincts(d)
    d = d[d.pocetbytu.notna()]
    redrawn = d.valid_from >= REDRAWN_FROM
    out = {
        "election": "Chamber of Deputies, 3-4 October 2025, Prague",
        "check_totals": {**shares(d), "precincts_without_flats": int(1119 - len(d))},
        "by_metro_distance": by_bins(d, "metro_m", [0, 500, 1000, 2000, 4000, 1e5],
                                     ["<0.5 km", "0.5-1 km", "1-2 km", "2-4 km", ">4 km"]),
        "by_centre_distance": by_bins(d, "centre_m", [0, 2000, 4000, 6000, 8000, 10000, 1e5],
                                      ["<2 km", "2-4 km", "4-6 km", "6-8 km", "8-10 km", ">10 km"]),
        "by_panel_share": by_bins(d, "panel_share", [-0.01, 0.1, 0.4, 0.7, 1.0], ["<10 %", "10-40 %", "40-70 %", ">70 %"]),
        "flats": int(d.pocetbytu.sum()), "panel_flats_share": round(float(d.panel_flats.sum() / d.pocetbytu.sum()), 4),
        "models": {p: model(d, p) for p in ["ANO", "Piráti", "SPOLU", "STAN", "SPD", "Motoristé", "Stačilo!"]},
        "models_without_redrawn": {p: model(d[~redrawn], p) for p in ["ANO", "Piráti", "SPOLU"]},
        "redrawn_after_election": int(redrawn.sum()),
        "correlations": {p: {c: round(float(np.corrcoef(v, d[p] / d.PL_HL_CELK)[0, 1]), 3)
                             for c, v in [("panel_share", d.panel_share), ("log_centre", np.log(d.centre_m)),
                                          ("log_metro", np.log(d.metro_m))]} for p in PARTIES.values()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    write_map(d, polys, meta)
    d[["OBEC", "OKRSEK", "lon", "lat", "metro_m", "centre_m", "panel_share", "PL_HL_CELK", *PARTIES.values()]].to_csv(
        RAW / "precincts.csv", index=False)
    print(json.dumps(out["check_totals"], ensure_ascii=False))
    print({p: m["log_metro"] for p, m in out["models"].items()})


if __name__ == "__main__":
    main()
