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

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import fetch as F
import model as M
import report as R
import synth as S

log = logging.getLogger("memes")
DROP_IN_SENSITIVITY = {"Stonestreet (Cam)": ("Sofía_Vergara",)}


def _variant(panel, spec, name, n_placebo, seed, **kw):
    res, _ = M.run_event(panel, spec, n_placebo=n_placebo, seed=seed, variant=name, **kw)
    return dataclasses.asdict(res)


def study(panel: pd.DataFrame, n_placebo: int = C.N_PLACEBO, seed: int = C.SEED) -> tuple[dict, dict[str, pd.Series]]:
    """Primary runs, Holm over the confirmatory family, labels, then the sensitivity runs (design §4, §6, §7)."""
    results, ars = [], {}
    for spec in C.EVENTS:
        res, ar = M.run_event(panel, spec, n_placebo=n_placebo, seed=seed)
        results.append(res)
        ars[spec.name] = ar
    holm = M.holm_adjust(M.confirmatory_family(results))
    events = []
    for spec, res in zip(C.EVENTS, results, strict=True):
        if res.name in holm:
            res.holm_p = holm[res.name]
            res.label = M.label_event(res.placebo_p, res.holm_p, res.car, res.falsification_p, spec.gate_on_falsification)
        events.append({**dataclasses.asdict(res), "gates_label": spec.gate_on_falsification})
    sens = []
    for spec in C.EVENTS:
        for w in C.SENSITIVITY_WINDOWS:
            sens.append(_variant(panel, spec, f"window_{w[0]}_{w[1]}", n_placebo, seed, event_window=w))
        sens.append(_variant(panel, spec, "mean_index", n_placebo, seed, how="mean"))
        if spec.name in C.SENSITIVITY_DAY0:
            sens.append(_variant(panel, spec, "day0_" + C.SENSITIVITY_DAY0[spec.name], n_placebo, seed,
                                 event_date=C.SENSITIVITY_DAY0[spec.name]))
        if spec is C.STONESTREET:
            sens.append(_variant(panel, spec, "external_index", n_placebo, seed, controls=spec.reference,
                                 falsify=False))
        if spec.name in DROP_IN_SENSITIVITY:
            drop = DROP_IN_SENSITIVITY[spec.name]
            sens.append(_variant(panel, spec, "drop_" + "_".join(drop), n_placebo, seed, drop=drop))
    for spec in C.SENSITIVITY_EVENTS:
        sens.append(_variant(panel, spec, "tiktok_prewave", n_placebo, seed))
    hl = {e["name"]: e["half_life_days"] for e in events}
    day0 = next((s for s in sens if s["variant"].startswith("day0_")), None)
    values = list(hl.values())
    h2 = {"half_life_days": hl, "difference_days": values[0] - values[1] if None not in values else None,
          "stonestreet_from_6_oct": None if day0 is None else {"half_life_days": day0["half_life_days"],
                                                              "peak_date": day0["peak_date"]}}
    meta = {"windows": {"estimation": C.EST_WINDOW, "event": C.EVENT_WINDOW}, "n_placebo": n_placebo, "seed": seed,
            "data_range": [C.START, C.END], "holm_family": sorted(holm)}
    return {"meta": meta, "events": events, "h2": h2, "sensitivity": sens}, ars


def write_outputs(summary: dict, ars: dict[str, pd.Series], panel: pd.DataFrame, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    for spec in C.EVENTS:
        ars[spec.name].to_csv(out / f"ar_{spec.target}.csv", header=["ar"], index_label="date")
    dates = {e["name"]: e["event_date"] for e in summary["events"]}
    svg = R.ar_svg(ars, dates)
    (out / "abnormal_attention.svg").write_text(svg)
    cutoffs = {s.name: str((pd.Timestamp(dates[s.name]) + pd.Timedelta(days=C.EVENT_WINDOW[0] - 1)).date())
               for s in C.EVENTS}
    (out / "estimation_windows.svg").write_text(R.estimation_svg(panel, cutoffs, C.START))
    (out / "index.html").write_text(R.render_html(summary, svg))
    R.write_summary(out / "summary.json", summary)
    return out / "summary.json"


def screen_panel(panel: pd.DataFrame, max_zero_share: float = 0.01) -> dict[str, float]:
    """Design §3.2: an actor article with zeros on more than 1 % of days means holes in the data, not no readers."""
    zeros = (panel == 0).mean()
    bad = zeros[zeros > max_zero_share]
    if not bad.empty:
        sys.exit(f"stopping before any estimate: zero views on more than {max_zero_share:.0%} of days for "
                 f"{', '.join(bad.index)}. Record the decision in the change log first (design §3).")
    return zeros.to_dict()


def _versions() -> dict[str, str]:
    import importlib.metadata as md
    return {"python": sys.version.split()[0], "numpy": md.version("numpy"), "pandas": md.version("pandas")}


def _synthetic_panel() -> pd.DataFrame:
    groups = {e.target: e.controls for e in C.EVENTS}
    groups[C.REFERENCE_POOL[0]] = C.REFERENCE_POOL[1:]
    bumps = [("Eric_Stonestreet", "2023-09-27", 0.5, 5.0), ("Kevin_James", "2023-09-21", 0.3, 5.0),
             ("Eric_Stonestreet", "2023-06-13", 0.8, 3.0)]
    return S.synthetic_panel(1, groups, C.START, C.END, bumps, common_sd=0.1)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--verify-titles", action="store_true", help="check that the titles exist, no pageviews")
    src.add_argument("--download", action="store_true", help="download the real panel (needs --unblind)")
    src.add_argument("--panel-csv", type=Path, help="rerun on a saved real panel (needs --unblind)")
    src.add_argument("--synthetic", action="store_true", help="dry run on a made-up panel")
    ap.add_argument("--unblind", action="store_true", help="allow reading real pageview numbers (design §0)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--n-placebo", type=int, default=C.N_PLACEBO)
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
    if real:
        screen_panel(panel)
    summary, ars = study(panel, args.n_placebo)
    summary["meta"]["synthetic"] = bool(args.synthetic)
    summary["meta"]["versions"] = _versions()
    path = write_outputs(summary, ars, panel, out)
    if real:
        R.write_summary(C.RESULTS, summary)
    print(json.dumps({"summary": str(path), "labels": {e["name"]: e["label"] for e in summary["events"]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
