"""Are Prague's trams more delayed in hot hours: figures and the article, every number from the result files.

Reads docs/research/heat-delays-results.json, -describe.json, -power.json; writes assets/heat/ (charts.json,
01-modes.svg, 02-dose.svg, 03-checks.svg, 04-days.svg, results.json, describe.json) and texts/heat-delays.html from
tools/heat/template.html. Chart helpers are the rain article's.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with pyfixest python tools/heat/article.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from datetime import date
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("rain_article", ROOT / "tools" / "rain" / "article.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)
plt, n, ci, range_rows, range_chart, static_range = ra.plt, ra.n, ra.ci, ra.range_rows, ra.range_chart, ra.static_range

R = ROOT / "docs" / "research"
A = ROOT / "assets" / "heat"
HEAT = "#b4532a"  # the site's coral: heat, against the rain article's blue
DOSE_LABEL = {"t25_28": "25–28 °C", "t28_30": "28–30 °C", "t30_32": "30–32 °C", "t32_up": "≥ 32 °C"}


def load() -> dict:
    j = lambda name: json.loads((R / f"heat-delays-{name}.json").read_text())  # noqa: E731
    return {"res": j("results"), "desc": j("describe"), "pow": j("power")}


def recolour(rows: list[dict]) -> list[dict]:
    return [{**r, "c": HEAT if r["c"] == "held" else r["c"]} for r in rows]


def figures(x: dict) -> None:
    A.mkdir(parents=True, exist_ok=True)
    for name in ("results", "describe", "power"):
        shutil.copy(R / f"heat-delays-{name}.json", A / f"{name}.json")
    res, desc = x["res"], x["desc"]
    t, b, c = res["tram"], res["bus_secondary"], res["checks_tram"]
    unit = "seconds of delay gained per trip-hour, hot against mild"
    modes = recolour(range_rows([("trams", {"est_s": t["delta_s"], "ci95": t["ci95"]}, "held"),
                                 ("buses (secondary)", {"est_s": b["delta_s"], "ci95": b["ci95"]}, "ink"),
                                 ("metro (control)", c["metro"]["hot"], "grey")]))
    dose = recolour(range_rows([(DOSE_LABEL[k], c["dose"][k], "held") for k in DOSE_LABEL]))
    checks = recolour(range_rows([
        ("registered estimate", {"est_s": t["delta_s"], "ci95": t["ci95"]}, "held"),
        ("same date, not week", c["date_effects"]["hot"], "ink"),
        ("hot from 28 °C", c["threshold_28"]["hot"], "ink"),
        ("hot from 32 °C", c["threshold_32"]["hot"], "ink"),
        ("wet hours kept", c["wet_hours_kept"]["hot"], "ink"),
        ("delay level", c["level_instead_of_gain"]["hot"], "ink"),
        ("placebo: 2 days later", c["placebo_two_days_later"]["hot_lead2"], "grey")]))
    charts = {
        "modes": range_chart(modes, f"Delay gained in a hot hour against a mild one, with 95 % intervals: trams "
                             f"{n(t['delta_s'], 1, True)} s and buses {n(b['delta_s'], 1, True)} s, both below zero; "
                             f"the metro {n(c['metro']['hot']['est_s'], 1, True)} s.", unit, [-30, 10],
                             [-30, -20, -10, 0, 10]),
        "dose": range_chart(dose, "Delay gained by trams by the hour's temperature against mild hours, with 95 % "
                            "intervals: hotter hours went with less delay gained; the bands share the same few hot days.", "seconds per trip-hour, against mild "
                            "hours (15–25 °C)", [-30, 5], [-30, -20, -10, 0]),
        "checks": range_chart(checks, "The registered tram estimate and its checks, with 95 % intervals: every "
                              "check but the placebo has an interval below zero (analytic, about 11 date clusters); the "
                              "placebo's interval includes zero.", unit,
                              [-30, 10], [-30, -20, -10, 0, 10]),
    }
    days = [d for d in desc["hot_days"] if date(2025, 5, 1) <= date.fromisoformat(d["date"]) <= date(2025, 9, 8)]
    lab = lambda s: f"{date.fromisoformat(s).day} {date.fromisoformat(s).strftime('%b')}"  # noqa: E731
    charts["days"] = {
        "alt": "Hours at 30 °C or more per day in Prague, summer 2025: eleven days between mid-June and late August, "
               "the longest runs on 2 July and 13–15 August.",
        "panels": [{"h": 190, "x": {"kind": "cat", "domain": [lab(d["date"]) for d in days]},
                    "y": {"kind": "linear", "domain": [0, 11], "fmt": {"dp": 0}, "label": "dry hours at 30 °C or more"},
                    "marks": [{"type": "vbar", "c": HEAT,
                               "rows": [{"x": lab(d["date"]), "y1": d["hot_hours"],
                                         "tip": f"{lab(d['date'])}: {d['hot_hours']} hot hours, maximum "
                                                f"{n(d['tmax'], 1)} °C"} for d in days if d["hot_hours"]]}]}],
        "table": {"cols": ["date", "hot hours", "maximum °C"],
                  "rows": [[d["date"], d["hot_hours"], d["tmax"]] for d in days if d["hot_hours"]]},
        "data": ["describe.json"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    for rows, name, label, xlim in ((modes, "01-modes", unit, (-30, 10)), (dose, "02-dose", unit, (-30, 5)),
                                    (checks, "03-checks", unit, (-30, 10))):
        static_range([{**r, "c": "held" if r["c"] == HEAT else r["c"]} for r in rows], A / f"{name}.svg", label, xlim)
    f, ax = plt.subplots(figsize=(7.2, 2.0))
    hot = [d for d in days if d["hot_hours"]]
    ax.bar([lab(d["date"]) for d in hot], [d["hot_hours"] for d in hot], color=HEAT)
    ax.set_ylabel("hours ≥ 30 °C")
    f.tight_layout()
    f.savefig(A / "04-days.svg")
    plt.close(f)


def values(x: dict) -> dict:
    res, desc, pw = x["res"], x["desc"], x["pow"]
    t, b, c = res["tram"], res["bus_secondary"], res["checks_tram"]
    rm = desc["raw_means"]
    v = {"d": n(abs(t["delta_s"]), 1), "d_lo": n(t["ci95"][0], 1), "d_hi": n(t["ci95"][1], 1),
         "d_signed": n(t["delta_s"], 1), "label": t["label"],
         "bd": n(abs(b["delta_s"]), 1), "bd_lo": n(b["ci95"][0], 1), "bd_hi": n(b["ci95"][1], 1),
         "n_units": n(t["n_units"]), "b_units": n(b["n_units"]), "dates": n(t["dates"]), "hot_dates": n(t["hot_dates"]),
         "hot_units": n(t["hot_units"]), "hot_hours": n(pw["hot_hours"]), "mild_hours": n(pw["mild_hours"]),
         "hot_weeks": n(pw["hot_weeks"]), "mde": n(pw["mde_s"], 1), "pse": n(pw["se_s"], 1),
         "sig_day": n(pw["sigma_day_s"], 1), "tmax": n(desc["tmax_window"], 1),
         "t_hot": n(rm["tram"]["hot"]["mean_s"], 1), "t_mild": n(rm["tram"]["mild"]["mean_s"], 1),
         "b_hot": n(rm["bus"]["hot"]["mean_s"], 1), "b_mild": n(rm["bus"]["mild"]["mean_s"], 1),
         "t_pct": n(100 * abs(t["delta_s"]) / rm["tram"]["mild"]["mean_s"]), "pyfixest": metadata.version("pyfixest"),
         "pl_pct": n(100 * c["placebo_two_days_later"]["hot_lead2"]["est_s"] / t["delta_s"]),
         "hot_sundays": n(sum(date.fromisoformat(d["date"]).weekday() == 6 for d in desc["hot_days"] if d["hot_hours"])),
         "dwell_h": n(json.loads((R / "gehl-trams-results.json").read_text())["heat_secondary"]["est_s"], 2, True)}

    def put(key, e):
        v[key], v[key + "_lo"], v[key + "_hi"] = n(e["est_s"], 1), n(e["ci95"][0], 1), n(e["ci95"][1], 1)

    for key, e in (("de", c["date_effects"]["hot"]), ("mt", c["metro"]["hot"]), ("t28", c["threshold_28"]["hot"]),
                   ("t32", c["threshold_32"]["hot"]), ("wet", c["wet_hours_kept"]["hot"]),
                   ("lv", c["level_instead_of_gain"]["hot"]), ("pl", c["placebo_two_days_later"]["hot_lead2"])):
        put(key, e)
    for k in DOSE_LABEL:
        put(k, c["dose"][k])
    photo = next(p for p in json.loads((ROOT / "assets/photo/sources.json").read_text()) if p["slug"] == "heat-delays")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-heat-delays;'
                  '--bg:url(../assets/photo/heat-delays.jpg);--bg-s:url(../assets/photo/heat-delays-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, '
                  'toned</p></section>')
    return v


def main() -> None:
    x = load()
    figures(x)
    v = values(x)
    t = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), t)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "heat-delays.html").write_text(out, encoding="utf-8")
    print(f"written texts/heat-delays.html, {len(v)} values")


if __name__ == "__main__":
    main()
