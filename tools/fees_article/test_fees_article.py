import copy
import html
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import article

NB = " "


@pytest.fixture(scope="module")
def res() -> dict:
    return json.loads(article.RESULTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page(res) -> str:
    return article.build(res)


@pytest.fixture(scope="module")
def v(res) -> dict:
    return article.values(res)


def text(page: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.DOTALL)
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace(NB, " ")


def sentences(page: str) -> list[str]:
    blocks = re.findall(r"<(p|li|dd)\b[^>]*>(.*?)</\1>", page, re.DOTALL)
    return [x for _, b in blocks for x in re.split(r"(?<=[a-z0-9)%])\. (?=[A-ZČŘŠŽ])", re.sub(r"\s+", " ", text(b)))]


def plain(s: str) -> str:
    return s.replace(NB, " ")


def test_committed_page_is_what_the_results_render(page):
    assert article.PAGE.read_text(encoding="utf-8") == page, "run tools/fees_article/article.py"


def test_published_copies_match(res):
    assert (article.ASSETS / "results.json").read_bytes() == article.RESULTS.read_bytes()
    assert (article.ASSETS / "charts.json").read_text(encoding="utf-8") == article.charts_json(res)
    assert (article.ASSETS / "01-burden.svg").exists()


def test_every_token_and_citation_is_filled(page):
    assert "{{" not in page and "[[" not in page


def test_label_is_pre_specified_in_kicker_status_and_listing(page):
    assert re.search(r'<p class="kicker">Research · Pre-specified', page)
    assert "<dt>status</dt><dd>research, pre-specified analysis" in page
    works = (article.ROOT / "docs" / "works.toml").read_text(encoding="utf-8")
    entry = works[works.index('href = "texts/licence-fees"'):].split("[[works]]")[0]
    assert 'label = "Pre-specified"' in entry and 'topic = "money"' in entry


def test_registered_labels_appear_verbatim(page):
    t = text(page)
    for lab in ("bill lower", "depends on the assumption", "higher", "lower after",
                "the poorest tenth carries a higher share of its income than the richest tenth"):
        assert lab in t, lab


def test_y_range_carries_the_entitlement_caveat_in_the_same_sentence(page, v):
    claims = [s for s in sentences(page) if f"{v['y_lo']} and {v['y_hi']}" in s or f"{v['y_lo']} to {v['y_hi']}" in s]
    assert claims
    for s in claims:
        assert "entitle" in s or "depending on how many" in s, s
    reading_b = [s for s in claims if "between" in s and "times the share" in s]
    assert reading_b and all("take-up" in s and "crude" in s and "pays nothing" in s for s in reading_b)


def test_firm_figures_carry_the_not_like_for_like_caveat(page, v):
    for key in ("f_today", "f_after"):
        claims = [s for s in sentences(page) if plain(v[key]) in s and "firms and public bodies" in s.lower()]
        assert claims, key
        for s in claims:
            assert "not like for like" in s or "identity" in s or "by construction" in s, s


def test_x_is_always_in_2026_prices(page, v):
    claims = [s for s in sentences(page) if plain(v["x"]) in s]
    assert claims
    for s in claims:
        assert "2026 prices" in s, s


def test_z_is_tied_to_its_tax_structure(page, v):
    claims = [s for s in sentences(page) if f"{v['z']} times" in s]
    assert claims
    for s in claims:
        assert "average" in s or "mix of" in s, s


def test_conditional_on_the_bill_as_introduced(page):
    t = text(page)
    assert t.count("as introduced") >= 4
    assert "checked on 3 November 2026" in t and "24 December 2026" in t and "January 2028" in t
    assert "30 November 2026" in t and "run again" in t


def test_author_position_is_disclosed_once_in_the_methods_note(page):
    t = text(page)
    assert t.count("favours keeping the licence fee and raising it") == 1
    i = page.index("favours keeping the licence fee")
    assert page.rfind('id="reproduction"', 0, i) > 0


def test_no_causal_or_editorial_language(page):
    t = text(page).lower()
    for word in (r"\bcaused?\b", r"\bcauses\b", r"\bleads? to\b", r"\bresults? in(?!\s+results\.json)", r"\bimpact",
                 r"\bunfair", r"\bfairer\b", r"\bshould\b", r"\bmust\b"):
        assert not re.search(word, t), word


def test_body_is_within_the_research_cap():
    sys.path.insert(0, str(article.ROOT / "tools" / "site"))
    import check_standard

    hard, soft = check_standard.check(article.PAGE)
    assert not hard and not soft, (hard, soft)


def test_hard_coded_tag_objects_and_commits(page, res):
    tags = res["design"]["stamp"]["tag_commits"]
    for t in tags.values():
        assert t in page
    for obj in article.TAG_OBJECTS.values():
        assert re.fullmatch(r"[0-9a-f]{40}", obj) and obj in page


def test_a_changed_label_stops_the_build(res):
    bad = copy.deepcopy(res)
    bad["qb"]["labels"]["after"] = "similar"
    with pytest.raises(AssertionError):
        article.build(bad)


def test_a_new_trigger_stops_the_build(res):
    bad = copy.deepcopy(res)
    bad["qa"]["primary"]["bill_triggers"]["CT"] = [{"crossed_in": 2029, "raised_from": 2030, "window": [2026, 2029]}]
    with pytest.raises(AssertionError):
        article.build(bad)


def test_trigger_descriptions():
    assert article.law_rises([2027]) == "1 July 2028"
    assert article.law_rises([2027, 2029]) == "1 July 2028, 1 July 2030"
    assert article.law_rises([2030]) == "none by 2030"
    m = {"bill_triggers": {"CT": [{"raised_from": 2029}], "CRO": [{"raised_from": 2029}]}}
    assert article.bill_rises(m) == "from 2029"
    assert article.bill_rises({"bill_triggers": {"CT": [], "CRO": []}}) == "none by 2030"


def test_deck_is_the_listed_finding_and_the_title_matches(page):
    works = (article.ROOT / "docs" / "works.toml").read_text(encoding="utf-8")
    entry = works[works.index('href = "texts/licence-fees"'):].split("[[works]]")[0]
    finding = re.search(r'finding = "([^"]*)"', entry).group(1)
    title = re.search(r'title = "([^"]*)"', entry).group(1)
    deck = text(re.search(r'<p class="deck">(.*?)</p>', page).group(1))
    assert deck == finding and len(deck.split()) <= 35
    assert f"<title>{title}</title>" in page and f"<i>{title}</i>" in page
