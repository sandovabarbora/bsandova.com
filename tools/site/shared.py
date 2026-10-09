# Not site.py: the interpreter imports the standard library's site module first, so that name would never resolve here.
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://bsandova.com"
CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)"')
NOINDEX = re.compile(r'<meta name="robots" content="[^"]*noindex')


def tracked_html() -> list[str]:
    return subprocess.run(["git", "ls-files", "*.html"], cwd=ROOT, capture_output=True, text=True).stdout.split()


def last_commit(path: str, fmt: str) -> str:
    args = ["git", "log", "-1", f"--format={fmt}", "--", path]
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def canonical(page: str) -> str | None:
    m = CANONICAL.search(page)
    return m.group(1) if m else None


def noindex(page: str) -> bool:
    return bool(NOINDEX.search(page))


def slug(page: Path) -> str:
    """texts/a/b/index.html -> a-b: the key of an article's change log and its changelog/#anchor."""
    rel = page.resolve().relative_to(ROOT / "texts").with_suffix("")
    return "-".join(p for p in rel.parts if p != "index") or "index"


def write(path: Path, text: str) -> bool:
    """Leaves an unchanged file untouched, so a rerun keeps mtimes and reports nothing."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True
