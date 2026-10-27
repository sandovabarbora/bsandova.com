"""Run the meme event study (docs/research/memes-design.md) in two stages. Real pageviews need --unblind;
--verify-titles (existence only, no views) and --synthetic (a made-up panel, both stages in memory) need no flag.

Stage 1 (--null-stage) downloads the panel, screens it, computes the placebo null and the minimum detectable uplifts
from non-event dates only, and writes them with the screening outputs and a sha256 file into docs/research/. It computes
no CAR or AR at any event. The author commits those files and tags the commit `memes-null`. Stage 2 (--panel-csv)
refuses to run unless the committed files match their hashes, the panel matches the hash recorded in stage 1, and the tag
is on HEAD.

    P="--with pandas==3.0.6 --with numpy==2.5.3 --with matplotlib==3.11.2"
    uv run --no-project $P python -I tools/memes/cli.py --verify-titles
    uv run --no-project $P python -I tools/memes/cli.py --synthetic
    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project $P \\
        python -I tools/memes/cli.py --null-stage --unblind
    # commit docs/research/memes-placebo-null.json, memes-null-files.sha256 and the two screening files, tag memes-null
    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project $P \\
        python -I tools/memes/cli.py --panel-csv tools/data/memes/raw/pageviews.csv --unblind
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import logging
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import fetch as F
import model as M
import report as R
import synth as S

log = logging.getLogger("memes")
POWER_JSON = C.ROOT / "docs/research/memes-power.json"
WINDOW_KEYS = {(-3, 30): "window_-3_30", (-3, 14): "window_-3_14"}
PANEL_NAME = "pageviews.csv"


def variant_plan(spec: M.EventSpec) -> list[tuple[str, dict]]:
    """The sensitivity runs of design §7, as (variant name, run_event keyword arguments)."""
    out: list[tuple[str, dict]] = [(f"window_{w[0]}_{w[1]}", {"event_window": w}) for w in C.SENSITIVITY_WINDOWS]
    out.append(("mean_index", {"how": "mean"}))
    out += [("same_season", {"season_days": C.SEASON_DAYS, "falsify": False}),
            ("exclusion_90", {"exclusion_days": C.STRICT_EXCLUSION_DAYS, "falsify": False}),
            ("pre_event_only", {"pre_only": True, "falsify": False})]
    w60 = {"event_window": C.SENSITIVITY_WINDOWS[1], "falsify": False}
    if spec.name == C.STONESTREET.name:
        out += [("drop_Sofía_Vergara", {"drop": ("Sofía_Vergara",)}),
                (f"day0_{C.SENSITIVITY_DAY0[spec.name]}", {"event_date": C.SENSITIVITY_DAY0[spec.name]}),
                ("external_index", {"controls": spec.reference, "falsify": False}),
                ("external_index_window_-3_60", {**w60, "controls": spec.reference}),
                ("external_index_window_-3_60_without_Matt_LeBlanc",
                 {**w60, "controls": spec.reference, "drop": (C.LEBLANC,)})]
    else:
        out += [("koq_controls", {"controls": C.KOQ_CAST}),
                ("window_-3_60_without_Matt_LeBlanc", {**w60, "drop": (C.LEBLANC,)})]
    return out


def _variant(panel, spec, name, n_placebo, seed, kw) -> dict:
    try:
        res, _ = M.run_event(panel, spec, n_placebo=n_placebo, seed=seed, variant=name, **kw)
    except M.EventDropped as err:
        return {"name": spec.name, "variant": name, "dropped_event": str(err)}
    return dataclasses.asdict(res)


def falsification_power_pct() -> dict[str, float]:
    """Detection rate (percent) of the external falsification when all cast controls jump by 0.5, per event, from the
    runs of design §5 (Kevin James at a shared-factor share of 0.5)."""
    if not POWER_JSON.exists():
        return {}
    blocks = json.loads(POWER_JSON.read_text())
    out = {}
    for name, key in ((C.STONESTREET.name, C.STONESTREET.name), (C.KEVIN_JAMES.name, f"{C.KEVIN_JAMES.name} (shared 0.5)")):
        for row in blocks.get(key, {}).get("falsification_power", []):
            if row["jumping_controls"] == row["of"] and row["shock"] == 0.5:
                out[name] = 100 * row["external_falsification_p_below_0.05"]
    return out


# ---------------------------------------------------------------- stage 1: the null

def null_payload(panel: pd.DataFrame, n_placebo: int | None = C.N_PLACEBO, seed: int = C.SEED) -> dict:
    """Pool screening, Kevin James's baseline choice and the placebo null with minimum detectable uplifts, for both
    windows. Computes no CAR or AR at an event."""
    kept, dropped = M.pool_screen(panel, C.REFERENCE_POOL)
    events: dict = {}
    for spec in C.EVENTS:
        kw = {"n_placebo": n_placebo, "seed": seed}
        try:
            baseline = M.choose_baseline(panel, spec, **kw) if spec.second_regressor else {"chosen": "as registered"}
            second = baseline.get("second_regressor")
            events[spec.name] = {"baseline": baseline, "windows": {
                key: M.null_distribution(panel, spec, event_window=w, second=second, **kw)
                for w, key in WINDOW_KEYS.items()}}
        except M.EventDropped as err:
            events[spec.name] = {"dropped_event": str(err)}
        log.info("null %s: %s", spec.name, events[spec.name])
    return {"stage": "null (no CAR or AR at any event)", "date": str(dt.date.today()), "seed": seed,
            "n_placebo": n_placebo, "decay_days": M.DECAY, "uninformative_threshold_pct": M.UNINFORMATIVE_PCT,
            "pool_kept": len(kept), "pool_dropped": dropped, "events": events}


def pre_event_cutoff() -> str:
    """Day -4 of the earliest primary event, for the confounder figure and the monthly gap (design §3)."""
    first = min(pd.Timestamp(e.event_date) for e in C.EVENTS)
    return str((first + pd.Timedelta(days=C.EVENT_WINDOW[0] - 1)).date())


def screening_outputs(panel: pd.DataFrame, svg_path: Path, gap_path: Path) -> None:
    cutoff = pre_event_cutoff()
    articles = list(dict.fromkeys([C.STONESTREET.target, *C.MF_CAST, C.KEVIN_JAMES.target, *C.KOQ_CAST]))
    pool_kept, _ = M.pool_screen(panel, C.REFERENCE_POOL)
    pool_index = M.control_index(panel, pool_kept)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(R.estimation_svg(panel, articles, pool_index, cutoff, [C.TIKTOK_BLOCK], C.START))
    rows = []
    for spec in C.EVENTS:
        base = pool_kept if spec.controls == C.REFERENCE_POOL else spec.controls
        gap = M.monthly_gap(np.log1p(panel[spec.target]), M.control_index(panel, base), cutoff, spec.blocked)
        rows += [{"event": spec.name, "month": str(m), "gap": g} for m, g in gap.items()]
    pd.DataFrame(rows).to_csv(gap_path, index=False)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_null_stage(panel: pd.DataFrame, panel_path: Path, n_placebo: int | None = C.N_PLACEBO) -> dict:
    """Stage 1: write the null file, the screening outputs and the sha256 file into docs/research/."""
    screening_outputs(panel, C.NULL_SVG, C.NULL_GAP)
    payload = null_payload(panel, n_placebo)
    payload["panel_sha256"] = _sha(panel_path)
    R.write_summary(C.NULL_JSON, payload)
    lines = [f"{_sha(p)}  {p.name}" for p in (C.NULL_JSON, C.NULL_SVG, C.NULL_GAP)]
    lines.append(f"{payload['panel_sha256']}  {PANEL_NAME}  (the panel, gitignored)")
    C.NULL_SHA.write_text("\n".join(lines) + "\n")
    return payload


# ---------------------------------------------------------------- the gate of stage 2

def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(C.ROOT), *args], capture_output=True, text=True, check=True).stdout


def _git_ok(*args: str) -> bool:
    return subprocess.run(["git", "-C", str(C.ROOT), *args], capture_output=True, check=False).returncode == 0


DESIGN = "docs/research/memes-design.md"


def check_code_frozen() -> None:
    """Both stages refuse unless the code is the tagged one: the tag `memes-code` exists, tools/memes at HEAD equals it,
    and neither tools/memes nor the design text has uncommitted changes."""
    if not _git_ok("rev-parse", "--verify", "--quiet", f"refs/tags/{C.CODE_TAG}"):
        sys.exit(f"refusing to run: the code is not frozen, the tag {C.CODE_TAG} does not exist")
    if not _git_ok("diff", "--quiet", C.CODE_TAG, "HEAD", "--", "tools/memes"):
        sys.exit(f"refusing to run: tools/memes at HEAD differs from the tag {C.CODE_TAG}")
    if _git("status", "--porcelain", "--", "tools/memes", DESIGN).strip():
        sys.exit("refusing to run: tools/memes or the design text has uncommitted changes")


def check_null_tag_free() -> None:
    if _git_ok("rev-parse", "--verify", "--quiet", f"refs/tags/{C.NULL_TAG}"):
        sys.exit(f"refusing --null-stage: the tag {C.NULL_TAG} already exists, stage 1 is run once")


def verify_null_stage(panel_path: Path) -> dict:
    """Stage 2 refuses to run unless the committed null files match their recorded hashes, the panel matches the hash
    recorded in stage 1, the files are committed and unmodified, and the tag `memes-null` is on HEAD."""
    files = (C.NULL_JSON, C.NULL_SVG, C.NULL_GAP, C.NULL_SHA)
    absent = [p.name for p in files if not p.exists()]
    if absent:
        sys.exit(f"refusing to estimate: stage 1 has not been run, missing {absent} (run --null-stage first)")
    recorded = {ln.split()[1]: ln.split()[0] for ln in C.NULL_SHA.read_text().splitlines() if ln.strip()}
    for p in (C.NULL_JSON, C.NULL_SVG, C.NULL_GAP):
        if recorded.get(p.name) != _sha(p):
            sys.exit(f"refusing to estimate: {p.name} does not match the hash recorded in {C.NULL_SHA.name}")
    if not panel_path.exists() or recorded.get(PANEL_NAME) != _sha(panel_path):
        sys.exit("refusing to estimate: the panel file does not match the hash recorded in stage 1")
    if _git("status", "--porcelain", "--", *[str(p) for p in files]).strip():
        sys.exit("refusing to estimate: the stage 1 files are not committed or have changed since")
    if C.NULL_TAG not in _git("tag", "--points-at", "HEAD").split():
        sys.exit(f"refusing to estimate: the tag {C.NULL_TAG} is not on HEAD (commit the stage 1 files, then tag)")
    check_code_frozen()
    if not _git_ok("merge-base", "--is-ancestor", C.CODE_TAG, C.NULL_TAG):
        sys.exit(f"refusing to estimate: {C.CODE_TAG} is not an ancestor of {C.NULL_TAG}, stage 1 ran on other code")
    null = json.loads(C.NULL_JSON.read_text())
    if null.get("n_placebo") is not None or null.get("seed") != C.SEED:
        sys.exit(f"refusing to estimate: the null file must use every admissible date (n_placebo null) and seed {C.SEED}, "
                 f"not n_placebo={null.get('n_placebo')} and seed={null.get('seed')}")
    return null


# ---------------------------------------------------------------- stage 2: the estimates

def _recheck_null(panel: pd.DataFrame, spec: M.EventSpec, info: dict, res: M.EventResult, null: dict) -> None:
    """Recompute what stage 1 stored, exactly as stage 1 did, and stop on any difference: both windows' nulls (every
    field, including the number of placebo dates), the null the run itself used, and the baseline choice."""
    kw = {"n_placebo": null["n_placebo"], "seed": null["seed"]}
    second = info.get("baseline", {}).get("second_regressor")
    stage1 = info["windows"]["window_-3_30"]
    problems = []
    if not (np.isclose(res.mdu80_q975_pct, stage1["mdu80_q975_pct"], rtol=1e-9)
            and np.isclose(res.null_sd, stage1["null_sd"], rtol=1e-9)
            and np.isclose(res.null_q20, stage1["null_q20"], rtol=1e-9)):
        problems.append("the null the estimate used")
    for w, key in WINDOW_KEYS.items():
        now = M.null_distribution(panel, spec, event_window=w, second=second, **kw)
        old = info["windows"][key]
        if now.keys() != old.keys() or not all(np.isclose(now[k], old[k], rtol=1e-9, atol=0) for k in now):
            problems.append(f"the null of window {w}")
    if spec.second_regressor:
        base = M.choose_baseline(panel, spec, **kw)
        if (base["chosen"], base["second_regressor"]) != (info["baseline"]["chosen"], info["baseline"]["second_regressor"]):
            problems.append("the baseline choice")
    if problems:
        sys.exit(f"refusing to estimate: {', '.join(problems)} of {spec.name} differ from stage 1 (data or code changed)")


def study(panel: pd.DataFrame, null: dict, n_placebo: int | None = C.N_PLACEBO, seed: int = C.SEED
          ) -> tuple[dict, dict[str, pd.Series]]:
    """Primary runs, Holm over the confirmatory family, labels from H1 and the null file, and the checks."""
    _, dropped_now = M.pool_screen(panel, C.REFERENCE_POOL)
    if sorted(dropped_now) != sorted(null["pool_dropped"]):
        sys.exit("refusing to estimate: the pool actors dropped now differ from those of stage 1")
    results, specs, ars, events, dropped_events, seconds = [], [], {}, [], [], {}
    for spec in C.EVENTS:
        info = null["events"].get(spec.name, {})
        second = info.get("baseline", {}).get("second_regressor")
        try:
            res, ar = M.run_event(panel, spec, n_placebo=n_placebo, seed=seed, space_time=True, second=second)
        except M.EventDropped as err:
            dropped_events.append({"name": spec.name, "reason": str(err)})
            continue
        _recheck_null(panel, spec, info, res, null)
        results.append(res)
        specs.append(spec)
        seconds[spec.name] = second
        ars[spec.name] = ar
    holm = M.holm_adjust(M.confirmatory_family(results))
    for spec, res in zip(specs, results, strict=True):
        if res.name in holm:
            res.holm_p = holm[res.name]
            res.label = M.label_event(res.placebo_p, res.holm_p, res.car, res.mdu80_q975_pct)
        events.append({**dataclasses.asdict(res), "cast_note": spec.falsification})
    sens = []
    for spec in specs:
        for name, kw in variant_plan(spec):
            if seconds[spec.name] and "controls" not in kw:
                kw = {**kw, "second": seconds[spec.name]}
            sens.append(_variant(panel, spec, name, n_placebo, seed, kw))
    for spec in C.SENSITIVITY_EVENTS:
        sens.append(_variant(panel, spec, "tiktok_prewave", n_placebo, seed, {}))
    hl = {e["name"]: (e["half_life_days"], e["half_life_status"]) for e in events}
    stone, kevin = hl.get(C.STONESTREET.name), hl.get(C.KEVIN_JAMES.name)
    both = stone is not None and kevin is not None and stone[0] is not None and kevin[0] is not None
    day0 = next((s for s in sens if str(s.get("variant", "")).startswith("day0_")), None)
    h2 = {"half_life": hl, "difference_days_stonestreet_minus_kevin_james": stone[0] - kevin[0] if both else None,
          "ordering": ("Stonestreet minus Kevin James in days, see the difference" if both
                       else "no ordering claim: a half-life is censored, has no positive peak, or is missing"),
          "stonestreet_from_6_oct": None if day0 is None or "dropped_event" in day0 else {
              "half_life_days": day0["half_life_days"], "status": day0["half_life_status"],
              "peak_date": day0["peak_date"], "placebo_p": day0["placebo_p"]}}
    meta = {"windows": {"estimation": C.EST_WINDOW, "event": C.EVENT_WINDOW}, "n_placebo": n_placebo, "seed": seed,
            "data_range": [C.START, C.END], "holm_family": sorted(holm), "null": null,
            "falsification_power_pct": falsification_power_pct()}
    return {"meta": meta, "events": events, "dropped_events": dropped_events, "h2": h2, "sensitivity": sens}, ars


def write_outputs(summary: dict, ars: dict[str, pd.Series], out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    for spec in C.EVENTS:
        if spec.name in ars:
            ars[spec.name].to_csv(out / f"ar_{spec.target}.csv", header=["ar"], index_label="date")
    dates = {e["name"]: e["event_date"] for e in summary["events"]}
    svg = R.ar_svg({n: ars[n] for n in dates}, dates)
    (out / "abnormal_attention.svg").write_text(svg)
    (out / "index.html").write_text(R.render_html(summary, svg))
    R.write_summary(out / "summary.json", summary)
    return out / "summary.json"


def _synthetic_panel() -> pd.DataFrame:
    groups = {e.target: e.cast for e in C.EVENTS}
    groups[C.REFERENCE_POOL[0]] = C.REFERENCE_POOL[1:]
    bumps = [("Eric_Stonestreet", "2023-09-27", 0.5, 5.0), ("Kevin_James", "2023-09-21", 0.3, 5.0),
             ("Eric_Stonestreet", "2023-06-13", 0.8, 3.0)]
    return S.synthetic_panel(1, groups, C.START, C.END, bumps, common_sd=0.1)


def _versions() -> dict[str, str]:
    import importlib.metadata as md
    return {"python": sys.version.split()[0], "numpy": md.version("numpy"), "pandas": md.version("pandas")}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--verify-titles", action="store_true", help="check that the titles exist, no pageviews")
    src.add_argument("--null-stage", action="store_true",
                     help="stage 1: download, screen, write the placebo null (needs --unblind)")
    src.add_argument("--panel-csv", type=Path, help="stage 2: estimate on the saved panel (needs --unblind)")
    src.add_argument("--synthetic", action="store_true", help="dry run on a made-up panel, both stages in memory")
    ap.add_argument("--unblind", action="store_true", help="allow reading real pageview numbers (design §0)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--n-placebo", type=int, default=None, help="draw this many pseudo dates instead of all")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    n_placebo = args.n_placebo or C.N_PLACEBO
    if args.n_placebo is not None and not args.synthetic:
        sys.exit("refusing --n-placebo on real data: the registered run uses every admissible placebo date")

    if args.verify_titles:
        try:
            print(json.dumps(F.verify_titles(list(C.ARTICLES)), ensure_ascii=False, indent=1))
        except F.ArticleNotFound as err:
            sys.exit(str(err))
        return 0
    if (args.null_stage or args.panel_csv is not None) and not args.unblind:
        sys.exit("refusing to read real pageview numbers: the design is blinded until the code is frozen. "
                 "Pass --unblind to run the registered analysis.")
    if args.null_stage:
        check_code_frozen()
        check_null_tag_free()
        try:
            F.verify_titles(list(C.ARTICLES))
        except F.ArticleNotFound as err:
            sys.exit(str(err))
        panel = F.fetch_panel(list(C.ARTICLES), C.START, C.END)
        digest = F.save_panel(panel, C.RAW)
        F.write_manifest(C.MANIFEST, digest, C.RAW, C.START, C.END)
        payload = run_null_stage(panel, C.RAW, n_placebo)
        print(json.dumps({"null_file": str(C.NULL_JSON), "panel_sha256": payload["panel_sha256"],
                          "next": f"commit the files named in {C.NULL_SHA.name}, tag {C.NULL_TAG}, run --panel-csv"}))
        return 0
    if args.synthetic:
        panel, out = _synthetic_panel(), (args.out or C.OUT / "synthetic")
        null = null_payload(panel, n_placebo)
        out.mkdir(parents=True, exist_ok=True)
        R.write_summary(out / "placebo_null.json", null)
        screening_outputs(panel, out / "estimation_windows.svg", out / "estimation_gap_by_month.csv")
    else:
        null = verify_null_stage(args.panel_csv)
        panel, out = F.load_panel(args.panel_csv), (args.out or C.OUT)
        out.mkdir(parents=True, exist_ok=True)
    summary, ars = study(panel, null, n_placebo, C.SEED)
    summary["meta"]["synthetic"] = bool(args.synthetic)
    summary["meta"]["versions"] = _versions()
    path = write_outputs(summary, ars, out)
    if not args.synthetic:
        R.write_summary(C.RESULTS, summary)
    print(json.dumps({"summary": str(path), "labels": {e["name"]: e["label"] for e in summary["events"]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
