"""Every page title ends with the author's name, so a search for the name finds the pages and not only the repository.

Idempotent: a title that already holds the name is left alone. Deploy-only: committed pages keep the plain title and
build.sh adds the name on the way out; og:title is not changed, so share cards and the feed keep the plain title.

    python3 tools/site/titles.py           # add the name where it is missing
    python3 tools/site/titles.py --check   # exit 1 and list the pages that would change
"""

from __future__ import annotations

import argparse
import re
import sys

from shared import ROOT

NAME = "Barbora Šandová"
SKIP = {"node_modules", ".venv", "tools", ".git", ".claude"}


def with_name(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    if not m or NAME in m.group(1):
        return page
    return page[:m.start(1)] + f"{m.group(1).strip()} · {NAME}" + page[m.end(1):]


def main() -> None:
    ap = argparse.ArgumentParser(description="Add the author's name to every page title.")
    ap.add_argument("--check", action="store_true", help="list pages that would change and exit 1, writing nothing")
    args = ap.parse_args()
    changed = []
    for f in ROOT.rglob("*.html"):
        if SKIP & set(f.relative_to(ROOT).parts):
            continue
        page = f.read_text(encoding="utf-8")
        new = with_name(page)
        if new == page:
            continue
        changed.append(f.relative_to(ROOT))
        if not args.check:
            f.write_text(new, encoding="utf-8")
    if args.check:
        for p in changed:
            print(p)
        sys.exit(1 if changed else 0)
    print(f"titles: {len(changed)} pages given the author's name")


if __name__ == "__main__":
    main()
