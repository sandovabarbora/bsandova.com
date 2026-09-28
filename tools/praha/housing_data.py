"""Part 4 extended, the design frames: covariates and sample definitions for every registered question
(docs/research/prague-housing-design.md, §3 and §5a), built before any outcome is summarised.

No outcome is summarised here. Outcome columns that a later script needs are carried through untouched
(Czech completions, RÚIAN completion dates), and the only statistics written are counts of units and reasons for
dropping them.

  - H1: European metropolitan regions (NUTS 2021 metro typology). Covariates dated 2011 or earlier. The numerator
    (dwellings built 2011+) is checked for presence only; its values are not read into the frame.
  - H2/H3: monthly permitted and completed dwellings by kraj, with the registered rules for the missing 2006-11
    cumulation and for negative monthly differences.
  - H5: Prague's RÚIAN building points, re-queried with nespravny, platiod and pocetpodlazi and filtered to the 57
    city districts; 1 km cells with their covariates (distances, GEOSTAT 2011 population, district).

Sources: see housing_fetch.py; in addition, RÚIAN (ČÚZK ArcGIS REST) layers 2 (building points), 8 (city
districts), 10 (the 22 administrative districts), 12 (municipality), queried here and saved to praha4x/prague/.

Usage (from a worktree, point DATA at the main checkout's gitignored tools/data):
    DATA=/path/to/bsandova.com/tools/data uv run --with pandas --with numpy --with shapely --with pyproj \
        --with pyarrow --with openpyxl python tools/praha/housing_data.py
"""

import json
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import STRtree, wkb
from shapely.geometry import Point, shape

sys.path.insert(0, str(Path(__file__).parent))
from rings_data import esri_polygon, ruian  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("DATA", ROOT / "tools" / "data"))
RAW = DATA / "praha4x"
REPORT = RAW / "design_report.json"
PRAGUE_OBEC = 554782
MUSTEK = (14.4232, 50.0842)  # as in Part 2 [lon, lat]
LINE_A_2015 = {"Bořislavka", "Nádraží Veleslavín", "Petřiny", "Nemocnice Motol"}
UNK_MAX = 0.10
RECONSTRUCTION = {"CZ", "ES", "HR"}  # census concept "construction or reconstruction" (referee data audit)
WARSAW = {"PL911": ["071412831000", "071412865000"],  # powiat warszawski (to 2001) and the city (2002-)
          "PL912": ["071412908000", "071412912000", "071412917000", "071412934000"],
          "PL913": ["071413005000", "071413014000", "071413018000", "071413021000", "071413032000"]}


def inverse(d: dict) -> dict:
    return {i: c for c, i in d.items()}


def jsonstat(name: str, **fixed) -> pd.DataFrame:
    """A Eurostat JSON-stat file as long rows (geo, time, value), with the other dimensions fixed."""
    d = json.loads((RAW / "eurostat" / f"{name}.json").read_text())
    ids, size = d["id"], d["size"]
    inv = {k: inverse(d["dimension"][k]["category"]["index"]) for k in ids}
    strides = np.cumprod([1] + size[::-1][:-1])[::-1]
    keys = np.array([int(k) for k in d["value"]])
    vals = np.array(list(d["value"].values()), dtype=float)
    cols = {}
    for dim, s, n in zip(ids, strides, size):
        cols[dim] = (keys // s) % n
    keep = np.ones(len(keys), bool)
    for f, val in fixed.items():
        want = d["dimension"][f]["category"]["index"][val]
        keep &= cols[f] == want
    return pd.DataFrame({"geo": [inv["geo"][i] for i in cols["geo"][keep]],
                         "time": [inv["time"][i] for i in cols["time"][keep]], "value": vals[keep]})


def back_codes() -> dict:
    """NUTS 2021 code -> earlier codes of the same region under pure recodes (no boundary change), newest first."""
    b = pd.read_excel(RAW / "eurostat" / "NUTS2021.xlsx", "Changes NUTS-3")
    a = pd.read_excel(RAW / "eurostat" / "NUTS2013-NUTS2016.xlsx", "Correspondence NUTS-3")
    pure = lambda c: c.astype(str).str.contains("recode") & ~c.astype(str).str.contains("boundary")  # noqa: E731
    to16 = dict(zip(b[pure(b.Change)]["Code 2021"], b[pure(b.Change)]["Code 2016"]))
    to13 = dict(zip(a[pure(a.Change)]["Code 2016"], a[pure(a.Change)]["Code 2013"]))

    def chain(g: str) -> list:
        out = [g]
        g16 = to16.get(g, g)
        if g16 not in out:
            out.append(g16)
        if to13.get(g16) and to13[g16] not in out:
            out.append(to13[g16])
        return out
    return chain


def lookup(series: pd.Series, chain, g: str) -> float:
    for c in chain(g):
        if c in series.index and pd.notna(series[c]):
            return float(series[c])
    return np.nan


def metro_frame(report: dict) -> pd.DataFrame:
    chain = back_codes()
    t = pd.read_excel(RAW / "eurostat" / "NUTS2021.xlsx", "Metropolitan")
    t.columns = ["nuts3", "metro_yn", "metro", "label"]
    t = t[t.metro_yn == "Y"].copy()
    t["country"] = t.nuts3.str[:2]
    members = t.groupby("metro").nuts3.apply(list)
    m = pd.DataFrame({"members": members, "label": t.groupby("metro").label.first(),
                      "country": t.groupby("metro").country.first()})
    m["capital"] = m.index.str.endswith("MC")
    steps = {"metro regions in the NUTS 2021 typology": len(m)}

    # census 2021: presence of the numerator and the unknown-period share (TOTAL and UNK only)
    total, unk = (jsonstat("cens_21dwop_r3", housing="DW", y_const=c).set_index("geo").value
                  for c in ["TOTAL", "UNK"])
    has_num = set.intersection(*(set(jsonstat("cens_21dwop_r3", housing="DW", y_const=c).geo)
                                 for c in ["Y2011-2015", "Y_GE2016"]))  # presence only; values discarded
    ok = m.members.apply(lambda ms: all(g in total.index and g in has_num for g in ms))
    report["drop_census_missing"] = sorted(m.index[~ok])
    m = m[ok]
    steps["with census 2021 total and period of construction"] = len(m)
    m["unk_share"] = m.members.apply(lambda ms: sum(unk.get(g, 0) for g in ms) / sum(total[g] for g in ms))
    report["drop_unknown_period"] = sorted(m.index[m.unk_share > UNK_MAX])
    m = m[m.unk_share <= UNK_MAX]
    steps[f"unknown period of construction <= {UNK_MAX:.0%}"] = len(m)

    # population 1 Jan 2001 and 2011 (Eurostat; Warsaw rebuilt from BDL year-end 2000 and 2010)
    pop = jsonstat("demo_r_pjanaggr3", sex="T", age="TOTAL", unit="NR").pivot(
        index="geo", columns="time", values="value")
    bdl = {x["id"]: {int(v["year"]): v["val"] for v in x["values"]}
           for x in json.loads((RAW / "bdl" / "72305_L5.json").read_text())["results"]}
    for nuts, units in WARSAW.items():
        for year in (2001, 2011):
            vals = [bdl[u].get(year - 1) for u in units if bdl[u].get(year - 1) is not None]
            pop.loc[nuts, str(year)] = sum(vals)
    report["warsaw_population_rebuilt_from_bdl"] = {n: {y: float(pop.loc[n, str(y)]) for y in (2001, 2011)}
                                                   for n in WARSAW}
    # registered rule: annualised log growth from the first year t0 >= 2001 in which every member has a value,
    # to 2011, provided 2011 - t0 >= 4
    def growth(ms: list) -> tuple:
        for t0 in range(2001, 2008):
            v0 = [lookup(pop[str(t0)], chain, g) for g in ms]
            v1 = [lookup(pop["2011"], chain, g) for g in ms]
            if not any(np.isnan(v0 + v1)):
                return t0, sum(v1), (np.log(sum(v1)) - np.log(sum(v0))) / (2011 - t0)
        return None, np.nan, np.nan

    m[["pop_t0", "pop2011", "pop_growth"]] = m.members.apply(lambda ms: pd.Series(growth(ms)))
    report["drop_population"] = sorted(m.index[m.pop_growth.isna()])
    report["population_t0_after_2001"] = {k: int(v) for k, v in m.pop_t0.dropna().items() if v > 2001}
    m = m[m.pop_growth.notna()]
    steps["population 2011 and a growth window of at least 4 years from 2001-2007"] = len(m)

    # GDP 2011 in PPS: RO from 2012 (pre-registered); metros with any other missing member dropped
    gdp = jsonstat("nama_10r_3gdp", unit="MIO_PPS_EU27_2020").pivot(index="geo", columns="time",
                                                                         values="value")

    def gdp_of(ms: list) -> float:
        out = 0.0
        for g in ms:
            year = "2012" if g.startswith("RO") else "2011"
            v = lookup(gdp[year], chain, g)
            if pd.isna(v):
                return np.nan
            out += v
        return out

    m["gdp_pps_mio"] = m.members.apply(gdp_of)
    report["drop_gdp"] = sorted(m.index[m.gdp_pps_mio.isna()])
    report["gdp_ro_from_2012"] = sorted(m.index[m.country == "RO"])
    m_gdp = m[m.gdp_pps_mio.notna()]
    steps["GDP 2011 in PPS for every member (primary sample)"] = len(m_gdp)

    # dwellings 2011 (census 2011, same NUTS 3 code; Warsaw from BDL stock at end-2010)
    d11 = jsonstat("cens_11dwob_r3", housing="DW", building="TOTAL").set_index("geo").value
    stock = {x["id"]: {int(v["year"]): v["val"] for v in x["values"]}
             for x in json.loads((RAW / "bdl" / "60811_L5.json").read_text())["results"]}
    for nuts, units in WARSAW.items():
        d11[nuts] = sum(stock[u][2010] for u in units if 2010 in stock[u])
    m["dw2011"] = m.members.apply(lambda ms: np.sum([lookup(d11, chain, g) for g in ms]))
    report["drop_dwellings_2011"] = sorted(m.index[m.dw2011.isna()])
    m["in_primary"] = m.gdp_pps_mio.notna() & m.dw2011.notna()
    steps["dwellings 2011 for every member (primary sample, final n)"] = int(m.in_primary.sum())
    m["reconstruction_concept"] = m.country.isin(RECONSTRUCTION)
    report["h1_steps"] = steps
    report["h1_n_primary"] = int(m.in_primary.sum())
    report["h1_n_without_gdp"] = int(m.dw2011.notna().sum())
    report["h1_capital_metros_primary"] = int((m.in_primary & m.capital).sum())
    report["h1_prague_vienna_warsaw"] = {c: {"metro": k, "members": m.loc[k].members if k in m.index else None,
                                             "in_primary": bool(m.loc[k].in_primary) if k in m.index else False}
                                         for c, k in [("prague", "CZ001MC"), ("vienna", "AT001MC"),
                                                      ("warsaw", "PL001MC")]}
    return m.drop(columns=["label"]).assign(members=lambda t: t.members.apply(",".join))


def czech_monthly(report: dict) -> pd.DataFrame:
    """Monthly flows from ČSÚ year-to-date cumulations (STA09B), 2007-01 to 2025-12, by kraj."""
    t = pd.read_csv(RAW / "csu" / "STA09B.csv", dtype=str)
    codes = {"3074": "permitted_multi", "3114": "completed_multi", "3072": "permitted_family",
             "3113": "completed_family"}
    t = t[t.IndicatorType.isin(codes)].copy()
    t["series"] = t.IndicatorType.map(codes)
    t["year"] = t.CASKMR.str[:4].astype(int)
    t["month"] = t.CASKMR.str[5:7].astype(int)
    t["cum"] = t.Hodnota.astype(float)
    t = t[t.year >= 2007]  # 2006-11 is missing in every series; the windows start in 2007 (registered)
    out, negatives = [], 0
    for (kraj, s, y), g in t.groupby(["Uz2", "series", "year"]):
        g = g.set_index("month").cum.reindex(range(1, 13))
        if g.isna().any():
            raise ValueError(f"gap in {kraj} {s} {y}")
        flow = g.diff().fillna(g.iloc[0]).to_numpy().copy()
        # registered rule: a negative month is pooled with the preceding month(s) until the pool is non-negative,
        # and the pool is shared equally (the annual total is unchanged)
        i = 11
        while i >= 1:
            if flow[i] < 0:
                negatives += 1
                j = i
                while j > 0 and flow[j:i + 1].sum() < 0:
                    j -= 1
                flow[j:i + 1] = flow[j:i + 1].sum() / (i - j + 1)
                i = j
            i -= 1
        out += [{"kraj": kraj, "series": s, "date": pd.Timestamp(y, mth, 1), "value": v}
                for mth, v in zip(range(1, 13), flow)]
    report["czech_negative_months_pooled"] = negatives
    m = pd.DataFrame(out).pivot_table(index=["kraj", "date"], columns="series", values="value").reset_index()
    report["czech_monthly_span"] = [str(m.date.min().date()), str(m.date.max().date())]
    report["czech_kraje"] = int(m.kraj.nunique())
    return m


def prague_layers(report: dict) -> tuple:
    d = RAW / "prague"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "buildings.parquet").exists():
        districts = ruian(8, f"obec={PRAGUE_OBEC}", "kod,nazev")
        codes = sorted(f["attributes"]["kod"] for f in districts)
        pd.DataFrame([{**f["attributes"], "geom_wkb": esri_polygon(f["geometry"]).wkb} for f in districts]) \
            .to_parquet(d / "city_districts.parquet")
        admin = ruian(10, "1=1", "kod,nazev")
        pd.DataFrame([{**f["attributes"], "geom_wkb": esri_polygon(f["geometry"]).wkb} for f in admin]) \
            .to_parquet(d / "admin_districts.parquet")
        city = esri_polygon(ruian(12, f"kod={PRAGUE_OBEC}", "kod")[0]["geometry"])
        pd.DataFrame([{"kod": PRAGUE_OBEC, "geom_wkb": city.wkb}]).to_parquet(d / "prague.parquet")
        fields = "kod,pocetbytu,dokonceni,druhkonstrukcekod,zpusobvyuzitikod,momc,nespravny,platiod,pocetpodlazi"
        rows = []
        for i in range(0, len(codes), 20):
            where = f"pocetbytu>0 AND momc IN ({','.join(map(str, codes[i:i + 20]))})"
            rows += [{**f["attributes"], "x": f["geometry"]["x"], "y": f["geometry"]["y"]}
                     for f in ruian(2, where, fields) if f.get("geometry")]
        pd.DataFrame(rows).to_parquet(d / "buildings.parquet")
    b = pd.read_parquet(d / "buildings.parquet")
    districts = pd.read_parquet(d / "city_districts.parquet")
    admin = pd.read_parquet(d / "admin_districts.parquet")
    city = wkb.loads(pd.read_parquet(d / "prague.parquet").geom_wkb[0])
    done = pd.to_datetime(b.dokonceni, unit="ms", errors="coerce")
    report["ruian_prague"] = {
        "city_districts": int(len(districts)), "admin_districts": int(len(admin)),
        "buildings_with_flats": int(len(b)), "flats": int(b.pocetbytu.sum()),
        "flats_missing_dokonceni_share": round(float((b.pocetbytu * done.isna()).sum() / b.pocetbytu.sum()), 4),
        "buildings_flagged_nespravny": int(b.nespravny.notna().sum() - (b.nespravny.astype(str) == "").sum()),
        "pocetpodlazi_missing_share": round(float(b.pocetpodlazi.isna().mean()), 4),
        "platiod_range": [str(pd.to_datetime(b.platiod, unit="ms").min().date()),
                          str(pd.to_datetime(b.platiod, unit="ms").max().date())],
    }
    return b, districts, admin, city


def prague_cells(report: dict, districts: pd.DataFrame, admin: pd.DataFrame, city) -> pd.DataFrame:
    raw = json.loads((DATA / "praha2x" / "grid_obyvatelstvo_sldb2021_20210326.geojson").read_text())
    cells = []
    for f in raw["features"]:
        g = shape(f["geometry"])
        if g.intersects(city):
            cells.append({"cell": f["properties"]["grd_inspir"], "geom": g,
                          "area_km2": g.intersection(city).area / 1e6})
    c = pd.DataFrame(cells)
    report["h5_cells_intersecting"] = len(c)
    c = c[c.area_km2 >= 0.25].reset_index(drop=True)
    report["h5_cells_with_0_25_km2"] = len(c)
    with zipfile.ZipFile(RAW / "prague" / "GEOSTAT-grid-POP-1K-2011-V2-0-1.zip") as z:
        geo = pd.read_csv(z.open("Version 2_0_1/GEOSTAT_grid_POP_1K_2011_V2_0_1.csv"),
                          usecols=["TOT_P", "GRD_ID", "CNTR_CODE"])
    geo = geo[geo.CNTR_CODE == "CZ"].set_index("GRD_ID").TOT_P
    c["pop2011"] = c.cell.map(geo).fillna(0)
    report["h5_cells_without_geostat_record"] = int((~c.cell.isin(geo.index)).sum())
    to5514 = Transformer.from_crs("EPSG:4326", "EPSG:5514", always_xy=True)
    st = pd.read_csv(DATA / "praha2" / "metro_stations.csv")
    st = st[~st.name.isin(LINE_A_2015)]
    report["h5_metro_stations_2012"] = int(len(st))
    sx, sy = to5514.transform(st.stop_lon.to_numpy(), st.stop_lat.to_numpy())
    mx, my = to5514.transform(*MUSTEK)
    cen = np.array([[g.centroid.x, g.centroid.y] for g in c.geom])
    dmetro = np.sqrt(((cen[:, None, 0] - sx) ** 2 + (cen[:, None, 1] - sy) ** 2)).min(axis=1)
    c["log2_metro_km"] = np.log2(np.maximum(dmetro, 100) / 1000)  # floor of 100 m (registered)
    c["log2_centre_km"] = np.log2(np.maximum(np.hypot(cen[:, 0] - mx, cen[:, 1] - my), 100) / 1000)
    for name, t in [("admin_district", admin), ("city_district", districts)]:
        polys = [wkb.loads(g) for g in t.geom_wkb]
        tree = STRtree(polys)
        # the district holding the cell centroid; a centroid outside Prague takes the nearest district
        c[name] = [t.kod.iloc[int(tree.nearest(Point(x, y)))] for x, y in cen]
        report[f"h5_cells_centroid_outside_{name}"] = int(sum(
            not len(tree.query(Point(x, y), predicate="within")) for x, y in cen))
    report["h5_admin_districts"] = int(c.admin_district.nunique())
    report["h5_city_districts"] = int(c.city_district.nunique())
    c["geom_wkb"] = c.geom.apply(lambda g: g.wkb)
    return c.drop(columns=["geom"])


def main() -> None:
    report: dict = {}
    metro_frame(report).to_parquet(RAW / "h1_frame.parquet")
    czech_monthly(report).to_parquet(RAW / "czech_monthly.parquet")
    b, districts, admin, city = prague_layers(report)
    prague_cells(report, districts, admin, city).to_parquet(RAW / "prague_cells.parquet")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str) + "\n")
    print(json.dumps(report, ensure_ascii=False, default=str)[:4000])


if __name__ == "__main__":
    main()
