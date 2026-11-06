import html
import itertools
import json
import re
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import article

NB = "\u00a0"


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


def story(page: str) -> str:
    """The visible article above the details: what a reader sees without opening anything."""
    a = page.find("</details>", page.find('class="meta-more"'))
    return text(page[a:page.find('<section id="reproduction"')])


def test_committed_page_is_what_the_results_render(page):
    assert article.PAGE.read_text(encoding="utf-8") == page, "run tools/rebates_article/article.py"


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
    figs = re.findall(r'<figure id="fig(\d+)" data-chart="\.\./assets/film-rebates/charts\.json#([\w-]+)">(.*?)</figure>',
                      page, re.DOTALL)
    assert [(int(i), k) for i, k, _ in figs] == list(enumerate(article.CHARTS, 1))
    assert page.count("<figure") == len(figs)
    for i, key, body in figs:
        img = re.search(r'<img src="\.\./assets/film-rebates/([\w.-]+)" alt="([^"]+)"', body)
        assert img and img.group(1) == article.CHARTS[key][1], key
        assert html.unescape(img.group(2)) == specs[key]["alt"] and len(specs[key]["alt"]) > 80, key
        assert re.search(r'<p class="ch-head">[^<]{20,}</p>', body), key
        cap = re.search(r"<figcaption><b>fig\. (\d+)</b> · (.*?)</figcaption>", body, re.DOTALL)
        assert cap and cap.group(1) == i and 8 <= len(text(cap.group(2)).split()) <= 30, key
        assert "no interval" in text(cap.group(2)).lower(), key
        assert specs[key]["table"]["rows"] and specs[key]["data"] == ["results.json"], key


def test_in_short_points_at_figures_1_to_5(page):
    box = re.search(r'<details class="tldr" open>(.*?)</details>', page, re.DOTALL).group(1)
    items = re.findall(r"<li>(.*?)</li>", box, re.DOTALL)
    assert [re.search(r'href="#fig(\d+)">fig\. (\d+)<', li).groups() for li in items] == [(str(k), str(k)) for k in range(1, 6)]


def test_paid_chart_steps_from_allocated_to_paid(res):
    rows = article.paid_rows(res)
    q1 = res["q1"]
    assert rows[0]["x1"] == round(q1["promised"] / 1e9, 4) and rows[-1]["x1"] == round(q1["paid"] / 1e9, 4)
    for a, b in itertools.pairwise(rows[1:-1]):
        assert a["x1"] == b["x0"]
    assert rows[1]["x0"] == rows[0]["x1"] and abs(rows[-2]["x1"] - rows[-1]["x1"]) < 1e-4
    assert [r["label"].replace(NB, " ") for r in rows[1:-1]] == ["−419 m", "+185 m", "−28 m", "−17 m"]


def test_time_chart_shows_only_estimable_years(res):
    for (name, pts, *_), key in zip(article.time_series(res), ("q2", "q2_from_request")):
        h = res[key]["horizons_years"]
        assert [p[0] for p in pts] == [0] + [int(y) for y, e in h.items() if e["estimable"]], name
        for y, val in pts[1:]:
            assert h[str(y)]["at_risk"] >= 30 and val == round(100 * h[str(y)]["cumulative_incidence"]["decision"], 2)


def test_committed_and_size_charts_are_the_results(res):
    b = res["q3"]["lists"]["B"]
    rows = article.committed_rows(res)
    assert [r["x1"] for r in rows] == [round(b["o"] / 1e9, 4), round(res["q3"]["s2026"] / 1e9, 4)]
    q4 = res["q4"]
    want = [res["q1"], q4["above_median"], q4["at_or_below_median"], q4["without_largest"]]
    assert [(r["lo"], r["hi"]) for r in article.size_rows(res)] == [(round(100 * e["r_low"], 2), round(100 * e["r_high"], 2))
                                                                   for e in want]


def test_base_chart_is_q5_beside_the_official_figures(res):
    q5 = res["q5"]
    rows = {r["y"]: r for r in article.base_rows(res)}
    for y in ("2020", "2021"):
        assert rows[f"{y} · from the lists"]["x1"] == round(q5["by_evidence_year"]["main"][y]["base"] / 1e9, 4)
        assert rows[f"{y} · Fund's annual report"]["x1"] == round(q5["official"][y]["czk"] / 1e9, 4)
    reg = q5["by_registration_year"]["main"]["2025"]
    r = rows["2025 · lists, registered that year"]
    assert (r["x0"], r["x1"]) == (round(reg["base_low"] / 1e9, 4), round(reg["base"] / 1e9, 4))


def test_headline_numbers_in_the_text(page, v):
    s = story(page)
    for k in ("promised", "paid", "r", "r_low", "r_high", "below", "above", "undecided", "cancelled", "median",
              "o_b", "s2026", "o_ratio", "o_r", "big", "small", "top5", "no_largest", "b20", "o20", "b21", "o21", "o25"):
        assert str(v[k]).replace(NB, " ") in s, k
    assert "nearly all paid" in s and "only narrowly" in s


def test_no_codes_in_the_visible_story(page):
    s = story(page)
    for code in ("Q1", "Q2", "Q3", "Q4", "Q5", "R_low", "R_high", "OOE", "OOR", "ŽOP", "P0", "P1", "S2026"):
        assert not re.search(rf"\b{re.escape(code)}\b", s), code
    assert not re.search(r"\b\d+P/\d{4}\b", text(page)), "an evidence number is shown"


def test_methods_carry_the_flags_the_exposures_and_the_disclosure(page, v):
    s = text(page)
    assert "The author builds production software for film crews (FilmRunner)." in s
    assert "509 rows" in s and "507" in s
    assert f"{v['over_p1']} of {v['n_decided_all']}" in s and v["excess"].replace(NB, " ") in s
    assert "web-search summary" in s and "faulty mask" in s and "total allocations" in s
    for tag in ("rebates-design", "rebates-data-step", "rebates-code"):
        assert tag in s


def test_listing_matches_the_results(v):
    works = tomllib.loads((article.ROOT / "docs" / "works.toml").read_text(encoding="utf-8"))["works"]
    w = next(w for w in works if w["href"] == f"texts/{article.SLUG}")
    for k in ("promised", "o_b"):
        assert v[k].replace(NB, " ") in w["finding"], k
    assert v["r"].replace(NB, " ") in w["finding"].replace(" to ", "–")
    assert f"{v['o_ratio']} times" in w["finding"] and w["label"] == "Pre-specified"


def test_every_token_and_citation_is_filled(page):
    assert "{{" not in page and "[[" not in page


def test_label_is_pre_specified_in_kicker_and_status(page):
    assert re.search(r'<p class="kicker">Research · Pre-specified', page)
    assert "<dt>status</dt><dd>research, pre-specified analysis" in page
