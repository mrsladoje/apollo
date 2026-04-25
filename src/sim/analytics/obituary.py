"""Failure attribution + obituary generation — PLAN-B §11 (Workstream B7).

ADR-019: calm, professional voice. ADR-014: every claim cited. ADR-003 +
ADR-004: cascade attribution walks the coupling matrix.

Voice rules (enforced by ``test_voice_constraints``):
- No exclamation marks.
- No first-person pronouns.
- No theatrical adjectives (``catastrophic``, ``disaster``, ``dead``,
  ``severe``, ``horrible``, ``massive``, ``critical failure``).
- Severity is communicated by the cause, not by adjectives.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

from engine.contracts import (
    COUPLING_MATRIX_M,
    ROW_ORDER,
    ComponentId,
    ComponentStatus,
)
from sim.historian.reader import query_historian


# Cascades per ADR-003. Mapping: (downstream, upstream) -> cascade label.
# Strict: only the upstream→downstream pairs that actually appear in the
# coupling matrix as non-zero entries with the right semantic role.
_CASCADE_BY_PAIR = {
    (ComponentId.MOTOR, ComponentId.BLADE): "CSC-A Recoating loop",
    (ComponentId.NOZZLE, ComponentId.BLADE): "CSC-C Powder contamination loop",
    (ComponentId.NOZZLE, ComponentId.HEATER): "CSC-B Thermal-Printhead loop",
    (ComponentId.RESISTOR, ComponentId.HEATER): "CSC-B Thermal-Printhead loop",
    (ComponentId.HEATER, ComponentId.INSULATION): "CSC-B Thermal-Printhead loop",
}

# Banned tokens in obituary narratives (ADR-019 voice lint).
_BANNED_TOKENS = (
    "catastrophic",
    "disaster",
    "dead",
    "horrible",
    "massive",
    "tragic",
    "severe",
)
_FIRST_PERSON = re.compile(r"\b(i|me|my|mine|we|us|our|ours)\b", re.IGNORECASE)

OBITUARY_TEMPLATE = (
    "At {failure_t} during run {run_id}, {component_pretty} crossed the failure "
    "threshold (health {health:.2f}). The dominant cause was {cause_phrase}. "
    "{cascade_sentence}The component had been in {prior_status} status since "
    "{status_change_t}. {final_sentence}"
)


def attribute_cause(
    failed_id: ComponentId,
    failure_t: datetime,
    run_id: str,
    db_path: str = "historian.db",
) -> Dict[str, Any]:
    """Return the dominant suspect (PLAN-B §11.2).

    Walks back 30 minutes per the plan and scores upstream components via the
    coupling-matrix weight × upstream health debt. The driver-driven baseline
    is a fallback for runs where no upstream component is degraded.
    """
    id_to_idx = {cid: i for i, cid in enumerate(ROW_ORDER)}
    failed_idx = id_to_idx[failed_id]

    suspects: List[Dict[str, Any]] = []
    lookback = timedelta(minutes=30)

    for upstream_id in ROW_ORDER:
        if upstream_id == failed_id:
            continue
        upstream_idx = id_to_idx[upstream_id]
        weight = COUPLING_MATRIX_M[failed_idx][upstream_idx]
        if weight <= 0:
            continue
        history = query_historian(
            run_id,
            upstream_id,
            (failure_t - lookback, failure_t),
            db_path=db_path,
        )
        if not history:
            continue
        min_health = min(r.health for r in history)
        # Pick the timestep at which upstream was worst — that's the citation.
        worst = min(history, key=lambda r: r.health)
        score = weight * (1.0 - min_health)
        suspects.append(
            {
                "type": "coupled",
                "id": upstream_id,
                "score": score,
                "phrase": f"cascading degradation from {upstream_id.value}",
                "peak_t": worst.t,
            }
        )

    suspects.append(
        {
            "type": "driver",
            "id": "operational_wear",
            "score": 0.1,
            "phrase": "standard operational duty cycle",
            "peak_t": failure_t,
        }
    )

    return max(suspects, key=lambda s: s["score"])


def _cascade_sentence(failed_id: ComponentId, cause: Dict[str, Any]) -> str:
    if cause["type"] != "coupled":
        return ""
    upstream = cause["id"]
    label = _CASCADE_BY_PAIR.get((failed_id, upstream))
    if not label:
        return ""
    return f"This corresponds to the {label} cascade. "


def _find_status_change_t(
    run_id: str,
    component_id: ComponentId,
    failure_t: datetime,
    db_path: str,
) -> datetime:
    """Return the timestep at which the component first entered CRITICAL,
    or ``failure_t`` if that record cannot be found.
    """
    history = query_historian(
        run_id,
        component_id,
        (failure_t - timedelta(minutes=120), failure_t),
        db_path=db_path,
    )
    for row in sorted(history, key=lambda r: r.t):
        if row.status in (ComponentStatus.CRITICAL, ComponentStatus.FAILED):
            return row.t
    return failure_t


def _voice_lint(narrative: str) -> None:
    """Raise ``ValueError`` if the narrative breaks ADR-019 rules."""
    if "!" in narrative:
        raise ValueError("ADR-019 voice violation: exclamation mark in narrative")
    if _FIRST_PERSON.search(narrative):
        raise ValueError("ADR-019 voice violation: first-person pronoun")
    lower = narrative.lower()
    for tok in _BANNED_TOKENS:
        if tok in lower:
            raise ValueError(
                f"ADR-019 voice violation: banned adjective {tok!r} in narrative"
            )


def generate_obituary(
    run_id: str,
    component_id: ComponentId,
    failure_t: datetime,
    state,
    db_path: str = "historian.db",
) -> Dict[str, Any]:
    """Generate a failure obituary per PLAN-B §11.3.

    Citations are validated to be resolvable later by
    ``test_citations_resolvable``: every entry must point to a row that
    exists in ``component_states`` for this run.
    """
    cause = attribute_cause(component_id, failure_t, run_id, db_path=db_path)
    comp_state = state.components[component_id]

    cascade_sentence = _cascade_sentence(component_id, cause)
    status_change_t = _find_status_change_t(run_id, component_id, failure_t, db_path)

    # Derive prior_status from the historian instead of hard-coding "CRITICAL"
    # so the narrative stays accurate for components that fail directly from
    # DEGRADED (rapid failure paths in CSC-B).
    prior_history = query_historian(
        run_id,
        component_id,
        (failure_t - timedelta(minutes=60), failure_t),
        db_path=db_path,
    )
    prior_status = "CRITICAL"
    saw_critical = False
    for row in sorted(prior_history, key=lambda r: r.t):
        if row.t >= failure_t:
            continue
        if row.status == ComponentStatus.CRITICAL:
            saw_critical = True
        elif row.status == ComponentStatus.DEGRADED and not saw_critical:
            prior_status = "DEGRADED"
    if saw_critical:
        prior_status = "CRITICAL"

    narrative = OBITUARY_TEMPLATE.format(
        failure_t=failure_t.isoformat(),
        run_id=run_id,
        component_pretty=component_id.value.capitalize(),
        health=comp_state.health,
        cause_phrase=cause["phrase"],
        cascade_sentence=cascade_sentence,
        prior_status=prior_status,
        status_change_t=status_change_t.isoformat(),
        final_sentence="Replacement is required before operation can resume.",
    )

    _voice_lint(narrative)

    citations: List[Dict[str, Any]] = [
        {
            "run_id": run_id,
            "component": component_id.value,
            "t": failure_t.isoformat(),
        },
        {
            "run_id": run_id,
            "component": component_id.value,
            "t": status_change_t.isoformat(),
        },
    ]
    if cause["type"] == "coupled":
        citations.append(
            {
                "run_id": run_id,
                "component": cause["id"].value,
                "t": cause["peak_t"].isoformat(),
            }
        )

    return {
        "run_id": run_id,
        "component_id": component_id.value,
        "failure_t": failure_t.isoformat(),
        "narrative": narrative,
        "citations_json": json.dumps(citations),
    }


__all__ = [
    "attribute_cause",
    "generate_obituary",
    "OBITUARY_TEMPLATE",
]
