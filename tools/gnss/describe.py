"""Added after the results, not registered: the share of degraded position reports per region and sampled day.

Descriptive only, no interval and no label. Imports the frozen estimation code (tag gnss-code) unchanged and uses its
own panel, airframe drop and day sums, the same ones behind the registered degraded-position-day counts, which this
script reproduces before it writes anything. Writes docs/research/gnss-describe.json.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with shapely --with numpy \
        --with pandas --with pyarrow python -I tools/gnss/describe.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate as E  # noqa: E402
import fetch as F  # noqa: E402
import regions as R  # noqa: E402

OUT = R.ROOT / "docs/research/gnss-describe.json"


def main() -> None:
    P = E.load_panel(F.DAYS, F.parse_kp((F.KP_DIR / F.KP_NAME).read_text()))
    r = P.points["primary"]
    U, G = E.sums(r, np.ones(P.n_days), P.base_w, r.dkey, P.n_days * E.NREG)
    U, G = U.reshape(P.n_days, E.NREG), G.reshape(P.n_days, E.NREG)
    share = E.ratio(G, U)

    published = json.loads(E.OUT.read_text(encoding="utf-8"))["degraded_position_days"]
    if E.degraded_position_days(P) != published:
        sys.exit("the day sums do not reproduce the registered degraded-position-day counts; nothing written")

    regions = [*E.STUDY, "CTRL"]
    c = E.RID["CTRL"]
    days = []
    for i, (wed, used) in enumerate(zip(P.wed, P.used)):
        row = {"wednesday": str(wed), "date_used": str(used), "study_year": int(P.year[i]) + 1}
        for x in regions:
            k = E.RID[x]
            row[x] = {"usable": int(round(U[i, k])), "degraded": int(round(G[i, k])),
                      "share": None if not np.isfinite(share[i, k]) else float(share[i, k])}
            if x != "CTRL":
                ok = U[i, k] >= E.DAY_MIN_POINTS and U[i, c] >= E.DAY_MIN_POINTS
                row[x]["degraded_position_day"] = bool(
                    ok and share[i, k] >= E.DAY_MIN_SHARE - E.EPS and share[i, k] - share[i, c] >= E.DAY_MIN_GAP - E.EPS)
        days.append(row)
    pooled = {x: {"usable": int(round(U[:, E.RID[x]].sum())), "degraded": int(round(G[:, E.RID[x]].sum()))}
              for x in regions}
    OUT.write_text(json.dumps({
        "note": "added after the results, not registered: per-day shares of degraded position reports (NACp below 8) "
                "on primary usable points after the entry buffer and the persistent-airframe drop, from the frozen "
                "estimation code's own day sums (tools/gnss/describe.py); descriptive, no interval, no label",
        "rule": "a degraded-position day: at least 300 usable points in the region and in control, a day share of at "
                "least 2 % and at least 2 percentage points above control's share that day (design §4)",
        "reproduces_registered_day_counts": True,
        "pooled_points": pooled,
        "days": days,
        "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}: {len(days)} days; pooled {pooled}")


if __name__ == "__main__":
    main()
