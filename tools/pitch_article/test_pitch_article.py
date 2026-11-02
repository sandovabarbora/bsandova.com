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
    assert re.search(r'<p class="kicker">[^<]*exploratory', page)
    assert "<dt>status</dt><dd>research, exploratory" in page
    assert not re.search(r"registered study", text(page), re.IGNORECASE)


def test_run_2_instability_sits_in_the_paragraph_of_the_first_film_q2_claim(page):
    para = next(p for p in re.findall(r"<p>(.*?)</p>", page, re.DOTALL) if "D, the share on the speaker" in p)
    assert "does not hold across runs" in para and "would read inconclusive" in para


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
