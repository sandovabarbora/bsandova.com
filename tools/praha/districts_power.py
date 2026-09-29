"""Part 3 extended, §6: design-stage power on the real switch vectors, before any grant or budget amount is read
(docs/research/prague-districts-design.md).

Inputs: the frozen alignment panel (tools/praha/districts_alignment.py) and population at 31 December 2014 (ČSÚ).
No outcome enters. Outcomes are simulated, in units of each district's own mean (so an effect of 0.2 is a premium
of 20 % of the district's usual city grants), with:
  - heavy tails: standardised Student t innovations, ν ∈ {3, 5};
  - heteroskedasticity: SD ∝ (N_i / median N)^(−θ/2), θ ∈ {0, 0.5, 1};
  - AR(1) persistence ρ ∈ {0, 0.3, 0.6};
  - lumpiness: a district-year gets no city grant with probability q ∈ {0, 0.2, 0.4};
  - coefficient of variation CV ∈ {0.5, 1, 2} of a district's non-zero years.

The test is the registered one: stacked by event (2018, 2023), window −3…+2, switch-in units against clean
controls (unaligned throughout the window), studentised difference of (post mean − pre mean), randomisation
inference permuting the switch-in label within tier among baseline-unaligned units (999 draws). Power is the share
of 400 simulated data sets with p ≤ α at α = 0.025 (Holm's first step for two hypotheses) and α = 0.05.

The TOST check applies the registered equivalence margin m to data simulated with no effect: H0 δ ≥ m is tested by
RI after dividing the switchers' post-event outcomes by (1 + m), and likewise for −m.

Usage:
    uv run --with pandas --with numpy --with openpyxl python tools/praha/districts_power.py
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import json
import os
import re
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get("PRAHA3X", ROOT / "tools" / "data" / "praha3x"))
OUT = ROOT / "docs" / "research" / "prague-districts-power.json"
YEARS = list(range(2015, 2026))
EVENTS = {2018: ([2016, 2017, 2018], [2019, 2020, 2021]), 2023: ([2020, 2021, 2022], [2023, 2024, 2025])}
BASE = {"cv": 1.0, "nu": 3, "theta": 0.5, "rho": 0.3, "q": 0.2}
GRID = {"cv": [0.5, 2.0], "nu": [5], "theta": [0.0, 1.0], "rho": [0.0, 0.6], "q": [0.0, 0.4]}
DELTAS = [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0]
SIMS, PERMS = 400, 999
RNG = np.random.default_rng(20260928)


def population() -> pd.Series:
    s = pd.read_excel(RAW / "mc_pop.xlsx", header=None)
    col = next(i for i in range(s.shape[1]) if "31.12.2014" in str(s.iloc[4, i]).replace("\n", ""))
    p = s.iloc[6:, [3, col]]
    p.columns = ["district", "pop"]
    p = p[s.iloc[6:, 2].astype(str).str.fullmatch(r"\d{6}")]
    return p.assign(district=p.district.astype(str).str.strip()).set_index("district")["pop"].astype(float)


def design(panel: pd.DataFrame) -> list[dict]:
    """Per event: switch-in units, clean controls and permutation strata (tier, among baseline-unaligned)."""
    wide = panel.pivot(index="district", columns="r", values="A")
    tier = panel.groupby("district").tier.first()
    out = []
    for event, (pre, post) in EVENTS.items():
        w = wide[pre + post]
        switch = (w[pre] == 0).all(axis=1) & (w[post] == 1).all(axis=1)
        stay = (w == 0).all(axis=1)  # clean controls: unaligned throughout the window
        units = w.index[switch | stay]
        out.append({"event": event, "units": list(units), "switch": switch[units].to_numpy(),
                    "base0": (w.loc[units, pre[-1]] == 0).to_numpy(), "tier": tier[units].to_numpy(),
                    "pre": [YEARS.index(y) for y in pre], "post": [YEARS.index(y) for y in post]})
    return out


def simulate(n: int, size: np.ndarray, p: dict) -> np.ndarray:
    """Outcomes in units of each district's mean, n × len(YEARS)."""
    t = len(YEARS)
    eps = RNG.standard_t(p["nu"], (SIMS, n, t)) / np.sqrt(p["nu"] / (p["nu"] - 2))
    e = np.empty_like(eps)
    e[..., 0] = eps[..., 0]
    for k in range(1, t):
        e[..., k] = p["rho"] * e[..., k - 1] + np.sqrt(1 - p["rho"] ** 2) * eps[..., k]
    sd = p["cv"] * (size / np.median(size)) ** (-p["theta"] / 2)
    y = np.maximum(0.0, 1 + sd[None, :, None] * e)
    y *= RNG.random((SIMS, n, t)) >= p["q"]
    return y / (1 - p["q"])


def stat(d: np.ndarray, sw: np.ndarray) -> np.ndarray:
    """Studentised switchers-minus-stayers difference; d is (..., units), sw is (..., units) boolean."""
    ns, nc = sw.sum(-1), (~sw).sum(-1)
    ms = np.where(sw, d, 0).sum(-1) / ns
    mc = np.where(~sw, d, 0).sum(-1) / nc
    vs = np.where(sw, (d - ms[..., None]) ** 2, 0).sum(-1) / np.maximum(ns - 1, 1)
    vc = np.where(~sw, (d - mc[..., None]) ** 2, 0).sum(-1) / np.maximum(nc - 1, 1)
    return ms - mc, vs / ns + vc / nc


def perms(ev: dict) -> np.ndarray:
    """PERMS relabellings of switch-in within tier among baseline-unaligned units; stayers at 1 keep their label."""
    out = np.tile(ev["switch"], (PERMS, 1))
    for t in (0, 1):
        idx = np.where(ev["base0"] & (ev["tier"] == t))[0]
        k = int(ev["switch"][idx].sum())
        for b in range(PERMS):
            lab = np.zeros(len(idx), bool)
            lab[RNG.choice(len(idx), k, replace=False)] = True
            out[b, idx] = lab
    return out


def pvalues(y: np.ndarray, evs: list[dict], index: dict, pm: list[np.ndarray], delta: float, shift: float = 0.0):
    """One-sided RI p-values (switchers larger), pooled over events, for SIMS data sets."""
    num_obs, var_obs = 0, 0
    num_p, var_p = 0, 0
    total = sum(ev["switch"].sum() for ev in evs)
    for ev, P in zip(evs, pm):
        rows = [index[u] for u in ev["units"]]
        yy = y[:, rows, :].copy()
        post = np.zeros(yy.shape[-1], bool)
        post[ev["post"]] = True
        yy[:, ev["switch"], :] *= np.where(post, (1 + delta) / (1 + shift), 1.0)
        d = yy[..., ev["post"]].mean(-1) - yy[..., ev["pre"]].mean(-1)  # SIMS × units
        w = ev["switch"].sum() / total
        m, v = stat(d, ev["switch"][None, :])
        num_obs, var_obs = num_obs + w * m, var_obs + w**2 * v
        mp, vp = stat(d[:, None, :], P[None, :, :])  # SIMS × PERMS
        num_p, var_p = num_p + w * mp, var_p + w**2 * vp
    t_obs = num_obs / np.sqrt(var_obs)
    t_p = num_p / np.sqrt(var_p)
    return ((t_p >= t_obs[:, None]).sum(1) + 1) / (PERMS + 1)


def power(y, evs, index, pm, delta, alpha) -> float:
    return float((pvalues(y, evs, index, pm, delta) <= alpha).mean())


def main() -> None:
    panel = pd.read_csv(RAW / "alignment" / "panel.csv")
    pop = population()
    evs = design(panel)
    units = sorted({u for ev in evs for u in ev["units"]})
    index = {u: i for i, u in enumerate(units)}
    size = pop.reindex(units).to_numpy()
    pm = [perms(ev) for ev in evs]
    assignments = 1
    for ev in evs:
        for t in (0, 1):
            idx = ev["base0"] & (ev["tier"] == t)
            assignments *= comb(int(idx.sum()), int(ev["switch"][idx].sum()))
    report = {"events": {str(ev["event"]): {"switch_in": int(ev["switch"].sum()),
                                            "stayers": int((~ev["switch"]).sum()),
                                            "stayers_unaligned": int((~ev["switch"] & ev["base0"]).sum()),
                                            "switch_in_by_tier": {"numbered": int((ev["switch"] & (ev["tier"] == 1)).sum()),
                                                                  "other": int((ev["switch"] & (ev["tier"] == 0)).sum())}}
                         for ev in evs},
              "distinct_assignments": str(assignments),
              "smallest_attainable_p": max(1 / assignments, 1 / (PERMS + 1)),
              "sims": SIMS, "perms": PERMS, "base": BASE, "scenarios": []}
    scenarios = [BASE] + [BASE | {k: v} for k, vals in GRID.items() for v in vals]
    for p in scenarios:
        y = simulate(len(units), size, p)
        row = {"params": p}
        for alpha in (0.025, 0.05):
            curve = {str(dl): power(y, evs, index, pm, dl, alpha) for dl in DELTAS}
            row[f"power_a{alpha}"] = curve
            row[f"mde80_a{alpha}"] = next((float(k) for k, v in curve.items() if v >= 0.8), None)
        size0 = float((pvalues(y, evs, index, pm, 0.0) <= 0.05).mean())
        row["size_at_0.05"] = size0
        for m in (0.1, 0.2, 0.3):
            lo = pvalues(y, evs, index, pm, 0.0, shift=m)  # H0: δ ≥ m, reject if switchers small: use 1 − p
            hi_up = pvalues(y, evs, index, pm, 0.0, shift=-m)
            p_upper = 1 - lo + 1 / (PERMS + 1)
            row[f"tost_power_margin_{m}"] = float(((p_upper <= 0.05) & (hi_up <= 0.05)).mean())
        report["scenarios"].append(row)
        print(p, row["mde80_a0.025"], row["size_at_0.05"])
    OUT.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
