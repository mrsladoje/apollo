"""What-If route — POST /api/whatif (PLAN-C §5.1, §12).

The endpoint projects Plan B's typed ``CounterfactualResult`` into the compact
chart shape the current React panel consumes. It no longer imports the Apollo
mock directly; mock mode flows through the same tool registry as the real agent.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from apollo.agent.tools.registry import invoke
from engine.contracts import ComponentId
from sim.drivers.composite import SIM_START_TIME

router = APIRouter(prefix="/api")


class WhatIfRequest(BaseModel):
    run_id: str
    branch_t: float | int | datetime
    alternate_action: dict[str, Any] | None = None
    alt_action: str | dict[str, Any] | None = Field(default=None)


def _branch_datetime(branch_t: float | int | datetime) -> datetime:
    if isinstance(branch_t, datetime):
        if branch_t.tzinfo is None:
            return branch_t
        return branch_t.astimezone(timezone.utc).replace(tzinfo=None)
    return SIM_START_TIME + timedelta(minutes=float(branch_t))


def _branch_minutes(branch_t: float | int | datetime, branch_dt: datetime) -> float:
    if isinstance(branch_t, (float, int)):
        return float(branch_t)
    return (branch_dt - SIM_START_TIME).total_seconds() / 60.0


def _normalize_action(req: WhatIfRequest) -> dict[str, Any]:
    if isinstance(req.alternate_action, dict):
        return req.alternate_action
    if isinstance(req.alt_action, dict):
        return req.alt_action

    action_name = req.alt_action or "swap_blade"
    mapping = {
        "swap_blade": ComponentId.BLADE,
        "clean_nozzle": ComponentId.NOZZLE,
        "replace_insulation": ComponentId.INSULATION,
    }
    component = mapping.get(str(action_name))
    if component is None:
        return {"action": str(action_name)}
    return {"action": "MAINTENANCE", "component_id": component.value}


def _mean_health_by_time(rows: list[dict[str, Any]], start: datetime) -> list[dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["t"]), []).append(float(row["health"]))
    points: list[dict[str, float]] = []
    for t_iso in sorted(grouped):
        t = datetime.fromisoformat(t_iso)
        if t.tzinfo is not None:
            t = t.astimezone(timezone.utc).replace(tzinfo=None)
        points.append({
            "t": (t - start).total_seconds() / 60.0,
            "health": sum(grouped[t_iso]) / len(grouped[t_iso]),
        })
    return points


@router.post("/whatif")
async def whatif(req: WhatIfRequest) -> dict:
    branch_dt = _branch_datetime(req.branch_t)
    action = _normalize_action(req)
    result = invoke(
        "run_counterfactual",
        {
            "run_id": req.run_id,
            "branch_t": branch_dt,
            "alternate_action": action,
        },
    )
    diff = result.get("diff", {})
    return {
        "run_id": req.run_id,
        "branch_t": _branch_minutes(req.branch_t, branch_dt),
        "alt_action": req.alt_action if isinstance(req.alt_action, str) else action.get("action", ""),
        "original_health": _mean_health_by_time(result.get("original", []), SIM_START_TIME),
        "alt_health": _mean_health_by_time(result.get("alternate", []), SIM_START_TIME),
        "uptime_delta_h": float(diff.get("uptime_delta", 0.0)) / 60.0,
        "counterfactual": result,
    }
