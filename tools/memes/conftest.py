import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long simulations (false-positive rate, power); run with -m slow")


def pytest_collection_modifyitems(config, items):
    # a plain run skips them; any -m expression (not slow, slow) decides for itself
    if config.getoption("markexpr"):
        return
    skip = pytest.mark.skip(reason="slow simulation, run with -m slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
