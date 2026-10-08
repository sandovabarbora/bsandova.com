"""Post-hoc check of Part 2's metro test (H2), added 8 October 2026, not registered.

The registered distance is to the nearest of the 58 stations of the network (the GTFS of 28 September 2026 plus Flora,
closed in 2026 but open at the election). Two of them, Pankrác (line C) and Českomoravská (line B), were closed for
reconstruction on election day, 3–4 October 2025 (Pankrác reopened on 19 December 2025, Českomoravská in early 2026).
This re-runs H2 exactly as registered, same code and seed, once with the registered distances (to confirm the
published estimate) and once with the distance to the 56 stations open on election day.

Writes assets/praha/rings_metro_open.json.

    uv run --with pandas --with numpy --with scipy --with statsmodels --with pyarrow --with shapely --with pyproj \
        python tools/praha/rings_metro_open.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely import wkb

sys.path.insert(0, str(Path(__file__).parent))
import rings_extended as rx  # noqa: E402
from metro import metro_stations  # noqa: E402

CLOSED = ["Pankrác", "Českomoravská"]
OUT = Path(__file__).resolve().parents[2] / "assets" / "praha" / "rings_metro_open.json"


def run(d, stations) -> dict:
    x, y = Transformer.from_crs(4326, 5514, always_xy=True).transform(stations.stop_lon.values, stations.stop_lat.values)
    d = d.copy()
    d["metro_m"] = np.hypot(d.cx.values[:, None] - x[None, :], d.cy.values[:, None] - y[None, :]).min(axis=1)
    d["log2_metro"] = np.log2(d.metro_m / 1000)
    j = d.merge(rx.results(2025), on=["momc", "cislo"], how="left")
    u = rx.to_clusters(j[j.V.notna()])
    return rx.h2(u, np.random.default_rng(rx.SEED))


def main() -> None:
    d = rx.frame()
    cent = [wkb.loads(g).centroid for g in rx.pd.read_parquet(rx.RAW / "design.parquet", columns=["geom_wkb"]).geom_wkb]
    d["cx"], d["cy"] = [p.x for p in cent], [p.y for p in cent]
    st = metro_stations()
    assert set(CLOSED) <= set(st.stop_name) and len(st) == 58, (len(st), set(CLOSED) - set(st.stop_name))
    out = {"registered_58_stations": run(d, st), "open_on_election_day_56": run(d, st[~st.stop_name.isin(CLOSED)]),
           "closed": CLOSED, "note": "post hoc, 8 October 2026; not registered"}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    for k in ("registered_58_stations", "open_on_election_day_56"):
        r = out[k]; print(k, r["estimate"], r["ci90_used"], r["outcome"])


if __name__ == "__main__":
    main()
