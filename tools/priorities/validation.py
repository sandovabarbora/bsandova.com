"""The validation results of the priorities study (design §2.2): the reference topic of each of the 600 speeches (the
coders' topic where they agree, else the adjudicated one), against the classifier's label, weighted back by the
inverse inclusion probability, separately for the ParlaCAP-CZ frame (the primary corpus) and the psp.cz 2004–2013
frame. Per harmonised topic: precision, recall and F1, and the error in the topic's word share; the weighted macro-F1
against the registered bound of 0.50. A classifier label of Mix or Other predicts no topic (the analysis drops those
speeches). Also: the coders' agreement, and the same measures on the speeches the author adjudicated herself.

    uv run --no-project --with pandas --with pyarrow python -I tools/priorities/validation.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "tools/data/priorities/validation"
OUT = ROOT / "docs/research/priorities-validation.json"
BOUND = 0.50
HARMONISED = {"Macroeconomics": "Economy", "Labor": "Unemployment", "Health": "Health", "Social Welfare": "Pensions",
              "Education": "Education", "Law and Crime": "Crime", "Immigration": "Immigration", "Housing": "Housing",
              "Environment": "Environment and energy", "Energy": "Environment and energy",
              "Defense": "Security and international", "International Affairs": "Security and international"}
TOPICS = sorted(set(HARMONISED.values()))


def coded(model: str) -> dict:
    return {r["key"]: r["topic"] for f in sorted(V.glob(f"coding-{model}-*.json"))
            for r in json.loads(f.read_text(encoding="utf-8"))}


def measures(d: pd.DataFrame) -> dict:
    w = 1 / d.pi
    out, f1s = {}, []
    for t in TOPICS:
        pred, true = d.pred == t, d.ref == t
        tp, fp, fn = (w * (pred & true)).sum(), (w * (pred & ~true)).sum(), (w * (~pred & true)).sum()
        p = tp / (tp + fp) if tp + fp else float("nan")
        r = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        f1s.append(f1)
        # word shares among the speeches the analysis keeps (classifier label not Mix or Other) vs the reference
        ww = w * d.word_count
        kept = ~d.label.isin(["Mix", "Other"])
        share_pred = (ww * (pred & kept)).sum() / (ww * kept).sum()
        share_true = (ww * (true & ~d.ref.isin(["Other"]))).sum() / (ww * ~d.ref.isin(["Other"])).sum()
        out[t] = {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
                  "n_predicted": int(pred.sum()), "n_reference": int(true.sum()),
                  "word_share_classifier": round(share_pred, 4), "word_share_reference": round(share_true, 4),
                  "word_share_error": round(share_pred - share_true, 4)}
    macro = float(pd.Series(f1s).mean())
    return {"by_topic": out, "macro_f1": round(macro, 3), "classifier_limited": macro < BOUND, "speeches": len(d)}


def main() -> None:
    s = pd.read_parquet(V / "sample.parquet")
    a, b = coded("sonnet"), coded("opus")
    author = json.loads((V / "adjudication-author.json").read_text())
    assistant = json.loads((V / "adjudication-assistant.json").read_text())
    s["sonnet"], s["opus"] = s.key.map(a), s.key.map(b)
    agree = s.sonnet == s.opus
    s["ref"] = s.sonnet.where(agree, s.key.map({**assistant, **author}))
    assert s.ref.notna().all()
    s["by"] = "agreed"
    s.loc[~agree & s.key.isin(author), "by"] = "author"
    s.loc[~agree & s.key.isin(assistant) & ~s.key.isin(author), "by"] = "assistant"
    s["pred"] = s.label.map(HARMONISED).fillna("—")
    s["ref"] = s.ref.map(lambda x: HARMONISED.get(x, x))
    w = 1 / s.pi
    res = {"bound_macro_f1": BOUND,
           "coders": {"agree": int(agree.sum()), "of": len(s), "raw_agreement": round(float(agree.mean()), 4),
                      "weighted_agreement": round(float((w * agree).sum() / w.sum()), 4)},
           "adjudicated": {"author": int((s.by == "author").sum()), "assistant": int((s.by == "assistant").sum())},
           "parlacap": measures(s[s.source == "parlacap"]),
           "psp_2004_2013": measures(s[s.source == "psp_2004_2013"])}
    sub = s[s.by == "author"]
    res["author_adjudicated_only"] = {"speeches": len(sub), "classifier_label_equals_author": int(
        (sub.pred == sub.ref).sum())}
    res["mix_reference"] = {k: int(v) for k, v in s[s.label == "Mix"].ref.value_counts().items()}
    print(json.dumps({k: v for k, v in res.items() if k not in ("parlacap", "psp_2004_2013")}, indent=1))
    for fr in ("parlacap", "psp_2004_2013"):
        print(fr, "macro-F1", res[fr]["macro_f1"], "limited" if res[fr]["classifier_limited"] else "ok")
        for t, m in res[fr]["by_topic"].items():
            print(f"  {t:28} P {m['precision']:.2f} R {m['recall']:.2f} F1 {m['f1']:.2f}  share err {m['word_share_error']:+.3f}")
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
