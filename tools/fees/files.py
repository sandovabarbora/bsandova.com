"""Hashes, the manifest and the gates: the frozen-code check and the check that every snapshot file is the hashed one
(design "Running and verification"; pattern of tools/pitch and tools/gnss)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import config as C


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(path: Path | None = None) -> dict[str, str]:
    """Resolved path -> sha256. Fields are separated by two spaces; the path is relative to tools/data/fees."""
    path = path or C.MANIFEST
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split("  ")[:2]
        out[str((C.DATA / rel).resolve())] = digest
    return out


def verify_files(manifest: dict[str, str] | None = None, data: Path | None = None) -> list[str]:
    """Problems found: a hashed file missing or changed, a file under the data folder that no line hashes."""
    manifest = read_manifest() if manifest is None else manifest
    data = data or C.DATA
    problems = []
    for p, digest in manifest.items():
        f = Path(p)
        if not f.is_file():
            problems.append(f"missing: {f.relative_to(C.ROOT) if f.is_relative_to(C.ROOT) else f}")
        elif sha256(f) != digest:
            problems.append(f"changed: {f.relative_to(C.ROOT) if f.is_relative_to(C.ROOT) else f}")
    known = set(manifest)
    for f in sorted(data.rglob("*")):
        if f.is_file() and str(f.resolve()) not in known:
            problems.append(f"not in the manifest: {f.relative_to(data)}")
    return problems


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(C.ROOT), *args], capture_output=True, text=True, check=True).stdout


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", "-C", str(C.ROOT), *args], capture_output=True, check=False).returncode == 0


def code_ref() -> str:
    return f"refs/tags/{C.CODE_TAG}"                 # a branch of the same name can never stand in for the tag


def check_code_frozen() -> None:
    """The code tag exists, is an ancestor of HEAD, tools/fees at HEAD equals it, and neither tools/fees nor the design
    text has uncommitted changes. Returns None or exits with the reason."""
    ref = code_ref()
    if not git_ok("rev-parse", "--verify", "--quiet", ref):
        raise SystemExit(f"refusing to run: the code is not frozen, the tag {C.CODE_TAG} does not exist")
    if not git_ok("merge-base", "--is-ancestor", ref, "HEAD"):
        raise SystemExit(f"refusing to run: the tag {C.CODE_TAG} is not an ancestor of HEAD")
    if not git_ok("diff", "--quiet", ref, "HEAD", "--", C.TOOL):
        raise SystemExit(f"refusing to run: {C.TOOL} at HEAD differs from the tag {C.CODE_TAG}")
    rel = str(C.DESIGN.relative_to(C.ROOT))
    if git("status", "--porcelain", "--", C.TOOL, rel).strip():
        raise SystemExit(f"refusing to run: {C.TOOL} or the design text has uncommitted changes")


def gate() -> None:
    check_code_frozen()
    problems = verify_files()
    if problems:
        raise SystemExit("refusing to run: the snapshot does not match docs/research/fees-files.sha256: "
                         + "; ".join(problems[:5]) + (f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""))


def tag_commits() -> dict[str, str | None]:
    out = {}
    for t in C.STAMP_TAGS:
        try:
            out[t] = git("rev-parse", f"refs/tags/{t}^{{commit}}").strip()
        except subprocess.CalledProcessError:
            out[t] = None
    return out


def _short(p: str) -> str:
    f, data = Path(p), C.DATA.resolve()
    return str(f.relative_to(data)) if f.is_relative_to(data) else f"tools/fees/{f.name}"


def stamp() -> dict:
    """What a results file is tied to: the manifest and every hashed file (through it), the two maps, the three tags."""
    return {"manifest_sha256": sha256(C.MANIFEST), "files_sha256": {_short(p): d for p, d in read_manifest().items()},
            "maps_sha256": {C.VAT_MAP.name: sha256(C.VAT_MAP), C.EXCISE_MAP.name: sha256(C.EXCISE_MAP)},
            "tag_commits": tag_commits()}
