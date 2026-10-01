"""Build texts/prague-programmes-2026.html from assets/programmes-2026/ratings.json.

The ratings file holds one row per promise for each of the six programmes; this script writes the
overview, the per-list tables and the counts in the facts strip, so every number on the page comes
from the data file.

    python3 tools/notes/programmes_2026.py
"""
from __future__ import annotations

import collections
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "assets/programmes-2026/ratings.json").read_text(encoding="utf-8"))
LABEL = {"yes": "yes", "likely": "likely", "partly": "partly", "no": "not in one term", "other": "state or another body"}
e = html.escape

rows = [r for l in D["lists"] for r in l["rows"]]
c = collections.Counter(r[1] for r in rows)
N, DOABLE, OTHER, NO = len(rows), c["yes"] + c["likely"], c["other"], c["no"]


def chip(k: str) -> str:
    return f'<span class="rt rt-{k}">{LABEL[k]}</span>'


def list_section(l: dict) -> str:
    trs = "\n".join(f"      <tr><td>{e(p)}</td><td class=\"v\">{chip(k)}</td><td>{e(w)}</td></tr>" for p, k, w in l["rows"])
    unv = "".join(f"<li>{e(u)}</li>" for u in l["unverified"])
    return f"""<details class="prog" id="{l['id']}">
  <summary>List {l['no']} · {e(l['name'])} <small>{len(l['rows'])} promises</small></summary>
  <p>{e(l['verdict'])}</p>
  <div class="ht-wrap"><table class="ht">
    <thead><tr><th>Promise</th><th>Within one term</th><th>Why</th></tr></thead>
    <tbody>
{trs}
    </tbody>
  </table></div>
  <p><b>Not checked here:</b></p><ul>{unv}</ul>
  <p><b>Overall:</b> {e(l['overall'])}</p>
  <p class="note">Source: <a href="{l['source']}">{e(l['source'].split('//')[1].rstrip('/'))}</a>, {e(l['captured'])}.</p>
</details>"""


SECTIONS = "\n".join(list_section(l) for l in D["lists"])
page = (ROOT / "tools/notes/programmes_2026.template.html").read_text(encoding="utf-8")
for k, v in {"{{N}}": N, "{{DOABLE}}": DOABLE, "{{OTHER}}": OTHER, "{{NO}}": NO, "{{PARTLY}}": c["partly"],
             "{{SECTIONS}}": SECTIONS}.items():
    page = page.replace(k, str(v))
(ROOT / "texts/prague-programmes-2026.html").write_text(page, encoding="utf-8")
print(f"{N} promises: {dict(c)}")
