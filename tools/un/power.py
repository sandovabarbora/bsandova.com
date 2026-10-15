"""Power of the UN votes study (design §5), on the EU members other than Czechia only: Czechia is dropped in the query
that reads the file, so no Czech position is read. For pseudo changes sized like Q1 (the votes of one October–December
after four years) and like Q2 (four years after four, with the buffer), β of every other EU-27 member as focal, by the
code of the study (votes.py): interval widths, the spread of β and of |β|/se across members, and the votes that split
the EU in each after set.

    nice -n 20 uv run --no-project --with duckdb --with pandas --with numpy python tools/un/power.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from votes import DRAWS, EU27, MIN_AFTER, ROOT, agreements, beta, load, positions, windows  # noqa: E402

OUT = ROOT / "docs/research/un-votes-power.json"
# before and after periods: Q1-like (an after period from mid-October, as Q1's from registration) and Q2a's own
PSEUDO = {"q1_like_2022": (("2018-10-16", "2022-10-15"), ("2022-10-16", "2022-12-31")),
          "q1_like_2023": (("2019-10-16", "2023-10-15"), ("2023-10-16", "2023-12-31")),
          "q2_like": (("2014-01-29", "2017-12-12"), ("2018-01-12", "2021-12-16"))}


def main() -> None:
    df = load(drop=("CZE",))
    assert "CZE" not in set(df["ms_code"])
    m, info, dup = positions(df)
    out = {"duplicates": dup, "votes": int(len(m)), "codes": sorted(df["ms_vote"].dropna().unique().tolist()),
           "votes_per_year": {str(y): int(n) for y, n in info["date"].dt.year.value_counts().sort_index().items()},
           "dropped_at_load": ["CZE"], "comparison_note": "Czechia is absent, so each placebo has one comparison "
                                                          "member fewer than the real run", "pseudo": {}}
    members = [c for c in EU27 if c in m.columns]
    eu_vals = m[members].to_numpy()
    split = ((eu_vals >= 0)[:, :, None] & (eu_vals[:, :, None] == np.arange(3))).any(1).sum(1) > 1
    for name, (before_w, after_w) in PSEUDO.items():
        before, after = windows(info["date"], before_w, after_w)
        rows = {}
        for f in members:
            a_f, a_c = agreements(m, f, None)
            if a_f[after].notna().sum() < MIN_AFTER or a_f[before].notna().sum() == 0:
                continue
            r = beta(a_f, a_c, before, after, info["cluster"], draws=DRAWS)
            rows[f] = {"est": round(r["est"], 4), "se": round(r["se"], 4), "width90": round(r["ci90"][1] - r["ci90"][0], 4),
                       "n_after": r["n_after"], "clusters_after": r["clusters_after"]}
        est = np.array([r["est"] for r in rows.values()])
        t = np.array([r["est"] / r["se"] for r in rows.values()])
        w = np.array([r["width90"] for r in rows.values()])
        out["pseudo"][name] = {
            "before": before_w, "after": after_w, "first_vote_after": str((info["date"][after]).min().date()), "members": len(rows),
            "votes_after": int(after.sum()), "split_votes_after": int(split[after.to_numpy()].sum()),
            "clusters_after_median": int(np.median([r["clusters_after"] for r in rows.values()])),
            "width90_median": round(float(np.median(w)), 4), "width90_max": round(float(w.max()), 4),
            "abs_beta_q90": round(float(np.quantile(np.abs(est), 0.9)), 4),
            "abs_t_q90": round(float(np.quantile(np.abs(t), 0.9)), 2), "by_member": rows}
        print(name, {k: v for k, v in out["pseudo"][name].items() if k != "by_member"})
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
