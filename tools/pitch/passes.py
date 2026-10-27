"""One run of the two passes over one film (design §2.3, §2.4, §3.6): segment each scene, then code each joke, one
retry per failed attempt, the failure limit of 2 %. The client, cache and log are passed in, so the tests mock them."""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence

import coding as K
import config as C
from client import CallFailed, Reply
from subtitles import Scene

log = logging.getLogger(__name__)


class RunStopped(RuntimeError):
    """More than 2 % of a film's scenes or jokes failed after one retry: no estimate is computed (design §3.6)."""


def _attempts(client, cache, call_log, request: dict, parse: Callable[[str], object], unit: Mapping) -> tuple[object, str]:
    """Up to 1 + RETRIES attempts; returns (parsed, model version) or (None, '') when every attempt failed."""
    for attempt in range(1, C.RETRIES + 2):
        req = {**request, "attempt": attempt}
        reply = cache.get(req)
        cached = reply is not None
        status = "ok"
        try:
            if reply is None:
                reply = client.call(req["system"], req["user"], req["max_tokens"], req["schema"])
                cache.put(req, reply)
            # a reply cut at max_tokens, refused or stopped any other way fails even if its JSON parses
            if reply.stop_reason != "end_turn":
                raise K.BadReply(f"stop reason {reply.stop_reason}")
            parsed = parse(reply.text)
        except (CallFailed, K.BadReply) as err:
            status = f"failed: {err}"
            parsed = None
        tokens = (reply.input_tokens, reply.output_tokens) if isinstance(reply, Reply) else (0, 0)
        call_log.write(**unit, attempt=attempt, status=status, cached=cached, input_tokens=tokens[0],
                       output_tokens=tokens[1])
        if parsed is not None:
            return parsed, reply.model
    return None, ""


def _check_failures(film: str, pass_name: str, failed: int, total: int) -> None:
    if total and failed / total > C.MAX_FAIL_SHARE:
        raise RunStopped(f"{film}, {pass_name}: {failed} of {total} failed after one retry, more than "
                         f"{C.MAX_FAIL_SHARE:.0%}; no estimate is computed")


def run_film(film: str, scenes: Sequence[Scene], prompts: Mapping[str, str], client, cache, call_log,
             run: int) -> dict:
    """Pass 1 over every scene, then pass 2 over every joke found. Returns cue numbers and codes only, no text."""
    base = {"model": C.MODEL, "thinking": C.THINKING, "effort": C.EFFORT, "run": run, "film": film}
    versions: set[str] = set()
    jokes, failed_scenes = [], []
    for k, scene in enumerate(scenes):
        system, user = K.segment_prompt(prompts, scenes[k - 1] if k else None, scene)
        req = {**base, "pass": "segment", "unit": scene.number, "system": system, "user": user,
               "max_tokens": C.MAX_TOKENS["segment"], "schema": K.segment_schema(scene)}
        segs, version = _attempts(client, cache, call_log, req, lambda t, s=scene: K.parse_segments(t, s),
                                  {"film": film, "run": run, "pass": "segment", "unit": scene.number})
        if segs is None:
            failed_scenes.append(scene.number)
            continue
        versions.add(version)
        jokes += K.joke_records(scene, segs)
    _check_failures(film, "pass 1 (scenes)", len(failed_scenes), len(scenes))
    by_number = {s.number: s for s in scenes}
    coded, failed_jokes = [], []
    for joke in jokes:
        system, user = K.code_prompt(prompts, by_number[joke["scene"]], joke)
        req = {**base, "pass": "code", "unit": joke["id"], "system": system, "user": user,
               "max_tokens": C.MAX_TOKENS["code"], "schema": K.CODE_SCHEMA}
        codes, version = _attempts(client, cache, call_log, req, K.parse_codes,
                                   {"film": film, "run": run, "pass": "code", "unit": joke["id"]})
        if codes is None:
            failed_jokes.append(joke["id"])
            continue
        versions.add(version)
        coded.append({**joke, **codes})
    _check_failures(film, "pass 2 (jokes)", len(failed_jokes), len(jokes))
    log.info("%s run %d: %d scenes, %d jokes, %d failed scenes, %d failed jokes", film, run, len(scenes), len(jokes),
             len(failed_scenes), len(failed_jokes))
    return {"film": film, "run": run, "scenes": len(scenes), "jokes": coded, "jokes_found": len(jokes),
            "failed_scenes": failed_scenes, "failed_jokes": failed_jokes, "model_versions": sorted(versions)}
