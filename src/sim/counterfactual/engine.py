"""Counterfactual replay engine — PLAN-B §10 (Workstream B6, ADR-012).

Branching strategy: load the nearest earlier checkpoint, deepcopy the
state, apply the alternate action, then forward via ``engine.step`` to
horizon end. Drivers are deterministic in ``(scenario, seed, t)`` so
replay does not need its own RNG state.

Determinism contract: ``run_counterfactual(run_id, branch_t, action)``
called twice → identical ``CounterfactualResult`` (NFR-1, NFR-8). The
no-op alternate at any branch reproduces the original timeline within
mock-engine float tolerance.
"""

from __future__ import annotations

import json
import pickle
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from engine import mock_engine as engine
from engine.contracts import (
    ComponentId,
    ComponentState,
    ComponentStatus,
    EngineState,
)
from sim.contracts import CounterfactualResult, HistorianRow
from sim.drivers.composite import SIM_START_TIME, CompositeDriverProvider
from sim.historian.connection import connect
from sim.historian.reader import query_historian


def _load_checkpoint(conn, run_id: str, branch_t: datetime):
    """Return ``(EngineState, checkpoint_t)`` — the nearest checkpoint at-or-before
    ``branch_t`` — or ``None`` if no checkpoint exists.
    """
    row = conn.execute(
        """SELECT t, state_blob FROM checkpoints
           WHERE run_id = ? AND t <= ?
           ORDER BY t DESC LIMIT 1""",
        (run_id, branch_t.isoformat()),
    ).fetchone()
    if not row:
        return None
    return pickle.loads(row["state_blob"]), datetime.fromisoformat(row["t"])


def _reconstruct_from_history(
    run_id: str, branch_t: datetime, db_path: str
) -> EngineState:
    """Build an EngineState from the persisted ``component_states`` row at
    the requested ``branch_t``. Used when no checkpoint covers the request.
    """
    rows = query_historian(run_id, None, (branch_t, branch_t), db_path=db_path)
    if not rows:
        raise ValueError(
            f"No state found at {branch_t.isoformat()} for run {run_id!r}; "
            "checkpoints exhausted and no historian row at that time."
        )
    components = {
        r.component_id: ComponentState(
            component_id=r.component_id,
            health=r.health,
            status=r.status,
            metrics=r.metrics,
        )
        for r in rows
    }
    return EngineState(
        components=components,
        coupling_matrix=engine.initial_state().coupling_matrix,
        rng_state=(0, run_id),
        events=(),
    )


def _replay_from_start(
    run_id: str,
    branch_t: datetime,
    scenario_name: str,
    seed: int,
    time_step_minutes: int,
    db_path: str,
) -> EngineState:
    """Rebuild state by replaying the original run when checkpoints are absent."""
    from sim.loop import _apply_maintenance, _apply_maintenance_memory

    conn = connect(db_path)
    try:
        events = conn.execute(
            """SELECT t, component_id
               FROM maintenance_events
               WHERE run_id = ? AND t <= ?
               ORDER BY t ASC""",
            (run_id, branch_t.isoformat()),
        ).fetchall()
    finally:
        conn.close()
    events_by_t: Dict[datetime, List[ComponentId]] = {}
    for row in events:
        events_by_t.setdefault(datetime.fromisoformat(row["t"]), []).append(
            ComponentId(row["component_id"])
        )

    state = engine.initial_state(scenario_name, seed)
    drivers_provider = CompositeDriverProvider()
    maintenance_clock: Dict[ComponentId, datetime] = {}
    cursor = SIM_START_TIME
    while cursor <= branch_t:
        drivers = drivers_provider.get(cursor, scenario_name, seed)
        state = engine.step(state, drivers, time_step_minutes)
        state = _apply_maintenance_memory(state, maintenance_clock, cursor)
        if cursor == branch_t:
            return state
        for cid in events_by_t.get(cursor, []):
            state = _apply_maintenance(state, cid)
            maintenance_clock[cid] = cursor
        cursor += timedelta(minutes=time_step_minutes)

    return _reconstruct_from_history(run_id, branch_t, db_path)


def _apply_alternate(state: EngineState, action: Dict[str, Any]) -> EngineState:
    if action.get("action") in ("MAINTENANCE", "swap_blade", "swap"):
        from sim.loop import _apply_maintenance

        cid = ComponentId(action["component_id"])
        return _apply_maintenance(state, cid)
    return state


def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: Dict[str, Any],
    db_path: str = "historian.db",
) -> CounterfactualResult:
    """Branch from ``branch_t`` under ``alternate_action`` and return the
    full replay alongside the original tail and a typed diff payload.

    The alternate timeline carries ``run_id + "-cf"`` so it can be
    distinguished from the original in downstream tools without polluting
    the historian.
    """
    conn = connect(db_path)
    try:
        run_info = conn.execute(
            "SELECT scenario_name, seed, config_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if run_info is None:
            raise ValueError(f"Unknown run_id {run_id!r}")
        scenario_name = run_info["scenario_name"]
        seed = run_info["seed"]
        config = json.loads(run_info["config_json"]) if run_info["config_json"] else {}
        horizon_minutes = int(config.get("horizon_minutes", 600))
        time_step_minutes = int(config.get("time_step_minutes", 1))

        cp = _load_checkpoint(conn, run_id, branch_t)
    finally:
        conn.close()

    drivers_provider = CompositeDriverProvider()
    end_time = SIM_START_TIME + timedelta(minutes=horizon_minutes)

    if cp is not None:
        from sim.loop import _apply_maintenance, _apply_maintenance_memory

        state, cp_t = cp
        # Replay forward from checkpoint to branch_t to materialize the exact
        # state at the requested branch — keeps determinism even when the
        # checkpoint cadence does not align with branch_t.
        state = deepcopy(state)
        conn = connect(db_path)
        try:
            events = conn.execute(
                """SELECT t, component_id
                   FROM maintenance_events
                   WHERE run_id = ? AND t >= ? AND t < ?
                   ORDER BY t ASC""",
                (run_id, cp_t.isoformat(), branch_t.isoformat()),
            ).fetchall()
        finally:
            conn.close()
        events_by_t: Dict[datetime, List[ComponentId]] = {}
        for row in events:
            events_by_t.setdefault(datetime.fromisoformat(row["t"]), []).append(
                ComponentId(row["component_id"])
            )
        maintenance_clock: Dict[ComponentId, datetime] = {}
        cursor = cp_t
        while cursor < branch_t:
            for cid in events_by_t.get(cursor, []):
                state = _apply_maintenance(state, cid)
                maintenance_clock[cid] = cursor
            cursor += timedelta(minutes=time_step_minutes)
            drivers = drivers_provider.get(cursor, scenario_name, seed)
            state = engine.step(state, drivers, time_step_minutes)
            state = _apply_maintenance_memory(state, maintenance_clock, cursor)
    else:
        state = _replay_from_start(
            run_id,
            branch_t,
            scenario_name,
            seed,
            time_step_minutes,
            db_path,
        )

    state = _apply_alternate(state, alternate_action)

    alt_rows: List[HistorianRow] = []
    cf_run_id = run_id + "-cf"
    t = branch_t
    while t < end_time:
        drivers = drivers_provider.get(t, scenario_name, seed)
        state = engine.step(state, drivers, time_step_minutes)
        for cid, cstate in state.components.items():
            alt_rows.append(
                HistorianRow(
                    run_id=cf_run_id,
                    t=t,
                    component_id=cid,
                    health=cstate.health,
                    status=cstate.status,
                    metrics=cstate.metrics,
                )
            )
        t += timedelta(minutes=time_step_minutes)

    original = query_historian(run_id, None, (branch_t, end_time), db_path=db_path)
    diff = _compute_diff(original, alt_rows, time_step_minutes, alternate_action)
    return CounterfactualResult(original=original, alternate=alt_rows, diff=diff)


def _compute_diff(
    original: List[HistorianRow],
    alternate: List[HistorianRow],
    time_step_minutes: int,
    alternate_action: Dict[str, Any],
) -> Dict[str, float]:
    def uptime_minutes(rows: List[HistorianRow]) -> int:
        by_t: Dict[datetime, bool] = {}
        for r in rows:
            if r.t not in by_t:
                by_t[r.t] = True
            if r.status == ComponentStatus.FAILED:
                by_t[r.t] = False
        return sum(1 for v in by_t.values() if v) * time_step_minutes

    orig_up = uptime_minutes(original)
    alt_up = uptime_minutes(alternate)

    def fail_components(rows: List[HistorianRow]) -> int:
        return len({r.component_id for r in rows if r.status == ComponentStatus.FAILED})

    orig_fails = fail_components(original)
    alt_fails = fail_components(alternate)

    return {
        # Minutes regained (positive = alternate ran longer without failures).
        "uptime_delta": float(alt_up - orig_up),
        "failures_avoided": float(orig_fails - alt_fails),
        # Signed intervention-cost delta per PLAN-B §10.4. The counterfactual
        # engine does not persist alternate maintenance events, so the action
        # payload carries the optional cost estimate for the branch.
        "cost_delta": float(
            _cost_estimate(alternate_action, alternate)
            - _cost_estimate(None, original)
        ),
    }


def _cost_estimate(
    alternate_action: Optional[Dict[str, Any]],
    rows: List[HistorianRow],
) -> float:
    failed_components = {r.component_id for r in rows if r.status == ComponentStatus.FAILED}
    action_cost = 0.0
    if alternate_action and alternate_action.get("action") not in (None, "noop", "no-op"):
        action_cost = float(alternate_action.get("cost", 1.0))
    return action_cost + 50.0 * len(failed_components)


__all__ = ["run_counterfactual"]
