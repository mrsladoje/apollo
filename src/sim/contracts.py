from datetime import datetime
from pydantic import BaseModel, ConfigDict
from engine.contracts import ComponentId, ComponentStatus

class HistorianRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    t: datetime
    component_id: ComponentId
    health: float
    status: ComponentStatus
    metrics: dict

def query_historian(
    run_id: str,
    component: ComponentId | None = None,
    time_range: tuple[datetime, datetime] | None = None,
) -> list[HistorianRow]:
    """Query the historian for a specific run and component."""
    from sim.historian.reader import query_historian as _query_historian

    return _query_historian(run_id, component, time_range)

def compare_runs(run_ids: list[str], metric: str) -> dict[str, float]:
    """metric ∈ {'uptime_hours', 'failure_count', 'maintenance_count', 'avg_health'}.
    Returns {run_id: float, ...}. Plan C charts this directly."""
    from sim.historian.reader import compare_runs as _compare_runs

    return _compare_runs(run_ids, metric)

class CounterfactualResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    original: list[HistorianRow]
    alternate: list[HistorianRow]
    diff: dict   # {"uptime_delta": float, "failures_avoided": int, "cost_delta": float}

def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict,    # e.g. {"action": "swap_blade", "component_id": "blade"}
) -> CounterfactualResult:
    """Run a counterfactual simulation branching from a specific point in time."""
    from sim.counterfactual.engine import run_counterfactual as _run_counterfactual

    return _run_counterfactual(run_id, branch_t, alternate_action)

class RetrievedRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    component: ComponentId
    t: datetime
    score: float
    snippet: str

def late_interaction_search(
    query: str,
    run_id: str | None = None,
    top_k: int = 10,
) -> list[RetrievedRow]:
    """Perform a late-interaction semantic search over the historian data."""
    from sim.retrieval.search_mock import late_interaction_search as _late_interaction_search

    return _late_interaction_search(query, run_id, top_k)
