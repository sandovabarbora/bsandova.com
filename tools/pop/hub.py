"""Pop, measured: the series hub, texts/pop-measured.html, with every number read from the parts' results.

The page keeps the layout of the Prague, measured hub (its head and styles are copied from texts/prague-measured.html)
and adds the comparison across parts that the series design promises (§3): the focal songs' places, Czechia's place,
how many songs make half of each artist's streams, the share of sold-out entries and the dearest ticket in days.

    python3 tools/pop/hub.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
NB = " "
PARTS = [  # slug, part number, title on the part's page, what the part is about
    ("harry-styles", 1, "Harry Styles, measured: how long a hit lasts, where, and what a ticket costs",
     "Spotify charts 2017–2026 · two tours, 2017–2023"),
    ("taylor-swift", 2, "Taylor Swift, measured: a catalogue that sells out everything",
     "Spotify charts 2017–2026 · two stadium tours · Europe's prices in 2024"),
    ("bts", 3, "BTS, measured: a catalogue, not a hit", "Spotify charts 2017–2026 · three tours, 2018–2026"),
    ("bad-bunny", 4, "Bad Bunny, measured: a long hit, everywhere at once", "Spotify charts 2017–2026 · three tours, 2019–2026"),
    ("billie-eilish", 5, "Billie Eilish, measured: two long hits, five years apart", "Spotify charts 2017–2026 · three tours, 2019–2025"),
]
NAME = {"harry-styles": "Harry Styles", "taylor-swift": "Taylor Swift", "bts": "BTS", "bad-bunny": "Bad Bunny",
        "billie-eilish": "Billie Eilish"}


def n(v: float, dp: int = 0) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 and round(abs(v), dp) else "") + s


def pct(v: float, dp: int = 0) -> str:
    return f"{n(100 * v, dp)} %"


def songs_to_half(slug: str) -> int:
    import csv
    rows = list(csv.DictReader(open(R / f"{slug}-songs.csv", encoding="utf-8")))
    total, cum = sum(int(r["streams"]) for r in rows), 0
    for i, r in enumerate(rows, 1):
        cum += int(r["streams"])
        if cum >= total / 2:
            return i
    return len(rows)


def part(slug: str) -> dict:
    r = json.loads((R / f"{slug}-results.json").read_text())
    focal = next(p for p in r["q1"]["own"] if p["focal"])
    cz = r["q2"]["czechia"]
    t5 = r["q5"].get("countries", [])
    return {"slug": slug, "focal": focal["label"].split(" - ", 1)[1], "days": focal["days"], "still": focal["still_charting"],
            "longer": focal["share_longer"], "lo": focal["ci95"][0], "hi": focal["ci95"][1],
            "peak": 2 if slug == "taylor-swift" else 1, "cz_ratio": cz["ratio"], "cz_rank": cz["rank"],
            "ranked": r["q2"]["n_ranked"], "above": sum(c["ratio"] > 1 for c in r["q2"]["countries"]),
            "countries": len(r["q2"]["countries"]), "half": songs_to_half(slug), "songs": r["q4"]["songs"],
            "top_share": r["q4"]["top_share"], "sold_out": r["q3"]["share_sold_out"], "entries": r["q3"]["entries"],
            "top_ticket": t5[0] if t5 else None, "n_t": len(t5)}


def summary(p: dict) -> str:
    s = (f"<i>{p['focal']}</i> spent {n(p['days'])} days in Spotify's global Top 200{' and is still there' if p['still'] else ''}; "
         f"{pct(p['longer'], 1)} of {'number ones' if p['peak'] == 1 else 'songs that also peaked at two'} since 2017 lasted longer "
         f"(95 % CI {pct(p['lo'], 1)} to {pct(p['hi'], 1)}). It outlasted the local median number one in {p['above']} of "
         f"{p['countries']} national charts; in Czechia it lasted {n(p['cz_ratio'], 2)} times as long, {p['cz_rank']}th of {p['ranked']}. "
         f"Half of {NAME[p['slug']]}'s streams come from {p['half']} songs. {pct(p['sold_out'])} of {p['entries']} Boxscore entries sold out")
    if p["top_ticket"]:
        s += (f", and the dearest ticket relative to income was in {p['top_ticket']['country']}, "
              f"{n(p['top_ticket']['days_of_income'], 1)} days of GDP per capita.")
    else:
        s += "."
    return s


def main() -> None:
    src = (ROOT / "texts" / "prague-measured.html").read_text(encoding="utf-8")
    head = src[:src.index("</style>") + len("</style>")]
    head = re.sub(r"<title>.*?</title>", "<title>Pop, measured</title>", head)
    head = head.replace("</style>", ".minis{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px 24px;margin:1rem 0 0}"
                        ".minis figure{margin:0}.minis img{display:block;width:100%;height:auto}"
                        ".minis figcaption{font:400 12px var(--mono);color:#666;margin-top:4px}\n</style>")
    head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="Five registered studies of five artists on Spotify\'s charts and on tour, asking the same five questions, with a comparison across them.">', head)
    head = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="Pop, measured">', head)
    head = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="Harry Styles, Taylor Swift, BTS, Bad Bunny and Billie Eilish, measured the same way: how long a hit lasts, where, whether it is one song or many, how many nights a city fills and what a ticket costs.">', head)
    head = head.replace("prague-measured", "pop-measured").replace("assets/og/prague-council.jpg", "assets/og/pop-harry-styles.jpg")
    ps = [part(s) for s, *_ in PARTS]
    items = []
    for (slug, k, title, what), p in zip(PARTS, ps):
        items.append(f'''  <li>
    <a class="still" href="pop-{slug}" aria-label="Part {k}, {title}"><span class="shot" style="view-transition-name:ph-pop-{slug};--bg:url(../assets/photo/pop-{slug}.jpg);--bg-s:url(../assets/photo/pop-{slug}-1200.jpg)"></span></a>
    <div>
      <p class="n">Part {k} · {NAME[slug]} · {what}</p>
      <h2><a href="pop-{slug}">{title}</a></h2>
      <p>{summary(p)}</p>
    </div>
  </li>''')
    rows = "\n".join(
        f"<tr><td>{k} · {NAME[p['slug']]}</td><td><i>{p['focal']}</i></td><td class=\"v\">{pct(p['longer'], 1)}</td>"
        f"<td class=\"v\">{n(p['cz_ratio'], 2)}× · {p['cz_rank']}/{p['ranked']}</td><td class=\"v\">{p['half']} of {p['songs']}</td>"
        f"<td class=\"v\">{pct(p['sold_out'])}</td><td class=\"v\">"
        + (f"{n(p['top_ticket']['days_of_income'], 1)} · {p['top_ticket']['country']}" if p["top_ticket"] else "–") + "</td></tr>"
        for (slug, k, *_), p in zip(PARTS, ps))
    english = [p for p in ps if p["slug"] in ("harry-styles", "taylor-swift", "billie-eilish")]
    t6 = json.loads((R / "pop-measured-part6-results.json").read_text())
    m1, m2 = t6["m1"], t6["m2"]
    items.append(f'''  <li>
    <a class="still" href="pop-together" aria-label="Part 6, the five together"><span class="shot" style="view-transition-name:ph-pop-together;--bg:url(../assets/photo/pop-together.jpg);--bg-s:url(../assets/photo/pop-together-1200.jpg)"></span></a>
    <div>
      <p class="n">Part 6 · all five artists · two exploratory models</p>
      <h2><a href="pop-together">A hit lasts three times as long in its own language, and tickets barely follow income</a></h2>
      <p>Across {m1["n"]} artist–country pairs, with artist and country fixed effects, a song lasted {1 + m1["pct"]:.1f} times as long in a country speaking its language (95 % CI {1 + m1["pct_lo"]:.1f}–{1 + m1["pct_hi"]:.1f}). Across {m2["n"]} tour entries, the average ticket rose with the host country's income at an elasticity of {m2["coef"]:.2f} ({m2["lo"]:.2f} to {m2["hi"]:.2f}), so a show cost several times more days of income in poorer countries. Exploratory: models fixed before estimation, inputs seen in parts 1–5.</p>
    </div>
  </li>''')
    maps = "".join(f'<figure class="mini"><a href="pop-{slug}"><img src="../assets/pop/{slug}/map.svg" alt="World map for {NAME[slug]}: where the focal song lasted longer than local number ones, and ticket prices in days of income." loading="lazy"></a><figcaption>{NAME[slug]}</figcaption></figure>'
                   for slug, *_ in PARTS)
    body = f'''<body>
<div class="top"><b><a href="../" aria-label="bŠ, bsandova.com, home">bŠ</a></b><nav><a href="../#work">Work</a><a href="../#works">All work</a><a href="../#about">About</a><a href="../ask/" class="ask-link">Ask</a><a href="../#contact">Contact</a></nav><span class="tr">hub · pop · en</span></div>

<article class="text">
<header class="text-head">
  <p class="kicker">Hub · Pop, measured · five artists, the same five questions, and the five together</p>
  <h1>Pop, <em>measured</em></h1>
  <p class="deck">Five artists measured the same way: how long their biggest song lasted, where, whether their listening is one song or many, how many nights a city could fill and what a ticket cost in days of income.</p>
  <dl class="facts">
    <div><dt>parts published</dt><dd>6 <small>five artists and one part across them</small></dd></div>
    <div><dt>designs committed</dt><dd>1–2 Oct 2026 <small>CEST, commit times self-reported</small></dd></div>
  </dl>
</header>

<details class="tldr" open>
  <summary>Overwhelmed? Here's the short version</summary>
  <ul>
    <li>Every part answers the same questions from the same data, collected on one day, under one design written before the data were parsed.</li>
    <li>The parts differ most in how spread their listening is, from six songs making half of one artist's streams to {max(p['half'] for p in ps)} for another.</li>
    <li>Czech listeners keep English-language hits about as long as the world's middle and let hits in other languages pass quickly.</li>
    <li>Nearly every show sold out for every artist, so the data cannot say where demand ends; tickets weighed most where incomes are lowest.</li>
  </ul>
</details>

<dl class="meta">
  <div><dt>published</dt><dd>2 October 2026 · updated 2 October 2026 · <a href="#changelog">version 1</a></dd></div>
</dl>
<details class="meta-more">
  <summary>About this series</summary>
<dl class="meta">
  <div><dt>status</dt><dd>hub, index of six research articles and one related study</dd></div>
  <div><dt>data</dt><dd>kworb.net Spotify chart totals, Wikipedia tour articles (Boxscore), World Bank GDP per capita, Eurostat HICP; hashes in <a href="https://github.com/sandovabarbora/bsandova.com/blob/main/docs/research/pop-measured-files.sha256">pop-measured-files.sha256</a></dd></div>
  <div><dt>code</dt><dd><a href="https://github.com/sandovabarbora/bsandova.com/tree/main/tools/pop">tools/pop/</a>, the same scripts for every part; this page is built by <code>tools/pop/hub.py</code></dd></div>
  <div><dt>cite as</dt><dd>Šandová, B. (2026). <i>Pop, measured</i>. bsandova.com/texts/pop-measured, version 1.</dd></div>
  <div><dt>licence</dt><dd>code MIT; text, figures and data CC BY 4.0</dd></div>
</dl>
</details>

<section class="series">
<h2>The parts</h2>
<ol class="parts">
{chr(10).join(items)}
</ol>
</section>

<section id="maps">
<h2>Five maps</h2>
<p>Each part's map shades the countries by how many times as long the artist's biggest song lasted in the national chart as the local median number one, blue where longer and grey where shorter, with circles for the average ticket in days of income. Side by side, they show where each artist's audience is: much of the world for Harry Styles and Billie Eilish, the English-speaking world and Asia more than Latin America for Taylor Swift, East and South-East Asia for BTS, and Latin America, Spain and the United States for Bad Bunny.</p>
<div class="minis">{maps}</div>
</section>

<section id="compare">
<h2>Across the series</h2>
<p>The series design fixed one comparison in advance: the focal songs' places, Czechia's place, and the share of sold-out entries, side by side, with no test across artists. The table adds how many songs make up half of each artist's streams and the country where a ticket cost the most days of income. Taylor Swift's focal song peaked at two, so its place is among songs that peaked at two, not among number ones.</p>
<div class="tw">
<table class="ht">
<thead><tr><th>Part</th><th>Focal song</th><th>Lasted longer</th><th>Czechia, ratio · rank</th><th>Songs for half the streams</th><th>Entries sold out</th><th>Dearest ticket, days of income</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<p>Three patterns stand out. The artists differ most in how their listening is spread: {ps[0]['half']} songs make half of Harry Styles's streams and {max(p['half'] for p in ps)} of {NAME[max(ps, key=lambda p: p['half'])['slug']]}'s, with BTS and Bad Bunny close behind, fan bases that play albums and catalogues rather than singles. Czechia's place follows language: for the three English-language artists it sits near the middle of the ranking ({", ".join(f"{p['cz_rank']}th of {p['ranked']}" for p in english)}), for BTS and Bad Bunny well below it. And nearly every show sold out for every artist, so the series cannot say where demand ends; what it can say is that the same dollar price weighed several times more on fans in South-East Asia and Latin America than in Europe or North America.</p>
</section>

<section id="related">
<h2>Related</h2>
<p><a href="concert-effect">Does a concert move the charts?</a>: a registered difference-in-differences that uses Spotify's daily charts to ask whether Harry Styles's first tour raised his share of each country's chart after he played there. The show week lifted it by about three quarters, and within three weeks the lift was gone. It is a separate study, not a part of the series.</p>
</section>

<section>
<h2>How the series was registered</h2>
<p>Part 1 was designed first, on 1 October 2026, before any chart day or ticket count was collected (<code>cecad1c</code>). The design for parts 2–5 and two questions added to all five followed the same evening, before any data were parsed (<code>e890c27</code>, <code>12417ae</code>). The data were collected once, for all parts, and each part's results were computed from the same files with the same code. Part 2's study of prices during the Eras Tour has its own design, committed before any price index was downloaded (<code>f5d702c</code>). Changes after registration, including two data definitions added once results had been seen, are dated in the series design and in each part. Commit times are self-reported; there was no external review.</p>
</section>

<section id="data">
<h2>Data and code</h2>
<p>Every part reads the same sources: kworb.net's totals of Spotify's global and national charts and its artist pages, the Wikipedia articles of the artists' tours with Billboard's Boxscore figures, and the World Bank's GDP per capita; part 2 adds Eurostat's harmonised price indices. The scripts in <code>tools/pop/</code> collect, parse, analyse and draw every part, and each article's numbers are filled in from its published results file.</p>
<div class="tw">
<table class="ht">
<thead><tr><th>Part</th><th>Results</th><th>Rows</th></tr></thead>
<tbody>
{chr(10).join(f'<tr><td>{k} · {NAME[slug]}</td><td><a href="../assets/pop/{slug}/results.json"><code>results.json</code></a></td><td><a href="../assets/pop/{slug}/ones.csv"><code>ones.csv</code></a> · <a href="../assets/pop/{slug}/countries.csv"><code>countries.csv</code></a> · <a href="../assets/pop/{slug}/songs.csv"><code>songs.csv</code></a> · <a href="../assets/pop/{slug}/tour.csv"><code>tour.csv</code></a></td></tr>' for slug, k, *_ in PARTS)}
</tbody>
</table>
</div>
</section>

<section id="changelog" class="changelog">
<h2>Change log</h2>
<ul>
<li>2 October 2026: version 1 published as the series hub.</li>
<li>Checked against editorial standard v1 on 2 October 2026.</li>
</ul>
</section>

<footer class="text-foot">
  <p class="back"><a href="../#works">← projects</a></p>
</footer>
</article>
</body>
</html>
'''
    (ROOT / "texts" / "pop-measured.html").write_text(head + "\n</head>\n" + body, encoding="utf-8")
    print("written texts/pop-measured.html")


if __name__ == "__main__":
    main()
