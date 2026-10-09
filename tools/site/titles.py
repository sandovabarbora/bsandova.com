"""Every page title ends with the author's name, so a search for the name finds the pages and not only the repository.

Idempotent: a title that already holds the name is left alone. Deploy-only: committed pages keep the plain title and
build.sh adds the name on the way out; og:title is not changed, so share cards and the feed keep the plain title.

    python3 tools/site/titles.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = "Barbora Šandová"
SKIP = {"node_modules", ".venv", "tools", ".git", ".claude"}


def main() -> None:
    n = 0
    for f in ROOT.rglob("*.html"):
        if SKIP & set(f.relative_to(ROOT).parts):
            continue
        s = f.read_text(encoding="utf-8")
        m = re.search(r"<title>(.*?)</title>", s, re.S)
        if not m or NAME in m.group(1):
            continue
        s = s[:m.start(1)] + f"{m.group(1).strip()} · {NAME}" + s[m.end(1):]
        f.write_text(s, encoding="utf-8")
        n += 1
    print(f"titles: {n} pages given the author's name")


if __name__ == "__main__":
    main()
