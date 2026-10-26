"""Tests of the Wikimedia calls with urlopen mocked: no request leaves the machine (design §2, §3)."""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from email.message import Message
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch as F


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def body(days: dict[str, int]) -> Resp:
    items = [{"project": "en.wikipedia", "article": "x", "granularity": "daily", "timestamp": d + "00",
              "access": "all-access", "agent": "user", "views": v} for d, v in days.items()]
    return Resp(json.dumps({"items": items}).encode())


def http_error(code, retry_after=None):
    hdrs = Message()
    if retry_after:
        hdrs["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://x", code, "err", hdrs, io.BytesIO(b""))


@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(F.time, "sleep", lambda s: seen.append(("sleep", s)))
    return seen


def script(monkeypatch, calls, answers):
    answers = list(answers)

    def fake(req, timeout=None):
        calls.append(("get", req.full_url, req.get_header("User-agent")))
        a = answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a
    monkeypatch.setattr(F.urllib.request, "urlopen", fake)


def test_missing_days_are_filled_with_zero(monkeypatch, calls):
    script(monkeypatch, calls, [body({"20230101": 10, "20230103": 30})])
    s = F.fetch_pageviews("Eric_Stonestreet", "2023-01-01", "2023-01-03")
    assert s.tolist() == [10, 0, 30]
    assert s.index.equals(pd.date_range("2023-01-01", "2023-01-03"))


def test_omitted_days_can_be_kept_as_missing(monkeypatch, calls):
    script(monkeypatch, calls, [body({"20230101": 10, "20230103": 30}), body({"20230101": 10, "20230103": 30})])
    s = F.fetch_pageviews("A", "2023-01-01", "2023-01-03", missing="nan")
    assert s.iloc[[0, 2]].tolist() == [10, 30] and s.isna().tolist() == [False, True, False]
    panel = F.fetch_panel(["A"], "2023-01-01", "2023-01-03")                # the panel keeps the hole for the §3 rule
    assert panel["A"].isna().tolist() == [False, True, False]


def test_diacritics_and_apostrophe_are_encoded_and_the_user_agent_is_sent(monkeypatch, calls):
    script(monkeypatch, calls, [body({"20230101": 1}), body({"20230101": 1})])
    F.fetch_pageviews("Sofía_Vergara", "2023-01-01", "2023-01-01")
    F.fetch_pageviews("Ed_O'Neill", "2023-01-01", "2023-01-01")
    urls = [c[1] for c in calls if c[0] == "get"]
    assert "Sof%C3%ADa_Vergara" in urls[0] and "Ed_O%27Neill" in urls[1]
    assert urls[0].endswith("/all-access/user/Sof%C3%ADa_Vergara/daily/20230101/20230101")
    assert calls[0][2] == "bsandova-meme-event-study/0.1 (https://bsandova.com)"
    assert "@" not in calls[0][2]


def test_retries_with_exponential_backoff_then_succeeds(monkeypatch, calls):
    script(monkeypatch, calls, [http_error(429), http_error(503), body({"20230101": 5})])
    assert F.fetch_pageviews("A", "2023-01-01", "2023-01-01").tolist() == [5]
    assert [c[1] for c in calls if c[0] == "sleep"] == [1.0, 2.0]


def test_retry_after_header_is_honoured(monkeypatch, calls):
    script(monkeypatch, calls, [http_error(429, "7"), body({"20230101": 5})])
    F.fetch_pageviews("A", "2023-01-01", "2023-01-01")
    assert [c[1] for c in calls if c[0] == "sleep"] == [7.0]


def test_gives_up_after_three_attempts(monkeypatch, calls):
    script(monkeypatch, calls, [http_error(500), http_error(502), http_error(503)])
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        F.fetch_pageviews("A", "2023-01-01", "2023-01-01")
    assert sum(c[0] == "get" for c in calls) == 3


def test_404_raises_at_once_without_retry(monkeypatch, calls):
    script(monkeypatch, calls, [http_error(404)])
    with pytest.raises(F.ArticleNotFound, match="Do not guess a replacement"):
        F.fetch_pageviews("Nobody_Here", "2023-01-01", "2023-01-01")
    assert sum(c[0] == "get" for c in calls) == 1


def test_other_http_errors_are_not_retried(monkeypatch, calls):
    script(monkeypatch, calls, [http_error(403)])
    with pytest.raises(RuntimeError, match="HTTP 403"):
        F.fetch_pageviews("A", "2023-01-01", "2023-01-01")


def test_panel_pauses_between_requests(monkeypatch, calls):
    script(monkeypatch, calls, [body({"20230101": 1}), body({"20230101": 2}), body({"20230101": 3})])
    panel = F.fetch_panel(["A", "B", "C"], "2023-01-01", "2023-01-01")
    assert list(panel.columns) == ["A", "B", "C"] and panel.iloc[0].tolist() == [1, 2, 3]
    assert [c for c in calls if c[0] == "sleep"] == [("sleep", 0.2), ("sleep", 0.2)]


def pages(*rows, normalized=()):
    return Resp(json.dumps({"query": {"normalized": [{"from": a, "to": b} for a, b in normalized],
                                      "pages": list(rows)}}).encode())


def test_title_check_returns_normalised_titles_and_asks_for_no_views(monkeypatch, calls):
    script(monkeypatch, calls, [pages({"title": "Eric Stonestreet", "pageid": 1}, {"title": "Sofía Vergara", "pageid": 2},
                                      normalized=[("Eric_Stonestreet", "Eric Stonestreet"),
                                                  ("Sofía_Vergara", "Sofía Vergara")])])
    out = F.verify_titles(["Eric_Stonestreet", "Sofía_Vergara"])
    assert out == {"Eric_Stonestreet": "Eric Stonestreet", "Sofía_Vergara": "Sofía Vergara"}
    url = calls[0][1]
    assert "prop=info" in url and "pageviews" not in url and "Sof%C3%ADa" in url


def test_title_check_stops_on_missing_titles_and_redirects(monkeypatch, calls):
    script(monkeypatch, calls, [pages({"title": "Gary Valentine", "redirect": True, "pageid": 3},
                                      {"title": "Nobody Here", "missing": True})])
    with pytest.raises(F.ArticleNotFound) as e:
        F.verify_titles(["Gary Valentine", "Nobody Here"])
    msg = str(e.value)
    assert "Gary Valentine: is a redirect" in msg and "Nobody Here: does not exist" in msg and "guess" in msg


def test_panel_cache_round_trip_and_hash(tmp_path):
    panel = pd.DataFrame({"A": [1.0, 0.0, 3.0]}, index=pd.date_range("2023-01-01", periods=3))
    path = tmp_path / "raw" / "pageviews.csv"
    digest = F.save_panel(panel, path)
    back = F.load_panel(path)
    assert back["A"].tolist() == [1.0, 0.0, 3.0] and back.index.freqstr == "D"
    assert len(digest) == 64
    F.write_manifest(tmp_path / "m.sha256", digest, path, "2023-01-01", "2023-01-03")
    assert digest in (tmp_path / "m.sha256").read_text()


def test_title_check_stops_on_a_disambiguation_page(monkeypatch, calls):
    script(monkeypatch, calls, [pages({"title": "Rico Rodriguez", "pageid": 4, "pageprops": {"disambiguation": ""}},
                                      normalized=[("Rico_Rodriguez", "Rico Rodriguez")])])
    with pytest.raises(F.ArticleNotFound, match="Rico_Rodriguez: is a disambiguation page"):
        F.verify_titles(["Rico_Rodriguez"])
    assert "ppprop=disambiguation" in calls[0][1]


def test_title_check_asks_in_chunks_of_fifty(monkeypatch, calls):
    names = [f"A{i}" for i in range(120)]
    script(monkeypatch, calls, [pages(*({"title": n} for n in names[i:i + 50])) for i in (0, 50, 100)])
    assert len(F.verify_titles(names)) == 120
    assert sum(c[0] == "get" for c in calls) == 3
