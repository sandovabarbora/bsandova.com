import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(autouse=True, scope="session")
def real_outputs_untouched():
    # tests use invented inputs and temporary folders: fail loudly if the study's real output appears or changes
    import config as C
    before = C.RESULTS.stat().st_mtime_ns if C.RESULTS.exists() else None
    yield
    after = C.RESULTS.stat().st_mtime_ns if C.RESULTS.exists() else None
    assert after == before, "a test wrote into the study's real results file"


@pytest.fixture(autouse=True)
def never_open_the_real_snapshot(monkeypatch):
    # blinding: no test may read anything under tools/data/fees (the tests that need a repository use temporary ones)
    import builtins
    import io
    import pathlib

    import config as C
    real = C.DATA.resolve()
    orig = builtins.open

    def guard(file, *a, **k):
        if isinstance(file, (str, bytes, pathlib.PurePath)):
            p = pathlib.Path(file if not isinstance(file, bytes) else file.decode()).resolve()
            if p == real or real in p.parents:
                raise AssertionError(f"a test opened the real snapshot: {p.name}")
        return orig(file, *a, **k)

    monkeypatch.setattr(builtins, "open", guard)
    monkeypatch.setattr(io, "open", guard)
    monkeypatch.setattr(pathlib.Path, "open", lambda self, *a, **k: guard(self, *a, **k))
