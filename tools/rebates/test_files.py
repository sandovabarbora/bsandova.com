"""The gate on throwaway git repositories: the three tags, the frozen code, the manifest, the design text, a clean tree,
and the hashes. No network, no real file."""
from __future__ import annotations

import subprocess

import config as C
import files as F
import pytest


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


DESIGN_TEXT = "intro\n\n## 2. Rules\nrule\n\n## Change log\n- first entry\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repository holding the design commit tagged `rebates-design`; `snapshot` and `freeze` add the rest."""
    r = tmp_path / "repo"
    (r / "tools/rebates").mkdir(parents=True)
    (r / "docs/research").mkdir(parents=True)
    (r / "tools/rebates/code.py").write_text("x = 1\n")
    (r / "docs/research/rebates-design.md").write_text(DESIGN_TEXT)
    (r / "docs/research/rebates-files.sha256").write_text("# header\n")
    (r / ".gitignore").write_text("tools/data/rebates/\n")
    git(r.parent, "init", "-q", "-b", "main", str(r))
    for k, v in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false"), ("tag.gpgsign", "false")):
        git(r, "config", k, v)
    git(r, "add", "-A")
    git(r, "commit", "-qm", "design")
    git(r, "tag", "-a", "-m", "design", C.DESIGN_TAG)
    for name, value in (("ROOT", r), ("DATA", r / "tools/data/rebates"), ("DESIGN", r / "docs/research/rebates-design.md"),
                        ("MANIFEST", r / "docs/research/rebates-files.sha256"),
                        ("STRUCTURE", r / "docs/research/rebates-structure.json"),
                        ("RESULTS", r / "docs/research/rebates-results.json")):
        monkeypatch.setattr(C, name, value)
    (r / "tools/data/rebates/2026-11-05").mkdir(parents=True)
    return r


def snapshot(repo):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "data step")
    git(repo, "tag", "-a", "-m", "data", C.DATA_TAG)


def code_tag(repo, annotated=True):
    git(repo, "tag", *(["-a", "-m", "code"] if annotated else []), C.CODE_TAG)


def freeze(repo):
    snapshot(repo)
    git(repo, "commit", "-q", "--allow-empty", "-m", "code")
    code_tag(repo)


def refusal(match):
    return pytest.raises(SystemExit, match=match)


@pytest.mark.parametrize("missing", [C.DESIGN_TAG, C.DATA_TAG, C.CODE_TAG])
def test_each_of_the_three_tags_is_required(repo, missing):
    freeze(repo)
    F.check_code_frozen()
    git(repo, "tag", "-d", missing)
    with refusal(f"the tag {missing} does not exist"):
        F.check_code_frozen()


def test_a_branch_of_the_same_name_is_not_the_tag(repo):
    snapshot(repo)
    git(repo, "branch", C.CODE_TAG)
    with refusal("does not exist"):
        F.check_code_frozen()


def test_tags_must_be_annotated(repo):
    snapshot(repo)
    code_tag(repo, annotated=False)
    with refusal("not an annotated tag"):
        F.check_code_frozen()


def test_the_tags_must_lie_on_one_chain_in_order(repo):
    code_tag(repo)                                                      # the code tag before the data-step tag
    snapshot(repo)
    with refusal("rebates-data-step is not an ancestor of rebates-code"):
        F.check_code_frozen()


def test_code_tag_must_be_an_ancestor_of_head(repo):
    snapshot(repo)
    git(repo, "checkout", "-q", "-b", "other")
    git(repo, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    code_tag(repo)
    git(repo, "checkout", "-q", "main")
    git(repo, "commit", "-q", "--allow-empty", "-m", "main moves on")
    with refusal("not an ancestor"):
        F.check_code_frozen()


def test_tools_at_head_must_equal_the_code_tag(repo):
    freeze(repo)
    (repo / "tools/rebates/code.py").write_text("x = 2\n")
    git(repo, "commit", "-qam", "change the code after the tag")
    with refusal("differs from the tag rebates-code"):
        F.check_code_frozen()


def test_manifest_must_equal_the_data_step_tag(repo):
    snapshot(repo)
    (repo / "docs/research/rebates-files.sha256").write_text("# header\nchanged\n")
    git(repo, "commit", "-qam", "manifest changed after the data step")
    code_tag(repo)
    with refusal("manifest differs from the tag rebates-data-step"):
        F.check_code_frozen()


def test_design_text_above_the_change_log_must_equal_the_design_tag(repo):
    snapshot(repo)
    (repo / "docs/research/rebates-design.md").write_text(DESIGN_TEXT + "- appended entry\n")
    git(repo, "commit", "-qam", "log entry")
    code_tag(repo)
    F.check_code_frozen()                                               # appending to the change log is allowed
    git(repo, "tag", "-d", C.CODE_TAG)
    (repo / "docs/research/rebates-design.md").write_text(DESIGN_TEXT.replace("rule", "other rule") + "- appended entry\n")
    git(repo, "commit", "-qam", "rule edited")
    code_tag(repo)
    with refusal("above its change log differs"):
        F.check_code_frozen()


def test_a_design_without_its_change_log_heading_refuses(repo):
    snapshot(repo)
    (repo / "docs/research/rebates-design.md").write_text("intro\n\n## 2. Rules\nrule\n")
    git(repo, "commit", "-qam", "heading removed")
    code_tag(repo)
    with refusal("above its change log differs"):
        F.check_code_frozen()


@pytest.mark.parametrize("path,text", [("docs/research/rebates-design.md", DESIGN_TEXT + "- x\n"),
                                       ("tools/rebates/new.py", "y = 1\n"),
                                       ("docs/research/rebates-files.sha256", "# header\nedited\n"),
                                       ("elsewhere.txt", "anything\n")])
def test_any_uncommitted_change_refuses(repo, path, text):
    freeze(repo)
    F.check_code_frozen()                                               # frozen and clean: passes
    (repo / path).write_text(text)
    with refusal("uncommitted"):
        F.check_code_frozen()


def test_ignored_snapshot_files_do_not_make_the_tree_dirty(repo):
    freeze(repo)
    (repo / "tools/data/rebates/2026-11-05/a.pdf").write_bytes(b"x")
    F.check_code_frozen()


def write_manifest(repo, files: dict[str, bytes]):
    lines = []
    for rel, content in files.items():
        p = repo / "tools/data/rebates" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        lines.append(f"{F.sha256(p)}  {rel}  https://example.org/x  2026-11-05  description")
    C.MANIFEST.write_text("# header\n" + "\n".join(lines) + "\n")


def test_hash_check_covers_every_listed_file_and_nothing_else(repo):
    write_manifest(repo, {"2026-11-05/a.pdf": b"one", "2026-11-05/annual/b.zip": b"two"})
    assert F.verify_files() == []
    (repo / "tools/data/rebates/2026-11-05/a.pdf").write_bytes(b"changed")
    assert F.verify_files() == ["changed: tools/data/rebates/2026-11-05/a.pdf"]
    (repo / "tools/data/rebates/2026-11-05/a.pdf").write_bytes(b"one")
    (repo / "tools/data/rebates/2026-11-05/annual/b.zip").unlink()
    assert F.verify_files() == ["missing: tools/data/rebates/2026-11-05/annual/b.zip"]
    (repo / "tools/data/rebates/2026-11-05/annual/b.zip").write_bytes(b"two")
    (repo / "tools/data/rebates/2026-11-05/extra.txt").write_bytes(b"x")
    assert F.verify_files() == ["not in the manifest: 2026-11-05/extra.txt"]


def test_gate_needs_both_the_freeze_and_the_hashes(repo):
    write_manifest(repo, {"2026-11-05/a.pdf": b"one"})
    freeze(repo)
    F.gate()
    (repo / "tools/data/rebates/2026-11-05/a.pdf").write_bytes(b"changed")
    with refusal("does not match"):
        F.gate()


def test_stamp(repo):
    write_manifest(repo, {"2026-11-05/a.pdf": b"one"})
    freeze(repo)
    st = F.stamp()
    for t in C.STAMP_TAGS:
        assert st["tag_commits"][t] == git(repo, "rev-parse", f"refs/tags/{t}^{{commit}}").strip()
    assert st["head"] == git(repo, "rev-parse", "HEAD").strip()
    assert st["tools_rebates_tree"] == git(repo, "rev-parse", "HEAD:tools/rebates").strip()
    assert list(st["files_sha256"]) == ["2026-11-05/a.pdf"] and st["manifest_sha256"] == F.sha256(C.MANIFEST)


def test_the_real_manifest_lists_both_project_lists():
    # reads the committed manifest only (docs/research), never the snapshot
    listed = {p.rsplit("/", 1)[-1] for p in F.read_manifest()}
    assert {s.path.name for s in C.LISTS} <= listed
