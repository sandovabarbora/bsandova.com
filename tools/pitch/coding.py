"""The two model passes as pure functions (design §2.3, §2.4): the prompts built from the frozen files and the strict
parsing of the replies. No call is made here."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence

import config as C
from subtitles import Scene

PROMPT_FILES = ("segment_system.txt", "segment_user.txt", "code_system.txt", "code_user.txt", "codebook.md")
FENCE = re.compile(r"^```(?:json)?\s*\n(.*)\n```$", re.DOTALL)


class BadReply(ValueError):
    """A reply that does not parse or uses a value outside the codebook. Retried once, then logged as failed."""


def render_scene(scene: Scene | None, mark: tuple[int, int] | None = None) -> str:
    if scene is None:
        return "(none: this is the first scene)"
    out = []
    for c in scene.cues:
        inside = mark is not None and _between(scene, c.index, *mark)
        out.append(f"{'>> ' if inside else ''}[{c.index}] {' / '.join(c.lines)}")
    return "\n".join(out)


def _between(scene: Scene, cue: int, first: int, last: int) -> bool:
    pos = {i: k for k, i in enumerate(scene.cue_ids)}
    return pos[first] <= pos[cue] <= pos[last]


def _fill(template: str, **values: str) -> str:
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    return template


def segment_prompt(prompts: Mapping[str, str], prev: Scene | None, scene: Scene) -> tuple[str, str]:
    user = _fill(prompts["segment_user.txt"], CONTEXT=render_scene(prev), SCENE=render_scene(scene),
                 FIRST=str(scene.cue_ids[0]), LAST=str(scene.cue_ids[-1]))
    return prompts["segment_system.txt"], user


def code_prompt(prompts: Mapping[str, str], scene: Scene, joke: Mapping) -> tuple[str, str]:
    system = _fill(prompts["code_system.txt"], CODEBOOK=prompts["codebook.md"].strip())
    user = _fill(prompts["code_user.txt"], SCENE=render_scene(scene, (joke["first_cue"], joke["last_cue"])),
                 FIRST=str(joke["first_cue"]), LAST=str(joke["last_cue"]))
    return system, user


def prompt_hashes(prompts: Mapping[str, str]) -> dict[str, str]:
    return {name: hashlib.sha256(prompts[name].encode("utf-8")).hexdigest() for name in PROMPT_FILES}


def segment_schema(scene: Scene) -> dict:
    """Pass 1's structured-output schema: cue numbers limited to the scene's own, kind to the codebook."""
    ids = list(scene.cue_ids)
    item = {"type": "object", "properties": {"first_cue": {"type": "integer", "enum": ids},
                                             "last_cue": {"type": "integer", "enum": ids},
                                             "kind": {"type": "string", "enum": list(C.KINDS)}},
            "required": ["first_cue", "last_cue", "kind"], "additionalProperties": False}
    return {"type": "object", "properties": {"jokes": {"type": "array", "items": item}}, "required": ["jokes"],
            "additionalProperties": False}


CODE_SCHEMA = {
    "type": "object",
    "properties": {"target": {"type": "string", "enum": list(C.TARGETS)},
                   "group_type": {"type": "string", "enum": ["", *C.GROUP_TYPES]},
                   "group_other": {"type": "string"},
                   "butt": {"type": "string", "enum": list(C.BUTTS)}},
    "required": ["target", "group_type", "group_other", "butt"],
    "additionalProperties": False,
}


def parse_json(text: str):
    """The whole reply must be one JSON value; a single ```json fence around the whole reply is the only wrapper taken."""
    body = text.strip()
    m = FENCE.match(body)
    if m:
        body = m.group(1).strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError as err:
        raise BadReply(f"not JSON: {err.msg}") from err


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def parse_segments(text: str, scene: Scene) -> list[dict]:
    """Pass 1: {"jokes": [{first_cue, last_cue, kind}, ...]}, every cue number inside the scene and first not after
    last. The schema already constrains this; the check stays as a second guard."""
    data = parse_json(text)
    if not isinstance(data, dict) or set(data) != {"jokes"} or not isinstance(data["jokes"], list):
        raise BadReply('pass 1 reply is not {"jokes": [...]}')
    data = data["jokes"]
    ids = set(scene.cue_ids)
    out = []
    for item in data:
        if not isinstance(item, dict) or set(item) != {"first_cue", "last_cue", "kind"}:
            raise BadReply("each joke must be exactly {first_cue, last_cue, kind}")
        first, last, kind = item["first_cue"], item["last_cue"], item["kind"]
        if not (_is_int(first) and _is_int(last)) or first not in ids or last not in ids:
            raise BadReply(f"cue numbers outside the scene: {first}, {last}")
        if not _between(scene, last, first, scene.cue_ids[-1]):
            raise BadReply(f"first cue {first} comes after last cue {last}")
        if kind not in C.KINDS:
            raise BadReply(f"kind outside the codebook: {kind!r}")
        out.append({"first_cue": first, "last_cue": last, "kind": kind})
    return out


def check_codes(target, group_type, group_other, butt) -> dict:
    """The codebook rule shared by the model's and the author's codes. Raises ValueError."""
    gtype = group_type or ""
    other = (group_other or "").strip()
    if target not in C.TARGETS or butt not in C.BUTTS:
        raise ValueError("target or butt outside the codebook")
    if not all(isinstance(v, str) for v in (gtype, other)):
        raise ValueError("group type and group must be text")
    if (target == "group") != bool(gtype) or (gtype and gtype not in C.GROUP_TYPES):
        raise ValueError("group type is required for target group and only for it")
    if (gtype == "other") != bool(other):
        raise ValueError("the group is written down for group type other and only for it")
    return {"target": target, "group_type": gtype, "group_other": other, "butt": butt}


def parse_codes(text: str) -> dict:
    """Pass 2: exactly {target, group_type, group_other, butt} within the codebook (a second guard after the schema)."""
    data = parse_json(text)
    if not isinstance(data, dict) or set(data) != {"target", "group_type", "group_other", "butt"}:
        raise BadReply("pass 2 reply must be exactly {target, group_type, group_other, butt}")
    try:
        return check_codes(data["target"], data["group_type"], data["group_other"], data["butt"])
    except ValueError as err:
        raise BadReply(str(err)) from err


def joke_records(scene: Scene, segments: Sequence[Mapping]) -> list[dict]:
    return [{"id": f"{scene.number}-{k + 1}", "scene": scene.number, **s} for k, s in enumerate(segments)]


def is_protected(code: Mapping) -> bool:
    return code.get("target") == "group" and code.get("group_type") in C.PROTECTED
