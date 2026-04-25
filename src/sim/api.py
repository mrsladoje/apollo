"""Public façade for Plan B's published-language tools (PLAN-B §3.2 / §17.5).

Plan C imports from here and gets the right backend per env var:

    HISTORIAN_BACKEND   = "real" (default) | "mock"
    RETRIEVAL_BACKEND   = "mock" (default) | "lateon" | "dense"

Defaulting retrieval to ``mock`` keeps the demo flow alive in environments
where PyLate / HuggingFace are unavailable (R-7). Flipping the env var swaps
to the real index without touching consumer code (§12.5: "5-second config
flip"). ``lateon`` falls back to ``dense`` if pylate cannot load — the
caller never sees an exception, only a warning.
"""

from __future__ import annotations

import os
import warnings

# Re-export typed models so consumers can ``from sim.api import HistorianRow``
# instead of reaching into ``sim.contracts``.
from .contracts import (
    CounterfactualResult,
    HistorianRow,
    RetrievedRow,
)

if os.environ.get("HISTORIAN_BACKEND", "real").lower() == "mock":
    from .mocks.counterfactual_mock import run_counterfactual
    from .mocks.historian_mock import compare_runs, query_historian
else:
    from .counterfactual.engine import run_counterfactual  # noqa: F401
    from .historian.reader import compare_runs, query_historian  # noqa: F401


def _resolve_retrieval_backend():
    backend = os.environ.get("RETRIEVAL_BACKEND", "mock").lower()
    if backend == "lateon":
        try:
            from .retrieval.lateon import (  # type: ignore
                LateOnUnavailable,
                late_interaction_search as _real,
            )
            # Probe at resolution time so a missing index / missing pylate
            # fails early and the dense fallback takes over before Plan C
            # ever calls the search.
            import os as _os
            index_path = _os.environ.get("LATEON_INDEX_PATH", "data/lateon.index")
            if not _os.path.isdir(index_path):
                raise LateOnUnavailable(f"LateOn index missing at {index_path!r}")
            return _real
        except Exception as exc:  # noqa: BLE001 - graceful degradation
            warnings.warn(
                f"RETRIEVAL_BACKEND=lateon unavailable ({exc}); "
                "falling back to dense.",
                RuntimeWarning,
                stacklevel=2,
            )
            from .retrieval.dense_fallback import late_interaction_search as fn
            return fn
    if backend == "dense":
        from .retrieval.dense_fallback import late_interaction_search as fn
        return fn
    from .retrieval.search_mock import late_interaction_search as fn
    return fn


late_interaction_search = _resolve_retrieval_backend()


__all__ = [
    "query_historian",
    "compare_runs",
    "run_counterfactual",
    "late_interaction_search",
    "HistorianRow",
    "CounterfactualResult",
    "RetrievedRow",
]
