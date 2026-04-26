"""Schema-compatible mock implementations of the Plan-C tools.

These are Plan C convenience mocks, but they intentionally return the same
Pydantic models as ``sim.contracts`` so mock mode cannot drift from the real
Plan B contract.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

from engine.contracts import ComponentId, ComponentStatus, status_for_health
from sim.contracts import CounterfactualResult, HistorianRow, RetrievedRow

COMPONENTS: list[ComponentId] = list(ComponentId)

# Canned historian rows keyed by run_id.
HISTORIAN_DATA: dict[str, list[HistorianRow]] = {}

_START = datetime(2026, 4, 25, 8, 0, 0)


def _seed_run(run_id: str, seed: int = 42) -> None:
    rng = random.Random(seed)
    rows: list[HistorianRow] = []
    healths = {component: 1.0 for component in COMPONENTS}
    for minute in range(0, 121, 5):
        t = _START + timedelta(minutes=minute)
        for component in COMPONENTS:
            healths[component] -= rng.uniform(0.01, 0.06)
            healths[component] = max(0.0, healths[component])
            rows.append(
                HistorianRow(
                    run_id=run_id,
                    t=t,
                    component_id=component,
                    health=round(healths[component], 3),
                    status=status_for_health(healths[component]),
                    metrics={"temp_C": round(rng.uniform(60, 95), 3)},
                )
            )
    HISTORIAN_DATA[run_id] = rows


def _status(h: float) -> ComponentStatus:
    return status_for_health(h)


def _canonical_run_id(run_id: str) -> str:
    aliases = {
        "barcelona-01": "barcelona-humid-none-seed0042",
        "phoenix-02": "phoenix-dry-none-seed0042",
        "dark-twin-00": "stressed-none-seed0042",
    }
    return aliases.get(run_id, run_id)


def _rows(run_id: str) -> list[HistorianRow]:
    canonical = _canonical_run_id(run_id)
    return HISTORIAN_DATA.get(canonical, [])


def _action_component(action: dict) -> ComponentId:
    component = action.get("component_id")
    if component is not None:
        return ComponentId(component)
    action_name = str(action.get("action", ""))
    mapping = {
        "swap_blade": ComponentId.BLADE,
        "clean_nozzle": ComponentId.NOZZLE,
        "replace_insulation": ComponentId.INSULATION,
        "fix_resistor": ComponentId.RESISTOR,
    }
    return mapping.get(action_name, ComponentId.BLADE)


def _with_legacy_run_id(rows: list[HistorianRow], requested_run_id: str) -> list[HistorianRow]:
    canonical = _canonical_run_id(requested_run_id)
    if canonical == requested_run_id:
        return rows
    return [row.model_copy(update={"run_id": requested_run_id}) for row in rows]


# Pre-seed canonical Plan-B runs plus the historical Plan-C aliases.
_seed_run("barcelona-humid-none-seed0042", seed=10)
_seed_run("phoenix-dry-none-seed0042", seed=20)
_seed_run("stressed-none-seed0042", seed=5)


def query_historian(
    run_id: str,
    component: Optional[ComponentId] = None,
    time_range: Optional[tuple[datetime, datetime]] = None,
) -> list[HistorianRow]:
    rows = _with_legacy_run_id(_rows(run_id), run_id)
    if component is not None:
        rows = [row for row in rows if row.component_id == component]
    if time_range is not None:
        start, end = time_range
        rows = [row for row in rows if start <= row.t <= end]
    return rows


def late_interaction_search(
    query: str,
    run_id: Optional[str] = None,
    top_k: int = 10,
) -> list[RetrievedRow]:
    query_l = query.lower()
    candidate_run_ids = [run_id] if run_id else list(HISTORIAN_DATA)
    results: list[RetrievedRow] = []
    for candidate in candidate_run_ids:
        if candidate is None:
            continue
        for row in _rows(candidate):
            if len(results) >= top_k:
                return results
            token_match = row.component_id.value in query_l or row.status.value.lower() in query_l
            if token_match or not results:
                results.append(
                    RetrievedRow(
                        run_id=candidate,
                        component=row.component_id,
                        t=row.t,
                        score=0.85 if token_match else 0.5,
                        snippet=(
                            f"component={row.component_id.value} status={row.status.value} "
                            f"health={row.health:.3f}"
                        ),
                    )
                )
    return results[:top_k]


def compare_runs(run_ids: list[str], metric: str) -> dict[str, float]:
    valid_metrics = {"uptime_hours", "failure_count", "maintenance_count", "avg_health"}
    if metric not in valid_metrics:
        raise ValueError(f"Unknown metric {metric!r}; valid options: {sorted(valid_metrics)}")
    comparison: dict[str, float] = {}
    for run_id in run_ids:
        rows = _rows(run_id)
        if not rows:
            comparison[run_id] = 0.0
            continue
        if metric == "avg_health":
            comparison[run_id] = sum(row.health for row in rows) / len(rows)
        elif metric == "failure_count":
            comparison[run_id] = float(
                len({row.component_id for row in rows if row.status == ComponentStatus.FAILED})
            )
        elif metric == "maintenance_count":
            comparison[run_id] = 0.0
        else:
            by_t: dict[datetime, bool] = {}
            for row in rows:
                by_t.setdefault(row.t, True)
                if row.status == ComponentStatus.FAILED:
                    by_t[row.t] = False
            comparison[run_id] = sum(1 for up in by_t.values() if up) * 5.0 / 60.0
    return comparison


def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict,
) -> CounterfactualResult:
    original = query_historian(run_id, None, (branch_t, _START + timedelta(minutes=120)))
    target = _action_component(alternate_action)
    alternate: list[HistorianRow] = []
    for row in original:
        if row.t >= branch_t and row.component_id == target:
            health = min(1.0, row.health + 0.1)
            alternate.append(
                row.model_copy(
                    update={
                        "run_id": f"{row.run_id}-cf",
                        "health": health,
                        "status": _status(health),
                    }
                )
            )
        else:
            alternate.append(row.model_copy(update={"run_id": f"{row.run_id}-cf"}))
    return CounterfactualResult(
        original=original,
        alternate=alternate,
        diff={
            "uptime_delta": 30.0,
            "failures_avoided": 1.0,
            "cost_delta": -50.0,
        },
    )
