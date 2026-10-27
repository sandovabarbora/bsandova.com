"""The blind validation sample (design §3.4): the seeded draw, the offline coding form and the check of the author's
codes. Pure: no file is read or written here."""
from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence

import coding
import config as C
import numpy as np
from subtitles import Cue, Scene


def draw(kept: Mapping[str, Sequence[Cue]], n: int = C.SAMPLE_PER_FILM, seed: int = C.SAMPLE_SEED) -> dict:
    """`n` kept cues from each film, uniformly without replacement, one generator over the kept cues sorted by film
    and cue number (PP1 first). The display order is a permutation drawn from the same generator afterwards."""
    rng = np.random.default_rng(seed)
    items = []
    for film in C.FILMS:
        ids = sorted(c.index for c in kept[film])
        if len(ids) < n:
            raise ValueError(f"{film} has {len(ids)} kept cues, fewer than the {n} to sample")
        pick = rng.choice(len(ids), size=n, replace=False)
        items += [{"film": film, "cue": ids[k]} for k in sorted(pick)]
    order = [int(k) for k in rng.permutation(len(items))]
    return {"seed": seed, "per_film": n, "items": items, "order": order}


def form_items(sample: Mapping, scenes: Mapping[str, Sequence[Scene]]) -> list[dict]:
    """Each sampled cue inside its scene, with the preceding scene as context: what the model is shown in pass 1."""
    out = []
    for k in sample["order"]:
        item = sample["items"][k]
        film_scenes = scenes[item["film"]]
        pos = next(i for i, s in enumerate(film_scenes) if item["cue"] in s.cue_ids)
        prev = film_scenes[pos - 1] if pos > 0 else None
        out.append({"film": item["film"], "cue": item["cue"],
                    "context": [[c.index, c.text] for c in prev.cues] if prev else [],
                    "scene": [[c.index, c.text] for c in film_scenes[pos].cues]})
    return out


def render_form(items: Sequence[Mapping]) -> str:
    """A self-contained page: no external request (a CSP forbids them), progress kept in the browser, the codes saved
    as validation-human.json (film, cue and codes only, no text)."""
    data = json.dumps(list(items), ensure_ascii=False).replace("</", "<\\/")
    opts = {"targets": C.TARGETS, "group_types": C.GROUP_TYPES, "butts": C.BUTTS}
    return FORM_TEMPLATE.replace("__DATA__", data).replace("__OPTS__", json.dumps(opts)).replace(
        "__N__", html.escape(str(len(items))))


def check_codes(payload: Mapping, sample: Mapping) -> list[dict]:
    """The author's codes, checked against the sample and the codebook. Raises ValueError on anything off."""
    codes = payload.get("codes")
    if not isinstance(codes, list):
        raise TypeError("the codes file has no list 'codes'")
    want = {(i["film"], i["cue"]) for i in sample["items"]}
    got = [(c.get("film"), c.get("cue")) for c in codes]
    if len(got) != len(set(got)) or set(got) != want:
        raise ValueError("the codes do not cover exactly the sampled cues, once each")
    return [_check_one(c) for c in codes]


def _check_one(c: Mapping) -> dict:
    where = f"{c.get('film')} cue {c.get('cue')}"
    allowed = {"film", "cue", "joke", "target", "group_type", "group_other", "butt"}
    if set(c) - allowed:
        raise ValueError(f"{where}: unknown fields {sorted(set(c) - allowed)}")
    joke = c.get("joke")
    base = {"film": c["film"], "cue": c["cue"]}
    if joke == C.SKIP or joke is False:
        if any(c.get(k) for k in ("target", "group_type", "group_other", "butt")):
            raise ValueError(f"{where}: a cue that is skipped or not a joke has no codes")
        return {**base, "joke": joke}
    if joke is not True:
        raise ValueError(f"{where}: joke must be true, false or 'skip'")
    try:
        codes = coding.check_codes(c.get("target"), c.get("group_type"), c.get("group_other"), c.get("butt"))
    except ValueError as err:
        raise ValueError(f"{where}: {err}") from err
    return {**base, "joke": True, **codes}


FORM_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'">
<title>Blind sample</title>
<style>
body { font: 16px/1.45 system-ui, sans-serif; max-width: 46rem; margin: 2rem auto; padding: 0 1rem; color: #111; background: #fff; }
.item { border-top: 1px solid #ccc; padding: 1rem 0; }
.ctx { color: #777; }
.cue { margin: .15rem 0; white-space: pre-wrap; }
.hl { background: #ffe58a; font-weight: 600; }
fieldset { border: 0; padding: 0; margin: .4rem 0; }
label { margin-right: .8rem; }
.done { color: #0a0; }
</style>
</head>
<body>
<h1>Blind sample: __N__ cues</h1>
<p>Is the highlighted cue part of a joke? If yes, code target, group type and butt by the codebook (design §2.4).
Mark <b>skip</b> if you cannot code it. Progress stays in this browser. When done, press <b>Save codes</b>: the file holds
film, cue number and codes only.</p>
<p><span id="count"></span> <button id="save">Save codes</button></p>
<div id="items"></div>
<script>
const ITEMS = __DATA__;
const OPTS = __OPTS__;
const KEY = "pitch-blind-sample";
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }
const id = it => it.film + ":" + it.cue;
function radios(name, values, cur) {
  return values.map(v => `<label><input type="radio" name="${name}" value="${v}"${cur === v ? " checked" : ""}> ${v}</label>`).join("");
}
function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
function render() {
  const root = document.getElementById("items");
  root.innerHTML = "";
  ITEMS.forEach((it, k) => {
    const s = state[id(it)] || {};
    const div = document.createElement("div");
    div.className = "item";
    const ctx = it.context.map(c => `<div class="cue ctx">[${c[0]}] ${esc(c[1])}</div>`).join("");
    const scene = it.scene.map(c => `<div class="cue${c[0] === it.cue ? " hl" : ""}">[${c[0]}] ${esc(c[1])}</div>`).join("");
    const n = "i" + k;
    div.innerHTML = `<p><b>${k + 1}.</b> cue ${it.cue}</p>${ctx}${scene}
      <fieldset>Joke: ${radios(n + "j", ["yes", "no", "skip"], s.joke)}</fieldset>
      <fieldset>Target: ${radios(n + "t", OPTS.targets, s.target)}</fieldset>
      <fieldset>Group type: ${radios(n + "g", OPTS.group_types, s.group_type)}
        <label>other: <input type="text" name="${n}o" value="${esc(s.group_other || "")}"></label></fieldset>
      <fieldset>Butt: ${radios(n + "b", OPTS.butts, s.butt)}</fieldset>`;
    div.addEventListener("change", () => {
      const pick = f => (div.querySelector(`input[name="${n}${f}"]:checked`) || {}).value;
      state[id(it)] = {joke: pick("j"), target: pick("t"), group_type: pick("g"),
                       group_other: div.querySelector(`input[name="${n}o"]`).value, butt: pick("b")};
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
      count();
    });
    root.appendChild(div);
  });
  count();
}
function count() {
  const done = ITEMS.filter(it => (state[id(it)] || {}).joke).length;
  document.getElementById("count").textContent = done + " of " + ITEMS.length + " answered";
}
document.getElementById("save").addEventListener("click", () => {
  const codes = ITEMS.map(it => {
    const s = state[id(it)] || {};
    const out = {film: it.film, cue: it.cue};
    if (s.joke === "skip") { out.joke = "skip"; return out; }
    if (s.joke !== "yes") { out.joke = s.joke === "no" ? false : null; return out; }
    out.joke = true;
    out.target = s.target || null;
    out.group_type = s.target === "group" ? (s.group_type || null) : "";
    out.group_other = out.group_type === "other" ? (s.group_other || "").trim() : "";
    out.butt = s.butt || null;
    return out;
  });
  const blob = new Blob([JSON.stringify({codes: codes}, null, 1) + "\\n"], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "validation-human.json";
  a.click();
});
render();
</script>
</body>
</html>
"""
