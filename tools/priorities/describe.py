"""Post-hoc and descriptive, not registered: series drawn after the registered results were read, with the
definitions of the frozen code (estimate.py, imported, nothing in it changed) and no estimation.

1. Per wave and topic, on the whole series 2004–2025: C, the share of mentions in the Czech column, and A, the share of
   plenary words in the 182-day window after the wave, exactly the rows of the registered Q1 panel.
2. Per year and spending topic: C̄, the year's mean concern within one spell, and S, the topic's share of general
   government expenditure, exactly the rows of the registered Q2 panel.
3. Per topic, the lowest and highest of C and A over the waves, and of C̄ and S over the years, for the reading aid of
   how far each series moved.

Writes docs/research/priorities-describe.json.

    nice -n 20 uv run --no-project --with pandas --with pyarrow --with numpy --with scipy python -I tools/priorities/describe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate import ROOT, SPENDING_TOPICS, TOPICS, Study, Variant  # noqa: E402

OUT = ROOT / "docs/research/priorities-describe.json"


def r(x: float) -> float:
    return round(float(x), 6)


def main() -> None:
    st = Study()
    con = st.concern("A")
    wp = st.wave_panel("whole", Variant())
    yp = st.year_panel(None, Variant()).dropna(subset=["s", "s_next"])
    waves = sorted(int(w) for w in wp.time.unique())
    out = {"note": "descriptive, drawn after the registered results; not registered, no label",
           "waves": {str(w): {"start": str(con.dates[w][0]), "end": str(con.dates[w][1])} for w in waves},
           "wave_series": {}, "year_series": {}, "ranges": {}}
    for k in TOPICS:
        g = wp[wp.topic == k].sort_values("time")
        out["wave_series"][k] = [[int(t), r(c), r(a)] for t, c, a in zip(g.time, g.c, g.a_post)]
        out["ranges"][k] = {"c": [r(g.c.min()), r(g.c.max())], "a": [r(g.a_post.min()), r(g.a_post.max())]}
    for k in SPENDING_TOPICS:
        g = yp[yp.topic == k].sort_values("time")
        out["year_series"][k] = [[int(y), r(c), r(s)] for y, c, s in zip(g.time, g.cbar, g.s)]
        out["ranges"][k] |= {"cbar": [r(g.cbar.min()), r(g.cbar.max())], "s": [r(g.s.min()), r(g.s.max())]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
