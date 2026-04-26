"""Bounded-context import direction enforcement (ADR-021 / PLAN.md §9.8).

The allowed dependency direction is:

    apollo -> sim -> engine

The Engine context must not import Simulation or Apollo, and Simulation must
not import Apollo. This keeps the published-language seams load-bearing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                found.append((node.lineno, node.module))
    return found


def _python_files(path: Path) -> list[Path]:
    return [
        candidate
        for candidate in path.rglob("*.py")
        if "__pycache__" not in candidate.parts
    ]


@pytest.mark.parametrize(
    ("context", "forbidden_prefixes"),
    [
        (SRC / "engine", ("sim", "apollo")),
        (SRC / "sim", ("apollo",)),
    ],
)
def test_context_imports_only_flow_downstream(
    context: Path,
    forbidden_prefixes: tuple[str, ...],
):
    failures: list[str] = []
    for path in _python_files(context):
        for line, module in _imports(path):
            if module.split(".")[0] in forbidden_prefixes:
                failures.append(f"{path.relative_to(ROOT)}:{line} imports {module!r}")

    if failures:
        pytest.fail(
            "Forbidden bounded-context imports found. Import direction must be "
            "apollo -> sim -> engine:\n  " + "\n  ".join(failures)
        )
