"""Tool registry — five typed Pydantic-input/Pydantic-output callables.

Per PLAN-C §6.2 / ADR-009: the agent has exactly five tools. Four wrap Plan B's
``sim.contracts`` callables; the fifth (``plot_component_history``) is Plan C
native and emits a ``ChartSpec`` the React frontend renders inline.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field

from engine.contracts import ComponentId
from ..contracts import ChartSpec


class ToolError(RuntimeError):
    """Raised when a tool's input is structurally invalid."""


# -----------------------------------------------------------------------------
# Pydantic input schemas (one per tool)
# -----------------------------------------------------------------------------

class QueryHistorianArgs(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    component: ComponentId
    time_range: tuple[datetime, datetime]


class LateInteractionSearchArgs(BaseModel):
    model_config = ConfigDict(frozen=True)
    query: str
    run_id: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)


class CompareRunsArgs(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_ids: list[str] = Field(min_length=1)
    metric: str


class RunCounterfactualArgs(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    branch_t: datetime
    alternate_action: dict[str, Any]


class PlotComponentHistoryArgs(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    component: ComponentId


class ToolSchema(BaseModel):
    """Description surface used by the agent loop / tests / CI guard."""

    model_config = ConfigDict(frozen=True)
    name: str
    description: str
    args_model: str  # qualified name of the Pydantic args model


# -----------------------------------------------------------------------------
# Tool implementations
# -----------------------------------------------------------------------------

def _backend() -> str:
    if os.environ.get("USE_MOCKS", "").lower() in {"1", "true", "yes", "on", "mock"}:
        return "mock"
    return os.environ.get("APOLLO_TOOLS_BACKEND", "auto").lower()


def _call_query_historian(args: QueryHistorianArgs):
    backend = _backend()
    if backend == "mock":
        from apollo.mocks.tool_mocks import query_historian as fn
        return [
            r.model_dump(mode="json")
            for r in fn(args.run_id, args.component, args.time_range)
        ]
    # default: route through sim.contracts (which itself honors HISTORIAN_BACKEND)
    from sim.contracts import query_historian as fn
    return [r.model_dump(mode="json") for r in fn(args.run_id, args.component, args.time_range)]


def _call_late_interaction_search(args: LateInteractionSearchArgs):
    backend = _backend()
    if backend == "mock":
        from apollo.mocks.tool_mocks import late_interaction_search as fn
        return [
            r.model_dump(mode="json")
            for r in fn(args.query, args.run_id, args.top_k)
        ]
    from sim.contracts import late_interaction_search as fn
    return [r.model_dump(mode="json") for r in fn(args.query, args.run_id, args.top_k)]


def _call_compare_runs(args: CompareRunsArgs):
    backend = _backend()
    if backend == "mock":
        from apollo.mocks.tool_mocks import compare_runs as fn
        return fn(args.run_ids, args.metric)
    from sim.contracts import compare_runs as fn
    return fn(args.run_ids, args.metric)


def _call_run_counterfactual(args: RunCounterfactualArgs):
    backend = _backend()
    if backend == "mock":
        from apollo.mocks.tool_mocks import run_counterfactual as fn
        return fn(
            args.run_id,
            args.branch_t,
            args.alternate_action,
        ).model_dump(mode="json")
    from sim.contracts import run_counterfactual as fn
    res = fn(args.run_id, args.branch_t, args.alternate_action)
    return res.model_dump(mode="json")


def plot_component_history(run_id: str, component: ComponentId) -> ChartSpec:
    """Plan C native — emits a ChartSpec the React frontend renders inline.

    Pulls from the historian directly, then projects to ``[{"t": ..., "health": ...}]``.
    """
    from sim.contracts import query_historian
    rows = query_historian(run_id, component, None) or []
    points = [
        {"t": r.t.timestamp() if hasattr(r.t, "timestamp") else float(r.t),
         "health": float(r.health)}
        for r in rows
    ]
    return ChartSpec(run_id=run_id, component=component, points=points)


def _call_plot_component_history(args: PlotComponentHistoryArgs):
    return plot_component_history(args.run_id, args.component).model_dump(mode="json")


# -----------------------------------------------------------------------------
# Public registry
# -----------------------------------------------------------------------------

REGISTRY: dict[str, dict[str, Any]] = {
    "query_historian": {
        "schema": ToolSchema(
            name="query_historian",
            description="Look up historian rows for one (run_id, component, time_range).",
            args_model=f"{QueryHistorianArgs.__module__}.{QueryHistorianArgs.__name__}",
        ),
        "args_model": QueryHistorianArgs,
        "call": _call_query_historian,
    },
    "late_interaction_search": {
        "schema": ToolSchema(
            name="late_interaction_search",
            description="LateOn-Code-edge retrieval over component snippets.",
            args_model=f"{LateInteractionSearchArgs.__module__}.{LateInteractionSearchArgs.__name__}",
        ),
        "args_model": LateInteractionSearchArgs,
        "call": _call_late_interaction_search,
    },
    "compare_runs": {
        "schema": ToolSchema(
            name="compare_runs",
            description="Compare a metric across multiple runs.",
            args_model=f"{CompareRunsArgs.__module__}.{CompareRunsArgs.__name__}",
        ),
        "args_model": CompareRunsArgs,
        "call": _call_compare_runs,
    },
    "run_counterfactual": {
        "schema": ToolSchema(
            name="run_counterfactual",
            description="Branch a run at branch_t with an alternate action.",
            args_model=f"{RunCounterfactualArgs.__module__}.{RunCounterfactualArgs.__name__}",
        ),
        "args_model": RunCounterfactualArgs,
        "call": _call_run_counterfactual,
    },
    "plot_component_history": {
        "schema": ToolSchema(
            name="plot_component_history",
            description="Emit a ChartSpec for a (run_id, component) so the UI can render the curve.",
            args_model=f"{PlotComponentHistoryArgs.__module__}.{PlotComponentHistoryArgs.__name__}",
        ),
        "args_model": PlotComponentHistoryArgs,
        "call": _call_plot_component_history,
    },
}


def list_tools() -> list[ToolSchema]:
    return [REGISTRY[name]["schema"] for name in REGISTRY]


def invoke(name: str, raw_args: dict[str, Any]) -> Any:
    """Validate ``raw_args`` against the tool's Pydantic schema, then call it."""
    if name not in REGISTRY:
        raise ToolError(f"Unknown tool: {name}")
    args_model: type[BaseModel] = REGISTRY[name]["args_model"]
    try:
        args = args_model(**raw_args)
    except Exception as exc:  # noqa: BLE001 — re-raise as ToolError
        raise ToolError(f"Invalid args for {name}: {exc}") from exc
    return REGISTRY[name]["call"](args)


__all__ = [
    "CompareRunsArgs",
    "LateInteractionSearchArgs",
    "PlotComponentHistoryArgs",
    "QueryHistorianArgs",
    "REGISTRY",
    "RunCounterfactualArgs",
    "ToolError",
    "ToolSchema",
    "invoke",
    "list_tools",
    "plot_component_history",
]
