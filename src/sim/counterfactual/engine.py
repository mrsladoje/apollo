import pickle
import json
from datetime import datetime, timedelta
from engine.contracts import EngineState, ComponentId, ComponentStatus
from engine import mock_engine as engine
from sim.contracts import CounterfactualResult, HistorianRow
from sim.historian.reader import query_historian
from sim.historian.connection import connect
from sim.drivers.composite import CompositeDriverProvider

def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict, # e.g. {"action": "MAINTENANCE", "component_id": "blade"}
    db_path: str = "historian.db"
) -> CounterfactualResult:
    """Run a counterfactual simulation branching from branch_t. (PLAN-B §10.3)"""
    
    # 1. Load the state at branch_t
    conn = connect(db_path)
    res = conn.execute(
        "SELECT state_blob FROM checkpoints WHERE run_id = ? AND t = ?",
        (run_id, branch_t.isoformat())
    ).fetchone()
    
    if res:
        state = pickle.loads(res["state_blob"])
    else:
        # Fallback: find nearest checkpoint or replay (for simplicity, we'll just query the history)
        # and reconstruct EngineState. 
        # But for the real thing, replaying is safer for RNG.
        # Here we'll just look for any row at branch_t and reconstruct.
        rows = query_historian(run_id, None, (branch_t, branch_t), db_path=db_path)
        if not rows:
            # Replay from t=0 would be here. For mock, we'll just error or use initial.
            raise ValueError(f"No state found at {branch_t} for run {run_id}")
            
        # Reconstruct state from HistorianRows
        components = {}
        for r in rows:
            from engine.contracts import ComponentState
            components[r.component_id] = ComponentState(
                component_id=r.component_id,
                health=r.health,
                status=r.status,
                metrics=r.metrics
            )
        state = EngineState(
            components=components,
            coupling_matrix=engine.initial_state().coupling_matrix, # placeholder
            rng_state=(0, run_id) # placeholder
        )

    # 2. Apply alternate action
    if alternate_action.get("action") == "MAINTENANCE":
        from sim.loop import _apply_maintenance
        cid = ComponentId(alternate_action["component_id"])
        state = _apply_maintenance(state, cid)

    # 3. Replay from branch_t to end
    # Get run config
    run_info = conn.execute("SELECT scenario_name, seed, config_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    scenario_name = run_info["scenario_name"]
    seed = run_info["seed"]
    config = json.loads(run_info["config_json"])
    horizon_minutes = config.get("horizon_minutes", 600)
    time_step_minutes = config.get("time_step_minutes", 1)
    conn.close()
    
    drivers_provider = CompositeDriverProvider()
    
    start_time = datetime(2026, 4, 25, 8, 0, 0)
    end_time = start_time + timedelta(minutes=horizon_minutes)
    
    alt_rows = []
    t = branch_t
    while t < end_time:
        drivers = drivers_provider.get(t, scenario_name, seed)
        state = engine.step(state, drivers, time_step_minutes)
        
        for cid, cstate in state.components.items():
            alt_rows.append(HistorianRow(
                run_id=run_id + "-cf",
                t=t,
                component_id=cid,
                health=cstate.health,
                status=cstate.status,
                metrics=cstate.metrics
            ))
            
        t += timedelta(minutes=time_step_minutes)

    # 4. Get original rows for comparison
    original = query_historian(run_id, None, (branch_t, end_time), db_path=db_path)
    
    # 5. Compute diff
    diff = _compute_diff(original, alt_rows)
    
    return CounterfactualResult(original=original, alternate=alt_rows, diff=diff)

def _compute_diff(original: list[HistorianRow], alternate: list[HistorianRow]) -> dict:
    def get_uptime(rows):
        # Unique timestamps where no component is FAILED
        t_steps = {}
        for r in rows:
            if r.t not in t_steps: t_steps[r.t] = True
            if r.status == ComponentStatus.FAILED: t_steps[r.t] = False
        return sum(1 for v in t_steps.values() if v)

    orig_uptime = get_uptime(original)
    alt_uptime = get_uptime(alternate)
    
    orig_fails = len(set((r.run_id, r.component_id) for r in original if r.status == ComponentStatus.FAILED))
    alt_fails = len(set((r.run_id, r.component_id) for r in alternate if r.status == ComponentStatus.FAILED))
    
    return {
        "uptime_delta": float(alt_uptime - orig_uptime),
        "failures_avoided": orig_fails - alt_fails,
        "cost_delta": float((alt_uptime - orig_uptime) * 10.0) # Dummy cost
    }
