"""Hub of the series Weather on the rails: the parts and one chart comparing them, every number from the results.

Reads docs/research/rain-delays-results.json and heat-delays-results.json; writes assets/weather-rails/ (charts.json,
01-compare.svg) and texts/weather-rails.html from tools/rain/hub.template.html.

    uv run --with matplotlib python tools/rain/hub.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
from article_kit import (n, part_item, photo_section, range_chart, range_rows, render, static_range,  # noqa: E402
                         use_article_style)

use_article_style()
ROOT = Path(__file__).resolve().parents[2]
R, A = ROOT / "docs" / "research", ROOT / "assets" / "weather-rails"
HEAT = "#b4532a"


def main() -> None:
    rain = json.loads((R / "rain-delays-results.json").read_text())
    heat = json.loads((R / "heat-delays-results.json").read_text())
    dwell = json.loads((R / "gehl-trams-results.json").read_text())
    rt, rb, rm = rain["tram"], rain["bus_secondary"], rain["checks_tram"]["metro"]["rain"]
    ht, hb, hm = heat["tram"], heat["bus_secondary"], heat["checks_tram"]["metro"]["hot"]
    e = lambda x: {"est_s": x["delta_s"], "ci95": x["ci95"]}  # noqa: E731
    rows = range_rows([("rain: trams", e(rt), "held"), ("rain: buses", e(rb), "held"), ("rain: metro", rm, "grey"),
                       ("heat: trams", e(ht), HEAT), ("heat: buses", e(hb), HEAT), ("heat: metro", hm, "grey")])
    A.mkdir(parents=True, exist_ok=True)
    chart = range_chart(rows, f"Delay gained per trip-hour against fair weather, with 95 % intervals: in rain hours "
                        f"about {n(rt['delta_s'], 1)} s more for trams and {n(rb['delta_s'], 1)} s for buses, in hot "
                        f"hours about {n(abs(ht['delta_s']), 1)} and {n(abs(hb['delta_s']), 1)} s less; the metro's "
                        f"intervals include zero under both.", "seconds of delay gained per trip-hour, against a dry or "
                        "mild hour", [-30, 20], [-30, -20, -10, 0, 10, 20])
    shutil.copy(R / "rain-delays-results.json", A / "rain-results.json")
    shutil.copy(R / "heat-delays-results.json", A / "heat-results.json")
    chart["data"] = ["rain-results.json", "heat-results.json"]
    (A / "charts.json").write_text(json.dumps({"compare": chart}, ensure_ascii=False))
    static_range(rows, A / "01-compare.svg", "seconds of delay gained per trip-hour", (-30, 20))
    v = {"r": n(rt["delta_s"], 1), "r_lo": n(rt["ci95"][0], 1), "r_hi": n(rt["ci95"][1], 1), "rl": rt["label"],
         "h": n(abs(ht["delta_s"]), 1), "h_lo": n(ht["ci95"][0], 1), "h_hi": n(ht["ci95"][1], 1), "hl": ht["label"],
         "rm": n(rm["est_s"], 1), "hm": n(hm["est_s"], 1), "hot_dates": n(ht["hot_dates"]),
         "rm_lo": n(rm["ci95"][0], 1), "rm_hi": n(rm["ci95"][1], 1), "hm_lo": n(hm["ci95"][0], 1),
         "hm_hi": n(hm["ci95"][1], 1), "hde": n(heat["checks_tram"]["date_effects"]["hot"]["est_s"], 1),
         "hde_lo": n(heat["checks_tram"]["date_effects"]["hot"]["ci95"][0], 1),
         "hde_hi": n(heat["checks_tram"]["date_effects"]["hot"]["ci95"][1], 1),
         "rpl": n(rain["checks_tram"]["placebo_lead"]["rain_next"]["est_s"], 1),
         "rain_dates": n(rt["rain_dates"]), "th": n(dwell["primary_theta"]["est_s"], 2, sign=True),
         "th_lo": n(dwell["primary_theta"]["ci95"][0], 2), "th_hi": n(dwell["primary_theta"]["ci95"][1], 2),
         "tl": dwell["primary_theta"]["label"], "dh": n(dwell["heat_secondary"]["est_s"], 2, sign=True),
         "dr": n(abs(dwell["checks"]["by_window"]["rain"]["est_s"]), 2),
         "wet_weekends": n(dwell["primary_theta"]["treated_dates"])}
    parts = render("\n".join(part_item(*part) for part in PARTS), v)
    photo = photo_section("weather-rails", image="rain-delays")
    template = Path(__file__).with_name("hub.template.html").read_text(encoding="utf-8")
    page = render(template, {**v, "parts": parts, "photo": photo})
    (ROOT / "texts" / "weather-rails.html").write_text(page, encoding="utf-8")
    print(v)


PARTS = [  # slug, part, title, kicker, summary; {{tokens}} are filled from the results
    ("rain-delays", 1, "Are Prague's trams later in rain hours?",
     "Part 1 · rain · March–September 2025, {{rain_dates}} days with rain",
     "In an hour with at least 0.5 mm of rain, a tram gained {{r}} seconds more delay than in a dry hour of the same "
     "route, hour and weekday on the same date ({{r_lo}} to {{r_hi}}, {{rl}}); the difference is larger in heavier "
     "rain, but the registered placebo failed, so it is an adjusted association."),
    ("heat-delays", 2, "Are Prague's trams more delayed in hot hours?",
     "Part 2 · heat · summer 2025, {{hot_dates}} days at 30 °C or more",
     "In a dry hour at 30 °C or more, a tram gained {{h}} seconds less delay than in a mild hour of the same route and "
     "week ({{h_lo}} to {{h_hi}}); registered as more delay, so {{hl}}; an association on {{hot_dates}} hot days whose "
     "cause the data cannot distinguish."),
    ("rain-dwell", 3, "Are tram stops shorter in rain?",
     "Part 3 · rain, heat and who boards · {{wet_weekends}} wet weekend days",
     "In rain hours a tram's stop was about {{dr}} seconds shorter on a weekday morning, and the weekend difference is "
     "{{th}} s ({{th_lo}} to {{th_hi}}, {{tl}}), so dwell gives no sign that rain cancels mainly optional trips; hot "
     "hours show no shorter stops ({{dh}} s)."),
]


if __name__ == "__main__":
    main()
