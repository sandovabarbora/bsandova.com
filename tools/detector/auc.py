"""Held-out AUCs of the silent-failure detector, with question-level bootstrap intervals.

Reads assets/detector/answers.csv (the 3 704 numeric answers the detector was trained on, as written by
quaesitor/method/src/detector.py at b99c89e) and writes assets/detector/auc.json. Used by
texts/silent-detector.html and tools/charts/silent_detector.py.

    uv run --with scikit-learn==1.9.1 --with pandas==3.0.5 --with numpy==2.5.1 python tools/detector/auc.py

Step 1 refits the eight combinations (four feature sets x logistic regression and gradient boosting) with
GroupKFold(5) by question, the agreement rule and the 3 x 3 pack-transfer matrix, exactly as detector.py does, and
checks them against assets/detector/detector.json. Step 2 resamples question groups with replacement
(B = 2 000, fixed seeds per block) and recomputes every AUC on the held-out predictions of step 1. The interval therefore
covers which questions happened to be asked, not the refitting of the models; percentile 95 % intervals.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets/detector"
B = 2000
SEED = 20260929

NUM = ["n_distinct_sql", "n_distinct_values", "is_majority_value", "repeats_agree", "sql_len", "n_join", "n_tables",
       "n_where_terms", "n_bool_flags", "has_distinct", "has_group", "has_date", "has_cast", "n_subquery", "has_null_check"]
CAT = ["alias", "pack", "lang"]
SETS = {"agreement": ["n_distinct_sql", "n_distinct_values", "is_majority_value", "repeats_agree"],
        "sql": [f for f in NUM if f not in ("n_distinct_sql", "n_distinct_values")
                and f.startswith(("sql_", "n_", "has_"))],
        "run": CAT, "all": NUM + CAT}


def pipe(feats: list[str], model):
    num = [f for f in feats if f in NUM]
    cat = [f for f in feats if f in CAT]
    pre = ColumnTransformer([("num", StandardScaler(), num), ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    return make_pipeline(pre, model)


def gbm():
    return GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0)


def oof(df: pd.DataFrame, y: np.ndarray, feats: list[str], make_model) -> np.ndarray:
    pred = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=5).split(df, y, df["group"]):
        p = pipe(feats, make_model())
        p.fit(df.iloc[tr][feats], y[tr])
        pred[te] = p.predict_proba(df.iloc[te][feats])[:, 1]
    return pred


def boot_auc(y: np.ndarray, score: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> dict:
    """AUC over B resamples of question groups; a resampled group enters with weight = times drawn."""
    codes, uniq = pd.factorize(groups)
    g = len(uniq)
    vals, skipped = [], 0
    for _ in range(B):
        w = np.bincount(rng.integers(0, g, g), minlength=g)[codes]
        m = w > 0
        if len(np.unique(y[m])) < 2:
            skipped += 1
            continue
        vals.append(roc_auc_score(y[m], score[m], sample_weight=w[m]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"auc": float(roc_auc_score(y, score)), "lo": float(lo), "hi": float(hi), "groups": int(g),
            "answers": int(len(y)), "resamples_used": len(vals), "resamples_one_class": skipped, "_draws": vals}


def boot_share(num_mask: np.ndarray, den_mask: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> dict:
    """A ratio sum(num)/sum(den) with a question-level bootstrap interval."""
    codes, uniq = pd.factorize(groups)
    g = len(uniq)
    n_g = np.bincount(codes, weights=num_mask.astype(float), minlength=g)
    d_g = np.bincount(codes, weights=den_mask.astype(float), minlength=g)
    vals = []
    for _ in range(B):
        k = np.bincount(rng.integers(0, g, g), minlength=g)
        if (k * d_g).sum() > 0:
            vals.append((k * n_g).sum() / (k * d_g).sum())
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"value": float(n_g.sum() / d_g.sum()), "lo": float(lo), "hi": float(hi), "num": int(n_g.sum()),
            "den": int(d_g.sum()), "groups": int(g)}


def reading(r: dict) -> str:
    if r["lo"] > 0.5:
        return "above chance"
    if r["hi"] < 0.5:
        return "below chance: anti-predictive"
    return "indistinguishable from chance"


def main() -> None:
    df = pd.read_csv(A / "answers.csv", keep_default_na=False)
    y = (df["outcome"] == "silently_wrong").to_numpy().astype(int)
    groups = df["group"].to_numpy()
    rng = np.random.default_rng(SEED)
    published = json.loads((A / "detector.json").read_text())

    # step 1 and 2: eight combinations
    models, preds = {}, {}
    for name, feats in SETS.items():
        for key, make in (("logistic", lambda: LogisticRegression(max_iter=2000, C=1.0)), ("gbm", gbm)):
            p = oof(df, y, feats, make)
            preds[f"{name}/{key}"] = p
            r = boot_auc(y, p, groups, rng)
            r.update({"ap_correct": float(average_precision_score(1 - y, 1 - p)),
                      "brier": float(brier_score_loss(y, p)),
                      "published_auc": published["models"][f"{name}/{key}"]["auc"]})
            models[f"{name}/{key}"] = r

    # selection: how often each combination is the best of eight across resamples
    best = max(models, key=lambda k: models[k]["auc"])
    rng_sel = np.random.default_rng(SEED + 1)
    codes, uniq = pd.factorize(groups)
    wins = dict.fromkeys(models, 0)
    maxes = []
    for _ in range(B):
        w = np.bincount(rng_sel.integers(0, len(uniq), len(uniq)), minlength=len(uniq))[codes]
        m = w > 0
        a = {k: roc_auc_score(y[m], preds[k][m], sample_weight=w[m]) for k in models}
        top = max(a, key=a.get)
        wins[top] += 1
        maxes.append(a[top])
    selection = {"best": best, "best_auc": models[best]["auc"], "best_lo": models[best]["lo"],
                 "best_hi": models[best]["hi"], "share_resamples_best": {k: v / B for k, v in wins.items()},
                 "max_of_eight_lo": float(np.percentile(maxes, 2.5)), "max_of_eight_hi": float(np.percentile(maxes, 97.5))}

    # the agreement rule and the filter lane of the best model at a 50 % threshold
    rng = np.random.default_rng(SEED + 3)
    flag = (df["repeats_agree"] == 0).to_numpy()
    rule = boot_auc(y, flag.astype(float), groups, rng)
    rule["published_auc"] = published["baseline"]["auc"]
    correct = y == 0
    keep = ~flag
    lane = preds[best] < 0.5
    shares = {
        "base_rate_correct": boot_share(correct, np.ones(len(y), bool), groups, rng),
        "correct_when_repeats_agree": boot_share(correct & keep, keep, groups, rng),
        "correct_when_agree_three_sql": boot_share(correct & keep & (df["n_distinct_sql"] == 3).to_numpy(),
                                                   keep & (df["n_distinct_sql"] == 3).to_numpy(), groups, rng),
        "best_forwarded": boot_share(lane, np.ones(len(y), bool), groups, rng),
        "best_correct_among_forwarded": boot_share(correct & lane, lane, groups, rng),
        "best_share_of_correct_caught": boot_share(correct & lane, correct, groups, rng),
    }

    # paired: correct share among agreeing answers minus the base rate, same resamples for both
    codes, uniq = pd.factorize(groups)
    g = len(uniq)
    agg = [np.bincount(codes, weights=v.astype(float), minlength=g) for v in (correct & keep, keep, correct)]
    size = np.bincount(codes, minlength=g)
    diffs = []
    for _ in range(B):
        k = np.bincount(rng.integers(0, g, g), minlength=g)
        diffs.append((k * agg[0]).sum() / (k * agg[1]).sum() - (k * agg[2]).sum() / (k * size).sum())
    shares["agree_minus_base_pp"] = {
        "value": float(100 * (agg[0].sum() / agg[1].sum() - agg[2].sum() / len(y))),
        "lo": float(100 * np.percentile(diffs, 2.5)), "hi": float(100 * np.percentile(diffs, 97.5)),
        "num": int(agg[0].sum()), "den": int(agg[1].sum()), "groups": int(g)}

    per_q = df[lane].groupby("group").size().sort_values(ascending=False)
    shares["best_lane_questions"] = {"questions": int(len(per_q)), "top_question": str(per_q.index[0]),
                                     "top_question_answers": int(per_q.iloc[0]), "answers": int(lane.sum()),
                                     "by_question": {k: int(v) for k, v in per_q.items()}}

    # transfer: SQL-shape gradient boosting trained on one pack, scored on another; diagonal within pack
    rng = np.random.default_rng(SEED + 2)
    feats = SETS["sql"]
    packs = [p for p, g in df.groupby("pack") if len(g) >= 150 and 0 < y[g.index].mean() < 1]
    transfer = {}
    for src in packs:
        tr = (df["pack"] == src).to_numpy()
        fitted = pipe(feats, gbm()).fit(df[tr][feats], y[tr])
        row = {}
        for dst in packs:
            te = (df["pack"] == dst).to_numpy()
            sub = df[te].reset_index(drop=True)
            if dst == src:
                p = oof(sub, y[te], feats, gbm)
            else:
                p = fitted.predict_proba(sub[feats])[:, 1]
            r = boot_auc(y[te], p, groups[te], rng)
            r["published_auc"] = published["transfer_sql_gbm_auc"][src][dst]
            r["reading"] = reading(r)
            row[dst] = r
        transfer[src] = row

    for r in [*models.values(), rule, *(c for row in transfer.values() for c in row.values())]:
        r.pop("_draws", None)
        r["reading"] = reading(r)

    diffs = [abs(r["auc"] - r["published_auc"]) for r in [*models.values(), rule]]
    diffs += [abs(c["auc"] - c["published_auc"]) for row in transfer.values() for c in row.values()]
    per_pack = {p: {"answers": int(len(g)), "questions": int(g["group"].nunique()),
                    "silent_rate": float((g["outcome"] == "silently_wrong").mean())} for p, g in df.groupby("pack")}
    out = {"source": "assets/detector/answers.csv", "answers": int(len(df)), "questions": int(df["group"].nunique()),
           "silent_rate": float(y.mean()),
           "bootstrap": {"B": B, "seed": SEED, "unit": "question (pack:question id)", "interval": "percentile 95 %",
                         "what": "held-out predictions fixed, question groups resampled with replacement"},
           "reproduction": {"against": "assets/detector/detector.json", "max_abs_auc_diff": float(max(diffs)),
                            "reproduced": bool(max(diffs) < 1e-9)},
           "models": models, "selection": selection, "rule": rule, "shares": shares, "transfer_sql_gbm": transfer,
           "per_pack": per_pack,
           "by_alias": {a: int(n) for a, n in df["alias"].value_counts().items()}}
    (A / "auc.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")

    print(f"{len(df)} answers, {out['questions']} questions; reproduced: {out['reproduction']}")
    for k, r in models.items():
        print(f"  {k:20s} {r['auc']:.3f} [{r['lo']:.2f}, {r['hi']:.2f}]  {r['reading']}")
    print(f"  {'rule':20s} {rule['auc']:.3f} [{rule['lo']:.2f}, {rule['hi']:.2f}]")
    print("  selection", {k: round(v, 3) if isinstance(v, float) else v for k, v in selection.items() if k != 'share_resamples_best'},
          {k: round(v, 3) for k, v in selection["share_resamples_best"].items()})
    for k, s in shares.items():
        if "value" not in s:
            print(f"  {k:32s} {s['by_question']}")
            continue
        print(f"  {k:32s} {s['value']:.3f} [{s['lo']:.3f}, {s['hi']:.3f}]  {s['num']}/{s['den']}")
    for a, row in transfer.items():
        print(f"  {a:10s}", "  ".join(f"{b}:{c['auc']:.2f} [{c['lo']:.2f}, {c['hi']:.2f}] n_q={c['groups']} skip={c['resamples_one_class']}"
                                      for b, c in row.items()))


if __name__ == "__main__":
    main()
