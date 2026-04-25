"""In-memory mock historian — PLAN-B §4.1 (Step-0 deliverable).

Seeded with 9 fake runs (3 scenarios × 3 policies) so Plan A and Plan C are
unblocked from hour 1. The real backends drop in transparently when
``HISTORIAN_BACKEND=real`` is set on the consumer side (via ``sim.api``).

Every NONE run drives at least one component to FAILED — asserted by
``test_dark_twin_kills`` against the real and mock historians.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from engine.contracts import ComponentId, ComponentStatus, status_for_health
from sim.contracts import HistorianRow

# 3x3 Grid
SCENARIOS = ("barcelona-humid", "phoenix-dry", "stressed")
POLICIES = ("none", "fixed", "ai")

_MOCK_DATA: Dict[str, List[HistorianRow]] = {}
_MOCK_MAINTENANCE: Dict[str, List[datetime]] = {}


def _generate_mock_data() -> None:
    if _MOCK_DATA:
        return

    start_time = datetime(2026, 4, 25, 8, 0, 0)

    for scenario in SCENARIOS:
        for policy in POLICIES:
            seed = 42
            rng = random.Random(f"{scenario}-{policy}-{seed}")
            run_id = f"{scenario}-{policy}-seed{seed:04d}"
            rows: List[HistorianRow] = []
            maint_events: List[datetime] = []

            healths = {cid: 1.0 for cid in ComponentId}

            base_decay = 0.0005
            if scenario == "stressed":
                base_decay = 0.0015
            elif scenario == "barcelona-humid":
                base_decay = 0.0008

            decay_modifiers = {
                ComponentId.BLADE: 1.0,
                ComponentId.MOTOR: 1.2,
                ComponentId.NOZZLE: 1.5,
                ComponentId.RESISTOR: 0.8,
                ComponentId.HEATER: 1.1,
                ComponentId.INSULATION: 0.9,
            }

            for t_step in range(601):
                t = start_time + timedelta(minutes=t_step)

                for cid in ComponentId:
                    if policy == "fixed" and t_step > 0 and t_step % 90 == 0:
                        if healths[cid] < 0.95:
                            maint_events.append(t)
                        healths[cid] = min(1.0, healths[cid] + 0.3)
                    elif policy == "ai" and healths[cid] < 0.4:
                        maint_events.append(t)
                        healths[cid] = min(1.0, healths[cid] + 0.5)

                    decay = (
                        base_decay
                        * decay_modifiers[cid]
                        * (1.0 + 0.2 * rng.random())
                    )
                    healths[cid] = max(0.0, healths[cid] - decay)

                    # Force at least one FAILED in every NONE run (§16.2 / FR-2.5).
                    if policy == "none":
                        if scenario == "stressed" and t_step > 300 and cid == ComponentId.NOZZLE:
                            healths[cid] = max(0.05, healths[cid] - 0.01)
                        if t_step > 550 and cid == ComponentId.MOTOR:
                            healths[cid] = 0.05

                    rows.append(
                        HistorianRow(
                            run_id=run_id,
                            t=t,
                            component_id=cid,
                            health=healths[cid],
                            status=status_for_health(healths[cid]),
                            metrics={"synthetic_temp_C": 20.0 + rng.random() * 5.0},
                        )
                    )

            _MOCK_DATA[run_id] = rows
            _MOCK_MAINTENANCE[run_id] = maint_events


def query_historian(
    run_id: str,
    component: Optional[ComponentId] = None,
    time_range: Optional[Tuple[datetime, datetime]] = None,
) -> List[HistorianRow]:
    _generate_mock_data()
    rows = _MOCK_DATA.get(run_id, [])

    if component:
        rows = [r for r in rows if r.component_id == component]
    if time_range:
        start, end = time_range
        rows = [r for r in rows if start <= r.t <= end]
    return rows


def compare_runs(run_ids: List[str], metric: str) -> Dict[str, float]:
    """Mirrors ``sim.historian.reader.compare_runs`` — must accept the same
    metric set so Plan C can swap mock↔real transparently.
    """
    _VALID = {"uptime_hours", "failure_count", "maintenance_count", "avg_health"}
    if metric not in _VALID:
        raise ValueError(
            f"Unknown metric {metric!r}; valid options: {sorted(_VALID)}"
        )

    _generate_mock_data()
    results: Dict[str, float] = {}

    for rid in run_ids:
        rows = _MOCK_DATA.get(rid, [])
        if not rows:
            results[rid] = 0.0
            continue

        if metric == "uptime_hours":
            # Group by t; a timestep is "up" iff all 6 components are non-FAILED.
            by_t: Dict[datetime, bool] = {}
            for r in rows:
                if r.t not in by_t:
                    by_t[r.t] = True
                if r.status == ComponentStatus.FAILED:
                    by_t[r.t] = False
            up_steps = sum(1 for v in by_t.values() if v)
            results[rid] = up_steps / 60.0  # 1-min mock ticks → hours
        elif metric == "failure_count":
            # Per the real impl: number of distinct components ever FAILED.
            failed = {r.component_id for r in rows if r.status == ComponentStatus.FAILED}
            results[rid] = float(len(failed))
        elif metric == "maintenance_count":
            results[rid] = float(len(_MOCK_MAINTENANCE.get(rid, [])))
        elif metric == "avg_health":
            results[rid] = sum(r.health for r in rows) / len(rows)

    return results


__all__ = ["query_historian", "compare_runs", "SCENARIOS", "POLICIES"]
