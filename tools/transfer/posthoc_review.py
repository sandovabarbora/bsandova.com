"""Check added 9 October 2026 after a review of the frozen code; not registered.

estimate.py's label() applies §6 in the rule's literal order, so a 95 % interval wholly below 0 whose 90 % interval
lies within ±1 point reads "not supported"; the bunching study now checks "wholly below 0 → inconclusive" first. This
lists every labelled interval in the results and post-hoc files whose label would differ under that order.

Writes docs/research/transfers-posthoc-review.json.

    python3 tools/transfer/posthoc_review.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs/research"
OUT = R / "transfers-posthoc-review.json"


def below_first(o: dict) -> str:
    """The stored label (estimate.label on unrounded bounds), with "wholly below 0 → inconclusive" checked first."""
    return "inconclusive" if o["ci95"][1] < 0 else o["label"]


def labelled(o, path=""):
    if isinstance(o, dict):
        if "label" in o and o.get("ci95") and o.get("ci90"):
            yield path, o
        for k, v in o.items():
            yield from labelled(v, f"{path}/{k}")


def main() -> None:
    res = {"note": "added 9 October 2026 after a review of the frozen code; not registered"}
    for name in ("transfers-results.json", "transfers-posthoc.json"):
        rows = list(labelled(json.loads((R / name).read_text())))
        diff = {p: {"est": o["est"], "ci95": o["ci95"], "label": o["label"],
                    "below_zero_first": below_first(o)}
                for p, o in rows if below_first(o) != o["label"]}
        res[name] = {"labelled": len(rows), "ci95_wholly_below_0": sum(o["ci95"][1] < 0 for _, o in rows),
                     "label_differs": len(diff), "differs": diff}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
