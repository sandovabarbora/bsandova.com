"""Estimates of the bypass accidents study (design §4, §6, §7): the Poisson extended two-way fixed-effects model of
town-year injury accidents, the Q1/Q2 ratios weighted by treated town-years, the predicted changes in accidents per
town and year, the offset share, pre-trend leads and placebo, the bypass-level bootstrap, the labels and the checks.

Everything below `main` works on any town table and count table; the tests feed it made-up panels. On real data it
runs only with `--stage A --headline-fixed` (stage A is the registered headline, change log of 16 October 2026);
stage B is not part of the study and is refused. Writes docs/research/bypass-results-a.json.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with pandas --with numpy \
        --with pyarrow --with statsmodels --with scipy python -I tools/bypass/estimate.py --stage A --headline-fixed
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import towns as T  # noqa: E402

ROOT = T.ROOT
DESIGN = ROOT / "docs/research/bypass-design.md"
ACCIDENTS = ROOT / "tools/data/bypass/accidents.parquet"
OUT = ROOT / "docs/research/bypass-results-a.json"
DRAWS_LOG = ROOT / "tools/data/bypass/bootstrap-draws.jsonl"
SEED, DRAWS = 20261015, 2000
POST = (1, 2, 3)
MIN_COMPARISONS = 15
MIN_TREATED = 30
MIN_LEAD_TOWNS = 20
NEAR_ZERO = 0.1
NOT_DEFINED_SHARE = 0.05
CAVEAT = "with differing trends before construction"


@dataclass(frozen=True)
class Spec:
    """One fit: the outcome column and how the panel is built (§4 primary; §7 checks change one field)."""
    outcome: str = "q1"
    post: tuple[int, ...] = POST
    event_study: bool = False
    drop_years: tuple[int, ...] = ()
    opening_dose: bool = False
    trends: bool = False
    leads: bool = False


@dataclass
class Fit:
    est: float = np.nan
    delta: float = np.nan
    beta: dict = field(default_factory=dict)
    weights: dict = field(default_factory=dict)
    dropped_zero: list = field(default_factory=list)
    thin_cells: dict = field(default_factory=dict)
    converged: bool = False
    separated: list = field(default_factory=list)
    post_towns: dict = field(default_factory=dict)
    leads: dict = field(default_factory=dict)
    n_treated: int = 0
    n_obs: int = 0
    ok: bool = False


# ---------------------------------------------------------------- panel

def event_rows(towns: pd.DataFrame, years: range, spec: Spec) -> pd.DataFrame:
    """Town-years in the model with their event time: comparison towns before censoring, treated towns in every year
    but the opening year (kept with a dose in check 8)."""
    rows = []
    for t in towns.itertuples():
        for y in years:
            if y in spec.drop_years:
                continue
            if t.role == "comparison":
                if y <= t.last_year:
                    rows.append((t.town, y, "comparison", None, 0.0))
                continue
            if y < t.start_year:
                rows.append((t.town, y, "pre", y - t.start_year, 0.0))
            elif y < t.open_year:
                rows.append((t.town, y, "construction", t.open_year - y, 0.0))
            elif y == t.open_year:
                if spec.opening_dose:
                    m = t.open_month if pd.notna(t.open_month) else 7
                    rows.append((t.town, y, "opening", 0, (13 - m) / 12))
            else:
                rows.append((t.town, y, "post", y - t.open_year, 0.0))
    p = pd.DataFrame(rows, columns=["town", "year", "phase", "k", "dose"])
    return p.merge(towns[["town", "cluster", "role", "cohort", "open_year"]], on="town", how="left")


def comparisons_by_year(p: pd.DataFrame) -> dict[int, int]:
    serving = p[p["phase"].isin(["comparison", "pre"])]
    return serving.groupby("year")["town"].nunique().to_dict()


def indicators(p: pd.DataFrame, spec: Spec) -> tuple[pd.DataFrame, dict]:
    """Cohort × construction-year and cohort × post-year columns; post cells in a year with fewer than 15 comparison
    towns get their own column and are left out of Q1/Q2 (§2). Check 4 (`event_study`) instead gives every pre- and
    construction year its own cohort × event-time column, with the year before opening as the reference."""
    cols, thin = {}, {}
    serving = comparisons_by_year(p)
    for i, r in enumerate(p.itertuples()):
        k = int(r.k) if pd.notna(r.k) else None
        if spec.event_study and r.phase in ("pre", "construction"):
            e = int(r.year) - int(r.open_year)
            if e != -1:
                cols.setdefault(f"e|{r.cohort}|{e}", {})[i] = 1.0
        elif r.phase == "construction":
            cols.setdefault(f"c|{r.cohort}|{k}", {})[i] = 1.0
        elif r.phase == "post":
            if serving.get(r.year, 0) < MIN_COMPARISONS:
                name = f"x|{r.cohort}|{k}|{r.year}"
                thin[name] = serving.get(r.year, 0)
            else:
                name = f"p|{r.cohort}|{k}"
            cols.setdefault(name, {})[i] = 1.0
        elif r.phase == "opening":
            cols.setdefault(f"p|{r.cohort}|1", {})[i] = r.dose
            cols.setdefault(f"c|{r.cohort}|1", {})[i] = 1 - r.dose
        elif r.phase == "pre" and spec.leads:
            name = "lead|-3" if k == -3 else "lead|-2" if k == -2 else "lead|<=-4" if k <= -4 else None
            if name:
                cols.setdefault(name, {})[i] = 1.0
    X = pd.DataFrame({k: pd.Series(v) for k, v in cols.items()}, index=range(len(p))).fillna(0.0)
    return X, thin


def design(p: pd.DataFrame, X: pd.DataFrame) -> np.ndarray:
    town = pd.get_dummies(p["town"], drop_first=False, dtype=float).to_numpy()
    year = pd.get_dummies(p["year"], drop_first=True, dtype=float).to_numpy()
    return np.hstack([town, year, X.to_numpy()])


def separated(y: np.ndarray, X: pd.DataFrame, columns: list[str]) -> list[str]:
    """Columns among `columns` whose observations are all zero: their coefficient runs to minus infinity."""
    return [c for c in columns if c in X.columns and y[X[c].to_numpy() != 0].sum() == 0]


def poisson(y: np.ndarray, D: np.ndarray, offset: np.ndarray | None = None, groups: np.ndarray | None = None):
    import statsmodels.api as sm
    model = sm.GLM(y, D, family=sm.families.Poisson(), offset=offset)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if groups is not None:
            return model.fit(maxiter=200, tol=1e-10, cov_type="cluster", cov_kwds={"groups": groups})
        return model.fit(maxiter=200, tol=1e-10)


def trend_offset(p: pd.DataFrame, y: np.ndarray, X: pd.DataFrame) -> np.ndarray:
    """Check 9: town-specific linear trends fitted on untreated town-years (comparison and pre-construction) for
    treated towns with at least three pre-construction years, then carried into every year of those towns."""
    pre_n = p[p["phase"] == "pre"].groupby("town").size()
    trended = sorted(pre_n[pre_n >= 3].index)
    base = p["phase"].isin(["comparison", "pre"]).to_numpy()
    q = p[base].reset_index(drop=True)
    t0 = q["year"] - q["year"].min()
    tr = np.column_stack([((q["town"] == tw) * t0).to_numpy(float) for tw in trended]) if trended else np.empty((len(q), 0))
    res = poisson(y[base], np.hstack([design(q, pd.DataFrame(index=q.index)), tr]))
    gamma = dict(zip(trended, res.params[-len(trended):])) if trended else {}
    return np.array([gamma.get(tw, 0.0) * (yr - p["year"].min()) for tw, yr in zip(p["town"], p["year"])])


def fit(towns: pd.DataFrame, counts: pd.DataFrame, years: range, spec: Spec, *, clustered: bool = False) -> Fit:
    """One Poisson ETWFE fit (§4) and its Q1/Q2-type summary over the post years in `spec.post`.

    The town sample is the same for every outcome: towns with no injury accident anywhere in the municipality (q2)
    in their model years are dropped and listed (§4). A kept town with no accident of the outcome itself carries no
    information and is left out of the likelihood, which is the limit its town effect would reach; it still counts in
    the cell weights and, with a predicted change of zero, in the change per town and year, so that the changes inside
    and outside the built-up area add up to the Q2 change."""
    p = event_rows(towns, years, spec)
    need = list(dict.fromkeys([spec.outcome, "q2"]))
    p = p.merge(counts[["town", "year", *need]], on=["town", "year"], how="left")
    missing = p[need].isna().any(axis=1)
    assert not missing.any(), f"town-years missing from the count table: {p.loc[missing, ['town', 'year']].head(3).values.tolist()}"
    total = p.groupby("town")["q2"].sum()
    out = Fit(dropped_zero=sorted(total[total == 0].index.tolist(), key=str))
    p = p[~p["town"].isin(out.dropped_zero)].reset_index(drop=True)
    out.n_treated = int(p.loc[p["role"] == "treated", "town"].nunique())
    out.n_obs = len(p)
    if p.empty or out.n_treated == 0:
        return out
    X, out.thin_cells = indicators(p, spec)
    post_cols = [c for c in X.columns if c.startswith("p|") and int(c.split("|")[2]) in spec.post]
    out.post_towns = {k: int(p.loc[(p["phase"] == "post") & (p["k"] == k), "town"].nunique()) for k in spec.post}
    out.weights = {c: float(X[c].sum()) for c in post_cols}
    used_rows = X[post_cols].sum(axis=1).to_numpy() > 0 if post_cols else np.zeros(len(p), bool)

    y_all = p[spec.outcome].to_numpy(float)
    informative = (p.groupby("town")[spec.outcome].transform("sum") > 0).to_numpy()
    checked = post_cols + [c for c in X.columns if c.startswith(("c|", "e|", "lead|"))]
    out.separated = separated(y_all[informative], X[informative], checked)
    # rows of a separated cell that is not reported (thin years, post years outside spec.post) carry no information
    idle = [c for c in X.columns if c not in checked and y_all[informative & (X[c].to_numpy() != 0)].sum() == 0]
    keep = informative & ~(X[idle].to_numpy().sum(axis=1) > 0) if idle else informative
    q, Xq, y = p[keep].reset_index(drop=True), X[keep].reset_index(drop=True), y_all[keep]
    Xq = Xq.loc[:, Xq.abs().sum() > 0]
    offset = trend_offset(q, y, Xq) if spec.trends else None
    D = design(q, Xq)
    try:
        res = poisson(y, D, offset, q["cluster"].to_numpy() if clustered else None)
    except (np.linalg.LinAlgError, ValueError):
        return out
    out.converged = bool(res.converged) and bool(np.all(np.isfinite(res.params)))
    k = D.shape[1] - Xq.shape[1]
    beta = dict(zip(Xq.columns, res.params[k:]))
    out.beta = {c: float(b) for c, b in beta.items()}
    if spec.leads:
        out.leads = lead_test(res, Xq, k, q)
    out.ok = out.converged and not out.separated
    w = out.weights
    if not post_cols or sum(w.values()) == 0 or any(c not in beta for c in post_cols):
        return out
    out.est = float(np.exp(sum(w[c] * beta[c] for c in post_cols) / sum(w.values())) - 1)
    mu = np.asarray(res.fittedvalues)
    cols_q = [c for c in post_cols if c in Xq.columns]
    eff = (Xq[cols_q].to_numpy() * np.array([beta[c] for c in cols_q])).sum(axis=1)
    hit = Xq[cols_q].sum(axis=1).to_numpy() > 0
    out.delta = float((mu[hit] * (1 - np.exp(-eff[hit]))).sum() / used_rows.sum())
    return out


def lead_test(res, X: pd.DataFrame, k: int, p: pd.DataFrame) -> dict:
    """§4 pre-trends: leads −3 and −2 against the last pre-construction year, Wald test on those that exist."""
    from scipy import stats
    names = [c for c in ("lead|-3", "lead|-2") if c in X.columns and X[c].sum() > 0]
    towns_per = {c: int(p.loc[X[c].to_numpy() > 0, "town"].nunique()) if c in X.columns else 0
                 for c in ("lead|-3", "lead|-2")}
    contributing = p.loc[X[[c for c in ("lead|-3", "lead|-2") if c in X.columns]].sum(axis=1).to_numpy() > 0, "town"]
    out = {"towns_per_lead": towns_per, "towns_any_lead": int(contributing.nunique()),
           "coefficients": {c: float(res.params[k + list(X.columns).index(c)]) for c in names}}
    if names:
        idx = [k + list(X.columns).index(c) for c in names]
        b, V = res.params[idx], res.cov_params()[np.ix_(idx, idx)]
        wald = float(b @ np.linalg.pinv(V) @ b)
        out.update({"wald": wald, "df": len(names), "p": float(stats.chi2.sf(wald, len(names)))})
    else:
        out.update({"wald": None, "df": 0, "p": None})
    out["uninformative"] = out["towns_any_lead"] < MIN_LEAD_TOWNS
    out["rejects_5pct"] = bool(out["p"] is not None and out["p"] < 0.05)
    return out


def placebo(towns: pd.DataFrame, counts: pd.DataFrame, years: range, outcome: str = "q1") -> dict:
    """§4: construction start moved two years earlier, pre-construction years only; one pooled indicator for the
    two placebo years, town and year effects, intervals clustered by bypass."""
    p = event_rows(towns, years, Spec(outcome=outcome))
    p = p[p["phase"].isin(["comparison", "pre"])].reset_index(drop=True)
    p = p.merge(counts[["town", "year", outcome]], on=["town", "year"], how="left").fillna({outcome: 0})
    total = p.groupby("town")[outcome].sum()
    p = p[p["town"].isin(total[total > 0].index)].reset_index(drop=True)
    fake = ((p["phase"] == "pre") & (p["k"] >= -2)).to_numpy(float)
    has_before = p[(p["phase"] == "pre") & (p["k"] < -2)]["town"].nunique()
    if fake.sum() == 0 or has_before == 0:
        return {"run": False, "reason": "no treated town has a year before its placebo start"}
    res = poisson(p[outcome].to_numpy(float), np.hstack([design(p, pd.DataFrame(index=p.index)), fake[:, None]]),
                  groups=p["cluster"].to_numpy())
    b, se = float(res.params[-1]), float(res.bse[-1])
    return {"run": True, "est": float(np.exp(b) - 1), "ci95": [float(np.exp(b - 1.96 * se) - 1), float(np.exp(b + 1.96 * se) - 1)],
            "treated_towns_with_earlier_years": int(has_before), "interval": "cluster-robust by bypass"}


# ---------------------------------------------------------------- bootstrap

def resample(towns: pd.DataFrame, counts: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """§4: whole bypasses (all their towns and years), treated and comparison drawn separately."""
    is_t = towns.groupby("cluster")["role"].agg(lambda r: (r == "treated").any())
    parts_t, parts_c = [], []
    for flag, parts in ((True, parts_t), (False, parts_c)):
        ids = is_t.index[is_t == flag].to_numpy()
        if len(ids):
            parts.extend(rng.choice(ids, size=len(ids), replace=True))
    tw, ct = [], []
    for j, cl in enumerate(parts_t + parts_c):
        t = towns[towns["cluster"] == cl].copy()
        new = {old: f"{old}#{j}" for old in t["town"]}
        t["town"] = t["town"].map(new)
        t["cluster"] = f"{cl}#{j}"
        c = counts[counts["town"].isin(new)].copy()
        c["town"] = c["town"].map(new)
        tw.append(t)
        ct.append(c)
    return pd.concat(tw, ignore_index=True), pd.concat(ct, ignore_index=True)


def bootstrap(towns, counts, years, specs: dict[str, Spec], draws: int = DRAWS, seed: int = SEED,
              gate: tuple[str, ...] = ("q1", "q2"), extra=None, log: Path | None = None, name: str = "") -> dict:
    """Draws of every spec; a draw is redrawn when a gate spec (Q1, Q2) has a post year 1–3 without a treated town,
    has a separated cell, or does not converge, tallied in that order. Other specs that fail in an accepted draw are
    left missing. Each accepted draw is appended to `log` as it is made, so a crash keeps the draws so far."""
    rng = np.random.default_rng(seed)
    got = {k: {"est": [], "delta": []} for k in specs}
    extras = []
    redrawn = {"no_treated_post_year": 0, "separated": 0, "not_converged": 0}
    sink = log.open("a") if log else None
    try:
        while len(got[next(iter(specs))]["est"]) < draws:
            tw, ct = resample(towns, counts, rng)
            fits, bad = {}, None
            for k in gate:
                f = fit(tw, ct, years, specs[k])
                fits[k] = f
                if any(f.post_towns.get(p, 0) == 0 for p in specs[k].post):
                    bad = "no_treated_post_year"
                elif f.separated:
                    bad = "separated"
                elif not f.converged:
                    bad = "not_converged"
                if bad:
                    break
            if bad:
                redrawn[bad] += 1
                continue
            row = {}
            for k, s in specs.items():
                f = fits.get(k) or fit(tw, ct, years, s)
                row[k] = (f.est if f.ok else np.nan, f.delta if f.ok else np.nan)
                got[k]["est"].append(row[k][0])
                got[k]["delta"].append(row[k][1])
            if extra is not None:
                extras.append(extra(tw, ct))
            n = len(got[next(iter(specs))]["est"])
            if sink:
                sink.write(json.dumps({"set": name, "draw": n, "redrawn": redrawn,
                                       **{k: [None if not np.isfinite(v) else v for v in vals] for k, vals in row.items()},
                                       **({"extra": extras[-1]} if extra is not None else {})}) + "\n")
                sink.flush()
            if n % 100 == 0:
                print(f"{name or 'bootstrap'}: {n}/{draws} draws, redrawn {redrawn}", file=sys.stderr, flush=True)
    finally:
        if sink:
            sink.close()
    return {"draws": got, "redrawn": redrawn, "extra": extras}


def interval(values, level: float) -> list[float] | None:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return None
    a = (1 - level) / 2
    return [float(np.quantile(v, a)), float(np.quantile(v, 1 - a))]


def summary(f: Fit, draws: dict) -> dict:
    return {"est": f.est, "ci90": interval(draws["est"], 0.90), "ci95": interval(draws["est"], 0.95),
            "delta_per_town_year": f.delta, "delta_ci95": interval(draws["delta"], 0.95),
            "treated_towns": f.n_treated, "draws_missing": int(np.sum(~np.isfinite(draws["est"])))}


# ---------------------------------------------------------------- §4 offset, §5 power, §6 labels

def offset_share(q1: dict, q2: dict, d1: list, d2: list) -> dict:
    """1 − ΔQ2/ΔQ1 in accidents per town and year; only if Q1's 95 % interval excludes zero, and 'not defined' if more
    than 5 % of draws have |ΔQ1| below 0.1."""
    lo, hi = q1["ci95"] or (np.nan, np.nan)
    if not (lo > 0 or hi < 0):
        return {"reported": False, "reason": "Q1's 95 % interval includes zero"}
    d1, d2 = np.asarray(d1, float), np.asarray(d2, float)
    near = float(np.mean(np.abs(d1[np.isfinite(d1)]) < NEAR_ZERO))
    if near > NOT_DEFINED_SHARE:
        return {"reported": True, "value": "not defined", "share_draws_near_zero": near}
    share = 1 - d2 / d1
    return {"reported": True, "value": float(1 - q2["delta_per_town_year"] / q1["delta_per_town_year"]),
            "ci90": interval(share, 0.90), "ci95": interval(share, 0.95), "share_draws_near_zero": near}


def power(r: dict) -> dict:
    """§5: the width of the 90 % interval and the smallest change it could tell from zero (half the 95 % width)."""
    if not r.get("ci90") or not r.get("ci95"):
        return {}
    return {"ci90_width": r["ci90"][1] - r["ci90"][0], "smallest_detectable_change": (r["ci95"][1] - r["ci95"][0]) / 2}


def label(est: float, ci95, ci90, *, differing_trends: bool, minimum_met: bool, stage: str) -> str:
    """§6, in order. Under stage A the pre-trend test is taken as uninformative: labels 1 and 2 carry the caveat and
    label 3 cannot be issued. Below the minimum of treated towns, labels 1–3 are not given."""
    if not (np.isfinite(est) and ci95 and ci90 and np.all(np.isfinite(ci95)) and np.all(np.isfinite(ci90))):
        return "not estimated"
    differing = differing_trends or stage == "A"
    lo95, hi95 = ci95
    lo90, hi90 = ci90
    if minimum_met:
        if hi95 < 0 and est <= -0.10:
            return "fewer accidents after opening" + (f" {CAVEAT}" if differing else "")
        if lo95 > 0 and est >= 0.10:
            return "more accidents after opening" + (f" {CAVEAT}" if differing else "")
        if -0.15 <= lo90 and hi90 <= 0.15:
            return "inconclusive" if differing else "no change larger than 15 %"
    if round(hi90 - lo90, 12) > 0.30:
        return "underpowered"
    return "inconclusive"


def sign_sentence(primary: float, by_class: dict[str, float], by_period: dict[str, float] | None = None) -> str | None:
    """§6: checks 13 (and 14, stage B) with an estimate of the opposite sign to the primary; the label stands."""
    opposite = [f"class {k}" for k, v in by_class.items() if np.isfinite(v) and np.sign(v) == -np.sign(primary) != 0]
    opposite += [f"opened {k}" for k, v in (by_period or {}).items() if np.isfinite(v) and np.sign(v) == -np.sign(primary) != 0]
    if not opposite:
        return None
    return ("Taken separately, the estimate for " + " and ".join(opposite)
            + " has the opposite sign to the primary estimate; the label stands.")


# ---------------------------------------------------------------- §7 checks

def callaway_santanna(towns: pd.DataFrame, counts: pd.DataFrame, years: range, outcome: str = "q1",
                      post: tuple[int, ...] = POST) -> float:
    """Check 5: each treated town's change from its last pre-construction year to post years 1–3, less the mean change
    of towns not yet under construction in that year (comparison towns before censoring, treated towns before their
    works), in counts; as a share of the treated towns' pre-construction mean."""
    c = counts.set_index(["town", "year"])[outcome]
    tr = towns[towns["role"] == "treated"]
    att, pre_means = [], []
    for t in tr.itertuples():
        base = t.start_year - 1
        if base not in years or (t.town, base) not in c.index:
            continue
        pre_means.append(np.mean([c.get((t.town, y), 0) for y in years if y < t.start_year]))
        for k in post:
            y = t.open_year + k
            if y not in years:
                continue
            ctrl = towns[((towns["role"] == "comparison") & (towns["last_year"] >= y))
                         | ((towns["role"] == "treated") & (towns["start_year"] > y))]
            ctrl = ctrl[ctrl["town"] != t.town]
            if ctrl.empty:
                continue
            d_ctrl = np.mean([c.get((u, y), 0) - c.get((u, base), 0) for u in ctrl["town"]])
            att.append((c.get((t.town, y), 0) - c.get((t.town, base), 0)) - d_ctrl)
    if not att or not pre_means or np.mean(pre_means) == 0:
        return np.nan
    return float(np.mean(att) / np.mean(pre_means))


def check_specs() -> dict[str, Spec]:
    return {
        "q1": Spec("q1"), "q2": Spec("q2"),
        "1_all_accidents_q1": Spec("q1_all"), "1_all_accidents_q2": Spec("q2_all"),
        "2_killed_seriously_injured_q1": Spec("q1_ksi"), "2_killed_seriously_injured_q2": Spec("q2_ksi"),
        "3_without_2020_2021_q1": Spec("q1", drop_years=(2020, 2021)),
        "4_plain_event_study_q1": Spec("q1", event_study=True),
        "6_post_1_2_q1": Spec("q1", post=(1, 2)), "6_post_1_5_q1": Spec("q1", post=(1, 2, 3, 4, 5)),
        "8_opening_year_dose_q1": Spec("q1", opening_dose=True),
        "9_town_trends_q1": Spec("q1", trends=True),
        "10_old_through_road_q1": Spec("q1_oldroad"),
    }


def subset_checks(towns: pd.DataFrame, counts: pd.DataFrame, years: range) -> dict[str, pd.DataFrame]:
    """Checks that change the set of towns and are bootstrapped on their own: 11 by size, 13 by road class."""
    tr = towns[towns["role"] == "treated"]
    c = counts.set_index(["town", "year"])["q1"]
    pre = {t.town: np.mean([c.get((t.town, y), 0) for y in years if y < t.start_year] or [np.nan]) for t in tr.itertuples()}
    med = float(np.nanmedian(list(pre.values()))) if pre else np.nan
    comp = towns[towns["role"] == "comparison"]
    small = [t for t, v in pre.items() if v <= med]
    out = {"11_smaller_towns": pd.concat([comp, tr[tr["town"].isin(small)]]),
           "11_larger_towns": pd.concat([comp, tr[~tr["town"].isin(small)]])}
    for cls in ("I", "II"):
        out[f"13_class_{cls}"] = pd.concat([comp, tr[tr["road_class"] == cls]])
    return out


def stage_b_only() -> dict:
    return {"run": False, "reason": "stage B is not part of the study (change log, 16 October 2026)"}


# ---------------------------------------------------------------- the whole analysis

def analyse(towns: pd.DataFrame, counts: pd.DataFrame, years: range, *, stage: str = "A", draws: int = DRAWS,
            seed: int = SEED, extra_sets: dict[str, pd.DataFrame] | None = None, minimum_towns: int | None = None,
            log: Path | None = None, q3: dict | None = None) -> dict:
    """§4–§7 on a town table (town, role, cluster, cohort, start_year, open_year, open_month, last_year, road_class)
    and a count table (town, year, outcome columns)."""
    specs = check_specs()
    specs = {k: s for k, s in specs.items() if s.outcome in counts.columns}
    primary = {k: fit(towns, counts, years, s) for k, s in specs.items()}
    leads = fit(towns, counts, years, Spec("q1", leads=True), clustered=True).leads
    boot = bootstrap(towns, counts, years, specs, draws, seed,
                     extra=lambda tw, ct: callaway_santanna(tw, ct, years), log=log, name="primary")
    res = {k: summary(primary[k], boot["draws"][k]) for k in specs}
    n_before_zero = int((towns["role"] == "treated").sum()) if minimum_towns is None else minimum_towns
    minimum_met = n_before_zero >= MIN_TREATED
    leads["uninformative_by_rule"] = stage == "A" or bool(leads.get("uninformative"))
    leads["note"] = "one lead test, on Q1; Q2 reuses it"
    differing = bool(leads["uninformative_by_rule"] or leads.get("rejects_5pct"))

    sub = {}
    for name, tw in {**subset_checks(towns, counts, years), **(extra_sets or {})}.items():
        if (tw["role"] == "treated").sum() == 0:
            sub[name] = {"run": False, "reason": "no treated town"}
            continue
        f = fit(tw, counts, years, Spec("q1"))
        b = bootstrap(tw, counts, years, {"q1": Spec("q1")}, draws, seed, gate=("q1",), log=log, name=name)
        sub[name] = {**summary(f, b["draws"]["q1"]), "redrawn": b["redrawn"]}

    out = {"stage": stage, "years": [years.start, years.stop - 1], "seed": seed, "draws": draws,
           "redrawn": boot["redrawn"], "treated_towns_before_zero_drop": n_before_zero, "minimum_met": minimum_met,
           "pre_trends": leads, "differing_trends": differing,
           "placebo": placebo(towns, counts, years), "questions": {}, "checks": {}}
    for q in ("q1", "q2"):
        r = res[q]
        f = primary[q]
        r.update({"label": label(r["est"], r["ci95"], r["ci90"], differing_trends=differing, minimum_met=minimum_met,
                                 stage=stage),
                  "power": power(r), "cells": {c: {"beta": f.beta[c], "weight": f.weights[c]} for c in f.weights},
                  "treated_towns_per_post_year": f.post_towns, "dropped_no_injury_accident": f.dropped_zero,
                  "thin_year_cells": f.thin_cells, "separated": f.separated, "converged": f.converged})
        out["questions"][q] = r
    out["questions"]["q2"]["change_inside_built_up_per_town_year"] = res["q1"]["delta_per_town_year"]
    outside = np.asarray(boot["draws"]["q2"]["delta"], float) - np.asarray(boot["draws"]["q1"]["delta"], float)
    out["questions"]["q2"]["change_outside_built_up_per_town_year"] = res["q2"]["delta_per_town_year"] - res["q1"]["delta_per_town_year"]
    out["questions"]["q2"]["change_outside_ci95"] = interval(outside, 0.95)
    out["questions"]["q2"]["same_towns_as_q1"] = primary["q1"].dropped_zero == primary["q2"].dropped_zero
    out["offset_share"] = offset_share(res["q1"], res["q2"], boot["draws"]["q1"]["delta"], boot["draws"]["q2"]["delta"])
    out["questions"]["q3"] = q3 or {"run": False, "reason": "no bypass geometry passed"}

    checks = {k: v for k, v in res.items() if k not in ("q1", "q2")}
    if "9_town_trends_q1" in checks:
        checks["9_town_trends_q1"]["shift_against_primary"] = checks["9_town_trends_q1"]["est"] - res["q1"]["est"]
    checks["5_callaway_santanna_q1"] = {"est": callaway_santanna(towns, counts, years),
                                        "ci90": interval(boot["extra"], 0.90), "ci95": interval(boot["extra"], 0.95),
                                        "scale": "share of the treated towns' pre-construction mean"}
    checks.update(sub)
    checks["14_by_opening_period"] = stage_b_only()
    checks["15_without_2015_2016"] = stage_b_only()
    out["checks"] = checks
    by_class = {c: sub.get(f"13_class_{c}", {}).get("est", np.nan) for c in ("I", "II")}
    for q in ("q1",):
        out["questions"][q]["sign_sentence"] = sign_sentence(res[q]["est"], by_class)
    return out


# ---------------------------------------------------------------- real data (guarded)

def headline_is_a() -> bool:
    text = DESIGN.read_text()
    return "the headline stage is therefore **stage A**" in " ".join(text.split())


def real_counts(towns: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """Town-year counts for the selected towns only; run only behind the guard in `main`."""
    a = pd.read_parquet(ACCIDENTS, columns=["year", "injury", "ksi", "built_up", "road", "muni_polygon", "muni"])
    a = a[a["year"].between(T.FIRST_YEAR, T.LAST_YEAR)]
    roads = {t.town: {s.strip() for s in str(t.road).split(",")} for t in towns.itertuples()}
    codes = set(towns["town"])
    inside = a[a["built_up"].fillna(False) & a["muni_polygon"].isin(codes)].copy()
    whole = a[a["muni"].isin(codes)].copy()
    inside["town"], whole["town"] = inside["muni_polygon"].astype(int), whole["muni"].astype(int)
    inside["oldroad"] = [r in roads.get(t, set()) for r, t in zip(inside["road"], inside["town"])]
    cols = {"q1": inside[inside["injury"].fillna(False)], "q1_all": inside, "q1_ksi": inside[inside["ksi"].fillna(False)],
            "q1_oldroad": inside[inside["injury"].fillna(False) & inside["oldroad"]],
            "q2": whole[whole["injury"].fillna(False)], "q2_all": whole, "q2_ksi": whole[whole["ksi"].fillna(False)]}
    grid = pd.MultiIndex.from_product([sorted(codes), range(T.FIRST_YEAR, T.LAST_YEAR + 1)], names=["town", "year"])
    out = pd.DataFrame(index=grid)
    for k, d in cols.items():
        out[k] = d.groupby(["town", "year"]).size().reindex(grid, fill_value=0)
    out["outside"] = out["q2"] - out["q1"]
    return out.reset_index()


def town_table(sel: T.Selection) -> pd.DataFrame:
    t = sel.towns.rename(columns={"code": "town"})
    t["last_year"] = t["last_year"].fillna(T.LAST_YEAR)
    return t


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o


def versions() -> dict:
    import importlib.metadata as md
    return {p: md.version(p) for p in ("numpy", "pandas", "statsmodels", "scipy")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("A", "B"), required=True)
    ap.add_argument("--headline-fixed", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()
    if args.stage == "B":
        sys.exit("stage B is not part of the study (change log, 16 October 2026)")
    if not args.headline_fixed or not headline_is_a():
        sys.exit("refusing to read accident counts: pass --headline-fixed, and the change log must fix stage A")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import screen as S
    b = T.load_list()
    table, _ = S.areas(S.ku_versions(), S.ku_areas(), [f"{y}-01-01" for y in range(T.FIRST_YEAR, T.LAST_YEAR + 2)])
    change = S.area_change(table)
    towns = town_table(T.select(b, change))
    years = range(T.FIRST_YEAR, T.LAST_YEAR + 1)
    planned = town_table(T.select(b, change, planned_only=True))
    wide = town_table(T.select(b, change, classes=("I", "II", "III")))
    counts = real_counts(pd.concat([towns, planned, wide]).drop_duplicates("town"), b)
    extra = {"7_comparison_planned_only": planned, "12_class_III_added": wide}
    log = DRAWS_LOG.with_name(f"{DRAWS_LOG.stem}-{pd.Timestamp.now():%Y%m%dT%H%M%S}.jsonl")
    res = analyse(towns, counts, years, stage="A", draws=args.draws, extra_sets=extra, log=log)
    res["versions"] = versions()
    OUT.write_text(json.dumps(clean(res), indent=1, ensure_ascii=False, default=str))
    for q in ("q1", "q2"):
        r = res["questions"][q]
        print(q, round(r["est"], 4), r["ci95"], r["label"])


if __name__ == "__main__":
    main()
