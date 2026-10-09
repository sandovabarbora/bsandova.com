import pytest

from status_check import judge


@pytest.mark.parametrize("ok, age_h, cadence_h, state", [
    (True, 3, 24, "ok"),
    (None, 3, 24, "ok"),       # no workflow to ask: the data age alone decides
    (True, 24, 24, "late"),    # the boundary is late, not ok
    (True, 47.9, 24, "late"),
    (True, 48, 24, "stale"),
    (False, 1, 24, "failed"),  # a failed run is failed even with fresh data
    (False, None, None, "failed"),
    (True, None, 24, "ok"),    # data without a date cannot be late
    (True, 500, None, "ok"),   # nor can a job without a cadence
])
def test_judge(ok, age_h, cadence_h, state):
    assert judge(ok, age_h, cadence_h) == state
