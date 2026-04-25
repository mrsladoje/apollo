"""FR-2.3 — every tick persists drivers + 6 component_states + 6 forecasts.

Smaller horizon than the demo so this stays fast in CI.
"""

from __future__ import annotations

import json
import sqlite3

from sim.config import SimulationConfig
from sim.historian.connection import connect
from sim.loop import run_simulation


def test_full_row_counts_match_horizon(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=3,
        horizon_minutes=60,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    conn = sqlite3.connect(db_path)
    assert conn.execute(
        "SELECT count(*) FROM drivers WHERE run_id = ?", (run_id,)
    ).fetchone()[0] == 60
    assert conn.execute(
        "SELECT count(*) FROM component_states WHERE run_id = ?", (run_id,)
    ).fetchone()[0] == 60 * 6


def test_json_columns_round_trip(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="phoenix-dry",
        policy="fixed",
        seed=4,
        horizon_minutes=10,
        historian_path=str(db_path),
    )
    run_simulation(cfg)

    conn = connect(str(db_path))
    rows = conn.execute(
        "SELECT metrics_json FROM component_states LIMIT 5"
    ).fetchall()
    assert rows
    for row in rows:
        parsed = json.loads(row["metrics_json"])
        assert isinstance(parsed, dict)
        assert all(isinstance(k, str) for k in parsed)
