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
    trs = []
    for p, k, can, cannot, rc, rn in l["rows"]:
        trs.append(f"      <tr><td>{e(p)}</td><td class=\"v\">{chip(k)}</td>"
                   f"<td><b>Why it can:</b> {e(can)}{cite(rc, l['source'])}<br><b>Why not:</b> {e(cannot)}{cite(rn, l['source'])}</td></tr>")
    unv = "".join(f"<li>{e(u)}</li>" for u in l["unverified"])
    return f"""<details class="prog" id="{l['id']}">
  <summary>List {l['no']} · {e(l['name'])} <small>{len(l['rows'])} promises</small></summary>
  <p>{e(l['verdict'])}</p>
  <div class="ht-wrap"><table class="ht">
    <thead><tr><th>Promise</th><th>Within one term</th><th>Why it can, and why not</th></tr></thead>
    <tbody>
{chr(10).join(trs)}
    </tbody>
  </table></div>
  <p><b>Not checked here:</b></p><ul>{unv}</ul>
  <p><b>Overall:</b> {e(l['overall'])}</p>
  <p class="note">Source: <a href="{l['source']}">{e(l['source'].split('//')[1].rstrip('/'))}</a>, {e(l['captured'])}. A reason with no reference rests on the author's reading of the programme and of the city's practice.</p>
</details>"""


SECTIONS = "\n".join(list_section(l) for l in D["lists"])
rows = [r for l in D["lists"] for r in l["rows"]]
c = collections.Counter(r[1] for r in rows)
REFLIST = "\n".join(f'<li id="r{i}">{e(REFS[k]).replace("https://", "<a href=\"https://").replace(" (", " (") }</li>'.replace('<a href="https://', 'https://') for i, k in enumerate(order, 1))
REFLIST = "\n".join(
    f'<li id="r{i}">' + re.sub(r"(https://\S+)", lambda m: f'<a href="{m.group(1)}">{e(m.group(1).split("//")[1])}</a>', e(REFS[k])) + " Accessed 1 October 2026.</li>"
    for i, k in enumerate(order, 1))
for k, v in {"{{N}}": len(rows), "{{DOABLE}}": c["yes"] + c["likely"], "{{OTHER}}": c["other"], "{{NO}}": c["no"],
             "{{PARTLY}}": c["partly"], "{{SECTIONS}}": SECTIONS, "{{REFS}}": REFLIST}.items():
    page = page.replace(k, str(v))
(ROOT / "texts/prague-programmes-2026.html").write_text(page, encoding="utf-8")
print(f"{len(rows)} promises: {dict(c)}; {len(order)} references")
