"""Parsing, cleaning and scene building of a subtitle file (design §2.2). Pure: text in, cues and counts out."""
from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterable, Mapping, Sequence

import config as C

TIME = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})(?:\s.*)?$")
INDEX = re.compile(r"^\s*(\d+)\s*$")
SOUND = re.compile(r"\[[^\[\]]*\]|\([^()]*\)", re.DOTALL)
TAG = re.compile(r"</?[a-zA-Z][^<>]*>|\{\\[^{}]*\}")
ITALIC = re.compile(r"<i>(.*?)</i>", re.DOTALL | re.IGNORECASE)
# a line left with only a dialogue dash ("- [laughs]") says nothing, so it is empty
EMPTY = re.compile(r"^[\s\-–—]*$")


class MalformedSrt(ValueError):
    """A cue without a valid time line, a duplicate index or an end before its start. The run stops (design §2.2.1)."""


class NeedsSongMarks(ValueError):
    """The lyric fallback applies and the author's marks are missing or do not match the listed runs."""


@dataclasses.dataclass(frozen=True)
class Cue:
    """Times in integer milliseconds, as the file writes them, so that the 8 s rule compares exact values."""
    index: int
    start_ms: int
    end_ms: int
    lines: tuple[str, ...]

    @classmethod
    def secs(cls, index: int, start: float, end: float, lines: tuple[str, ...]) -> Cue:
        return cls(index, round(start * 1000), round(end * 1000), lines)

    @property
    def start(self) -> float:
        return self.start_ms / 1000

    @property
    def end(self) -> float:
        return self.end_ms / 1000

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclasses.dataclass(frozen=True)
class Scene:
    number: int
    cues: tuple[Cue, ...]

    @property
    def start_ms(self) -> int:
        return self.cues[0].start_ms

    @property
    def end_ms(self) -> int:
        return max(c.end_ms for c in self.cues)

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def start(self) -> float:
        return self.start_ms / 1000

    @property
    def end(self) -> float:
        return self.end_ms / 1000

    @property
    def duration(self) -> float:
        return self.duration_ms / 1000

    @property
    def cue_ids(self) -> tuple[int, ...]:
        return tuple(c.index for c in self.cues)


def _ms(h: str, m: str, s: str, ms: str) -> int:
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms.ljust(3, "0"))


def parse_srt(text: str) -> list[Cue]:
    """Every cue of the file, in file order. A cue starts at an index line; its next line must be a valid time line."""
    lines = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues: list[Cue] = []
    seen: set[int] = set()
    i, n = 0, len(lines)
    while i < n:
        if not lines[i].strip():
            i += 1
            continue
        m = INDEX.match(lines[i])
        if not m:
            raise MalformedSrt(f"line {i + 1}: expected a cue index, found {lines[i].strip()[:40]!r}")
        index = int(m.group(1))
        t = TIME.match(lines[i + 1]) if i + 1 < n else None
        if not t:
            raise MalformedSrt(f"line {i + 2}: cue {index} has no valid time line")
        start, end = _ms(*t.groups()[:4]), _ms(*t.groups()[4:])
        if end < start:
            raise MalformedSrt(f"line {i + 2}: cue {index} ends before it starts")
        if index in seen:
            raise MalformedSrt(f"line {i + 1}: cue index {index} appears twice")
        seen.add(index)
        j, text_lines = i + 2, []
        while j < n and not _starts_cue(lines, j):
            text_lines.append(lines[j])
            j += 1
        while text_lines and not text_lines[-1].strip():
            text_lines.pop()
        cues.append(Cue(index, start, end, tuple(ln.strip() for ln in text_lines if ln.strip())))
        i = j
    return cues


def _starts_cue(lines: Sequence[str], j: int) -> bool:
    # an "index / time" pair opens the next cue, with or without the blank line before it; after a blank line, an index
    # or a time line alone opens one too, so that a malformed cue stops the run instead of joining the text above
    def opens(k: int) -> bool:
        return k + 1 < len(lines) and bool(INDEX.match(lines[k])) and bool(TIME.match(lines[k + 1]))
    if opens(j):
        return True
    nxt = lines[j + 1] if j + 1 < len(lines) else ""
    return not lines[j].strip() and (bool(INDEX.match(nxt)) or bool(TIME.match(nxt)))


def _bare(line: str) -> str:
    return TAG.sub("", line).strip()


def is_lyric_line(line: str) -> bool:
    bare = _bare(line)
    return any(s in line for s in C.LYRIC_SYMBOLS) or bare.startswith(C.LYRIC_HASH) or bare.endswith(C.LYRIC_HASH)


def has_lyric_markers(cues: Iterable[Cue]) -> bool:
    return any(is_lyric_line(ln) for c in cues for ln in c.lines)


def is_wholly_italic(cue: Cue) -> bool:
    text = cue.text.strip()
    if not text:
        return False
    inside = "".join(ITALIC.findall(text))
    return bool(inside.strip()) and not _bare(ITALIC.sub("", text))


def italic_runs(cues: Sequence[Cue], min_len: int = C.ITALIC_RUN_MIN) -> list[dict]:
    """Runs of at least `min_len` consecutive cues (file order) whose text is wholly in italics, for the author to mark
    song or not song (design §2.2.2, decision H). Cue numbers and times only, no text."""
    runs, cur = [], []
    for c in [*cues, None]:
        if c is not None and is_wholly_italic(c):
            cur.append(c)
            continue
        if len(cur) >= min_len:
            runs.append({"first_cue": cur[0].index, "last_cue": cur[-1].index, "cues": len(cur),
                         "start": cur[0].start, "end": cur[-1].end})
        cur = []
    return runs


def _check_marks(runs: Sequence[dict], marks: Mapping[tuple[int, int], str] | None) -> set[tuple[int, int]]:
    listed = {(r["first_cue"], r["last_cue"]) for r in runs}
    if not listed:
        return set()
    if marks is None:
        raise NeedsSongMarks(f"no ♪, ♫ or # marker: {len(listed)} italic runs need the author's song marks")
    if set(marks) != listed:
        raise NeedsSongMarks("the song marks do not cover exactly the italic runs listed by the code")
    bad = {v for v in marks.values() if v not in ("song", "not song")}
    if bad:
        raise NeedsSongMarks(f"a song mark must be 'song' or 'not song', found {sorted(bad)}")
    return {k for k, v in marks.items() if v == "song"}


def strip_sound(text: str) -> str:
    return SOUND.sub("", text)


def strip_tags(text: str) -> str:
    return TAG.sub("", text)


def clean(cues: Sequence[Cue], song_marks: Mapping[tuple[int, int], str] | None = None) -> tuple[list[Cue], dict]:
    """Steps 2 to 4 of design §2.2: lyric lines out (or, without any marker, the runs the author marked song), sound
    cues out, formatting tags out, empty cues dropped. Returns the kept cues and the counts dropped at each step."""
    fallback = not has_lyric_markers(cues)
    report = {"raw_cues": len(cues), "raw_lines": sum(len(c.lines) for c in cues), "lyric_fallback": fallback,
              "lyric_lines_removed": 0, "italic_runs": 0, "italic_runs_song": 0, "song_run_cues_removed": 0,
              "cues_dropped_at_lyrics": 0, "lines_dropped_at_sound_and_tags": 0, "cues_dropped_at_sound_and_tags": 0}
    step2: list[Cue] = []
    if fallback:
        runs = italic_runs(cues)
        songs = _check_marks(runs, song_marks)
        report["italic_runs"], report["italic_runs_song"] = len(runs), len(songs)
        pos = {c.index: k for k, c in enumerate(cues)}
        drop = {c.index for c in cues for a, b in songs if pos[a] <= pos[c.index] <= pos[b]}
        report["song_run_cues_removed"] = len(drop)
        step2 = [c for c in cues if c.index not in drop]
        report["cues_dropped_at_lyrics"] = len(drop)
    else:
        for c in cues:
            kept = tuple(ln for ln in c.lines if not is_lyric_line(ln))
            report["lyric_lines_removed"] += len(c.lines) - len(kept)
            if kept:
                step2.append(dataclasses.replace(c, lines=kept))
            elif c.lines:
                report["cues_dropped_at_lyrics"] += 1
    kept_cues: list[Cue] = []
    for c in step2:
        lines = strip_tags(strip_sound(c.text)).split("\n")
        out = tuple(" ".join(ln.split()) for ln in lines if not EMPTY.match(ln))
        report["lines_dropped_at_sound_and_tags"] += len(c.lines) - len(out)
        if out:
            kept_cues.append(dataclasses.replace(c, lines=out))
        else:
            report["cues_dropped_at_sound_and_tags"] += 1
    report["cues_without_text_in_file"] = sum(1 for c in cues if not c.lines)
    report["kept_cues"] = len(kept_cues)
    report["kept_lines"] = sum(len(c.lines) for c in kept_cues)
    return kept_cues, report


def build_scenes(cues: Sequence[Cue], gap: float = C.SCENE_GAP_S) -> list[Scene]:
    """Maximal runs of kept cues with no gap over `gap` seconds between the latest end so far and the next start
    (design §2.2.5), compared in integer milliseconds. Cues are taken in time order; overlapping cues never open a
    scene."""
    gap_ms = round(gap * 1000)
    ordered = sorted(cues, key=lambda c: (c.start_ms, c.index))
    scenes: list[list[Cue]] = []
    last_end = None
    for c in ordered:
        if last_end is None or c.start_ms - last_end > gap_ms:
            scenes.append([c])
            last_end = c.end_ms
        else:
            scenes[-1].append(c)
            last_end = max(last_end, c.end_ms)
    return [Scene(k + 1, tuple(s)) for k, s in enumerate(scenes)]


def dialogue_hours(scenes: Sequence[Scene]) -> float:
    return sum(s.duration_ms for s in scenes) / 3_600_000


def runtime_hours(raw_cues: Sequence[Cue]) -> float:
    return max((c.end_ms for c in raw_cues), default=0) / 3_600_000


def scene_of(scenes: Sequence[Scene]) -> dict[int, int]:
    return {c.index: s.number for s in scenes for c in s.cues}
