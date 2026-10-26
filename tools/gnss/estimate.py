"""Estimation of the GNSS design (§4-§7): shares of degraded position reports, the two-way bootstrap, labels, Q3, Q4 and
the checks. Everything below `load_panel` works on a Panel and is tested on made-up days with known effects.

The degraded and jump counts sit in days/*/sealed/. Only `merged_day` opens them, and `main` calls it only with
`--unblind`, on a tree whose HEAD carries the tag `gnss-code` (§3: the counts stay unread until that tag).
Writes docs/research/gnss-results.json and appends every bootstrap draw to tools/data/gnss/bootstrap-draws-<time>.jsonl.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with shapely --with numpy \
        --with pandas --with pyarrow python -I tools/gnss/estimate.py --unblind
    ... python -I tools/gnss/estimate.py --unblind --from-log tools/data/gnss/bootstrap-draws-<time>.jsonl  # after a crash
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script's own directory off the path

import count as C  # noqa: E402
import fetch as F  # noqa: E402
import regions as R  # noqa: E402

ROOT = R.ROOT
OUT = ROOT / "docs/research/gnss-results.json"
DRAWS_LOG = R.DATA / "bootstrap-draws.jsonl"
SEED, DRAWS, BLOCK = 20261015, 2000, 4
MARGIN = 0.01
EPS = 1e-12  # a share written as 2 % must not fail the test because 0.03 - 0.01 is 0.01999...
AIRFRAME_POINTS, AIRFRAME_DAYS, AIRFRAME_SHARE = 30, 2, 0.5
DAY_MIN_POINTS, DAY_MIN_SHARE, DAY_MIN_GAP = 300, 0.02, 0.02
TOP_AIRFRAMES = 10
KP_STORM = 5.0
CROSSING_MIN_POINTS, CROSSING_MIN_DEGRADED = 3, 2
Q3_FROM, Q3_TO = (3, 1), (10, 14)
MAX_REDRAW_FACTOR = 10
FREEZE_TAG = "gnss-code"

NREG, RID = len(R.REGIONS), R.REGION_ID
STUDY = ("CZ", "PL", "BALT")
NYEAR, NBAND = 4, len(C.BANDS)
BAND_ALL = NBAND
HIGHER, NO_EXCESS = "higher degraded share than control", "no excess larger than one point"
INCONCLUSIVE, NOT_COMPUTED = "inconclusive", "not computed"
INCREASE, NO_INCREASE = "increase", "no increase larger than one point"


@dataclass
class Rows:
    day: np.ndarray
    ac: np.ndarray
    reg: np.ndarray
    band: np.ndarray
    u: np.ndarray
    g: np.ndarray
    ykey: np.ndarray | None = None  # study year x region
    bkey: np.ndarray | None = None  # band x region
    akey: np.ndarray | None = None  # aircraft x region
    dkey: np.ndarray | None = None  # day x region

    def take(self, m: np.ndarray) -> Rows:
        return Rows(**{f.name: (getattr(self, f.name)[m] if getattr(self, f.name) is not None else None)
                       for f in dataclasses.fields(self)})

    def keyed(self, year: np.ndarray) -> Rows:
        d, r = self.day.astype(np.int64), self.reg.astype(np.int64)
        self.ykey = year[self.day].astype(np.int64) * NREG + r
        self.bkey = self.band.astype(np.int64) * NREG + r
        self.akey = self.ac.astype(np.int64) * NREG + r
        self.dkey = d * NREG + r
        return self


def empty_rows() -> Rows:
    z = np.zeros(0, np.int32)
    return Rows(z, z, z.astype(np.int8), z.astype(np.int8), z.astype(np.float64), z.astype(np.float64))


def cat_rows(parts: list[Rows]) -> Rows:
    if not parts:
        return empty_rows()
    return Rows(*(np.concatenate([getattr(p, f) for p in parts]) for f in ("day", "ac", "reg", "band", "u", "g")))


class Panel:
    """Per-day counts of the days used, joined to one table per kind and keyed for fast weighted sums.

    `points[variant]`: usable and degraded points per day, aircraft, region (and band, primary only).
    `west`: usable and degraded points west of 5° E per day and aircraft. `cross`: crossings with at least 3 usable
    points after the buffer, g = 1 if at least 2 of them are degraded. `cagg_all`, `cagg_band`: crossings with a usable
    point (u) and those with a jump (g), per day, aircraft, region (and band).
    """

    def __init__(self, wed, used, kp, icao, points, west, cross, cagg_all, cagg_band, airframes=None):
        self.wed, self.used, self.icao = list(wed), list(used), list(icao)
        self.n_ac, self.n_days = len(self.icao), len(self.wed)
        self.year = np.array([F.study_year(w) - 1 for w in self.wed], np.int64)
        self.kp = np.array([np.nan if kp.get(u) is None else float(kp[u]) for u in self.used])
        self.storm = self.kp >= KP_STORM
        self.calm = np.isfinite(self.kp) & ~self.storm
        # only the primary rows are summed by year, band, aircraft and day, so only they carry keys
        self.points = {k: (v.keyed(self.year) if k == "primary" else v) for k, v in points.items()}
        self.west, self.cross = west.keyed(self.year), cross.keyed(self.year)
        self.cagg_all, self.cagg_band = cagg_all.keyed(self.year), cagg_band.keyed(self.year)
        self.keep, self.screen, self.persistent, self.keep_strict = airframes or self.airframes()
        self.base_w, self.strict_w = self.keep.astype(float), self.keep_strict.astype(float)
        self.pool = self.pool_of(self)
        self.periods = [np.flatnonzero(self.year == y) for y in range(NYEAR)]

    def airframes(self):
        """§2 persistent airframes, over the whole sample: screenable (change log 15 Oct, choice 10) and at least half
        of the points west of 5° E degraded."""
        w = self.west
        u = np.bincount(w.ac, w.u, self.n_ac)
        g = np.bincount(w.ac, w.g, self.n_ac)
        days = np.bincount(w.ac, (w.u > 0).astype(float), self.n_ac)
        screen = (u >= AIRFRAME_POINTS) & (days >= AIRFRAME_DAYS)
        persistent = screen & (g >= AIRFRAME_SHARE * u)
        strict_screen = np.bincount(w.ac, (w.u >= AIRFRAME_POINTS).astype(float), self.n_ac) >= AIRFRAME_DAYS
        return ~persistent, screen, persistent, ~(strict_screen & (g >= AIRFRAME_SHARE * u))

    @staticmethod
    def pool_of(P) -> np.ndarray:
        """Aircraft that can carry weight in a draw: present, and kept under the primary or the strict airframe rule
        (the strict rule is check 13 and needs its own aircraft in the draw)."""
        present = np.zeros(P.n_ac, bool)
        for r in (*P.points.values(), P.cross, P.cagg_all, P.cagg_band):
            present[r.ac] = True
        return np.flatnonzero(present & (P.keep | P.keep_strict))
    def restrict(self, day_mask: np.ndarray) -> Panel:
        """The same panel on some days only; the airframe screen stays the one of the whole sample."""
        p = copy.copy(self)
        m = lambda r: r.take(day_mask[r.day])  # noqa: E731
        p.points = {k: m(v) for k, v in self.points.items()}
        p.west, p.cross, p.cagg_all, p.cagg_band = m(self.west), m(self.cross), m(self.cagg_all), m(self.cagg_band)
        p.pool = self.pool_of(p)
        p.periods = [np.flatnonzero(day_mask)]
        return p


# ---------------------------------------------------------------- weighted sums

def sums(r: Rows, wd: np.ndarray, wa: np.ndarray, key: np.ndarray, size: int):
    w = wd[r.day] * wa[r.ac]
    return np.bincount(key, w * r.u, size), np.bincount(key, w * r.g, size)


def ratio(g, u):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.asarray(u) > 0, np.asarray(g, float) / np.where(np.asarray(u) > 0, u, 1), np.nan)


def excess(D: np.ndarray, ctrl: str = "CTRL") -> dict:
    return {f"E.{x}": float(D[RID[x]] - D[RID[ctrl]]) for x in STUDY}


# ---------------------------------------------------------------- estimators: fn(panel, day weights, aircraft weights)

def primary(P: Panel, wd, wa) -> dict:
    r = P.points["primary"]
    U, G = sums(r, wd, wa, r.ykey, NYEAR * NREG)
    U, G = U.reshape(NYEAR, NREG), G.reshape(NYEAR, NREG)
    out = {}
    for tag, u, g in [("", U.sum(0), G.sum(0))] + [(f".y{y + 1}", U[y], G[y]) for y in range(NYEAR)]:
        D = ratio(g, u)
        for x in R.PRIMARY:
            out[f"D.{x}{tag}"] = float(D[RID[x]])
        out.update({k + tag: v for k, v in excess(D).items()})
    Ub, Gb = sums(r, wd, wa, r.bkey, NBAND * NREG)
    Ub, Gb = Ub.reshape(NBAND, NREG), Gb.reshape(NBAND, NREG)
    ctrl = out["D.CTRL"]
    n = len(R.PRIMARY)
    for b, name in enumerate(C.BANDS):
        for x in R.PRIMARY:
            out[f"D.{x}.band.{name}"] = float(ratio(Gb[b, RID[x]], Ub[b, RID[x]]))
        out[f"E.band.{name}"] = float(ratio(Gb[b, :n].sum(), Ub[b, :n].sum()) - ctrl)
    return out


def variant(name: str):
    def fn(P, wd, wa):
        r = P.points[name]
        U, G = sums(r, wd, wa, r.reg, NREG)
        return excess(ratio(G, U))
    return fn


def control(name: str):
    def fn(P, wd, wa):
        r = P.points["primary"]
        U, G = sums(r, wd, wa, r.reg, NREG)
        return excess(ratio(G, U), name)
    return fn


def screenable_only(P, wd, wa):
    r = P.points["primary"]
    U, G = sums(r, wd, wa * P.screen, r.reg, NREG)
    return excess(ratio(G, U))


def paired(P, wd, wa):
    """Check 5: per screenable aircraft, share in the region minus its share west of 5° E, averaged over aircraft."""
    a = wa * P.screen
    r, w = P.points["primary"], P.west
    U = np.bincount(r.akey, wd[r.day] * r.u, P.n_ac * NREG).reshape(P.n_ac, NREG)
    G = np.bincount(r.akey, wd[r.day] * r.g, P.n_ac * NREG).reshape(P.n_ac, NREG)
    Uw = np.bincount(w.ac, wd[w.day] * w.u, P.n_ac)
    Gw = np.bincount(w.ac, wd[w.day] * w.g, P.n_ac)
    out = {}
    for x in (*STUDY, "CTRL"):
        i = RID[x]
        ok = (U[:, i] > 0) & (Uw > 0) & (a > 0)
        diff = G[ok, i] / U[ok, i] - Gw[ok] / Uw[ok]
        out[x] = float((a[ok] * diff).sum() / a[ok].sum()) if ok.any() else np.nan
    return {f"E.{x}": out[x] - out["CTRL"] for x in STUDY}


def equal_day(P, wd, wa):
    """Check 7: day shares averaged with equal weight per sampled day (bootstrap day counts weight the average)."""
    r = P.points["primary"]
    U, G = sums(r, np.ones(P.n_days), wa, r.dkey, P.n_days * NREG)
    D = ratio(G, U).reshape(P.n_days, NREG)
    out = {}
    for x in STUDY:
        diff = D[:, RID[x]] - D[:, RID["CTRL"]]
        ok = np.isfinite(diff) & (wd > 0)
        out[f"E.{x}"] = float((wd[ok] * diff[ok]).sum() / wd[ok].sum()) if ok.any() else np.nan
    return out


def on_days(mask_name: str, negate: bool = False):
    def fn(P, wd, wa):
        m = getattr(P, mask_name)
        m = ~m if negate else m
        r = P.points["primary"]
        U, G = sums(r, wd * m, wa, r.reg, NREG)
        return excess(ratio(G, U))
    return fn


def crossings(P, wd, wa):
    r = P.cross
    U, G = sums(r, wd, wa, r.reg, NREG)
    return excess(ratio(G, U))


def jumps(P, wd, wa):
    """Q4: crossings with a jump over crossings with a usable point after the buffer, per region, year and band."""
    r = P.cagg_all
    U, G = sums(r, wd, wa, r.ykey, NYEAR * NREG)
    U, G = U.reshape(NYEAR, NREG), G.reshape(NYEAR, NREG)
    out = {}
    for tag, u, g in [("", U.sum(0), G.sum(0))] + [(f".y{y + 1}", U[y], G[y]) for y in range(NYEAR)]:
        S = ratio(g, u)
        for x in R.PRIMARY:
            out[f"S.{x}{tag}"] = float(S[RID[x]])
        for x in STUDY:
            out[f"S.diff.{x}{tag}"] = float(S[RID[x]] - S[RID["CTRL"]])
    rb = P.cagg_band
    Ub, Gb = sums(rb, wd, wa, rb.band, NBAND)
    for b, name in enumerate(C.BANDS):
        out[f"S.band.{name}"] = float(ratio(Gb[b], Ub[b]))
    return out


CHECKS = {
    "c1_nic": variant("c1_nic"), "c1_nic_same": variant("c1_nic_same"), "c2_anyalt": variant("c2_anyalt"),
    "c3_v12": variant("c3_v12"), "c4_screenable": screenable_only, "c5_paired": paired,
    "c6_austria": control("AT"), "c6_switzerland": control("CH"), "c6_germany_w10e": control("DEW"),
    "c7_equal_days": equal_day, "c8_nobuf": variant("c8_nobuf"), "c9_without_storm_days": on_days("storm", True),
    "c9_kp_below5": on_days("calm"), "c9_kp_5_or_more": on_days("storm"), "c10_nacp7": variant("c10_nacp7"),
    "c11_crossings": crossings, "c12_cap40": variant("c12_cap40"),
    "c13_strict_airframes": variant("primary"),  # the airframe set of the stricter reading, see weights_for
}
STRICT_ESTIMATORS = ("c13_strict_airframes",)
GATE = variant("primary")
ESTIMATORS = {"primary": primary, "jumps": jumps, **CHECKS}
Q3_ESTIMATORS = ("primary", *CHECKS)


# ---------------------------------------------------------------- resampling

def block_weights(rng, periods: list[np.ndarray], n_days: int) -> np.ndarray:
    """Moving blocks of 4 consecutive sampled days, circular within each period, as many blocks as cover the period,
    cut to its length; counts per day."""
    wd = np.zeros(n_days)
    for idx in periods:
        n = idx.size
        if n == 0:
            continue
        starts = rng.integers(0, n, -(-n // BLOCK))
        pick = ((starts[:, None] + np.arange(BLOCK)) % n).ravel()[:n]
        wd[idx] += np.bincount(pick, minlength=n)
    return wd


def aircraft_weights(rng, P: Panel, pool: np.ndarray | None = None) -> np.ndarray:
    pool = P.pool if pool is None else pool
    if pool.size == 0:
        return np.zeros(P.n_ac)
    return np.bincount(pool[rng.integers(0, pool.size, pool.size)], minlength=P.n_ac).astype(float)


ERRORS: dict[str, str] = {}  # first exception class seen per estimator, reported once


def attempt(fn, *args, name: str = "") -> dict | None:
    """A non-gate estimate that fails in a draw (any error: singular, empty, a missing key) is left missing; the run
    goes on. Only the gate and programming interrupts may stop a draw."""
    try:
        return {k: (float(v) if np.isfinite(v) else np.nan) for k, v in fn(*args).items()}
    except Exception as e:  # noqa: BLE001
        ERRORS.setdefault(name or getattr(fn, "__name__", "?"), type(e).__name__)
        return None


def flat(prefix: str, got: dict | None, template: dict, source: str | None = None) -> dict:
    keys = template[source or prefix]
    return {f"{prefix}.{k}": (got[k] if got is not None and k in got else np.nan) for k in keys}


def weights_for(P: Panel, name: str) -> np.ndarray:
    return P.strict_w if name in STRICT_ESTIMATORS else P.base_w


def point_estimates(P: Panel) -> tuple[dict, dict, dict]:
    wd = np.ones(P.n_days)
    out, template, failed = {}, {}, {}
    for name, fn in ESTIMATORS.items():
        got = attempt(fn, P, wd, weights_for(P, name), name=name)
        if got is None:
            failed[name], template[name] = True, []
            continue
        template[name] = list(got)
        out.update({f"{name}.{k}": v for k, v in got.items()})
    return out, template, failed


def gate_ok(P: Panel, wd, wa) -> bool:
    """The gate is the pooled E_CZ alone, computed on its own: undefined means the draw is redrawn."""
    try:
        return bool(np.isfinite(GATE(P, wd, wa)["E.CZ"]))
    except Exception:  # noqa: BLE001
        return False


def run_draws(sampler, draws: int, seed: int, log: Path | None, name: str, replay: list | None = None):
    """Appends each accepted draw to the log as it is made, so a crash keeps the draws so far. With logged draws the
    generator is fast-forwarded through the same gate, so continuing equals never having stopped."""
    rng = np.random.default_rng(seed)
    got, redrawn = [r["stats"] for r in (replay or [])], 0
    for _ in range(len(got)):
        while not sampler.gate(ctx := sampler.draw(rng)):
            redrawn += 1
    if replay and redrawn != replay[-1]["redrawn"]:
        raise RuntimeError(f"{name}: the log does not belong to this data and code (redraws {redrawn} vs "
                           f"{replay[-1]['redrawn']})")
    sink = log.open("a") if log and len(got) < draws else None
    try:
        while len(got) < draws:
            ctx = sampler.draw(rng)
            if not sampler.gate(ctx):
                redrawn += 1
                if redrawn > MAX_REDRAW_FACTOR * draws:
                    raise RuntimeError(f"{name}: over {MAX_REDRAW_FACTOR * draws} draws redrawn; the gate is broken")
                continue
            row = sampler.row(ctx)
            got.append(row)
            if sink:
                sink.write(json.dumps({"set": name, "draw": len(got), "redrawn": redrawn,
                                       "stats": {k: (v if np.isfinite(v) else None) for k, v in row.items()}}) + "\n")
                sink.flush()
            if len(got) % 100 == 0:
                print(f"{name}: {len(got)}/{draws} draws, redrawn {redrawn}", file=sys.stderr, flush=True)
    finally:
        if sink:
            sink.close()
    return got, redrawn


class MainSampler:
    def __init__(self, P: Panel, template: dict, names: tuple):
        self.P, self.template, self.names = P, template, names

    def draw(self, rng):
        return block_weights(rng, self.P.periods, self.P.n_days), aircraft_weights(rng, self.P)

    def gate(self, ctx) -> bool:
        return gate_ok(self.P, ctx[0], ctx[1] * self.P.base_w)

    def row(self, ctx) -> dict:
        P, (wd, wa) = self.P, ctx
        row = flat("primary", attempt(primary, P, wd, wa * P.base_w, name="primary"), self.template)
        row.update(flat("days_only", attempt(primary, P, wd, P.base_w, name="days_only"), self.template, "primary"))
        for n in self.names:
            if n != "primary":
                row.update(flat(n, attempt(ESTIMATORS[n], P, wd, wa * weights_for(P, n), name=n), self.template))
        return row


class Q3Sampler:
    """Days are resampled in blocks within each window on its own. The aircraft draw is shared by the two windows (the
    primary, paired reading); a draw per window is the independent reading, reported beside it."""

    def __init__(self, P24: Panel, P26: Panel):
        self.W = (("e24", P24), ("e26", P26))
        self.pool = np.union1d(P24.pool, P26.pool)

    def draw(self, rng):
        wd = {t: block_weights(rng, W.periods, W.n_days) for t, W in self.W}
        shared = aircraft_weights(rng, self.W[0][1], self.pool)
        own = {t: aircraft_weights(rng, W) for t, W in self.W}
        return {"wd": wd, "shared": shared, "own": own}

    def gate(self, ctx) -> bool:
        return all(gate_ok(W, ctx["wd"][t], ctx["shared"] * W.base_w) for t, W in self.W)

    def row(self, ctx) -> dict:
        out = {}
        for t, W in self.W:
            wd, wa = ctx["wd"][t], ctx["shared"]
            out[f"{t}.primary.E.CZ"] = GATE(W, wd, wa * W.base_w)["E.CZ"]
            out[f"{t}.days_only.E.CZ"] = (attempt(primary, W, wd, W.base_w, name="days_only") or {}).get("E.CZ", np.nan)
            out[f"{t}.indep.E.CZ"] = (attempt(GATE, W, wd, ctx["own"][t] * W.base_w, name="indep") or {}).get("E.CZ", np.nan)
            for n in Q3_ESTIMATORS:
                if n != "primary":
                    out[f"{t}.{n}.E.CZ"] = (attempt(ESTIMATORS[n], W, wd, wa * weights_for(W, n), name=n) or {}).get(
                        "E.CZ", np.nan)
        return out


# ---------------------------------------------------------------- intervals and labels

def interval(x, level: float):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 20:
        return None
    a = (1 - level) / 2 * 100
    lo, hi = np.percentile(x, [a, 100 - a])
    return [float(lo), float(hi)]


def label_excess(ci95, ci90) -> str:
    if ci95 is None or ci90 is None:
        return NOT_COMPUTED
    if ci95[0] > MARGIN:
        return HIGHER
    if ci90[1] < MARGIN:
        return NO_EXCESS
    return INCONCLUSIVE


def label_change(ci95, ci90) -> str:
    if ci95 is None or ci90 is None:
        return NOT_COMPUTED
    if ci95[0] > 0:
        return INCREASE
    if ci90[1] < MARGIN:
        return NO_INCREASE
    return INCONCLUSIVE


def describe(est, draws, days_draws=None, label=None) -> dict:
    d = {"est": None if est is None or not np.isfinite(est) else float(est),
         "ci95": interval(draws, 0.95), "ci90": interval(draws, 0.90),
         "missing_draws": int(np.sum(~np.isfinite(np.asarray(draws, float))))}
    if days_draws is not None:
        d["days_only_ci95"], d["days_only_ci90"] = interval(days_draws, 0.95), interval(days_draws, 0.90)
    if label:
        d["label"] = label(d["ci95"], d["ci90"])
    return d


def column(got: list[dict], key: str) -> np.ndarray:
    return np.array([np.nan if r.get(key) is None else r[key] for r in got], float)


def gradient(est: dict, got: list[dict], primary_res: dict) -> dict:
    """G = E_CZ / E_BALT, only where E_BALT's label is a higher share than control; per draw only where that draw's
    E_BALT exceeds 0.01. Otherwise E_CZ and E_PL are shown as differences from E_BALT."""
    out = {}
    for tag in ("", *(f".y{y + 1}" for y in range(NYEAR))):
        bal, cz, pl = f"primary.E.BALT{tag}", f"primary.E.CZ{tag}", f"primary.E.PL{tag}"
        eb, ec, ep = column(got, bal), column(got, cz), column(got, pl)
        if primary_res[f"E.BALT{tag}"].get("label") == HIGHER:
            ok = eb > MARGIN
            g = np.where(ok, ec / np.where(ok, eb, 1), np.nan)
            point = est[cz] / est[bal] if est[bal] > MARGIN else None
            out[tag or "pooled"] = {"computed": True, **describe(point, g),
                                    "share_draws_undefined": float(np.mean(~ok)) if len(eb) else None}
        else:
            out[tag or "pooled"] = {"computed": False,
                                    "E_CZ_minus_E_BALT": describe(est[cz] - est[bal], ec - eb),
                                    "E_PL_minus_E_BALT": describe(est[pl] - est[bal], ep - eb)}
    return out


# ---------------------------------------------------------------- descriptive counts without intervals

def degraded_position_days(P: Panel) -> dict:
    r = P.points["primary"]
    U, G = sums(r, np.ones(P.n_days), P.base_w, r.dkey, P.n_days * NREG)
    U, G = U.reshape(P.n_days, NREG), G.reshape(P.n_days, NREG)
    share = ratio(G, U)
    out = {}
    for x in STUDY:
        i, c = RID[x], RID["CTRL"]
        eligible = (U[:, i] >= DAY_MIN_POINTS) & (U[:, c] >= DAY_MIN_POINTS)
        flagged = eligible & (share[:, i] >= DAY_MIN_SHARE - EPS) & (share[:, i] - share[:, c] >= DAY_MIN_GAP - EPS)
        out[x] = {str(y + 1): {"eligible_days": int((eligible & (P.year == y)).sum()),
                               "degraded_position_days": int((flagged & (P.year == y)).sum())}
                  for y in range(NYEAR)}
    return out


def repeat_airframes(P: Panel) -> dict:
    r = P.points["primary"]
    G = np.bincount(r.akey, P.base_w[r.ac] * r.g, P.n_ac * NREG).reshape(P.n_ac, NREG)
    out = {}
    for x in R.PRIMARY:
        g = G[:, RID[x]]
        out[x] = float(np.sort(g)[::-1][:TOP_AIRFRAMES].sum() / g.sum()) if g.sum() > 0 else None
    return out


# ---------------------------------------------------------------- the whole analysis

def windows(P: Panel) -> dict[int, np.ndarray]:
    return {y: np.array([dt.date(y, *Q3_FROM) <= w <= dt.date(y, *Q3_TO) for w in P.wed]) for y in (2024, 2026)}


def differs(label: str, primary_label: str) -> bool:
    return NOT_COMPUTED not in (label, primary_label) and label != primary_label


def analyse(P: Panel, draws: int = DRAWS, seed: int = SEED, log: Path | None = None,
            replay: dict | None = None) -> dict:
    ERRORS.clear()
    point, template, failed = point_estimates(P)
    if failed.get("primary") or not gate_ok(P, np.ones(P.n_days), P.base_w):
        raise RuntimeError("the primary estimate fails on the full data; no draw is made")
    w = windows(P)
    main_rows = (replay or {}).get("main") or []
    if replay is not None and len(main_rows) >= draws and "q3" not in replay:
        raise RuntimeError("the log holds no Q3 draws; stopping instead of drawing them silently (run without --from-log)")
    names = tuple(n for n in ESTIMATORS if not failed.get(n))
    got, redrawn = run_draws(MainSampler(P, template, names), draws, seed, log, "main", main_rows)
    res = {"design": "docs/research/gnss-design.md", "seed": seed, "draws": len(got),
           "draws_complete": len(got) == draws, "redrawn": redrawn,
           "estimators_failed_on_all_data": sorted(failed),
           "sample": {"days": P.n_days, "per_year": {str(y + 1): int((P.year == y).sum()) for y in range(NYEAR)},
                      "aircraft": P.n_ac, "screenable": int(P.screen.sum()),
                      "persistently_degraded": int(P.persistent.sum()),
                      "persistently_degraded_strict_reading": int((~P.keep_strict).sum()),
                      "days_kp_5_or_more": int(P.storm.sum()), "days_kp_below_5": int(P.calm.sum())}}
    pri = {}
    for k in template["primary"]:
        pri[k] = describe(point[f"primary.{k}"], column(got, f"primary.{k}"), column(got, f"days_only.{k}"),
                          label_excess if k.startswith("E.") else None)
    res["primary"] = pri
    res["q1"] = pri["E.CZ"]
    res["q2"] = {"E_PL": pri["E.PL"], "E_BALT": pri["E.BALT"],
                 "gradient": gradient(point, got, pri),
                 "bands": {n: pri[f"E.band.{n}"] for n in C.BANDS},
                 "bands_note": "E.band is the share over the four regions' points in the band minus control's pooled "
                               "share; it is not a regional contrast. D.<region>.band.<band> below are the regions' own "
                               "shares per band.",
                 "D_by_region_and_band": {x: {n: pri[f"D.{x}.band.{n}"] for n in C.BANDS} for x in R.PRIMARY}}
    res["q4"] = {k: describe(point[f"jumps.{k}"], column(got, f"jumps.{k}")) for k in template["jumps"]}
    res["degraded_position_days"] = degraded_position_days(P)
    res["repeat_airframes_top10_share"] = repeat_airframes(P)

    checks = {}
    for n in CHECKS:
        if failed.get(n):
            checks[n] = {"run": False}
            continue
        c = {}
        for x in STUDY:
            k = f"E.{x}"
            d = describe(point[f"{n}.{k}"], column(got, f"{n}.{k}"), label=label_excess)
            d["primary_label"] = pri[k]["label"]
            d["differs_from_primary"] = differs(d["label"], pri[k]["label"])
            c[k] = d
        checks[n] = c
    res["checks"] = checks
    res["q3"] = q3(P, w, draws, seed, log, replay)
    res["estimator_errors"] = dict(ERRORS)
    return res


def q3(P: Panel, w: dict, draws: int, seed: int, log: Path | None, replay: dict | None) -> dict:
    if not w[2024].any() or not w[2026].any():
        return {"run": False, "reason": "a window has no sampled day"}
    P24, P26 = P.restrict(w[2024]), P.restrict(w[2026])
    wd = np.ones(P.n_days)
    est = {}
    for tag, W in (("e24", P24), ("e26", P26)):
        for n in Q3_ESTIMATORS:
            est[f"{tag}.{n}"] = (attempt(ESTIMATORS[n], W, wd, weights_for(W, n), name=n) or {}).get("E.CZ", np.nan)
    got, redrawn = run_draws(Q3Sampler(P24, P26), draws, seed, log, "q3", (replay or {}).get("q3") or [])
    out = {"windows": {"2024": [str(dt.date(2024, *Q3_FROM)), str(dt.date(2024, *Q3_TO))],
                       "2026": [str(dt.date(2026, *Q3_FROM)), str(dt.date(2026, *Q3_TO))]},
           "days": {"2024": int(w[2024].sum()), "2026": int(w[2026].sum())}, "redrawn": redrawn,
           "reading": "aircraft draw shared by the two windows (paired); blocks of days per window on their own",
           "estimators": {}}
    for n in (*Q3_ESTIMATORS, "days_only", "indep"):
        src = "primary" if n in ("days_only", "indep") else n
        e24, e26 = est.get(f"e24.{src}", np.nan), est.get(f"e26.{src}", np.nan)
        diff = column(got, f"e26.{n}.E.CZ") - column(got, f"e24.{n}.E.CZ")
        out["estimators"][n] = {"E_CZ_2024": e24, "E_CZ_2026": e26, **describe(e26 - e24, diff, label=label_change)}
    out["change"] = dict(out["estimators"]["primary"])
    for k, n in (("days_only", "days_only"), ("independent_aircraft", "indep")):
        out["change"][f"{k}_ci95"] = out["estimators"][n]["ci95"]
        out["change"][f"{k}_ci90"] = out["estimators"][n]["ci90"]
    out["independent_aircraft"] = out["estimators"].pop("indep")
    out["independent_aircraft"]["note"] = "check: aircraft redrawn per window instead of shared"
    del out["estimators"]["days_only"]
    for n, d in out["estimators"].items():
        d["primary_label"] = out["change"]["label"]
        d["differs_from_primary"] = differs(d["label"], out["change"]["label"])
    out["independent_aircraft"]["differs_from_primary"] = differs(out["independent_aircraft"]["label"],
                                                                  out["change"]["label"])
    return out


# ---------------------------------------------------------------- real data: the only code that opens sealed/

def merged_day(days_dir: Path, wed: dt.date) -> dict[str, pd.DataFrame]:
    """One day's screening and sealed layers joined row for row; the keys must agree or the day stops the run."""
    base = days_dir / str(wed)
    keys = {"points": ["icao", "variant", "region", "band"], "west": ["icao"],
            "crossings": ["icao", "region", "crossing"], "crossings_agg": ["band", "region", "icao"]}
    out = {}
    for name, k in keys.items():
        s = pd.read_parquet(base / "screening" / f"{name}.parquet")
        d = pd.read_parquet(base / "sealed" / f"{name}.parquet")
        if len(s) != len(d) or any((s[c].to_numpy() != d[c].to_numpy()).any() for c in k):
            raise ValueError(f"{wed}: screening and sealed {name} do not line up")
        out[name] = pd.concat([s, d.drop(columns=[c for c in d.columns if c in s.columns])], axis=1)
    return out


def build_panel(days: list[tuple[dt.date, str]], frame_of, kp: dict) -> Panel:
    """`frame_of(wed)` returns one day as `merged_day` does (one at a time, so only one day is in memory). Columns:
    points (icao, variant, region, band, usable, degraded), west (icao, usable, degraded), crossings (icao, region,
    usable_buf, degraded_buf), crossings_agg (band, region, icao, crossings_usable, jump_crossings_usable)."""
    ids: dict[str, int] = {}

    def code(s: pd.Series) -> np.ndarray:
        inv, uniq = pd.factorize(s)
        g = np.array([ids.setdefault(u, len(ids)) for u in uniq], np.int32)
        return g[inv] if len(inv) else np.zeros(0, np.int32)

    nprim = len(R.PRIMARY)
    pts: dict[str, list[Rows]] = {v: [] for v in C.VARIANTS}
    west, cross, call, cband = [], [], [], []
    band_id = {b: i for i, b in enumerate(C.BANDS)}
    for i, (wed, _) in enumerate(days):
        f = frame_of(wed)
        p = f["points"]
        df = pd.DataFrame({"v": p["variant"].to_numpy(), "ac": code(p["icao"]),
                           "reg": strict(p["region"], RID), "band": strict(p["band"], band_id),
                           "u": p["usable"].to_numpy(float), "g": p["degraded"].to_numpy(float)})
        for v, g in df.groupby("v"):
            if v == "primary":
                pts[v].append(mk(i, g["ac"], g["reg"], g["band"], g["u"], g["g"]))
            else:
                g = g[g["reg"] < nprim].groupby(["ac", "reg"], as_index=False)[["u", "g"]].sum()
                pts[v].append(mk(i, g["ac"], g["reg"], 0, g["u"], g["g"]))
        w = f["west"]
        west.append(mk(i, code(w["icao"]), 0, 0, w["usable"], w["degraded"]))
        x = f["crossings"]
        x = x[(x["usable_buf"] >= CROSSING_MIN_POINTS) & (strict(x["region"], RID) < nprim)]
        cross.append(mk(i, code(x["icao"]), strict(x["region"], RID), 0, 1.0,
                        (x["degraded_buf"] >= CROSSING_MIN_DEGRADED).astype(float)))
        a = f["crossings_agg"]
        a = a[strict(a["region"], RID) < nprim]
        reg, ac = strict(a["region"], RID), code(a["icao"])
        isall = (a["band"] == "all").to_numpy()
        cu, ju = a["crossings_usable"], a["jump_crossings_usable"]
        call.append(mk(i, ac[isall], reg[isall], BAND_ALL, cu[isall], ju[isall]))
        cband.append(mk(i, ac[~isall], reg[~isall], strict(a["band"][~isall], band_id), cu[~isall], ju[~isall]))
    return Panel([w for w, _ in days], [u for _, u in days], kp, list(ids), {v: cat_rows(r) for v, r in pts.items()},
                 cat_rows(west), cat_rows(cross), cat_rows(call), cat_rows(cband))


def strict(s: pd.Series, mapping: dict) -> np.ndarray:
    out = s.map(mapping)
    if out.isna().any():
        raise ValueError(f"unknown label in {sorted(set(s[out.isna()]))}")
    return out.to_numpy()


def mk(day: int, ac, reg, band, u, g) -> Rows:
    ac = np.asarray(ac, np.int32)
    n = ac.size
    full = lambda x, dt_: (np.full(n, x, dt_) if np.isscalar(x) else np.asarray(x).astype(dt_))  # noqa: E731
    return Rows(np.full(n, day, np.int32), ac, full(reg, np.int8), full(band, np.int8), full(u, np.float64),
                full(g, np.float64))


def load_panel(days_dir: Path, kp: dict) -> Panel:
    days = []
    for wed in F.sample_days():
        p = days_dir / str(wed) / "manifest.json"
        m = json.loads(p.read_text()) if p.exists() else None
        if m and m["status"] in ("counted", "replaced"):
            days.append((wed, m["date_used"]))
    return build_panel(days, lambda wed: merged_day(days_dir, wed), kp)


def frozen() -> str | None:
    """None if the code is tagged and unchanged since; otherwise why not."""
    git = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout  # noqa: E731
    if FREEZE_TAG not in git("tag", "--points-at", "HEAD").split():
        return f"HEAD does not carry the tag {FREEZE_TAG}"
    if git("status", "--porcelain", "--", "tools/gnss").strip():
        return "tools/gnss has uncommitted changes"
    return None


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer, np.bool_)):
        return o.item()
    return o


def versions() -> dict:
    import importlib.metadata as md
    return {p: md.version(p) for p in ("numpy", "pandas", "pyarrow", "shapely")}


def replay_rows(path: Path) -> dict[str, list]:
    out: dict[str, list] = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        out.setdefault(r["set"], []).append(r)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unblind", action="store_true", help="open the sealed counts (degraded points, jumps)")
    ap.add_argument("--from-log", type=Path, help="continue from a draw log (to 2 000 draws) and append to it")
    args = ap.parse_args()
    if not args.unblind:
        sys.exit("refusing to open the sealed counts: pass --unblind once the estimation code is tagged (§3)")
    why = frozen()
    if why:
        sys.exit(f"refusing to open the sealed counts: {why}")
    kp_file = F.KP_DIR / F.KP_NAME
    P = load_panel(F.DAYS, F.parse_kp(kp_file.read_text()))
    log = args.from_log or DRAWS_LOG.with_name(f"{DRAWS_LOG.stem}-{pd.Timestamp.now():%Y%m%dT%H%M%S}.jsonl")
    res = analyse(P, DRAWS, SEED, log, replay_rows(args.from_log) if args.from_log else None)
    res["versions"] = versions()
    res["generated"] = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(clean(res), indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}: {res['draws']} draws, {res['redrawn']} redrawn")


if __name__ == "__main__":
    main()
