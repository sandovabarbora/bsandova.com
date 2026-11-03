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


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    (r / "tools/fees").mkdir(parents=True)
    (r / "docs/research").mkdir(parents=True)
    (r / "tools/fees/code.py").write_text("x = 1\n")
    (r / "docs/research/fees-design.md").write_text("design\n")
    (r / ".gitignore").write_text("tools/data/fees/\n")
    git(r.parent, "init", "-q", "-b", "main", str(r))
    for k, v in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false"), ("tag.gpgsign", "false")):
        git(r, "config", k, v)
    git(r, "add", "-A")
    git(r, "commit", "-qm", "design")
    for name, value in (("ROOT", r), ("DATA", r / "tools/data/fees"), ("DESIGN", r / "docs/research/fees-design.md"),
                        ("MANIFEST", r / "docs/research/fees-files.sha256"),
                        ("RESULTS", r / "docs/research/fees-results.json")):
        monkeypatch.setattr(C, name, value)
    (r / "tools/data/fees/2026-11-03").mkdir(parents=True)
    return r


def refusal(match):
    return pytest.raises(SystemExit, match=match)


def test_no_tag_no_run(repo):
    with refusal("does not exist"):
        F.check_code_frozen()


def test_a_branch_of_the_same_name_is_not_the_tag(repo):
    git(repo, "branch", C.CODE_TAG)
    with refusal("does not exist"):
        F.check_code_frozen()


def test_tag_must_be_an_ancestor_of_head(repo):
    git(repo, "checkout", "-q", "-b", "other")
    git(repo, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    git(repo, "tag", C.CODE_TAG)
    git(repo, "checkout", "-q", "main")
    git(repo, "commit", "-q", "--allow-empty", "-m", "main moves on")
    with refusal("not an ancestor"):
        F.check_code_frozen()


def test_tools_at_head_must_equal_the_tag(repo):
    git(repo, "tag", C.CODE_TAG)
    (repo / "tools/fees/code.py").write_text("x = 2\n")
    git(repo, "commit", "-qam", "change the code after the tag")
    with refusal("differs from the tag"):
        F.check_code_frozen()


def test_uncommitted_changes_in_tools_or_design_refuse(repo):
    git(repo, "tag", C.CODE_TAG)
    F.check_code_frozen()                                               # frozen and clean: passes
    (repo / "docs/research/fees-design.md").write_text("edited\n")
    with refusal("uncommitted"):
        F.check_code_frozen()
    git(repo, "checkout", "--", "docs/research/fees-design.md")
    (repo / "tools/fees/new.py").write_text("y = 1\n")
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
    git(repo, "tag", C.CODE_TAG)
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
    (repo / "tools/fees/vat_map.csv").write_text("v\n")
    (repo / "tools/fees/excise_map.csv").write_text("e\n")
    for name in ("VAT_MAP", "EXCISE_MAP"):
        monkeypatch.setattr(C, name, repo / "tools/fees" / ("vat_map.csv" if name == "VAT_MAP" else "excise_map.csv"))
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "maps")
    git(repo, "tag", C.CODE_TAG)
    monkeypatch.setattr(I, "real_sources", lambda: SY.make_snapshot(tmp_path / "snap"))
    monkeypatch.setattr(cli, "results_for", lambda src: {"qa": {"label": "x"}})
    cli.main(["--run", "--unblind"])
    res = json.loads(C.RESULTS.read_text())
    st = res["design"]["stamp"]
    assert st["tag_commits"][C.CODE_TAG] == git(repo, "rev-parse", f"refs/tags/{C.CODE_TAG}^{{commit}}").strip()
    assert st["tag_commits"][C.DESIGN_TAG] is None                      # absent in the throwaway repository, recorded as such
    assert set(st) == {"manifest_sha256", "files_sha256", "maps_sha256", "tag_commits"}
    assert list(st["files_sha256"]) == ["2026-11-03/a.txt"]


def test_synthetic_run_needs_no_gate_and_writes_aggregates_only(tmp_path):
    cli.main(["--synthetic", "--out", str(tmp_path)])
    res = json.loads((tmp_path / "fees-results-synthetic.json").read_text())
    assert res["synthetic"] is True and len(res["qa"]["members"]) == 12
    assert res["checks_flag"]["2_allocation_to_the_crown"]["passed"] is True
    assert "households" in res["qb"] and "decile_total_czk" in res["qb"]["after"]
    assert not C.RESULTS.exists() or C.RESULTS.stat().st_mtime_ns > 0          # the real file is the conftest's to guard


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
