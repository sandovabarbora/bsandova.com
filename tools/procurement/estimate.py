"""The registered analysis (design §5–§10) on tools/data/procurement/contracts.parquet. Not run before registration.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pandas==3.0.6 \
        --with pyarrow==26.0.0 python tools/procurement/estimate.py [--quick]

--quick is a crash check: 99 draws for every row, nothing written, and the only output is "ok". The registered run
uses 999 draws for the primary row and 199 for the others, and writes procurement-bunching-results.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bunching as bu  # noqa: E402

ROOT = HERE.parents[1]
POWER = ROOT / "docs" / "research" / "procurement-bunching-power.json"
SECONDARY = ["D_new_b", "D_old_b", "D_new_a_supplies_services", "D_new_a_works", "D_old_a_supplies_services",
             "D_old_a_works", "D_new_b_supplies_services", "D_new_b_works", "k_low_minus_high",
             "controls_a_pre", "controls_a_post", "controls_b_pre", "controls_b_post"]
ROW_KEYS = ["D_new_a", "D_old_a", "D_new_b", "D_old_b", "D_new_a_supplies_services", "D_new_a_works",
            "D_new_b_supplies_services", "D_new_b_works"]
NOT_SENSITIVITY = {"placebo date 1 January 2023 (pre only)", "type split: works by subject stems",
                   "type split: supplies and services by subject stems"}


def summarise(point: dict, ci: dict, keys: list[str]) -> dict:
    return {k: {"estimate": point[k], **{n: list(v) if isinstance(v, tuple) else v for n, v in ci.get(k, {}).items()}}
            for k in keys}


def arrays(df: pd.DataFrame):
    return df["value"].to_numpy(float), df["authority"].fillna("?").to_numpy(), df["period"].to_numpy()


def monthly_exact(df: pd.DataFrame) -> dict:
    """§7.6, descriptive: by month of conclusion, the share of contracts in the range priced at exactly each limit
    and at the control millions (pooled)."""
    in_range = df[(df["value"] > bu.LO) & (df["value"] <= bu.HI)]
    month = in_range["concluded"].str[:7]
    out = {}
    for name, v in {"2M": 2e6, "3M": 3e6, "6M": 6e6, "9M": 9e6}.items():
        out[name] = (in_range["value"].sub(v).abs() < 0.5).groupby(month).mean().to_dict()
    ctrl = np.isin(np.round(in_range["value"]), np.array(bu.CONTROLS, float)) & bu.exact_million(in_range["value"].to_numpy())
    out["controls"] = pd.Series(ctrl, index=in_range.index).groupby(month).mean().to_dict()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    draws_main, draws_rob = (99, 99) if a.quick else (999, 199)
    power = json.loads(POWER.read_text()) if POWER.exists() else {}
    if "data_step_mde" not in power and not a.quick:
        raise SystemExit("data_step_mde missing: run power.py <n_pre> <n_post> first (§9.3)")
    mde = power.get("data_step_mde", {})
    df = pd.read_parquet(ROOT / "tools" / "data" / "procurement" / "contracts.parquet")
    df = df[df["value"].gt(0)]
    main_df = df[df["period"].isin(["pre", "post"])]
    v, auth, per = arrays(main_df)

    point, ci = bu.estimate(v, auth, per, draws=draws_main)
    adjust = point["adjust"]
    gate = bu.gate_failed(point, ci)
    labels = {}
    for h in bu.PRIMARY:
        lab, note = bu.label(ci[h]["ci95"], ci[h]["ci90"], underpowered=mde.get(h, 0.0) > bu.UNDERPOWERED_MDE,
                             gate=gate)
        labels[h] = {"label": lab, "note": note}
    placebos = [k for k in point if k.startswith("placebo_")]
    out = {"adjust": adjust, "gate_failed": gate, "labels": labels,
           "primary": summarise(point, ci, list(bu.PRIMARY)), "secondary": summarise(point, ci, SECONDARY + placebos),
           "locations": {k: point[k] for k in point if k.startswith(("a_", "b_", "r_", "m_above_"))},
           "monthly_exact_share": monthly_exact(df), "robustness": {}}

    def rob(name: str, frame: pd.DataFrame = main_df, period=None, **kw) -> None:
        vv, aa, pp = arrays(frame)
        p, c = bu.estimate(vv, aa, pp if period is None else period, draws=draws_rob, **{"adjust": adjust, **kw})
        out["robustness"][name] = summarise(p, c, ROW_KEYS)

    rob("window 2.5 % below", spec=bu.Spec(share_below=0.025))
    rob("window 10 % below", spec=bu.Spec(share_below=0.10))
    rob("polynomial degree 5", spec=bu.Spec(degree=5))
    rob("polynomial degree 9", spec=bu.Spec(degree=9))
    rob("other adjustment of a", adjust="difference" if adjust == "ratio" else "ratio")
    rob("neighbouring controls only", spec=bu.Spec(control_set="neighbours"))
    rob("VAT images excluded from the fit", spec=bu.Spec(exclude_vat_images=True))
    vat_only = df[df["value"].isna() & df["value_vat"].gt(0) & df["period"].isin(["pre", "post"])].assign(
        value=lambda x: x["value_vat"] / 1.21)
    rob("R-VAT: VAT-only prices added, / 1.21", pd.concat([main_df, vat_only]))
    rob("equal with- and without-VAT values dropped", main_df[~main_df["equal_values"]])
    with_transition = df[df["period"].isin(["pre", "post", "transition"])].assign(
        period=lambda x: x["period"].replace("transition", "post"))
    rob("post from 3 April 2025", with_transition)
    rob("post from 1 October 2025", main_df[(main_df["period"] == "pre") | (main_df["concluded"].str[:10] >= "2025-10-01")])
    rob("pre 2022–2024 only", main_df[main_df["concluded"].str[:4].isin(["2022", "2023", "2024", "2025", "2026"])])
    counts = main_df["authority"].value_counts()
    rob("largest 1 % of authorities dropped", main_df[~main_df["authority"].isin(counts.index[: max(1, len(counts) // 100)])])
    rob("linked records dropped", main_df[~main_df["linked"]])
    rob("call-offs (objednávka) dropped", main_df[~main_df["call_off"]])
    rob("frameworks and periodic prices dropped", main_df[~main_df["framework"] & ~main_df["periodic"]])
    rob("authority flagged as payer only", main_df[main_df["payer_flag"]])
    pre = main_df[main_df["period"] == "pre"]
    rob("placebo date 1 January 2023 (pre only)", pre,
        period=np.where(pre["concluded"].str[:10] >= "2023-01-01", "post", "pre"))
    rob("type split: works by subject stems", main_df[main_df["works"]])
    rob("type split: supplies and services by subject stems", main_df[~main_df["works"]])

    lo = ci["D_new_a"]["ci95"][0]
    flips = [n for n, r in out["robustness"].items() if n not in NOT_SENSITIVITY and (
        np.sign(r["D_new_a"]["estimate"]) != np.sign(point["D_new_a"]) or (lo > 0) != (r["D_new_a"]["ci95"][0] > 0))]
    out["sensitivity"] = {"rows_that_flip": flips, "sensitive": len(flips) >= 3}
    if a.quick:
        print("ok")
        return
    (ROOT / "docs" / "research" / "procurement-bunching-results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"labels": labels, "adjust": adjust, "gate_failed": gate, "sensitive": out["sensitivity"]["sensitive"]}))


if __name__ == "__main__":
    main()
