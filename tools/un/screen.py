"""Screening of the UN votes study (design §3), before any agreement is summarised and without reading a Czech
position: Czechia's rows are dropped in the query that reads the file, except for one count of its rows per period
(the column of positions is not selected). Writes docs/research/un-votes-screen.json.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with numpy python tools/un/screen.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from votes import EU27, FILE, ROOT, SHA256, load, positions  # noqa: E402

OUT = ROOT / "docs/research/un-votes-screen.json"
PARTNERS = ("USA", "RUS", "HUN", "SVK")
PERIODS = {"sobotka": ("2014-01-29", "2017-12-12"), "buffer_2017": ("2017-12-13", "2018-01-11"),
           "babis": ("2018-01-12", "2021-12-16"), "buffer_2021": ("2021-12-17", "2022-01-15"),
           "fiala": ("2022-01-16", "2025-12-14"), "after_2025_12_15": ("2025-12-15", "2026-12-31")}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def czech_rows(period: tuple[str, str]) -> int:
    """How many votes list Czechia at all; its position is not selected."""
    import duckdb
    return int(duckdb.sql(f"""
        SELECT count(DISTINCT undl_id) FROM read_csv('{FILE}', header = true, all_varchar = true)
        WHERE ms_code = 'CZE' AND CAST(date AS DATE) BETWEEN DATE '{period[0]}' AND DATE '{period[1]}'
    """).fetchone()[0])


def main() -> None:
    digest = sha256(FILE)
    assert digest == SHA256, "not version 5 of the file"
    df = load(drop=("CZE",))
    assert "CZE" not in set(df["ms_code"])
    m, info, dup = positions(df)
    dates = info["date"]
    eu = [c for c in EU27 if c in m.columns]
    vals = m[eu].to_numpy()
    split = np.array([len(set(r[r >= 0])) > 1 for r in vals])
    out = {"sha256": digest, "rows": int(len(df)), "votes": int(len(m)), "duplicates": dup,
           "codes": sorted(df["ms_vote"].dropna().unique().tolist()),
           "votes_by_session": {str(k): int(v) for k, v in info["session"].value_counts().sort_index().items()},
           "votes_by_year": {str(k): int(v) for k, v in dates.dt.year.value_counts().sort_index().items()},
           "eu27_present": {c: bool(c in m.columns) for c in EU27 if c != "CZE"},
           "partners_present": {p: bool(p in m.columns) for p in PARTNERS}, "periods": {}}
    # a vote outside its session's span: regular session n runs from September of 1945 + n to the next September
    reg = info["session"].str.fullmatch(r"\d+")
    year = info.loc[reg, "session"].astype(int) + 1945
    outside = info.loc[reg][(dates[reg] < pd.to_datetime(year.astype(str) + "-09-01"))
                            | (dates[reg] > pd.to_datetime((year + 1).astype(str) + "-09-30"))]
    out["outside_session_span"] = [{"undl_id": str(i), "session": r.session, "date": str(r.date.date())}
                                   for i, r in outside.iterrows()]
    for name, (a, b) in PERIODS.items():
        inside = ((dates >= a) & (dates <= b)).to_numpy()
        x_share = {c: round(float((m.loc[inside, c] < 0).mean()), 4) for c in eu if inside.any()}
        out["periods"][name] = {"from": a, "to": b, "votes": int(inside.sum()),
                                "split_without_czechia": int(split[inside].sum()),
                                "split_share": round(float(split[inside].mean()), 4) if inside.any() else None,
                                "votes_listing_czechia": czech_rows((a, b)),
                                "x_share_comparison": x_share}
        print(name, out["periods"][name]["votes"], out["periods"][name]["split_without_czechia"])
    print("duplicates", dup, "outside span", len(out["outside_session_span"]))
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
