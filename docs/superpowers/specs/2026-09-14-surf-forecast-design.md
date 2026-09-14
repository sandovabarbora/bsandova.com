# Not worth the flight — surf forecast verification, design

**Date:** 2026-09-14 · **Status:** approved ("klidně rovnou na ty surfing"), building.

## Question
When the forecast says a swell is coming to Portugal in five days, how often is it still
there when you land? And given that, at what forecast and how many days ahead is booking
the flight the right call?

## Data (no keys, no servers)
- **Forecasts:** Open-Meteo Marine API, hourly, 7 days, three wave models (Météo-France
  MFWAM, DWD GWAM, DWD EWAM): swell height, swell period, swell direction, wave height;
  Open-Meteo Forecast API: 10 m wind speed and direction. Spots: Ericeira (38.96 N, 9.42 W),
  Peniche/Supertubos (39.35 N, 9.36 W), Sagres (37.00 N, 8.94 W).
- **Truth proxy:** the same API's `past_days` analysis (lead 0), i.e. the forecast a surfer
  checks the evening before. Stated on the page as a proxy: it is the final model state, not a
  buoy. Portuguese buoys (Instituto Hidrográfico) are available on request only; a Copernicus
  in-situ feed can replace the proxy later without changing the verification code.
- **Climatology:** `past_days=92` at first run, extended by the daily analysis from then on.

## Pipeline
`surf/collect.py` runs daily (GitHub Actions, 06:10 UTC): stores the day's 7-day forecast per
spot and model as daily aggregates per target date (max and mean swell height, mean period,
circular-mean direction, mean wind, offshore flag) in `surf/data/forecasts/<issue-date>.json`,
appends yesterday's analysis to `surf/data/analysis.json`, commits. `surf/verify.py` then
pairs every forecast with the analysis for its target date and writes `surf/data.json`:
- skill by lead day (1–7) and model: MAE and bias of daily max swell height and mean period,
  Spearman rank correlation, hit/miss/false-alarm table for "surfable";
- reliability: P(surfable at lead 0 | forecast said surfable at lead d);
- decision: for lead d and forecast class, the expected value of booking given a flight cost
  and a value of a surf day, both adjustable on the page; the break-even probability.
"Surfable" (v1, adjustable): daily max swell height 1.0–2.5 m, mean period ≥ 9 s, mean
wind ≤ 25 km/h or offshore (E ± 60°).

## Page — `bsandova.com/surf/`
Facts: days collected · spots · latest skill at lead 3 · how often Ericeira was surfable in the
last 92 days. Charts: MAE by lead day per model; reliability diagram; climatology by week.
Decision table with sliders for flight cost and day value. Method and honesty notes: proxy
truth, model family shared between forecast and analysis (skill will read optimistic), n.
"Collecting: N of 14 days" until the first skill numbers can be shown.

## Not in v1
Buoy truth, tide, local wind sea vs swell separation beyond the API's fields, alerts.
