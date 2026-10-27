"""Parsing, lyric and sound-cue removal, the italic fallback and scenes (design §2.2), on invented subtitles only."""
from __future__ import annotations

import pytest
import subtitles as S
from conftest import srt


def test_parse_reads_index_times_and_lines():
    cues = S.parse_srt("﻿" + srt((1, 1.5, 3.25, "Hello there.\nGeneral remark."), (2, 4, 5, "Bye.")))
    assert [c.index for c in cues] == [1, 2]
    assert cues[0].start == 1.5 and cues[0].end == 3.25 and cues[0].lines == ("Hello there.", "General remark.")


def test_parse_handles_crlf_dots_in_times_and_a_missing_blank_line():
    text = "1\r\n00:00:01.000 --> 00:00:02.000\r\nOne.\r\n2\r\n00:00:03,000 --> 00:00:04,000 X1:10\r\nTwo.\r\n"
    cues = S.parse_srt(text)
    assert [(c.index, c.lines) for c in cues] == [(1, ("One.",)), (2, ("Two.",))]


def test_empty_file_has_no_cues():
    assert S.parse_srt("") == [] and S.parse_srt("\n\n  \n") == []


def test_a_cue_without_a_time_line_stops_with_its_position():
    text = srt((1, 1, 2, "Fine.")) + "\n2\nnot a time\nText.\n"
    with pytest.raises(S.MalformedSrt, match="line 6: cue 2 has no valid time line"):
        S.parse_srt(text)


def test_a_time_line_without_index_duplicate_index_and_reversed_times_stop():
    with pytest.raises(S.MalformedSrt, match="expected a cue index"):
        S.parse_srt(srt((1, 1, 2, "A.")) + "\n00:00:03,000 --> 00:00:04,000\nB.\n")
    with pytest.raises(S.MalformedSrt, match="appears twice"):
        S.parse_srt(srt((1, 1, 2, "A."), (1, 3, 4, "B.")))
    with pytest.raises(S.MalformedSrt, match="ends before"):
        S.parse_srt(srt((1, 5, 2, "A.")))


def test_a_blank_line_inside_a_cue_keeps_its_text():
    text = "1\n00:00:01,000 --> 00:00:02,000\nFirst.\n\nStill first.\n\n2\n00:00:03,000 --> 00:00:04,000\nSecond.\n"
    cues = S.parse_srt(text)
    assert cues[0].lines == ("First.", "Still first.") and cues[1].lines == ("Second.",)


@pytest.mark.parametrize("line,lyric", [
    ("♪ Sing about the toaster ♪", True), ("♫ la la", True), ("# Hum the kettle #", True),
    ("<i># Hum the kettle</i>", True), ("Number one #", True), ("It costs # 5 a ticket", False),
    ("Plain words.", False), ("<i>Off-screen voice.</i>", False)])
def test_lyric_line_rule(line, lyric):
    assert S.is_lyric_line(line) is lyric


def test_lyric_lines_go_and_spoken_lines_of_the_same_cue_stay():
    cues = S.parse_srt(srt((1, 0, 2, "♪ The oven is on fire ♪\nCOMMENTATOR: What a riff."),
                           (2, 2, 4, "♪ Only singing here ♪"), (3, 5, 6, "Talking again.")))
    kept, rep = S.clean(cues)
    assert [(c.index, c.lines) for c in kept] == [(1, ("COMMENTATOR: What a riff.",)), (3, ("Talking again.",))]
    assert rep["lyric_lines_removed"] == 2 and rep["cues_dropped_at_lyrics"] == 1 and not rep["lyric_fallback"]


def test_all_lyrics_leaves_nothing():
    cues = S.parse_srt(srt((1, 0, 2, "♪ one ♪"), (2, 3, 4, "# two #")))
    kept, rep = S.clean(cues)
    assert kept == [] and rep["kept_cues"] == 0 and rep["cues_dropped_at_lyrics"] == 2
    assert S.build_scenes(kept) == [] and S.dialogue_hours([]) == 0


def test_sound_cues_and_tags_are_stripped_speaker_labels_kept_and_empty_cues_dropped():
    cues = S.parse_srt(srt((1, 0, 2, "[door slams]\nBOB: <i>Who left</i> the (sighs) fridge open?"),
                           (2, 3, 4, "<i>(cheering)</i>"), (3, 5, 6, "- [laughs]\n- No."),
                           (4, 7, 8, "[man\nshouting]"), (5, 9, 10, "<font color=\"#ff0\">{\\an8}Up here.</font>")))
    kept, rep = S.clean(cues)
    assert [(c.index, c.lines) for c in kept] == [
        (1, ("BOB: Who left the fridge open?",)), (3, ("- No.",)), (5, ("Up here.",))]
    assert rep["cues_dropped_at_sound_and_tags"] == 2 and rep["kept_cues"] == 3


def test_tags_come_off_after_the_lyric_rule_so_a_tagged_marker_still_counts():
    cues = S.parse_srt(srt((1, 0, 2, "<i>♪ la ♪</i>"), (2, 3, 4, "<b>Words</b>")))
    kept, _ = S.clean(cues)
    assert [c.lines for c in kept] == [("Words",)]


# ---------------------------------------------------------------- the italic fallback

def italic_file():
    return S.parse_srt(srt(
        (1, 0, 2, "Talking."), (2, 3, 5, "<i>A sung line about soup</i>"), (3, 5, 7, "<i>Another sung line</i>"),
        (4, 7, 9, "<i>And one more</i>\n<i>with two lines</i>"), (5, 10, 12, "Normal again."),
        (6, 13, 14, "<i>Lonely italic voice</i>"), (11, 15, 16, "Plain."), (7, 20, 21, "<i>Announcer one</i>"), (8, 21, 22, "<i>two</i>"),
        (9, 22, 23, "<i>three</i>"), (10, 23, 24, "<i>half</i> not")))


def test_no_marker_lists_runs_of_three_or_more_wholly_italic_cues():
    cues = italic_file()
    assert not S.has_lyric_markers(cues)
    runs = S.italic_runs(cues)
    assert [(r["first_cue"], r["last_cue"], r["cues"]) for r in runs] == [(2, 4, 3), (7, 9, 3)]
    assert runs[0]["start"] == 3 and runs[0]["end"] == 9 and "text" not in runs[0]


def test_the_fallback_needs_marks_that_cover_exactly_the_listed_runs():
    cues = italic_file()
    with pytest.raises(S.NeedsSongMarks, match="2 italic runs"):
        S.clean(cues)
    with pytest.raises(S.NeedsSongMarks, match="cover exactly"):
        S.clean(cues, {(2, 4): "song"})
    with pytest.raises(S.NeedsSongMarks, match="'song' or 'not song'"):
        S.clean(cues, {(2, 4): "song", (7, 9): "maybe"})


def test_runs_marked_song_go_whole_and_italic_cues_outside_runs_stay():
    kept, rep = S.clean(italic_file(), {(2, 4): "song", (7, 9): "not song"})
    assert [c.index for c in kept] == [1, 5, 6, 11, 7, 8, 9, 10]
    assert rep["lyric_fallback"] and rep["italic_runs"] == 2 and rep["italic_runs_song"] == 1
    assert rep["song_run_cues_removed"] == 3 and kept[2].lines == ("Lonely italic voice",)


def test_no_marker_and_no_italic_run_needs_no_marks():
    kept, rep = S.clean(S.parse_srt(srt((1, 0, 1, "Plain."), (2, 2, 3, "<i>One italic.</i>"))))
    assert len(kept) == 2 and rep["lyric_fallback"] and rep["italic_runs"] == 0


def test_a_file_with_markers_never_uses_the_fallback():
    cues = S.parse_srt(srt((1, 0, 1, "# hum #"), (2, 2, 3, "<i>a</i>"), (3, 3, 4, "<i>b</i>"), (4, 4, 5, "<i>c</i>")))
    kept, rep = S.clean(cues)
    assert not rep["lyric_fallback"] and [c.index for c in kept] == [2, 3, 4]


# ---------------------------------------------------------------- scenes

def cues_at(*spans):
    return [S.Cue.secs(k + 1, a, b, ("x",)) for k, (a, b) in enumerate(spans)]


def test_a_gap_of_exactly_eight_seconds_stays_in_the_scene_and_more_opens_a_new_one():
    scenes = S.build_scenes(cues_at((0, 2), (10, 12), (20.5, 21.5)))
    assert [s.cue_ids for s in scenes] == [(1, 2), (3,)]
    assert scenes[0].duration == 12 and scenes[1].duration == 1
    assert S.dialogue_hours(scenes) == pytest.approx(13 / 3600)


def test_overlapping_cues_stay_together_and_the_scene_ends_at_the_latest_end():
    scenes = S.build_scenes(cues_at((0, 30), (5, 6), (35, 36), (50, 51)))
    assert [s.cue_ids for s in scenes] == [(1, 2, 3), (4,)]
    assert scenes[0].end == 36 and scenes[0].duration == 36


def test_scenes_are_built_in_time_order_and_numbered():
    cues = [S.Cue.secs(1, 100, 101, ("a",)), S.Cue.secs(2, 0, 1, ("b",)), S.Cue.secs(3, 2, 3, ("c",))]
    scenes = S.build_scenes(cues)
    assert [(s.number, s.cue_ids) for s in scenes] == [(1, (2, 3)), (2, (1,))]
    assert S.scene_of(scenes) == {2: 1, 3: 1, 1: 2}


def test_scenes_come_after_cleaning_so_a_song_breaks_a_scene():
    cues = S.parse_srt(srt((1, 0, 2, "Before."), (2, 2, 30, "♪ long song ♪"), (3, 30, 32, "After.")))
    kept, _ = S.clean(cues)
    scenes = S.build_scenes(kept)
    assert [s.cue_ids for s in scenes] == [(1,), (3,)]
    assert S.dialogue_hours(scenes) == pytest.approx(4 / 3600) and S.runtime_hours(cues) == pytest.approx(32 / 3600)


def test_the_gap_is_a_parameter_for_the_sensitivity_checks():
    cues = cues_at((0, 1), (7, 8), (19, 20))
    assert len(S.build_scenes(cues, 5.0)) == 3 and len(S.build_scenes(cues, 12.0)) == 1


def test_times_are_integer_milliseconds_so_eight_seconds_is_exact():
    text = ("1\n00:00:00,500 --> 00:00:01,100\nA.\n\n2\n00:00:09,100 --> 00:00:09,700\nB.\n\n"
            "3\n00:00:17,701 --> 00:00:18,000\nC.\n")
    cues = S.parse_srt(text)
    assert [(c.start_ms, c.end_ms) for c in cues] == [(500, 1100), (9100, 9700), (17701, 18000)]
    assert [s.cue_ids for s in S.build_scenes(cues)] == [(1, 2), (3,)]          # 8 000 ms joins, 8 001 ms splits
    assert S.build_scenes(cues)[0].duration_ms == 9200
    assert S.dialogue_hours(S.build_scenes(cues)) == 9499 / 3_600_000


@pytest.mark.parametrize("gap_s,gap_ms_between,scenes", [(5.0, 5000, 1), (5.0, 5001, 2), (12.0, 12000, 1),
                                                          (12.0, 12001, 2), (8.0, 8000, 1), (8.0, 8001, 2)])
def test_every_scene_gap_is_compared_in_whole_milliseconds(gap_s, gap_ms_between, scenes):
    a = S.Cue(1, 0, 1_100, ("x",))
    b = S.Cue(2, 1_100 + gap_ms_between, 1_100 + gap_ms_between + 300, ("y",))
    assert len(S.build_scenes([a, b], gap_s)) == scenes


def test_a_short_millisecond_field_reads_as_hundreds():
    cue = S.parse_srt("1\n00:00:01,1 --> 00:00:02,25\nA.\n")[0]
    assert (cue.start_ms, cue.end_ms) == (1100, 2250)
