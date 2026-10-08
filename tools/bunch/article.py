"""Why do two 22s come at once: figures, the map and the article, every number from the result files.

Reads docs/research/bunching-{results,results-bus,screen,describe,describe-bus,review}.json and the tram pair tables in tools/data/bunch/;
writes assets/bunch/ (charts.json, map.json, segments.json, results.json, describe.json, static SVGs) and
texts/bunching.html from tools/bunch/template.html. Chart and map helpers are part 1's and the rain article's.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with scipy --with numpy python tools/bunch/article.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ra = load_module("rain_article", "tools/rain/article.py")
la = load_module("late_article", "tools/late/article.py")
be = load_module("bunch_estimate", "tools/bunch/estimate.py")
plt, n = ra.plt, ra.n
R, A = ROOT / "docs" / "research", ROOT / "assets" / "bunch"
INK, HELD, GREY, LIGHT = "#111111", "#c0503f", "#666666", "#b5b5b0"


def load() -> dict:
    j = lambda name: json.loads((R / f"bunching-{name}.json").read_text())  # noqa: E731
    return {"res": j("results"), "bus": j("results-bus"), "scr": j("screen"), "desc": j("describe"),
            "bdesc": j("describe-bus"), "rev": j("review")}


def segment_table() -> pd.DataFrame:
    """Per tram segment (stop before → stop): transitions, large headway steps, sudden closings, bunched share."""
    allp = be.load("tram")
    ps = allp[allp["H0"] >= be.H_MIN].reset_index(drop=True)
    ev = be.events(ps)
    ev["step"] = (ev["v"] - ev["v1"]).abs() > 0.25
    ev["bunched"] = (ev["v"] >= 0) & (ev["v"] < be.BUNCH)
    g = ev.groupby(["prev_name", "stop_name"], observed=True).agg(
        transitions=("step", "size"), steps=("step", "sum"), births=("birth", "sum"), bunched=("bunched", "sum"))
    g = g[g["transitions"] >= 500].reset_index()
    g["steps_per_1000"] = 1000 * g["steps"] / g["transitions"]
    g["bunched_per_1000"] = 1000 * g["bunched"] / g["transitions"]
    return g


def map_spec(t: pd.DataFrame, xy: dict, top: str) -> tuple[dict, int]:
    feats = []
    for r in t.sort_values("steps_per_1000").itertuples():
        a, b = str(r.prev_name), str(r.stop_name)
        if a in xy and b in xy and a != b:
            feats.append({"id": f"{a} → {b}", "name": f"{a} → {b}", "sub": f"{n(r.transitions)} pair passes",
                          "l": [la.offset_line(xy[a], xy[b])],
                          "v": {"steps": round(float(r.steps_per_1000), 2), "bunched": round(float(r.bunched_per_1000), 2),
                                "births": int(r.births)}})
    per = {"dp": 1, "unit": " ‰"}
    spec = {"held": HELD, "base": "../assets/praha-base.json", "fit": "features", "features": feats,
            "views": [{"key": "steps", "label": "sudden headway changes", "fmt": per, "scale": "seq",
                       "domain": [0, 5], "note": "pairs whose spacing changed by over a quarter of the planned gap, per 1 000",
                       "mark": {"id": top, "label": "most sudden closings"}},
                      {"key": "bunched", "label": "bunched pairs", "fmt": per, "scale": "seq", "domain": [0, 20],
                       "note": "pairs arriving under a quarter of the planned gap apart, per 1 000"},
                      {"key": "births", "label": "sudden closings", "fmt": {"dp": 0}, "scale": "seq", "domain": [0, 10],
                       "note": "count over the season"}],
            "hint": "hover, tap or use the arrow keys for a segment; each direction is drawn on its right",
            "data": ["segments.json", "results.json"]}
    return spec, len(feats)


def static_map(spec: dict, path: Path) -> None:
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    k = np.cos(np.radians(50.08))
    cmap = LinearSegmentedColormap.from_list("bunch", ["#e2e2de", HELD])
    norm = Normalize(0, 5)
    f, ax = plt.subplots(figsize=(7.2, 5.6))
    feats = spec["features"]
    ax.add_collection(LineCollection([[(x * k, y) for x, y in ft["l"][0]] for ft in feats],
                                     colors=[cmap(norm(ft["v"]["steps"])) for ft in feats], linewidths=1.8,
                                     capstyle="round", rasterized=True))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    cb = f.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("sudden headway changes per 1 000 pair passes", color=GREY)
    f.tight_layout()
    f.savefig(path, dpi=220)
    plt.close(f)


def line_chart(series: list[dict], alt: str, xlab: str, ylab: str, xdom: list, ydom: list, table: dict,
               data: list, yfmt: dict) -> dict:
    return {"alt": alt, "panels": [{"h": 240, "x": {"kind": "linear", "domain": xdom, "fmt": {"dp": 0}, "label": xlab},
                                    "y": {"kind": "linear", "domain": ydom, "fmt": yfmt, "label": ylab},
                                    "marks": [{"type": "line", "dots": True, **s} for s in series]}],
            "legend": [{"label": s["name"], "c": s["c"]} for s in series], "table": table, "data": data}


def static_lines(series: list[dict], path: Path, xlab: str, ylab: str) -> None:
    f, ax = plt.subplots(figsize=(7.2, 2.8))
    for s in series:
        ax.plot([p[0] for p in s["pts"]], [p[1] for p in s["pts"]], color=s["c"], lw=1.6, marker="o", ms=3,
                ls="--" if s.get("dash") else "-")
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def range_rows(rows: list[tuple]) -> list[dict]:
    out = []
    for lab, est, ci, col in rows:
        lo, hi = (ci if ci else (est, est))
        tip = f"{lab}: {est:+.4f}" + (f" ({lo:+.4f} to {hi:+.4f})" if ci else "")
        out.append({"y": lab, "lo": lo, "hi": hi, "mid": est, "c": col, "tip": tip})
    return out


def range_chart(rows: list[dict], alt: str, label: str, domain: list, band: float | None, line: float,
                fmt: dict, data: list) -> dict:
    marks = []
    if band:
        marks.append({"type": "span", "v0": -band, "v1": band, "c": "grey", "o": 0.08, "label": "the registered ±0.01"})
    marks += [{"type": "rule", "axis": "x", "v": line, "c": "grey"}, {"type": "range", "rows": rows}]
    return {"alt": alt, "panels": [{"h": 26 * len(rows) + 40, "x": {"kind": "linear", "domain": domain, "fmt": fmt,
                                                                   "label": label},
                                    "y": {"kind": "cat", "domain": [r["y"] for r in rows]}, "marks": marks}],
            "table": {"cols": ["version", "estimate", "95 % interval"],
                      "rows": [[r["y"], r["mid"], "" if r["lo"] == r["hi"] else f"{r['lo']} to {r['hi']}"] for r in rows]},
            "data": data}


def static_range(rows: list[dict], path: Path, label: str, xlim: tuple, line: float) -> None:
    f, ax = plt.subplots(figsize=(7.2, 0.3 * len(rows) + 0.9))
    for i, r in enumerate(reversed(rows)):
        ax.plot([r["lo"], r["hi"]], [i, i], color=INK, lw=1.2)
        ax.plot(r["mid"], i, "o", color=HELD if r["c"] == "held" else INK, ms=4)
    ax.axvline(line, color=GREY, lw=0.8)
    ax.set_yticks(range(len(rows)), [r["y"] for r in reversed(rows)], fontsize=7)
    ax.set_xlim(*xlim)
    ax.set_xlabel(label)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def figures(x: dict, t: pd.DataFrame, xy: dict) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "bunching-results.json", A / "results.json")
    shutil.copy(R / "bunching-describe.json", A / "describe.json")
    shutil.copy(R / "bunching-describe-bus.json", A / "describe-bus.json")
    shutil.copy(R / "bunching-results-bus.json", A / "results-bus.json")
    shutil.copy(R / "bunching-review.json", A / "review.json")
    (A / "segments.json").write_text(json.dumps(
        [{"from": str(r.prev_name), "to": str(r.stop_name), "pair_passes": int(r.transitions),
          "sudden_changes_per_1000": round(float(r.steps_per_1000), 2), "bunched_per_1000": round(float(r.bunched_per_1000), 2),
          "sudden_closings": int(r.births)} for r in t.itertuples()], ensure_ascii=False))
    top = x["desc"]["segments_most_births"][0]["segment"]
    spec, drawn = map_spec(t, xy, top)
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    static_map(spec, A / "01-map.svg")
    res, d = x["res"], x["desc"]
    charts = {}

    obs = d["bunched_or_swapped_by_decile"]["observed"]
    sh = d["bunched_or_swapped_by_decile"]["shuffled"]
    var = {k: v["var_r"] for k, v in res["Q4"]["by_decile"].items()}
    var_s = {k: v["var_r"] for k, v in res["Q4"]["by_decile_shuffled"].items()}
    ser = [{"name": "observed", "c": HELD, "pts": [[int(k), round(100 * v, 2)] for k, v in obs.items()]},
           {"name": "shuffled benchmark (lets trams swap)", "c": GREY, "dash": "dash",
            "pts": [[int(k), round(100 * v, 2)] for k, v in sh.items()]}]
    charts["curve"] = line_chart(
        ser, "Share of pairs arriving bunched or swapped, by tenth of the way along the line: it rises from about 0.1 % "
             "near the start to about 1 % near the end; the shuffled benchmark, which lets trams swap order as they "
             "cannot on rails, gives a similar curve.", "tenth of the way along the line", "bunched or swapped, % of pair passes", [1, 10],
        [0, 1.2], {"cols": ["tenth", "observed %", "shuffled %", "variance of spacing", "variance, shuffled"],
                   "rows": [[int(k), round(100 * obs[k], 2), round(100 * sh[k], 2), var[k], var_s[k]] for k in obs]},
        ["describe.json", "results.json"], {"dp": 1})
    static_lines(ser, A / "02-curve.svg", "tenth of the way along the line", "bunched or swapped, %")

    q1, v = res["Q1"], d
    rows = range_rows([
        ("registered: IV, two stops back", q1["gamma_iv"], q1["ci95"], "held"),
        ("by ISO week", q1["gamma_iv"], q1["week_clustered_ci95"], "ink"),
        ("IV, three stops back", v["gamma_iv_instrument_3_stops_back"], None, "ink"),
        ("IV, four stops back", v["gamma_iv_instrument_4_stops_back"], None, "ink"),
        ("between timing points", v["gamma_iv_without_timing_points"]["est"],
         v["gamma_iv_without_timing_points"]["ci95"], "ink"),
        ("departures instead of arrivals", v["gamma_iv_departures"]["est"], v["gamma_iv_departures"]["ci95"], "ink"),
        ("plain OLS (pulled down by noise)", q1["gamma_ols"], None, "grey"),
        ("registered shuffle, γ − γ₀", q1["gamma_minus_gamma0_registered"], None, "grey")])
    charts["gamma"] = range_chart(rows, "Amplification per stop with 95 % intervals: every estimate lies within a "
                                        "few thousandths of zero, far inside the registered ±0.01; over all stops it "
                                        "is slightly negative, without the timing points and on departures slightly "
                                        "positive.",
                                  "change in spacing per stop, per unit of spacing off schedule", [-0.012, 0.012],
                                  0.01, 0.0, {"dp": 3}, ["results.json", "describe.json"])
    static_range(rows, A / "03-gamma.svg", "amplification per stop (γ)", (-0.012, 0.012), 0.0)

    hw, he = res["Q4"]["by_hour_weekday"], res["Q4"]["by_hour_weekend"]
    hours = list(range(5, 24))
    ser = [{"name": "weekdays", "c": HELD, "pts": [[h, round(100 * hw[str(h)]["bunched"], 2)] for h in hours if str(h) in hw]},
           {"name": "weekends", "c": GREY, "pts": [[h, round(100 * he[str(h)]["bunched"], 2)] for h in hours if str(h) in he]}]
    charts["hours"] = line_chart(ser, "Share of pairs arriving bunched by the hour the pair set out: highest in the "
                                      "weekday afternoon peak, lowest late at night.",
                                 "hour the pair set out", "bunched, % of pair passes", [5, 23], [0, 1.2],
                                 {"cols": ["hour", "weekdays %", "weekends %"],
                                  "rows": [[h, round(100 * hw.get(str(h), {}).get("bunched", float("nan")), 2),
                                            round(100 * he.get(str(h), {}).get("bunched", float("nan")), 2)] for h in hours]},
                                 ["results.json"], {"dp": 1})
    static_lines(ser, A / "04-hours.svg", "hour the pair set out", "bunched, %")

    q2, c = res["Q2"], res["checks"]
    qp = x["rev"]["q2_null_within_pattern"]
    rows = range_rows([
        ("registered: fall to under 0.25 from 0.5", q2["ratio"], q2["ratio_ci95"], "held"),
        ("from 0.75 (registered check)", c["alternative_birth_rule_prev_0.75"]["ratio"],
         c["alternative_birth_rule_prev_0.75"]["ratio_ci95"], "ink"),
        ("under 0.20", c["bunched_below_0.20"]["ratio"], c["bunched_below_0.20"]["ratio_ci95"], "ink"),
        ("under 0.33", c["bunched_below_0.33"]["ratio"], c["bunched_below_0.33"]["ratio_ci95"], "ink"),
        ("without timing points", c["without_timing_points"]["ratio"], c["without_timing_points"]["ratio_ci95"], "ink"),
        ("without the busiest 1 % of days", c["without_top_1pct_dates"]["ratio"],
         c["without_top_1pct_dates"]["ratio_ci95"], "ink"),
        ("null within route variant (post hoc)", qp["ratio"], qp["ratio_ci95"], "ink"),
        ("sudden re-openings (deaths)", c["deaths"]["ratio"], c["deaths"]["ratio_ci95"], "grey"),
        ("reversed order (registered placebo)", c["reversed_order"]["ratio"], c["reversed_order"]["ratio_ci95"], "grey")])
    charts["places"] = range_chart(rows, "How much more the hottest tenth of platforms holds than exposure alone "
                                         "would give, with 95 % intervals: above 1 in every version, lower when "
                                         "closings are reassigned only within their route variant (post hoc), and "
                                         "higher for sudden re-openings and for the closings counted backwards.",
                                   "concentration against exposure alone (ratio)", [0, 6], None, 1.25, {"dp": 2},
                                   ["results.json", "review.json"])
    static_range(rows, A / "05-places.svg", "concentration against exposure alone", (0, 6), 1.25)
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    return {"drawn": drawn}


def values(x: dict, t: pd.DataFrame, fig: dict) -> dict:
    res, bus, scr, d = x["res"], x["bus"], x["scr"], x["desc"]
    q1, q2, q3, c = res["Q1"], res["Q2"], res["Q3"], res["checks"]
    months = scr["months"].values()
    pct = lambda v, dp=1: n(100 * v, dp)  # noqa: E731
    g4 = lambda v: f"{v:+.4f}".replace("-", "−")  # noqa: E731
    obs, sh = d["bunched_or_swapped_by_decile"]["observed"], d["bunched_or_swapped_by_decile"]["shuffled"]
    v = {"pairs": n(res["pairs"]), "pair_stops_m": n(res["pair_stops_observed"] / 1e6, 1),
         "patterns": n(scr["patterns_kept"]), "thin": n(len(scr["patterns_thin_removed"])),
         "g": g4(q1["gamma_iv"]), "g_lo": g4(q1["ci95"][0]), "g_hi": g4(q1["ci95"][1]), "g_label": q1["label"],
         "g90_lo": g4(q1["ci90"][0]), "g90_hi": g4(q1["ci90"][1]),
         "gw_lo": g4(q1["week_clustered_ci95"][0]), "gw_hi": g4(q1["week_clustered_ci95"][1]),
         "g_ols": g4(q1["gamma_ols"]), "g_reg": g4(q1["gamma_minus_gamma0_registered"]),
         "g3": g4(d["gamma_iv_instrument_3_stops_back"]), "g4": g4(d["gamma_iv_instrument_4_stops_back"]),
         "g_tp": g4(d["gamma_iv_without_timing_points"]["est"]),
         "g_tp_lo": g4(d["gamma_iv_without_timing_points"]["ci95"][0]),
         "g_tp_hi": g4(d["gamma_iv_without_timing_points"]["ci95"][1]),
         "g_dep": g4(d["gamma_iv_departures"]["est"]), "fs": f"{d['iv_first_stage']['coef']:.3f}",
         "transitions_m": n(q1["transitions"] / 1e6, 1),
         "bunched": pct(res["Q4"]["overall"]["bunched"], 2), "gap": pct(res["Q4"]["overall"]["gap"], 2),
         "b05": pct(c["bunched_below_0.5_gap_above_1.5_shares"]["bunched"], 1),
         "g15": pct(c["bunched_below_0.5_gap_above_1.5_shares"]["gap"], 1),
         "d1": pct(obs["1"], 1), "d10": pct(obs["10"], 1), "s10": pct(sh["10"], 1),
         "var1": f"{res['Q4']['by_decile']['1']['var_r']:.3f}", "var10": f"{res['Q4']['by_decile']['10']['var_r']:.3f}",
         "ever": n(d["pairs_ever_bunched"]), "ever_pct": pct(d["share_pairs_ever_bunched"], 1),
         "gradual": n(d["first_bunched_from_0.25_to_0.5"]), "sudden": n(d["first_bunched_from_r_ge_0.5"]),
         "gradual_pct": n(100 * d["first_bunched_from_0.25_to_0.5"] / d["pairs_ever_bunched"]),
         "sudden_pct": n(100 * d["first_bunched_from_r_ge_0.5"] / d["pairs_ever_bunched"]),
         "stay": pct(d["bunched_still_bunched_next_stop"], 0),
         "births": n(res["transitions"]["births"]), "deaths": n(res["transitions"]["deaths"]),
         "eligible_m": n(res["transitions"]["eligible"] / 1e6, 1),
         "ratio": f"{q2['ratio']:.2f}", "r_lo": f"{q2['ratio_ci95'][0]:.2f}", "r_hi": f"{q2['ratio_ci95'][1]:.2f}",
         "r_label": q2["ratio_label"], "platforms": n(q2["platforms"]), "Sb": pct(q2["S_b"]), "Sb0": pct(q2["S_b0"]),
         "rho": f"{q2['rho_split_half']:.2f}", "rho_lo": f"{q2['rho_ci95'][0]:.2f}", "rho_hi": f"{q2['rho_ci95'][1]:.2f}",
         "rho_label": q2["rho_label"], "zero_pct": pct(d["platforms_with_zero_births_share"], 0),
         "r075": f"{c['alternative_birth_rule_prev_0.75']['ratio']:.2f}",
         "r075_lo": f"{c['alternative_birth_rule_prev_0.75']['ratio_ci95'][0]:.2f}",
         "r075_label": c["alternative_birth_rule_prev_0.75"]["ratio_label"],
         "r020": f"{c['bunched_below_0.20']['ratio']:.2f}", "r033": f"{c['bunched_below_0.33']['ratio']:.2f}",
         "rho033": f"{c['bunched_below_0.33']['rho_split_half']:.2f}", "b033": n(c["bunched_below_0.33"]["births"]),
         "r_deaths": f"{c['deaths']['ratio']:.2f}", "fwd_bwd": f"{c['reversed_vs_forward_rank_correlation']:.2f}",
         "vol": f"{d['platforms_rank_corr_birth_rate_vs_large_steps']:.2f}",
         "dr": f"{d['platforms_rank_corr_drops_vs_rises']:.2f}",
         "q3": f"{q3['rho_b']:.2f}", "q3_lo": f"{q3['ci95'][0]:.2f}", "q3_hi": f"{q3['ci95'][1]:.2f}",
         "q3_label": q3["label"], "q3_mean": f"{q3['rho_with_mean_gain']:.2f}", "q3_seg": n(q3["segments"]),
         "tp": n(d["timing_points"]["stops"]),
         "dep_share": pct(np.mean([m["pair_stops_with_departures_share"] for m in months]), 0),
         "modal_lo": pct(min(m["patterns"]["on_modal_pattern"] / m["patterns"]["trips"] for m in months), 0),
         "modal_hi": pct(max(m["patterns"]["on_modal_pattern"] / m["patterns"]["trips"] for m in months), 0),
         "drawn": n(fig["drawn"]), "segs": n(len(t)),
         "low_pairs": n(c["H_3_4min_stratum"]["pairs"]),
         "tt_b": pct(c["timetable_order_pairs"]["bunched_incl_swaps"], 2)}
    top = d["platforms_most_births"]
    v.update({"nd_b": n(top[0]["births"]), "nd_e": n(top[0]["expected"], 1), "seg1": d["segments_most_births"][0]["segment"],
              "seg1_b": n(d["segments_most_births"][0]["births"]), "seg2": d["segments_most_births"][1]["segment"],
              "seg2_b": n(d["segments_most_births"][1]["births"])})
    bq1, bq2 = bus["Q1"], bus["Q2"]
    v.update({"bg": g4(bq1["gamma_iv"]), "bg_lo": g4(bq1["ci95"][0]), "bg_hi": g4(bq1["ci95"][1]),
              "bg_label": bq1["label"], "bpairs": n(bus["pairs"]), "bratio": f"{bq2['ratio']:.2f}",
              "br_lo": f"{bq2['ratio_ci95'][0]:.2f}", "br_hi": f"{bq2['ratio_ci95'][1]:.2f}", "br_label": bq2["ratio_label"],
              "brho": f"{bq2['rho_split_half']:.2f}", "brho_label": bq2["rho_label"],
              "bbunched": pct(bus["Q4"]["overall"]["bunched"], 2), "bbirths": n(bus["transitions"]["births"])})
    tpi = d["timing_points"]
    l9, no9, sim, ac = d["line_9"], d["q2_without_line_9"], d["q2b_power_simulation"]["by_multiplier"], \
        d["autocorrelation_of_spacing_changes"]
    q4 = res["Q4"]
    v.update({"rbirths": n(q2["births"]), "l9_births": n(100 * l9["share_of_births"]),
              "l9_exp": n(100 * l9["share_of_eligible"], 1), "no9": f"{no9['ratio']:.2f}",
              "no9_lo": f"{no9['ratio_ci95'][0]:.2f}", "no9_hi": f"{no9['ratio_ci95'][1]:.2f}",
              "sim1": f"{sim['1']['split_half_rho']:.2f}", "sim5": f"{sim['5']['split_half_rho']:.2f}",
              "rho_no9": f"{no9['rho_split_half']:.2f}", "b_no9": n(no9["births"]),
              "no9_label": "inconclusive" if no9["ratio_ci95"][0] <= 1.25 else "supported", "sim10": f"{sim['10']['split_half_rho']:.2f}",
              "ac2": f"{ac['2']:.3f}".replace("-0.000", "0.000").replace("-", "−"),
              "ac3": f"{ac['3']:.3f}".replace("-0.000", "0.000").replace("-", "−"),
              "s10u": pct(q4["by_decile_shuffled"]["10"]["bunched"], 2),
              "s10swap": pct(q4["by_decile_shuffled"]["10"]["swap"], 2),
              "r_deaths_lo": f"{c['deaths']['ratio_ci95'][0]:.2f}", "r_deaths_hi": f"{c['deaths']['ratio_ci95'][1]:.2f}",
              "tp_top": n(tpi["top8_platforms_among_them"]),
              "bg2": g4(x["bdesc"]["gamma_iv_by_instrument_lag"]["2"]), "bg3": g4(x["bdesc"]["gamma_iv_by_instrument_lag"]["3"]),
              "bg4": g4(x["bdesc"]["gamma_iv_by_instrument_lag"]["4"]),
              "bac": f"{x['bdesc']['autocorrelation_lag_1']:+.3f}".replace("-", "−"),
              "bswap": pct(bus["Q4"]["overall"]["swap"], 2),
              "btp": n(x["bdesc"]["timing_point_stops"])})
    # version 2 (correction after publication, 8 October 2026): values for the corrected readings
    rv, qv = x["rev"], res["Q1_variants"]
    iv_points = [q1["gamma_iv"], d["gamma_iv_instrument_3_stops_back"], d["gamma_iv_instrument_4_stops_back"],
                 d["gamma_iv_without_timing_points"]["est"], d["gamma_iv_departures"]["est"],
                 qv["cut_at_first_swap"], qv["balanced_80pct"], qv["weighted_by_H"]]
    iv_ends = iv_points + q1["ci95"] + q1["week_clustered_ci95"] + d["gamma_iv_without_timing_points"]["ci95"] + \
        d["gamma_iv_departures"]["ci95"]
    near1 = lambda z: f"{z:.4f}" if f"{z:.2f}" == "1.00" and z != 1 else f"{z:.2f}"  # noqa: E731
    qp, ql, gl = rv["q2_null_within_pattern"], rv["q2_null_within_line"], rv["gamma_iv_by_line"]
    big = gl["at_least_50000_transitions"]
    shares = [m["patterns"]["on_modal_pattern"] / m["patterns"]["trips"] for m in months]
    v.update({"g_max": f"{max(abs(z) for z in iv_ends):.3f}",
              "t_min": g4(min(iv_points)), "t_max": g4(max(iv_points)), "t_spread": f"{max(iv_points) - min(iv_points):.4f}",
              "fs_t": n(d["iv_first_stage"]["t"]), "no9_lo": near1(no9["ratio_ci95"][0]),
              "drop_lo": n(100 * (1 - max(shares))), "drop_hi": n(100 * (1 - min(shares))),
              "first_pct": n(100 * d["first_bunched_at_first_observed_stop"] / d["pairs_ever_bunched"]),
              "d10u": pct(q4["by_decile"]["10"]["bunched"], 2), "o10swap": pct(q4["by_decile"]["10"]["swap"], 2),
              "var10s": f"{q4['by_decile_shuffled']['10']['var_r']:.3f}",
              "rp": f"{qp['ratio']:.2f}", "rp_lo": f"{qp['ratio_ci95'][0]:.2f}", "rp_hi": f"{qp['ratio_ci95'][1]:.2f}",
              "Sb0p": pct(qp["S_b0_stratified"]), "rp_strata": n(qp["strata"]),
              "boot": n(qp["bootstrap_draws"]), "nulls": n(qp["null_draws_per_bootstrap_draw"]),
              "rl": f"{ql['ratio']:.2f}", "rl_lo": f"{ql['ratio_ci95'][0]:.2f}", "rl_hi": f"{ql['ratio_ci95'][1]:.2f}",
              "r_rev": f"{c['reversed_order']['ratio']:.2f}", "r_rev_lo": f"{c['reversed_order']['ratio_ci95'][0]:.2f}",
              "r_rev_hi": f"{c['reversed_order']['ratio_ci95'][1]:.2f}",
              "r033_lo": f"{c['bunched_below_0.33']['ratio_ci95'][0]:.2f}",
              "r033_hi": f"{c['bunched_below_0.33']['ratio_ci95'][1]:.2f}",
              "gl_min": g4(big["min"]["gamma_iv"]), "gl_min_line": big["min"]["line"],
              "gl_max": g4(big["max"]["gamma_iv"]), "gl_max_line": big["max"]["line"], "gl_n": n(big["lines"]),
              "gla_min": g4(gl["min"]["gamma_iv"]), "gla_min_line": gl["min"]["line"],
              "gla_max": g4(gl["max"]["gamma_iv"]), "gla_max_line": gl["max"]["line"],
              "g_label_v1": rv["q1_label"]["published"]})
    photo = next(q for q in json.loads((ROOT / "assets/photo/sources.json").read_text()) if q["slug"] == "bunching")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-bunching;'
                  '--bg:url(../assets/photo/bunching.jpg);--bg-s:url(../assets/photo/bunching-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · '
                  f'{photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    x = load()
    t = segment_table()
    xy = {r.name: (r.lon, r.lat) for r in la.tram_stops().itertuples()}
    fig = figures(x, t, xy)
    v = values(x, t, fig)
    tpl = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), tpl)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "bunching.html").write_text(out, encoding="utf-8")
    print(json.dumps({k: v[k] for k in v if k != "photo"}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
