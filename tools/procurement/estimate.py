"""The registered analysis (design §5–§10) on tools/data/procurement/contracts.parquet. Not run before registration.

    OMP_NUM_THREADS=2 nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pandas==3.0.6 \
        --with pyarrow==26.0.0 python tools/procurement/estimate.py [--quick]

--quick is a crash check: 99 draws for every row, nothing written, and the only output is "ok". The registered run
uses 999 draws for the primary row and 199 for the others, and writes procurement-bunching-results.json after every
row, so a later failure keeps what came before.
"""
from __future__ import annotations

import argparse
import json
import subprocess
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
             "D_old_a_works", "D_new_b_supplies_services", "D_new_b_works", "k_low", "k_high", "k_low_minus_high",
             "placebo_a_mean", "placebo_a_sd", "placebo_b_mean", "controls_a_pre", "controls_a_post",
             "controls_b_pre", "controls_b_post"]
ROW_KEYS = ["D_new_a", "D_old_a", "D_new_b", "D_old_b", "D_new_a_supplies_services", "D_new_a_works",
            "D_new_b_supplies_services", "D_new_b_works"]
START_ROWS = {"post from 3 April 2025": "at most", "post from 1 October 2025": "at least"}
TYPE_ROWS = {"stems": ("type split: works by subject stems", "type split: supplies and services by subject stems"),
             "hlidac": ("type split: works by Hlídač classification (sample)",
                        "type split: supplies and services by Hlídač classification (sample)")}
NOT_COUNTED = {*START_ROWS, "placebo date 1 January 2023 (pre only)", *TYPE_ROWS["stems"], *TYPE_ROWS["hlidac"]}


def provenance(root: Path) -> dict:
    """The commit the run used and whether the working tree was clean (added 13 October 2026, after the registered
    run, which predates it)."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"), "clean_tree": git("status", "--porcelain", "--untracked-files=no") == ""}


def summarise(point: dict, ci: dict, keys: list[str]) -> dict:
    return {k: {"estimate": point[k], **{n: list(v) if isinstance(v, tuple) else v for n, v in ci.get(k, {}).items()}}
            for k in keys if k in point}


def arrays(df: pd.DataFrame):
    return df["value"].to_numpy(float), df["authority"].to_numpy(object), df["period"].to_numpy()


def ungated(point: dict, ci: dict) -> dict:
    """Calibrated D_new_a and its label without gate or underpowered rule: the basis of the sensitivity count."""
    cal = bu.calibrate(point, ci, "D_new_a")
    return {"estimate": cal["estimate"], "ci95": list(cal["ci95"]),
            "label": bu.label(cal["ci95"], cal["ci90"])[0]}


def sensitivity(rows: dict, primary: dict) -> dict:
    """§10. A counted row flips if its ungated label differs from the primary's; failed rows are listed apart. The two
    start-date rows read by direction instead: 3 April at most the primary, 1 October at least the primary. The
    placebo date reads by the "not supported" rule (its 90 % interval inside ±0.15)."""
    ok = {n: r for n, r in rows.items() if "failed" not in r}
    flips = [n for n, r in ok.items() if n not in NOT_COUNTED and r["calibrated_D_new_a"]["label"] != primary["label"]]
    starts = {}
    for n, rule in START_ROWS.items():
        if n in ok:
            e = ok[n]["calibrated_D_new_a"]["estimate"]
            starts[n] = "consistent" if (e <= primary["estimate"] if rule == "at most" else e >= primary["estimate"]) \
                else "not consistent"
    placebo = ok.get("placebo date 1 January 2023 (pre only)")
    placebo_ok = placebo is not None and -bu.MARGIN < placebo["D_new_a"]["ci90"][0] and placebo["D_new_a"]["ci90"][1] < bu.MARGIN
    return {"rows_that_flip": flips, "sensitive": len(flips) >= 3,
            "failed_rows": [n for n, r in rows.items() if "failed" in r], "start_rows": starts,
            "placebo_date_inside_margin": bool(placebo_ok)}


def cross_check(rows: dict, works_row: str, other_row: str) -> str:
    """§7.6: within works no response is expected at 3 M, within supplies and services none at 9 M; each passes if its
    90 % interval lies inside ±0.15."""
    def inside(row, key):
        r = rows.get(row, {})
        return "failed" not in r and key in r and -bu.MARGIN < r[key]["ci90"][0] and r[key]["ci90"][1] < bu.MARGIN
    if any("failed" in rows.get(r, {"failed": 1}) for r in (works_row, other_row)):
        return "not available"
    ok = inside(works_row, "D_new_a_supplies_services") and inside(other_row, "D_new_a_works")
    return "passes" if ok else "fails"


def monthly_exact(df: pd.DataFrame) -> dict:
    """§7.6, descriptive: by month of conclusion, the share of contracts in the range priced at exactly each limit
    and at the control millions (pooled)."""
    r = df[(df["value"] > bu.LO) & (df["value"] <= bu.HI)]
    month = r["concluded"].str[:7]
    out = {name: (r["value"].sub(v).abs() < 0.5).groupby(month).mean().to_dict()
           for name, v in {"2M": 2e6, "3M": 3e6, "6M": 6e6, "9M": 9e6}.items()}
    ctrl = np.isin(np.round(r["value"]), np.array(bu.CONTROLS, float)) & bu.exact_million(r["value"].to_numpy())
    out["controls"] = pd.Series(ctrl, index=r.index).groupby(month).mean().to_dict()
    return out


def run(quick: bool, root: Path = ROOT, power_path: Path = POWER) -> dict:
    draws_main, draws_rob = (99, 99) if quick else (999, 199)
    power = json.loads(power_path.read_text()) if power_path.exists() else {}
    if "data_step_mde" not in power and not quick:
        raise SystemExit("data_step_mde missing: run prepare.py --totals-to-power first (§9.4)")
    out_path = root / "docs" / "research" / "procurement-bunching-results.json"
    df = pd.read_parquet(root / "tools" / "data" / "procurement" / "contracts.parquet")
    in_periods = df["period"].isin(["pre", "post"])
    # R-VAT is built before the primary filter, which drops records without a price without VAT
    vat_only = df[df["value"].isna() & df["value_vat"].gt(0) & in_periods & ~df["content_duplicate"]].assign(
        value=lambda x: x["value_vat"] / 1.21)
    priced = df[df["value"].gt(0)]
    main_df = priced[priced["period"].isin(["pre", "post"]) & ~priced["content_duplicate"]]

    point, ci = bu.estimate(*arrays(main_df), draws=draws_main)
    adjust = point["adjust"]
    decision = bu.decide(point, ci, power.get("data_step_mde"))
    primary_ungated = ungated(point, ci)
    out = {"provenance": provenance(root), "adjust": adjust, "decision": decision, "primary_ungated": primary_ungated,
           "secondary": summarise(point, ci, SECONDARY + list(bu.PLACEBO_KEYS)),
           "locations": {k: point[k] for k in point if k.startswith(("a_", "b_", "r_", "m_above_"))},
           "monthly_exact_share": monthly_exact(priced), "robustness": {}}

    def save():
        if not quick:
            out_path.write_text(json.dumps(out, indent=1, default=float))

    save()

    def rob(name: str, frame: pd.DataFrame, period=None, **kw) -> None:
        try:
            vv, aa, pp = arrays(frame)
            p, c = bu.estimate(vv, aa, pp if period is None else period, draws=draws_rob, **{"adjust": adjust, **kw})
            out["robustness"][name] = summarise(p, c, ROW_KEYS) | {"calibrated_D_new_a": ungated(p, c)}
        except (RuntimeError, ZeroDivisionError, KeyError) as e:
            out["robustness"][name] = {"failed": str(e) or "undefined k"}
        save()

    rob("window 2.5 % below", main_df, spec=bu.Spec(share_below=0.025))
    rob("window 10 % below", main_df, spec=bu.Spec(share_below=0.10))
    rob("polynomial degree 5", main_df, spec=bu.Spec(degree=5))
    rob("polynomial degree 9", main_df, spec=bu.Spec(degree=9))
    rob("other adjustment of a", main_df, adjust="difference" if adjust == "ratio" else "ratio")
    rob("neighbouring controls only", main_df, spec=bu.Spec(control_set="neighbours"))
    rob("VAT images excluded from the fit", main_df, spec=bu.Spec(exclude_vat_images=True))
    rob("R-VAT: VAT-only prices added, / 1.21", pd.concat([main_df, vat_only]))
    rob("equal with- and without-VAT values dropped", main_df[~main_df["equal_values"]])
    rob("no content-key deduplication", priced[priced["period"].isin(["pre", "post"])])
    with_transition = priced[priced["period"].isin(["pre", "post", "transition"]) & ~priced["content_duplicate"]]
    rob("post from 3 April 2025", with_transition.assign(period=lambda x: x["period"].replace("transition", "post")))
    rob("post from 1 October 2025", main_df[(main_df["period"] == "pre") | (main_df["concluded"].str[:10] >= "2025-10-01")])
    rob("pre 2022–2024 only", main_df[main_df["concluded"].str[:4] >= "2022"])
    counts = main_df["authority"].value_counts()
    rob("largest 1 % of authorities dropped", main_df[~main_df["authority"].isin(counts.index[: max(1, len(counts) // 100)])])
    rob("linked records dropped", main_df[~main_df["linked"]])
    rob("call-offs (objednávka) dropped", main_df[~main_df["call_off"]])
    rob("frameworks and periodic prices dropped", main_df[~main_df["framework"] & ~main_df["periodic"]])
    rob("authority flagged as payer only", main_df[main_df["payer_flag"]])
    pre = main_df[main_df["period"] == "pre"]
    rob("placebo date 1 January 2023 (pre only)", pre,
        period=np.where(pre["concluded"].str[:10] >= "2023-01-01", "post", "pre"))
    rob(TYPE_ROWS["stems"][0], main_df[main_df["works"]])
    rob(TYPE_ROWS["stems"][1], main_df[~main_df["works"]])
    out["type_cross_check"] = {"stems": cross_check(out["robustness"], *TYPE_ROWS["stems"])}
    hl_path = root / "tools" / "data" / "procurement" / "hlidac_types.parquet"
    if hl_path.exists():  # optional (§4.11): written by hlidac.py only when a token was present
        hl = pd.read_parquet(hl_path).dropna(subset=["works"]).rename(columns={"works": "hl_works"})
        typed = main_df.merge(hl, on="id")
        hw = typed["hl_works"].astype(bool)
        out["hlidac"] = {"classified_in_primary": int(len(typed)),
                         "agreement_with_stems": float((hw == typed["works"]).mean()) if len(typed) else None}
        rob(TYPE_ROWS["hlidac"][0], typed[hw])
        rob(TYPE_ROWS["hlidac"][1], typed[~hw])
        out["type_cross_check"]["hlidac"] = cross_check(out["robustness"], *TYPE_ROWS["hlidac"])
    else:
        out["hlidac"] = {"skipped": "no Hlídač státu classification (token absent or hlidac.py not run)"}
        out["type_cross_check"]["hlidac"] = "skipped"

    out["sensitivity"] = sensitivity(out["robustness"], primary_ungated)
    save()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    out = run(a.quick)
    if a.quick:
        print("ok")
        return
    d = out["decision"]
    print(json.dumps({h: d[h]["label"] for h in bu.PRIMARY} | {"gate_failed": d["gate_failed"],
                                                              "sensitive": out["sensitivity"]["sensitive"]}))


if __name__ == "__main__":
    main()
