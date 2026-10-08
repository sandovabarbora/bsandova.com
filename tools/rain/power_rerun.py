"""Power re-run of the rain-delays design (§7, change note of 6 October 2026), with the dispersion the data imply.

Reads tram units (units.parquet) WITHOUT the rain indicator: delay gained is regressed on the cell and date effects
of §4 only, and its residual is split into a city-wide date × hour shock (the mean residual of all units in that
hour; σ_c, with its hour-to-hour autocorrelation ρ within a date) and the unit-level rest (σ_e). The simulation of
power.py is then run with those values, the median number of tram units per date × hour, and the rain pattern of
the 170 dates left by §3 rule 2.

Writes docs/research/rain-delays-power-rerun.json.

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest --with numpy python tools/rain/power_rerun.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import power  # noqa: E402
from estimate import D, drop_singletons, frame, weather  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/research/rain-delays-power-rerun.json"
FEED = ROOT / "docs/research/rain-delays-screen-feed.json"


def dispersion(d: pd.DataFrame) -> dict:
    d = drop_singletons(d)
    m = pf.feols("y ~ 1 | cell + date_s", data=d)
    r = d.assign(res=d["y"].to_numpy() - m.predict())
    shock = r.groupby(["date", "hour"])["res"].mean().rename("c").reset_index()
    r = r.merge(shock, on=["date", "hour"])
    shock = shock.sort_values(["date", "hour"])
    same = shock["date"].eq(shock["date"].shift()) & shock["hour"].eq(shock["hour"].shift() + 1)
    rho = float(np.corrcoef(shock["c"][same], shock["c"].shift()[same])[0, 1])
    return {"sigma_e_s": float((r["res"] - r["c"]).std()), "sigma_c_s": float(shock["c"].std()), "rho": rho,
            "units_per_date_hour": int(r.groupby(["date", "hour"]).size().median()), "units": int(len(r))}


def main() -> None:
    units = pd.read_parquet(D / "units.parquet")
    wx = weather(power.precipitation())
    d = frame(units, wx, "tram")  # §3 rules applied; the weather columns are merged but not used below
    disp = dispersion(d)
    excluded = set(json.loads(FEED.read_text())["rule2_dates_excluded"])
    c = power.classify(power.precipitation())
    c = c[~pd.Series(c["date"]).astype(str).isin(excluded).to_numpy()]
    power.ROUTES = disp["units_per_date_hour"]
    rng = np.random.default_rng(power.SEED)
    se = power.se_sim(c, disp["sigma_e_s"], disp["sigma_c_s"], max(disp["rho"], 0.0), rng)
    res = {**{k: round(v, 3) if isinstance(v, float) else v for k, v in disp.items()},
           "dates": int(pd.Series(c["date"]).nunique()), "rain_dates": int(pd.Series(c.loc[c["rain"], "date"]).nunique()),
           "rain_hours": int(c["rain"].sum()), "dry_hours": int(c["dry"].sum()),
           "se_s": round(se, 2), "mde_s": round(2.80 * se, 1), "passes_30s_rule": 2.80 * se <= 30,
           "not_supported_reachable": 1.645 * se < 10}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
