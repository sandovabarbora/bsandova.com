"""Added after the results, not registered: the 34 events one by one, the map of the 28 treated districts and the
example district. Descriptive only; nothing here is an estimate and nothing changes a label.

Builds the events and sub-panels with the frozen code (projects.py, estimate.py, population.py; imported, nothing there
is changed or run beyond building the panels), checks that the panels reproduce the registered point estimate of Q1,
and writes per event: the promise (company, date, promised jobs, cancellation flag), the promised jobs per 100
residents aged 15–64 of the district in year −1 (the Q3 ratio of one event), and the raw gap between the treated
district and the plain mean of its comparison districts in each event year. With every event holding all six years,
the registered Q1 is exactly the mean over events of each event's own gap change (years 1–3 minus years −2 and −1),
so the per-event numbers are a decomposition of the registered estimate, not a new one.

The example district is the event with the most promised jobs, the one registered check 1 leaves out; it was picked
after the per-event gaps had been computed.

Writes docs/research/incentives-districts.json and assets/investment-incentives/{map.json, base.json, 02-map.svg,
districts.json}. The municipal polygons are ČÚZK RÚIAN's (fetched to tools/data/incentives/ruian/ if absent).

    nice -n 20 uv run --no-project --with pandas --with numpy --with geopandas --with pyogrio --with shapely \
        --with matplotlib python -I tools/incentives/districts.py
"""
from __future__ import annotations

import io
import json
import math
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate as E
import population
import projects as P
from common import DATA, PROJECTS_CSV, ROOT, UA

A = ROOT / "assets/investment-incentives"
OUT = ROOT / "docs/research/incentives-districts.json"
RES = ROOT / "docs/research/incentives-results.json"
RUIAN_URL = "https://services.cuzk.gov.cz/shp/stat/epsg-5514/1.zip"
OBCE = DATA / "ruian" / "OBCE_P.shp"
HELD, GREY = "#34507c", "#8a8a86"
STEP_2014 = 2014 * 12  # January 2014, where the base of the published share changes in the MPSV files
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
STATUS = {"ANO": " (cancelled)", "ověřit": " (to be verified)"}


def jobs_text(j: int) -> str:
    return format(j, ",").replace(",", " ")


def ensure_ruian() -> Path:
    if not OBCE.exists():
        OBCE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(RUIAN_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=600) as r, zipfile.ZipFile(io.BytesIO(r.read())) as z:
            for name in z.namelist():
                if Path(name).stem == "OBCE_P":
                    (OBCE.parent / Path(name).name).write_bytes(z.read(name))
    return OBCE


def rings(geom, tol: float) -> list:
    g = geom.simplify(tol, preserve_topology=True)
    return [[[round(x, 3), round(y, 3)] for x, y in p.exterior.coords] for p in getattr(g, "geoms", [g])]


def implied_denominator() -> dict:
    """The national base the published share divides by, read back as sum(job seekers 15-64) / share × 100 summed over
    districts: it tells which months use the economically active base of the old rate and which the population 15-64."""
    from fetch import months, mpsv_name
    out = {}
    for y, m in months():
        f = E.MPSV_DIR / mpsv_name(y, m)
        if not f.exists():
            continue
        items = json.loads(f.read_text(encoding="utf-8"))["polozky"]
        out[f"{y}-{m:02d}"] = sum(it["dosazitelniUchazeci15_64"] / it["podilNezamestnanychOsobPNO"] * 100
                                  for it in items if it.get("podilNezamestnanychOsobPNO"))
    step = [k for a, k in zip(out, list(out)[1:]) if out[k] / out[a] > 1.1]
    assert step == ["2014-01"], step  # the article states the base changes in January 2014 and nowhere else
    return {"by_month": {k: round(v) for k, v in out.items()}, "step": step[0],
            "before": round(np.mean([v for k, v in out.items() if "2013-01" <= k <= "2013-12"])),
            "after": round(np.mean([v for k, v in out.items() if "2014-01" <= k <= "2014-12"]))}


def panels():
    geo = P.load_geo()
    projects = P.load_projects()
    p = P.attach_places(projects, P.places_table(projects, geo))
    raw, _ = P.build_events(p, geo, P.boundary_districts(geo=geo))
    wide = E.load_panel()
    events = E.to_events(raw)
    districts = sorted({u for ev in events for u in (ev.treated, *ev.comparisons)})
    pop = population.load(districts, E.FIRST_MONTH, E.LAST_MONTH)
    return [sp for ev in events if (sp := E.sub_panel(wide, ev, pop=pop))], geo


def company_rows() -> dict[str, dict]:
    return {r["id_projekt"]: r for r in P.read_csv(PROJECTS_CSV)}


def main() -> None:
    res = json.loads(RES.read_text(encoding="utf-8"))
    sps, geo = panels()
    assert [sp.event.id for sp in sps] == res["events_used"]
    est = E.estimate(sps)
    reg = res["primary"]
    assert abs(est["q1"] - reg["estimate"]) < 1e-9, (est["q1"], reg["estimate"])
    assert all(len(sp.years) == len(E.YEARS) for sp in sps)  # balanced, so Q1 is the mean of the per-event changes

    co = company_rows()
    rows = []
    for sp in sps:
        ev = sp.event
        gap = dict(zip(sp.years, (sp.y[0] - sp.y[1:].mean(axis=0)).tolist()))
        change = float(np.mean([gap[k] for k in E.POST]) - np.mean([gap[k] for k in E.PRE]))
        y, m = divmod(ev.month, 12)
        c = co[ev.id]
        rows.append({"id": ev.id, "district": ev.treated, "district_name": geo.district_name[ev.treated],
                     "place": c["lokalita_mesto"], "company": c["nazev_cz_entita_pri_zadani_projektu"],
                     "group": c["nazev_skupina_pri_zadani_projektu"], "decision": c["rozhodnuti_datum"],
                     "year": y, "month": m + 1, "jobs": int(ev.jobs), "cancelled": ev.cancelled, "regime": ev.regime,
                     "comparisons": len(sp.units) - 1, "pop_15_64_year_m1": round(sp.pop_pre),
                     "jobs_per_100": 100 * ev.jobs / sp.pop_pre, "spans_2013_01": E.spans_pno_change(ev),
                     "spans_2014_01": E.covers(ev, STEP_2014, STEP_2014),
                     "gap": {str(k): v for k, v in gap.items()}, "change": change,
                     "treated": {str(k): float(v) for k, v in zip(sp.years, sp.y[0])},
                     "comparison_mean": {str(k): float(v) for k, v in zip(sp.years, sp.y[1:].mean(axis=0))}})
    mean_change = float(np.mean([r["change"] for r in rows]))
    assert abs(mean_change - reg["estimate"]) < 1e-9
    example = max(rows, key=lambda r: r["jobs"])
    assert example["id"] == res["checks"]["1_without_largest"]["left_out"]
    OUT.write_text(json.dumps({
        "note": "added after the results, not registered: raw gaps per event, not estimates (tools/incentives/districts.py)",
        "units": "MPSV podilNezamestnanychOsobPNO, percentage points; gap = treated minus the plain mean of the event's "
                 "comparison districts; change = mean gap in years 1-3 minus mean gap in years -2 and -1",
        "mean_change_equals_registered_q1": mean_change,
        "example_rule": "the event with the most promised jobs, the one registered check 1 leaves out; picked after "
                        "the per-event gaps had been computed",
        "example": example["id"], "implied_denominator": implied_denominator(),
        "events": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    write_map(rows)
    print("events", len(rows), "mean change", round(mean_change, 6), "registered", round(reg["estimate"], 6),
          "example", example["district_name"], example["jobs"])


def write_map(rows: list[dict]) -> None:
    import geopandas as gpd

    obce = gpd.read_file(ensure_ruian())
    okresy = obce.to_crs(4326).dissolve("OKRES_KOD").geometry
    okresy.index = okresy.index.astype(str)
    base = {"outline": rings(okresy.union_all(), 0.01), "districts": [r for g in okresy for r in rings(g, 0.008)],
            "water": [], "credit": "base: the 77 districts from ČÚZK RÚIAN"}
    A.mkdir(parents=True, exist_ok=True)
    (A / "base.json").write_text(json.dumps(base, separators=(",", ":")), encoding="utf-8")

    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["district"], []).append(r)
    big = max(rows, key=lambda r: r["jobs"])
    feats = []
    for d, rs in sorted(by.items(), key=lambda kv: min(r["year"] for r in kv[1])):
        rs = sorted(rs, key=lambda r: (r["year"], r["month"]))
        sub = "; ".join(f'{r["company"]}, {jobs_text(r["jobs"])} jobs, {MONTHS[r["month"] - 1][:3]} {r["year"]}'
                        + STATUS.get(r["cancelled"], "") for r in rs)
        feats.append({"id": d, "name": rs[0]["district_name"], "sub": sub, "r": rings(okresy[d], 0.004),
                      "v": {"jobs": sum(r["jobs"] for r in rs), "year": rs[0]["year"], "n": len(rs),
                            "per100": round(sum(r["jobs_per_100"] for r in rs), 2),
                            "change": round(float(np.mean([r["change"] for r in rs])), 2),
                            "cancelled": 1 if any(r["cancelled"] for r in rs) else 0}})
    spec = {"held": HELD, "neg": "#2a7f86", "base": "base.json", "lat0": 49.8, "features": feats,
            "views": [{"key": "jobs", "label": "promised jobs", "fmt": {"dp": 0}, "scale": "seq", "domain": [300, 1500],
                       "note": f'promised jobs of the district\'s events in the study ({big["district_name"]} {jobs_text(big["jobs"])})'},
                      {"key": "year", "label": "year", "fmt": {"dp": 0, "nogroup": True}, "scale": "seq",
                       "domain": [2006, 2020], "note": "year of the district's first decision in the study"},
                      {"key": "per100", "label": "per 100 aged 15–64", "fmt": {"dp": 2}, "scale": "seq", "domain": [0, 2],
                       "note": f'promised jobs per 100 residents aged 15–64 in the year before the decision ({big["district_name"]} {big["jobs_per_100"]:.1f})'},
                      {"key": "change", "label": "raw gap change", "fmt": {"dp": 2, "sign": True, "unit": " pp"},
                       "scale": "div", "domain": [-2, 2],
                       "note": "unemployment share minus comparison districts' mean, years 1–3 minus years −2 and −1; "
                               "mean of the district's events; raw, not an estimate"},
                      {"key": "cancelled", "label": "status", "cats": [{"v": 0, "label": "not flagged"},
                                                                       {"v": 1, "label": "cancelled or to be verified"}]},
                      {"key": "n", "label": "promises", "fmt": {"dp": 0}, "scale": "seq", "domain": [1, 2],
                       "note": f"promises in the study (two in {sum(len(rs) == 2 for rs in by.values())} districts)"}],
            "note": f"The {len(by)} districts of the {len(rows)} promises; one district's raw gap change is not an estimate.",
            "hint": "hover, tap or use the arrow keys for a district",
            "data": ["../assets/investment-incentives/map.json", "../assets/investment-incentives/districts.json"]}
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (A / "districts.json").write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "svg.fonttype": "none"})
    f, ax = plt.subplots(figsize=(7.2, 4.0))
    small = okresy.simplify(0.008, preserve_topology=True)
    small.plot(ax=ax, color="#f2f2ef", edgecolor="#ffffff", linewidth=0.6)
    treated = small[small.index.isin(list(by))]
    jobs = np.array([sum(r["jobs"] for r in by[d]) for d in treated.index])
    shade = [HELD if j >= 1000 else "#7d92b5" if j >= 600 else "#c9d3e3" for j in jobs]
    treated.plot(ax=ax, color=shade, edgecolor="#ffffff", linewidth=0.6)
    gpd.GeoSeries([okresy.union_all().simplify(0.01)], crs=4326).boundary.plot(ax=ax, color="#c9c9c4", linewidth=0.8)
    for d, g in treated.items():
        c = g.representative_point()
        ax.annotate(str(min(r["year"] for r in by[d]))[2:].join(("’", "")), (c.x, c.y), ha="center", va="center",
                    fontsize=6.5, color="white" if sum(r["jobs"] for r in by[d]) >= 600 else "#111")
    for c, lab in (("#c9d3e3", "300–599 promised jobs"), ("#7d92b5", "600–999"), (HELD, "1 000 or more")):
        ax.scatter([], [], s=40, marker="s", color=c, label=lab)
    ax.set_aspect(1 / math.cos(math.radians(49.8)))
    ax.set_axis_off()
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    f.tight_layout()
    f.savefig(A / "02-map.svg")
    plt.close(f)


if __name__ == "__main__":
    main()
