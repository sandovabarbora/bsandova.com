"""All file I/O of the study apart from the model calls: subtitle files with their encoding, hashes and the manifest,
the author's song marks, the frozen prompts, JSON outputs."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import coding as K
import config as C


def read_srt(path: Path) -> tuple[str, str]:
    """UTF-8 (a BOM allowed), else cp1252 (design §2.1). Returns the text and the encoding used."""
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1252"), "cp1252"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(path: Path | None = None) -> dict[str, dict]:
    """`sha256  name  note` lines, keyed by name."""
    path = path or C.MANIFEST
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                sha, name, *note = line.split(maxsplit=2)
                out[name] = {"sha256": sha, "note": note[0] if note else ""}
    return out


def write_manifest_entry(name: str, sha: str, note: str, path: Path | None = None) -> None:
    path = path or C.MANIFEST
    entries = read_manifest(path)
    entries[name] = {"sha256": sha, "note": note}
    lines = [f"{e['sha256']}  {n}  {e['note']}".rstrip() for n, e in entries.items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def raw_note(path: Path, encoding: str, sdh: bool) -> str:
    return (f"{path.stat().st_size} bytes, read as {encoding}, {'SDH' if sdh else 'not SDH'} (sound cues found: "
            f"{'yes' if sdh else 'no'}), hashed {dt.date.today()}, gitignored")


def load_prompts(root: Path | None = None) -> dict[str, str]:
    return {name: ((root or C.PROMPTS) / name).read_text(encoding="utf-8") for name in K.PROMPT_FILES}


def load_song_marks(path: Path | None = None) -> dict[str, dict[tuple[int, int], str]] | None:
    """{film: {(first_cue, last_cue): 'song' | 'not song'}} from the committed marks file, or None if there is none."""
    path = path or C.SONG_MARKS
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {f: {(r["first_cue"], r["last_cue"]): r["mark"] for r in data.get(f, [])} for f in C.FILMS}


def write_json(path: Path, payload: Mapping | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
