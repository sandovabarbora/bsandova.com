"""The stages: the data step on invented lists (counts and booleans, no outcome value), its refusal on a changed
snapshot, the blinding flag and the gate before --run, the placeholder estimation, and the guard of conftest.py."""
from __future__ import annotations

import json
import re
import subprocess

import analysis as A
import cli
import config as C
import files as F
import pytest
import synth as SY
from test_files import freeze, repo, write_manifest  # noqa: F401  (the fixture)


def refusal(match):
    return pytest.raises(SystemExit, match=match)


def outcome_texts(specs) -> set[str]:
    # every printed outcome cell of the invented lists, digits only
    out = set()
    for s in specs:
        for row in SY.list_rows(s.years):
            for k in ("allocation", "new_allocation", "incentive_1", "incentive_2", "paid", "cancellation_date",
                      "change_date", "decision_1_date", "decision_2_date"):
                if row.get(k):
                    out.add(re.sub(r"\D", "", row[k]))
    return out


def test_structure_on_invented_lists_writes_counts_and_shows_no_outcome(monkeypatch, tmp_path, capsys):
    specs = SY.make_lists(tmp_path / "snap")
    monkeypatch.setattr(C, "LISTS", specs)
    monkeypatch.setattr(C, "STRUCTURE", tmp_path / "structure.json")
    monkeypatch.setattr(C, "MANIFEST", tmp_path / "manifest")
    (tmp_path / "manifest").write_text("# header\n")
    monkeypatch.setattr(F, "verify_files", lambda *a, **k: [])
    with pytest.raises(SystemExit) as e:
        cli.main(["--structure"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert "check 1 (row parse): passed" in out and "stops: none; flags: none" in out
    rep = json.loads((tmp_path / "structure.json").read_text())
    assert rep["check_6_counts"]["A"]["rows"] == 18 and rep["manifest_sha256"] == F.sha256(tmp_path / "manifest")
    shown = {re.sub(r"\D", "", t) for t in re.findall(r"[\d. ]{5,}", out + json.dumps(rep))}
    assert not shown & outcome_texts(specs)


def test_structure_stops_with_exit_1_on_a_row_that_does_not_parse(monkeypatch, tmp_path, capsys):
    rows = SY.list_rows((2016, 2021))
    rows[0]["title"] = ""
    specs = SY.make_lists(tmp_path / "snap", a=rows)
    monkeypatch.setattr(C, "LISTS", specs)
    monkeypatch.setattr(C, "STRUCTURE", tmp_path / "structure.json")
    monkeypatch.setattr(F, "verify_files", lambda *a, **k: [])
    with pytest.raises(SystemExit) as e:
        cli.main(["--structure"])
    assert e.value.code == 1
    assert "STOP: list A 1P/2016: no title" in capsys.readouterr().out
    assert json.loads((tmp_path / "structure.json").read_text())["stops"] == ["check_1"]


def test_structure_refuses_when_a_file_changed(repo):  # noqa: F811
    write_manifest(repo, {"2026-11-05/a.pdf": b"one"})
    (repo / "tools/data/rebates/2026-11-05/a.pdf").write_bytes(b"changed")
    with refusal("refusing to look at the files"):
        cli.main(["--structure"])
    assert not C.STRUCTURE.exists()


def test_synthetic_run(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--synthetic", "--out", str(tmp_path)])
    assert e.value.code == 0
    assert json.loads((tmp_path / "rebates-structure-synthetic.json").read_text())["stops"] == []


def test_run_refuses_without_unblind_and_never_touches_the_lists(repo, monkeypatch):  # noqa: F811
    def boom(*a, **k):
        raise AssertionError("the lists were read before the gate")
    monkeypatch.setattr(cli, "load", boom)
    with refusal("--unblind"):
        cli.main(["--run"])
    with refusal("the tag rebates-data-step does not exist"):
        cli.main(["--run", "--unblind"])
    assert not C.RESULTS.exists()


def test_run_after_the_gate_reaches_the_placeholder(repo, monkeypatch):  # noqa: F811
    write_manifest(repo, {"2026-11-05/a.pdf": b"one"})
    freeze(repo)
    monkeypatch.setattr(cli, "load", lambda *a, **k: {})
    with pytest.raises(NotImplementedError, match="estimation code comes after rebates-data-step"):
        cli.main(["--run", "--unblind"])
    with pytest.raises(NotImplementedError):
        A.run({})


def test_the_blinding_guard_fires_on_open_and_on_a_subprocess_argument():
    real = C.DATA.resolve() / "2026-11-05" / "list-A-2016-2021-30012026.pdf"
    with pytest.raises(AssertionError, match="real snapshot"), open(real, "rb"):
        pass
    with pytest.raises(AssertionError, match="real snapshot"):
        real.read_bytes()
    with pytest.raises(AssertionError, match="subprocess"):
        subprocess.run(["pdftotext", "-tsv", str(real), "-"], check=False)
    with pytest.raises(AssertionError, match="subprocess"):
        subprocess.run(["cat", f"--file={real}"], check=False)
    with pytest.raises(AssertionError, match="real snapshot"):
        cli.load()                                                     # the real lists, through the parser
