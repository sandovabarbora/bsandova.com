"""Part 1 extended: estimates every registered hypothesis of docs/research/prague-council-design.md.

H1  within-person change in the against rate, consecutive terms, sign-flip randomisation over persons
H2  (descriptive) sitting-level abstain / (abstain + nehlasoval): jump at the 2018 term boundary against trends
H3  classification errors of the coalition partition vs the best left-right cut, contested votes, block bootstrap
H4  opposition non-support on planning + property vs grants, 2022-26, WLS with CR2 by sitting + wild bootstrap
RQ5 (descriptive) yes share and against rate by list x coalition period

Usage:
    uv run --with pandas --with numpy --with scipy python tools/zhmp/council_extended.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).parent))
from council import PRESENT, RAW, TERMS, load, seats  # noqa: E402
from topics import classify  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "zhmp" / "council_extended.json"
SEED = 20260928
FLIPS = 99_999
B = 9_999
T = pd.Timestamp
# Appendix A: governing lists by period (None = interregnum)
COALITIONS = [
    ("2010", T("2010-11-01"), T("2011-11-24"), {"ODS", "ČSSD"}),
    ("2010", T("2011-11-24"), T("2013-05-23"), {"ODS", "TOP 09"}),
    ("2010", T("2013-05-23"), T("2013-06-20"), None),
    ("2010", T("2013-06-20"), T("2014-11-01"), {"TOP 09"}),
    ("2014", T("2014-11-01"), T("2015-10-23"), {"ANO", "ČSSD", "Trojkoalice"}),
    ("2014", T("2015-10-23"), T("2016-04-28"), None),
    ("2014", T("2016-04-28"), T("2018-11-01"), {"ANO", "ČSSD", "Trojkoalice"}),
    ("2018", T("2018-11-01"), T("2022-11-01"), {"Piráti", "Praha sobě", "Spojené síly"}),
    ("2022", T("2022-11-01"), T("2023-02-16"), None),
    ("2022", T("2023-02-16"), T("2026-12-31"), {"SPOLU", "Piráti", "STAN"}),
]
EXPELLED = ("Kordová Marvanová Hana", T("2023-02-17"))  # out of the SPOLU club, not in the coalition
CHES = {  # national party scores (CHES 2019 V3 for 2018-22, CHES 2024 for 2022-26)
    "2018": {"axis": "lrecon", "ODS": 7.70, "TOP 09": 7.33, "KDU-ČSL": 5.54, "STAN": 6.58, "Piráti": 4.35,
             "ANO": 4.50, "SPD": 4.67},
    "2022": {"axis": "lrgen", "ODS": 7.12, "TOP 09": 6.88, "KDU-ČSL": 6.00, "STAN": 5.80, "Piráti": 4.20,
             "ANO": 4.22, "SPD": 8.75},
}
JOINT = {"Spojené síly": ["TOP 09", "STAN"], "SPOLU": ["ODS", "TOP 09", "KDU-ČSL"]}
SINGLE = {"Piráti": "Piráti", "ANO": "ANO", "SPD": "SPD", "STAN": "STAN", "ODS": "ODS", "TOP 09": "TOP 09"}
PARTY_ALIAS = {"KDU-ČSL": "KDU-ČSL", "KDU": "KDU-ČSL", "TOP 09": "TOP 09", "ODS": "ODS", "STAN": "STAN",
               "Piráti": "Piráti", "ANO": "ANO", "ANO 2011": "ANO", "SPD": "SPD"}


# ------------------------------------------------------------------------------------------------------- inputs

def crosswalk() -> pd.DataFrame:
    return pd.read_csv(ROOT / "docs" / "research" / "prague-council-crosswalk.csv")


def status_matrix(term: str, meta: pd.DataFrame, people: list[str], lists: dict[str, str]) -> pd.DataFrame:
    """For each roll call and person: 1 = in coalition, 0 = opposition, NaN = interregnum or unknown list."""
    out = pd.DataFrame(np.nan, index=meta.index, columns=people)
    for t_, a, b, coal in COALITIONS:
        if t_ != term or coal is None:
            continue
        rows = (meta.t >= a) & (meta.t < b)
        for p in people:
            if isinstance(lists.get(p), str):
                out.loc[rows, p] = float(lists[p] in coal)
    p, when = EXPELLED
    if p in out:
        out.loc[meta.t >= when, p] = 0.0
    return out


def terms() -> dict:
    cw = crosswalk()
    data = {}
    for term in TERMS:
        meta, v = load(term)
        keep = ~meta.excluded
        meta, v = meta[keep].reset_index(drop=True), v[keep].reset_index(drop=True)
        lists = cw[cw.term == int(term)].set_index("person").list.to_dict()
        party = cw[cw.term == int(term)].set_index("person").party.to_dict()
        data[term] = {"meta": meta, "v": v, "lists": lists, "party": party,
                      "status": status_matrix(term, meta, list(v.columns), lists)}
    return data


# ----------------------------------------------------------------------------------------------------------- H1

def person_term(d: dict) -> pd.DataFrame:
    v, st = d["v"], d["status"]
    seated = v != ""
    present = v.isin(PRESENT)
    against, abstain, yes = (v == "Hlas proti"), (v == "Zdržel se"), (v == "Hlas pro")
    opp = ((st == 0) & seated).sum() / ((st.notna()) & seated).sum().replace(0, np.nan)
    return pd.DataFrame({"seated": seated.sum(), "present": present.sum(), "against": against.sum(),
                         "abstain": abstain.sum(), "nonyes": (present & ~yes).sum(), "opp_share": opp,
                         "list": pd.Series(d["lists"])})


def logit(x):
    return np.log(x / (1 - x))


def signflip(d_i: np.ndarray, rng, n: int = FLIPS) -> float:
    """One-sided p for mean(D) < 0 under symmetric-about-zero null."""
    obs = d_i.mean()
    s = rng.choice([-1.0, 1.0], size=(n, len(d_i)))
    return float((1 + np.sum((s * d_i).mean(axis=1) <= obs)) / (n + 1))


def h1(data: dict, rng, outcome: str = "against", stayers_only: bool = False, adjust: bool = True,
       passed_only: bool = False, skip: tuple = ()) -> dict:
    if passed_only:
        data = {k: {**d, "v": d["v"][d["meta"].passed.values], "status": d["status"][d["meta"].passed.values]}
                for k, d in data.items()}
    pt = {term: person_term(d) for term, d in data.items()}
    ts = list(TERMS)
    rows = []
    for a, b in zip(ts, ts[1:]):
        if f"{a}->{b}" in skip:
            continue
        both = pt[a].index.intersection(pt[b].index).drop("neurčeno", errors="ignore")
        for p in both:
            x, y = pt[a].loc[p], pt[b].loc[p]
            if x.seated < 300 or y.seated < 300 or pd.isna(x.list) or pd.isna(y.list):
                continue
            if outcome == "against":
                ra, rb = (x.against + .5) / (x.present + 1), (y.against + .5) / (y.present + 1)
            else:  # explicit non-support among present non-yes
                if x.nonyes < 20 or y.nonyes < 20:
                    continue
                ra = (x.against + x.abstain + .5) / (x.nonyes + 1)
                rb = (y.against + y.abstain + .5) / (y.nonyes + 1)
            rows.append({"person": p, "pair": f"{a}->{b}", "delta": logit(rb) - logit(ra),
                         "d_opp": y.opp_share - x.opp_share, "stayer": abs(y.opp_share - x.opp_share) < 0.5})
    r = pd.DataFrame(rows)
    if stayers_only:
        r = r[r.stayer]
    X = np.c_[np.ones(len(r)), r.d_opp.fillna(0)]
    beta = np.linalg.lstsq(X, r.delta.values, rcond=None)[0] if adjust else np.zeros(2)
    r["adj"] = r.delta - beta[1] * r.d_opp.fillna(0)
    d_i = r.groupby("person").adj.mean().values
    by_pair = {}
    for k, g in r.groupby("pair"):
        m, s, n = g.adj.mean(), g.adj.std(ddof=1), len(g)
        by_pair[k] = {"n": n, "mean": round(float(m), 3),
                      "ci95": [round(float(m - tdist.ppf(.975, n - 1) * s / np.sqrt(n)), 3),
                               round(float(m + tdist.ppf(.975, n - 1) * s / np.sqrt(n)), 3)],
                      "ratio": round(float(np.exp(m)), 3)}
    return {"outcome": outcome, "persons": len(d_i), "transitions": len(r), "status_slope": round(float(beta[1]), 3),
            "mean_D": round(float(d_i.mean()), 3), "ratio_per_term": round(float(np.exp(d_i.mean())), 3),
            "sd_D": round(float(d_i.std(ddof=1)), 3), "p": signflip(d_i, rng), "by_pair": by_pair}


def shift_share(data: dict) -> dict:
    pt = {term: person_term(d) for term, d in data.items()}
    ts, out = list(TERMS), {}
    for a, b in zip(ts, ts[1:]):
        x, y = pt[a], pt[b]
        stay = x.index.intersection(y.index).drop("neurčeno", errors="ignore")
        rate = lambda df: 100 * df.against.sum() / df.present.sum()  # noqa: E731
        A0, A1 = rate(x), rate(y)
        S0, S1 = rate(x.loc[stay]), rate(y.loc[stay])
        w0, w1 = x.loc[stay].present.sum() / x.present.sum(), y.loc[stay].present.sum() / y.present.sum()
        within = (w0 + w1) / 2 * (S1 - S0)
        out[f"{a}->{b}"] = {"against_per_100_present": [round(A0, 3), round(A1, 3)], "change": round(A1 - A0, 3),
                            "within_stayers": round(within, 3), "entry_exit_and_mix": round(A1 - A0 - within, 3),
                            "stayer_share_of_present": [round(w0, 3), round(w1, 3)]}
    return out


def newcomers(data: dict) -> dict:
    seen, out = set(), {}
    for term, d in data.items():
        pt = person_term(d)
        new = pt.index.difference(list(seen))
        if term != "2010":
            g = pt.loc[new]
            out[term] = {"n": len(g), "against_per_100_present": round(100 * g.against.sum() / g.present.sum(), 3)}
        seen |= set(pt.index)
    return out


# ----------------------------------------------------------------------------------------------------------- H2

def sittings(data: dict, people: dict | None = None) -> pd.DataFrame:
    rows = []
    for term, d in data.items():
        v = d["v"] if people is None else d["v"][[c for c in people.get(term, []) if c in d["v"]]]
        m = d["meta"]
        ab = (v == "Zdržel se").sum(axis=1)
        nh = (v == "Nehlasoval").sum(axis=1)
        g = pd.DataFrame({"sitting": m.sitting, "t": m.t, "ab": ab, "nh": nh, "off_ab": m.pocetzdrzel,
                          "off_pr": m.pocetpro + m.pocetproti + m.pocetzdrzel}).groupby("sitting").agg(
            t=("t", "min"), ab=("ab", "sum"), nh=("nh", "sum"), off_ab=("off_ab", "sum"), off_pr=("off_pr", "sum"))
        g["term"] = term
        rows.append(g.reset_index())
    s = pd.concat(rows, ignore_index=True)
    s["share"] = s.ab / (s.ab + s.nh)
    s["official"] = s.off_ab / s.off_pr
    return s


def jump(s: pd.DataFrame, col: str, rng) -> dict:
    """y = a + b k + g D + d k D on 2014-18 and 2018-22 sittings, WLS; fixed-regressor AR(1)-sieve bootstrap."""
    w = s[s.term.isin(["2014", "2018"])].reset_index(drop=True)
    w = w[(w.ab + w.nh) > 0]
    k = np.arange(len(w), dtype=float)
    D = (w.term == "2018").values.astype(float)
    X = np.c_[np.ones(len(w)), k, D, k * D]
    wt = (w.ab + w.nh).values.astype(float) if col == "share" else w.off_pr.values.astype(float)
    y = w[col].values
    sw = np.sqrt(wt / wt.mean())
    Xw, yw = X * sw[:, None], y * sw
    b = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    X0 = np.delete(Xw, 2, axis=1)
    b0 = np.linalg.lstsq(X0, yw, rcond=None)[0]
    e0 = yw - X0 @ b0
    rho = float(np.corrcoef(e0[:-1], e0[1:])[0, 1])
    u = e0[1:] - rho * e0[:-1]
    stats = []
    for _ in range(B):
        eps = rng.choice(u, size=len(e0))
        e = np.empty(len(e0))
        e[0] = rng.choice(e0)
        for i in range(1, len(e)):
            e[i] = rho * e[i - 1] + eps[i]
        stats.append(np.linalg.lstsq(Xw, X0 @ b0 + e, rcond=None)[0][2])
    stats = np.array(stats)
    return {"gamma": round(float(b[2]), 4), "p_one_sided_less": round(float((1 + np.sum(stats <= b[2])) / (B + 1)), 4),
            "slope_2014_18": round(float(b[1]), 5), "slope_2018_22": round(float(b[1] + b[3]), 5), "ar1": round(rho, 3),
            "sittings": len(w)}


# ----------------------------------------------------------------------------------------------------------- H3

def scores(term: str, d: dict) -> dict:
    ches = CHES[term]
    out = {}
    for p, lst in d["lists"].items():
        if not isinstance(lst, str) or lst == "Praha sobě":
            continue
        party = PARTY_ALIAS.get(str(d["party"].get(p)))
        if lst in JOINT:
            out[p] = ches[party] if party in JOINT[lst] else float(np.mean([ches[x] for x in JOINT[lst]]))
        elif lst in SINGLE:
            out[p] = ches[SINGLE[lst]]
    return out


def h3_period(term: str, d: dict, rng) -> dict:
    meta, v, st = d["meta"], d["v"], d["status"]
    start = T("2018-11-15") if term == "2018" else T("2023-02-16")
    rows = (meta.t >= start).values
    sc = scores(term, d)
    people = [p for p in v.columns if p in sc]
    order = sorted(set(sc[p] for p in people))
    errs, sit = [], []
    for i in np.where(rows)[0]:
        cells = v.loc[i, people]
        pres = cells.isin(PRESENT)
        if pres.sum() < 20:
            continue
        yes = (cells[pres] == "Hlas pro").values.astype(int)
        minority = min(yes.mean(), 1 - yes.mean())
        if minority < 0.025:
            continue
        pp = [p for p, ok in zip(people, pres) if ok]
        coal = st.loc[i, pp].values
        if np.isnan(coal).any():
            continue
        ea = min(np.sum(yes != coal), np.sum(yes != 1 - coal))
        s_ = np.array([sc[p] for p in pp])
        eb = min(min(np.sum(yes != (s_ <= c)), np.sum(yes != (s_ > c))) for c in [order[0] - 1] + order)
        errs.append((eb - ea) / len(pp))
        sit.append(meta.sitting[i])
    e = pd.DataFrame({"d": errs, "sitting": sit})
    stat = e.d.mean()
    by = e.groupby("sitting").d.agg(["sum", "size"])
    ids = by.index.values
    n_blocks = int(np.ceil(len(ids) / 3))
    boot = []
    for _ in range(B):
        starts = rng.integers(0, len(ids) - 2, size=n_blocks)
        pick = np.concatenate([ids[s_:s_ + 3] for s_ in starts])[:len(ids)]
        sub = by.loc[pick]
        boot.append(sub["sum"].sum() / sub["size"].sum())
    boot = np.array(boot)
    p = float((1 + np.sum(boot - stat >= stat)) / (B + 1))
    return {"axis": CHES[term]["axis"], "contested_votes": len(e), "sittings": len(ids), "scored_people": len(people),
            "mean_error_gap": round(float(stat), 4), "ci95": [round(float(np.quantile(boot, .025)), 4),
                                                             round(float(np.quantile(boot, .975)), 4)], "p": p}


def irt_1d(term: str, d: dict) -> dict:
    """Descriptive: 1-D 2PL by MAP on contested votes of the H3 period; club means of theta (sign: mayor > 0)."""
    meta, v = d["meta"], d["v"]
    start = T("2018-11-15") if term == "2018" else T("2023-02-16")
    sub = v[(meta.t >= start).values]
    Y = np.where(sub.isin(PRESENT).values, (sub == "Hlas pro").values.astype(float), np.nan)
    share = np.nanmean(Y, axis=1)
    keep = (np.minimum(share, 1 - share) >= 0.025) & (np.sum(~np.isnan(Y), axis=1) >= 20)
    Y = Y[keep].T  # people x votes
    people = list(sub.columns)
    ok = np.sum(~np.isnan(Y), axis=1) >= 50
    Y, people = Y[ok], [p for p, o in zip(people, ok) if o]
    n, m = Y.shape
    mask = ~np.isnan(Y)
    Yz = np.nan_to_num(Y)
    rng = np.random.default_rng(SEED)

    def nlp(par):
        th, a, b = par[:n], par[n:n + m], par[n + m:]
        z = np.outer(th, b) + a
        ll = np.where(mask, Yz * z - np.logaddexp(0, z), 0).sum()
        return -(ll - 0.5 * th @ th - 0.5 * (a @ a + b @ b) / 2.5 ** 2)

    def grad(par):
        th, a, b = par[:n], par[n:n + m], par[n + m:]
        z = np.outer(th, b) + a
        r = np.where(mask, Yz - expit(z), 0)
        return -np.concatenate([r @ b - th, r.sum(0) - a / 2.5 ** 2, th @ r - b / 2.5 ** 2])

    best = None
    for _ in range(10):
        x0 = rng.normal(0, .5, n + 2 * m)
        f = minimize(nlp, x0, jac=grad, method="L-BFGS-B")
        if best is None or f.fun < best.fun:
            best = f
    th = best.x[:n]
    th = (th - th.mean()) / th.std()
    mayor = "Hřib Zdeněk" if term == "2018" else "Svoboda Bohuslav"
    if mayor in people and th[people.index(mayor)] < 0:
        th = -th
    lists = pd.Series(d["lists"])
    df = pd.DataFrame({"theta": th}, index=people).join(lists.rename("list"))
    return {"votes": int(m), "people": int(n),
            "club_mean_theta": {k: round(float(g.theta.mean()), 2) for k, g in df.groupby("list")},
            "club_range_theta": {k: [round(float(g.theta.min()), 2), round(float(g.theta.max()), 2)]
                                 for k, g in df.groupby("list")}}


# ----------------------------------------------------------------------------------------------------------- H4

def h4(d: dict, rng) -> dict:
    meta, v, st = d["meta"], d["v"], d["status"]
    titles = pd.read_csv(RAW / "titles2022.csv", dtype=str).drop_duplicates("cislousneseni")
    m = meta.merge(titles[["cislousneseni", "title"]], on="cislousneseni", how="left")
    m["cat"] = m.title.map(classify)
    rows = (m.t >= T("2023-02-16")) & m.council
    opp_cells = v.where(st == 0)
    pres = opp_cells.isin(PRESENT)
    non = pres & (opp_cells != "Hlas pro")
    df = pd.DataFrame({"y": non.sum(axis=1) / pres.sum(axis=1), "w": pres.sum(axis=1), "cat": m.cat,
                       "sitting": m.sitting})[rows.values & (pres.sum(axis=1) > 0).values].reset_index(drop=True)
    cats = [c for c in sorted(df.cat.unique()) if c != "grants"]
    X = np.c_[np.ones(len(df)), np.column_stack([(df.cat == c).astype(float) for c in cats])]
    cols = ["const", *cats]
    w = df.w.values.astype(float)
    XtW = X.T * w
    bread = np.linalg.inv(XtW @ X)
    beta = bread @ XtW @ df.y.values
    e = df.y.values - X @ beta
    n_plan, n_prop = int((df.cat == "planning").sum()), int((df.cat == "property").sum())
    L = np.zeros(len(cols))
    L[cols.index("planning")] = n_plan / (n_plan + n_prop)
    L[cols.index("property")] = n_prop / (n_plan + n_prop)
    theta = float(L @ beta)
    # CR2 by sitting on the sqrt(w)-transformed problem
    g = df.sitting.values
    sw = np.sqrt(w)
    xt, et = X * sw[:, None], e * sw
    A = bread @ xt.T
    meat = np.zeros(len(cols))
    contrib = []
    for s_ in np.unique(g):
        ix = np.where(g == s_)[0]
        h = xt[ix] @ bread @ xt[ix].T
        vals, vecs = np.linalg.eigh(np.eye(len(ix)) - (h + h.T) / 2)
        inv = np.where(vals > 1e-10, 1 / np.sqrt(np.clip(vals, 1e-10, None)), 0)
        contrib.append(L @ A[:, ix] @ ((vecs * inv) @ vecs.T @ et[ix]))
    G = len(contrib)
    se = float(np.sqrt(np.sum(np.square(contrib))))
    p_cr2 = float(tdist.sf(theta / se, G - 1))
    # wild cluster restricted bootstrap (Rademacher), null theta = 0 imposed by constrained WLS
    Lx = L[1:]
    # restricted fit: beta_r = beta - bread L' (L bread L')^-1 (L beta)
    br = beta - bread @ L * (theta / (L @ bread @ L))
    er = df.y.values - X @ br
    gi = np.searchsorted(np.unique(g), g)
    stats = []
    for _ in range(B):
        vg = rng.choice([-1.0, 1.0], size=G)[gi]
        ys = X @ br + er * vg
        bs = bread @ XtW @ ys
        es = ys - X @ bs
        ets = es * sw
        c_ = [L @ A[:, np.where(g == s_)[0]] @ ets[np.where(g == s_)[0]] for s_ in np.unique(g)]
        stats.append((L @ bs) / np.sqrt(np.sum(np.square(c_))))
    t_obs = theta / np.sqrt(np.sum(np.square([L @ A[:, np.where(g == s_)[0]] @ et[np.where(g == s_)[0]]
                                              for s_ in np.unique(g)])))
    p_wcr = float((1 + np.sum(np.array(stats) >= t_obs)) / (B + 1))
    del Lx
    return {"votes": len(df), "sittings": G, "theta_pp": round(100 * theta, 2), "se_cr2_pp": round(100 * se, 2),
            "p_cr2": round(p_cr2, 4), "p_wcr": round(p_wcr, 4), "n_planning": n_plan, "n_property": n_prop,
            "coef_pp_vs_grants": {c: round(100 * float(b_), 2) for c, b_ in zip(cols, beta) if c != "const"},
            "grants_level_pp": round(100 * float(beta[0]), 2),
            "mean_nonsupport_by_category_pp": {c: round(100 * float(np.average(g_.y, weights=g_.w)), 2)
                                               for c, g_ in df.groupby("cat")}}


# ---------------------------------------------------------------------------------------------------------- RQ5

def rq5(data: dict) -> list[dict]:
    rows = []
    for term, d in data.items():
        v, st, meta = d["v"], d["status"], d["meta"]
        lists = pd.Series(d["lists"])
        for t_, a, b, coal in COALITIONS:
            if t_ != term:
                continue
            r = (meta.t >= a) & (meta.t < b)
            if r.sum() < 50:
                continue
            for lst in sorted(lists.dropna().unique()):
                ppl = [p for p in lists[lists == lst].index if p in v]
                cells = v.loc[r.values, ppl]
                pres = cells.isin(PRESENT)
                if pres.values.sum() < 500:
                    continue
                rows.append({"term": term, "from": str(a.date()), "to": str(b.date()), "list": lst,
                             "status": "interregnum" if coal is None else ("coalition" if lst in coal else "opposition"),
                             "votes": int(r.sum()), "yes_share": round(float((cells == "Hlas pro").values.sum() / pres.values.sum()), 3),
                             "against_per_100": round(float(100 * (cells == "Hlas proti").values.sum() / pres.values.sum()), 3)})
    return rows


def minority_clubs(term: str, d: dict) -> dict:
    """Exploratory (after registration): on contested votes of the H3 period, which clubs had a majority not voting
    yes. Shows what kind of split the votes are."""
    meta, v = d["meta"], d["v"]
    start = T("2018-11-15") if term == "2018" else T("2023-02-16")
    lists = pd.Series(d["lists"]).dropna()
    counts, n = {}, 0
    for i in np.where((meta.t >= start).values)[0]:
        cells = v.loc[i]
        pres = cells.isin(PRESENT)
        if pres.sum() < 20:
            continue
        yes = (cells[pres] == "Hlas pro")
        if min(yes.mean(), 1 - yes.mean()) < 0.025:
            continue
        n += 1
        no_clubs = []
        for lst in sorted(lists.unique()):
            ppl = [p for p in lists[lists == lst].index if p in pres.index and pres[p]]
            if ppl and (cells[ppl] != "Hlas pro").mean() > 0.5:
                no_clubs.append(lst)
        key = " + ".join(no_clubs) if no_clubs else "(no club; scattered)"
        counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
    return {"contested": n, "top": [{"clubs_not_yes": k, "votes": c, "share": round(c / n, 3)} for k, c in top]}


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, stop = {}, False
    for i, (k, p) in enumerate(items):
        thr = 0.05 / (len(items) - i)
        rej = (not stop) and p <= thr
        stop = stop or not rej
        out[k] = {"p": round(p, 4), "threshold": round(thr, 4), "reject": bool(rej)}
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    data = terms()
    out = {"H1": h1(data, rng), "H1_explicit_nonsupport": h1(data, rng, "explicit"),
           "H1_stayers": h1(data, rng, stayers_only=True), "shift_share": shift_share(data),
           "newcomers": newcomers(data)}
    s = sittings(data)
    cont = {}
    for a, b in [("2014", "2018")]:
        both = sorted(set(data[a]["v"].columns) & set(data[b]["v"].columns) - {"neurčeno"})
        cont = {a: both, b: both}
    s_c = sittings({k: data[k] for k in ["2014", "2018"]}, cont)
    s_c = s_c.assign(share=s_c.ab / (s_c.ab + s_c.nh))
    out["H2"] = {"all_members": jump(s, "share", rng), "official_totals": jump(s, "official", rng),
                 "continuing_members": jump(s_c, "share", rng), "continuing_n": len(cont.get("2014", [])),
                 "series": s[["term", "t", "ab", "nh", "share", "official"]].assign(t=lambda x: x.t.astype(str)).round(4)
                 .to_dict(orient="records")}
    out["H3"] = {term: h3_period(term, data[term], rng) for term in ["2018", "2022"]}
    out["H3_p"] = max(out["H3"]["2018"]["p"], out["H3"]["2022"]["p"])
    out["H3_minority_clubs"] = {term: minority_clubs(term, data[term]) for term in ["2018", "2022"]}
    out["IRT"] = {term: irt_1d(term, data[term]) for term in ["2018", "2022"]}
    out["H4"] = h4(data["2022"], rng)
    out["RQ5"] = rq5(data)
    out["robustness"] = {
        "H1_no_status_adjustment": h1(data, rng, adjust=False),
        "H1_passed_only": h1(data, rng, passed_only=True),
        "H1_without_2010_14": h1(data, rng, skip=("2010->2014",)),
        "H1_stayers": out["H1_stayers"],
        "not_run": ["conditional logit and Kline-Santos score bootstrap (H1)", "Lee bounds for non-return (H1)",
                    "H3 with 1 % / 5 % lopsidedness and nehlasoval as missing", "H4 with session fixed effects",
                    "selection audit against full session records"],
    }
    out["holm"] = holm({"H1": out["H1"]["p"], "H3": out["H3_p"], "H4": out["H4"]["p_cr2"]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n")
    brief = {k: out[k] for k in ["H1", "H1_explicit_nonsupport", "H1_stayers", "shift_share", "newcomers", "H3",
                                 "IRT", "H4", "holm"]}
    brief["H2"] = {k: v_ for k, v_ in out["H2"].items() if k != "series"}
    print(json.dumps(brief, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
