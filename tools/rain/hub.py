"""Hub of the series Weather on the rails: the parts and one chart comparing them, every number from the results.

Reads docs/research/rain-delays-results.json and heat-delays-results.json; writes assets/weather-rails/ (charts.json,
01-compare.svg) and texts/weather-rails.html.

    uv run --with matplotlib python tools/rain/hub.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
from article_kit import n, range_chart, range_rows, static_range, use_article_style  # noqa: E402

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
    page = TEMPLATE
    for k, val in v.items():
        page = page.replace("{{" + k + "}}", str(val))
    assert "{{" not in page
    (ROOT / "texts" / "weather-rails.html").write_text(page, encoding="utf-8")
    print(v)


PART = '''  <li>
    <a class="still" href="{slug}" aria-label="Part {k}, {title}"><span class="shot" style="view-transition-name:ph-{slug};--bg:url(../assets/photo/{slug}.jpg);--bg-s:url(../assets/photo/{slug}-1200.jpg)"></span></a>
    <div>
      <p class="n">{n}</p>
      <h2><a href="{slug}">{title}</a></h2>
      <p>{text}</p>
    </div>
  </li>
'''

TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather on the rails · Barbora Šandová</title>
<meta name="description" content="Three pre-specified studies of one season of Prague's trams and buses: about {{r}} seconds more delay gained per trip-hour in rain hours, about {{h}} seconds less in hot hours, both associations, and no weekend-against-weekday difference in how much shorter stops are in rain.">
<meta property="og:title" content="Weather on the rails">
<meta property="og:description" content="Prague's trams gained about {{r}} seconds more delay in rain hours and about {{h}} seconds less in hot hours, both associations; stops were slightly shorter in rain, alike on weekdays and weekends. Three pre-specified studies of the same 121 million stop passes.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://bsandova.com/texts/weather-rails">
<meta property="og:image" content="https://bsandova.com/assets/og/weather-rails.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://bsandova.com/assets/og/weather-rails.jpg">
<meta name="theme-color" content="#ffffff">
<link rel="canonical" href="https://bsandova.com/texts/weather-rails">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="../style.css">
<link rel="stylesheet" href="../text.css">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500&family=JetBrains+Mono:wght@400&family=Fraunces:opsz,wght@9..144,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../a24.css">
</head>
<body>
<div class="top"><b><a href="../" aria-label="bŠ, bsandova.com, home">bŠ</a></b><nav><a href="../#work">Work</a><a href="../#works">All work</a><a href="../#about">About</a><a href="../ask/" class="ask-link">Ask</a><a href="../#contact">Contact</a></nav><span class="tr">hub · transit · en</span></div>

<article class="text">
<header class="text-head">
  <p class="kicker">Hub · Weather on the rails · Prague trams, buses and the metro, summer 2025</p>
  <h1>Weather <em>on the rails</em></h1>
  <p class="deck">Three pre-specified studies of how Prague's tram and bus delays and stop times differ with the weather, on the same 121 million stop passes: rain hours, hot hours, and dwell as a passenger proxy.</p>
  <dl class="facts">
    <div><dt>parts published</dt><dd>3 <small>numbered by publication order</small></dd></div>
    <div><dt>designs committed</dt><dd>6 and 8 Oct 2026 <small>CEST, commit times self-reported</small></dd></div>
  </dl>
</header>
<details class="tldr" open>
  <summary>Overwhelmed? Here's the short version</summary>
  <ul>
    <li>Each part fixed its question, its model and its reading rule before the weather was joined to the delays.</li>
    <li>Part 1: in an hour with rain, a tram gained about {{r}} seconds more delay than in a dry hour ({{r_lo}} to {{r_hi}}, {{rl}}); the registered placebo failed ({{rpl}} s), so it is an adjusted association.</li>
    <li>Part 2: in a dry hour at 30 °C or more, a tram gained about {{h}} seconds less delay than in a mild one ({{h_lo}} to {{h_hi}}), the opposite of the registered expectation, so {{hl}}; it rests on {{hot_dates}} hot days.</li>
    <li>Part 3: in rain hours a tram's stop was about {{dr}} seconds shorter, with no clear weekend-against-weekday-morning difference ({{th}} s, {{th_lo}} to {{th_hi}}, {{tl}}), so Jan Gehl's split between necessary and optional trips does not show in dwell.</li>
    <li>Parts 1 and 2 measure the sum of passengers, traffic and the vehicles themselves; part 3 finds no shorter stops in hot hours ({{dh}} s), and traffic is untested.</li>
  </ul>
</details>
<dl class="meta">
  <div><dt>published</dt><dd>8 October 2026 · updated 9 October 2026 · <a href="../changelog/#weather-rails">version 2</a></dd></div>
  <div><dt>work since</dt><dd>October 2026</dd></div>
</dl>

<section class="film film-page"><div class="shot" style="view-transition-name:ph-weather-rails;--bg:url(../assets/photo/rain-delays.jpg);--bg-s:url(../assets/photo/rain-delays-1200.jpg)"></div><p class="credit">Photo: <a href="https://commons.wikimedia.org/wiki/File:Praha,_Ko%C5%A1%C3%AD%C5%99e_Kaval%C3%ADrka_v_noci.jpg">Aktron</a> · CC BY-SA 4.0, toned</p></section>

<section>
<h2>The parts</h2>
<ol class="parts">
''' + PART.format(k=1, slug="rain-delays", title="Are Prague's trams later in rain hours?",
                  n="Part 1 · rain · March–September 2025, {{rain_dates}} days with rain",
                  text="In an hour with at least 0.5 mm of rain, a tram gained {{r}} seconds more delay than in a dry hour of the same route, hour and weekday on the same date ({{r_lo}} to {{r_hi}}, {{rl}}); the difference is larger in heavier rain, but the registered placebo failed, so it is an adjusted association.") + PART.format(
    k=2, slug="heat-delays", title="Are Prague's trams more delayed in hot hours?",
    n="Part 2 · heat · summer 2025, {{hot_dates}} days at 30 °C or more",
    text="In a dry hour at 30 °C or more, a tram gained {{h}} seconds less delay than in a mild hour of the same route and week ({{h_lo}} to {{h_hi}}); registered as more delay, so {{hl}}; an association on {{hot_dates}} hot days whose cause the data cannot distinguish.") + PART.format(
    k=3, slug="rain-dwell", title="Are tram stops shorter in rain?",
    n="Part 3 · rain, heat and who boards · {{wet_weekends}} wet weekend days",
    text="In rain hours a tram's stop was about {{dr}} seconds shorter on a weekday morning, and the weekend difference is {{th}} s ({{th_lo}} to {{th_hi}}, {{tl}}), so dwell gives no sign that rain cancels mainly optional trips; hot hours show no shorter stops ({{dh}} s).") + '''</ol>
</section>

<section>
<h2>Parts 1 and 2 side by side</h2>
<p>Parts 1 and 2 use the same table and outcome, the delay a trip gains within a clock hour, compared with the same route at the same hour and weekday, with the weather of that hour from four ČHMÚ stations, but not the same model: part 1 compares hours within a date (date effects), part 2 within a week (week effects), because heat lasts all day. Part 2's registered check with date effects gives {{hde}} seconds ({{hde_lo}} to {{hde_hi}}). The two estimates have opposite signs. The metro's intervals include zero under both, {{rm}} s in rain ({{rm_lo}} to {{rm_hi}}) and {{hm}} s in heat ({{hm_lo}} to {{hm_hi}}), which fits a difference on the street rather than one common to all modes, without showing what causes it. The heat part rests on {{hot_dates}} hot days, the rain part on {{rain_dates}} wet ones.</p>
<figure data-chart="../assets/weather-rails/charts.json#compare">
  <p class="ch-head">About {{r}} s more delay gained per trip-hour in rain hours, about {{h}} s less in hot hours; the metro's intervals include zero.</p>
  <img src="../assets/weather-rails/01-compare.svg" alt="Delay gained per trip-hour against fair weather, with 95 % intervals: rain above zero for trams and buses, heat below zero for both, the metro near zero in both." loading="lazy">
  <figcaption><b>fig. 1</b> · Seconds of delay gained per trip in a rain hour against a dry hour (part 1) and in a hot dry hour against a mild one (part 2), with 95 % intervals; blue, rain; coral, heat; grey, the metro. Each estimate is the registered model of its part: date effects for rain, week effects for heat. Data: as in the parts.</figcaption>
</figure>
</section>

<section>
<h2>How each part was pre-specified</h2>
<p>Each part has its own design file, committed before the weather it studies was joined to its outcome, and its own dated changes after registration in its change log. The heat part reused the delays the rain part had already read, against rain only, and says so; the third part measures dwell, which neither earlier part had read, and changed its weekend window once, before the comparison, for a stated reason. The commit times are the author's own, not an independent registry's.</p>
</section>

<footer class="text-foot">
  <p class="back"><a href="../#works">← projects</a> · <a href="rain-delays">Part 1</a> · <a href="heat-delays">Part 2</a> · <a href="rain-dwell">Part 3</a></p>
</footer>
</article>

<script src="../assets/charts.js" defer></script>
</body>
</html>
'''

if __name__ == "__main__":
    main()
