"""Screening of the bypass accidents study (design §3), before any count is compared. Accident fields are summarised
nationally per year only: rows per year and file format, the shares with coordinates, joined to a municipality, with
p5a and with a severity code, and the code lists. The town tables use construction facts only (towns.py), and the
RÚIAN part sums each municipality's area from its cadastral units (KÚ) at every 1 January. No accident is
counted for a town, a municipality, a road or a bypass.

Writes docs/research/bypass-screening.json.

    nice -n 20 uv run --no-project --with pandas --with numpy --with pyarrow --with geopandas --with pyogrio \
        python -I tools/bypass/screen.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import towns as T  # noqa: E402

ROOT = T.ROOT
DATA = ROOT / "tools/data/bypass"
ACCIDENTS = DATA / "accidents.parquet"
HARMONISE_LOG = DATA / "harmonise-log.json"
RUIAN = DATA / "ruian"
RUIAN_FILES = ("20260930_ST_UZSZ.xml", "20260930_ST_UZHZ.xml")
KATUZE = RUIAN / "1/KATUZE_P.shp"
OUT = ROOT / "docs/research/bypass-screening.json"
CODE_FIELDS = ("p5a", "p9", "p35", "road_class", "p28", "killed", "serious", "slight")
MISSING_JUMP = 0.02


def share(s: pd.Series) -> float:
    return round(float(s.mean()), 4)


def national(df: pd.DataFrame, log: dict) -> dict:
    """§3.1, per year for the whole country; nothing below the national level."""
    out, prev = {}, None
    for y, g in df.groupby("file_year"):
        missing = 1 - g["x"].notna().mean()
        rec = {"format": g["format"].iat[0], "rows_in_files": log[str(y)]["rows_in_files"],
               "exact_duplicates_dropped": log[str(y)]["exact_duplicates_dropped"], "records": int(len(g)),
               "date_outside_file_year": int((g["year"] != y).sum()),
               "with_coordinates": share(g["x"].notna()),
               "coordinates_numeric_out_of_range": share(g["xy_status"] == "out_of_range"),
               "regions_present": sorted(g["region"].unique().tolist()),
               "months_present": sorted(int(m) for m in g["date"].dt.month.dropna().unique()),
               "joined_to_municipality_by_polygon": share(g["muni_polygon"].notna()),
               "without_coordinates_named_municipality": share(g["x"].isna() & g["muni_record_valid"].notna()),
               "without_coordinates_dropped": share(g["muni_source"] == "none"),
               "with_p5a": share(g["built_up"].notna()), "with_severity_code": share(g["severity_coded"]),
               "injury_flag_agrees_with_p9": share(g["injury"] == (g["p9"] == 1)),
               "with_junction_code": share(g["junction"].notna()), "with_road_number": share(g["road"].notna()),
               "codes": {c: sorted(int(v) for v in g[c].dropna().unique()) for c in CODE_FIELDS}}
        if g["format"].iat[0] == "csv":
            both = g["muni_polygon"].notna() & g["muni_record_valid"].notna()
            rec["record_code_agrees_with_polygon"] = share(g.loc[both, "muni_polygon"] == g.loc[both, "muni_record_valid"])
        rec["missing_coordinates_flag"] = bool(prev is not None and missing - prev > MISSING_JUMP)
        prev = missing
        out[int(y)] = rec
    return out


def ku_versions() -> list[tuple]:
    """(KÚ, municipality, from, to) for every version of every cadastral unit, current and historical."""
    ku = []
    ns = {"kui": "urn:cz:isvs:ruian:schemas:KatUzIntTypy:v1", "obi": "urn:cz:isvs:ruian:schemas:ObecIntTypy:v1",
          "vf": "urn:cz:isvs:ruian:schemas:VymennyFormatTypy:v1"}
    for name in RUIAN_FILES:
        for _, el in ET.iterparse(RUIAN / name):
            space, _, tag = el.tag[1:].partition("}")
            if space != ns["vf"] or not el.attrib:  # the container of KÚs has the same name as a KÚ, but no gml:id
                continue
            if tag == "KatastralniUzemi":
                obec = el.findtext("kui:Obec/obi:Kod", None, ns)
                ku.append((int(el.findtext("kui:Kod", namespaces=ns)), int(obec) if obec else None,
                           el.findtext("kui:PlatiOd", None, ns)[:10],
                           (el.findtext("kui:PlatiDo", None, ns) or "9999-12-31")[:10]))
            el.clear()
    return ku


def ku_areas() -> dict[int, float]:
    import geopandas as gpd
    k = gpd.read_file(KATUZE)
    return dict(zip(k["KOD"].astype(int), k.geometry.area))


def areas(ku: list[tuple], ku_area: dict[int, float], dates: list[str]) -> tuple[pd.DataFrame, list[int]]:
    """Municipality area (m²) at each date: the current polygon area of every KÚ that belonged to it that day.

    This sees whole KÚs moving between municipalities and municipalities created or merged; it cannot see parcels
    moved across a KÚ boundary, because RÚIAN keeps no earlier KÚ geometry in these files. The historical file keeps
    few superseded KÚ versions (a KÚ's current version often starts after 2016 with no earlier one listed), so a KÚ
    before its first known version is taken to belong to that version's municipality. KÚs abolished before today have
    no polygon and are returned so that the municipalities they touched can be listed."""
    out, by_ku = {}, defaultdict(list)
    for k, o, a, b in sorted(ku, key=lambda v: v[2]):
        by_ku[k].append((o, a, b))
    lost = sorted(k for k in by_ku if k not in ku_area)
    for d in dates:
        tot = defaultdict(float)
        for k, v in by_ku.items():
            o = next((o for o, a, b in v if a <= d < b), v[0][0] if d < v[0][1] else None)
            if o is not None:
                tot[o] += ku_area.get(k, 0.0)
        out[d] = tot
    return pd.DataFrame(out).fillna(0.0), lost


def area_change(table: pd.DataFrame) -> dict[int, float]:
    """Largest relative departure from the area on the first day of the data; a municipality missing then is 100 %."""
    base = table.iloc[:, 0]
    dev = table.sub(base, axis=0).abs().max(axis=1) / base.where(base > 0)
    return {int(k): (1.0 if pd.isna(v) else round(float(v), 4)) for k, v in dev.items()}


def town_tables(sel: T.Selection) -> dict:
    t = sel.towns
    tr, co = t[t["role"] == "treated"], t[t["role"] == "comparison"]
    cols = ["code", "town_names", "row", "cluster", "road", "road_class", "start_year", "open_year"]
    by = lambda d, k: {str(a): int(b) for a, b in d.groupby(k).size().items()}  # noqa: E731
    return {
        "treated_towns": int(len(tr)), "treated_bypasses": int(tr["cluster"].nunique()),
        "comparison_towns": int(len(co)), "comparison_bypasses": int(co["cluster"].nunique()),
        "treated_by_open_year": by(tr, "open_year"), "treated_by_start_year": by(tr, "start_year"),
        "treated_by_cohort": by(tr, "cohort"), "treated_by_class": by(tr, "road_class"),
        "comparison_by_status_stage": {f"{a} / {b}": int(n) for (a, b), n in
                                       co.groupby(["status", "stage"], dropna=False).size().items()},
        "comparison_by_class": by(co, "road_class"),
        "comparison_by_last_year": by(co, "last_year"),
        "treated": tr[cols + ["cohort", "staged", "group_ids", "date_precision"]].to_dict("records"),
        "comparison": co[cols + ["status", "stage", "last_year"]].to_dict("records"),
        "comparisons_serving_per_year": T.comparisons_per_year(t),
        "years_below_15_comparisons": [y for y, n in T.comparisons_per_year(t).items() if n < 15],
        "rows_excluded": sel.rows_excluded, "towns_excluded": sel.excluded,
        "minimum_30_met": bool(len(tr) >= 30),
    }


def main() -> None:
    b = T.load_list()
    digest = hashlib.sha256(T.LIST.read_bytes()).hexdigest()
    assert digest == T.LIST_SHA256, "not the frozen list"
    ku = ku_versions()
    dates = [f"{y}-01-01" for y in range(T.FIRST_YEAR, T.LAST_YEAR + 2)]
    table, lost = areas(ku, ku_areas(), dates)
    lost_munis = sorted({o for k, o, a, b in ku if k in set(lost) and o is not None})
    change = area_change(table)
    sel = T.select(b, change)
    candidates = {c for cs in b["codes"] for c in cs}
    out = {
        "list_sha256": digest, "stage": "A",
        "police_files": {"first_year_in_record_form": T.FIRST_YEAR, "last_year": T.LAST_YEAR,
                         "years_2014_2015": "no record-level file on the archive page (yearbooks and PDF summaries "
                                            "only); see docs/research/bypass-files.sha256",
                         "stage_a_construction_start_from": T.FIRST_YEAR + T.PRE_YEARS},
        "accidents_national": national(pd.read_parquet(ACCIDENTS), json.loads(HARMONISE_LOG.read_text())),
        "towns": town_tables(sel),
        "ruian": {"files": list(RUIAN_FILES), "ku_versions": len(ku), "dates": dates,
                  "method": "area = current polygon area of the KÚs belonging to the municipality on each 1 January; "
                            "whole-KÚ transfers, mergers and splits are seen, parcel moves across KÚ boundaries are not",
                  "abolished_kus_without_polygon": lost,
                  "listed_municipalities_touching_abolished_kus": sorted(c for c in candidates if c in lost_munis),
                  "municipalities_now": int((table.iloc[:, -1] > 0).sum()),
                  "municipalities_changed_over_2pct_nationally": int(sum(v > T.AREA_CHANGE for v in change.values())),
                  "listed_municipalities_changed_over_2pct": {str(c): change[c] for c in sorted(candidates)
                                                              if change.get(c, 0) > T.AREA_CHANGE},
                  "listed_municipalities_not_found": sorted(int(c) for c in candidates if c not in change)},
        "check_7_comparison_planned_only": town_tables(T.select(b, change, planned_only=True))["comparison_towns"],
        "check_12_class_III_added": {k: town_tables(T.select(b, change, classes=("I", "II", "III")))[k]
                                     for k in ("treated_towns", "comparison_towns")},
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    tt = out["towns"]
    print("treated", tt["treated_towns"], "bypasses", tt["treated_bypasses"], "comparison", tt["comparison_towns"],
          "thin years", tt["years_below_15_comparisons"])


if __name__ == "__main__":
    main()
