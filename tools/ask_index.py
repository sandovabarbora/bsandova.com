"""Build ask/index.json: every paragraph of every text on the site, with its page and title, so the
agent can search the texts and verify quotations verbatim.   python tools/ask_index.py"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ask" / "index.json"
PAGES = sorted(ROOT.glob("texts/*.html")) + sorted(ROOT.glob("texts/quaesitor/*.html"))


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<sup class=\"cite\">.*?</sup>", "", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def main() -> None:
    docs = []
    for p in PAGES:
        s = p.read_text()
        title = text_of(re.search(r"<h1>(.*?)</h1>", s, re.S).group(1)) if re.search(r"<h1>(.*?)</h1>", s, re.S) else p.stem
        url = "/" + str(p.relative_to(ROOT)).replace(".html", "").replace("/index", "/")
        body = s[s.index("<article"):] if "<article" in s else s
        body = body[: body.index('<section class="refs"')] if '<section class="refs"' in body else body
        n = 0
        for m in re.finditer(r"<(p|li|figcaption|dd)\b[^>]*>(.*?)</\1>", body, re.S):
            t = text_of(m.group(2))
            if len(t.split()) < 8 or m.group(0).startswith("<p class=\"kicker\"") or 'class="back"' in m.group(0):
                continue
            docs.append({"id": f"{p.stem}#{n}", "page": url, "title": title, "text": t})
            n += 1
    OUT.write_text(json.dumps({"built_from": len(PAGES), "passages": docs}, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{len(docs)} passages from {len(PAGES)} pages → {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
