"""Data step of the priorities design (§3): the three series as tables, and their counts.

Reads the raw files of fetch.py and writes, under tools/data/priorities/:
- concern.parquet: the Czech column of the Eurobarometer item "the two most important issues facing (our country)",
  one row per wave × split arm × answer item (share as published, weighted count, Czech N, fieldwork dates);
- attention.parquet: one row per kept ParlaCAP-CZ speech (no text); chair, Mix and Other speeches are dropped (§2.2);
- spending.parquet: gov_10a_exp, Czechia, S13, TE, million CZK, one row per year × COFOG code.
and docs/research/priorities-data.json with counts, formats and coverage only. Nothing here prints, plots or
summarises a Czech share of concern, attention or spending (§3); the shares are written to the parquet files only.

    nice -n 20 uv run --no-project --with pandas --with pyarrow --with xlrd --with openpyxl \
        python -I tools/priorities/prepare.py
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools/data/priorities"
OUT = ROOT / "docs/research/priorities-data.json"

# Volume A member file and sheets holding the item, per wave (feasibility inventory, 14 October 2026).
EB_SHEETS = {
    62: ("VolumeAEB620PRESSstandard20041122.xls", ("S3",)),
    63: ("VolumeAEB634PRESSstandard20050624.xls", ("QA26",)),
    64: ("VolumeAEB642PRESSstandard20051121.xls", ("QA30",)),
    65: ("VolumeAEB652COMMstandard20060510.xls", ("QA28a", "QA28b")),
    66: ("VolumeAEB661COMMstandard20061020.xls", ("QA23.1",)),
    67: ("VolumeAEB672COMMstandard20070720.xls", ("QA18a",)),
    68: ("VolumeAEB681COMMstandard20071107.xls", ("QA6a",)),
    69: ("VolumeAEB692COMMcomplet20080711.xls", ("QA6a",)),
    70: ("VolumeAEB701COMMstandard20081118.xls", ("QA8a",)),
    71: ("VolumeAEB713COMMstandard20091126.xls", ("QA4a",)),
    72: ("VolumeAEB724COMMstandard20091124.xls", ("QA5a",)),
    73: ("VolumeAEB734COMMcomplet20100602.xls", ("QA7a",)),
    74: ("VolumeAEB742COMMcomplet20101206.xls", ("QA6a1", "QA6a2")),
    75: ("VolumeAEB753COMMstandard20110531.xls", ("QA7a1", "QA7a2")),
    76: ("VolumeAEB763COMMstandard.xls", ("QA6a1", "QA6a2")),
    77: ("VolumeAEB773COMMstandard20120601.xls", ("QA7a",)),
    78: ("VolumeAEB781COMMstandard20121217.xls", ("QA5a",)),
    79: ("VolumeAEB793COMMstandardEU2820130603.xls", ("QA6a",)),
    80: ("VolumeAEB801COMMstandard20131129.xls", ("QA4a",)),
    81: ("VolumeAEB814COMMstandard.xls", ("QA4a",)),
    82: ("VolumeAEB823COMMstandard20141120.xls", ("QA3a",)),
    83: ("VolumeAEB833COMMcomplet20150619.xls", ("QA3a",)),
    84: ("VolumeAEB843COMMstandard20151119.xls", ("QA3a",)),
    85: ("EB85.2 Volume A.xls", ("QA3a",)),
    86: ("ST86 - Volume A.xls", ("QA3a",)),
    87: ("eb87_Volume_A_final.xls", ("QA3a",)),
    88: ("eb88_Volume_A_final.xls", ("QA3a",)),
    89: ("eb_89_vol_A.xls", ("QA3a",)),
    90: ("eb_90_volume_A.xls", ("QA3a",)),
    91: ("eb_91_volume_A.xls", ("QA3a",)),
    92: ("eb92_Volume_A.xls", ("QA3a", "QA3b")),
    93: ("eb_93_volume_A.xlsx", ("T31",)),
    **{w: (None, ("QA3a",)) for w in (94, 95)},
    **{w: (None, ("QA3",)) for w in range(96, 105)},
}
# Split-ballot arms by sheet (§2.1); EB71 marks its two environment items inside one table instead.
ARM_SHEETS = {65: ("QA28a", "QA28b"), 74: ("QA6a1", "QA6a2"), 75: ("QA7a1", "QA7a2"), 76: ("QA6a1", "QA6a2"),
              92: ("QA3a", "QA3b")}
# Survey fieldwork as printed in the Volume A header or the data.europa.eu description; Volume A carries no
# country-level dates, and before EB75 only months.
FIELDWORK = {
    62: ("2004-10", "2004-11"), 63: ("2005-05", "2005-06"), 64: ("2005-10", "2005-11"), 65: ("2006-04", "2006-04"),
    66: ("2006-09", "2006-09"), 67: ("2007-04", "2007-05"), 68: ("2007-09", "2007-10"), 69: ("2008-03", "2008-04"),
    70: ("2008-10", "2008-10"), 71: ("2009-06", "2009-06"), 72: ("2009-10", "2009-11"), 73: ("2010-05", "2010-05"),
    74: ("2010-11", "2010-11"), 75: ("2011-05-06", "2011-05-25"), 76: ("2011-11-03", "2011-11-20"),
    77: ("2012-05-12", "2012-05-27"), 78: ("2012-11-02", "2012-11-18"), 79: ("2013-05-10", "2013-05-26"),
    80: ("2013-11-02", "2013-11-17"), 81: ("2014-05-31", "2014-06-14"), 82: ("2014-11-08", "2014-11-17"),
    83: ("2015-05-16", "2015-05-27"), 84: ("2015-11-07", "2015-11-17"), 85: ("2016-05-21", "2016-05-30"),
    86: ("2016-11-05", "2016-11-14"), 87: ("2017-05-20", "2017-05-30"), 88: ("2017-11-05", "2017-11-14"),
    89: ("2018-03-13", "2018-03-28"), 90: ("2018-11-08", "2018-11-22"), 91: ("2019-06-07", "2019-07-01"),
    92: ("2019-11-14", "2019-11-29"), 93: ("2020-07-10", "2020-08-26"), 94: ("2021-02-12", "2021-03-11"),
    95: ("2021-06-14", "2021-07-15"), 96: ("2022-01-18", "2022-02-14"), 97: ("2022-06-17", "2022-07-17"),
    98: ("2023-01-12", "2023-02-06"), 99: ("2023-05-31", "2023-06-25"), 100: ("2023-10-23", "2023-11-17"),
    101: ("2024-04-02", "2024-05-09"), 102: ("2024-10-10", "2024-11-05"), 103: ("2025-03-26", "2025-04-22"),
    104: ("2025-10-09", "2025-11-05"),
}
MODE_FLAG = range(93, 97)
# Split B of EB92 ends with a row that is not on the questionnaire, apparently the net of its two new items.
NET_ROWS = {(92, "B", "The environment, climate and energy issues")}

ITEM_Q = re.compile(r"most important (issues?|problems?) (facing|in) \(?\s*(our country|OUR COUNTRY)", re.I)
NOT_ITEM = re.compile(r"personally|European Union|\(the EU\)|facing the EU|in 2030", re.I)
QUESTION = re.compile(r"^(Q[A-Z]{0,2}\d+[a-z]?\d*(\.\d+)?|D\d+[a-z]?)\b")
SPLIT_MARK =re.compile(r"^\((?:ONLY TO )?SPLIT ([AB])\)\s*", re.I)

# Chamber of Deputies terms in ParlaMint's text ids ("ps2013" is the term elected in 2013).
TERMS = {"ps2013": "2013-2017", "ps2017": "2017-2021", "ps2021": "2021-2025"}


def text(v) -> str:
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else ""


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_dash(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"\s*[-–]\s*", v) is not None


def sheet_rows(wave: int) -> dict[str, list[list]]:
    """Rows of the item's sheets, cells as stored (numbers unformatted)."""
    inner, sheets = EB_SHEETS[wave]
    path = RAW / "eb" / f"eb{wave}.{'zip' if inner else 'xlsx'}"
    if inner:
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if Path(n).name == inner)
            body = z.read(name)
    else:
        body = path.read_bytes()
    if (inner or "").endswith(".xls"):
        import xlrd
        book = xlrd.open_workbook(file_contents=body, on_demand=True)
        return {s: [book.sheet_by_name(s).row_values(r) for r in range(book.sheet_by_name(s).nrows)] for s in sheets}
    import openpyxl
    book = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    return {s: [list(r) for r in book[s].iter_rows(values_only=True)] for s in sheets}


def czech_blocks(rows: list[list]) -> list[tuple[int, list[list]]]:
    """(CZ column, rows from the Total row on) of every page of the item that has a Czech column."""
    out = []
    for i, r in enumerate(rows):
        q = " ".join(text(v) for v in r)
        if not ITEM_Q.search(q) or NOT_ITEM.search(q):
            continue
        for j in range(i + 1, min(i + 15, len(rows))):
            cz = [c for c, v in enumerate(rows[j]) if text(v) == "CZ"]
            if cz:
                end = j + 1
                while end < len(rows) and not any(QUESTION.match(text(v)) for v in rows[end]):
                    end += 1
                out.append((cz[0], rows[j + 1:end]))
                break
    return out


def label(r: list) -> str:
    return " ".join(text(v) for v in r[:3] if isinstance(v, str) and text(v) and not is_dash(v))


def parse_block(cz: int, rows: list[list]) -> tuple[float, list[dict]]:
    """Czech N (Total row) and the items. Each item is a weighted-count row, then a share row; the English label is
    on the share row, or after the line break of a combined French/English label on the count row."""
    filled = [r for r in rows if cz < len(r) and (is_number(r[cz]) or is_dash(r[cz]))]
    total, body = filled[0], filled[1:]
    assert re.match(r"total", label(total), re.I), label(total)
    assert len(body) % 2 == 0, len(body)
    items = []
    for count_row, share_row in zip(body[::2], body[1::2]):
        raw_fr = next(v for v in count_row[:3] if isinstance(v, str) and text(v) and not is_dash(v))
        en = label(share_row) or raw_fr.split("\n")[-1]
        c, s = count_row[cz], share_row[cz]
        assert is_number(c) or is_dash(c)
        assert is_dash(s) or (is_number(s) and 0 <= s <= 1), f"share cell of {en!r} is not a fraction"
        items.append({"label": text(en), "count_weighted": float(c) if is_number(c) else 0.0,
                      "share": float(s) if is_number(s) else 0.0, "share_dash": is_dash(s)})
    return float(total[cz]), items


def concern() -> tuple[pd.DataFrame, dict]:
    out, meta = [], {}
    for wave in EB_SHEETS:
        arms = ARM_SHEETS.get(wave)
        wave_meta = {"sheets": [], "czech_n": {}, "items": {}}
        for sheet, rows in sheet_rows(wave).items():
            arm = "AB" if arms is None else "AB"[arms.index(sheet)]
            blocks = czech_blocks(rows)
            assert blocks, (wave, sheet)
            ns = set()
            for cz, block in blocks:
                n, items = parse_block(cz, block)
                ns.add(n)
                for it in items:
                    m = SPLIT_MARK.match(it["label"])
                    item_arm = m.group(1).upper() if m else arm
                    out.append({"wave": wave, "sheet": sheet, "arm": "all" if item_arm == "AB" else item_arm,
                                "item": SPLIT_MARK.sub("", it["label"]), "share": it["share"],
                                "share_dash": it["share_dash"], "count_weighted": it["count_weighted"],
                                "czech_n": n})
            assert len(ns) == 1, (wave, sheet)
            key = "all" if arm == "AB" else arm
            wave_meta["sheets"].append(sheet)
            wave_meta["czech_n"][key] = int(round(ns.pop()))
        meta[wave] = wave_meta
    df = pd.DataFrame(out)
    start = {w: s for w, (s, _) in FIELDWORK.items()}
    end = {w: e for w, (_, e) in FIELDWORK.items()}
    df["fieldwork_start"], df["fieldwork_end"] = df.wave.map(start), df.wave.map(end)
    df["date_precision"] = df.fieldwork_start.str.len().map({7: "month", 10: "day"})
    df["mode_flag"] = df.wave.isin(MODE_FLAG)
    df["net_row"] = [(w, a, i) in NET_ROWS for w, a, i in zip(df.wave, df.arm, df["item"])]
    for w, g in df.groupby("wave"):
        meta[w]["items"] = {a: int(n) for a, n in g.groupby("arm").size().items()}
        # Whole percentages are fractions with two decimals; any finer value means decimal percentages.
        cents = g.share * 100
        meta[w]["share_format"] = "fraction, whole percent" if ((cents - cents.round()).abs() < 1e-9).all() \
            else "fraction, decimal percent"
    return df, meta


def attention() -> tuple[pd.DataFrame, dict]:
    path = RAW / "parlacap/ParlaCAP-CZ_speeches.tsv.zip"
    cols = ["text_id", "id", "date", "speaker_role", "speaker_MP", "party_status", "word_count", "CAP_category", "CAP_prob"]
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".tsv"))
        with z.open(name) as f:
            df = pd.read_csv(f, sep="\t", usecols=cols, dtype=str, na_values=["-"], keep_default_na=False)
    df["word_count"] = df.word_count.astype(int)
    df["CAP_prob"] = df.CAP_prob.astype(float)
    df["term"] = df.text_id.str.extract(r"(ps\d{4})", expand=False).map(TERMS)
    df["drop"] = None
    df.loc[df.CAP_category == "Other", "drop"] = "Other"
    df.loc[df.CAP_category == "Mix", "drop"] = "Mix"
    df.loc[df.speaker_role == "Chairperson", "drop"] = "chair"  # chair first: a chair speech is dropped as chair

    by_term = {}
    for t, g in df.groupby("term", dropna=False):
        row = {"speeches": len(g), "words": int(g.word_count.sum()), "first": g.date.min(), "last": g.date.max()}
        for reason in ("chair", "Mix", "Other"):
            d = g[g["drop"] == reason]
            row[f"dropped_{reason}"] = {"speeches": len(d), "words": int(d.word_count.sum())}
        k = g[g["drop"].isna()]
        row["kept"] = {"speeches": len(k), "words": int(k.word_count.sum())}
        by_term[str(t)] = row
    meta = {
        "rows": len(df),
        "speaker_role_values": sorted(df.speaker_role.dropna().unique().tolist()),
        "party_status_values": sorted(df.party_status.dropna().unique().tolist()),
        "CAP_category_values": sorted(df.CAP_category.dropna().unique().tolist()),
        "missing": {c: int(df[c].isna().sum()) for c in ("date", "speaker_role", "party_status", "CAP_category")},
        "by_term": by_term,
    }
    kept = df[df["drop"].isna()].drop(columns=["drop"])
    kept = kept.assign(date=pd.to_datetime(kept.date))
    return kept[["id", "date", "term", "speaker_role", "speaker_MP", "party_status", "CAP_category", "CAP_prob",
                 "word_count"]], meta


def spending() -> tuple[pd.DataFrame, dict]:
    js = json.loads((RAW / "eurostat/gov_10a_exp_CZ.json").read_text())
    dims, size = js["id"], js["size"]
    assert all(n == 1 for d, n in zip(dims, size) if d not in ("cofog99", "time")), dict(zip(dims, size))
    cof = {i: k for k, i in js["dimension"]["cofog99"]["category"]["index"].items()}
    yrs = {i: k for k, i in js["dimension"]["time"]["category"]["index"].items()}
    ci, ti = dims.index("cofog99"), dims.index("time")
    stride = [1] * len(size)
    for k in range(len(size) - 2, -1, -1):
        stride[k] = stride[k + 1] * size[k + 1]
    status = js.get("status", {})
    rows = []
    for flat, v in js["value"].items():
        flat = int(flat)
        rows.append({"year": int(yrs[flat // stride[ti] % size[ti]]), "cofog": cof[flat // stride[ci] % size[ci]],
                     "value": float(v), "status": status.get(str(flat), "")})
    df = pd.DataFrame(rows).sort_values(["year", "cofog"], ignore_index=True)
    years = sorted(df.year.unique().tolist())
    meta = {
        "updated": js.get("updated"),
        "cofog_codes": int(df.cofog.nunique()),
        "years_present": years,
        "years_with_total": sorted(df[df.cofog == "TOTAL"].year.unique().tolist()),
        "codes_per_year": {str(y): int(n) for y, n in df.groupby("year").size().items()},
        "status_flags": {k or "none": int(n) for k, n in df.status.value_counts().items()},
    }
    return df, meta


def main() -> None:
    con, con_meta = concern()
    con.to_parquet(RAW / "concern.parquet", index=False)
    att, att_meta = attention()
    att.to_parquet(RAW / "attention.parquet", index=False)
    spe, spe_meta = spending()
    spe.to_parquet(RAW / "spending.parquet", index=False)

    formats = sorted({m["share_format"] for m in con_meta.values()})
    OUT.write_text(json.dumps({
        "design": "docs/research/priorities-design.md, section 3",
        "note": "Counts, formats and coverage only. Window coverage (§3) is computed with the windows of §4, "
                "after the validation coding.",
        "concern": {
            "source": "Standard Eurobarometer Volume A (data.europa.eu), Czech column; no Volume C needed",
            "waves_read": sorted(con_meta),
            "n_waves": len(con_meta),
            "czech_n": {str(w): m["czech_n"] for w, m in con_meta.items()},
            "czech_n_note": "the Total row of the weighted Volume A table (weighted base)",
            "items_per_wave": {str(w): m["items"] for w, m in con_meta.items()},
            "sheets": {str(w): m["sheets"] for w, m in con_meta.items()},
            "share_format": formats[0] if len(formats) == 1 else {str(w): m["share_format"]
                                                                  for w, m in con_meta.items()},
            "fieldwork_dates": "survey-wide; Volume A gives no Czech dates; month precision before EB75",
            "waves_with_month_precision": sorted(w for w, (s, _) in FIELDWORK.items() if len(s) == 7),
        },
        "attention": {"source": "ParlaCAP-CZ (CROSSDA doi:10.23669/1ZTELP), speech file", **att_meta},
        "spending": {"source": "Eurostat gov_10a_exp, CZ, S13, TE, MIO_NAC", **spe_meta},
    }, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"concern {len(con)} rows, {len(con_meta)} waves; attention {len(att)} speeches; spending {len(spe)} rows")
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
