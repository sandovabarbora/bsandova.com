"""Shared definitions of the UN votes study (docs/research/un-votes-design.md §2 and §4): loading the Digital Library
file, the EU-27 comparison set, agreement with a leave-out EU majority or a partner, and β with its intervals.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/un"
FILE = DATA / "2026_02_06_ga_voting.csv"
SHA256 = "9b8ddbee7490d9e31aa1b2f852c0b074ff58afd9e4bb67e629bcddbdde7852f1"
START = "2014-01-29"
# the EU as it has been since February 2020, in every window, so that the comparison set never changes
EU27 = ("AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP "
        "SWE").split()
POS = {"Y": 0, "N": 1, "A": 2}
BUFFER_DAYS = 30
SEED, DRAWS, MIN_AFTER = 20261015, 2000, 20


def load(path: Path = FILE, drop: tuple[str, ...] = (), end: str = "2099-12-31") -> pd.DataFrame:
    """Rows from START to `end`; members in `drop` and later rows are removed in the query, never read."""
    import duckdb
    skip = ", ".join(f"'{c}'" for c in drop) or "''"
    df = duckdb.sql(f"""
        SELECT undl_id, ms_code, ms_name, ms_vote, CAST(date AS DATE) AS date, session, resolution, title, agenda_title
        FROM read_csv('{path}', header = true, all_varchar = true)
        WHERE CAST(date AS DATE) BETWEEN DATE '{START}' AND DATE '{end}' AND ms_code NOT IN ({skip})
    """).df()
    df["date"] = pd.to_datetime(df["date"])
    return df


def score(a: np.ndarray, b: np.ndarray, partial: bool = True) -> np.ndarray:
    """1 equal, 0.5 when one abstains and the other does not (0 without partial credit, §7.2), 0 for yes against no;
    NaN when either is missing."""
    half = 0.5 if partial else 0.0
    out = np.where(a == b, 1.0, np.where((a == POS["A"]) | (b == POS["A"]), half, 0.0))
    return np.where((a < 0) | (b < 0), np.nan, out)


def positions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """A vote × member matrix of position codes (−1 missing), each vote's date and cluster, and the duplicates dropped.
    The cluster is the agenda item (a resolution family repeated year after year), or the vote itself without one."""
    dup = int(df.duplicated(["undl_id", "ms_code"]).sum())
    d = df.drop_duplicates(["undl_id", "ms_code"]).assign(p=lambda x: x["ms_vote"].map(POS).fillna(-1).astype(int))
    m = d.pivot(index="undl_id", columns="ms_code", values="p").fillna(-1).astype(int)
    info = d.groupby("undl_id").agg(date=("date", "first"), session=("session", "first"), agenda=("agenda_title", "first"),
                                     title=("title", "first"))
    info["cluster"] = info["agenda"].fillna("").str.strip().where(lambda s: s != "", "vote " + info.index.astype(str))
    return m, info.reindex(m.index), dup


def agreement_eu(m: pd.DataFrame, member: str, exclude: tuple[str, ...] = (), partial: bool = True) -> pd.Series:
    """`member`'s agreement with the most common position of the EU-27 members other than it and `exclude` that voted
    (a tie drops the vote)."""
    others = [c for c in EU27 if c in m.columns and c != member and c not in exclude]
    vals = m[others].to_numpy()
    counts = np.stack([(vals == k).sum(1) for k in range(3)], 1)
    top = counts.max(1)
    maj = np.where(((counts == top[:, None]).sum(1) == 1) & (top > 0), counts.argmax(1), -1)
    return pd.Series(score(m[member].to_numpy(), maj, partial), index=m.index)


def agreement_partner(m: pd.DataFrame, member: str, partner: str, partial: bool = True) -> pd.Series:
    return pd.Series(score(m[member].to_numpy(), m[partner].to_numpy(), partial), index=m.index)


def agreements(m: pd.DataFrame, focal: str, partner: str | None, partial: bool = True,
               drop: tuple[str, ...] = ()) -> tuple[pd.Series, pd.DataFrame]:
    """§4: the focal member's agreement, and each comparison member's, scored without the focal member (and without
    the partner, who is neither focal nor a comparison member)."""
    comp = [c for c in EU27 if c in m.columns and c not in (focal, partner, *drop)]
    if partner is None:
        a_f = agreement_eu(m, focal, partial=partial)
        a_c = pd.DataFrame({c: agreement_eu(m, c, exclude=(focal,), partial=partial) for c in comp})
    else:
        a_f = agreement_partner(m, focal, partner, partial)
        a_c = pd.DataFrame({c: agreement_partner(m, c, partner, partial) for c in comp})
    return a_f, a_c


def after_cabinet(cabinet: str) -> str:
    """The first day of an after period: the cabinet date plus the buffer (§1)."""
    return str((pd.Timestamp(cabinet) + pd.Timedelta(days=BUFFER_DAYS)).date())


def windows(dates: pd.Series, before: tuple[str, str], after: tuple[str, str]) -> tuple[pd.Series, pd.Series]:
    """Votes in the before and after periods, both ends included; Q1's after period starts on the registration date,
    Q2's on after_cabinet()."""
    return (dates >= before[0]) & (dates <= before[1]), (dates >= after[0]) & (dates <= after[1])


def beta(a_f: pd.Series, a_c: pd.DataFrame, before: pd.Series, after: pd.Series, cluster: pd.Series,
         draws: int = DRAWS, seed: int = SEED) -> dict:
    """The change in the focal member's agreement minus the change in the comparison members' mean, on the votes where
    the focal member has a position; intervals from resampling agenda items within each period."""
    # comparison members with a position on both sides, so the set does not change across the change
    both = [c for c in a_c.columns if a_c.loc[before, c].notna().any() and a_c.loc[after, c].notna().any()]
    d = a_f - a_c[both].mean(axis=1)
    keep = d.notna() & (before | after)
    d, q, cl = d[keep], after[keep], cluster[keep]
    est = d[q].mean() - d[~q].mean()
    rng = np.random.default_rng(seed)

    def side(mask):
        g = d[mask].groupby(cl[mask]).agg(["sum", "count"]).to_numpy()
        return g, len(g)

    (gq, kq), (gp, kp) = side(q), side(~q)
    if kq == 0 or kp == 0:
        raise ValueError("a period without votes")
    boot = np.empty(draws)
    for i in range(draws):
        sq = gq[rng.integers(0, kq, kq)].sum(0)
        sp = gp[rng.integers(0, kp, kp)].sum(0)
        boot[i] = sq[0] / sq[1] - sp[0] / sp[1]
    return {"est": float(est), "se": float(boot.std(ddof=1)),
            "ci90": [float(x) for x in np.percentile(boot, [5, 95])],
            "ci95": [float(x) for x in np.percentile(boot, [2.5, 97.5])],
            "n_before": int((~q).sum()), "n_after": int(q.sum()), "clusters_after": int(kq),
            "comparison": len(both)}


def label(b: dict, rank_p: float, margin: float = 0.03, minimum: float = 0.02) -> str:
    """§6, in order."""
    lo95, hi95 = b["ci95"]
    lo90, hi90 = b["ci90"]
    if abs(b["est"]) >= minimum and (lo95 > 0 or hi95 < 0) and rank_p <= 0.10:
        return "higher agreement after the change" if b["est"] > 0 else "lower agreement after the change"
    if -margin <= lo90 and hi90 <= margin:
        return f"no change larger than {round(100 * margin)} points"
    if hi90 - lo90 > 2 * margin:
        return "underpowered"
    return "inconclusive"


def rank_p(focal_t: float, placebo_t: list[float]) -> tuple[float, int]:
    """Share of members, the focal one included, whose |β|/se is at least the focal member's; and their number."""
    allv = np.abs(np.array([focal_t, *placebo_t]))
    return float((allv >= abs(focal_t)).sum() / len(allv)), len(allv)
