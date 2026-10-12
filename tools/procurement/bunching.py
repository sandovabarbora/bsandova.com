"""Mass at and just below fixed locations of the contract-price distribution, before and after the change (§5–§8).

Two estimands per location L (design §6.1):
  a(L) = contracts priced at exactly L, per counterfactual contract in the band (0.95 L, L];
  b(L) = excess of contracts strictly inside (0.95 L, L), exact whole millions removed, per counterfactual contract.
The functions take arrays, so the tests run them on made-up data; nothing here reads a file.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.polynomial import legendre
from scipy import sparse

LO, HI, WIDTH = 500_000, 13_500_000, 10_000
N_BINS = (HI - LO) // WIDTH
MILLIONS = np.arange(1, 14) * 1_000_000
DEGREE = 7
SHARE_BELOW = 0.05
SHARE_ABOVE = 0.05

OLD = {"supplies_services": 2_000_000, "works": 6_000_000}
NEW = {"supplies_services": 3_000_000, "works": 9_000_000}
CONTROLS = (4_000_000, 5_000_000, 7_000_000, 8_000_000, 10_000_000, 12_000_000, 13_000_000)
# Proximity-weighted controls (robustness row and the validity gate, §7.1): the nearest usable controls.
NEIGHBOURS = {"new_supplies_services": (4_000_000, 5_000_000), "old_supplies_services": (4_000_000, 5_000_000),
              "new_works": (8_000_000, 10_000_000), "old_works": (5_000_000, 7_000_000)}
GATE_CONTROLS = (4_000_000, 5_000_000, 8_000_000, 10_000_000)
LOW_CONTROLS, HIGH_CONTROLS = (4_000_000, 5_000_000), (10_000_000, 12_000_000, 13_000_000)
EU_CENTRAL = (3_568_000, 3_653_000, 3_494_000, 3_491_000)
EU_SUBCENTRAL = (5_494_000, 5_610_000, 5_401_000, 5_386_000)
SMALL_LOT = (2_054_000, 2_087_000, 1_955_000, 1_995_000)
OTHER = (750_000, 1_000_000, 11_000_000)
VAT_IMAGES = tuple(round(t * 1.21) for t in (*OLD.values(), *NEW.values()))

MARGIN = 0.15
UNDERPOWERED_MDE = 0.25  # = MARGIN / 1.645 × 2.80, rounded down: above it "not supported" is out of reach (§8.1)
MAX_FAILED_SHARE = 0.01  # bootstrap draws with an undefined statistic; above this the run stops (§8.4)
PRIMARY = ("D_new_a", "D_old_a")


def exact_million(values: np.ndarray) -> np.ndarray:
    return np.abs(values - np.round(values / 1_000_000) * 1_000_000) < 0.5


def bin_index(values: np.ndarray) -> np.ndarray:
    """Bin j holds (LO + j·WIDTH, LO + (j+1)·WIDTH]; a value equal to a limit falls in the bin that ends at it."""
    j = np.ceil((np.asarray(values, float) - LO) / WIDTH).astype(np.int64) - 1
    return np.where((j >= 0) & (j < N_BINS), j, -1)


def edges() -> np.ndarray:
    return LO + WIDTH * np.arange(N_BINS + 1)


def window_bins(low: float, high: float) -> np.ndarray:
    """Bins inside (low, high], snapped outward to bin edges."""
    first = int(math.floor((low - LO) / WIDTH))
    last = int(math.ceil((high - LO) / WIDTH))
    return np.arange(max(first, 0), min(last, N_BINS))


def below(point: float, share: float = SHARE_BELOW) -> np.ndarray:
    return window_bins(point * (1 - share), point)


def above(point: float, share: float = SHARE_ABOVE) -> np.ndarray:
    return window_bins(point, point * (1 + share))


@dataclass
class Spec:
    degree: int = DEGREE
    share_below: float = SHARE_BELOW
    control_set: str = "all"  # "all" (primary) or "neighbours"
    exclude_vat_images: bool = False

    def locations(self) -> dict[str, float]:
        locs = {f"old_{k}": v for k, v in OLD.items()} | {f"new_{k}": v for k, v in NEW.items()}
        return locs | {f"control_{c // 1_000_000}M": c for c in CONTROLS}

    def excluded(self) -> np.ndarray:
        mask = np.zeros(N_BINS, bool)
        for p in self.locations().values():
            mask[below(p, self.share_below)] = True
        for t in (*OLD.values(), *NEW.values()):
            mask[above(t)] = True
        for p in (*EU_CENTRAL, *EU_SUBCENTRAL, *SMALL_LOT, *OTHER, *(VAT_IMAGES if self.exclude_vat_images else ())):
            mask[below(p)] = True
        return mask

    def controls_for(self, location: str) -> tuple:
        return NEIGHBOURS[location] if self.control_set == "neighbours" else CONTROLS


def design_matrix(degree: int) -> np.ndarray:
    e = edges()
    mid = np.log((e[:-1] + e[1:]) / 2)
    x = 2 * (mid - mid.min()) / (mid.max() - mid.min()) - 1

    def holds(m: int) -> np.ndarray:
        return (np.floor(e[1:] / m) * m > e[:-1]).astype(float)

    m500, m100, m50 = holds(500_000), holds(100_000), holds(50_000)
    return np.column_stack([legendre.legvander(x, degree), m500, m100 * (1 - m500), m50 * (1 - m100)])


def poisson_fit(y: np.ndarray, X: np.ndarray, iters: int = 100) -> np.ndarray:
    beta = np.zeros(X.shape[1])
    beta[0] = math.log(max(y.mean(), 1e-9))
    for _ in range(iters):
        mu = np.exp(np.clip(X @ beta, -30, 30))
        step = np.linalg.lstsq(X * np.sqrt(mu)[:, None], (y - mu) / np.sqrt(mu), rcond=None)[0]
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            break
    return beta


def excess(open_counts: np.ndarray, exact_counts: np.ndarray, spec: Spec) -> dict[str, float]:
    """open_counts: histogram without contracts at an exact whole million; exact_counts: contracts at 1 … 13 M."""
    X = design_matrix(spec.degree)
    keep = ~spec.excluded()
    fitted = np.exp(X @ poisson_fit(open_counts[keep].astype(float), X[keep]))
    out = {}
    for name, p in spec.locations().items():
        w = below(p, spec.share_below)
        den = float(fitted[w].sum())
        n_exact = float(exact_counts[int(round(p / 1_000_000)) - 1])
        num_b = float((open_counts[w] - fitted[w]).sum())
        out |= {f"a_{name}": n_exact / den, f"b_{name}": num_b / den, f"r_{name}": (n_exact + num_b) / den,
                f"exact_{name}": n_exact, f"numb_{name}": num_b, f"den_{name}": den}
        if not name.startswith("control_"):
            inner, outer = below(p, spec.share_below / 2), np.setdiff1d(w, below(p, spec.share_below / 2))
            out[f"b_inner_{name}"] = float((open_counts[inner] - fitted[inner]).sum() / fitted[inner].sum())
            out[f"b_outer_{name}"] = float((open_counts[outer] - fitted[outer]).sum() / fitted[outer].sum())
    for kind, t in [*((f"old_{k}", v) for k, v in OLD.items()), *((f"new_{k}", v) for k, v in NEW.items())]:
        w = above(t)
        out[f"m_above_{kind}"] = float((open_counts[w] - fitted[w]).sum() / fitted[w].sum())
    return out


def pooled(res: dict, controls: tuple, what: str) -> float:
    names = [f"control_{c // 1_000_000}M" for c in controls]
    num = sum(res[f"{'exact' if what == 'a' else 'numb'}_{n}"] for n in names)
    return num / sum(res[f"den_{n}"] for n in names)


def adjusted(pre: dict, post: dict, loc: str, controls: tuple, what: str, adjust: str) -> tuple[float, float]:
    """Expected post value of the round-number part at loc, from its pre value and the controls; returns
    (expected_post_from_pre, k). For b the adjustment is always additive (§6.2)."""
    c_pre, c_post = pooled(pre, controls, what), pooled(post, controls, what)
    if what == "a" and adjust == "ratio":
        k = c_post / c_pre if c_pre > 0 else float("nan")
        return k * pre[f"{what}_{loc}"], k
    return pre[f"{what}_{loc}"] + (c_post - c_pre), float("nan")


def contrasts(pre: dict, post: dict, spec: Spec, adjust: str) -> dict[str, float]:
    out = {}
    for what in ("a", "b"):
        for kind in OLD:
            new, old = f"new_{kind}", f"old_{kind}"
            exp_new, _ = adjusted(pre, post, new, spec.controls_for(new), what, adjust)
            exp_old, _ = adjusted(pre, post, old, spec.controls_for(old), what, adjust)
            out[f"D_new_{what}_{kind}"] = post[f"{what}_{new}"] - exp_new
            # D_old: how much the old limit's excess fell beyond the round-number change, scaled like D_new.
            out[f"D_old_{what}_{kind}"] = exp_old - post[f"{what}_{old}"]
        out[f"D_new_{what}"] = float(np.mean([out[f"D_new_{what}_{k}"] for k in OLD]))
        out[f"D_old_{what}"] = float(np.mean([out[f"D_old_{what}_{k}"] for k in OLD]))
        for c in CONTROLS:  # §7.1: each control as a 'new limit', adjusted by the other six
            name = f"control_{c // 1_000_000}M"
            exp_c, _ = adjusted(pre, post, name, tuple(o for o in CONTROLS if o != c), what, adjust)
            out[f"placebo_{what}_{name}"] = post[f"{what}_{name}"] - exp_c
        out[f"placebo_{what}_gate_mean"] = float(np.mean([out[f"placebo_{what}_control_{c // 1_000_000}M"]
                                                          for c in GATE_CONTROLS]))
    for what in ("a", "b"):
        out[f"controls_{what}_pre"], out[f"controls_{what}_post"] = pooled(pre, CONTROLS, what), pooled(post, CONTROLS, what)
    k_low = pooled(post, LOW_CONTROLS, "a") / pooled(pre, LOW_CONTROLS, "a") if pooled(pre, LOW_CONTROLS, "a") > 0 else float("nan")
    k_high = pooled(post, HIGH_CONTROLS, "a") / pooled(pre, HIGH_CONTROLS, "a") if pooled(pre, HIGH_CONTROLS, "a") > 0 else float("nan")
    out |= {"k_low": k_low, "k_high": k_high, "k_low_minus_high": k_low - k_high}
    return out


def choose_adjust(values: np.ndarray, period: np.ndarray, min_pre: int = 200, min_post: int = 50) -> str:
    """§6.2, decided once on the full sample from counts at the control millions only (never at a limit):
    ratio if at least min_pre (pre) and min_post (post) contracts sit at exactly a control million."""
    at_controls = np.isin(np.round(values), np.array(CONTROLS, float)) & exact_million(values)
    n_pre, n_post = int((at_controls & (period == "pre")).sum()), int((at_controls & (period == "post")).sum())
    return "ratio" if n_pre >= min_pre and n_post >= min_post else "difference"


def matrices(values, authority, period):
    ids, a = np.unique(authority, return_inverse=True)
    ex = exact_million(values)
    j = bin_index(values)
    m_idx = np.round(values / 1_000_000).astype(np.int64) - 1
    mats = {}
    for p in ("pre", "post"):
        o = (period == p) & ~ex & (j >= 0)
        e = (period == p) & ex & (m_idx >= 0) & (m_idx < len(MILLIONS))
        mats[p] = (sparse.csr_matrix((np.ones(o.sum()), (a[o], j[o])), shape=(len(ids), N_BINS)),
                   sparse.csr_matrix((np.ones(e.sum()), (a[e], m_idx[e])), shape=(len(ids), len(MILLIONS))))
    return ids, mats


def estimate(values, authority, period, spec: Spec | None = None, draws: int = 999, seed: int = 20250403,
             adjust: str | None = None):
    """Point estimates and a cluster bootstrap by contracting authority (drawn with all its contracts in both
    periods). adjust=None applies the full-sample rule of choose_adjust; the choice is fixed for every draw."""
    spec = spec or Spec()
    values, authority, period = np.asarray(values, float), np.asarray(authority), np.asarray(period)
    adjust = adjust or choose_adjust(values, period)
    ids, mats = matrices(values, authority, period)

    def run(weights):
        res = {}
        for p in ("pre", "post"):
            o, e = mats[p]
            oc = np.asarray(o.sum(0)).ravel() if weights is None else o.T @ weights
            ec = np.asarray(e.sum(0)).ravel() if weights is None else e.T @ weights
            res[p] = excess(oc, ec, spec)
        flat = {f"{k}_{p}": v for p in ("pre", "post") for k, v in res[p].items()
                if not k.startswith(("exact_", "numb_", "den_"))}
        return flat | contrasts(res["pre"], res["post"], spec, adjust)

    point = run(None) | {"adjust": adjust}
    rng = np.random.default_rng(seed)
    reps = [run(np.bincount(rng.integers(0, len(ids), len(ids)), minlength=len(ids)).astype(float))
            for _ in range(draws)]
    ci = {}
    if draws:
        for k in point:
            if k == "adjust":
                continue
            arr = np.array([r[k] for r in reps], float)
            failed = int(np.isnan(arr).sum())
            if k in PRIMARY and failed > MAX_FAILED_SHARE * draws:
                raise RuntimeError(f"{k}: {failed} of {draws} bootstrap draws undefined")
            ci[k] = {"ci95": tuple(np.nanpercentile(arr, [2.5, 97.5])), "ci90": tuple(np.nanpercentile(arr, [5, 95])),
                     "se": float(np.nanstd(arr, ddof=1)), "failed_draws": failed}
    return point, ci


def gate_failed(point: dict, ci: dict, margin: float = MARGIN, strict: bool = False) -> bool:
    """§7.1. Adopted rule: the mean placebo over the four gate controls must have its 90 % interval inside ±margin
    (absence of evidence is not a pass), and each gate control's own placebo must have its point estimate inside
    ±margin and its 90 % interval not wholly outside it. strict=True is the round-1 reviewer's rule (every gate
    control's 90 % interval inside ±margin), kept for the power comparison of §9."""
    def inside(k):
        lo, hi = ci[k]["ci90"]
        return -margin < lo and hi < margin
    names = [f"placebo_a_control_{c // 1_000_000}M" for c in GATE_CONTROLS]
    if strict:
        return not all(inside(k) for k in names)
    each = all(abs(point[k]) < margin and ci[k]["ci90"][0] < margin and ci[k]["ci90"][1] > -margin for k in names)
    return not (inside("placebo_a_gate_mean") and each)


def label(ci95, ci90, underpowered: bool = False, gate: bool = False, margin: float = MARGIN) -> tuple[str, str]:
    """§8.1 in its literal order. Returns (label, note); the note selects the pre-written sentence."""
    if underpowered:
        return "underpowered", ""
    if gate:
        return "inconclusive", "validity gate failed"
    if -margin < ci90[0] and ci90[1] < margin:
        return "not supported", "detected, below the margin" if ci95[0] > 0 else ""
    if ci95[0] > 0:
        return "supported", ""
    return "inconclusive", "interval wholly below 0" if ci95[1] < 0 else ""
