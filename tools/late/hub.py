"""Hub of the series Running late: its parts, every number from the result files.

Reads the results of parts 1–4 in docs/research/; writes texts/running-late.html from tools/late/hub.template.html.

    python3 tools/late/hub.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import part_item, photo_section, render  # noqa: E402

NB = "\u00a0"


def n(v: float, dp: int = 0) -> str:
    return f"{v:,.{dp}f}".replace(",", NB)


def main() -> None:
    t = json.loads((ROOT / "docs/research/delay-origins-results.json").read_text())["tram"]
    b = json.loads((ROOT / "docs/research/bunching-results.json").read_text())
    bb = json.loads((ROOT / "docs/research/bunching-results-bus.json").read_text())
    tr = json.loads((ROOT / "docs/research/transfers-results.json").read_text())
    ph = json.loads((ROOT / "docs/research/transfers-posthoc.json").read_text())
    sw = json.loads((ROOT / "docs/research/swiss-trams-results.json").read_text())
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
         "cells_shown": n(ph["roulette"]["cells_shown"]),
         "zs": n(100 * sw["cities"]["Zurich"]["S"]["est"], 1), "bs": n(100 * sw["cities"]["Basel"]["S"]["est"], 1),
         "ns": n(100 * sw["cities"]["Bern"]["S"]["est"], 1)}
    parts = render("\n".join(part_item(*p[:5], p[6] if len(p) > 6 else None, label=p[5]) for p in PARTS), v)
    photo = photo_section("running-late", image="delay-origins")
    template = Path(__file__).with_name("hub.template.html").read_text(encoding="utf-8")
    page = render(template, {**v, "parts": parts, "photo": photo})
    (ROOT / "texts" / "running-late.html").write_text(page, encoding="utf-8")
    print(v)


PARTS = [  # slug, part, title, kicker, summary, screen-reader name[, photo of another part]; {{tokens}} from the results
    ("delay-origins", 1, "Where do Prague's trams fall behind?",
     "Part 1 · where delay appears · {{segments}} tram segments, 15 March – 8 September 2025",
     "Delay piles up in a few fixed places, though only just past the bar set in advance. A tenth of the "
     "segments record {{S}} % of all delay gained, just over half, and they are the same ones in odd and even "
     "weeks. Many of them leave large stops, and part of "
     "what they record is early trams waiting for their time, both described afterwards and not registered.",
     None),
    ("bunching", 2, "How often do two trams of a line arrive together?",
     "Part 2 · bunching · {{pairs}} pairs of trams, 15 March – 8 September 2025",
     "When two trams of a line are off their planned spacing at one stop, they drift hardly any further off "
     "at the next, a result left {{g_label}} by the registered rule ({{g}} per stop, rule corrected in its "
     "version 2). Bunches "
     "build gradually towards the end of a line. The rare sudden closings concentrate on some platforms, as "
     "other rare one-stop events do, and partly by line. City buses show a small positive value ({{bg}}, "
     "{{bg_label}}), about the size of the spread among the tram estimates.",
     None),
    ("transfers", 3, "Will you make your tram connection?",
     "Part 3 · transfers · tram-to-tram connections, 15 March – 8 September 2025",
     "Planned three minutes apart, a connection was made {{m3}} times in a hundred, and {{c3}} % of the time "
     "it cost over five minutes more. The two lines' delays go together only slightly, about {{dp1}} "
     "percentage points, and the registered test came out {{dp_label}} ({{dp}}, and {{spec_lo}} to "
     "{{spec_hi}} across specifications). The differences between pairs of lines are real, and no mechanism "
     "was identified. A roulette gives the share made for {{cells_shown}} combinations of stop, lines and "
     "time of day.",
     None),
    ("swiss-trams", 4, "Do Swiss trams pile up delay like Prague's?",
     "Part 4 · four networks · Zurich, Basel and Bern, 15 March – 8 September 2025",
     "Swiss trams were measured the same way over the same season. A tenth of the segments make {{zs}} % of "
     "the delay in Zurich, {{bs}} % in Basel and {{ns}} % in Bern. Basel and Bern are like Prague by the "
     "registered rule and Zurich is not. Above what chance alone would give, all three concentrate less than "
     "Prague.",
     None, "delay-origins"),
]


if __name__ == "__main__":
    main()
