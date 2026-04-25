"""§8.4 / §16.2 — for the same scenario+seed, AI uptime ≥ FIXED ≥ NONE
on average health (a proxy for uptime under the mock decay curve).

The mock engine is a pure function of ``drivers.hours``, so naive uptime
diverges only via maintenance boosts that the loop's ``_apply_maintenance``
helper layers on. We compare AVG health here to keep the test resilient
to the mock's idempotent decay while still asserting policy ordering.
"""

from __future__ import annotations

import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def _avg_health(db_path, run_id):
    conn = sqlite3.connect(db_path)
    return conn.execute(
        "SELECT avg(health) FROM component_states WHERE run_id = ?",
        (run_id,),
    ).fetchone()[0]


def test_ai_dominates_fixed_dominates_none(tmp_path):
    db_path = tmp_path / "historian.db"
    run_ids = {}
    for policy in ("none", "fixed", "ai"):
        cfg = SimulationConfig(
            scenario_name="stressed",
            policy=policy,
            seed=42,
            horizon_minutes=240,
            historian_path=str(db_path),
        )
        run_ids[policy] = run_simulation(cfg)

    none_h = _avg_health(db_path, run_ids["none"])
    fixed_h = _avg_health(db_path, run_ids["fixed"])
    ai_h = _avg_health(db_path, run_ids["ai"])

    assert ai_h >= fixed_h, f"AI {ai_h:.4f} should dominate FIXED {fixed_h:.4f}"
    assert fixed_h >= none_h, f"FIXED {fixed_h:.4f} should dominate NONE {none_h:.4f}"
