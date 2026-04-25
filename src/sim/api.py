import os
from .contracts import ComponentId
from .historian.reader import query_historian, compare_runs
from .counterfactual.engine import run_counterfactual
from .retrieval.search_mock import late_interaction_search # Fallback to mock for search

# If env var set to mock, use mocks
if os.environ.get("HISTORIAN_BACKEND") == "mock":
    from .mocks.historian_mock import query_historian, compare_runs
    from .mocks.counterfactual_mock import run_counterfactual
    from .mocks.late_interaction_mock import late_interaction_search

__all__ = [
    "query_historian",
    "compare_runs",
    "run_counterfactual",
    "late_interaction_search",
]
