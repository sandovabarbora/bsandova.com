"""Run the licence-fee study (docs/research/fees-design.md). Every stage that reads a real source value needs --unblind
and the frozen code; --structure and --verify-files read labels and hashes only; --synthetic runs on invented files.

    P="--with pytest==9.1.1"          # tests only; the run itself needs no package (standard library, poppler's pdftotext)
    uv run --no-project python -I tools/fees/cli.py --synthetic
    uv run --no-project python -I tools/fees/cli.py --verify-files
    uv run --no-project python -I tools/fees/cli.py --structure
    # after the author signs the tag fees-code (config.CODE_TAG):
    nice -n 20 uv run --no-project python -I tools/fees/cli.py --run --unblind
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as A
import config as C
import files as F
import inputs as I
import parse as P
import structure as S
import synth as SY


def versions() -> dict:
    return {"python": platform.python_version(), "pdftotext": P.pdftotext_version()}


def results_for(src: I.Sources) -> dict:
    loaded = I.load(src)
    res = A.run(loaded.qb, loaded.qa, loaded.gross_labels)
    res["inputs"] = {"inflation_path_pct": A.L.inflation_series(loaded.qa.csu_2025, loaded.qa.cnb_annual),
                     "cnb_quarterly_pct": loaded.cnb_quarterly,
                     "fee_line_2026_czk": loaded.qa.fee_line_2026, "realised_2025_czk": loaded.qa.realised_2025,
                     "budget_items_with_empty_cell_read_as_zero": loaded.budget_blank_items,
                     "household_payers": {"tv": loaded.qb.payers_tv, "radio": loaded.qb.payers_r},
                     "employer_counts_by_band": loaded.qb.employer_counts}
    return res


def write(res: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(A.jsonable(res), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="dry run on invented files")
    ap.add_argument("--verify-files", action="store_true", help="hashes of the snapshot against the manifest")
    ap.add_argument("--structure", action="store_true", help="labels, positions and counts of the real files, no values")
    ap.add_argument("--run", action="store_true", help="the registered analysis; writes docs/research/fees-results.json")
    ap.add_argument("--unblind", action="store_true", help="open the real values (needs the frozen code)")
    ap.add_argument("--out", type=Path, help="folder for the synthetic run (default: a new temporary one)")
    args = ap.parse_args(argv)
    if args.synthetic:
        out = args.out or Path(tempfile.mkdtemp(prefix="fees-synthetic-"))
        res = results_for(SY.make_snapshot(out / "snapshot"))
        res["synthetic"] = True
        res["versions"] = versions()
        write(res, out / "fees-results-synthetic.json")
        print(f"wrote {out / 'fees-results-synthetic.json'}; labels: Q-A {res['qa']['label']}; Q-B {res['qb']['labels']}")
        return
    if args.verify_files:
        problems = F.verify_files()
        print("all files match the manifest" if not problems else "\n".join(problems))
        sys.exit(1 if problems else 0)
    if args.structure:
        problems = F.verify_files()
        if problems:
            sys.exit("refusing to look at the files: " + "; ".join(problems[:5]))
        for line in S.describe(I.real_sources()):
            print(line)
        return
    if args.run:
        if not args.unblind:
            sys.exit("refusing to open the real values: pass --unblind once the code is tagged (design: Running and verification)")
        F.gate()
        res = results_for(I.real_sources())
        res["design"] = {"file": str(C.DESIGN.relative_to(C.ROOT)), "stamp": F.stamp()}
        res["versions"] = versions()
        res["generated"] = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        write(res, C.RESULTS)
        print(f"wrote {C.RESULTS}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
