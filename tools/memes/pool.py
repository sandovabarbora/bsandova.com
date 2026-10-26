"""Builds the external reference pool of the falsification (design §1, §2) by a mechanical rule, from wikitext and page
existence only (MediaWiki API, no pageview numbers). The result is frozen in config.py; this module documents how and
is tested on made-up wikitext. Network use is limited to build(), which nothing else calls.

Rule, applied as written: shows in four Wikipedia categories (2010s and 2020s American multi-camera and single-camera
sitcoms) whose infobox network is ABC, CBS, NBC, Fox or The CW and whose infobox last_aired year is 2016 to 2021;
not animated; not Modern Family or The King of Queens, and not a show that lists any of their actors; not a show with
a starring actor whose article gives a 2023 death date. Candidates are the links of the infobox `starring` field.
Titles that are missing, redirects or disambiguation pages are dropped, never replaced. The pool is capped at CAP
actors in round-robin order: the first-billed actor of each show, then the second, and so on, shows in alphabetical order.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from collections.abc import Iterable, Sequence

import fetch as F

CATEGORIES = ("2010s American multi-camera sitcoms", "2010s American single-camera sitcoms",
              "2020s American multi-camera sitcoms", "2020s American single-camera sitcoms")
RUN_ENDED = (2016, 2021)
CAP = 36
EXCLUDED_SHOWS = ("Modern Family", "The King of Queens")
NETWORK = re.compile(r"American Broadcasting Company|\bABC\b|\bCBS\b|\bNBC\b|Fox Broadcasting|\[\[Fox\b|The CW|\bCW\b")


def field(wikitext: str, name: str) -> str:
    m = re.search(rf"\n\|\s*{name}\s*=(.*?)(?=\n\|\s*\w+\s*=|\n\}}\}})", wikitext, flags=re.DOTALL)
    return m.group(1) if m else ""


def starring_links(wikitext: str) -> list[str]:
    out = []
    for target in re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", field(wikitext, "starring")):
        title = target.strip().replace(" ", "_")
        if not re.match(r"(File|Image|Category):", title, flags=re.IGNORECASE) and title not in out:
            out.append(title)
    return out


def end_year(wikitext: str) -> int | None:
    m = re.search(r"(\d{4})", field(wikitext, "last_aired"))
    return int(m.group(1)) if m else None


def on_big_network(wikitext: str) -> bool:
    return bool(NETWORK.search(field(wikitext, "network")))


def is_animated(wikitext: str) -> bool:
    return bool(re.search(r"\[\[Category:[^\]]*animated", wikitext, flags=re.IGNORECASE))


def death_year(wikitext: str) -> int | None:
    m = re.search(r"death_date\s*=\s*\{\{[^}]*?(\d{4})", wikitext)
    return int(m.group(1)) if m else None


def round_robin(show_actors: dict[str, list[str]], cap: int = CAP) -> list[str]:
    shows = sorted(show_actors)
    out: list[str] = []
    for rank in range(max((len(v) for v in show_actors.values()), default=0)):
        for s in shows:
            if rank < len(show_actors[s]) and show_actors[s][rank] not in out:
                out.append(show_actors[s][rank])
                if len(out) == cap:
                    return out
    return out


def _api(**params) -> dict:
    params.update(format="json", formatversion="2")
    return json.loads(F._get(f"{F.MEDIAWIKI}?{urllib.parse.urlencode(params)}", 3))


def _wikitext(titles: Sequence[str]) -> dict[str, str]:
    out = {}
    for i in range(0, len(titles), 20):
        d = _api(action="query", titles="|".join(t.replace("_", " ") for t in titles[i:i + 20]), prop="revisions",
                 rvprop="content", rvslots="main", redirects=1)
        for p in d["query"]["pages"]:
            if "revisions" in p:
                out[p["title"].replace(" ", "_")] = p["revisions"][0]["slots"]["main"]["content"]
    return out


def build(excluded_actors: Iterable[str] = ()) -> dict:
    base = _wikitext([t.replace(" ", "_") for t in EXCLUDED_SHOWS])
    excluded = set(excluded_actors) | {a for wt in base.values() for a in starring_links(wt)}
    members: set[str] = set()
    for cat in CATEGORIES:
        cont: dict = {}
        while True:
            d = _api(action="query", list="categorymembers", cmtitle=f"Category:{cat}", cmnamespace=0, cmlimit=500, **cont)
            members |= {m["title"] for m in d["query"]["categorymembers"]}
            if "continue" not in d:
                break
            cont = d["continue"]
    texts = _wikitext(sorted(members))
    kept, dropped = {}, {}
    for title, wt in sorted(texts.items()):
        year = end_year(wt)
        links = starring_links(wt)
        if title.replace("_", " ") in EXCLUDED_SHOWS:
            dropped[title] = "Modern Family or The King of Queens"
        elif not on_big_network(wt):
            dropped[title] = "not an ABC, CBS, NBC, Fox or CW show"
        elif year is None or not RUN_ENDED[0] <= year <= RUN_ENDED[1]:
            dropped[title] = f"run did not end {RUN_ENDED[0]}-{RUN_ENDED[1]}"
        elif is_animated(wt):
            dropped[title] = "animated"
        elif not links:
            dropped[title] = "no starring links"
        elif excluded & set(links):
            dropped[title] = "lists an actor of Modern Family or The King of Queens"
        else:
            kept[title] = links
    actor_text = _wikitext(sorted({a for v in kept.values() for a in v}))
    for title in list(kept):
        if any(death_year(actor_text.get(a, "")) == 2023 for a in kept[title]):
            dropped[title] = "a starring actor died in 2023"
            del kept[title]
    candidates = sorted({a for v in kept.values() for a in v})
    ok, bad = {}, {}
    for i in range(0, len(candidates), 20):
        chunk = candidates[i:i + 20]
        d = _api(action="query", titles="|".join(c.replace("_", " ") for c in chunk), prop="info|pageprops",
                 ppprop="disambiguation")
        norm = {n["from"]: n["to"] for n in d["query"].get("normalized", [])}
        pages = {p["title"]: p for p in d["query"]["pages"]}
        for c in chunk:
            p = pages.get(norm.get(c.replace("_", " "), c.replace("_", " ")))
            if p is None or p.get("missing"):
                bad[c] = "missing"
            elif "redirect" in p:
                bad[c] = "redirect"
            elif "disambiguation" in p.get("pageprops", {}):
                bad[c] = "disambiguation page"
            else:
                ok[c] = True
    show_actors = {s: [a for a in v if a in ok] for s, v in kept.items()}
    return {"shows": sorted(kept), "show_actors": show_actors, "dropped_shows": dropped, "dropped_titles": bad,
            "pool": round_robin(show_actors), "n_eligible_actors": len(ok), "excluded_actors": sorted(excluded)}
