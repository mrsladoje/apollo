"""Ubiquitous-language enforcement — PLAN-A §14.9 / ADR-021 §"Decision".

Walks `src/` and asserts that no Python module names a component as a
bare string literal outside the `engine.contracts` enum definition.
ComponentId is the single source of truth (PLAN.md §3.4); string drift
breaks the (run_id, component_id, t) primary key Plans B and C use.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Tuple

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

# The literal six values from `engine.contracts.ComponentId`. Hard-coded
# here on purpose so the test fails closed if someone reduces the enum.
COMPONENT_NAMES = {"blade", "motor", "nozzle", "resistor", "heater", "insulation"}

# `engine.contracts` IS the canonical declaration site. Tests are exempt
# because pytest fixtures legitimately spell out component values to
# build Drivers / EngineState payloads.
ALLOWED_FILES = {
    SRC / "engine" / "contracts.py",
}


def _walk_python_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        # Skip __pycache__ artifacts and editable-install glue files.
        if "__pycache__" in p.parts:
            continue
        yield p


def _string_literal_offenders(path: Path) -> list[Tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover -- defensive; src/ should always parse
        return []
    offenders: list[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in COMPONENT_NAMES:
                offenders.append((node.lineno, node.value))
    return offenders


def test_no_string_component_names_in_src():
    """Any string literal matching a component name outside contracts.py is a bug."""
    failures: list[str] = []
    for path in _walk_python_files(SRC):
        if path in ALLOWED_FILES:
            continue
        for line, value in _string_literal_offenders(path):
            failures.append(f"{path.relative_to(ROOT)}:{line} -> {value!r}")
    if failures:
        msg = (
            "Bare component-name string literals found outside ComponentId "
            "enum (ADR-021 §14.9 violation). Use `ComponentId.<NAME>` instead:\n  "
            + "\n  ".join(failures)
        )
        pytest.fail(msg)
