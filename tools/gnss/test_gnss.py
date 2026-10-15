"""Worked examples on made-up traces for the GNSS data step (design §2, §3). No real adsb.lol data is read."""
from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import count as C
import fetch as F
import regions as R
import screen as S

FIX = HERE / "fixtures"

# Toy regions: CZ and PL share lon 16, CZ and AT share lat 49, CH and DEW share lon 10.
TOY = {"CZ": box(14, 49, 16, 51), "PL": box(16, 49, 20, 53), "BALT": box(21, 54, 26, 58),
       "AT": box(14, 47, 16, 49), "CH": box(10, 47, 14, 48), "DEW": box(6, 48, 10, 52)}


@pytest.fixture(scope="module")
def toy():
    return R.RegionIndex(TOY, step=0.1)


IN_CZ = (50.0, 15.0)
IN_PL = (51.0, 18.0)
OUT = (50.0, 12.5)  # between DEW and CZ, in no region


def pt(t, pos=IN_CZ, alt=36_000, flags=0, det=True, typ="adsb_icao", version=2, nacp=9, nic=8, **extra):
    d = None
    if det:
        d = {"type": typ, "version": version, "nac_p": nacp, "nic": nic, "sil": 3, **extra}
        for k in ("version", "nac_p", "nic"):
            if d[k] is MISSING:
                del d[k]
    return [float(t), pos[0], pos[1], alt, 450.0, 90.0, flags, 0, d, typ, None, None, None, None]


MISSING = object()


def run(points, idx, icao="4b1a2c", ts=1_700_000_000.0):
    return C.count_aircraft({"icao": icao, "timestamp": ts, "trace": points}, idx)


def U(a, variant="primary", region="CZ", band=None):
    return _sum(a.usable, variant, region, band)


def D(a, variant="primary", region="CZ", band=None):
    return _sum(a.degraded, variant, region, band)


def _sum(arr, variant, region, band):
    row = arr[C.VI[variant]].reshape(C.NR, C.NB)[R.REGION_ID[region]]
    return int(row.sum() if band is None else row[band])


def lead_in(t_end, pos=IN_CZ):
    """Non-usable points in the region (no details) covering the 2-minute buffer before t_end."""
    return [pt(t, pos, det=False) for t in range(0, t_end, 20)]


# --- usable point (§2) -------------------------------------------------------------------------------------------

def test_usable_base_point_counts(toy):
    a = run(lead_in(200) + [pt(200)], toy)
    assert U(a) == 1 and D(a) == 0


@pytest.mark.parametrize("kw", [
    {"typ": "mlat"}, {"typ": "adsb_icao_nt"}, {"typ": "adsr_icao"}, {"flags": 1}, {"det": False},
    {"version": 1}, {"version": 0}, {"version": MISSING}, {"nacp": MISSING}, {"nacp": None},
    {"alt": 24_975}, {"alt": "ground"}, {"alt": None},
])
def test_usable_each_condition_excludes(toy, kw):
    a = run(lead_in(200) + [pt(200, **kw)], toy)
    assert U(a) == 0 and U(a, "c8_nobuf") == 0


def test_usable_altitude_floor_inclusive(toy):
    assert U(run(lead_in(200) + [pt(200, alt=25_000)], toy)) == 1


def test_top_level_version_is_ignored(toy):
    d = {"icao": "4b1a2c", "timestamp": 0.0, "version": "wiedehopf readsb v3.14", "trace": lead_in(200) + [pt(200)]}
    assert U(C.count_aircraft(d, toy)) == 1


def test_tilde_address_dropped(toy):
    assert run([pt(0)], toy, icao="~4b1a2c") is None


def test_nacp_nonnumeric_is_counted_in_screening(toy):
    a = run([pt(0, nacp=None), pt(10)], toy)
    assert a.stats[R.REGION_ID["CZ"], C.STATS.index("nacp_nonnumeric")] == 1


# --- stale points and leg markers --------------------------------------------------------------------------------

def test_stale_points_do_not_enter_a_region(toy):
    # outside, then a stale point inside, then non-stale inside: entry is the non-stale point at t=60
    pts = [pt(0, OUT, det=False), pt(30, flags=1, det=False), pt(60, det=False), pt(170), pt(180)]
    a = run(pts, toy)
    assert U(a) == 1  # 170 - 60 < 120 is in the buffer, 180 - 60 = 120 is not
    assert len(a.crossings) == 1 and a.crossings[0, 1] == 1_700_000_060.0


def test_stale_points_are_not_usable_anywhere(toy):
    a = run(lead_in(200) + [pt(200, flags=1), pt(210, flags=1 | 2)], toy)
    assert U(a) == 0 and U(a, "c8_nobuf") == 0 and U(a, "c2_anyalt") == 0
    assert a.stats[R.REGION_ID["CZ"], C.STATS.index("stale")] == 2


def test_entry_judged_on_points_of_any_source(toy):
    # an mlat point inside starts the crossing; the ADS-B usable point 120 s later is outside the buffer
    a = run([pt(0, OUT, det=False), pt(10, typ="mlat", det=False), pt(130)], toy)
    assert U(a) == 1


# --- entry buffer -------------------------------------------------------------------------------------------------

def test_entry_buffer_first_point_of_day(toy):
    a = run([pt(t) for t in range(0, 301, 30)], toy)  # 0, 30, ..., 300
    assert U(a, "c8_nobuf") == 11
    assert U(a) == 7  # 120..300


def test_entry_buffer_after_outside_point(toy):
    pts = [pt(0, OUT), pt(30, OUT), pt(60), pt(90), pt(179), pt(180), pt(240)]
    a = run(pts, toy)
    assert U(a) == 2 and U(a, "c8_nobuf") == 5
    assert U(a, region="CZ", variant="primary") == 2


def test_reentry_gets_new_buffer(toy):
    pts = [pt(0), pt(200), pt(260, OUT), pt(300), pt(360), pt(420)]
    a = run(pts, toy)
    assert len(a.crossings) == 1 + 1 and U(a) == 1 + 1  # 200 in the first crossing, 420 in the second


def test_crossing_into_neighbouring_region_starts_its_buffer(toy):
    pts = [pt(0), pt(300), pt(360, IN_PL), pt(420, IN_PL), pt(480, IN_PL)]
    a = run(pts, toy)
    assert U(a, region="CZ") == 1 and U(a, region="PL") == 1


# --- crossing split at gaps of more than 10 minutes -----------------------------------------------------------------

def test_gap_over_ten_minutes_splits(toy):
    pts = [pt(0), pt(200), pt(200 + 601), pt(200 + 601 + 60), pt(200 + 601 + 120)]
    a = run(pts, toy)
    assert len(a.crossings) == 2
    assert U(a) == 2  # 200, and 921 (120 s after the new entry at 801)


def test_gap_of_exactly_ten_minutes_does_not_split(toy):
    pts = [pt(0), pt(200), pt(800), pt(860)]
    a = run(pts, toy)
    assert len(a.crossings) == 1 and U(a) == 3


def test_gap_measured_on_non_stale_points(toy):
    # a stale point in the middle of an 11-minute gap does not bridge it
    pts = [pt(0), pt(200), pt(500, flags=1, det=False), pt(801), pt(830)]
    a = run(pts, toy)
    assert len(a.crossings) == 2 and U(a) == 1


# --- boundary order and regions -------------------------------------------------------------------------------------

def test_boundary_order_toy(toy):
    p, c = toy.regions(np.array([16.0, 15.0, 10.0, 8.0, 12.5]), np.array([50.0, 49.0, 47.5, 50.0, 50.0]))
    assert [R.REGIONS[i] if i >= 0 else None for i in p] == ["CZ", "CZ", "CTRL", None, None]
    assert [R.REGIONS[i] if i >= 0 else None for i in c] == [None, None, "CH", "DEW", None]


def test_grid_agrees_with_exact_lookup(toy):
    rng = np.random.default_rng(1)
    lon, lat = rng.uniform(5, 29, 50_000), rng.uniform(45, 60.5, 50_000)
    lon = np.r_[lon, 16.0, 16.0, 14.0, 10.0]  # boundary points too
    lat = np.r_[lat, 50.0, 49.0, 49.0, 47.5]
    assert (toy.codes(lon, lat) == R._exact(toy.geoms, lon, lat)).all()


def test_ctrl_points_are_also_at_or_ch(toy):
    a = run([pt(t, (48.0, 15.0)) for t in range(0, 301, 60)], toy)  # inside AT
    assert U(a, region="CTRL") == U(a, region="AT") == 4 and U(a, region="CH") == 0


needs_ne = pytest.mark.skipif(not R.NE_FILE.exists(), reason="Natural Earth file not downloaded")


@pytest.fixture(scope="module")
def ne():
    return R.load_index()


def _names(idx, lonlat):
    lon, lat = np.array([p[0] for p in lonlat]), np.array([p[1] for p in lonlat])
    p, c = idx.regions(lon, lat)
    return [(R.REGIONS[a] if a >= 0 else None, R.REGIONS[b] if b >= 0 else None) for a, b in zip(p, c)]


@needs_ne
def test_real_regions_cities(ne):
    assert _names(ne, [(14.42, 50.08), (21.01, 52.23), (24.11, 56.95), (24.75, 59.44), (25.28, 54.69),
                       (16.37, 48.21), (8.54, 47.37), (8.68, 50.11), (11.58, 48.14), (20.51, 54.71),
                       (27.56, 53.90)]) == [
        ("CZ", None), ("PL", None), ("BALT", None), ("BALT", None), ("BALT", None), ("CTRL", "AT"), ("CTRL", "CH"),
        (None, "DEW"), (None, None), (None, None), (None, None)]


@needs_ne
def test_real_baltic_sea_band(ne):
    # off Liepaja (21.0 E, 56.5 N): the coast is near 21.0; 10 km out is in, 40 km out is not
    lon_10 = 21.0 - 10 / (111.32 * np.cos(np.radians(56.5)))
    lon_40 = 21.0 - 40 / (111.32 * np.cos(np.radians(56.5)))
    names = _names(ne, [(lon_10, 56.5), (lon_40, 56.5)])
    assert names == [("BALT", None), (None, None)]
    band = ne.geoms[R.CODES.index("BALT")]
    others = ne.geoms[R.CODES.index("PL")]
    assert band.intersection(others).area < 1e-9  # the band does not cover Polish land


@needs_ne
def test_real_boundary_vertices_follow_order(ne):
    g = {n: ne.geoms[R.CODES.index(n)] for n in R.CODES}
    for first, second, expect in (("CZ", "AT", ("CZ", None)), ("CZ", "PL", ("CZ", None)),
                                  ("PL", "BALT", ("PL", None)), ("AT", "CH", ("CTRL", "AT")),
                                  ("CH", "DEW", ("CTRL", "CH"))):
        shared = g[first].boundary.intersection(g[second])
        assert not shared.is_empty, (first, second)
        x, y = shared.representative_point().coords[0]
        assert _names(ne, [(x, y)]) == [expect], (first, second)


@needs_ne
def test_real_dew_clipped_at_10e(ne):
    assert _names(ne, [(9.99, 51.0), (10.01, 51.0)]) == [(None, "DEW"), (None, None)]


# --- position jumps (Q4) --------------------------------------------------------------------------------------------

def _east(nm, lat=IN_CZ[0]):
    return nm * C.NM_M / 1000 / (C.EARTH_KM * np.cos(np.radians(lat)) * np.pi / 180)


def test_jump_positive(toy):
    far = (IN_CZ[0], IN_CZ[1] + _east(20))
    a = run([pt(0, det=False), pt(30, far, det=False)], toy)  # 20 NM in 30 s = 2 400 kt
    assert a.crossings[:, 5].tolist() == [1]


@pytest.mark.parametrize("case", ["dt61", "short", "slow", "leg", "leg_on_stale_between", "mlat", "outside"])
def test_jump_negative(toy, case):
    lat, lon = IN_CZ
    pts = {
        "dt61": [pt(0), pt(61, (lat, lon + _east(30)))],
        "short": [pt(0), pt(1, (lat, lon + _east(1.9)))],  # 6 840 kt but under 2 NM
        "slow": [pt(0), pt(30, (lat, lon + _east(9.9)))],  # 1 188 kt
        "leg": [pt(0), pt(30, (lat, lon + _east(20)), flags=2)],
        "leg_on_stale_between": [pt(0), pt(10, flags=1 | 2), pt(30, (lat, lon + _east(20)))],
        "mlat": [pt(0, typ="mlat", det=False), pt(30, (lat, lon + _east(20)))],
        "outside": [pt(0, (lat, 13.9)), pt(30, (lat, 13.9 + _east(20)))],
    }[case]
    a = run(pts, toy)
    assert not a.crossings[:, 5].any()


def test_jump_skips_stale_between(toy):
    lat, lon = IN_CZ
    a = run([pt(0), pt(10, (lat, lon + 1), flags=1), pt(30, (lat, lon + _east(20)))], toy)
    assert a.crossings[:, 5].tolist() == [1]


def test_jump_crossing_counted_once(toy):
    lat, lon = IN_CZ
    a = run([pt(0), pt(30, (lat, lon + _east(20))), pt(60), pt(90, (lat, lon + _east(20)))], toy)
    assert len(a.crossings) == 1 and a.crossings[0, 5] == 1


def test_jump_needs_both_points_in_the_same_region(toy):
    a = run([pt(0, (50.0, 15.95)), pt(20, (50.0, 16.05 + _east(20)))], toy)  # CZ -> PL
    assert not a.crossings[:, 5].any()


# --- degraded points and variants ------------------------------------------------------------------------------------

def test_degraded_threshold_primary_and_check10(toy):
    pts = lead_in(200) + [pt(200, nacp=8), pt(210, nacp=7), pt(220, nacp=6), pt(230, nacp=0)]
    a = run(pts, toy)
    assert U(a) == 4 and D(a) == 3
    assert U(a, "c10_nacp7") == 4 and D(a, "c10_nacp7") == 2


def test_check1_nic(toy):
    pts = lead_in(200) + [pt(200, nic=7), pt(210, nic=6), pt(220, nic=MISSING, nacp=5)]
    a = run(pts, toy)
    assert U(a, "c1_nic") == 2 and D(a, "c1_nic") == 1
    assert U(a) == 3 and D(a) == 1


def test_check2_any_altitude(toy):
    pts = lead_in(200) + [pt(200, alt=5_000, nacp=5), pt(210, alt="ground"), pt(220)]
    a = run(pts, toy)
    assert U(a) == 1 and U(a, "c2_anyalt") == 3 and D(a, "c2_anyalt") == 1


def test_check3_versions_1_and_2(toy):
    pts = lead_in(200) + [pt(200, version=1, nacp=4), pt(210), pt(220, version=0)]
    a = run(pts, toy)
    assert U(a) == 1 and U(a, "c3_v12") == 2 and D(a, "c3_v12") == 1


def test_check8_no_buffer(toy):
    a = run([pt(0, nacp=3), pt(60), pt(130, nacp=3)], toy)
    assert (U(a), D(a)) == (1, 1)
    assert (U(a, "c8_nobuf"), D(a, "c8_nobuf")) == (3, 2)


def test_crossing_rows_check11(toy):
    pts = [pt(0, nacp=2)] + [pt(120 + 10 * k, nacp=5 if k < 2 else 9) for k in range(4)]
    a = run(pts, toy)
    region, _, n_points, ub, db, jump, _ = a.crossings[0]
    assert R.REGIONS[int(region)] == "CZ" and (n_points, ub, db, jump) == (5, 4, 2, 0)


# --- airframe screen: west of 5 E ---------------------------------------------------------------------------------

def test_west_of_5e_counts(toy):
    pts = [pt(0, (48.0, 4.9), nacp=5), pt(10, (48.0, 5.0)), pt(20, (40.6, -73.8)), pt(30, (48.0, 2.0), alt=10_000),
           pt(40, (48.0, 2.0), flags=1), pt(50, (48.0, 2.0), version=1)]
    a = run(pts, toy)
    assert (a.west_usable, a.west_degraded) == (2, 1)  # no buffer applies west of 5 E


# --- check 12: first 40 usable points after the buffer per aircraft-region-day -------------------------------------

def test_cap40_per_region_day(toy):
    cz = [pt(t, nacp=5 if t >= 120 + 40 * 10 else 9) for t in range(0, 120 + 60 * 10, 10)]  # 60 after the buffer
    a = run(cz, toy)
    assert U(a) == 60 and D(a) == 20
    assert U(a, "c12_cap40") == 40 and D(a, "c12_cap40") == 0


def test_cap40_spans_crossings_and_is_per_region(toy):
    first = [pt(t) for t in range(0, 120 + 30 * 10, 10)]  # 30 after buffer
    second = [pt(2000 + t) for t in range(0, 120 + 30 * 10, 10)]  # gap > 10 min: new crossing, 30 more
    pl = [pt(5000 + t, IN_PL) for t in range(0, 120 + 50 * 10, 10)]
    a = run(first + second + pl, toy)
    assert U(a) == 60 and U(a, "c12_cap40") == 40
    assert U(a, region="PL") == 50 and U(a, "c12_cap40", "PL") == 40


# --- distance bands from Kaliningrad ---------------------------------------------------------------------------------

def _south(km):
    return C.KALININGRAD[0] - km / (C.EARTH_KM * np.pi / 180), C.KALININGRAD[1]


def test_band_edges():
    lat, lon = zip(*[_south(k) for k in (0, 299.9, 300.1, 599.9, 600.1, 899.9, 900.1, 2000)])
    assert C.band_of(np.array(lat), np.array(lon)).tolist() == [0, 0, 1, 1, 2, 2, 3, 3]


def test_band_of_cities():
    assert C.band_of([50.08, 56.95], [14.42, 24.11]).tolist() == [2, 1]  # Prague about 720 km, Riga about 380 km


def test_points_and_crossings_by_band(toy):
    near = (54.5, 21.5)  # in toy BALT, about 70 km from Kaliningrad: band 0
    far = (57.5, 24.0)  # in toy BALT, about 370 km: band 1
    a = run([pt(t, near) for t in range(0, 301, 60)] + [pt(t, far) for t in range(360, 601, 60)], toy)
    assert U(a, region="BALT", band=0) == 4 and U(a, region="BALT", band=1) == 5
    assert len(a.crossings) == 1 and int(a.crossings[0, 6]) == 0b11


# --- the day: streaming, two processes, outputs ------------------------------------------------------------------

def _tar(tmp_path, traces: dict[str, dict], split: int | None = None, name="day"):
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w") as tf:
        for extra in ("./acas/acas.csv.gz",):
            info = tarfile.TarInfo(extra)
            info.size = 3
            tf.addfile(info, io.BytesIO(b"abc"))
        for icao, d in traces.items():
            raw = gzip.compress(json.dumps(d).encode())
            info = tarfile.TarInfo(f"./traces/{icao[-2:]}/trace_full_{icao}.json")
            info.size = len(raw)
            tf.addfile(info, io.BytesIO(raw))
    data = bio.getvalue()
    if split is None:
        p = tmp_path / f"{name}.tar"
        p.write_bytes(data)
        return [p]
    paths = []
    for k, i in enumerate(range(0, len(data), split)):
        p = tmp_path / f"{name}.tar.a{'abcdefghijklmnopqrstuvwxyz'[k]}"
        p.write_bytes(data[i:i + split])
        paths.append(p)
    return paths


def _fleet(n=40):
    out = {}
    for k in range(n):
        icao = f"4b{k:04x}"
        out[icao] = {"icao": icao, "timestamp": 1_700_000_000.0 + k,
                     "trace": [pt(t, IN_CZ if k % 2 else IN_PL, nacp=5 if k % 3 == 0 else 9) for t in range(0, 400, 20)]
                     + [pt(1000 + t, (48.0, 3.0)) for t in range(0, 400, 20)]}
    out["~1234ab"] = {"icao": "~1234ab", "timestamp": 0.0, "trace": [pt(0)]}
    return out


def test_count_day_one_and_two_processes_agree(tmp_path, toy):
    idx_path = tmp_path / "toy.npz"
    toy.save(idx_path)
    paths = _tar(tmp_path, _fleet(), split=4096)
    assert len(paths) > 2
    n1 = C.count_day(paths, tmp_path / "w1", "2024-01-03", toy, idx_path, workers=1, batch=7)
    n2 = C.count_day(paths, tmp_path / "w2", "2024-01-03", toy, idx_path, workers=2, batch=7)
    for k in ("trace_files", "tilde", "aircraft", "bad_files", "points"):
        assert n1[k] == n2[k]
    assert (n1["trace_files"], n1["tilde"], n1["aircraft"]) == (41, 1, 40)
    for name in ("screening/points", "sealed/points", "screening/crossings", "sealed/crossings",
                 "screening/crossings_agg", "sealed/crossings_agg", "screening/west", "sealed/west",
                 "screening/region_day", "screening/mix"):
        a = pd.read_parquet(tmp_path / "w1" / f"{name}.parquet")
        b = pd.read_parquet(tmp_path / "w2" / f"{name}.parquet")
        keys = [c for c in a.columns if c in ("icao", "variant", "region", "band", "crossing", "type", "version",
                                              "fl250")]
        pd.testing.assert_frame_equal(a.sort_values(keys).reset_index(drop=True),
                                      b.sort_values(keys).reset_index(drop=True))


def test_day_outputs_split_screening_from_sealed(tmp_path, toy):
    paths = _tar(tmp_path, _fleet(6))
    C.count_day(paths, tmp_path / "d", "2024-01-03", toy, workers=1)
    for f in (tmp_path / "d" / "screening").glob("*.parquet"):
        cols = set(pd.read_parquet(f).columns)
        assert not cols & {"degraded", "degraded_buf", "jump", "jump_crossings", "jump_crossings_usable"}, f.name
    pts = pd.read_parquet(tmp_path / "d/screening/points.parquet")
    deg = pd.read_parquet(tmp_path / "d/sealed/points.parquet")
    assert (pts.drop(columns="usable") == deg.drop(columns="degraded")).all().all()
    prim = pts[(pts.variant == "primary")].groupby("region")["usable"].sum()
    assert prim["CZ"] == 3 * 14 and prim["PL"] == 3 * 14  # 20 points a crossing, 6 in the buffer
    west = pd.read_parquet(tmp_path / "d/screening/west.parquet")
    assert len(west) == 6 and (west["usable"] == 20).all()
    agg = pd.read_parquet(tmp_path / "d/screening/crossings_agg.parquet")
    assert agg.loc[agg.band == "all", "crossings"].sum() == 6


def test_truncated_tar_is_unreadable(tmp_path, toy):
    [p] = _tar(tmp_path, _fleet(6))
    p.write_bytes(p.read_bytes()[:3000])
    with pytest.raises(C.Unreadable):
        C.count_day([p], tmp_path / "d", "2024-01-03", toy, workers=1)


def test_corrupt_member_is_counted_not_fatal(tmp_path, toy):
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w") as tf:
        info = tarfile.TarInfo("./traces/aa/trace_full_4b00aa.json")
        info.size = 4
        tf.addfile(info, io.BytesIO(b"\x1f\x8bxx"))
    p = tmp_path / "c.tar"
    p.write_bytes(bio.getvalue())
    with pytest.raises(C.SchemaDrift):  # one bad file of one: the format changed, the run stops
        C.count_day([p], tmp_path / "d", "2024-01-03", toy, workers=1)
    assert not (tmp_path / "d").exists()


@needs_ne
def test_fixture_flight_over_prague(ne):
    d = json.loads((FIX / "trace_full_4b9f01.json").read_text())
    a = C.count_aircraft(d, ne)
    # entry at t=60; 60 and 90 are in the buffer, 120 is stale, 360 is below FL250
    assert U(a, "c8_nobuf") == 6 and U(a) == 4
    assert D(a) == 1 and U(a, region="CZ", band=2) == 4 and U(a, "c1_nic") == 3
    assert not a.crossings[:, 5].any()


# --- sample, study years, holidays, Thursday replacement ------------------------------------------------------------

def test_sample_has_190_wednesdays():
    days = F.sample_days()
    assert len(days) == 190 and days[0] == dt.date(2023, 3, 1) and days[-1] == dt.date(2026, 10, 14)
    assert all(d.weekday() == 2 for d in days)


def test_study_years():
    assert [F.study_year(dt.date(*x)) for x in ((2023, 3, 1), (2024, 2, 28), (2024, 3, 6), (2025, 2, 26),
                                               (2025, 3, 5), (2026, 2, 25), (2026, 3, 4), (2026, 10, 14))] == \
        [1, 1, 2, 2, 3, 3, 4, 4]


def test_holiday_wednesdays():
    hol = [d for d in F.sample_days() if d in F.czech_holidays(d.year)]
    assert dt.date(2024, 5, 8) in hol and dt.date(2025, 12, 24) in hol
    assert F.easter(2024) == dt.date(2024, 3, 31) and F.easter(2026) == dt.date(2026, 4, 5)


def test_asset_urls_and_part_order():
    assert F.asset_url(dt.date(2026, 1, 1), "tar.aa") == ("https://github.com/adsblol/globe_history_2026/releases/"
                                                          "download/v2026.01.01-planes-readsb-prod-0/"
                                                          "v2026.01.01-planes-readsb-prod-0.tar.aa")
    gen = F.part_suffixes()
    assert [next(gen) for _ in range(4)] == ["tar", "tar.aa", "tar.ab", "tar.ac"]


def test_find_parts_probes_in_order(monkeypatch):
    have = {"tar.aa", "tar.ab", "tar.ac"}
    seen = []

    def fake_exists(url):
        seen.append(url.rsplit("-0.", 1)[1])
        return seen[-1] in have
    monkeypatch.setattr(F, "exists", fake_exists)
    parts = F.find_parts(dt.date(2024, 6, 5))
    assert [u.rsplit("-0.", 1)[1] for u in parts] == ["tar.aa", "tar.ab", "tar.ac"]
    assert seen == ["tar", "tar.aa", "tar.ab", "tar.ac", "tar.ad"]


def _attempt(unreadable: set[dt.date]):
    def f(d):
        if d in unreadable:
            raise C.Unreadable("release missing")
        return {"date_used": str(d), "trace_files": 100}
    return f


def test_thursday_replacement():
    wed = dt.date(2025, 12, 31)
    thu = dt.date(2026, 1, 1)
    assert F.resolve_day(wed, _attempt(set()))["status"] == "counted"
    m = F.resolve_day(wed, _attempt({wed}))
    assert m["status"] == "replaced" and m["date_used"] == str(thu) and m["study_year"] == 3
    assert F.asset_url(thu, "tar").startswith("https://github.com/adsblol/globe_history_2026/")
    lost = F.resolve_day(wed, _attempt({wed, thu}))
    assert lost["status"] == "lost" and set(lost["unreadable"]) == {str(wed), str(thu)}


def test_network_down_is_not_a_lost_day():
    def f(d):
        raise F.NetworkDown("no route")
    with pytest.raises(F.NetworkDown):
        F.resolve_day(dt.date(2024, 1, 3), f)


def test_low_count_rule():
    days = F.sample_days()[:9]
    counts = dict(zip(days, [100, 100, 100, 100, 69, 100, 100, 100, 71]))
    nb = F.nearest(days[4], counts)
    assert sorted(nb) == [days[2], days[3], days[5], days[6]]
    assert F.nearest(days[0], counts) == [days[1], days[2], days[3], days[4]]
    low = F.low_days(counts)
    assert set(low) == {days[4]}  # 71 is not below 70 % of a median of 100


def test_postpass_replaces_low_wednesday_by_thursday(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DAYS", tmp_path)
    days = F.sample_days()
    counts = {d: 100 for d in days}
    counts[days[10]] = 50
    counts[days[20]] = 50
    for d in days:
        status = "replaced" if d == days[20] else "counted"
        used = d + dt.timedelta(days=1) if status == "replaced" else d
        F.write_manifest(d, {"wednesday": str(d), "status": status, "study_year": F.study_year(d),
                             "date_used": str(used), "trace_files": counts[d], "unreadable": {}})
    calls = []

    def attempt(d, day_dir):
        calls.append(d)
        day_dir.mkdir(parents=True, exist_ok=True)
        return {"date_used": str(d), "trace_files": 95}
    F.postpass(attempt)
    m10, m20 = F.read_manifest(days[10]), F.read_manifest(days[20])
    assert calls == [days[10] + dt.timedelta(days=1)]
    assert m10["status"] == "replaced" and m10["date_used"] == str(days[10] + dt.timedelta(days=1))
    assert m20["status"] == "lost"  # already a Thursday: nothing left to replace it
    assert (tmp_path / f"{days[10]}.low-{days[10]}").exists()
    F.postpass(attempt)
    assert len(calls) == 1  # checked days are not flagged again


def test_postpass_low_thursday_is_lost(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DAYS", tmp_path)
    days = F.sample_days()
    for d in days:
        F.write_manifest(d, {"wednesday": str(d), "status": "counted", "study_year": F.study_year(d),
                             "date_used": str(d), "trace_files": 40 if d == days[5] else 100, "unreadable": {}})
    F.postpass(lambda d, day_dir: {"date_used": str(d), "trace_files": 60})
    assert F.read_manifest(days[5])["status"] == "lost"


def test_postpass_waits_for_all_days(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DAYS", tmp_path)
    d = F.sample_days()[0]
    F.write_manifest(d, {"wednesday": str(d), "status": "counted", "study_year": 1, "date_used": str(d),
                         "trace_files": 1, "unreadable": {}})
    F.postpass(lambda *a: pytest.fail("fetched before all days were in"))


def test_parse_kp():
    text = ("#YYY MM DD  days  days_m  Bsr dB    Kp1 ...\n"
            "2024 05 10 33733 33733.5 2600 13  3.667  4.000  5.333  7.667  8.667  9.000  8.667  9.000"
            "   22   27   56  179  322  400  322  400   241 210    217.4    222.6 0\n"
            "2024 05 11 33734 33734.5 2600 14  4.667  4.667  4.000  3.333  2.667  2.000  1.667  4.333"
            "   39   39   27   18   12    7    6   32    23 200    200.0    206.0 0\n"
            "2026 10 15 34245 34245.5 2700  1  2.000 -1.000 -1.000 -1.000 -1.000 -1.000 -1.000 -1.000"
            "    7   -1   -1   -1   -1   -1   -1   -1    -1  -1     -1.0     -1.0 0\n")
    kp = F.parse_kp(text)
    assert kp == {"2024-05-10": 9.0, "2024-05-11": 4.667, "2026-10-15": None}


# --- screening report --------------------------------------------------------------------------------------------

def test_screen_reads_only_screening(tmp_path, toy, monkeypatch):
    days = F.sample_days()
    fleet = _fleet(6)
    for k, d in enumerate(days[:3]):
        out = tmp_path / str(d)
        paths = _tar(tmp_path, fleet, name=f"t{k}")
        n = C.count_day(paths, out, str(d), toy, workers=1)
        (out / "sealed" / "points.parquet").write_bytes(b"not parquet")  # would fail if read
        (out / "manifest.json").write_text(json.dumps({"wednesday": str(d), "status": "counted", "study_year": 1,
                                                       "date_used": str(d), "unreadable": {}, **n}))
    aside = tmp_path / f"{days[0]}.low-{days[0]}" / "screening"
    aside.mkdir(parents=True)
    (aside / "points.parquet").write_bytes(b"set aside, never read")
    lost = days[3]
    (tmp_path / str(lost)).mkdir()
    (tmp_path / str(lost) / "manifest.json").write_text(json.dumps({
        "wednesday": str(lost), "status": "lost", "study_year": 1,
        "unreadable": {str(lost): "release missing", str(lost + dt.timedelta(days=1)): "release missing"}}))
    rep = S.build(tmp_path, {str(days[0]): 5.333, str(days[1]): 4.667})
    assert rep["days"]["counted_wednesday"] == 3 and len(rep["days"]["lost"]) == 1
    assert len(rep["days"]["not_fetched"]) == 190 - 4
    cz = rep["coverage"][0]["regions"]["CZ"]
    assert cz["usable"] == 42 and cz["crossings"] == 3 and cz["usable_per_crossing"] == 14.0
    assert cz["details_share"] == 1.0
    # each aircraft has 20 usable points west of 5 E on each of 3 days: 60 >= 30 over 3 days, never 30 in one day
    sc = rep["screenable_aircraft"]
    assert sc["aircraft_screenable"] == 6 and sc["aircraft_screenable_strict"] == 0
    assert sc["per_region_year"]["CZ"]["1"]["screenable"] == 3
    assert cz["usable_share_screenable"] == 1.0
    assert rep["kp"]["days_kp_max_ge_5"] == 1
    assert rep["version_and_source"]["1"]["type_share"]["adsb_icao"] == 1.0
    json.dumps(rep)


def test_screen_never_opens_sealed():
    src = (HERE / "screen.py").read_text()
    assert "sealed" not in src.replace("(never sealed/)", "")


# --- download: retries with backoff and Range resume ----------------------------------------------------------------

def test_download_retries_and_resumes(tmp_path, monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    body = bytes(range(256)) * 400
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            rng = self.headers.get("Range")
            seen.append((rng, self.headers.get("User-Agent")))
            if len(seen) == 1:  # first attempt: a server error
                self.send_response(500)
                self.end_headers()
                return
            start = int(rng.split("=")[1].rstrip("-")) if rng else 0
            if len(seen) == 2:  # second attempt: cut off half way
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body[: len(body) // 2])
                return
            self.send_response(206 if start else 200)
            self.send_header("Content-Length", str(len(body) - start))
            self.end_headers()
            self.wfile.write(body[start:])

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(F, "BACKOFF_S", 0)
    try:
        dest = tmp_path / "x.tar.aa"
        F.download(f"http://127.0.0.1:{srv.server_port}/x", dest)
    finally:
        srv.shutdown()
    assert dest.read_bytes() == body
    assert seen[0][1] == "bsandova.com research" and seen[2][0] == f"bytes={len(body) // 2}-"


# --- review round: schema drift, time order, NIC on the primary points, transient failures, preflight ------------

def test_schema_drift_threshold():
    ok = {"trace_files": 1001, "tilde": 1, "aircraft": 995, "bad_files": 5}
    C.check_schema(ok, "2024-01-03")  # 5 of 1 000 is 0.5 %: not above it
    with pytest.raises(C.SchemaDrift, match="6 bad of 1000"):
        C.check_schema({**ok, "bad_files": 6}, "2024-01-03")
    with pytest.raises(C.SchemaDrift):
        C.check_schema({**ok, "aircraft": 0, "bad_files": 0}, "2024-01-03")
    assert issubclass(C.SchemaDrift, C.StopRun) and not issubclass(C.SchemaDrift, C.Unreadable)


def test_schema_drift_stops_resolve_day():
    def f(d):
        raise C.SchemaDrift("format changed")
    with pytest.raises(C.SchemaDrift):
        F.resolve_day(dt.date(2024, 1, 3), f)


def test_bad_files_counted_below_threshold(tmp_path, toy):
    fleet = {k: v for k, v in _fleet(40).items() if not k.startswith("~")}
    paths = _tar(tmp_path, fleet)
    n = C.count_day(paths, tmp_path / "d", "2024-01-03", toy, workers=1)
    assert n["bad_files"] == 0 and n["aircraft"] == 40 and n["unsorted_aircraft"] == 0


def test_shuffled_trace_counts_like_sorted(toy):
    lat, lon = IN_CZ
    pts = ([pt(0, OUT, det=False)] + [pt(t, nacp=5 if t % 40 == 0 else 9) for t in range(20, 700, 10)]
           + [pt(700, (lat, lon + _east(20)))] + [pt(t, flags=2 if t == 1500 else 0) for t in range(1500, 1800, 20)]
           + [pt(t, IN_PL) for t in range(1800, 2100, 20)])
    rng = np.random.default_rng(3)
    shuffled = [pts[i] for i in rng.permutation(len(pts))]
    a, b = run(pts, toy), run(shuffled, toy)
    assert not a.unsorted and b.unsorted
    assert (a.usable == b.usable).all() and (a.degraded == b.degraded).all()
    assert (a.crossings == b.crossings).all() and a.crossings[:, 5].any()
    assert (a.west_usable, a.west_degraded) == (b.west_usable, b.west_degraded)
    assert (a.stats == b.stats).all() and (a.mix == b.mix).all()


def test_unsorted_aircraft_counted_per_day(tmp_path, toy):
    fleet = {k: v for k, v in _fleet(4).items() if not k.startswith("~")}
    first = next(iter(fleet.values()))
    first["trace"] = first["trace"][::-1]
    n = C.count_day(_tar(tmp_path, fleet), tmp_path / "d", "2024-01-03", toy, workers=1)
    assert n["unsorted_aircraft"] == 1


def test_check1_nic_on_primary_points(toy):
    pts = lead_in(200) + [pt(200, nic=6), pt(210, nic=7), pt(220, nic=MISSING), pt(230, nic=None, nacp=3),
                          pt(240, nic=2, alt=10_000)]
    a = run(pts, toy)
    assert U(a) == 4  # the point below FL250 is not primary usable
    assert U(a, "c1_nic_same") == 2 and D(a, "c1_nic_same") == 1  # 220 and 230 carry no numeric NIC
    assert U(a, "c1_nic") == 2 and D(a, "c1_nic") == 1


def test_probe_persistent_non_404_stops_run(monkeypatch):
    import urllib.error

    monkeypatch.setattr(F, "BACKOFF_S", 0)
    for exc in (urllib.error.HTTPError("u", 503, "busy", {}, None), urllib.error.HTTPError("u", 429, "slow", {}, None),
                urllib.error.HTTPError("u", 403, "no", {}, None), TimeoutError("t")):
        def boom(*a, exc=exc, **k):
            raise exc
        monkeypatch.setattr(F, "_request", boom)
        with pytest.raises(F.NetworkDown):
            F.exists("https://example.invalid/x")
        with pytest.raises(F.NetworkDown):
            F.resolve_day(dt.date(2024, 1, 3), lambda d: F.fetch_and_count(d, Path("/nonexistent"), None, None))

    def missing(*a, **k):
        raise urllib.error.HTTPError("u", 404, "missing", {}, None)
    monkeypatch.setattr(F, "_request", missing)
    assert F.exists("https://example.invalid/x") is False
    m = F.resolve_day(dt.date(2024, 1, 3), lambda d: F.fetch_and_count(d, Path("/nonexistent"), None, None))
    assert m["status"] == "lost" and set(m["unreadable"].values()) == {"release missing"}


def test_download_retries_incomplete_read(tmp_path, monkeypatch):
    import http.client

    calls = []

    class Resp(io.BytesIO):
        status = 200
        headers = {"Content-Length": "4"}

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 1:
            raise http.client.IncompleteRead(b"ab", 2)
        return Resp(b"abcd")
    monkeypatch.setattr(F, "BACKOFF_S", 0)
    monkeypatch.setattr(F, "_request", flaky)
    F.download("https://example.invalid/x", tmp_path / "x")
    assert (tmp_path / "x").read_bytes() == b"abcd" and len(calls) == 2


def test_download_persistent_5xx_stops_run(tmp_path, monkeypatch):
    import urllib.error

    def busy(*a, **k):
        raise urllib.error.HTTPError("u", 502, "bad gateway", {}, None)
    monkeypatch.setattr(F, "BACKOFF_S", 0)
    monkeypatch.setattr(F, "_request", busy)
    with pytest.raises(F.NetworkDown):
        F.download("https://example.invalid/x", tmp_path / "x")


def test_postpass_resumes_after_stop(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DAYS", tmp_path)
    days = F.sample_days()
    for d in days:
        F.write_manifest(d, {"wednesday": str(d), "status": "counted", "study_year": F.study_year(d),
                             "date_used": str(d), "trace_files": 40 if d == days[7] else 100, "unreadable": {}})

    def down(d, day_dir):
        raise F.NetworkDown("gone")
    with pytest.raises(F.NetworkDown):
        F.postpass(down)
    m = F.read_manifest(days[7])
    assert m["status"] == "pending-thursday" and m["low_median"] == 100
    assert (tmp_path / f"{days[7]}.low-{days[7]}").exists()

    def ok(d, day_dir):
        day_dir.mkdir(parents=True, exist_ok=True)
        return {"date_used": str(d), "trace_files": 90}
    F.postpass(ok)
    m = F.read_manifest(days[7])
    assert m["status"] == "replaced" and m["date_used"] == str(days[7] + dt.timedelta(days=1))


def test_screen_counts_pending_status(tmp_path):
    d = F.sample_days()[0]
    (tmp_path / str(d)).mkdir()
    (tmp_path / str(d) / "manifest.json").write_text(json.dumps({
        "wednesday": str(d), "status": "pending-thursday", "study_year": 1, "unreadable": {}, "low_median": 1}))
    rep = S.build(tmp_path, {})
    assert rep["days"]["by_study_year"]["1"]["pending-thursday"] == 1


def test_fetch_kp_keeps_old_file_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DATA", tmp_path)
    monkeypatch.setattr(F, "KP_DIR", tmp_path / "kp")
    (tmp_path / "kp").mkdir()
    (tmp_path / "kp" / F.KP_NAME).write_text("old")

    def fail(url, dest):
        raise F.NetworkDown("gone")
    monkeypatch.setattr(F, "download", fail)
    with pytest.raises(F.NetworkDown):
        F.fetch_kp()
    assert (tmp_path / "kp" / F.KP_NAME).read_text() == "old"


def test_preflight_reports_structure_only(tmp_path):
    fleet = {k: v for k, v in _fleet(5).items()}
    odd = fleet["4b0001"]
    odd.pop("timestamp")
    odd["trace"] = odd["trace"][::-1]
    odd["trace"][0] = odd["trace"][0][:10]
    odd["trace"][1][8] = {"type": "adsb_icao", "nic": 3}  # no version, no nac_p key
    fleet["4b0002"]["trace"][4][9] = "adsr_icao"
    paths = _tar(tmp_path, fleet)
    raw = paths[0].read_bytes()
    rep = C.preflight(paths)
    assert rep["files"] == 6 and rep["tilde_files"] == 1 and rep["share_files_parsed"] == 1.0
    assert rep["share_parsed_with_timestamp_key"] == round(5 / 6, 6)
    assert rep["share_traces_time_monotone"] == round(5 / 6, 6)
    assert rep["type_strings"] == ["adsb_icao", "adsr_icao"]
    assert rep["points"] == 5 * 40 + 1
    assert rep["share_points_14plus_elements"] == round((rep["points"] - 1) / rep["points"], 6)
    assert rep["share_details_with_version_key"] < 1 and rep["share_details_with_nac_p_key"] < 1
    # nothing in the report is, or is derived from, a nac_p or nic value
    assert set(rep) == {"files", "tilde_files", "share_files_parsed", "share_parsed_with_timestamp_key",
                        "share_parsed_without_trace_list", "share_traces_time_monotone", "points",
                        "share_points_14plus_elements", "share_points_with_details",
                        "share_details_with_version_key", "share_details_with_nac_p_key", "type_strings"}
    assert paths[0].read_bytes() == raw


def test_preflight_code_never_reads_quality_values():
    import inspect
    src = inspect.getsource(C.structure) + inspect.getsource(C.preflight)
    assert '"nac_p" in p[8]' in src
    for banned in ('["nac_p"]', ".get(\"nac_p", '["nic"]', ".get(\"nic"):
        assert banned not in src
