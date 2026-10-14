"""Post-hoc descriptions of the blackout study, added 14 October 2026 after the registered results were seen.

The registered delay measure (§1 Q3, median delay per bin) breaks down after the restart: about half of the tram passes
in 13:30–14:10 are more than two minutes early against the trip they were matched to, by up to seven hours, so they
were matched to other timetable trips than the ones they ran. Early and late passes then cancel in the median. This
script describes that and a measure that does not cancel: the share of passes more than five minutes off the
timetable either way, shown as a curve against the highest baseline day. A single "back to normal" time from it, by
the registered five-of-six rule, failed its own placebo (one ordinary Friday came out at 19:00), so none is reported.

Writes docs/research/blackout-posthoc.json.

    nice -n 20 uv run --no-project --with pandas --with pyarrow --with numpy python tools/blackout/posthoc.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import CACHE, EVENT, SCREEN, START_MIN  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/research/blackout-posthoc.json"
OFF, EARLY = 300, -120


def shares(p: pd.DataFrame) -> pd.DataFrame:
    t = p[(p["mode"] == "tramvaj") & (p.t >= START_MIN) & (p.t < 22 * 60)]
    t = t.assign(bin=((t.t - START_MIN) // 10).astype(int), off=t.delay.abs() > OFF, early=t.delay < EARLY)
    return t.groupby(["date", "bin"])[["off", "early"]].mean().reindex(
        pd.MultiIndex.from_product([t.date.unique(), range(72)], names=["date", "bin"]))


def main() -> None:
    p = pd.read_parquet(CACHE)
    base = json.loads(SCREEN.read_text())["baseline_days"]
    s = shares(p)
    off, early = s.off.unstack(0), s.early.unstack(0)

    w = p[(p.date == EVENT) & (p["mode"] == "tramvaj") & (p.t >= 13 * 60 + 30) & (p.t < 14 * 60 + 10)]
    rnd = lambda x: [None if pd.isna(v) else round(float(v), 3) for v in x]  # noqa: E731
    out = {
        "note": "post-hoc, added 14 October 2026 after the registered results; see the module docstring",
        "early_13_30_to_14_10": {"passes": int(len(w)), "share_more_than_2_min_early": round(float((w.delay < EARLY).mean()), 3),
                                 "delay_quartiles_s": [round(float(q)) for q in w.delay.quantile([0.25, 0.5, 0.75])],
                                 "most_early_s": int(w.delay.min())},
        "off_schedule_by_hour": {f"{h}:10": {"event": round(float(off[EVENT][(h - 10) * 6 + 1]), 3),
                                              "baseline_max": round(float(off[base].max(axis=1)[(h - 10) * 6 + 1]), 3)}
                                 for h in range(11, 22)},
        "curves": {"off_event": rnd(off[EVENT]), "off_base_max": rnd(off[base].max(axis=1)),
                   "early_event": rnd(early[EVENT]), "early_base_max": rnd(early[base].max(axis=1))},
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("early_13_30_to_14_10", "off_schedule_by_hour")}, indent=1))


if __name__ == "__main__":
    main()
