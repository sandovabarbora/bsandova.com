"""prepare.screen and estimate.run on made-up records and a made-up parquet (no register record is read).

    uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pandas==3.0.6 --with pyarrow==26.0.0 \
        --with pytest==9.1.1 pytest -q tools/procurement/test_pipeline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate  # noqa: E402
import prepare  # noqa: E402
from synth_contracts import World, draw  # noqa: E402


def record(**kw) -> dict:
    base = {"id": "1", "version": "1", "valid": True, "concluded": "2024-03-01", "value_raw": "1500000",
            "value_vat": "1815000", "no_price": False, "foreign": False, "linked": False, "number": "S-1",
            "parties": "111|222", "payer_flag": False, "authority": "222", "dump": "d", "not_purchase": False,
            "framework": False, "call_off": False, "periodic": False, "works": False}
    return base | kw


def test_screen_dedupes_only_with_a_contract_number_and_counts_exact_millions_apart():
    rows = pd.DataFrame([
        record(id="1"), record(id="2"),  # same content key with a number: one flagged
        record(id="3", number="", value_raw="700000"), record(id="4", number="", value_raw="700000"),  # no number
        record(id="5", value_raw="3000000", number="X"), record(id="6", value_raw="3000000", number="X"),
        record(id="7", version="1", value_raw="900000"), record(id="7", version="2", value_raw="950000"),
        record(id="8", authority=None, number="A"), record(id="9", not_purchase=True, number="B"),
        record(id="10", concluded="2025-02-01", number="C"),
        record(id="11", call_off=True, framework=True, periodic=True, linked=True, value_raw="1815000"),
        record(id="12", valid=False, number="D"),
    ])
    df, steps = prepare.screen(rows)
    dup = steps["content-key duplicates flagged (dropped in the primary)"]
    assert dup == {"at an exact whole million": 1, "other values": 1}
    assert set(df.loc[df["content_duplicate"], "id"]) <= {"1", "2", "5", "6"}
    assert not df.loc[df["id"].isin(["3", "4"]), "content_duplicate"].any()
    assert df.loc[df["id"] == "7", "value"].tolist() == [950000.0]
    assert "8" not in set(df["id"]) and steps["no publishing IČO (dropped)"] == 1
    assert "9" not in set(df["id"]) and "10" not in set(df["id"]) and "12" not in set(df["id"])
    r11 = df[df["id"] == "11"].iloc[0]
    assert r11["call_off"] and r11["framework"] and r11["periodic"] and r11["linked"] and r11["equal_values"]
    assert "parties" not in df.columns  # minimised: no party identifiers are written


@pytest.fixture(scope="module")
def synthetic_root(tmp_path_factory):
    v, a, p = draw(World(n_pre=80_000, n_post=20_000, move={"pre": 0.3, "post": 0.3}, move_exact=1.0), 7)
    rng = np.random.default_rng(0)
    start = np.where(p == "pre", np.datetime64("2020-01-01"), np.datetime64("2025-07-01"))
    span = np.where(p == "pre", 1826, 365)
    dates = start + (rng.random(len(p)) * span).astype("timedelta64[D]")
    n = len(v)
    df = pd.DataFrame({"id": np.arange(n).astype(str), "authority": a.astype(str),
                       "concluded": pd.Series(dates).dt.strftime("%Y-%m-%d"), "period": p, "value": v,
                       "value_vat": v * 1.21, "content_duplicate": False,
                       **{f: rng.random(n) < 0.1 for f in ("linked", "call_off", "framework", "periodic", "equal_values")},
                       "payer_flag": rng.random(n) < 0.5, "works": rng.random(n) < 0.3, "dump": "synthetic"})
    vat_only = rng.random(n) < 0.2  # a fifth of the records carry only a VAT-inclusive price
    df.loc[vat_only, "value"] = np.nan
    root = tmp_path_factory.mktemp("root")
    (root / "tools" / "data" / "procurement").mkdir(parents=True)
    (root / "docs" / "research").mkdir(parents=True)
    df.to_parquet(root / "tools" / "data" / "procurement" / "contracts.parquet")
    return root


def test_a_registered_run_needs_the_data_step_mde(synthetic_root):
    with pytest.raises(SystemExit):
        estimate.run(False, synthetic_root, synthetic_root / "missing.json")


def test_quick_writes_nothing_and_r_vat_adds_the_vat_only_records(synthetic_root):
    out = estimate.run(True, synthetic_root, synthetic_root / "missing.json")
    assert not (synthetic_root / "docs" / "research" / "procurement-bunching-results.json").exists()
    rvat = out["robustness"]["R-VAT: VAT-only prices added, / 1.21"]
    assert "failed" not in rvat
    assert rvat["D_new_a"]["estimate"] != out["robustness"]["no content-key deduplication"]["D_new_a"]["estimate"]
    assert set(out["sensitivity"]) >= {"rows_that_flip", "sensitive", "failed_rows", "start_rows",
                                       "placebo_date_inside_margin"}


def test_sensitivity_counts_label_flips_and_reads_start_rows_by_direction():
    primary = {"label": "supported", "estimate": 0.3}
    def row(lab, est=0.3, ci90=(-0.1, 0.1)):
        return {"calibrated_D_new_a": {"label": lab, "estimate": est}, "D_new_a": {"ci90": ci90}}
    rows = {"window 2.5 % below": row("supported"), "polynomial degree 5": row("inconclusive"),
            "polynomial degree 9": row("not supported"), "R-VAT: VAT-only prices added, / 1.21": {"failed": "undefined k"},
            "post from 3 April 2025": row("inconclusive", est=0.2), "post from 1 October 2025": row("supported", est=0.25),
            "placebo date 1 January 2023 (pre only)": row("inconclusive", ci90=(-0.05, 0.12))}
    s = estimate.sensitivity(rows, primary)
    assert s["rows_that_flip"] == ["polynomial degree 5", "polynomial degree 9"] and not s["sensitive"]
    assert s["failed_rows"] == ["R-VAT: VAT-only prices added, / 1.21"]
    assert s["start_rows"] == {"post from 3 April 2025": "consistent", "post from 1 October 2025": "not consistent"}
    assert s["placebo_date_inside_margin"]
    rows["linked records dropped"] = row("inconclusive")
    assert estimate.sensitivity(rows, primary)["sensitive"]


def test_a_registered_run_writes_results_with_the_mde(synthetic_root):
    power = synthetic_root / "power.json"
    power.write_text(json.dumps({"data_step_mde": {"D_new_a": 0.1, "D_old_a": 0.1}}))
    out = estimate.run(False, synthetic_root, power)
    saved = json.loads((synthetic_root / "docs" / "research" / "procurement-bunching-results.json").read_text())
    assert saved["decision"]["D_new_a"]["label"] == out["decision"]["D_new_a"]["label"]
    assert len(saved["robustness"]) == len(out["robustness"]) == 21
    assert saved["hlidac"]["skipped"] and saved["type_cross_check"]["hlidac"] == "skipped"
    assert saved["type_cross_check"]["stems"] in {"passes", "fails", "not available"}


def test_a_hlidac_classification_adds_two_type_rows_and_a_cross_check(synthetic_root):
    df = pd.read_parquet(synthetic_root / "tools" / "data" / "procurement" / "contracts.parquet")
    rng = np.random.default_rng(1)
    sample = df.sample(30_000, random_state=1)
    works = pd.array(np.where(rng.random(len(sample)) < 0.05, None, rng.random(len(sample)) < 0.3), dtype="boolean")
    hl = synthetic_root / "tools" / "data" / "procurement" / "hlidac_types.parquet"
    pd.DataFrame({"id": sample["id"].to_numpy(), "works": works}).to_parquet(hl, index=False)
    try:
        out = estimate.run(True, synthetic_root, synthetic_root / "missing.json")
    finally:
        hl.unlink()
    assert len(out["robustness"]) == 23 and out["hlidac"]["classified_in_primary"] > 0
    assert out["type_cross_check"]["hlidac"] in {"passes", "fails", "not available"}
    assert not set(estimate.TYPE_ROWS["hlidac"]) & set(out["sensitivity"]["rows_that_flip"])
