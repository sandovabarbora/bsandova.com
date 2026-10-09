"""Pop, measured: fill a part's article template with the numbers from its results, so no figure is retyped.

Reads tools/pop/templates/<slug>.html and docs/research/<slug>-results.json (plus the part's CSVs) and writes
texts/pop-<slug>.html. A template names a value as {{key}}; a key that is not computed here stops the build.

    python3 tools/pop/article.py harry-styles
"""

from __future__ import annotations

import csv
import json
import re
import statistics
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


def med(v: float) -> str:
    """A median of days: one decimal when it falls on a half day, so 678.5 and 359.5 are not rounded in opposite directions."""
    return n(v, 1) if v % 1 else n(v)


def ordinal(k: int) -> str:
    """1st, 2nd, 3rd, 4th, 11th, 21st, …"""
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


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
          "focal_one_in": n(round(1 / focal["share_longer"])), "focal_beat": pct(1 - focal["share_longer"]),
          "focal_still": "still in the chart" if focal["still_charting"] else "no longer in the chart"}
    # the Kaplan–Meier curve is a step function: S(t) is the value of the last step at or before t
    surv = lambda t: next((v_ for d_, v_ in reversed(q1["curve"]) if d_ <= t), 1.0)
    v |= {"s730": pct(surv(730)), "s1000": pct(surv(1000))}
    others = [p for p in q1["own"] if not p["focal"]]
    v["other_ones"] = "; ".join(f"<i>{p['label'].split(' - ', 1)[1]}</i>, {n(p['days'])} days ({pct(p['share_longer'])} of number ones lasted longer)"
                                for p in others) or "none"
    cs = q2["countries"]
    cz = q2["czechia"]
    v |= {"q2_countries": n(len(cs)), "q2_ranked": n(q2["n_ranked"]), "q2_above": n(sum(c["ratio"] > 1 for c in cs)), "q2_below": n(sum(c["ratio"] < 1 for c in cs)),
          "q2_median_ratio": n(statistics.median(c["ratio"] for c in cs), 1),
          "cz_days": n(cz["days"]), "cz_median": med(cz["median_ones_days"]), "cz_ratio": n(cz["ratio"], 1),
          "cz_lo": n(cz["ci95"][0], 1), "cz_hi": n(cz["ci95"][1], 1), "cz_rank": n(cz["rank"]), "cz_rank_days": n(cz["rank_by_days_post_hoc"]),
          "cz_rank_ord": ordinal(cz["rank"]), "cz_rank_days_ord": ordinal(cz["rank_by_days_post_hoc"]),
          "q2_still": n(sum(c["still_charting"] for c in cs))}
    by_days = sorted(cs, key=lambda c: c["rank_by_days_post_hoc"])
    name = {"ae": "the United Arab Emirates", "au": "Australia", "sg": "Singapore", "be": "Belgium", "gb": "the United Kingdom",
            "nz": "New Zealand", "ch": "Switzerland", "ie": "Ireland", "jp": "Japan", "tr": "Turkey", "lu": "Luxembourg",
            "is": "Iceland", "lv": "Latvia", "lt": "Lithuania", "ee": "Estonia"}
    v["q2_top_days"] = ", ".join(f"{name.get(c['country'], c['country'].upper())} ({n(c['days'])})" for c in by_days[:3])
    ranked = [c for c in cs if c["ranked"]]
    second = ranked[1:4]
    v["q2_top_ratio"] = ", ".join(f"{name.get(c['country'], c['country'].upper())} ({n(c['ratio'], 1)}×{', still charting, so a lower bound' if c['still_charting'] else ''})" for c in second)
    for c in cs:   # every country's values, so a template can name any of them: <cc>_ratio, <cc>_days, …
        k = c["country"]
        v |= {f"{k}_ratio": n(c["ratio"], 1 if c["ratio"] < 10 else 0), f"{k}_ratio2": n(c["ratio"], 2), f"{k}_days": n(c["days"]),
              f"{k}_median": med(c["median_ones_days"]), f"{k}_ones": n(c["ones"]), f"{k}_rank": n(c.get("rank", 0)),
              f"{k}_rank_days": n(c["rank_by_days_post_hoc"]), f"{k}_rank_ord": ordinal(c.get("rank", 0)),
              f"{k}_rank_days_ord": ordinal(c["rank_by_days_post_hoc"]),
              f"c_{k}_days": n(c["days"])}   # c_<cc>_days: chart days, which the Q5 us_days below does not overwrite
    low = sorted(cs, key=lambda c: c["ratio"])[:2]
    v["q2_low"] = " and ".join(f"{name.get(c['country'], c['country'].upper())} ({n(c['ratio'], 2)}×, {n(c['days'])} days against a median of {med(c['median_ones_days'])})" for c in low)

    tour = [t for t in rows(f"{slug}-tour.csv") if t.get("multi_venue") != "True" and t.get("hybrid") != "True"]
    if q3.get("answerable"):
        longest = max(tour, key=lambda t: int(t["nights"]))
        least = min(tour, key=lambda t: int(t["sold"]) / int(t["available"]))
        v |= {"q3_entries": n(q3["entries"]), "q3_shows": n(q3["shows"]), "q3_sold_out": pct(q3["share_sold_out"]),
              # with every entry sold out the correlation is undefined (no variation in the share sold)
              "q3_rho": n(q3["spearman_rho"], 2) if q3["spearman_rho"] is not None else "undefined",
              "q3_lo": n(q3["ci95"][0], 2) if q3["ci95"] else "", "q3_hi": n(q3["ci95"][1], 2) if q3["ci95"] else "",
              "q3_min": pct(q3["sell_through_min"]), "q3_rev_night": n(q3["revenue_per_night_median_usd"] / 1e6, 2),
              "long_venue": longest["venue"], "long_city": longest["city"].strip(), "long_nights": n(int(longest["nights"])),
              "long_runs": " and ".join(f'{t["venue"]} in {t["city"].strip()}' for t in tour if t["nights"] == longest["nights"]),
              "q3_rev_entries": n(sum(1 for t in tour if t["revenue_usd"])),
              "long_sold": n(int(longest["sold"])), "least_city": least["city"], "least_tour": least["tour"],
              "least_sold": n(int(least["sold"])), "least_avail": n(int(least["available"])), "least_year": least["year"],
              "q3_multi": n(q3.get("multi_venue_excluded", 0)), "q3_hybrid": n(q3.get("hybrid_excluded", 0)),
              "q3_tours": ", ".join(f"<i>{t}</i>" for t in q3["tours"][:-1]) + (" and " if len(q3["tours"]) > 1 else "") + f"<i>{q3['tours'][-1]}</i>"}
    v |= {"q4_songs": n(q4["songs"]), "q4_top": q4["top_song"], "q4_top_share": pct(q4["top_share"]),
          "q4_top3": pct(q4["top3_share"]), "q4_gini": n(q4["gini"], 2)}
    songs = rows(f"{slug}-songs.csv")
    total = sum(int(s["streams"]) for s in songs)
    cum, half = 0, 0
    for half, s_ in enumerate(songs, 1):
        cum += int(s_["streams"])
        if cum >= total / 2:
            break
    v |= {"q4_second": songs[1]["title"], "q4_third": songs[2]["title"],
          "q4_second_share": pct(int(songs[1]["streams"]) / total), "q4_half": n(half),
          "q4_over1": n(sum(int(s_["streams"]) / total >= 0.01 for s_ in songs))}
    if q3.get("answerable"):   # average price per ticket of each tour: tp_<tour slug>
        for name in q3["tours"]:
            es = [t for t in tour if t["tour"] == name and t["revenue_usd"]]
            if es:
                key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
                v[f"tp_{key}"] = n(sum(int(t["revenue_usd"]) for t in es) / sum(int(t["sold"]) for t in es))
    t5 = q5.get("countries", [])
    if t5:
        v |= {"q5_countries": n(len(t5)), "q5_entries": n(q5["entries_used"]),
              "q5_top": t5[0]["country"], "q5_top_days": n(t5[0]["days_of_income"], 1), "q5_top_price": n(t5[0]["price_usd"]),
              "q5_second": t5[1]["country"], "q5_second_days": n(t5[1]["days_of_income"], 1),
              "q5_last": t5[-1]["country"], "q5_last_days": n(t5[-1]["days_of_income"], 2), "q5_last_price": n(t5[-1]["price_usd"]),
              "dear": max(t5, key=lambda c: c["price_usd"])["country"], "dear_price": n(max(c["price_usd"] for c in t5)),
              "cheap": min(t5, key=lambda c: c["price_usd"])["country"], "cheap_price": n(min(c["price_usd"] for c in t5)),
              "q5_price_x": n(max(c["price_usd"] for c in t5) / min(c["price_usd"] for c in t5), 1),
              "q5_days_x": n(t5[0]["days_of_income"] / t5[-1]["days_of_income"]),
              "q5_over2": n(sum(c["days_of_income"] > 2 for c in t5)), "q5_under1": n(sum(c["days_of_income"] < 1 for c in t5))}
        for c in t5:   # t_<iso3>_price and t_<iso3>_days for every country
            v |= {f"t_{c['iso3'].lower()}_price": n(c["price_usd"]), f"t_{c['iso3'].lower()}_days": n(c["days_of_income"], 1)}
        v |= {"us_price": v.get("t_usa_price", ""), "us_days": v.get("t_usa_days", ""), "pl_price": v.get("t_pol_price", ""),
              "pl_days": v.get("t_pol_days", ""), "cz_price": v.get("t_cze_price", ""), "cz_tdays": v.get("t_cze_days", "")}
    prague = next((t for t in tour if t["country"] == "Czech Republic"), None)
    if prague:
        d = re.sub(r"^([A-Z][a-z]+) (\d{1,2})$", r"\2 \1", prague["first_date"].strip())   # "June 1" -> "1 June"
        v |= {"prague_venue": prague["venue"].replace("O 2", "O2"), "prague_date": f"{d} {prague['year']}",
              "prague_sold": n(int(prague["sold"])), "prague_rev": n(int(prague["revenue_usd"])) if prague["revenue_usd"] else ""}
    photo = next(p for p in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if p["slug"] == f"pop-{slug}")
    v["photo"] = (f'<section class="film film-page"><div class="shot" style="view-transition-name:ph-pop-{slug};'
                  f'--bg:url(../assets/photo/pop-{slug}.jpg);--bg-s:url(../assets/photo/pop-{slug}-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, toned</p></section>')
    meta = json.loads((RAW / "collected.json").read_text())
    v |= {"kworb_date": "1 October 2026" if meta["date"] == "2026-10-01" else meta["date"], "kworb_charts": n(len([c for c in meta["countries"] if c != "global"]))}   # national charts only
    for other in ("harry-styles", "taylor-swift", "bts", "bad-bunny", "billie-eilish"):   # Czechia across the series
        path = R / f"{other}-results.json"
        if path.exists():
            o = json.loads(path.read_text())
            key = other.replace("-", "_")
            c = o["q2"]["czechia"]
            v |= {f"s_{key}_cz_ratio": n(c["ratio"], 2), f"s_{key}_cz_rank": n(c["rank"]), f"s_{key}_n": n(o["q2"]["n_ranked"])}
            t = next((x for x in o["q5"].get("countries", []) if x["iso3"] == "CZE"), None)
            if t:
                v |= {f"s_{key}_cz_tdays": n(t["days_of_income"], 2), f"s_{key}_cz_tprice": n(t["price_usd"])}
    eras = R / "eras-inflation-results.json"
    if slug == "taylor-swift" and eras.exists():   # the Eras Tour price study, registered separately
        e = json.loads(eras.read_text())
        for k in ("accommodation", "restaurants", "all_items"):
            m = e[k]["month0"]
            v |= {f"e_{k}": n(m["att"], 2), f"e_{k}_lo": n(m["lo"], 2), f"e_{k}_hi": n(m["hi"], 2),
                  f"e_{k}_p": n(e[k]["permutation_p"], 2), f"e_{k}_label": e[k]["label"]}
        v |= {"e_countries": n(e["accommodation"]["countries"]), "e_treated": n(len(e["accommodation"]["treated"])),
              "e_never": n(e["never_treated_only"]["att"], 2), "e_placebo": n(e["placebo_2023"]["att"], 2),
              "e_placebo_lo": n(e["placebo_2023"]["lo"], 2), "e_placebo_hi": n(e["placebo_2023"]["hi"], 2),
              "e_loo_min": n(min(e["leave_one_out"].values()), 2), "e_loo_max": n(max(e["leave_one_out"].values()), 2),
              "e_at": n(e["austria_aug2024"]["yoy"], 1), "e_at_pct": n(100 * e["austria_aug2024"]["percentile_among_controls"]),
              "e_m1": n(next(r["att"] for r in e["accommodation"]["event"] if r["e"] == 1), 2)}
        after = [r for r in e["accommodation"]["event"] if r["e"] > 0]
        for r in after:   # e_acc_m<e>, _lo, _hi: accommodation, months +1 to +6 after the show
            v |= {f"e_acc_m{r['e']}": n(r["att"], 2), f"e_acc_m{r['e']}_lo": n(r["lo"], 2), f"e_acc_m{r['e']}_hi": n(r["hi"], 2)}
        v |= {"e_acc_after_neg": n(sum(r["att"] < 0 for r in after)), "e_acc_after_n": n(len(after)),
              "e_acc_after_zero": n(sum(r["lo"] <= 0 <= r["hi"] for r in after)),
              "e_hicp_geos": n(len({r["geo"] for r in rows("eras-inflation-hicp.csv")}))}
        pw = json.loads((R / "eras-inflation-pointwise.json").read_text())   # post-hoc pointwise intervals
        for k, short in (("accommodation", "acc"), ("restaurants", "res"), ("all_items", "all")):
            for r in pw[k]:   # e_pw_<short>_m<e>_lo / _hi, e.g. e_pw_acc_m0_lo; months before the show as m_4
                key = f"e_pw_{short}_m{r['e']}".replace("-", "_")
                v |= {f"{key}_lo": n(r["lo"], 2), f"{key}_hi": n(r["hi"], 2)}
        pre = [r for r in e["accommodation"]["event"] if -6 <= r["e"] <= -2 and not r["lo"] <= 0 <= r["hi"]]
        v |= {f"e_loo_{c.lower()}": n(x, 2) for c, x in e["leave_one_out"].items()}
        v["e_acc_pre_fail"] =", ".join(f"month {n(r['e'])}" for r in pre) or "none"
        p1 = json.loads((R / "taylor-swift-peak1-posthoc.json").read_text())   # post-hoc: her own number ones
        v["p1_n"] = n(p1["n_number_ones"])
        v["p1_count"] = n(len(p1["songs"]))
        v["p1_list"] = "; ".join(f"<i>{s['label'].split(' - ', 1)[1]}</i>, {n(s['days'])} days ({pct(s['share_longer'], 1)} lasted longer, 95 % CI {pct(s['ci95'][0], 1)} to {pct(s['ci95'][1], 1)}{', still charting' if s['still_charting'] else ''})"
                                 for s in p1["songs"][:4])
        tour_all = rows("taylor-swift-tour.csv")
        for t_, key in (("Reputation Stadium Tour", "rep"), ("The Eras Tour", "eras")):
            es = [t for t in tour_all if t["tour"] == t_]
            v |= {f"q3_{key}_entries": n(len(es)), f"q3_{key}_shows": n(sum(int(t["nights"]) for t in es))}
    artist = json.loads((Path(__file__).with_name("artists.json")).read_text(encoding="utf-8"))[slug]
    for name in artist["tours"]:   # rev_<tour slug>: the Wikipedia revision of each tour article
        key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        page = json.loads((RAW / "wiki" / f"{key}.json").read_text())
        if "parse" in page:
            v[f"rev_{key.replace('-', '_')}"] = str(page["parse"]["revid"])
    v |= {"rev_lot": v.get("rev_love_on_tour", ""), "rev_lot2018": v.get("rev_harry_styles_live_on_tour", "")}
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
