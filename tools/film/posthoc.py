"""Post-hoc completion of two registered steps of the film-fund study, added 13 October 2026 after publication.

- Q2 on first applications only, as §2 of the design keeps them; the published Q2 counted every application.
- The §6 bound on linking errors for Q1 O1. Read literally ("unmatched projects in both groups counted as released")
  it makes release 1 for every application, so there is nothing to estimate. Instead, at the main bandwidth, each
  unmatched application counts as released with the probability the blind recall audit found for its group
  (docs/research/film-fund-recall-audit.csv: 3 of 30 funded, 2 of 30 unfunded plus 1 unsure), taken at the ends of
  the 95 % Clopper-Pearson intervals that favour and disfavour an effect; the local linear estimator is linear in
  the outcome, so this equals the mean over random imputations. The worst case (every unmatched funded application
  released and no unfunded one, and the reverse) is reported alongside.

Writes docs/research/film-fund-posthoc.json.

    nice -n 20 uv run --no-project --with pandas --with pyarrow --with numpy --with scipy --with rdrobust \
        --with rddensity --with rapidfuzz python tools/film/posthoc.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse import load, q2, rd  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs" / "research" / "film-fund-posthoc.json"
AUDIT_N = 30


def clopper_pearson(k: int, n: int) -> tuple[float, float]:
    lo = float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0
    return lo, float(beta.ppf(0.975, k + 1, n - k))


def main() -> None:
    d = load()
    prim = d[(d.year <= 2021) & d["first"]]
    h = rd(prim, "linked")["h"]

    def imputed(p_funded: float, p_unfunded: float) -> dict:
        p = np.where(prim.funded, p_funded, p_unfunded)
        return rd(prim.assign(y=prim.linked.astype(float) + (~prim.linked).astype(float) * p), "y", h=h)

    funded, unfunded_lo, unfunded_hi = clopper_pearson(3, AUDIT_N), clopper_pearson(2, AUDIT_N), clopper_pearson(3, AUDIT_N)
    released = prim[prim.linked]
    films = released.src.astype(str) + ":" + released.src_id.astype(str)
    res = {
        "note": "post-hoc, added 13 October 2026 after publication; completes registered steps, see the module docstring",
        "Q2_first_applications": q2(d[(d.year <= 2021) & d["first"]]),
        "Q2_first_applications_linked_to_a_film_already_counted": int(films.duplicated().sum()),
        "O1_linking_bounds": {
            "bandwidth": h,
            "audit_recall_95ci": {"funded_3_of_30": funded, "unfunded_2_of_30": unfunded_lo, "unfunded_3_of_30": unfunded_hi},
            # a fixed bandwidth also fixes the bias-correction bandwidth, so the intervals compare with this, not the main one
            "no_imputation_same_settings": rd(prim, "linked", h=h),
            "audit_point": imputed(3 / AUDIT_N, 2.5 / AUDIT_N),
            "favouring_an_effect": imputed(funded[1], unfunded_lo[0]),
            "against_an_effect": imputed(funded[0], unfunded_hi[1]),
            "worst_case_favouring": imputed(1.0, 0.0),
            "worst_case_against": imputed(0.0, 1.0),
        },
    }
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
