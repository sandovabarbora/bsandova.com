"""Tests of the outputs: summary file, SVG, and the page's style rules (design §4 and the spec's section 10)."""
from __future__ import annotations

import html as htmllib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import report as R

FAKE_SVG = "<svg><text>x</text></svg>"


def event(name, label, **kw):
    base = {"name": name, "event_date": "2023-09-27", "car_pct_uplift": 14.2, "placebo_p": 0.01, "holm_p": 0.02,
            "half_life_days": 4.0, "label": label, "falsification_p": None, "gates_label": False}
    return {**base, **kw}


def summary(label_a="positive", label_b="no detectable jump", fp=0.4):
    return {"events": [event("Stonestreet (Cam)", label_a, falsification_p=fp, gates_label=True),
                       event("Kevin James", label_b, half_life_days=None, holm_p=0.5, placebo_p=0.3)]}


@pytest.mark.parametrize("a", R.BLURB)
@pytest.mark.parametrize("b", R.BLURB)
def test_page_obeys_the_style_rules_for_every_label(a, b):
    page = R.render_html(summary(a, b), FAKE_SVG)
    for banned in ("<script", "<b>", "<strong>", "—"):
        assert banned not in page
    assert len(page.replace(FAKE_SVG, "").encode()) <= 4096
    text = htmllib.unescape(R.visible_text(page))
    assert ";" not in text
    assert "<table>" in page and "<details>" in page and "prefers-color-scheme" in page
    assert not re.search(r"font-weight:\s*(bold|[6-9]00)", page)


def test_page_with_a_falsification_hit_says_so():
    page = R.render_html(summary("inconclusive", fp=0.01), FAKE_SVG)
    assert "news about the show" in page


def test_page_links_the_sources():
    page = R.render_html(summary(), FAKE_SVG)
    assert page.count("<a href=") == 3 and "MacKinlay (1997)" in page


def test_summary_is_written_as_json(tmp_path):
    R.write_summary(tmp_path / "out" / "summary.json", {"a": 1, "d": pd.Timestamp("2023-01-01")})
    assert json.loads((tmp_path / "out" / "summary.json").read_text())["a"] == 1


def test_ar_svg_is_produced_and_small():
    pytest.importorskip("matplotlib")
    days = pd.date_range("2023-09-24", periods=34)
    ar = pd.Series([0.0] * 3 + [1.0 / (1 + i) for i in range(31)], index=days)
    svg = R.ar_svg({"Stonestreet (Cam)": ar}, {"Stonestreet (Cam)": "2023-09-27"})
    assert svg.lstrip().startswith("<?xml") and "<svg" in svg and "abnormal attention (log)" in svg
    assert len(svg.encode()) < R.MAX_SVG_BYTES


def test_estimation_svg_stops_before_the_event_window():
    pytest.importorskip("matplotlib")
    panel = pd.DataFrame({"A": range(100, 130), "B": range(10, 40)}, index=pd.date_range("2023-01-01", periods=30))
    svg = R.estimation_svg(panel, {"Cam": "2023-01-20"}, "2023-01-01")
    assert "up to 2023-01-20" in svg
