"""FR-2.4 / §8.3 — three scenarios × three policies = nine runs.

Uses a short horizon so the test stays under CI budget. The acceptance
on the demo path is the same property held over the full 600-min grid.
"""

from __future__ import annotations

import sqlite3

from sim.build_grid import build_grid as _build_grid_real  # ensures import
from sim.config import SimulationConfig
from sim.loop import run_simulation


SCENARIOS = ("barcelona-humid", "phoenix-dry", "stressed")
POLICIES = ("none", "fixed", "ai")


def test_3x3_grid_creates_nine_runs(tmp_path):
    db_path = tmp_path / "historian.db"
    for scenario in SCENARIOS:
        for policy in POLICIES:
            run_simulation(
                SimulationConfig(
                    scenario_name=scenario,
                    policy=policy,
                    seed=42,
                    horizon_minutes=60,
                    historian_path=str(db_path),
                )
            )

    conn = sqlite3.connect(db_path)
    run_ids = {row[0] for row in conn.execute("SELECT run_id FROM runs")}
    assert len(run_ids) == 9
    for scenario in SCENARIOS:
        for policy in POLICIES:
            assert f"{scenario}-{policy}-seed0042" in run_ids
