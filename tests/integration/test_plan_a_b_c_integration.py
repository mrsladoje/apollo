"""Plan A → Plan B → Plan C integration suite — gate G4 (PLAN.md §6).

Gate G2 (in ``test_plan_b_c_integration.py``) proves Apollo's tools and
What-If route consume Plan B's published ``sim.contracts``. This suite is
the bigger one: it runs the **real** engine through the **real** simulation
loop into a freshly populated historian, then exercises the Plan C surface
(``AgentLoop`` plus the FastAPI routes) against that historian end-to-end.

Tests assert:

1. ``AgentLoop.answer`` resolves every citation against the just-written
   historian via the §7.2 ACL (no fabrications survive).
2. ``POST /api/chat`` streams the canonical SSE event order
   (``tool-call-start* tool-result* text-delta+ citation+ done``) and
   every emitted citation resolves in the historian.
3. Off-topic queries (``weather in Madrid``) and structurally unanswerable
   queries (non-existent run) downgrade to ``severity == "REFUSAL"`` with
   no citation events on the wire (NFR-6 / NFR-7 / ADR-014).
4. ``GET /api/sim/runs`` surfaces real persisted run IDs once the
   historian is populated (no longer the synthetic ``dark-twin-00`` stubs).
5. ``GET /api/sim/stream/<universe>`` replays real ``component_states``
   from the historian (tick events carry the canonical scenario-policy
   run_id) instead of the random fallback.
6. ``POST /api/whatif`` returns a counterfactual built from Plan B's real
   ``run_counterfactual`` contract against this historian.
7. ``invoke("plot_component_history", …)`` emits a ``ChartSpec`` whose
   point count equals the number of persisted ticks for that component.
8. ``AgentLoop`` is bit-deterministic across two answers to the same
   query against the same historian (NFR-1 / NFR-8 propagated through
   Plan C).
9. Plan C's published surface (``apollo.agent.contracts``) re-uses the
   shared-kernel ``ComponentId`` enum — no string component names cross
   the bounded-context boundary (PLAN.md §3.4 / §9.8 rule 1).

The mocks-first escape hatch is also pinned: ``USE_MOCKS=1`` still routes
the agent's tools to the in-memory mock backend, so Plan C's smoke path
keeps working when nothing has been pre-run yet (PLAN.md §5).
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apollo.agent.citations import resolve_citation
from apollo.agent.contracts import ApolloResponse, Citation, ToolCall
from apollo.agent.loop import AgentLoop
from apollo.agent.tools.registry import invoke
from apollo.api import routes as _api_routes_pkg  # noqa: F401 — ensures package import
from apollo.api.app import app
from apollo.api.routes.chat import reset_loop_for_tests
from engine.contracts import ComponentId
from sim.config import SimulationConfig
from sim.drivers.composite import SIM_START_TIME
from sim.loop import run_simulation


# ---------------------------------------------------------------------------
# Fixture — one fresh historian per test session, populated with a tiny but
# realistic stressed run (long enough that obituaries and forecasts persist).
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def integrated_historian(tmp_path_factory) -> tuple[str, str]:
    db_path = tmp_path_factory.mktemp("g4") / "historian.db"
    cfg = SimulationConfig(
        scenario_name="barcelona-humid",
        policy="none",
        seed=42,
        horizon_minutes=45,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)
    return run_id, str(db_path)


@pytest.fixture(autouse=True)
def _wire_env_to_integrated_historian(monkeypatch, integrated_historian):
    """Every test in this module runs against the gate-G4 historian.

    All three env vars cover the matrix Plan A/B/C honour:
      * ``HISTORIAN_PATH`` — sim.contracts (Plan B)
      * ``HISTORIAN_BACKEND=real`` — force the real reader (Plan B)
      * ``APOLLO_TOOLS_BACKEND=auto`` — let Apollo's registry pick real
      * ``APOLLO_AGENT=loop`` — pin the agent route to the real loop (not mock)
    """
    _, db_path = integrated_historian
    monkeypatch.setenv("HISTORIAN_PATH", db_path)
    monkeypatch.setenv("HISTORIAN_BACKEND", "real")
    monkeypatch.setenv("APOLLO_TOOLS_BACKEND", "auto")
    monkeypatch.setenv("APOLLO_AGENT", "loop")
    monkeypatch.setenv("RETRIEVAL_BACKEND", "dense")
    monkeypatch.delenv("USE_MOCKS", raising=False)
    # Force the cached AgentLoop to rebuild so it picks up the new env.
    reset_loop_for_tests()


# ---------------------------------------------------------------------------
# 1. AgentLoop directly: every citation it emits resolves in the historian.
# ---------------------------------------------------------------------------

def test_agent_loop_emits_only_resolvable_citations(integrated_historian):
    run_id, db_path = integrated_historian
    loop = AgentLoop()  # honors HISTORIAN_PATH lazily on every call

    response = loop.answer(
        f"How is the {run_id} nozzle doing?",
        run_context=run_id,
    )

    # Plan C aggregate-root invariant (PLAN-C §20.3): non-REFUSAL ⇒ ≥1 citation.
    assert isinstance(response, ApolloResponse)
    assert response.severity in {"INFO", "WARNING", "CRITICAL"}
    assert response.citations, "real-engine answer should carry citations"

    # ACL gate (PLAN-C §7.2 / §20.8): every citation resolves against the
    # just-written historian. If even one slipped through fabricated, the
    # downgrade in `enforce_grounding` would have stripped them.
    conn = sqlite3.connect(db_path)
    try:
        for c in response.citations:
            assert resolve_citation(c, conn), f"unresolved citation: {c}"
    finally:
        conn.close()

    # Tool calls actually fired (FR-3.2 / FR-3.7).
    tool_names = {tc.tool for tc in response.tool_calls}
    assert "query_historian" in tool_names


def test_agent_loop_is_deterministic_across_two_answers(integrated_historian):
    """NFR-1 / NFR-8 propagation: same historian + same query ⇒ same answer."""
    run_id, _ = integrated_historian
    loop = AgentLoop()
    q = f"How is the {run_id} heater doing?"

    a = loop.answer(q, run_context=run_id)
    b = loop.answer(q, run_context=run_id)

    assert a.severity == b.severity
    assert a.text == b.text
    assert [(c.run_id, c.component, c.timestamp) for c in a.citations] == \
           [(c.run_id, c.component, c.timestamp) for c in b.citations]


# ---------------------------------------------------------------------------
# 2. SSE event order via the real route — and every citation resolves.
# ---------------------------------------------------------------------------

ALLOWED_TYPES = {"text-delta", "tool-call-start", "tool-result", "citation", "done"}


def _drain_sse(body: bytes) -> list[dict]:
    """Pull the JSON-encoded event objects out of an SSE response body.

    sse-starlette emits ``event: message\\ndata: <json>\\n\\n`` per event.
    We're not asserting on heartbeats — they only fire after 15 s of idle.
    """
    out: list[dict] = []
    for line in body.decode("utf-8", errors="replace").splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return out


def test_chat_route_streams_real_events_and_citations_resolve(integrated_historian):
    run_id, db_path = integrated_historian
    client = TestClient(app)

    with client.stream(
        "POST", "/api/chat",
        json={"query": f"How is the {run_id} nozzle doing?", "run_context": run_id},
    ) as resp:
        assert resp.status_code == 200
        body = resp.read()

    events = _drain_sse(body)
    assert events, "no SSE events received"

    # Frozen schema closure (ADR-017 / PLAN-C §3.3): nothing else on the wire.
    for ev in events:
        assert ev["type"] in ALLOWED_TYPES, ev

    # Terminates in `done` carrying a Langfuse trace URL.
    assert events[-1]["type"] == "done"
    assert "trace_url" in events[-1]["payload"]

    # Tool calls precede text deltas (PLAN-C §6.3 grounding rule #1).
    first_tool = next((i for i, e in enumerate(events) if e["type"] == "tool-call-start"), None)
    first_text = next((i for i, e in enumerate(events) if e["type"] == "text-delta"), None)
    assert first_tool is not None, "no tool-call-start emitted"
    if first_text is not None:
        assert first_tool < first_text

    # Every `tool-call-start` has a matching `tool-result` with the same call_id.
    starts = {e["payload"]["call_id"] for e in events if e["type"] == "tool-call-start"}
    results = {e["payload"]["call_id"] for e in events if e["type"] == "tool-result"}
    assert starts == results, f"tool-call/result mismatch: {starts ^ results}"

    # Every emitted citation resolves in the historian. The ACL guarantees
    # this; we re-prove it from the SSE wire so a router-side regression
    # surfaces here, not three layers down.
    citation_events = [e for e in events if e["type"] == "citation"]
    assert citation_events, "no citation events emitted on a non-refusal answer"

    conn = sqlite3.connect(db_path)
    try:
        from datetime import datetime
        for ev in citation_events:
            p = ev["payload"]
            cit = Citation(
                run_id=p["run_id"],
                component=ComponentId(p["component"]),
                timestamp=datetime.fromisoformat(p["timestamp"]),
            )
            assert resolve_citation(cit, conn), f"unresolved wire citation: {p}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3. Refusal pathways via the real route.
# ---------------------------------------------------------------------------

def test_chat_route_refuses_off_topic_query():
    client = TestClient(app)
    with client.stream(
        "POST", "/api/chat",
        json={"query": "What is the weather in Madrid?"},
    ) as resp:
        assert resp.status_code == 200
        body = resp.read()

    events = _drain_sse(body)
    assert events[-1]["type"] == "done"
    # No fabricated citations on the wire — the ACL refuses outright.
    citations = [e for e in events if e["type"] == "citation"]
    assert citations == []
    # Refusal text is what the user sees.
    text = "".join(
        e["payload"]["token"] for e in events if e["type"] == "text-delta"
    )
    assert text.lstrip().startswith("REFUSAL")


def test_chat_route_refuses_unknown_run():
    """Citation resolution against a fabricated run_id ⇒ REFUSAL."""
    client = TestClient(app)
    with client.stream(
        "POST", "/api/chat",
        json={
            "query": "What was the bearing temperature in run-9999?",
            "run_context": "run-9999",
        },
    ) as resp:
        assert resp.status_code == 200
        body = resp.read()

    events = _drain_sse(body)
    assert events[-1]["type"] == "done"
    assert [e for e in events if e["type"] == "citation"] == []
    text = "".join(
        e["payload"]["token"] for e in events if e["type"] == "text-delta"
    )
    assert text.lstrip().startswith("REFUSAL")


# ---------------------------------------------------------------------------
# 4. /api/sim/runs surfaces the real run IDs the prerun has written.
# ---------------------------------------------------------------------------

def test_sim_runs_surfaces_real_persisted_run_ids(integrated_historian):
    run_id, _ = integrated_historian
    client = TestClient(app)

    resp = client.get("/api/sim/runs")
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list) and rows
    # The Dark Twin universe maps to (barcelona-humid, none) — i.e. our run.
    dark = next(r for r in rows if r["id"] == "dark-twin")
    assert dark["run_id"] == run_id
    assert dark.get("synthetic") is False
    assert dark.get("scenario") == "barcelona-humid"
    assert dark.get("policy") == "none"


def test_sim_stream_replays_real_historian(integrated_historian):
    """The first tick on the SSE stream carries the canonical run_id, not
    one of the synthetic ``dark-twin-00`` placeholders.
    """
    run_id, _ = integrated_historian
    client = TestClient(app)

    with client.stream("GET", "/api/sim/stream/dark-twin") as resp:
        assert resp.status_code == 200
        # Read enough chunks to capture at least one tick. The replay throttles
        # at 0.05 s/tick so this terminates well within pytest's default timeout.
        chunks = []
        for chunk in resp.iter_bytes():
            chunks.append(chunk)
            if len(b"".join(chunks)) > 4096:
                break
        body = b"".join(chunks)

    events = _drain_sse(body)
    ticks = [e for e in events if e.get("type") == "tick"]
    assert ticks, "no tick events on /api/sim/stream/dark-twin"
    assert ticks[0]["run_id"] == run_id
    # All six components present at every tick.
    assert {s["component_id"] for s in ticks[0]["states"]} == {
        c.value for c in ComponentId
    }


# ---------------------------------------------------------------------------
# 5. /api/whatif — real counterfactual against the integrated historian.
# ---------------------------------------------------------------------------

def test_whatif_route_against_integrated_historian(integrated_historian):
    run_id, _ = integrated_historian
    client = TestClient(app)

    resp = client.post(
        "/api/whatif",
        json={
            "run_id": run_id,
            "branch_t": 10,
            "alt_action": "clean_nozzle",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["original_health"] and body["alt_health"]
    diff = body["counterfactual"]["diff"]
    assert {"uptime_delta", "failures_avoided", "cost_delta"} <= diff.keys()


# ---------------------------------------------------------------------------
# 6. Tool registry on real data — point count == persisted-tick count.
# ---------------------------------------------------------------------------

def test_plot_component_history_returns_real_chart(integrated_historian):
    run_id, db_path = integrated_historian
    spec = invoke(
        "plot_component_history",
        {"run_id": run_id, "component": ComponentId.NOZZLE.value},
    )
    assert spec["run_id"] == run_id
    assert spec["component"] == ComponentId.NOZZLE.value
    n_points = len(spec["points"])
    # Independent count from the historian — the registry should not be
    # smoothing / decimating before returning a ChartSpec.
    conn = sqlite3.connect(db_path)
    try:
        n_rows = conn.execute(
            "SELECT count(*) FROM component_states "
            "WHERE run_id=? AND component_id=?",
            (run_id, ComponentId.NOZZLE.value),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n_points == n_rows == 45


# ---------------------------------------------------------------------------
# 7. Fabricated citations cannot resolve.
# ---------------------------------------------------------------------------

def test_fabricated_citation_does_not_resolve(integrated_historian):
    run_id, db_path = integrated_historian
    from datetime import datetime

    fake = Citation(
        run_id="run-does-not-exist-9999",
        component=ComponentId.NOZZLE,
        timestamp=datetime(2099, 1, 1, 0, 0, 0),
    )
    conn = sqlite3.connect(db_path)
    try:
        assert resolve_citation(fake, conn) is False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 8. Mocks-first escape hatch (PLAN.md §5) still works when env says so.
# ---------------------------------------------------------------------------

def test_use_mocks_still_short_circuits_to_in_memory_backend(monkeypatch):
    """PLAN.md §5.1 — ``USE_MOCKS=1`` ⇒ tools route to the in-memory mocks,
    even though the integrated historian above is reachable. Demo dry-runs
    keep working when the prerun grid hasn't been built yet.
    """
    monkeypatch.setenv("USE_MOCKS", "1")
    monkeypatch.setenv("APOLLO_TOOLS_BACKEND", "auto")

    rows = invoke(
        "query_historian",
        {
            "run_id": "barcelona-01",
            "component": ComponentId.BLADE.value,
            "time_range": (
                SIM_START_TIME,
                SIM_START_TIME + timedelta(minutes=5),
            ),
        },
    )
    # The mock historian carries this canonical id; the real one (gate-G4)
    # uses ``barcelona-humid-none-seed0042``. So a non-empty hit here proves
    # we routed to the mock backend.
    assert rows
    assert {r["run_id"] for r in rows} == {"barcelona-01"}


# ---------------------------------------------------------------------------
# 9. Ubiquitous-language guard — Plan C never re-defines ComponentId.
# ---------------------------------------------------------------------------

def test_plan_c_reuses_shared_kernel_component_enum():
    """ADR-021 §2 / PLAN.md §3.4 / §9.8 rule 1 — ``ComponentId`` lives in
    ``engine.contracts`` and Plan C must consume that single enum.
    """
    from apollo.agent import contracts as plan_c_contracts
    from apollo.agent.tools import registry as plan_c_registry
    from engine.contracts import ComponentId as KernelComponentId

    assert plan_c_contracts.Citation.model_fields["component"].annotation \
        is KernelComponentId
    # The registry's input schemas must also reference the shared enum.
    qh = plan_c_registry.QueryHistorianArgs.model_fields["component"].annotation
    assert qh is KernelComponentId


# ---------------------------------------------------------------------------
# 10. Public surface — Plan C's published language is exactly the contracts.
# ---------------------------------------------------------------------------

def test_plan_c_public_surface_is_the_aggregate_plus_value_objects():
    """PLAN-C §20.4 — the published language is ``ApolloResponse`` (the
    aggregate root) plus ``Citation`` / ``ToolCall`` (value objects). This
    test pins those exports so a refactor that drops one fails CI here.
    """
    from apollo.agent import contracts

    public = {n for n in contracts.__all__ if not n.startswith("_")}
    assert {"ApolloResponse", "Citation", "ToolCall"} <= public
