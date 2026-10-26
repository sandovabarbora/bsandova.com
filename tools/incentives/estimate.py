"""Estimates of the investment incentives study (design §4, §6, §7): the stacked weighted difference in differences,
Q1, Q2, Q3, the pre-path difference, the district bootstrap with clones, randomisation inference, the minimum rule,
the label, and checks 1-12.

Frozen with tests on made-up panels (test_incentives.py). On real MPSV data it runs only when asked with --unblind,
and only if the screening (docs/research/incentives-screening.json) names an outcome rule that can be computed
(the amended one of the 26 October 2026 change log entry: MPSV's podilNezamestnanychOsobPNO). Writes
docs/research/incentives-results.json; every bootstrap and permutation draw is appended to tools/data/incentives/draws.jsonl.

    nice -n 20 uv run --no-project --with pandas --with numpy python -I tools/incentives/estimate.py --demo
    nice -n 20 uv run --no-project --with pandas --with numpy python -I tools/incentives/estimate.py --unblind
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")  # two threads, set before numpy loads

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, MPSV_DIR, ROOT

YEARS = (-2, -1, 0, 1, 2, 3)
REF = -1
POST = (1, 2, 3)
PRE = (-2, -1)
MIN_MONTHS = 10
DRAWS = 2000
SEED_BOOT = 20261016
SEED_PERM = 20261017
FIRST_MONTH = 2004 * 12 + 6  # July 2004 as months since year 0
LAST_MONTH = 2024 * 12 + 11
MIN_EVENTS, MIN_DISTRICTS = 20, 15
EFFECT_MIN = 0.10  # labels 1 and 2
BAND = 0.20  # label 3
WIDTH_MAX = 0.40  # label 4
ALPHA_P = 0.05
SCREENING = ROOT / "docs/research/incentives-screening.json"
OUT = ROOT / "docs/research/incentives-results.json"
DRAW_LOG = DATA / "draws.jsonl"
MAX_MISSING_SHARE = 0.01  # more missing bootstrap or permutation draws than this and the primary gets no label
MAX_REDRAWS = 100_000  # a bootstrap whose draws never hold an event is a design failure, not something to wait out
Q3_REASON = "no ČSÚ population 15-64 for year -1 of the treated districts; Q3 not computable"
CRISIS = (2009 * 12, 2009 * 12 + 11)
COVID = (2020 * 12, 2021 * 12 + 11)
PNO_CHANGE = 2013 * 12  # January 2013, MPSV's new definition of the published rate (check 12)
TOL = 1e-12


# ---------- events and sub-panels ----------

@dataclass(frozen=True)
class Event:
    id: str
    treated: str
    month: int  # decision month, months since year 0
    comparisons: tuple[str, ...]
    jobs: float = 0.0
    cancelled: str = ""
    regime: str = ""
    moved: tuple[str, ...] = ()  # districts with a 2007/2016 boundary change inside years −2 to 3 (check 6)


@dataclass
class SubPanel:
    """One event's yearly means: rows are districts (treated first), columns the event years kept."""
    event: Event
    units: list[str]
    years: list[int]
    y: np.ndarray  # units × years
    pop_pre: float = float("nan")  # treated district's population 15-64, mean of year -1
    control: np.ndarray | None = None  # per unit, for check 11


def event_months(m0: int, years: tuple[int, ...]) -> np.ndarray:
    return np.arange(m0 + 12 * min(years), m0 + 12 * max(years) + 12)


def sub_panel(wide: pd.DataFrame, ev: Event, years: tuple[int, ...] = YEARS,
              required: tuple[int, ...] = YEARS, pop: pd.DataFrame | None = None,
              control_years: tuple[int, int] | None = None) -> SubPanel | None:
    """§2 "Missing months" and "Event time": months missing for any district of the event are dropped for all; an
    event year with fewer than 10 months left is missing; an event missing a required year is dropped (None).

    `wide` is months × districts of the monthly outcome (NaN where missing)."""
    units = [ev.treated] + list(ev.comparisons)
    span = event_months(ev.month, years)
    block = wide.reindex(index=span, columns=units)
    keep = block.notna().all(axis=1).to_numpy()
    k_of = (span - ev.month) // 12
    yrs, cols = [], []
    for k in years:
        mask = keep & (k_of == k)
        if mask.sum() < MIN_MONTHS:
            if k in required:
                return None
            continue
        yrs.append(k)
        cols.append(block.to_numpy()[mask].mean(axis=0))
    sp = SubPanel(ev, units, yrs, np.column_stack(cols))
    if pop is not None:
        mask = keep & (k_of == -1)
        sp.pop_pre = float(pop.reindex(index=span[mask], columns=[ev.treated]).to_numpy().mean())
    if control_years is not None:
        a, b = control_years  # control = mean(year b) - mean(year a), over months kept for all districts
        span_c = event_months(ev.month, (a, b))
        bc = wide.reindex(index=span_c, columns=units)
        kc = bc.notna().all(axis=1).to_numpy()
        kk = (span_c - ev.month) // 12
        ma, mb = kc & (kk == a), kc & (kk == b)
        if ma.sum() < MIN_MONTHS or mb.sum() < MIN_MONTHS:
            return None
        sp.control = bc.to_numpy()[mb].mean(axis=0) - bc.to_numpy()[ma].mean(axis=0)
    return sp


# ---------- the stacked weighted regression ----------

def demean(a: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted two-way within transformation of a balanced units × years block, weights constant within a unit:
    exactly the residual of the unit and year fixed effects of one event."""
    unit = a.mean(axis=1, keepdims=True)
    yr = (w @ a) / w.sum()
    return a - unit - yr[None, :] + (w @ unit).item() / w.sum()


@dataclass
class Design:
    """One event's block as entered in the stacked regression: outcome, treated flags, weights, unit labels."""
    years: list[int]
    y: np.ndarray
    treated: np.ndarray  # bool per unit
    w: np.ndarray
    control: np.ndarray | None = None


def weights(treated: np.ndarray) -> np.ndarray:
    """§4: 1 for a treated unit, 1/n_e for each of the n_e comparison units of the event."""
    n_c = int((~treated).sum())
    return np.where(treated, 1.0, 1.0 / n_c)


def design_of(sp: SubPanel, rows: np.ndarray | None = None, treated_row: int = 0) -> Design | None:
    """The block of one event; `rows` repeats units (bootstrap clones) and `treated_row` picks the unit that stands as
    treated (randomisation inference). None if it has no treated or no comparison unit."""
    idx = np.arange(len(sp.units)) if rows is None else rows
    tr = idx == treated_row
    if not tr.any() or tr.all():
        return None
    ctrl = None if sp.control is None else sp.control[idx]
    return Design(sp.years, sp.y[idx], tr, weights(tr), ctrl)


def fit(designs: list[Design], years: tuple[int, ...] = YEARS, with_control: bool = False) -> dict[int, float]:
    """WLS of the outcome on treated × event-year indicators (year −1 left out) with district-by-event and
    event-year-by-event fixed effects; returns β per event year, β(−1) = 0."""
    coef_years = [k for k in years if k != REF]
    p = len(coef_years) * (2 if with_control else 1)
    xtx, xty = np.zeros((p, p)), np.zeros(p)
    for d in designs:
        cols = []
        for k in coef_years:
            ind = np.array([1.0 if yk == k else 0.0 for yk in d.years])
            cols.append(np.outer(d.treated.astype(float), ind))
        if with_control:
            for k in coef_years:
                ind = np.array([1.0 if yk == k else 0.0 for yk in d.years])
                cols.append(np.outer(d.control, ind))
        yt = demean(d.y, d.w)
        xs = [demean(c, d.w) for c in cols]
        wm = d.w[:, None]
        for i, xi in enumerate(xs):
            xty[i] += (wm * xi * yt).sum()
            for j in range(i, p):
                xtx[i, j] += (wm * xi * xs[j]).sum()
                xtx[j, i] = xtx[i, j]
    used = np.diag(xtx) > TOL
    beta = np.full(p, np.nan)
    beta[used] = np.linalg.solve(xtx[np.ix_(used, used)], xty[used])
    out = {k: float(beta[i]) for i, k in enumerate(coef_years)}
    out[REF] = 0.0
    return out


def q1(beta: dict[int, float], post: tuple[int, ...] = POST, pre: tuple[int, ...] = PRE) -> float:
    """§4: mean of the post-year coefficients minus mean of the reference-year coefficients."""
    return float(np.mean([beta[k] for k in post]) - np.mean([beta[k] for k in pre]))


def stats_of(beta: dict[int, float], q3_den: float = float("nan")) -> dict[str, float]:
    if not all(k in beta for k in YEARS):
        return {}
    ref = np.mean([beta[k] for k in PRE])
    s = {"q1": q1(beta), "pre_diff": beta[-1] - beta[-2], "q1_ref_minus1": q1(beta, POST, (-1,))}
    for k in (0, 1, 2, 3):
        s[f"q2_y{k}"] = beta[k] - ref
    s["q3"] = s["q1"] / q3_den if q3_den and np.isfinite(q3_den) else float("nan")
    return s


def q3_denominator(panels: list[SubPanel], counts: list[int] | None = None) -> float:
    """Event-weighted mean of 100 × promised jobs / population 15-64 of the treated district in year −1 (Q3)."""
    vals, wts = [], []
    for i, sp in enumerate(panels):
        c = 1 if counts is None else counts[i]
        if c and np.isfinite(sp.pop_pre) and sp.pop_pre > 0:
            vals.append(100 * sp.event.jobs / sp.pop_pre)
            wts.append(c)
    return float(np.average(vals, weights=wts)) if vals else float("nan")


def estimate(panels: list[SubPanel], years: tuple[int, ...] = YEARS, with_control: bool = False) -> dict:
    designs = [d for d in (design_of(sp) for sp in panels) if d is not None]
    beta = fit(designs, years, with_control)
    return {"beta": beta, **stats_of(beta, q3_denominator(panels))}


# ---------- bootstrap and randomisation inference ----------

class DrawLog:
    """Appends one JSON line per draw as it is made, flushed at once, so an interrupted run keeps what it computed."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stamp = pd.Timestamp.now("UTC").isoformat()  # a rerun appends to the same file; this tells the runs apart
        self.f = open(path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - open for the whole run, line-flushed
        self.run = ""

    def write(self, kind: str, i: int, **row) -> None:
        self.f.write(json.dumps(jsonable({"stamp": self.stamp, "run": self.run, "kind": kind, "i": i} | row), allow_nan=False) + "\n")
        self.f.flush()


def failure(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"


def clone_rows(sp: SubPanel, counts: dict[str, int]) -> np.ndarray:
    """Rows of a sub-panel after a district bootstrap draw: a district drawn k times enters as k copies."""
    return np.array([i for i, u in enumerate(sp.units) for _ in range(counts.get(u, 0))], dtype=int)


def bootstrap(panels: list[SubPanel], draws: int = DRAWS, seed: int = SEED_BOOT, years: tuple[int, ...] = YEARS,
              with_control: bool = False, stat=None, log: DrawLog | None = None) -> dict:
    """§4 intervals: whole districts drawn with replacement from every district in the stacked panel; n_e counted on
    the drawn comparison copies; an event with no treated or no comparison copy is absent; draws with no event are
    redrawn and counted (the only gate). Any other failure inside a draw leaves that draw missing, and is counted."""
    stat = stat or (lambda beta, den: stats_of(beta, den))
    rng = np.random.default_rng(seed)
    universe = sorted({u for sp in panels for u in sp.units})
    out, redrawn, failed, n_events = [], 0, 0, []
    while len(out) < draws:
        pick = rng.integers(0, len(universe), size=len(universe))
        cnt = np.bincount(pick, minlength=len(universe))
        counts = {u: int(c) for u, c in zip(universe, cnt) if c}
        designs, kept, tcounts = [], [], []
        for sp in panels:
            rows = clone_rows(sp, counts)
            d = design_of(sp, rows, treated_row=0) if rows.size else None
            if d is not None:
                designs.append(d)
                kept.append(sp)
                tcounts.append(int(d.treated.sum()))
        if not designs:
            redrawn += 1
            if log:
                log.write("boot_redraw", redrawn)
            if redrawn > MAX_REDRAWS:
                raise RuntimeError("bootstrap: no draw holds an event")
            continue
        try:  # not a gate: a draw that cannot be estimated is missing, it must not stop the other draws
            row, err = stat(fit(designs, years, with_control), q3_denominator(kept, tcounts)), None
        except Exception as e:  # noqa: BLE001
            row, err = {}, failure(e)
            failed += 1
        out.append(row)
        n_events.append(len(designs))
        if log:
            log.write("boot", len(out) - 1, redrawn_so_far=redrawn, events=len(designs), stat=row, error=err)
    return {"draws": pd.DataFrame(out), "redrawn": redrawn, "failed": failed,
            "events_per_draw_mean": float(np.mean(n_events))}


def column(df: pd.DataFrame, name: str) -> pd.Series:
    """A statistic of the bootstrap draws; all missing if every draw failed."""
    return df[name] if name in df else pd.Series(np.full(max(len(df), 1), np.nan))


def interval(x: pd.Series, level: float) -> list[float]:
    """Percentile interval of the bootstrap draws that were estimated."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not x.size:
        return [float("nan"), float("nan")]
    a = (1 - level) / 2
    return [float(np.quantile(x, a)), float(np.quantile(x, 1 - a))]


def permutation_p(panels: list[SubPanel], observed: float, perms: int = DRAWS, seed: int = SEED_PERM,
                  years: tuple[int, ...] = YEARS,
                  statistic=q1, with_control: bool = False, log: DrawLog | None = None) -> dict:
    """§4 randomisation inference: per event one district of its pool (comparisons plus the true treated) drawn to
    stand as treated, the others as comparisons with weight 1/n_e; p = share of permutations with |Q1| ≥ observed.
    A permutation that cannot be estimated is left out of the share (counted in `failed`), not counted as below."""
    rng = np.random.default_rng(seed)
    vals = np.full(perms, np.nan)
    for b in range(perms):
        designs = []
        for sp in panels:
            pool = np.arange(len(sp.units))
            t = int(pool[rng.integers(0, len(pool))])
            d = design_of(sp, pool, treated_row=t)
            if d is not None:
                designs.append(d)
        err = None
        try:  # not a gate: same rule as in the bootstrap
            if not designs:
                raise ValueError("no event in the permutation")
            vals[b] = statistic(fit(designs, years, with_control))
        except Exception as e:  # noqa: BLE001
            err = failure(e)
        if log:
            log.write("perm", b, events=len(designs), q=vals[b], error=err)
    ok = np.isfinite(vals)
    failed = int((~ok).sum())
    p = float(np.mean(np.abs(vals[ok]) >= abs(observed) - TOL)) if ok.any() and np.isfinite(observed) else float("nan")
    return {"p": p, "perms": perms, "failed": failed}


# ---------- labels ----------

def label(q1_est: float, ci90: list[float], ci95: list[float], p: float, pre_ci95: list[float],
          minimum_met: bool = True) -> str:
    """§6, the first that holds; §4 minimum rule removes labels 1-3. With any input missing no label can be given."""
    if not all(np.isfinite([q1_est, p, *ci90, *ci95, *pre_ci95])):
        return "not computable"
    lab = None
    if minimum_met:
        if ci95[1] < 0 and q1_est <= -EFFECT_MIN + TOL and p <= ALPHA_P + TOL:
            lab = "lower unemployment after the promise"
        elif ci95[0] > 0 and q1_est >= EFFECT_MIN - TOL and p <= ALPHA_P + TOL:
            lab = "higher unemployment after the promise"
        elif ci90[0] >= -BAND - TOL and ci90[1] <= BAND + TOL:
            lab = "no change larger than 0.20 points"
    if lab is None:
        lab = "underpowered" if ci90[1] - ci90[0] > WIDTH_MAX + TOL else "inconclusive"
    if pre_ci95[0] > 0 or pre_ci95[1] < 0:
        lab += " with differing paths in the two years before the promise"
    return lab


def minimum_met(panels: list[SubPanel]) -> bool:
    return len(panels) >= MIN_EVENTS and len({sp.event.treated for sp in panels}) >= MIN_DISTRICTS


# ---------- one full run (primary or a check) ----------

def run(panels: list[SubPanel], draws: int = DRAWS, perms: int = DRAWS, years: tuple[int, ...] = YEARS,
        with_control: bool = False, post: tuple[int, ...] = POST, pre: tuple[int, ...] = PRE,
        labelled: bool = True, log: DrawLog | None = None, name: str = "") -> dict:
    """Point estimate, bootstrap intervals and randomisation p of Q = mean(β post) − mean(β pre); with the primary
    years and reference also Q2, Q3, Q1 against year −1, the minimum rule and the label."""
    if log:
        log.run = name
    designs = [d for d in (design_of(sp) for sp in panels) if d is not None]
    beta = fit(designs, years, with_control)
    stat = (lambda b, den: {"q": q1(b, post, pre), "pre_diff": b[-1] - b[-2],
                            **{f"beta_{k}": b[k] for k in years}} | stats_of(b, den))
    den = q3_denominator(panels)
    point = stat(beta, den)
    boot = bootstrap(panels, draws, SEED_BOOT, years, with_control, stat, log)
    d = boot["draws"]
    ri = permutation_p(panels, point["q"], perms, SEED_PERM, years, lambda b: q1(b, post, pre), with_control, log)
    q = column(d, "q")
    res = {
        "n_events": len(panels), "n_treated_districts": len({sp.event.treated for sp in panels}),
        "estimate": point["q"], "ci90": interval(q, 0.90), "ci95": interval(q, 0.95),
        "p_randomisation": ri["p"],
        "pre_diff": point["pre_diff"], "pre_diff_ci90": interval(column(d, "pre_diff"), 0.90),
        "pre_diff_ci95": interval(column(d, "pre_diff"), 0.95),
        "beta": {str(k): point[f"beta_{k}"] for k in years},
        "beta_ci95": {str(k): interval(column(d, f"beta_{k}"), 0.95) for k in years if k != REF},
        "bootstrap_redrawn": boot["redrawn"], "bootstrap_failed": boot["failed"], "bootstrap_events_per_draw_mean": boot["events_per_draw_mean"],
        "bootstrap_missing_q": int((~np.isfinite(q)).sum()) if len(d) else draws,
        "permutations_missing": ri["failed"], "draws": draws, "perms": perms,
    }
    if years == YEARS and post == POST and pre == PRE:
        res["q2"] = {str(k): {"est": point[f"q2_y{k}"], "ci95": interval(column(d, f"q2_y{k}"), 0.95)}
                     for k in (0, 1, 2, 3)}
        res["q3"] = ({"est": point["q3"], "ci90": interval(column(d, "q3"), 0.90), "denominator": den}
                     if np.isfinite(den) else {"est": None, "reason": Q3_REASON})
        res["q1_ref_minus1"] = {"est": point["q1_ref_minus1"], "ci95": interval(column(d, "q1_ref_minus1"), 0.95)}
        res["width90"] = res["ci90"][1] - res["ci90"][0]
        res["minimum_met"] = minimum_met(panels)
        res["label"] = label(res["estimate"], res["ci90"], res["ci95"], res["p_randomisation"],
                             res["pre_diff_ci95"], res["minimum_met"]) if labelled else None
        if labelled and (res["bootstrap_missing_q"] > MAX_MISSING_SHARE * draws
                         or res["permutations_missing"] > MAX_MISSING_SHARE * perms):
            res["label"] = "not computable"
    return res


# ---------- checks (§7) ----------

def covers(ev: Event, lo: int, hi: int, years: tuple[int, ...] = YEARS) -> bool:
    span = event_months(ev.month, years)
    return bool(span[0] <= hi and span[-1] >= lo)


def restrict_pool(sp: SubPanel, keep: set[str]) -> SubPanel | None:
    rows = [0] + [i for i, u in enumerate(sp.units) if i and u in keep]
    if len(rows) < 2:
        return None
    return replace(sp, units=[sp.units[i] for i in rows], y=sp.y[rows],
                   control=None if sp.control is None else sp.control[rows])


def baseline_means(wide: pd.DataFrame, ev: Event, districts: list[str]) -> pd.Series:
    """Check 4: each district's mean outcome over years −2 and −1 of the event (months it has)."""
    span = event_months(ev.month, PRE)
    return wide.reindex(index=span, columns=districts).mean(axis=0)


def tercile_pool(sp: SubPanel, base: pd.Series) -> set[str]:
    cut = np.nanquantile(base.to_numpy(), [1 / 3, 2 / 3])
    terc = base.apply(lambda v: int(np.searchsorted(cut, v, side="right")) if np.isfinite(v) else -1)
    t = terc.get(sp.event.treated, -1)
    return {u for u in sp.units[1:] if terc.get(u, -2) == t}


def drop_moved(sp: SubPanel) -> SubPanel | None:
    """Check 6: an event whose treated district moved is out; moved comparison districts leave the pool."""
    moved = set(sp.event.moved)
    if sp.event.treated in moved:
        return None
    return restrict_pool(sp, set(sp.units) - moved)


def spans_pno_change(ev: Event) -> bool:
    """Check 12: the event's months −24 to +47 (its clean window, and years −2 to 3) contain January 2013."""
    return covers(ev, PNO_CHANGE, PNO_CHANGE)


def checks(wide: pd.DataFrame, events: list[Event], panels: list[SubPanel], *, draws: int, perms: int,
           all_districts: list[str], regions: dict[str, str], log: DrawLog | None = None, save=None,
           pop: pd.DataFrame | None = None) -> dict:
    out = {}
    by_id = {sp.event.id: sp for sp in panels}

    def go(key: str, name: str, build, **kw) -> None:
        """Builds the event list of one check and runs it; a check that cannot be built or estimated is reported as
        such and must not cost the others. Saves after every check, so a late crash keeps what was computed."""
        try:
            sel = build()
            out[key] = run(sel, draws, perms, labelled=False, log=log, name=name, **kw) if sel else {"n_events": 0}
        except Exception as e:  # noqa: BLE001
            out[key] = {"error": failure(e)}
        if save:
            save(out)

    for thr in (500, 1000):
        go(f"1_jobs_{thr}", f"1_jobs_{thr}", lambda thr=thr: [sp for sp in panels if sp.event.jobs >= thr])
    if panels:
        top = max(panels, key=lambda sp: (sp.event.jobs, -sp.event.month))
        go("1_without_largest", "1_without_largest", lambda: [sp for sp in panels if sp is not top])
        out["1_without_largest"]["left_out"] = top.event.id
    go("2_without_cancelled_or_unverified", "2",
       lambda: [sp for sp in panels if sp.event.cancelled not in ("ANO", "ověřit")])
    go("3_same_region", "3", lambda: [r for sp in panels if (r := restrict_pool(
        sp, {u for u in sp.units if regions.get(u) == regions.get(sp.event.treated)}))])

    def tercile_events():
        found = []
        for sp in panels:
            r = restrict_pool(sp, tercile_pool(sp, baseline_means(wide, sp.event, all_districts)))
            if r:
                found.append(r)
        return found
    go("4_same_tercile", "4", tercile_events)
    go("5_without_2009_2020_21", "5", lambda: [sp for sp in panels if not covers(sp.event, *CRISIS)
                                              and not covers(sp.event, *COVID)])
    out["5_without_2009_2020_21"]["labels"] = "none (design §7.5)"
    go("6_without_boundary_districts", "6", lambda: [r for sp in panels if (r := drop_moved(sp))])
    go("7_years_1_to_5", "7", lambda: [sp for ev in events if ev.month <= 2019 * 12 + 11
                                       if (sp := sub_panel(wide, ev, years=(-2, -1, 0, 1, 2, 3, 4, 5), required=YEARS))],
       years=(-2, -1, 0, 1, 2, 3, 4, 5), post=(1, 2, 3, 4, 5))
    go("8_statutory_regime_only", "8", lambda: [sp for sp in panels if sp.event.regime == "Zákonná pobídka"])
    left = [0]

    def placebo_events():
        plac = []
        for ev in events:
            if ev.month - 48 < FIRST_MONTH:
                left[0] += 1
                continue
            sp = sub_panel(wide, replace(ev, month=ev.month - 24), years=(-2, -1, 0, 1), required=(-2, -1, 0, 1))
            if sp:
                plac.append(sp)
        return plac
    go("9_placebo_two_years_earlier", "9", placebo_events, years=(-2, -1, 0, 1), post=(0, 1))
    out["9_placebo_two_years_earlier"]["left_out_before_2004_07"] = left[0]
    go("10_reference_year_minus1", "10", lambda: panels, pre=(-1,))
    go("11_control_change_minus3_to_minus2", "11",
       lambda: [sp for ev in events if ev.month - 36 >= FIRST_MONTH and ev.id in by_id
                if (sp := sub_panel(wide, ev, pop=pop, control_years=(-3, -2)))], with_control=True)
    go("12_without_window_spanning_2013_01", "12", lambda: [sp for sp in panels if not spans_pno_change(sp.event)])
    return out


# ---------- real data (refused unless --unblind) ----------

def load_panel(mpsv_dir: Path = MPSV_DIR) -> pd.DataFrame:
    """Monthly outcome, months × districts: MPSV's own rate podilNezamestnanychOsobPNO in percentage points."""
    from fetch import months, mpsv_name
    rows = []
    for y, m in months():
        f = mpsv_dir / mpsv_name(y, m)
        if not f.exists():
            continue
        for it in json.loads(f.read_text(encoding="utf-8"))["polozky"]:
            rows.append({"month": y * 12 + m - 1, "district": it["okres"].split("/")[-1],
                         "y": it.get("podilNezamestnanychOsobPNO")})
    return pd.DataFrame(rows).pivot(index="month", columns="district", values="y").astype(float)


def to_events(raw: list[dict]) -> list[Event]:
    return sorted((Event(str(e["id_projekt"]), e["district"], int(e["month"]), tuple(e["comparisons"]),
                         float(e["jobs"]), e.get("cancelled") or "", e.get("regime") or "", tuple(e["moved"]))
                   for e in raw), key=lambda e: (e.month, e.id))


def real(draws: int, perms: int, log: DrawLog | None = None, save=None) -> dict:
    import projects as P
    screening = json.loads(SCREENING.read_text(encoding="utf-8"))
    rule = screening["mpsv"]["outcome_rule"]["rule"]
    if not rule.startswith("amended"):
        raise SystemExit(f"refused: screening says {rule!r}; the outcome of the 26 October 2026 amendment is not available")
    geo = P.load_geo()
    projects = P.load_projects()
    p = P.attach_places(projects, P.places_table(projects, geo))
    raw_events, _ = P.build_events(p, geo, P.boundary_districts(geo=geo))
    wide = load_panel()
    drop_idx = [y * 12 + m - 1 for y, m in (map(int, k.split("-")) for k in screening["mpsv"]["outcome_rule"]["months_dropped"])]
    wide.loc[wide.index.isin(drop_idx)] = np.nan
    events = to_events(raw_events)
    unknown = {u for ev in events for u in (ev.treated, *ev.comparisons)} - set(wide.columns)
    if unknown:  # a code mismatch would drop events silently as "missing year"
        raise SystemExit(f"refused: district codes of the events are not in the MPSV files: {sorted(unknown)[:5]}")
    import population
    districts = sorted({u for ev in events for u in (ev.treated, *ev.comparisons)})
    pop = population.load(districts, FIRST_MONTH, LAST_MONTH)  # Q3 denominator only; population is not an outcome
    panels = [sp for ev in events if (sp := sub_panel(wide, ev, pop=pop))]
    no_pop = [sp.event.id for sp in panels if not (np.isfinite(sp.pop_pre) and sp.pop_pre > 0)]
    if no_pop:  # Q3 would quietly average over fewer events
        raise SystemExit(f"refused: no ČSÚ population for year -1 of events {no_pop[:5]}")
    res = {"rule": rule, "events_used": [sp.event.id for sp in panels],
           "events_dropped_missing_year": [ev.id for ev in events if ev.id not in {sp.event.id for sp in panels}],
           "comparison_weight_total": comparison_weights(panels),
           "primary": run(panels, draws, perms, log=log, name="primary")}
    if save:
        save(res)
    res["checks"] = checks(wide, events, panels, draws=draws, perms=perms,
                           all_districts=[d for d in geo.districts if d != P.PRAGUE], regions=geo.district_kraj, log=log,
                           pop=pop,
                           save=(lambda c: save(res | {"checks": c})) if save else None)
    return res


def jsonable(o):
    """Missing numbers as null: JSON has no NaN."""
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    return o


def comparison_weights(panels: list[SubPanel]) -> dict[str, float]:
    """§4: the total weight a district carries as a comparison across events."""
    tot: dict[str, float] = {}
    for sp in panels:
        for u in sp.units[1:]:
            tot[u] = tot.get(u, 0.0) + 1.0 / (len(sp.units) - 1)
    return dict(sorted(tot.items(), key=lambda kv: -kv[1]))


def demo_panel(n_events: int = 24, n_districts: int = 40, effect: float = -0.3, noise: float = 0.2,
               seed: int = 1) -> tuple[pd.DataFrame, list[Event]]:
    """Made-up monthly panel and events, for --demo and the tests; no real data involved."""
    rng = np.random.default_rng(seed)
    months = np.arange(FIRST_MONTH, LAST_MONTH + 1)
    districts = [f"D{i:02d}" for i in range(n_districts)]
    base = rng.normal(6, 2, n_districts)
    trend = np.cumsum(rng.normal(0, 0.05, len(months)))
    y = base[None, :] + trend[:, None] + rng.normal(0, noise, (len(months), n_districts))
    events = []
    for e in range(n_events):
        t = e % n_districts
        m0 = int(rng.integers(2006 * 12 + 6, 2021 * 12 + 1))
        comps = tuple(d for i, d in enumerate(districts) if i != t and (i + e) % 3)
        events.append(Event(f"E{e:02d}", districts[t], m0, comps, jobs=float(rng.integers(300, 2000))))
        after = months >= m0
        y[after, t] += effect
    return pd.DataFrame(y, index=months, columns=districts), events


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unblind", action="store_true", help="run on the real MPSV outcome (design §4)")
    ap.add_argument("--demo", action="store_true", help="run on a made-up panel")
    ap.add_argument("--draws", type=int, default=DRAWS)
    a = ap.parse_args()
    if a.demo:
        wide, events = demo_panel()
        panels = [sp for ev in events if (sp := sub_panel(wide, ev))]
        print(json.dumps(run(panels, a.draws, a.draws), indent=1, default=float))
        return
    if not a.unblind:
        raise SystemExit("refused: estimate.py reads the real outcome only with --unblind (use --demo for made-up data)")
    if a.draws != DRAWS:
        raise SystemExit(f"refused: --draws is for --demo; the registered run uses {DRAWS} draws and permutations")
    save = lambda res: OUT.write_text(json.dumps(jsonable(res), indent=1, ensure_ascii=False, allow_nan=False) + "\n",
                                      encoding="utf-8")
    save(real(DRAWS, DRAWS, DrawLog(DRAW_LOG), save))
    print("written", OUT)


if __name__ == "__main__":
    main()
