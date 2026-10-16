"""Frozen estimation of the priorities design (docs/research/priorities-design.md, signed tag priorities-design):
harmonised topics and spells (§2.4), the static and dynamic PPML models with the split-panel jackknife, windows and
the crosswalk (§4), the wild cluster bootstrap and the randomisation interval (§4 Inference), the labels (§5) and the
checks (§6), for Q1, Q1r, Q2, Q3 and Q4 (§1), on ParlaCAP-CZ alone and on the whole 2004–2025 series (§2.2).

Writes docs/research/priorities-results.json and prints nothing but its path. Run only after the code is frozen:

    OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 nice -n 20 uv run --no-project --with pandas --with pyarrow \
        --with numpy --with scipy python -I tools/priorities/estimate.py

Inference. Both intervals invert a test of β = β0 with the null imposed. The bootstrap is the wild cluster *score*
bootstrap (Kline and Santos 2012; boottest's version for ML models): restricted fit at β0, cluster scores of the
efficient score of β perturbed by Webb weights, a cluster-robust score statistic. For the jackknifed dynamic model and
for Q3's difference the statistic is the same linear combination of the pieces' one-step scores as the estimator is of
the pieces' estimates. The randomisation interval permutes the regressor's topic series across topics and computes
the same score statistic on the null-adjusted outcome (y·exp(−β0·x)), whose null fit does not depend on the
permutation; this is what makes 100 000 permutations per candidate β0 affordable.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import itertools
import json
import math
import re
import zipfile
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import xlogy

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "tools/data/priorities"
OUT = ROOT / "docs/research/priorities-results.json"
VALIDATION = ROOT / "docs/research/priorities-validation.json"

# ---- registered settings (§4, §5) and the choices the design left open (listed in the change log)

SEED = 20261014                     # the design's date; bootstrap uses SEED, permutations SEED + 1
BOOT = 9_999
PERMS = 100_000                     # when K! <= PERMS (eight topics), all K! permutations instead
SESOI = 0.10
MAX_WIDTH_90 = 0.20
WINDOW_DAYS = 182
CHECK_WINDOW_DAYS = 365
COVERAGE = 0.90
SEARCH_LIMIT = 10.0                 # beyond |β0 − β̂| = 10 an interval is reported unbounded
SEARCH_TOL = 1e-4
MACRO_F1_BOUND = 0.50
F1_CHECK = 0.60
WHOLE_END = date(2025, 12, 31)      # "the whole series 2004–2025"
WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])

# ---- §2.4 harmonised topics, in the registered table's order

TOPICS = ("Economy", "Unemployment", "Health", "Pensions", "Education", "Crime", "Immigration", "Housing",
          "Environment and energy", "Security and international")
NT = len(TOPICS)
CAP = {"Economy": ("Macroeconomics",), "Unemployment": ("Labor",), "Health": ("Health",),
       "Pensions": ("Social Welfare",), "Education": ("Education",), "Crime": ("Law and Crime",),
       "Immigration": ("Immigration",), "Housing": ("Housing",), "Environment and energy": ("Environment", "Energy"),
       "Security and international": ("Defense", "International Affairs")}
CAP_TOPIC = {c: TOPICS.index(t) for t, cs in CAP.items() for c in cs}
COFOG = {"Unemployment": ("GF1005",), "Health": ("GF07",), "Pensions": ("GF1002",), "Education": ("GF09",),
         "Crime": ("GF03",), "Housing": ("GF06", "GF1006"), "Environment and energy": ("GF05", "GF0403"),
         "Security and international": ("GF02",)}
SPENDING_TOPICS = tuple(t for t in TOPICS if t in COFOG)
DISCRETIONARY = ("Education", "Crime", "Housing", "Environment and energy", "Security and international")

# Crosswalk of Eurobarometer item labels (normalised by `norm`) to (topic, item). Two labels map to one item where
# only the wording or punctuation differs ("the educational system" / "the education system", "economic situation" /
# "the economic situation"); "cost of living" added to the prices item is a new item, as the design's EB83 change says.
ITEMS = {
    "economic situation": ("Economy", "economic situation"),
    "rising prices inflation": ("Economy", "rising prices / inflation"),
    "rising prices inflation cost of living": ("Economy", "rising prices / inflation / cost of living"),
    "taxation": ("Economy", "taxation"),
    "government debt": ("Economy", "government debt"),
    "unemployment": ("Unemployment", "unemployment"),
    "healthcare system": ("Health", "healthcare system"),
    "health and social security": ("Health", "health and social security"),
    "health": ("Health", "health"),
    "pensions": ("Pensions", "pensions"),
    "educational system": ("Education", "the educational system"),
    "education system": ("Education", "the educational system"),
    "crime": ("Crime", "crime"),
    "immigration": ("Immigration", "immigration"),
    "housing": ("Housing", "housing"),
    "protecting the environment": ("Environment and energy", "protecting the environment"),
    "environment": ("Environment and energy", "the environment"),
    "energy related issues": ("Environment and energy", "energy related issues"),
    "energy": ("Environment and energy", "energy"),
    "environment climate and energy issues": ("Environment and energy", "the environment, climate and energy issues"),
    "environment and climate change": ("Environment and energy", "the environment and climate change"),
    "environment and risks related to climate change": ("Environment and energy",
                                                        "the environment and risks related to climate change"),
    "energy supply": ("Environment and energy", "energy supply"),
    "defence foreign affairs": ("Security and international", "defence / foreign affairs"),
    "terrorism": ("Security and international", "terrorism"),
    "international situation": ("Security and international", "the international situation"),
    "security and defence": ("Security and international", "security and defence"),
    "russia s invasion of ukraine": ("Security and international", "Russia's invasion of Ukraine"),
    "conflict in the middle east": ("Security and international", "the conflict in the Middle East"),
    "threats to democracy": ("Security and international", "threats to democracy"),
}
# Not used (§2.4), plus two arm-B-only items of EB74–76 that the registered table does not list.
UNUSED = {"public transport", "cyprus issue", "other", "none", "dk", "don t know", "climate change",
          "s external influence"}
SPELL_CHANGES = {"Economy": {77, 83, 104}, "Health": {77, 93}, "Environment and energy": {66, 71, 72, 77, 93, 103},
                 "Security and international": {77, 97, 103, 104}}
LAST_WAVE = {"Pensions": 102}
SPLIT_WAVES = (65, 71, 74, 75, 76, 92)
MODE_WAVES = frozenset(range(93, 97))
PANDEMIC_YEARS = frozenset((2020, 2021, 2022))
# Q4 governments (§1). A wave belongs to the government in office on most days of its window after.
GOVERNMENTS = (("Sobotka", date(2014, 1, 29), date(2017, 12, 12)),
               ("Babiš", date(2017, 12, 13), date(2021, 12, 16)),
               ("Fiala", date(2021, 12, 17), date(2025, 12, 14)))
PARTY_GROUPS = ("Coalition", "Opposition")


def norm(label: str) -> str:
    s = re.sub(r"\(.*?\)", " ", label.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"^the ", "", s)


def half(wave: int) -> str:
    """Standard Eurobarometer alternates spring (odd) and autumn (even) waves from EB62 (autumn 2004); the delayed
    pandemic waves (EB94, EB96, EB98 fielded in winter) keep their place in that calendar."""
    return "spring" if wave % 2 else "autumn"


# ---- §2.1 concern, spells (§2.4)

def parse_day(s: str, end: bool) -> date:
    if len(s) == 7:  # month only (EB62–EB74): first day of the start month, last day of the end month
        y, m = int(s[:4]), int(s[5:7])
        if not end:
            return date(y, m, 1)
        return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    return date.fromisoformat(s)


@dataclass
class Concern:
    share: dict            # (topic, wave) -> C, the sum of the topic's item shares
    floor: dict            # wave -> half a respondent, 0.5 / Czech N
    items: dict            # (topic, wave) -> frozenset of items
    spell: dict            # (topic, wave) -> spell id
    starts: dict           # topic -> waves at which a new spell starts (not the topic's first wave)
    dates: dict            # wave -> (fieldwork start, fieldwork end)

    def year(self, wave: int) -> int:
        return self.dates[wave][0].year

    def floored(self, topic: str, wave: int) -> float:
        c = self.share[topic, wave]
        return c if c > 0 else self.floor[wave]


def spells(items: dict) -> tuple[dict, dict]:
    """A spell is a run of consecutive waves with an unchanged item list for the topic."""
    spell, starts = {}, {t: set() for t in TOPICS}
    for t in TOPICS:
        waves = sorted(w for (k, w) in items if k == t)
        n, prev = 0, None
        for w in waves:
            if prev is not None and (items[t, w] != items[t, prev] or w != prev + 1):
                n += 1
                starts[t].add(w)
            spell[t, w] = f"{t}#{n}"
            prev = w
    return spell, starts


def arm_rows(df: pd.DataFrame, arm: str = "A") -> pd.DataFrame:
    """The rows read for a wave: arm A (or B, the check) in split-ballot waves with the rows common to both arms,
    every other wave's single table; the net row of EB92's arm B is not an item."""
    df = df[~df.net_row] if "net_row" in df else df
    split = df.wave.isin(SPLIT_WAVES)
    df = df[(split & df.arm.isin([arm, "all"])) | (~split & (df.arm == "all"))]
    keys = df["item"].map(norm)
    unknown = sorted(set(keys) - set(ITEMS) - UNUSED)
    if unknown:
        raise ValueError(f"items not in the registered crosswalk: {unknown}")
    df = df[keys.isin(set(ITEMS))]
    return df.assign(topic=[ITEMS[norm(i)][0] for i in df["item"]], item_id=[ITEMS[norm(i)][1] for i in df["item"]])


def item_lists(df: pd.DataFrame, arm: str = "A") -> dict:
    rows = arm_rows(df, arm)
    return {(t, int(w)): frozenset(g.item_id) for (t, w), g in rows.groupby(["topic", "wave"])}


def concern_from_table(df: pd.DataFrame, arm: str = "A") -> Concern:
    rows = arm_rows(df, arm)
    share = {}
    for r in rows.itertuples():
        share[r.topic, int(r.wave)] = share.get((r.topic, int(r.wave)), 0.0) + (0.0 if r.share_dash else float(r.share))
    sel = df[(df.wave.isin(SPLIT_WAVES) & df.arm.isin([arm, "all"])) | (~df.wave.isin(SPLIT_WAVES) & (df.arm == "all"))]
    czech_n = {}
    for w, g in sel.groupby("wave"):
        ns = g.czech_n.unique()
        if len(ns) != 1:
            raise ValueError(f"EB{w}: more than one Czech N in the arm read")
        czech_n[int(w)] = float(ns[0])
    first = sel.groupby("wave").fieldwork_start.first()
    last = sel.groupby("wave").fieldwork_end.first()
    dates = {int(w): (parse_day(first[w], False), parse_day(last[w], True)) for w in first.index}
    items = item_lists(df, arm)
    spell, starts = spells(items)
    return Concern(share, {w: 0.5 / n for w, n in czech_n.items()}, items, spell, starts, dates)


def registered_spells_hold(items: dict) -> None:
    """Stop if the data's item lists do not change exactly where §2.4 registered."""
    _, starts = spells(items)
    last_wave = max(w for _, w in items)
    for t in TOPICS:
        if starts[t] != SPELL_CHANGES.get(t, set()):
            raise ValueError(f"{t}: spells start at {sorted(starts[t])}, registered {sorted(SPELL_CHANGES.get(t, set()))}")
        last = max(w for (k, w) in items if k == t)
        if last != LAST_WAVE.get(t, last_wave):
            raise ValueError(f"{t}: last wave EB{last}")


def list_change_waves(con: Concern) -> frozenset:
    out = set().union(*con.starts.values())
    for t, w in LAST_WAVE.items():
        if w + 1 in con.dates:
            out.add(w + 1)
    return frozenset(out)


def load_concern(arm: str = "A") -> Concern:
    return concern_from_table(pd.read_parquet(D / "concern.parquet"), arm)


# ---- §4 windows and coverage

def windows(dates: dict, days: int = WINDOW_DAYS, cap: bool = True) -> dict:
    """The window after wave t: from the day after its fieldwork ends, `days` days long, cut at the day before the next
    wave's fieldwork starts; the window before t: the same length, ending the day before its fieldwork starts."""
    out = {}
    for w, (start, end) in dates.items():
        a0, a1 = end + timedelta(days=1), end + timedelta(days=days)
        if cap and w + 1 in dates:
            a1 = min(a1, dates[w + 1][0] - timedelta(days=1))
        length = (a1 - a0).days + 1
        out[w] = {"after": (a0, a1), "before": (start - timedelta(days=length), start - timedelta(days=1))}
    return out


def coverage(win: tuple[date, date], span: tuple[date, date]) -> float:
    lo, hi = max(win[0], span[0]), min(win[1], span[1])
    return max(0, (hi - lo).days + 1) / ((win[1] - win[0]).days + 1)


def covered_waves(wins: dict, span: tuple[date, date]) -> list[int]:
    return sorted(w for w, v in wins.items()
                  if coverage(v["after"], span) >= COVERAGE and coverage(v["before"], span) >= COVERAGE)


def wave_government(win_after: tuple[date, date]) -> str | None:
    days = {}
    for name, g0, g1 in GOVERNMENTS:
        days[name] = coverage(win_after, (g0, g1))
    best = max(days, key=days.get)
    return best if days[best] > 0.5 else None


# ---- §2.2 attention

class Corpus:
    """Daily sums of the numerator per topic and of the denominator, for window shares by cumulative sums."""

    def __init__(self, day: np.ndarray, num: np.ndarray, den: np.ndarray, span: tuple[date, date]):
        self.span = span
        self.origin = span[0]
        n = (span[1] - span[0]).days + 1
        idx = np.asarray(day, dtype=np.int64)
        keep = (idx >= 0) & (idx < n)
        self.num = np.zeros((n + 1, NT))
        self.den = np.zeros(n + 1)
        np.add.at(self.num, idx[keep] + 1, num[keep])
        np.add.at(self.den, idx[keep] + 1, den[keep])
        self.num, self.den = self.num.cumsum(0), self.den.cumsum()

    @classmethod
    def from_speeches(cls, df: pd.DataFrame, span: tuple[date, date]) -> "Corpus":
        """df: date, value (words or 1), topic (index into TOPICS or −1 for the other kept CAP topics)."""
        day = (pd.to_datetime(df.date).dt.normalize() - pd.Timestamp(span[0])).dt.days.to_numpy()
        num = np.zeros((len(df), NT))
        t = df.topic.to_numpy()
        on = t >= 0
        num[np.flatnonzero(on), t[on]] = df.value.to_numpy()[on]
        return cls(day, num, df.value.to_numpy(dtype=float), span)

    def shares(self, d0: date, d1: date) -> tuple[np.ndarray, float]:
        """Topic shares of the window and the half-unit floor (0.5 ÷ the window's denominator)."""
        n = len(self.den) - 1
        i0 = min(max((d0 - self.origin).days, 0), n)
        i1 = min(max((d1 - self.origin).days + 1, 0), n)
        den = self.den[i1] - self.den[i0]
        if den <= 0:
            return np.full(NT, np.nan), np.nan
        return (self.num[i1] - self.num[i0]) / den, 0.5 / den


def parlacap_speeches(chair: bool = False) -> pd.DataFrame:
    if not chair:
        df = pd.read_parquet(D / "attention.parquet", columns=["date", "word_count", "CAP_category", "party_status"])
    else:
        cols = ["date", "speaker_role", "word_count", "CAP_category", "party_status"]
        with zipfile.ZipFile(D / "parlacap/ParlaCAP-CZ_speeches.tsv.zip") as z, z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, sep="\t", usecols=cols, dtype=str, na_values=["-"], keep_default_na=False)
        df = df[~df.CAP_category.isin(["Mix", "Other"])]
        df = df.assign(word_count=df.word_count.astype(int), date=pd.to_datetime(df.date))
    return pd.DataFrame({"date": pd.to_datetime(df.date), "words": df.word_count.astype(float).to_numpy(),
                         "cap": df.CAP_category.to_numpy(), "party": df.party_status.to_numpy()})


def psp_speeches(chair: bool = False, mix: bool = False) -> pd.DataFrame:
    s = pd.read_parquet(D / "psp_speeches.parquet", columns=["id", "date", "chair", "word_count"])
    lab = pd.concat([pd.read_parquet(f, columns=["id", "CAP_category", "CAP_top"])
                     for f in sorted((D / "psp_topics").glob("part-*.parquet"))])
    s = s.merge(lab, on="id", how="inner")
    cap = np.where(mix & (s.CAP_category == "Mix"), s.CAP_top, s.CAP_category)
    keep = ~pd.Series(cap).isin(["Mix", "Other"]).to_numpy() & (chair | ~s.chair.to_numpy())
    return pd.DataFrame({"date": pd.to_datetime(s.date[keep]).to_numpy(), "words": s.word_count[keep].astype(float).to_numpy(),
                         "cap": cap[keep], "party": np.nan})


def series_speeches(series: str, pc_span: tuple[date, date], chair: bool = False, mix: bool = False) -> pd.DataFrame:
    """ParlaCAP alone: its own speeches. Whole series: ParlaCAP within its span, the psp.cz records outside it, to
    the end of 2025. ParlaCAP carries no top topic for Mix speeches, so the Mix check reads our psp.cz run of the
    same classifier throughout."""
    lo, hi = pd.Timestamp(pc_span[0]), pd.Timestamp(pc_span[1])
    if mix:
        df = psp_speeches(chair, True)
        if series == "parlacap":
            return df[df.date.between(lo, hi)]
        return df[df.date <= pd.Timestamp(WHOLE_END)]
    pc = parlacap_speeches(chair)
    if series == "parlacap":
        return pc
    ps = psp_speeches(chair, False)
    ps = ps[((ps.date < lo) | (ps.date > hi)) & (ps.date <= pd.Timestamp(WHOLE_END))]
    return pd.concat([pc, ps], ignore_index=True)


def topic_codes(cap: pd.Series) -> np.ndarray:
    return cap.map(CAP_TOPIC).fillna(-1).astype(int).to_numpy()


def corpus(df: pd.DataFrame, span: tuple[date, date], unit: str = "words") -> Corpus:
    value = df.words.to_numpy() if unit == "words" else np.ones(len(df))
    return Corpus.from_speeches(pd.DataFrame({"date": df.date.to_numpy(), "value": value,
                                              "topic": topic_codes(df.cap)}), span)


# ---- the validation sample: F1 per topic and the confusion matrix (§2.2, §6)

CLASSES = TOPICS + ("Other CAP topics",)        # what a kept speech can be labelled
REFS = CLASSES + ("Other",)                     # what the reference can say


def coded(model: str) -> dict:
    return {r["key"]: r["topic"] for f in sorted((D / "validation").glob(f"coding-{model}-*.json"))
            for r in json.loads(f.read_text(encoding="utf-8"))}


def confusion() -> dict[str, np.ndarray]:
    """Per frame, q[j, k]: the word- and inverse-inclusion-weighted share of speeches the classifier labelled j whose
    reference topic is k (the validation's reference: the coders' topic where they agree, else the adjudicated one)."""
    v = D / "validation"
    s = pd.read_parquet(v / "sample.parquet")
    a, b = coded("sonnet"), coded("opus")
    adj = {**json.loads((v / "adjudication-assistant.json").read_text()),
           **json.loads((v / "adjudication-author.json").read_text())}
    s["ref"] = [a[k] if a[k] == b[k] else adj[k] for k in s.key]

    def cls(lab: str, ref: bool) -> str:
        if lab in CAP_TOPIC:
            return TOPICS[CAP_TOPIC[lab]]
        if lab == "Other" and ref:
            return "Other"
        return "Other CAP topics"

    s = s[~s.label.isin(["Mix", "Other"])]
    s = s.assign(j=[cls(x, False) for x in s.label], k=[cls(x, True) for x in s.ref], wt=s.word_count / s.pi)
    out = {}
    for frame, g in s.groupby("source"):
        q = np.zeros((len(CLASSES), len(REFS)))
        for j, c in enumerate(CLASSES):
            h = g[g.j == c]
            if h.wt.sum() <= 0:
                q[j, REFS.index(c)] = 1.0  # no validated speech of this label in the frame: no correction
                continue
            for k, r in enumerate(REFS):
                q[j, k] = h.wt[h.k == r].sum() / h.wt.sum()
        out[frame] = q
    return out


def corrected_corpus(df: pd.DataFrame, span: tuple[date, date], q: dict, pc_start: date) -> Corpus:
    """Attention corrected by the confusion matrix: each labelled word is spread over the reference topics; words
    whose reference is Other leave the denominator. psp.cz before ParlaCAP uses the 2004–2013 frame, the rest the
    ParlaCAP frame."""
    t = topic_codes(df.cap)
    j = np.where(t >= 0, t, NT)
    early = (pd.to_datetime(df.date) < pd.Timestamp(pc_start)).to_numpy()
    qq = np.where(early[:, None], q["psp_2004_2013"][j], q["parlacap"][j])
    w = df.words.to_numpy()
    day = (pd.to_datetime(df.date).dt.normalize() - pd.Timestamp(span[0])).dt.days.to_numpy()
    return Corpus(day, w[:, None] * qq[:, :NT], w * (1 - qq[:, -1]), span)


# ---- §2.3 spending and the controls of the Q2 check

def load_spending() -> dict:
    sp = pd.read_parquet(D / "spending.parquet")
    wide = sp.pivot_table(index="year", columns="cofog", values="value", aggfunc="sum")
    out = {}
    for t, codes in COFOG.items():
        if not all(c in wide for c in codes):
            continue
        s = wide[list(codes)].sum(axis=1, min_count=len(codes)) / wide["TOTAL"]
        for y, v in s.dropna().items():
            out[t, int(y)] = float(v)
    return out


def eurostat_series(path: Path) -> dict:
    js = json.loads(path.read_text())
    dims, size = js["id"], js["size"]
    if any(n != 1 for d, n in zip(dims, size) if d != "time"):
        raise ValueError(f"{path.name}: more than one series")
    yrs = {i: int(k) for k, i in js["dimension"]["time"]["category"]["index"].items()}
    return {yrs[int(i)]: float(v) for i, v in js["value"].items()}


# ---- panels (§1, §4)

def flog(v, floor) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return np.log(np.where(v > 0, v, floor))


def wave_panel(con: Concern, corp: Corpus, wins: dict, waves: list[int], topics=TOPICS) -> pd.DataFrame:
    rows = []
    for t in waves:
        post, fpost = corp.shares(*wins[t]["after"])
        pre, fpre = corp.shares(*wins[t]["before"])
        if np.isnan(fpost) or np.isnan(fpre):
            continue
        for i, k in enumerate(TOPICS):
            if k not in topics or (k, t) not in con.share:
                continue
            nxt = (k, t + 1) in con.share
            rows.append({"topic": k, "code": i, "time": t, "spell": con.spell[k, t], "half": half(t),
                         "topic_half": f"{k}|{half(t)}", "first_of_spell": t in con.starts[k],
                         "c": con.share[k, t], "c_floor": con.floor[t],
                         "a_post": post[i], "a_post_floor": fpost, "a_pre": pre[i], "a_pre_floor": fpre,
                         "c_next": con.share[k, t + 1] if nxt else np.nan,
                         "c_next_floor": con.floor.get(t + 1, np.nan),
                         "spell_next": con.spell[k, t + 1] if nxt else None})
    return pd.DataFrame(rows)


def year_shares(corp: Corpus, years) -> dict:
    out = {}
    for y in years:
        win = (date(y, 1, 1), date(y, 12, 31))
        if coverage(win, corp.span) >= COVERAGE:
            out[y] = corp.shares(*win)
    return out


def cbar(con: Concern, topic: str, year: int, drop_waves=frozenset()) -> tuple[float, str] | None:
    """C̄(k, y): the mean of the year's floored C within one spell; where the year's waves straddle a spell change,
    the waves of the spell of the year's last wave."""
    ws = sorted(w for w in con.dates if con.year(w) == year and (topic, w) in con.share and w not in drop_waves)
    if not ws:
        return None
    sp = con.spell[topic, ws[-1]]
    vals = [con.floored(topic, w) for w in ws if con.spell[topic, w] == sp]
    return float(np.mean(vals)), sp


def year_panel(con: Concern, spend: dict, corp: Corpus | None = None, topics=SPENDING_TOPICS,
               drop_waves=frozenset()) -> pd.DataFrame:
    years = sorted({con.year(w) for w in con.dates})
    att = year_shares(corp, range(years[0], years[-1] + 2)) if corp is not None else {}
    rows = []
    for k in topics:
        i = TOPICS.index(k)
        for y in years:
            cb = cbar(con, k, y, drop_waves)
            if cb is None:
                continue
            r = {"topic": k, "code": i, "time": y, "spell": cb[1], "cbar": cb[0], "cbar_floor": np.nan,
                 "s": spend.get((k, y), np.nan), "s_next": spend.get((k, y + 1), np.nan), "s_floor": np.nan,
                 "s_next_floor": np.nan}
            a, a1 = att.get(y), att.get(y + 1)
            r.update({"a": a[0][i] if a else np.nan, "a_floor": a[1] if a else np.nan,
                      "a_next": a1[0][i] if a1 else np.nan, "a_next_floor": a1[1] if a1 else np.nan})
            rows.append(r)
    return pd.DataFrame(rows)


# ---- estimation core

@dataclass
class Spec:
    y: np.ndarray
    x: np.ndarray
    controls: np.ndarray            # (n, p)
    fe: tuple                       # label arrays, one per fixed-effect dimension
    cluster: np.ndarray             # topic code (0..NT−1)
    time: np.ndarray                # wave or year: the jackknife's halves, the randomisation's grid
    family: str = "poisson"
    w: np.ndarray | None = None
    xgrid: pd.DataFrame | None = None  # regressor by topic code × time, for the randomisation
    floored: dict = field(default_factory=dict)  # zero cells set to the half-unit floor before the log, per column

    def __post_init__(self):
        self.controls = np.asarray(self.controls, dtype=float).reshape(len(self.y), -1)
        if self.w is None:
            self.w = np.ones(len(self.y))

    def subset(self, mask: np.ndarray) -> "Spec":
        return replace(self, y=self.y[mask], x=self.x[mask], controls=self.controls[mask],
                       fe=tuple(f[mask] for f in self.fe), cluster=self.cluster[mask], time=self.time[mask],
                       w=self.w[mask])


def independent(X: np.ndarray, tol: float = 1e-9) -> np.ndarray:
    """Columns kept left to right, dropping any in the span of those before (greedy Gram–Schmidt)."""
    keep, Q = [], np.zeros((X.shape[0], 0))
    for j in range(X.shape[1]):
        v = X[:, j].astype(float)
        nv = np.linalg.norm(v)
        if nv == 0:
            keep.append(False)
            continue
        r = v - Q @ (Q.T @ v)
        r = r - Q @ (Q.T @ r)
        ok = np.linalg.norm(r) > tol * nv * 1e3 if Q.shape[1] else True
        keep.append(bool(ok))
        if ok:
            Q = np.column_stack([Q, r / np.linalg.norm(r)])
    return np.array(keep)


def design(spec: Spec, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """[x, controls, dummies of every fixed effect] on the rows of mask, collinear columns dropped (x kept first),
    and rows of fixed-effect groups whose outcome is all zero dropped (PPML separation)."""
    rows = np.flatnonzero(mask)
    if spec.family == "poisson":
        while True:
            bad = np.zeros(len(rows), bool)
            for f in spec.fe:
                lab = pd.Series(f[rows])
                tot = pd.Series(spec.y[rows]).groupby(lab.values).transform("sum").to_numpy()
                bad |= tot <= 0
            if not bad.any():
                break
            rows = rows[~bad]
    cols = [spec.x[rows][:, None], spec.controls[rows]]
    for f in spec.fe:
        codes, _ = pd.factorize(pd.Series(f[rows]).astype(str))
        cols.append(np.eye(codes.max() + 1)[codes])
    X = np.column_stack(cols)
    keep = independent(X)
    if not keep[0]:
        raise ValueError("the regressor is collinear with the fixed effects")
    return X[:, keep], rows


def fit(y, X, offset, w, family, start=None, maxit=200, tol=1e-11):
    """Coefficients and fitted mean; Poisson pseudo-ML by iteratively reweighted least squares with step-halving.
    A warm start (the nuisance fit at a neighbouring β0) that fails falls back to a cold start; a cold start that
    fails raises FloatingPointError, which the interval search reads as no rejection."""
    if family == "gaussian":
        sw = np.sqrt(w)
        b = np.linalg.lstsq(X * sw[:, None], (y - offset) * sw, rcond=None)[0]
        return b, offset + X @ b
    if start is not None:
        try:
            return _ppml(y, X, offset, w, start, maxit, tol)
        except FloatingPointError:
            pass
    return _ppml(y, X, offset, w, None, maxit, tol)


IRLS_NOT_CONVERGED = [0]


def _ppml(y, X, offset, w, start, maxit, tol):
    top = math.log(max(float(y.max()), 1e-300)) + 30
    if start is not None:
        eta = offset + X @ start
        if not np.all(np.isfinite(eta)) or eta.max() > top or eta.min() < -500:
            raise FloatingPointError("warm start out of range")
        b = start
    else:
        eta, b = np.log((y + y.mean()) / 2), None
    mu = np.exp(eta)

    def dev(m):
        return 2 * np.sum(w * (xlogy(y, y) - xlogy(y, m) - (y - m)))

    d_old = dev(mu) if b is not None else np.inf
    converged = False
    with np.errstate(all="ignore"):
        for _ in range(maxit):
            z = eta - offset + (y - mu) / mu
            ww = w * mu
            try:
                b_new = np.linalg.solve(X.T @ (X * ww[:, None]), X.T @ (ww * z))
            except np.linalg.LinAlgError:
                b_new = np.linalg.lstsq(X * np.sqrt(ww)[:, None], z * np.sqrt(ww), rcond=None)[0]
            found = False
            for _ in range(50):
                eta_new = offset + X @ b_new
                if np.all(np.isfinite(eta_new)) and eta_new.max() < top and eta_new.min() > -700:
                    mu_new = np.exp(eta_new)
                    d_new = dev(mu_new)
                    if np.isfinite(d_new) and (b is None or d_new <= d_old * (1 + 1e-12) + 1e-300):
                        found = True
                        break
                if b is None or not np.all(np.isfinite(b_new)):
                    raise FloatingPointError("IRLS step out of range")
                b_new = (b_new + b) / 2
            if not found:
                if b is None:
                    raise FloatingPointError("IRLS made no progress")
                converged = True  # no decrease within 50 halvings: at the optimum to working precision
                break
            b, eta, mu = b_new, eta_new, mu_new
            if abs(d_new - d_old) <= tol * (abs(d_new) + 1e-8):
                converged = True
                break
            d_old = d_new
    if not converged:
        IRLS_NOT_CONVERGED[0] += 1
    return b, mu


@dataclass
class Piece:
    c: float
    X: np.ndarray
    y: np.ndarray
    w: np.ndarray
    cluster: np.ndarray
    rows: np.ndarray
    family: str
    start: np.ndarray | None = None

    def estimate(self) -> float:
        b, _ = fit(self.y, self.X, np.zeros(len(self.y)), self.w, self.family)
        return float(b[0])

    def null_fit(self, b0: float, y: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Fitted mean with β fixed at b0 (offset b0·x), the nuisance parameters re-estimated."""
        y = self.y if y is None else y
        Z, x = self.X[:, 1:], self.X[:, 0]
        coef, mu = fit(y, Z, b0 * x, self.w, self.family, start=self.start)
        if np.all(np.isfinite(coef)):
            self.start = coef
        return mu, y - mu

    def omega(self, mu):
        return self.w * (mu if self.family == "poisson" else 1.0)

    def one_step(self, b0: float) -> tuple[np.ndarray, np.ndarray]:
        """From the null fit: ψ, the clusters' contributions to the one-step update of β (s̃_g ÷ D, s̃ the efficient
        score of β), and C, with C·w the clusters' scores of the re-estimated (one-step) residuals when cluster h's
        null residuals are multiplied by w_h. With w = 1, ψ·1 ÷ ‖C·1‖ is the cluster-robust (CR3-type) t of β̂ − b0;
        with Webb draws it is the wild cluster restricted bootstrap's t (the PPML analogue of Roodman et al.'s fast
        WCR)."""
        mu, e = self.null_fit(b0)
        om = self.omega(mu)
        X, Z, x = self.X, self.X[:, 1:], self.X[:, 0]
        xt = x - Z @ np.linalg.solve(Z.T @ (Z * om[:, None]), Z.T @ (om * x))
        D = np.sum(om * xt ** 2)
        psi = np.bincount(self.cluster, self.w * xt * e, minlength=NT) / D
        onehot = (self.cluster[:, None] == np.arange(NT)[None, :]).astype(float)
        E_ = e[:, None] * onehot                                  # residuals of cluster h in column h
        dmu = mu if self.family == "poisson" else np.ones_like(mu)
        H = X.T @ (X * om[:, None])
        U = E_ - dmu[:, None] * (X @ np.linalg.solve(H, X.T @ (self.w[:, None] * E_)))
        C = onehot.T @ ((self.w * xt)[:, None] * U) / D
        # Leave-one-cluster-out (CR3-type) scaling of the residualised scores: cluster g's score is divided by
        # (D − D_g) instead of D, D_g its own information on β after partialling out the nuisance. Adopted after the
        # size simulation with topic-specific noise scales rejected 0.15 at a nominal 0.10 (test_estimate.py).
        Dg = np.bincount(self.cluster, om * xt ** 2, minlength=NT)
        C = C * (D / np.maximum(D - Dg, 1e-3 * D))[:, None]
        return psi, C


def halves(time: np.ndarray, jackknife: bool) -> list[tuple[float, np.ndarray]]:
    """Split-panel jackknife of Dhaene and Jochmans (2015, Review of Economic Studies 82(3), section 3):
    β̃ = 2·β̂ − ½(β̂₁ + β̂₂), with the halves {1..T/2} and {T/2+1..T}; for odd T the halves overlap in the middle
    period, {1..⌈T/2⌉} and {⌊T/2⌋+1..T}."""
    every = np.ones(len(time), bool)
    if not jackknife:
        return [(1.0, every)]
    ts = np.sort(np.unique(time))
    n = len(ts)
    first, second = ts[:(n + 1) // 2], ts[n // 2:]
    return [(2.0, every), (-0.5, np.isin(time, first)), (-0.5, np.isin(time, second))]


class Equation:
    def __init__(self, spec: Spec, jackknife: bool):
        self.spec, self.jackknife = spec, jackknife
        self._pieces, self._est = None, None

    @property
    def pieces(self) -> list[Piece]:
        if self._pieces is None:
            self._pieces = []
            for c, m in halves(self.spec.time, self.jackknife):
                X, rows = design(self.spec, m)
                s = self.spec
                self._pieces.append(Piece(c, X, s.y[rows], s.w[rows], s.cluster[rows], rows, s.family))
        return self._pieces

    def estimate(self) -> float:
        if self._est is None:
            self._parts = [p.estimate() for p in self.pieces]
            self._est = float(sum(p.c * b for p, b in zip(self.pieces, self._parts)))
        return self._est

    def one_step(self, b0: float) -> tuple[np.ndarray, np.ndarray]:
        psi, C = np.zeros(NT), np.zeros((NT, NT))
        for p in self.pieces:
            ps, cs = p.one_step(b0)
            psi, C = psi + p.c * ps, C + p.c * cs
        return psi, C

    def describe(self) -> dict:
        self.estimate()
        out = {"estimate": self._est, "n": int(len(self.spec.y)), "topics": int(len(np.unique(self.spec.cluster))),
               "periods": [int(t) for t in np.unique(self.spec.time)], "floored_cells": dict(self.spec.floored),
               "x_mean": float(np.mean(self.spec.x)), "y_mean": float(np.mean(self.spec.y))}
        if self.jackknife:
            out["uncorrected"] = self._parts[0]
            out["halves"] = self._parts[1:]
        return out


class Target:
    """Σ sign·β_e over one equation (Q1, Q1r, Q2, Q4) or two (Q3: attention − spending)."""

    def __init__(self, eqs: list[tuple[float, Equation]]):
        self.eqs = eqs
        self._proj = None

    def estimate(self) -> float:
        return float(sum(s * e.estimate() for s, e in self.eqs))

    def restricted(self, theta0: float) -> list[float]:
        """Equation-level values under the null Σ sign·β_e = θ0: θ0 itself for one equation; for two, the
        minimum-distance projection of the estimates with their cluster-robust covariance."""
        if len(self.eqs) == 1:
            return [theta0]
        if self._proj is None:
            est = np.array([e.estimate() for _, e in self.eqs])
            psi = np.column_stack([e.one_step(b)[0] for (_, e), b in zip(self.eqs, est)])
            self._proj = (est, psi.T @ psi, np.array([s for s, _ in self.eqs]))
        est, V, R = self._proj
        gap = R @ est - theta0
        return list(est - V @ R * gap / (R @ V @ R))

    def psi(self, theta0: float) -> tuple[np.ndarray, np.ndarray]:
        psi, C = np.zeros(NT), np.zeros((NT, NT))
        for (s, e), b in zip(self.eqs, self.restricted(theta0)):
            ps, cs = e.one_step(b)
            psi, C = psi + s * ps, C + s * cs
        return psi, C


def webb_weights(n: int | None = None, seed: int = SEED) -> np.ndarray:
    return np.random.default_rng(seed).choice(WEBB, size=(BOOT if n is None else n, NT))


def boot_pvalue(target: Target, theta0: float, W: np.ndarray) -> float:
    psi, C = target.psi(theta0)
    one = np.ones(NT)
    den = np.linalg.norm(C @ one)
    t = float(psi @ one) / den if den > 0 else 0.0
    num = W @ psi
    dens = np.linalg.norm(W @ C.T, axis=1)
    tb = np.divide(num, dens, out=np.zeros_like(num), where=dens > 0)
    return float(np.mean(np.abs(tb) >= abs(t) - 1e-12))


# ---- the randomisation interval

def permutations(k: int, n: int | None = None, seed: int = SEED + 1) -> tuple[np.ndarray, bool]:
    """All k! permutations when there are at most n, else n drawn uniformly (with replacement)."""
    n = PERMS if n is None else n
    if math.factorial(k) <= n:
        return np.array(list(itertools.permutations(range(k)))), True
    rng = np.random.default_rng(seed)
    return rng.permuted(np.tile(np.arange(k), (n, 1)), axis=1), False


def ri_subset(spec: Spec) -> tuple[Spec, list[int]]:
    """Rows at times where every topic of the equation has the regressor, so that any topic's series can be given
    to any other topic."""
    codes = np.unique(spec.cluster)
    g = spec.xgrid.loc[codes]
    full = [t for t in g.columns if g[t].notna().all()]
    return spec.subset(np.isin(spec.time, full)), [int(t) for t in full]


class Randomisation:
    def __init__(self, target: Target, perms: np.ndarray, exact: bool):
        self.target, self.perms, self.exact = target, perms, exact
        self.codes = np.unique(np.concatenate([e.spec.cluster for _, e in target.eqs]))
        for _, e in target.eqs:
            if not np.array_equal(np.unique(e.spec.cluster), self.codes):
                raise ValueError("equations of one target must have the same topics")

    def piece_terms(self, eq: Equation, p: Piece, b0: float):
        spec, K = eq.spec, len(self.codes)
        x = p.X[:, 0]
        y_adj = p.y * np.exp(-b0 * x) if p.family == "poisson" else p.y - b0 * x
        mu, e = p.null_fit(0.0, y_adj)
        om = p.omega(mu)
        Z = p.X[:, 1:]
        M = np.eye(len(x)) - Z @ np.linalg.solve(Z.T @ (Z * om[:, None]), (Z * om[:, None]).T)
        grid = spec.xgrid.loc[self.codes]
        tpos = grid.columns.get_indexer(spec.time[p.rows])
        kpos = np.searchsorted(self.codes, p.cluster)
        src = grid.to_numpy()[:, tpos]                      # (K sources, n)
        V = (src[None, :, :] * (kpos[None, None, :] == np.arange(K)[:, None, None])).reshape(K * K, -1)
        G = V @ M.T                                         # row k*K+j: x̃ when topic k is given source j's series
        onehot = (kpos[:, None] == np.arange(K)[None, :]).astype(float)
        a = G @ (onehot * (p.w * e)[:, None])               # (K², K): cluster scores
        B = (G * om[None, :]) @ G.T                         # (K², K²): pieces of D
        return a, B

    def pvalue(self, theta0: float, chunk: int = 10_000) -> float:
        K = len(self.codes)
        perms = np.vstack([np.arange(K)[None, :], self.perms])
        psi = np.zeros((len(perms), K))
        for (s, eq), b0 in zip(self.target.eqs, self.target.restricted(theta0)):
            for p in eq.pieces:
                a, B = self.piece_terms(eq, p, b0)
                for i in range(0, len(perms), chunk):
                    idx = np.arange(K)[None, :] * K + perms[i:i + chunk]
                    sc = a[idx].sum(axis=1)
                    Dn = B[idx[:, :, None], idx[:, None, :]].sum(axis=(1, 2))
                    psi[i:i + chunk] += s * p.c * sc / Dn[:, None]
        den = np.sqrt((psi ** 2).sum(1))
        T = np.divide(psi.sum(1), den, out=np.zeros(len(psi)), where=den > 0)
        hits = np.abs(T[1:]) >= abs(T[0]) - 1e-12
        if self.exact:
            return float(hits.mean())
        return float((1 + hits.sum()) / (1 + len(hits)))


# ---- intervals by test inversion and the labels (§5)

def invert(pfun, est: float, alpha: float, start: tuple[float, float] | None = None) -> tuple[float, float]:
    """{θ0 : p(θ0) > α}, searched outward from the estimate: steps doubling from 0.01, then bisection. A p-value
    that cannot be computed (a failed fit) makes that side unbounded. If the estimate itself is rejected, a grid of
    est ± 2 in steps of 0.01 is scanned and the interval spans the accepted points; with none accepted the
    interval is degenerate (nan, nan), which the labels read as underpowered."""
    cache = {}

    def p(t):
        if t not in cache:
            try:
                cache[t] = float(pfun(t))
            except (np.linalg.LinAlgError, FloatingPointError, ValueError):
                cache[t] = np.nan
        return cache[t]

    if start is None or any(np.isnan(b) for b in start):
        start = None
        p0 = p(est)
        if not p0 > alpha:
            grid = est + np.round(np.arange(-200, 201) * 0.01, 2)
            ps = np.array([p(t) for t in grid])
            if np.isnan(ps).any():
                return -math.inf, math.inf
            ok = grid[ps > alpha]
            if not len(ok):
                return math.nan, math.nan
            lo = -math.inf if ok.min() == grid[0] else float(ok.min())
            hi = math.inf if ok.max() == grid[-1] else float(ok.max())
            return lo, hi

    bounds = []
    for side in (-1, 1):
        inner = est if start is None else start[(side + 1) // 2]
        if not np.isfinite(inner):
            bounds.append(side * math.inf)
            continue
        step, outer, unbounded = 0.01, None, False
        while abs(inner + side * step - est) <= SEARCH_LIMIT:
            t = inner + side * step
            pv = p(t)
            if np.isnan(pv):
                unbounded = True
                break
            if pv <= alpha:
                outer = t
                break
            inner, step = t, step * 2
        if outer is None or unbounded:
            bounds.append(side * math.inf)
            continue
        while abs(outer - inner) > SEARCH_TOL:
            mid = (inner + outer) / 2
            pv = p(mid)
            if np.isnan(pv):
                unbounded = True
                break
            if pv <= alpha:
                outer = mid
            else:
                inner = mid
        bounds.append(side * math.inf if unbounded else (inner + outer) / 2)
    return bounds[0], bounds[1]


def width(ci) -> float:
    return ci[1] - ci[0]


def hull(a, b) -> tuple[float, float]:
    """The registered "wider" interval: the hull of the two methods' intervals; a degenerate (nan) interval makes
    the hull degenerate."""
    if any(np.isnan(v) for v in (*a, *b)):
        return math.nan, math.nan
    return min(a[0], b[0]), max(a[1], b[1])


def label(ci90, ci95) -> str:
    """§5, in the registered order."""
    lo90, hi90 = ci90
    lo95, _ = ci95
    if not width(ci90) <= MAX_WIDTH_90 or np.isnan(lo95):
        return "underpowered"
    if lo90 >= -SESOI and hi90 <= SESOI:
        return "not supported"
    if lo95 > SESOI:
        return "supported"
    if lo95 > 0:
        return "positive, possibly small"
    return "inconclusive"


def combined(static: str, dynamic: str) -> str:
    return static if static == dynamic else "model-dependent"


def intervals(target: Target, W: np.ndarray, randomisation: bool = True, n_perms: int | None = None) -> dict:
    est = target.estimate()
    pb = lambda t: boot_pvalue(target, t, W)
    b90 = invert(pb, est, 0.10)
    b95 = invert(pb, est, 0.05, start=b90)
    out = {"estimate": est, "wild": {"90": list(b90), "95": list(b95)}, "label_wild": label(b90, b95)}
    if len(target.eqs) == 1:
        out.update(target.eqs[0][1].describe())
    else:
        out["components"] = [e.describe() for _, e in target.eqs]
    if not randomisation:
        return out
    try:
        eqs, times = [], None
        for s, e in target.eqs:
            sub, times = ri_subset(e.spec)
            eqs.append((s, Equation(sub, e.jackknife)))
        rt = Target(eqs)
        perms, exact = permutations(len(np.unique(eqs[0][1].spec.cluster)), n_perms)
        ri = Randomisation(rt, perms, exact)
        rest = rt.estimate()
        r90 = invert(ri.pvalue, rest, 0.10)
        r95 = invert(ri.pvalue, rest, 0.05, start=r90)
    except (ValueError, KeyError, np.linalg.LinAlgError, FloatingPointError) as err:
        out["randomisation"] = {"error": f"{type(err).__name__}: {err}"}
        out["label"] = "not estimable (randomisation interval failed)"
        return out
    out["randomisation"] = {"90": list(r90), "95": list(r95), "estimate": rest, "periods": times,
                            "permutations": int(len(perms)), "all_permutations": exact}
    out["label_randomisation"] = label(r90, r95)
    used = {"90": hull(b90, r90), "95": hull(b95, r95)}
    out["used"] = {k: list(v) for k, v in used.items()}
    out["label"] = label(used["90"], used["95"])
    return out


# ---- specs per question

@dataclass(frozen=True)
class Variant:
    corpus: str = "words"           # words | speeches | chair | mix | corrected
    window: str = "half"            # half | year
    arm: str = "A"
    drop_waves: frozenset = frozenset()
    drop_years: frozenset = frozenset()
    form: str = "ppml"              # ppml | log | levels
    weighted: bool = False
    topics: tuple = TOPICS
    controls: bool = False
    change_in_share: bool = False


def make_spec(df: pd.DataFrame, y: str, x: str, lag: str | None, fe: tuple, form: str, weights=None,
              centre_by: str | None = None) -> Spec:
    """centre_by: the randomisation grid holds each topic's regressor centred within that topic's spells, so that a
    series given to another topic does not carry its own spells' level shifts (the model's spell effects absorb the
    centring for the topic's own series)."""
    floored = {}

    def val(col, logged):
        v = df[col].to_numpy(dtype=float)
        if not logged:
            return v
        floored[col] = int(np.sum(~(v > 0)))
        return flog(v, df[col + "_floor"].to_numpy(dtype=float))

    if form == "ppml":
        yy, xx, ll, fam = val(y, False), val(x, True), (val(lag, True) if lag else None), "poisson"
    elif form == "log":
        yy, xx, ll, fam = val(y, True), val(x, True), (val(lag, True) if lag else None), "gaussian"
    else:
        yy, xx, ll, fam = val(y, False), val(x, False), (val(lag, False) if lag else None), "gaussian"
    ctl = np.zeros((len(df), 0)) if ll is None else ll[:, None]
    gx = xx
    if centre_by is not None:
        gx = xx - pd.Series(xx).groupby([df.code.to_numpy(), df[centre_by].astype(str).to_numpy()]).transform("mean").to_numpy()
    grid = pd.DataFrame({"code": df.code, "time": df.time, "x": gx}).pivot_table(index="code", columns="time",
                                                                                  values="x", aggfunc="first")
    return Spec(yy, xx, ctl, tuple(df[f].astype(str).to_numpy() for f in fe), df.code.to_numpy(),
                df.time.to_numpy(), fam, None if weights is None else np.asarray(weights, float), grid, floored)


def topic_weights(df: pd.DataFrame, col: str) -> np.ndarray:
    return df.groupby("topic")[col].transform("mean").to_numpy()


def q1_targets(panel: pd.DataFrame, v: Variant) -> dict:
    df = panel[panel.topic.isin(v.topics) & ~panel.time.isin(v.drop_waves)].dropna(subset=["a_post", "a_pre"])
    fe = ("spell", "time", "topic_half")
    w = topic_weights(df, "c") if v.weighted else None
    # The lag A(k, t−) is a calendar window, not a concern item list, so it never crosses a spell change and the
    # dynamic model keeps the static model's rows.
    static = make_spec(df, "a_post", "c", None, fe, v.form, w, centre_by="spell")
    dynamic = make_spec(df, "a_post", "c", "a_pre", fe, v.form, w, centre_by="spell")
    return {"static": Target([(1.0, Equation(static, False))]), "dynamic": Target([(1.0, Equation(dynamic, True))])}


def q1r_targets(panel: pd.DataFrame, v: Variant) -> dict:
    df = panel[panel.topic.isin(v.topics) & ~panel.time.isin(v.drop_waves) & ~(panel.time + 1).isin(v.drop_waves)]
    df = df.dropna(subset=["c_next", "a_post"])
    fe = ("spell_next", "time", "topic_half")
    w = topic_weights(df, "c") if v.weighted else None
    static = make_spec(df, "c_next", "a_post", None, fe, v.form, w)
    dyn = df[df.spell == df.spell_next]
    wd = topic_weights(dyn, "c") if v.weighted else None
    dynamic = make_spec(dyn, "c_next", "a_post", "c", fe, v.form, wd)
    full = panel.dropna(subset=["a_post"])
    grid = make_spec(full, "c", "a_post", None, ("time",), v.form).xgrid
    static.xgrid = dynamic.xgrid = grid
    return {"static": Target([(1.0, Equation(static, False))]), "dynamic": Target([(1.0, Equation(dynamic, True))])}


def yearly_rows(yp: pd.DataFrame, v: Variant, need: list[str]) -> pd.DataFrame:
    df = yp[yp.topic.isin(v.topics) & ~yp.time.isin(v.drop_years) & ~(yp.time + 1).isin(v.drop_years)]
    return df.dropna(subset=need)


def q2_targets(yp: pd.DataFrame, v: Variant, controls: dict | None = None) -> dict:
    df = yearly_rows(yp, v, ["cbar", "s", "s_next"])
    fe = ("spell", "time")
    w = topic_weights(df, "cbar") if v.weighted else None
    if v.change_in_share:
        df = df.assign(ds=df.s_next - df.s, ds_floor=np.nan)
        spec = make_spec(df, "ds", "cbar", None, fe, "log", w)
        spec.y = df.ds.to_numpy()
        return {"static": Target([(1.0, Equation(spec, False))])}
    static = make_spec(df, "s_next", "cbar", None, fe, v.form, w, centre_by="spell")
    dynamic = make_spec(df, "s_next", "cbar", "s", fe, v.form, w, centre_by="spell")
    if controls is not None:
        extra = np.column_stack([
            np.where(df.topic == "Unemployment", np.log(df.time.map(controls["unemployment"])), 0.0),
            np.where(df.topic == "Pensions", np.log(df.time.map(controls["old_age_dependency"])), 0.0)])
        static.controls = np.column_stack([static.controls, extra])
        dynamic.controls = np.column_stack([dynamic.controls, extra])
    return {"static": Target([(1.0, Equation(static, False))]), "dynamic": Target([(1.0, Equation(dynamic, True))])}


def q3_target(yp: pd.DataFrame, v: Variant) -> dict:
    df = yearly_rows(yp, v, ["cbar", "s", "s_next", "a", "a_next"])
    fe = ("spell", "time")
    w = topic_weights(df, "cbar") if v.weighted else None
    att = make_spec(df, "a_next", "cbar", "a", fe, v.form, w, centre_by="spell")
    spe = make_spec(df, "s_next", "cbar", "s", fe, v.form, w, centre_by="spell")
    return {"dynamic": Target([(1.0, Equation(att, True)), (-1.0, Equation(spe, True))])}


# ---- the study

class Study:
    def __init__(self):
        self.con = {"A": load_concern("A")}
        registered_spells_hold(self.con["A"].items)
        self.spend = load_spending()
        pc = pd.read_parquet(D / "attention.parquet", columns=["date"]).date
        self.pc_span = (pc.min().date(), pc.max().date())
        psp_dates = pd.read_parquet(D / "psp_speeches.parquet", columns=["date"]).date
        self.spans = {"parlacap": self.pc_span,
                      "whole": (psp_dates.min().date(), min(WHOLE_END, psp_dates.max().date()))}
        self.validation = json.loads(VALIDATION.read_text())
        self.W = webb_weights()
        self._speeches, self._corpora, self._q = {}, {}, None

    def concern(self, arm: str) -> Concern:
        if arm not in self.con:
            self.con[arm] = load_concern(arm)
        return self.con[arm]

    def speeches(self, series: str, chair=False, mix=False) -> pd.DataFrame:
        key = (series, chair, mix)
        if key not in self._speeches:
            self._speeches[key] = series_speeches(series, self.pc_span, chair, mix)
        return self._speeches[key]

    def corpus(self, series: str, kind: str = "words", party: str | None = None) -> Corpus:
        key = (series, kind, party)
        if key in self._corpora:
            return self._corpora[key]
        span = self.spans[series]
        if kind == "corrected":
            if self._q is None:
                self._q = confusion()
            c = corrected_corpus(self.speeches(series), span, self._q, self.pc_span[0])
        else:
            df = self.speeches(series, chair=kind == "chair", mix=kind == "mix")
            if party is not None:
                df = df[df.party == party]
            c = corpus(df, span, "speeches" if kind == "speeches" else "words")
        self._corpora[key] = c
        return c

    def wins(self, arm: str, window: str) -> dict:
        con = self.concern(arm)
        return windows(con.dates) if window == "half" else windows(con.dates, CHECK_WINDOW_DAYS, cap=False)

    def wave_panel(self, series: str, v: Variant, party=None, waves=None) -> pd.DataFrame:
        con, wins = self.concern(v.arm), self.wins(v.arm, v.window)
        sample = covered_waves(wins, self.spans[series]) if waves is None else waves
        return wave_panel(con, self.corpus(series, v.corpus, party), wins, sample)

    def year_panel(self, series: str | None, v: Variant) -> pd.DataFrame:
        con = self.concern(v.arm)
        corp = self.corpus(series, v.corpus) if series else None
        topics = SPENDING_TOPICS
        return year_panel(con, self.spend, corp, topics, v.drop_waves)

    def f1_topics(self, series: str) -> tuple:
        frames = ["parlacap"] if series == "parlacap" else ["parlacap", "psp_2004_2013"]
        return tuple(t for t in TOPICS if all(self.validation[f]["by_topic"][t]["f1"] >= F1_CHECK for f in frames))

    def classifier_limited(self, series: str) -> bool:
        frames = ["parlacap"] if series == "parlacap" else ["parlacap", "psp_2004_2013"]
        return any(self.validation[f]["macro_f1"] < MACRO_F1_BOUND for f in frames)

    def controls(self) -> dict | None:
        paths = {"unemployment": D / "eurostat/une_rt_a_CZ.json", "old_age_dependency": D / "eurostat/demo_pjanind_CZ.json"}
        if not all(p.exists() for p in paths.values()):
            return None
        return {k: eurostat_series(p) for k, p in paths.items()}


def attempt(fn, *args, **kw):
    """A result, or the reason it could not be estimated (recorded, so one failure does not stop the run)."""
    try:
        return fn(*args, **kw)
    except (ValueError, KeyError, np.linalg.LinAlgError, FloatingPointError) as e:
        return {"error": f"{type(e).__name__}: {e}", "label": "not estimable"}


def primary(build, W) -> dict:
    targets = attempt(build)
    if "error" in targets:
        return targets
    out = {m: attempt(intervals, t, W) for m, t in targets.items()}
    if "static" in out and "dynamic" in out:
        out["label"] = combined(out["static"]["label"], out["dynamic"]["label"])
    else:
        out["label"] = out["dynamic"]["label"]
    return out


def check(build, W) -> dict:
    targets = attempt(build)
    if "error" in targets:
        return targets
    return {m: attempt(intervals, t, W, randomisation=False) for m, t in targets.items()}


def leave_out(build, frame: pd.DataFrame, by: str) -> dict:
    """Point estimates with each topic (or period) left out, and their range."""
    out = {}
    for val in sorted(frame[by].unique()):
        ts = build(frame[frame[by] != val])
        out[str(val)] = {m: attempt(t.estimate) for m, t in ts.items()}
    models = next(iter(out.values())).keys()
    ok = lambda m: [o[m] for o in out.values() if isinstance(o[m], float)]
    return {"estimates": out, "range": {m: [min(ok(m)), max(ok(m))] if ok(m) else None for m in models}}


def at_means(res: dict) -> dict:
    """Levels models: the coefficient as an elasticity at the estimation sample's means, bounds scaled alike."""
    f = res["x_mean"] / res["y_mean"]
    return {"factor": f, "estimate": res["estimate"] * f,
            "wild": {k: [b * f for b in v] for k, v in res["wild"].items()}}


def run() -> dict:
    IRLS_NOT_CONVERGED[0] = 0
    st = Study()
    W = st.W
    base = Variant()
    res = {"design": "docs/research/priorities-design.md (signed tag priorities-design)",
           "settings": {"seed_bootstrap": SEED, "seed_permutations": SEED + 1, "bootstrap_draws": BOOT,
                        "permutations": PERMS, "webb_weights": WEBB.tolist(), "window_days": WINDOW_DAYS,
                        "coverage": COVERAGE, "sesoi": SESOI, "max_width_90": MAX_WIDTH_90,
                        "search_limit": SEARCH_LIMIT, "search_tol": SEARCH_TOL},
           "data": {}, "primary": {}, "q4": {}, "checks": {}}
    con = st.concern("A")
    res["data"]["spell_starts"] = {t: sorted(con.starts[t]) for t in TOPICS}
    changes = list_change_waves(con)

    panels, ypanels = {}, {}
    for s in ("parlacap", "whole"):
        panels[s] = st.wave_panel(s, base)
        ypanels[s] = st.year_panel(s, base)
        res["data"][s] = {"span": [str(d) for d in st.spans[s]], "waves": sorted(panels[s].time.unique().tolist()),
                          "years_q3": sorted(ypanels[s].dropna(subset=["a", "a_next", "s", "s_next"]).time.unique().tolist()),
                          "classifier_limited": st.classifier_limited(s)}
        lim = st.classifier_limited(s)
        res["primary"][s] = {
            "Q1": {**primary(lambda: q1_targets(panels[s], base), W), "classifier_limited": lim},
            "Q1r": primary(lambda: q1r_targets(panels[s], base), W),
            "Q3": {**primary(lambda: q3_target(ypanels[s], base), W), "classifier_limited": lim},
        }
    yp2 = st.year_panel(None, base)
    res["primary"]["spending"] = {"Q2": primary(lambda: q2_targets(yp2, base), W)}

    # Q4 (descriptive, no label)
    q4 = {"party_status": {}, "government": {}}
    wins = st.wins("A", "half")
    for g in PARTY_GROUPS:
        q4["party_status"][g] = attempt(
            lambda: intervals(q1_targets(st.wave_panel("parlacap", base, party=g), base)["static"], W))
    for s in ("parlacap", "whole"):
        q4["government"][s] = {}
        for name, _, _ in GOVERNMENTS:
            waves = [w for w in res["data"][s]["waves"] if wave_government(wins[w]["after"]) == name]
            p = panels[s][panels[s].time.isin(waves)]
            q4["government"][s][name] = attempt(lambda: intervals(q1_targets(p, base)["static"], W))
    for k in ("party_status", "government"):
        for grp in q4[k].values():
            for r in (grp.values() if k == "government" else [grp]):
                r.pop("label", None)
    q4["classifier_limited"] = {s: st.classifier_limited(s) for s in ("parlacap", "whole")}
    q4["note"] = "party status is in ParlaCAP only; the governments are the three of §1"
    res["q4"] = q4

    # §6 checks: point estimates and wild bootstrap intervals; none relabels a primary result
    pandemic = (date(min(PANDEMIC_YEARS), 1, 1), date(max(PANDEMIC_YEARS), 12, 31))
    years_pandemic = frozenset(w for w, v in wins.items()
                               if coverage(v["before"], pandemic) > 0 or coverage(v["after"], pandemic) > 0)
    variants = {
        "speeches_instead_of_words": Variant(corpus="speeches"),
        "chair_kept": Variant(corpus="chair"),
        "mix_kept": Variant(corpus="mix"),
        "window_one_year": Variant(window="year"),
        "without_2020_2022": Variant(drop_waves=years_pandemic, drop_years=PANDEMIC_YEARS),
        "without_eb93_96": Variant(drop_waves=MODE_WAVES),
        "without_list_changes": Variant(drop_waves=changes),
        "split_ballot_arm_b": Variant(arm="B"),
        "log_ols": Variant(form="log"),
        "levels": Variant(form="levels"),
        "weighted_mean_concern": Variant(weighted=True),
        "confusion_corrected": Variant(corpus="corrected"),
    }
    attention_only = {"speeches_instead_of_words", "chair_kept", "mix_kept", "window_one_year", "confusion_corrected"}
    checks = {}
    for s in ("parlacap", "whole"):
        cs = checks[s] = {}
        f1v = Variant(topics=st.f1_topics(s))
        for name, v in {**variants, "f1_at_least_0_60": f1v}.items():
            wp = panels[s] if v in (base, f1v) else attempt(st.wave_panel, s, v)
            if isinstance(wp, dict):
                cs[name] = wp
                continue
            out = {"Q1": check(lambda: q1_targets(wp, v), W), "Q1r": check(lambda: q1r_targets(wp, v), W)}
            if v.window == "half":
                yp = ypanels[s] if v in (base, f1v) else attempt(st.year_panel, s, v)
                out["Q3"] = yp if isinstance(yp, dict) else check(lambda: q3_target(yp, v), W)
            if v.form == "levels":
                for q in ("Q1", "Q1r"):
                    for m, r in out[q].items():
                        if isinstance(r, dict) and "wild" in r:
                            r["elasticity_at_means"] = at_means(r)
            cs[name] = out
        cs["leave_one_topic_out"] = {"Q1": attempt(leave_out, lambda d: q1_targets(d, base), panels[s], "topic"),
                                     "Q1r": attempt(leave_out, lambda d: q1r_targets(d, base), panels[s], "topic"),
                                     "Q3": attempt(leave_out, lambda d: q3_target(d, base), ypanels[s], "topic")}
        cs["leave_one_wave_out"] = {"Q1": attempt(leave_out, lambda d: q1_targets(d, base), panels[s], "time"),
                                    "Q1r": attempt(leave_out, lambda d: q1r_targets(d, base), panels[s], "time"),
                                    "Q3_year": attempt(leave_out, lambda d: q3_target(d, base), ypanels[s], "time")}
    cq2 = checks["spending"] = {}
    for name, v in variants.items():
        if name in attention_only:
            continue
        yp = yp2 if v == base else attempt(st.year_panel, None, v)
        if isinstance(yp, dict):
            cq2[name] = yp
            continue
        cq2[name] = check(lambda: q2_targets(yp, v), W)
        if v.form == "levels":
            for m, r in cq2[name].items():
                if isinstance(r, dict) and "wild" in r:
                    r["elasticity_at_means"] = at_means(r)
    cq2["discretionary_topics"] = check(lambda: q2_targets(yp2, Variant(topics=DISCRETIONARY)), W)
    ctl = st.controls()
    cq2["unemployment_and_old_age_dependency_controls"] = (
        check(lambda: q2_targets(yp2, base, ctl), W) if ctl else "not run: control series not fetched")
    ch = check(lambda: q2_targets(yp2, Variant(change_in_share=True)), W)
    if "estimate" in ch.get("static", {}):
        sample = yearly_rows(yp2, Variant(change_in_share=True), ["cbar", "s", "s_next"])
        ch["static"]["per_mean_share"] = ch["static"]["estimate"] / sample.s.mean()
    cq2["spending_change_in_share"] = ch
    cq2["leave_one_topic_out"] = attempt(leave_out, lambda d: q2_targets(d, base), yp2, "topic")
    cq2["leave_one_year_out"] = attempt(leave_out, lambda d: q2_targets(d, base), yp2, "time")
    res["checks"] = checks
    res["diagnostics"] = {"irls_not_converged": IRLS_NOT_CONVERGED[0],
                          "note": "floored cells (zeros set to the half-unit floor before the log) are counted per "
                                  "estimate under floored_cells"}
    return res


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return "inf" if f == math.inf else "-inf" if f == -math.inf else None if math.isnan(f) else round(f, 6)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main() -> None:
    OUT.write_text(json.dumps(clean(run()), indent=1, ensure_ascii=False) + "\n")
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
