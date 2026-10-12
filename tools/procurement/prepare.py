"""Registr smluv dumps → one row per contract, with the screening of design §4. Not run before registration.

    nice -n 20 uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pandas==3.0.6 --with pyarrow==26.0.0 \
        python tools/procurement/prepare.py [--totals-to-power]

Writes tools/data/procurement/contracts.parquet (minimised: no party, no name, no subject text) and
docs/research/procurement-bunching-screen.json (counts after each step and shares by period over all values, never a
count by value inside the analysis range). --totals-to-power passes the numbers of contracts in the range and of
authorities straight to power.py's data step (§9.4), so nobody sees them before the results. Prints only "ok".
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "procurement"
NS = "{http://portal.gov.cz/rejstriky/ISRS/1.2/}"
PERIODS = {"pre": (date(2020, 1, 1), date(2024, 12, 31)), "transition": (date(2025, 4, 3), date(2025, 6, 30)),
           "post": (date(2025, 7, 1), date(2026, 6, 30))}
COLUMNS = ["id", "authority", "concluded", "period", "value", "value_vat", "content_duplicate", "linked", "call_off",
           "framework", "periodic", "payer_flag", "works", "equal_values", "dump"]


def text(el, path: str) -> str | None:
    return el.findtext("/".join(f"{NS}{p}" for p in path.split("/")))


def records(path: Path):
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != f"{NS}zaznam":
            continue
        s = el.find(f"{NS}smlouva")
        subject = text(s, "predmet") or ""  # reduced to flags here; no subject text is kept
        parties = sorted({p.findtext(f"{NS}ico") or "" for p in s.findall(f"{NS}smluvniStrana")}
                         | {text(s, "subjekt/ico") or ""})
        yield {
            "id": text(el, "identifikator/idSmlouvy"), "version": text(el, "identifikator/idVerze"),
            "valid": text(el, "platnyZaznam") == "1", "concluded": text(s, "datumUzavreni"),
            "value_raw": text(s, "hodnotaBezDph"), "value_vat": text(s, "hodnotaVcetneDph"),
            "no_price": s.find(f"{NS}cenaNeuvedena") is not None, "foreign": s.find(f"{NS}ciziMena") is not None,
            "linked": el.find(f"{NS}navazanyZaznam") is not None or s.find(f"{NS}navazanyZaznam") is not None,
            "number": (text(s, "cisloSmlouvy") or "").strip(), "parties": "|".join(parties),
            "payer_flag": text(s, "subjekt/platce") == "1", "authority": text(s, "subjekt/ico"), "dump": path.name,
            **rules.flags(subject),
        }
        el.clear()


def screen(rows: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """§4 on a table of records (as yielded by records()); returns the minimised table and the step counts."""
    steps = {"records": len(rows)}
    rows = rows[rows["valid"]].copy()
    steps["valid version"] = len(rows)
    rows["version_n"] = pd.to_numeric(rows["version"], errors="coerce")
    rows = rows.sort_values("version_n").drop_duplicates("id", keep="last")
    steps["latest version per contract"] = len(rows)
    # §4.3: a content key needs a contract number; without one, two genuine contracts can share the rest
    key = ["parties", "concluded", "number", "value_raw"]
    keyed = rows["value_raw"].notna() & rows["number"].ne("")
    rows["content_duplicate"] = keyed & rows.duplicated(key, keep="last")
    v = pd.to_numeric(rows["value_raw"], errors="coerce")
    at_million = (v - (v / 1e6).round() * 1e6).abs().lt(0.5)
    steps["content-key duplicates flagged (dropped in the primary)"] = {
        "at an exact whole million": int((rows["content_duplicate"] & at_million).sum()),
        "other values": int((rows["content_duplicate"] & ~at_million).sum())}
    d = pd.to_datetime(rows["concluded"].str[:10], errors="coerce").dt.date
    rows["period"] = None
    for name, (lo, hi) in PERIODS.items():
        rows.loc[(d >= lo) & (d <= hi), "period"] = name
    rows = rows[rows["period"].notna()]
    steps["dated in a period"] = len(rows)
    rows["value"] = pd.to_numeric(rows["value_raw"], errors="coerce")
    rows["value_vat"] = pd.to_numeric(rows["value_vat"], errors="coerce")
    czk = ~rows["foreign"] & ~rows["no_price"]
    steps["presence by period (all values)"] = {
        p: {"records": int((rows["period"] == p).sum()),
            "share with value without VAT": float(rows.loc[czk & (rows["period"] == p), "value"].gt(0).mean()),
            "share with VAT-inclusive value only": float((rows.loc[czk & (rows["period"] == p), "value"].isna()
                                                          & rows.loc[czk & (rows["period"] == p), "value_vat"].gt(0)).mean())}
        for p in PERIODS}
    rows = rows[czk]
    steps["CZK with a price"] = len(rows)
    steps["subject excluded as not a purchase (§4.5)"] = int(rows["not_purchase"].sum())
    rows = rows[~rows["not_purchase"]]
    missing = rows["authority"].isna() | rows["authority"].astype(str).str.strip().eq("")
    steps["no publishing IČO (dropped)"] = int(missing.sum())
    rows = rows[~missing]
    for f in ("linked", "call_off", "framework", "periodic", "payer_flag", "works"):
        steps[f"flag {f} (kept)"] = int(rows[f].sum())
    rows["equal_values"] = rows["value"].notna() & (rows["value"] - rows["value_vat"]).abs().lt(0.005)
    steps["flag value without VAT equals value with VAT (kept)"] = int(rows["equal_values"].sum())
    return rows[COLUMNS].reset_index(drop=True), steps


def totals(df: pd.DataFrame) -> tuple[int, int, int]:
    """Numbers of primary contracts in the range by period, and of authorities: for power.py only, never printed."""
    import bunching as bu
    m = df["value"].gt(bu.LO) & df["value"].le(bu.HI) & ~df["content_duplicate"] & df["period"].isin(["pre", "post"])
    return (int((m & (df["period"] == "pre")).sum()), int((m & (df["period"] == "post")).sum()),
            int(df.loc[m, "authority"].nunique()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--totals-to-power", action="store_true")
    a = ap.parse_args()
    rows = pd.DataFrame([r for p in sorted(DATA.glob("dump_20*.xml")) for r in records(p)])
    df, steps = screen(rows)
    df.to_parquet(DATA / "contracts.parquet", index=False)
    (ROOT / "docs" / "research" / "procurement-bunching-screen.json").write_text(json.dumps(steps, indent=1))
    if a.totals_to_power:
        import power
        power.data_step(*totals(df))
    else:
        print("ok")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
