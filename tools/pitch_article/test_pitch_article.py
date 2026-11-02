import copy
import html
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import article


@pytest.fixture(scope="module")
def res() -> dict:
    return json.loads(article.RESULTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page(res) -> str:
    return article.build(res)


def text(page: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.DOTALL)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def test_committed_page_is_what_the_results_render(page):
    assert article.PAGE.read_text(encoding="utf-8") == page, "run tools/pitch_article/article.py"


def test_published_results_copy_matches_the_research_file():
    assert (article.ROOT / "assets" / article.SLUG / "results.json").read_bytes() == article.RESULTS.read_bytes()


def test_every_token_and_citation_is_filled(page):
    assert "{{" not in page and "[[" not in page


def test_status_is_exploratory_in_kicker_and_metadata(page):
    assert re.search(r'<p class="kicker">[^<]*Exploratory', page)
    assert "<dt>status</dt><dd>research, Exploratory" in page
    assert not re.search(r"registered study", text(page), re.IGNORECASE)


def sentences(page: str) -> list[str]:
    return [x for p in re.findall(r"<(?:p|li)>(.*?)</(?:p|li)>", page, re.DOTALL)
            for x in re.split(r"(?<=[a-z)])\. ", text(p))]


def test_each_q2_direction_claim_carries_the_run_2_caveat_in_the_same_sentence(page, res):
    d1 = article.values(res)["D1"]
    claims = [x for x in sentences(page) if "speaker more often" in x or d1 in x and "run 1" in x]
    assert claims
    for x in claims:
        assert "run 2" in x and "includes zero" in x, x


def test_would_not_pass_today_is_defined_where_it_first_appears(page):
    og = re.search(r'og:description" content="([^"]*)"', page).group(1)
    for part in (og, page[page.index('class="facts"'):], page[page.index('class="tldr"'):]):
        i = part.index("would not pass today")
        assert "protected trait with the laugh on the group" in part[i:i + 120]


def test_no_lyric_line_claim_matches_the_results(page, res):
    assert "no line was removed as a lyric" in page
    assert all(res["counts"][f]["cleaning"]["lyric_lines_removed"] == 0 for f in ("pp1", "pp2"))


def test_hard_coded_hashes_match_the_results(page, res):
    tags = res["meta"]["tags"]
    assert tags["pitch-design"] in page and tags["pitch-code-cli-2"] in page
    assert tags["pitch-code-cli-2"].startswith("21fa3ea") and "<code>e1a34ec</code>" in page
    for obj in article.TAG_OBJECTS.values():
        assert re.fullmatch(r"[0-9a-f]{40}", obj) and obj in page


def test_no_hedged_interval_glosses(page):
    for word in ("plausible", "compatible", "range the data", "consistently"):
        assert word not in text(page).lower(), word


def test_a_changed_label_stops_the_build(res):
    bad = copy.deepcopy(res)
    bad["estimates"]["delta1"]["ci95"] = [0.01, 0.05]
    with pytest.raises(AssertionError):
        article.build(bad)


def test_reading_rule_treats_an_end_at_zero_as_not_excluding_it():
    e = {"indeterminate": False, "ci95": [0.0, 0.3]}
    assert article.reading(e, "Q2") == "inconclusive"
    assert article.reading({**e, "ci95": [0.01, 0.3]}, "Q2") == "speaker"
    assert article.reading({**e, "ci95": [-0.3, -0.01]}, "Q1") == "not supported"
    assert article.reading({**e, "indeterminate": True}, "Q3") == "indeterminate"
