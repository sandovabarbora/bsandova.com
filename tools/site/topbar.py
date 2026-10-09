"""One top bar for every subpage: the bŠ mark and the same five links, with paths relative to each page.

Rewrites the <div class="top"> brand and nav in every tracked page, and in the page templates of the generators
(tools/site/changelog.html, tools/quaesitor/quaesitor_texts.py, tools/quaesitor/port_quaesitor.py), so a regenerated page keeps the same bar.
The page label (<span class="tr">) is left alone.

Usage:
    python3 tools/site/topbar.py
"""

import re

from shared import ROOT, tracked_html

LINKS = [("#work", "Work"), ("#works", "All work"), ("#about", "About"), ("ask/", "Ask"), ("#contact", "Contact")]
BAR = re.compile(r'(<div class="top">)<b><a href="([^"]*)"[^>]*>[^<]*</a></b><nav>.*?</nav>')
SKIP = ("tools/", "assets/", "index.html")


def bar(home: str) -> str:
    links = "".join(f'<a href="{home}{h}"{" class=\"ask-link\"" if h == "ask/" else ""}>{t}</a>' for h, t in LINKS)
    return f'<b><a href="{home}" aria-label="bŠ, bsandova.com, home">bŠ</a></b><nav>{links}</nav>'


def rewrite(text: str) -> str:
    return BAR.sub(lambda m: m.group(1) + bar(m.group(2)), text)


def main() -> None:
    targets = [f for f in tracked_html() if not f.startswith(SKIP) and f not in SKIP]
    targets += ["tools/site/changelog.html", "tools/quaesitor/quaesitor_texts.py", "tools/quaesitor/port_quaesitor.py"]
    for f in targets:
        path = ROOT / f
        old = path.read_text()
        new = rewrite(old)
        if new != old:
            path.write_text(new)
            print(f)


if __name__ == "__main__":
    main()
