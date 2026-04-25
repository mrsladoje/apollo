"""Shared fixtures for the Plan C agent test suite."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORIAN = REPO_ROOT / "historian.db"


@pytest.fixture(scope="session")
def historian_db_path() -> str:
    os.environ["HISTORIAN_DB_PATH"] = str(HISTORIAN)
    return str(HISTORIAN)


@pytest.fixture(scope="session")
def historian_conn(historian_db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(historian_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def real_citation(historian_conn: sqlite3.Connection):
    """A citation tuple known to resolve against the historian."""
    row = historian_conn.execute(
        "SELECT run_id, component_id, t FROM component_states LIMIT 1"
    ).fetchone()
    assert row is not None, "historian.db is empty — run plan_b_demo first"
    return {
        "run_id": row["run_id"],
        "component": row["component_id"],
        "timestamp": datetime.fromisoformat(row["t"]),
    }
