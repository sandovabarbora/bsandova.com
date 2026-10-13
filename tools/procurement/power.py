"""Power, gate and label rates (design §9), simulated from a smooth density calibrated on the far bands only.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 python tools/procurement/power.py

The data step (§9.4) is called by `prepare.py --totals-to-power`. Inputs: docs/research/procurement-bunching-
structure.json (counts in value bands far from every threshold). Every other input is an assumption, named in
ASSUME. Labels and the gate are computed by bunching.decide, the code the registered run uses. Output:
docs/research/procurement-bunching-power.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bunching as bu  # noqa: E402
from synth_contracts import World, draw  # noqa: E402

DOCS = HERE.parents[1] / "docs" / "research"
ASSUME = {
    "retained_share": [0.6, 0.35],  # after §4 screening
    "round_1m": [0.02, 0.10, 0.30],  # share of contracts rounded to a whole million (unknown; swept)
    "drift": {"retained_share": 0.6, "round_1m": 0.10, "post_exponent": 1.0},  # rounding drifting by magnitude
    "months_pre": 60,  # 1 Jan 2020 – 31 Dec 2024
    "months_post": 12,  # 1 Jul 2025 – 30 Jun 2026 (§4.1)
    "authorities": 8_000,
    "size_sigma": 1.5,
    "tilt_sd": 0.3,
    "habit_shape": 0.5,
    "round_100k": 0.15,
    "relevant_share": [0.3, 0.5, 0.7],
    "alternative": {"move": 0.7, "move_exact": 1.0, "relevant_share": 0.5},  # planted placement at the limits
}
MDE_SIMS, BOOT_DRAWS, LABEL_SIMS, LABEL_DRAWS = 150, 199, 40, 99
Z = 2.446912 + 0.905703  # t(6): 95 % interval above 0 with 80 % power, as the labels use (§6.2)
KEYS = ["D_new_a", "D_old_a", "D_new_b", "D_old_b"]


def calibrate(structure: dict) -> tuple[float, float]:
    files = structure["files"].values()
    bands = [tuple(b) for b in structure["far_bands_kc"]]
    counts = np.array([np.mean([f["far_band_counts_hodnotaBezDph"][f"({lo}, {hi}]"] for f in files])
                       for lo, hi in bands])

    def expected(params):
        logc, a = params
        return np.array([np.exp(logc) * (hi ** (1 - a) - lo ** (1 - a)) / (1 - a) for lo, hi in bands])

    fit = minimize(lambda p: float(np.sum(expected(p) - counts * np.log(expected(p)))), x0=[17.0, 1.6],
                   method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-8})
    logc, a = fit.x
    return float(a), float(np.exp(logc) * (bu.HI ** (1 - a) - bu.LO ** (1 - a)) / (1 - a))


def world(alpha, n_pre, n_post, r1m, authorities=None, drift=0.0, **kw) -> World:
    return World(n_pre=n_pre, n_post=n_post, alpha=alpha, authorities=authorities or ASSUME["authorities"],
                 size_sigma=ASSUME["size_sigma"], tilt_sd=ASSUME["tilt_sd"], habit_shape=ASSUME["habit_shape"],
                 round_100k=ASSUME["round_100k"], round_1m={"pre": r1m, "post": r1m},
                 round_1m_drift={"pre": 0.0, "post": drift}, **kw)


def mde(alpha, n_pre, n_post, r1m, authorities=None, drift=0.0) -> dict:
    """MDE at 80 % power: 2.80 × the larger of the simulation spread and the calibrated bootstrap SE."""
    arr = np.array([[bu.estimate(*draw(world(alpha, n_pre, n_post, r1m, authorities, drift), 1000 + s),
                                 draws=0)[0][k] for k in KEYS] for s in range(MDE_SIMS)])
    sd = dict(zip(KEYS, np.nanstd(arr, axis=0, ddof=1)))
    p, c = bu.estimate(*draw(world(alpha, n_pre, n_post, r1m, authorities, drift), 5000), draws=BOOT_DRAWS)
    se = {k: bu.calibrate(p, c, k)["se"] if k in bu.PRIMARY else c[k]["se"] for k in KEYS}
    return {k: float(Z * max(sd[k], se[k])) for k in KEYS}


def label_rates(alpha, n_pre, n_post, r1m, drift=0.0, alternative=False) -> dict:
    """Runs the registered labels and gate (bunching.decide) on simulated data."""
    kw = {}
    if alternative:
        alt = ASSUME["alternative"]
        kw = {"move": {"pre": alt["move"], "post": alt["move"]}, "move_exact": alt["move_exact"],
              "relevant_share": alt["relevant_share"]}
    labels, gates, est, notes = [], [], [], []
    for s in range(LABEL_SIMS):
        p, c = bu.estimate(*draw(world(alpha, n_pre, n_post, r1m, drift=drift, **kw), 9000 + s), draws=LABEL_DRAWS)
        d = bu.decide(p, c)
        labels.append(d["D_new_a"]["label"])
        notes.append(d["D_new_a"]["note"] == "detected, below the margin")
        gates.append(d["gate_failed"])
        est.append(d["D_new_a"]["estimate"])
    lab = np.array(labels)
    return {"gate_fail_rate": float(np.mean(gates)),
            **{f"H1 {x}": float(np.mean(lab == x)) for x in ("supported", "not supported", "inconclusive")},
            "H1 not supported, detected below the margin": float(np.mean(notes)),
            "mean_calibrated_D_new_a": float(np.mean(est))}


def scenario(alpha, n_pre, n_post, r1m, drift=0.0) -> dict:
    m = mde(alpha, n_pre, n_post, r1m, drift=drift)
    null = label_rates(alpha, n_pre, n_post, r1m, drift)
    alt = label_rates(alpha, n_pre, n_post, r1m, drift, alternative=True)
    return {"round_1m": r1m, "drift": drift, "n_pre": n_pre, "n_post": n_post, "mde_80": m,
            "mde_80_affected_scale": {f"s={s}": m["D_new_a"] / s for s in ASSUME["relevant_share"]},
            "null": null, "alternative": alt,
            "effective_power_supported": alt["H1 supported"]}


def data_step(n_pre: int, n_post: int, authorities: int) -> None:
    """§9.4, called by prepare.py --totals-to-power: the worst case over the rounding sweep at the real totals."""
    path = DOCS / "procurement-bunching-power.json"
    out = json.loads(path.read_text())
    runs = [mde(out["alpha"], n_pre, n_post, r, authorities) for r in ASSUME["round_1m"]]
    out["data_step"] = {"runs": runs}  # the totals themselves are not written
    out["data_step_mde"] = {k: max(r[k] for r in runs) for k in KEYS}
    path.write_text(json.dumps(out, indent=1))
    print("ok")


def mde_only() -> None:
    """Recomputes the MDE columns of the saved scenarios (same seeds) after a change of Z; labels are untouched."""
    path = DOCS / "procurement-bunching-power.json"
    out = json.loads(path.read_text())
    for sc in out["scenarios"]:
        sc["mde_80"] = mde(out["alpha"], sc["n_pre"], sc["n_post"], sc["round_1m"], drift=sc["drift"])
        sc["mde_80_affected_scale"] = {f"s={s}": sc["mde_80"]["D_new_a"] / s for s in ASSUME["relevant_share"]}
        path.write_text(json.dumps(out, indent=1))
    out["mde_multiplier"] = Z
    path.write_text(json.dumps(out, indent=1))
    print("ok")


def main() -> None:
    if sys.argv[1:] == ["--mde-only"]:
        return mde_only()
    alpha, per_month = calibrate(json.loads((DOCS / "procurement-bunching-structure.json").read_text()))
    out = {"assumptions": ASSUME, "alpha": alpha, "records_per_month_in_range_interpolated": per_month,
           "scenarios": []}
    runs = [(sh, r, 0.0) for sh in ASSUME["retained_share"] for r in ASSUME["round_1m"]]
    d = ASSUME["drift"]
    runs.append((d["retained_share"], d["round_1m"], d["post_exponent"]))
    for share, r1m, drift in runs:
        n_pre = int(per_month * share * ASSUME["months_pre"])
        n_post = int(per_month * share * ASSUME["months_post"])
        res = scenario(alpha, n_pre, n_post, r1m, drift) | {"retained_share": share}
        out["scenarios"].append(res)
        (DOCS / "procurement-bunching-power.json").write_text(json.dumps(out, indent=1))
        print(f"retained {share} round {r1m} drift {drift}: MDE " + " ".join(f"{k} {v:.2f}" for k, v in res["mde_80"].items())
              + f" | null: gate fail {res['null']['gate_fail_rate']:.2f}, supported {res['null']['H1 supported']:.2f},"
              f" not supported {res['null']['H1 not supported']:.2f}"
              f" | alt (D≈{res['alternative']['mean_calibrated_D_new_a']:.2f}): supported {res['effective_power_supported']:.2f},"
              f" gate fail {res['alternative']['gate_fail_rate']:.2f}")
    print(f"alpha {alpha:.3f}, {per_month:.0f} records a month interpolated into the range")


if __name__ == "__main__":
    main()
