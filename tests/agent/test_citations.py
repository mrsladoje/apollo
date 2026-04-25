"""Adversarial citation suite (PLAN-C §7.4)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from apollo.agent.citations import (
    REFUSAL_TEMPLATE,
    downgrade_to_refusal,
    enforce_grounding,
    resolve_citation,
)
from apollo.agent.contracts import ApolloResponse, Citation
from engine.contracts import ComponentId


def _ts() -> datetime:
    return datetime(2026, 4, 25, 8, 0, 0)


# -----------------------------------------------------------------------------
# Layer 1 — Pydantic enforcement
# -----------------------------------------------------------------------------

def test_non_refusal_has_citation() -> None:
    with pytest.raises(ValidationError):
        ApolloResponse(severity="INFO", text="Hi", citations=[])


def test_unknown_component_rejected() -> None:
    with pytest.raises(ValidationError):
        Citation(run_id="r", component="microwave", timestamp=_ts())  # type: ignore[arg-type]


def test_refusal_template_text() -> None:
    text = REFUSAL_TEMPLATE.format(summarized_query="weather in Madrid")
    assert text.startswith("REFUSAL — ")
    assert "weather in Madrid" in text


# -----------------------------------------------------------------------------
# Layer 2 — citation resolution
# -----------------------------------------------------------------------------

def test_real_citation_resolves(historian_db_path, real_citation) -> None:
    c = Citation(
        run_id=real_citation["run_id"],
        component=ComponentId(real_citation["component"]),
        timestamp=real_citation["timestamp"],
    )
    assert resolve_citation(c) is True


def test_fabricated_citation_refuses(historian_db_path, real_citation) -> None:
    fabricated = Citation(
        run_id="run-9999",  # known-bad run id
        component=ComponentId.NOZZLE,
        timestamp=_ts(),
    )
    response = ApolloResponse(
        severity="INFO", text="My nozzle is fine.", citations=[fabricated]
    )
    downgraded = enforce_grounding(response)
    assert downgraded.severity == "REFUSAL"
    assert downgraded.citations == []


def test_partial_fabrication_refuses(historian_db_path, real_citation) -> None:
    real = Citation(
        run_id=real_citation["run_id"],
        component=ComponentId(real_citation["component"]),
        timestamp=real_citation["timestamp"],
    )
    fabricated = Citation(
        run_id="run-9999",
        component=ComponentId.NOZZLE,
        timestamp=_ts(),
    )
    response = ApolloResponse(
        severity="INFO",
        text="My nozzle has degraded.",
        citations=[real, fabricated],
    )
    downgraded = enforce_grounding(response)
    assert downgraded.severity == "REFUSAL"
    assert downgraded.citations == []


def test_pydantic_error_caught_via_downgrade(historian_db_path, real_citation) -> None:
    real = Citation(
        run_id=real_citation["run_id"],
        component=ComponentId(real_citation["component"]),
        timestamp=real_citation["timestamp"],
    )
    response = ApolloResponse(
        severity="INFO", text="OK", citations=[real]
    )
    # Force the resolver to fail by pointing at a non-existent DB; the
    # enforcer must still return a structured REFUSAL rather than crash.
    refused = enforce_grounding(response, db=sqlite3.connect(":memory:"))
    assert refused.severity == "REFUSAL"


def test_already_refusal_is_passthrough() -> None:
    refused = ApolloResponse(severity="REFUSAL", text="REFUSAL — x", citations=[])
    assert enforce_grounding(refused) is refused


def test_downgrade_preserves_audit(historian_db_path, real_citation) -> None:
    real = Citation(
        run_id=real_citation["run_id"],
        component=ComponentId(real_citation["component"]),
        timestamp=real_citation["timestamp"],
    )
    response = ApolloResponse(
        severity="INFO",
        text="OK",
        citations=[real],
        trace_url="https://example/trace/abc",
    )
    refused = downgrade_to_refusal(response, summarized_query="x")
    assert refused.severity == "REFUSAL"
    assert refused.trace_url == "https://example/trace/abc"
