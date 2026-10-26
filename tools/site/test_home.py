import copy
import re

import pytest

import home

CFG = {
    "topics": {
        "transit": {"title": "Getting around", "note": "Trams."},
        "theses": {"title": "Theses", "note": "Three theses.", "collapsed": True, "anchors": ["old"]},
    },
    "works": [
        {"href": "texts/a", "title": "A", "label": "Registered study", "published": "2026-10-20", "topic": "transit",
         "finding": "A fell: underpowered.", "detail": "stage B in 2027", "progress": True},
        {"href": "texts/hub", "title": "Hub", "label": "Series", "published": "2026-09-01", "topic": "transit"},
        {"href": "texts/p1", "title": "Rain and delays", "label": "Pre-specified", "published": "2026-10-25", "topic": "transit",
         "series": "texts/hub"},
        {"href": "texts/p2", "title": "Heat and delays", "label": "Exploratory", "finding": "Less delay: inconclusive.", "published": "2026-09-01", "topic": "transit",
         "series": "texts/hub"},
        {"href": "texts/b", "title": "B", "label": "Note", "published": "2026-10-10", "topic": "transit"},
        {"href": "texts/c", "title": "C", "label": "Tool", "published": "2026-08-01", "topic": "transit"},
        {"href": "texts/d", "title": "D", "label": "Note", "published": "2026-07-01", "topic": "transit"},
        {"href": "texts/t", "title": "T", "label": "Thesis", "published": "2021-04-01", "date": "Apr 2021",
         "topic": "theses"},
        {"href": "texts/method", "title": "Method", "label": "Note", "published": "2026-10-30"},
    ],
}
CSS = ".rows{list-style:none}\n"


def cfg(**change):
    c = copy.deepcopy(CFG)
    c["works"][0].update(change)
    return c


def test_valid_config_passes():
    home.validate(copy.deepcopy(CFG))


@pytest.mark.parametrize("label", ["Research", "registered study", "Hub · series of three", ""])
def test_label_outside_the_vocabulary_is_rejected(label):
    with pytest.raises(ValueError, match="is not one of"):
        home.validate(cfg(label=label))


def test_unknown_topic_is_rejected():
    with pytest.raises(ValueError, match="unknown topic 'other'"):
        home.validate(cfg(topic="other"))


def test_missing_label_is_rejected():
    c = copy.deepcopy(CFG)
    del c["works"][0]["label"]
    with pytest.raises(ValueError, match="no label"):
        home.validate(c)


def test_a_part_needs_a_series_hub_in_its_topic():
    c = copy.deepcopy(CFG)
    c["works"][1]["label"] = "Note"
    with pytest.raises(ValueError, match="must be a Series"):
        home.validate(c)


@pytest.mark.parametrize("title, why", [
    ("Injury accidents after a bypass: −19 %, underpowered", "':'"),
    ("Unemployment +0.10 points", "number other than a year"),
    ("A fall of 19 %", "'%'"),
    ("A very long title that keeps going well past the limit set for every title", "longer than 60"),
])
def test_titles_that_carry_a_result_are_rejected(title, why):
    with pytest.raises(ValueError, match=why):
        home.validate(cfg(title=title))


@pytest.mark.parametrize("title", ["What can Prague's next council actually deliver?", "Are towns calmer after the bypass opens?",
                                   "Prague's 2026 election programmes", 'What "pre-specified" means'])
def test_short_names_and_years_pass(title):
    home.validate(cfg(title=title))


def test_latest_is_newest_first_without_parts_or_untopiced_pages():
    hrefs = [w["href"] for w in home.latest(CFG["works"], 4)]
    # the hub counts by its own date (Sep), not its newest part (Oct 25); parts and the method note are left out
    assert hrefs == ["texts/a", "texts/b", "texts/hub", "texts/c"]


def test_latest_ties_keep_the_config_order():
    c = copy.deepcopy(CFG)
    for w in c["works"]:
        w["published"] = "2026-10-01"
    assert [w["href"] for w in home.latest(c["works"], 3)] == ["texts/a", "texts/hub", "texts/b"]


def test_series_is_one_row_dated_by_its_newest_part():
    rows = home.grouped(CFG["works"], "transit")
    assert [w["href"] for w, _ in rows] == ["texts/hub", "texts/a", "texts/b", "texts/c", "texts/d"]
    assert [p["href"] for p in rows[0][1]] == ["texts/p1", "texts/p2"]


def test_series_row_folds_its_parts_in_details():
    w, parts = home.grouped(CFG["works"], "transit")[0]
    html = home.row(w, parts)
    assert html.count("<details") == 1 and "<summary>2 parts</summary>" in html
    assert html.index('href="texts/hub"') < html.index("<details") < html.index('href="texts/p1"')
    assert ">Part 1 · Rain and delays<" in html and ">Part 2 · Heat and delays<" in html


def test_row_shows_the_finding_under_the_title():
    html = home.row(CFG["works"][0], [])
    assert '<span class="tt"><span class="t">A</span><span class="f">A fell: underpowered.</span></span>' in html
    assert 'class="f"' not in home.row(CFG["works"][4], [])


def test_label_carries_detail_and_progress_marker():
    html = home.label(CFG["works"][0])
    assert html == '<span class="c" title="stage B in 2027">Registered study<i class="wip">in progress</i></span>'


def test_card_without_finding_shows_title_only():
    assert 'class="f"' in home.card(CFG["works"][0])
    assert 'class="f"' not in home.card(CFG["works"][4])


def test_home_shows_four_rows_per_topic_and_collapses_theses():
    out = home.catalogue(copy.deepcopy(CFG))
    transit = out[out.index('id="transit"'):out.index('id="theses"')]
    top_level = re.findall(r'^        <li', transit, re.M)
    assert len(top_level) == 4 and "texts/d" not in transit
    assert 'href="topics/transit">All 7 in Getting around' in transit
    assert '<details class="grp" id="theses"><span id="old"></span>' in out
    assert 'id="works"' in out and 'id="texts"' in out and 'href="#transit"' in out


def test_topic_page_lists_everything_with_relative_links_and_canonical():
    pages = home.topic_pages("x /* catalogue */\n" + CSS + "/* /catalogue */", copy.deepcopy(CFG))
    assert set(pages) == {"topics/transit.html", "topics/theses.html"}
    page = pages["topics/transit.html"]
    assert '<link rel="canonical" href="https://bsandova.com/topics/transit">' in page
    for href in ("texts/a", "texts/hub", "texts/p1", "texts/p2", "texts/b", "texts/c", "texts/d"):
        assert f'href="../{href}"' in page
    assert "texts/method" not in page and CSS in page
    assert '<div class="top"><b><a href="../"' in page and "7 entries" in page


def test_topic_pages_need_the_shared_css_block():
    with pytest.raises(ValueError, match="catalogue"):
        home.topic_pages("<style></style>", copy.deepcopy(CFG))


def test_repository_output_is_up_to_date():
    assert home.stale() == []
