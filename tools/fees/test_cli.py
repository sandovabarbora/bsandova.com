"""The stages and their gates on throwaway git repositories and invented files: the freeze, the hashes, the blinding
flag, the layout stage that shows no value, the synthetic dry run. No network, no real file."""
from __future__ import annotations

import json
import re
import subprocess

import cli
import config as C
import files as F
import inputs as I
import pytest
import structure as S
import synth as SY
import xlsx as X


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


DESIGN_TEXT = "intro\n\n## 2. Rules\nrule\n\n## Change log\n- first entry\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repository holding the design commit tagged `fees-design`; `snapshot` and `freeze` add the rest."""
    r = tmp_path / "repo"
    (r / "tools/fees").mkdir(parents=True)
    (r / "docs/research").mkdir(parents=True)
    (r / "tools/fees/code.py").write_text("x = 1\n")
    (r / "tools/fees/vat_map.csv").write_text("v\n")
    (r / "tools/fees/excise_map.csv").write_text("e\n")
    (r / "docs/research/fees-design.md").write_text(DESIGN_TEXT)
    (r / "docs/research/fees-files.sha256").write_text("# header\n")
    (r / ".gitignore").write_text("tools/data/fees/\n")
    git(r.parent, "init", "-q", "-b", "main", str(r))
    for k, v in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false"), ("tag.gpgsign", "false")):
        git(r, "config", k, v)
    git(r, "add", "-A")
    git(r, "commit", "-qm", "design")
    git(r, "tag", "-a", "-m", "design", C.DESIGN_TAG)
    for name, value in (("ROOT", r), ("DATA", r / "tools/data/fees"), ("DESIGN", r / "docs/research/fees-design.md"),
                        ("MANIFEST", r / "docs/research/fees-files.sha256"), ("VAT_MAP", r / "tools/fees/vat_map.csv"),
                        ("EXCISE_MAP", r / "tools/fees/excise_map.csv"), ("RESULTS", r / "docs/research/fees-results.json")):
        monkeypatch.setattr(C, name, value)
    (r / "tools/data/fees/2026-11-03").mkdir(parents=True)
    return r


def snapshot(repo):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "snapshot")
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
    with refusal("fees-data-step is not an ancestor of fees-code"):
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
    (repo / "tools/fees/code.py").write_text("x = 2\n")
    git(repo, "commit", "-qam", "change the code after the tag")
    with refusal("differs from the tag fees-code"):
        F.check_code_frozen()


def test_manifest_and_maps_must_equal_the_data_step_tag(repo):
    snapshot(repo)
    (repo / "docs/research/fees-files.sha256").write_text("# header\nchanged\n")
    git(repo, "commit", "-qam", "manifest changed after the data step")
    code_tag(repo)
    with refusal("manifest or a map differs from the tag fees-data-step"):
        F.check_code_frozen()


def test_a_map_changed_before_the_code_tag_is_still_refused(repo):
    snapshot(repo)
    (repo / "tools/fees/vat_map.csv").write_text("v2\n")
    git(repo, "commit", "-qam", "map changed")
    code_tag(repo)
    with refusal("manifest or a map differs"):
        F.check_code_frozen()


def test_design_text_above_the_change_log_must_equal_the_design_tag(repo):
    snapshot(repo)
    (repo / "docs/research/fees-design.md").write_text(DESIGN_TEXT + "- appended entry\n")
    git(repo, "commit", "-qam", "log entry")
    code_tag(repo)
    F.check_code_frozen()                                               # appending to the change log is allowed
    git(repo, "tag", "-d", C.CODE_TAG)
    (repo / "docs/research/fees-design.md").write_text(DESIGN_TEXT.replace("rule", "other rule") + "- appended entry\n")
    git(repo, "commit", "-qam", "rule edited")
    code_tag(repo)
    with refusal("above its change log differs"):
        F.check_code_frozen()


@pytest.mark.parametrize("path,text", [("docs/research/fees-design.md", DESIGN_TEXT + "- x\n"),
                                       ("tools/fees/new.py", "y = 1\n"),
                                       ("docs/research/fees-files.sha256", "# header\nedited\n")])
def test_uncommitted_changes_in_tools_design_or_manifest_refuse(repo, path, text):
    freeze(repo)
    F.check_code_frozen()                                               # frozen and clean: passes
    (repo / path).write_text(text)
    with refusal("uncommitted"):
        F.check_code_frozen()


def write_manifest(repo, files: dict[str, bytes]):
    lines = []
    for rel, content in files.items():
        p = repo / "tools/data/fees" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        lines.append(f"{F.sha256(p)}  {rel}  url  2026-11-03  description")
    C.MANIFEST.write_text("# header\n" + "\n".join(lines) + "\n")


def test_hash_check(repo):
    write_manifest(repo, {"2026-11-03/a.txt": b"one", "2026-11-03/b/c.txt": b"two"})
    assert F.verify_files() == []
    (repo / "tools/data/fees/2026-11-03/a.txt").write_bytes(b"changed")
    assert F.verify_files() == ["changed: tools/data/fees/2026-11-03/a.txt"]
    (repo / "tools/data/fees/2026-11-03/a.txt").write_bytes(b"one")
    (repo / "tools/data/fees/2026-11-03/b/c.txt").unlink()
    assert F.verify_files() == ["missing: tools/data/fees/2026-11-03/b/c.txt"]
    (repo / "tools/data/fees/2026-11-03/b/c.txt").write_bytes(b"two")
    (repo / "tools/data/fees/2026-11-03/extra.txt").write_bytes(b"x")
    assert F.verify_files() == ["not in the manifest: 2026-11-03/extra.txt"]


def test_maps_outside_the_data_folder_are_hashed_through_a_relative_path(repo):
    (repo / "tools/fees/vat_map.csv").write_text("a\n")
    C.MANIFEST.write_text(f"{F.sha256(repo / 'tools/fees/vat_map.csv')}  ../../fees/vat_map.csv  repo  d  map\n")
    assert F.verify_files() == []
    (repo / "tools/fees/vat_map.csv").write_text("b\n")
    assert F.verify_files() == ["changed: tools/fees/vat_map.csv"]


def test_gate_needs_both_the_freeze_and_the_hashes(repo):
    write_manifest(repo, {"2026-11-03/a.txt": b"one"})
    freeze(repo)
    F.gate()
    (repo / "tools/data/fees/2026-11-03/a.txt").write_bytes(b"changed")
    with refusal("does not match"):
        F.gate()


def test_run_refuses_without_unblind_and_never_touches_the_sources(repo, monkeypatch):
    def boom():
        raise AssertionError("the sources were touched before the gate")
    monkeypatch.setattr(I, "real_sources", boom)
    with refusal("--unblind"):
        cli.main(["--run"])
    with refusal("does not exist"):
        cli.main(["--run", "--unblind"])
    assert not C.RESULTS.exists()


def test_run_after_the_gate_writes_results_with_the_stamp(repo, monkeypatch, tmp_path):
    write_manifest(repo, {"2026-11-03/a.txt": b"one"})
    freeze(repo)
    monkeypatch.setattr(I, "real_sources", lambda: SY.make_snapshot(tmp_path / "snap"))
    monkeypatch.setattr(cli, "results_for", lambda src: {"qa": {"label": "x"}})
    cli.main(["--run", "--unblind"])
    res = json.loads(C.RESULTS.read_text())
    st = res["design"]["stamp"]
    for t in C.STAMP_TAGS:
        assert st["tag_commits"][t] == git(repo, "rev-parse", f"refs/tags/{t}^{{commit}}").strip()
    assert st["head"] == git(repo, "rev-parse", "HEAD").strip()
    assert st["tools_fees_tree"] == git(repo, "rev-parse", "HEAD:tools/fees").strip()
    assert set(st) == {"manifest_sha256", "files_sha256", "maps_sha256", "tag_commits", "head", "tools_fees_tree"}
    assert list(st["files_sha256"]) == ["2026-11-03/a.txt"]


def test_synthetic_run_needs_no_gate_and_writes_aggregates_only(tmp_path):
    cli.main(["--synthetic", "--out", str(tmp_path)])
    res = json.loads((tmp_path / "fees-results-synthetic.json").read_text())
    assert res["synthetic"] is True and len(res["qa"]["members"]) == 12
    assert res["checks_flag"]["2_allocation_to_the_crown"]["passed"] is True
    assert "households" in res["qb"] and "decile_total_czk" in res["qb"]["after"]


def test_structure_stage_shows_labels_and_counts_but_no_value(monkeypatch, tmp_path, capsys):
    src = SY.make_snapshot(tmp_path / "snap")
    monkeypatch.setattr(I, "real_sources", lambda: src)
    monkeypatch.setattr(F, "verify_files", lambda *a, **k: [])
    cli.main(["--structure"])
    out = capsys.readouterr().out
    assert "decile columns" in out and "quintile columns" in out and "items with an empty cell" in out
    shown = {t for t in re.findall(r"\d{5,}", out)}
    invented = set()
    for text in (SY.budget_g(), SY.ct_budget(), SY.ct_report(), SY.cro_report(), SY.cro_chart()):
        invented |= {re.sub(r"\D", "", t) for t in re.findall(r"\d{1,3}(?: \d{3})+|\d{5,}", text)}
    for v in (SY.HH, SY.NET_CU, SY.Q_HH, SY.TAX_CU):
        invented |= {str(int(x)) for x in v}
    # the band bound 10 000 is a label; every other long number would be an invented value leaking into the output
    assert not (shown & invented - {"10000"})


def test_layout_reading_of_a_workbook_holds_no_number(tmp_path):
    src = SY.make_snapshot(tmp_path / "snap")
    for path in (src.silc_3a, src.silc_10a, src.hbs_characteristics, src.hbs_expenditure, src.cnb_indicators):
        for rows in X.read_workbook(path, values=False).values():
            assert all(not hasattr(c, "as_tuple") for r in rows for c in r)          # no Decimal anywhere
    assert list(S.describe(src))                                                      # and the stage still finds everything


def test_structure_stage_refuses_when_a_file_changed(repo):
    write_manifest(repo, {"2026-11-03/a.txt": b"one"})
    (repo / "tools/data/fees/2026-11-03/a.txt").write_bytes(b"changed")
    with refusal("refusing to look at the files"):
        cli.main(["--structure"])


def test_the_blinding_guard_fires_on_open_and_on_a_subprocess_argument():
    real = C.DATA.resolve() / "2026-11-03" / "x.csv"
    with pytest.raises(AssertionError, match="real snapshot"), open(real, encoding="utf-8"):
        pass
    with pytest.raises(AssertionError, match="real snapshot"):
        real.read_text()
    with pytest.raises(AssertionError, match="subprocess"):
        subprocess.run(["pdftotext", "-layout", str(real), "-"], check=False)
    with pytest.raises(AssertionError, match="subprocess"):
        subprocess.run(["cat", f"--file={real}"], check=False)
