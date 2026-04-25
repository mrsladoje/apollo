import json
from datetime import datetime, timedelta
from engine.contracts import ComponentId, ComponentStatus, ROW_ORDER, COUPLING_MATRIX_M
from sim.contracts import HistorianRow
from sim.historian.reader import query_historian

OBITUARY_TEMPLATE = """\
At {failure_t} during run {run_id}, {component_pretty} crossed the failure threshold (health {health:.2f}). \
The dominant cause was {cause_phrase}. {cascade_sentence} \
The component had been in {prior_status} status since {status_change_t}. {final_sentence}\
"""

def attribute_cause(failed_id: ComponentId, failure_t: datetime, run_id: str, db_path: str = "historian.db"):
    """Attribute failure cause per PLAN-B §11.2."""
    
    # 1. Check for coupled components
    # Map ComponentId to index in COUPLING_MATRIX_M
    id_to_idx = {cid: i for i, cid in enumerate(ROW_ORDER)}
    failed_idx = id_to_idx[failed_id]
    
    suspects = []
    
    # Check upstream components in the matrix
    for upstream_id in ROW_ORDER:
        upstream_idx = id_to_idx[upstream_id]
        weight = COUPLING_MATRIX_M[failed_idx][upstream_idx]
        if weight > 0:
            # Check upstream health history (last 60 mins)
            history = query_historian(run_id, upstream_id, (failure_t - timedelta(minutes=60), failure_t), db_path=db_path)
            if history:
                min_health = min(r.health for r in history)
                # Score based on how much the upstream component contributed
                score = weight * (1.0 - min_health)
                suspects.append({
                    "type": "coupled",
                    "id": upstream_id,
                    "score": score,
                    "phrase": f"cascading degradation from {upstream_id.value}"
                })
                
    # 2. Driver-driven cause (fallback or highest score)
    # In a real model we'd check which driver was most aggressive
    suspects.append({
        "type": "driver",
        "id": "operational_wear",
        "score": 0.1, # Base score for normal wear
        "phrase": "standard operational duty cycle"
    })
    
    best_cause = max(suspects, key=lambda s: s["score"])
    return best_cause

def generate_obituary(run_id: str, component_id: ComponentId, failure_t: datetime, state, db_path: str = "historian.db") -> dict:
    """Generate a failure obituary per PLAN-B §11.3."""
    
    cause = attribute_cause(component_id, failure_t, run_id, db_path=db_path)
    comp_state = state.components[component_id]
    
    # Determine cascade name per ADR-003
    cascade_sentence = ""
    if cause["type"] == "coupled":
        upstream = cause["id"]
        if component_id == ComponentId.MOTOR and upstream == ComponentId.BLADE:
            cascade_sentence = "This corresponds to the CSC-A Recoating loop cascade."
        elif component_id in [ComponentId.NOZZLE, ComponentId.RESISTOR, ComponentId.HEATER] and upstream in [ComponentId.INSULATION, ComponentId.HEATER]:
            cascade_sentence = "This corresponds to the CSC-B Thermal-Printhead loop cascade."
        elif component_id == ComponentId.NOZZLE and upstream == ComponentId.BLADE:
            cascade_sentence = "This corresponds to the CSC-C Powder contamination loop cascade."

    # Finding status_change_t (mock logic)
    status_change_t = failure_t - timedelta(minutes=120) # placeholder
    
    narrative = OBITUARY_TEMPLATE.format(
        failure_t=failure_t.isoformat(),
        run_id=run_id,
        component_pretty=component_id.value.capitalize(),
        health=comp_state.health,
        cause_phrase=cause["phrase"],
        cascade_sentence=cascade_sentence,
        prior_status="CRITICAL",
        status_change_t=status_change_t.isoformat(),
        final_sentence="Replacement is required before operation can resume."
    )
    
    cause_component = cause["id"] if cause["type"] == "coupled" else component_id
    citations = [
        {"run_id": run_id, "component": component_id.value, "t": failure_t.isoformat()},
        {"run_id": run_id, "component": cause_component.value, "t": failure_t.isoformat()}
    ]
    
    return {
        "run_id": run_id,
        "component_id": component_id.value,
        "failure_t": failure_t.isoformat(),
        "narrative": narrative,
        "citations_json": json.dumps(citations)
    }
