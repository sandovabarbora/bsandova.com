"""Reproducibility probe of the psp.cz extension (priorities design §2.2): psp.cz speeches matched to ParlaCAP-CZ.

Matches the speeches of psp_speeches.parquet (terms 2013ps–2021ps) to the ParlaCAP-CZ speech file on date and the
first 80 letters and digits of the text, keeping keys unique on both sides; prints the match rate by term, how well
the matched pairs agree on words, speaker and chair, then classifies a random sample of matched 2013ps speeches with
classify.py's pipeline and prints the share whose label (Mix included) and top topic equal ParlaCAP's, with the
seconds per speech on two threads. Rates and timings only, no topic counts (§3). Writes
tools/data/priorities/psp_probe.json.

    OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false nice -n 20 uv run --no-project \
        --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match \
        --with torch --with transformers --with pandas --with pyarrow \
        python -I tools/priorities/psp_probe.py [--n 300]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import Classifier

ROOT = Path(__file__).resolve().parents[2]
SPEECHES = ROOT / "tools/data/priorities/psp_speeches.parquet"
PARLACAP = ROOT / "tools/data/priorities/parlacap/ParlaCAP-CZ_speeches.tsv.zip"
OUT = ROOT / "tools/data/priorities/psp_probe.json"
TERMS = ("2013ps", "2017ps", "2021ps")
SEED = 20261014


def key(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower())[:80]


def parlacap() -> pd.DataFrame:
    cols = ["id", "date", "speaker_role", "speaker_name", "word_count", "CAP_category", "CAP_prob", "text"]
    with zipfile.ZipFile(PARLACAP) as z, z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, sep="\t", usecols=cols, dtype=str, keep_default_na=False)
    df["date"] = pd.to_datetime(df.date)
    df["word_count"] = df.word_count.astype(int)
    return df


def unique_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(key=df.date.dt.strftime("%Y-%m-%d") + "|" + df.text.map(key))
    return df[~df.key.duplicated(keep=False)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    n = ap.parse_args().n
    pc = parlacap()
    psp = pd.read_parquet(SPEECHES)
    psp = psp[psp.term.isin(TERMS) & psp.date.between(pc.date.min(), pc.date.max())]
    m = unique_keys(psp).merge(unique_keys(pc), on="key", suffixes=("", "_pc"))
    res = {"overlap": [f"{pc.date.min():%Y-%m-%d}", f"{pc.date.max():%Y-%m-%d}"], "by_term": {}}
    for term, g in psp.groupby("term"):
        mt = m[m.term == term]
        pct = pc[pc.date.between(g.date.min(), g.date.max())]
        res["by_term"][term] = {"psp_speeches": len(g), "parlacap_speeches": len(pct), "matched": len(mt),
                                "psp_matched_share": round(len(mt) / len(g), 4),
                                "parlacap_matched_share": round(len(mt) / len(pct), 4)}
    surname = m.speaker.str.split().str[-1] == m.speaker_name.str.split(",").str[0]
    res["matched"] = {
        "pairs": len(m),
        "same_surname": round(float(surname.mean()), 4),
        "word_count_equal": round(float((m.word_count == m.word_count_pc).mean()), 4),
        "word_count_within_5pct": round(float(((m.word_count - m.word_count_pc).abs()
                                               <= 0.05 * m.word_count_pc).mean()), 4),
        "chair_ours_vs_parlacap": {f"{a}|{b}": int(v) for (a, b), v in
                                   pd.crosstab(m.chair, m.speaker_role == "Chairperson").stack().items()},
    }
    print(json.dumps(res, indent=2), flush=True)

    sample = m[m.term == "2013ps"].sample(n, random_state=SEED)
    clf = Classifier()
    t0 = time.perf_counter()
    ours = clf.label(sample[["id", "text"]])
    dt = time.perf_counter() - t0
    same = ours.CAP_category.values == sample.CAP_category.values
    same_top = ours.CAP_top.values == sample.CAP_category.values
    clear = sample.CAP_category.values != "Mix"
    diff = abs(ours.CAP_prob.values - sample.CAP_prob.astype(float).values)[same]
    res["probe"] = {
        "speeches": n, "words": int(sample.word_count.sum()), "seconds": round(dt, 1),
        "seconds_per_speech": round(dt / n, 3), "seconds_per_1000_words": round(1000 * dt / sample.word_count.sum(), 3),
        "label_agreement": round(float(same.mean()), 4),
        "label_agreement_not_chair": round(float(same[~sample.chair.values].mean()), 4),
        "top_topic_agreement_where_parlacap_not_mix": round(float(same_top[clear].mean()), 4),
        "prob_difference_where_same_label": {"median": round(float(pd.Series(diff).median()), 4),
                                             "max": round(float(diff.max()), 4)},
        "same_text": round(float((sample.word_count == sample.word_count_pc).mean()), 4),
    }
    print(json.dumps(res["probe"], indent=2))
    OUT.write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
