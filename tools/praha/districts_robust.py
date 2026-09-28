"""Part 3 extended, §8: robustness and the specification curve (docs/research/prague-districts-design.md).

Reuses the data and estimators of tools/praha/districts_extended.py. Writes assets/praha/districts_extended_robust.json.
The specification curve uses 999 permutations and 999 bootstrap draws per specification (the confirmatory tests use
9 999).

Usage:
    uv run --with pandas --with numpy --with openpyxl --with xlrd --with scipy python tools/praha/districts_robust.py
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import districts_alignment as al  # noqa: E402
import districts_extended as x  # noqa: E402

OUT = x.ROOT / "assets" / "praha" / "districts_extended_robust.json"


def frame(drop_interregnum: bool = False, pop_2021: bool = False) -> pd.DataFrame:
    panel = pd.read_csv(x.RAW / "alignment" / "panel.csv")
    y = x.grants(drop_interregnum)
    y = y[y.source == "measures"]
    r16, pop = x.allocation(2016), x.population()
    full = pd.MultiIndex.from_product([sorted(panel.district.unique()), x.YEARS], names=["district", "r"])
    y = y.set_index(["district", "r"]).drop(columns="source").reindex(full).fillna(0.0).reset_index()
    y["total_R"] = y.total / y.district.map(r16)
    p = [pop.loc[d, 2021] if pop_2021 else pop.loc[d, r - 2] for d, r in zip(y.district, y.r)]
    y["total_pc"] = y.total / p
    y["total_log"] = np.log1p(y.total_pc)
    return y


def estimate(y, panel, outcome, rule="A", controls="never", events=x.EVENTS, drop=None, b=999):
    evs = x.stacked(y, panel, outcome, rule=rule, controls=controls, events=events, drop=drop)
    evs = [ev for ev in evs if ev["switch"].sum() and (~ev["switch"]).sum()]
    if not evs:
        return None
    perms = [x.permutations(ev, b) for ev in evs]
    r = x.pooled(evs, perms)
    r["conley_taber_95"] = x.conley_taber(evs, draws=5000)
    r["relative"] = r["estimate"] / np.mean([ev["pre_level_ctrl"] for ev in evs])
    r["switch_in"] = int(sum(ev["switch"].sum() for ev in evs))
    return r


def main() -> None:
    panel = pd.read_csv(x.RAW / "alignment" / "panel.csv")
    pop = x.population()
    small = [d for d in panel.district.unique() if pop.loc[d, 2021] < 1000]
    base = frame()
    noint = frame(drop_interregnum=True)
    out = {"checks": {}}
    chk = out["checks"]
    chk["per_resident"] = estimate(base, panel, "total_pc")
    chk["per_resident_2021_stock"] = estimate(frame(pop_2021=True), panel, "total_pc")
    chk["log1p_per_resident"] = estimate(base, panel, "total_log")
    for rule in ["seat_majority", "largest_list_has_coalition_party", "A_hand_member"]:
        chk[f"rule_{rule}"] = estimate(base, panel, "total_R", rule=rule)
    chk["without_interregnum"] = estimate(noint, panel, "total_R")
    chk["without_adjacent_years_2018_event_only"] = estimate(base, panel, "total_R",
                                                            events={2018: ([2016, 2017], [2020, 2021])})
    chk["always_aligned_as_controls"] = estimate(base, panel, "total_R", controls="both")
    chk["without_praha_1"] = estimate(base, panel, "total_R", drop={"Praha 1"})
    chk["without_under_1000"] = estimate(base, panel, "total_R", drop=set(small))
    chk["event_2018_only"] = estimate(base, panel, "total_R", events={2018: x.EVENTS[2018]})
    chk["event_2023_only"] = estimate(base, panel, "total_R", events={2023: x.EVENTS[2023]})
    # leave one district out
    full = estimate(base, panel, "total_R", b=199)["estimate"]
    lodo = {}
    for d in sorted(panel.district.unique()):
        r = estimate(base, panel, "total_R", drop={d}, b=199)
        if r:
            lodo[d] = r["estimate"] - full
    chk["leave_one_district_out_max_abs_change"] = float(max(abs(v) for v in lodo.values()))
    # leave one party out: drop every district whose mayor belonged to party P on 30 June of any window year
    reg = al.registers()
    coder = al.spells(x.RAW / "alignment" / "coder_A.csv")
    party = {}
    for _, row in panel.iterrows():
        day = f"{row.r}-06-30"
        party[(row.district, row.r)] = al.register_party(al.mayor_on(coder, row.district, day), reg, int(row.code), day)
    lopo = {}
    for p in sorted({v for v in party.values() if v and v != "LOCAL"}):
        drop = {d for (d, r), v in party.items() if v == p and 2016 <= r <= 2023}
        r = estimate(base, panel, "total_R", drop=drop, b=199)
        if r:
            lopo[p] = {"estimate": r["estimate"], "dropped": len(drop)}
    chk["leave_one_party_out"] = lopo
    # specification curve
    specs = []
    frames = {False: base, True: noint}
    for scale, rule, inter, sample in itertools.product(["total_R", "total_pc", "total_log"],
                                                         ["A", "seat_majority", "largest_list_has_coalition_party"],
                                                         [False, True], ["all", "no_praha_1", "no_under_1000"]):
        drop = {"all": None, "no_praha_1": {"Praha 1"}, "no_under_1000": set(small)}[sample]
        r = estimate(frames[inter], panel, scale, rule=rule, drop=drop)
        if r is None:
            continue
        reg_ = x.regression_form(frames[inter], panel, scale, rule=rule, wcr_b=999) if drop is None else None
        specs.append({"scale": scale, "rule": rule, "without_interregnum": inter, "sample": sample,
                      "estimate": r["estimate"], "relative": r["relative"], "p_ri": r["p_ri"],
                      "ct_excludes_zero_above": r["conley_taber_95"][0] > 0,
                      "p_wcr": reg_["p_wcr"] if reg_ else None, "p_cr2": reg_["p_cr2"] if reg_ else None})
    s = pd.DataFrame(specs)
    out["specification_curve"] = {
        "n": int(len(s)), "share_positive": float((s.estimate > 0).mean()),
        "share_p_ri_below_05": float((s.p_ri < 0.05).mean()),
        "share_ct_above_zero": float(s.ct_excludes_zero_above.mean()),
        "share_p_wcr_below_05": float((s.p_wcr.dropna() < 0.05).mean()),
        "share_p_cr2_below_05": float((s.p_cr2.dropna() < 0.05).mean()),
        "relative_range": [float(s.relative.min()), float(s.relative.max())],
        "specs": specs}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: v[kk] for kk in ("estimate", "p_ri", "relative") if kk in v})
                      for k, v in chk.items() if k != "leave_one_party_out"}, ensure_ascii=False, default=float))
    print(json.dumps({k: v for k, v in out["specification_curve"].items() if k != "specs"}))


if __name__ == "__main__":
    main()
