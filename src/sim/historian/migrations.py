from __future__ import annotations

import sqlite3
from pathlib import Path


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply idempotent historian schema migrations.

    PLAN-B keeps the SQLite schema as executable DDL with ``IF NOT EXISTS``
    guards, so re-running the schema is the migration mechanism for the demo
    scope. Existing historian files therefore pick up newly-added tables such
    as ``checkpoints`` without manual deletion.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()


__all__ = ["apply_migrations"]
