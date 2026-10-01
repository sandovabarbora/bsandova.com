"""One row per application from the fund's decision tables (tools/film/collect_tables.py).

Each table has a header row naming the columns ("evidenční číslo projektu", "název projektu",
..., "bodové hodnocení Rada", "výše podpory"), a row of point ranges under the criteria
("0-40", ...) and one row per application. The criteria change between schemes, so they are
kept as (name, range, points) per application; the total and the award are fixed columns.

Output: tools/data/film/applications.parquet (+ .csv), and a log of every table that could
not be read, with the reason.

    uv run --no-project --with pandas --with openpyxl --with xlrd --with pyarrow \
        python tools/film/parse_tables.py
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "data" / "film"
CALL = re.compile(r"(20[12]\d)[-_ ]([A-D]|\d{1,2})[-_ ](\d{1,2})[-_ ](\d{1,2})(?:[-_ ](\d{1,3}))?")
RANGE = re.compile(r"^\s*0\s*[-–]\s*(\d+)\s*$")


def norm(x) -> str:
    s = "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)
    return " ".join(unicodedata.normalize("NFC", s).replace("\n", " ").split()).strip()


def num(x) -> float | None:
    s = norm(x).replace(" ", "").replace(" ", "").replace(",", ".").rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def call_id(name: str, title: str) -> str | None:
    for text in (title, name):
        m = CALL.search(text)
        if m:
            return "-".join(g for g in m.groups() if g)
    return None


def parse(path: Path, url: str) -> tuple[list[dict], str | None]:
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    v = next(iter(sheets.values()))
    title = norm(v.iat[0, 0]) if v.shape[0] else ""
    hdr = next((i for i in range(min(40, len(v)))
                if any("název projektu" in norm(c).lower() for c in v.iloc[i])), None)
    if hdr is None:
        return [], "no header row"
    head = [norm(c).lower() for c in v.iloc[hdr]]
    rng_row = next((j for j in range(hdr + 1, min(hdr + 5, len(v)))
                    if sum(bool(RANGE.match(norm(c))) for c in v.iloc[j]) >= 2), None)
    ranges = {k: int(RANGE.match(norm(c)).group(1)) for k, c in enumerate(v.iloc[rng_row])
              if RANGE.match(norm(c))} if rng_row is not None else {}

    def col(*keys, after: int = -1) -> int | None:
        return next((k for k, h in enumerate(head) if k > after and any(key in h for key in keys)), None)

    c_id, c_app, c_title = col("evidenční"), col("název žadatele", "žadatel"), col("název projektu")
    c_budget, c_req = col("celkový rozpočet"), col("požadovan")
    c_total = col("bodové hodnocení rada") or col("bodové hodnocení celkem", "celkem bod", "bodové hodnocení")
    c_award = col("výše podpory", "přidělená podpora", "výše dotace", after=c_total if c_total is not None else -1)
    if None in (c_title, c_total):
        return [], f"missing columns (title {c_title}, total {c_total})"
    crit = [k for k in sorted(ranges) if k < c_total]
    names = {k: head[k] or norm(v.iat[hdr + 1, k]) for k in crit}
    experts = [k for k, h in enumerate(head) if "expert" in h]
    cid = call_id(path.name, title)
    if cid is None:
        # some tables name the call only in their header block ("Evidenční číslo výzvy: 2016-2-1-2")
        cid = call_id("", " ".join(norm(c) for c in v.iloc[:hdr].values.ravel()))
    start = (rng_row if rng_row is not None else hdr) + 1
    rows = []
    for i in range(start, len(v)):
        r = v.iloc[i]
        t = norm(r.iat[c_title])
        total = num(r.iat[c_total])
        if not t or total is None:
            continue   # blank rows, sub-headers, the allocation and "remaining" lines
        award = num(r.iat[c_award]) if c_award is not None else None
        rows.append({
            "call": cid, "call_title": title, "file": path.name, "url": url,
            "app_id": norm(r.iat[c_id]) if c_id is not None else "",
            "applicant": norm(r.iat[c_app]) if c_app is not None else "",
            "title": t,
            "budget": num(r.iat[c_budget]) if c_budget is not None else None,
            "requested": num(r.iat[c_req]) if c_req is not None else None,
            "total": total,
            "award": award or 0.0,
            "funded": bool(award and award > 0),
            "criteria": json.dumps([{"name": names[k], "max": ranges[k], "points": num(r.iat[k])} for k in crit],
                                   ensure_ascii=False),
            "experts": json.dumps([norm(r.iat[k]) for k in experts if norm(r.iat[k])], ensure_ascii=False),
        })
    return rows, None if rows else "no application rows"


def main() -> None:
    manifest = list(csv.DictReader((DATA / "manifest.csv").open(encoding="utf-8")))
    out, log = [], []
    for m in manifest:
        if m["status"] != "200":
            continue
        try:
            rows, why = parse(DATA / "raw" / m["file"], m["url"])
        except Exception as e:   # noqa: BLE001 -- logged per table, never silent
            rows, why = [], f"error: {e}"[:200]
        out += rows
        if why:
            log.append({"file": m["file"], "reason": why})
    df = pd.DataFrame(out)
    # the same table can be linked from two pages under two paths: one copy per call and application
    df = df.drop_duplicates(subset=["call", "app_id", "title", "total", "award"])
    df.to_parquet(DATA / "applications.parquet", index=False)
    df.to_csv(DATA / "applications.csv", index=False)
    pd.DataFrame(log).to_csv(DATA / "parse_log.csv", index=False)
    print(f"{len(df)} applications from {df['file'].nunique()} tables, {df['call'].nunique()} calls; "
          f"{len(log)} tables skipped (parse_log.csv)")


if __name__ == "__main__":
    main()
