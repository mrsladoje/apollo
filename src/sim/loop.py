from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

from engine import mock_engine as engine
from engine.contracts import (
    ComponentId,
    ComponentState,
    ComponentStatus,
    EngineState,
    status_for_health,
)

from .analytics.obituary import generate_obituary
from .config import SimulationConfig
from .drivers.composite import CompositeDriverProvider
from .historian.writer import HistorianWriter
from .policies import AIPolicy, FixedPolicy, NonePolicy

# Wall-clock anchor for the entire data plane. Plan B owns the cursor; Plan
# A's ``Drivers`` does not carry ``t`` (PLAN-B §3.1 note).
SIM_START_TIME = datetime(2026, 4, 25, 8, 0, 0)

# ADR-012: checkpoint cadence in simulated minutes. Counterfactual replay
# loads the nearest earlier checkpoint and forwards.
CHECKPOINT_INTERVAL_MIN = 10


def run_simulation(cfg: SimulationConfig) -> str:
    """Drive ``engine.step`` once per tick, persist everything. (PLAN-B §7.1).

    Returns the deterministic ``run_id`` (§3.3). The caller's reproducibility
    key is ``(scenario_name, policy, seed, config_json)`` — same key ⇒ byte-
    identical historian (NFR-8).
    """
    # NFR-8: dump the full config (including thresholds + lookahead_coef +
    # time_step_minutes + horizon_minutes) into ``config_json`` so the run is
    # self-describing and ``compare_runs`` can introspect time_step_minutes
    # without reaching back into Python.
    config_dump = cfg.model_dump(mode="json")

    run_id = cfg.get_run_id()
    writer = HistorianWriter(cfg.historian_path)
    try:
        writer.log_run(
            run_id,
            cfg.scenario_name,
            cfg.policy,
            cfg.seed,
            config_dump,
        )

        state = engine.initial_state(cfg.scenario_name, cfg.seed)
        drivers_provider = CompositeDriverProvider()

        if cfg.policy == "none":
            policy = NonePolicy()
        elif cfg.policy == "fixed":
            policy = FixedPolicy()
        else:
            policy = AIPolicy(
                thresholds=cfg.thresholds,
                lookahead_coef=cfg.lookahead_coef,
            )

        t = SIM_START_TIME
        end = t + timedelta(minutes=cfg.horizon_minutes)
        invocation_count = 0
        maintenance_clock: Dict[ComponentId, datetime] = {}

        while t < end:
            drivers = drivers_provider.get(t, cfg.scenario_name, cfg.seed)

            # Advance engine (FR-2.2)
            state = engine.step(state, drivers, cfg.time_step_minutes)
            invocation_count += 1

            action_cid = policy.decide(state, t)
            if action_cid is not None:
                # ``engine.apply_maintenance`` is not on Plan A's mock contract
                # yet (PLAN-A §4 mock is decay-only). We apply the boost on
                # the B side and ``_apply_maintenance_memory`` below smooths
                # the boost over subsequent ticks until Plan A ships the
                # real surface.
                state = _apply_maintenance(state, action_cid)
                maintenance_clock[action_cid] = t
                writer.log_event(run_id, t, action_cid, "MAINTENANCE", "policy")

            state = _apply_maintenance_memory(state, maintenance_clock, t)

            # Persist (FR-2.3)
            writer.log_step(run_id, t, state, drivers)
            writer.log_forecasts(run_id, t, engine.forecast(state, horizon_min=60))

            # FR-W.4: synchronous obituary on first FAILED transition
            for cid, comp in state.components.items():
                if (
                    comp.status == ComponentStatus.FAILED
                    and not writer.has_obituary(run_id, cid)
                ):
                    obit = generate_obituary(
                        run_id, cid, t, state, db_path=cfg.historian_path
                    )
                    writer.log_obituary(obit)

            # ADR-012: checkpoint at SIM_START + 0, 10, 20, ... minutes,
            # robust to any ``time_step_minutes`` (the previous ``%10`` test
            # silently dropped checkpoints whenever the step did not divide
            # 10 evenly, e.g. step=3).
            elapsed_minutes = int(
                round((t - SIM_START_TIME).total_seconds() / 60.0)
            )
            tick_window = max(cfg.time_step_minutes, 1)
            if elapsed_minutes % CHECKPOINT_INTERVAL_MIN < tick_window:
                writer.log_checkpoint(run_id, t, state)

            t += timedelta(minutes=cfg.time_step_minutes)

        writer.finalize_run(run_id)

        expected_invocations = cfg.horizon_minutes // cfg.time_step_minutes
        if invocation_count != expected_invocations:
            raise AssertionError(
                f"FR-2.2 invocation count mismatch: "
                f"expected {expected_invocations}, got {invocation_count}"
            )
    finally:
        writer.close()

    return run_id

def _apply_maintenance(state: EngineState, component_id: ComponentId) -> EngineState:
    """Helper to 'reset' health in the state. 
    Note: Plan A's mock_engine will overwrite this in the next step() call 
    because it's a function of drivers.hours. This is a known limitation of the mock.
    """
    new_components = dict(state.components)
    comp = new_components[component_id]
    
    # Pydantic models are frozen, so we use model_copy
    new_comp = comp.model_copy(update={"health": 1.0, "status": ComponentStatus.FUNCTIONAL})
    new_components[component_id] = new_comp
    
    return state.model_copy(update={"components": new_components})

def _apply_maintenance_memory(
    state: EngineState,
    maintenance_clock: Dict[ComponentId, datetime],
    t: datetime,
) -> EngineState:
    """Keep Plan B policy effects visible while Plan A is still mocked."""
    if not maintenance_clock:
        return state

    new_components = dict(state.components)
    for cid, last_t in maintenance_clock.items():
        elapsed_min = max(0.0, (t - last_t).total_seconds() / 60.0)
        maintained_health = max(0.0, 1.0 - elapsed_min / 600.0)
        current = new_components[cid]
        if maintained_health > current.health:
            metrics = dict(current.metrics)
            metrics["maintenance_boost"] = round(maintained_health - current.health, 6)
            new_components[cid] = ComponentState(
                component_id=cid,
                health=maintained_health,
                status=status_for_health(maintained_health),
                metrics=metrics,
            )

    return state.model_copy(update={"components": new_components})
