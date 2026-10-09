"""Home page films and "All work" from docs/works.toml, written into index.html between marker comments.

    python3 tools/site/home.py          # rewrite index.html
    python3 tools/site/home.py --check  # fail if index.html is not what the config renders
"""
from __future__ import annotations

import html
import sys
import tomllib
from datetime import date

from shared import ROOT

CONFIG, INDEX = ROOT / "docs/works.toml", ROOT / "index.html"
ARROW = ('<svg viewBox="0 0 56 14" fill="none" stroke="currentColor" stroke-width="1.3">'
         '<path d="M0 7h54M48 1l6 6-6 6"/></svg>')
e = html.escape


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


def row(w: dict, sub: bool = False) -> str:
    shown, title = when(w)
    return (f'        <li{" class=\"sub\"" if sub else ""}><a href="{w["href"]}"><span class="t">{e(w["title"])}</span>'
            f'<span class="c">{e(w["kind"])}</span><span class="s">{e(w["status"])}</span>'
            f'<span class="y"{title}>{e(shown)}</span></a></li>')


def all_work(cfg: dict) -> str:
    works, topics = cfg["works"], cfg["topics"]
    nav = "".join(f'<a href="#{k}">{e(t["title"])}</a>' for k, t in topics.items())
    groups = []
    for key, t in topics.items():
        mine = [w for w in works if w["topic"] == key]
        parts = {}
        for w in mine:
            if "series" in w:
                parts.setdefault(w["series"], []).append(w)
        heads = [w for w in mine if "series" not in w]
        latest = lambda w: max([w["published"]] + [p["published"] for p in parts.get(w["href"], [])])  # noqa: E731
        heads.sort(key=latest, reverse=True)
        heads.sort(key=lambda w: w["href"] not in parts)  # stable: series first, each group newest first
        rows = []
        for w in heads:
            rows.append(row(w))
            rows += [row(p, sub=True) for p in parts.get(w["href"], [])]
        groups.append(f'    <div class="grp" id="{key}">\n'
                      f'      <div class="grp-h"><h3>{e(t["title"])}</h3><p>{e(t["note"])}</p></div>\n'
                      f'      <ul class="rows">\n' + "\n".join(rows) + '\n      </ul>\n    </div>')
    return (f'  <section class="idx" id="works" aria-label="All work"><span id="texts"></span>\n'
            f'    <div class="idx-h">\n      <h2 class="big">All work</h2>\n'
            f'      <nav class="groups" aria-label="Topics">{nav}</nav>\n    </div>\n'
            + "\n".join(groups) + "\n  </section>")


def splice(page: str, name: str, body: str) -> str:
    a, b = f"<!-- {name} -->", f"<!-- /{name} -->"
    i, j = page.index(a), page.index(b) + len(b)
    return page[:i] + f"{a}\n{body}\n  {b}" + page[j:]


def render(page: str) -> str:
    cfg = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    hrefs = [w["href"] for w in cfg["works"]]
    assert len(hrefs) == len(set(hrefs)), "a work is listed twice"
    assert all(w["topic"] in cfg["topics"] for w in cfg["works"]), "unknown topic"
    assert all(w["series"] in hrefs for w in cfg["works"] if "series" in w), "a part's hub is missing"
    tops = sorted(w["top"] for w in cfg["works"] if "top" in w)
    assert tops == list(range(1, len(tops) + 1)), f"top must run 1..n without gaps: {tops}"
    page = splice(page, "films", films(cfg["works"]))
    return splice(page, "works", all_work(cfg))


def main() -> None:
    page = INDEX.read_text(encoding="utf-8")
    out = render(page)
    if "--check" in sys.argv:
        sys.exit(0 if out == page else "index.html differs from docs/works.toml; run tools/site/home.py")
    INDEX.write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
