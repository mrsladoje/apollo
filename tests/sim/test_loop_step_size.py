"""FR-2.1 + FR-2.2 coverage: loop step size honors ``time_step_minutes``.

PLAN-B §7.3: ``time_step=5`` over a 600-min horizon must produce 120 ticks
and exactly ``120 * 6 = 720`` component_states rows.
"""

from __future__ import annotations

import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def test_loop_step_minutes_drives_invocation_count(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="phoenix-dry",
        policy="none",
        seed=1,
        horizon_minutes=600,
        time_step_minutes=5,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    conn = sqlite3.connect(db_path)
    n_drivers = conn.execute(
        "SELECT count(*) FROM drivers WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    n_states = conn.execute(
        "SELECT count(*) FROM component_states WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert n_drivers == 120
    assert n_states == 120 * 6


def test_loop_invocation_count_matches_horizon_over_step(tmp_path):
    """FR-2.2: invocation count == horizon // step."""
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="barcelona-humid",
        policy="none",
        seed=2,
        horizon_minutes=300,
        time_step_minutes=3,
        historian_path=str(db_path),
    )
    run_simulation(cfg)
    conn = sqlite3.connect(db_path)
    n_drivers = conn.execute("SELECT count(*) FROM drivers").fetchone()[0]
    assert n_drivers == 100
