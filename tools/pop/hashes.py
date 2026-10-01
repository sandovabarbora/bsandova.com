"""Pop, measured: SHA-256 of every raw file collected, published as docs/research/pop-measured-files.sha256.

    python3 tools/pop/hashes.py
"""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "pop" / "raw"
lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(RAW)}" for p in sorted(RAW.rglob("*")) if p.is_file()]
(ROOT / "docs" / "research" / "pop-measured-files.sha256").write_text("\n".join(lines) + "\n")
print(len(lines), "files")
