"""Pytest console-script shim — PLAN-A §13.4 CLI compatibility.

The §13.4 verification command literally writes `--benchmark-only=false`,
but pytest-benchmark 5.x registers `--benchmark-only` as a boolean flag.
Argparse rejects the `=value` form. We expose `pytest` as a console
script (registered via `[project.scripts]` in pyproject.toml) that
pre-processes `sys.argv` before delegating to `pytest.console_main()`.
This makes the literal §13.4 command exit 0 from the venv's `pytest`
binary without touching pytest-benchmark.
"""

from __future__ import annotations

import sys


def _patch_argv() -> None:
    for i, arg in enumerate(list(sys.argv)):
        if arg == "--benchmark-only=false":
            sys.argv[i] = "--benchmark-disable"
        elif arg == "--benchmark-only=true":
            sys.argv[i] = "--benchmark-only"


def main() -> int:
    _patch_argv()
    from _pytest.config import main as pytest_main
    return pytest_main()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
