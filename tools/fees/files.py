"""Hashes, the manifest and the gates: the frozen-code check and the check that every snapshot file is the hashed one
(design "Running and verification"; the pattern of tools/memes and tools/pitch, with the data-step and design tags added)."""
from __future__ import annotations

import hashlib
import itertools
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


CHANGE_LOG_MARK = "\n## Change log"


def _rel(path: Path) -> str:
    return str(path.relative_to(C.ROOT))


def check_code_frozen() -> None:
    """Exits with the reason unless: the three tags exist as annotated tags and lie on one chain (design, data step,
    code, HEAD); tools/fees at HEAD equals `fees-code`; the manifest and both maps equal `fees-data-step`; the design text
    above its change log equals `fees-design`; and tools/fees, the design text and the manifest are committed. A branch
    of the same name can never stand in for a tag."""
    for t in C.STAMP_TAGS:
        ref = f"refs/tags/{t}"
        if not git_ok("rev-parse", "--verify", "--quiet", ref):
            raise SystemExit(f"refusing to run: the tag {t} does not exist")
        if git("cat-file", "-t", ref).strip() != "tag":
            raise SystemExit(f"refusing to run: the tag {t} is not an annotated tag")
    chain = [f"refs/tags/{t}" for t in C.STAMP_TAGS] + ["HEAD"]
    for older, newer in itertools.pairwise(chain):
        if not git_ok("merge-base", "--is-ancestor", older, newer):
            raise SystemExit(f"refusing to run: {older.removeprefix('refs/tags/')} is not an ancestor of "
                             f"{newer.removeprefix('refs/tags/')}")
    code = f"refs/tags/{C.CODE_TAG}"
    if not git_ok("diff", "--quiet", code, "HEAD", "--", C.TOOL):
        raise SystemExit(f"refusing to run: {C.TOOL} at HEAD differs from the tag {C.CODE_TAG}")
    frozen = [_rel(C.MANIFEST), _rel(C.VAT_MAP), _rel(C.EXCISE_MAP)]
    if not git_ok("diff", "--quiet", f"refs/tags/{C.DATA_TAG}", "HEAD", "--", *frozen):
        raise SystemExit(f"refusing to run: the manifest or a map differs from the tag {C.DATA_TAG}")
    if git("status", "--porcelain", "--", C.TOOL, _rel(C.DESIGN), _rel(C.MANIFEST)).strip():
        raise SystemExit(f"refusing to run: {C.TOOL}, the design text or the manifest has uncommitted changes")
    registered = git("show", f"refs/tags/{C.DESIGN_TAG}:{_rel(C.DESIGN)}").split(CHANGE_LOG_MARK, 1)
    current = C.DESIGN.read_text(encoding="utf-8").split(CHANGE_LOG_MARK, 1)
    if len(registered) != 2 or len(current) != 2 or registered[0] != current[0]:
        raise SystemExit(f"refusing to run: the design text above its change log differs from the tag {C.DESIGN_TAG}")


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
            "tag_commits": tag_commits(), "head": git("rev-parse", "HEAD").strip(),
            "tools_fees_tree": git("rev-parse", f"HEAD:{C.TOOL}").strip()}
