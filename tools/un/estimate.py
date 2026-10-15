"""The UN votes study's estimates (design §4, §6, §7): every β, its placebo rank and label, the checks, Czechia's
levels and absences, and the list of votes on which Czechia left the EU majority (Q4).

Stage A (Q2, the changes of 2017 and 2021) reads version 5 of the file and Czech positions up to 14 December 2025
only; stage B (Q1, the third Babiš government) reads the first version covering December 2026, given as --data, and
compares its rows up to 30 December 2025 with version 5. Writes docs/research/un-votes-results-<stage>.json.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with numpy python tools/un/estimate.py --stage A
    nice -n 20 uv run --no-project --with duckdb --with pandas --with numpy python tools/un/estimate.py --stage B --data <csv>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from votes import (DATA, EU27, FILE, MIN_AFTER, ROOT, SHA256, after_cabinet, agreement_eu, agreements, beta,  # noqa: E402
                   label, load, positions, rank_p, windows)

FOCAL = "CZE"
PARTNERS = (None, "USA", "RUS", "HUN", "SVK")
STAGE_A_END = "2025-12-14"
CABINET = {"babis_2017": "2017-12-13", "fiala_2021": "2021-12-17", "babis_2025": "2025-12-15"}
CONFIDENCE = {"babis_2017": "2018-07-12", "fiala_2021": "2022-01-13"}
US_CHANGE = "2025-01-20"
CHANGES = {
    "q2a": {"before": ("2014-01-29", "2017-12-12"), "after": (after_cabinet(CABINET["babis_2017"]), "2021-12-16"),
            "cabinet": "babis_2017"},
    "q2b": {"before": (after_cabinet(CABINET["babis_2017"]), "2021-12-16"),
            "after": (after_cabinet(CABINET["fiala_2021"]), STAGE_A_END), "cabinet": "fiala_2021"},
    "q1": {"before": (after_cabinet(CABINET["fiala_2021"]), STAGE_A_END), "after": ("2026-10-16", "2026-12-31"),
           "cabinet": "babis_2025"},
}
STAGE = {"A": ("q2a", "q2b"), "B": ("q1",)}


def name(partner: str | None) -> str:
    return partner or "EU"


def split_mask(m: pd.DataFrame, focal: str) -> pd.Series:
    """Votes on which the EU-27 members other than the focal one did not all take the same position (§7.1)."""
    others = [c for c in EU27 if c in m.columns and c != focal]
    v = m[others].to_numpy()
    return pd.Series([len(set(r[r >= 0])) > 1 for r in v], index=m.index)


def one(m, info, focal, partner, before, after, *, partial=True, drop=(), mask=None) -> dict:
    a_f, a_c = agreements(m, focal, partner, partial=partial, drop=drop)
    if mask is not None:
        before, after = before & mask, after & mask
    return beta(a_f, a_c, before, after, info["cluster"])


def with_placebo(m, info, partner, before, after) -> dict:
    """§4: Czechia's β, and every other EU-27 member's as focal with at least MIN_AFTER votes after; the rank and label."""
    res = one(m, info, FOCAL, partner, before, after)
    placebo = {}
    for c in EU27:
        if c in (FOCAL, partner) or c not in m.columns:
            continue
        a_c_f = agreements(m, c, partner)[0]
        if a_c_f[after].notna().sum() < MIN_AFTER or a_c_f[before].notna().sum() == 0:
            continue
        b = one(m, info, c, partner, before, after)
        placebo[c] = {"est": round(b["est"], 4), "se": round(b["se"], 4)}
    p, n = rank_p(res["est"] / res["se"], [v["est"] / v["se"] for v in placebo.values()])
    res.update({"p": round(p, 4), "members_ranked": n, "label": label(res, p), "placebo": placebo})
    return res


def levels(m, partner, before, after) -> dict:
    a_f, a_c = agreements(m, FOCAL, partner)
    return {"czechia_before": round(float(a_f[before].mean()), 4), "czechia_after": round(float(a_f[after].mean()), 4),
            "comparison_before": round(float(a_c[before].mean(axis=1).mean()), 4),
            "comparison_after": round(float(a_c[after].mean(axis=1).mean()), 4)}


def checks(m, info, key, ch, before, after) -> dict:
    """§7, reported with Czechia's β and intervals; none relabels a primary result."""
    out = {}
    trim = lambda b: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in b.items()}  # noqa: E731
    out["split_votes_only"] = trim(one(m, info, FOCAL, None, before, after, mask=split_mask(m, FOCAL)))
    out["no_partial_credit"] = trim(one(m, info, FOCAL, None, before, after, partial=False))
    out["without_hungary_slovakia"] = trim(one(m, info, FOCAL, None, before, after, drop=("HUN", "SVK")))
    regular = info["session"].str.fullmatch(r"\d+").fillna(False)
    out["regular_sessions_only"] = trim(one(m, info, FOCAL, None, before, after, mask=regular))
    dates = info["date"]
    if key != "q1":
        cab = CABINET[ch["cabinet"]]
        _, nobuf = windows(dates, ch["before"], (cab, ch["after"][1]))
        out["no_buffer"] = trim(one(m, info, FOCAL, None, before, nobuf))
        _, conf = windows(dates, ch["before"], (after_cabinet(CONFIDENCE[ch["cabinet"]]), ch["after"][1]))
        out["confidence_dates"] = trim(one(m, info, FOCAL, None, before, conf))
    else:
        season = before & (dates.dt.month * 100 + dates.dt.day >= 1016)
        out["same_season_before"] = trim(one(m, info, FOCAL, None, season, after))
    # §7.7: with the US, only the part of the Fiala period before the US change
    fiala_side = "after" if key == "q2b" else ("before" if key == "q1" else None)
    if fiala_side:
        cut = dates < US_CHANGE
        b2, a2 = (before & cut, after) if fiala_side == "before" else (before, after & cut)
        out["usa_before_us_change"] = trim(one(m, info, FOCAL, "USA", b2, a2))
    for k in out:
        out[k].pop("se", None)
    return out


def absences(m, info) -> dict:
    """§7.8: Czechia's share of X (not voting) per period."""
    dates = info["date"]
    spans = {k: ch["before"] for k, ch in CHANGES.items()} | {f"{k}_after": ch["after"] for k, ch in CHANGES.items()}
    out = {}
    for k, (a, b) in spans.items():
        inside = (dates >= a) & (dates <= b)
        if inside.any():
            out[k] = round(float((m.loc[inside, FOCAL] < 0).mean()), 4)
    return out


def departures(m, info, a: str, b: str) -> dict:
    """Q4: votes on which Czechia's position differed from the majority of the other EU-27 members."""
    agree = agreement_eu(m, FOCAL)
    inside = (info["date"] >= a) & (info["date"] <= b) & agree.notna()
    off = agree[inside & (agree < 1)]
    rows = [{"date": str(info.at[i, "date"].date()), "agreement": float(v), "title": info.at[i, "title"],
             "agenda": info.at[i, "agenda"]} for i, v in off.items()]
    ties = int((agreement_eu(m, FOCAL).isna() & (m[FOCAL] >= 0) & ((info["date"] >= a) & (info["date"] <= b))).sum())
    return {"votes": int(inside.sum()), "departures": len(rows), "ties_dropped": ties, "list": rows}


def ungadm_crosscheck(df: pd.DataFrame) -> dict:
    """§7.10: sessions 68–77, all members, positions of the same member on the same adopted resolution."""
    path = DATA / "ungadm/votes.csv"
    if not path.exists():
        return {"run": False, "reason": "UNGA-DM votes.csv not found"}
    u = pd.read_csv(path, usecols=["decision_id", "member_state", "original_seat_name", "original_vote", "resolution_id",
                                   "session_id"])
    u = u[u["decision_id"].str.endswith("-FP") & u["session_id"].isin([f"RS-{s:03d}" for s in range(68, 78)])]
    u["res"] = u["resolution_id"].str.replace(r"\[.*\]$", "", regex=True)
    u["who"] = u["original_seat_name"].str.upper().str.replace(r"[^A-Z]", "", regex=True)
    u["v"] = u["original_vote"].map({"in favor": "Y", "against": "N", "abstaining": "A"})
    d = df[df["session"].isin([str(s) for s in range(68, 78)])][["resolution", "ms_name", "ms_vote"]].copy()
    d["res"] = d["resolution"]
    d["who"] = d["ms_name"].str.upper().str.replace(r"[^A-Z]", "", regex=True)
    j = d.merge(u[["res", "who", "v"]], on=["res", "who"], how="left")
    both = j[j["v"].notna() & j["ms_vote"].isin(["Y", "N", "A"])]
    return {"run": True, "pairs": int(len(d)), "matched": int(j["v"].notna().sum()),
            "matched_with_positions": int(len(both)), "same_position": round(float((both["v"] == both["ms_vote"]).mean()), 4)}


def compare_versions(new: pd.DataFrame, old: pd.DataFrame) -> dict:
    """Stage B: rows up to 30 December 2025 that differ between the new version and version 5."""
    key = ["undl_id", "ms_code"]
    cut = lambda d: d[d["date"] <= "2025-12-30"][key + ["ms_vote"]]  # noqa: E731
    j = cut(old).merge(cut(new), on=key, how="outer", suffixes=("_v5", "_new"), indicator=True)
    return {"only_v5": int((j["_merge"] == "left_only").sum()), "only_new": int((j["_merge"] == "right_only").sum()),
            "changed": int(((j["_merge"] == "both") & (j["ms_vote_v5"] != j["ms_vote_new"])).sum())}


def run(df: pd.DataFrame, stage: str) -> dict:
    m, info, dup = positions(df)
    out = {"stage": stage, "duplicates": dup, "questions": {}}
    for key in STAGE[stage]:
        ch = CHANGES[key]
        before, after = windows(info["date"], ch["before"], ch["after"])
        q = {"before": ch["before"], "after": ch["after"], "by_partner": {}}
        for partner in PARTNERS:
            r = with_placebo(m, info, partner, before, after)
            r.update(levels(m, partner, before, after))
            q["by_partner"][name(partner)] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
            print(key, name(partner), round(r["est"], 4), r["ci95"], r["p"], r["label"])
        q["checks"] = checks(m, info, key, ch, before, after)
        q["departures_after"] = departures(m, info, *ch["after"])
        q["departures_before"] = departures(m, info, *ch["before"])
        out["questions"][key] = q
    if stage == "B":
        out["block_2025_12_15_to_2026_10_15"] = departures(m, info, "2025-12-15", "2026-10-15")
    out["absences"] = absences(m, info)
    out["ungadm"] = ungadm_crosscheck(df)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("A", "B"), required=True)
    ap.add_argument("--data", type=Path)
    args = ap.parse_args()
    if args.stage == "A":
        assert hashlib.sha256(FILE.read_bytes()).hexdigest() == SHA256, "stage A runs on version 5"
        df = load(end=STAGE_A_END)  # stage A reads Czech positions up to 14 December 2025 only
        res = run(df, "A")
    else:
        df = load(args.data)
        res = run(df, "B")
        res["version"] = {"file": args.data.name, "sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
                          "against_v5": compare_versions(df, load())}
    (ROOT / f"docs/research/un-votes-results-{args.stage.lower()}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
