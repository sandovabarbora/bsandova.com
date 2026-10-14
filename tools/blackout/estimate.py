"""Estimates of the blackout design (§1, §4–§6): service ratio, restart and recovery times, delay recovery, the stopped
share and the order of restart, each with its placebo (the same rule on each baseline day against the other two).

Reads the passes of the event, baseline, spare and June Fridays from the transit database (cached in
tools/data/blackout/passes.parquet) and the baseline days chosen by screen.py. Writes docs/research/blackout-results.json.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with pyarrow --with numpy python tools/blackout/estimate.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "tools/data/rain/prague_transit.duckdb"
CACHE = ROOT / "tools/data/blackout/passes.parquet"
SCREEN = ROOT / "docs/research/blackout-screen.json"
OUT = ROOT / "docs/research/blackout-results.json"
EVENT = "2025-07-04"
JUNE = ["2025-06-06", "2025-06-13", "2025-06-20", "2025-06-27"]
DAYS = [EVENT, "2025-07-11", "2025-07-18", "2025-07-25", "2025-08-01", "2025-08-08", *JUNE]
START_MIN, END_MIN = 10 * 60, 22 * 60          # 10:00–22:00
NOON, LAST_SUBSTATION = 12 * 60, 13 * 60 + 1   # 12:00, Chodov back at 13:01
MIN_PASSES_D, MIN_BASE_Q1, MAX_HEADWAY = 20, 3, 15
METRO_REPORTED = {"991": 12 * 60 + 15, "992": 12 * 60 + 35, "993": 12 * 60 + 15}  # A, B, C
RULED = ("tramvaj", "metro", "autobus")        # trolleybuses: curves only (§1 Q5)

QUERY = """
SELECT route_type AS mode, string_split(rt_trip_id, '_')[2] AS route, stop_name AS seg_from, next_stop_name AS seg_to,
       CAST(timezone('Europe/Prague', real_next_stop_arrival) AS DATE)::VARCHAR AS date,
       hour(timezone('Europe/Prague', real_next_stop_arrival)) * 60
         + minute(timezone('Europe/Prague', real_next_stop_arrival))
         + second(timezone('Europe/Prague', real_next_stop_arrival)) / 60.0 AS t,
       hour(timezone('Europe/Prague', real_current_stop_departure)) * 60
         + minute(timezone('Europe/Prague', real_current_stop_departure))
         + second(timezone('Europe/Prague', real_current_stop_departure)) / 60.0 AS t_dep,
       next_stop_arr_delay AS delay
FROM stop_times_history_modeling
WHERE year = 2025 AND month IN (6, 7, 8) AND real_next_stop_arrival IS NOT NULL
  AND route_type IN ('tramvaj', 'metro', 'autobus', 'trolejbus') AND stop_name <> next_stop_name
  AND CAST(timezone('Europe/Prague', real_next_stop_arrival) AS DATE) IN ({dates})
"""


def load() -> pd.DataFrame:
    if not CACHE.exists():
        import duckdb
        con = duckdb.connect(str(DB), read_only=True)
        con.execute("SET threads = 2")
        con.execute("SET memory_limit = '4GB'")
        df = con.execute(QUERY.format(dates=", ".join(f"DATE '{d}'" for d in DAYS))).df()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE, index=False)
    return pd.read_parquet(CACHE)


def hhmm(minute: float | None) -> str | None:
    return None if minute is None or pd.isna(minute) else f"{int(minute) // 60:02d}:{int(minute) % 60:02d}"


def binned(p: pd.DataFrame, width: int = 10, col: str = "t") -> pd.DataFrame:
    """Passes, median and mean delay per date × mode × bin of `width` minutes from 10:00."""
    q = p[(p[col] >= START_MIN) & (p[col] < END_MIN)]
    q = q.assign(bin=((q[col] - START_MIN) // width).astype(int))
    return q.groupby(["date", "mode", "bin"]).delay.agg(n="size", d_median="median", d_mean="mean").reset_index()


def grid(b: pd.DataFrame, mode: str, value: str, width: int) -> pd.DataFrame:
    nb = (END_MIN - START_MIN) // width
    return b[b["mode"] == mode].pivot(index="bin", columns="date", values=value).reindex(range(nb))


def ratio(b: pd.DataFrame, day: str, ref: list[str], mode: str, width: int = 10) -> pd.Series:
    n = grid(b, mode, "n", width).fillna(0)
    base = n[ref].mean(axis=1)
    return (n[day] / base).where(base > 0)


def first_run(ok: pd.Series, width: int, need: int = 5, of: int = 6) -> float | None:
    """Minute of day of the first bin at or after 12:00 that is True and opens `of` bins with `need` True, none missing.

    The opening bin must itself be True: otherwise a run could start one bin before the service came back (change log,
    code frozen 14 October 2026)."""
    start = (NOON - START_MIN) // width
    v = ok.to_numpy(dtype=float)
    for i in range(start, len(v) - of + 1):
        w = v[i:i + of]
        if not np.isnan(w).any() and w[0] == 1 and w.sum() >= need:
            return START_MIN + i * width
    return None


def t_service(b, day, ref, mode, thr, width=10, need=5, of=6):
    r = ratio(b, day, ref, mode, width)
    return first_run((r >= thr).astype(float).where(r.notna()), width, need, of)


def t_delay(b, day, ref, mode, width=10, stat="d_median", need=5, of=6):
    d = grid(b, mode, stat, width)
    n = grid(b, mode, "n", width).fillna(0)
    lo, hi, mid = d[ref].min(axis=1), d[ref].max(axis=1), d[ref].mean(axis=1)
    pad = np.maximum(30.0, 0.25 * mid.abs())
    x = d[day].where(n[day] >= MIN_PASSES_D)
    ok = ((x >= lo - pad) & (x <= hi + pad)).astype(float).where(x.notna())
    return first_run(ok, width, need, of)


def segment_counts(p: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    q = p[(p["mode"] == "tramvaj") & (p.t >= lo) & (p.t < hi)]
    return q.groupby(["seg_from", "seg_to", "date"]).size().unstack(fill_value=0)


def stopped_share(p, day, ref, lo=NOON + 10, hi=NOON + 30) -> dict:
    c = segment_counts(p, lo, hi).reindex(columns=[day, *ref], fill_value=0)
    w = c[ref].mean(axis=1)
    keep = w >= MIN_BASE_Q1
    stopped = c[day] == 0
    return {"share": round(float(w[keep & stopped].sum() / w[keep].sum()), 4),
            "segments_stopped": int((keep & stopped).sum()), "segments": int(keep.sum()),
            "low_frequency_excluded": int((~keep & (w > 0)).sum())}


def restart_order(p, day, ref) -> list[dict]:
    c = segment_counts(p, NOON + 10, NOON + 30).reindex(columns=[day, *ref], fill_value=0)
    w = c[ref].mean(axis=1)
    stopped = c[(w >= MIN_BASE_Q1) & (c[day] == 0)].index
    two_h = segment_counts(p, NOON, NOON + 120).reindex(columns=ref, fill_value=0).mean(axis=1)
    tram = p[(p["mode"] == "tramvaj") & (p.date == day) & (p.t >= NOON + 10)]
    first = tram.groupby(["seg_from", "seg_to"]).t.min()
    lines = p[(p["mode"] == "tramvaj") & p.date.isin(ref)].groupby(["seg_from", "seg_to"]).route.agg(
        lambda s: sorted(set(s)))
    rows = []
    for seg in stopped:
        headway = 120 / two_h[seg] if two_h.get(seg, 0) > 0 else None
        t0 = first.get(seg)
        lag = None if t0 is None or headway is None else t0 - (NOON + 10) - headway / 2
        rows.append({"from": seg[0], "to": seg[1], "lines": lines.get(seg, []), "restart": hhmm(t0),
                     "lag_min": None if lag is None else round(float(lag), 1),
                     "after_13_01_min": None if t0 is None else round(float(t0 - LAST_SUBSTATION), 1),
                     "baseline_headway_min": None if headway is None else round(float(headway), 1),
                     "mapped": headway is not None and headway <= MAX_HEADWAY})
    return sorted(rows, key=lambda r: (r["restart"] is None, r["restart"] or ""))


def metro_control(p, day) -> dict:
    m = p[(p["mode"] == "metro") & (p.date == day) & (p.t >= NOON)]
    first = m.groupby(["route", "seg_from", "seg_to"]).t.min().groupby(level=0).median()
    out = {}
    for line, reported in METRO_REPORTED.items():
        est = first.get(line)
        out[line] = {"estimated": hhmm(est), "reported": hhmm(reported),
                     "miss_min": None if est is None else round(float(est - reported), 1)}
    return out


def times(b, day, ref, mode, width=10, thr90=0.9, need=5, stat="d_median") -> dict:
    return {"T50": hhmm(t_service(b, day, ref, mode, 0.5, width, need)),
            "T90": hhmm(t_service(b, day, ref, mode, thr90, width, need)),
            "TD": hhmm(t_delay(b, day, ref, mode, width, stat, need))}


def with_placebo(fn, day: str, base: list[str]) -> dict:
    return {"event": fn(day, base), "placebo": {b: fn(b, [x for x in base if x != b]) for b in base}}


def curves(b: pd.DataFrame, day: str, base: list[str], mode: str) -> dict:
    n = grid(b, mode, "n", 10)
    d = grid(b, mode, "d_median", 10)
    r = ratio(b, day, base, mode)
    rnd = lambda s: [None if pd.isna(x) else round(float(x), 3) for x in s]  # noqa: E731
    return {"R": rnd(r), "D_event": rnd(d[day]), "D_base_min": rnd(d[base].min(axis=1)),
            "D_base_max": rnd(d[base].max(axis=1)), "n_event": rnd(n[day])}


def main() -> None:
    p = load()
    screen = json.loads(SCREEN.read_text())
    # §3.1 makes feed-suspect bins missing for every mode; screening found none, so the bins are read as they are
    assert "feed-suspect" not in screen["feed_flags"].values()
    base = screen["baseline_days"]
    b10 = binned(p)
    res = {"event": EVENT, "baseline_days": base, "modes": {}}
    for mode in RULED:
        res["modes"][mode] = with_placebo(lambda d, r, m=mode: times(b10, d, r, m), EVENT, base)
    res["Q1_stopped"] = with_placebo(lambda d, r: stopped_share(p, d, r), EVENT, base)
    res["Q4_restart"] = restart_order(p, EVENT, base)
    res["curves"] = {m: curves(b10, EVENT, base, m) for m in ("tramvaj", "metro", "autobus", "trolejbus")}

    checks = {"metro_control": metro_control(p, EVENT)}
    for name, kw in {"threshold_0_85": {"thr90": 0.85}, "all_six_bins": {"need": 6},
                     "mean_delay": {"stat": "d_mean"}}.items():
        checks[name] = with_placebo(lambda d, r, kw=kw: times(b10, d, r, "tramvaj", **kw), EVENT, base)
    for width in (5, 15):
        bw = binned(p, width)
        of = 60 // width
        checks[f"bins_{width}_min"] = with_placebo(
            lambda d, r, bw=bw, w=width, of=of: {
                "T50": hhmm(t_service(bw, d, r, "tramvaj", 0.5, w, of - 1, of)),
                "T90": hhmm(t_service(bw, d, r, "tramvaj", 0.9, w, of - 1, of)),
                "TD": hhmm(t_delay(bw, d, r, "tramvaj", w, "d_median", of - 1, of))}, EVENT, base)
    checks["Q1_12_10_to_12_40"] = with_placebo(lambda d, r: stopped_share(p, d, r, NOON + 10, NOON + 40), EVENT, base)
    dep = binned(p[p.t_dep.notna()], col="t_dep")
    checks["departures"] = {"T50": hhmm(t_service(dep, EVENT, base, "tramvaj", 0.5)),
                            "T90": hhmm(t_service(dep, EVENT, base, "tramvaj", 0.9))}
    checks["june_curves_tram_R"] = curves(b10, EVENT, JUNE, "tramvaj")["R"]
    res["checks"] = checks
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("modes", "Q1_stopped")}, indent=1))
    print(json.dumps(checks["metro_control"], indent=1))


if __name__ == "__main__":
    main()
