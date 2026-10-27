"""Prompts from the frozen files and strict parsing of the model's replies (design §2.3, §2.4). Invented text only."""
from __future__ import annotations

import coding as K
import config as C
import pytest
import subtitles as S


def prompts():
    return {name: (C.PROMPTS / name).read_text(encoding="utf-8") for name in K.PROMPT_FILES}


SCENE = S.Scene(4, (S.Cue.secs(10, 0, 1, ("The kettle is judging me.",)), S.Cue.secs(12, 1, 2, ("It whistles in B flat.", "Sharp.")),
                    S.Cue.secs(13, 2, 3, ("Of course it does.",))))
PREV = S.Scene(3, (S.Cue.secs(7, -20, -19, ("We bought a kettle.",)),))


def test_the_prompt_files_exist_name_no_film_and_carry_only_invented_examples():
    p = prompts()
    for text in p.values():
        assert "Pitch" not in text and "Bellas" not in text and "{{" not in text.replace("{{CODEBOOK}}", "").replace(
            "{{CONTEXT}}", "").replace("{{SCENE}}", "").replace("{{FIRST}}", "").replace("{{LAST}}", "")
    assert "Every example below is invented" in p["codebook.md"]
    assert len(K.prompt_hashes(p)) == 5 and all(len(h) == 64 for h in K.prompt_hashes(p).values())


def test_segment_prompt_shows_cue_numbers_and_the_preceding_scene_as_context():
    system, user = K.segment_prompt(prompts(), PREV, SCENE)
    assert "allusion" in system
    assert "[7] We bought a kettle." in user and "[12] It whistles in B flat. / Sharp." in user
    assert "cues 10 to 13" in user and ">>" not in user
    _, first = K.segment_prompt(prompts(), None, SCENE)
    assert "first scene" in first


def test_code_prompt_marks_the_joke_cues_and_carries_the_codebook():
    system, user = K.code_prompt(prompts(), SCENE, {"first_cue": 12, "last_cue": 13})
    assert "Butt: on whom the laugh falls" in system and "{{CODEBOOK}}" not in system
    assert "[10] The kettle" in user and ">> [12]" in user and ">> [13]" in user and ">> [10]" not in user


def J(items: str) -> str:
    return '{"jokes": ' + items + '}'


def test_valid_segments_parse_including_overlaps_and_the_empty_scene():
    text = J('[{"first_cue": 10, "last_cue": 12, "kind": "joke"}, {"first_cue": 12, "last_cue": 13, "kind": "allusion"}]')
    assert [j["kind"] for j in K.parse_segments(text, SCENE)] == ["joke", "allusion"]
    assert K.parse_segments('  {"jokes": []}  ', SCENE) == []
    fenced = "```json\n" + J('[{"first_cue": 13, "last_cue": 13, "kind": "joke"}]') + "\n```"
    assert K.parse_segments(fenced, SCENE)[0]["first_cue"] == 13


@pytest.mark.parametrize("text,msg", [
    ('Here are the jokes: {"jokes": []}', "not JSON"),
    (J('[{"first_cue": 10, "last_cue": 12, "kind": "joke"}]') + " trailing", "not JSON"),
    ('[{"first_cue": 10, "last_cue": 12, "kind": "joke"}]', "is not"),
    ('{"first_cue": 10, "last_cue": 12, "kind": "joke"}', "is not"),
    ('{"jokes": [], "note": "x"}', "is not"),
    ('{"jokes": {}}', "is not"),
    (J('[{"first_cue": 7, "last_cue": 10, "kind": "joke"}]'), "outside the scene"),
    (J('[{"first_cue": 10, "last_cue": 11, "kind": "joke"}]'), "outside the scene"),
    (J('[{"first_cue": 13, "last_cue": 10, "kind": "joke"}]'), "comes after"),
    (J('[{"first_cue": 10, "last_cue": 10, "kind": "pun"}]'), "kind outside"),
    (J('[{"first_cue": 10, "last_cue": 10}]'), "exactly"),
    (J('[{"first_cue": true, "last_cue": 10, "kind": "joke"}]'), "outside the scene"),
    (J('[{"first_cue": "10", "last_cue": 10, "kind": "joke"}]'), "outside the scene"),
    ("```\n{\"jokes\": []}\n``` and more", "not JSON"),
    ("", "not JSON")])
def test_malformed_segment_replies_are_refused(text, msg):
    with pytest.raises(K.BadReply, match=msg):
        K.parse_segments(text, SCENE)


def test_valid_codes_parse():
    assert K.parse_codes('{"target": "group", "group_type": "weight", "group_other": "", "butt": "group"}') == {
        "target": "group", "group_type": "weight", "group_other": "", "butt": "group"}
    assert K.parse_codes('{"target": "america", "group_type": null, "group_other": null, "butt": "unclear"}')[
        "group_type"] == ""
    assert K.parse_codes('{"target": "group", "group_type": "other", "group_other": "dentists", "butt": "speaker"}')[
        "group_other"] == "dentists"


@pytest.mark.parametrize("text,msg", [
    ('{"target": "people", "group_type": "", "group_other": "", "butt": "group"}', "outside the codebook"),
    ('{"target": "genre", "group_type": "", "group_other": "", "butt": "audience"}', "outside the codebook"),
    ('{"target": "group", "group_type": "", "group_other": "", "butt": "group"}', "group type is required"),
    ('{"target": "group", "group_type": "age", "group_other": "", "butt": "group"}', "group type is required"),
    ('{"target": "character", "group_type": "race", "group_other": "", "butt": "group"}', "group type is required"),
    ('{"target": "group", "group_type": "other", "group_other": " ", "butt": "group"}', "written down"),
    ('{"target": "group", "group_type": 3, "group_other": "", "butt": "group"}', "must be text"),
    ('{"target": "genre", "butt": "group"}', "exactly"),
    ('{"target": "genre", "group_type": "", "group_other": "", "butt": "group", "why": "x"}', "exactly"),
    ('["genre"]', "exactly"),
    ("{'target': 'genre'}", "not JSON")])
def test_malformed_or_out_of_codebook_codes_are_refused(text, msg):
    with pytest.raises(K.BadReply, match=msg):
        K.parse_codes(text)


def test_the_schemas_are_enums_of_the_codebook_and_of_the_scenes_cues():
    seg = K.segment_schema(SCENE)
    item = seg["properties"]["jokes"]["items"]
    assert item["properties"]["first_cue"]["enum"] == [10, 12, 13] == item["properties"]["last_cue"]["enum"]
    assert item["properties"]["kind"]["enum"] == ["joke", "allusion"]
    assert seg["additionalProperties"] is False and item["additionalProperties"] is False
    assert seg["required"] == ["jokes"] and item["required"] == ["first_cue", "last_cue", "kind"]
    code = K.CODE_SCHEMA["properties"]
    assert code["target"]["enum"] == list(C.TARGETS) and code["butt"]["enum"] == list(C.BUTTS)
    assert code["group_type"]["enum"] == ["", *C.GROUP_TYPES] and code["group_other"] == {"type": "string"}
    assert K.CODE_SCHEMA["additionalProperties"] is False and len(K.CODE_SCHEMA["required"]) == 4


def test_protected_trait_is_the_seven_group_types_of_decision_d():
    assert set(C.PROTECTED) == {"gender", "race", "weight", "sexuality", "nationality", "religion", "disability"}
    assert K.is_protected({"target": "group", "group_type": "religion"})
    assert not K.is_protected({"target": "group", "group_type": "other"})
    assert not K.is_protected({"target": "america", "group_type": ""})


def test_joke_records_number_jokes_within_their_scene():
    recs = K.joke_records(SCENE, [{"first_cue": 10, "last_cue": 10, "kind": "joke"}])
    assert recs == [{"id": "4-1", "scene": 4, "first_cue": 10, "last_cue": 10, "kind": "joke"}]
