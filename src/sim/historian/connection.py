from __future__ import annotations

import sqlite3

from .migrations import apply_migrations

def connect(db_path: str = "historian.db") -> sqlite3.Connection:
    """Connect to the SQLite historian, applying WAL mode and schema if needed."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # ADR-007: WAL mode and pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    apply_migrations(conn)
        
    return conn
