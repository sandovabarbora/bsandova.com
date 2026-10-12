"""Power (design §9), simulated from a smooth density calibrated on the far bands only.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 python tools/procurement/power.py
    ... python tools/procurement/power.py <n_pre> <n_post>     # the data step of §9.3

Inputs: docs/research/procurement-bunching-structure.json (counts in value bands far from every threshold). Every
other input is an assumption, named in ASSUME. Output: docs/research/procurement-bunching-power.json.
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
    "months_pre": 60,  # 1 Jan 2020 – 31 Dec 2024
    "months_post": 12,  # 1 Jul 2025 – 30 Jun 2026 (§4.1)
    "authorities": 8_000,
    "size_sigma": 1.5,
    "tilt_sd": 0.3,  # authority price level
    "habit_shape": 0.5,  # authority round-million habit (gamma shape)
    "round_100k": 0.15,
    "relevant_share": [0.3, 0.5, 0.7],  # share of contracts at a limit of the type it binds
}
SIMS, BOOT, BOOT_DRAWS = 150, 2, 199
Z = 1.959964 + 0.841621  # 95 % interval above 0 with 80 % power
KEYS = ["D_new_a", "D_old_a", "D_new_b", "D_old_b", "D_new_a_supplies_services", "D_new_a_works"]
GATE = [f"placebo_a_control_{c // 1_000_000}M" for c in bu.GATE_CONTROLS] + ["placebo_a_gate_mean"]


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


def world(alpha: float, n_pre: int, n_post: int, r1m: float) -> World:
    return World(n_pre=n_pre, n_post=n_post, alpha=alpha, authorities=ASSUME["authorities"],
                 size_sigma=ASSUME["size_sigma"], tilt_sd=ASSUME["tilt_sd"], habit_shape=ASSUME["habit_shape"],
                 round_100k=ASSUME["round_100k"], round_1m={"pre": r1m, "post": r1m})


def scenario(alpha: float, n_pre: int, n_post: int, r1m: float) -> dict:
    rows = []
    for s in range(SIMS):
        est, _ = bu.estimate(*draw(world(alpha, n_pre, n_post, r1m), 1000 + s), draws=0)
        rows.append([est[k] for k in KEYS + GATE] + [est["adjust"] == "ratio"])
    arr = np.array(rows, float)
    sd = {k: float(np.nanstd(arr[:, i], ddof=1)) for i, k in enumerate(KEYS + GATE)}
    boot = []
    for s in range(BOOT):
        est, ci = bu.estimate(*draw(world(alpha, n_pre, n_post, r1m), 5000 + s), draws=BOOT_DRAWS)
        boot.append({k: ci[k]["se"] for k in KEYS + GATE} | {"gate_failed": bu.gate_failed(est, ci),
                                                             "gate_failed_strict": bu.gate_failed(est, ci, strict=True)})
    bse = {k: float(np.mean([b[k] for b in boot])) for k in KEYS + GATE}
    mde = {k: Z * max(sd[k], bse[k]) for k in KEYS}
    # gate pass under the null, each simulated placebo ± 1.645 × its se: strict (every control inside) and adopted
    se = np.array([max(sd[g], bse[g]) for g in GATE])
    pl = arr[:, len(KEYS):len(KEYS) + len(GATE)]
    m = bu.MARGIN
    strict = np.all(np.abs(pl[:, :-1]) + 1.645 * se[:-1] < m, axis=1)
    each = np.all((np.abs(pl[:, :-1]) < m) & (np.abs(pl[:, :-1]) - 1.645 * se[:-1] < m), axis=1)
    adopted = each & (np.abs(pl[:, -1]) + 1.645 * se[-1] < m)
    return {"round_1m": r1m, "n_pre": n_pre, "n_post": n_post, "ratio_chosen_share": float(arr[:, -1].mean()),
            "null_mean": {k: float(np.nanmean(arr[:, i])) for i, k in enumerate(KEYS)}, "mc_sd": sd,
            "bootstrap_se": bse, "bootstrap_gate_failed": [b["gate_failed"] for b in boot], "mde_80": mde,
            "mde_80_affected_scale": {f"s={s}": {k: mde[k] / s for k in ("D_new_a", "D_new_b")}
                                      for s in ASSUME["relevant_share"]},
            "gate_pass_rate_null": float(adopted.mean()), "gate_pass_rate_null_strict": float(strict.mean())}


def data_step(n_pre: int, n_post: int) -> None:
    """§9.3: the real totals in the range (two counts), before estimate.py; the worst case over the rounding sweep."""
    out = json.loads((DOCS / "procurement-bunching-power.json").read_text())
    runs = [scenario(out["alpha"], n_pre, n_post, r) for r in ASSUME["round_1m"]]
    out["data_step"] = runs
    out["data_step_mde"] = {h: max(r["mde_80"][h] for r in runs) for h in ("D_new_a", "D_old_a", "D_new_b", "D_old_b")}
    (DOCS / "procurement-bunching-power.json").write_text(json.dumps(out, indent=1))
    print("ok")


def main() -> None:
    if len(sys.argv) == 3:
        return data_step(int(sys.argv[1]), int(sys.argv[2]))
    alpha, per_month = calibrate(json.loads((DOCS / "procurement-bunching-structure.json").read_text()))
    out = {"assumptions": ASSUME, "alpha": alpha, "records_per_month_in_range_interpolated": per_month,
           "scenarios": []}
    for share in ASSUME["retained_share"]:
        n_pre = int(per_month * share * ASSUME["months_pre"])
        n_post = int(per_month * share * ASSUME["months_post"])
        for r1m in ASSUME["round_1m"]:
            res = scenario(alpha, n_pre, n_post, r1m) | {"retained_share": share}
            out["scenarios"].append(res)
            print(f"retained {share} round_1m {r1m}: n {n_pre}/{n_post}; ratio chosen {res['ratio_chosen_share']:.2f}; "
                  + "; ".join(f"{k} {v:.3f}" for k, v in res["mde_80"].items())
                  + f"; gate pass {res['gate_pass_rate_null']:.2f} (strict {res['gate_pass_rate_null_strict']:.2f})")
    (DOCS / "procurement-bunching-power.json").write_text(json.dumps(out, indent=1))
    print(f"alpha {alpha:.3f}, {per_month:.0f} records a month interpolated into the range")


if __name__ == "__main__":
    main()
