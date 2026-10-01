"""Pop, measured: fill a part's article template with the numbers from its results, so no figure is retyped.

Reads tools/pop/templates/<slug>.html and docs/research/<slug>-results.json (plus the part's CSVs) and writes
texts/pop-<slug>.html. A template names a value as {{key}}; a key that is not computed here stops the build.

    python3 tools/pop/article.py harry-styles
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
RAW = ROOT / "tools" / "data" / "pop" / "raw"
NB = " "


def n(v: float, dp: int = 0) -> str:
    """A number in the site's style: thin space between thousands, a real minus."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 else "") + s


def pct(v: float, dp: int = 0) -> str:
    return f"{n(100 * v, dp)} %"


def rows(name: str) -> list[dict]:
    with open(R / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def values(slug: str) -> dict:
    res = json.loads((R / f"{slug}-results.json").read_text())
    q1, q2, q3, q4, q5 = (res[k] for k in ("q1", "q2", "q3", "q4", "q5"))
    v: dict[str, str] = {}
    focal = next(p for p in q1["own"] if p["focal"])
    v |= {"q1_n": n(q1["n_number_ones"]), "q1_excluded": n(q1["excluded_before_2017"]), "q1_censored": n(q1["censored"]),
          "q1_median": n(q1["median_days"]), "focal_title": focal["label"].split(" - ", 1)[1], "focal_days": n(focal["days"]),
          "focal_longer": pct(focal["share_longer"], 1), "focal_lo": pct(focal["ci95"][0], 1), "focal_hi": pct(focal["ci95"][1], 1),
          "focal_one_in": n(round(1 / focal["share_longer"]))}
    surv = lambda t: next((v_ for d_, v_ in q1["curve"] if d_ >= t), q1["curve"][-1][1])
    v |= {"s730": pct(surv(730)), "s1000": pct(surv(1000))}
    others = [p for p in q1["own"] if not p["focal"]]
    v["other_ones"] = "; ".join(f"<i>{p['label'].split(' - ', 1)[1]}</i>, {n(p['days'])} days ({pct(p['share_longer'])} of number ones lasted longer)"
                                for p in others) or "none"
    cs = q2["countries"]
    cz = q2["czechia"]
    v |= {"q2_countries": n(len(cs)), "q2_ranked": n(q2["n_ranked"]), "q2_above": n(sum(c["ratio"] > 1 for c in cs)),
          "q2_median_ratio": n(sorted(c["ratio"] for c in cs)[len(cs) // 2], 1),
          "cz_days": n(cz["days"]), "cz_median": n(cz["median_ones_days"]), "cz_ratio": n(cz["ratio"], 1),
          "cz_lo": n(cz["ci95"][0], 1), "cz_hi": n(cz["ci95"][1], 1), "cz_rank": n(cz["rank"]), "cz_rank_days": n(cz["rank_by_days_post_hoc"]),
          "q2_still": n(sum(c["still_charting"] for c in cs))}
    by_days = sorted(cs, key=lambda c: c["rank_by_days_post_hoc"])
    name = {"ae": "the United Arab Emirates", "au": "Australia", "sg": "Singapore", "be": "Belgium", "gb": "the United Kingdom",
            "nz": "New Zealand", "ch": "Switzerland", "ie": "Ireland", "jp": "Japan", "tr": "Turkey", "lu": "Luxembourg",
            "is": "Iceland", "lv": "Latvia", "lt": "Lithuania", "ee": "Estonia"}
    v["q2_top_days"] = ", ".join(f"{name.get(c['country'], c['country'].upper())} ({n(c['days'])})" for c in by_days[:3])
    ranked = [c for c in cs if c["ranked"]]
    second = ranked[1:4]
    v["q2_top_ratio"] = ", ".join(f"{name.get(c['country'], c['country'].upper())} ({n(c['ratio'], 1)}×)" for c in second)
    cc = {c["country"]: c for c in cs}
    for k in ("lv", "lt", "ee", "sk", "mx", "jp"):
        v |= {f"{k}_ratio": n(cc[k]["ratio"], 1), f"{k}_days": n(cc[k]["days"]), f"{k}_median": n(cc[k]["median_ones_days"]),
              f"{k}_rank": n(cc[k]["rank"])}
    lu = next(c for c in cs if c["country"] == "lu")
    v |= {"lu_ratio": n(lu["ratio"]), "lu_median": n(lu["median_ones_days"]), "lu_ones": n(lu["ones"])}
    low = sorted(cs, key=lambda c: c["ratio"])[:2]
    v["q2_low"] = " and ".join(f"{name.get(c['country'], c['country'].upper())} ({n(c['ratio'], 2)}×, {n(c['days'])} days against a median of {n(c['median_ones_days'])})" for c in low)

    tour = rows(f"{slug}-tour.csv")
    longest = max(tour, key=lambda t: int(t["nights"]))
    least = min(tour, key=lambda t: int(t["sold"]) / int(t["available"]))
    v |= {"q3_entries": n(q3["entries"]), "q3_shows": n(q3["shows"]), "q3_sold_out": pct(q3["share_sold_out"]),
          "q3_rho": n(q3["spearman_rho"], 2), "q3_lo": n(q3["ci95"][0], 2), "q3_hi": n(q3["ci95"][1], 2),
          "q3_min": pct(q3["sell_through_min"]), "q3_rev_night": n(q3["revenue_per_night_median_usd"] / 1e6, 2),
          "long_venue": longest["venue"], "long_city": longest["city"], "long_nights": n(int(longest["nights"])),
          "long_sold": n(int(longest["sold"])), "least_city": least["city"], "least_tour": least["tour"],
          "q3_tours": " and ".join(f"<i>{t}</i>" for t in q3["tours"])}
    v |= {"q4_songs": n(q4["songs"]), "q4_top": q4["top_song"], "q4_top_share": pct(q4["top_share"]),
          "q4_top3": pct(q4["top3_share"]), "q4_gini": n(q4["gini"], 2)}
    songs = rows(f"{slug}-songs.csv")
    v |= {"q4_second": songs[1]["title"], "q4_third": songs[2]["title"],
          "q4_second_share": pct(int(songs[1]["streams"]) / sum(int(s["streams"]) for s in songs))}
    t5 = q5["countries"]
    get = lambda name_: next(c for c in t5 if c["country"] == name_)
    v |= {"q5_countries": n(len(t5)), "q5_entries": n(q5["entries_used"]),
          "q5_top": t5[0]["country"], "q5_top_days": n(t5[0]["days_of_income"], 1), "q5_top_price": n(t5[0]["price_usd"]),
          "q5_second": t5[1]["country"], "q5_second_days": n(t5[1]["days_of_income"], 1),
          "q5_last": t5[-1]["country"], "q5_last_days": n(t5[-1]["days_of_income"], 2), "q5_last_price": n(t5[-1]["price_usd"]),
          "us_price": n(get("United States")["price_usd"]), "us_days": n(get("United States")["days_of_income"], 1),
          "pl_price": n(get("Poland")["price_usd"]), "pl_days": n(get("Poland")["days_of_income"], 1),
          "cz_price": n(get("Czech Republic")["price_usd"]), "cz_tdays": n(get("Czech Republic")["days_of_income"], 1),
          "dear": max(t5, key=lambda c: c["price_usd"])["country"], "dear_price": n(max(c["price_usd"] for c in t5)),
          "cheap": min(t5, key=lambda c: c["price_usd"])["country"], "cheap_price": n(min(c["price_usd"] for c in t5)),
          "q5_price_x": n(max(c["price_usd"] for c in t5) / min(c["price_usd"] for c in t5), 1),
          "q5_days_x": n(t5[0]["days_of_income"] / t5[-1]["days_of_income"]),
          "q5_over2": n(sum(c["days_of_income"] > 2 for c in t5)), "q5_under1": n(sum(c["days_of_income"] < 1 for c in t5))}
    prague = next(t for t in tour if t["country"] == "Czech Republic")
    v |= {"prague_venue": prague["venue"], "prague_date": f"{prague['first_date']} {prague['year']}", "prague_sold": n(int(prague["sold"])),
          "prague_rev": n(int(prague["revenue_usd"]))}
    photo = next(p for p in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if p["slug"] == f"pop-{slug}")
    v["photo"] = (f'<section class="film film-page"><div class="shot" style="view-transition-name:ph-pop-{slug};'
                  f'--bg:url(../assets/photo/pop-{slug}.jpg);--bg-s:url(../assets/photo/pop-{slug}-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, toned</p></section>')
    meta = json.loads((RAW / "collected.json").read_text())
    v |= {"kworb_date": "1 October 2026" if meta["date"] == "2026-10-01" else meta["date"], "kworb_charts": n(len(meta["countries"]))}
    for key, page in (("rev_lot", "love-on-tour"), ("rev_lot2018", "harry-styles-live-on-tour")):
        v[key] = str(json.loads((RAW / "wiki" / f"{page}.json").read_text())["parse"]["revid"])
    return v


def main(slug: str) -> None:
    template = (Path(__file__).with_name("templates") / f"{slug}.html").read_text(encoding="utf-8")
    v = values(slug)
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", template)) - set(v))
    if missing:
        sys.exit(f"keys not computed: {missing}")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: v[m.group(1)], template)
    (ROOT / "texts" / f"pop-{slug}.html").write_text(out, encoding="utf-8")
    print("written", f"texts/pop-{slug}.html", f"{len(re.sub(r'<[^>]+>', ' ', out).split())} words in the page")


if __name__ == "__main__":
    main(sys.argv[1])
