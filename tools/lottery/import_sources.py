"""One-off import of the raw lottery files into assets/lottery/ (already done; the outputs are committed).

    python3 tools/lottery/import_sources.py <lottery-analysis dir> <monthly results dir>

- <lottery-analysis>/data/sportka.csv: the Sportka history exported from Sazka (Allwyn), 3 775 drawing days from
  9 January 1994 to 5 July 2026, copied unchanged to assets/lottery/sportka.csv.
- <lottery-analysis>/data/eurojackpot_clean.csv: 952 Eurojackpot draws, 23 March 2012 to 5 May 2026, copied to
  assets/lottery/eurojackpot.csv (draws to 25 February 2025 from a public GitHub CSV, draws from 28 February 2025 with
  jackpot and win flag transcribed from lotto.net result pages).
- <monthly>/sportka_*.txt: monthly result lists May 2025 to August 2026 transcribed from sportkasazka.cz, written as
  assets/lottery/sportka_check_2025_2026.csv (date, draw, six numbers, bonus) and used only as a cross-check.
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
from datetime import date
from pathlib import Path

A = Path(__file__).resolve().parents[2] / "assets" / "lottery"


def monthly(src: Path) -> list[list]:
    rows = []
    for f in sorted(src.glob("sportka_*.txt")):
        for blk in re.split(r"^### ", f.read_text(encoding="utf-8"), flags=re.M)[1:]:
            d, m, y = re.match(r"\[(\d+)\.(\d+)\.(\d+)", blk).groups()
            nums = [int(x) for x in re.findall(r"^\s*(\d+)\s*$", blk.split("ŠANCE")[0], flags=re.M)]
            assert len(nums) == 14, (f, d, m, y, nums)
            day = date(int(y), int(m), int(d)).isoformat()
            rows.append([day, 1, *nums[:7]])
            rows.append([day, 2, *nums[7:14]])
    return sorted(rows)


def main() -> None:
    lot, mon = Path(sys.argv[1]), Path(sys.argv[2])
    A.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(lot / "data" / "sportka.csv", A / "sportka.csv")
    shutil.copyfile(lot / "data" / "eurojackpot_clean.csv", A / "eurojackpot.csv")
    with open(A / "sportka_check_2025_2026.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "draw", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"])
        w.writerows(monthly(mon))
    print("imported into", A)


if __name__ == "__main__":
    main()
