"""Public façade for Plan B's published-language tools (PLAN-B §3.2 / §17.5).

``sim.contracts`` is the frozen contract surface. This module intentionally
re-exports it so Plan C can import either path without splitting backend
semantics. Backend selection happens at call time through:

    HISTORIAN_BACKEND   = "real" (default) | "mock"
    RETRIEVAL_BACKEND   = "lateon" (default) | "dense" | "mock"
"""

from .contracts import (
    CounterfactualResult,
    HistorianRow,
    RetrievedRow,
    compare_runs,
    late_interaction_search,
    query_historian,
    run_counterfactual,
)


__all__ = [
    "query_historian",
    "compare_runs",
    "run_counterfactual",
    "late_interaction_search",
    "HistorianRow",
    "CounterfactualResult",
    "RetrievedRow",
]
