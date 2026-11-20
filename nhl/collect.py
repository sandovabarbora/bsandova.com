from __future__ import annotations

import argparse
import csv
import gzip
import json
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from nhl.parse import SHOT_FIELDS, parse_game

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SEASON = "20262027"
SEASON_START = date(2026, 9, 28)
PAST = ["20232024", "20242025", "20252026"]
# Standings on a date after a season's last game come back empty, so each is read on its final day.
PAST_STANDINGS = {"20232024": "2024-04-18", "20242025": "2025-04-17", "20252026": "2026-04-16"}
PLAYERS = {"pastrnak": (8477956, "BOS"), "necas": (8480039, "COL")}
GAME_FIELDS = ["gid", "date", "home", "away", "hg", "ag", "h_sf5", "h_gf5", "a_sf5", "a_gf5"]
UA = {"User-Agent": "bsandova.com nhl tracker"}


def get(url: str):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def skaters(season: str) -> list[dict]:
    # The stats API ignores limit=-1 and caps a page at 100 rows.
    rows, start = [], 0
    while True:
        d = get(f"https://api.nhle.com/stats/rest/en/skater/summary?start={start}&limit=100&sort=playerId"
                f"&cayenneExp=seasonId={season}%20and%20gameTypeId=2")
        rows += d["data"]
        start += 100
        time.sleep(0.4)
        if start >= d["total"]:
            return rows


def finished_games(today: date) -> dict[int, str]:
    games, d = {}, SEASON_START
    while d <= today:
        for day in get(f"https://api-web.nhle.com/v1/schedule/{d}")["gameWeek"]:
            for g in day["games"]:
                if g["gameType"] == 2 and g["gameState"] in ("OFF", "FINAL"):
                    games[g["id"]] = day["date"]
        d += timedelta(days=7)
        time.sleep(0.4)
    return games


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with gzip.open(path, "rt", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with gzip.open(path, "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def dump(name: str, obj) -> None:
    (DATA / name).write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))


def history() -> None:
    hist = {"skaters": {}, "standings": {}, "gamelogs": {}}
    for s in PAST:
        hist["skaters"][s] = [[r["playerId"], r["positionCode"], r["goals"], r["shots"]] for r in skaters(s)]
        st = get(f"https://api-web.nhle.com/v1/standings/{PAST_STANDINGS[s]}")["standings"]
        hist["standings"][s] = [[t["goalFor"], t["goalAgainst"], t["points"], t["gamesPlayed"]] for t in st]
        for key, (pid, _) in PLAYERS.items():
            log = get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/{s}/2")["gameLog"]
            hist["gamelogs"].setdefault(key, {})[s] = [[x["gameDate"], x["points"]] for x in log]
    dump("history.json", hist)


def daily(today: date) -> dict:
    games = finished_games(today)
    known = {int(r["gid"]) for r in read_csv(DATA / "games.csv.gz")}
    shots, rows, bad = read_csv(DATA / "shots.csv.gz"), read_csv(DATA / "games.csv.gz"), []
    for gid in sorted(set(games) - known):
        s, g, check = parse_game(get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play"))
        time.sleep(0.35)
        if not check["sides_ok"]:
            bad.append(gid)
            continue
        shots += s
        rows.append(g)
    write_csv(DATA / "shots.csv.gz", SHOT_FIELDS, shots)
    write_csv(DATA / "games.csv.gz", GAME_FIELDS, rows)
    dump("skaters.json", [[r["playerId"], r["skaterFullName"], r["teamAbbrevs"], r["positionCode"], r["gamesPlayed"],
                           r["goals"], r["assists"], r["points"], r["shots"], r["ppPoints"]] for r in skaters(SEASON)])
    dump("standings.json", get("https://api-web.nhle.com/v1/standings/now")["standings"])
    for key, (pid, team) in PLAYERS.items():
        dump(f"{key}.json", {
            "landing": get(f"https://api-web.nhle.com/v1/player/{pid}/landing"),
            "log": get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/{SEASON}/2")["gameLog"],
            "schedule": [g["gameDate"] for g in get(f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{SEASON}")["games"]
                         if g["gameType"] == 2 and g["gameState"] in ("FUT", "PRE")],
        })
    return {"games_total": len(games), "new": len(rows) - len(known), "dropped_bad_sides": bad}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true")
    a = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    if a.history:
        history()
    print(json.dumps(daily(date.today())))
