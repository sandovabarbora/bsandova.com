"""Excess mass at fixed locations of the contract-value distribution, before and after 3 April 2025 (design §5–§7).

The functions take arrays (values in Kč without VAT, authority ids, period labels), so the tests can run them on
made-up data. The data step (prepare.py) supplies the real arrays; nothing here reads a file.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.polynomial import legendre
from scipy import sparse

LO, HI, WIDTH = 500_000, 13_500_000, 10_000
N_BINS = (HI - LO) // WIDTH
DEGREE = 7
SHARE_BELOW = 0.05  # every location window is (0.95 L, L]
SHARE_ABOVE = 0.05  # missing-mass window above a threshold, (T, 1.05 T]

OLD = {"supplies_services": 2_000_000, "works": 6_000_000}
NEW = {"supplies_services": 3_000_000, "works": 9_000_000}
CONTROLS = (4_000_000, 5_000_000, 7_000_000, 8_000_000, 10_000_000, 12_000_000, 13_000_000)
# Nuisance points excluded from the fit with the 5 % window below them; not analysed (design §5.3).
EU_CENTRAL = (3_568_000, 3_653_000, 3_494_000, 3_491_000)  # NV 172/2016 § 2(1)(a), § 3(1)(a), 2020–2026
EU_SUBCENTRAL = (5_494_000, 5_610_000, 5_401_000, 5_386_000)  # § 2(1)(b), § 3(1)(b)
SMALL_LOT = (2_054_000, 2_087_000, 1_955_000, 1_995_000)  # § 5(a), part of a contract under § 18(3) ZZVZ
OTHER = (750_000, 1_000_000, 11_000_000)  # MPZ direct purchase, § 219 / round million, VAT image of 9 M
VAT_IMAGES = tuple(round(t * 1.21) for t in (*OLD.values(), *NEW.values()))  # robustness only


def bin_index(values: np.ndarray) -> np.ndarray:
    """Bin j holds (LO + j·WIDTH, LO + (j+1)·WIDTH]: a value equal to a limit falls in the bin that ends at it,
    as § 27 ZZVZ makes a contract 'equal to or below' the limit a small-scale contract. −1 = outside the range."""
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
    controls: tuple = CONTROLS
    exclude_vat_images: bool = False
    extra_excluded: tuple = field(default_factory=tuple)

    def locations(self) -> dict[str, float]:
        locs = {f"old_{k}": v for k, v in OLD.items()} | {f"new_{k}": v for k, v in NEW.items()}
        return locs | {f"control_{c // 1_000_000}M": c for c in self.controls}

    def excluded(self) -> np.ndarray:
        mask = np.zeros(N_BINS, bool)
        for p in self.locations().values():
            mask[below(p, self.share_below)] = True
        for t in (*OLD.values(), *NEW.values()):
            mask[above(t)] = True
        nuisance = (*EU_CENTRAL, *EU_SUBCENTRAL, *SMALL_LOT, *OTHER, *self.extra_excluded,
                    *(VAT_IMAGES if self.exclude_vat_images else ()))
        for p in nuisance:
            mask[below(p)] = True
        return mask


def design_matrix(degree: int) -> np.ndarray:
    e = edges()
    mid = np.log((e[:-1] + e[1:]) / 2)
    x = 2 * (mid - mid.min()) / (mid.max() - mid.min()) - 1
    poly = legendre.legvander(x, degree)

    def holds(m: int) -> np.ndarray:
        return (np.floor(e[1:] / m) * m > e[:-1]).astype(float)

    m500, m100, m50 = holds(500_000), holds(100_000), holds(50_000)
    return np.column_stack([poly, m500, m100 * (1 - m500), m50 * (1 - m100)])


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


def excess(counts: np.ndarray, spec: Spec) -> dict[str, float]:
    """r(L) = Σ_W (c − ĉ) / Σ_W ĉ for each location window W = (0.95 L, L]; m(T) the same above each limit."""
    X = design_matrix(spec.degree)
    keep = ~spec.excluded()
    beta = poisson_fit(counts[keep].astype(float), X[keep])
    fitted = np.exp(X @ beta)
    out = {}
    num = den = 0.0
    for name, p in spec.locations().items():
        w = below(p, spec.share_below)
        out[name] = float((counts[w] - fitted[w]).sum() / fitted[w].sum())
        if name.startswith("control_"):
            out[f"num_{name}"], out[f"den_{name}"] = float((counts[w] - fitted[w]).sum()), float(fitted[w].sum())
            num, den = num + out[f"num_{name}"], den + out[f"den_{name}"]
    out["controls_pooled"] = num / den  # Σ excess / Σ expected over the control windows
    for name, t in [*(("above_old_" + k, v) for k, v in OLD.items()), *(("above_new_" + k, v) for k, v in NEW.items())]:
        w = above(t)
        out[name] = float((counts[w] - fitted[w]).sum() / fitted[w].sum())
    return out


def contrasts(pre: dict[str, float], post: dict[str, float], spec: Spec, adjust: str = "ratio") -> dict[str, float]:
    """D_new = r(new, post) − k·r(new, pre) and D_old = k·r(old, pre) − r(old, post), where k scales the round-number
    component by the change in the control locations' mean excess (design §6.2). adjust = "ratio" (primary),
    "difference" (k·r replaced by r + Δcontrols) or "none" (k = 1)."""
    c_pre, c_post = pre["controls_pooled"], post["controls_pooled"]
    k = {"ratio": c_post / c_pre if c_pre > 0 else float("nan"), "difference": 1.0, "none": 1.0}[adjust]
    shift = c_post - c_pre if adjust == "difference" else 0.0
    out = {"control_ratio": c_post / c_pre if c_pre > 0
           else float("nan")}
    for kind in OLD:
        out[f"D_new_{kind}"] = post[f"new_{kind}"] - (k * pre[f"new_{kind}"] + shift)
        out[f"D_old_{kind}"] = (k * pre[f"old_{kind}"] + shift) - post[f"old_{kind}"]
    out["D_new"] = float(np.mean([out[f"D_new_{kind}"] for kind in OLD]))
    out["D_old"] = float(np.mean([out[f"D_old_{kind}"] for kind in OLD]))
    # Placebo (§7.1): each control in turn treated as a 'new limit', with k from the other controls.
    ctrl = [key.removeprefix("num_") for key in pre if key.startswith("num_")]
    loo = []
    for c in ctrl:
        others = [o for o in ctrl if o != c]
        r_pre = sum(pre[f"num_{o}"] for o in others) / sum(pre[f"den_{o}"] for o in others)
        r_post = sum(post[f"num_{o}"] for o in others) / sum(post[f"den_{o}"] for o in others)
        k_c = r_post / r_pre if adjust == "ratio" and r_pre > 0 else 1.0
        shift_c = r_post - r_pre if adjust == "difference" else 0.0
        loo.append(post[c] - (k_c * pre[c] + shift_c))
    out["placebo_controls"] = float(np.mean(loo))
    return out


def histograms(values: np.ndarray, authority: np.ndarray, period: np.ndarray):
    """Authority × bin count matrices for 'pre' and 'post', on one shared authority index."""
    ids, a = np.unique(authority, return_inverse=True)
    j = bin_index(values)
    mats = {}
    for p in ("pre", "post"):
        m = (period == p) & (j >= 0)
        mats[p] = sparse.csr_matrix((np.ones(m.sum()), (a[m], j[m])), shape=(len(ids), N_BINS))
    return ids, mats


def estimate(values, authority, period, spec: Spec | None = None, draws: int = 999, seed: int = 20250403,
             adjust: str = "ratio", drop_exact_millions: bool = False):
    """Point estimates and a cluster bootstrap by contracting authority. Authorities are drawn once per replicate
    and keep their contracts in both periods, so the pre/post covariance is kept. drop_exact_millions removes
    contracts priced at exactly a whole million (the pure round-number component, §6.3)."""
    spec = spec or Spec()
    values, authority, period = np.asarray(values, float), np.asarray(authority), np.asarray(period)
    if drop_exact_millions:
        keep = np.abs(values - np.round(values / 1_000_000) * 1_000_000) >= 0.5
        values, authority, period = values[keep], authority[keep], period[keep]
    ids, mats = histograms(values, authority, period)

    def run(weights: np.ndarray | None) -> dict[str, float]:
        res = {}
        for p in ("pre", "post"):
            c = np.asarray(mats[p].sum(0)).ravel() if weights is None else mats[p].T @ weights
            res[p] = excess(c, spec)
        return {**{f"{k}_pre": v for k, v in res["pre"].items()}, **{f"{k}_post": v for k, v in res["post"].items()},
                **contrasts(res["pre"], res["post"], spec, adjust)}

    point = run(None)
    rng = np.random.default_rng(seed)
    reps = []
    for _ in range(draws):
        w = np.bincount(rng.integers(0, len(ids), len(ids)), minlength=len(ids)).astype(float)
        reps.append(run(w))
    ci = {}
    for k in point:
        arr = np.array([r[k] for r in reps])
        ci[k] = {"ci95": tuple(np.percentile(arr, [2.5, 97.5])), "ci90": tuple(np.percentile(arr, [5, 95])),
                 "se": float(arr.std(ddof=1))} if draws else {}
    return point, ci


MARGIN = 0.15  # equivalence margin on the r scale (design §8)


def label(ci95: tuple[float, float], ci90: tuple[float, float], underpowered: bool = False,
          margin: float = MARGIN) -> str:
    """Rules of §8 in their literal order: underpowered (fixed before data), supported, not supported,
    inconclusive."""
    if underpowered:
        return "underpowered"
    if ci95[0] > 0:
        return "supported"
    if -margin < ci90[0] and ci90[1] < margin:
        return "not supported"
    return "inconclusive"
