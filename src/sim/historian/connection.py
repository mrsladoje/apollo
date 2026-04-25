from __future__ import annotations

import sqlite3
import os
from pathlib import Path

def connect(db_path: str = "historian.db") -> sqlite3.Connection:
    """Connect to the SQLite historian, applying WAL mode and schema if needed."""
    exists = os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # ADR-007: WAL mode and pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    if not exists or db_path == ":memory:":
        _apply_schema(conn)
        
    return conn

def _apply_schema(conn: sqlite3.Connection):
    """Apply the schema.sql file to the database."""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
