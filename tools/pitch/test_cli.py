"""The stages and their gates on a throwaway git repository with invented subtitle files and a scripted model: the
blinding flag, the freeze, the hashes, the blind sample before any model output, the song marks. No network."""
from __future__ import annotations

import functools
import json
import subprocess

import analysis as A
import cli
import client as CL
import config as C
import files as F
import pytest
import synth as SY
from conftest import srt


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture(autouse=True)
def no_real_client(monkeypatch):
    class Scripted(SY.ScriptedModel):
        sdk_version = "scripted"
    monkeypatch.setattr(CL, "AnthropicClient", Scripted)
    monkeypatch.setattr(CL, "ClaudeCliClient", Scripted)
    monkeypatch.setitem(cli._gate, "passed", False)
    monkeypatch.setattr(A, "study", functools.partial(A.study, reps=200))
    monkeypatch.setattr(SY, "srt_file", functools.partial(SY.srt_file, n_cues=160))    # keeps the suite fast


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    (r / "tools/pitch").mkdir(parents=True)
    (r / "docs/research").mkdir(parents=True)
    (r / "tools/pitch/code.py").write_text("x = 1\n")
    (r / "docs/research/pitch-design.md").write_text("design\n")
    (r / ".gitignore").write_text("tools/data/pitch/\n")
    git(r.parent, "init", "-q", str(r))
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    git(r, "config", "commit.gpgsign", "false")
    git(r, "config", "tag.gpgsign", "false")
    git(r, "add", "-A")
    git(r, "commit", "-qm", "design")
    git(r, "tag", "pitch-design")
    git(r, "commit", "-q", "--allow-empty", "-m", "code")
    git(r, "tag", C.CODE_TAG)
    data = r / "tools/data/pitch"
    for name, value in (("ROOT", r), ("DATA", data), ("RAW", data / "raw"), ("VALIDATION", data / "validation"),
                        ("OUT", data / "out"), ("MANIFEST", r / "docs/research/pitch-files.sha256"),
                        ("SONG_MARKS", r / "docs/research/pitch-song-marks.json"),
                        ("RESULTS", r / "docs/research/pitch-results.json"),
                        ("SAMPLE", data / "validation/sample.json"), ("FORM", data / "validation/form.html"),
                        ("HUMAN", data / "validation/validation-human.json"),
                        ("ITALIC_RUNS", data / "validation/italic-runs.json")):
        monkeypatch.setattr(C, name, value)
    (data / "raw").mkdir(parents=True)
    return r


def put_files(repo, pp1=None, pp2=None):
    (C.RAW / "pp1.srt").write_text(pp1 or SY.srt_file(1), encoding="utf-8")
    cp = pp2 or SY.srt_file(2).replace("\u266a", "#").replace("ferry", "caf\u00e9")    # # for ♪: cp1252 has no ♪
    (C.RAW / "pp2.srt").write_bytes(cp.encode("cp1252"))


def code_sample(change=None):
    smp = json.loads(C.SAMPLE.read_text())
    codes = []
    for k, it in enumerate(smp["items"]):
        if k % 3 == 0:
            codes.append({**it, "joke": True, "target": "genre", "group_type": "", "group_other": "", "butt": "group"})
        else:
            codes.append({**it, "joke": False if k % 7 else C.SKIP})
    if change:
        change(codes)
    C.HUMAN.write_text(json.dumps({"codes": codes}))


def commit_all(repo, msg="results"):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", msg)


def to_blind_sample(repo):
    put_files(repo)
    cli.main(["--hash-files", "--unblind"])
    commit_all(repo, "hashes")
    cli.main(["--draw-sample", "--unblind"])
    code_sample()
    cli.main(["--hash-sample", "--unblind"])
    commit_all(repo, "sample hash")


# ---------------------------------------------------------------- blinding and the dry run

def test_every_real_stage_needs_unblind_and_touches_nothing_without_it(repo):
    put_files(repo)
    for argv in (["--hash-files"], ["--italic-runs"], ["--draw-sample"], ["--hash-sample"], ["--run", "1"],
                 ["--analyse"]):
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        assert "--unblind" in str(e.value)
    assert not C.MANIFEST.exists() and not C.VALIDATION.exists() and not C.OUT.exists()


def test_reps_is_refused_on_real_data_and_one_stage_must_be_chosen():
    with pytest.raises(SystemExit, match="10 000 replicates"):
        cli.main(["--analyse", "--unblind", "--reps", "100"])
    with pytest.raises(SystemExit):
        cli.main([])


def test_the_synthetic_dry_run_writes_results_without_subtitle_text(tmp_path, capsys):
    assert cli.main(["--synthetic", "--out", str(tmp_path), "--reps", "200"]) == 0
    res = json.loads((tmp_path / "results.json").read_text())
    assert res["status"] in ("Registered study", "Exploratory") and res["meta"]["synthetic"]
    assert set(res["readings"]) == {"Q1", "Q2", "Q2_difference", "Q3"}
    assert set(res["checks"]) == {"run_2", "unclear_as_group", "unclear_as_speaker", "scene_gap_5s", "scene_gap_12s",
                                  "full_runtime", "without_allusions", "protected_widened", "q1_america_per_hour"}
    text = (tmp_path / "results.json").read_text()
    assert not any(w in text for w in SY.WORDS)                         # counts and codes, never subtitle text
    assert (tmp_path / "form.html").exists() and (tmp_path / "run1/pp1.json").exists()
    assert json.loads(capsys.readouterr().out)["results"].endswith("results.json")


# ---------------------------------------------------------------- the freeze

def test_the_freeze_passes_on_the_tagged_clean_code(repo):
    cli.check_code_frozen()


def test_the_freeze_refuses_without_the_tag_or_when_it_is_not_an_ancestor(repo):
    git(repo, "tag", "-d", C.CODE_TAG)
    with pytest.raises(SystemExit, match=f"{C.CODE_TAG} does not exist"):
        cli.check_code_frozen()
    git(repo, "checkout", "-q", "--orphan", "other")
    git(repo, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    git(repo, "tag", C.CODE_TAG)
    git(repo, "checkout", "-q", "master" if "master" in git(repo, "branch") else "main")
    with pytest.raises(SystemExit, match="not an ancestor of HEAD"):
        cli.check_code_frozen()


def test_a_branch_named_like_the_tag_does_not_count_as_the_freeze(repo):
    git(repo, "tag", "-d", C.CODE_TAG)
    git(repo, "branch", C.CODE_TAG)
    with pytest.raises(SystemExit, match=f"{C.CODE_TAG} does not exist"):
        cli.check_code_frozen()


def test_a_file_in_neither_encoding_is_refused(repo):
    put_files(repo, pp1="1\n00:00:01,000 --> 00:00:02,000\nA.\n")
    (C.RAW / "pp1.srt").write_bytes(b"1\n00:00:01,000 --> 00:00:02,000\n\x81\xff\n")
    with pytest.raises(SystemExit, match="neither UTF-8 nor cp1252"):
        cli.main(["--hash-files", "--unblind"])


def test_the_freeze_refuses_code_changed_after_the_tag_and_uncommitted_changes(repo):
    (repo / "docs/research/pitch-design.md").write_text("edited\n")
    with pytest.raises(SystemExit, match="uncommitted"):
        cli.check_code_frozen()
    git(repo, "checkout", "--", ".")
    (repo / "tools/pitch/code.py").write_text("x = 2\n")
    commit_all(repo, "change")
    with pytest.raises(SystemExit, match=f"differs from the tag {C.CODE_TAG}"):
        cli.check_code_frozen()


def test_no_real_stage_runs_on_unfrozen_code(repo):
    put_files(repo)
    git(repo, "tag", "-d", C.CODE_TAG)
    for argv in (["--hash-files"], ["--draw-sample"], ["--hash-sample"], ["--run", "1"], ["--analyse"]):
        with pytest.raises(SystemExit, match="refusing"):
            cli.main([*argv, "--unblind"])
    assert not C.MANIFEST.exists()


# ---------------------------------------------------------------- files, sample and the model gate

def test_the_whole_registered_sequence_on_invented_files(repo, capsys):
    to_blind_sample(repo)
    manifest = C.MANIFEST.read_text()
    assert "pp1.srt" in manifest and "read as cp1252" in manifest and "validation-human.json" in manifest
    assert "♪" not in C.FORM.read_text() and "://" not in C.FORM.read_text()
    cli.gate_model_run()
    assert cli.main(["--run", "1", "--unblind"]) == 0
    assert cli.main(["--run", "2", "--unblind"]) == 0
    settings = json.loads((C.OUT / "run1/settings.json").read_text())
    assert settings["model"] == "claude-sonnet-5-5" and "temperature" not in settings
    assert settings["thinking"] == {"type": "adaptive"} and settings["effort"] == "high"
    assert settings["sdk_pin"] == "anthropic==2.3.0" and set(settings["schema_sha256"]) == {"segment", "code"}
    assert len(settings["prompt_sha256"]) == 5 and settings["sdk"] == "scripted"
    capsys.readouterr()
    assert cli.main(["--analyse", "--unblind"]) == 0
    res = json.loads(C.RESULTS.read_text())
    assert res["validation"]["cues"] == 100 and res["validation"]["skipped"] > 0
    assert res["meta"]["tags"][C.CODE_TAG] == git(repo, "rev-parse", C.CODE_TAG).strip()
    assert set(res["meta"]["file_hashes"]) == {"pp1.srt", "pp2.srt", "validation-human.json"}
    assert not any(w in C.RESULTS.read_text() for w in SY.WORDS)


def test_the_model_run_refuses_a_dirty_tree_or_untracked_files(repo):
    to_blind_sample(repo)
    (repo / "README.md").write_text("x\n")
    commit_all(repo, "readme")
    (repo / "README.md").write_text("changed\n")
    with pytest.raises(SystemExit, match="uncommitted changes"):
        cli.main(["--run", "1", "--unblind"])
    git(repo, "checkout", "--", "README.md")
    (repo / "docs/research/notes.txt").write_text("x\n")
    with pytest.raises(SystemExit, match="untracked files"):
        cli.main(["--run", "1", "--unblind"])
    assert not C.OUT.exists()


def test_the_model_run_refuses_without_the_committed_hash_of_the_blind_sample(repo):
    put_files(repo)
    cli.main(["--hash-files", "--unblind"])
    commit_all(repo, "hashes")
    with pytest.raises(SystemExit, match="validation-human.json is not in"):
        cli.main(["--run", "1", "--unblind"])
    cli.main(["--draw-sample", "--unblind"])
    code_sample()
    cli.main(["--hash-sample", "--unblind"])
    with pytest.raises(SystemExit, match="uncommitted changes"):           # the hash is written, not committed
        cli.main(["--run", "1", "--unblind"])
    assert not C.OUT.exists()


def test_the_model_run_refuses_codes_changed_or_missing_after_the_hash(repo):
    to_blind_sample(repo)
    code_sample(lambda codes: codes[1].update(joke=True, target="america", butt="speaker", group_type="",
                                              group_other=""))
    with pytest.raises(SystemExit, match="does not match its committed hash"):
        cli.main(["--run", "1", "--unblind"])
    with pytest.raises(SystemExit, match="have changed since"):
        cli.main(["--hash-sample", "--unblind"])
    C.HUMAN.unlink()
    with pytest.raises(SystemExit, match="validation-human.json is missing"):
        cli.main(["--run", "1", "--unblind"])


def test_every_stage_stops_on_a_subtitle_file_other_than_the_hashed_one(repo):
    to_blind_sample(repo)
    (C.RAW / "pp1.srt").write_text(SY.srt_file(3), encoding="utf-8")
    for argv in (["--run", "1"], ["--analyse"], ["--italic-runs"]):
        with pytest.raises(SystemExit, match="pp1.srt does not match the hash"):
            cli.main([*argv, "--unblind"])
    with pytest.raises(SystemExit, match="files are never replaced"):
        cli.main(["--hash-files", "--unblind"])


def test_the_sample_is_drawn_once_and_never_after_model_output(repo):
    put_files(repo)
    cli.main(["--hash-files", "--unblind"])
    (C.OUT / "run1").mkdir(parents=True)
    (C.OUT / "run1/pp1.json").write_text("{}")
    with pytest.raises(SystemExit, match="model output exists"):
        cli.main(["--draw-sample", "--unblind"])
    (C.OUT / "run1/pp1.json").unlink()
    cli.main(["--draw-sample", "--unblind"])
    with pytest.raises(SystemExit, match="drawn once"):
        cli.main(["--draw-sample", "--unblind"])


def test_hash_sample_refuses_codes_that_do_not_fit_the_sample_or_the_codebook(repo):
    put_files(repo)
    cli.main(["--hash-files", "--unblind"])
    cli.main(["--draw-sample", "--unblind"])
    code_sample(lambda codes: codes.pop())
    with pytest.raises(SystemExit, match="exactly the sampled cues"):
        cli.main(["--hash-sample", "--unblind"])
    code_sample(lambda codes: codes[0].update(target="people"))
    with pytest.raises(SystemExit, match="outside the codebook"):
        cli.main(["--hash-sample", "--unblind"])


def test_analyse_refuses_an_incomplete_pair_of_runs(repo):
    to_blind_sample(repo)
    cli.main(["--run", "1", "--unblind"])
    with pytest.raises(SystemExit, match="run 2 is incomplete"):
        cli.main(["--analyse", "--unblind"])


def test_a_malformed_subtitle_file_stops_with_its_position(repo):
    put_files(repo, pp1=srt((1, 0, 1, "Fine.")) + "\n2\nno time here\nText.\n")
    with pytest.raises(SystemExit, match="malformed subtitle file pp1.srt: line 6"):
        cli.main(["--hash-files", "--unblind"])
    assert not C.MANIFEST.exists()


def test_a_missing_key_refuses_the_run_without_printing_anything_secret(repo, monkeypatch):
    to_blind_sample(repo)
    def no_key():
        raise CL.CallFailed("no ANTHROPIC_API_KEY in the environment or in .env")
    monkeypatch.setattr(CL, "AnthropicClient", no_key)
    with pytest.raises(SystemExit, match="no ANTHROPIC_API_KEY"):
        cli.main(["--run", "1", "--unblind", "--client", "api"])


@pytest.mark.parametrize("args, chosen", [([], "cli"), (["--client", "claude-cli"], "cli"), (["--client", "api"], "api")])
def test_the_client_flag_picks_the_client(repo, monkeypatch, args, chosen):
    to_blind_sample(repo)
    def pick(name):
        def make():
            raise CL.CallFailed(f"picked {name}")
        return make
    monkeypatch.setattr(CL, "AnthropicClient", pick("api"))
    monkeypatch.setattr(CL, "ClaudeCliClient", pick("cli"))
    with pytest.raises(SystemExit, match=f"picked {chosen}"):
        cli.main(["--run", "1", "--unblind", *args])


def test_a_run_refuses_a_client_version_other_than_the_one_recorded(tmp_path):
    F.write_json(tmp_path / "run1" / "settings.json", {"sdk": "claude-cli 1.0"})
    cli.check_same_client(tmp_path, 1, "claude-cli 1.0")
    with pytest.raises(SystemExit, match="made with claude-cli 1.0"):
        cli.check_same_client(tmp_path, 2, "claude-cli 2.0")


# ---------------------------------------------------------------- the lyric fallback

def italic_film(seed):
    """Invented file with no ♪, ♫ or # marker and one italic run of four cues."""
    base = SY.srt_file(seed, n_cues=300, songs=False).split("\n\n")
    cues = []
    for k, block in enumerate(base):
        lines = block.strip().split("\n")
        if 100 <= k < 104:
            lines[2] = f"<i>{lines[2]}</i>"
        cues.append("\n".join(lines))
    return "\n\n".join(cues) + "\n"


def test_the_fallback_needs_the_authors_marks_before_the_sample_and_committed_before_the_run(repo):
    put_files(repo, italic_film(5), italic_film(6))
    cli.main(["--hash-files", "--unblind"])
    commit_all(repo, "hashes")
    with pytest.raises(SystemExit, match="need the author's song marks"):
        cli.main(["--draw-sample", "--unblind"])
    cli.main(["--italic-runs", "--unblind"])
    marks = json.loads(C.SONG_MARKS.read_text())
    assert [(r["first_cue"], r["last_cue"], r["mark"]) for r in marks["pp1"]] == [(101, 104, None)]
    assert "text" not in json.dumps(marks)
    for f in C.FILMS:
        marks[f][0]["mark"] = "song" if f == "pp1" else "not song"
    C.SONG_MARKS.write_text(json.dumps(marks))
    cli.main(["--draw-sample", "--unblind"])
    code_sample()
    cli.main(["--hash-sample", "--unblind"])
    assert "pitch-song-marks.json" in C.MANIFEST.read_text()
    git(repo, "add", str(C.MANIFEST))
    git(repo, "commit", "-qm", "hash without the marks")
    with pytest.raises(SystemExit, match="untracked files"):
        cli.main(["--run", "1", "--unblind"])
    with pytest.raises(SystemExit, match="pitch-song-marks.json is not committed"):
        cli.check_song_marks_committed()
    git(repo, "add", str(C.SONG_MARKS))
    git(repo, "commit", "-qm", "the marks")
    cli.gate_model_run()
    marks["pp2"][0]["mark"] = "song"
    C.SONG_MARKS.write_text(json.dumps(marks))
    with pytest.raises(SystemExit, match="uncommitted changes"):
        cli.main(["--run", "1", "--unblind"])
    with pytest.raises(SystemExit, match="song marks are not committed"):
        cli.check_song_marks_committed()


# ---------------------------------------------------------------- run stamps, no re-runs, the gate inside the library

def test_synthetic_output_never_goes_into_the_real_data_folder(tmp_path, monkeypatch):
    for out in (C.OUT / "run1", C.DATA, C.OUT / "synthetic"):
        with pytest.raises(SystemExit, match="refusing --synthetic"):
            cli.main(["--synthetic", "--out", str(out), "--reps", "10"])
    monkeypatch.setattr(cli.tempfile, "mkdtemp", lambda prefix: str(tmp_path / "tmpdir"))
    assert cli.main(["--synthetic", "--reps", "10"]) == 0 and (tmp_path / "tmpdir/results.json").exists()


def test_run_model_refuses_a_real_client_without_the_gate(tmp_path):
    class Real:
        def call(self, *a):
            raise AssertionError("called")
    films = cli.load_films({"pp1": SY.srt_file(1), "pp2": SY.srt_file(2)}, None)
    with pytest.raises(SystemExit, match="needs the gate"):
        cli.run_model(films, Real(), 1, tmp_path)
    assert not (tmp_path / "run1").exists()


def test_a_run_is_made_once_and_carries_its_stamp(repo):
    to_blind_sample(repo)
    cli.main(["--run", "1", "--unblind"])
    out = json.loads((C.OUT / "run1/pp1.json").read_text())
    stamp = out["stamp"]
    assert stamp == json.loads((C.OUT / "run1/settings.json").read_text())["stamp"]
    assert stamp["pitch_code_commit"] == git(repo, "rev-parse", f"{C.CODE_TAG}^{{commit}}").strip()
    assert stamp["human_sha256"] == cli.F.sha256(C.HUMAN) and set(stamp["raw_sha256"]) == {"pp1", "pp2"}
    with pytest.raises(SystemExit, match="run 1 exists already"):
        cli.main(["--run", "1", "--unblind"])


def test_analyse_refuses_runs_made_on_other_inputs(repo):
    to_blind_sample(repo)
    cli.main(["--run", "1", "--unblind"])
    cli.main(["--run", "2", "--unblind"])
    path = C.OUT / "run2/pp2.json"
    run2 = json.loads(path.read_text())
    run2["stamp"]["human_sha256"] = "0" * 64
    path.write_text(json.dumps(run2))
    with pytest.raises(SystemExit, match="run 2 was made on other"):
        cli.main(["--analyse", "--unblind"])
    run2["stamp"] = None
    path.write_text(json.dumps(run2))
    with pytest.raises(SystemExit, match="run 2 was made on other"):
        cli.main(["--analyse", "--unblind"])


def test_a_stopped_run_writes_no_run_output(repo, monkeypatch):
    to_blind_sample(repo)

    class Failing(SY.ScriptedModel):
        sdk_version = "x"

        def call(self, system, user, max_tokens, schema):
            if "Scene to segment" in user:
                return CL.Reply("nope", "m", "end_turn", 1, 1)
            return super().call(system, user, max_tokens, schema)
    monkeypatch.setattr(CL, "AnthropicClient", Failing)
    monkeypatch.setattr(CL, "ClaudeCliClient", Failing)
    with pytest.raises(SystemExit, match="stopping"):
        cli.main(["--run", "1", "--unblind"])
    assert not (C.OUT / "run1/pp1.json").exists() and (C.OUT / "run1/settings.json").exists()
