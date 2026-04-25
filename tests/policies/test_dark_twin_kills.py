"""FR-2.5 / §16.2 — every NONE (Dark Twin) run drives ≥1 component to FAILED.

Run length must be enough to exhaust nozzle/heater under the mock decay
curve (PLAN-A §4.1 puts heater FAILED at t≈480 and nozzle FAILED at t≈520).
"""

from __future__ import annotations

import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def _failed_components(db_path, run_id):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT DISTINCT component_id FROM component_states
           WHERE run_id = ? AND status = 'FAILED'""",
        (run_id,),
    ).fetchall()
    return {r[0] for r in rows}


def test_every_dark_twin_run_kills_at_least_one_component(tmp_path):
    db_path = tmp_path / "historian.db"
    for scenario in ("barcelona-humid", "phoenix-dry", "stressed"):
        cfg = SimulationConfig(
            scenario_name=scenario,
            policy="none",
            seed=42,
            horizon_minutes=600,
            historian_path=str(db_path),
        )
        run_id = run_simulation(cfg)
        failed = _failed_components(db_path, run_id)
        assert failed, f"{run_id}: NONE policy did not kill any component"
