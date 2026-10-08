"""Will you make your connection: the roulette, figures, map and the article, every number from the result files.

Reads docs/research/transfers-{design,screen,results,describe}.json and the roulette cells in assets/transfers/;
writes assets/transfers/ (charts.json, map.json, results.json, describe.json, static SVGs) and texts/transfers.html
from tools/transfer/template.html. Chart helpers are part 2's.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with scipy --with numpy python tools/transfer/article.py
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


ba = load_module("bunch_article", "tools/bunch/article.py")
plt, n = ba.plt, ba.n
R, A = ROOT / "docs" / "research", ROOT / "assets" / "transfers"
HELD, INK, GREY = ba.HELD, ba.INK, ba.GREY
HUB_HALF_M = 120  # half the side of the square drawn for a hub on the map


def load() -> dict:
    j = lambda name: json.loads((R / f"transfers-{name}.json").read_text())  # noqa: E731
    return {"res": j("results"), "scr": j("screen"), "desc": j("describe"),
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
    for k in ("results", "describe"):
        shutil.copy(R / f"transfers-{k}.json", A / f"{k}.json")
    res, d = x["res"], x["desc"]
    charts = {}
    curve = pooled_curve(x["cells"])
    cost = res["q2_cost"]
    ser = [{"name": "made, all shown cells", "c": HELD, "pts": [[s, round(100 * p, 1)] for s, p in curve]},
           {"name": "made, connections as planned", "c": INK,
            "pts": [[int(s), round(100 * cost[s]["made"], 1)] for s in ("2", "3", "4")]},
           {"name": "cost over 5 min extra wait", "c": GREY, "dash": "dash",
            "pts": [[int(s), round(100 * cost[s]["costly_miss"], 1)] for s in ("2", "3", "4")]}]
    charts["slack"] = ba.line_chart(
        ser, "Share of tram-to-tram connections made by the minutes planned between them, Prague 2025: about 71 % "
             "with 2 minutes, 80 % with 3 and 87 % with 4, and over 95 % from about 6 minutes; one connection in "
             "five planned 3 minutes apart costs more than 5 minutes of extra wait.",
        "minutes planned between arrival and departure", "% of connections", [1, 10], [0, 100],
        {"cols": ["minutes planned", "made, all cells %", "made, as planned %", "cost over 5 min %"],
         "rows": [[s, round(100 * p, 1), round(100 * cost[str(s)]["made"], 1) if str(s) in cost else "",
                   round(100 * cost[str(s)]["costly_miss"], 1) if str(s) in cost else ""] for s, p in curve]},
        ["results.json", "roulette.json"], {"dp": 0})
    ba.static_lines(ser, A / "02-slack.svg", "minutes planned", "% of connections")

    q1, q1b, bd, c = res["q1_within"], res["q1b_day"], res["bounds"], res["checks"]
    rows = ba.range_rows([
        ("registered: same day, slack 2–4", q1["est"], q1["ci95"], "held"),
        ("bound: uncertain B all made", bd["all_made"]["est"], bd["all_made"]["ci95"], "grey"),
        ("bound: uncertain B all missed", bd["all_missed"]["est"], bd["all_missed"]["ci95"], "grey"),
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
    chart = ba.range_chart(rows, "How much more often connections were made than with the two lines' delays set "
                                 "against other trips of the same day, in percentage points with 95 % intervals: "
                                 "the registered estimate is +0.6, inside the ±1 band, and the bounds for connections "
                                 "whose planned tram may have been missing run from −20 to +6.",
                           "percentage points", [-22, 8], 1.0, 0.0, {"dp": 1}, ["results.json"])
    chart["panels"][0]["marks"][0]["label"] = "the registered ±1 point"
    charts["checks"] = chart
    ba.static_range(rows, A / "03-checks.svg", "percentage points", (-22, 8), 0.0)

    spec, drawn = map_spec(x)
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    static_map(spec, A / "04-map.svg")
    roul = A / "01-roulette.svg"
    f, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.plot([s for s, _ in curve], [100 * p for _, p in curve], color=HELD, marker="o", ms=3)
    ax.set_xlabel("minutes planned")
    ax.set_ylabel("% made, all hubs")
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
         "calib": n(100 * d["max_abs_gap"], 1),
         "costly_m": n(q4["costly_misses"] / 1e6, 1),
         "lost_last": pct(q4["origin_share"]["lost_on_last_segment"]),
         "already": pct(q4["origin_share"]["already_late"]),
         "after_top": pct(q4["lost_on_last_segment_after_a_top_producer"]),
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
    photo = next(q for q in json.loads((ROOT / "assets/photo/sources.json").read_text()) if q["slug"] == "transfers")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-transfers;'
                  '--bg:url(../assets/photo/transfers.jpg);--bg-s:url(../assets/photo/transfers-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · '
                  f'{photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    x = load()
    fig = figures(x)
    v = values(x, fig)
    tpl = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), tpl)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "transfers.html").write_text(out, encoding="utf-8")
    print(json.dumps({k: v[k] for k in v if k != "photo"}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
