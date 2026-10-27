"""Agreement, the scene bootstrap, the estimands and their pre-written readings (design §1, §4, §5). Pure."""
from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping, Sequence

import config as C
import numpy as np

COLS = ("jokes", "america", "protected", "speaker", "group", "unclear", "wnpt", "hours")


# ---------------------------------------------------------------- per-cue codes and agreement (§4.6, §4.7)

def cue_codes(jokes: Sequence[Mapping], cues: Sequence[int]) -> dict[int, dict]:
    """Each cue's codes: the joke whose span starts first, then the shortest; a cue in no span is not a joke."""
    out = {}
    for cue in cues:
        covering = [j for j in jokes if j["first_cue"] <= cue <= j["last_cue"]]
        if not covering:
            out[cue] = {"joke": False}
            continue
        j = min(covering, key=lambda j: (j["first_cue"], j["last_cue"] - j["first_cue"]))
        out[cue] = {"joke": True, "target": j["target"], "butt": j["butt"]}
    return out


def kappa(a: Sequence, b: Sequence) -> float | None:
    """Cohen's kappa; None when it is undefined (no cue, or both coders used one and the same value throughout)."""
    if len(a) != len(b):
        raise ValueError("kappa needs paired codes")
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b), key=str)
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pe = sum((list(a).count(c) / n) * (list(b).count(c) / n) for c in cats)
    if math.isclose(pe, 1.0):
        return None
    return (po - pe) / (1 - pe)


def _pct(a: Sequence, b: Sequence) -> float | None:
    return 100 * sum(x == y for x, y in zip(a, b, strict=True)) / len(a) if a else None


def agreement(x: Mapping[int, Mapping], y: Mapping[int, Mapping], cues: Sequence[int]) -> dict:
    """Joke detection on every cue, then target and butt on the cues both call a joke."""
    dx, dy = [x[c]["joke"] for c in cues], [y[c]["joke"] for c in cues]
    both = [c for c in cues if x[c]["joke"] and y[c]["joke"]]
    return {"detection": {"cues": len(cues), "percent_agreement": _pct(dx, dy), "kappa": kappa(dx, dy)},
            "codes": {"cues": len(both),
                      "kappa_target": kappa([x[c]["target"] for c in both], [y[c]["target"] for c in both]),
                      "kappa_butt": kappa([x[c]["butt"] for c in both], [y[c]["butt"] for c in both])}}


def kappa_interval(pairs: Sequence[tuple], reps: int = C.BOOT_REPS, seed: int = C.VALID_BOOT_SEED) -> dict:
    """95 % bootstrap interval over cues for kappa on target and on butt, matched replicates; undefined draws drop."""
    n = len(pairs)
    if n == 0:
        return {"kappa_target": None, "kappa_butt": None, "dropped_target": reps, "dropped_butt": reps}
    rng = np.random.default_rng(seed)
    kt, kb = [], []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        draw = [pairs[i] for i in idx]
        kt.append(kappa([p[0] for p in draw], [p[1] for p in draw]))
        kb.append(kappa([p[2] for p in draw], [p[3] for p in draw]))
    out = {}
    for name, vals in (("target", kt), ("butt", kb)):
        ok = [v for v in vals if v is not None]
        out[f"kappa_{name}"] = [float(q) for q in np.quantile(ok, [0.025, 0.975])] if ok else None
        out[f"dropped_{name}"] = reps - len(ok)
    return out


def validation(model: Mapping[tuple, Mapping], human: Sequence[Mapping], reps: int = C.BOOT_REPS) -> dict:
    """Run 1 against the author on the sampled cues (design §4.7, §4.8). `model` maps (film, cue) to codes."""
    skipped = [h for h in human if h["joke"] == C.SKIP]
    rows = [h for h in human if h["joke"] != C.SKIP]
    m = [model[(h["film"], h["cue"])] for h in rows]
    dh, dm = [h["joke"] for h in rows], [x["joke"] for x in m]
    author_jokes = [k for k, h in enumerate(rows) if h["joke"]]
    model_jokes = [k for k, x in enumerate(m) if x["joke"]]
    both = [k for k in author_jokes if m[k]["joke"]]
    pairs = [(m[k]["target"], rows[k]["target"], m[k]["butt"], rows[k]["butt"]) for k in both]
    kt = kappa([p[0] for p in pairs], [p[1] for p in pairs])
    kb = kappa([p[2] for p in pairs], [p[3] for p in pairs])
    gate = kt is not None and kb is not None and kt >= C.KAPPA_GATE and kb >= C.KAPPA_GATE
    return {
        "cues": len(human), "skipped": len(skipped), "coded": len(rows),
        "detection": {"percent_agreement": _pct(dh, dm), "kappa": kappa(dh, dm),
                      "author_joke_cues": len(author_jokes), "model_joke_cues": len(model_jokes),
                      "share_of_author_jokes_found_by_model": len(both) / len(author_jokes) if author_jokes else None,
                      "share_of_model_jokes_marked_by_author": len(both) / len(model_jokes) if model_jokes else None},
        "codes": {"cues": len(both), "kappa_target": kt, "kappa_butt": kb,
                  "interval": kappa_interval(pairs, reps=reps)},
        "status": "Registered study" if gate else "Exploratory",
    }


# ---------------------------------------------------------------- scene tables and the bootstrap (§4.5)

@dataclasses.dataclass(frozen=True)
class Variant:
    """One way of counting: the primary analysis or a check of design §7."""
    unclear_as: str | None = None                  # "group" or "speaker" for the two bounds
    protected: tuple[str, ...] = C.PROTECTED
    kinds: tuple[str, ...] = C.KINDS
    hours: str = "dialogue"                        # or "runtime"


PRIMARY = Variant()


def scene_table(jokes: Sequence[Mapping], scene_hours: Sequence[float], scene_of_cue: Mapping[int, int],
                v: Variant = PRIMARY, runtime_hours: float | None = None) -> np.ndarray:
    """One row per scene (in scene order), the counts of COLS. A joke belongs to the scene of its first cue."""
    n = len(scene_hours)
    t = np.zeros((n, len(COLS)))
    t[:, COLS.index("hours")] = scene_hours if v.hours == "dialogue" else (runtime_hours or 0.0) / max(n, 1)
    for j in jokes:
        if j["kind"] not in v.kinds:
            continue
        row = t[scene_of_cue[j["first_cue"]] - 1]
        row[COLS.index("jokes")] += 1
        row[COLS.index("america")] += j["target"] == "america"
        if j["target"] == "group" and j["group_type"] in v.protected:
            butt = v.unclear_as if (j["butt"] == "unclear" and v.unclear_as) else j["butt"]
            row[COLS.index("protected")] += 1
            row[COLS.index(butt)] += 1
            row[COLS.index("wnpt")] += butt == "group"
    return t


def bootstrap_totals(tables: Mapping[str, np.ndarray], reps: int = C.BOOT_REPS, seed: int = C.BOOT_SEED
                     ) -> dict[str, np.ndarray]:
    """Per replicate and film, the column totals of the resampled scenes: one generator, PP1 then PP2 within each
    replicate, each film resampled to its own number of scenes."""
    rng = np.random.default_rng(seed)
    out = {f: np.empty((reps, len(COLS))) for f in tables}
    for b in range(reps):
        for f in C.FILMS:
            t = tables[f]
            if len(t) == 0:
                raise ValueError(f"{f} has no scene to resample")
            out[f][b] = t[rng.integers(0, len(t), len(t))].sum(axis=0)
    return out


def _ratio(num, den):
    num, den = np.asarray(num, float), np.asarray(den, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def statistics(totals: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Every estimand of §1 from column totals (a row of totals, or one row per replicate); NaN = no denominator."""
    col = {f: {c: totals[f][..., k] for k, c in enumerate(COLS)} for f in totals}
    s = {}
    for f in C.FILMS:
        x = col[f]
        s[f"share_america_{f}"] = _ratio(x["america"], x["jokes"])
        for b in C.BUTTS:
            s[f"share_{b}_{f}"] = _ratio(x[b], x["protected"])
        s[f"D_{f}"] = _ratio(x["speaker"] - x["group"], x["protected"])
        s[f"rate_wnpt_{f}"] = _ratio(x["wnpt"], x["hours"])
        s[f"rate_america_{f}"] = _ratio(x["america"], x["hours"])
    s["delta1"] = s["share_america_pp2"] - s["share_america_pp1"]
    s["D_diff"] = s["D_pp2"] - s["D_pp1"]
    s["delta3"] = s["rate_wnpt_pp2"] - s["rate_wnpt_pp1"]
    s["delta_rate_america"] = s["rate_america_pp2"] - s["rate_america_pp1"]
    return s


def summarise(point: Mapping[str, np.ndarray], boot: Mapping[str, np.ndarray]) -> dict[str, dict]:
    out = {}
    for k, v in boot.items():
        ok = v[~np.isnan(v)]
        dropped = int(len(v) - len(ok))
        p = float(point[k])
        out[k] = {"estimate": None if math.isnan(p) else p,
                  "ci95": [float(q) for q in np.quantile(ok, [0.025, 0.975])] if len(ok) else None,
                  "dropped": dropped, "replicates": len(v),
                  "indeterminate": dropped > C.DEGENERATE_MAX_SHARE * len(v)}
    return out


def estimate(tables: Mapping[str, np.ndarray], reps: int = C.BOOT_REPS, seed: int = C.BOOT_SEED) -> dict[str, dict]:
    point = statistics({f: t.sum(axis=0) for f, t in tables.items()})
    return summarise(point, statistics(bootstrap_totals(tables, reps, seed)))


# ---------------------------------------------------------------- minimum detectable differences (§5)

def mdd(counts: Mapping[str, Mapping[str, float]]) -> dict:
    """§5's formulas on the real counts, design effect 1.2. Unequal films enter as the sum of the two variances,
    which is §5's formula when the films are equal."""
    z, de = C.Z_POWER, C.DESIGN_EFFECT
    c1, c2 = counts["pp1"], counts["pp2"]
    n1, n2 = c1["jokes"], c2["jokes"]
    out: dict = {"design_effect": de}
    if n1 and n2:
        p = (c1["america"] + c2["america"]) / (n1 + n2)
        out["q1_pp"] = 100 * z * math.sqrt(de * p * (1 - p) * (1 / n1 + 1 / n2))
    out["q2_D"] = {f: (z * math.sqrt(de / counts[f]["protected"]) if counts[f]["protected"] else None) for f in C.FILMS}
    if c1["hours"] and c2["hours"]:
        out["q3_per_hour"] = z * math.sqrt(de * (c1["wnpt"] / c1["hours"] ** 2 + c2["wnpt"] / c2["hours"] ** 2))
    return out


# ---------------------------------------------------------------- the pre-written readings (§1, §6.2)

def side(ci: Sequence[float] | None) -> str:
    """'above' or 'below' when both ends lie strictly on one side of 0; an end exactly at 0 does not exclude it."""
    if ci is None:
        return "includes"
    lo, hi = ci
    return "above" if lo > 0 else "below" if hi < 0 else "includes"


def _f(x: float) -> str:
    return f"{x:.1f}"


def read_q1(s: Mapping, m_pp: float | None) -> dict:
    if s["indeterminate"] or s["estimate"] is None:
        return {"label": "indeterminate", "sentence": None}
    x, (a, b) = 100 * s["estimate"], [100 * v for v in s["ci95"]]
    ci = f"(95 % CI {_f(a)} to {_f(b)}, bootstrap by scene)"
    where = side(s["ci95"])
    if where == "above":
        return {"label": "supported", "sentence": "A larger share of the second film's jokes aim at America than of "
                f"the first film's: {_f(abs(x))} pp more {ci}."}
    if where == "below":
        return {"label": "not supported", "sentence": "The opposite: a smaller share of the second film's jokes aim at "
                f"America, {_f(abs(x))} pp fewer {ci}."}
    m = "?" if m_pp is None else _f(m_pp)
    return {"label": "inconclusive", "sentence": "The two films aim a similar share of jokes at America, or differ by "
            f"less than this sample can tell: {_f(x)} pp {ci}. A difference of about {m} pp would have been detected "
            "four times in five."}


def read_q2(s: Mapping, film: str, protected: int) -> dict:
    name = C.FILM_NAMES[film]
    if protected == 0:
        return {"label": "no protected-trait joke found", "sentence": None}
    if s["indeterminate"] or s["estimate"] is None:
        return {"label": "indeterminate", "sentence": None}
    x, (a, b) = 100 * s["estimate"], [100 * v for v in s["ci95"]]
    tail = f"D = {_f(x)} pp (95 % CI {_f(a)} to {_f(b)})."
    where = side(s["ci95"])
    if where == "above":
        return {"label": "direction", "side": "above", "sentence": f"In {name}, jokes on protected traits more often laugh at the "
                f"speaker than at the group: {tail}"}
    if where == "below":
        return {"label": "direction", "side": "below", "sentence": f"In {name}, jokes on protected traits more often laugh at "
                f"the group than at the speaker: {tail}"}
    return {"label": "inconclusive", "sentence": f"In {name}, satire and punching down cannot be told apart in this "
            f"sample: {tail}"}


def read_q3(s: Mapping) -> dict:
    if s["indeterminate"] or s["estimate"] is None:
        return {"label": "indeterminate", "sentence": None}
    x, (a, b) = s["estimate"], s["ci95"]
    ci = f"(95 % CI {_f(a)} to {_f(b)})"
    where = side(s["ci95"])
    if where == "above":
        return {"label": "direction", "side": "above", "sentence": "The second film has more jokes that would not pass today "
                f"per hour of dialogue: {_f(abs(x))} more per hour {ci}."}
    if where == "below":
        return {"label": "direction", "side": "below", "sentence": "The first film has more jokes that would not pass today per "
                f"hour of dialogue: {_f(abs(x))} more per hour {ci}."}
    return {"label": "inconclusive", "sentence": "The two films have a similar rate of jokes that would not pass today, "
            f"or differ by less than this sample can tell: {_f(x)} per hour {ci}."}
