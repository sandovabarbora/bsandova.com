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


def unquoted(page: str) -> str:
    """The page without the registered readings, which are quoted verbatim and carry their conditions beside them."""
    return re.sub(r'<blockquote class="registered">.*?</blockquote>', " ", page, flags=re.DOTALL)


def sentences(page: str) -> list[str]:
    blocks = re.findall(r"<(p|li|dd)\b[^>]*>(.*?)</\1>", unquoted(page), re.DOTALL)
    return [x for _, b in blocks for x in re.split(r"(?<=[a-z0-9)%])\. (?=[A-ZČŘŠŽ])", re.sub(r"\s+", " ", text(b)))]


def plain(s: str) -> str:
    return s.replace(NB, " ")


def test_committed_page_is_what_the_results_render(page):
    assert article.PAGE.read_text(encoding="utf-8") == page, "run tools/fees_article/article.py"


def test_published_copies_match(res):
    assert (article.ASSETS / "results.json").read_bytes() == article.RESULTS.read_bytes()
    assert (article.ASSETS / "charts.json").read_text(encoding="utf-8") == article.charts_json(res)


def test_static_figures_were_drawn_from_the_current_numbers(res):
    for fn, name in article.CHARTS.values():
        svg = (article.ASSETS / name).read_text(encoding="utf-8")
        assert f"data sha256 {article.chart_hash(fn(res))}" in svg, f"{name}: run article.py --figures"
    drawn = {p.name for p in article.ASSETS.glob("*.svg")}
    assert drawn == {name for _, name in article.CHARTS.values()}, drawn


def test_every_figure_has_a_chart_alt_text_a_takeaway_and_a_caption(page, res):
    specs = json.loads(article.charts_json(res))
    figs = re.findall(r'<figure id="fig(\d+)" data-chart="\.\./assets/licence-fees/charts\.json#([\w-]+)">(.*?)</figure>',
                      page, re.DOTALL)
    assert [(int(i), k) for i, k, _ in figs] == list(enumerate(article.CHARTS, 1))
    assert page.count("<figure") == len(figs)
    for i, key, body in figs:
        name = article.CHARTS[key][1]
        img = re.search(r'<img src="\.\./assets/licence-fees/([\w.-]+)" alt="([^"]+)"', body)
        assert img and img.group(1) == name, key
        assert html.unescape(img.group(2)) == specs[key]["alt"] and len(specs[key]["alt"]) > 80, key
        assert re.search(r'<p class="ch-head">[^<]{20,}</p>', body), key
        cap = re.search(r"<figcaption><b>fig\. (\d+)</b> · (.*?)</figcaption>", body, re.DOTALL)
        assert cap and cap.group(1) == i and len(text(cap.group(2)).split()) > 20, key
        assert "no interval" in text(cap.group(2)).lower(), key
        assert specs[key]["table"]["rows"] and specs[key]["data"] == ["results.json"], key


def test_in_short_points_at_figures_1_to_4(page):
    box = re.search(r'<details class="tldr" open>(.*?)</details>', page, re.DOTALL).group(1)
    assert "<summary>In short</summary>" in box
    items = re.findall(r"<li>(.*?)</li>", box, re.DOTALL)
    assert [re.search(r'href="#fig(\d+)">fig\. (\d+)<', li).groups() for li in items] == [(str(k), str(k)) for k in range(1, 5)]


def test_money_chart_is_the_primary_paths_in_2026_prices(res):
    qa = res["qa"]
    pr = qa["primary"]
    spec = article.money_chart(res)
    area, law, bill, note = spec["panels"][0]["marks"]
    for line, path in ((law, "p1"), (bill, "p2")):
        ys = [(pr["nominal"][path]["CT"][y] + pr["nominal"][path]["CRO"][y]) / pr["price_level"][y] / 1e9
              for y in article.YEARS]
        assert [p[0] for p in line["pts"]] == [int(y) for y in article.YEARS]
        assert [p[1] for p in line["pts"]] == [round(v, 4) for v in ys]
        assert abs(sum(ys) - pr["real"][path] / 1e9) < 1e-9
    assert [[p[0], p[2], p[1]] for p in area["pts"]] == [[a[0], a[1], b[1]] for a, b in zip(law["pts"], bill["pts"])]
    assert spec["table"]["rows"][-1][1:] == [round(pr["real"]["p1"] / 1e9, 4), round(pr["real"]["p2"] / 1e9, 4),
                                             round(qa["x_primary_bn"], 4)]
    assert article.bnx(qa["x_primary_bn"]) in note["s"] and article.bnx(qa["x_primary_bn"]) in note["narrow"]["s"]
    assert "2026 prices" in note["s"]


def test_first_year_chart_is_reading_c(res):
    rc = res["reading_c"]
    today, bill, gap = article.first_year_chart(res)["panels"][0]["marks"][0]["rows"]
    assert today["x1"] == round(rc["budgeted_fee_revenue_2026_czk"] / 1e9, 4) and "x0" not in today
    assert bill["x1"] == round(rc["bill_2027_czk"] / 1e9, 4) and "x0" not in bill
    assert (gap["x0"], gap["x1"]) == (round(rc["bill_2027_in_2026_prices_czk"] / 1e9, 4), today["x1"])
    assert gap["label"] == article.values(res)["d_level"] + " less" and "2026 prices" in gap["y"]


def test_ratio_chart_is_y_and_z(res):
    qb = res["qb"]
    a = qb["after"]
    spec = article.ratio_chart(res)
    marks = spec["panels"][0]["marks"]
    span, rule, main, pale = marks
    assert (span["v0"], span["v1"], rule["v"]) == (0.9, 1.1, 1)
    want = [qb["y_hi"], qb["y_lo"], a["ratio_z"], a["ratio_z_vat_only"], a["ratio_z_pit_only"]]
    rows = main["rows"] + pale["rows"]
    assert [r["x1"] for r in rows] == [round(w, 4) for w in want]
    assert [r["label"] for r in rows] == ["5.26", "0.00", "2.37", "4.81", "0.10"]
    assert [r["y"] for r in rows] == spec["panels"][0]["y"]["domain"] and len(main["rows"]) == 3


def test_decile_charts_are_the_payments_and_burdens(res):
    qb = res["qb"]
    for key, fields, dp in (("pay", (qb["today"]["e0"]["pay_hh"], qb["today"]["e1"]["pay_hh"], qb["after"]["per_hh"]), 0),
                            ("burden", (qb["today"]["e0"]["burden_pct"], qb["today"]["e1"]["burden_pct"],
                                        qb["after"]["burden_pct"]), 3)):
        spec = article.CHARTS[key][0](res)
        lines = spec["panels"][0]["marks"]
        assert [[p[1] for p in m["pts"]] for m in lines] == [[round(v, dp) for v in f] for f in fields], key
        assert [r[1:] for r in spec["table"]["rows"]] == [[round(f[i], dp) for f in fields] for i in range(10)], key


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


def test_firm_comparison_sits_in_one_sentence_with_its_caveat(page, v):
    both = [s for s in sentences(page) if plain(v["f_today"]) in s and plain(v["f_after"]) in s]
    assert both and all("not like for like" in s for s in both), both
    for s in sentences(page):
        if plain(v["f_after"]) in s and "firms and public bodies" in s.lower():
            assert plain(v["f_today"]) in s and "not like for like" in s, s


def test_x_is_always_in_2026_prices_with_payers_held_fixed(page, v):
    claims = [s for s in sentences(page) if plain(v["x"]) in s]
    assert claims
    deck = text(re.search(r'<p class="deck">(.*?)</p>', page).group(1))
    for s in claims:
        assert "2026 prices" in s, s
        assert "payers held fixed" in s or s == deck, s  # the deck is the listed finding, capped at 35 words


MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def main_story(page: str) -> str:
    """Visible prose: the sections between the metadata and the folded details, without figures and tables."""
    a = page.index("</details>", page.index('class="meta-more"'))
    body = page[a:page.index('<section id="reproduction">')]
    return re.sub(r"<(figure|table)\b[^>]*>.*?</\1>", " ", body, flags=re.DOTALL)


def counted_numbers(s: str) -> list[str]:
    s = re.sub(rf"(\d{{1,2}} )?({MONTHS}) \d{{4}}|\b(19|20)\d\d(–(19|20)\d\d)?\b", " ", s)
    return re.findall(r"\d{1,3}(?: \d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", s)


def test_main_story_is_short_with_short_paragraphs(page):
    story = main_story(page)
    words = len(text(story).split())
    assert 700 <= words <= 900, words
    for _, b in re.findall(r"<(p|li)\b[^>]*>(.*?)</\1>", story, re.DOTALL):
        t = re.sub(r"\s+", " ", text(b)).strip()
        assert len(t.split()) <= 55, t
        assert len(counted_numbers(t)) <= 3, (counted_numbers(t), t)


def test_visible_text_has_no_codes(page):
    head = page.index("<article")
    seen = re.sub(r'<details class="appendix">.*?</details>|<details class="meta-more">.*?</details>|<table\b.*?</table>',
                  " ", page[head:page.index('id="refs"')], flags=re.DOTALL)
    t = text(seen)
    for pat in (r"\b(X|Y|Z|Q-A|Q-B|E0|E1|R1|R2)\b", r"\bpp\b", "§", r"\bdeciles?\b", r"\blabel (after )?is\b",
                r"\bprimary\b"):
        assert not re.search(pat, t), (pat, re.search(rf".{{0,40}}{pat}.{{0,40}}", t).group(0))


def test_registered_readings_are_quoted_verbatim_with_their_conditions(page, res):
    block = re.search(r'<blockquote class="registered">(.*?)</blockquote>\s*<p class="note">(.*?)</p>', page, re.DOTALL)
    assert block
    quoted = [html.unescape(q) for q in re.findall(r"<p>(.*?)</p>", block.group(1), re.DOTALL)]
    assert quoted == [res["qa"]["reading_a"], res["qb"]["reading_b"], res["reading_c"]["text"]]
    note = text(block.group(2))
    for part in ("payers held fixed", "crude", "not like for like"):
        assert part in note, part
    assert page.rfind('<details class="appendix">', 0, block.start()) > page.index('<section id="reproduction">')


def test_z_is_tied_to_its_tax_structure_and_followed_by_its_assumptions(page, v):
    claims = [s for s in sentences(page) if f"{v['z']} times" in s]
    assert claims
    for s in claims:
        assert "average" in s or "mix of" in s, s
    ss = sentences(page)
    i = next(k for k, s in enumerate(ss) if s.startswith("Funded from the state budget at the average tax structure"))
    nxt = ss[i + 1]
    for part in ("VAT and excise fall wholly on households", "corporate income tax stays with firms",
                 "social insurance is left out", "spend the same", "checks"):
        assert part in nxt, part


def test_conditional_on_the_bill_as_introduced(page):
    t = text(page)
    assert t.count("as introduced") >= 4
    assert "checked on 3 November 2026" in t and "24 December 2026" in t and "January 2028" in t
    assert "30 November 2026" in t and "run again" in t


def test_author_position_is_disclosed_once_and_visibly_in_the_methods_section(page):
    t = text(page)
    assert t.count("favours keeping the licence fee and raising it") == 1
    i = page.index("favours keeping the licence fee")
    assert page.rfind("<h2>How this was done</h2>", 0, i) > page.rfind("<details", 0, i)


def test_no_causal_or_editorial_language(page):
    t = text(page).lower()
    for word in (r"\bcaused?\b", r"\bcauses\b", r"\bleads? to\b", r"\bresults? in(?!\s+results\.json)", r"\bimpact",
                 r"\bunfair", r"\bfairer\b", r"\bshould\b", r"\bmust\b", r"disfavour", r"points the same way",
                 r"\bfavour(?!s current law|s keeping)"):
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


def test_tags_are_described_as_public_and_fees_code_as_superseded(page):
    t = text(page)
    assert "The tags are the author's own and are in the public repository; commit times are self-reported." in t
    assert "superseded by fees-code-2" in re.sub(r"\s+", " ", t)


def test_deck_and_og_carry_both_parts(page, v):
    deck = text(re.search(r'<p class="deck">(.*?)</p>', page).group(1))
    assert plain(v["x"]) in deck and "poorest tenth" in deck and "exemption-free" in deck and "exempting" in deck
    for name in ('property="og:description"', 'name="description"'):
        og = plain(re.search(name + r' content="([^"]*)"', page).group(1))
        assert plain(v["x"]) in og and f"{v['y_lo']} to {v['y_hi']}" in og and v["z"] in og, name


def test_part_a_is_not_set_against_part_b(page):
    for s in sentences(page):
        if "bill gives" in s:
            assert " yet " not in f" {s.lower()} ", s


def test_labels_are_quoted_in_running_text(page):
    t = text(page)
    for lab in ('"bill lower"', '"depends on the assumption"', '"higher"'):
        assert f"label is {lab}" in t or f"label after is {lab}" in t or f"labelled {lab}" in t, lab
