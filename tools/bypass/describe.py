"""After the results, not registered: descriptive counts behind the note on check 1 (all accidents, damage-only
included), which came out of the opposite sign to the injury-accident headline.

Counts only, by year, nothing estimated: damage-only and injury accidents nationally, in Prague and in the rest of the
country; damage-only accidents by type (p6) and by recorded damage (p14); and inside the built-up area of the study's
towns (the definition of `estimate.real_counts`): the treated towns, Prague (a comparison town through BYP-057,
Úvaly) and the other comparison towns, every year, whether or not a town served as a comparison in it. The frozen
code is imported, not changed or run. p6 and p14 are not in the harmonised file, so they are read from the extracted
police files here and joined on the year and p1.

Writes docs/research/bypass-describe.json.

    nice -n 20 uv run --no-project --with pandas --with numpy --with pyarrow --with geopandas --with pyogrio \
        python -I tools/bypass/describe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate as E  # noqa: E402
import harmonise as H  # noqa: E402
import screen as S  # noqa: E402
import towns as T  # noqa: E402

OUT = T.ROOT / "docs/research/bypass-describe.json"
PRAGUE = 554782
YEARS = range(T.FIRST_YEAR, T.LAST_YEAR + 1)
BEFORE, AFTER = range(2016, 2020), range(2023, 2026)
WILDLIFE = 5  # p6: collision with game
BANDS = [(0, 20_000, "up to 20 000"), (20_000, 50_000, "20 000–50 000"), (50_000, 100_000, "50 000–100 000"),
         (100_000, np.inf, "over 100 000")]


def raw_fields() -> pd.DataFrame:
    """p6 and the recorded damage in CZK per accident; the CSV years give p14 in hundreds of CZK, the HTML years
    give p14*100 in CZK."""
    parts = []
    for y in YEARS:
        folder = H.extract(y)
        if y in H.CSV_YEARS:
            for f in sorted(folder.glob("[0-9][0-9].csv")):
                if f.stat().st_size == 0:
                    continue
                d = pd.read_csv(f, sep=";", header=None, names=H.CSV_COLUMNS, dtype=str, encoding="cp1250",
                                keep_default_na=False)
                parts.append(pd.DataFrame({"file_year": y, "p1": d["p1"].str.strip(), "p6": H.number(d["p6"]),
                                           "damage": H.number(d["p14"]) * 100}))
        else:
            d = H.read_html_table(folder / "Inehody.xls")
            parts.append(pd.DataFrame({"file_year": y, "p1": d["p1"].astype("int64").astype(str),
                                       "p6": H.number(d["p6"]), "damage": H.number(d["p14*100"])}))
    return pd.concat(parts, ignore_index=True).drop_duplicates(["file_year", "p1"])


def by_year(df: pd.DataFrame) -> dict[int, int]:
    return {y: int(v) for y, v in df.groupby("year").size().reindex(YEARS, fill_value=0).items()}


def change(series: dict[int, int]) -> float:
    return float(np.mean([series[y] for y in AFTER]) / np.mean([series[y] for y in BEFORE]) - 1)


def bands(df: pd.DataFrame) -> dict[int, dict[str, int]]:
    out = {}
    for y in YEARS:
        d = df[df["year"] == y]["damage"]
        out[y] = {lab: int(((d > lo) & (d <= hi)).sum() if lo else (d <= hi).sum()) for lo, hi, lab in BANDS}
    return out


def towns_table() -> pd.DataFrame:
    b = T.load_list()
    table, _ = S.areas(S.ku_versions(), S.ku_areas(), [f"{y}-01-01" for y in range(T.FIRST_YEAR, T.LAST_YEAR + 2)])
    return E.town_table(T.select(b, S.area_change(table)))


def phase(t, y: int) -> str:
    if y < t.start_year:
        return "pre-construction"
    if y < t.open_year:
        return "construction"
    if y == t.open_year:
        return "opening year"
    return "post years 1–3" if y - t.open_year <= 3 else "post years 4+"


def main() -> None:
    a = pd.read_parquet(E.ACCIDENTS)
    a = a[a["year"].between(T.FIRST_YEAR, T.LAST_YEAR)].merge(raw_fields(), on=["file_year", "p1"], how="left",
                                                               validate="many_to_one")
    assert a["p6"].notna().all()
    a["damage_only"] = a["injury"] == False  # noqa: E712  (a missing severity code is neither)
    a["inj"] = a["injury"] == True  # noqa: E712
    dmg, inj = a[a["damage_only"]], a[a["inj"]]
    pd_, pi = dmg["muni_polygon"] == PRAGUE, inj["muni_polygon"] == PRAGUE

    national = {
        "damage_only": by_year(dmg), "injury": by_year(inj),
        "damage_only_prague": by_year(dmg[pd_]), "injury_prague": by_year(inj[pi]),
        "damage_only_rest": by_year(dmg[~pd_]), "injury_rest": by_year(inj[~pi]),
        "damage_only_wildlife": by_year(dmg[dmg["p6"] == WILDLIFE]),
        "damage_only_wildlife_outside_built_up": by_year(dmg[(dmg["p6"] == WILDLIFE) & (dmg["built_up"] == False)]),  # noqa: E712
        "damage_only_not_wildlife": by_year(dmg[dmg["p6"] != WILDLIFE]),
    }
    damage = {"prague": bands(dmg[pd_]), "rest": bands(dmg[~pd_]),
              "missing": int(dmg["damage"].isna().sum())}

    t = towns_table()
    role = t.drop_duplicates("town").set_index("town")["role"]
    inside = a[a["built_up"].fillna(False) & a["muni_polygon"].isin(set(t["town"]))].copy()
    inside["town"] = inside["muni_polygon"].astype(int)
    inside["role"] = inside["town"].map(role)
    groups = {"treated": inside["role"] == "treated", "prague": inside["town"] == PRAGUE,
              "other_comparison": (inside["role"] == "comparison") & (inside["town"] != PRAGUE)}
    sample = {}
    for g, m in groups.items():
        for kind, k in (("damage_only", "damage_only"), ("injury", "inj")):
            sample[f"{g}_{kind}"] = by_year(inside[m & inside[k]])
    comp = inside["role"] == "comparison"
    serving = inside["year"] <= int(t.loc[t["town"] == PRAGUE, "last_year"].iloc[0])
    prague_share = {kind: float((inside[groups["prague"] & inside[k] & serving]).shape[0]
                                / inside[comp & inside[k] & serving].shape[0])
                    for kind, k in (("damage_only", "damage_only"), ("injury", "inj"))}

    tr = t[t["role"] == "treated"].copy()
    roads = {r.town: {s.strip() for s in str(r.road).split(",")} for r in tr.itertuples()}
    ti = inside[groups["treated"]].copy()
    ti["old_road"] = [r in roads.get(x, set()) for r, x in zip(ti["road"], ti["town"])]
    rows = []
    for r in tr.itertuples():
        for y in YEARS:
            d = ti[(ti["town"] == r.town) & (ti["year"] == y)]
            rows.append({"phase": phase(r, y), "injury": int(d["inj"].sum()), "damage_only": int(d["damage_only"].sum()),
                         "damage_only_old_road": int((d["damage_only"] & d["old_road"]).sum())})
    ph = pd.DataFrame(rows).groupby("phase")
    phases = {p: {"town_years": int(len(g)), **{c: float(g[c].mean()) for c in ("injury", "damage_only",
                                                                                 "damage_only_old_road")}}
              for p, g in ph}

    out = {
        "note": "after the results, not registered: counts by year, nothing estimated (tools/bypass/describe.py)",
        "years": [T.FIRST_YEAR, T.LAST_YEAR], "prague_code": PRAGUE,
        "prague_row": str(t.loc[t["town"] == PRAGUE, "row"].iloc[0]),
        "prague_last_comparison_year": int(t.loc[t["town"] == PRAGUE, "last_year"].iloc[0]),
        "national": national,
        "change_2016_19_to_2023_25": {
            **{f"national_{k}": change(v) for k, v in national.items()},
            **{f"inside_{k}": change(v) for k, v in sample.items()},
        },
        "damage_bands_czk_nominal": damage,
        "inside_built_up": sample,
        "prague_share_of_comparison_inside_2016_to_last_year": prague_share,
        "treated_by_phase_per_town_year": phases,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out["change_2016_19_to_2023_25"], indent=1))
    print(json.dumps(prague_share), json.dumps(phases, indent=1))


if __name__ == "__main__":
    main()
