"""Counter of the GNSS data step (design §2, §3): one day's trace_full files in, per-day counts out.

Reads the day's tar (one or more parts, concatenated) as a stream, never extracting it to disk, and writes to
tools/data/gnss/days/<sampled Wednesday>/:

    screening/  usable points, crossings, coverage and mix counts; opened by screen.py
    sealed/     degraded points and jump counts; not opened until the estimation code is tagged (§3)
    manifest.json

The two directories share their keys row for row, so the estimation joins them without recounting. Nothing here
prints or logs a degraded or jump count.
"""
from __future__ import annotations

import gzip
import io
import json
import re
import tarfile
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import orjson

    _loads = orjson.loads
except ImportError:  # the stdlib parser gives the same objects, only slower
    _loads = json.loads

import regions as R

# §2 constants
FL250 = 25_000
BUFFER_S = 120  # a usable point less than 120 s after the crossing's entry is in the buffer
SPLIT_S = 600  # a gap of more than 10 minutes between consecutive non-stale stored points ends a crossing
JUMP_DT_S = 60
JUMP_KT = 1_200
JUMP_NM = 2.0
NM_M = 1_852.0
NACP_MIN, NACP_MIN_C10, NIC_MIN = 8, 7, 7
CAP = 40
WEST_LON = 5.0
KALININGRAD = (54.71, 20.51)
BAND_EDGES_KM = np.array([300.0, 600.0, 900.0])
BANDS = ("0-300", "300-600", "600-900", "900+")
EARTH_KM = 6_371.0088

NR, NB = len(R.REGIONS), len(BANDS)
# Variant name -> design reference. Each has its own usable-point definition; the airframe screen (west of 5° E)
# always uses the primary one.
# c1_nic_same: the primary usable points that also carry a numeric NIC, degraded if NIC < 7, so that check 1 can be
# read on the same points as the primary share.
VARIANTS = ("primary", "c1_nic", "c2_anyalt", "c3_v12", "c8_nobuf", "c10_nacp7", "c1_nic_same", "c12_cap40")
VI = {v: i for i, v in enumerate(VARIANTS)}

TYPES = ("adsb_icao", "adsb_icao_nt", "adsr_icao", "tisb_icao", "adsc", "mlat", "other", "mode_s", "adsb_other",
         "adsr_other", "tisb_trackfile", "tisb_other", "mode_ac", "unknown")
TYPE_CODE = {t: i for i, t in enumerate(TYPES)}
T_OTHER = len(TYPES)  # anything not in TYPES, including a missing type
T_LABELS = TYPES + ("unlisted",)
NT = len(T_LABELS)
ADSB = TYPE_CODE["adsb_icao"]
# Version index: 0 no details object, 1 details without an integer version, 2 + v for v = 0..3, 5 for anything higher
V_LABELS = ("no_details", "no_version", "v0", "v1", "v2", "v3+")
NV = len(V_LABELS)
V2, V1 = 4, 3
MIX_REGIONS = ("CZ", "PL", "BALT", "CTRL", "DEW", "W5")
NMR = len(MIX_REGIONS)
MIX_SIZE = NMR * NT * NV * 2
STATS = ("points", "stale", "details", "adsb_fl250", "adsb_fl250_details", "adsb_fl250_v2_details", "nacp_nonnumeric")
TRACE_RE = re.compile(r"(?:^|/)traces/[^/]+/trace_full_([^/]+)\.json$")
_MISSING = object()


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(np.subtract(lon2, lon1)) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def band_of(lat, lon) -> np.ndarray:
    """0-300 km is band 0; a point at exactly 300 km is in band 1."""
    d = haversine_km(KALININGRAD[0], KALININGRAD[1], np.asarray(lat, float), np.asarray(lon, float))
    return np.searchsorted(BAND_EDGES_KM, d, side="right")


def _num(x) -> bool:
    return x.__class__ is int or x.__class__ is float


@dataclass
class Aircraft:
    icao: str
    usable: np.ndarray = field(default_factory=lambda: np.zeros((len(VARIANTS), NR * NB), np.int64))
    degraded: np.ndarray = field(default_factory=lambda: np.zeros((len(VARIANTS), NR * NB), np.int64))
    # one row per crossing: region, t_start, n_points, usable_buf, degraded_buf, jump, bandmask
    crossings: np.ndarray = field(default_factory=lambda: np.zeros((0, 7), np.float64))
    west_usable: int = 0
    west_degraded: int = 0
    stats: np.ndarray = field(default_factory=lambda: np.zeros((NR, len(STATS)), np.int64))
    mix: np.ndarray = field(default_factory=lambda: np.zeros(MIX_SIZE, np.int64))
    points: int = 0
    unsorted: bool = False


def count_aircraft(d: dict, idx: R.RegionIndex) -> Aircraft | None:
    icao = str(d.get("icao", "")).lower()
    if not icao or icao.startswith("~"):
        return None
    a = Aircraft(icao)
    tr = d.get("trace") or []
    n = len(tr)
    if n == 0:
        return a
    cols = list(zip(*tr))
    if len(cols) < 10:
        raise ValueError("trace points shorter than 10 elements")
    a.points = n
    t = float(d["timestamp"]) + np.asarray(cols[0], float)
    if (np.diff(t) < 0).any():  # crossings, buffer, cap, legs and jumps all assume time order
        a.unsorted = True
        order = np.argsort(t, kind="stable")
        tr = [tr[i] for i in order]
        cols = list(zip(*tr))
        t = t[order]
    lat = np.asarray(cols[1], float)
    lon = np.asarray(cols[2], float)
    flags = np.nan_to_num(np.asarray(cols[6], float)).astype(np.int64)
    finite = np.isfinite(lat) & np.isfinite(lon)
    stale = (flags & 1) != 0
    leg = np.cumsum((flags & 2) != 0)  # leg markers seen up to and including each stored point

    prim = np.full(n, -1, np.int16)
    chk6 = np.full(n, -1, np.int16)
    fi = np.flatnonzero(finite)
    if fi.size:
        prim[fi], chk6[fi] = idx.regions(lon[fi], lat[fi])

    tcode = np.fromiter((TYPE_CODE.get(x, T_OTHER) for x in cols[9]), np.int8, n)
    alt = np.fromiter((x if _num(x) else np.nan for x in cols[3]), float, n)
    ver = np.zeros(n, np.int8)
    nacp = np.full(n, np.nan)
    nic = np.full(n, np.nan)
    nacp_bad = np.zeros(n, bool)
    for i, dd in enumerate(cols[8]):
        if dd.__class__ is not dict:
            continue
        v = dd.get("version")
        ver[i] = (2 + v if v <= 3 else 5) if v.__class__ is int and v >= 0 else 1
        x = dd.get("nac_p", _MISSING)
        if x is not _MISSING:
            if _num(x):
                nacp[i] = x
            else:
                nacp_bad[i] = True
        y = dd.get("nic")
        if y is not None and _num(y):
            nic[i] = y

    # Coverage statistics per region (both layers), over all stored points with a position.
    fl250_all = alt >= FL250
    adsb_all = tcode == ADSB
    has_det = ver > 0
    stat_cols = (finite & ~stale, finite & stale, finite & ~stale & has_det, finite & ~stale & adsb_all & fl250_all,
                 finite & ~stale & adsb_all & fl250_all & has_det,
                 finite & ~stale & adsb_all & fl250_all & (ver == V2), finite & ~stale & nacp_bad)
    for layer in (prim, chk6):
        inl = layer >= 0
        if inl.any():
            for j, m in enumerate(stat_cols):
                a.stats[:, j] += np.bincount(layer[m & inl], minlength=NR)

    S = np.flatnonzero(finite & ~stale)
    if S.size == 0:
        return a
    ts, la, lo = t[S], lat[S], lon[S]
    P, C, tc, al, vr, npc, nc_ = prim[S], chk6[S], tcode[S], alt[S], ver[S], nacp[S], nic[S]
    legS = leg[S]
    adsb = tc == ADSB
    fl = al >= FL250
    v2 = vr == V2
    v12 = (vr == V1) | (vr == V2)
    has_nacp = ~np.isnan(npc)
    has_nic = ~np.isnan(nc_)
    with np.errstate(invalid="ignore"):
        deg8 = npc < NACP_MIN
        deg7 = npc < NACP_MIN_C10
        degnic = nc_ < NIC_MIN
    u_prim = adsb & v2 & has_nacp & fl

    # Airframe screen: primary usable points west of 5° E, anywhere in the trace, no region and no buffer.
    w = u_prim & (lo < WEST_LON)
    a.west_usable = int(w.sum())
    a.west_degraded = int((w & deg8).sum())

    mr = np.where(P >= 0, P, np.where(C == R.REGION_ID["DEW"], 4, np.where(lo < WEST_LON, 5, -1)))
    mm = mr >= 0
    if mm.any():
        key = ((mr[mm].astype(np.int64) * NT + tc[mm]) * NV + vr[mm]) * 2 + fl[mm]
        a.mix += np.bincount(key, minlength=MIX_SIZE)

    if not ((P >= 0).any() or (C >= 0).any()):
        return a

    band = band_of(la, lo)
    variants = (  # usable mask, degraded mask, entry buffer applied
        (u_prim, deg8, True),
        (adsb & v2 & has_nic & fl, degnic, True),
        (adsb & v2 & has_nacp, deg8, True),
        (adsb & v12 & has_nacp & fl, deg8, True),
        (u_prim, deg8, False),
        (u_prim, deg7, True),
        (u_prim & has_nic, degnic, True),
    )
    rows = []
    for L in (P, C):
        inr = L >= 0
        if not inr.any():
            continue
        prev = np.r_[-2, L[:-1]]
        gap = np.r_[np.inf, np.diff(ts)]
        start = inr & ((L != prev) | (gap > SPLIT_S))
        cid = np.cumsum(start) - 1
        cid[~inr] = -1
        st = np.flatnonzero(start)
        inbuf = np.zeros(S.size, bool)
        inbuf[inr] = (ts[inr] - ts[st][cid[inr]]) < BUFFER_S
        key = L.astype(np.int64) * NB + band
        for vi, (um, dm, buffered) in enumerate(variants):
            m = um & inr & ~inbuf if buffered else um & inr
            a.usable[vi] += np.bincount(key[m], minlength=NR * NB)
            a.degraded[vi] += np.bincount(key[m & dm], minlength=NR * NB)
        after = u_prim & inr & ~inbuf
        cap = np.zeros(S.size, bool)
        for r in np.unique(L[after]):
            cap[np.flatnonzero(after & (L == r))[:CAP]] = True
        a.usable[VI["c12_cap40"]] += np.bincount(key[cap], minlength=NR * NB)
        a.degraded[VI["c12_cap40"]] += np.bincount(key[cap & deg8], minlength=NR * NB)

        ncx = st.size
        npts = np.bincount(cid[inr], minlength=ncx)
        ub = np.bincount(cid[after], minlength=ncx)
        db = np.bincount(cid[after & deg8], minlength=ncx)
        bmask = np.zeros(ncx, np.int64)
        for b in range(NB):
            bmask |= (np.bincount(cid[inr & (band == b)], minlength=ncx) > 0).astype(np.int64) << b
        jump = np.zeros(ncx, bool)
        if S.size > 1:
            dt = np.diff(ts)
            ok = (inr[1:] & (L[1:] == L[:-1]) & adsb[1:] & adsb[:-1] & (dt >= 0) & (dt <= JUMP_DT_S)
                  & (legS[1:] == legS[:-1]))
            k = np.flatnonzero(ok) + 1
            if k.size:
                dist_nm = haversine_km(la[k - 1], lo[k - 1], la[k], lo[k]) * 1000 / NM_M
                hit = (dist_nm >= JUMP_NM) & (dist_nm * 3600 > JUMP_KT * dt[k - 1])
                jump[np.unique(cid[k[hit]])] = True
        rows.append(np.column_stack([L[st], ts[st], npts, ub, db, jump, bmask]).astype(np.float64))
    if rows:
        a.crossings = np.vstack(rows)
    return a


class DayAcc:
    """Rows and sums of one day, mergeable across the two processes."""

    def __init__(self):
        self.icao: list[str] = []
        self.usable: list[np.ndarray] = []
        self.degraded: list[np.ndarray] = []
        self.x_icao: list[str] = []
        self.crossings: list[np.ndarray] = []
        self.west: list[tuple[str, int, int]] = []
        self.stats = np.zeros((NR, len(STATS)), np.int64)
        self.mix = np.zeros(MIX_SIZE, np.int64)
        self.n = {"trace_files": 0, "tilde": 0, "aircraft": 0, "bad_files": 0, "points": 0, "unsorted_aircraft": 0}

    def add(self, a: Aircraft) -> None:
        self.n["aircraft"] += 1
        self.n["points"] += a.points
        self.n["unsorted_aircraft"] += a.unsorted
        if a.usable.any() or a.degraded.any():
            self.icao.append(a.icao)
            self.usable.append(a.usable)
            self.degraded.append(a.degraded)
        if len(a.crossings):
            self.x_icao.extend([a.icao] * len(a.crossings))
            self.crossings.append(a.crossings)
        if a.west_usable:
            self.west.append((a.icao, a.west_usable, a.west_degraded))
        self.stats += a.stats
        self.mix += a.mix

    def merge(self, o: DayAcc) -> None:
        self.icao += o.icao
        self.usable += o.usable
        self.degraded += o.degraded
        self.x_icao += o.x_icao
        self.crossings += o.crossings
        self.west += o.west
        self.stats += o.stats
        self.mix += o.mix
        for k, v in o.n.items():
            self.n[k] += v

    def feed(self, name: str, raw: bytes, idx: R.RegionIndex) -> None:
        self.n["trace_files"] += 1
        if TRACE_RE.search(name).group(1).startswith("~"):
            self.n["tilde"] += 1
            return
        try:
            data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
            a = count_aircraft(_loads(data), idx)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, EOFError, OSError,
                zlib.error):
            self.n["bad_files"] += 1
            return
        if a is not None:
            self.add(a)

    def frames(self, date: str) -> dict[str, object]:
        import pandas as pd

        out = {}
        vi, ki, ii, u, dg = [], [], [], [], []
        for j, (U, D) in enumerate(zip(self.usable, self.degraded)):
            v, k = np.nonzero(U)
            vi.append(v), ki.append(k), ii.append(np.full(v.size, j)), u.append(U[v, k]), dg.append(D[v, k])
        cat = (lambda xs, dt: np.concatenate(xs).astype(dt) if xs else np.zeros(0, dt))
        vi, ki, ii, u, dg = cat(vi, np.int64), cat(ki, np.int64), cat(ii, np.int64), cat(u, np.int64), cat(dg, np.int64)
        icao = np.array(self.icao, object)
        keys = pd.DataFrame({
            "date": date,
            "icao": icao[ii] if ii.size else np.zeros(0, object),
            "variant": np.array(VARIANTS, object)[vi],
            "region": np.array(R.REGIONS, object)[ki // NB],
            "band": np.array(BANDS, object)[ki % NB],
        })
        out["screening/points"] = keys.assign(usable=u)
        out["sealed/points"] = keys.assign(degraded=dg)

        X = np.vstack(self.crossings) if self.crossings else np.zeros((0, 7))
        xi = np.array(self.x_icao, object)
        reg = np.array(R.REGIONS, object)[X[:, 0].astype(int)]
        seq = pd.Series(np.arange(len(X))).groupby([xi, reg]).cumcount().to_numpy() if len(X) else np.zeros(0, int)
        xk = pd.DataFrame({"date": date, "icao": xi, "region": reg, "crossing": seq})
        xs = xk.assign(t_start=X[:, 1], n_points=X[:, 2].astype(int), usable_buf=X[:, 3].astype(int),
                       bandmask=X[:, 6].astype(int))
        xd = xk.assign(degraded_buf=X[:, 4].astype(int), jump=X[:, 5].astype(bool))
        keep = xs["usable_buf"].to_numpy() >= 1
        out["screening/crossings"] = xs[keep].reset_index(drop=True)
        out["sealed/crossings"] = xd[keep].reset_index(drop=True)

        rows_s, rows_d = [], []
        bm = X[:, 6].astype(int)
        has_u = X[:, 3] >= 1
        jmp = X[:, 5].astype(bool)
        for label, sel in [("all", np.ones(len(X), bool))] + [(BANDS[b], (bm >> b) & 1 == 1) for b in range(NB)]:
            if not sel.any():
                continue
            g = pd.DataFrame({"icao": xi[sel], "region": reg[sel], "c": 1, "cu": has_u[sel].astype(int),
                              "j": jmp[sel].astype(int), "ju": (jmp & has_u)[sel].astype(int)})
            g = g.groupby(["region", "icao"], as_index=False).sum()
            g.insert(0, "band", label)
            rows_s.append(g[["band", "region", "icao", "c", "cu"]].rename(
                columns={"c": "crossings", "cu": "crossings_usable"}))
            rows_d.append(g[["band", "region", "icao", "j", "ju"]].rename(
                columns={"j": "jump_crossings", "ju": "jump_crossings_usable"}))
        cols_s = ["band", "region", "icao", "crossings", "crossings_usable"]
        cols_d = ["band", "region", "icao", "jump_crossings", "jump_crossings_usable"]
        out["screening/crossings_agg"] = (pd.concat(rows_s) if rows_s else pd.DataFrame(columns=cols_s)).assign(date=date)
        out["sealed/crossings_agg"] = (pd.concat(rows_d) if rows_d else pd.DataFrame(columns=cols_d)).assign(date=date)

        wi = [w[0] for w in self.west]
        out["screening/west"] = pd.DataFrame({"date": date, "icao": wi, "usable": [w[1] for w in self.west]})
        out["sealed/west"] = pd.DataFrame({"date": date, "icao": wi, "degraded": [w[2] for w in self.west]})

        st = pd.DataFrame(self.stats, columns=list(STATS))
        st.insert(0, "region", list(R.REGIONS))
        out["screening/region_day"] = st.assign(date=date)

        nz = np.flatnonzero(self.mix)
        f, rest = nz % 2, nz // 2
        v, rest = rest % NV, rest // NV
        tt, m = rest % NT, rest // NT
        out["screening/mix"] = pd.DataFrame({
            "date": date, "region": np.array(MIX_REGIONS, object)[m], "type": np.array(T_LABELS, object)[tt],
            "version": np.array(V_LABELS, object)[v], "fl250": f.astype(bool), "points": self.mix[nz]})
        return out


class _Concat(io.RawIOBase):
    """The parts of a split tar read back to back as one stream."""

    def __init__(self, paths: list[Path]):
        self.paths, self.i, self.f = list(paths), 0, None

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        while self.i < len(self.paths):
            if self.f is None:
                self.f = open(self.paths[self.i], "rb")
            n = self.f.readinto(b)
            if n:
                return n
            self.f.close()
            self.f, self.i = None, self.i + 1
        return 0

    def close(self) -> None:
        if self.f is not None:
            self.f.close()
        super().close()


class Unreadable(Exception):
    """The day is unreadable by §2 and is replaced by its Thursday."""


class StopRun(Exception):
    """Not a property of the day: the run stops so that no day is lost or miscounted for it."""


class SchemaDrift(StopRun):
    pass


BAD_SHARE_MAX = 0.005


def check_schema(n: dict, date: str) -> None:
    """Too many files that fail to parse, or no aircraft, means the format changed, not that the day is bad."""
    ok_files = n["trace_files"] - n["tilde"]
    if n["aircraft"] == 0 or (ok_files and n["bad_files"] / ok_files > BAD_SHARE_MAX):
        raise SchemaDrift(f"{date}: {n['bad_files']} bad of {ok_files} non-~ trace files, {n['aircraft']} aircraft")


def iter_traces(paths: list[Path]):
    try:
        with _Concat(paths) as raw, tarfile.open(fileobj=io.BufferedReader(raw, 1 << 20), mode="r|") as tf:
            for m in tf:
                if m.isfile() and TRACE_RE.search(m.name):
                    yield m.name, tf.extractfile(m).read()
    except (tarfile.TarError, EOFError, OSError, zlib.error) as e:
        raise Unreadable(f"tar stream: {type(e).__name__}: {e}") from e


_IDX: R.RegionIndex | None = None


def _init(index_path: str) -> None:
    global _IDX
    _IDX = R.RegionIndex.load(Path(index_path))


def _work(batch: list[tuple[str, bytes]]) -> DayAcc:
    acc = DayAcc()
    for name, raw in batch:
        acc.feed(name, raw, _IDX)
    return acc


def count_day(paths: list[Path], out_dir: Path, date: str, idx: R.RegionIndex, index_path: Path | None = None,
              workers: int = 2, batch: int = 256) -> dict:
    """Counts one day into out_dir; with workers=2 the reading process counts every other batch itself."""
    t0 = time.time()
    acc = DayAcc()
    pool = ProcessPoolExecutor(1, initializer=_init, initargs=(str(index_path),)) if workers > 1 else None
    pending = []
    try:
        buf, turn = [], 0
        for name, raw in iter_traces(paths):
            buf.append((name, raw))
            if len(buf) < batch:
                continue
            if pool is not None and turn % 2 == 0 and len(pending) < 2:
                pending.append(pool.submit(_work, buf))
            else:
                for nm, rw in buf:
                    acc.feed(nm, rw, idx)
            turn += 1
            buf = []
            while pending and pending[0].done():
                acc.merge(pending.pop(0).result())
        for nm, rw in buf:
            acc.feed(nm, rw, idx)
        for p in pending:
            acc.merge(p.result())
    finally:
        if pool is not None:
            pool.shutdown(cancel_futures=True)
    if acc.n["trace_files"] == 0:
        raise Unreadable("no trace_full files in the archive")
    check_schema(acc.n, date)
    write_day(acc, out_dir, date)
    return {**acc.n, "count_seconds": round(time.time() - t0, 1)}


def write_day(acc: DayAcc, out_dir: Path, date: str) -> None:
    for sub in ("screening", "sealed"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    for name, df in acc.frames(date).items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)


def structure(d: dict, acc: dict) -> None:
    """Structure of one parsed trace for the preflight; looks at key presence and types only, never at a value of
    nac_p, nic or any other quality field."""
    acc["timestamp_key"] += "timestamp" in d
    tr = d.get("trace")
    if not isinstance(tr, list):
        acc["no_trace_list"] += 1
        return
    prev, mono = None, True
    for p in tr:
        acc["points"] += 1
        if not isinstance(p, list):
            continue
        acc["points_14plus"] += len(p) >= 14
        if len(p) > 9:
            acc["types"].add(p[9] if isinstance(p[9], str) else repr(type(p[9]).__name__))
        if len(p) > 8 and isinstance(p[8], dict):
            acc["details"] += 1
            acc["details_version_key"] += "version" in p[8]
            acc["details_nac_p_key"] += "nac_p" in p[8]
        if p and _num(p[0]):
            mono &= prev is None or p[0] >= prev
            prev = p[0]
    acc["traces_monotone"] += mono


def preflight(paths: list[Path]) -> dict:
    acc = {"files": 0, "tilde": 0, "parsed": 0, "no_trace_list": 0, "timestamp_key": 0, "traces_monotone": 0,
           "points": 0, "points_14plus": 0, "details": 0, "details_version_key": 0, "details_nac_p_key": 0,
           "types": set()}
    for name, raw in iter_traces(paths):
        acc["files"] += 1
        if TRACE_RE.search(name).group(1).startswith("~"):
            acc["tilde"] += 1
        try:
            d = _loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
        except (ValueError, EOFError, OSError, zlib.error):
            continue
        if not isinstance(d, dict):
            continue
        acc["parsed"] += 1
        structure(d, acc)
    f, p, det = acc["files"], acc["points"], acc["details"]
    return {
        "files": f, "tilde_files": acc["tilde"],
        "share_files_parsed": share_or_none(acc["parsed"], f),
        "share_parsed_with_timestamp_key": share_or_none(acc["timestamp_key"], acc["parsed"]),
        "share_parsed_without_trace_list": share_or_none(acc["no_trace_list"], acc["parsed"]),
        "share_traces_time_monotone": share_or_none(acc["traces_monotone"], acc["parsed"] - acc["no_trace_list"]),
        "points": p,
        "share_points_14plus_elements": share_or_none(acc["points_14plus"], p),
        "share_points_with_details": share_or_none(det, p),
        "share_details_with_version_key": share_or_none(acc["details_version_key"], det),
        "share_details_with_nac_p_key": share_or_none(acc["details_nac_p_key"], det),
        "type_strings": sorted(acc["types"]),
    }


def share_or_none(a, b):
    return round(a / b, 6) if b else None
