"""One-off runs for design §5: false-positive rate, power, minimum detectable uplift and falsification detection of the
registered analysis on made-up panels with the registered geometry (baseline, cast, reference pool, TikTok exclusion,
every admissible placebo date). Writes docs/research/memes-power.json.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with pandas --with numpy \\
        python -I tools/memes/simulate.py
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import model as M
import synth as S

SHOCKS = (0.1, 0.3, 0.5, 1.0, 2.0)
DECAY = 5.0
SEEDS = 300
CAST_SHOCKS = (0.5, 1.0)
COMMON_SD = 0.1  # one factor shared by all actors, on top of one factor per group (target with its cast, the pool)


def _panel(spec: M.EventSpec, seed: int, shock: float = 0.0, jumpers: int = 0, cast_shock: float = 0.0):
    bumps = [(spec.target, spec.event_date, shock, DECAY)] if shock else []
    bumps += [(c, spec.event_date, cast_shock, DECAY) for c in spec.cast[:jumpers]]
    groups = {spec.target: spec.cast, spec.reference[0]: spec.reference[1:]}
    return S.synthetic_panel(seed, groups, C.START, C.END, bumps, common_sd=COMMON_SD)


def _runs(spec: M.EventSpec, seeds: range, **kw) -> list[M.EventResult]:
    return [M.run_event(_panel(spec, s, **kw), spec)[0] for s in seeds]


def _share(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs)


def false_positive_rate(spec: M.EventSpec, n_seeds: int = SEEDS) -> dict:
    runs = _runs(spec, range(1000, 1000 + n_seeds))
    return {"n_seeds": n_seeds, "h1_p_below_0.05": _share(r.placebo_p < 0.05 for r in runs),
            "external_falsification_p_below_0.05": _share(r.falsification_p < 0.05 for r in runs),
            "leave_one_out_p_below_0.05": _share(r.loo_p < 0.05 for r in runs),
            "median_null_sd": float(np.median([r.null_sd for r in runs])),
            "median_mdu_pct": float(np.median([r.mdu_pct for r in runs])),
            "median_mdu80_pct": float(np.median([r.mdu80_pct for r in runs])),
            "median_placebo_dates": float(np.median([r.n_placebo for r in runs]))}


def power(spec: M.EventSpec, shock: float, n_seeds: int = SEEDS) -> dict:
    h1 = dataclasses.replace(spec, falsification=False)      # H1 only, the falsification is timed separately
    runs = [M.run_event(_panel(spec, s, shock=shock), h1)[0] for s in range(2000, 2000 + n_seeds)]
    return {"shock": shock, "decay_days": DECAY, "n_seeds": n_seeds,
            "mean_uplift_pct": float(np.median([r.car_pct_uplift for r in runs])),
            "p_below_0.05": _share(r.placebo_p < 0.05 for r in runs),
            "p_below_0.025": _share(r.placebo_p < 0.025 for r in runs),
            "median_car": float(np.median([r.car for r in runs]))}


def cast_jump_detection(spec: M.EventSpec, jumpers: int, cast_shock: float = 0.5, n_seeds: int = SEEDS) -> dict:
    runs = _runs(spec, range(3000, 3000 + n_seeds), jumpers=jumpers, cast_shock=cast_shock)
    return {"jumping_controls": jumpers, "of": len(spec.cast), "shock": cast_shock, "n_seeds": n_seeds,
            "external_falsification_p_below_0.05": _share(r.falsification_p < 0.05 for r in runs),
            "leave_one_out_p_below_0.05": _share(r.loo_p < 0.05 for r in runs)}


def main() -> None:
    out = {}
    for spec in C.EVENTS:
        n = len(spec.cast)
        block = {"baseline": len(spec.controls), "cast": n, "false_positive_rate": false_positive_rate(spec),
                 "power": [power(spec, s) for s in SHOCKS]}
        block["falsification_power"] = [cast_jump_detection(spec, k, shock) for shock in CAST_SHOCKS
                                        for k in ((3, 5, n) if n > 2 else (n,))]
        out[spec.name] = block
    path = C.ROOT / "docs/research/memes-power.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
