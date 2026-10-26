"""Completeness check of the decoded CzechInvest project table (design §2 "Projects", §3.1).

The registered decode came from one Power BI response whose data set carried `IC: true`. This script asks the public
dashboard (headless, no login) for the row count of `RP_1993-2025` and re-reads the whole table in pages of 500 rows
following the restart tokens, decodes it and compares it, row by row, with the registered CSV. If the table differs,
the new decode is saved under a new name beside the old one and both hashes go to the manifest; nothing is
overwritten. Writes tools/data/incentives/raw/czechinvest_completeness.json.

    nice -n 20 uv run --no-project python -I tools/incentives/czechinvest.py
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import MANIFEST, PROJECTS_CSV, RAW, UA, sha256

HOST = "https://wabi-north-europe-api.analysis.windows.net/public/reports/querydata?synchronous=true"
RESOURCE_KEY = "bef24953-47fe-4f39-a628-9d969c61d68f"  # public embed key from the czechinvest.org page
DATASET = "6bba6836-a650-4255-b332-c3d112abf941"
MODEL = 23716933
ENTITY = "RP_1993-2025"
PAGE = 500
PAUSE_S = 2.0
OUT = RAW / "czechinvest_completeness.json"
COUNT_FN = 2  # Power BI aggregation code for Count


def columns(path: Path = PROJECTS_CSV) -> list[str]:
    with open(path, encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def post(query: dict, binding: dict) -> dict:
    body = {"version": "1.0.0", "queries": [{"Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
        "Query": query, "Binding": binding, "ExecutionMetricsKind": 1}}]}, "QueryId": "",
        "ApplicationContext": {"DatasetId": DATASET, "Sources": [{"ReportId": "x"}]}}],
        "cancelQueries": [], "modelId": MODEL}
    rq = urllib.request.Request(HOST, data=json.dumps(body).encode(), headers={
        "User-Agent": UA, "X-PowerBI-ResourceKey": RESOURCE_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(rq, timeout=120) as r:
        return json.loads(r.read())


def col_ref(c: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": "r"}}, "Property": c}}


def row_count() -> int:
    q = {"Version": 2, "From": [{"Name": "r", "Entity": ENTITY, "Type": 0}],
         "Select": [{"Aggregation": {"Expression": col_ref("id_projekt"), "Function": COUNT_FN}, "Name": "n"}]}
    d = post(q, {"Primary": {"Groupings": [{"Projections": [0]}]}, "Version": 1})
    return int(d["results"][0]["result"]["data"]["dsr"]["DS"][0]["PH"][0]["DM0"][0]["M0"])


def decode(ds: dict, names: list[str]) -> list[list]:
    """Rows of one DSR data set: `R` repeats the previous row's value, `Ø` marks nulls, `DN` points into ValueDicts."""
    vd, n = ds.get("ValueDicts", {}), len(names)
    rows, prev, schema = [], None, None
    for r in ds["PH"][0]["DM0"]:
        schema = r.get("S", schema)
        c, rep, nul = r.get("C", []), r.get("R", 0), r.get("Ø", 0)
        cur, ci = [None] * n, 0
        for i in range(n):
            if prev is not None and (rep >> i) & 1:
                cur[i] = prev[i]
            elif (nul >> i) & 1:
                cur[i] = None
            else:
                v = c[ci]
                ci += 1
                dn = schema[i].get("DN") if schema else None
                cur[i] = vd[dn][v] if dn and isinstance(v, int) else v
        prev = cur
        rows.append(cur)
    return rows


def fetch_pages(names: list[str]) -> tuple[list[list], list[dict]]:
    q = {"Version": 2, "From": [{"Name": "r", "Entity": ENTITY, "Type": 0}],
         "Select": [col_ref(c) | {"Name": "r." + c} for c in names]}
    rows, pages, restart = [], [], None
    while True:
        window = {"Count": PAGE} | ({"RestartTokens": restart} if restart else {})
        binding = {"Primary": {"Groupings": [{"Projections": list(range(len(names)))}]},
                   "DataReduction": {"DataVolume": 4, "Primary": {"Window": window}}, "Version": 1}
        ds = post(q, binding)["results"][0]["result"]["data"]["dsr"]["DS"][0]
        page = decode(ds, names)
        if rows and page and page[0] == rows[-1]:
            page = page[1:]  # a restarted window begins again with the last row of the previous one
        rows += page
        pages.append({"rows": len(page), "IC": ds.get("IC"), "has_restart": "RT" in ds})
        restart = ds.get("RT")
        if not restart or not page:
            return rows, pages
        time.sleep(PAUSE_S)


def as_csv(names: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(names)
    w.writerows(rows)
    return buf.getvalue()


def canonical(path_or_text, names: list[str]) -> list[tuple]:
    text = path_or_text.read_text(encoding="utf-8") if isinstance(path_or_text, Path) else path_or_text
    return sorted(tuple(r.get(c) or "" for c in names) for r in csv.DictReader(io.StringIO(text)))


def main() -> None:
    names = columns()
    n_count = row_count()
    rows, pages = fetch_pages(names)
    fresh = as_csv(names, rows)
    old_rows, new_rows = canonical(PROJECTS_CSV, names), canonical(fresh, names)
    old_ids, new_ids = {r[0] for r in old_rows}, {r[0] for r in new_rows}
    same = old_rows == new_rows
    report = {"date": dt.date.today().isoformat(), "dashboard_row_count": n_count, "registered_rows": len(old_rows),
              "paged_rows": len(new_rows), "pages": pages, "identical_to_registered": same,
              "ids_only_in_registered": sorted(old_ids - new_ids), "ids_only_in_paged": sorted(new_ids - old_ids),
              "registered_sha256": sha256(PROJECTS_CSV)}
    if not same:
        new = RAW / f"czechinvest_powerbi_RP_1993-2025_paged_{report['date']}.csv"
        new.write_text(fresh, encoding="utf-8")
        report |= {"new_file": new.name, "new_sha256": sha256(new)}
        with open(MANIFEST, "a", encoding="utf-8") as f:
            f.write(f"{new.name}\t{HOST.split('?')[0]} (paged re-query, {PAGE} rows per page)\t{report['date']}\t"
                    f"{report['new_sha256']}\n")
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "pages"}, ensure_ascii=False))
    print("pages:", len(pages))


if __name__ == "__main__":
    main()
