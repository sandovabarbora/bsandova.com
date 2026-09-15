"""Collect the daily weather forecast for two Prague stations, and what the stations then measured.

    python weather/collect.py               # today's 7-day forecast (4 models) + observations to date this month
    python weather/collect.py --climatology  # once: 1991–2020 day-of-year climatology from the ČHMÚ historical file

Truth is a station, not a model: the Czech Hydrometeorological Institute (ČHMÚ) publishes daily
climatological values per station as open data, one file per station and month, rewritten after
each day ends. The three elements used are defined over specific 24-hour windows, and the forecast
is aggregated from hourly values into the same windows, or the comparison would be wrong by design:

    TMA, TMI   daily max / min temperature, read at 20:00 UTC, over (D-1 20:00, D 20:00]
    SRA        precipitation total, read at 06:00 UTC, over (D-1 06:00, D 06:00]

Forecasts: Open-Meteo, hourly temperature_2m and precipitation, four models (best_match, ICON,
ECMWF IFS 0.25°, GFS), 7 days ahead plus the previous day so the 20:00 window of the first target
day is complete. Stored per issue date as daily aggregates per station × model × target date.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FORECASTS = DATA / "forecasts"
OBS = DATA / "observations.json"
CLIM = DATA / "climatology.json"

STATIONS = {
    "ruzyne": {"lat": 50.100278, "lon": 14.255556, "wsi": "0-20000-0-11518", "name": "Praha, Ruzyně", "elev": 364},
    "klementinum": {"lat": 50.086634, "lon": 14.416923, "wsi": "0-203-0-11514", "name": "Praha, Klementinum", "elev": 191},
}
MODELS = ["best_match", "icon_seamless", "ecmwf_ifs025", "gfs_seamless"]
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
CHMI = "https://opendata.chmi.cz/meteorology/climate"
ELEMENTS = {"TMA": "tmax", "TMI": "tmin", "SRA": "precip"}


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def windows(times: list[str], values: list, kind: str) -> dict[str, float | None]:
    """Aggregate hourly values into ČHMÚ daily windows. kind: 'max'/'min' → (D-1 20:00, D 20:00]; 'sum' → (D-1 06:00, D 06:00]."""
    end_hour = 6 if kind == "sum" else 20
    buckets: dict[str, list] = defaultdict(list)
    for t, v in zip(times, values, strict=True):
        if v is None:
            continue
        # an hourly value stamped h covers (h, h+1]; shifting by (24 - end_hour) hours moves every
        # window's end to midnight, so the calendar date after the shift is the window's day
        target = (datetime.fromisoformat(t) + timedelta(hours=24 - end_hour)).date()
        buckets[target.isoformat()].append(v)
    out = {}
    for day, vals in buckets.items():
        if len(vals) < 24:  # incomplete window (edges of the series)
            continue
        out[day] = round(max(vals) if kind == "max" else min(vals) if kind == "min" else sum(vals), 2)
    return out


def fetch_forecast(lat: float, lon: float) -> dict[str, dict[str, dict]]:
    url = (f"{OPEN_METEO}?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation"
           f"&models={','.join(MODELS)}&forecast_days=7&past_days=1&timezone=UTC")
    h = get(url)["hourly"]
    out = {}
    for m in MODELS:
        t = h[f"temperature_2m_{m}"]; p = h[f"precipitation_{m}"]
        tmax = windows(h["time"], t, "max"); tmin = windows(h["time"], t, "min"); pr = windows(h["time"], p, "sum")
        days = sorted(set(tmax) & set(tmin) & set(pr))
        out[m] = {d: {"tmax": tmax[d], "tmin": tmin[d], "precip": pr[d]} for d in days}
    return out


def fetch_observations(wsi: str, months: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = defaultdict(dict)
    for ym in months:
        try:
            rows = get(f"{CHMI}/recent/data/daily/dly-{wsi}-{ym}.json")["data"]["data"]["values"]
        except Exception as e:  # noqa: BLE001 - a missing month file is a gap, reported by the verifier
            print(f"  {wsi} {ym}: {e}")
            continue
        for _, element, _vtype, dt, val, _flag, _q in rows:
            if element in ELEMENTS and val is not None:
                out[dt[:10]][ELEMENTS[element]] = val
    return dict(out)


def climatology(wsi: str, years: tuple[int, int] = (1991, 2020)) -> dict[str, dict]:
    """Day-of-year climatology from the historical file: mean/sd of TMA and TMI and the rain frequency
    (SRA ≥ 1.0 mm, ≥ 0.1 mm) in a ±15-day window over the reference years."""
    print(f"  downloading historical {wsi} (large)…")
    rows = get(f"{CHMI}/historical/data/daily/dly-{wsi}.json")["data"]["data"]["values"]
    by_doy: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for _, element, _v, dt, val, *_ in rows:
        if element not in ELEMENTS or val is None:
            continue
        d = date.fromisoformat(dt[:10])
        if not years[0] <= d.year <= years[1]:
            continue
        by_doy[d.timetuple().tm_yday][ELEMENTS[element]].append(val)
    out = {}
    for doy in range(1, 367):
        vals: dict[str, list] = defaultdict(list)
        for k in range(-15, 16):
            for key, v in by_doy.get((doy - 1 + k) % 366 + 1, {}).items():
                vals[key] += v
        if not vals["tmax"]:
            continue
        mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
        sd = lambda xs: (sum((x - mean(xs)) ** 2 for x in xs) / max(1, len(xs) - 1)) ** 0.5  # noqa: E731
        out[str(doy)] = {
            "tmax_mean": round(mean(vals["tmax"]), 2), "tmax_sd": round(sd(vals["tmax"]), 2),
            "tmin_mean": round(mean(vals["tmin"]), 2), "tmin_sd": round(sd(vals["tmin"]), 2),
            "rain1_freq": round(sum(1 for x in vals["precip"] if x >= 1.0) / len(vals["precip"]), 3) if vals["precip"] else None,
            "rain01_freq": round(sum(1 for x in vals["precip"] if x >= 0.1) / len(vals["precip"]), 3) if vals["precip"] else None,
            "n": len(vals["tmax"]),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--climatology", action="store_true")
    args = parser.parse_args()
    FORECASTS.mkdir(parents=True, exist_ok=True)
    today = date.today()
    issue = today.isoformat()
    fc = {s: fetch_forecast(c["lat"], c["lon"]) for s, c in STATIONS.items()}
    (FORECASTS / f"{issue}.json").write_text(json.dumps({"issued": issue, "models": MODELS, "stations": fc}, separators=(",", ":")) + "\n")
    print(f"forecast {issue}: {len(STATIONS)} stations × {len(MODELS)} models × {len(next(iter(fc['ruzyne'].values())))} days")
    obs = json.loads(OBS.read_text()) if OBS.exists() else {"source": "ČHMÚ open data, daily climatological values (TMA, TMI at 20:00 UTC; SRA at 06:00 UTC)", "stations": {}}
    months = sorted({today.strftime("%Y%m"), (today.replace(day=1) - timedelta(days=1)).strftime("%Y%m")})
    for s, c in STATIONS.items():
        recs = fetch_observations(c["wsi"], months)
        obs["stations"].setdefault(s, {}).update({d: r for d, r in recs.items() if d < issue and "tmax" in r})
    OBS.write_text(json.dumps(obs, separators=(",", ":"), sort_keys=True) + "\n")
    print("observation days:", {s: len(v) for s, v in obs["stations"].items()})
    if args.climatology:
        clim = {"reference": "1991–2020, ±15-day window by day of year", "stations": {s: climatology(c["wsi"]) for s, c in STATIONS.items()}}
        CLIM.write_text(json.dumps(clim, separators=(",", ":")) + "\n")
        print("climatology days:", {s: len(v) for s, v in clim["stations"].items()})


if __name__ == "__main__":
    main()
