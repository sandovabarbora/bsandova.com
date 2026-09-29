"""Part 3 extended: the registered analysis (docs/research/prague-districts-design.md, §3-§8, with the changes of
29 September 2026).

Inputs (tools/data/praha3x/, not committed): grants.csv (tools/praha/districts_grants.py --build), the frozen
alignment (alignment/panel.csv, coder files), allocation tables (city/approved_*), MONITOR reports (api/), ČSÚ
population (mc_pop.xlsx) and age (mc_age.xlsx), candidate registers (kv*/).

Writes assets/praha/districts_extended.json: H1, H2 with Holm, the TOST, the event study with its pre-trend test,
HonestDiD-type relative-magnitude intervals, the placebo event, de Chaisemartin-D'Haultfœuille DID_M, the
party-level permutation, the MONITOR 2022-2025 secondary with covariate balance, H3 and H4 (descriptive), and the
formula channel. Robustness and the specification curve are in tools/praha/districts_robust.py.

Usage:
    uv run --with pandas --with numpy --with openpyxl --with xlrd --with scipy python tools/praha/districts_extended.py
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import glob
import itertools
import json
import os
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get("PRAHA3X", ROOT / "tools" / "data" / "praha3x"))
OUT = ROOT / "assets" / "praha" / "districts_extended.json"
sys.path.insert(0, str(Path(__file__).parent))
import districts_alignment as al  # noqa: E402

YEARS = list(range(2015, 2024))  # regime-years of the budget-measure lists
EVENTS = {2018: ([2016, 2017, 2018], [2019, 2020, 2021]), 2023: ([2020, 2021, 2022], [2023])}  # bridge: 2023 only
B = 9999
RNG = np.random.default_rng(20260929)


def reseed(label: str) -> None:
    """Every block draws from its own fixed stream, so adding a block never moves another block's p-values."""
    global RNG
    RNG = np.random.default_rng([20260929, sum(ord(ch) * (i + 1) for i, ch in enumerate(label))])
INTERREGNUM = ("2015-11-10", "2016-04-27")  # registered; robustness also from the recalls of 22/23 Oct 2015
NON_DISCRETIONARY = {8, 98, 99}  # ÚZ 8 loans (NFV), 98 gambling-levy shares, 99 income-tax refunds
ICO = dict(pd.read_csv(RAW / "mc_ico.csv", dtype=str).values)


# ---------------------------------------------------------------- data


def regime_year(day: str) -> int:
    if "2018-11-15" <= day <= "2018-12-31":
        return 2019
    if "2023-01-01" <= day <= "2023-02-15":
        return 2022
    return int(day[:4])


DAYS = {2018: 318, 2019: 412, 2022: 411, 2023: 319}


def grant_rows() -> pd.DataFrame:
    g = pd.read_csv(RAW / "grants.csv", dtype={"uz": str, "ro": str})
    g = g[(g.city_own == True) & g.date.notna()].copy()  # noqa: E712
    g["uz_code"] = g.uz.str.split("/").str[0].astype(int)
    g["r"] = g.date.map(regime_year)
    return g


def grants(drop_interregnum: bool = False, variant: str = "primary",
           interregnum: tuple[str, str] = INTERREGNUM) -> pd.DataFrame:
    """City's own grants by district and regime-year, CZK a year (annualised), total / investment / current.
    variant: 'primary' = the city paying the district (5347 / 6363); 'signflip' = that minus what the district paid
    the city (4137 / 4251); 'discretionary' = primary without ÚZ 8, 98 and 99."""
    g = grant_rows()
    if drop_interregnum:
        g = g[~g.date.between(*interregnum)]
    if variant == "signflip":
        g["amount_czk"] = g.amount_czk.fillna(0) - g.from_district_czk.fillna(0)
    elif variant == "discretionary":
        g = g[~g.uz_code.isin(NON_DISCRETIONARY)]
    g["cap"] = g.investment.astype(str).str.lower().eq("true")
    measures = g[g.kind == "measures"]
    draw = g[(g.kind == "drawdown") & g.year.isin([2024, 2025])]
    out = []
    for src, d in [("measures", measures), ("drawdown", draw)]:
        s = d.groupby(["district", "r", "cap"]).amount_czk.sum().unstack(fill_value=0.0)
        s = s.reindex(columns=[False, True], fill_value=0.0)
        s.columns = ["cur", "cap"]
        s["total"] = s.cur + s.cap
        s["source"] = src
        out.append(s.reset_index())
    y = pd.concat(out)
    y = y[((y.source == "measures") & y.r.isin(YEARS)) | ((y.source == "drawdown") & y.r.isin([2024, 2025]))]
    days = y.r.map(DAYS).fillna(365.25)
    for k in ["cur", "cap", "total"]:
        y[k] = y[k] * 365.25 / days
    return y


def allocation(year: int) -> pd.Series:
    """Approved 'finanční vztah' by district, CZK, from the approved budget's allocation table."""
    pats = {2016: "approved_2016/*priloha_c_9*", 2020: "approved_2020/priloha_c_9_*", 2021: "approved_2021/priloha_c_8_*",
            2022: "approved_2022/priloha_c_8_*", 2023: "approved_2023/priloha_c_7_*", 2024: "approved_2024/priloha_c_8_*"}
    f = glob.glob(str(RAW / "city" / pats[year]))[0]
    sheets = pd.read_excel(f, sheet_name=None, header=None)
    df = [v for k, v in sheets.items() if "1-57" in k or "FVz" in k][0]
    hrow = next(i for i in range(15) if str(df.iloc[i, 0]).strip() == "Městská část")
    heads = [" ".join(str(c).split()) for c in df.iloc[hrow]]
    col = next(j for j, h in enumerate(heads) if re.search(rf"(FVZ|FVz) k MČ na rok {year} CELKEM$", h)
               or (year >= 2024 and h.startswith("CELKEM FVz")))
    body = first_block(df, hrow)
    s = pd.Series(body.iloc[:, col].values, index=body.iloc[:, 0].astype(str).str.strip())
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index = [canon(n) for n in s.index]
    s = s[~s.index.isna()]
    return s[~s.index.duplicated()] * 1000


def formula_parts(year: int) -> pd.DataFrame:
    """2020-2023: the formula amount before the floor/cap and the final approved total (CZK)."""
    pats = {2020: "approved_2020/priloha_c_9_*", 2021: "approved_2021/priloha_c_8_*",
            2022: "approved_2022/priloha_c_8_*", 2023: "approved_2023/priloha_c_7_*"}
    f = glob.glob(str(RAW / "city" / pats[year]))[0]
    df = [v for k, v in pd.read_excel(f, sheet_name=None, header=None).items() if "1-57" in k][0]
    hrow = next(i for i in range(15) if str(df.iloc[i, 0]).strip() == "Městská část")
    heads = [" ".join(str(c).split()) for c in df.iloc[hrow]]
    before = next(j for j, h in enumerate(heads) if h.startswith(f"FVz k MČ na r. {year} před dokrytím"))
    final = next(j for j, h in enumerate(heads) if re.search(rf"k MČ na rok {year} CELKEM", h))
    body = first_block(df, hrow)
    out = pd.DataFrame({"before": pd.to_numeric(body.iloc[:, before], errors="coerce").values,
                        "final": pd.to_numeric(body.iloc[:, final], errors="coerce").values},
                       index=[canon(str(n)) for n in body.iloc[:, 0]])
    return out.dropna()[lambda d: ~d.index.isna()] * 1000


SHORTS = {"Dol.Měcholupy": "Dolní Měcholupy", "Dol.Počernice": "Dolní Počernice", "Dol. Měcholupy": "Dolní Měcholupy",
          "Dol. Počernice": "Dolní Počernice", "Před.Kopanina": "Přední Kopanina", "Před. Kopanina": "Přední Kopanina"}


def first_block(df: pd.DataFrame, hrow: int) -> pd.DataFrame:
    """The table's 57 district rows: from the header to the 'Celkem 1-57' line (rows below repeat some districts)."""
    end = next((i for i in range(hrow + 1, len(df)) if str(df.iloc[i, 0]).strip().lower().startswith("celkem")),
               len(df))
    return df.iloc[hrow + 1:end]


def canon(name: str) -> str | None:
    name = " ".join(str(name).split())
    if re.fullmatch(r"Praha \d{1,2}", name) and int(name.split()[1]) <= 22:
        return name
    name = SHORTS.get(name, name)
    name = re.sub(r"^Praha\s?-\s?", "", name)
    ok = {"Běchovice", "Benice", "Březiněves", "Čakovice", "Ďáblice", "Dolní Chabry", "Dolní Měcholupy",
          "Dolní Počernice", "Dubeč", "Klánovice", "Koloděje", "Kolovraty", "Královice", "Křeslice", "Kunratice",
          "Libuš", "Lipence", "Lochkov", "Lysolaje", "Nebušice", "Nedvězí", "Petrovice", "Přední Kopanina",
          "Řeporyje", "Satalice", "Slivenec", "Suchdol", "Šeberov", "Štěrboholy", "Troja", "Újezd", "Velká Chuchle",
          "Vinoř", "Zbraslav", "Zličín"}
    return f"Praha-{name}" if name in ok else None


def population() -> pd.DataFrame:
    """Residents at 31 December by district and year (ČSÚ Prague office)."""
    s = pd.read_excel(RAW / "mc_pop.xlsx", header=None)
    cols = {}
    for i in range(s.shape[1]):
        m = re.search(r"31\.12\.(\d{4})", str(s.iloc[4, i]).replace("\n", ""))
        if m:
            cols[int(m.group(1))] = i
    p = s.iloc[6:, [2, 3, *cols.values()]]
    p.columns = ["code", "district", *cols.keys()]
    p = p[p.code.astype(str).str.fullmatch(r"\d{6}")].copy()
    p["district"] = p.district.astype(str).str.strip()
    return p.set_index("district").drop(columns="code").astype(float)


def ages(year: int = 2021) -> pd.DataFrame:
    df = pd.read_excel(RAW / "mc_age.xlsx", sheet_name=str(year), header=None)
    """Shares of 0-14 and 65+ in all residents; the sheet's first block of five-year groups is both sexes."""
    heads = [str(x).strip() for x in df.iloc[3]]
    name_col = next(j for j, h in enumerate(heads) if h.startswith("název městské"))
    first = heads.index("0–4")
    young_cols = [first, first + 1, first + 2]
    old_cols = list(range(heads.index("65–69"), heads.index("85+") + 1))
    body = df.iloc[4:61]
    tot = pd.to_numeric(body.iloc[:, first - 1], errors="coerce")
    young = body.iloc[:, young_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    old = body.iloc[:, old_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    return pd.DataFrame({"share_0_14": (young / tot).values, "share_65": (old / tot).values},
                        index=body.iloc[:, name_col].astype(str).str.strip().values)


def alignment_panel(rule: str = "A") -> pd.DataFrame:
    p = pd.read_csv(RAW / "alignment" / "panel.csv")
    p["Aalt"] = p[rule]
    return p


def stacked(y: pd.DataFrame, panel: pd.DataFrame, outcome: str, rule: str = "A", controls: str = "never",
            events: dict = EVENTS, drop: set | None = None) -> list[dict]:
    """Per event: Δ = mean(post) − mean(pre) for switch-in units and clean controls."""
    wide = panel.pivot(index="district", columns="r", values=rule)
    tier = panel.groupby("district").tier.first()
    yy = y.pivot_table(index="district", columns="r", values=outcome, aggfunc="sum").reindex(wide.index).fillna(0.0)
    out = []
    for e, (pre, post) in events.items():
        w = wide[pre + post]
        switch = (w[pre] == 0).all(axis=1) & (w[post] == 1).all(axis=1)
        if controls == "never":
            ctrl = (w == 0).all(axis=1)
        else:  # never + always aligned
            ctrl = (w == 0).all(axis=1) | (w == 1).all(axis=1)
        units = w.index[switch | ctrl]
        if drop:
            units = [u for u in units if u not in drop]
        d = yy.loc[units, post].mean(axis=1) - yy.loc[units, pre].mean(axis=1)
        out.append({"event": e, "units": list(units), "switch": switch[units].to_numpy(), "delta": d.to_numpy(),
                    "tier": tier[units].to_numpy(), "base0": (w.loc[units, pre[-1]] == 0).to_numpy(),
                    "pre_level_ctrl": float(yy.loc[[u for u, s in zip(units, switch[units]) if not s], pre].mean().mean()),
                    "pre_level_switch": float(yy.loc[[u for u, s in zip(units, switch[units]) if s], pre].mean().mean())})
    return out


# ---------------------------------------------------------------- inference


def welch(d: np.ndarray, sw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ns, nc = sw.sum(-1), (~sw).sum(-1)
    ms = np.where(sw, d, 0).sum(-1) / ns
    mc = np.where(~sw, d, 0).sum(-1) / nc
    vs = np.where(sw, (d - ms[..., None]) ** 2, 0).sum(-1) / np.maximum(ns - 1, 1)
    vc = np.where(~sw, (d - mc[..., None]) ** 2, 0).sum(-1) / np.maximum(nc - 1, 1)
    return ms - mc, vs / ns + vc / nc


def permutations(ev: dict, b: int = B) -> np.ndarray:
    """Switch-in labels permuted within tier among baseline-unaligned units (always-aligned controls keep theirs)."""
    out = np.tile(ev["switch"], (b, 1))
    for t in (0, 1):
        idx = np.where(ev["base0"] & (ev["tier"] == t))[0]
        k = int(ev["switch"][idx].sum())
        if len(idx) == 0:
            continue
        for i in range(b):
            lab = np.zeros(len(idx), bool)
            lab[RNG.choice(len(idx), k, replace=False)] = True
            out[i, idx] = lab
    return out


def pooled(evs: list[dict], perms: list[np.ndarray] | None = None, scale: dict | None = None):
    """Pooled switch-in estimate, its Welch SE, the studentised statistic, and (with perms) the RI p-value."""
    total = sum(ev["switch"].sum() for ev in evs)
    est = var = 0.0
    pm = pv = 0.0
    for k, ev in enumerate(evs):
        d = ev["delta"] * (scale[ev["event"]] if scale else 1.0)
        w = ev["switch"].sum() / total
        m, v = welch(d, ev["switch"])
        est, var = est + w * m, var + w**2 * v
        if perms is not None:
            mp, vp = welch(np.broadcast_to(d, perms[k].shape), perms[k])
            pm, pv = pm + w * mp, pv + w**2 * vp
    t = est / np.sqrt(var)
    out = {"estimate": float(est), "se": float(np.sqrt(var)), "t": float(t)}
    if perms is not None:
        tp = pm / np.sqrt(pv)
        out["p_ri"] = float((1 + (tp >= t).sum()) / (1 + len(tp)))
        out["p_ri_lower"] = float((1 + (tp <= t).sum()) / (1 + len(tp)))
    return out


def conley_taber(evs: list[dict], level: float = 0.95, draws: int = 20000) -> list[float]:
    """CI from the controls' distribution of Δ (few treated units): W = Σ w_e (mean of n_e control residuals)."""
    total = sum(ev["switch"].sum() for ev in evs)
    est = sum(ev["switch"].sum() / total * (ev["delta"][ev["switch"]].mean() - ev["delta"][~ev["switch"]].mean())
              for ev in evs)
    w = np.zeros(draws)
    for ev in evs:
        res = ev["delta"][~ev["switch"]] - ev["delta"][~ev["switch"]].mean()
        n = int(ev["switch"].sum())
        w += ev["switch"].sum() / total * RNG.choice(res, (draws, n)).mean(axis=1)
    lo, hi = np.quantile(w, [(1 - level) / 2, 1 - (1 - level) / 2])
    return [float(est - hi), float(est - lo)]


def regression_form(y: pd.DataFrame, panel: pd.DataFrame, outcome: str, rule: str = "A", wcr_b: int = 9999,
                    drop: set | None = None):
    """Y_ier = α_ie + γ_re + β·switch×post, stacked; CR2 (clusters: districts) and WCR (Webb) p-values."""
    wide = panel.pivot(index="district", columns="r", values=rule)
    yy = y.pivot_table(index="district", columns="r", values=outcome, aggfunc="sum").reindex(wide.index).fillna(0.0)
    rows = []
    for e, (pre, post) in EVENTS.items():
        w = wide[pre + post]
        switch = (w[pre] == 0).all(axis=1) & (w[post] == 1).all(axis=1)
        ctrl = (w == 0).all(axis=1)
        for u in w.index[switch | ctrl]:
            if drop and u in drop:
                continue
            for r in pre + post:
                rows.append({"unit": f"{u}|{e}", "cl": u, "yr": f"{r}|{e}", "y": yy.loc[u, r],
                             "d": float(switch[u] and r in post)})
    df = pd.DataFrame(rows)
    X = pd.get_dummies(df[["unit", "yr"]], drop_first=True).astype(float)
    X.insert(0, "const", 1.0)
    X.insert(1, "d", df.d)
    Xv, yv = X.to_numpy(), df.y.to_numpy()
    XtX_inv = np.linalg.pinv(Xv.T @ Xv)
    beta = XtX_inv @ Xv.T @ yv
    e = yv - Xv @ beta
    groups = df.cl.to_numpy()
    G = np.unique(groups)
    H = Xv @ XtX_inv @ Xv.T
    meat = np.zeros((Xv.shape[1], Xv.shape[1]))
    for g in G:
        idx = groups == g
        Hg = H[np.ix_(idx, idx)]
        val, vec = np.linalg.eigh(np.eye(idx.sum()) - Hg)
        A = vec @ np.diag(1 / np.sqrt(np.clip(val, 1e-8, None))) @ vec.T
        s = Xv[idx].T @ (A @ e[idx])
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    se_cr2 = float(np.sqrt(V[1, 1]))
    t = beta[1] / se_cr2
    p_cr2 = float(1 - stats.t.cdf(t, len(G) - 1))
    # WCR: impose β = 0, Webb weights by cluster
    Xr = np.delete(Xv, 1, axis=1)
    br = np.linalg.pinv(Xr) @ yv
    er = yv - Xr @ br
    fit_r = Xr @ br
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    gidx = np.searchsorted(G, groups)
    P = np.linalg.pinv(Xv)
    tb = np.empty(wcr_b)
    for b in range(wcr_b):
        v = RNG.choice(webb, len(G))[gidx]
        yb = fit_r + er * v
        bb = P @ yb
        eb = yb - Xv @ bb
        s2 = 0.0
        for g in G:
            idx = groups == g
            sg = XtX_inv[1] @ (Xv[idx].T @ eb[idx])
            s2 += sg**2
        tb[b] = bb[1] / np.sqrt(s2)
    s_obs = np.sqrt(sum((XtX_inv[1] @ (Xv[groups == g].T @ e[groups == g])) ** 2 for g in G))
    t_obs = beta[1] / s_obs
    return {"beta": float(beta[1]), "se_cr2": se_cr2, "p_cr2": p_cr2, "p_wcr": float((1 + (tb >= t_obs).sum()) / (1 + wcr_b)),
            "clusters": int(len(G)), "rows": int(len(df))}


# ---------------------------------------------------------------- pieces


def event_study(y: pd.DataFrame, panel: pd.DataFrame, outcome: str) -> dict:
    """Per event, switchers minus controls by year, relative to the last pre year; lags from drawdown lists marked."""
    wide = panel.pivot(index="district", columns="r", values="A")
    yy = y.pivot_table(index="district", columns="r", values=outcome, aggfunc="sum").reindex(wide.index).fillna(0.0)
    res, leads_all = {}, []
    for e, (pre, post) in EVENTS.items():
        w = wide[pre + post]
        switch = (w[pre] == 0).all(axis=1) & (w[post] == 1).all(axis=1)
        ctrl = (w == 0).all(axis=1)
        years = [r for r in range(pre[0], post[0] + 3) if r in yy.columns]  # −3 … +2 around the first post year
        base = pre[-1]
        diff = {r: float((yy.loc[switch[switch].index, r].mean() - yy.loc[ctrl[ctrl].index, r].mean())
                         - (yy.loc[switch[switch].index, base].mean() - yy.loc[ctrl[ctrl].index, base].mean()))
                for r in years}
        res[str(e)] = {"relative_to": base, "first_post": post[0], "by_year": {str(r): diff[r] for r in years},
                       "descriptive_years": [r for r in years if r >= 2024]}
        leads_all.append((switch, ctrl, [r for r in pre if r != base], base))
    # joint pre-trend RI: sum of squared lead differences, labels permuted as in H1
    def lead_stat(sw_sets):
        tot = 0.0
        for (switch, ctrl, leads, base), sw in zip(leads_all, sw_sets):
            for r in leads:
                a = yy.loc[sw, r].mean() - yy.loc[(switch | ctrl) & ~sw, r].mean()
                b = yy.loc[sw, base].mean() - yy.loc[(switch | ctrl) & ~sw, base].mean()
                tot += (a - b) ** 2
        return tot
    obs = lead_stat([s for s, *_ in leads_all])
    evs = stacked(y, panel, outcome)
    perms = [permutations(ev, 1999) for ev in evs]
    count = 0
    for i in range(1999):
        sets = []
        for (switch, ctrl, *_), ev, P in zip(leads_all, evs, perms):
            s = pd.Series(False, index=switch.index)
            s[ev["units"]] = P[i]
            sets.append(s)
        count += lead_stat(sets) >= obs
    res["pretrend_joint_p_ri"] = float((1 + count) / 2000)
    return res


def honest(es: dict, est: float, se: float) -> dict:
    """Relative-magnitudes bound (Rambachan-Roth, simplified): the post-period violation is at most M̄ times the
    largest pre-period change; the interval widens by that bound (sampling noise in the bound ignored)."""
    pre_changes = []
    for e in ("2018", "2023"):
        by = es[e]["by_year"]
        yrs = sorted(int(k) for k in by if int(k) <= es[e]["relative_to"])
        vals = [by[str(r)] for r in yrs]
        pre_changes += [abs(b - a) for a, b in zip(vals, vals[1:])]
    m = max(pre_changes) if pre_changes else 0.0
    return {str(mb): [est - mb * m - 1.96 * se, est + mb * m + 1.96 * se] for mb in (0.5, 1.0)} | {"max_pre_change": m}


def dcdh(y: pd.DataFrame, panel: pd.DataFrame, outcome: str, boot: int = 999) -> dict:
    """de Chaisemartin-D'Haultfœuille DID_M over 2015-2023 (switches on and off), and joiners only; district bootstrap."""
    wide = panel.pivot(index="district", columns="r", values="A")[YEARS]
    yy = y.pivot_table(index="district", columns="r", values=outcome, aggfunc="sum").reindex(wide.index).fillna(0.0)[YEARS]

    def est(idx):
        A, Y = wide.loc[idx].to_numpy(), yy.loc[idx].to_numpy()
        num_m = num_p = den_m = den_p = 0.0
        for t in range(1, A.shape[1]):
            dY = Y[:, t] - Y[:, t - 1]
            J = (A[:, t - 1] == 0) & (A[:, t] == 1)
            S0 = (A[:, t - 1] == 0) & (A[:, t] == 0)
            L = (A[:, t - 1] == 1) & (A[:, t] == 0)
            S1 = (A[:, t - 1] == 1) & (A[:, t] == 1)
            if J.sum() and S0.sum():
                num_m += J.sum() * (dY[J].mean() - dY[S0].mean())
                num_p += J.sum() * (dY[J].mean() - dY[S0].mean())
                den_m += J.sum()
                den_p += J.sum()
            if L.sum() and S1.sum():
                num_m += L.sum() * (dY[S1].mean() - dY[L].mean())
                den_m += L.sum()
        return num_m / den_m, num_p / den_p
    m, p = est(wide.index)
    bs = np.array([est(RNG.choice(wide.index, len(wide.index))) for _ in range(boot)])
    return {"did_m": float(m), "did_m_ci": np.quantile(bs[:, 0], [0.025, 0.975]).tolist(),
            "did_plus": float(p), "did_plus_ci": np.quantile(bs[:, 1], [0.025, 0.975]).tolist()}


def placebo(y: pd.DataFrame, panel: pd.DataFrame, outcome: str) -> dict:
    """Pseudo-event between regime-years 2020 and 2021 (no coalition change): the 2023 event's switch-ins and clean
    controls, pre 2019-2020, post 2021-2022."""
    evs = stacked(y, panel, outcome, events={2023: ([2020, 2021, 2022], [2023])})
    ev = evs[0]
    wide = y.pivot_table(index="district", columns="r", values=outcome, aggfunc="sum").fillna(0.0)
    d = wide.reindex(ev["units"]).fillna(0.0)
    ev = ev | {"delta": (d[[2021, 2022]].mean(axis=1) - d[[2019, 2020]].mean(axis=1)).to_numpy(), "event": "placebo"}
    return pooled([ev], [permutations(ev)])


def party_permutation(y: pd.DataFrame, outcome: str) -> dict:
    """Replace the entering parties at each event by every equal-size set of parties that held a mayor then."""
    reg = al.registers()
    coders = {c: al.spells(RAW / "alignment" / f"coder_{c}.csv") for c in "A"}
    panel = pd.read_csv(RAW / "alignment" / "panel.csv")
    party = {}
    for _, row in panel.iterrows():
        day = f"{row.r}-06-30"
        m = al.mayor_on(coders["A"], row.district, day)
        party[(row.district, row.r)] = al.register_party(m, reg, int(row.code), day)
    held = {r: {p for (d, rr), p in party.items() if rr == r and p and p != "LOCAL"} for r in YEARS}
    actual = {2018: ({"ANO", "ČSSD", "SZ", "KDU-ČSL", "STAN"}, {"Piráti", "PRAHA SOBĚ", "TOP 09", "STAN", "KDU-ČSL"}),
              2023: ({"Piráti", "PRAHA SOBĚ", "TOP 09", "STAN", "KDU-ČSL"}, {"ODS", "TOP 09", "KDU-ČSL", "Piráti", "STAN"})}

    def stat_for(post_sets):
        evs = []
        for e, (pre, post) in EVENTS.items():  # each event's stack is rebuilt on its own relabelled panel
            p2 = panel.copy()
            cpre, _ = actual[e]
            for r in pre + post:
                c = cpre if r in pre else post_sets[e]
                p2.loc[p2.r == r, "A"] = [int(party[(d, r)] in c) if party[(d, r)] else 0 for d in p2[p2.r == r].district]
            evs.append(stacked(y, p2, outcome, events={e: EVENTS[e]})[0])
        return pooled(evs)["t"] if all(ev["switch"].sum() for ev in evs) else np.nan
    obs = stat_for({e: actual[e][1] for e in EVENTS})
    draws = []
    options = {}
    for e in EVENTS:
        cpre, cpost = actual[e]
        staying = cpre & cpost
        entering = cpost - cpre
        pool = sorted(held[EVENTS[e][1][0]] - staying)
        options[e] = [staying | set(s) for s in itertools.combinations(pool, len(entering))]
    for s18, s23 in itertools.product(options[2018], options[2023]):
        draws.append(stat_for({2018: s18, 2023: s23}))
    draws = np.array([d for d in draws if not np.isnan(d)])
    return {"t_obs": float(obs), "sets": int(len(draws)), "p": float((draws >= obs).mean()),
            "entering_options": {str(e): len(v) for e, v in options.items()}}


# ---------------------------------------------------------------- MONITOR


def node_values(path: Path, codes: set[str]) -> dict:
    out = {c: {"approved": 0.0, "afterChanges": 0.0, "reality": 0.0} for c in codes}
    stack = json.loads(path.read_text()).get("children") or []
    while stack:
        c = stack.pop()
        if c["code"] in codes:
            for k in out[c["code"]]:
                out[c["code"]][k] += c["budget"][k] or 0.0
        stack += c.get("children") or []
    return out


def monitor() -> pd.DataFrame:
    rows = []
    for name, ico in ICO.items():
        for y in (2022, 2023, 2024, 2025):
            api = RAW / "api"
            inc = node_values(api / f"{ico}_{y}_prij.json", {"4137", "4251"})
            out = node_values(api / f"{ico}_{y}_dru.json", {"5347", "6", "5901"})
            tot = json.loads((api / f"{ico}_{y}_tot.json").read_text())
            rows.append({"district": name, "year": y,
                         "D": sum(inc[c]["reality"] - inc[c]["approved"] for c in inc),
                         "ret_5347": out["5347"]["reality"],
                         "cap_real": out["6"]["reality"], "cap_amended": out["6"]["afterChanges"],
                         "res_5901_approved": out["5901"]["approved"],
                         "bal_real": tot["incomes"]["reality"] - tot["outgoings"]["reality"],
                         "bal_appr": tot["incomes"]["approved"] - tot["outgoings"]["approved"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main


def main() -> None:
    panel = pd.read_csv(RAW / "alignment" / "panel.csv")
    y = grants()
    r16 = allocation(2016)
    pop = population()
    ym = y[y.source == "measures"].copy()
    missing = sorted(set(panel.district) - set(r16.index))
    for k in ["total", "cap", "cur"]:
        ym[f"{k}_R"] = ym[k] / ym.district.map(r16)
        ym[f"{k}_pc"] = ym[k] / [pop.loc[d, r - 2] if d in pop.index else np.nan for d, r in zip(ym.district, ym.r)]
    ym["diff_R"] = ym.cap_R - ym.cur_R
    # every district-year, zeros where no grant
    full = pd.MultiIndex.from_product([sorted(panel.district.unique()), YEARS], names=["district", "r"])
    ym = ym.set_index(["district", "r"]).drop(columns="source").reindex(full).fillna(0.0).reset_index()
    result = {"allocation_2016_missing": missing, "units": {}}
    # H1
    reseed("H1")
    evs = stacked(ym, panel, "total_R")
    perms = [permutations(ev) for ev in evs]
    h1 = pooled(evs, perms)
    h1["relative_to_control_pre_mean"] = h1["estimate"] / np.mean([ev["pre_level_ctrl"] for ev in evs])
    h1["conley_taber_95"] = conley_taber(evs)
    h1["regression"] = regression_form(ym, panel, "total_R")
    h1["by_event"] = {str(ev["event"]): {"switch_in": int(ev["switch"].sum()), "controls": int((~ev["switch"]).sum()),
                                         "estimate": float(ev["delta"][ev["switch"]].mean() - ev["delta"][~ev["switch"]].mean()),
                                         "pre_level_ctrl": ev["pre_level_ctrl"], "pre_level_switch": ev["pre_level_switch"]}
                      for ev in evs}
    # TOST at ±20 % of the controls' pre-window mean (RI with the switchers' post values rescaled)
    ctrl_mean = np.mean([ev["pre_level_ctrl"] for ev in evs])
    m = 0.2 * ctrl_mean
    shifted_up = [ev | {"delta": ev["delta"] - np.where(ev["switch"], m, 0.0)} for ev in evs]
    shifted_dn = [ev | {"delta": ev["delta"] + np.where(ev["switch"], m, 0.0)} for ev in evs]
    p_upper = pooled(shifted_up, perms)["p_ri_lower"]   # H0: effect ≥ +m
    p_lower = pooled(shifted_dn, perms)["p_ri"]          # H0: effect ≤ −m
    h1["tost_margin_abs"] = m
    h1["tost_p"] = float(max(p_upper, p_lower))
    h1["tost_p_upper"] = float(p_upper)  # H0: premium ≥ +20 %
    h1["tost_p_lower"] = float(p_lower)  # H0: effect ≤ −20 %
    # H2: intersection-union
    evc = stacked(ym, panel, "cap_R")
    evd = stacked(ym, panel, "diff_R")
    p_cap = pooled(evc, perms)
    p_diff = pooled(evd, perms)
    h2 = {"cap": p_cap, "cap_minus_cur": p_diff, "p": float(max(p_cap["p_ri"], p_diff["p_ri"])),
          "cur": pooled(stacked(ym, panel, "cur_R"), perms)}
    # Holm
    ps = {"H1": h1["p_ri"], "H2": h2["p"]}
    order = sorted(ps, key=ps.get)
    holm, stop = {}, False
    for k, name in enumerate(order):
        thr = 0.05 / (len(order) - k)
        ok = (not stop) and ps[name] <= thr
        stop = stop or not ok
        holm[name] = {"p": ps[name], "threshold": thr, "rejected": ok}
    result |= {"H1": h1, "H2": h2, "holm": holm,
               "smallest_attainable_p": 1 / (B + 1)}
    reseed("switch_out")
    # switch-out (descriptive): aligned through the pre window, unaligned after, against always-aligned districts
    wide = panel.pivot(index="district", columns="r", values="A")
    so = []
    for e, (pre, post) in EVENTS.items():
        w = wide[pre + post]
        out_ = (w[pre] == 1).all(axis=1) & (w[post] == 0).all(axis=1)
        keep = (w == 1).all(axis=1)
        units = w.index[out_ | keep]
        yy = ym.pivot_table(index="district", columns="r", values="total_R", aggfunc="sum").reindex(wide.index).fillna(0)
        d = yy.loc[units, post].mean(axis=1) - yy.loc[units, pre].mean(axis=1)
        so.append({"event": e, "units": list(units), "switch": out_[units].to_numpy(), "delta": d.to_numpy(),
                   "tier": panel.groupby("district").tier.first()[units].to_numpy(),
                   "base0": np.ones(len(units), bool)})
    so = [ev for ev in so if ev["switch"].sum() and (~ev["switch"]).sum()]
    result["switch_out"] = (pooled(so, [permutations(ev, 999) for ev in so]) if so else {}) | {
        "switch_out_units": {str(ev["event"]): int(ev["switch"].sum()) for ev in so},
        "always_aligned_controls": {str(ev["event"]): int((~ev["switch"]).sum()) for ev in so},
        "note": "descriptive; the sign is read as (aligned-then-not) minus (always aligned)"}
    align = json.loads((ROOT / "docs" / "research" / "prague-districts-alignment.json").read_text())
    result["mid_term_switches"] = align["other_switches"]
    result["always_aligned_by_event"] = {k: v["always"] for k, v in align["events"].items()}
    # composition of the outcome: shares of ÚZ 8 (loans), 98 (gambling levy), 99 (income-tax refunds) by year
    gr = grant_rows()
    gr = gr[(gr.kind == "measures") & gr.r.isin(YEARS)]
    comp = {}
    for r_ in YEARS:
        t = gr[gr.r == r_].amount_czk.sum()
        comp[str(r_)] = {str(u): float(gr[(gr.r == r_) & (gr.uz_code == u)].amount_czk.sum() / t) for u in (8, 98, 99)}
    result["composition"] = comp
    result["district_to_city_2016_2023"] = {
        "rows": int(((gr.from_district_czk > 0) & (gr.amount_czk == 0) & gr.r.between(2016, 2023)).sum()),
        "czk": float(gr[gr.r.between(2016, 2023)].from_district_czk.sum())}
    reseed("event_study")
    # event study, honest, placebo, dCDH, party permutation
    yall = y.copy()
    for k in ["total", "cap", "cur"]:
        yall[f"{k}_R"] = yall[k] / yall.district.map(r16)
    es = event_study(pd.concat([ym, yall[yall.source == "drawdown"][["district", "r", "total_R"]]]), panel, "total_R")
    result["event_study"] = es
    result["honest"] = honest(es, h1["estimate"], h1["se"])
    reseed("placebo")
    result["placebo"] = placebo(ym, panel, "total_R")
    reseed("dcdh")
    result["dcdh"] = dcdh(ym, panel, "total_R")
    result["party_permutation"] = party_permutation(ym, "total_R")
    # descriptive levels (for the article; no per-district table)
    lv = ym.merge(panel[["district", "r", "A", "tier"]], on=["district", "r"])
    result["levels"] = {
        "grants_total_czk_by_year": {str(r): float(ym[ym.r == r].total.sum()) for r in YEARS},
        "share_investment_by_year": {str(r): float(ym[ym.r == r].cap.sum() / ym[ym.r == r].total.sum()) for r in YEARS},
        "mean_total_R_by_A": {str(a): float(lv[lv.A == a].total_R.mean()) for a in (0, 1)},
        "median_total_R": float(ym.total_R.median()),
        "share_zero_district_years": float((ym.total == 0).mean()),
        "cv_within_district": float(ym.groupby("district").total_R.agg(lambda s: s.std() / s.mean() if s.mean() else np.nan).median()),
    }
    reseed("monitor")
    # MONITOR secondary (2023 event, 2022 pre, 2023-2025 post)
    mo = monitor()
    mo["pop"] = [pop.loc[d, yr - 2] for d, yr in zip(mo.district, mo.year)]
    mo["D_pc"] = mo.D / mo["pop"]
    mo["D_net_pc"] = (mo.D - mo.ret_5347) / mo["pop"]
    ap = panel  # the frozen panel already covers 30 June 2024 and 2025
    mo = mo.rename(columns={"year": "r"})
    sec = {}
    for out in ["D_pc", "D_net_pc"]:
        ev = stacked(mo, ap, out, events={2023: ([2022], [2023, 2024, 2025])})
        sec[out] = pooled(ev, [permutations(ev[0])]) | {"switch_in": int(ev[0]["switch"].sum()),
                                                        "controls": int((~ev[0]["switch"]).sum())}
    reseed("balance")
    # covariate balance for the MONITOR stack
    ev = stacked(mo, ap, "D_pc", events={2023: ([2022], [2023, 2024, 2025])})[0]
    units = ev["units"]
    ag = ages(2021)
    cov = pd.DataFrame({"pop_growth": [pop.loc[u, 2021] / pop.loc[u, 2015] - 1 for u in units],
                        "share_0_14": [ag.loc[u, "share_0_14"] if u in ag.index else np.nan for u in units],
                        "share_65": [ag.loc[u, "share_65"] if u in ag.index else np.nan for u in units]},
                       index=units)
    bal = {}
    for c in cov.columns:
        e2 = ev | {"delta": cov[c].to_numpy()}
        r_ = pooled([e2], [permutations(e2, B)])
        bal[c] = {"diff": r_["estimate"], "p_two_sided": float(min(1, 2 * min(r_["p_ri"], r_["p_ri_lower"])))}
    sec["balance"] = bal
    sec["population_growth_added"] = bal["pop_growth"]["p_two_sided"] < 0.1  # the registered trigger
    if True:  # the adjusted estimate is always reported; it is primary only if the trigger fired
        for out in ["D_pc", "D_net_pc"]:
            e3 = stacked(mo, ap, out, events={2023: ([2022], [2023, 2024, 2025])})[0]
            X = np.column_stack([np.ones(len(units)), cov.pop_growth.to_numpy()])
            resid = e3["delta"] - X @ np.linalg.lstsq(X[~e3["switch"]], e3["delta"][~e3["switch"]], rcond=None)[0]
            e3 = e3 | {"delta": resid}
            sec[out + "_adjusted"] = pooled([e3], [permutations(e3)])
    result["monitor_secondary"] = sec
    # H3 (exploratory, two-sided): capital execution on log population within tier, year effects
    h3 = mo[mo.cap_amended > 0].copy()
    h3["exec"] = h3.cap_real / h3.cap_amended
    h3["logpop"] = np.log(h3["pop"])
    h3 = h3.merge(panel.groupby("district").tier.first().rename("tier"), left_on="district", right_index=True)
    X = pd.get_dummies(h3[["r"]].astype(str), drop_first=True).astype(float)
    X.insert(0, "tier", h3.tier)
    X.insert(0, "logpop", h3.logpop)
    X.insert(0, "const", 1.0)
    result["H3"] = cr2_simple(X.to_numpy(), h3.exec.to_numpy(), h3.district.to_numpy(), 1) | {
        "n": int(len(h3)), "dropped_zero_amended": int((mo.cap_amended <= 0).sum()),
        "median_exec": float(h3.exec.median())}
    # H4 (descriptive): (actual − approved) balance per resident, district means
    mo["gap_pc"] = (mo.bal_real - mo.bal_appr) / mo["pop"]
    mo["gap_net_D_pc"] = mo.gap_pc - mo.D / mo["pop"]
    mo["gap_net_5901_pc"] = mo.gap_pc - mo.res_5901_approved / mo["pop"]
    h4 = {}
    for c in ["gap_pc", "gap_net_D_pc", "gap_net_5901_pc"]:
        dm = mo.groupby("district")[c].mean()
        popw = mo.groupby("district")["pop"].mean()
        t = stats.ttest_1samp(dm, 0.0)
        h4[c] = {"mean": float(dm.mean()), "median": float(dm.median()), "t": float(t.statistic),
                 "p_two_sided": float(t.pvalue), "positive": int((dm > 0).sum()), "n": int(len(dm)),
                 "pop_weighted_mean": float((dm * popw).sum() / popw.sum())}
    result["H4"] = h4
    # formula channel (descriptive)
    fc = {}
    for yr in (2020, 2021, 2022, 2023):
        try:
            fp = formula_parts(yr)
        except (StopIteration, IndexError):
            fc[str(yr)] = "table layout not recognised"
            continue
        fp["adj_share"] = fp.final / fp.before - 1
        a = panel[panel.r == yr].set_index("district").A
        fp = fp.join(a, how="inner")
        fc[str(yr)] = {str(k): float(v) for k, v in fp.groupby("A").adj_share.mean().items()} | {"n": int(len(fp))}
    a23, a24 = allocation(2023), allocation(2024)
    ch = (a24 / a23 - 1).dropna()
    al24 = ap[ap.r == 2024].set_index("district").A
    ch = pd.DataFrame({"change": ch}).join(al24, how="inner")
    fc["2024_rule_change"] = {str(k): float(v) for k, v in ch.groupby("A").change.mean().items()} | {
        "n": int(len(ch)), "median_change": float(ch.change.median())}
    result["formula_channel"] = fc
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float) + "\n")
    print(json.dumps({"H1": {k: h1[k] for k in ["estimate", "p_ri", "relative_to_control_pre_mean", "conley_taber_95", "tost_p"]},
                      "H2_p": h2["p"], "holm": holm}, ensure_ascii=False, default=float))


def cr2_simple(X: np.ndarray, y: np.ndarray, groups: np.ndarray, j: int) -> dict:
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    H = X @ XtX_inv @ X.T
    meat = np.zeros((X.shape[1], X.shape[1]))
    G = np.unique(groups)
    for g in G:
        idx = groups == g
        val, vec = np.linalg.eigh(np.eye(idx.sum()) - H[np.ix_(idx, idx)])
        A = vec @ np.diag(1 / np.sqrt(np.clip(val, 1e-8, None))) @ vec.T
        s = X[idx].T @ (A @ e[idx])
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    se = float(np.sqrt(V[j, j]))
    t = b[j] / se
    return {"coef": float(b[j]), "se_cr2": se, "p_two_sided": float(2 * (1 - stats.t.cdf(abs(t), len(G) - 1))),
            "clusters": int(len(G))}


if __name__ == "__main__":
    main()
