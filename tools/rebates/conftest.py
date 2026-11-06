import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(autouse=True, scope="session")
def real_outputs_untouched():
    # tests use invented inputs and temporary folders: fail loudly if a real structure or results file appears or changes
    import config as C
    real = (C.STRUCTURE, C.RESULTS)
    before = [p.stat().st_mtime_ns if p.exists() else None for p in real]
    yield
    after = [p.stat().st_mtime_ns if p.exists() else None for p in real]
    assert after == before, "a test wrote into the study's real structure or results file"


@pytest.fixture(autouse=True)
def never_open_the_real_snapshot(monkeypatch):
    # blinding: no test may read anything under tools/data/rebates, by open() or by a subprocess argument (the tests that
    # need a repository use temporary ones)
    import builtins
    import io
    import pathlib
    import subprocess

    import config as C
    real = C.DATA.resolve()
    orig_open = builtins.open
    orig_popen_init = subprocess.Popen.__init__

    def under(x) -> bool:
        if isinstance(x, bytes):
            x = x.decode(errors="ignore")
        if not isinstance(x, (str, pathlib.PurePath)):
            return False
        text = str(x)
        for cand in (text, *text.split("=", 1)[-1:]):
            try:
                p = pathlib.Path(cand).resolve()
            except (OSError, ValueError):
                continue
            if p == real or real in p.parents:
                return True
        return False

    def guard(file, *a, **k):
        if under(file):
            raise AssertionError(f"a test opened the real snapshot: {pathlib.Path(str(file)).name}")
        return orig_open(file, *a, **k)

    def popen_guard(self, args, *a, **k):
        items = [args] if isinstance(args, (str, bytes, pathlib.PurePath)) else list(args)
        if any(under(x) for x in items):
            raise AssertionError("a test passed a path under the real snapshot to a subprocess")
        return orig_popen_init(self, args, *a, **k)

    monkeypatch.setattr(builtins, "open", guard)
    monkeypatch.setattr(io, "open", guard)
    monkeypatch.setattr(pathlib.Path, "open", lambda self, *a, **k: guard(self, *a, **k))
    monkeypatch.setattr(subprocess.Popen, "__init__", popen_guard)
