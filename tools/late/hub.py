"""Hub of the series Running late: its parts, every number from the result files.

Reads docs/research/delay-origins-results.json; writes texts/running-late.html.

    python3 tools/late/hub.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NB = " "


def n(v: float, dp: int = 0) -> str:
    return f"{v:,.{dp}f}".replace(",", NB)


def main() -> None:
    t = json.loads((ROOT / "docs/research/delay-origins-results.json").read_text())["tram"]
    b = json.loads((ROOT / "docs/research/bunching-results.json").read_text())
    bb = json.loads((ROOT / "docs/research/bunching-results-bus.json").read_text())
    g4 = lambda x: f"{x:+.4f}".replace("-", "−")  # noqa: E731
    v = {"S": n(100 * t["S"]["est"], 1), "S_label": t["S"]["label"], "rho": f"{t['rho']['est']:.3f}",
         "segments": n(t["segments"]), "passes_m": n(t["passes"] / 1e6, 1),
         "pairs": n(b["pairs"]), "g": g4(b["Q1"]["gamma_iv"]), "g_label": b["Q1"]["label"],
         "bg": g4(bb["Q1"]["gamma_iv"]), "bg_label": bb["Q1"]["label"],
         "bunched": n(100 * b["Q4"]["overall"]["bunched"], 2)}
    page = TEMPLATE
    for k, val in v.items():
        page = page.replace("{{" + k + "}}", val)
    assert "{{" not in page
    (ROOT / "texts" / "running-late.html").write_text(page, encoding="utf-8")
    print(v)


TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Running late · Barbora Šandová</title>
<meta name="description" content="Pre-specified studies of where and why Prague's trams fall behind, from the stop passes of 2025: a tenth of the segments record {{S}} % of the delay, narrowly, the same ones in odd and even weeks; and the spacing between two trams of a line shows practically no amplification from stop to stop.">
<meta property="og:title" content="Running late">
<meta property="og:description" content="Where and why Prague's trams fall behind, one pre-specified question at a time: where delay is recorded, and why two trams of a line come at once.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://bsandova.com/texts/running-late">
<meta property="og:image" content="https://bsandova.com/assets/og/running-late.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://bsandova.com/assets/og/running-late.jpg">
<meta name="theme-color" content="#ffffff">
<link rel="canonical" href="https://bsandova.com/texts/running-late">
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
  <p class="kicker">Hub · Running late · Prague trams and buses, spring and summer 2025</p>
  <h1>Running <em>late</em></h1>
  <p class="deck">Where and why Prague's trams fall behind, asked one question at a time of the stop passes behind the author's thesis, each question registered before the data that answers it was read.</p>
  <dl class="facts">
    <div><dt>parts published</dt><dd>2 <small>numbered by publication order</small></dd></div>
    <div><dt>design committed</dt><dd>8 Oct 2026 <small>CEST, commit times self-reported</small></dd></div>
  </dl>
</header>
<details class="tldr" open>
  <summary>Overwhelmed? Here's the short version</summary>
  <ul>
    <li>Each part fixes its question, its measure and its reading rule before the data that answers it is read.</li>
    <li>Part 1: over {{passes_m}} million tram passes on {{segments}} segments, a tenth of the segments record {{S}} % of all delay gained, just over the half set in advance, so concentration is {{S_label}}, narrowly; they are the same segments in odd and even weeks.</li>
    <li>Many of the largest totals are segments leaving large stops, and part of what they record is early trams waiting for their time; both were described afterwards, not registered.</li>
    <li>Part 2: over {{pairs}} pairs of trams of the same line, the spacing between them shows practically no amplification from stop to stop ({{g}} per stop, {{g_label}} by the registered rule); bunches, {{bunched}} % of pair passes and a floor, build gradually towards the end of a line, and the rare sudden closings concentrate partly by line. City buses show a small positive value ({{bg}}, {{bg_label}}), about the size of the spread among the tram estimates.</li>
  </ul>
</details>
<dl class="meta">
  <div><dt>published</dt><dd>8 October 2026 · <a href="../changelog/#running-late">version 3</a></dd></div>
  <div><dt>work since</dt><dd>October 2026</dd></div>
</dl>

<section class="film film-page"><div class="shot" style="view-transition-name:ph-running-late;--bg:url(../assets/photo/delay-origins.jpg);--bg-s:url(../assets/photo/delay-origins-1200.jpg)"></div><p class="credit">Photo: <a href="https://commons.wikimedia.org/wiki/File:Prague_night_tram_Lazarska.jpg">che</a> · CC BY-SA 3.0, toned</p></section>

<section>
<h2>The parts</h2>
<ol class="parts">
  <li>
    <a class="still" href="delay-origins" aria-label="Part 1, Where is delay born on Prague's trams?"><span class="shot" style="view-transition-name:ph-delay-origins;--bg:url(../assets/photo/delay-origins.jpg);--bg-s:url(../assets/photo/delay-origins-1200.jpg)"></span></a>
    <div>
      <p class="n">Part 1 · where delay appears · {{segments}} tram segments, 15 March – 8 September 2025</p>
      <h2><a href="delay-origins">Where is delay born on Prague's trams?</a></h2>
      <p>A tenth of the segments record {{S}} % of all delay gained, just over half, the same ones in odd and even weeks. Described afterwards, not registered: many of them leave large stops, and part of what they record is early trams waiting for their time.</p>
    </div>
  </li>
  <li>
    <a class="still" href="bunching" aria-label="Part 2, Why do two 22s come at once?"><span class="shot" style="view-transition-name:ph-bunching;--bg:url(../assets/photo/bunching.jpg);--bg-s:url(../assets/photo/bunching-1200.jpg)"></span></a>
    <div>
      <p class="n">Part 2 · bunching · {{pairs}} pairs of trams, 15 March – 8 September 2025</p>
      <h2><a href="bunching">Why do two 22s come at once? Tram bunching in Prague, 2025</a></h2>
      <p>The spacing between two trams of a line shows practically no amplification from stop to stop ({{g}} per stop, {{g_label}} by the registered rule, corrected in its version 2), and bunches build gradually towards the end of a line. The rare sudden closings concentrate on some platforms, as other rare one-stop events do, and partly by line. City buses show a small positive value ({{bg}}, {{bg_label}}), about the size of the spread among the tram estimates.</p>
    </div>
  </li>
</ol>
</section>

<section>
<h2>What the series asks next</h2>
<p>The same stop passes can answer one more question, registered before its data is read: how often a scheduled transfer between two tram lines at a large interchange actually works. It has no date; it appears here when it is done.</p>
<p>The series sits next to <a href="weather-rails">Weather on the rails</a>, which asks what rain and heat do to the same trams.</p>
</section>

<footer class="text-foot">
  <p class="back"><a href="../#works">← projects</a> · <a href="delay-origins">Part 1</a> · <a href="bunching">Part 2</a></p>
</footer>
</article>
</body>
</html>
'''

if __name__ == "__main__":
    main()
