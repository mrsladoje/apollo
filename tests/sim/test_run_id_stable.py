"""§7.2 — re-running the same ``(scenario, policy, seed)`` rolls forward
under a transaction; row counts stay stable.
"""

from __future__ import annotations

import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def test_rerun_does_not_grow_rows(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="fixed",
        seed=42,
        horizon_minutes=60,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    conn = sqlite3.connect(db_path)
    first_states = conn.execute(
        "SELECT count(*) FROM component_states WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    first_drivers = conn.execute(
        "SELECT count(*) FROM drivers WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    conn.close()

    run_simulation(cfg)
    conn = sqlite3.connect(db_path)
    second_states = conn.execute(
        "SELECT count(*) FROM component_states WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    second_drivers = conn.execute(
        "SELECT count(*) FROM drivers WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    runs = conn.execute(
        "SELECT count(*) FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()[0]

    assert first_states == second_states
    assert first_drivers == second_drivers
    assert runs == 1
