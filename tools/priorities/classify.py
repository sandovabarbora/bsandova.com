"""CAP major topic of each psp.cz speech (priorities design §2.2, extension), as ParlaCAP labelled ParlaMint.

Model `classla/ParlaCAP-Topic-Classifier` (XLM-R-Parla fine-tuned on ParlaCAP-train), applied as in ParlaCAP's
annotation code (github.com/clarinsi/ParlaMint-Annotation-with-CAP-Topics): the speech text with whitespace
collapsed and cut to its first 512 words, tokenised with max_length=512 and truncation, softmax over the 22 labels;
the top label if its probability is at least 0.60, else "Mix". Notes are already out of the text (psp.py).

Reads tools/data/priorities/psp_speeches.parquet and writes one file per sitting,
tools/data/priorities/psp_topics/part-<term>-<sitting>.parquet (id, CAP_category, CAP_top, CAP_prob, probs), so a
stopped run resumes at the first sitting not yet written. `--period FROM:TO` (ISO dates, either side may be empty)
keeps the sittings with a day in the period; `--limit N` classifies only the first N speeches of the selection into
psp_topics/limit.parquet, as a timing check, and leaves the parts alone. Nothing here tallies topics.

    OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false nice -n 20 uv run --no-project \
        --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match \
        --with torch --with transformers --with pandas --with pyarrow \
        python -I tools/priorities/classify.py [--period 2004-01-01:2013-11-24] [--limit 300]
"""
from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPEECHES = ROOT / "tools/data/priorities/psp_speeches.parquet"
PARTS = ROOT / "tools/data/priorities/psp_topics"
MODEL = "classla/ParlaCAP-Topic-Classifier"
REVISION = "82a13c61ff63b3450638e35f7b1b2cb9e6694ad6"  # the model's commit on 14 October 2026
THRESHOLD = 0.60
BATCH = 8


def prepare(text: str) -> str:
    """ParlaCAP's input: transcriber notes in [[ ]] out, whitespace collapsed, the first 512 words."""
    text = re.sub(r"\[\[.*?\]\]", "", text).strip()
    return " ".join(re.sub(r"\s+", " ", text).split(" ")[:512])


class Classifier:
    def __init__(self) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        torch.set_num_threads(2)
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL, revision=REVISION).eval()
        self.labels = [self.model.config.id2label[i] for i in range(self.model.config.num_labels)]

    def probs(self, texts: list[str]) -> np.ndarray:
        """Softmax probabilities, batched over texts of similar length to keep padding short."""
        order = np.argsort([len(t) for t in texts])
        out = np.zeros((len(texts), len(self.labels)), dtype=np.float32)
        for i in range(0, len(texts), BATCH):
            idx = order[i:i + BATCH]
            enc = self.tok([texts[j] for j in idx], max_length=512, truncation=True, padding=True,
                           return_tensors="pt")
            with self.torch.inference_mode():
                out[idx] = self.torch.softmax(self.model(**enc).logits.float(), dim=-1).numpy()
        return out

    def label(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.probs([prepare(t) for t in df.text])
        top = p.argmax(axis=1)
        prob = p[np.arange(len(p)), top]
        names = np.array(self.labels)[top]
        return pd.DataFrame({"id": df.id.values, "CAP_category": np.where(prob >= THRESHOLD, names, "Mix"),
                             "CAP_top": names, "CAP_prob": prob, "probs": list(p)})


def select(df: pd.DataFrame, period: str | None) -> pd.DataFrame:
    if not period:
        return df
    lo, _, hi = period.partition(":")
    day = df.date.between(pd.Timestamp(lo or "1900-01-01"), pd.Timestamp(hi or "2100-01-01"))
    keep = df.loc[day, ["term", "sitting"]].drop_duplicates()
    return df.merge(keep, on=["term", "sitting"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", help="FROM:TO, ISO dates; sittings with a day in the period")
    ap.add_argument("--limit", type=int, help="classify only the first N speeches, into psp_topics/limit.parquet")
    args = ap.parse_args()
    df = select(pd.read_parquet(SPEECHES, columns=["id", "term", "sitting", "date", "text"]), args.period)
    PARTS.mkdir(parents=True, exist_ok=True)
    clf = Classifier()

    if args.limit:
        sample = df.head(args.limit)
        t0 = time.perf_counter()
        clf.label(sample).to_parquet(PARTS / "limit.parquet", index=False)
        dt = time.perf_counter() - t0
        print(f"{len(sample)} speeches in {dt:.0f} s, {dt / max(len(sample), 1):.2f} s a speech")
        return

    groups = list(df.groupby(["term", "sitting"], sort=True))
    todo = [(k, g) for k, g in groups if not (PARTS / f"part-{k[0]}-{k[1]:03d}.parquet").exists()]
    print(f"{len(groups)} sittings selected, {len(groups) - len(todo)} done, {sum(len(g) for _, g in todo):,} "
          f"speeches to classify", flush=True)
    for n, ((term, sitting), g) in enumerate(todo, 1):
        t0 = time.perf_counter()
        path = PARTS / f"part-{term}-{sitting:03d}.parquet"
        clf.label(g).to_parquet(path.with_suffix(".tmp"), index=False)
        path.with_suffix(".tmp").rename(path)
        dt = time.perf_counter() - t0
        print(f"[{n}/{len(todo)}] {term} {sitting}: {len(g)} speeches, {dt:.0f} s", flush=True)


if __name__ == "__main__":
    main()
