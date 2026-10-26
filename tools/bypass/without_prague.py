"""Added after the results, not registered: Q1, Q2 and check 1 (all accidents, Q1 and Q2) with Prague left out of the
comparison towns, approved by the author on 26 October 2026 after the note on damage-only accidents.

Prague (554782) enters the comparison group only through BYP-057, the bypass of Úvaly, whose resampling unit holds
Úvaly and Prague. Only Prague's row is dropped; Úvaly stays as the unit's one town, so the number of comparison units
and the bootstrap draw sequence by unit are the same as in the registered run. Everything else is the frozen code
at the tag bypass-code-2, imported and not changed: the town selection, the count table, the fit, the bypass-level
bootstrap (2 000 draws, seed 20261015, Q1 and Q2 as the gate), the lead test and the label rule. Before the run, the
point estimates with Prague kept are checked against the registered results file.

Writes docs/research/bypass-without-prague.json.

    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with pandas --with numpy \
        --with pyarrow --with statsmodels --with scipy --with shapely --with pyproj --with geopandas --with pyogrio \
        python -I tools/bypass/without_prague.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate as E  # noqa: E402
import screen as S  # noqa: E402
import towns as T  # noqa: E402

PRAGUE = 554782
OUT = T.ROOT / "docs/research/bypass-without-prague.json"
LOG = T.ROOT / "tools/data/bypass/bootstrap-draws-without-prague.jsonl"
SPECS = {"q1": E.Spec("q1"), "q2": E.Spec("q2"), "1_all_accidents_q1": E.Spec("q1_all"),
         "1_all_accidents_q2": E.Spec("q2_all")}


def main() -> None:
    assert E.headline_is_a()
    b = T.load_list()
    table, _ = S.areas(S.ku_versions(), S.ku_areas(), [f"{y}-01-01" for y in range(T.FIRST_YEAR, T.LAST_YEAR + 2)])
    towns = E.town_table(T.select(b, S.area_change(table)))
    years = range(T.FIRST_YEAR, T.LAST_YEAR + 1)
    counts = E.real_counts(towns, b)
    registered = json.loads(E.OUT.read_text())

    for k, s in SPECS.items():  # the frozen code reproduces the registered point estimates on the full sample
        f = E.fit(towns, counts, years, s)
        reg = (registered["questions"].get(k) or registered["checks"][k])["est"]
        assert abs(f.est - reg) < 1e-9, (k, f.est, reg)

    prague = towns[towns["town"] == PRAGUE]
    assert len(prague) == 1 and prague["role"].iloc[0] == "comparison"
    unit = prague["cluster"].iloc[0]
    kept = towns[towns["town"] != PRAGUE].reset_index(drop=True)
    left_in_unit = kept.loc[kept["cluster"] == unit, "town_names"].tolist()

    primary = {k: E.fit(kept, counts, years, s) for k, s in SPECS.items()}
    leads = E.fit(kept, counts, years, E.Spec("q1", leads=True), clustered=True).leads
    boot = E.bootstrap(kept, counts, years, SPECS, E.DRAWS, E.SEED, log=LOG, name="without_prague")
    res = {k: E.summary(primary[k], boot["draws"][k]) for k in SPECS}
    n_treated = int((kept["role"] == "treated").sum())
    out = {"note": "added after the results, not registered; does not replace the registered labels",
           "dropped": {"town": PRAGUE, "name": "Praha", "unit": unit, "left_in_unit": left_in_unit},
           "comparison_towns": int((kept["role"] == "comparison").sum()), "treated_towns": n_treated,
           "comparison_units": int(kept.loc[kept["role"] == "comparison", "cluster"].nunique()),
           "years": [years.start, years.stop - 1], "seed": E.SEED, "draws": E.DRAWS, "redrawn": boot["redrawn"],
           "pre_trends": leads, "results": {}}
    for k in SPECS:
        r = res[k]
        r["power"] = E.power(r)
        r["label_by_registered_rule"] = E.label(r["est"], r["ci95"], r["ci90"], differing_trends=True,
                                                minimum_met=n_treated >= E.MIN_TREATED, stage="A")
        r["registered"] = {key: (registered["questions"].get(k) or registered["checks"][k]).get(key)
                           for key in ("est", "ci90", "ci95", "label")}
        out["results"][k] = r
    out["results"]["q2"]["change_inside_built_up_per_town_year"] = res["q1"]["delta_per_town_year"]
    outside = np.asarray(boot["draws"]["q2"]["delta"], float) - np.asarray(boot["draws"]["q1"]["delta"], float)
    out["results"]["q2"]["change_outside_built_up_per_town_year"] = (res["q2"]["delta_per_town_year"]
                                                                     - res["q1"]["delta_per_town_year"])
    out["results"]["q2"]["change_outside_ci95"] = E.interval(outside, 0.95)
    out["versions"] = E.versions()
    OUT.write_text(json.dumps(E.clean(out), indent=1, ensure_ascii=False, default=str))
    for k, r in out["results"].items():
        print(k, round(r["est"], 4), r["ci90"], r["ci95"], r["label_by_registered_rule"])


if __name__ == "__main__":
    main()
