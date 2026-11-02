"""The blind sample: seeded draw, offline form, the check of the author's codes (design §3.4). Invented cues only."""
from __future__ import annotations

import json
import re

import numpy as np
import pytest
import sample as SA
import subtitles as S


def film(n, start_index=1, step=1):
    return [S.Cue.secs(start_index + k * step, 20.0 * k, 20.0 * k + 2, (f"invented line {k}",)) for k in range(n)]


def test_draws_fifty_per_film_with_seed_2012_pp1_first_then_the_display_order():
    kept = {"pp1": film(120, 1, 2), "pp2": film(80, 5)}
    s = SA.draw(kept)
    rng = np.random.default_rng(2012)
    ids1 = sorted(c.index for c in kept["pp1"])
    ids2 = sorted(c.index for c in kept["pp2"])
    want = [("pp1", ids1[k]) for k in sorted(rng.choice(120, 50, replace=False))]
    want += [("pp2", ids2[k]) for k in sorted(rng.choice(80, 50, replace=False))]
    assert [(i["film"], i["cue"]) for i in s["items"]] == want
    assert s["order"] == list(rng.permutation(100))
    assert s == SA.draw(kept) and s["seed"] == 2012


def test_the_draw_is_without_replacement_and_ignores_input_order():
    kept = {"pp1": film(60), "pp2": film(60)}
    shuffled = {"pp1": kept["pp1"][::-1], "pp2": kept["pp2"]}
    s = SA.draw(kept)
    assert len({(i["film"], i["cue"]) for i in s["items"]}) == 100
    assert SA.draw(shuffled) == s


def test_a_film_with_too_few_kept_cues_stops_the_draw():
    with pytest.raises(ValueError, match="fewer than the 50"):
        SA.draw({"pp1": film(49), "pp2": film(60)})


def test_form_items_show_the_scene_and_the_preceding_scene_in_display_order():
    kept = {"pp1": film(60), "pp2": film(60)}
    scenes = {f: S.build_scenes(c, 8.0) for f, c in kept.items()}   # 18 s gaps: one cue per scene
    s = SA.draw(kept)
    items = SA.form_items(s, scenes)
    first = s["items"][s["order"][0]]
    assert (items[0]["film"], items[0]["cue"]) == (first["film"], first["cue"])
    assert items[0]["scene"][0][0] == first["cue"]
    assert all(len(i["context"]) == (0 if i["cue"] == 1 else 1) for i in items)


def test_the_form_makes_no_external_request_and_escapes_the_text():
    items = [{"film": "pp1", "cue": 3, "context": [], "scene": [[3, "</script><img src=x onerror=alert(1)>"]]}]
    page = SA.render_form(items)
    assert "://" not in page and "Content-Security-Policy" in page and "default-src 'none'" in page
    outside_data = "\n".join(ln for ln in page.splitlines() if not ln.startswith("const ITEMS"))
    assert not re.search(r"\ssrc=|<link", outside_data)
    assert page.count("</script>") == 1 and "<\\/script>" in page


def test_valid_codes_pass_and_are_normalised():
    smp = {"items": [{"film": "pp1", "cue": 1}, {"film": "pp1", "cue": 2}, {"film": "pp2", "cue": 7},
                     {"film": "pp2", "cue": 9}]}
    codes = {"codes": [
        {"film": "pp1", "cue": 1, "joke": True, "target": "group", "group_type": "other", "group_other": " vegans ",
         "butt": "group"},
        {"film": "pp1", "cue": 2, "joke": False},
        {"film": "pp2", "cue": 7, "joke": "skip"},
        {"film": "pp2", "cue": 9, "joke": True, "target": "genre", "group_type": "", "group_other": "", "butt": "speaker"}]}
    out = SA.check_codes(codes, smp)
    assert out[0]["group_other"] == "vegans" and out[2] == {"film": "pp2", "cue": 7, "joke": "skip"}
    json.dumps(out)


@pytest.mark.parametrize("bad,msg", [
    ({"joke": True, "target": "people", "butt": "group"}, "outside the codebook"),
    ({"joke": True, "target": "group", "butt": "group"}, "group type is required"),
    ({"joke": True, "target": "genre", "group_type": "race", "butt": "group"}, "group type is required"),
    ({"joke": True, "target": "group", "group_type": "other", "butt": "speaker"}, "written down"),
    ({"joke": True, "target": "group", "group_type": "race", "group_other": "x", "butt": "speaker"}, "written down"),
    ({"joke": None}, "true, false or 'skip'"),
    ({"joke": False, "target": "genre"}, "has no codes"),
    ({"joke": True, "target": "genre", "butt": "speaker", "text": "a line"}, "unknown fields")])
def test_codes_outside_the_codebook_are_refused(bad, msg):
    with pytest.raises(ValueError, match=msg):
        SA.check_codes({"codes": [{"film": "pp1", "cue": 1, **bad}]}, {"items": [{"film": "pp1", "cue": 1}]})


def test_codes_must_cover_exactly_the_sample_once():
    smp = {"items": [{"film": "pp1", "cue": 1}, {"film": "pp1", "cue": 2}]}
    one = {"film": "pp1", "cue": 1, "joke": False}
    for codes in ([one], [one, one], [one, {"film": "pp1", "cue": 3, "joke": False}]):
        with pytest.raises(ValueError, match="exactly the sampled cues"):
            SA.check_codes({"codes": codes}, smp)
    with pytest.raises(TypeError, match="no list"):
        SA.check_codes({}, smp)


def test_the_forms_escape_covers_quotes_for_attribute_values():
    page = SA.render_form([])
    assert '.replace(/"/g, "&quot;").replace(/\'/g, "&#39;")' in page
