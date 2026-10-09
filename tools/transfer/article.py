"""Will you make your connection: the roulette, figures, map and the article, every number from the result files.

Reads docs/research/transfers-{design,screen,results,describe}.json and the roulette cells in assets/transfers/;
writes assets/transfers/ (charts.json, map.json, results.json, describe.json, static SVGs) and texts/transfers.html
from tools/transfer/template.html. Chart helpers are part 2's.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with scipy --with numpy python tools/transfer/article.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import photo_section, render  # noqa: E402


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ba = load_module("bunch_article", "tools/bunch/article.py")
plt, n = ba.plt, ba.n
R, A = ROOT / "docs" / "research", ROOT / "assets" / "transfers"
HELD, INK, GREY = ba.HELD, ba.INK, ba.GREY
HUB_HALF_M = 120  # half the side of the square drawn for a hub on the map


def load() -> dict:
    j = lambda name: json.loads((R / f"transfers-{name}.json").read_text())  # noqa: E731
    return {"res": j("results"), "scr": j("screen"), "desc": j("describe"), "ph": j("posthoc"),
            "cells": json.loads((A / "roulette.json").read_text())}


def pooled_curve(cells: dict) -> list[tuple[int, float]]:
    """Share made by planned slack across all shown roulette cells, weighted by their connections."""
    rows = cells["rows"]
    w = np.array([r[6] for r in rows], dtype=float)
    out = []
    for s in range(1, 11):
        p = np.array([next(k[1] for k in r[13] if k[0] == s) for r in rows])
        out.append((s, float(np.sum(w * p) / w.sum())))
    return out


def hub_squares() -> dict[str, list]:
    stops = pd.read_csv(ROOT / "tools/data/praha2/gtfs/stops.txt", dtype=str)
    stops = stops[stops["location_type"].fillna("0") == "0"].astype({"stop_lat": float, "stop_lon": float})
    c = stops.groupby("stop_name")[["stop_lat", "stop_lon"]].mean()
    dy = HUB_HALF_M / 111_320
    out = {}
    for name, r in c.iterrows():
        dx = HUB_HALF_M / (111_320 * np.cos(np.radians(r.stop_lat)))
        x, y = r.stop_lon, r.stop_lat
        out[name] = [[[round(x - dx, 5), round(y - dy, 5)], [round(x + dx, 5), round(y - dy, 5)],
                      [round(x + dx, 5), round(y + dy, 5)], [round(x - dx, 5), round(y + dy, 5)],
                      [round(x - dx, 5), round(y - dy, 5)]]]
    return out


def map_spec(x: dict) -> tuple[dict, int]:
    res = x["res"]
    by_hub = res["checks"]["by_hub"]
    made3 = res["q2_cost"]["3"]["by_hub"]
    sq = hub_squares()
    feats = []
    for hub in sorted(set(made3) | set(by_hub)):
        if hub not in sq:
            continue
        v = {}
        if hub in made3 and made3[hub]["connections"] >= 500:
            v["made3"] = round(100 * made3[hub]["made"], 1)
        if hub in by_hub and by_hub[hub].get("est") is not None:
            v["dp"] = round(100 * by_hub[hub]["est"], 2)
        if v:
            feats.append({"id": hub, "name": hub, "sub": f"{n(made3.get(hub, {}).get('connections', 0))} connections "
                                                         "planned 3 min apart", "r": sq[hub], "v": v})
    worst = min((f for f in feats if "made3" in f["v"]), key=lambda f: f["v"]["made3"])["id"]
    spec = {"held": HELD, "base": "../assets/praha-base.json", "fit": "features", "features": feats,
            "views": [{"key": "made3", "label": "made with 3 min planned", "fmt": {"dp": 0, "unit": " %"},
                       "scale": "seq", "domain": [60, 95], "note": "share of connections planned 3 min apart that were made",
                       "mark": {"id": worst, "label": "lowest share made"}},
                      {"key": "dp", "label": "lines late together", "fmt": {"dp": 1, "unit": " pp"}, "scale": "div",
                       "domain": [-2, 2], "note": "Δp within the day at slack 2–4 min, percentage points"}],
            "hint": "hover, tap or use the arrow keys for a hub",
            "data": ["results.json"]}
    return spec, len(feats)


def static_map(spec: dict, path: Path) -> None:
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.patches import Polygon
    k = np.cos(np.radians(50.08))
    cmap = LinearSegmentedColormap.from_list("t", [HELD, "#e2e2de"])
    norm = Normalize(60, 95)
    f, ax = plt.subplots(figsize=(7.2, 5.6))
    for ft in spec["features"]:
        if "made3" not in ft["v"]:
            continue
        ax.add_patch(Polygon([(x * k, y) for x, y in ft["r"][0]], color=cmap(norm(ft["v"]["made3"]))))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    cb = f.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("% made with 3 min planned", color=GREY)
    f.tight_layout()
    f.savefig(path, dpi=220)
    plt.close(f)


def figures(x: dict) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    for k in ("results", "describe", "posthoc"):
        shutil.copy(R / f"transfers-{k}.json", A / f"{k}.json")
    res = x["res"]
    charts = {}
    curve = pooled_curve(x["cells"])
    cost = res["q2_cost"]
    ser = [{"name": "made, all shown cells", "c": HELD, "pts": [[s, round(100 * p, 1)] for s, p in curve]},
           {"name": "made, connections as planned", "c": INK,
            "pts": [[int(s), round(100 * cost[s]["made"], 1)] for s in ("2", "3", "4")]},
           {"name": "cost over 5 min extra wait", "c": GREY, "dash": "dash",
            "pts": [[int(s), round(100 * cost[s]["costly_miss"], 1)] for s in ("2", "3", "4")]}]
    first95 = next(s for s, p in curve if p >= 0.95)
    cm = dict(curve)
    charts["slack"] = ba.line_chart(
        ser, "Share of tram-to-tram connections made by the minutes planned between them, Prague 2025. Among "
             f"connections planned that way: {100 * cost['2']['made']:.0f} % at 2 minutes, "
             f"{100 * cost['3']['made']:.0f} % at 3 and {100 * cost['4']['made']:.0f} % at 4. Read off the pooled "
             f"model over all shown cells: {100 * cm[2]:.1f} % at 2, {100 * cm[3]:.1f} % at 3 and over 95 % from "
             f"{first95} minutes. {100 * cost['3']['costly_miss']:.0f} % of connections planned 3 minutes apart cost "
             "more than 5 minutes of extra wait.",
        "minutes planned between arrival and departure", "% of connections", [1, 10], [0, 100],
        {"cols": ["minutes planned", "made, all cells %", "made, as planned %", "cost over 5 min %"],
         "rows": [[s, round(100 * p, 1), round(100 * cost[str(s)]["made"], 1) if str(s) in cost else "",
                   round(100 * cost[str(s)]["costly_miss"], 1) if str(s) in cost else ""] for s, p in curve]},
        ["results.json", "roulette.json"], {"dp": 0})
    charts["slack"]["panels"][0]["marks"][0]["name"] = "made, pooled model over all shown cells"
    charts["slack"]["legend"][0]["label"] = "made, pooled model over all shown cells"
    ba.static_lines(ser, A / "02-slack.svg", "minutes planned", "% of connections")

    q1, q1b, c = res["q1_within"], res["q1b_day"], res["checks"]
    pb = x["ph"]["q1_bounds"]
    rows = ba.range_rows([
        ("registered: same day, slack 2–4", q1["est"], q1["ci95"], "held"),
        ("post-hoc bound: unobserved B all made", pb["unobserved_all_made"]["est"], pb["unobserved_all_made"]["ci95"],
         "grey"),
        ("post-hoc bound: unobserved B all missed", pb["unobserved_all_missed"]["est"],
         pb["unobserved_all_missed"]["ci95"], "grey"),
        ("other days (Q1b)", q1b["est"], q1b["ci95"], "ink"),
        ("hubs and weeks resampled", c["hub_and_week_resampling"]["est"], c["hub_and_week_resampling"]["ci95"], "ink"),
        ("observed departures", c["observed_departures"]["est"], c["observed_departures"]["ci95"], "ink"),
        ("walk margin −30 s", c["margin_m_minus_30s"]["est"], c["margin_m_minus_30s"]["ci95"], "ink"),
        ("walk margin +30 s", c["margin_m_plus_30s"]["est"], c["margin_m_plus_30s"]["ci95"], "ink"),
        ("walk margin fixed 2 min", c["margin_m_fixed_2min"]["est"], c["margin_m_fixed_2min"]["ci95"], "ink"),
        ("A arrival +30 s", c["timing_a_plus_30s"]["est"], c["timing_a_plus_30s"]["ci95"], "ink"),
        ("A arrival −30 s", c["timing_a_minus_30s"]["est"], c["timing_a_minus_30s"]["ci95"], "ink"),
        ("returns and same trunk kept", c["without_exclusions"]["est"], c["without_exclusions"]["ci95"], "ink"),
        ("weekday peaks only", c["peaks_only"]["est"], c["peaks_only"]["ci95"], "ink"),
        ("school holidays", c["school_holidays"]["est"], c["school_holidays"]["ci95"], "ink"),
        ("term time", c["term_time"]["est"], c["term_time"]["ci95"], "ink")])
    for r in rows:  # percentage points on the page
        r["lo"], r["hi"], r["mid"] = round(100 * r["lo"], 2), round(100 * r["hi"], 2), round(100 * r["mid"], 2)
        r["tip"] = f"{r['y']}: {r['mid']:+.2f} pp ({r['lo']:+.2f} to {r['hi']:+.2f})"
    specs = [r for r in rows[3:] if not r["y"].startswith("other days") and not r["y"].startswith("hubs")]
    chart = ba.range_chart(rows, "How much more often connections were made than with the two lines' delays set "
                                 "against other trips of the same day, in percentage points with 95 % intervals: "
                                 f"the registered estimate is {q1['est'] * 100:+.2f}; the checks run from "
                                 f"{min(r['mid'] for r in specs):+.2f} to {max(r['mid'] for r in specs):+.2f}; the "
                                 "post-hoc bounds for connections whose planned tram was not observed run from "
                                 f"{100 * pb['unobserved_all_missed']['est']:+.2f} to "
                                 f"{100 * pb['unobserved_all_made']['est']:+.2f}.",
                           "percentage points", [-1.2, 1.6], 1.0, 0.0, {"dp": 1}, ["results.json", "posthoc.json"])
    chart["panels"][0]["marks"][0]["label"] = "the registered ±1 point"
    charts["checks"] = chart
    ba.static_range(rows, A / "03-checks.svg", "percentage points", (-1.2, 1.6), 0.0)

    spec, drawn = map_spec(x)
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    static_map(spec, A / "04-map.svg")
    roul = A / "01-roulette.svg"
    f, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.plot([s for s, _ in curve], [100 * p for _, p in curve], color=HELD, marker="o", ms=3)
    ax.set_xlabel("minutes planned")
    ax.set_ylabel("% made, pooled model")
    f.tight_layout()
    f.savefig(roul)
    plt.close(f)
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    return {"drawn": drawn, "curve": dict(curve)}


def values(x: dict, fig: dict) -> dict:
    res, scr, d = x["res"], x["scr"], x["desc"]
    pp = lambda v, dp=1: f"{100 * v:+.{dp}f}".replace("-", "−")  # noqa: E731
    pct = lambda v, dp=0: n(100 * v, dp)  # noqa: E731
    q1, q1b, bd, c, cost = res["q1_within"], res["q1b_day"], res["bounds"], res["checks"], res["q2_cost"]
    ub = d["post_hoc_uncertain_breakdown"]
    q4 = d["q4"]
    curve = fig["curve"]
    first95 = next(s for s in range(1, 11) if curve[s] >= 0.95)
    v = {"q1": pp(q1["est"], 2), "q1_lo": pp(q1["ci95"][0], 2), "q1_hi": pp(q1["ci95"][1], 2),
         "q1_90lo": pp(q1["ci90"][0], 2), "q1_90hi": pp(q1["ci90"][1], 2), "q1_label": q1["label"],
         "q1b": pp(q1b["est"], 2), "q1b_lo": pp(q1b["ci95"][0], 2), "q1b_hi": pp(q1b["ci95"][1], 2),
         "q1b_label": q1b["label"], "q1b_n": n(res["q1b_connections_with_donors"]),
         "q1b_share": pct(res["q1b_connections_with_donors"] / res["q1_connections"], 1),
         "p_obs": pct(res["p_obs"], 1), "p_within": pct(res["p_within"], 1),
         "q1_n": n(res["q1_connections"]), "q1_n_m": n(res["q1_connections"] / 1e6, 1), "dates": n(res["q1_dates"]),
         "weeks": n(res["weeks"]), "hubs_q1": n(len(res["q1_hubs"])),
         "b_share": pct(bd["uncertain_share"], 1), "b_hi": pp(bd["all_made"]["est"]), "b_lo": pp(bd["all_missed"]["est"]),
         "ub_unobs": pct(ub["planned_b_unobserved"], 1), "ub_short": pct(ub["line_short_that_hour_only"], 1),
         "ub_made_c": pct(ub["made_certain"], 1), "ub_made_s": pct(ub["made_line_short_that_hour"], 1),
         "hubs": n(len(scr["hubs"])), "conns_m": n(scr["counts"]["connections"] / 1e6, 1),
         "conns24_m": n(scr["counts"]["connections_slack_2_4"] / 1e6, 1),
         "excl_m": n(scr["counts"]["excluded_return_or_trunk"] / 1e6, 0),
         "missing": pct(scr["missing_trip_share"], 1), "removed": ", ".join(scr["hubs_removed_early_departures"]),
         "mde": n(scr["precision"]["mde_points_80pct"], 1),
         "m2": pct(cost["2"]["made"]), "m3": pct(cost["3"]["made"]), "m4": pct(cost["4"]["made"]),
         "c2": pct(cost["2"]["costly_miss"]), "c3": pct(cost["3"]["costly_miss"]), "c4": pct(cost["4"]["costly_miss"]),
         "w3": n(cost["3"]["median_extra_wait_s"]), "w2": n(cost["2"]["median_extra_wait_s"]),
         "peak3": pct(cost["3"]["by_band"]["peak"]["made"]), "eve3": pct(cost["3"]["by_band"]["evening"]["made"]),
         "wkd3": pct(cost["3"]["by_band"]["weekend"]["made"]), "day3": pct(cost["3"]["by_band"]["daytime"]["made"]),
         "first95": n(first95), "cells": n(d["cells"]), "cells_shown": n(d["cells_shown"]),
         "costly_m": n(q4["costly_misses"] / 1e6, 1),
         "lost_last": pct(q4["origin_share"]["lost_on_last_segment"]),
         "already": pct(q4["origin_share"]["already_late"]),
         "peaks": pp(c["peaks_only"]["est"], 2), "peaks_lo": pp(c["peaks_only"]["ci95"][0], 2),
         "peaks_hi": pp(c["peaks_only"]["ci95"][1], 2),
         "od": pp(c["observed_departures"]["est"], 2), "od_lo": pp(c["observed_departures"]["ci95"][0], 2),
         "od_hi": pp(c["observed_departures"]["ci95"][1], 2),
         "hw_lo": pp(c["hub_and_week_resampling"]["ci95"][0], 2), "hw_hi": pp(c["hub_and_week_resampling"]["ci95"][1], 2),
         "mfix": pp(c["margin_m_fixed_2min"]["est"], 2), "ap30": pp(c["timing_a_plus_30s"]["est"], 2),
         "am30": pp(c["timing_a_minus_30s"]["est"], 2),
         "pairs_n": n(len(c["by_line_pair"])), "hubs_n": n(len(c["by_hub"])),
         "drawn": n(fig["drawn"])}
    lp = [x_["est"] for x_ in c["by_line_pair"].values() if x_.get("est") is not None]
    v["lp_lo"], v["lp_hi"] = pp(min(lp)), pp(max(lp))
    excl = lambda d: 100 * np.mean([x_["ci95"][0] > 0 or x_["ci95"][1] < 0 for x_ in d.values()])  # noqa: E731
    v["lp_excl"], v["hub_excl"] = n(excl(c["by_line_pair"]), 1), n(excl(c["by_hub"]), 1)
    v.update(posthoc_values(x, fig, pp, pct))
    v["photo"] = photo_section("transfers")
    return v


SPEC_KEYS = ("margin_m_fixed_2min", "margin_m_minus_30s", "margin_m_plus_30s", "timing_a_plus_30s", "timing_a_minus_30s",
             "observed_departures", "peaks_only", "without_exclusions", "school_holidays", "term_time")
ROBUST = [("registered: same day, slack 2–4 min (999 draws)", "q1_within"),
          ("stops resampled as well as weeks", "hub_and_week_resampling"),
          ("other days instead of the same day (Q1b, 999 draws)", "q1b_day"),
          ("B on its observed departure", "observed_departures"),
          ("walk margin −30 s", "margin_m_minus_30s"), ("walk margin +30 s", "margin_m_plus_30s"),
          ("walk margin fixed at 2 min", "margin_m_fixed_2min"),
          ("A's arrival +30 s (= B −30 s)", "timing_a_plus_30s"), ("A's arrival −30 s (= B +30 s)", "timing_a_minus_30s"),
          ("returns and same-street pairs kept", "without_exclusions"), ("weekday peaks only", "peaks_only"),
          ("school holidays", "school_holidays"), ("term time", "term_time")]


def posthoc_values(x: dict, fig: dict, pp, pct) -> dict:
    """Numbers of the analyses added after the results (tools/transfer/posthoc.py)."""
    res, ph, d = x["res"], x["ph"], x["desc"]
    c = res["checks"]
    qb, q1bb, q2, ex, rl = ph["q1_bounds"], ph["q1b_bounds"], ph["q2"]["3"], ph["extrapolation"]["all_months"], ph["roulette"]
    ci = lambda r: f"95 % CI {pp(r['ci95'][0], 2)} to {pp(r['ci95'][1], 2)}"  # noqa: E731
    specs = [c[k]["est"] for k in SPEC_KEYS]
    curve, first95 = fig["curve"], next(s for s in range(1, 11) if fig["curve"][s] >= 0.95)
    df = rl["default"]
    t = q2["timing"]
    v = {"q1_short": pp(res["q1_within"]["est"], 1), "spec_lo": pp(min(specs), 1), "spec_hi": pp(max(specs), 1),
         "mm30": pp(c["margin_m_minus_30s"]["est"], 2),
         "q2u3": pct(q2["unobserved_share"], 1), "q2b3_lo": pct(q2["bound_unobserved_all_missed"], 1),
         "q2b3_hi": pct(q2["bound_unobserved_all_made"], 1),
         "q2r3_lo": pct(q2["registered_uncertain_all_missed"], 1), "q2r3_hi": pct(q2["registered_uncertain_all_made"], 1),
         "q2t_lo": pct(t["a+30"]["made"], 1), "q2t_hi": pct(t["a-30"]["made"], 1),
         "q2tc_lo": pct(t["a-30"]["costly_miss"], 1), "q2tc_hi": pct(t["a+30"]["costly_miss"], 1),
         "ph_lo": pp(qb["unobserved_all_missed"]["est"], 2), "ph_hi": pp(qb["unobserved_all_made"]["est"], 2),
         "ph_lo_ci": ci(qb["unobserved_all_missed"]), "ph_hi_ci": ci(qb["unobserved_all_made"]),
         "unobs": pct(qb["unobserved_share"], 1), "bound_n": n(qb["rows_with_same_day_donors"]),
         "ub_short": pct(qb["line_short_observed_share"], 1),
         "obs_s": pp(qb["observed_line_short"]["est"], 2), "obs_ns": pp(qb["observed_line_not_short"]["est"], 2),
         "q1br_lo": pp(q1bb["registered_all_missed"]["est"], 2), "q1br_hi": pp(q1bb["registered_all_made"]["est"], 2),
         "zb_n": n(x["scr"]["early_departure_share_by_hub"]["Zborovská"]["observed_departures"]),
         "cells_all": n(rl["cells"]), "hubs_shown": n(rl["hubs_shown"]), "hubs_all": n(rl["hubs"]),
         "cov24": pct(rl["connections_share_slack_2_4"]), "tight_n": n(rl["tight_cells"]),
         "def_desc": (f"{df['hub']}, from line {df['a']} towards {df['a_to']} to line {df['b']} towards {df['b_to']}, "
                      f"where {pct(df['p3']['p'])} % were made at 3 minutes (rough 95 % interval {pct(df['p3']['lo'])}–"
                      f"{pct(df['p3']['hi'])} %)"),
         "pm2": n(100 * curve[2], 1), "pm3": n(100 * curve[3], 1), "pm95": n(100 * curve[first95], 1),
         "ex_cov": pct(ex["predicted"] / ex["connections_2_4"], 0),
         "ext_gap": n(max(abs(ex[s]["predicted"] - ex[s]["observed"]) for s in ("2", "3", "4")) * 100, 1),
         "calib": n(100 * d["max_abs_gap"], 2),
         "all_top": pct(d["q4"]["all_costly_after_a_top_producer"], 1),
         "after_top": pct(d["q4"]["lost_on_last_segment_after_a_top_producer"], 1),
         "base_top": pct(ph["q4_baseline"]["after_a_top_producer"], 1),
         "dw_gap": n(ph["dwell"]["median_od_minus_dep_hat_s"]), "dw_od": pct(ph["dwell"]["made_observed_departure"], 1),
         "dw_hat": pct(ph["dwell"]["made_dep_hat"], 1), "dw_after": pct(ph["dwell"]["share_od_after_dep_hat"], 1)}
    v["def_band"] = {"peak": "weekday-peak", "daytime": "weekday-daytime", "weekend": "weekend", "evening": "evening"}[df["band"]]
    am = ph["extrapolation"]["april_may"]["3"]
    v["exam3p"], v["exam3o"] = pct(am["predicted"], 1), pct(am["observed"], 1)
    for s in ("2", "3", "4"):
        v[f"ex{s}p"], v[f"ex{s}o"] = pct(ex[s]["predicted"], 1), pct(ex[s]["observed"], 1)
    rows = []
    for lab, k in ROBUST:
        r = res[k] if k in res else c[k]
        rows.append((lab, r))
    rows += [("post-hoc: unobserved planned B all made", qb["unobserved_all_made"]),
             ("post-hoc: unobserved planned B all missed", qb["unobserved_all_missed"]),
             ("post-hoc: observed, line ran a trip short that hour", qb["observed_line_short"]),
             ("post-hoc: observed, line not short", qb["observed_line_not_short"])]
    v["robust_rows"] = "\n".join(
        f'  <tr><td>{lab}</td><td class="v">{pp(r["est"], 2)}</td><td class="v">{pp(r["ci95"][0], 2)} to '
        f'{pp(r["ci95"][1], 2)}</td><td class="v">{r["label"]}</td></tr>' for lab, r in rows)
    return v


def main() -> None:
    x = load()
    fig = figures(x)
    v = values(x, fig)
    tpl = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = render(tpl, v)
    (ROOT / "texts" / "transfers.html").write_text(out, encoding="utf-8")
    print(f"written texts/transfers.html, {len(v)} values")


if __name__ == "__main__":
    main()
