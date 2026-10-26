"""Tests of the reference-pool rule on made-up wikitext, and of the frozen pool in config (design §1, §2)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import pool as P

SHOW = """{{Infobox television
| name = Made Up
| starring = {{Plainlist|
* [[Ann One]]
* [[Bob Two (actor)|Bob Two]]
* Carl Unlinked
* [[File:x.jpg]]
* [[Ann One]]
}}
| network = [[American Broadcasting Company|ABC]]
| first_aired = {{Start date|2015|9|23}}
| last_aired = {{End date|2019|4|8}}
| num_seasons = 4
}}
[[Category:2010s American sitcoms]]
"""


def test_starring_links_are_targets_in_order_without_files_unlinked_or_duplicates():
    assert P.starring_links(SHOW) == ["Ann_One", "Bob_Two_(actor)"]


def test_run_end_network_and_animation():
    assert P.end_year(SHOW) == 2019
    assert P.on_big_network(SHOW) and not P.on_big_network(SHOW.replace("ABC", "HBO").replace(
        "American Broadcasting Company", "HBO"))
    assert not P.is_animated(SHOW) and P.is_animated(SHOW + "[[Category:American adult animated sitcoms]]")
    assert P.end_year("| last_aired = ") is None


def test_death_year():
    assert P.death_year("| death_date = {{Death date and age|2023|10|28|1969|8|19}}\n") == 2023
    assert P.death_year("| birth_date = {{birth date|1969|8|19}}") is None


def test_comments_and_namespace_links_are_not_cast():
    wt = """\n| starring = {{plainlist|
<!-- see [[Talk:Made Up/Archive 2#x]] and [[MOS:TV]] -->
* [[Ann One]]
* [[Wikipedia:Cast]]
* [[Bob Two]]
}}
| network = ABC
"""
    assert P.starring_links(wt) == ["Ann_One", "Bob_Two"]


def test_first_billed_is_the_first_entry_and_never_the_next_when_it_has_no_link():
    assert P.first_billed_link(SHOW) == "Ann_One"
    unlinked = SHOW.replace("* [[Ann One]]", "* Ann Unlinked", 1)
    assert P.first_billed_link(unlinked) is None
    assert P.first_billed_link("\n| starring = {{ubl|[[Cy Three]]|[[Di Four]]}}\n| network = x") == "Cy_Three"


def test_the_pool_takes_one_first_billed_actor_per_show_and_replaces_nobody():
    firsts = {"B": "bob", "A": "ann", "C": "ann", "D": None, "E": "eve", "F": "fay"}
    pool, table = P.first_billed(firsts, {"eve": "redirect"})
    assert pool == ["ann", "bob", "fay"]
    assert table["C"]["status"] == "dropped: already taken from an earlier show"
    assert table["D"]["status"].startswith("dropped: the first-billed actor has no article link")
    assert table["E"]["status"] == "dropped: redirect" and table["A"]["status"] == "in pool"


def test_frozen_pool_obeys_its_own_rules_and_matches_the_committed_candidate_list():
    import json
    pool = C.REFERENCE_POOL
    assert len(pool) == len(set(pool)) <= len(C.REFERENCE_SHOWS) == 53
    inside = {*C.MF_CAST, *C.KOQ_CAST, "Eric_Stonestreet", "Kevin_James", "Rico_Rodriguez", "Gary_Valentine"}
    assert not inside & set(pool)
    assert not set(C.REFERENCE_DROPPED) & set(pool)
    assert "Modern_Family" not in C.REFERENCE_SHOWS and "The_King_of_Queens" not in C.REFERENCE_SHOWS
    assert "Kevin_Can_Wait" not in C.REFERENCE_SHOWS
    assert set(pool) <= set(C.ARTICLES) and C.LEBLANC in pool
    listed = json.loads((C.ROOT / "docs/research/memes-reference-pool.json").read_text())
    assert listed["pool"] == list(pool) and listed["shows"] == list(C.REFERENCE_SHOWS)
    assert [s for s, v in listed["candidates"].items() if v["status"] == "in pool"] and len(listed["candidates"]) == 53
