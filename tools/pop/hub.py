"""Pop, measured: the series hub, texts/pop-measured.html, with every number read from the parts' results.

The page keeps the layout of the Prague, measured hub (its head and styles are copied from texts/prague-measured.html)
and adds the comparison across parts that the series design promises (§3, §4): the focal songs' places with intervals,
the top five countries, Czechia's place, the top song's share and Gini, the share of sold-out entries and the dearest ticket.

    python3 tools/pop/hub.py
"""

from __future__ import annotations

import json
import re
from math import exp
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


def country_names() -> dict:
    """The country names of tools/pop/figures.py, read without importing matplotlib."""
    import ast
    tree = ast.parse((ROOT / "tools" / "pop" / "figures.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "COUNTRY":
            return ast.literal_eval(node.value)
    return {}


COUNTRY = country_names()
LIST_CAP = 500  # the kworb artist page lists at most this many songs (part 2, Taylor Swift)


def part(slug: str) -> dict:
    r = json.loads((R / f"{slug}-results.json").read_text())
    focal = next(p for p in r["q1"]["own"] if p["focal"])
    cz = r["q2"]["czechia"]
    t5 = r["q5"].get("countries", [])
    top5 = sorted((c for c in r["q2"]["countries"] if c.get("ranked")), key=lambda c: c["rank"])[:5]
    return {"slug": slug, "focal": focal["label"].split(" - ", 1)[1], "days": focal["days"], "still": focal["still_charting"],
            "longer": focal["share_longer"], "lo": focal["ci95"][0], "hi": focal["ci95"][1],
            "peak": 2 if slug == "taylor-swift" else 1, "cz_ratio": cz["ratio"], "cz_rank": cz["rank"],
            "ranked": r["q2"]["n_ranked"], "above": sum(c["ratio"] > 1 for c in r["q2"]["countries"]),
            "countries": len(r["q2"]["countries"]), "songs": r["q4"]["songs"], "gini": r["q4"]["gini"],
            "top_share": r["q4"]["top_share"], "sold_out": r["q3"]["share_sold_out"], "entries": r["q3"]["entries"],
            "top5": [COUNTRY.get(c["country"], c["country"].upper()) for c in top5],
            "top_ticket": t5[0] if t5 else None, "n_t": len(t5)}


def summary(p: dict) -> str:
    s = (f"<i>{p['focal']}</i> spent {n(p['days'])} days in Spotify's global Top 200{' and is still there' if p['still'] else ''}; "
         f"{pct(p['longer'], 1)} of {'number ones' if p['peak'] == 1 else 'songs that also peaked at two'} since 2017 lasted longer "
         f"(95 % CI {pct(p['lo'], 1)} to {pct(p['hi'], 1)}). It outlasted the local median number one in {p['above']} of "
         f"{p['countries']} national charts; in Czechia it lasted {n(p['cz_ratio'], 2)} times as long, {p['cz_rank']}th of {p['ranked']}. "
         f"{pct(p['sold_out'])} of {p['entries']} Boxscore entries sold out")
    if p["top_ticket"]:
        s += (f", and the dearest ticket relative to income was in {p['top_ticket']['country']}, "
              f"{n(p['top_ticket']['days_of_income'], 1)} days of GDP per capita.")
    else:
        s += "."
    return s


def main() -> None:
    src = (ROOT / "texts" / "prague-measured.html").read_text(encoding="utf-8")
    head = src[:src.index("</style>") + len("</style>")]
    head = re.sub(r"<title>.*?</title>", "<title>Pop, measured · Barbora Šandová</title>", head)
    head = head.replace("</style>", ".minis{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px 24px;margin:1rem 0 0}"
                        ".minis figure{margin:0}.minis img{display:block;width:100%;height:auto}"
                        ".minis figcaption{font:400 12px var(--mono);color:#666;margin-top:4px}\n</style>")
    head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="Five pre-specified studies of five artists on Spotify\'s charts and on tour, asking the same five questions, with a comparison across them.">', head)
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
        f"<tr><td>{k} · {NAME[p['slug']]}</td><td><i>{p['focal']}</i></td><td class=\"v\">{pct(p['longer'], 1)} [{n(100 * p['lo'], 1)}–{n(100 * p['hi'], 1)}]</td>"
        f"<td>{', '.join(p['top5'])}</td>"
        f"<td class=\"v\">{n(p['cz_ratio'], 2)}× · {p['cz_rank']}/{p['ranked']}</td><td class=\"v\">{pct(p['top_share'], 1)} · {p['gini']:.2f} · {p['songs']}{'*' if p['songs'] >= LIST_CAP else ''}</td>"
        f"<td class=\"v\">{pct(p['sold_out'])}</td><td class=\"v\">"
        + (f"{n(p['top_ticket']['days_of_income'], 1)} · {p['top_ticket']['country']}" if p["top_ticket"] else "–") + "</td></tr>"
        for (slug, k, *_), p in zip(PARTS, ps))
    english = [p for p in ps if p["slug"] in ("harry-styles", "taylor-swift", "billie-eilish")]
    other = [p for p in ps if p not in english]
    so_lo, so_hi = min(p["sold_out"] for p in ps), max(p["sold_out"] for p in ps)
    t6 = json.loads((R / "pop-measured-part6-results.json").read_text())
    m1, m2, m1b, wsc = t6["m1"], t6["m2"], t6["m1b"], t6["m1_checks"]["without_still_charting"]
    zero = [NAME[a] for a, e in t6["m2c"].items() if e["lo"] < 0 < e["hi"]]
    wide = ", ".join(zero[:-1]) + " and " + zero[-1] if len(zero) > 1 else "".join(zero)
    items.append(f'''  <li>
    <a class="still" href="pop-together" aria-label="Part 6, the five together"><span class="shot" style="view-transition-name:ph-pop-together;--bg:url(../assets/photo/pop-together.jpg);--bg-s:url(../assets/photo/pop-together-1200.jpg)"></span></a>
    <div>
      <p class="n">Part 6 · all five artists · two exploratory models</p>
      <h2><a href="pop-together">Hits charted longer where the language matched, and tickets barely followed income</a></h2>
      <p>Across the {m1["n"]} artist–country pairs where the focal song charted (pairs where it never charted are left out), comparing each country with itself across artists and each artist with itself across countries, a song lasted {1 + m1["pct"]:.1f} times as long in a country speaking its language (95 % CI {1 + m1["pct_lo"]:.1f}–{1 + m1["pct_hi"]:.1f}): about {exp(m1b["en"]["coef"]):.1f} times for English songs ({m1b["en"]["pairs"]} matched pairs; {exp(m1b["en"]["lo"]):.2f}–{exp(m1b["en"]["hi"]):.2f}) and {exp(m1b["es"]["coef"]):.1f} for Spanish ones ({m1b["es"]["pairs"]}; {exp(m1b["es"]["lo"]):.1f}–{exp(m1b["es"]["hi"]):.1f}), and {1 + wsc["pct"]:.1f} times ({1 + wsc["pct_lo"]:.1f}–{1 + wsc["pct_hi"]:.1f}) without the songs still charting. Across {m2["n"]} tour entries, the average ticket rose with the host country's income at an elasticity of {m2["coef"]:.2f} ({m2["lo"]:.2f} to {m2["hi"]:.2f}; 0 means one price everywhere, 1 prices in proportion to income), {t6["m2_drop_artist"]["bad-bunny"]:.2f} without Bad Bunny, and with intervals that include zero for {wide} alone; so a show cost more days of income in poorer countries. Exploratory: models fixed before estimation, inputs seen in parts 1–5.</p>
    </div>
  </li>''')
    maps = "".join(f'<figure class="mini" data-pop="map" data-src="../assets/pop/{slug}/map.svg"><a href="pop-{slug}"><img src="../assets/pop/{slug}/map.svg" alt="World map for {NAME[slug]}: where the focal song lasted longer than local number ones, and ticket prices in days of income." loading="lazy"></a><figcaption>{NAME[slug]}</figcaption></figure>'
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
    <li>Every part answers the same questions from one data collection, under analysis plans written before the analysis was run (the author had worked with the data since March 2026); two data definitions and one extra collection were added after the first results.</li>
    <li>Harry Styles's top song carries {pct(ps[0]['top_share'])} of his Spotify streams, the most of the five (the others {n(100 * min(p['top_share'] for p in ps[1:]))}–{pct(max(p['top_share'] for p in ps[1:]))}); by the Gini, Taylor Swift's and BTS's listening is the most unequal across their longer song lists.</li>
    <li>In Czechia, the focal songs of Harry Styles, Taylor Swift and Billie Eilish sit near the middle of the world ranking and those of BTS (<i>Dynamite</i>, sung in English) and Bad Bunny well below it; with five songs this is a pattern, not a test.</li>
    <li>For every artist, {n(100 * so_lo)}–{pct(so_hi)} of Boxscore entries sold at least 99.5 % of their tickets, so the data cannot say where demand ends. In the exploratory part 6, ticket prices rose only a little with income, so a ticket cost more days of income in poorer countries.</li>
    <li>All of it rests on Spotify's charts (no Korean services, no YouTube) and the Boxscore figures on Wikipedia, for five artists chosen for the series rather than sampled; no pattern across artists is tested.</li>
  </ul>
</details>

<dl class="meta">
  <div><dt>published</dt><dd>2 October 2026 · updated 6 October 2026 · <a href="../changelog/#pop-measured">version 3</a></dd></div>
  <div><dt>work since</dt><dd>March 2026</dd></div>
</dl>
<details class="meta-more">
  <summary>About this series</summary>
<dl class="meta">
  <div><dt>status</dt><dd>hub, index of six research articles and one related study</dd></div>
  <div><dt>data</dt><dd>kworb.net Spotify chart totals, Wikipedia tour articles (Boxscore), World Bank GDP per capita, Eurostat HICP; hashes in <a href="https://github.com/sandovabarbora/bsandova.com/blob/main/docs/research/pop-measured-files.sha256">pop-measured-files.sha256</a></dd></div>
  <div><dt>code</dt><dd><a href="https://github.com/sandovabarbora/bsandova.com/tree/main/tools/pop">tools/pop/</a>, the same scripts for every part; this page is built by <code>tools/pop/hub.py</code></dd></div>
  <div><dt>cite as</dt><dd>Šandová, B. (2026). <i>Pop, measured</i>. bsandova.com/texts/pop-measured, version 3.</dd></div>
  <div><dt>licence</dt><dd>code MIT; text, figures and data CC BY 4.0</dd></div>
</dl>
</details>

<section class="series">
<h2>The parts</h2>
<p>Each part's focal song is the artist's most-streamed song on kworb's totals of Spotify's global chart, chosen by that rule. "Lasted longer" is the share of songs with the same global peak since 2017 that spent more days in the global Top 200, with songs still charting counted as lasting at least their days so far (Kaplan–Meier); the 95 % CI comes from 2 000 bootstrap resamples. A country's ratio is the focal song's days in its national chart divided by the median days of that country's own number ones. A Boxscore entry is one venue, for one night or a run, as Billboard reported it and Wikipedia lists it; it counts as sold out at 99.5 % of tickets sold or more.</p>
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
<p>The series design fixed one comparison in advance: the focal songs' places with their intervals, each artist's top five countries, and the share of sold-out entries, side by side, with no test across artists; a later addition to the design put Czechia's place beside them. The table adds two registered measures of how much one song carries (the top song's share; the Gini over all songs listed, 0 for equal streams, near 1 for one song) and the dearest ticket in days of income. Taylor Swift's focal song peaked at two, so its place is among songs that peaked at two, not among number ones.</p>
<div class="tw">
<table class="ht">
<thead><tr><th>Part</th><th>Focal song</th><th>Lasted longer [95 % CI]</th><th>Top five countries, by ratio</th><th>Czechia, ratio · rank</th><th>Top song's share · Gini · songs listed</th><th>Entries sold out</th><th>Dearest ticket, days of income</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<p>* The artist page lists 500 songs and Taylor Swift has more, so her list may stop short of her catalogue. Every list counts versions, remixes and re-recordings as separate songs, as kworb lists them.</p>
<p>Three patterns stand out, none of them tested. Harry Styles's listening leans most on one song ({pct(ps[0]['top_share'], 1)} of his streams), while by the Gini Taylor Swift's ({ps[1]['gini']:.2f}) and BTS's ({ps[2]['gini']:.2f}) are the most unequal, across lists six to ten times as long as his. In Czechia, the three English-language artists' focal songs sit near the middle of the ranking ({", ".join(f"{p['cz_rank']}th of {p['ranked']}" for p in english)}), BTS's and Bad Bunny's well below it ({", ".join(f"{p['cz_rank']}th of {p['ranked']}" for p in other)}); since <i>Dynamite</i> is sung in English, the split is by artist rather than by the song's language, and five songs cannot say why. And for every artist nearly every Boxscore entry sold out, so the series cannot say where demand ends; what it can say, from the exploratory part 6, is that prices rose only a little with income, and for four of the five artists the dearest ticket in days of income was in South-East Asia or Latin America.</p>
</section>

<section id="related">
<h2>Related</h2>
<p><a href="concert-effect">Does a concert move the charts?</a>: a pre-specified difference-in-differences that uses Spotify's daily charts to ask whether Harry Styles's first tour raised his share of each country's chart after he played there. In the show week his chart share rose by about three quarters against countries not yet visited, and within three weeks the rise was gone; the registered five-week effect is inconclusive. It is a separate study, not a part of the series.</p>
</section>

<section>
<h2>How the series was registered</h2>
<p>Part 1's analysis plan was committed first, on 1 October 2026, before this analysis was run (<code>cecad1c</code>). The plan for parts 2–5 and two questions added to all five followed the same evening, also before the analysis was run (<code>e890c27</code>, <code>12417ae</code>). The author had worked with these data since March 2026; the plans set the analysis in advance; the author already knew the data. The data were collected once, for all parts (with one later addition, below), and each part's results were computed from the same files with the same code. Part 2's study of prices during the Eras Tour has its own analysis plan, committed before that analysis was run (<code>f5d702c</code>). Three changes were made after the first results of parts 2–5 had been seen, and are dated in the series design and in each part: two data definitions (attendance cells that span several venues, and entries that mix online viewers with the hall, both left out of the sell-out share) and one extra collection (the track pages of songs that peaked at two, Taylor Swift's reference set). Part 6 has its own design, committed before either model was estimated but after its inputs had been seen, so it is exploratory (<code>4fe0484</code>). Commit times are self-reported; there was no external review.</p>
</section>

<section id="data">
<h2>Data and code</h2>
<p>Every part reads the same sources: kworb.net's totals of Spotify's global and national charts and its artist pages (<a href="https://kworb.net/spotify/">kworb.net/spotify</a>, accessed 1 October 2026); the English Wikipedia articles of the artists' tours with Billboard's Boxscore figures, at the revisions listed in each part's references (accessed 1 October 2026); and the World Bank's GDP per capita, current US$, <code>NY.GDP.PCAP.CD</code> (<a href="https://data.worldbank.org/indicator/NY.GDP.PCAP.CD">data.worldbank.org</a>, accessed 1 October 2026). Part 2 adds Eurostat's harmonised price indices, <code>prc_hicp_midx</code> (<a href="https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_midx/default/table">ec.europa.eu/eurostat</a>, accessed 2 October 2026). The scripts in <code>tools/pop/</code> collect, parse, analyse and draw every part, and each article's numbers are filled in from its published results file.</p>
<div class="tw">
<table class="ht">
<thead><tr><th>Part</th><th>Results</th><th>Rows</th></tr></thead>
<tbody>
{chr(10).join(f'<tr><td>{k} · {NAME[slug]}</td><td><a href="../assets/pop/{slug}/results.json"><code>results.json</code></a></td><td><a href="../assets/pop/{slug}/ones.csv"><code>ones.csv</code></a> · <a href="../assets/pop/{slug}/countries.csv"><code>countries.csv</code></a> · <a href="../assets/pop/{slug}/songs.csv"><code>songs.csv</code></a> · <a href="../assets/pop/{slug}/tour.csv"><code>tour.csv</code></a></td></tr>' for slug, k, *_ in PARTS)}
</tbody>
</table>
</div>
</section>


<footer class="text-foot">
  <p class="back"><a href="../#works">← projects</a></p>
</footer>
</article>
<script src="../assets/pop/pop.js" defer></script>
</body>
</html>
'''
    (ROOT / "texts" / "pop-measured.html").write_text(head + "\n</head>\n" + body, encoding="utf-8")
    print("written texts/pop-measured.html")


if __name__ == "__main__":
    main()
