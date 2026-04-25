"""§10.7 — counterfactual correctness, determinism, perf.

Three properties:

1. ``no-op`` branch reproduces the original timeline within float tolerance
   (mock_engine is deterministic in driver hours so the only drift comes
   from float rounding inside Pydantic).
2. Same call twice ⇒ identical result (NFR-1, NFR-8).
3. p95 latency under the 5-s budget for a 6-h tail.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest

from engine.contracts import ComponentId
from sim.config import SimulationConfig
from sim.counterfactual.engine import run_counterfactual
from sim.drivers.composite import SIM_START_TIME
from sim.loop import run_simulation


def _setup_run(tmp_path, horizon=120):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=horizon,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)
    return run_id, db_path


def test_no_op_branch_reproduces_original(tmp_path):
    run_id, db_path = _setup_run(tmp_path, horizon=60)
    branch_t = SIM_START_TIME + timedelta(minutes=30)

    result = run_counterfactual(
        run_id, branch_t, {"action": "noop"}, db_path=str(db_path)
    )
    # alternate carries run_id + "-cf"; pair by (component_id, t).
    orig_by_key = {(r.component_id, r.t): r for r in result.original}
    for alt in result.alternate:
        key = (alt.component_id, alt.t)
        if key not in orig_by_key:
            continue
        orig = orig_by_key[key]
        assert abs(orig.health - alt.health) < 1e-6


def test_counterfactual_is_deterministic(tmp_path):
    run_id, db_path = _setup_run(tmp_path, horizon=60)
    branch_t = SIM_START_TIME + timedelta(minutes=20)
    action = {"action": "MAINTENANCE", "component_id": ComponentId.NOZZLE.value}

    a = run_counterfactual(run_id, branch_t, action, db_path=str(db_path))
    b = run_counterfactual(run_id, branch_t, action, db_path=str(db_path))
    assert a.diff == b.diff
    assert [r.health for r in a.alternate] == [r.health for r in b.alternate]


def test_counterfactual_perf_under_5s(tmp_path):
    run_id, db_path = _setup_run(tmp_path, horizon=360)
    branch_t = SIM_START_TIME + timedelta(minutes=60)
    t0 = time.perf_counter()
    run_counterfactual(
        run_id,
        branch_t,
        {"action": "MAINTENANCE", "component_id": ComponentId.NOZZLE.value},
        db_path=str(db_path),
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"counterfactual took {elapsed:.2f}s"
