"""Estimates of the investment incentives study (design §4, §6, §7): the stacked weighted difference in differences,
Q1, Q2, Q3, the pre-path difference, the district bootstrap with clones, randomisation inference, the minimum rule,
the label, and checks 1-11.

Frozen with tests on made-up panels (test_incentives.py). On real MPSV data it runs only when asked with --unblind,
and only if the screening (docs/research/incentives-screening.json) names an outcome rule of §2 that can be computed.
Writes docs/research/incentives-results.json.

    nice -n 20 uv run --no-project --with pandas --with numpy python -I tools/incentives/estimate.py --demo
    nice -n 20 uv run --no-project --with pandas --with numpy python -I tools/incentives/estimate.py --unblind
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import MPSV_DIR, ROOT

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
CRISIS = (2009 * 12, 2009 * 12 + 11)
COVID = (2020 * 12, 2021 * 12 + 11)
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


@dataclass
class SubPanel:
    """One event's yearly means: rows are districts (treated first), columns the event years kept."""
    event: Event
    units: list[str]
    years: list[int]
    y: np.ndarray  # units × years
    pop_pre: float = float("nan")  # treated district's population 15-64, mean of year -1
    control: np.ndarray | None = None  # per unit, for check 11
    extra: dict = field(default_factory=dict)


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

def clone_rows(sp: SubPanel, counts: dict[str, int]) -> np.ndarray:
    """Rows of a sub-panel after a district bootstrap draw: a district drawn k times enters as k copies."""
    return np.array([i for i, u in enumerate(sp.units) for _ in range(counts.get(u, 0))], dtype=int)


def bootstrap(panels: list[SubPanel], draws: int = DRAWS, seed: int = SEED_BOOT, years: tuple[int, ...] = YEARS,
              with_control: bool = False, stat=None) -> dict:
    """§4 intervals: whole districts drawn with replacement from every district in the stacked panel; n_e counted on
    the drawn comparison copies; an event with no treated or no comparison copy is absent; empty draws are redrawn."""
    stat = stat or (lambda beta, den: stats_of(beta, den))
    rng = np.random.default_rng(seed)
    universe = sorted({u for sp in panels for u in sp.units})
    out, redrawn, n_events = [], 0, []
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
            continue
        beta = fit(designs, years, with_control)
        out.append(stat(beta, q3_denominator(kept, tcounts)))
        n_events.append(len(designs))
    df = pd.DataFrame(out)
    return {"draws": df, "redrawn": redrawn, "events_per_draw_mean": float(np.mean(n_events))}


def interval(x: pd.Series, level: float) -> list[float]:
    """Percentile interval of the bootstrap draws."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not x.size:
        return [float("nan"), float("nan")]
    a = (1 - level) / 2
    return [float(np.quantile(x, a)), float(np.quantile(x, 1 - a))]


def permutation_p(panels: list[SubPanel], observed: float, perms: int = DRAWS, seed: int = SEED_PERM,
                  years: tuple[int, ...] = YEARS, pools: list[np.ndarray] | None = None,
                  statistic=q1, with_control: bool = False) -> dict:
    """§4 randomisation inference: per event one district of its pool (comparisons plus the true treated) drawn to
    stand as treated, the others as comparisons with weight 1/n_e; p = share of permutations with |Q1| ≥ observed."""
    rng = np.random.default_rng(seed)
    vals = np.empty(perms)
    for b in range(perms):
        designs = []
        for i, sp in enumerate(panels):
            pool = np.arange(len(sp.units)) if pools is None else pools[i]
            t = int(pool[rng.integers(0, len(pool))])
            d = design_of(sp, pool, treated_row=t)
            if d is not None:
                designs.append(d)
        vals[b] = statistic(fit(designs, years, with_control))
    p = float(np.mean(np.abs(vals) >= abs(observed) - TOL))
    return {"p": p, "perms": perms}


# ---------- labels ----------

def label(q1_est: float, ci90: list[float], ci95: list[float], p: float, pre_ci95: list[float],
          minimum_met: bool = True, descriptive: bool = False) -> str | None:
    """§6, the first that holds; §4 minimum rule removes labels 1-3; a descriptive study has no label."""
    if descriptive:
        return None
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
        labelled: bool = True, descriptive: bool = False) -> dict:
    """Point estimate, bootstrap intervals and randomisation p of Q = mean(β post) − mean(β pre); with the primary
    years and reference also Q2, Q3, Q1 against year −1, the minimum rule and the label."""
    designs = [d for d in (design_of(sp) for sp in panels) if d is not None]
    beta = fit(designs, years, with_control)
    stat = (lambda b, den: {"q": q1(b, post, pre), "pre_diff": b[-1] - b[-2],
                            **{f"beta_{k}": b[k] for k in years}} | stats_of(b, den))
    point = stat(beta, q3_denominator(panels))
    boot = bootstrap(panels, draws, SEED_BOOT, years, with_control, stat)
    d = boot["draws"]
    ri = permutation_p(panels, point["q"], perms, SEED_PERM, years, None, lambda b: q1(b, post, pre), with_control)
    res = {
        "n_events": len(panels), "n_treated_districts": len({sp.event.treated for sp in panels}),
        "estimate": point["q"], "ci90": interval(d["q"], 0.90), "ci95": interval(d["q"], 0.95),
        "p_randomisation": ri["p"],
        "pre_diff": point["pre_diff"], "pre_diff_ci90": interval(d["pre_diff"], 0.90),
        "pre_diff_ci95": interval(d["pre_diff"], 0.95),
        "beta": {str(k): point[f"beta_{k}"] for k in years},
        "beta_ci95": {str(k): interval(d[f"beta_{k}"], 0.95) for k in years if k != REF},
        "bootstrap_redrawn": boot["redrawn"], "draws": draws, "perms": perms,
    }
    if years == YEARS and post == POST and pre == PRE:
        res["q2"] = {str(k): {"est": point[f"q2_y{k}"], "ci95": interval(d[f"q2_y{k}"], 0.95)} for k in (0, 1, 2, 3)}
        res["q3"] = {"est": point["q3"], "ci90": interval(d["q3"], 0.90), "denominator": q3_denominator(panels)}
        res["q1_ref_minus1"] = {"est": point["q1_ref_minus1"], "ci95": interval(d["q1_ref_minus1"], 0.95)}
        res["width90"] = res["ci90"][1] - res["ci90"][0]
        res["minimum_met"] = minimum_met(panels)
        res["label"] = label(res["estimate"], res["ci90"], res["ci95"], res["p_randomisation"],
                             res["pre_diff_ci95"], res["minimum_met"], descriptive) if labelled else None
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


def checks(wide: pd.DataFrame, events: list[Event], panels: list[SubPanel], *, draws: int, perms: int,
           pop: pd.DataFrame | None, boundary: dict[str, list[str]], all_districts: list[str],
           regions: dict[str, str], events_put_back: list[Event] | None = None) -> dict:
    out = {}
    by_id = {sp.event.id: sp for sp in panels}

    def go(sel: list[SubPanel], **kw) -> dict:
        return run(sel, draws, perms, labelled=False, **kw) if sel else {"n_events": 0}

    for thr in (500, 1000):
        out[f"1_jobs_{thr}"] = go([sp for sp in panels if sp.event.jobs >= thr])
    if panels:
        top = max(panels, key=lambda sp: (sp.event.jobs, -sp.event.month))
        out["1_without_largest"] = go([sp for sp in panels if sp is not top]) | {"left_out": top.event.id}
    out["2_without_cancelled_or_unverified"] = go([sp for sp in panels if sp.event.cancelled not in ("ANO", "ověřit")])
    same_region = [r for sp in panels
                   if (r := restrict_pool(sp, {u for u in sp.units if regions.get(u) == regions.get(sp.event.treated)}))]
    out["3_same_region"] = go(same_region)
    terc = []
    for sp in panels:
        base = baseline_means(wide, sp.event, all_districts)
        r = restrict_pool(sp, tercile_pool(sp, base))
        if r:
            terc.append(r)
    out["4_same_tercile"] = go(terc)
    out["5_without_2009_2020_21"] = go([sp for sp in panels if not covers(sp.event, *CRISIS)
                                        and not covers(sp.event, *COVID)]) | {"labels": "none (design §7.5)"}
    moved = set().union(*boundary.values()) if boundary else set()
    out["6_without_boundary_districts"] = go([r for sp in panels if sp.event.treated not in moved
                                              and (r := restrict_pool(sp, set(sp.units) - moved))])
    if events_put_back:
        out["6_boundary_districts_put_back"] = go([sp for ev in events_put_back if (sp := sub_panel(wide, ev, pop=pop))])
    long = [sp for ev in events if ev.month <= 2019 * 12 + 11
            if (sp := sub_panel(wide, ev, years=(-2, -1, 0, 1, 2, 3, 4, 5), required=YEARS))]
    out["7_years_1_to_5"] = go(long, years=(-2, -1, 0, 1, 2, 3, 4, 5), post=(1, 2, 3, 4, 5))
    out["8_statutory_regime_only"] = go([sp for sp in panels if sp.event.regime == "Zákonná pobídka"])
    plac, left = [], 0
    for ev in events:
        if ev.month - 48 < FIRST_MONTH:
            left += 1
            continue
        sp = sub_panel(wide, replace(ev, month=ev.month - 24), years=(-2, -1, 0, 1), required=(-2, -1, 0, 1))
        if sp:
            plac.append(sp)
    out["9_placebo_two_years_earlier"] = go(plac, years=(-2, -1, 0, 1), post=(0, 1)) | {"left_out_before_2004_07": left}
    out["10_reference_year_minus1"] = go(panels, pre=(-1,))
    ctl = [sp for ev in events if ev.month - 36 >= FIRST_MONTH and ev.id in by_id
           if (sp := sub_panel(wide, ev, control_years=(-3, -2)))]
    out["11_control_change_minus3_to_minus2"] = go(ctl, with_control=True)
    return out


# ---------- real data (refused unless --unblind) ----------

def load_panel(rule: str, mpsv_dir: Path = MPSV_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monthly outcome and population 15-64, months × districts, from the MPSV files, by the rule of §2."""
    from fetch import months, mpsv_name
    num = "uchazeciOZamestnaniUoZ" if rule.startswith("fallback") else "dosazitelniUchazeci15_64"
    rows = []
    for y, m in months():
        f = mpsv_dir / mpsv_name(y, m)
        if not f.exists():
            continue
        for it in json.loads(f.read_text(encoding="utf-8"))["polozky"]:
            rows.append({"month": y * 12 + m - 1, "district": it["okres"].split("/")[-1],
                         "num": it.get(num), "pop": it.get("celkemObyvatelstvo15_64")})
    d = pd.DataFrame(rows)
    d["y"] = 100 * d["num"] / d["pop"]
    if rule.startswith("descriptive"):
        d = d[d["month"] >= 2013 * 12]
    return d.pivot(index="month", columns="district", values="y"), d.pivot(index="month", columns="district", values="pop")


def to_events(raw: list[dict]) -> list[Event]:
    return sorted((Event(str(e["id_projekt"]), e["district"], int(e["month"]), tuple(e["comparisons"]),
                         float(e["jobs"]), e.get("cancelled") or "", e.get("regime") or "")
                   for e in raw), key=lambda e: (e.month, e.id))


def real(draws: int, perms: int) -> dict:
    import projects as P
    screening = json.loads(SCREENING.read_text(encoding="utf-8"))
    rule = screening["mpsv"]["outcome_rule"]["rule"]
    if rule.startswith("none"):
        raise SystemExit(f"refused: screening says {rule!r}; the outcome cannot be computed as registered")
    geo = P.load_geo()
    projects = P.load_projects()
    p = P.attach_places(projects, P.places_table(projects, geo))
    bounds = P.boundary_districts(geo=geo)
    kw = {}
    if rule.startswith("descriptive"):
        import datetime as dt
        kw = {"first": dt.date(2015, 1, 1), "last": dt.date(2021, 12, 31)}
    raw_events, _ = P.build_events(p, geo, bounds, **kw)
    no_bounds, _ = P.build_events(p, geo, {k: [] for k in bounds}, **kw)
    wide, pop = load_panel(rule)
    dropped_months = set(screening["mpsv"]["outcome_rule"]["months_dropped"])
    drop_idx = [y * 12 + m - 1 for y, m in (map(int, k.split("-")) for k in dropped_months)]
    wide.loc[wide.index.isin(drop_idx)] = np.nan
    events = to_events(raw_events)
    panels = [sp for ev in events if (sp := sub_panel(wide, ev, pop=pop))]
    descriptive = rule.startswith("descriptive")
    res = {"rule": rule, "events_used": [sp.event.id for sp in panels],
           "events_dropped_missing_year": [ev.id for ev in events if ev.id not in {sp.event.id for sp in panels}],
           "comparison_weight_total": comparison_weights(panels),
           "primary": run(panels, draws, perms, descriptive=descriptive)}
    res["checks"] = checks(wide, events, panels, draws=draws, perms=perms, pop=pop, boundary=bounds,
                           all_districts=[d for d in geo.districts if d != P.PRAGUE], regions=geo.district_kraj,
                           events_put_back=to_events(no_bounds))
    return res


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
    res = real(a.draws, a.draws)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()
