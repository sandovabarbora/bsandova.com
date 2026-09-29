"""Dump the data behind the five figures of the first parking estimate (8 September 2026) to JSON, from the same model
calls as the parking project's make_figures_web.py, so the interactive charts show the numbers the run produced.

Needs the parking project (PARKING_DIR, default ~/Downloads/parking); writes assets/parking/figures-data.json.

    PARKING_DIR=~/Downloads/parking uv run --no-project --with numpy --with pandas --with scipy \
        python tools/charts/parking_text01_data.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

PARKING = Path(os.environ.get("PARKING_DIR", Path.home() / "Downloads/parking")).expanduser()
sys.path.insert(0, str(PARKING / "src"))
os.chdir(PARKING)

from capacity_model import area_model, load_zps_aggregates, pitch_model  # noqa: E402
from config import GAP_CENTRAL_M, PARALLEL_SHARE_CENTRAL  # noqa: E402
from run_analysis import capacity_tables, dimension_scenarios, net_area  # noqa: E402
from vehicle_dimensions import fleet_dimension, load_te_series, mean_fleet_age_at  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "assets/parking/figures-data.json"
r = lambda x, n=4: round(float(x), n)  # noqa: E731

agg = load_zps_aggregates()
scen = dimension_scenarios()
stalls = float(sum(x["soucet_ps_zps"] for x in agg["useky_dle_typzony"]))

gaps = [r(g, 3) for g in np.linspace(0.5, 1.0, 51)]
gap = {name: {"central": [r(pitch_model(stalls, d["delka_zaklad"], d["delka_dnes"], g, PARALLEL_SHARE_CENTRAL).lost, 1) for g in gaps],
              "share_050": [r(pitch_model(stalls, d["delka_zaklad"], d["delka_dnes"], g, 0.50).lost, 1) for g in gaps],
              "share_085": [r(pitch_model(stalls, d["delka_zaklad"], d["delka_dnes"], g, 0.85).lost, 1) for g in gaps]}
       for name, d in scen.items()}

_, net = net_area(agg)
park = scen["te_park"]
lengths = [pitch_model(stalls, park["delka_zaklad"], park["delka_dnes"], g, s).lost
           for g in (0.5, GAP_CENTRAL_M, 1.0) for s in (0.50, 0.68, 0.85)]
areas = [area_model(net, stalls, park["delka_zaklad"], park["sirka_zaklad"], park["delka_dnes"], park["sirka_dnes"],
                    overhead=o).lost for o in ("absolutni", "pomerna")]
models = {"length": {"central": r(pitch_model(stalls, park["delka_zaklad"], park["delka_dnes"], GAP_CENTRAL_M,
                                              PARALLEL_SHARE_CENTRAL).lost, 1), "lo": r(min(lengths), 1), "hi": r(max(lengths), 1)},
          "area": {"central": r(np.mean(areas), 1), "lo": r(min(areas), 1), "hi": r(max(areas), 1)}}

length = load_te_series("delka_m")
yrs = list(range(2005, 2026))
fleet = {s: [r(fleet_dimension(y, length, shape=s)) for y in yrs] for s in ("weibull", "exponential", "uniform")}
lag = {"years": yrs, "new_car": [r(length.at(y)) for y in yrs], "fleet": fleet,
       "age": [r(mean_fleet_age_at(y), 2) for y in yrs]}

_, by = capacity_tables(agg)
fr = by[by["soucet_ps_zps"] >= 1000].sort_values("plocha_na_stani_m2")
gross = sum(x["plocha_m2"] for x in agg["useky_dle_typzony"])
districts = {"rows": [{"district": d, "m2_per_stall": r(a, 2), "stalls": int(n)}
                      for d, a, n in zip(fr["KODMC_T"], fr["plocha_na_stani_m2"], fr["soucet_ps_zps"])],
             "city_mean": r(gross / stalls, 2)}

width = load_te_series("sirka_m")
wy = list(range(2005, 2041))
widths = {"years": wy, "new_car": [r(width.at(y)) for y in wy], "fleet": [r(fleet_dimension(y, width)) for y in wy],
          "mirrors_m": 0.20, "stall_m": 2.00, "design_vehicle_m": 1.75}

OUT.write_text(json.dumps({"source": "parking project, make_figures_web.py model calls", "stalls": stalls, "gaps_m": gaps,
                           "gap_sensitivity": gap, "model_comparison": models, "fleet_lag": lag, "districts": districts,
                           "width": widths}, ensure_ascii=False, indent=1))
print("wrote", OUT, models)
