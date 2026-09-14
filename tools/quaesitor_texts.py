"""Generate the three condensed Quaesitor texts. Run: python tools/quaesitor_texts.py"""
import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
grid = (ROOT / "tools/data/quaesitor-docs-grid.html").read_text()
CSS = """
.tbl{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11px;margin:1rem 0 1.5rem}
.tbl th,.tbl td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
.tbl th:first-child,.tbl td:first-child{padding-left:0}
.tbl th{font-weight:400;color:var(--fg-2);letter-spacing:.12em;text-transform:uppercase;font-size:10px}
.tbl td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.tbl th.n{text-align:right}
.tbl td b{color:var(--hot);font-weight:400}.tbl .hi{color:var(--coral)}
.scroller{overflow-x:auto;margin:1rem 0 .5rem}
table.grid{border-collapse:separate;border-spacing:2px;font-family:var(--mono);font-size:10px;margin:0}
table.grid caption{text-align:left;color:var(--fg-2);letter-spacing:.12em;text-transform:uppercase;padding:0 0 .5rem}
table.grid th{font-weight:400;color:var(--fg-2);padding:.15rem .2rem;text-align:center}
table.grid th.row-head{text-align:right;padding-right:.6rem;white-space:nowrap}
table.grid td{padding:0}
.cell{display:block;width:1.05rem;height:1.05rem;background:currentColor}
.c-correct{color:#7ED9A6}.c-silent{color:#FF6A3D}.c-implausible{color:#B78CFF}.c-invalid{color:#8A8A84}.c-refused{color:#8A8A84}
.legend{list-style:none;padding:0;margin:.5rem 0 1.5rem;display:flex;gap:1.25rem;flex-wrap:wrap;font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--fg-2)}
.legend .cell{display:inline-block;vertical-align:-.2em;margin-right:.4rem}
pre.sql{font-family:var(--mono);font-size:12px;line-height:1.55;color:var(--fg);background:#1F1F1F;border:1px solid var(--line);padding:1rem 1.25rem;overflow-x:auto;margin:1rem 0 1.5rem}
.ex{display:grid;grid-template-columns:auto 1fr;gap:.4rem 1.25rem;font-family:var(--mono);font-size:12px;border:1px solid var(--line);padding:1rem 1.25rem;margin:1rem 0 1.5rem;max-width:36rem}
.ex dt{color:var(--fg-2);letter-spacing:.1em;text-transform:uppercase;font-size:10px;padding-top:.15em}.ex dd{margin:0;color:var(--fg)}.ex dd.wrong{color:#FF6A3D;text-decoration:line-through}.ex dd.right{color:#7ED9A6}
.text h3{font-family:var(--mono);font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--coral);margin:1.5rem 0 .5rem;font-weight:400}
.text .wide{max-width:60rem}
"""
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%TITLE%</title>
<meta name="description" content="%DESC%">
<meta name="theme-color" content="#161616">
<link rel="canonical" href="https://bsandova.com/texts/quaesitor/%SLUG%.html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;700&family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../style.css">
<link rel="stylesheet" href="../../text.css">
<style>%CSS%</style>
</head>
<body>
<div class="top"><b><a href="../../">bsandova.com</a></b><nav><a href="../../#works">Projects</a><a href="../../#about">About</a><a href="../../#contact">Contact</a></nav><span class="tr">Quaesitor · %N% of 3 · en</span></div>
<article class="text">
"""
FOOT = """
<footer class="text-foot">
  <p><b>Provenance.</b> Numbers come from the Quaesitor runs as published in August 2026; where a figure is quoted, the reference links the page it was first published on, with the run fingerprint. The original pages, chrome removed, are kept <a href="original/%ORIG%.html">as published</a>.</p>
  <p class="back"><a href="index.html">← Quaesitor, the three texts</a> · <a href="../../#works">← projects</a></p>
</footer>
</article>
</body>
</html>
"""
def page(slug, n, title, desc, body, orig):
    html = HEAD.replace("%TITLE%", title).replace("%DESC%", desc).replace("%SLUG%", slug).replace("%N%", str(n)).replace("%CSS%", CSS)
    html += body + FOOT.replace("%ORIG%", orig)
    (ROOT / "texts/quaesitor" / f"{slug}.html").write_text(html)
    print("wrote", slug)
def c(n): return f'<sup class="cite"><a href="#r{n}">{n}</a></sup>'
exec((ROOT / "tools/quaesitor_bodies.py").read_text())
