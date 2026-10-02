"""Build the H1, H2 and H3 tables of design §3–§5 (with the change notes) from the raw files of collect.py.

Votes: Spijkervet `votes.csv` 1975–2023 (total, televote and jury points); Wikipedia jury and televote tables for the
2024 and 2025 finals and the televote-only semi-finals (parser validated on 2023 against Spijkervet); Mirovision
2016–2022 as a cross-check of the split points. Who performed in each round: Spijkervet `contestants.csv` and the
Wikipedia tables' rows. Zeros are filled for every voter × performer of a round.

Writes tools/data/eurovision/{h1,h2,h3,validation}.parquet/json and prints counts and validation results only.

    uv run --with pandas --with pyarrow --with openpyxl --with xlrd python tools/eurovision/prepare.py
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = Path(os.environ.get("ESC_DATA", ROOT / "tools" / "data" / "eurovision"))
RAW = D / "raw"
# ISO2 (as in the vote files) -> (M49 code for UN DESA, ISO3 for UNHCR / World Bank / CEPII)
CODES = {"AL": (8, "ALB"), "AD": (20, "AND"), "AM": (51, "ARM"), "AU": (36, "AUS"), "AT": (40, "AUT"),
         "AZ": (31, "AZE"), "BY": (112, "BLR"), "BE": (56, "BEL"), "BA": (70, "BIH"), "BG": (100, "BGR"),
         "HR": (191, "HRV"), "CY": (196, "CYP"), "CZ": (203, "CZE"), "DK": (208, "DNK"), "EE": (233, "EST"),
         "FI": (246, "FIN"), "FR": (250, "FRA"), "GE": (268, "GEO"), "DE": (276, "DEU"), "GR": (300, "GRC"),
         "HU": (348, "HUN"), "IS": (352, "ISL"), "IE": (372, "IRL"), "IL": (376, "ISR"), "IT": (380, "ITA"),
         "LV": (428, "LVA"), "LT": (440, "LTU"), "LU": (442, "LUX"), "MT": (470, "MLT"), "MD": (498, "MDA"),
         "MC": (492, "MCO"), "ME": (499, "MNE"), "MA": (504, "MAR"), "NL": (528, "NLD"), "MK": (807, "MKD"),
         "NO": (578, "NOR"), "PL": (616, "POL"), "PT": (620, "PRT"), "RO": (642, "ROU"), "RU": (643, "RUS"),
         "SM": (674, "SMR"), "RS": (688, "SRB"), "SK": (703, "SVK"), "SI": (705, "SVN"), "ES": (724, "ESP"),
         "SE": (752, "SWE"), "CH": (756, "CHE"), "TR": (792, "TUR"), "UA": (804, "UKR"), "GB": (826, "GBR")}
EU = {"BE": 1958, "FR": 1958, "DE": 1958, "IT": 1958, "LU": 1958, "NL": 1958, "DK": 1973, "IE": 1973, "GB": 1973,
      "GR": 1981, "PT": 1986, "ES": 1986, "AT": 1995, "FI": 1995, "SE": 1995, "CY": 2004, "CZ": 2004, "EE": 2004,
      "HU": 2004, "LV": 2004, "LT": 2004, "MT": 2004, "PL": 2004, "SK": 2004, "SI": 2004, "BG": 2007, "RO": 2007,
      "HR": 2013}
WIKI_NAMES = {"Czech Republic": "CZ", "Bosnia and Herzegovina": "BA", "North Macedonia": "MK", "Serbia and Montenegro": "CS",
              "Moldova": "MD", "Russia": "RU", "Turkey": "TR", "Türkiye": "TR", "United Kingdom": "GB", "Netherlands": "NL"}
POINTS = {12, 10, 8, 7, 6, 5, 4, 3, 2, 1}


def rnd(label: str) -> str:
    return {"final": "final", "semi-final": "sf", "semi-final-1": "sf1", "semi-final-2": "sf2"}[label]


def in_eu(c: str, y: int) -> bool:
    return c in EU and EU[c] <= y and not (c == "GB" and y >= 2020)


# ------------------------------------------------------------------------------------------------ votes
def spijkervet() -> pd.DataFrame:
    v = pd.read_csv(RAW / "spijkervet_votes.csv")
    v = v[v.year >= 1975].copy()
    v["i"], v["j"], v["r"] = v.from_country.str.upper(), v.to_country.str.upper(), v["round"].map(rnd)
    for c in ("total_points", "tele_points", "jury_points"):
        v[c] = pd.to_numeric(v[c], errors="coerce")
    return v[["year", "r", "i", "j", "total_points", "tele_points", "jury_points"]]


def performers_spijkervet() -> pd.DataFrame:
    c = pd.read_csv(RAW / "spijkervet_contestants.csv")
    c = c[c.year >= 1975]
    rows = []
    for _, x in c.iterrows():
        code = str(x.to_country_id).upper()
        if pd.notna(x.place_final) or pd.notna(x.running_final):
            rows.append((int(x.year), "final", code))
        if pd.notna(x.sf_num):
            sf = int(x.sf_num)
            rows.append((int(x.year), "sf" if x.year < 2008 else f"sf{sf}", code))
    return pd.DataFrame(rows, columns=["year", "r", "j"]).drop_duplicates()


def name_to_code() -> dict:
    out = {}
    for row in csv.DictReader(open(RAW / "mirovision_countries.csv", encoding="utf-8")):
        out[row["country_name"]] = row["country"]
    out.update(WIKI_NAMES)
    return out


def wiki_tables(year: int) -> list[dict]:
    """Every 'Detailed … voting results' table: kind (jury/tele/total), round, voters, rows of (performer, cells)."""
    t = json.loads((RAW / f"wiki_{year}.json").read_text())["parse"]["text"]
    names = name_to_code()
    out = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", t, re.S):
        body = m.group(1)
        cap = re.search(r"<caption>(.*?)</caption>", body, re.S)
        cap = html.unescape(re.sub(r"<[^>]+>", "", cap.group(1))) if cap else ""
        if not cap.startswith("Detailed"):
            continue
        kind = "jury" if "jury" in cap else "tele" if "televoting" in cap else "total"
        r = "final" if "of the final" in cap else "sf1" if "first semi-final" in cap else "sf2" if "second semi-final" in cap else None
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)
        cell = lambda c: re.sub(r"\[[^\]]*\]", "", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()  # noqa: E731
        parsed = [[(tag, cell(c)) for tag, _, c in re.findall(r"<(t[hd])([^>]*)>(.*?)</t[hd]>", x, re.S)] for x in rows]
        head = next(p for p in parsed if len(p) > 10 and all(tag == "th" for tag, _ in p))
        voters = [names.get(n, n) for _, n in head]
        data = []
        for p in parsed:
            ths = [c for tag, c in p if tag == "th"]
            tds = [c for tag, c in p if tag == "td"]
            if ths and len(tds) >= len(voters) and ths[-1] in names:
                data.append((names[ths[-1]], tds[-len(voters):]))
        out.append({"kind": kind, "r": r, "voters": voters, "rows": data})
    return out


def wiki_votes(year: int) -> pd.DataFrame:
    """Long table year, r, i, j, audience, points (zeros kept) from the jury, televote and semi-final tables."""
    rows = []
    for tb in wiki_tables(year):
        aud = "tele" if tb["kind"] in ("tele", "total") else "jury"  # semi-finals from 2023: televote only
        for j, cells in tb["rows"]:
            for i, c in zip(tb["voters"], cells):
                if i not in CODES or i == j:
                    continue  # "Rest of the World" and any non-country voter dropped
                p = int(c) if c.isdigit() else 0
                rows.append((year, tb["r"], i, j, aud, p))
    return pd.DataFrame(rows, columns=["year", "r", "i", "j", "aud", "points"])


def validate(sp: pd.DataFrame) -> dict:
    """The Wikipedia parser on 2023 against Spijkervet 2023; Spijkervet against Mirovision 2016–2022."""
    w = wiki_votes(2023)
    w = w[w.points > 0]
    s = sp[sp.year == 2023]
    s = pd.concat([s.assign(aud="tele", points=s.tele_points), s.assign(aud="jury", points=s.jury_points)])
    s = s[s.points > 0][["year", "r", "i", "j", "aud", "points"]]
    key = ["r", "i", "j", "aud"]
    m = w.merge(s, on=key, how="outer", suffixes=("_w", "_s"), indicator=True)
    wiki_vs_spij = {"wiki_rows": len(w), "spij_rows": len(s), "only_wiki": int((m._merge == "left_only").sum()),
                    "only_spij": int((m._merge == "right_only").sum()),
                    "different_points": int(((m._merge == "both") & (m.points_w != m.points_s)).sum())}
    mv = pd.read_csv(RAW / "mirovision_votes.csv")
    mv = mv[mv.year.between(2016, 2022)].copy()
    mv["r"] = mv["round"].map(rnd)
    sp2 = sp[sp.year.between(2016, 2022)]
    mm = mv.merge(sp2, left_on=["year", "r", "from_country", "to_country"], right_on=["year", "r", "i", "j"], how="outer",
                  indicator=True)
    both = mm[mm._merge == "both"]
    miro_vs_spij = {"miro_rows": len(mv), "spij_rows": len(sp2), "unmatched": int((mm._merge != "both").sum()),
                    "tele_diff": int((both.televoting_points.fillna(0) != both.tele_points.fillna(0)).sum()),
                    "jury_diff": int((both.jury_points_x.fillna(0) != both.jury_points_y.fillna(0)).sum())}
    return {"wiki_2023_vs_spijkervet": wiki_vs_spij, "mirovision_vs_spijkervet_2016_2022": miro_vs_spij}


# ------------------------------------------------------------------------------------------------ covariates
def migrants() -> pd.DataFrame:
    """Migrants born in j living in i (both sexes), stock years 2015, 2020, 2024, for the countries of CODES."""
    x = pd.read_excel(RAW / "undesa_ims_2024.xlsx", sheet_name="Table 1", header=10)
    m49 = {v[0]: k for k, v in CODES.items()}
    cols = list(x.columns)
    yi = {y: cols.index(y) for y in (2015, 2020, 2024)}  # first occurrence = both sexes
    x = x[x["Location code of destination"].isin(m49) & x["Location code of origin"].isin(m49)]
    rows = []
    for _, r in x.iterrows():
        for y, k in yi.items():
            rows.append((m49[r["Location code of destination"]], m49[r["Location code of origin"]], y, r.iloc[k]))
    return pd.DataFrame(rows, columns=["i", "j", "stock_year", "migrants"])


def population() -> pd.DataFrame:
    w = json.loads((RAW / "wb_population.json").read_text())[1]
    iso3 = {v[1]: k for k, v in CODES.items()}
    return pd.DataFrame([(iso3[r["countryiso3code"]], int(r["date"]), r["value"]) for r in w
                         if r["countryiso3code"] in iso3 and r["value"]], columns=["i", "year", "pop"])


def stock_year(y: int) -> int:
    return 2015 if y <= 2017 else 2020 if y <= 2022 else 2024


def refugees() -> pd.DataFrame:
    iso3 = {v[1]: k for k, v in CODES.items()}
    out = []
    for y in (2022, 2024):
        for r in json.loads((RAW / f"unhcr_ukr_{y}.json").read_text())["items"]:
            if r["coa_iso"] in iso3:
                out.append((iso3[r["coa_iso"]], y, float(r["refugees"] or 0)))
    return pd.DataFrame(out, columns=["i", "year", "refugees"])


def cepii() -> pd.DataFrame:
    c = pd.read_excel(RAW / "dist_cepii.xls")
    iso3 = {v[1]: k for k, v in CODES.items()}
    iso3.update({"ROM": "RO", "YUG": "RS"})  # the 2004 file's codes
    c = c[c.iso_o.isin(iso3) & c.iso_d.isin(iso3)]
    return pd.DataFrame({"i": c.iso_o.map(iso3), "j": c.iso_d.map(iso3), "contig": c.contig, "comlang": c.comlang_off})


# ------------------------------------------------------------------------------------------------ tables
def main() -> None:
    sp = spijkervet()
    perf = performers_spijkervet()
    val = validate(sp)
    print(json.dumps(val))
    # split votes 2016–2025: Spijkervet to 2023, Wikipedia 2024–2025
    s = sp[sp.year.between(2016, 2023)]
    split = pd.concat([s.assign(aud="tele", points=s.tele_points), s.assign(aud="jury", points=s.jury_points)])
    split = split[["year", "r", "i", "j", "aud", "points"]].dropna()
    wk = pd.concat([wiki_votes(2024), wiki_votes(2025)])
    perf = pd.concat([perf, wk[["year", "r", "j"]].drop_duplicates()]).drop_duplicates()
    split = pd.concat([split, wk[wk.points > 0]])

    # H1 cells: rounds where a voter gave points with both audiences; every performer of the round
    rows = []
    for (y, r), g in split.groupby(["year", "r"]):
        both = set(g[g.aud == "tele"].i) & set(g[g.aud == "jury"].i)
        pf_ = set(perf[(perf.year == y) & (perf.r == r)].j) | set(g.j)
        pts = {(a, i, j): p for a, i, j, p in zip(g.aud, g.i, g.j, g.points)}
        for i in both:
            for j in pf_:
                if i != j:
                    for a in ("tele", "jury"):
                        rows.append((y, r, i, j, a, pts.get((a, i, j), 0)))
    h1 = pd.DataFrame(rows, columns=["year", "r", "i", "j", "aud", "points"])
    mig = migrants()
    pop = population()
    h1["stock_year"] = h1.year.map(stock_year)
    h1 = h1.merge(mig, on=["i", "j", "stock_year"], how="left").merge(
        pop.rename(columns={"year": "stock_year"}), on=["i", "stock_year"], how="left")
    h1["per1000"] = 1000 * h1.migrants / h1["pop"]
    h1["x"] = np.log1p(h1.per1000)
    h1 = h1.merge(cepii(), on=["i", "j"], how="left")
    n_missing = int(h1.x.isna().sum())
    h1_missing_pairs = sorted({f"{a}>{b}" for a, b in h1[h1.x.isna()][["i", "j"]].itertuples(index=False)})
    h1 = h1.dropna(subset=["x"])
    h1.to_parquet(D / "h1.parquet", index=False)

    # H2: finals with Ukraine performing; televote minus jury points to Ukraine
    f = h1[(h1.j == "UA") & (h1.r == "final")].pivot_table(index=["year", "i"], columns="aud", values="points").reset_index()
    f["diff"] = f.tele - f.jury
    ref = refugees().merge(pop, on=["i", "year"], how="left")
    ref["ref_per1000"] = 1000 * ref.refugees / ref["pop"]
    r22 = ref[ref.year == 2022][["i", "ref_per1000"]]
    h2 = f.merge(r22, on="i", how="left")
    h2["ref_x"] = np.log1p(h2.ref_per1000.fillna(0))
    h2["post"] = (h2.year >= 2022).astype(int)
    h2.to_parquet(D / "h2.parquet", index=False)

    # H3: directed dyads, 1975–2025, share of the voter's points in the round
    tot = sp[["year", "r", "i", "j", "total_points"]].rename(columns={"total_points": "points"})
    wk_tot = wk.groupby(["year", "r", "i", "j"], as_index=False).points.sum()
    tot = pd.concat([tot[tot.year <= 2023], wk_tot]).dropna()
    rows = []
    for (y, r), g in tot.groupby(["year", "r"]):
        voters = set(g.i)
        pf_ = set(perf[(perf.year == y) & (perf.r == r)].j) | set(g.j)
        pts = {(i, j): p for i, j, p in zip(g.i, g.j, g.points)}
        given = g.groupby("i").points.sum().to_dict()
        for i in voters:
            for j in pf_:
                if i != j and given.get(i):
                    rows.append((y, r, i, j, pts.get((i, j), 0) / given[i]))
    h3 = pd.DataFrame(rows, columns=["year", "r", "i", "j", "share"])
    h3["both_eu"] = [in_eu(i, y) and in_eu(j, y) for i, j, y in zip(h3.i, h3.j, h3.year)]
    h3.to_parquet(D / "h3.parquet", index=False)

    log = {"validation": val, "h1_cells": len(h1), "h1_missing_x_cells": n_missing, "h1_missing_pairs": h1_missing_pairs,
           "h1_rounds": sorted({f"{y} {r}" for y, r in zip(h1.year, h1.r)}), "h2_rows": len(h2), "h3_rows": len(h3)}
    (D / "prepare_log.json").write_text(json.dumps(log, indent=1))
    print(json.dumps({k: v for k, v in log.items() if k != "h1_missing_pairs"}, indent=0)[:3000])


if __name__ == "__main__":
    main()
