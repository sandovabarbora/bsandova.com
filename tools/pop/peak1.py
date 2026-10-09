"""Pop, measured, part 2, post-hoc (9 October 2026): Taylor Swift's own global number ones placed among the number
ones, as series design §2 asks ("every other song of the artist with global peak 1 is also placed in Q1") and the
published part had not done. The number-ones set is part 1's (docs/research/harry-styles-ones.csv, kept rows); the
method is analyse.py's q1 (Kaplan–Meier, 2 000 bootstrap resamples). Writes docs/research/taylor-swift-peak1-posthoc.json.

    uv run --with numpy python tools/pop/peak1.py
"""

from __future__ import annotations

import json

import numpy as np

import analyse as A

ARTIST = "Taylor Swift - "


def main() -> None:
    ones = [r for r in A.rows("harry-styles-ones.csv") if r["kept"] == "True"]
    days = np.array([int(r["days"]) for r in ones])
    event = np.array([r["still_charting"] == "False" for r in ones])
    rng = np.random.default_rng(20261009)
    placed = []
    for r in ones:
        if not r["label"].startswith(ARTIST):
            continue
        t = int(r["days"])
        boot = []
        for _ in range(A.B):
            i = rng.integers(0, len(days), len(days))
            boot.append(A.surv_at(days[i], event[i], t))
        placed.append({"label": r["label"], "days": t, "still_charting": r["still_charting"] == "True",
                       "share_longer": A.surv_at(days, event, t),
                       "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]})
    out = {"post_hoc": "9 October 2026", "reference": "harry-styles-ones.csv, kept rows", "n_number_ones": len(ones),
           "songs": sorted(placed, key=lambda p: -p["days"])}
    (A.R / "taylor-swift-peak1-posthoc.json").write_text(json.dumps(out, indent=1))
    print("written taylor-swift-peak1-posthoc.json", len(placed))


if __name__ == "__main__":
    main()
