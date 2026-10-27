"""Run the Pitch Perfect joke-target study (docs/research/pitch-design.md) stage by stage. Every stage that reads a
real subtitle file needs --unblind and the frozen code; --synthetic runs everything on invented subtitles with a
scripted model and needs neither.

    P="--with numpy==2.5.3"
    uv run --no-project $P python -I tools/pitch/cli.py --synthetic
    # after the tag pitch-code, with tools/data/pitch/raw/pp1.srt and pp2.srt in place:
    uv run --no-project $P python -I tools/pitch/cli.py --hash-files --unblind     # commit pitch-files.sha256
    uv run --no-project $P python -I tools/pitch/cli.py --italic-runs --unblind    # only if a file has no ♪, ♫ or #
    uv run --no-project $P python -I tools/pitch/cli.py --draw-sample --unblind    # code the form offline
    uv run --no-project $P python -I tools/pitch/cli.py --hash-sample --unblind    # commit the manifest (and marks)
    uv run --no-project $P --with anthropic==2.3.0 python -I tools/pitch/cli.py --run 1 --unblind
    uv run --no-project $P --with anthropic==2.3.0 python -I tools/pitch/cli.py --run 2 --unblind
    uv run --no-project $P python -I tools/pitch/cli.py --analyse --unblind
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as A
import client as CL
import coding as K
import config as C
import files as F
import passes as P
import sample as SA
import subtitles as S
import synth as SY

log = logging.getLogger("pitch")
TOOL = "tools/pitch"
DESIGN = "docs/research/pitch-design.md"


def raw_path(film: str) -> Path:
    return C.RAW / f"{film}.srt"


# ---------------------------------------------------------------- git and the gates

def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(C.ROOT), *args], capture_output=True, text=True, check=True).stdout


def _git_ok(*args: str) -> bool:
    return subprocess.run(["git", "-C", str(C.ROOT), *args], capture_output=True, check=False).returncode == 0


def _rel(path: Path) -> str:
    return str(path.relative_to(C.ROOT))


def check_code_frozen() -> None:
    """The tag `pitch-code` exists and is an ancestor of HEAD, tools/pitch at HEAD equals it, and neither tools/pitch
    nor the design text has uncommitted changes (design §3.3)."""
    if not _git_ok("rev-parse", "--verify", "--quiet", f"refs/tags/{C.CODE_TAG}"):
        sys.exit(f"refusing to run: the code is not frozen, the tag {C.CODE_TAG} does not exist")
    if not _git_ok("merge-base", "--is-ancestor", C.CODE_TAG, "HEAD"):
        sys.exit(f"refusing to run: the tag {C.CODE_TAG} is not an ancestor of HEAD")
    if not _git_ok("diff", "--quiet", C.CODE_TAG, "HEAD", "--", TOOL):
        sys.exit(f"refusing to run: {TOOL} at HEAD differs from the tag {C.CODE_TAG}")
    if _git("status", "--porcelain", "--", TOOL, DESIGN).strip():
        sys.exit(f"refusing to run: {TOOL} or the design text has uncommitted changes")


def check_clean_tree() -> None:
    """No tracked file differs from HEAD anywhere, and nothing untracked sits in tools/pitch or docs/research."""
    if _git("status", "--porcelain", "--untracked-files=no").strip():
        sys.exit("refusing to run: the working tree has uncommitted changes")
    if _git("status", "--porcelain", "--untracked-files=all", "--", TOOL, "docs/research").strip():
        sys.exit("refusing to run: untracked files in tools/pitch or docs/research")


def _committed(path: Path) -> bool:
    return (_git_ok("ls-files", "--error-unmatch", "--", _rel(path))
            and not _git("status", "--porcelain", "--", _rel(path)).strip())


def verify_raw() -> dict[str, str]:
    """Both subtitle files exist and match the hashes in the manifest (design §2.1). Returns the encodings."""
    manifest = F.read_manifest()
    enc = {}
    for f in C.FILMS:
        p = raw_path(f)
        if not p.exists():
            sys.exit(f"refusing to run: {p.name} is missing from {_rel(C.RAW)}")
        if manifest.get(p.name, {}).get("sha256") != F.sha256(p):
            sys.exit(f"refusing to run: {p.name} does not match the hash in {C.MANIFEST.name} (run --hash-files once)")
        enc[f] = F.read_srt(p)[1]
    return enc


def model_output_exists() -> bool:
    return any(p.is_file() for r in C.RUNS for p in (C.OUT / f"run{r}").rglob("*")) if C.OUT.exists() else False


def check_human_hashed() -> None:
    entry = F.read_manifest().get(C.HUMAN.name)
    if entry is None:
        sys.exit(f"refusing to run: the hash of {C.HUMAN.name} is not in {C.MANIFEST.name} (run --hash-sample)")
    if not C.HUMAN.exists():
        sys.exit(f"refusing to run: {C.HUMAN.name} is missing")
    if entry["sha256"] != F.sha256(C.HUMAN):
        sys.exit(f"refusing to run: {C.HUMAN.name} does not match its committed hash; a code may not change after the hash")


def fallback_films(films: dict | None = None) -> list[str]:
    """Films whose file has no ♪, ♫ or # marker and has italic runs for the author to mark."""
    out = []
    for f in C.FILMS:
        raw = films[f] if films else S.parse_srt(F.read_srt(raw_path(f))[0])
        if not S.has_lyric_markers(raw) and S.italic_runs(raw):
            out.append(f)
    return out


def check_song_marks_committed() -> None:
    if not fallback_films():
        return
    entry = F.read_manifest().get(C.SONG_MARKS.name)
    if not C.SONG_MARKS.exists() or entry is None or entry["sha256"] != F.sha256(C.SONG_MARKS):
        sys.exit("refusing to run: the lyric fallback applies and the author's song marks are not committed with "
                 f"their hash in {C.MANIFEST.name}")
    if not _committed(C.SONG_MARKS):
        sys.exit(f"refusing to run: {C.SONG_MARKS.name} is not committed")


def gate_model_run() -> None:
    """The model may run on real subtitles only after the freeze and the committed hash of the blind sample (§3)."""
    check_clean_tree()
    check_code_frozen()
    if not _committed(C.MANIFEST):
        sys.exit(f"refusing to run: {C.MANIFEST.name} is not committed")
    verify_raw()
    check_human_hashed()
    check_song_marks_committed()


# ---------------------------------------------------------------- loading the films

def load_films(raw_texts: dict[str, str], marks: dict | None) -> dict[str, A.Film]:
    films = {}
    for f in C.FILMS:
        raw = S.parse_srt(raw_texts[f])
        try:
            kept, report = S.clean(raw, (marks or {}).get(f))
        except S.NeedsSongMarks as err:
            sys.exit(f"refusing to run: {f}: {err} (run --italic-runs and fill {C.SONG_MARKS.name})")
        films[f] = A.Film(tuple(raw), tuple(kept), report)
    return films


def load_real_films() -> dict[str, A.Film]:
    texts = {}
    for f in C.FILMS:
        try:
            texts[f] = F.read_srt(raw_path(f))[0]
        except OSError as err:
            sys.exit(f"refusing to run: {err}")
    try:
        return load_films(texts, F.load_song_marks())
    except S.MalformedSrt as err:
        sys.exit(f"stopping: malformed subtitle file: {err}")


# ---------------------------------------------------------------- stages

def stage_hash_files() -> dict:
    check_code_frozen()
    manifest = F.read_manifest()
    out = {}
    for f in C.FILMS:
        p = raw_path(f)
        if not p.exists():
            sys.exit(f"refusing to run: {p.name} is missing from {_rel(C.RAW)}")
        sha = F.sha256(p)
        if p.name in manifest and manifest[p.name]["sha256"] != sha:
            sys.exit(f"refusing to run: {p.name} was hashed before with another hash; files are never replaced")
        text, enc = F.read_srt(p)
        try:
            sdh = any(S.SOUND.search(c.text) for c in S.parse_srt(text))
        except S.MalformedSrt as err:
            sys.exit(f"stopping: malformed subtitle file {p.name}: {err}")
        F.write_manifest_entry(p.name, sha, F.raw_note(p, enc, sdh))
        out[f] = {"sha256": sha, "encoding": enc, "sdh": sdh}
    return out


def stage_italic_runs() -> dict:
    check_code_frozen()
    verify_raw()
    runs = {}
    for f in C.FILMS:
        raw = S.parse_srt(F.read_srt(raw_path(f))[0])
        runs[f] = [] if S.has_lyric_markers(raw) else S.italic_runs(raw)
    F.write_json(C.ITALIC_RUNS, runs)
    if any(runs.values()) and not C.SONG_MARKS.exists():
        F.write_json(C.SONG_MARKS, {f: [{"first_cue": r["first_cue"], "last_cue": r["last_cue"], "start": r["start"],
                                         "end": r["end"], "mark": None} for r in rs] for f, rs in runs.items()})
    return {f: len(r) for f, r in runs.items()}


def stage_draw_sample() -> dict:
    check_code_frozen()
    verify_raw()
    if model_output_exists():
        sys.exit("refusing to draw: model output exists already; the sample is coded before any model output")
    if C.SAMPLE.exists() or C.FORM.exists():
        sys.exit("refusing to draw: the sample was drawn already; it is drawn once")
    films = load_real_films()
    smp = SA.draw({f: films[f].kept for f in C.FILMS})
    scenes = {f: S.build_scenes(films[f].kept) for f in C.FILMS}
    F.write_json(C.SAMPLE, smp)
    C.FORM.write_text(SA.render_form(SA.form_items(smp, scenes)), encoding="utf-8")
    return {"sample": _rel(C.SAMPLE), "form": _rel(C.FORM), "cues": len(smp["items"])}


def stage_hash_sample() -> dict:
    check_code_frozen()
    verify_raw()
    if model_output_exists():
        sys.exit("refusing to hash: model output exists already")
    if not (C.SAMPLE.exists() and C.HUMAN.exists()):
        sys.exit(f"refusing to hash: {C.SAMPLE.name} or {C.HUMAN.name} is missing")
    try:
        codes = SA.check_codes(F.read_json(C.HUMAN), F.read_json(C.SAMPLE))
    except (ValueError, TypeError) as err:
        sys.exit(f"refusing to hash: {err}")
    sha = F.sha256(C.HUMAN)
    old = F.read_manifest().get(C.HUMAN.name)
    if old and old["sha256"] != sha:
        sys.exit("refusing to hash: the codes were hashed before and have changed since; a code may not change")
    skipped = sum(c["joke"] == C.SKIP for c in codes)
    F.write_manifest_entry(C.HUMAN.name, sha, f"the blind sample, {len(codes)} cues, {skipped} skipped; "
                                                "committed after the model run")
    out = {"validation_human_sha256": sha, "skipped": skipped}
    if fallback_films():
        load_real_films()                                  # stops unless the marks cover exactly the listed runs
        F.write_manifest_entry(C.SONG_MARKS.name, F.sha256(C.SONG_MARKS), "the author's song marks (design §2.2)")
        out["song_marks_sha256"] = F.sha256(C.SONG_MARKS)
    return out


def run_settings(prompts: dict, sdk_version: str | None) -> dict:
    return {"model": C.MODEL, "temperature": C.TEMPERATURE, "max_tokens": C.MAX_TOKENS, "retries": C.RETRIES,
            "max_fail_share": C.MAX_FAIL_SHARE, "prompt_sha256": K.prompt_hashes(prompts), "sdk": sdk_version}


def run_model(films: dict[str, A.Film], client, run: int, out: Path, sdk_version: str | None = None) -> dict:
    prompts = F.load_prompts()
    folder = out / f"run{run}"
    F.write_json(folder / "settings.json", run_settings(prompts, sdk_version))
    cache, call_log = CL.Cache(folder / "cache"), CL.CallLog(folder / "calls.jsonl")
    result = {}
    for f in C.FILMS:
        result[f] = P.run_film(f, S.build_scenes(films[f].kept), prompts, client, cache, call_log, run)
        F.write_json(folder / f"{f}.json", result[f])
    return result


def stage_run(run: int) -> dict:
    gate_model_run()
    films = load_real_films()
    try:
        model = CL.AnthropicClient()
    except CL.CallFailed as err:
        sys.exit(f"refusing to run: {err}")
    try:
        res = run_model(films, model, run, C.OUT, model.sdk_version)
    except P.RunStopped as err:
        sys.exit(f"stopping: {err}")
    return {f: {"jokes": len(r["jokes"]), "failed_scenes": len(r["failed_scenes"]),
                "failed_jokes": len(r["failed_jokes"])} for f, r in res.items()}


def _versions(sdk: str | None) -> dict:
    import numpy as np
    return {"python": sys.version.split()[0], "numpy": np.__version__, "anthropic": sdk}


def load_runs(out: Path) -> dict[int, dict]:
    runs = {}
    for r in C.RUNS:
        missing = [f for f in C.FILMS if not (out / f"run{r}" / f"{f}.json").exists()]
        if missing:
            sys.exit(f"refusing to analyse: run {r} is incomplete, missing {missing}")
        runs[r] = {f: F.read_json(out / f"run{r}" / f"{f}.json") for f in C.FILMS}
    return runs


def stage_analyse() -> dict:
    check_code_frozen()
    verify_raw()
    check_human_hashed()
    check_song_marks_committed()
    films = load_real_films()
    runs = load_runs(C.OUT)
    human = SA.check_codes(F.read_json(C.HUMAN), F.read_json(C.SAMPLE))
    res = A.study(films, runs, human)
    settings = [F.read_json(C.OUT / f"run{r}" / "settings.json") for r in C.RUNS]
    manifest = F.read_manifest()
    res["meta"] = {
        "versions": _versions(settings[0].get("sdk")), "run_settings": settings,
        "model_versions": {r: {f: runs[r][f]["model_versions"] for f in C.FILMS} for r in C.RUNS},
        "tags": {t: _git("rev-list", "-n", "1", t).strip() for t in (C.DESIGN_TAG, C.CODE_TAG)},
        "file_hashes": {k: v["sha256"] for k, v in manifest.items()},
    }
    F.write_json(C.RESULTS, res)
    return {"results": _rel(C.RESULTS), "status": res["status"],
            "readings": {q: v.get("label") if "label" in v else {f: x["label"] for f, x in v.items()}
                         for q, v in res["readings"].items() if q != "Q2_difference"}}


# ---------------------------------------------------------------- the dry run

def synthetic(out: Path, reps: int = C.BOOT_REPS) -> dict:
    """Both runs, the validation and the results on invented subtitle files with a scripted model."""
    texts = {"pp1": SY.srt_file(1), "pp2": SY.srt_file(2)}
    films = load_films(texts, None)
    runs = {r: run_model(films, SY.ScriptedModel(noise_seed=None if r == 1 else 7), r, out) for r in C.RUNS}
    smp = SA.draw({f: films[f].kept for f in C.FILMS})
    by_cue = {(f, c.index): c.text for f in C.FILMS for c in films[f].kept}
    human = []
    for item in smp["items"]:
        text = by_cue[(item["film"], item["cue"])]
        if "JOKE" in text or "ALLUSION" in text:
            human.append({"film": item["film"], "cue": item["cue"], "joke": True, **SY.code_from_text(text)})
        else:
            human.append({"film": item["film"], "cue": item["cue"], "joke": False})
    res = A.study(films, runs, human, reps=reps)
    res["meta"] = {"synthetic": True, "versions": _versions(None)}
    F.write_json(out / "results.json", res)
    F.write_json(out / "sample.json", smp)
    (out / "form.html").write_text(SA.render_form(SA.form_items(smp, {f: S.build_scenes(films[f].kept)
                                                                       for f in C.FILMS})), encoding="utf-8")
    return res


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    stage = ap.add_mutually_exclusive_group(required=True)
    stage.add_argument("--synthetic", action="store_true", help="dry run on invented subtitles, scripted model")
    stage.add_argument("--hash-files", action="store_true", help="hash both subtitle files into the manifest")
    stage.add_argument("--italic-runs", action="store_true", help="list italic runs for the lyric fallback")
    stage.add_argument("--draw-sample", action="store_true", help="draw the blind sample and write the form")
    stage.add_argument("--hash-sample", action="store_true", help="hash the author's codes into the manifest")
    stage.add_argument("--run", type=int, choices=C.RUNS, help="model run 1 (primary) or 2 (self-agreement)")
    stage.add_argument("--analyse", action="store_true", help="estimate and write docs/research/pitch-results.json")
    ap.add_argument("--unblind", action="store_true", help="allow reading the real subtitle files (design §3)")
    ap.add_argument("--out", type=Path, default=None, help="output folder of --synthetic")
    ap.add_argument("--reps", type=int, default=None, help="bootstrap replicates of --synthetic only")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.reps is not None and not args.synthetic:
        sys.exit("refusing --reps on real data: the registered run uses 10 000 replicates")
    if args.synthetic:
        out = args.out or C.OUT / "synthetic"
        res = synthetic(out, args.reps or C.BOOT_REPS)
        print(json.dumps({"results": str(out / "results.json"), "status": res["status"]}))
        return 0
    if not args.unblind:
        sys.exit("refusing to read the real subtitle files: the study is blinded until the code is frozen. "
                 "Pass --unblind to run a registered stage.")
    if args.hash_files:
        result = stage_hash_files()
    elif args.italic_runs:
        result = stage_italic_runs()
    elif args.draw_sample:
        result = stage_draw_sample()
    elif args.hash_sample:
        result = stage_hash_sample()
    elif args.run is not None:
        result = stage_run(args.run)
    else:
        result = stage_analyse()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
