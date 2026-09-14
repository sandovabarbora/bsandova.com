"""Port the quaesitor.eu pages into bsandova.com/texts/quaesitor/.

The source pages are self-contained HTML (fonts and images inlined) in the
quaesitor project's publish/site. Their stylesheet is carried over with the
palette remapped to this site's tokens; the chrome (nav, footer, wordmark) is
replaced by this site's; everything else — findings, tables, footnotes — is
kept verbatim so the numbers stay the ones the runs produced.

Usage: python tools/port_quaesitor.py /path/to/quaesitor/publish/site
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "texts" / "quaesitor"
OUT.mkdir(parents=True, exist_ok=True)

# quaesitor palette → bsandova.com palette (light↔dark inversion, blue→acid)
COLOURS = {
    "#6B655C": "#8A8A84", "#DAD6CC": "#3A3A36", "#1C1A17": "#DCDCD6", "#4657D9": "#D6FF3A",
    "#9A3324": "#FF6A3D", "#EFEBDF": "#161616", "#F6F4EE": "#1F1F1F", "#33424A": "#232323",
    "#E4E0D6": "#2A2A27", "#9EAFAB": "#8A8A84", "#D9A441": "#B78CFF", "#5E6259": "#9A9A94",
    "#F5F3EE": "#161616", "#3A3733": "#C8C8C2", "#2E3BA8": "#BFE82F", "#E0736A": "#FF6A3D",
    "#2E6B4F": "#7ED9A6", "#B9C2E8": "#5A5A56", "#4B4F48": "#B0B0AA", "#C9CFF5": "#8A8A84",
    "#8FA0F0": "#D6FF3A",
    "rgba(28,26,23,.2)": "rgba(220,220,214,.2)", "rgba(239,235,223,.9)": "rgba(22,22,22,.9)",
    "rgba(28,26,23,.055)": "rgba(220,220,214,.08)", "rgba(239,235,223,.8)": "rgba(22,22,22,.8)",
    "rgba(28,26,23,.16)": "rgba(220,220,214,.16)",
}

PAGES = {  # source → (slug, kicker label)
    "method": ("method", "Quaesitor · methodology"),
    "documentation-finding": ("documentation-finding", "Quaesitor · measurement 01"),
    "silent-failure-rate": ("silent-failure-rate", "Quaesitor · measurement 02"),
    "abstention": ("abstention", "Quaesitor · finding"),
    "silent-failures/index": ("silent-failures", "Quaesitor · essay"),
    "traps": ("traps", "Quaesitor · catalogue"),
    "access": ("access", "Quaesitor · catalogue"),
    "packs": ("packs", "Quaesitor · question packs"),
    "why": ("why", "Quaesitor · why"),
    "evidence": ("evidence", "Quaesitor · literature"),
    "about": ("about", "Quaesitor · about"),
    "report-built": ("report-built", "Quaesitor · sample report"),
}

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#161616">
<link rel="canonical" href="https://bsandova.com/texts/quaesitor/{slug}.html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;700&family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../style.css">
<link rel="stylesheet" href="../../text.css">
<style>
/* quaesitor.eu stylesheet, palette remapped; see tools/port_quaesitor.py */
{css}
/* port overrides: gutter alignment, this site's chrome */
body{{background:#161616}}
main.article{{max-width:none !important;margin:0 !important;padding:2rem 1.5rem 3rem !important}}
main.article > .wrap{{max-width:60rem}}
.cell.c-correct,.cell.c-silent,.cell.c-implausible,.cell.c-invalid{{display:inline-block;width:1rem;height:1rem;background:currentColor;border:0;padding:0;vertical-align:-.15em;margin-right:.4rem}}
.grid .cell{{display:block;width:100%;min-width:.9rem;height:1.25rem;margin:0}}
.q-title{{font-family:'Fraunces',serif;font-weight:700;font-variation-settings:'opsz' 144;font-size:clamp(2rem,4.5vw,4rem);line-height:1;letter-spacing:-.04em;margin:0 0 1.5rem;color:#F2F2EE;max-width:18em}}
.q-note{{margin:0;padding:.7rem 1.5rem;border-bottom:1px solid #3A3A36;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#8A8A84}}
.q-note b{{color:#D6FF3A;font-weight:400}}
.q-back{{padding:1.5rem;border-top:1px solid #3A3A36;font-family:'JetBrains Mono',monospace;font-size:11px}}
.q-back a{{color:#D6FF3A}}
@media (max-width:64rem){{main.article{{padding:1.5rem 1rem 2.5rem !important}}}}
</style>
</head>
<body>
<div class="top"><b><a href="../../">bsandova.com</a></b><nav><a href="../../#works">Works</a><a href="../../#texts">Texts</a><a href="../../#about">About</a><a href="../../#contact">Contact</a></nav><span class="tr">{kicker} · en</span></div>
<p class="q-note"><b>Quaesitor</b> · independent review of AI assistants over data warehouses · first published at quaesitor.eu, 2026 · the service is retired, the findings are not</p>
"""

FOOT = """
<div class="q-back"><a href="index.html">← Quaesitor overview</a> · <a href="../../#texts">← back to texts</a></div>
</body>
</html>
"""


def remap(css: str) -> str:
    for a, b in COLOURS.items():
        css = re.sub(re.escape(a), b, css, flags=re.I)
    return css


def clean_css(html: str) -> str:
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    css = re.sub(r"@font-face\{.*?\}", "", css, flags=re.S)          # fonts come from Google here
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"url\(data:[^)]+\)", "none", css)
    return remap(css).strip()


def content(html: str) -> str:
    m = re.search(r"<main[^>]*>(.*)</main>", html, re.S)
    if m:
        body = "<main class=\"article\">" + m.group(1) + "</main>"
    else:  # index / report-built have no <main>: take body minus footer
        m = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
        body = m.group(1) if m else html[html.rfind("</style>") + len("</style>"):].replace("</html>", "")
        body = re.sub(r"<footer.*?</footer>", "", body, flags=re.S)
        body = "<main class=\"article\"><div class=\"wrap\">" + body + "</div></main>"
    body = re.sub(r"<nav[^>]*>.*?</nav>", "", body, count=1, flags=re.S)
    body = re.sub(r"<footer.*?</footer>", "", body, flags=re.S)
    body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.S)
    # brand chrome that may sit outside <nav>
    body = re.sub(r"<span class=\"brandmark\">.*?</span>\s*</span>", "", body, flags=re.S)
    body = re.sub(r"<img[^>]*src=\"data:[^\"]*\"[^>]*>", "", body)   # inlined bust/og images
    body = remap(body)
    # links: everything lives flat in texts/quaesitor/
    body = body.replace('href="silent-failures/"', 'href="silent-failures.html"')
    body = body.replace('href="/silent-failures/"', 'href="silent-failures.html"')
    body = re.sub(r'href="/?([a-z-]+)\.html', r'href="\1.html', body)
    body = body.replace('href="/"', 'href="index.html"').replace('href="index.html#', 'href="index.html#')
    body = body.replace('href="../', 'href="')
    return body


def title_of(html: str, fallback: str) -> tuple[str, str]:
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', html)
    return (re.sub(r"\s+", " ", t.group(1)).strip() if t else fallback,
            d.group(1) if d else "")


for src, (slug, kicker) in PAGES.items():
    path = SRC / f"{src}.html"
    if not path.exists():
        print("missing", path)
        continue
    html = path.read_text(encoding="utf-8")
    title, desc = title_of(html, slug)
    page = HEAD.format(title=title.replace("qu&aelig;sitor*: ", "").replace("quæsitor", "Quaesitor") + " — Barbora Šandová", desc=desc.replace('"', "'"),
                       slug=slug, kicker=kicker, css=clean_css(html))
    body = content(html)
    if "<h1" not in body:
        t = title.replace("qu&aelig;sitor*: ", "").replace("quæsitor*: ", "").split(" · ")[0].split(" — ")[0]
        t = t[0].upper() + t[1:]
        body = body.replace('<main class="article">', f'<main class="article"><h1 class="q-title">{t}</h1>', 1)
    page += body + FOOT
    (OUT / f"{slug}.html").write_text(page, encoding="utf-8")
    print(f"{src:24s} → texts/quaesitor/{slug}.html  {len(page)//1024} KB")
