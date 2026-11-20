from __future__ import annotations

import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from scipy import optimize, special
from scipy.stats import beta as Beta
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PLAYERS = {"pastrnak": 8477956, "necas": 8480039}
TARGETS = {"pastrnak": 1000, "necas": 500}
STRENGTHS = ["PP", "SH", "even_other", "extra_attacker"]
Z80 = 1.2816


def load_csv(name: str) -> list[dict]:
    with gzip.open(DATA / name, "rt", newline="") as f:
        return list(csv.DictReader(f))


def load(name: str):
    return json.loads((DATA / name).read_text())


def features(shots: list[dict], types: list[str]) -> np.ndarray:
    rows = []
    for s in shots:
        x, y = float(s["x"]), float(s["y"])
        dx = 89 - min(x, 89)
        dist = math.hypot(dx, y)
        ang = math.degrees(math.atan2(abs(y), max(dx, 0.5)))
        tip = int(s["type"] in ("tip-in", "deflected"))
        rows.append([dist, dist ** 2, ang, dist * ang, int(s["reb"]), tip * dist]
                    + [int(s["type"] == t) for t in types] + [int(s["st"] == k) for k in STRENGTHS])
    return np.array(rows, dtype=float)


def model():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))


def xg(shots: list[dict], rng) -> dict:
    tc = Counter(s["type"] for s in shots)
    types = [t for t, c in tc.items() if c / len(shots) >= 0.01 and t != "unknown"]
    X, y = features(shots, types), np.array([int(s["goal"]) for s in shots])
    groups = np.array([s["gid"] for s in shots])
    oof, oof_d = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups):
        oof[te] = model().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        oof_d[te] = model().fit(X[tr][:, :2], y[tr]).predict_proba(X[te][:, :2])[:, 1]
    p_att = y.mean()
    out = {"attempts": len(y), "goals": int(y.sum()), "sum_xg": round(float(oof.sum()), 1),
           "auc": round(roc_auc_score(y, oof), 3), "auc_distance": round(roc_auc_score(y, oof_d), 3),
           "log_loss": round(log_loss(y, oof), 4), "log_loss_base": round(log_loss(y, np.full(len(y), p_att)), 4),
           "brier": round(brier_score_loss(y, oof), 4), "p_att": round(float(p_att), 4)}
    hi = oof > 0.2
    out["high_bin"] = {"n": int(hi.sum()), "pred": round(float(oof[hi].mean()), 3), "obs": round(float(y[hi].mean()), 3)}
    team = defaultdict(lambda: [0.0, 0])
    for s, p in zip(shots, oof):
        team[s["team"]][0] += p
        team[s["team"]][1] += int(s["goal"])
    out["team_mad_pct"] = round(float(np.mean([abs(a - b) / b * 100 for a, b in team.values() if b])), 1)
    sog = np.array([int(s["sog"]) for s in shots]) == 1
    out["league_xg_per_sog"] = round(float(oof[sog].sum() / sog.sum()), 4)

    shooter = np.array([int(s["shooter"] or 0) for s in shots])
    agg = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for sid, g, p in zip(shooter, y, oof):
        a = agg[sid]; a[0] += 1; a[1] += g; a[2] += p; a[3] += p * (1 - p)
    funnel = [[k, v[0], round(v[1] - v[2], 2), round(math.sqrt(v[3]), 2)] for k, v in agg.items() if k and v[0] >= 30]
    above = sum(1 for f in funnel if f[2] / f[3] > Z80)
    out["funnel"] = funnel
    out["funnel_above"] = {"above": above, "expected": round(0.1 * len(funnel), 1), "n": len(funnel)}

    players = {}
    for key, pid in PLAYERS.items():
        m = shooter == pid
        if m.sum() == 0:
            continue
        # Refit without the player so he is never judged on shots that trained the model.
        p = model().fit(X[~m], y[~m]).predict_proba(X[m])[:, 1]
        sims = (rng.random((20000, len(p))) < p).sum(1) - p.sum()
        lo, hi_ = np.percentile(sims, [10, 90])
        g = int(y[m].sum())
        idx = np.where(m)[0]
        players[key] = {"attempts": int(m.sum()), "sog": int(sog[m].sum()), "goals": g, "xg": round(float(p.sum()), 2),
                        "gax": round(g - float(p.sum()), 2), "band80": [round(float(lo), 1), round(float(hi_), 1)],
                        "z": round((g - float(p.sum())) / math.sqrt(float((p * (1 - p)).sum())), 2),
                        "xg_per_sog": round(float(p[sog[m]].sum() / max(sog[m].sum(), 1)), 4),
                        "shots": [[round(float(shots[i]["x"]), 1), round(float(shots[i]["y"]), 1), round(float(q), 3),
                                   int(shots[i]["goal"]), shots[i]["type"]] for i, q in zip(idx, p)]}
    out["players"] = players
    return out


def fit_prior(hist: dict, min_sog: int) -> tuple[float, float, int]:
    G, S = [], []
    for rows in hist["skaters"].values():
        for _, pos, g, s in rows:
            if pos in ("C", "L", "R") and s >= min_sog:
                G.append(g); S.append(s)
    G, S = np.array(G), np.array(S)

    def nll(v):
        a, b = np.exp(v)
        return -np.sum(special.betaln(G + a, S - G + b) - special.betaln(a, b))

    a, b = np.exp(optimize.minimize(nll, [np.log(10), np.log(80)], method="Nelder-Mead").x)
    return float(a), float(b), len(G)


def shrink(hist: dict, landing: dict) -> dict:
    ss = landing["featuredStats"]["regularSeason"]["subSeason"]
    ct = landing["careerTotals"]["regularSeason"]
    g, s = ss["goals"], ss["shots"]
    out = {"goals": g, "sog": s, "raw": round(g / s, 4) if s else None}
    for cut in (30, 100):
        a, b, n = fit_prior(hist, cut)
        post = Beta(a + g, b + s - g)
        out[f"league_{cut}"] = {"mean": round(post.mean(), 4), "lo": round(post.ppf(.1), 4), "hi": round(post.ppf(.9), 4),
                                "weight_own": round(s / (a + b + s), 3), "prior_mean": round(a / (a + b), 4), "n": n}
    pg, ps = ct["goals"] - g, ct["shots"] - s
    rate = pg / ps
    for ne in (150, 300, 600):
        post = Beta(ne * rate + g, ne * (1 - rate) + s - g)
        out[f"career_{ne}"] = round(post.mean(), 4)
    return out


def milestone(key: str, p: dict, hist: dict, rng) -> dict:
    cur = p["landing"]["careerTotals"]["regularSeason"]["points"]
    need = TARGETS[key] - cur
    dates = p["schedule"]
    this = [x["points"] for x in sorted(p["log"], key=lambda x: x["gameDate"])]
    past = [pts for s in sorted(hist["gamelogs"][key]) for _, pts in sorted(hist["gamelogs"][key][s])]
    allp = np.array(past + this)
    gp_past = sum(len(v) for v in hist["gamelogs"][key].values())
    team_games = 82 * len(hist["gamelogs"][key]) + len(this) + 0
    avail = (gp_past + len(this)) / max(team_games, 1)
    out = {"current": cur, "target": TARGETS[key], "need": need, "remaining": len(dates), "availability": round(avail, 3),
           "rate_last82": round(float(allp[-82:].mean()), 3), "rate_season": round(float(np.mean(this)), 3) if this else None}
    if need <= 0:
        out["reached"] = True
        return out
    windows = {"season": np.array(this), "last82": allp[-82:], "since2023": allp}
    runs = {}
    for wn, w in windows.items():
        if len(w) < 5:
            continue
        for av_name, av in (("all", 1.0), ("misses", avail)):
            idx = []
            for _ in range(20000):
                ww = rng.choice(w, len(w))
                pts = np.where(rng.random(len(dates)) < av, rng.choice(ww, len(dates)), 0).cumsum()
                if len(pts) and pts[-1] >= need:
                    idx.append(int(np.argmax(pts >= need)))
            r = {"p_season": round(len(idx) / 20000, 3)}
            if idx:
                q = np.percentile(idx, [10, 50, 90]).astype(int)
                r.update(d10=dates[q[0]], d50=dates[q[1]], d90=dates[q[2]])
            if wn == "last82" and av_name == "all" and idx:
                h = Counter(idx)
                out["hist"] = {dates[k]: v for k, v in sorted(h.items())}
            runs[f"{wn}|{av_name}"] = r
    out["runs"] = runs
    return out


def longest(a) -> int:
    best = cur = 0
    for v in a:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def streak(log: list[dict], rng) -> dict:
    a = np.array([x["points"] > 0 for x in sorted(log, key=lambda x: x["gameDate"])])
    obs = longest(a)
    perm = np.array([longest(rng.permutation(a)) for _ in range(10000)])
    vals, counts = np.unique(perm, return_counts=True)
    return {"games": len(a), "point_games": int(a.sum()), "longest": obs, "p_ge": round(float((perm >= obs).mean()), 3),
            "dist": {int(v): int(c) for v, c in zip(vals, counts)}}


def teams(games: list[dict], standings: list[dict], hist: dict) -> dict:
    past = np.array([r for rows in hist["standings"].values() for r in rows], dtype=float)
    k = optimize.minimize_scalar(lambda k: np.sum((past[:, 2] / (2 * past[:, 3]) - past[:, 0] ** k / (past[:, 0] ** k + past[:, 1] ** k)) ** 2),
                                 bounds=(1, 4), method="bounded").x
    gf, ga = Counter(), Counter()
    sf5, gf5, sa5, ga5 = Counter(), Counter(), Counter(), Counter()
    for g in games:
        h, a = g["home"], g["away"]
        hg, ag = int(g["hg"]), int(g["ag"])
        gf[h] += hg; ga[h] += ag; gf[a] += ag; ga[a] += hg
        sf5[h] += int(g["h_sf5"]); gf5[h] += int(g["h_gf5"]); sa5[h] += int(g["a_sf5"]); ga5[h] += int(g["a_gf5"])
        sf5[a] += int(g["a_sf5"]); gf5[a] += int(g["a_gf5"]); sa5[a] += int(g["h_sf5"]); ga5[a] += int(g["h_gf5"])
    p5 = sum(gf5.values()) / max(sum(sf5.values()), 1)
    rows = []
    for t in standings:
        ab = t["teamAbbrev"]["default"]
        if not sf5[ab] or not sa5[ab]:
            continue
        gp, pts = t["gamesPlayed"], t["points"]
        pyth = {kk: gf[ab] ** kk / (gf[ab] ** kk + ga[ab] ** kk) for kk in (1.8, 2.2, k)}
        resid = [(pts / (2 * gp) - v) * 2 * gp for v in pyth.values()]
        rows.append({"t": ab, "name": t["teamCommonName"]["default"], "gp": gp, "pts": pts, "gf": gf[ab], "ga": ga[ab],
                     "expected": round(pyth[k] * 2 * gp, 1), "resid": round((pts / (2 * gp) - pyth[k]) * 2 * gp, 1),
                     "resid_range": [round(min(resid), 1), round(max(resid), 1)],
                     "extra_time": t["otLosses"] + t["wins"] - t["regulationWins"],
                     "pdo": round(100 * (gf5[ab] / sf5[ab] + 1 - ga5[ab] / sa5[ab]), 1),
                     "pdo_sd": round(100 * math.sqrt(p5 * (1 - p5) / sf5[ab] + p5 * (1 - p5) / sa5[ab]), 2)})
    return {"k": round(float(k), 2), "k_n": len(past), "sh5": round(p5 * 100, 2), "rows": sorted(rows, key=lambda r: -r["resid"])}


def run() -> dict:
    rng = np.random.default_rng(88)
    shots, games, hist = load_csv("shots.csv.gz"), load_csv("games.csv.gz"), load("history.json")
    out = {"updated": date.today().isoformat(), "games": len(games),
           "last_game": max(g["date"] for g in games) if games else None, "xg": xg(shots, rng), "players": {}}
    for key in PLAYERS:
        p = load(f"{key}.json")
        out["players"][key] = {"shrink": shrink(hist, p["landing"]), "milestone": milestone(key, p, hist, rng),
                               "streak": streak(p["log"], rng),
                               "season": p["landing"]["featuredStats"]["regularSeason"]["subSeason"],
                               "log": [[x["gameDate"], x["opponentAbbrev"], x["homeRoadFlag"], x["goals"], x["assists"], x["shots"]]
                                       for x in sorted(p["log"], key=lambda x: x["gameDate"])]}
    st = load("standings.json")
    out["teams"] = teams(games, st, hist)
    sk = load("skaters.json")
    names = {r[0]: (r[1], r[2]) for r in sk}
    out["xg"]["funnel"] = [f + list(names.get(f[0], ("", ""))) for f in out["xg"]["funnel"]]
    out["skaters"] = sorted(sk, key=lambda r: (-r[7], -r[5]))[:100]
    return out


if __name__ == "__main__":
    res = run()
    (ROOT / "data.json").write_text(json.dumps(res, separators=(",", ":"), ensure_ascii=False, default=lambda o: o.item()))
    print(json.dumps({"games": res["games"], "last_game": res["last_game"], "auc": res["xg"]["auc"],
                      "players": {k: v.get("gax") for k, v in res["xg"]["players"].items()}}))
