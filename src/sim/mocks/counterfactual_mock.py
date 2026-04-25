from __future__ import annotations

from datetime import datetime
from sim.contracts import CounterfactualResult
from .historian_mock import query_historian

def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict,
) -> CounterfactualResult:
    # Get original data
    original = query_historian(run_id)
    
    # Create alternate by shifting health slightly higher after branch_t
    alternate = []
    for row in original:
        if row.t >= branch_t:
            # Pydantic models are frozen, so we use model_copy
            new_health = min(1.0, row.health + 0.1)
            alternate.append(row.model_copy(update={"health": new_health}))
        else:
            alternate.append(row)
            
    return CounterfactualResult(
        original=original,
        alternate=alternate,
        diff={
            "uptime_delta": 1.5,
            "failures_avoided": 1,
            "cost_delta": -50.0
        }
    )
