"""All network and file I/O of the meme event study: daily pageviews from the Wikimedia Analytics API, the title check
against the MediaWiki API (existence and redirects, no pageview numbers), and the CSV cache of the raw panel.

API facts verified against the Analytics API documentation and the Wikimedia API rate limits (see README): a 404 can
mean zero views or data not yet loaded, zero days are omitted from a series, 429 is throttling, a User-Agent is
required, and redirect titles are not counted as views of the page they point to.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from config import USER_AGENT

log = logging.getLogger(__name__)

AQS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
MEDIAWIKI = "https://en.wikipedia.org/w/api.php"
RETRY_STATUS = (429, 500, 502, 503)
PAUSE = 0.2
MAX_WAIT = 60.0


class ArticleNotFound(LookupError):
    """A title is missing, or points to another page. Never replaced by a guess (design §2)."""


def _stamp(day: str) -> str:
    return pd.Timestamp(day).strftime("%Y%m%d")


def _get(url: str, retries: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            if err.code not in RETRY_STATUS or attempt == retries:
                raise
            retry_after = err.headers.get("Retry-After") if err.headers else None
            wait = min(float(retry_after), MAX_WAIT) if retry_after and retry_after.isdigit() else 2.0 ** (attempt - 1)
            log.warning("HTTP %s, attempt %d of %d, waiting %.1f s", err.code, attempt, retries, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def fetch_pageviews(article: str, start: str, end: str, project: str = "en.wikipedia", retries: int = 3, *,
                    missing: str = "zero") -> pd.Series:
    """Daily user-agent views of one article, reindexed to every day of start..end. The API omits days without data:
    they are filled with 0 (the spec) or, with missing="nan", kept as NaN for the omitted-day rule of design §3."""
    url = (f"{AQS}/{project}/all-access/user/{urllib.parse.quote(article, safe='')}/daily/"
           f"{_stamp(start)}/{_stamp(end)}")
    try:
        body = _get(url, retries)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise ArticleNotFound(f"404 for {article!r} on {project} for {start}..{end}: the title does not exist, or the "
                                  "API holds no views for it. Do not guess a replacement.") from err
        raise RuntimeError(f"HTTP {err.code} for {article!r} after {retries} attempts") from err
    items = json.loads(body)["items"]
    got = pd.Series({pd.Timestamp(i["timestamp"][:8]): i["views"] for i in items}, dtype="float64")
    days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    out = got.reindex(days)
    filled = int(out.isna().sum())
    if filled:
        log.info("%s: %d of %d days missing in the API response, %s", article, filled, len(days),
                 "filled with 0" if missing == "zero" else "kept as missing")
    return (out.fillna(0.0) if missing == "zero" else out).rename(article)


def fetch_panel(articles: Sequence[str], start: str, end: str) -> pd.DataFrame:
    series = []
    for i, art in enumerate(articles):
        if i:
            time.sleep(PAUSE)
        series.append(fetch_pageviews(art, start, end, missing="nan"))
    return pd.concat(series, axis=1)


def verify_titles(articles: Sequence[str]) -> dict[str, str]:
    """Existence check through the MediaWiki API (prop=info), which returns no pageview numbers. Raises ArticleNotFound
    for a missing title, a redirect (its own views are not those of the page it points to) or a disambiguation page.
    Returns {title as given: normalised title}."""
    out, bad = {}, []
    for i in range(0, len(articles), 50):
        chunk = articles[i:i + 50]
        params = urllib.parse.urlencode({"action": "query", "titles": "|".join(chunk), "prop": "info|pageprops",
                                         "ppprop": "disambiguation", "format": "json", "formatversion": "2"})
        data = json.loads(_get(f"{MEDIAWIKI}?{params}", 3))["query"]
        normalised = {n["from"]: n["to"] for n in data.get("normalized", [])}
        pages = {p["title"]: p for p in data["pages"]}
        for art in chunk:
            title = normalised.get(art, art)
            page = pages.get(title)
            if page is None or page.get("missing") or page.get("invalid"):
                bad.append(f"{art}: does not exist")
            elif "redirect" in page:
                bad.append(f"{art}: is a redirect to another page")
            elif "disambiguation" in page.get("pageprops", {}):
                bad.append(f"{art}: is a disambiguation page")
            out[art] = title
    if bad:
        raise ArticleNotFound("title check failed, nothing is replaced by a guess: " + "; ".join(bad))
    return out


def save_panel(panel: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    panel.rename_axis("date").to_csv(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_csv(path, index_col="date", parse_dates=True)
    panel.index = pd.DatetimeIndex(panel.index, freq="D")
    return panel


def write_manifest(path: Path, digest: str, source: Path, start: str, end: str) -> None:
    line = f"{digest}  {source.name}  Wikimedia Analytics API per-article daily {start}..{end}  {dt.date.today()}\n"
    path.write_text(line)
