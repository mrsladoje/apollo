"""Top-level pytest configuration.

Adds opt-in flags for slow suites that would otherwise dominate every
local ``pytest`` run.

Currently gated:
  * ``ga`` — PLAN-B §9 GA / Optuna fitness suite. A single tiny
    invocation runs ~108 stressed-scenario simulations end-to-end and
    takes ~15 minutes on M3 Max even with the trimmed test fixture
    (``POP_SIZE=6``, ``N_GEN=3``). Skipped by default; pass ``--ga`` to
    include the suite (``make train-ga`` covers the production path).

Add new gates here when a suite costs > 60 s on the dev box.
"""

from __future__ import annotations

import pytest


_OPT_IN_GATES = {
    # marker name -> (CLI flag, skip reason shown in pytest -rs)
    "ga": (
        "--ga",
        "GA suite is opt-in (~15 min); pass --ga to run "
        "(or `make train-ga` for the production tuning path).",
    ),
}


def pytest_addoption(parser):
    for marker, (flag, _) in _OPT_IN_GATES.items():
        parser.addoption(
            flag,
            action="store_true",
            default=False,
            help=f"include the @pytest.mark.{marker} suite (off by default)",
        )


def pytest_configure(config):
    for marker, (flag, _) in _OPT_IN_GATES.items():
        config.addinivalue_line(
            "markers",
            f"{marker}: opt-in slow test, requires {flag}",
        )


def pytest_collection_modifyitems(config, items):
    for marker, (flag, reason) in _OPT_IN_GATES.items():
        if config.getoption(flag):
            continue
        skip = pytest.mark.skip(reason=reason)
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)
