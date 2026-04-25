"""FR-2.6 / §11.7 — known cascade scenario → expected upstream cause.

We run a stressed Dark Twin to horizon end, then call ``attribute_cause``
on the heater failure. CSC-B says heater is downstream of insulation
(coupling weight 0.5), so the dominant cause should be ``coupled``
attributed to ``insulation``. The nozzle failure should attribute to
``heater`` (CSC-B, weight 0.3) since heater is fully degraded by then.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from engine.contracts import ComponentId
from sim.analytics.obituary import attribute_cause
from sim.config import SimulationConfig
from sim.loop import run_simulation


def _failure_t(db_path, run_id, cid: ComponentId):
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        """SELECT failure_t FROM obituaries
           WHERE run_id = ? AND component_id = ?""",
        (run_id, cid.value),
    ).fetchone()
    return datetime.fromisoformat(row[0]) if row else None


def test_heater_failure_attributes_to_insulation(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=600,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    failure_t = _failure_t(db_path, run_id, ComponentId.HEATER)
    assert failure_t is not None, "heater did not fail in stressed-none-600min"
    cause = attribute_cause(
        ComponentId.HEATER, failure_t, run_id, db_path=str(db_path)
    )
    assert cause["type"] == "coupled"
    assert cause["id"] == ComponentId.INSULATION


def test_nozzle_failure_attributes_to_heater(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=600,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    failure_t = _failure_t(db_path, run_id, ComponentId.NOZZLE)
    assert failure_t is not None, "nozzle did not fail in stressed-none-600min"
    cause = attribute_cause(
        ComponentId.NOZZLE, failure_t, run_id, db_path=str(db_path)
    )
    assert cause["type"] == "coupled"
    # CSC-B path dominates over CSC-C in this scenario because heater is
    # fully degraded by t≈520, whereas blade is only partially worn.
    assert cause["id"] == ComponentId.HEATER
