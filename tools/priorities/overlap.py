"""The registered reproducibility check of the psp.cz extension (priorities design §2.2): on every psp.cz speech of
2013–2023 matched to ParlaCAP-CZ, the share whose label from our run of the classifier (Mix included) equals
ParlaCAP's. The extension is estimated only if the share is at least 90 %. Rates only, no topic counts (§3). Writes
docs/research/priorities-overlap.json.

    uv run --no-project --with pandas --with pyarrow python -I tools/priorities/overlap.py
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPEECHES = ROOT / "tools/data/priorities/psp_speeches.parquet"
PARLACAP = ROOT / "tools/data/priorities/parlacap/ParlaCAP-CZ_speeches.tsv.zip"
TERMS = ("2013ps", "2017ps", "2021ps")
TOPICS = ROOT / "tools/data/priorities/psp_topics"
OUT = ROOT / "docs/research/priorities-overlap.json"
BAR = 0.90


# the matching of psp_probe.py, repeated here so that this check does not load the classifier
def key(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower())[:80]


def parlacap() -> pd.DataFrame:
    cols = ["id", "date", "speaker_role", "word_count", "CAP_category", "text"]
    with zipfile.ZipFile(PARLACAP) as z, z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, sep="\t", usecols=cols, dtype=str, keep_default_na=False)
    df["date"] = pd.to_datetime(df.date)
    df["word_count"] = df.word_count.astype(int)
    return df


def unique_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(key=df.date.dt.strftime("%Y-%m-%d") + "|" + df.text.map(key))
    return df[~df.key.duplicated(keep=False)]


def main() -> None:
    pc = parlacap()
    psp = pd.read_parquet(SPEECHES, columns=["id", "term", "date", "chair", "text", "word_count"])
    psp = psp[psp.term.isin(TERMS) & psp.date.between(pc.date.min(), pc.date.max())]
    ours = pd.concat([pd.read_parquet(f, columns=["id", "CAP_category"]) for f in sorted(TOPICS.glob("*.parquet"))])
    psp = psp.merge(ours.rename(columns={"CAP_category": "ours"}), on="id", how="left")
    m = unique_keys(psp).merge(unique_keys(pc), on="key", suffixes=("", "_pc"))
    same = m.ours == m.CAP_category
    words = m.word_count_pc
    res = {
        "rule": f"extension estimated only if label agreement >= {BAR:.0%} (design §2.2)",
        "psp_speeches_in_overlap": len(psp), "parlacap_speeches": len(pc), "matched": len(m),
        "matched_without_our_label": int(m.ours.isna().sum()),
        "label_agreement": round(float(same.mean()), 4),
        "label_agreement_not_chair": round(float(same[~m.chair].mean()), 4),
        "label_agreement_word_weighted": round(float((same * words).sum() / words.sum()), 4),
        "by_term": {t: round(float(same[m.term == t].mean()), 4) for t in TERMS if (m.term == t).any()},
    }
    res["passes"] = res["label_agreement"] >= BAR
    print(json.dumps(res, indent=2))
    OUT.write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
