"""The gate of docs/style/editorial-standard.md, run on every build: a listed page that breaks a hard rule fails the
deploy; soft rules (word caps) are reported as warnings.

Hard rules, for every article in texts/*.html:
  - one short-version box (details.tldr), one metadata block (dl.meta) whose version links to the article's change log
    on the changelog page (changelog/#<slug>), and that change log (docs/changelogs/<slug>.html) records the standard
    check; changes after registration are listed there too, never in the article;
  - no claim of review ("referee"), and "pre-registered" only in its negated form ("not pre-registered");
  - references: numbered r1..rN without gaps, every entry cited, every citation resolves;
  - figures numbered 1..n in order, and every "(fig. n)" in the text points at an existing figure;
  - no link to a local text page that does not exist.

    python3 tools/site/check_standard.py            # exit 1 on a hard failure
"""
from __future__ import annotations

import html as H
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXTS = ROOT / "texts"
CAPS = {"research": (2500, 3500), "tool": (1000, 1500), "note": (400, 900), "hub": (0, 1000)}
SKIP = {"forecast-verification", "thesis"}  # no word cap: a protocol note, and the thesis summary (about 1 700)


def visible(s: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    return H.unescape(re.sub(r"<[^>]+>", " ", s))


def body_words(s: str) -> int:
    """Words of the sections between the metadata block and the references, without tables, figures and captions."""
    a = s.find("</dl>", s.find('class="meta"'))
    b = s.find('id="refs"')
    b = b if b > 0 else s.find('<footer')
    part = s[a:b] if a > 0 and b > a else s
    part = re.sub(r"<(table|figure|figcaption|pre)[^>]*>.*?</\1>", " ", part, flags=re.S)
    return len(visible(part).split())


def kind(s: str) -> str:
    m = re.search(r'<p class="kicker">\s*([A-Za-z]+)', s)
    k = (m.group(1).lower() if m else "")
    return {"research": "research", "tool": "tool", "note": "note", "hub": "hub"}.get(k, "")


def check(path: Path) -> tuple[list[str], list[str]]:
    s = path.read_text(encoding="utf-8")
    hard, soft = [], []
    if s.count('class="tldr"') != 1:
        hard.append(f"{s.count('class=\"tldr\"')} short-version boxes (need 1)")
    if 'class="meta"' not in s:
        hard.append("no metadata block (dl.meta)")
    rel = path.resolve().relative_to(ROOT / "texts").with_suffix("")
    canon = re.search(r'rel="canonical" href="https://bsandova\.com/texts/([^"]*)"', s)
    if not canon or canon.group(1).rstrip("/") not in (rel.as_posix(), rel.as_posix().removesuffix("/index")):
        hard.append("no canonical link to its own /texts/ URL (the article grid in a24.css keys on it)")
    slug = "-".join(x for x in rel.parts if x != "index") or "index"
    log = ROOT / "docs" / "changelogs" / f"{slug}.html"
    if f"changelog/#{slug}" not in s:
        hard.append(f"version does not link to its change log (changelog/#{slug})")
    if not log.exists():
        hard.append(f"no change log (docs/changelogs/{slug}.html)")
    elif "Checked against editorial standard" not in log.read_text(encoding="utf-8"):
        hard.append("change log does not record the standard check")
    if 'id="changelog"' in s:
        hard.append("change log inside the article; it belongs on the changelog page")
    if 'id="changes"' in s:
        hard.append("changes after registration inside the article; they belong in its change log")
    text = visible(s)
    if re.search(r"\breferees?\b", text, re.I):
        hard.append('mentions "referee"')
    for m in re.finditer(r"pre-?registered", text, re.I):
        before = text[max(0, m.start() - 12):m.start()].lower()
        after = text[m.end():m.end() + 2]
        quoted = text[max(0, m.start() - 1)] in "\"“'" or after[:1] in "\"”'"
        if "not " not in before and "no longer" not in text[max(0, m.start() - 40):m.start()] and not quoted:
            hard.append('uses "pre-registered" without a timestamped registration')
            break
    ids = [int(x) for x in re.findall(r'id="r(\d+)"', s)]
    cites = {int(x) for x in re.findall(r'href="#r(\d+)"', s)}
    if ids and ids != list(range(1, len(ids) + 1)):
        hard.append(f"references not numbered 1..{len(ids)} in order")
    if set(ids) - cites:
        hard.append(f"uncited references {sorted(set(ids) - cites)}")
    if cites - set(ids):
        hard.append(f"citations without an entry {sorted(cites - set(ids))}")
    figs = [int(x) for x in re.findall(r"<b>fig\. (\d+)</b>", s)]
    if figs and figs != list(range(1, len(figs) + 1)):
        hard.append(f"figures numbered {figs}")
    refs = {int(x) for x in re.findall(r"\(fig\. (\d+)\)", text)}
    if refs - set(figs):
        hard.append(f"text points at missing figures {sorted(refs - set(figs))}")
    base = path.parent
    for href in re.findall(r'href="([a-z0-9-]+)(?:\.html)?(?:#[^"]*)?"', s):
        if not (base / f"{href}.html").exists() and not (base / href).is_dir():
            hard.append(f"link to missing page {href}")
    k = kind(s)
    if k in CAPS and path.stem not in SKIP:
        lo, hi = CAPS[k]
        n = body_words(s)
        if not lo * 0.9 <= n <= hi * 1.1:
            soft.append(f"{k} body about {n} words (cap {lo}–{hi})")
    return hard, soft


def main() -> int:
    failed = 0
    for p in sorted(TEXTS.glob("*.html")):
        if p.name.startswith("_"):
            continue
        hard, soft = check(p)
        for h in hard:
            print(f"FAIL {p.relative_to(ROOT)}: {h}")
        for w in soft:
            print(f"warn {p.relative_to(ROOT)}: {w}")
        failed += bool(hard)
    import importlib.util
    spec = importlib.util.spec_from_file_location("home", Path(__file__).with_name("home.py"))
    home = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(home)
    page = home.INDEX.read_text(encoding="utf-8")
    if home.render(page) != page:
        print("FAIL index.html: differs from docs/works.toml; run tools/site/home.py")
        failed += 1
    linked = {w["href"].removeprefix("texts/").rstrip("/") for w in home.tomllib.loads(home.CONFIG.read_text())["works"]}
    for p in sorted(TEXTS.glob("*.html")):
        if not p.name.startswith("_") and p.stem not in linked:
            print(f"FAIL {p.relative_to(ROOT)}: not listed in docs/works.toml")
            failed += 1
    print(f"standard check: {failed} page(s) failing" if failed else "standard check: all pages pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
