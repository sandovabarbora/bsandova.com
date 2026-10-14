"""Screening of the swiss-trams design (§3), and the passes and segment × date × hour sums the estimate uses.

Reads the tram rows kept by swiss_fetch.py. Writes tools/data/late/swiss_passes.parquet (one row per kept pass, for the
chance level), tools/data/late/swiss_segments.parquet (sums in the layout of part 1's segments.parquet, so
estimate.py's functions apply unchanged), tools/data/late/swiss_stops.parquet (stop name → BPUIC, for the length
check) and docs/research/swiss-trams-screen.json, with counts and shares only; no segment's delay is summarised.

    nice -n 20 uv run --no-project --with pandas --with pyarrow --with holidays --with duckdb \
        python tools/late/swiss_screen.py
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

import duckdb
import holidays
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools/data/late/swiss"
OUT_DATA = ROOT / "tools/data/late"
OUT = ROOT / "docs/research/swiss-trams-screen.json"
START, END = date(2025, 3, 15), date(2025, 9, 8)
MAX_GAIN, MIN_PASSES, MIN_REAL = 600, 1000, 0.5
CITY = {"VBZ": "Zurich", "BVB": "Basel", "BLT": "Basel", "TPG": "Geneva", "SVB": "Bern"}
CANTON = {"Zurich": "ZH", "Basel": "BS", "Geneva": "GE", "Bern": "BE"}
SCHED, ACTUAL = "%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S"


def stop_rows(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """§3.1–3.2: served stops of the four networks, ordered within each trip, tied stops dropped."""
    # the abbreviation carries a suffix in the archive ("VBZ    Fpl", "SVB Auto"); its first word names the operator
    raw = raw.assign(BETREIBER_ABK=raw.BETREIBER_ABK.str.split().str[0])
    t = raw[raw.BETREIBER_ABK.isin(CITY)].copy()
    n0 = len(t)
    t = t[(t.FAELLT_AUS_TF != "true") & (t.DURCHFAHRT_TF != "true")]
    n1 = len(t)
    t["arr"] = pd.to_datetime(t.ANKUNFTSZEIT, format=SCHED, errors="coerce")
    t["dep"] = pd.to_datetime(t.ABFAHRTSZEIT, format=SCHED, errors="coerce")
    t = t.sort_values(["FAHRT_BEZEICHNER", "dep", "arr"], na_position="last")
    tied = t.duplicated(["FAHRT_BEZEICHNER", "dep", "arr"], keep=False)
    t = t[~tied].copy()
    # the delay at a stop is taken at the arrival, at a trip's first stop (no arrival) at the departure
    has_arr = t.arr.notna()
    t["sched"] = t.arr.where(has_arr, t.dep)
    t["actual"] = pd.to_datetime(t.AN_PROGNOSE.where(has_arr, t.AB_PROGNOSE), format=ACTUAL, errors="coerce")
    t["status"] = t.AN_PROGNOSE_STATUS.where(has_arr, t.AB_PROGNOSE_STATUS)
    t["delay"] = (t.actual - t.sched).dt.total_seconds()
    t["city"] = t.BETREIBER_ABK.map(CITY)
    real_arr = t[has_arr & (t.AN_PROGNOSE_STATUS == "REAL")]
    info = {"rows": n0, "cancelled_or_passed": n0 - n1, "tied_stops": int(tied.sum()),
            "real_arrivals": real_arr.groupby("city").size().to_dict(),
            "real_arrivals_with_seconds": real_arr.groupby("BETREIBER_ABK").AN_PROGNOSE.apply(
                lambda s: int((~s.str.endswith(":00")).sum())).to_dict(),
            "real_arrivals_by_operator": real_arr.groupby("BETREIBER_ABK").size().to_dict()}
    return t, info


def passes(t: pd.DataFrame) -> pd.DataFrame:
    """Consecutive served stops of a trip; a tie dropped in stop_rows splits nothing but removes that stop."""
    nxt = t.groupby("FAHRT_BEZEICHNER").shift(-1)
    p = pd.DataFrame({"city": t.city, "op": t.BETREIBER_ABK, "trip": t.FAHRT_BEZEICHNER,
                      "seg_from": t.HALTESTELLEN_NAME, "seg_to": nxt.HALTESTELLEN_NAME,
                      "g": nxt.delay - t.delay, "real": (t.status == "REAL") & (nxt.status == "REAL"),
                      "measured": t.status.isin(["REAL", "PROGNOSE"]) & nxt.status.isin(["REAL", "PROGNOSE"]),
                      "hour": t.actual.dt.hour})
    p = p[p.seg_to.notna() & (p.seg_from != p.seg_to)].copy()
    first = ~p.trip.duplicated(keep="first")
    last = ~p.trip.duplicated(keep="last")
    p["terminal"] = first | last
    return p.drop(columns="trip")


def feed_gaps(real: pd.DataFrame) -> set[tuple[str, str]]:
    """§3.4: a city's date with fewer REAL tram arrivals than half its median for the day type."""
    gaps = set()
    for city, g in real.groupby("city"):
        hol = holidays.Switzerland(subdiv=CANTON[city], years=2025)
        kind = g.date.map(lambda d: "holiday" if d in hol or d.weekday() == 6 else "sat" if d.weekday() == 5 else "wd")
        med = g.groupby(kind).n.transform("median")
        gaps |= {(city, str(d)) for d in g[g.n < med / 2].date}
    return gaps


def prague_schedule_resolution() -> dict:
    """§3.7: the timetable only; no delay is read."""
    con = duckdb.connect(str(ROOT / "tools/data/rain/prague_transit.duckdb"), read_only=True)
    con.execute("SET threads = 2")
    n, off = con.execute(f"""
        SELECT count(*), count(*) FILTER (WHERE planned_travel_time % 60 <> 0) FROM prague_cascade
        WHERE route_type = 'tramvaj' AND planned_travel_time IS NOT NULL
          AND CAST(timezone('Europe/Prague', current_stop_arrival) AS DATE) BETWEEN DATE '{START}' AND DATE '{END}'
    """).fetchone()
    return {"tram_passes_with_planned_time": int(n), "share_not_whole_minutes": round(off / n, 6) if n else None}


def main() -> None:
    files = sorted(f for f in RAW.glob("*.parquet") if START <= date.fromisoformat(f.stem) <= END)
    all_p, counts, stops, ops = [], Counter(), {}, Counter()
    real_by_date, secs = [], Counter()
    for f in files:
        raw = pd.read_parquet(f)
        ops.update(raw.drop_duplicates("FAHRT_BEZEICHNER").BETREIBER_ABK)
        t, info = stop_rows(raw)
        counts.update({k: info[k] for k in ("rows", "cancelled_or_passed", "tied_stops")})
        secs.update({(op, "with_seconds"): n for op, n in info["real_arrivals_with_seconds"].items()})
        secs.update({(op, "all"): n for op, n in info["real_arrivals_by_operator"].items()})
        d = date.fromisoformat(f.stem)
        real_by_date += [{"city": c, "date": d, "n": n} for c, n in info["real_arrivals"].items()]
        for r in t.drop_duplicates(["city", "HALTESTELLEN_NAME"]).itertuples():
            stops.setdefault((r.city, r.HALTESTELLEN_NAME), r.BPUIC)
        all_p.append(passes(t).assign(date=d))
    p = pd.concat(all_p, ignore_index=True)
    formed = p.groupby("city").size()

    # §3.3 measured times: the segment's share of REAL passes over all its formed passes
    seg_real = p.groupby(["city", "seg_from", "seg_to"]).real.mean().rename("real_share")
    p = p.join(seg_real, on=["city", "seg_from", "seg_to"])
    low_real = p.real_share < MIN_REAL
    gaps = feed_gaps(pd.DataFrame(real_by_date))
    gap = pd.Series([(c, str(d)) in gaps for c, d in zip(p.city, p.date)], index=p.index)

    base = ~low_real & ~gap & p.g.notna()
    kept_real = base & p.real & (p.g.abs() <= MAX_GAIN)
    # the check with forecasts kept (§6) relaxes all of §3.3, the per-segment REAL share included
    kept_fc = ~gap & p.g.notna() & p.measured & (p.g.abs() <= MAX_GAIN)
    month = pd.to_datetime(p.date).dt.month

    k = p[kept_real]
    n_seg = k.groupby(["city", "seg_from", "seg_to"]).size()
    rare = n_seg[n_seg < MIN_PASSES]
    keep_idx = n_seg[n_seg >= MIN_PASSES].index
    in_keep = pd.MultiIndex.from_frame(p[["city", "seg_from", "seg_to"]]).isin(keep_idx)

    final = p[kept_real & in_keep]
    n_fc = p[kept_fc].groupby(["city", "seg_from", "seg_to"]).size()
    fc_keep = pd.MultiIndex.from_frame(p[["city", "seg_from", "seg_to"]]).isin(n_fc[n_fc >= MIN_PASSES].index)
    fc = p[kept_fc & fc_keep]
    final[["city", "op", "seg_from", "seg_to", "date", "hour", "g"]].astype({"g": "int32"}).to_parquet(
        OUT_DATA / "swiss_passes.parquet", index=False)

    keys = ["city", "op", "seg_from", "seg_to", "date", "hour", "terminal"]
    agg = final.assign(g300=final.g.where(final.g.abs() <= 300), n300=final.g.abs() <= 300).groupby(keys).agg(
        n=("g", "size"), gsum=("g", "sum"), n300=("n300", "sum"), gsum300=("g300", "sum"),
        real_share=("real_share", "first"))
    agg = agg.join(fc.groupby(keys).g.agg(n_fc="size", gsum_fc="sum"), how="outer").reset_index()
    agg = agg.fillna({"n": 0, "gsum": 0.0, "n300": 0, "gsum300": 0.0, "n_fc": 0, "gsum_fc": 0.0})
    agg["mode"] = "tram"
    agg.to_parquet(OUT_DATA / "swiss_segments.parquet", index=False)
    pd.DataFrame([{"city": c, "name": n, "bpuic": b} for (c, n), b in stops.items()]).to_parquet(
        OUT_DATA / "swiss_stops.parquet", index=False)

    def share(mask, by):
        return {str(kk): round(float(v), 4) for kk, v in mask.groupby(by).mean().items()}

    out = {
        "window": [str(START), str(END)], "dates_read": len(files),
        "trips_by_operator": dict(ops.most_common()),
        "rows_four_networks": counts["rows"], "rows_cancelled_or_passed_through": counts["cancelled_or_passed"],
        "stops_dropped_as_ties": counts["tied_stops"],
        "real_arrivals_with_nonzero_seconds": {op: round(secs[(op, "with_seconds")] / secs[(op, "all")], 4)
                                               for op in CITY if secs[(op, "all")]},
        "passes_formed": formed.to_dict(),
        "real_share_by_city_month": share(p.real, [p.city, month]),
        "low_real_segments": {c: {"segments": int(g.groupby(["seg_from", "seg_to"]).ngroups),
                                  "share_of_passes": round(len(g) / formed[c], 4)}
                              for c, g in p[low_real].groupby("city")},
        "feed_gap_dates": sorted(f"{c} {d}" for c, d in gaps),
        "implausible_share_by_city_month": share(p.g.abs() > MAX_GAIN, [p.city, month]),
        "rare_segments": {c: {"segments": int(len(g)), "passes": int(g.sum())} for c, g in rare.groupby(level=0)},
        "kept": {c: {"segments": int(g.groupby(["seg_from", "seg_to"]).ngroups), "passes": int(len(g)),
                     "dates": int(g.date.nunique())} for c, g in final.groupby("city")},
        "kept_with_forecasts": {c: {"segments": int(g.groupby(["seg_from", "seg_to"]).ngroups), "passes": int(len(g))}
                                for c, g in fc.groupby("city")},
        "prague_schedule": prague_schedule_resolution(),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
