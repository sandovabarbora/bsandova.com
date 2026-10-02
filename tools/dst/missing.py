"""Share of window records with an unknown hour, by crash kind (pedestrian or not), as promised in the data-step note.

    uv run --with pandas --with pyarrow --with shapely python tools/dst/missing.py
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import D, DAYS, YEARS, change_day, parse_date, parse_hour, records  # noqa: E402

out = {"ped": [0, 0], "other": [0, 0]}
for year in YEARS:
    c0 = change_day(year)
    lo, hi = c0 + timedelta(days=-14), c0 + timedelta(days=14)
    for reg, p2a, p2b, p6, p19 in records(year):
        d = parse_date(p2a)
        if d is None or not (lo <= d <= hi) or d == c0:
            continue
        k = "ped" if p6 == "4" else "other"
        out[k][0] += 1
        out[k][1] += parse_hour(p2b) is None
res = {k: {"records": n, "unknown_hour": u, "share": u / n} for k, (n, u) in out.items()}
(D / "missing.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res))
