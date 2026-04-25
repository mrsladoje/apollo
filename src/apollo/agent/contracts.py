"""Plan C published language — frozen Pydantic surface (PLAN-C §3.2, ADR-014, ADR-021).

The aggregate root is ``ApolloResponse``. ``Citation`` and ``ToolCall`` are value
objects on the aggregate's exposed surface. The ``SSEEvent`` payload type lives
on the TypeScript side (``frontend/src/types.ts``); see PLAN-C §3.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from engine.contracts import ComponentId

# CANONICAL_COMPONENTS is computed from engine.contracts.ComponentId at import
# time per PLAN-C §3.2 — the only allowed source of component names.
CANONICAL_COMPONENTS: frozenset[str] = frozenset(c.value for c in ComponentId)

ToolName = Literal[
    "query_historian",
    "late_interaction_search",
    "compare_runs",
    "run_counterfactual",
    "plot_component_history",
]

Severity = Literal["INFO", "WARNING", "CRITICAL", "REFUSAL"]


class Citation(BaseModel):
    """Citation value object — identified by ``(run_id, component, timestamp)``.

    The ``component`` field is typed against the ``ComponentId`` enum from the
    shared kernel — string component names are forbidden (PLAN-C §3.4 / §20.8).
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    component: ComponentId
    timestamp: datetime


class ToolCall(BaseModel):
    """Snapshot of one tool invocation. Replayable but not mutable."""

    model_config = ConfigDict(frozen=True)

    tool: ToolName
    args: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    call_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class ApolloResponse(BaseModel):
    """Plan C aggregate root.

    Invariants (PLAN-C §3.2 / §20.3):
      * ``severity`` is closed under ``INFO | WARNING | CRITICAL | REFUSAL``
      * non-REFUSAL responses require ``len(citations) >= 1``
      * each ``Citation`` must resolve against the historian primary key BEFORE
        the SSE ``done`` event fires (handled by ``citations.resolve_citation``;
        unresolvable citations downgrade the aggregate to REFUSAL).
    """

    severity: Severity
    text: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    trace_url: str = ""

    @field_validator("citations")
    @classmethod
    def _citations_required_unless_refusal(cls, v, info):
        if info.data.get("severity") != "REFUSAL" and len(v) < 1:
            raise ValueError("non-REFUSAL responses require ≥1 citation")
        return v


class ChartSpec(BaseModel):
    """Plan C native — output of ``plot_component_history`` tool."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    component: ComponentId
    points: list[dict[str, float]]


__all__ = [
    "ApolloResponse",
    "CANONICAL_COMPONENTS",
    "ChartSpec",
    "Citation",
    "Severity",
    "ToolCall",
    "ToolName",
]
