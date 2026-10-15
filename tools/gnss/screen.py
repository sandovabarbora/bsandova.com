"""Screening report of the GNSS design (§3), from the screening counts only.

Reads tools/data/gnss/days/*/manifest.json and days/*/screening/*.parquet (never sealed/) and the GFZ Kp file, and
writes docs/research/gnss-screen.json: days fetched, replaced and lost, holiday Wednesdays, coverage per region and
day, screenable aircraft per region and year, version and source shares per year, Kp_max per sampled day.

    nice -n 20 uv run --no-project --with pandas --with pyarrow python -I tools/gnss/screen.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch as F
import regions as R

OUT = R.ROOT / "docs/research/gnss-screen.json"
SCREEN_MIN = 30
SCREEN_DAYS = 2
KP_STORM = 5.0


def load(days_dir: Path, name: str, wednesdays: list) -> pd.DataFrame:
    """Only the directories of counted or replaced days: a day set aside by the low-count rule is not read."""
    files = [days_dir / str(d) / "screening" / f"{name}.parquet" for d in wednesdays]
    parts = [pd.read_parquet(p) for p in files if p.exists()]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def screenable(west: pd.DataFrame) -> pd.DataFrame:
    """Per aircraft: usable points west of 5° E over the sample and the days carrying them (§2, usable counts only).

    `screenable`: at least 30 such points in total, from at least two sampled days. `screenable_strict`: at least 30 on
    each of at least two sampled days. Both are reported; the design text admits either reading.
    """
    if west.empty:
        return pd.DataFrame(columns=["icao", "west_usable", "west_days", "screenable", "screenable_strict"])
    g = west.groupby("icao").agg(west_usable=("usable", "sum"), west_days=("usable", lambda s: int((s > 0).sum())),
                                 days30=("usable", lambda s: int((s >= SCREEN_MIN).sum())))
    g["screenable"] = (g["west_usable"] >= SCREEN_MIN) & (g["west_days"] >= SCREEN_DAYS)
    g["screenable_strict"] = g["days30"] >= SCREEN_DAYS
    return g.drop(columns="days30").reset_index()


def share(num, den):
    return None if not den else round(float(num) / float(den), 6)


def build(days_dir: Path, kp: dict[str, float | None]) -> dict:
    sample = F.sample_days()
    man = {}
    for d in sample:
        p = days_dir / str(d) / "manifest.json"
        man[d] = json.loads(p.read_text()) if p.exists() else None
    status = {d: (m["status"] if m else "not_fetched") for d, m in man.items()}
    used = {d: m["date_used"] for d, m in man.items() if m and m["status"] in ("counted", "replaced")}

    holidays = []
    for d in sample:
        name = F.czech_holidays(d.year).get(d)
        if name:
            holidays.append({"wednesday": str(d), "holiday": name, "status": status[d]})
    by_year = {}
    for d in sample:
        y = by_year.setdefault(str(F.study_year(d)), {"sampled": 0, "counted": 0, "replaced": 0, "lost": 0,
                                                      "not_fetched": 0})
        y["sampled"] += 1
        y[status[d]] += 1
    days = {
        "sampled": len(sample),
        "counted_wednesday": sum(s == "counted" for s in status.values()),
        "replaced_by_thursday": [{"wednesday": str(d), "thursday": man[d]["date_used"],
                                  "wednesday_unreadable": man[d]["unreadable"].get(str(d))}
                                 for d in sample if status[d] == "replaced"],
        "lost": [{"wednesday": str(d), "reasons": man[d]["unreadable"]} for d in sample if status[d] == "lost"],
        "not_fetched": [str(d) for d in sample if status[d] == "not_fetched"],
        "low_count_flagged": [{"wednesday": str(d), "median_of_neighbours": man[d]["low_median"]}
                              for d in sample if man[d] and "low_median" in man[d]],
        "holiday_wednesdays": holidays,
        "by_study_year": by_year,
    }

    pts = load(days_dir, "points", list(used))
    xagg = load(days_dir, "crossings_agg", list(used))
    stats = load(days_dir, "region_day", list(used))
    west = load(days_dir, "west", list(used))
    mix = load(days_dir, "mix", list(used))
    scr = screenable(west)
    scr_set = set(scr.loc[scr["screenable"], "icao"]) if len(scr) else set()
    strict_set = set(scr.loc[scr["screenable_strict"], "icao"]) if len(scr) else set()

    prim = pts[pts["variant"] == "primary"] if len(pts) else pd.DataFrame(columns=["date", "icao", "region", "usable"])
    per_ac = prim.groupby(["date", "region", "icao"], as_index=False)["usable"].sum()
    per_ac["screenable"] = per_ac["icao"].isin(scr_set)
    per_ac["screenable_strict"] = per_ac["icao"].isin(strict_set)
    allx = xagg[xagg["band"] == "all"] if len(xagg) else pd.DataFrame(columns=["date", "region", "crossings",
                                                                               "crossings_usable"])

    per_ac["u_s"] = per_ac["usable"].where(per_ac["screenable"], 0)
    per_ac["u_ss"] = per_ac["usable"].where(per_ac["screenable_strict"], 0)
    ug = per_ac.assign(ac=(per_ac["usable"] > 0).astype(int)).groupby(["date", "region"])[
        ["usable", "ac", "u_s", "u_ss"]].sum()
    xg = allx.groupby(["date", "region"])[["crossings", "crossings_usable"]].sum()
    sg = stats.set_index(["date", "region"]) if len(stats) else pd.DataFrame()

    def row(frame, key):
        return frame.loc[key] if key in frame.index else {}

    coverage = []
    for d in sample:
        if d not in used:
            continue
        m, du = man[d], used[d]
        regions = {}
        for r in R.REGIONS:
            u, x, s = row(ug, (du, r)), row(xg, (du, r)), row(sg, (du, r))
            g = (lambda f, k: int(f[k]) if k in f else 0)
            nu, ncu = g(u, "usable"), g(x, "crossings_usable")
            regions[r] = {
                "crossings": g(x, "crossings"),
                "crossings_with_usable": ncu,
                "usable": nu,
                "usable_per_crossing": share(nu, ncu),
                "aircraft_with_usable": g(u, "ac"),
                "details_share": share(g(s, "details"), g(s, "points")),
                "details_share_adsb_fl250": share(g(s, "adsb_fl250_details"), g(s, "adsb_fl250")),
                "stale_share": share(g(s, "stale"), g(s, "stale") + g(s, "points")),
                "nacp_nonnumeric_points": g(s, "nacp_nonnumeric"),
                "usable_share_screenable": share(g(u, "u_s"), nu),
                "usable_share_screenable_strict": share(g(u, "u_ss"), nu),
            }
        coverage.append({"wednesday": str(d), "date_used": du, "study_year": F.study_year(d),
                         "trace_files": m["trace_files"], "tilde_files": m["tilde"], "aircraft": m["aircraft"],
                         "bad_files": m["bad_files"], "regions": regions})

    date_year = {used[d]: F.study_year(d) for d in used}
    per_ac["year"] = per_ac["date"].map(date_year)
    scr_ry = {}
    for (r, y), g in per_ac[per_ac["usable"] > 0].groupby(["region", "year"]):
        ac = g.groupby("icao").agg(usable=("usable", "sum"), s=("screenable", "first"),
                                   ss=("screenable_strict", "first"))
        scr_ry.setdefault(r, {})[str(int(y))] = {
            "aircraft_with_usable": len(ac),
            "screenable": int(ac["s"].sum()),
            "screenable_strict": int(ac["ss"].sum()),
            "usable_share_screenable": share(ac.loc[ac["s"], "usable"].sum(), ac["usable"].sum()),
            "usable_share_screenable_strict": share(ac.loc[ac["ss"], "usable"].sum(), ac["usable"].sum()),
        }
    screen_block = {
        "rule": "at least 30 primary usable points west of 5 deg E over the sample, from at least two sampled days",
        "rule_strict": "at least 30 primary usable points west of 5 deg E on each of at least two sampled days",
        "aircraft_screenable": len(scr_set), "aircraft_screenable_strict": len(strict_set),
        "per_region_year": scr_ry,
    }

    mixes = {}
    if len(mix):
        mix = mix.assign(year=mix["date"].map(date_year))
        reg = mix[mix["region"] != "W5"]
        for y, g in reg.groupby("year"):
            tot = g["points"].sum()
            types = g.groupby("type")["points"].sum()
            det = g[(g["type"] == "adsb_icao") & (g["version"] != "no_details")]
            vers = det.groupby("version")["points"].sum()
            hi = det[det["fl250"]]
            vhi = hi.groupby("version")["points"].sum()
            mixes[str(int(y))] = {
                "points": int(tot),
                "type_share": {k: share(v, tot) for k, v in types.items()},
                "adsb_icao_version_share": {k: share(v, vers.sum()) for k, v in vers.items()},
                "adsb_icao_fl250_version_share": {k: share(v, vhi.sum()) for k, v in vhi.items()},
            }

    kp_days = {}
    for d in sample:
        du = used.get(d)
        kp_days[str(d)] = {"date_used": du, "kp_max": kp.get(du) if du else None}
    storm = sorted(d for d, v in kp_days.items() if v["kp_max"] is not None and v["kp_max"] >= KP_STORM)

    return {
        "design": "docs/research/gnss-design.md (signed tag gnss-design)",
        "days": days,
        "coverage": coverage,
        "screenable_aircraft": screen_block,
        "version_and_source": mixes,
        "kp": {"source": F.KP_URL, "per_day": kp_days, "days_kp_max_ge_5": len(storm), "dates_kp_max_ge_5": storm},
    }


def main() -> None:
    kp_file = F.KP_DIR / F.KP_NAME
    kp = F.parse_kp(kp_file.read_text()) if kp_file.exists() else {}
    report = build(F.DAYS, kp)
    report["generated"] = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    d = report["days"]
    print(f"wrote {OUT.relative_to(R.ROOT)}: {d['counted_wednesday']} Wednesdays, "
          f"{len(d['replaced_by_thursday'])} Thursdays, {len(d['lost'])} lost, {len(d['not_fetched'])} not fetched")


if __name__ == "__main__":
    main()
