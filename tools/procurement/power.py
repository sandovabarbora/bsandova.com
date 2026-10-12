"""Power for D_new and D_old (design §9), simulated from a smooth density calibrated on the far bands only.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 python tools/procurement/power.py

Inputs: docs/research/procurement-bunching-structure.json (record counts in value bands far from every threshold,
two monthly dumps). Everything else is an assumption and is named as one in ASSUME. Output:
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
    "retained_share": [0.6, 0.35],  # valid version, not an amendment, CZK, not excluded by §4.3 keywords
    "months_pre": 60,  # 1 Jan 2020 – 31 Dec 2024 (§4.1)
    "months_post": 15,  # 3 Apr 2025 – 30 Jun 2026
    "authorities": 8_000,  # distinct publishing IČO over the window; 4 286 and 4 719 in the two months read
    "size_sigma": 1.5,
    "round_100k": 0.15,
    "round_1m": 0.02,
    "move_concentration": 0.5,
}
SIMS, BOOT_CHECK, Z = 200, 3, 1.959964 + 0.841621  # one-sided 2.5 % (95 % CI above 0), 80 % power


def calibrate(structure: dict) -> tuple[float, float]:
    """Fit density c·v^−α to the far-band counts, averaged over the dumps read (Poisson deviance)."""
    files = structure["files"].values()
    bands = [tuple(b) for b in structure["far_bands_kc"]]
    counts = np.array([np.mean([f["far_band_counts_hodnotaBezDph"][f"({lo}, {hi}]"] for f in files])
                       for lo, hi in bands])

    def expected(params):
        logc, a = params
        return np.array([np.exp(logc) * (hi ** (1 - a) - lo ** (1 - a)) / (1 - a) for lo, hi in bands])

    def deviance(params):
        mu = expected(params)
        return float(np.sum(mu - counts * np.log(mu)))

    fit = minimize(deviance, x0=[17.0, 1.6], method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-8})
    logc, a = fit.x
    per_month = float(np.exp(logc) * (bu.HI ** (1 - a) - bu.LO ** (1 - a)) / (1 - a))
    return float(a), per_month


def sd_under_null(alpha: float, n_pre: int, n_post: int, sims: int) -> dict:
    keys = ["D_new", "D_old", "D_new_supplies_services", "D_new_works", "D_old_supplies_services", "D_old_works"]
    rows = []
    for s in range(sims):
        w = World(n_pre=n_pre, n_post=n_post, alpha=alpha, authorities=ASSUME["authorities"],
                  size_sigma=ASSUME["size_sigma"], round_100k=ASSUME["round_100k"],
                  round_1m={"pre": ASSUME["round_1m"], "post": ASSUME["round_1m"]})
        est, _ = bu.estimate(*draw(w, 1000 + s), draws=0)
        rows.append([est[k] for k in keys])
    arr = np.array(rows)
    return {k: {"mean": float(arr[:, i].mean()), "sd": float(arr[:, i].std(ddof=1)),
                "mde_80": float(Z * arr[:, i].std(ddof=1))} for i, k in enumerate(keys)}


def boot_check(alpha: float, n_pre: int, n_post: int) -> list[float]:
    ses = []
    for s in range(BOOT_CHECK):
        w = World(n_pre=n_pre, n_post=n_post, alpha=alpha, authorities=ASSUME["authorities"])
        _, ci = bu.estimate(*draw(w, 5000 + s), draws=199)
        ses.append(ci["D_new"]["se"])
    return ses


def data_step(n_pre: int, n_post: int) -> None:
    """§9.3: after prepare.py, with the real totals in the analysis range (a count, not a histogram), and before
    estimate.py: the larger of the Monte Carlo and the bootstrap-based MDE decides 'underpowered'."""
    out = json.loads((DOCS / "procurement-bunching-power.json").read_text())
    null = sd_under_null(out["alpha"], n_pre, n_post, SIMS)
    boot = boot_check(out["alpha"], n_pre, n_post)
    mde_new = max(null["D_new"]["mde_80"], Z * float(np.mean(boot)))
    mde_old = max(null["D_old"]["mde_80"], Z * float(np.mean(boot)) * null["D_old"]["sd"] / null["D_new"]["sd"])
    out["data_step"] = {"n_pre": n_pre, "n_post": n_post, "null": null, "bootstrap_se_D_new": boot}
    out["data_step_mde"] = {"D_new": mde_new, "D_old": mde_old}
    (DOCS / "procurement-bunching-power.json").write_text(json.dumps(out, indent=1))
    print(out["data_step_mde"])


def main() -> None:
    if len(sys.argv) == 3:
        return data_step(int(sys.argv[1]), int(sys.argv[2]))
    structure = json.loads((DOCS / "procurement-bunching-structure.json").read_text())
    alpha, per_month = calibrate(structure)
    out = {"assumptions": ASSUME, "alpha": alpha, "records_per_month_in_range_interpolated": per_month,
           "scenarios": []}
    for share in ASSUME["retained_share"]:
        n_pre = int(per_month * share * ASSUME["months_pre"])
        n_post = int(per_month * share * ASSUME["months_post"])
        res = sd_under_null(alpha, n_pre, n_post, SIMS)
        out["scenarios"].append({"retained_share": share, "n_pre": n_pre, "n_post": n_post, "null": res,
                                 "bootstrap_se_D_new_check": boot_check(alpha, n_pre, n_post)})
        print(f"retained {share}: n_pre {n_pre}, n_post {n_post}; "
              + "; ".join(f"{k} MDE {v['mde_80']:.3f} (null mean {v['mean']:+.3f})" for k, v in res.items()))
    (DOCS / "procurement-bunching-power.json").write_text(json.dumps(out, indent=1))
    print(f"alpha {alpha:.3f}, {per_month:.0f} records a month interpolated into the analysis range")


if __name__ == "__main__":
    main()
