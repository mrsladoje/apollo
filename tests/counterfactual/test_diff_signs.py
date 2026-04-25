from __future__ import annotations

from datetime import datetime

from engine.contracts import ComponentId, ComponentStatus
from sim.contracts import HistorianRow
from sim.counterfactual.engine import _compute_diff


def _row(run_id: str, status: ComponentStatus) -> HistorianRow:
    return HistorianRow(
        run_id=run_id,
        t=datetime(2026, 4, 25, 8, 0, 0),
        component_id=ComponentId.NOZZLE,
        health=0.05 if status == ComponentStatus.FAILED else 0.9,
        status=status,
        metrics={},
    )


def test_better_alternate_has_positive_uptime_and_failures_avoided():
    diff = _compute_diff(
        [_row("orig", ComponentStatus.FAILED)],
        [_row("alt", ComponentStatus.FUNCTIONAL)],
        time_step_minutes=1,
        alternate_action={"action": "MAINTENANCE", "component_id": "nozzle", "cost": 1.0},
    )
    assert diff["uptime_delta"] > 0
    assert diff["failures_avoided"] > 0
    assert diff["cost_delta"] < 0


def test_worse_alternate_has_negative_uptime_and_failures_avoided():
    diff = _compute_diff(
        [_row("orig", ComponentStatus.FUNCTIONAL)],
        [_row("alt", ComponentStatus.FAILED)],
        time_step_minutes=1,
        alternate_action={"action": "noop"},
    )
    assert diff["uptime_delta"] < 0
    assert diff["failures_avoided"] < 0
    assert diff["cost_delta"] > 0
