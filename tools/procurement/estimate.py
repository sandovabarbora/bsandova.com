"""The registered analysis (design §5–§8) on tools/data/procurement/contracts.parquet. Not run before registration.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pandas==3.0.6 \
        --with pyarrow==26.0.0 python tools/procurement/estimate.py [--quick]

--quick uses 99 bootstrap draws for every row (a check run whose output is not published); the registered run
uses 999 for the primary row and 199 for the robustness rows.
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
MDE_UNDERPOWERED = 0.30  # §9: a hypothesis whose data-step MDE exceeds this is labelled underpowered in advance


def summarise(point: dict, ci: dict, keys: list[str]) -> dict:
    return {k: {"estimate": point[k], **{n: list(v) if isinstance(v, tuple) else v for n, v in ci.get(k, {}).items()}}
            for k in keys}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    draws_main, draws_rob = (99, 99) if a.quick else (999, 199)
    df = pd.read_parquet(ROOT / "tools" / "data" / "procurement" / "contracts.parquet")
    main_rows = df[df["value"].gt(0)]
    v, auth, per = main_rows["value"].to_numpy(), main_rows["authority"].fillna("?").to_numpy(), main_rows["period"].to_numpy()
    keys = ["D_new", "D_old", "D_new_supplies_services", "D_new_works", "D_old_supplies_services", "D_old_works",
            "control_ratio", "placebo_controls", "controls_pooled_pre", "controls_pooled_post"]
    power = json.loads(POWER.read_text()) if POWER.exists() else {}
    under = {h: power.get("data_step_mde", {}).get(h, 0.0) > MDE_UNDERPOWERED for h in ("D_new", "D_old")}

    point, ci = bu.estimate(v, auth, per, draws=draws_main)
    adjust = "ratio"
    if ci["controls_pooled_pre"]["ci95"][0] <= 0:  # §6.2 fallback, decided before any D is read
        adjust = "difference"
        point, ci = bu.estimate(v, auth, per, draws=draws_main, adjust=adjust)
    gate = abs(point["placebo_controls"]) > bu.MARGIN and not (
        ci["placebo_controls"]["ci95"][0] <= 0 <= ci["placebo_controls"]["ci95"][1])
    labels = {h: ("inconclusive" if gate and not under[h] else
                  bu.label(ci[h]["ci95"], ci[h]["ci90"], underpowered=under[h])) for h in ("D_new", "D_old")}
    out = {"adjust": adjust, "placebo_gate_failed": gate, "labels": labels, "primary": summarise(point, ci, keys),
           "locations": {k: point[k] for k in point if k.startswith(("old_", "new_", "control_", "above_"))},
           "robustness": {}}

    def rob(name: str, values=v, authority=auth, period=per, **kw) -> None:
        p, c = bu.estimate(values, authority, period, draws=draws_rob, **{"adjust": adjust, **kw})
        out["robustness"][name] = summarise(p, c, ["D_new", "D_old", "placebo_controls"])

    rob("window 2.5 % below", spec=bu.Spec(share_below=0.025))
    rob("window 10 % below", spec=bu.Spec(share_below=0.10))
    rob("polynomial degree 5", spec=bu.Spec(degree=5))
    rob("polynomial degree 9", spec=bu.Spec(degree=9))
    rob("no control adjustment", adjust="none")
    rob("additive control adjustment", adjust="difference")
    rob("exact whole millions dropped", drop_exact_millions=True, adjust="difference")
    rob("VAT images excluded from the fit", spec=bu.Spec(exclude_vat_images=True))
    late = (per == "pre") | (pd.to_datetime(main_rows["concluded"].str[:10]) >= "2025-10-01").to_numpy()
    rob("post from 1 October 2025", v[late], auth[late], per[late])
    no_covid = ~pd.to_datetime(main_rows["concluded"].str[:10]).dt.year.isin([2020, 2021]).to_numpy()
    rob("pre 2022–2024 only", v[no_covid], auth[no_covid], per[no_covid])
    counts = pd.Series(auth).value_counts()
    small = ~np.isin(auth, counts.index[: max(1, len(counts) // 100)])
    rob("largest 1 % of authorities dropped", v[small], auth[small], per[small])
    vat_only = df[df["value"].isna() & df["value_vat"].gt(0)]
    rob("with VAT-only values / 1.21 (R-VAT)", np.r_[v, vat_only["value_vat"].to_numpy() / 1.21],
        np.r_[auth, vat_only["authority"].fillna("?").to_numpy()], np.r_[per, vat_only["period"].to_numpy()])
    pre_only = main_rows[main_rows["period"] == "pre"]
    fake = np.where(pd.to_datetime(pre_only["concluded"].str[:10]) >= "2023-01-01", "post", "pre")
    rob("placebo date 1 January 2023 (pre period only)", pre_only["value"].to_numpy(),
        pre_only["authority"].fillna("?").to_numpy(), fake)
    for kind, flag in (("works", True), ("supplies_services", False)):
        sub = main_rows["works"].to_numpy() == flag
        rob(f"type split: {kind} by subject keywords (§4.5)", v[sub], auth[sub], per[sub])
    (ROOT / "docs" / "research" / "procurement-bunching-results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"labels": labels, "adjust": adjust, "placebo_gate_failed": gate}, indent=1))


if __name__ == "__main__":
    main()
