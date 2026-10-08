"""Screening step of the rain-delays design (§3, rule 1): PID announcements only, no delay value.

pid.cz removes a change page once the change is over, so the announcements are read from the Internet Archive:
every archived page under pid.cz/zmena/ (one page per closure, diversion or replacement service, with its lines and
its first and last day) and every archived snapshot of the list at pid.cz/zmeny/ in the window. The list snapshots
are used to measure how many announced changes the archived pages miss.

Output: docs/research/rain-delays-screen.json — one row per announced change that touches a tram or city bus line
on at least one date of 15 March – 8 September 2025, and the coverage counts. Raw pages are cached in
tools/data/rain/pid/ (not committed).

    uv run python tools/rain/screen_pid.py
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "tools/data/rain/pid"
OUT = ROOT / "docs/research/rain-delays-screen.json"
START, END = date(2025, 3, 15), date(2025, 9, 8)
UA = "bsandova.com research"
CDX = "https://web.archive.org/cdx/search/cdx"


def fetch(url: str, path: Path) -> str:
    failed = path.with_suffix(".failed")  # the archive did not serve it four times; delete the marker to retry
    if not path.exists() and not failed.exists():
        for attempt in range(4):
            r = subprocess.run(["curl", "-sfL", "--compressed", "-A", UA, url], capture_output=True)
            if r.returncode == 0 and r.stdout:
                path.write_bytes(r.stdout)
                break
            time.sleep(5 * (attempt + 1))
        else:
            failed.touch()
        time.sleep(1)
    return path.read_text("utf-8", "ignore") if path.exists() else ""


def text(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", "\n", s))
    return "\n".join(x.strip() for x in s.splitlines() if x.strip())


def cdx(url: str, prefix: bool) -> list[list[str]]:
    q = f"{CDX}?url={url}&from=20240901&to=20251001&output=json&fl=timestamp,original&filter=statuscode:200"
    q += "&matchType=prefix&collapse=urlkey" if prefix else "&collapse=timestamp:8"
    path = CACHE / f"cdx_{'pages' if prefix else 'list'}.json"
    return json.loads(fetch(q, path))[1:]


def when(s: str) -> date | None:
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s)
    return date(int(m[3]), int(m[2]), int(m[1])) if m else None


def lines(block: str) -> list[str]:
    return [x for x in re.split(r"[,\s]+", block) if re.fullmatch(r"[A-Z]{0,2}\d{1,3}|[A-C]", x)]


def page(ts: str, url: str) -> dict | None:
    key = re.search(r"/zmena/(.+?)/?$", url)[1]
    t = text(fetch(f"https://web.archive.org/web/{ts}id_/{url}", CACHE / "pages" / f"{key}.html"))
    m = re.search(r"\n(Výluka|Mimořádnost|Trvalá změna|[^\n:]{1,30}): ([^\n]+)\nNaposledy aktualizováno", t)
    od = re.search(r"\nOd\n([^\n]+)", t)
    do = re.search(r"\nDo\n([^\n]+)", t)
    ln = re.search(r"Dotčené linky\n(.+?)\nDruh události", t, flags=re.S)
    kind = re.search(r"Druh události\n([^\n]+)", t)
    if not (m and od and ln and when(od[1])):
        return None
    return {"id": key, "url": url, "archived": ts[:8], "category": m[1], "title": m[2].strip(),
            "first": str(when(od[1])), "last": str(when(do[1])) if do and when(do[1]) else None,
            "last_raw": do[1].strip() if do else None, "lines": lines(ln[1]),
            "open_ended": bool(do and "odvolání" in do[1]),
            "kind": kind[1].strip() if kind else None}


def snapshot(ts: str) -> list[dict]:
    t = text(fetch(f"https://web.archive.org/web/{ts}id_/https://pid.cz/zmeny/", CACHE / "list" / f"{ts}.html"))
    rows = t[t.find("trvalé změny"):].splitlines()
    out, pending, i = [], [], 0
    while i < len(rows):
        x = rows[i]
        if x in ("Výluka", "Mimořádnost", "Trvalá změna") and i + 2 < len(rows):
            j, frm, to = i + 2, rows[i + 1], ""
            if rows[j].startswith("- "):
                to, j = rows[j][2:].strip(), j + 1
            if rows[j].startswith("před "):
                j += 1
            out.append({"snapshot": ts[:8], "lines": pending, "category": x, "from": frm, "to": to, "title": rows[j]})
            pending, i = [], j + 1
            continue
        if re.fullmatch(r"([A-Z]{0,2}\d{1,3}|[A-C])(,\s*([A-Z]{0,2}\d{1,3}|[A-C]))*,?", x):
            pending += lines(x)
        i += 1
    return out


def mode(line: str) -> str | None:
    """Tram (day 1-39, night 90-99), city bus (100-299), else None: metro, rail, regional and night buses."""
    if not line.isdigit():
        return None
    n = int(line)
    return "tram" if n < 40 or 90 <= n <= 99 else "bus" if 100 <= n < 300 else None


def city_surface(line: str) -> bool:
    return mode(line) is not None


# Rule 1 covers "a closure, diversion or replacement service". A stop moved or skipped on an unchanged route is not one.
ROUTE_KINDS = ("Změna trasy", "Odklon", "Přerušení provozu", "Náhradní doprava", "Omezení provozu", "Zrušení linky")
ROUTE_WORDS = ("přerušení provozu", "změna trasy", "odklon", "náhradní", "omezení provozu")


def snap_day(s: str, snap: date, first: date | None = None) -> date | None:
    s = s.replace("\xa0", " ")
    if "dnes" in s:
        return snap
    if "zítra" in s:
        return snap + timedelta(days=1)
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.(?:\s*(\d{4}))?", s)
    if m:
        return date(int(m[3] or snap.year), int(m[2]), int(m[1]))
    return first if re.fullmatch(r"\d{1,2}:\d{2}", s.strip()) else None


def spans(rows: list[dict], listed: list[dict]) -> list[dict]:
    """One span per announcement: lines, first and last day, source. Snapshot-only closures fill the pages' gaps."""
    out = []
    for r in rows:
        if r["kind"] and any(k in r["kind"] for k in ROUTE_KINDS):
            out.append({"source": r["url"], "title": r["title"], "lines": r["lines"], "first": r["first"],
                        "last": r["last"] or END.isoformat(), "open_ended": r["open_ended"] and not r["last"],
                        "prague": r["url"].rstrip("/").endswith("-3")})
    for s in listed:
        if not any(w in s["title"].lower() for w in ROUTE_WORDS):
            continue
        snap = date.fromisoformat(f"{s['snapshot'][:4]}-{s['snapshot'][4:6]}-{s['snapshot'][6:]}")
        if s["from"].startswith("provoz"):  # "provoz obnoven: <day>": only the last day is known
            first = last = snap_day(s["from"].split(":", 1)[1], snap)
        else:
            first = snap_day(s["from"], snap)
            last = END if "odvolání" in s["to"] else snap_day(s["to"], snap, first) if s["to"] else first
        if first and last:
            out.append({"source": f"pid.cz/zmeny/ snapshot {s['snapshot']}", "title": s["title"], "lines": s["lines"],
                        "first": first.isoformat(), "last": last.isoformat(), "open_ended": "odvolání" in s["to"],
                        "prague": "tramvaj" in s["title"].lower()})
    return out


def line_days(spans_: list[dict], whole_window: bool) -> dict[str, dict[str, list[str]]]:
    """Line-days to exclude. Tram numbers count only from Prague announcements (regional towns reuse 1-39 for buses).
    whole_window=False drops spans in force on every day of the window (see rain-delays-screen.md)."""
    days: dict[str, dict[str, set[str]]] = {"tram": {}, "bus": {}}
    for sp in spans_:
        if not whole_window and sp["first"] <= START.isoformat() and sp["last"] >= END.isoformat():
            continue
        d = max(date.fromisoformat(sp["first"]), START)
        while d <= min(date.fromisoformat(sp["last"]), END):
            for ln in sp["lines"]:
                if mode(ln) == "bus" or (mode(ln) == "tram" and sp["prague"]):
                    days[mode(ln)].setdefault(ln, set()).add(d.isoformat())
            d += timedelta(days=1)
    return {m: {ln: sorted(v) for ln, v in sorted(x.items(), key=lambda kv: int(kv[0]))} for m, x in days.items()}


def main() -> None:
    (CACHE / "pages").mkdir(parents=True, exist_ok=True)
    (CACHE / "list").mkdir(parents=True, exist_ok=True)
    latest: dict[str, tuple[str, str]] = {}
    for ts, url in cdx("pid.cz/zmena/", prefix=True):
        m = re.match(r"https?://(?:www\.)?pid\.cz/zmena/([a-z0-9-]+)/?$", url.split("?")[0])
        if m and ts > latest.get(m[1], ("",))[0]:
            latest[m[1]] = (ts, f"https://pid.cz/zmena/{m[1]}/")
    # Planned changes only. Suffix -1 pages are unplanned incidents (mimořádnosti): rain can cause them, so excluding
    # them would remove part of the effect. Prague planned changes (-3) are fetched first, regional ones (-2) last.
    order = {"3": 0, "9": 1, "4": 2, "2": 3}
    pages = sorted((v for k, v in latest.items() if k.rsplit("-", 1)[1] in order),
                   key=lambda v: (order[v[1].rstrip("/").rsplit("-", 1)[1]], v[0]))
    with ThreadPoolExecutor(3) as pool:
        parsed = list(pool.map(lambda v: page(*v), pages))
    rows, unparsed = [], []
    for (ts, url), r in zip(pages, parsed):
        if r is None or r["category"] != "Výluka":
            if r is None:
                unparsed.append(url)
            continue
        first = date.fromisoformat(r["first"])
        last = date.fromisoformat(r["last"]) if r["last"] else END  # "do odvolání" = until further notice
        if first <= END and last >= START and any(city_surface(x) for x in r["lines"]):
            rows.append(r)
    snaps = [x for ts, _ in cdx("pid.cz/zmeny/", prefix=False) if START.isoformat().replace("-", "") <= ts[:8] <= "20250908"
             for x in snapshot(ts)]
    titles = {r["title"] for r in rows}
    listed = [s for s in snaps if s["category"] == "Výluka" and any(city_surface(x) for x in s["lines"])]
    matched = [s for s in listed if s["title"] in titles]
    sp = spans(rows, [s for s in listed if s["title"] not in titles])
    excl = line_days(sp, whole_window=False)
    literal = line_days(sp, whole_window=True)
    OUT.write_text(json.dumps({
        "generated": datetime.now().isoformat(timespec="seconds"),
        "window": [START.isoformat(), END.isoformat()],
        "archived_pages": len(pages), "unparsed_pages": len(unparsed),
        "changes_in_window_city_surface": len(rows),
        "coverage": {"list_snapshots": len({s["snapshot"] for s in snaps}),
                     "closures_listed_unique": len({s["title"] for s in listed}),
                     "of_which_with_archived_page": len({s["title"] for s in matched})},
        "missing_from_pages": sorted({(s["title"], s["from"], s["to"], ",".join(s["lines"])) for s in listed
                                      if s["title"] not in titles}),
        "excluded_line_days": {m: sum(len(v) for v in x.values()) for m, x in excl.items()},
        "excluded_line_days_literal": {m: sum(len(v) for v in x.values()) for m, x in literal.items()},
        "whole_window_spans": sorted({(x["title"], x["first"], x["last"]) for x in sp
                                      if x["first"] <= START.isoformat() and x["last"] >= END.isoformat()}),
        "open_ended_spans_to_window_end": sum(1 for x in sp if x["open_ended"]),
        "exclusions": excl,
        "exclusions_literal": literal,
        "spans": sorted(sp, key=lambda x: x["first"]),
        "changes": sorted(rows, key=lambda r: r["first"]),
    }, ensure_ascii=False, indent=1))
    print(f"{len(sp)} spans; excluded line-days {dict((m, sum(len(v) for v in x.values())) for m, x in excl.items())}")
    print(f"{len(rows)} changes in window; coverage {len({s['title'] for s in matched})}/{len({s['title'] for s in listed})}")


if __name__ == "__main__":
    main()
