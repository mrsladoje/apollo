"""§5.3 — ``query_historian`` must use the composite
``idx_component_states_run_comp_t`` index (no full-table scan).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from engine.contracts import ComponentId
from sim.config import SimulationConfig
from sim.historian.connection import connect
from sim.loop import run_simulation


def test_query_plan_uses_composite_index(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="phoenix-dry",
        policy="none",
        seed=11,
        horizon_minutes=60,
        historian_path=str(db_path),
    )
    run_simulation(cfg)

    conn = connect(str(db_path))
    plan = conn.execute(
        """EXPLAIN QUERY PLAN
           SELECT * FROM component_states
           WHERE run_id = ? AND component_id = ? AND t BETWEEN ? AND ?""",
        (
            "phoenix-dry-none-seed0011",
            ComponentId.NOZZLE.value,
            datetime(2026, 4, 25, 8, 10, 0).isoformat(),
            datetime(2026, 4, 25, 8, 50, 0).isoformat(),
        ),
    ).fetchall()
    plan_text = " ".join(str(row[-1]) for row in plan).lower()
    # SQLite picks the primary key (which is the same composite key) or the
    # explicit index. Either is index-backed; what matters is that no full
    # ``SCAN component_states`` shows up without USING INDEX/PK.
    assert "scan component_states" not in plan_text, plan_text
    assert "index" in plan_text or "primary key" in plan_text, plan_text
