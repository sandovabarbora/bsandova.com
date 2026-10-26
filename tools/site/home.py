"""Home page films, Latest and By topic from docs/works.toml, written into index.html between marker comments, and one
page per topic (topics/<key>.html) listing everything in it.

    python3 tools/site/home.py          # rewrite index.html and topics/
    python3 tools/site/home.py --check  # fail if index.html or a topic page is not what the config renders
"""
from __future__ import annotations

import html
import re
import sys
import tomllib
from datetime import date

from shared import ROOT, SITE
from topbar import bar

CONFIG, INDEX, TOPICS = ROOT / "docs/works.toml", ROOT / "index.html", ROOT / "topics"
LABELS = ("Registered study", "Pre-specified", "Exploratory", "Note", "Tool", "Series", "Thesis")
LATEST, PER_TOPIC = 6, 4
ARROW = ('<svg viewBox="0 0 56 14" fill="none" stroke="currentColor" stroke-width="1.3">'
         '<path d="M0 7h54M48 1l6 6-6 6"/></svg>')
e = html.escape


def load() -> dict:
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))


def validate(cfg: dict) -> None:
    works, topics = cfg["works"], cfg["topics"]
    problems = []
    hrefs = [w.get("href") for w in works]
    if len(hrefs) != len(set(hrefs)):
        problems.append("a work is listed twice")
    for w in works:
        name = w.get("href", w.get("title", "?"))
        problems += [f"{name}: no {f}" for f in ("href", "title", "label", "published") if f not in w]
        if "label" in w and w["label"] not in LABELS:
            problems.append(f"{name}: label {w['label']!r} is not one of {', '.join(LABELS)}")
        if "topic" in w and w["topic"] not in topics:
            problems.append(f"{name}: unknown topic {w['topic']!r}")
        if "series" in w:
            hub = next((h for h in works if h.get("href") == w["series"]), None)
            if hub is None:
                problems.append(f"{name}: its hub {w['series']} is missing")
            elif hub.get("label") != "Series" or hub.get("topic") != w.get("topic"):
                problems.append(f"{name}: its hub {w['series']} must be a Series in the same topic")
    tops = sorted(w["top"] for w in works if "top" in w)
    if tops != list(range(1, len(tops) + 1)):
        problems.append(f"top must run 1..n without gaps: {tops}")
    if problems:
        raise ValueError("docs/works.toml: " + "; ".join(problems))


def films(works: list[dict]) -> str:
    out = []
    for i, w in enumerate(sorted((w for w in works if w.get("top")), key=lambda w: w["top"])):
        f = w["film"]
        tag = "h1" if i == 0 else "h2"
        lazy = " lazy" if i >= 2 else ""
        ctas = "".join(f'<a class="cta" href="{href}">{ARROW}{e(text)}</a>' for text, href in f["ctas"])
        out.append(
            f'  <section class="film{" rv" if i else ""}" style="--tint:{f["tint"]};--move:{f["move"]}" '
            f'id="f-{f["id"]}" aria-label="{e(w["title"])}">\n'
            f'    <div class="shot{lazy}" style="view-transition-name:ph-{f.get("vt", f["photo"])};'
            f'--bg:url(assets/photo/{f["photo"]}.jpg);--bg-s:url(assets/photo/{f["photo"]}-1200.jpg)"></div>\n'
            f'    <div class="film-in">\n'
            f'      <div class="film-txt"><p class="lbl">{e(f["label"])}</p><{tag} class="huge">{f["heading"]}</{tag}>'
            f'<p class="dek">{e(f["dek"])}</p><div class="ctas">{ctas}</div></div>\n'
            f'    </div>\n'
            f'    <p class="credit">{f["credit"]}</p>\n'
            f'  </section>')
    return "\n".join(out)


def when(w: dict) -> tuple[str, str]:
    d = date.fromisoformat(w["published"])
    title = f' title="published {d.day} {d:%b %Y}"' if "date" not in w else ""
    return w.get("date", f"{d:%b %Y}"), title


def label(w: dict) -> str:
    title = f' title="{e(w["detail"])}"' if "detail" in w else ""
    wip = '<i class="wip">in progress</i>' if w.get("progress") else ""
    return f'<span class="c"{title}>{e(w["label"])}{wip}</span>'


def latest(works: list[dict], n: int = LATEST) -> list[dict]:
    """Newest first by each work's own date (a hub by its own, not its parts'); ties keep the order of works.toml."""
    listed = [w for w in works if "topic" in w and "series" not in w]
    return sorted(listed, key=lambda w: w["published"], reverse=True)[:n]


def grouped(works: list[dict], topic: str) -> list[tuple[dict, list[dict]]]:
    """A topic's rows, newest first: each standalone work, and each hub with its parts, dated by its newest part."""
    mine = [w for w in works if w.get("topic") == topic]
    parts: dict[str, list[dict]] = {}
    for w in mine:
        if "series" in w:
            parts.setdefault(w["series"], []).append(w)
    rows = [(w, parts.get(w["href"], [])) for w in mine if "series" not in w]
    return sorted(rows, key=lambda r: max([r[0]["published"]] + [p["published"] for p in r[1]]), reverse=True)


def row(w: dict, parts: list[dict], base: str = "", indent: str = "        ") -> str:
    shown, title = when(w)
    link = (f'<a href="{base}{w["href"]}"><span class="t">{e(w["title"])}</span>{label(w)}'
            f'<span class="y"{title}>{e(shown)}</span></a>')
    if not parts:
        return f"{indent}<li>{link}</li>"
    subs = "\n".join(row(p, [], base, indent + "    ") for p in parts)
    return (f'{indent}<li class="ser">{link}\n'
            f'{indent}  <details class="sp"><summary>{len(parts)} parts</summary><ul>\n{subs}\n'
            f'{indent}  </ul></details></li>')


def card(w: dict) -> str:
    shown, title = when(w)
    finding = f'<span class="f">{e(w["finding"])}</span>' if "finding" in w else ""
    return (f'      <li><a href="{w["href"]}"><span class="t">{e(w["title"])}</span>{finding}'
            f'<span class="m">{label(w)}<span class="y"{title}>{e(shown)}</span></span></a></li>')


def catalogue(cfg: dict) -> str:
    works, topics = cfg["works"], cfg["topics"]
    cards = "\n".join(card(w) for w in latest(works))
    nav = "".join(f'<a href="#{k}">{e(t["title"])}</a>' for k, t in topics.items())
    groups = []
    for key, t in topics.items():
        rows = grouped(works, key)
        shown = "\n".join(row(w, parts) for w, parts in rows[:PER_TOPIC])
        anchors = "".join(f'<span id="{a}"></span>' for a in t.get("anchors", []))
        n = sum(1 + len(parts) for _, parts in rows)
        more = (f'      <p class="all"><a href="topics/{key}">All {n} in {e(t["title"])}'
                f'<span aria-hidden="true"> →</span></a></p>')
        body = f'      <ul class="rows">\n{shown}\n      </ul>\n{more}\n'
        if t.get("collapsed"):
            groups.append(f'    <details class="grp" id="{key}">{anchors}\n'
                          f'      <summary class="grp-h"><h3>{e(t["title"])}</h3><span class="note">{e(t["note"])}</span>'
                          f'</summary>\n{body}    </details>')
        else:
            groups.append(f'    <div class="grp" id="{key}">{anchors}\n'
                          f'      <div class="grp-h"><h3>{e(t["title"])}</h3><p class="note">{e(t["note"])}</p></div>\n'
                          f'{body}    </div>')
    return (f'  <section class="idx" id="works" aria-labelledby="latest-h"><span id="texts"></span>\n'
            f'    <div class="idx-h">\n      <h2 class="big" id="latest-h">Latest</h2>\n'
            f'      <a class="jump" href="#topics">By topic <span aria-hidden="true">↓</span></a>\n    </div>\n'
            f'    <ol class="cards">\n{cards}\n    </ol>\n  </section>\n'
            f'  <section class="idx" id="topics" aria-labelledby="topics-h">\n'
            f'    <div class="idx-h">\n      <h2 class="big" id="topics-h">By topic</h2>\n'
            f'      <nav class="groups" aria-label="Topics">{nav}</nav>\n    </div>\n'
            + "\n".join(groups) + "\n  </section>")


def splice(page: str, name: str, body: str) -> str:
    a, b = f"<!-- {name} -->", f"<!-- /{name} -->"
    i, j = page.index(a), page.index(b) + len(b)
    return page[:i] + f"{a}\n{body}\n  {b}" + page[j:]


def render(page: str, cfg: dict | None = None) -> str:
    cfg = cfg or load()
    validate(cfg)
    page = splice(page, "films", films(cfg["works"]))
    return splice(page, "works", catalogue(cfg))


def shared_css(page: str) -> str:
    """The row styles live once, in index.html between /* catalogue */ markers; topic pages carry a copy."""
    m = re.search(r"/\* catalogue \*/\n(.*?)/\* /catalogue \*/", page, re.S)
    if not m:
        raise ValueError("index.html: no /* catalogue */ ... /* /catalogue */ block")
    return m.group(1)


def topic_page(key: str, cfg: dict, css: str) -> str:
    t, topics = cfg["topics"][key], cfg["topics"]
    rows = grouped(cfg["works"], key)
    n = sum(1 + len(parts) for _, parts in rows)
    others = " · ".join(f'<a href="{k}">{e(o["title"])}</a>' for k, o in topics.items() if k != key)
    desc = e(f'{t["note"]} Everything on bsandova.com in this topic, newest first.')
    title = e(t["title"])
    body = "\n".join(row(w, parts, "../", "  ") for w, parts in rows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://bsandova.com/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://bsandova.com/assets/og.png">
<meta name="theme-color" content="#161616">
<link rel="canonical" href="{SITE}/topics/{key}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="../style.css">
<link rel="stylesheet" href="../text.css">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500&family=JetBrains+Mono:wght@400&family=Fraunces:opsz,wght@9..144,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../a24.css">
<style>
/* written by tools/site/home.py from docs/works.toml; the row styles are copied from index.html */
:root{{--ink:#000;--grey-ink:#6e6e6e;--display:var(--sans)}}
.text-head{{border-bottom:0}}
.text .rows,.text .rows ul{{margin:0;padding:0}}
.text .rows a{{text-decoration:none}}
{css}</style>
</head>
<body>
<div class="top">{bar("../")}<span class="tr">topic · en</span></div>
<article class="text">
<header class="text-head">
  <p class="kicker">All work · {n} {"entry" if n == 1 else "entries"}, newest first</p>
  <h1>{title}</h1>
  <p class="deck">{e(t["note"])}</p>
</header>
<ul class="rows">
{body}
</ul>
<footer class="text-foot"><p class="back"><a href="../#works">← all work</a> · {others} · <a href="../texts/registered">method</a></p></footer>
</article>
</body>
</html>
"""


def topic_pages(page: str, cfg: dict | None = None) -> dict[str, str]:
    cfg = cfg or load()
    css = shared_css(page)
    return {f"topics/{k}.html": topic_page(k, cfg, css) for k in cfg["topics"]}


def outputs() -> dict[str, str]:
    cfg = load()
    page = render(INDEX.read_text(encoding="utf-8"), cfg)
    return {"index.html": page} | topic_pages(page, cfg)


def stale() -> list[str]:
    """Generated files that differ from what docs/works.toml renders, and topic pages no topic renders any more."""
    out = outputs()
    bad = [p for p, text in out.items() if not (ROOT / p).exists() or (ROOT / p).read_text(encoding="utf-8") != text]
    return bad + [f"topics/{p.name}" for p in sorted(TOPICS.glob("*.html")) if f"topics/{p.name}" not in out]


def main() -> None:
    try:
        if "--check" in sys.argv:
            bad = stale()
            sys.exit(f"differs from docs/works.toml, run tools/site/home.py: {', '.join(bad)}" if bad else 0)
        out = outputs()
    except ValueError as err:
        sys.exit(str(err))
    TOPICS.mkdir(exist_ok=True)
    for p in TOPICS.glob("*.html"):
        if f"topics/{p.name}" not in out:
            p.unlink()
    for p, text in out.items():
        (ROOT / p).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
