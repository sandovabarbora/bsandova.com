"""Changelog of the site, generated from git at build time. Nothing typed.

    python tools/changelog.py        # writes changelog/index.html and changelog/data.json

Each commit becomes one line: date, an area derived from the files it touched, the subject.
Data commits made by the jobs (surf, watch) are kept but marked, so the page shows the site
changing and the pipelines running as two different kinds of event.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "changelog"
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
# (build.sh stamps style.css?v= into every text on every commit, so file counts over-vote "texts")
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
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Changelog</title>
<meta name="description" content="Every change to bsandova.com, read from git at build time: what changed, when, in which part of the site, with the commit. Job commits (surf, watch) shown separately.">
<meta name="theme-color" content="#161616">
<link rel="canonical" href="https://bsandova.com/changelog/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;700&family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../style.css">
<link rel="stylesheet" href="../text.css">
<style>
.text h2{{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-2);font-weight:400;margin:1.8rem 0 .4rem;border-bottom:1px solid var(--line);padding-bottom:.4rem}}
.log{{list-style:none;margin:0;padding:0;max-width:64rem}}
.c{{display:grid;grid-template-columns:3.2rem 7.5rem minmax(0,1fr) auto auto;gap:.2rem 1rem;align-items:baseline;padding:.45rem 0;border-bottom:1px solid var(--line);font-size:.92rem}}
.c .t,.c .h,.c .f{{font-family:var(--mono);font-size:11px;color:var(--fg-2)}}
.c .a{{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--coral)}}
.c.job .a{{color:var(--fg-2)}}.c.job .s{{color:var(--fg-2)}}
.c .s{{color:var(--fg)}}.c .h{{color:var(--fg-2)}}.c .h:hover{{color:var(--hot)}}
.c .body{{grid-column:3/-1;margin:0;font-size:.85rem;color:var(--fg-2);white-space:pre-wrap}}
@media (max-width:48rem){{.c{{grid-template-columns:3.2rem 1fr;}}.c .a{{grid-column:2}}.c .s{{grid-column:1/-1}}.c .h,.c .f{{grid-column:auto}}.c .body{{grid-column:1/-1}}}}
</style>
</head>
<body>
<div class="top"><b><a href="../">bsandova.com</a></b><nav><a href="../#works">Projects</a><a href="../#about">About</a><a href="../#contact">Contact</a></nav><span class="tr">changelog · en</span></div>
<article class="text">
<header class="text-head">
  <p class="kicker">Changelog · every commit since {first} · generated from git at build time</p>
  <h1>What changed, <em>and when.</em></h1>
  <p class="deck">The <a href="../status/">status page</a> says whether the jobs ran. This page says what the site itself did: every commit, its area, the files it touched, and the commit to read if you want the diff. Job commits, the surf collector and the model watch writing their data, are kept and greyed, so the two kinds of change stay distinguishable. Nothing here is typed; the page is rebuilt from <code>git log</code> on every deploy.</p>
  <dl class="facts">
    <div><dt>commits</dt><dd>{n_site} <small>by hand</small></dd></div>
    <div><dt>job commits</dt><dd>{n_job} <small>surf · watch, data only</small></dd></div>
    <div><dt>days</dt><dd>{len(days)} <small>{first} → {days[0] if days else ""}</small></dd></div>
    <div><dt>data</dt><dd><a href="data.json">data.json</a> <small>one record per commit</small></dd></div>
  </dl>
</header>
{"".join(rows)}
<footer class="text-foot"><p class="back"><a href="../#works">← projects</a> · <a href="../status/">status</a></p></footer>
</article>
</body>
</html>
'''


def main() -> None:
    items = commits()
    OUT.mkdir(exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    (OUT / "index.html").write_text(render(items))
    print(f"changelog: {len(items)} commits, {sum(1 for c in items if c['job'])} by jobs")


if __name__ == "__main__":
    main()
