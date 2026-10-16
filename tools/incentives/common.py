"""Paths and small helpers shared by the investment incentives study (design docs/research/incentives-design.md).

Raw files live in tools/data/incentives (a gitignored symlink); hashes go to docs/research/.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools/data/incentives"
RAW = DATA / "raw"
MPSV_DIR = DATA / "mpsv"
CODES_DIR = DATA / "codes"
MANIFEST = RAW / "manifest.tsv"
PROJECTS_CSV = RAW / "czechinvest_powerbi_RP_1993-2025.csv"
UA = "bsandova.com research"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
