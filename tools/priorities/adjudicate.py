"""The adjudication sheet of the validation sample (priorities design §2.2): the speeches on which the two coders
disagree, with their two topics and the text, for the author to decide without the classifier's label. Writes
tools/data/priorities/validation/adjudicate.html (a local page; the decisions are saved as adjudication.json by its
button) and prints the coders' raw agreement.

    python3 -I tools/priorities/adjudicate.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "tools/data/priorities/validation"
TOPICS = ["Macroeconomics", "Civil Rights", "Health", "Agriculture", "Labor", "Education", "Environment", "Energy",
          "Immigration", "Transportation", "Law and Crime", "Social Welfare", "Housing", "Domestic Commerce", "Defense",
          "Technology", "Foreign Trade", "International Affairs", "Government Operations", "Public Lands", "Culture",
          "Other"]


def coded(model: str) -> dict:
    out = {}
    for f in sorted(V.glob(f"coding-{model}-*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            assert r["topic"] in TOPICS, (f.name, r)
            out[r["key"]] = r["topic"]
    return out


def main() -> None:
    texts = {}
    for f in sorted(V.glob("batch-*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            texts[r["key"]] = r
    a, b = coded("sonnet"), coded("opus")
    assert set(a) == set(b) == set(texts), "a coder file is missing"
    diff = sorted(k for k in texts if a[k] != b[k])
    print(f"{len(texts)} speeches; coders agree on {len(texts) - len(diff)} ({1 - len(diff) / len(texts):.1%}); "
          f"{len(diff)} to adjudicate")
    opts = "".join(f"<option>{t}</option>" for t in TOPICS)
    items = []
    for i, k in enumerate(diff, 1):
        t = texts[k]
        choices = [a[k], b[k]]
        radios = "".join(f'<label><input type="radio" name="{k}" value="{html.escape(c)}"> {html.escape(c)}</label>'
                         for c in dict.fromkeys(choices))
        items.append(f"""<section id="{k}"><h2>{i}/{len(diff)} · {k} · {t['words']} words{' (cut at 1 500)' if t['cut'] else ''}</h2>
<div class="choice">{radios}<label><input type="radio" name="{k}" value="__other"> other:</label>
<select data-for="{k}"><option value=""></option>{opts}</select></div>
<p class="text">{html.escape(t['text'])}</p></section>""")
    page = f"""<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Adjudication</title><style>
:root{{--ink:#111;--muted:#666;--line:#ddd;--bg:#fff}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--ink:#eee;--muted:#aaa;--line:#333;--bg:#161616}}}}
body{{font:15px/1.55 system-ui,sans-serif;color:var(--ink);background:var(--bg);max-width:820px;margin:0 auto;padding:16px}}
h1{{font-size:20px}} h2{{font:500 13px ui-monospace,monospace;color:var(--muted)}} section{{border-top:1px solid var(--line);padding:12px 0}}
.choice{{display:flex;flex-wrap:wrap;gap:14px;margin:6px 0 10px;position:sticky;top:0;background:var(--bg);padding:6px 0}}
.text{{white-space:pre-wrap}} #bar{{position:sticky;bottom:0;background:var(--bg);border-top:1px solid var(--line);padding:10px 0}}
button{{font:inherit;padding:6px 14px}}
</style></head><body><h1>Rozhodni téma u {len(diff)} projevů</h1>
<p>Dva hodnotitelé se neshodli. Vyber téma, o kterém projev hlavně je (podle CAP), nebo zvol jiné. Štítek klasifikátoru tu není. Postup se průběžně ukládá v prohlížeči.</p>
{''.join(items)}
<div id="bar"><span id="count"></span> <button id="save">Uložit adjudication.json</button></div>
<script>
const KEY='prio-adjudication';
let st={{}}; try{{st=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
const keys=[...document.querySelectorAll('section')].map(s=>s.id);
function val(k){{const r=document.querySelector(`input[name="${{k}}"]:checked`); if(!r) return null;
  return r.value==='__other' ? (document.querySelector(`select[data-for="${{k}}"]`).value||null) : r.value}}
function sync(){{keys.forEach(k=>{{const v=val(k); if(v) st[k]=v; else delete st[k]}});
  try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}}
  document.getElementById('count').textContent=Object.keys(st).length+' / '+keys.length}}
keys.forEach(k=>{{const v=st[k]; if(!v) return; const r=[...document.querySelectorAll(`input[name="${{k}}"]`)].find(x=>x.value===v);
  if(r) r.checked=true; else {{document.querySelector(`input[name="${{k}}"][value="__other"]`).checked=true;
  document.querySelector(`select[data-for="${{k}}"]`).value=v}}}});
document.addEventListener('change',sync); sync();
document.getElementById('save').onclick=()=>{{sync(); const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify(st,null,1)],{{type:'application/json'}})); a.download='adjudication.json'; a.click()}};
</script></body></html>"""
    (V / "adjudicate.html").write_text(page, encoding="utf-8")
    (V / "agreement.json").write_text(json.dumps({"speeches": len(texts), "agree": len(texts) - len(diff),
                                                  "disagree": len(diff)}, indent=1))


if __name__ == "__main__":
    main()
