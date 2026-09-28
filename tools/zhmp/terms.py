"""Prague City Assembly votes across four terms, 2010-2026: measures that need no club or coalition labels.

Coalitions changed within earlier terms, so this compares only what the vote files show directly: how many
present members voted yes, and how the rest recorded dissent ("Hlas proti", "Zdržel se", or pressing nothing,
"Nehlasoval"). Abstaining and not voting have the same legal effect (neither counts towards the 33 needed);
only the record differs.

The files hold substantive votes only, mostly one final vote per resolution. Older terms keep more failed votes
(24 in 2010-2014, 2 in 2022-2026), which carry more "against" votes, so dissent is also reported on passed votes
only.

Usage:
    uv run --with pandas python tools/zhmp/terms.py
"""

import json
from pathlib import Path

import pandas as pd

from votes import RAW, fetch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "zhmp" / "terms.json"
BASE = "https://storage.golemio.cz/ckan/obis/Vysledky_hlasovani_ZHMP_{}.csv"
TERMS = {"2010-2014": ";", "2014-2018": ";", "2018-2022": ",", "2022-2026": ","}  # older files use semicolons
PRESENT = ["Hlas pro", "Hlas proti", "Zdržel se", "Nehlasoval"]
MAJORITY = 33  # of 65 seats


def load(term: str, sep: str) -> pd.DataFrame:
    path = fetch(BASE.format(term.replace("-", "_-_")), RAW / f"votes{term[:4]}.csv")
    d = pd.read_csv(path, sep=sep, encoding="utf-8-sig", low_memory=False)
    d.columns = [c.strip() for c in d.columns]
    return d[d.datumcas.notna()]


def measures(d: pd.DataFrame) -> dict:
    members = list(d.columns[17:])
    n = {v: (d[members] == v).sum(axis=1) for v in PRESENT}
    present = sum(n.values())
    keep = present > 0
    yes = n["Hlas pro"][keep] / present[keep]
    passed = keep & (d.pocetpro >= MAJORITY)

    def per100(v: str, m: pd.Series) -> float:
        return round(100 * float(n[v][m].sum() / present[m].sum()), 2)

    return {
        "votes": int(keep.sum()),
        "failed": int((d.pocetpro[keep] < MAJORITY).sum()),
        "present_mean": round(float(present[keep].mean()), 1),
        "yes_share_mean": round(float(yes.mean()), 3),
        "near_unanimous_share": round(float((yes >= 0.9).mean()), 3),
        "passed": {
            "votes": int(passed.sum()),
            "against_per_100_present": per100("Hlas proti", passed),
            "abstain_per_100_present": per100("Zdržel se", passed),
            "no_vote_per_100_present": per100("Nehlasoval", passed),
            "share_with_any_against": round(float((n["Hlas proti"][passed] > 0).mean()), 3),
        },
    }


def main() -> None:
    out = {t: measures(load(t, sep)) for t, sep in TERMS.items()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    flat = {t: {**{k: v for k, v in m.items() if k != "passed"}, **{f"passed_{k}": v for k, v in m["passed"].items()}}
            for t, m in out.items()}
    print(pd.DataFrame(flat))


if __name__ == "__main__":
    main()
