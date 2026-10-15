"""Regions of the GNSS design (§2): CZ, PL, BALT, CTRL and the check-6 regions AT, CH and Germany west of 10° E.

Built from Natural Earth 1:10 m admin 0 countries v5.1.2 (GeoJSON of the v5.1.2 tag), whose hash is recorded in
docs/research/gnss-files.sha256. A point is classified once against all regions in the order
CZ, PL, BALT, AT, CH, DEW; AT and CH together are CTRL, so a boundary point goes to the first region of the
registered order CZ, PL, BALT, CTRL, and DEW only takes points outside the four primary regions.

    uv run --no-project --with shapely --with numpy python -I tools/gnss/regions.py   # downloads once, builds the grid
"""
from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import box, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/gnss"
NE_DIR = DATA / "ne"
NE_NAME = "ne_10m_admin_0_countries.geojson"
NE_FILE = NE_DIR / NE_NAME
NE_URL = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/{NE_NAME}"
SHA_FILE = ROOT / "docs/research/gnss-files.sha256"
UA = "bsandova.com research"

PRIMARY = ("CZ", "PL", "BALT", "CTRL")
CHECK6 = ("AT", "CH", "DEW")
REGIONS = PRIMARY + CHECK6  # index into this tuple is the region id used in the outputs
REGION_ID = {r: i for i, r in enumerate(REGIONS)}

# Grid codes. The order of CODES is the boundary order: the first geometry covering a point wins.
NONE, AMBIG = 0, 255
CODES = ("CZ", "PL", "BALT", "AT", "CH", "DEW")  # code k + 1
CODE_PRIMARY = np.array([-1, REGION_ID["CZ"], REGION_ID["PL"], REGION_ID["BALT"], REGION_ID["CTRL"], REGION_ID["CTRL"],
                         -1], np.int16)
CODE_CHECK6 = np.array([-1, -1, -1, -1, REGION_ID["AT"], REGION_ID["CH"], REGION_ID["DEW"]], np.int16)

ADM0 = {"CZ": ["CZE"], "PL": ["POL"], "BALT": ["EST", "LVA", "LTU"], "AT": ["AUT"], "CH": ["CHE"], "DEW": ["DEU"]}
SEA_BAND_M = 22_000
DEW_EAST = 10.0
GRID_STEP = 0.01
GRID_BOX = (5.0, 45.0, 29.0, 60.5)  # lon0, lat0, lon1, lat1: holds every region with margin
EARTH_R = 6_371_008.8


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def recorded_hashes() -> dict[str, str]:
    if not SHA_FILE.exists():
        return {}
    out = {}
    for line in SHA_FILE.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            out[name.strip()] = digest
    return out


def record_hash(name: str, digest: str) -> None:
    hashes = recorded_hashes()
    hashes[name] = digest
    SHA_FILE.write_text("".join(f"{d}  {n}\n" for n, d in sorted(hashes.items())))


def ensure_ne() -> Path:
    if not NE_FILE.exists():
        NE_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(NE_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(NE_FILE.with_suffix(".part"), "wb") as f:
            f.write(r.read())
        NE_FILE.with_suffix(".part").rename(NE_FILE)
    digest = sha256(NE_FILE)
    known = recorded_hashes().get(NE_NAME)
    if known is None:
        record_hash(NE_NAME, digest)
    elif known != digest:
        raise RuntimeError(f"{NE_NAME}: sha256 {digest} differs from the recorded {known}")
    return NE_FILE


# Azimuthal equidistant projection on the sphere, centred on the Baltic states, so that the 22 km band is metric.
# Over a few hundred kilometres its scale error is below 0.1 %.
AEQD_CENTRE = (24.5, 57.0)


def _aeqd(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    l0, p0 = map(math.radians, AEQD_CENTRE)
    lam, phi = np.radians(lon), np.radians(lat)
    cos_c = np.sin(p0) * np.sin(phi) + np.cos(p0) * np.cos(phi) * np.cos(lam - l0)
    c = np.arccos(np.clip(cos_c, -1, 1))
    k = np.where(c > 1e-12, c / np.sin(np.where(c > 1e-12, c, 1)), 1.0)
    x = EARTH_R * k * np.cos(phi) * np.sin(lam - l0)
    y = EARTH_R * k * (np.cos(p0) * np.sin(phi) - np.sin(p0) * np.cos(phi) * np.cos(lam - l0))
    return x, y


def _aeqd_inv(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    l0, p0 = map(math.radians, AEQD_CENTRE)
    rho = np.hypot(x, y)
    c = rho / EARTH_R
    safe = np.where(rho > 1e-9, rho, 1)
    phi = np.arcsin(np.clip(np.cos(c) * np.sin(p0) + np.where(rho > 1e-9, y * np.sin(c) * np.cos(p0) / safe, 0), -1, 1))
    lam = l0 + np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c))
    return np.degrees(lam), np.degrees(phi)


def _project(geom, fwd: bool):
    f = _aeqd if fwd else _aeqd_inv
    return shapely.transform(geom, lambda xy: np.column_stack(f(xy[:, 0], xy[:, 1])))


def build_regions(features: list[dict]) -> dict[str, shapely.Geometry]:
    by_a3: dict[str, list] = {}
    for feat in features:
        a3 = feat["properties"]["ADM0_A3"]
        by_a3.setdefault(a3, []).append(shape(feat["geometry"]))
    country = {a3: unary_union(gs) for a3, gs in by_a3.items()}

    def union(codes):
        return unary_union([country[c] for c in codes])

    geoms = {name: union(codes) for name, codes in ADM0.items() if name not in ("BALT", "DEW")}
    balt_land = union(ADM0["BALT"])
    band = _project(_project(balt_land, True).buffer(SEA_BAND_M, quad_segs=32), False)
    others = [g for a3, g in country.items() if a3 not in ADM0["BALT"] and g.intersects(band)]
    geoms["BALT"] = unary_union([balt_land, band.difference(unary_union(others))])
    geoms["DEW"] = union(ADM0["DEW"]).intersection(box(-180, -90, DEW_EAST, 90))
    return {name: geoms[name] for name in CODES}


def _exact(geoms: list, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    out = np.zeros(lon.shape, np.uint8)
    todo = np.ones(lon.shape, bool)
    for k, g in enumerate(geoms):
        if not todo.any():
            break
        idx = np.flatnonzero(todo)
        hit = shapely.intersects_xy(g, lon[idx], lat[idx])  # covers: a boundary point is inside
        out[idx[hit]] = k + 1
        todo[idx[hit]] = False
    return out


def build_grid(geoms: list, step: float = GRID_STEP, bbox=GRID_BOX) -> np.ndarray:
    lon0, lat0, lon1, lat1 = bbox
    nx, ny = round((lon1 - lon0) / step), round((lat1 - lat0) / step)
    cx = lon0 + (np.arange(nx) + 0.5) * step
    cy = lat0 + (np.arange(ny) + 0.5) * step
    gx, gy = np.meshgrid(cx, cy)
    gx, gy = gx.ravel(), gy.ravel()
    grid = _exact(geoms, gx, gy)
    # A cell whose centre lies farther than its half-diagonal from every boundary lies wholly on one side.
    half_diag = step * math.sqrt(2) / 2 * 1.01
    edge = np.zeros(gx.shape, bool)
    for g in geoms:
        b = g.boundary
        shapely.prepare(b)
        x0, y0, x1, y1 = b.bounds
        near = np.flatnonzero((gx > x0 - step) & (gx < x1 + step) & (gy > y0 - step) & (gy < y1 + step))
        edge[near[shapely.dwithin(b, shapely.points(gx[near], gy[near]), half_diag)]] = True
    grid[edge] = AMBIG
    return grid.reshape(ny, nx)


class RegionIndex:
    def __init__(self, geoms: dict[str, shapely.Geometry], grid: np.ndarray | None = None,
                 step: float = GRID_STEP, bbox=GRID_BOX):
        self.geoms = [geoms[name] for name in CODES]
        for g in self.geoms:
            shapely.prepare(g)
        self.step, self.bbox = step, bbox
        self.grid = build_grid(self.geoms, step, bbox) if grid is None else grid

    def codes(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        lon0, lat0, _, _ = self.bbox
        ny, nx = self.grid.shape
        ix = np.floor((lon - lon0) / self.step).astype(np.int64)
        iy = np.floor((lat - lat0) / self.step).astype(np.int64)
        inside = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
        out = np.zeros(lon.shape, np.uint8)
        out[inside] = self.grid[iy[inside], ix[inside]]
        amb = np.flatnonzero(out == AMBIG)
        if amb.size:
            out[amb] = _exact(self.geoms, lon[amb], lat[amb])
        return out

    def regions(self, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        c = self.codes(np.asarray(lon, float), np.asarray(lat, float))
        return CODE_PRIMARY[c], CODE_CHECK6[c]

    def save(self, path: Path) -> None:
        wkb = {f"wkb_{n}": np.frombuffer(shapely.to_wkb(g), np.uint8) for n, g in zip(CODES, self.geoms)}
        np.savez_compressed(path, grid=self.grid, step=self.step, bbox=np.array(self.bbox), **wkb)

    @classmethod
    def load(cls, path: Path) -> RegionIndex:
        z = np.load(path)
        geoms = {n: shapely.from_wkb(z[f"wkb_{n}"].tobytes()) for n in CODES}
        return cls(geoms, grid=z["grid"], step=float(z["step"]), bbox=tuple(z["bbox"]))


def cache_path() -> Path:
    return DATA / f"regions-{sha256(NE_FILE)[:12]}.npz"


def load_index() -> RegionIndex:
    ensure_ne()
    path = cache_path()
    if path.exists():
        return RegionIndex.load(path)
    features = json.loads(NE_FILE.read_text())["features"]
    idx = RegionIndex(build_regions(features))
    idx.save(path)
    return idx


if __name__ == "__main__":
    import time

    t = time.time()
    idx = load_index()
    amb = float((idx.grid == AMBIG).mean())
    print(f"regions ready in {time.time() - t:.1f} s; grid {idx.grid.shape}, boundary cells {amb:.2%}")
    for name, g in zip(CODES, idx.geoms):
        print(f"  {name}: bounds {tuple(round(v, 2) for v in g.bounds)}")
