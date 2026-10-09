"""Changelog of the site, generated from git at build time. Nothing typed.

    python tools/site/changelog.py        # writes changelog/index.html and changelog/data.json

Each commit becomes one line: date, an area derived from the files it touched, the subject.
Data commits made by the jobs (surf, watch) are kept but marked, so the page shows the site
changing and the pipelines running as two different kinds of event.

Above the commits, each article's own change log (corrections, version notes, the editorial-standard check), kept by
hand in docs/changelogs/<slug>.html and linked from the article's version number as changelog/#<slug>.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from shared import ROOT, slug, write

OUT = ROOT / "changelog"
LOGS = ROOT / "docs" / "changelogs"
TEMPLATE = (Path(__file__).parent / "changelog.html").read_text(encoding="utf-8")
MONTHS = "January February March April May June July August September October November December".split()
AREAS = [  # first match wins; order matters
    (r"^(surf|watch)/data", "data"),
    (r"^texts/", "texts"),
    (r"^(surf|watch|status|changelog|library|atlantic)/", "live pages"),
    (r"^(infra/|\.github/|wrangler\.jsonc|\.assetsignore|404\.html|build\.sh)", "infra"),
    (r"^(tools/|assets/)", "figures & tools"),
    (r"^(index\.html|style\.css|text\.css)$", "site"),
    (r"^docs/", "specs"),
]
JOB_SUBJECT = re.compile(r"^(surf|watch): \d{4}-\d{2}-\d{2}$")
# the subject prefix is the author's own word for the area; files only decide when it is missing
# (older commits carry build.sh's style.css?v= stamp in every text, so file counts over-vote "texts")
PREFIX = {
    "texts": "texts", "text": "texts", "engineering": "texts", "contact": "site", "projects": "site", "links": "site",
    "hero": "site", "feat": "site", "fix": "site", "chore": "site", "brand": "brand",
    "infra": "infra", "deploy": "infra", "ci": "infra", "status": "live pages", "watch": "live pages",
    "surf": "live pages", "changelog": "live pages", "library": "live pages", "atlantic": "live pages",
    "tools": "figures & tools", "spec": "specs", "plan": "specs",
}


def area_of(files: list[str]) -> str:
    votes = Counter()
    for f in files:
        for pat, name in AREAS:
            if re.search(pat, f):
                votes[name] += 1
                break
        else:
            votes["mixed"] += 1
    return votes.most_common(1)[0][0] if votes else "mixed"


def commits() -> list[dict]:
    raw = subprocess.run(
        ["git", "log", "--date=iso-strict", "--format=%x1e%H%x1f%h%x1f%ad%x1f%s%x1f%b", "--name-only"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    out = []
    for chunk in raw.split("\x1e")[1:]:
        head, _, files = chunk.partition("\n\n")
        h, short, date, subject, body = (head.split("\x1f") + [""] * 5)[:5]
        body = "\n".join(l for l in body.splitlines() if not l.startswith(("Co-Authored-By", "Claude-Session"))).strip()
        flist = [f for f in files.splitlines() if f.strip()]
        job = bool(JOB_SUBJECT.match(subject))
        prefix = subject.split(":", 1)[0].strip().lower() if ":" in subject else ""
        area = "data" if job else PREFIX.get(prefix) or area_of(flist)
        out.append({"sha": short, "date": date[:10], "time": date[11:16], "subject": subject,
                    "body": body, "files": len(flist), "area": area, "job": job})
    out.sort(key=lambda c: (c["date"], c["time"]), reverse=True)
    return out


def articles() -> list[dict]:
    """Each article with a change log: its title, URL, version and the hand-kept list, newest-changed first."""
    out = []
    for page in sorted((ROOT / "texts").rglob("*.html")):
        key = slug(page)
        log = LOGS / f"{key}.html"
        if not log.exists():
            continue
        s = page.read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", s, re.S).group(1).split(" · Barbora")[0].strip()
        version = re.search(r'changelog/#' + re.escape(key) + r'">(version \d+)<', s)
        body = log.read_text(encoding="utf-8")
        dates = [(int(y), MONTHS.index(m) + 1, int(d)) for d, m, y in re.findall(r"(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})", body)]
        href = "../" + str(page.relative_to(ROOT).with_suffix("")).replace("/index", "/")
        out.append({"slug": key, "title": title, "href": href, "version": version.group(1) if version else "",
                    "latest": max(dates) if dates else (0, 0, 0), "body": body})
    return sorted(out, key=lambda a: (a["latest"], a["title"]), reverse=True)


def render(items: list[dict]) -> str:
    by_day = defaultdict(list)
    for c in items:
        by_day[c["date"]].append(c)
    days = sorted(by_day, reverse=True)
    n_site = sum(1 for c in items if not c["job"])
    n_job = len(items) - n_site
    rows = []
    for d in days:
        rows.append(f'<h2 id="d-{d}">{d}</h2><ol class="log">')
        for c in by_day[d]:
            cls = " job" if c["job"] else ""
            body = f'<p class="body">{html.escape(c["body"])}</p>' if c["body"] and not c["job"] else ""
            rows.append(
                f'<li class="c{cls}"><span class="t">{c["time"]}</span><span class="a">{c["area"]}</span>'
                f'<span class="s">{html.escape(c["subject"])}</span>'
                f'<a class="h" href="https://github.com/sandovabarbora/bsandova.com/commit/{c["sha"]}">{c["sha"]}</a>'
                f'<span class="f">{c["files"]} file{"s" if c["files"] != 1 else ""}</span>{body}</li>'
            )
        rows.append("</ol>")
    first = items[-1]["date"] if items else ""
    arts = articles()
    art_rows = ['<h2 id="articles">Article change logs</h2>'] + [
        f'<section class="art" id="{a["slug"]}"><h3><a href="{a["href"]}">{html.escape(a["title"])}</a>'
        f'<small>{a["version"]}</small></h3>{a["body"]}</section>' for a in arts] + ['<h2 id="commits">Commits</h2>']
    return TEMPLATE.format(first=first, n_site=n_site, n_job=n_job, n_days=len(days), last=days[0] if days else "",
                           n_arts=len(arts), articles="".join(art_rows), commits="".join(rows))


def main() -> None:
    items = commits()
    OUT.mkdir(exist_ok=True)
    write(OUT / "data.json", json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    write(OUT / "index.html", render(items))
    print(f"changelog: {len(items)} commits, {sum(1 for c in items if c['job'])} by jobs")


if __name__ == "__main__":
    main()
