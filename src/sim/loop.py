from datetime import datetime, timedelta
from engine.contracts import (
    ComponentId,
    ComponentState,
    ComponentStatus,
    EngineState,
    status_for_health,
)
from engine import mock_engine as engine
from .config import SimulationConfig
from .historian.writer import HistorianWriter
from .drivers.composite import CompositeDriverProvider
from .policies import NonePolicy, FixedPolicy, AIPolicy
from .analytics.obituary import generate_obituary

def run_simulation(cfg: SimulationConfig) -> str:
    """Returns run_id. Writes everything to historian. (PLAN-B §7.1)"""
    
    # 1. Setup
    run_id = cfg.get_run_id()
    writer = HistorianWriter(cfg.historian_path)
    writer.log_run(run_id, cfg.scenario_name, cfg.policy, cfg.seed, cfg.model_dump())
    
    # Initialize state
    state = engine.initial_state(cfg.scenario_name, cfg.seed)
    drivers_provider = CompositeDriverProvider()
    
    # Select policy
    if cfg.policy == "none":
        policy = NonePolicy()
    elif cfg.policy == "fixed":
        policy = FixedPolicy()
    else:
        policy = AIPolicy(thresholds=cfg.thresholds, lookahead_coef=cfg.lookahead_coef)
        
    start_time = datetime(2026, 4, 25, 8, 0, 0)
    t = start_time
    end = t + timedelta(minutes=cfg.horizon_minutes)
    invocation_count = 0
    maintenance_clock: dict[ComponentId, datetime] = {}
    
    # 2. Main Loop
    while t < end:
        drivers = drivers_provider.get(t, cfg.scenario_name, cfg.seed)
        
        # Advance engine (FR-2.2)
        state = engine.step(state, drivers, cfg.time_step_minutes)
        invocation_count += 1

        # Policy decision
        action_cid = policy.decide(state, t)
        if action_cid is not None:
            # apply_maintenance (B-side helper since it's not in Plan A's mock)
            state = _apply_maintenance(state, action_cid)
            maintenance_clock[action_cid] = t
            writer.log_event(run_id, t, action_cid, "MAINTENANCE", "policy")

        state = _apply_maintenance_memory(state, maintenance_clock, t)

        # Persist (FR-2.3)
        writer.log_step(run_id, t, state, drivers)
        writer.log_forecasts(run_id, t, engine.forecast(state, horizon_min=60))

        # Failure detection & Obituary (FR-W.4)
        for cid, comp in state.components.items():
            if comp.status == ComponentStatus.FAILED and not writer.has_obituary(run_id, cid):
                obit = generate_obituary(run_id, cid, t, state, db_path=cfg.historian_path)
                writer.log_obituary(obit)

        # ADR-012: 10-minute checkpointing
        elapsed_minutes = int((t - start_time).total_seconds() / 60)
        if elapsed_minutes % 10 == 0:
            writer.log_checkpoint(run_id, t, state)

        t += timedelta(minutes=cfg.time_step_minutes)
        
    writer.finalize_run(run_id)
    writer.close()
    
    expected_invocations = cfg.horizon_minutes // cfg.time_step_minutes
    assert invocation_count == expected_invocations, f"Expected {expected_invocations}, got {invocation_count}"
    
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
    maintenance_clock: dict[ComponentId, datetime],
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
