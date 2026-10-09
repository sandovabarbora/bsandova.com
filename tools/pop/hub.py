"""Pop, measured: the series hub, texts/pop-measured.html, with every number read from the parts' results.

The page keeps the layout of the Prague, measured hub (its head and styles, taken from texts/prague-measured.html, are in
tools/pop/hub.template.html) and adds the comparison across parts that the series design promises (§3, §4): the focal songs' places with intervals,
the top five countries, Czechia's place, the top song's share and Gini, the share of sold-out entries and the dearest ticket.

    python3 tools/pop/hub.py
"""

from __future__ import annotations

import json
import re
import sys
from math import exp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import part_item, render  # noqa: E402
R = ROOT / "docs" / "research"
NB = " "
PARTS = [  # slug, part number, title on the part's page, what the part is about
    ("harry-styles", 1, "Harry Styles, measured: how long a hit lasts, where, and what a ticket costs",
     "Spotify charts 2017–2026 · two tours, 2017–2023"),
    ("taylor-swift", 2, "Taylor Swift, measured: chart runs, tour attendance and prices around the Eras Tour",
     "Spotify charts 2017–2026 · two stadium tours · Europe's prices in 2024"),
    ("bts", 3, "BTS, measured: Dynamite, and streams spread over hundreds of songs", "Spotify charts 2017–2026 · three tours, 2018–2026"),
    ("bad-bunny", 4, "Bad Bunny, measured: a long-running hit, and tickets in days of income", "Spotify charts 2017–2026 · five tours, 2019–2026"),
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


def page_title(slug: str, fallback: str) -> str:
    """The part's current title, read from its built page, so a retitled part is listed under its new title."""
    page = ROOT / "texts" / f"pop-{slug}.html"
    m = re.search(r'<meta property="og:title" content="([^"]*)">', page.read_text(encoding="utf-8")) if page.exists() else None
    return m.group(1).replace("&#39;", "'") if m else fallback


def eras_entries() -> int:
    """Taylor Swift's Q3 entries from the Eras Tour, whose figures on Wikipedia are reported capacity or attendance."""
    import csv
    with open(R / "taylor-swift-tour.csv", encoding="utf-8") as f:
        return sum(1 for t in csv.DictReader(f) if t["tour"] == "The Eras Tour"
                   and t.get("multi_venue") != "True" and t.get("hybrid") != "True")


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
         + (f"{pct(p['sold_out'])} of {p['entries']} tour entries were reported sold out ({eras_entries()} of them Eras Tour figures, "
            "reported capacity or attendance rather than Boxscore tickets sold)" if p["slug"] == "taylor-swift"
            else f"{pct(p['sold_out'])} of {p['entries']} Boxscore entries sold out"))
    if p["top_ticket"]:
        s += (f", and the dearest ticket relative to income was in {p['top_ticket']['country']}, "
              f"{n(p['top_ticket']['days_of_income'], 1)} days of GDP per capita"
              + (" (Reputation Stadium Tour only: the Eras Tour has no gross on Wikipedia)." if p["slug"] == "taylor-swift" else "."))
    else:
        s += "."
    return s


def main() -> None:
    PARTS[:] = [(slug, k, page_title(slug, title), what) for slug, k, title, what in PARTS]
    ps = [part(s) for s, *_ in PARTS]
    items = [part_item(f"pop-{slug}", k, title, f"Part {k} · {NAME[slug]} · {what}", summary(p))
             for (slug, k, title, what), p in zip(PARTS, ps)]
    rows = "\n".join(
        f"<tr><td>{k} · {NAME[p['slug']]}</td><td><i>{p['focal']}</i></td><td class=\"v\">{pct(p['longer'], 1)} [{n(100 * p['lo'], 1)}–{n(100 * p['hi'], 1)}]</td>"
        f"<td>{', '.join(p['top5'])}</td>"
        f"<td class=\"v\">{n(p['cz_ratio'], 2)}× · {p['cz_rank']}/{p['ranked']}</td><td class=\"v\">{pct(p['top_share'], 1)} · {p['gini']:.2f} · {p['songs']}{'*' if p['songs'] >= LIST_CAP else ''}</td>"
        f"<td class=\"v\">{pct(p['sold_out'])}</td><td class=\"v\">"
        + (f"{n(p['top_ticket']['days_of_income'], 1)} · {p['top_ticket']['country']}{' (Reputation only)' if p['slug'] == 'taylor-swift' else ''}" if p["top_ticket"] else "–") + "</td></tr>"
        for (slug, k, *_), p in zip(PARTS, ps))
    english = [p for p in ps if p["slug"] in ("harry-styles", "taylor-swift", "billie-eilish")]
    other = [p for p in ps if p not in english]
    so_lo, so_hi = min(p["sold_out"] for p in ps), max(p["sold_out"] for p in ps)
    t6 = json.loads((R / "pop-measured-part6-results.json").read_text())
    m1, m2, m1b, wsc = t6["m1"], t6["m2"], t6["m1b"], t6["m1_checks"]["without_still_charting"]
    dyn = t6["m1_checks"]["dynamite_as_english"]
    zero = [NAME[a] for a, e in t6["m2c"].items() if e["lo"] < 0 < e["hi"]]
    wide = ", ".join(zero[:-1]) + " and " + zero[-1] if len(zero) > 1 else "".join(zero)
    together = page_title("together", "Pop, measured, together").split(": ", 1)[-1]
    items.append(part_item("pop-together", 6, together[:1].upper() + together[1:], "Part 6 · all five artists · two exploratory models",
        f'''Across the {m1["n"]} artist–country pairs where the focal song charted (pairs where it never charted are left out), net of the country and the song, a song lasted {1 + m1["pct"]:.1f} times as long in a country speaking the language of its artist's market (95 % CI {1 + m1["pct_lo"]:.1f}–{1 + m1["pct_hi"]:.1f}), and {1 + dyn["pct"]:.1f} times ({1 + dyn["pct_lo"]:.1f}–{1 + dyn["pct_hi"]:.1f}) with BTS's <i>Dynamite</i> coded as English, the language it is sung in: about {exp(m1b["en"]["coef"]):.1f} times for English songs ({m1b["en"]["pairs"]} matched pairs; {exp(m1b["en"]["lo"]):.2f}–{exp(m1b["en"]["hi"]):.2f}) and {exp(m1b["es"]["coef"]):.1f} for Spanish ones ({m1b["es"]["pairs"]}; {exp(m1b["es"]["lo"]):.1f}–{exp(m1b["es"]["hi"]):.1f}), and {1 + wsc["pct"]:.1f} times ({1 + wsc["pct_lo"]:.1f}–{1 + wsc["pct_hi"]:.1f}) without the songs still charting. These are associations: song age, promotion and diaspora audiences are not separated from language, all Spanish pairs are Bad Bunny's and the one Korean pair is BTS's. Across {m2["n"]} tour entries, within a tour, the average ticket was {m2["coef"]:.2f} % higher in countries with 1 % higher GDP per capita, an elasticity of {m2["coef"]:.2f} ({m2["lo"]:.2f} to {m2["hi"]:.2f}; 0 means one price everywhere, 1 prices in proportion to income), {t6["m2_drop_artist"]["bad-bunny"]:.2f} without Bad Bunny, and with intervals that include zero for {wide} alone; so a show cost more days of income in poorer countries. Exploratory: models fixed before estimation, inputs seen in parts 1–5.''',
        label="the five together"))
    ce_r = json.loads((R / "concert-effect-results.json").read_text())["y1_share"]
    ce = ce_r["summary"]
    week0 = ce_r["event"][[e["e"] for e in ce_r["event"]].index(0)]
    v = {"parts": "\n".join(items), "rows": rows,
         "maps": "".join(f'<figure class="mini" data-pop="map" data-src="../assets/pop/{slug}/map.svg"><a href="pop-{slug}"><img src="../assets/pop/{slug}/map.svg" alt="World map for {NAME[slug]}: where the focal song lasted longer than local number ones, and ticket prices in days of income." loading="lazy"></a><figcaption>{NAME[slug]}</figcaption></figure>'
                         for slug, *_ in PARTS),
         "top1_share": pct(ps[0]["top_share"]), "top1_share_1dp": pct(ps[0]["top_share"], 1),
         "others_lo": n(100 * min(p["top_share"] for p in ps[1:])), "others_hi": pct(max(p["top_share"] for p in ps[1:])),
         "sold_lo": n(100 * so_lo), "sold_hi": pct(so_hi),
         "gini_ts": f"{ps[1]['gini']:.2f}", "gini_bts": f"{ps[2]['gini']:.2f}",
         "cz_english": ", ".join(f"{p['cz_rank']}th of {p['ranked']}" for p in english),
         "cz_other": ", ".join(f"{p['cz_rank']}th of {p['ranked']}" for p in other),
         "ce_att": n(ce["att"] * 100, 3), "ce_lo": n(ce["lo"] * 100, 3), "ce_hi": n(ce["hi"] * 100, 3),
         "ce_label": ce_r["label"], "ce_week": f"{week0['att'] * 100:.3f}",
         "data_rows": "\n".join(f'<tr><td>{k} · {NAME[slug]}</td><td><a href="../assets/pop/{slug}/results.json"><code>results.json</code></a></td><td><a href="../assets/pop/{slug}/ones.csv"><code>ones.csv</code></a> · <a href="../assets/pop/{slug}/countries.csv"><code>countries.csv</code></a> · <a href="../assets/pop/{slug}/songs.csv"><code>songs.csv</code></a> · <a href="../assets/pop/{slug}/tour.csv"><code>tour.csv</code></a></td></tr>' for slug, k, *_ in PARTS)}
    template = Path(__file__).with_name("hub.template.html").read_text(encoding="utf-8")
    (ROOT / "texts" / "pop-measured.html").write_text(render(template, v), encoding="utf-8")
    print("written texts/pop-measured.html")

if __name__ == "__main__":
    main()
