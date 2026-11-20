from __future__ import annotations

UNBLOCKED = {"shot-on-goal", "missed-shot", "goal"}
# A rebound only follows a save in the same sequence: any of these ends the sequence.
RESET = {"faceoff", "stoppage", "goal", "period-start", "period-end"}
SHOT_FIELDS = ["gid", "date", "team", "shooter", "goal", "sog", "x", "y", "type", "st", "reb"]


def secs(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def situation(code: str, shooter_is_home: bool) -> tuple[int, int, int, int]:
    """NHL situationCode digits are away goalie, away skaters, home skaters, home goalie."""
    ag, ask, hsk, hg = (int(c) for c in code)
    if shooter_is_home:
        return hsk, ask, hg, ag
    return ask, hsk, ag, hg


def strength(own_sk: int, opp_sk: int, own_g: int) -> str:
    if own_g == 0:
        return "extra_attacker"
    if own_sk == opp_sk == 5:
        return "5v5"
    if own_sk > opp_sk:
        return "PP"
    if own_sk < opp_sk:
        return "SH"
    return "even_other"


def parse_game(g: dict) -> tuple[list[dict], dict, dict]:
    """Shots for the xG model, the game's non-shootout score, and 5-on-5 shot counts per team."""
    home, away = g["homeTeam"]["id"], g["awayTeam"]["id"]
    abbr = {home: g["homeTeam"]["abbrev"], away: g["awayTeam"]["abbrev"]}
    date = g.get("gameDate", "")
    goals = {abbr[home]: 0, abbr[away]: 0}
    five = {t: {"sf": 0, "gf": 0} for t in goals}
    shots, seen, last_sog = [], set(), None
    for p in g["plays"]:
        if p["eventId"] in seen:
            continue
        seen.add(p["eventId"])
        k = p["typeDescKey"]
        if k in RESET:
            last_sog = None
        if p["periodDescriptor"].get("periodType") == "SO":
            continue
        d = p.get("details", {})
        owner = d.get("eventOwnerTeamId")
        if k == "goal":
            goals[abbr[owner]] += 1
        if k not in UNBLOCKED or len(p.get("situationCode", "")) != 4:
            continue
        is_home = owner == home
        own_sk, opp_sk, own_g, opp_g = situation(p["situationCode"], is_home)
        if own_sk == opp_sk == 5 and own_g == opp_g == 1 and k in ("shot-on-goal", "goal"):
            five[abbr[owner]]["sf"] += 1
            five[abbr[owner]]["gf"] += k == "goal"
        t, per = secs(p["timeInPeriod"]), p["periodDescriptor"]["number"]
        if last_sog is not None and last_sog[0] != owner:
            last_sog = None
        reb = int(last_sog is not None and last_sog[1] == per and 0 <= t - last_sog[2] <= 3)
        last_sog = (owner, per, t) if k == "shot-on-goal" else None
        side = p.get("homeTeamDefendingSide")
        if opp_g == 0 or d.get("xCoord") is None or d.get("yCoord") is None or side not in ("left", "right"):
            continue
        attacks_right = (side == "left") == is_home
        sign = 1 if attacks_right else -1
        shots.append({
            "gid": g["id"], "date": date, "team": abbr[owner],
            "shooter": d.get("scoringPlayerId") if k == "goal" else d.get("shootingPlayerId"),
            "goal": int(k == "goal"), "sog": int(k in ("goal", "shot-on-goal")),
            "x": sign * d["xCoord"], "y": sign * d["yCoord"],
            "type": d.get("shotType") or "unknown", "st": strength(own_sk, opp_sk, own_g), "reb": reb,
        })
    game = {"gid": g["id"], "date": date, "home": abbr[home], "away": abbr[away],
            "hg": goals[abbr[home]], "ag": goals[abbr[away]],
            "h_sf5": five[abbr[home]]["sf"], "h_gf5": five[abbr[home]]["gf"],
            "a_sf5": five[abbr[away]]["sf"], "a_gf5": five[abbr[away]]["gf"]}
    goals_x = [s["x"] for s in shots if s["goal"]]
    ok = not goals_x or sum(x < 0 for x in goals_x) / len(goals_x) <= 0.5
    return shots, game, {"sides_ok": ok}
