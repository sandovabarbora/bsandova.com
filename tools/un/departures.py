"""Post-hoc and descriptive, not registered: the stage A votes on which Czechia's position differed from the EU
majority (design §1, Q4), grouped by topic. The topics were defined after the results had been read, from the agenda
item and title of each listed vote, by the first rule below that matches. Reads only
docs/research/un-votes-results-a.json; no vote file is opened. Writes docs/research/un-votes-departures.json.

    python3 tools/un/departures.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs/research/un-votes-results-a.json"
OUT = ROOT / "docs/research/un-votes-departures.json"

# order matters: "the risk of nuclear proliferation in the Middle East" is counted under nuclear weapons, not under
# Israel and Palestine, because its agenda item is a disarmament item
TOPICS = (
    ("nuclear", "nuclear weapons and disarmament", r"nuclear|uranium|disarmament"),
    ("israel_palestine", "Israel and Palestine", r"palestin|israel|jerusalem|golan|relief and works agency"),
    ("racism", "racism (Durban follow-up)", r"durban|racism"),
)
OTHER = ("other", "other")
PERIODS = (("sobotka", "Sobotka", "q2a", "departures_before"), ("babis", "Babiš", "q2a", "departures_after"),
           ("fiala", "Fiala", "q2b", "departures_after"))


def topic(vote: dict) -> str:
    text = f"{vote['agenda'] or ''} {vote['title'] or ''}".lower()
    return next((key for key, _, rx in TOPICS if re.search(rx, text)), OTHER[0])


def main() -> None:
    res = json.loads(SRC.read_text(encoding="utf-8"))
    keys = [k for k, _, _ in TOPICS] + [OTHER[0]]
    out = {"note": "post-hoc, descriptive: topics defined after the stage A results were read",
           "topics": {k: lab for k, lab, _ in TOPICS} | {OTHER[0]: OTHER[1]}, "rules": {k: rx for k, _, rx in TOPICS},
           "periods": {}}
    for key, label, q, side in PERIODS:
        d = res["questions"][q][side]
        rows = [{**v, "topic": topic(v)} for v in d["list"]]
        assert len(rows) == d["departures"]
        out["periods"][key] = {
            "label": label, "votes": d["votes"], "departures": d["departures"],
            "by_topic": {k: sum(r["topic"] == k for r in rows) for k in keys},
            "opposite_by_topic": {k: sum(r["topic"] == k and r["agreement"] == 0 for r in rows) for k in keys},
            "list": sorted(rows, key=lambda r: r["date"]),
        }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for k, p in out["periods"].items():
        print(k, p["votes"], p["departures"], p["by_topic"], p["opposite_by_topic"])


if __name__ == "__main__":
    main()
