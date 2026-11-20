from nhl.parse import parse_game, situation, strength

HOME, AWAY = 6, 21


def play(eid, kind, code="1551", side="left", owner=HOME, x=80, y=5, t="05:00", period=1, ptype="REG", **details):
    d = {"eventOwnerTeamId": owner, "xCoord": x, "yCoord": y, "shotType": "wrist", **details}
    if kind == "goal":
        d["scoringPlayerId"] = 1
    else:
        d["shootingPlayerId"] = 1
    return {"eventId": eid, "typeDescKey": kind, "situationCode": code, "homeTeamDefendingSide": side,
            "timeInPeriod": t, "periodDescriptor": {"number": period, "periodType": ptype}, "details": d}


def game(plays):
    return {"id": 1, "gameDate": "2026-11-01", "homeTeam": {"id": HOME, "abbrev": "BOS"},
            "awayTeam": {"id": AWAY, "abbrev": "COL"}, "plays": plays}


def test_situation_digits_are_away_goalie_away_skaters_home_skaters_home_goalie():
    assert situation("1451", True) == (5, 4, 1, 1)
    assert situation("1451", False) == (4, 5, 1, 1)
    assert situation("0651", True) == (5, 6, 1, 0)


def test_strength_labels():
    assert strength(5, 5, 1) == "5v5"
    assert strength(5, 4, 1) == "PP"
    assert strength(4, 5, 1) == "SH"
    assert strength(3, 3, 1) == "even_other"
    assert strength(6, 5, 0) == "extra_attacker"


def test_attacking_end_follows_defending_side_for_both_teams():
    shots, _, check = parse_game(game([
        play(1, "goal", side="left", owner=HOME, x=80),
        play(2, "goal", side="left", owner=AWAY, x=-80),
        play(3, "goal", side="right", owner=HOME, x=-80, period=2),
    ]))
    assert [s["x"] for s in shots] == [80, 80, 80]
    assert check["sides_ok"]


def test_mirrored_sides_are_flagged():
    _, _, check = parse_game(game([play(1, "goal", side="right", owner=HOME, x=80)]))
    assert not check["sides_ok"]


def test_empty_net_shots_are_dropped_but_the_goal_counts():
    shots, g, _ = parse_game(game([play(1, "goal", code="0651", owner=HOME)]))
    assert shots == []
    assert g["hg"] == 1


def test_shootout_goals_do_not_count():
    _, g, _ = parse_game(game([play(1, "goal", owner=HOME), play(2, "goal", owner=AWAY, ptype="SO", period=5)]))
    assert (g["hg"], g["ag"]) == (1, 0)


def test_rebound_needs_a_save_by_the_same_team_inside_three_seconds_without_a_faceoff():
    shots, _, _ = parse_game(game([
        play(1, "shot-on-goal", t="05:00"),
        play(2, "shot-on-goal", t="05:02"),
        play(3, "shot-on-goal", owner=AWAY, side="left", x=-80, t="05:03"),
        play(4, "shot-on-goal", t="05:04"),
        {"eventId": 5, "typeDescKey": "faceoff", "timeInPeriod": "05:05", "periodDescriptor": {"number": 1, "periodType": "REG"}, "details": {}},
        play(6, "shot-on-goal", t="05:06"),
    ]))
    assert [s["reb"] for s in shots] == [0, 1, 0, 0, 0]


def test_duplicate_events_are_counted_once():
    shots, g, _ = parse_game(game([play(1, "goal"), play(1, "goal")]))
    assert len(shots) == 1 and g["hg"] == 1


def test_five_on_five_counts_include_goals_and_skip_power_plays():
    _, g, _ = parse_game(game([play(1, "shot-on-goal"), play(2, "goal"), play(3, "shot-on-goal", code="1451")]))
    assert (g["h_sf5"], g["h_gf5"]) == (2, 1)
