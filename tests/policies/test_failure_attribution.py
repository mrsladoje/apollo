"""FR-2.6 / §11.7 — known cascade scenario → expected upstream cause.

Two integration concerns are exercised here:

1. **Live cascade attribution.** A 600-minute stressed Dark Twin is run
   end-to-end against the real engine (PLAN-A's tuned components +
   coupling matrix). The heater obituary's attribution must point to the
   insulation panel via CSC-B (``M[heater, insulation] = 0.5`` is the
   dominant edge feeding heater).

2. **CSC-B attribution machinery.** A second test seeds the historian
   with a synthetic late-run window in which the heater is fully
   degraded *before* the nozzle fails. ``attribute_cause`` must then
   resolve the nozzle failure to the heater (CSC-B, weight 0.3),
   independent of how the live engine sequences the cascade. This keeps
   the attribution machinery covered without baking a specific
   real-engine failure ordering into the test.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

from engine.contracts import ComponentId, ComponentStatus
from sim.analytics.obituary import attribute_cause
from sim.config import SimulationConfig
from sim.drivers.composite import SIM_START_TIME
from sim.historian.connection import connect
from sim.historian.writer import HistorianWriter
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


def _seed_synthetic_window(
    db_path,
    run_id: str,
    failure_t: datetime,
    upstream_id: ComponentId,
    upstream_health: float,
    *,
    minutes: int = 30,
) -> None:
    """Write a 30-minute slice of ``component_states`` + a `runs` row so
    ``attribute_cause`` has a coherent historian to read against.

    Every component is healthy except ``upstream_id`` which is pinned at
    ``upstream_health``. The slice ends at ``failure_t`` (inclusive).
    """
    conn = connect(str(db_path))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO runs (run_id, scenario_name, policy, "
            "started_at, seed, config_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                "stressed",
                "none",
                SIM_START_TIME.isoformat(),
                42,
                json.dumps({"horizon_minutes": minutes}),
            ),
        )
        for offset in range(minutes + 1):
            t = failure_t - timedelta(minutes=minutes - offset)
            for cid in ComponentId:
                if cid is upstream_id:
                    h = upstream_health
                    status = ComponentStatus.FAILED if h < 0.1 else ComponentStatus.CRITICAL
                else:
                    h = 1.0
                    status = ComponentStatus.FUNCTIONAL
                conn.execute(
                    """INSERT INTO component_states
                       (run_id, t, component_id, health, status, metrics_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        t.isoformat(),
                        cid.value,
                        h,
                        status.value,
                        json.dumps({}),
                    ),
                )
            # Drivers row for the same timestamp keeps the ``_driver_cause``
            # branch from short-circuiting on missing data.
            conn.execute(
                """INSERT INTO drivers
                   (run_id, t, temp_C, humidity, pm25, psd_d50,
                    voltage_stability, operator_shift)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    t.isoformat(),
                    25.0,
                    0.5,
                    20.0,
                    20.0,
                    0.97,
                    "day",
                ),
            )
        conn.commit()
    finally:
        conn.close()


def test_nozzle_failure_attributes_to_heater(tmp_path):
    """The CSC-B downstream path: nozzle failure with a fully-degraded
    heater upstream must resolve to ``ComponentId.HEATER`` via the
    M[nozzle, heater] = 0.3 edge.

    We seed the historian directly so the test isolates the attribution
    machinery from the live cascade timing. The first test in this module
    already exercises end-to-end cascade attribution against the real
    engine.
    """
    db_path = tmp_path / "historian.db"
    failure_t = SIM_START_TIME + timedelta(minutes=520)
    run_id = "csc-b-attribution-fixture"

    _seed_synthetic_window(
        db_path,
        run_id,
        failure_t,
        upstream_id=ComponentId.HEATER,
        upstream_health=0.05,
    )

    cause = attribute_cause(
        ComponentId.NOZZLE, failure_t, run_id, db_path=str(db_path)
    )
    assert cause["type"] == "coupled"
    assert cause["id"] == ComponentId.HEATER
