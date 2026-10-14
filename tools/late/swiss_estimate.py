"""Estimates of the swiss-trams design (§4–§6): S and ρ for Zurich, Basel and Bern with the estimator of part 1, the
difference from Prague (D), the chance level S₀ by permuting segments among passes within date and hour, the excess
over chance (E, D_E), the descriptions of Q4 and the checks.

Reads tools/data/late/swiss_segments.parquet, swiss_passes.parquet, swiss_stops.parquet and swiss_sp/stops.txt (Swiss
GTFS, June 2025, for stop positions), part 1's tools/data/late/segments.parquet, and Prague's passes from the transit
database for the chance level. Writes docs/research/swiss-trams-results.json.

    nice -n 20 uv run --no-project --with numpy --with pandas --with pyarrow --with scipy --with duckdb \
        python tools/late/swiss_estimate.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
from estimate import MIDDAY, PEAK, REPS, SEED, TOP, concentration, jaccard, label, matrix, per_pass, stability, top_set  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/late"
OUT = ROOT / "docs/research/swiss-trams-results.json"
CITIES = ("Zurich", "Basel", "Bern")
SEED_CH, PERMS, MARGIN = 20261014, 199, 0.05


def draws(G: np.ndarray, N: np.ndarray, dates: pd.Index, rng, stat) -> np.ndarray:
    """The bootstrap of part 1 (whole service dates with replacement), returning the draws."""
    out = np.empty(REPS)
    for r in range(REPS):
        idx = rng.integers(0, len(dates), len(dates))
        out[r] = stat(G[:, idx], N[:, idx], idx)
    return out


def interval(x: np.ndarray, level: float) -> list[float]:
    a = (1 - level) / 2
    return [round(float(v), 4) for v in np.nanquantile(x, [a, 1 - a])]


def s_and_rho(seg: pd.DataFrame, rng) -> tuple[dict, np.ndarray]:
    """S and ρ as part 1's primary(): S first, then ρ, from one generator; returns S's draws too."""
    keys, dates, G, N = matrix(seg)
    week = np.array([pd.Timestamp(d).isocalendar().week for d in dates])
    s_draws = draws(G, N, dates, rng, lambda g, n, i: concentration(g.sum(1)))
    r_draws = draws(G, N, dates, rng, lambda g, n, i: stability(g, n, week[i] % 2 == 1))
    s, r = concentration(G.sum(1)), stability(G, N, week % 2 == 1)
    total = G.sum(1)
    s95, r95 = interval(s_draws, 0.95), interval(r_draws, 0.95)
    res = {"segments": len(keys), "dates": len(dates), "passes": int(N.sum()),
           "S": {"est": round(s, 4), "ci95": s95, "ci90": interval(s_draws, 0.90), "label": label(s95, 0.50),
                 "imprecise": s95[1] - s95[0] > 0.20},
           "rho": {"est": round(r, 4), "ci95": r95, "ci90": interval(r_draws, 0.90),
                   "label": label(r95, 0.70, at_or_above=True), "imprecise": r95[1] - r95[0] > 0.20},
           "producers": int((total > 0).sum()), "recoverers": int((total < 0).sum()),
           "recoverer_share": round(float((total < 0).mean()), 4)}
    return res, s_draws


def q3_label(diff: np.ndarray) -> str:
    """§5 Q3: like Prague, unlike Prague (more or less concentrated), underpowered for equivalence, inconclusive."""
    lo90, hi90 = interval(diff, 0.90)
    lo95, hi95 = interval(diff, 0.95)
    if -MARGIN <= lo90 and hi90 <= MARGIN:
        return "like Prague"
    if lo95 > MARGIN:
        return "unlike Prague, more concentrated"
    if hi95 < -MARGIN:
        return "unlike Prague, less concentrated"
    if hi90 - lo90 > 2 * MARGIN:
        return "underpowered for equivalence"
    return "inconclusive"


def compare(diff: np.ndarray, est: float) -> dict:
    return {"est": round(est, 4), "ci95": interval(diff, 0.95), "ci90": interval(diff, 0.90), "label": q3_label(diff)}


def chance(seg_id: np.ndarray, group: np.ndarray, g: np.ndarray, n_seg: int, rng) -> dict:
    """S₀: segment labels permuted among passes within each date × hour, S recomputed (§4)."""
    order = np.argsort(group, kind="stable")
    seg_id, group, g = seg_id[order], group[order], g[order]
    out = np.empty(PERMS)
    for k in range(PERMS):
        perm = np.lexsort((rng.random(len(group)), group))
        out[k] = concentration(np.bincount(seg_id[perm], weights=g, minlength=n_seg))
    return {"median": round(float(np.median(out)), 4), "range95": interval(out, 0.95)}


def codes(*cols: pd.Series) -> np.ndarray:
    return pd.MultiIndex.from_arrays(cols).factorize()[0]


def gini(total: np.ndarray) -> float:
    x = np.sort(total[total > 0])
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum())) if n else float("nan")


def length_share(seg: pd.DataFrame, xy: dict, top: float = TOP) -> dict:
    """§6 length: producers ranked by N_s taken until their straight-line length reaches 10 % of the network's."""
    t = seg.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum().reset_index()
    placed = t.seg_from.isin(xy) & t.seg_to.isin(xy)
    share_placed = float(t.loc[placed, "n"].sum() / t["n"].sum())
    if share_placed < 0.90:
        return {"reported": False, "share_of_passes_placed": round(share_placed, 4)}
    t = t[placed].copy()
    k = math.cos(math.radians(47.0))

    def km(a, b):
        (x0, y0), (x1, y1) = xy[a], xy[b]
        return math.hypot((x1 - x0) * k * 111.32, (y1 - y0) * 110.57)
    t["km"] = [km(a, b) for a, b in zip(t.seg_from, t.seg_to)]
    pair = t.apply(lambda r: tuple(sorted((r.seg_from, r.seg_to))), axis=1)
    network_km = t.assign(pair=pair).drop_duplicates("pair")["km"].sum()
    t = t.sort_values("gsum", ascending=False)
    take = t["km"].cumsum() <= top * network_km
    producers = t.loc[t.gsum > 0, "gsum"].sum()
    return {"reported": True, "share_of_passes_placed": round(share_placed, 4), "network_km": round(network_km, 1),
            "S_length": round(float(t.loc[take, "gsum"].sum() / producers), 4), "segments_taken": int(take.sum())}


def checks(seg: pd.DataFrame, xy: dict) -> dict:
    keys, dates, G, N = matrix(seg)
    month = pd.to_datetime(seg["date"]).dt.month
    out = {"per_pass": round(concentration(per_pass(G, N)), 4),
           "top_5": round(concentration(G.sum(1), 0.05), 4), "top_20": round(concentration(G.sum(1), 0.20), 4),
           "without_terminal_segments": round(concentration(matrix(seg[~seg["terminal"]])[2].sum(1)), 4),
           "gain_within_300s": round(concentration(matrix(seg, "gsum300", "n300")[2].sum(1)), 4),
           "by_month": {int(m): round(concentration(matrix(seg[month == m])[2].sum(1)), 4) for m in sorted(month.unique())},
           "gini": round(gini(G.sum(1)), 4),
           "peak_midday_jaccard": round(jaccard(top_set(seg, PEAK), top_set(seg, MIDDAY)), 4),
           "length": length_share(seg, xy)}
    if "real_share" in seg:
        well = seg[seg["real_share"] >= 0.90]
        out["well_measured_segments"] = {"segments": int(well.groupby(["seg_from", "seg_to"]).ngroups),
                                         "S": round(concentration(matrix(well)[2].sum(1)), 4)}
    return out


def swiss_xy() -> dict:
    """Stop name → (lon, lat): the mean of the GTFS stops whose number matches a BPUIC used under that name."""
    gtfs = pd.read_csv(DATA / "swiss_sp/stops.txt", dtype=str)
    gtfs["bpuic"] = gtfs.stop_id.str.split(":").str[0]
    pos = gtfs.groupby("bpuic")[["stop_lon", "stop_lat"]].apply(lambda d: d.astype(float).mean())
    names = pd.read_parquet(DATA / "swiss_stops.parquet").astype({"bpuic": str})
    names = names.join(pos, on="bpuic").dropna()
    return {r.name: (r.stop_lon, r.stop_lat) for r in names.groupby("name")[["stop_lon", "stop_lat"]].mean().reset_index()
            .itertuples()}


def prague_passes() -> pd.DataFrame:
    """Part 1's kept tram passes, rebuilt with its screening rules, for the chance level only."""
    import duckdb
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import screen as sc
    con = duckdb.connect(str(ROOT / "tools/data/rain/prague_transit.duckdb"), read_only=True)
    for s in ("threads = 2", "memory_limit = '4GB'", "preserve_insertion_order = false"):
        con.execute(f"SET {s}")
    con.register("closed", sc.excluded())
    feed = set(json.loads((ROOT / "docs/research/rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])
    con.register("feed", pd.DataFrame({"date_s": sorted(feed)}))
    keep = pd.read_parquet(DATA / "segments.parquet", columns=["mode", "seg_from", "seg_to"]).query("mode == 'tram'")
    con.register("keep", keep.drop_duplicates())
    parts = []
    for month in range(3, 10):
        con.execute(sc.PASSES.format(month=month))
        parts.append(con.execute(f"""
            SELECT p.seg_from, p.seg_to, CAST(p.date AS VARCHAR) AS date, p.hour, p.g
            FROM p
            JOIN keep ON keep.seg_from = p.seg_from AND keep.seg_to = p.seg_to
            LEFT JOIN closed ON closed.mode = p.mode AND closed.route = p.route AND closed.date_s = CAST(p.date AS VARCHAR)
            LEFT JOIN feed ON feed.date_s = CAST(p.date AS VARCHAR)
            WHERE p.mode = 'tram' AND p.date BETWEEN DATE '{sc.START}' AND DATE '{sc.END}'
              AND closed.route IS NULL AND feed.date_s IS NULL AND p.g IS NOT NULL AND abs(p.g) <= {sc.MAX_GAIN}
        """).df())
    return pd.concat(parts, ignore_index=True)


def chance_for(p: pd.DataFrame, rng) -> dict:
    seg_id = codes(p.seg_from, p.seg_to)
    return chance(seg_id, codes(p.date.astype(str), p.hour), p.g.to_numpy(float), seg_id.max() + 1, rng)


def main() -> None:
    sw = pd.read_parquet(DATA / "swiss_segments.parquet")
    sw["date"] = sw["date"].astype(str)
    passes = pd.read_parquet(DATA / "swiss_passes.parquet")
    prague = pd.read_parquet(DATA / "segments.parquet").query("mode == 'tram'")

    # Prague's draws: part 1's generator and order (S first), so its published interval is reproduced
    pr, pr_draws = s_and_rho(prague, np.random.default_rng(SEED))
    published = json.loads((ROOT / "docs/research/delay-origins-results.json").read_text())["tram"]
    assert pr["S"]["ci95"] == published["S"]["ci95"] and pr["S"]["est"] == published["S"]["est"], "part 1 not reproduced"
    res = {"top_share": TOP, "margin": MARGIN, "prague": {"S": pr["S"], "rho": pr["rho"]}, "cities": {}}
    rng_c = np.random.default_rng(SEED_CH + 1)
    s0_prague = chance_for(prague_passes(), rng_c)
    res["prague"]["S0"] = s0_prague
    from tram_geo import tram_stops
    xy_pr = {r.name: (r.lon, r.lat) for r in tram_stops().itertuples()}
    res["prague"]["checks"] = {"gini": round(gini(matrix(prague)[2].sum(1)), 4), "length": length_share(prague, xy_pr)}
    e_prague = pr_draws - s0_prague["median"]

    xy = swiss_xy()
    for k, city in enumerate(CITIES):
        seg = sw[(sw.city == city) & (sw.n > 0)]
        out, s_draws = s_and_rho(seg, np.random.default_rng(SEED_CH + 10 * (k + 1)))
        s0 = chance_for(passes[passes.city == city], rng_c)
        out["S0"] = s0
        out["D"] = compare(s_draws - pr_draws, out["S"]["est"] - pr["S"]["est"])
        out["E"] = round(out["S"]["est"] - s0["median"], 4)
        out["D_E"] = compare((s_draws - s0["median"]) - e_prague,
                             out["E"] - (pr["S"]["est"] - s0_prague["median"]))
        out["checks"] = checks(seg, xy)
        if city == "Basel":
            bvb = seg[seg.op == "BVB"]
            tot = seg.groupby(["seg_from", "seg_to", "op"]).gsum.sum().unstack(fill_value=0)
            out["checks"]["basel"] = {"BVB_only_S": round(concentration(matrix(bvb)[2].sum(1)), 4),
                                      "S_BVB_passes": round(concentration(tot.get("BVB", pd.Series(dtype=float)).to_numpy()), 4),
                                      "S_BLT_passes": round(concentration(tot.get("BLT", pd.Series(dtype=float)).to_numpy()), 4)}
        res["cities"][city] = out

    # §6 forecasts kept, Geneva included
    fc = sw[sw.n_fc > 0].rename(columns={"n": "n_real", "gsum": "gsum_real", "n_fc": "n", "gsum_fc": "gsum"})
    res["forecasts_kept"] = {}
    for k, city in enumerate((*CITIES, "Geneva")):
        seg = fc[fc.city == city]
        out, _ = s_and_rho(seg, np.random.default_rng(SEED_CH + 100 + k))
        res["forecasts_kept"][city] = {"segments": out["segments"], "passes": out["passes"], "S": out["S"],
                                       "rho": out["rho"]}
    screen = json.loads((ROOT / "docs/research/swiss-trams-screen.json").read_text())
    res["minute_schedules"] = {"prague_share_not_whole_minutes": screen["prague_schedule"]["share_not_whole_minutes"],
                               "check": "both timetables are to the minute; nothing recomputed (§6)"}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({c: {k: v[k] for k in ("S", "rho", "D", "D_E")} for c, v in res["cities"].items()}, indent=1))


if __name__ == "__main__":
    main()
