"""Part 4 extended, addenda after the fact-check (30 Sep 2026): registered checks that were omitted from the first
runs, and raw descriptive ranks for H1. Nothing here enters the confirmatory family.

  - H5 with the wild score bootstrap clustered by the 57 city districts (registered sensitivity).
  - H6: Warsaw against the other Polish powiats, relative cumulative response of starts to lagged price growth
    (annual, 3 lags), with Warsaw's rank among all powiats given the same treatment.
  - H1: raw ranks of the annualised rate per resident (no model), Eurostat and ČSÚ-rebuilt numerators.

Updates assets/praha/housing_extended.json (H1 raw ranks) and assets/praha/housing_extended_robust.json (addenda).

Usage (from a worktree, point DATA at the main checkout's gitignored tools/data):
    DATA=/path/to/bsandova.com/tools/data uv run --with pandas --with numpy --with scipy --with statsmodels \
        --with pyarrow --with openpyxl --with shapely --with pyproj --with pyfixest --with arch \
        python tools/praha/housing_addenda.py
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from housing_extended import PRAGUE, RAW, ROOT, SEED, bdl, h1_design, h1_regions, h5  # noqa: E402

warnings.filterwarnings("ignore")
MAIN = ROOT / "assets" / "praha" / "housing_extended.json"
ROB = ROOT / "assets" / "praha" / "housing_extended_robust.json"
WARSAW_UNIT = "071412865000"


def raw_ranks() -> dict:
    reg = h1_regions()
    out = {}
    for level, key, prague in (("metro", "metro", "CZ001MC"), ("core", "core", PRAGUE)):
        d = reg[key][reg[key].in_primary]
        d = d[~d.index.duplicated()]
        for label in ("eurostat", "csu_rebuilt"):
            dd = d.copy()
            if label == "csu_rebuilt":
                dd.loc[dd.country == "CZ", "num_eu"] = dd.loc[dd.country == "CZ", "num_csu"]
            y, X = h1_design(dd)
            ok = y.notna() & X.notna().all(axis=1)
            rate = np.exp(y[ok])
            out[f"{level}_{label}"] = {"n": int(len(rate)), "prague_rate": round(float(rate[prague]), 2),
                                       "rank_from_lowest": int((rate < rate[prague]).sum() + 1),
                                       "median": round(float(rate.median()), 2)}
    return out


def h5_city_districts(rng) -> dict:
    cells = pd.read_parquet(RAW / "prague_cells.parquet")
    r = h5(rng, cells, clusters=cells.city_district.to_numpy())
    return {k: r[k] for k in ("gamma", "p_conley_negative", "p_wcr_negative", "p", "clusters",
                              "effective_clusters")}


def warsaw(lags: int = 3) -> dict:
    import pyfixest as pf

    s = bdl(747729).rename(columns={"val": "S"})
    p = bdl(633677).sort_values(["unit", "year"])
    p["dlp"] = p.groupby("unit").val.transform(lambda v: np.log(v).diff())
    st = bdl(60811).sort_values(["unit", "year"])
    st["stock_lag"] = st.groupby("unit").val.shift(1)
    d = s.merge(st[["unit", "year", "stock_lag"]], on=["unit", "year"])
    wide = p.pivot(index="unit", columns="year", values="dlp")
    for lag in range(1, lags + 1):
        d[f"l{lag}"] = [wide.loc[u, y - lag] if u in wide.index and (y - lag) in wide.columns else np.nan
                        for u, y in zip(d.unit, d.year)]
    first = int(wide.columns.min()) + 1 + lags  # first year with all lags of a defined change
    d = d[d.year.between(first - 1, 2024) & (d.stock_lag > 0)].dropna()
    d["lnstock"] = np.log(d.stock_lag)
    d = d[d.groupby("unit").S.transform("sum") > 0]
    cols = [f"l{lag}" for lag in range(1, lags + 1)]

    def rel(unit: str) -> float:
        dd = d.copy()
        for c in cols:
            dd[c + "t"] = dd[c] * (dd.unit == unit)
        f = pf.fepois(f"S ~ {' + '.join(cols + [c + 't' for c in cols])} | unit + year", data=dd,
                      offset="lnstock", vcov="iid")
        return float(sum(f.coef()[c + "t"] for c in cols)), float(sum(f.coef()[c] for c in cols))

    w_rel, rest = rel(WARSAW_UNIT)
    others = []
    for u in d.unit.unique():
        if u != WARSAW_UNIT:
            try:
                others.append(rel(u)[0])
            except Exception:  # noqa: BLE001 - a powiat whose interaction is not identified
                continue
    others = np.array(others)
    return {"years": [int(d.year.min()), int(d.year.max())], "lags_years": lags, "powiats": int(d.unit.nunique()),
            "warsaw_relative_cumulative": round(w_rel, 3), "rest_cumulative": round(rest, 3),
            "warsaw_rank_from_lowest": int((others < w_rel).sum() + 1), "ranked_powiats": int(len(others) + 1),
            "note": "starts (notified starts of works), a different concept from Czech permitted dwellings; "
                    "single treated unit, so no test; rank among all powiats given the same treatment"}


def main() -> None:
    rng = np.random.default_rng(SEED + 2)
    main_res = json.loads(MAIN.read_text())
    rob = json.loads(ROB.read_text())
    ranks = raw_ranks()
    main_res["H1"]["raw_rate_ranks"] = ranks
    add = {"date": "2026-09-29", "H5_city_district_clusters": h5_city_districts(rng), "H6_warsaw": warsaw()}
    rob["addenda"] = add
    MAIN.write_text(json.dumps(main_res, ensure_ascii=False, indent=1) + "\n")
    ROB.write_text(json.dumps(rob, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"raw": ranks, **add}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
