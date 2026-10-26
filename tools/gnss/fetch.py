"""Fetch-and-count runner of the GNSS data step (design §2, §3), one sampled day at a time.

For each sampled Wednesday: find the parts of the `prod-0` release by direct URL, download them (two at a time)
into a new empty scratch directory, stream them through count.py, delete them. An unreadable Wednesday is replaced
by its Thursday; if that is unreadable too, the day is lost. After the pass, the low-count rule (fewer than 70 % of
the median aircraft-file count of the four nearest sampled days) flags days, whose Thursday is then fetched.
Resumes: a day with a manifest is not fetched again. Progress goes to tools/data/gnss/fetch.log.

    nice -n 20 uv run --no-project --with shapely --with numpy --with pandas --with pyarrow --with orjson \
        python -I tools/gnss/fetch.py --days all
    ... python -I tools/gnss/fetch.py --kp      # GFZ Potsdam Kp file only
    ... python -I tools/gnss/fetch.py --preflight   # structure of one Wednesday per study year, no quality values
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import logging
import shutil
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script's own directory off the path

import count
import regions as R

DATA = R.DATA
DAYS = DATA / "days"
SCRATCH = DATA / "scratch"
LOG = DATA / "fetch.log"
UA = R.UA
FIRST, LAST = dt.date(2023, 3, 1), dt.date(2026, 10, 14)
LOW_SHARE = 0.70
NEIGHBOURS = 4
RETRIES = 5
BACKOFF_S = 30
KP_URL = "https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"
KP_NAME = "Kp_ap_Ap_SN_F107_since_1932.txt"
KP_DIR = DATA / "kp"
PREFLIGHT_DAYS = (dt.date(2023, 3, 15), dt.date(2024, 3, 6), dt.date(2025, 3, 5), dt.date(2026, 3, 4))
PREFLIGHT_OUT = R.ROOT / "docs/research/gnss-preflight.json"

log = logging.getLogger("gnss")


def sample_days() -> list[dt.date]:
    return [FIRST + dt.timedelta(weeks=k) for k in range((LAST - FIRST).days // 7 + 1)]


def study_year(d: dt.date) -> int:
    """Study year of a sampled Wednesday; a replacement Thursday is given the year of its Wednesday by the caller."""
    return (d.year - 2023) + (1 if d.month >= 3 else 0)


def easter(year: int) -> dt.date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    return dt.date(year, month, (h + l_ - 7 * m + 114) % 31 + 1)


def czech_holidays(year: int) -> dict[dt.date, str]:
    fixed = {(1, 1): "New Year / Restoration Day", (5, 1): "Labour Day", (5, 8): "Liberation Day",
             (7, 5): "Saints Cyril and Methodius", (7, 6): "Jan Hus Day", (9, 28): "Czech Statehood Day",
             (10, 28): "Independent Czechoslovak State Day", (11, 17): "Struggle for Freedom and Democracy Day",
             (12, 24): "Christmas Eve", (12, 25): "Christmas Day", (12, 26): "St Stephen's Day"}
    out = {dt.date(year, m, d): name for (m, d), name in fixed.items()}
    e = easter(year)
    out[e - dt.timedelta(days=2)] = "Good Friday"
    out[e + dt.timedelta(days=1)] = "Easter Monday"
    return out


def tag(d: dt.date) -> str:
    return f"v{d:%Y.%m.%d}-planes-readsb-prod-0"


def asset_url(d: dt.date, suffix: str) -> str:
    t = tag(d)
    return f"https://github.com/adsblol/globe_history_{d.year}/releases/download/{t}/{t}.{suffix}"


def part_suffixes():
    yield "tar"
    for a in "abcdefghijklmnopqrstuvwxyz":
        for b in "abcdefghijklmnopqrstuvwxyz":
            yield f"tar.{a}{b}"


class NetworkDown(count.StopRun):
    """A failure that is not a property of the day (no connection, 403/429/5xx or timeouts after every retry)."""


TRANSIENT = (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, OSError)


def _request(url: str, method: str = "GET", headers: dict | None = None):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=120)


def exists(url: str) -> bool:
    for attempt in range(RETRIES):
        try:
            with _request(url, "HEAD"):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            err = f"HTTP {e.code}"
        except TRANSIENT as e:
            err = f"{type(e).__name__}: {e}"
        log.warning("HEAD %s: %s (attempt %d)", url, err, attempt + 1)
        time.sleep(BACKOFF_S * 2 ** attempt)
    raise NetworkDown(f"HEAD {url}: {err} after {RETRIES} attempts")


def find_parts(d: dt.date) -> list[str]:
    """`.tar`, or `.tar.aa`, `.tar.ab`, ... probed in order until the first missing one; [] if none exists."""
    gen = part_suffixes()
    if exists(asset_url(d, next(gen))):
        return [asset_url(d, "tar")]
    parts = []
    for suf in gen:
        url = asset_url(d, suf)
        if not exists(url):
            break
        parts.append(url)
    return parts


def download(url: str, dest: Path) -> int:
    """Streams url to dest, resuming a partial file by Range. HTTP 404 raises OSError (the part is missing: the day is
    unreadable); any other failure that outlasts the retries raises NetworkDown and stops the run."""
    part = dest.with_suffix(dest.suffix + ".part")
    err = None
    for attempt in range(RETRIES):
        have = part.stat().st_size if part.exists() else 0
        try:
            with _request(url, headers={"Range": f"bytes={have}-"} if have else None) as r:
                resumed = bool(have) and r.status == 206
                length = r.headers.get("Content-Length")
                with open(part, "ab" if resumed else "wb") as f:
                    shutil.copyfileobj(r, f, 1 << 22)
            if length is not None and part.stat().st_size != (have if resumed else 0) + int(length):
                raise ConnectionError(f"short read: {part.stat().st_size} bytes")
            part.rename(dest)
            return dest.stat().st_size
        except urllib.error.HTTPError as e:
            if e.code == 416:  # already complete
                part.rename(dest)
                return dest.stat().st_size
            if e.code == 404:
                raise FileNotFoundError(f"{url}: HTTP 404") from e
            err = f"HTTP {e.code}"
        except TRANSIENT as e:
            err = f"{type(e).__name__}: {e}"
        log.warning("download %s: %s (attempt %d)", url, err, attempt + 1)
        time.sleep(BACKOFF_S * 2 ** attempt)
    raise NetworkDown(f"{url}: {err} after {RETRIES} attempts")


def fetch_and_count(d: dt.date, out_dir: Path, idx, index_path: Path) -> dict:
    """Counts one calendar day into out_dir; raises count.Unreadable if the day is unreadable by §2."""
    urls = find_parts(d)
    if not urls:
        raise count.Unreadable("release missing")
    scratch = SCRATCH / f"{d}"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    try:
        t0 = time.time()
        dests = [scratch / u.rsplit("/", 1)[1] for u in urls]
        try:
            with ThreadPoolExecutor(2) as ex:
                sizes = list(ex.map(download, urls, dests))
        except FileNotFoundError as e:  # a part that 404s; a local error while counting is not caught here
            raise count.Unreadable(f"download: {e}") from e
        t1 = time.time()
        log.info("%s: %d part(s), %.2f GB in %.0f s", d, len(urls), sum(sizes) / 1e9, t1 - t0)
        tmp = out_dir.with_name(out_dir.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        n = count.count_day(dests, tmp, str(d), idx, index_path)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        tmp.rename(out_dir)
        return {"date_used": str(d), "tag": tag(d), "parts": [u.rsplit("/", 1)[1] for u in urls], "bytes": sum(sizes),
                "download_seconds": round(t1 - t0, 1), **n}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def resolve_day(wed: dt.date, attempt: Callable[[dt.date], dict]) -> dict:
    """§2 replacement: the Wednesday, else the Thursday after it, else lost. `attempt` raises Unreadable."""
    reasons = {}
    for d, status in ((wed, "counted"), (wed + dt.timedelta(days=1), "replaced")):
        try:
            return {"wednesday": str(wed), "status": status, "study_year": study_year(wed), **attempt(d),
                    "unreadable": reasons}
        except count.Unreadable as e:
            reasons[str(d)] = str(e)
    return {"wednesday": str(wed), "status": "lost", "study_year": study_year(wed), "unreadable": reasons}


def nearest(wed: dt.date, counts: dict[dt.date, int], k: int = NEIGHBOURS) -> list[dt.date]:
    """The k sampled days nearest to wed with a count, ties to the earlier day."""
    others = sorted((d for d in counts if d != wed), key=lambda d: (abs((d - wed).days), d))
    return others[:k]


def low_days(counts: dict[dt.date, int]) -> dict[dt.date, float]:
    """Days below 70 % of the median aircraft-file count of their four nearest sampled days -> that median."""
    out = {}
    for d, n in counts.items():
        nb = nearest(d, counts)
        if nb:
            med = statistics.median(counts[x] for x in nb)
            if n < LOW_SHARE * med:
                out[d] = med
    return out


def read_manifest(wed: dt.date) -> dict | None:
    p = DAYS / str(wed) / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else None


def write_manifest(wed: dt.date, m: dict) -> None:
    p = DAYS / str(wed) / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")


def postpass(attempt: Callable[[dt.date, Path], dict]) -> None:
    """The low-count rule over all sampled days counted so far, judged on the counts before any flag."""
    man = {d: read_manifest(d) for d in sample_days()}
    missing = [d for d, m in man.items() if m is None]
    if missing:
        log.info("post-pass skipped: %d sampled days not yet fetched", len(missing))
        return
    counts = {d: m["trace_files"] for d, m in man.items() if m and m["status"] in ("counted", "replaced")
              and not m.get("low_checked")}
    all_counts = {d: m["trace_files"] for d, m in man.items() if m and m["status"] in ("counted", "replaced")}
    flagged = {d: med for d, med in low_days(all_counts).items() if d in counts}
    for d in counts:
        if d not in flagged:
            man[d]["low_checked"] = True
            write_manifest(d, man[d])
    for wed, med in sorted(flagged.items()):
        m = man[wed]
        day_dir = DAYS / str(wed)
        aside = DAYS / f"{wed}.low-{m['date_used']}"
        if aside.exists():
            shutil.rmtree(aside)
        day_dir.rename(aside)
        reasons = {**m.get("unreadable", {}), m["date_used"]: f"low count {m['trace_files']} < 70 % of median {med}"}
        log.info("%s: %s flagged low (%d files, median %.0f)", wed, m["date_used"], m["trace_files"], med)
        # Written before the Thursday is tried, so a run stopped half way resumes here and loses nothing.
        man[wed] = {"wednesday": str(wed), "status": "pending-thursday" if m["status"] == "counted" else "lost",
                    "study_year": m["study_year"], "unreadable": reasons, "low_checked": True, "low_median": med}
        write_manifest(wed, man[wed])
    for wed in sorted(d for d, m in man.items() if m["status"] == "pending-thursday"):
        try_thursday(wed, man[wed], attempt)


def try_thursday(wed: dt.date, m: dict, attempt: Callable[[dt.date, Path], dict]) -> None:
    day_dir = DAYS / str(wed)
    thu = wed + dt.timedelta(days=1)
    med = m["low_median"]
    reasons = dict(m["unreadable"])
    new = {**m, "status": "lost", "unreadable": reasons}
    try:
        r = attempt(thu, day_dir)
    except count.Unreadable as e:
        reasons[str(thu)] = str(e)
        shutil.rmtree(day_dir, ignore_errors=True)
    else:
        if r["trace_files"] < LOW_SHARE * med:
            reasons[str(thu)] = f"low count {r['trace_files']} < 70 % of median {med}"
            shutil.rmtree(day_dir, ignore_errors=True)
        else:
            new = {**new, "status": "replaced", **r}
    write_manifest(wed, new)


def parse_kp(text: str) -> dict[str, float | None]:
    """Kp_max per UT day; a day with any missing three-hour value (-1) is None."""
    out = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split()
        kp = [float(x) for x in f[7:15]]
        out[f"{f[0]}-{f[1]}-{f[2]}"] = None if min(kp) < 0 else max(kp)
    return out


def fetch_kp() -> Path:
    new = DATA / "kp.new"  # a fresh empty directory; the previous file stays until the new one is complete
    if new.exists():
        shutil.rmtree(new)
    new.mkdir(parents=True)
    download(KP_URL, new / KP_NAME)
    if KP_DIR.exists():
        shutil.rmtree(KP_DIR)
    new.rename(KP_DIR)
    dest = KP_DIR / KP_NAME
    R.record_hash(KP_NAME, R.sha256(dest))
    log.info("Kp file %s, sha256 %s", dest.name, R.sha256(dest))
    return dest


def run_preflight(days=PREFLIGHT_DAYS, out: Path = PREFLIGHT_OUT) -> dict:
    """Structure of one Wednesday per study year, streamed and deleted; no quality value is read (count.structure)."""
    report = {}
    for d in days:
        urls = find_parts(d)
        if not urls:
            report[str(d)] = {"error": "release missing"}
            continue
        scratch = SCRATCH / f"preflight-{d}"
        if scratch.exists():
            shutil.rmtree(scratch)
        scratch.mkdir(parents=True)
        try:
            dests = [scratch / u.rsplit("/", 1)[1] for u in urls]
            with ThreadPoolExecutor(2) as ex:
                list(ex.map(download, urls, dests))
            report[str(d)] = {"parts": [p.name for p in dests], **count.preflight(dests)}
        except (count.Unreadable, FileNotFoundError) as e:
            report[str(d)] = {"error": str(e)}
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        log.info("preflight %s done", d)
        out.write_text(json.dumps(report, indent=1) + "\n")
    return report


def select(spec: str) -> list[dt.date]:
    days = sample_days()
    if spec == "all":
        return days
    if ":" in spec:
        a, b = (dt.date.fromisoformat(x) for x in spec.split(":"))
        return [d for d in days if a <= d <= b]
    want = {dt.date.fromisoformat(x) for x in spec.split(",")}
    bad = want - set(days)
    if bad:
        raise SystemExit(f"not sampled Wednesdays: {sorted(map(str, bad))}")
    return sorted(want)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", help="all | YYYY-MM-DD[,YYYY-MM-DD...] | YYYY-MM-DD:YYYY-MM-DD")
    ap.add_argument("--kp", action="store_true", help="download the GFZ Kp file")
    ap.add_argument("--preflight", action="store_true", help="structure-only check of one Wednesday per study year")
    ap.add_argument("--no-postpass", action="store_true")
    ap.add_argument("--retry-lost", action="store_true", help="fetch again days whose manifest says lost")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOG, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler())
    if args.kp:
        fetch_kp()
    if args.preflight:
        run_preflight()
    if not args.days:
        return
    idx = R.load_index()
    index_path = R.cache_path()

    def attempt_into(day_dir: Path):
        return lambda d: fetch_and_count(d, day_dir, idx, index_path)

    todo = select(args.days)
    for i, wed in enumerate(todo, 1):
        m = read_manifest(wed)
        if m and (m["status"] != "lost" or not args.retry_lost):
            continue
        t0 = time.time()
        m = resolve_day(wed, attempt_into(DAYS / str(wed)))
        write_manifest(wed, m)
        log.info("[%d/%d] %s %s %s files in %.0f s", i, len(todo), wed, m["status"], m.get("trace_files", "-"),
                 time.time() - t0)
    if not args.no_postpass and args.days == "all":
        postpass(lambda d, day_dir: fetch_and_count(d, day_dir, idx, index_path))


if __name__ == "__main__":
    main()
