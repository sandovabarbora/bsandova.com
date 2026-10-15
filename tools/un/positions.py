"""Post-hoc and descriptive, not registered: positions on the votes of the Israel and Palestine topic (the topic rule of
departures.py, defined after the stage A results were read), per stage A period. For each period: the number of such
votes, Czechia's yes / abstain / no / not voting counts, and the shares of yes, abstain and no among the positions of
the other 26 EU members. Also the votes of the emergency special sessions, overall and among Czechia's departures from
the EU majority. Czech positions are read only up to 14 December 2025, through load(end=...). Writes
docs/research/un-votes-positions.json.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with numpy python tools/un/positions.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from departures import topic  # noqa: E402
from describe import PERIODS, majority  # noqa: E402
from votes import EU27, POS, ROOT, load, positions  # noqa: E402

END = "2025-12-14"
OUT = ROOT / "docs/research/un-votes-positions.json"
CODE = {v: k for k, v in POS.items()} | {-1: "X"}


def main() -> None:
    m, info, _ = positions(load(end=END))
    ip = info.apply(lambda r: topic({"agenda": r["agenda"], "title": r["title"]}) == "israel_palestine", axis=1)
    emergency = ~info["session"].astype(str).str.fullmatch(r"\d+")
    others = [c for c in EU27 if c in m.columns and c != "CZE"]
    maj = majority(m, "CZE")
    out = {"note": "post-hoc, descriptive: Israel and Palestine topic by the rule of departures.py; Czech positions to " + END,
           "periods": {}}
    for key, (a, b) in PERIODS.items():
        inside = (info["date"] >= a) & (info["date"] <= b)
        sel = inside & ip
        cz = m.loc[sel, "CZE"].map(CODE).value_counts().to_dict()
        vals = m.loc[sel, others].to_numpy().ravel()
        voted = vals[vals >= 0]
        shares = {CODE[k]: round(float((voted == k).mean()), 4) for k in range(3)}
        # the majority of the other 26 on these votes
        mj = {CODE[k]: int((maj[sel.to_numpy()] == k).sum()) for k in (-1, 0, 1, 2)}
        czv = m["CZE"].to_numpy()
        off = inside.to_numpy() & (czv >= 0) & (maj >= 0) & (czv != maj)
        out["periods"][key] = {
            "votes": int(inside.sum()), "ip_votes": int(sel.sum()),
            "ip_czechia": {k: int(cz.get(k, 0)) for k in ("Y", "A", "N", "X")},
            "ip_others_shares": shares, "ip_majority": mj,
            "emergency_votes": int((inside & emergency).sum()),
            "departures": int(off.sum()), "departures_emergency": int((off & emergency.to_numpy()).sum()),
            "emergency_by_session": {str(k): int(v) for k, v in info.loc[inside & emergency, "session"].value_counts().items()},
            "departures_by_session": {str(k): int(v) for k, v in
                                      info.loc[off & emergency.to_numpy(), "session"].value_counts().items()},
        }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
