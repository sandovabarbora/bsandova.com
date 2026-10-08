"""Build texts/prague-programmes-2026.html from assets/programmes-2026/ratings.json.

Every promise carries why it can be done and why it cannot (or what limits it), each with its
references; references are numbered by first citation across the page, prose first. The counts in
the facts strip and the overview come from the same file.

    python3 tools/notes/programmes_2026.py
"""
from __future__ import annotations

import collections
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "assets/programmes-2026/ratings.json").read_text(encoding="utf-8"))
REFS = D["refs"]
# references added after the audit of 3 October 2026
ACCESSED = {"DPPD": "3 October 2026", "OZV18": "3 October 2026", "EU1028": "3 October 2026"}
LABEL = {"yes": "yes", "likely": "likely", "partly": "partly", "no": "not in one term", "other": "state or another body"}
e = html.escape
order: list[str] = []


def cite(keys: list[str], source: str | None = None) -> str:
    out = []
    for k in keys:
        if k == "PROG":
            out.append(f' <a class="prog-src" href="{source}">programme</a>')
            continue
        if k not in order:
            order.append(k)
        n = order.index(k) + 1
        out.append(f'<sup class="cite"><a href="#r{n}">{n}</a></sup>')
    return "".join(out)


def chip(k: str) -> str:
    return f'<span class="rt rt-{k}">{LABEL[k]}</span>'


page = (ROOT / "tools/notes/programmes_2026.template.html").read_text(encoding="utf-8")
# prose citations first, in reading order
page = re.sub(r"\{\{ref:([A-Z0-9]+)\}\}", lambda m: cite([m.group(1)]), page)


def list_section(l: dict) -> str:
    cards = []
    for p, k, can, cannot, rc, rn in l["rows"]:
        cards.append(f"""    <article class="pr pr-{k}">
      <div class="pr-head">{chip(k)}<h3>{e(p)}</h3></div>
      <div class="pr-why">
        <div class="pr-can"><p class="pr-lab">Why it can</p><p>{e(can)}{cite(rc, l['source'])}</p></div>
        <div class="pr-not"><p class="pr-lab">Why not</p><p>{e(cannot)}{cite(rn, l['source'])}</p></div>
      </div>
    </article>""")
    unv = "".join(f"<li>{e(u)}</li>" for u in l["unverified"])
    return f"""<details class="prog" id="{l['id']}">
  <summary><span class="prog-no">{l['no']}</span><span class="prog-name">{e(l['name'])}</span><span class="prog-n">{len(l['rows'])} promises</span></summary>
  <p class="prog-verdict">{e(l['verdict'])}</p>
  <div class="prs">
{chr(10).join(cards)}
  </div>
  <div class="prog-foot">
    <div><p class="pr-lab">Not checked here</p><ul>{unv}</ul></div>
    <div><p class="pr-lab">Overall</p><p>{e(l['overall'])}</p></div>
  </div>
  <p class="note">Source: <a href="{l['source']}">{e(l['source'].split('//')[1].rstrip('/'))}</a>, {e(l['captured'])}. A reason with no reference rests on the author's reading of the programme and of the city's practice.</p>
</details>"""


def bar(c: collections.Counter, n: int) -> str:
    segs = "".join(f'<span class="seg rt-{k}" style="flex:{c[k]}" title="{LABEL[k]}: {c[k]}"></span>' for k in LABEL if c[k])
    leg = "".join(f'<li><span class="sw rt-{k}"></span>{LABEL[k]} <b>{c[k]}</b></li>' for k in LABEL)
    return f'<div class="bar" role="img" aria-label="{n} promises by rating">{segs}</div><ul class="bar-leg">{leg}</ul>'


COLOURS = {"yes": "#2f8a5b", "likely": "#8cc6a2", "partly": "#d9a83a", "no": "#c0503f", "other": "#8a939e"}


def parties_chart() -> tuple[str, str]:
    """fig. 1: promises by rating per programme, as a stacked bar per list (charts.js) and a static SVG fallback."""
    rows, shares = [], []
    names = [f"{l['no']} {l['name']}" for l in D["lists"]]
    for l, name in zip(D["lists"], names):
        cc = collections.Counter(r[1] for r in l["rows"])
        x = 0
        for k in LABEL:
            if cc[k]:
                rows.append({"y": name, "x0": x, "x1": x + cc[k], "c": COLOURS[k],
                             "tip": f"{l['name']}: {LABEL[k]} {cc[k]} of {len(l['rows'])}"})
                x += cc[k]
        shares.append((cc["yes"] + cc["likely"]) / len(l["rows"]))
    top = max(len(l["rows"]) for l in D["lists"])
    spec = {"parties": {
        "alt": "Stacked bars of the promises read in each of the six programmes by rating.",
        "panels": [{"h": 40 * len(names) + 20, "x": {"kind": "linear", "domain": [0, top], "fmt": {"dp": 0},
                                                       "label": "promises read"},
                    "y": {"kind": "cat", "domain": names}, "marks": [{"type": "hbar", "rows": rows}]}],
        "legend": [{"label": LABEL[k], "c": COLOURS[k], "shape": "box", "o": 1} for k in LABEL],
        "table": {"cols": ["programme", *[LABEL[k] for k in LABEL]],
                  "rows": [[n, *[collections.Counter(r[1] for r in l["rows"])[k] for k in LABEL]] for n, l in zip(names, D["lists"])]},
        "data": ["ratings.json"]}}
    (ROOT / "assets/programmes-2026/charts.json").write_text(json.dumps(spec, ensure_ascii=False))
    w, rh, left = 720, 34, 150
    sx = (w - left - 20) / top
    bars = []
    for i, name in enumerate(names):
        bars.append(f'<text x="{left - 8}" y="{20 + i * rh + 16}" text-anchor="end" font-size="12" font-family="Helvetica">{e(name)}</text>')
        for r in [r for r in rows if r["y"] == name]:
            bars.append(f'<rect x="{left + r["x0"] * sx:.1f}" y="{20 + i * rh + 4}" width="{(r["x1"] - r["x0"]) * sx:.1f}" height="20" fill="{r["c"]}"/>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {40 + len(names) * rh}">{"".join(bars)}</svg>'
    (ROOT / "assets/programmes-2026/01-parties.svg").write_text(svg)
    lo, hi = round(100 * min(shares)), round(100 * max(shares))
    head = f"In each programme, between {lo} % and {hi} % of the promises read are within the city's powers in one term, rated yes or likely."
    alt = (f"Stacked bars for the six programmes, each split into promises rated yes, likely, partly, not in one term and "
           f"decided by the state or another body; the share rated yes or likely ranges from {lo} % to {hi} %.")
    return head, alt


PHEAD, PALT = parties_chart()
FILTERS = '<button type="button" data-k="all" aria-pressed="true">all</button>' + "".join(
    f'<button type="button" data-k="{k}" aria-pressed="false">{LABEL[k]}</button>' for k in LABEL)


SECTIONS = "\n".join(list_section(l) for l in D["lists"])
rows = [r for l in D["lists"] for r in l["rows"]]
c = collections.Counter(r[1] for r in rows)
REFLIST = "\n".join(f'<li id="r{i}">{e(REFS[k]).replace("https://", "<a href=\"https://").replace(" (", " (") }</li>'.replace('<a href="https://', 'https://') for i, k in enumerate(order, 1))
REFLIST = "\n".join(
    f'<li id="r{i}">' + re.sub(r"(https://\S+)", lambda m: f'<a href="{m.group(1)}">{e(m.group(1).split("//")[1])}</a>', e(REFS[k])) + f" Accessed {ACCESSED.get(k, '1 October 2026')}.</li>"
    for i, k in enumerate(order, 1))
for k, v in {"{{N}}": len(rows), "{{DOABLE}}": c["yes"] + c["likely"], "{{LIKELY}}": c["likely"], "{{OTHER}}": c["other"], "{{NO}}": c["no"],
             "{{PARTLY}}": c["partly"], "{{SECTIONS}}": SECTIONS, "{{BAR}}": bar(c, len(rows)), "{{JUMP}}": "".join(f'<a href="#{l["id"]}">{l["no"]} {e(l["name"])}</a>' for l in D["lists"]), "{{REFS}}": REFLIST, "{{PHEAD}}": PHEAD, "{{PALT}}": PALT, "{{FILTERS}}": FILTERS}.items():
    page = page.replace(k, str(v))
(ROOT / "texts/prague-programmes-2026.html").write_text(page, encoding="utf-8")
print(f"{len(rows)} promises: {dict(c)}; {len(order)} references")
