"""Part 3 extended, §8: robustness and the specification curve (docs/research/prague-districts-design.md).

Reuses the data and estimators of tools/praha/districts_extended.py. Writes assets/praha/districts_extended_robust.json.
The specification curve uses 999 permutations and 999 wild-bootstrap draws per specification (the confirmatory tests
use 9 999). Each check draws from its own fixed random stream.

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


def frame(drop_interregnum: bool = False, pop_2021: bool = False, variant: str = "primary",
          interregnum: tuple[str, str] = x.INTERREGNUM) -> pd.DataFrame:
    panel = pd.read_csv(x.RAW / "alignment" / "panel.csv")
    y = x.grants(drop_interregnum, variant=variant, interregnum=interregnum)
    y = y[y.source == "measures"]
    r16, pop = x.allocation(2016), x.population()
    full = pd.MultiIndex.from_product([sorted(panel.district.unique()), x.YEARS], names=["district", "r"])
    y = y.set_index(["district", "r"]).drop(columns="source").reindex(full).fillna(0.0).reset_index()
    y["total_R"] = y.total / y.district.map(r16)
    p = [pop.loc[d, 2021] if pop_2021 else pop.loc[d, r - 2] for d, r in zip(y.district, y.r)]
    y["total_pc"] = y.total / p
    y["total_log"] = np.log1p(y.total_pc.clip(lower=0))
    return y


def estimate(y, panel, outcome, rule="A", controls="never", events=x.EVENTS, drop=None, b=999, label="check"):
    x.reseed(label)
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


def membership_panel(panel: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Alignment from the coders' own membership field: a mayor who is a member of a coalition party is aligned; a
    recorded non-member ('bez PP') is not, even if a coalition party nominated them; where neither coder recorded a
    membership, the registered rule stands. Where the coders give different parties, the registered rule stands."""
    coders = {c: al.spells(x.RAW / "alignment" / f"coder_{c}.csv") for c in "AB"}
    p2, used = panel.copy(), 0
    for i, row in p2.iterrows():
        day = f"{row.r}-06-30"
        mem = [m.member for m in (al.mayor_on(s, row.district, day) for s in coders.values())
               if m is not None and isinstance(m.member, str) and m.member]
        mem = sorted(set(mem))
        if len(mem) == 1:
            used += 1
            p2.at[i, "A"] = 0 if mem[0] == "BEZPP" else int(mem[0] in al.coalition(day))
    return p2, used


def main() -> None:
    panel = pd.read_csv(x.RAW / "alignment" / "panel.csv")
    pop = x.population()
    small = [d for d in panel.district.unique() if pop.loc[d, 2021] < 1000]
    base = frame()
    noint = frame(drop_interregnum=True)
    out = {"checks": {}}
    chk = out["checks"]
    chk["per_resident"] = estimate(base, panel, "total_pc", label="pc")
    chk["per_resident_2021_stock"] = estimate(frame(pop_2021=True), panel, "total_pc", label="pc21")
    chk["log1p_per_resident"] = estimate(base, panel, "total_log", label="log")
    for rule in ["seat_majority", "largest_list_has_coalition_party"]:
        chk[f"rule_{rule}"] = estimate(base, panel, "total_R", rule=rule, label=rule)
    mp, used = membership_panel(panel)
    chk["rule_coders_membership"] = estimate(base, mp, "total_R", label="membership") | {
        "district_years_with_membership": used,
        "district_years_changed": int((mp.A != panel.A).sum())}
    p10 = panel.copy()
    p10.loc[(p10.district == "Praha 10") & (p10.r == 2022), "A"] = 1  # acting head Komrsková (Piráti)
    chk["praha_10_2022_acting_head"] = estimate(base, p10, "total_R", label="p10")
    chk["without_interregnum"] = estimate(noint, panel, "total_R", label="noint")
    chk["without_interregnum_from_22_oct_2015"] = estimate(
        frame(drop_interregnum=True, interregnum=("2015-10-22", "2016-04-27")), panel, "total_R", label="noint22")
    chk["signflip_district_to_city"] = estimate(frame(variant="signflip"), panel, "total_R", label="signflip")
    chk["without_uz_8_98_99"] = estimate(frame(variant="discretionary"), panel, "total_R", label="discretionary")
    chk["without_adjacent_years_2018_event_only"] = estimate(base, panel, "total_R",
                                                            events={2018: ([2016, 2017], [2020, 2021])}, label="adj")
    chk["always_aligned_as_controls"] = estimate(base, panel, "total_R", controls="both", label="always")
    chk["without_under_1000"] = estimate(base, panel, "total_R", drop=set(small), label="small")
    chk["event_2018_only"] = estimate(base, panel, "total_R", events={2018: x.EVENTS[2018]}, label="e18")
    chk["event_2023_only"] = estimate(base, panel, "total_R", events={2023: x.EVENTS[2023]}, label="e23")
    # leave one district out
    full = estimate(base, panel, "total_R", b=199, label="lodo")
    lodo = {}
    for d in sorted(panel.district.unique()):
        r = estimate(base, panel, "total_R", drop={d}, b=199, label="lodo")
        if r:
            lodo[d] = {"estimate": r["estimate"], "relative": r["relative"],
                       "change_points": 100 * (r["relative"] - full["relative"])}
    top = sorted(lodo.items(), key=lambda kv: -abs(kv[1]["change_points"]))
    chk["leave_one_district_out"] = {"largest": [{"district": k} | v for k, v in top[:3]],
                                     "max_abs_change_points_excluding_largest": abs(top[1][1]["change_points"])}
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
        r = estimate(base, panel, "total_R", drop=drop, b=199, label="lopo")
        if r:
            lopo[p] = {"estimate": r["estimate"], "relative": r["relative"], "dropped": len(drop)}
    chk["leave_one_party_out"] = lopo
    # specification curve (Praha 1 is in neither stack, so 'without Praha 1' would duplicate 'all' and is not used)
    specs = []
    frames = {False: base, True: noint}
    for scale, rule, inter, sample in itertools.product(["total_R", "total_pc", "total_log"],
                                                         ["A", "seat_majority", "largest_list_has_coalition_party"],
                                                         [False, True], ["all", "no_under_1000"]):
        drop = {"all": None, "no_under_1000": set(small)}[sample]
        r = estimate(frames[inter], panel, scale, rule=rule, drop=drop, label="spec")
        if r is None:
            continue
        x.reseed("spec_wcr")
        reg_ = x.regression_form(frames[inter], panel, scale, rule=rule, wcr_b=999, drop=drop)
        specs.append({"scale": scale, "rule": rule, "without_interregnum": inter, "sample": sample,
                      "estimate": r["estimate"], "relative": r["relative"], "p_ri": r["p_ri"],
                      "ct_excludes_zero_above": r["conley_taber_95"][0] > 0,
                      "p_wcr": reg_["p_wcr"], "p_cr2": reg_["p_cr2"]})
    s = pd.DataFrame(specs)
    out["specification_curve"] = {
        "n": int(len(s)), "share_positive": float((s.estimate > 0).mean()), "positive": int((s.estimate > 0).sum()),
        "share_p_ri_below_05": float((s.p_ri < 0.05).mean()),
        "share_ct_above_zero": float(s.ct_excludes_zero_above.mean()),
        "share_p_wcr_below_05": float((s.p_wcr < 0.05).mean()),
        "share_p_cr2_below_05": float((s.p_cr2 < 0.05).mean()),
        "relative_range": [float(s.relative.min()), float(s.relative.max())],
        "relative_range_by_rule": {k: [float(v.relative.min()), float(v.relative.max())] for k, v in s.groupby("rule")},
        "specs": specs}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: v[kk] for kk in ("relative", "p_ri") if kk in v})
                      for k, v in chk.items() if k not in ("leave_one_party_out", "leave_one_district_out")},
                     ensure_ascii=False, default=float))
    print(json.dumps(chk["leave_one_district_out"], ensure_ascii=False, default=float))
    print(json.dumps({k: v for k, v in out["specification_curve"].items() if k != "specs"}))


if __name__ == "__main__":
    main()
