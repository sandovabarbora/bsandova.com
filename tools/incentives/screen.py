"""Screening of the investment incentives design (§3), before any outcome is compared.

Projects: rows, incentive rows, place matching, decision years and promised-jobs bands, events, comparison districts
per event, dropped events and why, the event and treated-district counts that decide the minimum rule of §4, and
whether the decoded dashboard table is complete. MPSV files: months present, districts per month, per month the number
of districts carrying each field used (present and not null), whether the population field changes within a calendar
year (one yes/no per district-year from an equality test of hashes, never the value), and the outcome rule of §2 that
follows. Districts moved in 2007 and 2016. No job-seeker or population value is printed, stored or compared across
districts or periods. Writes docs/research/incentives-screening.json.

    uv run --no-project --with pandas python -I tools/incentives/screen.py
"""
from __future__ import annotations

import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import projects as P  # noqa: E402
from common import MPSV_DIR, RAW, ROOT  # noqa: E402
from fetch import months, mpsv_name  # noqa: E402

OUT = ROOT / "docs/research/incentives-screening.json"
JOBSEEKERS = "dosazitelniUchazeci15_64"
POPULATION = "celkemObyvatelstvo15_64"
FALLBACK = "uchazeciOZamestnaniUoZ"
FIELDS = (JOBSEEKERS, POPULATION, FALLBACK)
SPLIT_YEAR = 2013
MIN_EVENTS, MIN_DISTRICTS = 20, 15
BANDS = ((0, 1, "0"), (1, 50, "1-49"), (50, 100, "50-99"), (100, 200, "100-199"), (200, 300, "200-299"),
         (300, 500, "300-499"), (500, 1000, "500-999"), (1000, float("inf"), "1000+"))


def band(jobs: float) -> str:
    return next(lab for lo, hi, lab in BANDS if lo <= jobs < hi)


def present(item: dict, field: str) -> bool:
    return item.get(field) is not None


def digest(v) -> str:
    """A stand-in for a value that can be compared for equality without being kept or shown."""
    return hashlib.sha256(repr(v).encode()).hexdigest()


def mpsv_structure(mpsv_dir: Path = MPSV_DIR) -> dict:
    per_month, district_sets, pop_hashes = {}, {}, collections.defaultdict(set)
    for y, m in months():
        f = mpsv_dir / mpsv_name(y, m)
        key = f"{y}-{m:02d}"
        if not f.exists():
            per_month[key] = {"file": False}
            continue
        items = json.loads(f.read_text(encoding="utf-8"))["polozky"]
        districts = sorted({it["okres"].split("/")[-1] for it in items})
        district_sets[key] = tuple(districts)
        per_month[key] = {"file": True, "districts": len(districts), "rows": len(items),
                          "present": {fld: sum(present(it, fld) for it in items) for fld in FIELDS}}
        for it in items:
            if present(it, POPULATION):
                pop_hashes[(it["okres"], y)].add(digest(it[POPULATION]))
    modal = collections.Counter(district_sets.values()).most_common(1)[0][0] if district_sets else ()
    for key, ds in district_sets.items():
        per_month[key]["same_district_set"] = ds == modal
    varies = {k: len(h) > 1 for k, h in pop_hashes.items()}
    by_year = collections.defaultdict(lambda: [0, 0])
    for (_okres, y), v in varies.items():
        by_year[y][0 if v else 1] += 1
    return {"months": per_month, "modal_district_count": len(modal),
            "population_within_year": {"district_years_checked": len(varies),
                                       "district_years_varying": sum(varies.values()),
                                       "by_year_varying_constant": {str(y): v for y, v in sorted(by_year.items())}}}


def field_everywhere(per_month: dict, field: str, pre: bool | None) -> str:
    """'all', 'none' or 'some': whether every district of every month (before 2013, from 2013, or all) has the field."""
    keys = [k for k, v in per_month.items() if v.get("file")
            and (pre is None or (int(k[:4]) < SPLIT_YEAR) == pre)]
    full = [per_month[k]["present"][field] == per_month[k]["districts"] for k in keys]
    empty = [per_month[k]["present"][field] == 0 for k in keys]
    return "all" if all(full) else "none" if all(empty) else "some"


def outcome_rule(per_month: dict) -> dict:
    """§2: the primary outcome, the fixed fallback, or a descriptive panel from January 2013, from presence alone.

    A field counts as missing before 2013 only if no pre-2013 month carries it; months where it is missing for some
    districts are dropped and listed under the rule that applies. A population field absent in every month leaves no
    rule of §2 that can be computed; that is reported, not resolved.
    """
    p = {f: {"pre2013": field_everywhere(per_month, f, True), "from2013": field_everywhere(per_month, f, False)}
         for f in FIELDS}
    pop, js, fb = p[POPULATION], p[JOBSEEKERS], p[FALLBACK]
    if pop["pre2013"] == "none" and pop["from2013"] == "none":
        rule = "none: the population field is absent from every month; design §2 gives no computable outcome"
    elif js["pre2013"] != "none" and pop["pre2013"] != "none":
        rule = "primary"
    elif js["pre2013"] == "none" and fb["pre2013"] != "none" and pop["pre2013"] != "none" and fb["from2013"] != "none":
        rule = "fallback: uchazeciOZamestnaniUoZ / celkemObyvatelstvo15_64 in every month"
    else:
        rule = "descriptive: panel from January 2013, window 1 January 2015 - 31 December 2021, no labels"
    fields_needed = (FALLBACK, POPULATION) if rule.startswith("fallback") else (JOBSEEKERS, POPULATION)
    dropped = sorted(k for k, v in per_month.items() if not v.get("file")
                     or any(v["present"][f] < v["districts"] for f in fields_needed) or not v["same_district_set"])
    return {"presence": p, "rule": rule, "months_dropped": dropped if not rule.startswith("none") else "n/a"}


def project_counts(p, geo, events, dropped) -> dict:
    ipo = p
    by_year = collections.Counter(d.year for d in ipo["date"])
    return {
        "rows_ipo": len(ipo),
        "place_status_of_ipo_rows": dict(collections.Counter(ipo["status"])),
        "multi_site_rows": int((ipo["status"] == "multi").sum()),
        "matched_to_one_district_rows": int((ipo["status"] == "matched").sum()),
        "by_decision_year": {str(y): by_year[y] for y in sorted(by_year)},
        "by_jobs_band": dict(collections.Counter(band(j) for j in ipo["jobs"])),
        "blockers_200_unplaceable": {
            "ambiguous_or_unmatched_rows": int(((ipo["jobs"] >= P.BLOCK_JOBS) & ipo["status"].isin(["ambiguous", "unmatched"])).sum()),
            "multi_site_rows": int(((ipo["jobs"] >= P.BLOCK_JOBS) & (ipo["status"] == "multi")).sum()),
        },
    }


def main() -> None:
    geo = P.load_geo()
    projects = P.load_projects()
    places = P.places_table(projects, geo)
    p = P.attach_places(projects, places)
    boundaries = P.boundary_districts(geo=geo)
    events, dropped = P.build_events(p, geo, boundaries)
    import pandas as pd
    all_rows = len(pd.read_csv(P.PROJECTS_CSV, dtype=str))
    completeness = json.loads((RAW / "czechinvest_completeness.json").read_text(encoding="utf-8"))
    n_events, n_districts = len(events), len({e["district"] for e in events})
    mpsv = mpsv_structure()
    rule = outcome_rule(mpsv["months"])
    out = {
        "design": "docs/research/incentives-design.md §3",
        "projects": {"rows": all_rows} | project_counts(p, geo, events, dropped),
        "place_strings": {"total": len(places), "by_status": dict(collections.Counter(places["status"])),
                          "unmatched_or_ambiguous": places.loc[places["status"].isin(["unmatched", "ambiguous"]),
                                                               ["lokalita_kraj", "lokalita_mesto", "status"]].to_dict("records")},
        "events": [{k: e[k] for k in ("id_projekt", "date", "jobs", "lokalita_mesto", "district", "district_name",
                                      "n_comparisons", "cancelled", "regime")} for e in events],
        "dropped": [{k: v for k, v in d.items() if k != "month"} for d in dropped],
        "dropped_by_reason": dict(collections.Counter(d["reason"] for d in dropped)),
        "n_events": n_events, "n_treated_districts": n_districts,
        "minimum_rule": {"events_min": MIN_EVENTS, "districts_min": MIN_DISTRICTS,
                         "met": n_events >= MIN_EVENTS and n_districts >= MIN_DISTRICTS,
                         "consequence": None if (n_events >= MIN_EVENTS and n_districts >= MIN_DISTRICTS)
                         else "Q1 reported without labels 1-3 (§4)"},
        "comparison_district_use": dict(collections.Counter(c for e in events for c in e["comparisons"])),
        "dashboard_table": {k: completeness[k] for k in ("date", "dashboard_row_count", "registered_rows", "paged_rows",
                                                         "identical_to_registered", "registered_sha256")},
        "mpsv": mpsv | {"outcome_rule": rule},
        "boundary_districts": {lab: [{"code": d, "name": geo.district_name[d]} for d in ds]
                               for lab, ds in boundaries.items()},
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("events", n_events, "treated districts", n_districts, "minimum met", out["minimum_rule"]["met"])
    print("dropped", out["dropped_by_reason"])
    print("outcome rule:", rule["rule"])
    print("presence:", rule["presence"])
    print("population within year:", mpsv["population_within_year"]["district_years_checked"],
          mpsv["population_within_year"]["district_years_varying"])


if __name__ == "__main__":
    main()
