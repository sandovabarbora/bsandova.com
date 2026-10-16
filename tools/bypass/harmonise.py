"""One schema for the police accident records of every year (design §2 "Accidents"), one row per accident, never
aggregated by place.

Two formats are published. 2016–2022: one headerless CSV per police region (00–19.csv, cp1250, `;`, quoted), whose
columns are listed in the field-description workbook (sheet "Seznam polí"); each row is one accident. 2023–2025: HTML
tables saved as .xls, Inehody.xls (one row per accident) and IntGPS.xls (coordinates), joined on p1. The S-JTSK
coordinates (EPSG:5514) come as d and e in both, but in the CSVs d is the easting and in the HTML files it is the
northing; the two axes do not overlap in Czechia (easting −430 to −905 km, northing −935 to −1 230 km), so x is the
larger of the two on every row. Records are placed in a municipality by the RÚIAN polygons; a record without
coordinates keeps the municipality it names (CSV column r, the RÚIAN municipality code; HTML column h, a name, used
only when it matches exactly one municipality name in RÚIAN) and counts in Q2 only.

Exact duplicate rows within a year are dropped and counted. Writes tools/data/bypass/accidents.parquet and
harmonise-log.json beside it.

    nice -n 20 uv run --no-project --with pandas --with numpy --with pyarrow --with geopandas --with pyogrio \
        python -I tools/bypass/harmonise.py
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/bypass"
RAW = DATA / "raw/police"
EXTRACTED = DATA / "extracted"
OBCE = DATA / "ruian/1/OBCE_P.shp"
OUT = DATA / "accidents.parquet"
LOG = DATA / "harmonise-log.json"
YEARS = range(2016, 2026)
CSV_YEARS = range(2016, 2023)
CSV_COLUMNS = ("p1 p36 p37 p2a weekday p2b p6 p7 p8 p9 p10 p11 p12 p13a p13b p13c p14 p15 p16 p17 p18 p19 p20 p21 p22 "
               "p23 p24 p27 p28 p34 p35 p39 p44 p45a p47 p48a p49 p50a p50b p51 p52 p53 p55a p57 p58 a b d e f g h i j k "
               "l n o p q r s t p5a").split()
# source column -> schema column, per format
MAPPING = {
    "csv": {"p1": "p1", "p2a": "date", "p5a": "p5a", "p9": "p9", "p13a": "killed", "p13b": "serious",
            "p13c": "slight", "p36": "road_class", "p37": "road_no", "p35": "p35", "p28": "p28", "d": "d", "e": "e",
            "r": "muni_record", "h": "muni_name_record"},
    "html": {"p1": "p1", "p2a": "date", "p4a": "region", "p5a": "p5a", "p9": "p9", "p13a": "killed",
             "p13b": "serious", "p13c": "slight", "p36": "road_class", "p37": "road_no", "p35": "p35", "p28": "p28",
             "d": "d", "e": "e", "h": "muni_name_record"},
}
DATE_FORMAT = {"csv": "%Y-%m-%d", "html": "%d.%m.%Y"}
ROAD_CLASS = {0: "D", 1: "I", 2: "II", 3: "III"}
X_RANGE, Y_RANGE = (-905_000, -430_000), (-1_230_000, -935_000)
JUNCTION = (10, 28)  # p35: 10 at a junction, 11–19 inside its zones, 22–28 grade-separated ramps; 0 and 29 are outside


def archive(year: int) -> Path:
    found = sorted(RAW.glob(f"{year}_*.rar")) + sorted(RAW.glob(f"{year}_*.zip"))
    assert len(found) == 1, (year, found)
    return found[0]


def extract(year: int) -> Path:
    out = EXTRACTED / str(year)
    if not out.exists():
        out.mkdir(parents=True)
        subprocess.run(["bsdtar", "-xf", str(archive(year)), "-C", str(out)], check=True)
    return out


def read_csv_year(folder: Path) -> pd.DataFrame:
    parts = []
    for f in sorted(folder.glob("[0-9][0-9].csv")):
        if f.stat().st_size == 0:
            continue
        df = pd.read_csv(f, sep=";", header=None, names=CSV_COLUMNS, dtype=str, encoding="cp1250",
                         keep_default_na=False)
        assert df.shape[1] == len(CSV_COLUMNS), f
        df["region_file"] = f.stem
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    return df[list(MAPPING["csv"]) + ["region_file"]].rename(columns=MAPPING["csv"])


ROW = re.compile(r"<TR>(.*?)</TR>", re.S | re.I)
CELL = re.compile(r"<T[DH]>(.*?)</T[DH]>", re.S | re.I)


def read_html_table(path: Path) -> pd.DataFrame:
    text = path.read_bytes().decode("cp1250")
    rows = [[html.unescape(c).strip() for c in CELL.findall(r)] for r in ROW.findall(text)]
    head, body = rows[0], rows[1:]
    body = [r[:-1] if len(r) == len(head) + 1 and r[-1] == "" else r for r in body]  # every data row ends in an empty cell
    assert all(len(r) == len(head) for r in body), path
    return pd.DataFrame(body, columns=head, dtype=str)


def read_html_year(folder: Path) -> pd.DataFrame:
    acc = read_html_table(folder / "Inehody.xls")
    gps = read_html_table(folder / "IntGPS.xls")
    for t in (acc, gps):
        t["p1"] = t["p1"].astype("int64").astype(str)
    assert acc["p1"].is_unique and gps["p1"].is_unique
    df = acc.merge(gps[["p1", "d", "e", "h"]], on="p1", how="left", validate="one_to_one")
    return df[list(MAPPING["html"])].rename(columns=MAPPING["html"])


def number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.strip().str.replace(",", ".", regex=False).replace("", np.nan),
                         errors="coerce")


def xy(d: pd.Series, e: pd.Series) -> tuple[pd.Series, pd.Series]:
    """x is the larger of d and e on each row; both inside their Czech ranges, else missing."""
    d, e = number(d), number(e)
    x, y = np.fmax(d, e), np.fmin(d, e)
    ok = x.between(*X_RANGE) & y.between(*Y_RANGE)
    return x.where(ok), y.where(ok)


def normalise(df: pd.DataFrame, fmt: str, year: int) -> pd.DataFrame:
    out = pd.DataFrame({"file_year": year, "format": fmt, "p1": df["p1"].str.strip()})
    out["date"] = pd.to_datetime(df["date"].str.strip(), format=DATE_FORMAT[fmt], errors="coerce")
    out["year"] = out["date"].dt.year.astype("Int64")
    out["region"] = (df["region_file"] if fmt == "csv" else df["region"]).astype(str).str.strip()
    for c in ("p5a", "p9", "killed", "serious", "slight", "road_class", "road_no", "p35", "p28"):
        out[c] = number(df[c]).astype("Int64")
    out["severity_coded"] = out[["killed", "serious", "slight"]].notna().all(axis=1)
    out["injury"] = (out[["killed", "serious", "slight"]].fillna(0).sum(axis=1) > 0).where(out["severity_coded"])
    out["ksi"] = ((out["killed"].fillna(0) + out["serious"].fillna(0)) > 0).where(out["severity_coded"])
    out["built_up"] = out["p5a"].map({1: True, 2: False}).astype("boolean")
    out["junction"] = out["p35"].between(*JUNCTION).where(out["p35"].notna()).astype("boolean")
    out["road"] = [f"{ROAD_CLASS[c]}/{n}" if pd.notna(c) and c in ROAD_CLASS and pd.notna(n) and n > 0 else None
                   for c, n in zip(out["road_class"], out["road_no"])]
    out["x"], out["y"] = xy(df["d"], df["e"])
    out["muni_record"] = (number(df["muni_record"]).astype("Int64") if "muni_record" in df else pd.NA)
    out["muni_name_record"] = df["muni_name_record"].astype(str).str.strip()
    return out


def fold(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", s)


def place(df: pd.DataFrame, obce) -> pd.DataFrame:
    import geopandas as gpd
    has = df["x"].notna()
    pts = gpd.GeoDataFrame(index=df.index[has], geometry=gpd.points_from_xy(df.loc[has, "x"], df.loc[has, "y"]),
                           crs=obce.crs)
    hit = gpd.sjoin(pts, obce[["KOD", "geometry"]], how="left", predicate="within")
    hit = hit[~hit.index.duplicated()]
    df["muni_polygon"] = pd.Series(hit["KOD"], index=hit.index).reindex(df.index).astype("Int64")
    codes = set(obce["KOD"].astype(int))
    by_name = obce.assign(f=obce["NAZEV"].map(fold)).groupby("f")["KOD"].agg(list)
    unique = {k: int(v[0]) for k, v in by_name.items() if len(v) == 1}
    rec = df["muni_record"].where(df["muni_record"].isin(codes))
    named = df["muni_name_record"].map(fold).map(unique).astype("Int64")
    rec = rec.fillna(named.where(df["format"] == "html"))
    df["muni_record_valid"] = rec.astype("Int64")
    df["muni"] = df["muni_polygon"].fillna(df["muni_record_valid"].where(df["x"].isna()))
    df["muni_source"] = np.select([df["muni_polygon"].notna(), df["x"].isna() & df["muni_record_valid"].notna()],
                                  ["polygon", "record"], "none")
    return df


def load_obce():
    import geopandas as gpd
    obce = gpd.read_file(OBCE)
    obce["KOD"] = obce["KOD"].astype(int)
    assert obce.crs is not None and obce.crs.to_epsg() in (5514, None)
    return obce


def build() -> tuple[pd.DataFrame, dict]:
    parts, log = [], {}
    for year in YEARS:
        folder = extract(year)
        fmt = "csv" if year in CSV_YEARS else "html"
        raw = read_csv_year(folder) if fmt == "csv" else read_html_year(folder)
        rows = normalise(raw, fmt, year)
        exact = rows.astype(str).duplicated()
        log[year] = {"format": fmt, "rows_in_files": len(raw), "exact_duplicates_dropped": int(exact.sum())}
        parts.append(rows[~exact.to_numpy()])
        print(year, fmt, len(raw))
    df = pd.concat(parts, ignore_index=True)
    assert not df.duplicated(["file_year", "p1"]).any(), "p1 repeated with different content"
    return place(df, load_obce()), log


def main() -> None:
    df, log = build()
    LOG.write_text(json.dumps(log, indent=1))
    df.to_parquet(OUT, index=False)
    print("rows", len(df), "->", OUT)


if __name__ == "__main__":
    main()
