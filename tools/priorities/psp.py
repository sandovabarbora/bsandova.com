"""Extension of the priorities design (§2.2): the Chamber of Deputies' stenographic records from psp.cz as speeches.

`download` fetches the per-sitting zip archives of each term from https://www.psp.cz/eknih/<term>/stenprot/zip/
(at most one request a second) to tools/data/priorities/psp/<term>/, and records URL, size and SHA-256 in
docs/research/priorities-psp-manifest.json. Where a zip answers 404 (all of 2002ps, the latest 2025ps sittings),
the sitting's HTML pages are fetched one by one (sittings ending in 2004 or later only) and packed into a local zip
of the same layout. Some archives carry stale day files (2017ps sittings with 2021ps day pages); where the day
files disagree with the days the zip index lists, the day files served online go into <sitting>-days.zip.
`parse` splits the pages into speeches (a speech runs from a speaker's label to the next label or the end of the
day) and writes tools/data/priorities/psp_speeches.parquet: id, term, sitting, date, page, seq, speaker, role,
chair (the label is the presiding role: "Předseda/Místopředseda PSP", "Předsedající"), text, word_count, notes.
Transcribers' notes in parentheses (applause, interjections, times) are taken out of the text, as in ParlaMint;
agenda headings (centred paragraphs), vote links and pages not yet transcribed are not speech. Nothing here reads
topics.

    nice -n 20 uv run --no-project --with certifi python -I tools/priorities/psp.py download
    nice -n 20 uv run --no-project --with pandas --with pyarrow python -I tools/priorities/psp.py parse
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import ssl
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools/data/priorities/psp"
OUT = ROOT / "tools/data/priorities/psp_speeches.parquet"
MANIFEST = ROOT / "docs/research/priorities-psp-manifest.json"
BASE = "https://www.psp.cz/eknih/{term}/stenprot/"
TERMS = ("2002ps", "2006ps", "2010ps", "2013ps", "2017ps", "2021ps", "2025ps")
HTML_FROM_YEAR = 2004  # first year needed by the extension; earlier 2002ps sittings are not fetched page by page
UA = {"User-Agent": "bsandova.com research"}
MONTHS = {m: i + 1 for i, m in enumerate(("ledna", "února", "března", "dubna", "května", "června", "července",
                                          "srpna", "září", "října", "listopadu", "prosince"))}
CHAIR = re.compile(r"^(Předseda|Předsedkyně|Místopředseda|Místopředsedkyně) PSP$|^Předsedající")
UPPER = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
ROLE_WORDS = {"Poslanec", "Poslankyně", "Senátor", "Senátorka", "Předsedající", "Pan", "Paní"}

_last = [0.0]


def get(url: str, tries: int = 4) -> bytes | None:
    """GET politely (one request a second); None on 404."""
    import certifi
    tls = ssl.create_default_context(cafile=certifi.where())
    for i in range(tries):
        time.sleep(max(0.0, 1.0 - (time.monotonic() - _last[0])))
        _last[0] = time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300, context=tls) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == tries - 1:
                raise
        except OSError:
            if i == tries - 1:
                raise
        time.sleep(5 * (i + 1))
    raise AssertionError


def decode(raw: bytes) -> str:
    m = re.search(rb"charset=([\w-]+)", raw[:2000])
    return raw.decode(m.group(1).decode() if m else "cp1250", errors="replace")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_dates(page: str) -> dict[str, list[date]]:
    """The days of each sitting as the term's zip index lists them, e.g. "(30. listopadu, 1. prosince 2017)"."""
    out = {}
    for name, txt in re.findall(r'href="(\d+schuz\.zip)"[^(]*\(([^)]*)\)', page):
        toks = re.findall(r"(\d{1,2})\.(?:\s+([^\s,\d]+))?(?:\s+(\d{4}))?", html.unescape(txt).replace("\xa0", " "))
        days, month, year = [], None, None
        for d, m, y in reversed(toks):
            year, month = int(y) if y else year, MONTHS.get(m, month) if m else month
            days.append(date(year, month, int(d)))
        out[name] = days[::-1]
    return out


def sittings(term: str) -> dict[str, list[date]]:
    """The term's zip index, saved under the term's folder, as {zip name: days}."""
    raw = get(BASE.format(term=term) + "zip/")
    (RAW / term).mkdir(parents=True, exist_ok=True)
    (RAW / term / "zip-index.html").write_bytes(raw)
    return index_dates(decode(raw))


def zip_days(path: Path) -> list[date]:
    with zipfile.ZipFile(path) as z:
        names = sorted((day_of(n)[1], n) for n in z.namelist() if day_of(n))
        return [day_date(decode(z.read(n))) for _, n in names]


def pack(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in sorted(files):
            z.writestr(zipfile.ZipInfo(fname, (1980, 1, 1, 0, 0, 0)), files[fname])
    return buf.getvalue()


def fetch_days(term: str, name: str) -> bytes | None:
    """The sitting's day files as served online (N-k.html), packed into a zip; some archives carry stale ones."""
    folder = BASE.format(term=term) + name.removesuffix(".zip") + "/"
    index = get(folder + "index.htm")
    if index is None:
        return None
    files = {}
    for day in sorted(set(re.findall(r'href="(\d+-\d+\.html?)"', decode(index)))):
        body = get(folder + day)
        if body is not None:
            files[day] = body
    return pack(files) if files else None


def fetch_html_sitting(term: str, name: str) -> bytes | None:
    """The sitting's index, day files and pages fetched one by one, packed into a zip of the archive's layout."""
    folder = BASE.format(term=term) + name.removesuffix(".zip") + "/"
    index = get(folder + "index.htm")
    if index is None:
        return None
    files = {"index.htm": index}
    for day in sorted(set(re.findall(r"(\d+-\d+\.html?)", decode(index)))):
        body = get(folder + day)
        if body is not None:
            files[day] = body
    linked = sorted({p for f in files.values() for p in re.findall(r"(s\d{6,}\.htm)", decode(f))})
    if not linked:
        return None
    stem, width = linked[0][:4], len(linked[0]) - 8
    last = max(int(p[4:-4]) for p in linked)
    n = 1
    while True:
        page = f"{stem}{n:0{width}d}.htm"
        body = get(folder + page)
        if body is None and n > last:
            break
        if body is not None:
            files[page] = body
        n += 1
    return pack(files)


def save(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".part").write_bytes(body)
    path.with_suffix(".part").rename(path)


def entry(term: str, name: str, url: str, path: Path, old: dict) -> dict:
    rel = str(path.relative_to(ROOT))
    if rel in old and old[rel]["sha256"] == sha256(path):
        return old[rel]
    if path.suffix != ".zip":
        source = "zip index"
    elif path.stem.endswith("-days"):
        source = "day files fetched online, replacing the archive's"
    else:
        with zipfile.ZipFile(path) as z:
            packed = all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist())
        source = "html pages packed locally" if packed else "zip"
    return {"term": term, "sitting": name, "url": url, "source": source, "path": rel,
            "bytes": path.stat().st_size, "sha256": sha256(path), "retrieved": date.today().isoformat()}


def download() -> None:
    old = {e["path"]: e for e in json.loads(MANIFEST.read_text())["files"]} if MANIFEST.exists() else {}
    files, missing = [], []
    for term in sorted(TERMS, key=lambda t: t == "2002ps"):  # the slow page-by-page term last
        index = sittings(term)
        files.append(entry(term, "index", BASE.format(term=term) + "zip/", RAW / term / "zip-index.html", {}))
        for name, days in index.items():
            path, folder = RAW / term / name, BASE.format(term=term) + name.removesuffix(".zip") + "/"
            url = BASE.format(term=term) + "zip/" + name
            if not path.exists():
                body = get(url)
                if body is None and days and days[-1].year >= HTML_FROM_YEAR:
                    body, url = fetch_html_sitting(term, name), folder
                if body is None:
                    missing.append({"term": term, "sitting": name, "days": [d.isoformat() for d in days]})
                    print(f"{term}/{name}: not available", flush=True)
                    continue
                save(path, body)
            elif rel_url := old.get(str(path.relative_to(ROOT)), {}).get("url"):
                url = rel_url
            files.append(entry(term, name, url, path, old))
            supplement = path.with_name(path.stem + "-days.zip")
            if not supplement.exists() and zip_days(path) != days:
                body = fetch_days(term, name)
                if body is not None:
                    save(supplement, body)
            if supplement.exists():
                files.append(entry(term, name, folder, supplement, old))
            print(f"{term}/{name}: {files[-1]['source']}", flush=True)
        MANIFEST.write_text(json.dumps({
            "design": "docs/research/priorities-design.md (§2.2, extension)",
            "note": "psp.cz stenographic records; tools/data/priorities/ is not committed. Where the zip archive "
                    "answers 404 (all of 2002ps, the latest 2025ps sittings), sittings ending in 2004 or later were "
                    "fetched page by page and packed into a zip with fixed timestamps; their hash is of that zip. "
                    "Where an archive's day files disagree with the days of the zip index (stale day files, "
                    "e.g. 2017ps sittings carrying 2021ps day pages), the day files served online are packed "
                    "into <sitting>-days.zip and used instead.",
            "files": files, "not_available": missing}, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(files)} files, {len(missing)} not available -> {MANIFEST.relative_to(ROOT)}")


# ---- parse

def strip_tags(s: str) -> str:
    s = re.sub(r"<!--\s*sttm\s*-->.*?<!--\s*ettm\s*-->", " ", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


NOTE = re.compile(rf"\((?=[^()]{{0,400}}\))\s*(?:[{UPPER}][^()]*?[a-záčďéěíňóřšťúůýž][^()]*?|\d{{1,2}}[.:]\d{{2}} hod[^()]*"
                  rf"|pokračuje[^()]*)\)\.?")


def clean(text: str) -> tuple[str, int]:
    """Text without transcribers' notes in parentheses and page-end marks; the number of notes taken out."""
    text, n = NOTE.subn(" ", text)
    text = text.replace("***", " ")
    return re.sub(r"\s+", " ", text).strip(), n


SPEAKER = re.compile(r"^\s*(?:<b>\s*)*<a\b[^>]*>(?P<label>[^<]{3,200})</a>\s*(?:</b>\s*)*(?:<b>\s*:\s*</b>|:+)?",
                     re.IGNORECASE)


def split_label(label: str) -> tuple[str, str]:
    """('Ministr obrany ČR', 'Martin Stropnický') from the label; the name is the trailing run of capitalised
    words after the first word."""
    words = label.split()
    i = len(words)
    while i > 1 and (words[i - 1][:1].isupper() and words[i - 1] not in ("PSP", "ČR", "ČNB", "EU", "NKÚ")
                     or i == len(words) and words[i - 1] in ("st.", "ml.")):
        i -= 1
    if i == 1 and len(words) <= 3 and words[0] not in ROLE_WORDS:  # a bare name, e.g. "Zbyněk Stanjura"
        return "", label
    return " ".join(words[:i]), " ".join(words[i:])


def paragraphs(page: str) -> list[str]:
    """The page's paragraphs between the transcript markers (<!-- eh/ex --> ... <!-- sf/sy -->, or the text div
    of the newest pages), each cut at its </p>; none for a page not yet transcribed."""
    if "nebyl dosud přepsán" in page:
        return []
    start = re.search(r"<!--\s*e[hx]\s*-->", page, flags=re.IGNORECASE) or re.search(r"<div class=\"text\b", page)
    body = page[start.end():] if start else page
    end = re.search(r"<!--\s*s[fy]\s*-->|<!--/ Main content -->", body, flags=re.IGNORECASE)
    body = body[:end.start()] if end else body
    return [re.split(r"</p\s*>", p, maxsplit=1, flags=re.IGNORECASE)[0] for p in re.split(r"<p\b", body, flags=re.IGNORECASE)[1:]]


def day_of(name: str) -> tuple[int, int] | None:
    m = re.fullmatch(r"(\d+)-(\d+)\.html?", name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def day_date(page: str) -> date | None:
    pattern = r"(\d{1,2})\.\s+(" + "|".join(MONTHS) + r")\s+(\d{4})"
    m = re.search(pattern, strip_tags(page.split("</title>")[0])) or re.search(pattern, strip_tags(page))
    return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))) if m else None


def parse_sitting(term: str, path: Path) -> tuple[list[dict], dict]:
    with zipfile.ZipFile(path) as z:
        pages = {n: decode(z.read(n)) for n in z.namelist()}
    supplement = path.with_name(path.stem + "-days.zip")
    if supplement.exists():
        pages = {n: p for n, p in pages.items() if not day_of(n)}
        with zipfile.ZipFile(supplement) as z:
            pages |= {n: decode(z.read(n)) for n in z.namelist()}
    sitting = int(path.name[:3])
    days = sorted((day_of(n)[1], n) for n in pages if day_of(n))
    starts = []
    for k, n in days:
        linked = [int(p[4:]) for p in re.findall(r"(s\d{6,})\.htm", pages[n])]
        if linked and day_date(pages[n]):
            starts.append((min(linked), day_date(pages[n])))
    if not starts and days:
        starts = [(0, day_date(pages[days[0][1]]))]
    starts.sort()
    spages = sorted((int(n[4:-4]), n) for n in pages if re.fullmatch(r"s\d{6,}\.htm", n) and pages[n])
    out, cur, seq = [], None, 0
    stats = {"pages": len(spages), "days": len(starts), "orphan_paragraphs": 0,
             "untranscribed": sum("nebyl dosud přepsán" in pages[n] for _, n in spages)}

    def close():
        if cur and cur["parts"]:
            text, notes = clean(" ".join(cur.pop("parts")))
            if text:
                out.append({**cur, "text": text, "notes": notes,
                            "word_count": len(text.split())})

    for num, name in spages:
        day = next((d for s, d in reversed(starts) if s <= num), starts[0][1] if starts else None)
        if cur and cur["date"] != day:
            close()
            cur = None
        for p in paragraphs(pages[name]):
            head, _, rest = p.partition(">")
            if re.search(r"align\s*=\s*\"?center", head, re.IGNORECASE):
                continue
            m = SPEAKER.match(rest)
            if m:
                role, speaker = split_label(strip_tags(m.group("label")).rstrip(" :"))
            if m and speaker:
                close()
                seq += 1
                cur = {"id": f"{term}-{sitting:03d}-{seq:05d}", "term": term, "sitting": sitting, "date": day,
                       "page": num, "seq": seq, "speaker": speaker, "role": role,
                       "chair": bool(CHAIR.search(role)), "parts": []}
                rest = rest[m.end():]
            text = strip_tags(rest)
            if not text:
                continue
            if cur is None:
                stats["orphan_paragraphs"] += 1
                continue
            cur["parts"].append(text)
    close()
    return out, stats


def parse() -> None:
    import pandas as pd
    rows, by_term = [], {}
    for term in TERMS:
        t = {"sittings": 0, "pages": 0, "orphan_paragraphs": 0, "untranscribed": 0}
        for path in sorted((RAW / term).glob("*schuz.zip")):
            speeches, stats = parse_sitting(term, path)
            rows += speeches
            t["sittings"] += 1
            t["pages"] += stats["pages"]
            t["orphan_paragraphs"] += stats["orphan_paragraphs"]
            t["untranscribed"] += stats["untranscribed"]
        by_term[term] = t
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df.to_parquet(OUT, index=False)
    for term, g in df.groupby("term"):
        t = by_term[term]
        print(f"{term}: {t['sittings']} sittings, {t['pages']} pages, {len(g):,} speeches "
              f"({int(g.chair.sum()):,} chair), {int(g.word_count.sum()):,} words, {g.date.min():%Y-%m-%d} to "
              f"{g.date.max():%Y-%m-%d}, {t['orphan_paragraphs']} paragraphs before any speaker, "
              f"{t['untranscribed']} pages not yet transcribed")
    print(f"{len(df):,} speeches -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("download", "parse"))
    {"download": download, "parse": parse}[ap.parse_args().step]()
