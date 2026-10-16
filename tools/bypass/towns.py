"""Treated and comparison towns of the bypass accidents study from construction facts only (design §2): which rows of
the frozen list enter, which towns are excluded and why, each town's event years, and the bypass clusters that the
bootstrap resamples (§4). No accident record is read here.

The registered stage is A (change log, 16 October 2026): police files from FIRST_YEAR (2016, found by fetch.py) to
LAST_YEAR, so a treated town needs its works to start in FIRST_YEAR + 2 or later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / "tools/bypass/bypasses.csv"
LIST_SHA256 = "485055ed073df50827a9443ae90f6cc33ec7b1b886a8e98cc1c8427909106033"
FIRST_YEAR, LAST_YEAR = 2016, 2025
PRE_YEARS = 2
OPENED = (2008, 2024)
CLASSES = ("I", "II")
COMPARISON_STAGES = ("in construction", "tender", "SP", "ÚR")
COHORTS = ((2008, 2010), (2011, 2013), (2014, 2016), (2017, 2019), (2020, 2022), (2023, 2024))
AREA_CHANGE = 0.02


def year_of(s) -> int | None:
    return int(str(s)[:4]) if isinstance(s, str) and s[:4].isdigit() else None


def month_of(s) -> int | None:
    return int(s[5:7]) if isinstance(s, str) and len(s) >= 7 else None


def codes(s) -> list[int]:
    """Municipality codes of a row; a blank between separators is a part of a municipality, not a code."""
    return [int(c) for c in str(s if isinstance(s, str) else "").split(";") if c.strip().isdigit()]


def cohort(open_year: int) -> str | None:
    for a, b in COHORTS:
        if a <= open_year <= b:
            return f"{a}-{b}"
    return None


def load_list(path: Path = LIST) -> pd.DataFrame:
    b = pd.read_csv(path, dtype=str)
    b["open_year"] = b["opened_date"].map(year_of)
    b["open_month"] = b["opened_date"].map(month_of)
    b["start_year"] = b["construction_start"].map(year_of)
    b["codes"] = b["municipality_code"].map(codes)
    return b


def is_full(b: pd.DataFrame, classes=CLASSES) -> pd.Series:
    return (b["kind"] == "full") & b["road_class"].isin(classes)


def staged_group(b: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    """§2 staged openings: earlier `partial` rows of the same road in the same town that already carry the through
    traffic belong to the bypass; the first of them gives the opening."""
    same = b[(b["id"] != row["id"]) & (b["road"] == row["road"]) & (b["kind"] == "partial")
             & (b["carries_through_traffic"] == "yes") & (b["status"] == "opened")
             & b["codes"].map(lambda c: bool(set(c) & set(row["codes"])))
             & (b["opened_date"] < row["opened_date"])]
    return pd.concat([row.to_frame().T, same])


@dataclass
class Selection:
    towns: pd.DataFrame
    excluded: list[dict] = field(default_factory=list)
    rows_excluded: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)


def treated_rows(b: pd.DataFrame, classes=CLASSES) -> tuple[pd.DataFrame, list[dict]]:
    rows = b[is_full(b, classes) & (b["status"] == "opened") & b["open_year"].between(*OPENED)]
    out, dropped = [], []
    for _, r in rows.iterrows():
        group = staged_group(b, r)
        start = min((y for y in group["start_year"] if pd.notna(y)), default=None)
        first = group.sort_values("opened_date").iloc[0]
        why = ("no municipality code" if not r["codes"] else "no construction start" if start is None
               else f"works started before {FIRST_YEAR + PRE_YEARS} (fewer than {PRE_YEARS} pre-construction years "
                    f"in the police files)" if start < FIRST_YEAR + PRE_YEARS else None)
        if why:
            dropped.append({"id": r["id"], "town": r["town"], "reason": why})
            continue
        out.append({"id": r["id"], "group_ids": list(group["id"]), "town_names": r["town"], "codes": r["codes"],
                    "road": r["road"], "road_class": r["road_class"], "start_year": int(start),
                    "open_year": int(first["open_year"]), "open_month": first["open_month"],
                    "date_precision": first["date_precision"], "staged": len(group) > 1})
    return pd.DataFrame(out), dropped


def comparison_rows(b: pd.DataFrame, classes=CLASSES, planned_only: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    late = (b["status"] == "opened") & (b["open_year"] >= OPENED[1] + 1)
    planned = (b["status"] == "planned") & b["stage"].isin(COMPARISON_STAGES)
    rows = b[is_full(b, classes) & ((planned) if planned_only else (late | planned))]
    out, dropped = [], []
    for _, r in rows.iterrows():
        start = r["start_year"]
        why = ("no municipality code" if not r["codes"]
               else "in construction without a start date" if r["stage"] == "in construction" and pd.isna(start)
               else None)
        if why:
            dropped.append({"id": r["id"], "town": r["town"], "reason": why})
            continue
        last = (int(start) - 1 if pd.notna(start) else int(r["open_year"]) - 1 if pd.notna(r["open_year"])
                else LAST_YEAR)
        out.append({"id": r["id"], "group_ids": [r["id"]], "town_names": r["town"], "codes": r["codes"],
                    "road": r["road"], "road_class": r["road_class"], "status": r["status"], "stage": r["stage"],
                    "start_year": None if pd.isna(start) else int(start),
                    "open_year": None if pd.isna(r["open_year"]) else int(r["open_year"]),
                    "last_year": min(last, LAST_YEAR)})
    return pd.DataFrame(out), dropped


def other_works(b: pd.DataFrame, code: int, own: list[str], first: int, last: int) -> list[str]:
    """§2: any other row of the list in the town, of any kind, opened or started from `first` to `last`."""
    hits = []
    for _, r in b[b["codes"].map(lambda c: code in c) & ~b["id"].isin(own)].iterrows():
        years = [y for y in (r["open_year"], r["start_year"]) if pd.notna(y)]
        if any(first <= y <= last for y in years):
            hits.append(r["id"])
    return hits


def two_full(b: pd.DataFrame, code: int, own: list[str]) -> list[str]:
    """§2: a second `full` row (any class) of the town opened in the treated window or the data years."""
    other = b[(b["kind"] == "full") & b["codes"].map(lambda c: code in c) & ~b["id"].isin(own)
              & (b["status"] == "opened") & b["open_year"].between(OPENED[0], LAST_YEAR)]
    return list(other["id"])


def select(b: pd.DataFrame, area_change: dict[int, float] | None = None, classes=CLASSES,
           planned_only: bool = False) -> Selection:
    """Town-level table: one row per municipality and role, after every exclusion that needs no accident count."""
    t_rows, t_drop = treated_rows(b, classes)
    c_rows, c_drop = comparison_rows(b, classes, planned_only)
    sel = Selection(towns=pd.DataFrame(), rows_excluded=[{"role": "treated", **d} for d in t_drop]
                    + [{"role": "comparison", **d} for d in c_drop])
    towns = []
    for role, rows in (("treated", t_rows), ("comparison", c_rows)):
        for _, r in rows.iterrows():
            for code in r["codes"]:
                last = LAST_YEAR if role == "treated" else r["last_year"]
                rec = {"code": code, "role": role, "row": r["id"], **{k: r[k] for k in r.index if k != "codes"}}
                reasons = []
                if role == "comparison" and last < FIRST_YEAR:
                    reasons.append(f"serves no year: works started or opened before {FIRST_YEAR + 1}")
                if f := two_full(b, code, r["group_ids"]):
                    reasons.append(f"two full bypasses in the period ({', '.join(f)})")
                if w := other_works(b, code, r["group_ids"], FIRST_YEAR, last):
                    reasons.append(f"other works in the town ({', '.join(w)})")
                ch = (area_change or {}).get(code)
                if ch is not None and ch > AREA_CHANGE:
                    reasons.append(f"RÚIAN territory changed by {ch:.1%}")
                rec["excluded"] = "; ".join(reasons) or None
                towns.append(rec)
    df = pd.DataFrame(towns)
    treated_codes = set(df.loc[(df["role"] == "treated") & df["excluded"].isna(), "code"])
    dup = (df["role"] == "comparison") & df["code"].isin(treated_codes) & df["excluded"].isna()
    df.loc[dup, "excluded"] = "already a treated town"
    twice = df[df["excluded"].isna()].duplicated(["code", "role"], keep=False)
    for code in df[df["excluded"].isna()][twice]["code"].unique():
        rows = df.index[(df["code"] == code) & df["excluded"].isna()]
        if (df.loc[rows, "role"] == "treated").sum() > 1:
            df.loc[rows, "excluded"] = "two treated rows"
        else:
            keep = df.loc[rows].sort_values("last_year").index[0]
            df.loc[rows.drop(keep), "excluded"] = "second comparison row of the town (earliest censoring kept)"
    sel.excluded = df[df["excluded"].notna()][["code", "town_names", "role", "row", "excluded"]].to_dict("records")
    df = df[df["excluded"].isna()].drop(columns="excluded").reset_index(drop=True)
    df["cohort"] = [cohort(y) if role == "treated" else None for y, role in zip(df["open_year"], df["role"])]
    df["cluster"] = clusters(df)
    sel.towns = df
    return sel


def clusters(towns: pd.DataFrame) -> list[str]:
    """§4: the resampling unit is the bypass with all the municipalities it treats; rows that share a municipality
    are one unit."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            a = parent[a]
        return a

    for _, r in towns.iterrows():
        parent[find(("town", r["code"]))] = find(("row", r["row"]))
    return [f"{find(('row', r))[1]}" for r in towns["row"]]


def comparisons_per_year(towns: pd.DataFrame) -> dict[int, int]:
    """Towns serving as comparisons in each year: comparison towns before censoring, treated towns before their works."""
    out = {}
    for y in range(FIRST_YEAR, LAST_YEAR + 1):
        c = ((towns["role"] == "comparison") & (towns["last_year"] >= y)).sum()
        t = ((towns["role"] == "treated") & (towns["start_year"] > y)).sum()
        out[y] = int(c + t)
    return out
