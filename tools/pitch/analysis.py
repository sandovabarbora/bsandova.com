"""From the two runs' codes, the cleaned films and the author's codes to the results (design §4, §7). Pure: the
results hold counts, cue numbers, codes, estimates and intervals, never subtitle text."""
from __future__ import annotations

import dataclasses
from collections import Counter
from collections.abc import Mapping, Sequence

import config as C
import stats as T
import subtitles as S

ESTIMANDS = ("delta1", "D_diff", "delta3", *(f"{s}_{f}" for f in C.FILMS for s in (
    "share_america", "share_speaker", "share_group", "share_unclear", "D", "rate_wnpt")))


@dataclasses.dataclass(frozen=True)
class Film:
    raw: tuple[S.Cue, ...]
    kept: tuple[S.Cue, ...]
    cleaning: Mapping


def coded_cues(film: Film, out: Mapping) -> list[S.Cue]:
    """The kept cues less those of scenes whose pass 1 failed: such scenes leave the scene table, the dialogue hours
    and the bootstrap (design change log, 27 October 2026)."""
    failed = set(out.get("failed_scene_cues", ()))
    return [c for c in film.kept if c.index not in failed]


def tables(films: Mapping[str, Film], run: Mapping[str, Mapping], v: T.Variant = T.PRIMARY,
           gap: float = C.SCENE_GAP_S) -> dict:
    out = {}
    for f in C.FILMS:
        scenes = S.build_scenes(coded_cues(films[f], run[f]), gap)
        out[f] = T.scene_table(run[f]["jokes"], [s.duration_ms / 3_600_000 for s in scenes], S.scene_of(scenes), v,
                               S.runtime_hours(films[f].raw))
    return out


def counts(film: Film, out: Mapping) -> dict:
    jokes = out["jokes"]
    scenes = S.build_scenes(coded_cues(film, out))
    protected = [j for j in jokes if j["target"] == "group" and j["group_type"] in C.PROTECTED]
    return {
        "jokes": len(jokes), "by_kind": dict(Counter(j["kind"] for j in jokes)),
        "by_target": dict(Counter(j["target"] for j in jokes)),
        "by_group_type": dict(Counter(j["group_type"] for j in jokes if j["target"] == "group")),
        "group_other": dict(Counter(j["group_other"].lower() for j in jokes if j["group_type"] == "other")),
        "by_butt": dict(Counter(j["butt"] for j in jokes)),
        "protected": len(protected), "would_not_pass_today": sum(j["butt"] == "group" for j in protected),
        "protected_by_butt": dict(Counter(j["butt"] for j in protected)),
        "america": sum(j["target"] == "america" for j in jokes),
        "scenes": len(scenes), "kept_cues": len(film.kept), "dialogue_hours": S.dialogue_hours(scenes),
        "runtime_hours": S.runtime_hours(film.raw), "cleaning": dict(film.cleaning),
        "failed_scenes": len(out["failed_scenes"]), "kept_cues_in_failed_scenes": len(out.get("failed_scene_cues", ())),
        "failed_jokes": len(out["failed_jokes"]),
        "jokes_found_in_pass_1": out["jokes_found"],
    }


def _pick(est: Mapping, keys: Sequence[str] = ESTIMANDS) -> dict:
    return {k: est[k] for k in keys}


def readings(est: Mapping, cnt: Mapping, power: Mapping) -> dict:
    return {"Q1": T.read_q1(est["delta1"], power.get("q1_pp")),
            "Q2": {f: T.read_q2(est[f"D_{f}"], f, cnt[f]["protected"]) for f in C.FILMS},
            "Q2_difference": {"reading": None, "note": "descriptive, no reading (design §1)", **est["D_diff"]},
            "Q3": T.read_q3(est["delta3"])}


def cue_map(films: Mapping[str, Film], run: Mapping[str, Mapping]) -> dict[tuple[str, int], dict | None]:
    out = {}
    for f in C.FILMS:
        r = run[f]
        codes = T.cue_codes(r["jokes"], [c.index for c in films[f].kept], r.get("detected_spans"),
                            r.get("failed_scene_cues", ()))
        out.update({(f, cue): v for cue, v in codes.items()})
    return out


def self_agreement(films: Mapping[str, Film], run1: Mapping, run2: Mapping) -> dict:
    a, b = cue_map(films, run1), cue_map(films, run2)
    out = {f: T.agreement(a, b, [(f, c.index) for c in films[f].kept]) for f in C.FILMS}
    out["pooled"] = T.agreement(a, b, list(a))
    return out


def checks(films: Mapping[str, Film], runs: Mapping[int, Mapping], reps: int, seed: int) -> dict:
    """Design §7: reported beside the primary results; none relabels them."""
    primary = runs[C.PRIMARY_RUN]
    q23 = ("D_pp1", "D_pp2", "D_diff", "delta3", "rate_wnpt_pp1", "rate_wnpt_pp2")
    plan = {
        "run_2": (runs[2], T.PRIMARY, C.SCENE_GAP_S, ESTIMANDS),
        "unclear_as_group": (primary, T.Variant(unclear_as="group"), C.SCENE_GAP_S, q23),
        "unclear_as_speaker": (primary, T.Variant(unclear_as="speaker"), C.SCENE_GAP_S, q23),
        **{f"scene_gap_{g:g}s": (primary, T.PRIMARY, g, ESTIMANDS) for g in C.SENSITIVITY_GAPS_S},
        "full_runtime": (primary, T.Variant(hours="runtime"), C.SCENE_GAP_S, ("delta3", "rate_wnpt_pp1",
                                                                               "rate_wnpt_pp2")),
        "without_allusions": (primary, T.Variant(kinds=("joke",)), C.SCENE_GAP_S, ESTIMANDS),
        "protected_widened": (primary, T.Variant(protected=C.GROUP_TYPES), C.SCENE_GAP_S, q23),
        "q1_america_per_hour": (primary, T.PRIMARY, C.SCENE_GAP_S, ("delta_rate_america", "rate_america_pp1",
                                                                     "rate_america_pp2")),
    }
    return {name: _pick(T.estimate(tables(films, run, v, gap), reps, seed), keys)
            for name, (run, v, gap, keys) in plan.items()}


def study(films: Mapping[str, Film], runs: Mapping[int, Mapping[str, Mapping]], human: Sequence[Mapping] | None,
          reps: int = C.BOOT_REPS, seed: int = C.BOOT_SEED) -> dict:
    primary = runs[C.PRIMARY_RUN]
    cnt = {f: counts(films[f], primary[f]) for f in C.FILMS}
    est = T.estimate(tables(films, primary), reps, seed)
    power = T.mdd({f: {"jokes": cnt[f]["jokes"], "america": cnt[f]["america"], "protected": cnt[f]["protected"],
                       "wnpt": cnt[f]["would_not_pass_today"], "hours": cnt[f]["dialogue_hours"]} for f in C.FILMS})
    valid = T.validation(cue_map(films, primary), human, reps=reps) if human is not None else None
    return {
        "status": valid["status"] if valid else None,
        "counts": cnt,
        "counts_run_2": {f: counts(films[f], runs[2][f]) for f in C.FILMS},
        "estimates": _pick(est),
        "readings": readings(est, cnt, power),
        "minimum_detectable": power,
        "validation": valid,
        "self_agreement": self_agreement(films, primary, runs[2]),
        "checks": checks(films, runs, reps, seed),
        "settings": {"bootstrap_replicates": reps, "bootstrap_seed": seed, "scene_gap_s": C.SCENE_GAP_S,
                     "primary_run": C.PRIMARY_RUN, "kappa_gate": C.KAPPA_GATE,
                     "degenerate_max_share": C.DEGENERATE_MAX_SHARE},
    }
