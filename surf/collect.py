"""Collect the daily surf forecast for three Portuguese spots, and the analysis for yesterday.

    python surf/collect.py            # today's 7-day forecast (3 wave models) + yesterday's analysis
    python surf/collect.py --climatology   # also fetch the last 92 days of analysis (first run)

Everything is stored as daily aggregates per target date, so the files stay small and the
verification only ever compares like with like: forecast issued on day D for target T,
against the analysis of T fetched on T+1. No keys, no servers: Open-Meteo only.
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FORECASTS = DATA / "forecasts"
ANALYSIS = DATA / "analysis.json"

SPOTS = {
    "ericeira": (38.96, -9.42),
    "peniche": (39.35, -9.36),
    "sagres": (37.00, -8.94),
}
MODELS = ["meteofrance_wave", "gwam", "ewam"]
MARINE = "https://marine-api.open-meteo.com/v1/marine"
WEATHER = "https://api.open-meteo.com/v1/forecast"
WAVE_VARS = "swell_wave_height,swell_wave_period,swell_wave_direction,wave_height"


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def circular_mean(degrees: list[float]) -> float | None:
    vals = [d for d in degrees if d is not None]
    if not vals:
        return None
    x = sum(math.cos(math.radians(d)) for d in vals) / len(vals)
    y = sum(math.sin(math.radians(d)) for d in vals) / len(vals)
    return round(math.degrees(math.atan2(y, x)) % 360, 0)


def mean(xs: list) -> float | None:
    vals = [x for x in xs if x is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def daily(hourly: dict, h: str, p: str, d: str, w: str, ws: str | None, wd: str | None) -> dict[str, dict]:
    """Aggregate hourly series to one record per target date."""
    out: dict[str, dict] = {}
    times = hourly["time"]
    for day in sorted({t[:10] for t in times}):
        idx = [i for i, t in enumerate(times) if t.startswith(day) and 6 <= int(t[11:13]) <= 20]  # daylight hours
        if len(idx) < 6:
            continue
        rec = {
            "swell_max": max((hourly[h][i] for i in idx if hourly[h][i] is not None), default=None),
            "swell_mean": mean([hourly[h][i] for i in idx]),
            "period_mean": mean([hourly[p][i] for i in idx]),
            "dir_mean": circular_mean([hourly[d][i] for i in idx]),
            "wave_max": max((hourly[w][i] for i in idx if hourly[w][i] is not None), default=None),
        }
        if ws and ws in hourly:
            rec["wind_mean"] = mean([hourly[ws][i] for i in idx])
            rec["wind_dir"] = circular_mean([hourly[wd][i] for i in idx])
        out[day] = rec
    return out


def fetch_forecast(lat: float, lon: float) -> dict[str, dict[str, dict]]:
    """Return {model: {target_date: aggregates}} for the next 7 days, wind attached to each."""
    marine = get(f"{MARINE}?latitude={lat}&longitude={lon}&hourly={WAVE_VARS}&models={','.join(MODELS)}&forecast_days=7&timezone=UTC")
    wind = get(f"{WEATHER}?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&forecast_days=7&timezone=UTC")
    hourly = marine["hourly"]
    wind_daily = daily({"time": wind["hourly"]["time"], "wind_speed_10m": wind["hourly"]["wind_speed_10m"],
                        "wind_direction_10m": wind["hourly"]["wind_direction_10m"],
                        "_h": [None] * len(wind["hourly"]["time"]), "_p": [None] * len(wind["hourly"]["time"]),
                        "_d": [None] * len(wind["hourly"]["time"]), "_w": [None] * len(wind["hourly"]["time"])},
                       "_h", "_p", "_d", "_w", "wind_speed_10m", "wind_direction_10m")
    result = {}
    for m in MODELS:
        recs = daily(hourly, f"swell_wave_height_{m}", f"swell_wave_period_{m}", f"swell_wave_direction_{m}", f"wave_height_{m}", None, None)
        for day, rec in recs.items():
            rec["wind_mean"] = wind_daily.get(day, {}).get("wind_mean")
            rec["wind_dir"] = wind_daily.get(day, {}).get("wind_dir")
        result[m] = recs
    return result


def fetch_analysis(lat: float, lon: float, past_days: int) -> dict[str, dict]:
    """The model's own past state (lead 0): the truth proxy. Default wave model (MFWAM)."""
    marine = get(f"{MARINE}?latitude={lat}&longitude={lon}&hourly={WAVE_VARS}&past_days={past_days}&forecast_days=1&timezone=UTC")
    wind = get(f"{WEATHER}?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&past_days={past_days}&forecast_days=1&timezone=UTC")
    h = marine["hourly"]; h["wind_speed_10m"] = wind["hourly"]["wind_speed_10m"]; h["wind_direction_10m"] = wind["hourly"]["wind_direction_10m"]
    recs = daily(h, "swell_wave_height", "swell_wave_period", "swell_wave_direction", "wave_height", "wind_speed_10m", "wind_direction_10m")
    today = date.today().isoformat()
    return {d: r for d, r in recs.items() if d < today}  # only complete past days


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--climatology", action="store_true", help="fetch the last 92 days of analysis (first run)")
    args = parser.parse_args()
    FORECASTS.mkdir(parents=True, exist_ok=True)
    issue = date.today().isoformat()
    forecasts = {spot: fetch_forecast(*coords) for spot, coords in SPOTS.items()}
    (FORECASTS / f"{issue}.json").write_text(json.dumps({"issued": issue, "models": MODELS, "spots": forecasts}, separators=(",", ":")) + "\n")
    print(f"forecast {issue}: {len(SPOTS)} spots × {len(MODELS)} models × 7 days")
    analysis = json.loads(ANALYSIS.read_text()) if ANALYSIS.exists() else {"model": "meteofrance_wave (analysis, lead 0)", "spots": {}}
    past = 92 if args.climatology else 2
    for spot, coords in SPOTS.items():
        recs = fetch_analysis(*coords, past)
        analysis["spots"].setdefault(spot, {}).update(recs)
    ANALYSIS.write_text(json.dumps(analysis, separators=(",", ":"), sort_keys=True) + "\n")
    print("analysis days per spot:", {s: len(v) for s, v in analysis["spots"].items()})


if __name__ == "__main__":
    main()
