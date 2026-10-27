"""The assembly of the results from two runs, the films and the author's codes (design §4, §7). Invented data only."""
from __future__ import annotations

import json

import analysis as A
import pytest
import subtitles as S


def film(n=30, gap_every=5):
    # cues 2 s long, 1 s apart, a 10 s gap after every `gap_every` cues: scenes of `gap_every` cues
    cues, t = [], 0.0
    for i in range(1, n + 1):
        cues.append(S.Cue.secs(i, t, t + 2, (f"invented {i}",)))
        t += 3 + (10 if i % gap_every == 0 else 0)
    return A.Film(tuple(cues), tuple(cues), {"kept_cues": n})


def j(first, target="character", butt="speaker", gtype="", kind="joke", last=None, other=""):
    return {"id": f"x-{first}", "scene": 0, "first_cue": first, "last_cue": last or first, "kind": kind,
            "target": target, "group_type": gtype, "group_other": other, "butt": butt}


def out(jokes, failed_scenes=(), failed_jokes=()):
    return {"jokes": jokes, "jokes_found": len(jokes) + len(failed_jokes), "failed_scenes": list(failed_scenes),
            "failed_jokes": list(failed_jokes), "model_versions": ["m"]}


PP1 = [j(1, "america"), j(2, "group", "group", "weight"), j(7, "group", "speaker", "race"),
       j(12, "group", "unclear", "religion", kind="allusion"), j(16, "group", "group", "other", other="Dentists"),
       j(22, "genre", "group", last=24)]
PP2 = [j(3, "america"), j(8, "america", kind="allusion"), j(13, "character"), j(27, "genre")]


def runs():
    return {1: {"pp1": out(PP1), "pp2": out(PP2, failed_jokes=["3-2"])}, 2: {"pp1": out(PP1[:-1]), "pp2": out(PP2)}}


def test_counts_per_film():
    c = A.counts(film(), out(PP1, failed_scenes=[4]))
    assert c["jokes"] == 6 and c["by_kind"] == {"joke": 5, "allusion": 1} and c["america"] == 1
    assert c["by_target"] == {"america": 1, "group": 4, "genre": 1}
    assert c["by_group_type"] == {"weight": 1, "race": 1, "religion": 1, "other": 1}
    assert c["group_other"] == {"dentists": 1} and c["protected"] == 3 and c["would_not_pass_today"] == 1
    assert c["protected_by_butt"] == {"group": 1, "speaker": 1, "unclear": 1}
    assert c["scenes"] == 6 and c["kept_cues"] == 30 and c["failed_scenes"] == 1
    assert c["dialogue_hours"] == pytest.approx(6 * 14 / 3600)


def test_the_study_reports_readings_checks_agreement_and_no_text():
    films = {"pp1": film(), "pp2": film()}
    human = [{"film": "pp1", "cue": 1, "joke": True, "target": "america", "group_type": "", "group_other": "",
              "butt": "speaker"}, {"film": "pp1", "cue": 3, "joke": False}, {"film": "pp2", "cue": 13, "joke": "skip"},
             {"film": "pp2", "cue": 27, "joke": True, "target": "genre", "group_type": "", "group_other": "",
              "butt": "speaker"}]
    res = A.study(films, runs(), human, reps=200)
    assert res["readings"]["Q2"]["pp2"] == {"label": "no protected-trait joke found", "sentence": None}
    assert res["readings"]["Q2_difference"]["reading"] is None
    assert res["validation"]["skipped"] == 1 and res["validation"]["detection"]["percent_agreement"] == 100
    assert res["counts"]["pp2"]["failed_jokes"] == 1
    assert res["self_agreement"]["pp2"]["detection"]["kappa"] == pytest.approx(1.0)
    assert res["self_agreement"]["pp1"]["detection"]["percent_agreement"] < 100
    assert res["checks"]["run_2"]["delta1"]["estimate"] == pytest.approx(2 / 4 - 1 / 5)
    assert res["estimates"]["delta1"]["estimate"] == pytest.approx(2 / 4 - 1 / 6)
    assert set(res["checks"]["full_runtime"]) == {"delta3", "rate_wnpt_pp1", "rate_wnpt_pp2"}
    assert "invented" not in json.dumps(res)


def test_the_scene_gap_checks_rebuild_scenes_and_move_jokes_with_them():
    films = {"pp1": film(), "pp2": film()}
    t8 = A.tables(films, runs()[1])                                # gaps between scenes are 11 s
    assert t8["pp1"].shape[0] == A.tables(films, runs()[1], gap=5.0)["pp1"].shape[0] == 6
    t12 = A.tables(films, runs()[1], gap=12.0)                     # nothing splits at 12 s: one scene
    assert t12["pp1"].shape[0] == 1 and t12["pp1"][0, 0] == 6
    assert t12["pp1"][0, -1] == pytest.approx(t8["pp1"][:, -1].sum() + 5 * 11 / 3600)


def test_a_film_without_jokes_still_bootstraps_and_reads_indeterminate_where_shares_lack_a_denominator():
    films = {"pp1": film(), "pp2": film()}
    rr = {1: {"pp1": out(PP1), "pp2": out([])}, 2: {"pp1": out(PP1), "pp2": out([])}}
    res = A.study(films, rr, None, reps=100)
    assert res["readings"]["Q1"]["label"] == "indeterminate" and res["validation"] is None and res["status"] is None
    assert res["estimates"]["share_america_pp2"]["estimate"] is None


def test_a_failed_pass_1_scene_leaves_the_table_the_hours_and_the_agreement():
    films = {"pp1": film(), "pp2": film()}
    failed = dict(out(PP1), failed_scenes=[2], failed_scene_cues=[6, 7, 8, 9, 10])
    failed["jokes"] = [x for x in PP1 if not 6 <= x["first_cue"] <= 10]
    rr = {1: {"pp1": failed, "pp2": out(PP2)}, 2: {"pp1": out(PP1), "pp2": out(PP2)}}
    t = A.tables(films, rr[1])
    assert t["pp1"].shape[0] == 5 and t["pp1"][:, -1].sum() == pytest.approx(5 * 14 / 3600)
    c = A.counts(films["pp1"], failed)
    assert c["scenes"] == 5 and c["kept_cues_in_failed_scenes"] == 5 and c["failed_scenes"] == 1
    assert c["dialogue_hours"] == pytest.approx(5 * 14 / 3600)
    agree = A.self_agreement(films, rr[1], rr[2])["pp1"]["detection"]
    assert agree["cues"] == 25 and agree["cues_without_model_output"] == 5


def test_detection_counts_jokes_whose_pass_2_failed():
    films = {"pp1": film(), "pp2": film()}
    r1 = dict(out(PP1[1:]), detected_spans=[{k: x[k] for k in ("first_cue", "last_cue", "kind")} for x in PP1])
    m = A.cue_map(films, {"pp1": r1, "pp2": out(PP2)})
    assert m[("pp1", 1)] == {"joke": True, "target": None, "butt": None}
    assert A.counts(films["pp1"], r1)["jokes"] == 5
