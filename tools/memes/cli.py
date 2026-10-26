"""Run the meme event study (docs/research/memes-design.md). The registered run needs real pageviews and so refuses
without --unblind; --verify-titles (existence only, no views) and --synthetic (made-up panel) need no flag.

    uv run --no-project --with pandas --with numpy --with matplotlib python -I tools/memes/cli.py --verify-titles
    uv run --no-project --with pandas --with numpy --with matplotlib python -I tools/memes/cli.py --synthetic
    nice -n 20 env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 uv run --no-project --with pandas --with numpy \\
        --with matplotlib python -I tools/memes/cli.py --download --unblind     # or --panel-csv <file> --unblind
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
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


def variant_plan(spec: M.EventSpec) -> list[tuple[str, dict]]:
    """The sensitivity runs of design §7, as (variant name, run_event keyword arguments)."""
    out: list[tuple[str, dict]] = [(f"window_{w[0]}_{w[1]}", {"event_window": w}) for w in C.SENSITIVITY_WINDOWS]
    out.append(("mean_index", {"how": "mean"}))
    out += [("same_season", {"season_days": C.SEASON_DAYS, "falsify": False}),
            ("exclusion_90", {"exclusion_days": C.STRICT_EXCLUSION_DAYS, "falsify": False}),
            ("pre_event_only", {"pre_only": True, "falsify": False})]
    w60 = {"event_window": C.SENSITIVITY_WINDOWS[1], "falsify": False}
    if spec is C.STONESTREET:
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


def falsification_power_pct() -> float | None:
    """Detection rate of the external falsification when all cast controls jump by 0.5, from the runs of §5."""
    if not POWER_JSON.exists():
        return None
    block = json.loads(POWER_JSON.read_text()).get(C.STONESTREET.name, {})
    for row in block.get("falsification_power", []):
        if row["jumping_controls"] == row["of"] and row["shock"] == 0.5:
            return 100 * row["external_falsification_p_below_0.05"]
    return None


def study(panel: pd.DataFrame, n_placebo: int | None = C.N_PLACEBO, seed: int = C.SEED,
          out: Path | None = None) -> tuple[dict, dict[str, pd.Series]]:
    """Null summary first (design §5), then primary runs, Holm over the confirmatory family, labels and the checks."""
    null = {}
    for spec in C.EVENTS:
        try:
            null[spec.name] = M.null_distribution(panel, spec, n_placebo=n_placebo, seed=seed)
        except M.EventDropped as err:
            null[spec.name] = {"dropped_event": str(err)}
        log.info("null %s: %s", spec.name, null[spec.name])
    if out is not None:
        R.write_summary(out / "placebo_null.json", null)
    results, specs, ars, events, dropped_events = [], [], {}, [], []
    for spec in C.EVENTS:
        try:
            res, ar = M.run_event(panel, spec, n_placebo=n_placebo, seed=seed, space_time=True)
        except M.EventDropped as err:
            dropped_events.append({"name": spec.name, "reason": str(err)})
            continue
        results.append(res)
        specs.append(spec)
        ars[spec.name] = ar
    holm = M.holm_adjust(M.confirmatory_family(results))
    for spec, res in zip(specs, results, strict=True):
        if res.name in holm:
            res.holm_p = holm[res.name]
            res.label = M.label_event(res.placebo_p, res.holm_p, res.car)
        events.append({**dataclasses.asdict(res), "cast_note": spec is C.STONESTREET})
    sens = []
    for spec in specs:
        sens += [_variant(panel, spec, name, n_placebo, seed, kw) for name, kw in variant_plan(spec)]
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


def pre_event_cutoff() -> str:
    """Day -4 of the earliest primary event, for the confounder figures and the monthly gap (design §3)."""
    first = min(pd.Timestamp(e.event_date) for e in C.EVENTS)
    return str((first + pd.Timedelta(days=C.EVENT_WINDOW[0] - 1)).date())


def screening_outputs(panel: pd.DataFrame, out: Path) -> None:
    cutoff = pre_event_cutoff()
    articles = list(dict.fromkeys([C.STONESTREET.target, *C.MF_CAST, C.KEVIN_JAMES.target, *C.KOQ_CAST]))
    pool_index = M.control_index(panel, C.REFERENCE_POOL)
    (out / "estimation_windows.svg").write_text(
        R.estimation_svg(panel, articles, pool_index, cutoff, [C.TIKTOK_BLOCK], C.START))
    rows = []
    for spec in C.EVENTS:
        gap = M.monthly_gap(np.log1p(panel[spec.target]), M.control_index(panel, spec.controls), cutoff, spec.blocked)
        rows += [{"event": spec.name, "month": str(m), "gap": g} for m, g in gap.items()]
    pd.DataFrame(rows).to_csv(out / "estimation_gap_by_month.csv", index=False)


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
    src.add_argument("--download", action="store_true", help="download the real panel (needs --unblind)")
    src.add_argument("--panel-csv", type=Path, help="rerun on a saved real panel (needs --unblind)")
    src.add_argument("--synthetic", action="store_true", help="dry run on a made-up panel")
    ap.add_argument("--unblind", action="store_true", help="allow reading real pageview numbers (design §0)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--n-placebo", type=int, default=None, help="draw this many pseudo dates instead of all")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.verify_titles:
        print(json.dumps(F.verify_titles(list(C.ARTICLES)), ensure_ascii=False, indent=1))
        return 0
    real = args.download or args.panel_csv is not None
    if real and not args.unblind:
        sys.exit("refusing to read real pageview numbers: the design is blinded until the code is frozen. "
                 "Pass --unblind to run the registered analysis.")
    if args.synthetic:
        panel, out = _synthetic_panel(), (args.out or C.OUT / "synthetic")
    elif args.download:
        F.verify_titles(list(C.ARTICLES))
        panel = F.fetch_panel(list(C.ARTICLES), C.START, C.END)
        digest = F.save_panel(panel, C.RAW)
        F.write_manifest(C.MANIFEST, digest, C.RAW, C.START, C.END)
        out = args.out or C.OUT
    else:
        panel, out = F.load_panel(args.panel_csv), (args.out or C.OUT)
    out.mkdir(parents=True, exist_ok=True)
    screening_outputs(panel, out)
    summary, ars = study(panel, args.n_placebo or C.N_PLACEBO, C.SEED, out)
    summary["meta"]["synthetic"] = bool(args.synthetic)
    summary["meta"]["versions"] = _versions()
    path = write_outputs(summary, ars, out)
    if real:
        R.write_summary(C.RESULTS, summary)
    print(json.dumps({"summary": str(path), "labels": {e["name"]: e["label"] for e in summary["events"]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
