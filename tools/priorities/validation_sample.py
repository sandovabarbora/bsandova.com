"""The validation sample of the priorities study (design §2.2): 600 speeches, 500 from ParlaCAP-CZ and 100 from the
psp.cz records of 2004–2013, drawn with probability proportional to words within strata of the assigned label, with
equal expected numbers per stratum. Strata: the ten harmonised topics, the other CAP topics together, Mix and Other
(13). Chair speeches are not in the frame, as they are not in the analysis.

Writes tools/data/priorities/validation/sample.parquet (with the assigned label, the stratum and the inclusion
probability; never shown to the coders) and coder files batch-NN.jsonl with only an anonymous key and the text, cut at
TEXT_WORDS words. No topic share is computed.

    uv run --no-project --with pandas --with pyarrow --with numpy python -I tools/priorities/validation_sample.py
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "tools/data/priorities"
OUT = D / "validation"
SEED, N_PARLACAP, N_EARLY, BATCH, TEXT_WORDS = 20261015, 500, 100, 50, 1500
HARMONISED = {"Macroeconomics": "Economy", "Labor": "Unemployment", "Health": "Health", "Social Welfare": "Pensions",
              "Education": "Education", "Law and Crime": "Crime", "Immigration": "Immigration", "Housing": "Housing",
              "Environment": "Environment and energy", "Energy": "Environment and energy",
              "Defense": "Security and international", "International Affairs": "Security and international"}
STRATA = sorted(set(HARMONISED.values())) + ["Other CAP topics", "Mix", "Other"]


def stratum(label: str) -> str:
    return label if label in ("Mix", "Other") else HARMONISED.get(label, "Other CAP topics")


def pps(frame: pd.DataFrame, n: int, rng) -> pd.DataFrame:
    """Systematic sampling proportional to words within a stratum; units larger than the step are taken with
    certainty, and the inclusion probability of each drawn unit is kept."""
    f = frame.sample(frac=1, random_state=int(rng.integers(1 << 31))).reset_index(drop=True)
    take, rest, k = [], f, n
    while k > 0 and len(rest):
        step = rest.word_count.sum() / k
        big = rest.word_count >= step
        if not big.any():
            break
        take.append(rest[big].assign(pi=1.0))
        k -= int(big.sum())
        rest = rest[~big]
    if k > 0 and len(rest):
        step = rest.word_count.sum() / k
        cum = rest.word_count.cumsum().to_numpy()
        points = rng.uniform(0, step) + step * np.arange(k)
        idx = np.searchsorted(cum, points, side="right")
        take.append(rest.iloc[idx].assign(pi=(k * rest.word_count.iloc[idx] / rest.word_count.sum()).to_numpy()))
    return pd.concat(take)


def draw(frame: pd.DataFrame, n: int, source: str, rng) -> pd.DataFrame:
    frame = frame.assign(stratum=frame.label.map(stratum))
    per, extra = divmod(n, len(STRATA))
    parts = []
    for i, s in enumerate(STRATA):
        g = frame[frame.stratum == s]
        parts.append(pps(g, per + (i < extra), rng))
    return pd.concat(parts).assign(source=source)


def main() -> None:
    rng = np.random.default_rng(SEED)
    cols = ["id", "speaker_role", "word_count", "CAP_category", "text"]
    with zipfile.ZipFile(D / "parlacap/ParlaCAP-CZ_speeches.tsv.zip") as z, z.open(z.namelist()[0]) as f:
        pc = pd.read_csv(f, sep="\t", usecols=cols, dtype=str, keep_default_na=False)
    pc = pc[pc.speaker_role != "Chairperson"].assign(word_count=lambda d: d.word_count.astype(int))
    pc = pc.rename(columns={"CAP_category": "label"})[["id", "label", "word_count", "text"]]
    psp = pd.read_parquet(D / "psp_speeches.parquet", columns=["id", "date", "chair", "word_count", "text"])
    psp = psp[~psp.chair & (psp.date < "2013-11-25")]
    ours = pd.concat([pd.read_parquet(f, columns=["id", "CAP_category"]) for f in sorted((D / "psp_topics").glob("*.parquet"))])
    psp = psp.merge(ours, on="id").rename(columns={"CAP_category": "label"})[["id", "label", "word_count", "text"]]
    s = pd.concat([draw(pc[pc.word_count > 0], N_PARLACAP, "parlacap", rng),
                   draw(psp[psp.word_count > 0], N_EARLY, "psp_2004_2013", rng)], ignore_index=True)
    s = s.sample(frac=1, random_state=SEED).reset_index(drop=True)
    s["key"] = [f"S{i:03d}" for i in range(len(s))]
    OUT.mkdir(parents=True, exist_ok=True)
    s.drop(columns="text").to_parquet(OUT / "sample.parquet")
    for b in range(0, len(s), BATCH):
        with (OUT / f"batch-{b // BATCH + 1:02d}.jsonl").open("w", encoding="utf-8") as f:
            for r in s.iloc[b:b + BATCH].itertuples():
                words = r.text.split()
                f.write(json.dumps({"key": r.key, "words": len(words), "cut": len(words) > TEXT_WORDS,
                                    "text": " ".join(words[:TEXT_WORDS])}, ensure_ascii=False) + "\n")
    print(len(s), "speeches;", s.groupby(["source", "stratum"]).size().unstack(0).to_string())
    print("cut at", TEXT_WORDS, "words:", int((s.word_count > TEXT_WORDS).sum()))


if __name__ == "__main__":
    main()
