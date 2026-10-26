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


def test_round_robin_takes_first_billed_actors_first_and_caps():
    shows = {"B": ["b1", "b2"], "A": ["a1", "a2", "a3"], "C": ["a1", "c2"]}
    assert P.round_robin(shows, cap=10) == ["a1", "b1", "a2", "b2", "c2", "a3"]
    assert P.round_robin(shows, cap=3) == ["a1", "b1", "a2"]


def test_frozen_pool_obeys_its_own_rules():
    pool = C.REFERENCE_POOL
    assert len(pool) == P.CAP == len(set(pool))
    inside = {*C.MF_CAST, *C.KOQ_CAST, "Eric_Stonestreet", "Kevin_James", "Rico_Rodriguez", "Gary_Valentine"}
    assert not inside & set(pool)
    assert not set(C.REFERENCE_DROPPED_TITLES) & set(pool)
    assert "Modern_Family" not in C.REFERENCE_SHOWS and "The_King_of_Queens" not in C.REFERENCE_SHOWS
    assert "Kevin_Can_Wait" not in C.REFERENCE_SHOWS
    assert set(pool) <= set(C.ARTICLES)
