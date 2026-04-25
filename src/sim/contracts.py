"""Frozen integration contracts for the Simulation & History bounded context.

PLAN-B §3.2 — published language: ``query_historian`` / ``compare_runs`` /
``run_counterfactual`` / ``late_interaction_search`` and their typed return
models. Plan C wraps these as Claude Agent SDK tools.

Frozen at hour zero. Any change requires a written ADR amendment.
"""

from __future__ import annotations

from datetime import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from engine.contracts import ComponentId, ComponentStatus


class HistorianRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    t: datetime
    component_id: ComponentId
    health: float
    status: ComponentStatus
    metrics: Dict[str, Any]


def query_historian(
    run_id: str,
    component: Optional[ComponentId] = None,
    time_range: Optional[Tuple[datetime, datetime]] = None,
) -> List[HistorianRow]:
    """Query the historian for a specific run and component."""
    if os.environ.get("HISTORIAN_BACKEND", "real").lower() == "mock":
        from sim.mocks.historian_mock import query_historian as _query_historian
    else:
        from sim.historian.reader import query_historian as _query_historian

    return _query_historian(run_id, component, time_range)


def compare_runs(run_ids: List[str], metric: str) -> Dict[str, float]:
    """metric ∈ {'uptime_hours', 'failure_count', 'maintenance_count', 'avg_health'}.

    Returns ``{run_id: float, ...}``. Plan C charts this directly.
    """
    if os.environ.get("HISTORIAN_BACKEND", "real").lower() == "mock":
        from sim.mocks.historian_mock import compare_runs as _compare_runs
    else:
        from sim.historian.reader import compare_runs as _compare_runs

    return _compare_runs(run_ids, metric)


class CounterfactualResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    original: List[HistorianRow]
    alternate: List[HistorianRow]
    diff: Dict[str, float]


def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: Dict[str, Any],
) -> CounterfactualResult:
    """Run a counterfactual simulation branching from a specific point in time."""
    if os.environ.get("HISTORIAN_BACKEND", "real").lower() == "mock":
        from sim.mocks.counterfactual_mock import run_counterfactual as _run_counterfactual
    else:
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
    run_id: Optional[str] = None,
    top_k: int = 10,
) -> List[RetrievedRow]:
    """Perform a late-interaction semantic search over the historian data."""
    backend = os.environ.get("RETRIEVAL_BACKEND", "lateon").lower()

    if backend == "mock":
        from sim.retrieval.search_mock import late_interaction_search as _search

        return _search(query, run_id, top_k)

    if backend == "dense":
        from sim.retrieval.dense_fallback import late_interaction_search as _search

        return _search(query, run_id, top_k)

    from sim.retrieval.lateon import late_interaction_search as _search

    return _search(query, run_id, top_k)


__all__ = [
    "HistorianRow",
    "CounterfactualResult",
    "RetrievedRow",
    "query_historian",
    "compare_runs",
    "run_counterfactual",
    "late_interaction_search",
]
