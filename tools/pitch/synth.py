"""Invented subtitle files and a scripted stand-in for the model, for the dry run and the tests. Every line is made
up from a fixed vocabulary; nothing resembles either film."""
from __future__ import annotations

import json
import re

import numpy as np
from client import Reply

WORDS = ("kettle", "umbrella", "tram", "spreadsheet", "pigeon", "lasagne", "sock", "tuba", "cactus", "ferry")
TAGS = ("", "", "", "JOKE", "JOKE AMERICA", "JOKE WEIGHT", "JOKE WEIGHT SELF", "JOKE OTHERGROUP", "ALLUSION GENRE",
        "JOKE RELIGION UNCLEAR", "JOKE GENDER SELF")


def _stamp(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt_file(seed: int, n_cues: int = 400, songs: bool = True) -> str:
    """Cues 2 to 4 s long with gaps drawn so that scenes form, a few song cues marked with ♪, a few sound cues."""
    rng = np.random.default_rng(seed)
    t, blocks = 5.0, []
    for i in range(1, n_cues + 1):
        t += float(rng.choice([0.3, 1.0, 2.0, 12.0], p=[0.5, 0.25, 0.15, 0.1]))
        dur = float(rng.uniform(2, 4))
        words = " ".join(rng.choice(WORDS, 4))
        tag = str(rng.choice(TAGS))
        kind = rng.random()
        if songs and kind < 0.04:
            text = f"♪ The {words} ♪"
        elif kind < 0.07:
            text = "[door creaks]"
        else:
            text = f"The {words}. {tag}".strip()
        blocks.append(f"{i}\n{_stamp(t)} --> {_stamp(t + dur)}\n{text}\n")
        t += dur
    return "\n".join(blocks)


class ScriptedModel:
    """Finds a joke at every cue whose text carries JOKE or ALLUSION and codes it from the other words."""

    def __init__(self, noise_seed: int | None = None):
        self.rng = np.random.default_rng(noise_seed) if noise_seed is not None else None

    def call(self, system: str, user: str, max_tokens: int, schema: dict) -> Reply:
        if "Scene to segment" in user:
            block = user.split("Scene to segment", 1)[1]
            jokes = []
            for m in re.finditer(r"^\[(\d+)\] (.*)$", block, re.MULTILINE):
                if "JOKE" in m.group(2) or "ALLUSION" in m.group(2):
                    if self.rng is not None and self.rng.random() < 0.1:
                        continue
                    kind = "allusion" if "ALLUSION" in m.group(2) else "joke"
                    jokes.append({"first_cue": int(m.group(1)), "last_cue": int(m.group(1)), "kind": kind})
            return Reply(json.dumps({"jokes": jokes}), "scripted", "end_turn", len(user) // 4, 20)
        marked = " ".join(m.group(1) for m in re.finditer(r"^>> \[\d+\] (.*)$", user, re.MULTILINE))
        return Reply(json.dumps(code_from_text(marked)), "scripted", "end_turn", len(user) // 4, 20)


def code_from_text(text: str) -> dict:
    target, gtype, other = "character", "", ""
    for word, gt in (("WEIGHT", "weight"), ("RELIGION", "religion"), ("GENDER", "gender")):
        if word in text:
            target, gtype = "group", gt
    if "OTHERGROUP" in text:
        target, gtype, other = "group", "other", "dentists"
    elif "AMERICA" in text and target == "character":
        target = "america"
    elif "GENRE" in text and target == "character":
        target = "genre"
    butt = "speaker" if "SELF" in text else "unclear" if "UNCLEAR" in text else "group"
    return {"target": target, "group_type": gtype, "group_other": other, "butt": butt}
