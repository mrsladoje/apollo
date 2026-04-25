import random
from datetime import datetime, timedelta
from engine.contracts import ComponentId, ComponentStatus, status_for_health
from sim.contracts import HistorianRow

# 3x3 Grid
SCENARIOS = ["barcelona-humid", "phoenix-dry", "stressed"]
POLICIES = ["none", "fixed", "ai"]

_MOCK_DATA: dict[str, list[HistorianRow]] = {}

def _generate_mock_data():
    if _MOCK_DATA:
        return

    start_time = datetime(2026, 4, 25, 8, 0, 0)
    
    for scenario in SCENARIOS:
        for policy in POLICIES:
            seed = 42
            random.seed(f"{scenario}-{policy}-{seed}")
            run_id = f"{scenario}-{policy}-seed{seed:04d}"
            rows = []
            
            # Initial health
            healths = {cid: 1.0 for cid in ComponentId}
            
            # Decay rates based on scenario
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
                    # Maintenance
                    if policy == "fixed" and t_step > 0 and t_step % 90 == 0:
                        healths[cid] = min(1.0, healths[cid] + 0.3)
                    elif policy == "ai" and healths[cid] < 0.4:
                        healths[cid] = min(1.0, healths[cid] + 0.5)
                        
                    # Decay
                    decay = base_decay * decay_modifiers[cid] * (1.0 + 0.2 * random.random())
                    healths[cid] = max(0.0, healths[cid] - decay)
                    
                    # Force failure in NONE run if it's stressed or late enough
                    if policy == "none":
                        if scenario == "stressed" and t_step > 300:
                            if cid == ComponentId.NOZZLE:
                                healths[cid] = max(0.05, healths[cid] - 0.01) # Rapid fail
                        if t_step > 550 and cid == ComponentId.MOTOR:
                             healths[cid] = 0.05 # Failure
                             
                    status = status_for_health(healths[cid])
                    
                    rows.append(HistorianRow(
                        run_id=run_id,
                        t=t,
                        component_id=cid,
                        health=healths[cid],
                        status=status,
                        metrics={"temp": 20.0 + random.random() * 5.0} # Placeholder
                    ))
            
            _MOCK_DATA[run_id] = rows

def query_historian(
    run_id: str,
    component: ComponentId | None = None,
    time_range: tuple[datetime, datetime] | None = None,
) -> list[HistorianRow]:
    _generate_mock_data()
    rows = _MOCK_DATA.get(run_id, [])
    
    if component:
        rows = [r for r in rows if r.component_id == component]
        
    if time_range:
        start, end = time_range
        rows = [r for r in rows if start <= r.t <= end]
        
    return rows

def compare_runs(run_ids: list[str], metric: str) -> dict[str, float]:
    _generate_mock_data()
    results = {}
    for rid in run_ids:
        rows = _MOCK_DATA.get(rid, [])
        if not rows:
            results[rid] = 0.0
            continue
            
        if metric == "uptime_hours":
            # count functional steps
            functional_steps = len([r for r in rows if r.status != ComponentStatus.FAILED]) / 6.0 # 6 components per step
            results[rid] = functional_steps / 60.0 # minutes to hours
        elif metric == "failure_count":
            # count steps where any component is FAILED
            failed_steps = len(set(r.t for r in rows if r.status == ComponentStatus.FAILED))
            results[rid] = float(failed_steps)
        elif metric == "avg_health":
            results[rid] = sum(r.health for r in rows) / len(rows)
        else:
            results[rid] = 0.0
            
    return results
