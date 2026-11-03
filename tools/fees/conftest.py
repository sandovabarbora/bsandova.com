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
