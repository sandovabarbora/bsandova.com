"""Hub of the series Running late: its parts, every number from the result files.

Reads the results of parts 1–3 in docs/research/; writes texts/running-late.html from tools/late/hub.template.html.

    python3 tools/late/hub.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import part_item, photo_section, render  # noqa: E402

NB = " "


def n(v: float, dp: int = 0) -> str:
    return f"{v:,.{dp}f}".replace(",", NB)


def main() -> None:
    t = json.loads((ROOT / "docs/research/delay-origins-results.json").read_text())["tram"]
    b = json.loads((ROOT / "docs/research/bunching-results.json").read_text())
    bb = json.loads((ROOT / "docs/research/bunching-results-bus.json").read_text())
    tr = json.loads((ROOT / "docs/research/transfers-results.json").read_text())
    ph = json.loads((ROOT / "docs/research/transfers-posthoc.json").read_text())
    specs = [tr["checks"][k]["est"] for k in ("margin_m_fixed_2min", "margin_m_minus_30s", "margin_m_plus_30s",
                                              "timing_a_plus_30s", "timing_a_minus_30s", "observed_departures",
                                              "peaks_only", "without_exclusions", "school_holidays", "term_time")]
    g4 = lambda x: f"{x:+.4f}".replace("-", "−")  # noqa: E731
    v = {"S": n(100 * t["S"]["est"], 1), "S_label": t["S"]["label"], "rho": f"{t['rho']['est']:.3f}",
         "segments": n(t["segments"]), "passes_m": n(t["passes"] / 1e6, 1),
         "pairs": n(b["pairs"]), "g": g4(b["Q1"]["gamma_iv"]), "g_label": b["Q1"]["label"],
         "bg": g4(bb["Q1"]["gamma_iv"]), "bg_label": bb["Q1"]["label"],
         "bunched": n(100 * b["Q4"]["overall"]["bunched"], 2),
         "m3": n(100 * tr["q2_cost"]["3"]["made"]), "c3": n(100 * tr["q2_cost"]["3"]["costly_miss"]),
         "dp": f"{100 * tr['q1_within']['est']:+.2f}".replace("-", "−"), "dp_label": tr["q1_within"]["label"],
         "dp1": f"{100 * tr['q1_within']['est']:+.1f}".replace("-", "−"),
         "spec_lo": f"{100 * min(specs):+.1f}".replace("-", "−"),
         "spec_hi": f"{100 * max(specs):+.1f}".replace("-", "−"),
         "cells_shown": n(ph["roulette"]["cells_shown"])}
    parts = render("\n".join(part_item(*part, label=label) for *part, label in PARTS), v)
    photo = photo_section("running-late", image="delay-origins")
    template = Path(__file__).with_name("hub.template.html").read_text(encoding="utf-8")
    page = render(template, {**v, "parts": parts, "photo": photo})
    (ROOT / "texts" / "running-late.html").write_text(page, encoding="utf-8")
    print(v)


PARTS = [  # slug, part, title, kicker, summary, screen-reader name; {{tokens}} are filled from the results
    ("delay-origins", 1, "Where is delay born on Prague's trams?",
     "Part 1 · where delay appears · {{segments}} tram segments, 15 March – 8 September 2025",
     "A tenth of the segments record {{S}} % of all delay gained, just over half, the same ones in odd and "
     "even weeks. Described afterwards, not registered: many of them leave large stops, and part of what they "
     "record is early trams waiting for their time.",
     None),
    ("bunching", 2, "How often do two 22s come at once? Tram bunching in Prague, 2025",
     "Part 2 · bunching · {{pairs}} pairs of trams, 15 March – 8 September 2025",
     "The spacing between two trams of a line shows practically no amplification from stop to stop ({{g}} per "
     "stop, {{g_label}} by the registered rule, corrected in its version 2), and bunches build gradually "
     "towards the end of a line. The rare sudden closings concentrate on some platforms, as other rare "
     "one-stop events do, and partly by line. City buses show a small positive value ({{bg}}, {{bg_label}}), "
     "about the size of the spread among the tram estimates.",
     "How often do two 22s come at once?"),
    ("transfers", 3, "Will you make your connection?",
     "Part 3 · transfers · tram-to-tram connections, 15 March – 8 September 2025",
     "Planned three minutes apart, a connection was made {{m3}} times in a hundred and cost over five minutes "
     "more {{c3}} % of the time. The data show a small association between the two lines' delays, about "
     "{{dp1}} percentage points ({{dp}} registered, {{dp_label}}; {{spec_lo}} to {{spec_hi}} across "
     "specifications), with real differences between pairs of lines and no mechanism identified. A roulette "
     "gives the share made for {{cells_shown}} combinations of stop, lines and time of day.",
     None),
]


if __name__ == "__main__":
    main()
