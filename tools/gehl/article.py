"""Does rain empty Prague's trams: figures and the article, every number from the result files.

Reads docs/research/gehl-trams-{results,power,screen,coverage}.json and part 2's heat-delays-results.json; writes
assets/rain-dwell/ (charts.json, 01-windows.svg, 02-checks.svg, 03-heat.svg, results.json) and texts/rain-dwell.html
from tools/gehl/template.html. Chart helpers are the rain article's.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with pyfixest python tools/gehl/article.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("rain_article", ROOT / "tools" / "rain" / "article.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)
n, ci, range_rows, range_chart, static_range = ra.n, ra.ci, ra.range_rows, ra.range_chart, ra.static_range

R = ROOT / "docs" / "research"
A = ROOT / "assets" / "rain-dwell"
HEAT = "#b4532a"
UNIT = "seconds of dwell per stop"


def load() -> dict:
    j = lambda name: json.loads((R / f"{name}.json").read_text())  # noqa: E731
    return {"res": j("gehl-trams-results"), "pow": j("gehl-trams-power"), "scr": j("gehl-trams-screen"),
            "cov": j("gehl-trams-coverage"), "heat": j("heat-delays-results"), "rain": j("rain-delays-results")}


def margin_rules(chart: dict, m: float) -> dict:
    marks = chart["panels"][0]["marks"]
    chart["panels"][0]["marks"] = [{"type": "rule", "axis": "x", "v": v, "c": "grey"} for v in (-m, m)] + marks
    return chart


def figures(x: dict) -> None:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "gehl-trams-results.json", A / "results.json")
    res, m = x["res"], x["res"]["margin_m_s"]
    p, c = res["primary_theta"], res["checks"]
    theta = {"est_s": p["est_s"], "ci95": p["ci95"]}
    windows = range_rows([("rain, weekday mornings", c["by_window"]["rain"], "ink"),
                          ("weekend difference (θ)", theta, "held")])
    checks = range_rows([
        ("registered θ", theta, "held"),
        ("date instead of week", c["date_effects"]["rain_opt"], "grey"),
        ("evening as necessary", c["evening"]["rain_opt"], "ink"),
        ("school holidays out", c["school_holidays_out"]["rain_opt"], "ink"),
        ("weekday midday in", c["weekday_midday"]["rain_opt"], "ink"),
        ("centre stops", c["centre"]["rain_opt"], "ink"),
        ("outer stops", c["outer"]["rain_opt"], "ink"),
        ("0.5–2 mm, weekend", c["dose"]["r0_2_opt"], "ink"),
        ("2–5 mm, weekend", c["dose"]["r2_5_opt"], "ink"),
        ("placebo: 2 days later", c["placebo_rain_two_days_later"]["rain_opt"], "grey")])
    t2 = x["heat"]["tram"]
    heat = [{**r, "c": HEAT if r["y"].startswith("delay") else r["c"]} for r in range_rows([
        ("delay gained, part 2", {"est_s": t2["delta_s"], "ci95": t2["ci95"]}, "ink"),
        ("dwell, this part", res["heat_secondary"], "held")])]
    charts = {
        "windows": margin_rules(range_chart(
            windows, f"Change in dwell in a rain hour, with 95 % intervals and the ±{n(m, 1)} s band: weekday "
                     f"mornings {n(c['by_window']['rain']['est_s'], 2, True)} s; the weekend difference "
                     f"{n(p['est_s'], 2, True)} s, inside the band.", UNIT + ", rain against dry", [-2.5, 2.5],
            [-2, -1, 0, 1, 2]), m),
        "checks": margin_rules(range_chart(
            checks, "The registered weekend difference and its checks, with 95 % intervals: all near zero except the "
                    "date-effects version, which rests on three or four dates.", UNIT + ", weekend difference",
            [-2.5, 2.5], [-2, -1, 0, 1, 2]), m),
        "heat": range_chart(heat, f"Hot against mild hours, with 95 % intervals: trams gained "
                                  f"{n(abs(t2['delta_s']), 1)} s less delay in part 2, while dwell changes by "
                                  f"{n(res['heat_secondary']['est_s'], 2, True)} s.", "seconds per trip-hour (delay) "
                            "or per stop (dwell), hot against mild", [-25, 5], [-20, -10, 0]),
    }
    charts["heat"]["data"] = ["results.json", "../heat/results.json"]
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    flat = lambda rows: [{**r, "c": "held" if r["c"] == HEAT else r["c"]} for r in rows]  # noqa: E731
    static_range(windows, A / "01-windows.svg", UNIT, (-2.5, 2.5))
    static_range(checks, A / "02-checks.svg", UNIT, (-2.5, 2.5))
    static_range(flat(heat), A / "03-heat.svg", "seconds, hot against mild", (-25, 5))


def values(x: dict) -> dict:
    res, pw, scr, cov, t2 = x["res"], x["pow"]["after_deviation"], x["scr"], x["cov"], x["heat"]["tram"]
    p, h, c = res["primary_theta"], res["heat_secondary"], res["checks"]
    v = {"m": n(res["margin_m_s"], 1), "th": n(p["est_s"], 2, True), "th_lo": n(p["ci95"][0], 2),
         "th_hi": n(p["ci95"][1], 2), "th90_lo": n(p["ci90"][0], 2), "th90_hi": n(p["ci90"][1], 2), "label": p["label"],
         "n_units": n(p["n_units"]), "dates": n(p["dates"]), "opt_dates": n(p["treated_dates"]),
         "opt_hours": n(pw["optional"]["rain_hours"]), "nec_hours": n(pw["necessary"]["rain_hours"]),
         "nec_dates": n(pw["necessary"]["rain_dates"]), "mde": n(pw["mde_theta_s"], 1),
         "reg_opt_hours": n(x["pow"]["registered"]["optional"]["rain_hours"]),
         "reg_opt_dates": n(x["pow"]["registered"]["optional"]["rain_dates"]),
         "reg_both_opt": n(x["pow"]["registered"]["optional"]["dates_with_rain_and_dry_hours"]),
         "reg_both_nec": n(x["pow"]["registered"]["necessary"]["dates_with_rain_and_dry_hours"]),
         "h": n(h["est_s"], 2, True), "h_lo": n(h["ci95"][0], 2), "h_hi": n(h["ci95"][1], 2), "hlabel": h["label"],
         "h_dates": n(h["treated_dates"]), "t2": n(abs(t2["delta_s"]), 1), "t2_lo": n(t2["ci95"][0], 1),
         "t2_hi": n(t2["ci95"][1], 1),
         "dwell": n(scr["margin"]["mean_dwell_dry_necessary_s"], 1), "units_all": n(scr["units"]["kept"]),
         "centre_n": n(scr["centre_stops"]["n"]),
         "cov_rain": n(100 * cov["rain"]["share"], 1), "cov_dry": n(100 * cov["dry"]["share"], 1),
         "cov_diff": n(cov["rain_minus_dry_within_dates"]["difference_points"], 1),
         "cov_hot": n(cov["hot_minus_mild_within_dates"]["difference_points"], 1),
         "r1d": n(x["rain"]["tram"]["delta_s"], 1), "pyfixest": metadata.version("pyfixest")}

    def put(key: str, e: dict) -> None:
        v[key], v[key + "_lo"], v[key + "_hi"] = n(e["est_s"], 2, True), n(e["ci95"][0], 2), n(e["ci95"][1], 2)

    for key, e in (("rn", c["by_window"]["rain"]), ("de", c["date_effects"]["rain_opt"]),
                   ("ev", c["evening"]["rain_opt"]), ("sc", c["school_holidays_out"]["rain_opt"]),
                   ("md", c["weekday_midday"]["rain_opt"]), ("ce", c["centre"]["rain_opt"]),
                   ("ou", c["outer"]["rain_opt"]), ("d1", c["dose"]["r0_2_opt"]), ("d2", c["dose"]["r2_5_opt"]),
                   ("r1", c["dose"]["r0_2"]), ("r2", c["dose"]["r2_5"]), ("r3", c["dose"]["r5_up"]),
                   ("pl", c["placebo_rain_two_days_later"]["rain_opt"]), ("hg", c["heat_gehl_contrast"]["hot_opt"])):
        put(key, e)
    v["rn_abs"] = n(abs(c["by_window"]["rain"]["est_s"]), 2)
    v["rn_pct"] = n(100 * abs(c["by_window"]["rain"]["est_s"]) / scr["margin"]["mean_dwell_dry_necessary_s"], 1)
    photo = next(q for q in json.loads((ROOT / "assets/photo/sources.json").read_text()) if q["slug"] == "rain-dwell")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-rain-dwell;'
                  '--bg:url(../assets/photo/rain-dwell.jpg);--bg-s:url(../assets/photo/rain-dwell-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · '
                  f'{photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    x = load()
    figures(x)
    v = values(x)
    t = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda mm: str(v[mm.group(1)]), t)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "rain-dwell.html").write_text(out, encoding="utf-8")
    print(json.dumps({k: v[k] for k in v if k != "photo"}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
