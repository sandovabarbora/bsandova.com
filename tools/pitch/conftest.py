import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: the full 10 000-replicate bootstrap; run with -m slow")


def pytest_collection_modifyitems(config, items):
    # a plain run skips them; any -m expression (not slow, slow) decides for itself
    if config.getoption("markexpr"):
        return
    skip = pytest.mark.skip(reason="slow, run with -m slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)


def srt(*cues: tuple) -> str:
    """An invented .srt file from (index, start s, end s, text) tuples."""
    def stamp(t: float) -> str:
        ms = round(t * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n" for i, a, b, text in cues)


@pytest.fixture(autouse=True, scope="session")
def real_outputs_untouched():
    # the tests write into temporary folders only: fail loudly if a real output of the study appears or changes
    import config as C
    paths = (C.MANIFEST, C.SONG_MARKS, C.RESULTS, C.SAMPLE, C.FORM, C.HUMAN, C.OUT / "run1", C.OUT / "run2")
    before = {p: p.stat().st_mtime_ns if p.exists() else None for p in paths}
    yield
    after = {p: p.stat().st_mtime_ns if p.exists() else None for p in paths}
    assert after == before, "a test wrote into the study's real outputs"
