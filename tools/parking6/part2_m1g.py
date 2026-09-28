"""Part II correction: Part II's own pipeline (read-only import from ~/Downloads/parking/src), fed with the EEA series
for M1 + M1G instead of M1 only. Nothing else changes: the ratio, the anchor, the fleet model, the gap, the parallel
share and the stall count are all Part II's. It also converts Part 6's comparator (EEA trend × register slope b̂).

    uv run --no-project --with numpy --with pandas python tools/parking6/part2_m1g.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/Users/barbora.sandova/Downloads/parking/src")
from capacity_model import load_zps_aggregates, pitch_model, segment_stall_counts  # noqa: E402
from config import BASE_YEAR, CURRENT_YEAR, GAP_CENTRAL_M, PARALLEL_SHARE_CENTRAL  # noqa: E402
from eea_series import RATIO, RATIO_RANGE, length_series, yearly  # noqa: E402
from vehicle_dimensions import fleet_dimension  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = Path("/Users/barbora.sandova/Documents/Coding/bsandova.com/tools/data/parking6")


def rows(path: Path) -> list[dict]:
    merged: dict = defaultdict(lambda: defaultdict(int))
    with path.open() as f:
        for r in csv.DictReader(f):
            k = (int(r["Year"]), r["Mk"], r["Cn"])
            for c in ("regs", "n_w", "sum_w"):
                merged[k][c] += int(float(r[c] or 0))
    return [{"Year": y, "Mk": mk, "Cn": cn, **v} for (y, mk, cn), v in merged.items()]


def run(rs: list[dict]) -> dict:
    w = yearly(rs, "n_w", "sum_w")
    stalls = float(segment_stall_counts(load_zps_aggregates()).sum())
    out = {"wheelbase_2012_mm": w[2012]["mean"], "wheelbase_2022_mm": w[2022]["mean"],
           "wheelbase_change_mm": w[2022]["mean"] - w[2012]["mean"],
           "length_change_2012_2022_cm": {"central": (w[2022]["mean"] - w[2012]["mean"]) / RATIO / 10,
                                          "ratio_0.70": (w[2022]["mean"] - w[2012]["mean"]) / RATIO_RANGE[1] / 10,
                                          "ratio_0.52": (w[2022]["mean"] - w[2012]["mean"]) / RATIO_RANGE[0] / 10},
           "scenarios": {}}
    for lab, r in (("central", RATIO), ("ratio_low", RATIO_RANGE[0]), ("ratio_high", RATIO_RANGE[1])):
        s = length_series(w, r)
        pb, pn = fleet_dimension(BASE_YEAR, s), fleet_dimension(CURRENT_YEAR, s)
        res = pitch_model(stalls, pb, pn, GAP_CENTRAL_M, PARALLEL_SHARE_CENTRAL)
        out["scenarios"][lab] = {"fleet_2012_m": pb, "fleet_2025_m": pn, "stalls_lost": res.stalls_base - res.stalls_current,
                                 "loss_pct": res.loss_pct, "new_car_2012_m": float(s.at(2012)), "new_car_2025_m": float(s.at(2025))}
    return out


def main() -> None:
    m1 = run(rows(Path("/Users/barbora.sandova/Downloads/parking/data/raw/eea_cz_by_model.csv")))
    m1g = run(rows(RAW / "eea_cz_by_model_m1_m1g.csv"))
    h = json.loads((ROOT / "assets/parking6/h2.json").read_text())
    out = {"part2_m1_only_rerun": m1, "m1_m1g": m1g,
           "part6_comparator_cm": h["estimates"]["comparator_C_cm"], "b_hat": h["estimates"]["b_hat"]}
    (ROOT / "assets/parking6/part2_correction.json").write_text(json.dumps(out, indent=1, default=float))
    for k in ("part2_m1_only_rerun", "m1_m1g"):
        v = out[k]
        print(k, round(v["wheelbase_change_mm"], 1), {a: round(b, 2) for a, b in v["length_change_2012_2022_cm"].items()},
              {a: (round(b["stalls_lost"]), round(b["loss_pct"], 3), round(b["fleet_2012_m"], 3), round(b["fleet_2025_m"], 3)) for a, b in v["scenarios"].items()})


if __name__ == "__main__":
    main()
