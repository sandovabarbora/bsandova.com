"""Tests of the outputs: summary file, SVG, and the page's style rules (design §4 and the spec's section 10)."""
from __future__ import annotations

import html as htmllib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import report as R

FAKE_SVG = "<svg><text>x</text></svg>"


def event(name, label, **kw):
    base = {"name": name, "event_date": "2023-09-27", "car_pct_uplift": 14.2, "excess_views": 12345.0, "placebo_p": 0.01,
            "holm_p": 0.02, "half_life_days": 4.0, "half_life_status": "observed", "label": label, "mdu80_pct": 8.7,
            "falsification_p": None, "cast_note": False}
    return {**base, **kw}


def summary(label_a="positive", label_b="no detectable jump", fp=0.4, power=20.0):
    return {"meta": {"falsification_power_pct": power},
            "events": [event("Stonestreet (Cam)", label_a, falsification_p=fp, cast_note=True),
                       event("Kevin James", label_b, half_life_days=None, half_life_status="censored", holm_p=0.5,
                             placebo_p=0.3)]}


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


def test_page_says_no_cast_wide_move_with_the_power_of_the_test():
    page = R.render_html(summary("positive", fp=0.4, power=20.4), FAKE_SVG)
    assert "No cast-wide move was seen, but the test's power is about 20 %." in page


def test_page_with_a_falsification_hit_describes_it_without_changing_the_label():
    page = R.render_html(summary("positive", fp=0.01), FAKE_SVG)
    assert "moved too, as a group" in page and "a jump, on average 14 %" in page


def test_no_detectable_jump_is_tied_to_the_minimum_detectable_uplift():
    page = R.render_html(summary("no detectable jump", "no detectable jump"), FAKE_SVG)
    assert "above about 9 % on average over the window would have been seen four times in five" in page


def test_a_censored_half_life_is_not_reported_as_a_number():
    page = R.render_html(summary("positive", "positive"), FAKE_SVG)
    assert "The peak had not halved by the end of the window." in page


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


def test_estimation_figure_has_one_panel_per_article_and_hides_blocked_and_later_days():
    pytest.importorskip("matplotlib")
    idx = pd.date_range("2023-01-01", periods=60)
    panel = pd.DataFrame({"Alpha": np.arange(100.0, 160.0), "Beta": np.arange(10.0, 70.0)}, index=idx)
    svg = R.estimation_svg(panel, ["Alpha", "Beta"], pd.Series(5.0, index=idx), "2023-02-10", [("2023-01-20", "2023-01-25")],
                           "2023-01-01")
    for title in ("Alpha", "Beta", "median of the reference pool", "up to 2023-02-10"):
        assert title in svg
