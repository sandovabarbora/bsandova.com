"""Run the film incentive study (docs/research/rebates-design.md). --structure is the data step: it reads the evidence
numbers and the non-outcome columns and writes counts and booleans; --run needs --unblind and the frozen code;
--synthetic runs the data step on invented lists.

    P="--with pytest==9.1.1"          # tests only; the run itself needs no package (standard library, poppler's pdftotext)
    uv run --no-project --python 3.12 python -I tools/rebates/cli.py --verify-files
    uv run --no-project --python 3.12 python -I tools/rebates/cli.py --structure      # or: python -m tools.rebates.cli --structure
    uv run --no-project --python 3.12 python -I tools/rebates/cli.py --synthetic
    # after the author signs the tag rebates-code (config.CODE_TAG):
    nice -n 20 uv run --no-project --python 3.12 python -I tools/rebates/cli.py --run --unblind
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as A
import config as C
import files as F
import parse as P
import structure as S
import synth as SY


def versions() -> dict:
    return {"python": platform.python_version(), "pdftotext": P.pdftotext_version()}


def load(specs: Sequence[C.ListSpec] | None = None) -> dict[str, list[P.Row]]:
    return {s.name: P.parse_list(s.path, s.name) for s in specs or C.LISTS}


def structure(specs: Sequence[C.ListSpec], out: Path, manifest: Path | None) -> dict:
    try:
        rep = S.report(load(specs), specs)
    except P.ParseError as e:
        rep = S.failed_parse(e)
    rep["lists"] = {s.name: {"file": s.path.name, "list_date": s.list_date.isoformat(),
                             "stated_years": list(s.years)} for s in specs}
    if manifest is not None:
        rep["manifest_sha256"] = F.sha256(manifest)
    rep["versions"] = versions()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return rep


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-files", action="store_true", help="hashes of the snapshot against the manifest")
    ap.add_argument("--structure", action="store_true",
                    help="the data step: non-outcome columns, counts and booleans; writes docs/research/rebates-structure.json")
    ap.add_argument("--synthetic", action="store_true", help="the data step on invented lists")
    ap.add_argument("--run", action="store_true", help="the registered analysis; writes docs/research/rebates-results.json")
    ap.add_argument("--unblind", action="store_true", help="open the outcome columns (needs the frozen code)")
    ap.add_argument("--out", type=Path, help="folder for the synthetic run (default: a new temporary one)")
    args = ap.parse_args(argv)
    if args.verify_files:
        problems = F.verify_files()
        print("all files match the manifest" if not problems else "\n".join(problems))
        sys.exit(1 if problems else 0)
    if args.structure or args.synthetic:
        if args.synthetic:
            out = args.out or Path(tempfile.mkdtemp(prefix="rebates-synthetic-"))
            specs, target, manifest = SY.make_lists(out / "snapshot"), out / "rebates-structure-synthetic.json", None
        else:
            problems = F.verify_files()
            if problems:
                sys.exit("refusing to look at the files: " + "; ".join(problems[:5]))
            specs, target, manifest = C.LISTS, C.STRUCTURE, C.MANIFEST
        rep = structure(specs, target, manifest)
        for line in S.describe(rep):
            print(line)
        print(f"wrote {target}")
        sys.exit(1 if rep["stops"] else 0)
    if args.run:
        if not args.unblind:
            sys.exit("refusing to open the outcome columns: pass --unblind once the code is tagged "
                     "(design: Running and verification)")
        F.gate()
        res = A.run(load())
        res["design"] = {"file": str(C.DESIGN.relative_to(C.ROOT)), "stamp": F.stamp()}
        res["versions"] = versions()
        res["generated"] = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        C.RESULTS.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {C.RESULTS}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
