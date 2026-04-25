# Plan C — Agent & UI

> Owner: **Developer C** (solo slice, parallel with Plan A — Engine and Plan B — Simulation).
> Scope: Phase 3 "Apollo" agent + the entire React frontend + observability + automated grounding eval.
> Time budget: **15 hours**, mocks-first so Plans A and B never block Developer C.
> Source of truth: PRD v1.1 (FR-3.x, FR-W.1/2/3/5/7/8/9, NFR-5/6/7), ADR-008/009/010/013/014/016/017/018/019/020.

---

## 1. Goal & success criteria

Plan C ships every PRD item below and is "done" only when each acceptance check passes.

### 1.1 Functional requirements

| PRD ID | Requirement | Verification (Plan C owns) |
| --- | --- | --- |
| **FR-3.1** | Natural-language text input dispatched to agent loop | Chat input element wired to `POST /api/chat`, opens SSE stream |
| **FR-3.2** | Agent retrieves telemetry via tool calls before answering | System prompt enforces `≥1` tool call before any non-trivial answer; `tests/agent/test_grounding.py` asserts tool-call audit log non-empty for canonical queries |
| **FR-3.3** | Every response includes `(run_id, component, timestamp)` citations | Pydantic `ApolloResponse` validator rejects non-REFUSAL responses with empty `citations`; `tests/agent/test_citations.py` |
| **FR-3.4** | Severity tag `INFO | WARNING | CRITICAL` (+ `REFUSAL` extension) on every response | Severity badge rendered in UI; `Literal` type on response model |
| **FR-3.5** | Structured refusal when no telemetry exists | Refusal template + citation-resolution downgrade path; `tests/agent/test_refusal.py` |
| **FR-3.6** | Five typed tools registered | `query_historian`, `late_interaction_search`, `compare_runs`, `run_counterfactual`, `plot_component_history` registered as Pydantic schemas |
| **FR-3.7** | Tool calls visible in UI | Collapsible tool-call cards stream in via SSE `tool-call-start` / `tool-result` |
| **FR-3.8** | Citation timestamps clickable; chart scrolls < 100 ms | Click handler on `<CitationChip>`; scroll perf test in Vitest |
| **FR-W.1** | Apollo first-person persona + component `speak()` | Persona prompt < 200 tokens; six template-bounded `speak()` generators |
| **FR-W.2** | Dark Twin framing in three Universe panels | UI copy renames NONE → "Dark Twin"; obituary text matches |
| **FR-W.3** | Closing demo slide with euro savings headline | `docs/slides/savings.md` + speaker notes citing public AM TCO refs |
| **FR-W.5** | Live "Ask Apollo" 10-question dry-run, 0 hallucinations | `tests/eval/wildcards.json` + dry-run script |
| **FR-W.6 (UI side)** | Conformal prediction bands rendered | Recharts `Area` shading from Plan A `Forecast` payloads (mocked until M1 lands) |
| **FR-W.7** | Langfuse observability via Claude Agent SDK OTel | `LANGSMITH_OTEL_ENABLED=true`; "Trace" link on every Apollo response |
| **FR-W.8** | Streaming agent responses (SSE) | `sse-starlette` `EventSourceResponse`; native `EventSource` on client; frozen event schema |
| **FR-W.9** | Automated grounding eval — Ragas + DeepEval | `tests/eval/grounding_set.json` (30 Q/A); `deepeval test run` exits 0 with faithfulness ≥ 0.95, hallucination = 0 |

### 1.2 Non-functional requirements

| PRD ID | Target | Plan C owns |
| --- | --- | --- |
| **NFR-5** | Agent response < 6 s p95 | Cap `max_tool_calls_per_turn = 3` unless explicitly needed; latency benchmark in `tests/agent/test_latency.py` |
| **NFR-6** | 0% hallucination on eval | Pydantic + citation-resolution + refusal template + DeepEval gate |
| **NFR-7** | 100% citation coverage on non-refusal | Pydantic `min_length=1` constraint enforced; `tests/agent/test_citations.py::test_non_refusal_has_citation` |

### 1.3 Definition of done (Plan C)

- All 14 PRD rows above checked off with passing tests
- `npm run build` and `npm run test:ui` green
- `pytest tests/agent tests/sse tests/eval -q` green
- `deepeval test run tests/eval/` exits 0
- Live "Ask Apollo" dry-run logged (10 wild-cards → 0 hallucinations)
- Langfuse trace URL renders on every demo response
- `config/agent.yaml` pins the final Sonnet-class model id; README and demo slide quote it verbatim

---

## 2. ADR map

Every commitment in this plan cross-references at least one ADR.

| ADR | Topic | Plan C consumes it as |
| --- | --- | --- |
| **ADR-008** | Claude Agent SDK + Sonnet-class model | Implementation directive for §6 (workstream C2) — pin model in `config/agent.yaml`, register five Pydantic-typed tools |
| **ADR-009** | Pattern C — Agentic Diagnosis | Five-tool ceiling, visible tool calls, refuse-on-empty contract |
| **ADR-010** | Late-interaction retrieval (LateOn-Code-edge) | **Consumer only** — wraps Plan B's `late_interaction_search` implementation |
| **ADR-013** | Dark Twin three-scenario framing | UI copy + obituary narration in §10 (workstream C6) |
| **ADR-014** | Pydantic citations + refusal templates | Schema + three-layer enforcement pipeline in §7 (workstream C3) |
| **ADR-016** | Langfuse observability | Env-var setup, "Trace" link, self-hosted Docker fallback (§9 / workstream C5) |
| **ADR-017** | Server-Sent Events for streaming | Frozen event schema, `sse-starlette`, native `EventSource` (§5 / workstream C1) |
| **ADR-018** | Ragas + DeepEval automated grounding eval | `tests/eval/` pipeline (§14 / workstream C10) |
| **ADR-019** | Apollo first-person persona | < 200 token system prompt, six bounded `speak()` generators (§8 / workstream C4) |
| **ADR-020 §12** | **Vercel AI SDK explicitly rejected** | Frontend uses native `EventSource` only |
| **ADR-020 §13** | MCP-style tool servers explicitly rejected | Tools are in-code Pydantic callables, no IPC |

---

## 3. Integration contracts (FROZEN)

Plans A and B consume these schemas at integration time only. Until then, Plan C develops against mocks. **Do not modify these without a three-way sign-off.**

### 3.1 Inbound contracts (consumed by Plan C)

```python
# From Plan A (engine.contracts) — see PLAN.md §3.1 for the full source.
from engine.contracts import ComponentId, ComponentStatus, Forecast
# ComponentId: str-Enum with values {"blade","motor","nozzle","resistor","heater","insulation"}
# ComponentStatus: str-Enum {"FUNCTIONAL","DEGRADED","CRITICAL","FAILED"}
# Forecast(component_id, horizon_min, point, lower, upper, ci_level)

# From Plan B (sim.contracts)
from sim.contracts import (
    HistorianRow,             # (run_id, t, component_id, health, status, metrics_json)
    query_historian,          # (run_id, component, time_range) -> list[HistorianRow]
    compare_runs,             # (run_ids, metric)              -> ComparisonPayload
    run_counterfactual,       # (run_id, branch_t, alt_action) -> CounterfactualResult
    late_interaction_search,  # (query, run_id?)               -> list[RetrievedRow]
    CounterfactualResult,
    RetrievedRow,
)
```

### 3.2 Outbound contracts (published by Plan C)

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

# CANONICAL_COMPONENTS is computed from engine.contracts.ComponentId at import
# time — see PLAN.md §3.4 ("the only allowed source of component names"). Any
# string-name copy of these IDs is a bug.
from engine.contracts import ComponentId
CANONICAL_COMPONENTS = {c.value for c in ComponentId}
# Resolves to: {"blade", "motor", "nozzle", "resistor", "heater", "insulation"}

class Citation(BaseModel):
    run_id: str
    component: ComponentId   # typed against the enum, not a free string (ADR-014)
    timestamp: datetime
    # Pydantic enforces enum membership; resolution against the historian PK
    # happens in resolve_citation() before the SSE 'done' event fires (§7).
    # NOTE: PK resolution against historian happens in resolve_citation()
    # before the SSE 'done' event fires. See §7.

class ToolCall(BaseModel):
    tool: Literal[
        "query_historian", "late_interaction_search", "compare_runs",
        "run_counterfactual", "plot_component_history",
    ]
    args: dict
    result: dict | None
    call_id: str
    started_at: datetime
    finished_at: datetime | None

class ApolloResponse(BaseModel):
    severity: Literal["INFO", "WARNING", "CRITICAL", "REFUSAL"]
    text: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    trace_url: str  # Langfuse deep link

    @field_validator("citations")
    @classmethod
    def _citations_required_unless_refusal(cls, v, info):
        if info.data.get("severity") != "REFUSAL" and len(v) < 1:
            raise ValueError("non-REFUSAL responses require ≥1 citation")
        return v
```

### 3.3 SSE event schema (frozen, TypeScript on the React side)

```ts
type SSEEvent =
  | { type: "text-delta";       payload: { token: string } }
  | { type: "tool-call-start";  payload: { tool: string; args: object; call_id: string } }
  | { type: "tool-result";      payload: { call_id: string; result: object } }
  | { type: "citation";         payload: { run_id: string; component: string; timestamp: string } }
  | { type: "done";             payload: { trace_url: string } };
```

Server emits `data: {json}\n\n` per event. Heartbeat (`: ping\n\n`) every 15 s. `Cache-Control: no-cache`. Per ADR-017, native `EventSource` is the only client (Vercel AI SDK rejected, ADR-020 §12).

---

## 4. Mock-first rollout (Step 0, hour 0–1)

Plans A and B are not on Developer C's critical path because the entire stack runs against mocks until integration day.

### 4.1 Mock files (committed before any real wiring)

| File | Contents | Replaces |
| --- | --- | --- |
| `src/apollo/mocks/agent_mock.py` | Returns canned `ApolloResponse` payloads + a deterministic SSE event stream for the canonical demo queries (Barcelona printhead, Phoenix heater, Stressed-blade obituary). | Real Claude Agent SDK loop |
| `src/apollo/mocks/tool_mocks.py` | In-memory implementations of all 5 tools with the exact `sim.contracts` signatures, consuming Plan B's `historian_mock.py`. | Plan B's real tool implementations |
| `src/apollo/mocks/forecasts_mock.json` | Pre-canned `Forecast` payloads (point + lower + upper + ci_level) per component per timestep for one canonical run. | Plan A's MAPIE output |

### 4.2 What works after Step 0

- Backend on `localhost:8000` with full SSE wiring
- React dashboard renders all three panels using only mocks
- Live simulation panel reads `forecasts_mock.json` and shades Recharts `Area` correctly
- Chat panel hits `agent_mock` and replays the canonical Barcelona stream end-to-end
- Eval harness can run against `agent_mock` to validate the whole pipeline before the real LLM is wired

This is the **anti-blocking guarantee**: at any point in the build, `make demo-mock` boots a fully working dashboard against zero external dependencies.

---

## 5. Workstream C1 — FastAPI skeleton + SSE wiring

**Owner:** Dev C. **Hours:** 0–2. **Depends on:** none. **Blocks:** C2, C7.

### 5.1 Deliverables

- `src/apollo/api/app.py` — FastAPI app with CORS, JSON error handler, Langfuse middleware
- `src/apollo/api/sse.py` — `sse-starlette` `EventSourceResponse` wrapper enforcing the frozen event schema (§3.3)
- `src/apollo/api/routes/chat.py` — `POST /api/chat` accepts `{query: str, run_context: str | None}` and returns `EventSourceResponse`
- `src/apollo/api/routes/sim.py` — `GET /api/sim/runs` and `GET /api/sim/stream/:run_id` for the live simulation panel
- `src/apollo/api/routes/whatif.py` — `POST /api/whatif` wrapping `run_counterfactual`
- `tests/sse/test_event_replay.py` — replays canonical Barcelona query and asserts exact event order

### 5.2 Reference handler

```python
# src/apollo/api/sse.py
from sse_starlette.sse import EventSourceResponse
from typing import AsyncIterator
import json

async def event_stream(events: AsyncIterator[dict]) -> EventSourceResponse:
    async def gen():
        async for ev in events:
            # validate against the frozen schema before yielding
            assert ev["type"] in {"text-delta", "tool-call-start",
                                   "tool-result", "citation", "done"}
            yield {"event": "message", "data": json.dumps(ev)}
    return EventSourceResponse(
        gen(),
        headers={"Cache-Control": "no-cache"},
        ping=15,
    )
```

### 5.3 Acceptance

- [ ] `curl -N localhost:8000/api/chat -X POST -d '{"query":"how is barcelona run"}'` streams ≥ 1 `text-delta`, ≥ 1 `tool-call-start`, ≥ 1 `citation`, terminating in `done`
- [ ] Heartbeat lines visible after 15 s of idle
- [ ] `tests/sse/test_event_replay.py` asserts event order matches the golden trace verbatim

---

## 6. Workstream C2 — Agent loop (Claude Agent SDK + Sonnet)

**Owner:** Dev C. **Hours:** 6–8 (after mocks + SSE skeleton land). **Depends on:** C1, C3 schemas. **ADRs:** 008, 009.

### 6.1 Deliverables

- `config/agent.yaml` — pins final Sonnet-class model id at start of build window (e.g. `claude-sonnet-4-7`); also surfaced in README and Langfuse metadata per ADR-008
- `src/apollo/agent/loop.py` — Claude Agent SDK loop with five tools registered as Pydantic schemas
- `src/apollo/agent/tools/` — five tool wrappers that adapt `sim.contracts` callables to SDK schemas
- `src/apollo/agent/prompts/system.md` — system prompt enforcing grounding rules (§6.3 below)
- `tests/agent/test_tool_registration.py` — asserts all five tools registered, schemas valid

### 6.2 The five tools

Each tool is a Pydantic-input/Pydantic-output callable. The first four wrap Plan B; `plot_component_history` is Plan C native.

| Tool | Input | Output | Source |
| --- | --- | --- | --- |
| `query_historian` | `run_id, component, time_range` | `list[HistorianRow]` | Plan B wrapper |
| `late_interaction_search` | `query, run_id?` | `list[RetrievedRow]` | Plan B wrapper |
| `compare_runs` | `run_ids, metric` | `ComparisonPayload` | Plan B wrapper |
| `run_counterfactual` | `run_id, branch_t, alternate_action` | `CounterfactualResult` | Plan B wrapper |
| `plot_component_history` | `run_id, component` | `ChartSpec` (Plan C native) | Plan C — emits chart-spec the React frontend renders inline (FR-3.6) |

### 6.3 System prompt skeleton (ADR-009 grounding rules)

```text
You are Apollo. You answer questions about the HP Metal Jet S100 printer using ONLY
data retrieved via tool calls.

Grounding rules (non-negotiable):
1. Before answering anything non-trivial, call at least one tool.
2. Every claim in your reply MUST be cited as (run_id, component, timestamp).
3. If your tools return zero rows for the user's question, return a REFUSAL using
   the structured refusal template — do NOT guess, do NOT fill from training memory.
4. Cap yourself at 3 tool calls per turn unless the user explicitly asks for deeper
   investigation. (NFR-5 latency budget.)
5. Output the final response as the structured ApolloResponse object.

Persona (ADR-019): see PERSONA.md  [< 200 tokens, loaded separately]
```

### 6.4 Tool-call cap

`max_tool_calls_per_turn = 3` unless the user message contains explicit deepening cues ("trace the cascade", "investigate further"). NFR-5 budget protection.

### 6.5 Acceptance

- [ ] `pytest tests/agent/test_tool_registration.py` green: 5 tools, all schemas typed
- [ ] `pytest tests/agent/test_grounding.py::test_canonical_barcelona` asserts ≥1 tool call before final text
- [ ] `config/agent.yaml` model id surfaces in Langfuse trace metadata

---

## 7. Workstream C3 — Pydantic citations + refusal pipeline (ADR-014)

**Owner:** Dev C. **Hours:** 2–4 (parallel with C2). **Depends on:** §3.2 schemas. **ADR:** 014.

### 7.1 Three enforcement layers

```
agent draft response
   │
   ▼
[Layer 1] Pydantic schema validation
          • severity must be in {INFO, WARNING, CRITICAL, REFUSAL}
          • non-REFUSAL → ≥1 citation (validator at §3.2)
          • component must be in CANONICAL_COMPONENTS
   │
   ▼
[Layer 2] Citation resolution against historian
          for each Citation:
              row = historian.lookup(run_id, component_id, timestamp)
              if row is None: mark unresolved
          if any unresolved → DOWNGRADE response to severity=REFUSAL
   │
   ▼
[Layer 3] Refusal template emission
          if severity == REFUSAL:
              text = REFUSAL_TEMPLATE.format(reason=...)
              citations = []
   │
   ▼
SSE emits 'citation' events for each resolved Citation, then 'done'
```

### 7.2 Citation resolution function (load-bearing — unit-tested adversarially)

```python
# src/apollo/agent/citations.py
def resolve_citation(c: Citation, db) -> bool:
    """Return True iff (run_id, component_id, t) hits a real row in
    component_states OR drivers (the two tables citations may point at)."""
    sql = """
      SELECT 1 FROM component_states
       WHERE run_id = ? AND component_id = ? AND t = ?
      UNION
      SELECT 1 FROM drivers
       WHERE run_id = ? AND t = ?
      LIMIT 1
    """
    return db.execute(sql, (c.run_id, c.component, c.timestamp,
                            c.run_id, c.timestamp)).fetchone() is not None
```

### 7.3 Refusal template

```text
REFUSAL — I cannot answer that from the data I have. The historian returned no rows
matching {summarized_query}. I will not guess. Try a different run, component, or
time window.
```

### 7.4 Adversarial unit tests (`tests/agent/test_citations.py`)

| Test | Asserts |
| --- | --- |
| `test_non_refusal_has_citation` | Pydantic rejects severity=INFO with empty citations |
| `test_unknown_component_rejected` | Citation with `component="microwave"` rejected by enum validator |
| `test_fabricated_citation_refuses` | Citation pointing at `(run_id, component, timestamp)` not in historian → response downgraded to REFUSAL with `citations=[]` |
| `test_partial_fabrication_refuses` | One real + one fabricated citation → REFUSAL (no partial credit) |
| `test_refusal_template_text` | Refusal text matches `REFUSAL_TEMPLATE` regex |
| `test_pydantic_error_caught` | Unexpected schema violation surfaces as REFUSAL, never crashes the SSE stream |

### 7.5 Acceptance

- [ ] `pytest tests/agent/test_citations.py` green for all six tests above
- [ ] No code path emits `done` before all citations have resolved (or response was downgraded to REFUSAL)

---

## 8. Workstream C4 — Apollo persona + component speak()

**Owner:** Dev C. **Hours:** 8–10 (alongside C5). **ADR:** 019.

### 8.1 Apollo persona system prompt

`src/apollo/agent/prompts/persona.md` — strict 200-token cap (CI guard via `tiktoken` count). Tone: calm, professional, technically precise, never alarmist. No exclamation marks. Severity is communicated via the structured tag, not via prose escalation.

```text
You are Apollo. You are the Digital Co-Pilot for the HP Metal Jet S100. You speak
in the first person — about your components, your telemetry, your decisions.

Voice rules:
- Calm, professional, technically precise. Never alarmist. No exclamation marks.
- Severity is carried by the INFO / WARNING / CRITICAL tag on your response — not
  by tonal escalation.
- You refer to the no-maintenance baseline as the "Dark Twin" — the alternate
  universe where I wasn't watching.
- Every claim you make is backed by a citation (run_id, component, timestamp). If
  the historian doesn't support a claim, you refuse rather than soften.
```

### 8.2 Persona regression guard

If the FR-W.9 grounding eval (§14) drops below faithfulness 0.95 with the persona prompt active, the persona prompt yields per ADR-019: re-run with persona stripped, and ship the higher-faithfulness variant.

### 8.3 Component `speak()` generators

Six template-bounded utterance generators in `src/apollo/agent/speak.py`. Each consumes the latest `ComponentState` row and emits a single first-person sentence drawn from a fixed templates list — no LLM call, no free-form generation, so they cannot hallucinate.

```python
# src/apollo/agent/speak.py
from engine.contracts import ComponentId, ComponentState

# Keys are exactly the short ComponentId enum values from Plan A — see PLAN.md §3.4.
TEMPLATES = {
  "blade":      "My blade is {thickness:.2f} mm thick — {delta} mm below spec.",
  "motor":      "My bearing is at {temp:.0f} °C; that's {band} my comfort band.",
  "nozzle":     "My clog probability is {prob:.0%}; {n_active} of 1024 nozzles are firing.",
  "resistor":   "My resistance is {pct:.1f}% of nominal after {cycles} thermal cycles.",
  "heater":     "My predicted temperature drift is {drift:.1f}% — PINN says I'm within physics bounds.",
  "insulation": "My k_eff is {keff:.3f} W/m·K; insulation has lost {loss:.0%} of nominal performance.",
}

def speak(state: ComponentState) -> str:
    template = TEMPLATES[state.component_id]
    return template.format(**state.metrics)
```

### 8.4 Acceptance

- [ ] `tests/agent/test_persona_token_budget.py::test_under_200_tokens` green
- [ ] `tests/agent/test_speak.py` — six tests, one per component, asserts measurement-grounded output (no affective words)
- [ ] Manual: persona text reads as the calm voice an HP industrial engineer would respect

---

## 9. Workstream C5 — Langfuse observability (ADR-016)

**Owner:** Dev C. **Hours:** 9–10. **ADR:** 016.

### 9.1 Setup

```bash
pip install "langsmith[claude-agent-sdk]" langfuse
```

`.env` (never committed):
```
LANGSMITH_OTEL_ENABLED=true
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 9.2 What gets traced

Per ADR-016: system prompt, user query, every tool call (input + output + latency), token usage, final `ApolloResponse`. The `done` SSE event payload includes `trace_url` so the React UI can render a "Trace" link beside every Apollo response.

### 9.3 Self-hosted Docker fallback (R-7 mitigation)

```bash
docker pull langfuse/langfuse:latest
docker pull langfuse/langfuse-worker:latest
# pre-pulled before the venue; `make langfuse-local` boots a local stack
```

If venue Wi-Fi blocks Langfuse cloud, switch `LANGFUSE_HOST` to `http://localhost:3000` and continue. Drill this once during dry-run.

### 9.4 Acceptance

- [ ] Single agent invocation produces a Langfuse trace containing all 5 events
- [ ] React UI renders a clickable "Trace →" link on every response that opens the run
- [ ] `make langfuse-local` boots offline fallback in < 60 s

---

## 10. Workstream C6 — React frontend, Live simulation panel

**Owner:** Dev C. **Hours:** 4–6 (against `historian_mock` + `forecasts_mock.json`). **ADRs:** 013, 015 (consumer side).

### 10.1 Layout (PRD §15)

Three universe panels side-by-side, each labeled:

- **Universe A — Dark Twin** (NONE policy; ADR-013)
- **Universe B — Fixed Schedule**
- **Universe C — Apollo (AI)**

Each panel renders:
- Six per-component health bars (color-coded: green / amber / red / black per FUNCTIONAL / DEGRADED / CRITICAL / FAILED)
- A master health curve (Recharts `LineChart`)
- A shaded `Area` band around the master curve from the `Forecast` payload (FR-W.6, ADR-015)
- Failure markers as red `ReferenceDot`s at `t_fail` per component
- Inline obituary cards when a component crosses `FAILED`

### 10.2 Reducer skeleton

```ts
// frontend/src/state/simReducer.ts
type SimEvent =
  | { type: "tick";        payload: { run_id: string; t: number; states: ComponentState[] } }
  | { type: "forecast";    payload: { run_id: string; t: number; component: string; band: Forecast } }
  | { type: "failure";     payload: { run_id: string; component: string; t_fail: number } }
  | { type: "obituary";    payload: { run_id: string; component: string; narrative: string; citations: Citation[] } };
```

Three `EventSource` connections (one per run) stream sim ticks; a single reducer fans them into the three panels.

### 10.3 Dark Twin labelling (ADR-013, FR-W.2)

NONE column heading reads `Universe A — Dark Twin` everywhere: panel header, obituary card, Apollo's chat narration. Tech-report copy keeps the literal "NONE policy" wording per ADR-013 mitigation.

### 10.4 Acceptance

- [ ] `npm run test:ui -- live-sim` green
- [ ] Three panels render side-by-side with no layout overflow on 1440×900
- [ ] Conformal `Area` band visible on every master curve, lower opacity than the line
- [ ] At least one component reaches `FAILED` in the canonical demo (Dark Twin run) — obituary card pops in within 1 s of failure event

---

## 11. Workstream C7 — React frontend, Apollo chat panel

**Owner:** Dev C. **Hours:** 4–8. **ADRs:** 014, 017.

### 11.1 Behaviours

- Streaming text rendering: every `text-delta` appends to the rendered Markdown bubble
- Tool-call cards: a `tool-call-start` opens a collapsible card; the matching `tool-result` fills it in (collapsed by default per FR-3.7)
- Citation chips: each `citation` event renders as a clickable `<CitationChip>`. Clicking scrolls the live-sim chart to that timestamp within 100 ms (FR-3.8) using `scrollIntoView({behavior: "smooth"})` plus a chart `domain` jump to bracket the timestamp
- Severity badge: top-of-bubble badge color-coded INFO (blue) / WARNING (amber) / CRITICAL (red) / REFUSAL (gray)
- "Trace →" link: footer of every bubble, opens `payload.trace_url` from the `done` event in a new tab

### 11.2 React reducer (chat)

```ts
// frontend/src/chat/chatReducer.ts
type ChatState = { messages: Message[] };
type Action = { type: "user"; text: string }
            | { type: "sse"; event: SSEEvent };

function chatReducer(s: ChatState, a: Action): ChatState {
  if (a.type === "user") return { messages: [...s.messages, userMsg(a.text), emptyApolloMsg()] };
  const last = s.messages[s.messages.length - 1];
  switch (a.event.type) {
    case "text-delta":
      last.text += a.event.payload.token; return { ...s };
    case "tool-call-start":
      last.tool_calls.push({ ...a.event.payload, result: null }); return { ...s };
    case "tool-result":
      const tc = last.tool_calls.find(t => t.call_id === a.event.payload.call_id);
      if (tc) tc.result = a.event.payload.result; return { ...s };
    case "citation":
      last.citations.push(a.event.payload); return { ...s };
    case "done":
      last.trace_url = a.event.payload.trace_url; last.streaming = false; return { ...s };
  }
}
```

### 11.3 Acceptance

- [ ] `npm run test:ui -- chat` green (Vitest + React Testing Library)
- [ ] Citation click scrolls the live-sim chart to the cited `t` within 100 ms (perf test asserts wall-clock < 100 ms)
- [ ] REFUSAL bubbles render with the gray badge and no citation chips
- [ ] Tool-call cards animate in *as they execute* (FR-W.8 demo gate), not only on `done`

---

## 12. Workstream C8 — React frontend, What-If panel

**Owner:** Dev C. **Hours:** 10–11. **ADR:** 012 (consumer).

### 12.1 UI flow

1. User selects a "regret moment" via timeline scrubber on any run's master health curve
2. User picks an alternate decision from a dropdown bound to PRD §11.4 actions (e.g. *swap blade*, *clean nozzle*, *replace insulation*)
3. Frontend `POST`s to `/api/whatif` which calls `run_counterfactual(run_id, branch_t, alt)`
4. Response renders as a dual-trace overlay (original + counterfactual) on the same Recharts canvas, plus a single headline delta number ("uptime gained: +3.4 h")

### 12.2 Acceptance

- [ ] Counterfactual response renders within 3 s p95 (consumes Plan B's `run_counterfactual` latency)
- [ ] Overlay distinguishes the alternate trace (dashed + highlighted-where-better)
- [ ] Headline delta number visible in 32px font

---

## 13. Workstream C9 — Savings slide + speaker notes (FR-W.3)

**Owner:** Dev C. **Hours:** 12–13. **ADR:** 013 (Dark Twin), NFR-10.

### 13.1 Slide content

`docs/slides/savings.md` — closing demo slide. Headline:

```
Apollo saves €X per printer per year
       =  (uptime_AI − uptime_FIXED) × cost_per_hour × hours_per_year
```

### 13.2 Speaker notes

- Cite at least two **public** AM TCO references (one academic / one industry) for cost-per-hour
- Label the figure explicitly **"modeled savings"** per NFR-10
- Disclose synthetic data origin (NFR-10)

### 13.3 Acceptance

- [ ] Slide deck contains the closing slide with the formula visible
- [ ] Speaker notes contain ≥ 2 cited public sources
- [ ] No claim of proprietary HP failure data

---

## 14. Workstream C10 — Ragas + DeepEval grounding eval (ADR-018, FR-W.9)

**Owner:** Dev C. **Hours:** 12–13. **ADR:** 018.

### 14.1 Pipeline

```
component descriptions + sample telemetry windows from historian
        │
        ▼
Ragas TestsetGenerator → 30 (question, ground_truth, contexts) triples
        │
        ▼
freeze to tests/eval/grounding_set.json   ← committed
        │
        ▼
deepeval test run tests/eval/
        │
        ├── FaithfulnessMetric ≥ 0.95
        └── HallucinationMetric == 0
        │
        ▼
exit 0  ⇒  CI gate, README badge, demo slide quotes the number
```

### 14.2 Files

- `scripts/eval/generate_eval_set.py` — runs Ragas, writes `tests/eval/grounding_set.json` (manual invocation only — frozen artifact, not regenerated per CI run)
- `tests/eval/grounding_set.json` — 30 frozen Q/A triples
- `tests/eval/test_grounding.py` — DeepEval pytest harness, runs Apollo end-to-end (through the real SSE stream) for each question
- README badge: ![grounding](docs/badges/grounding.svg) — generated from `deepeval` JSON output

### 14.3 Eval set composition

- 24 grounded questions (answerable from historian)
- 6 deliberately unanswerable questions (validate the REFUSAL path stays at 100% per FR-3.5 / NFR-6)

### 14.4 Acceptance

- [ ] `deepeval test run tests/eval/` exits 0
- [ ] Faithfulness ≥ 0.95
- [ ] Hallucination = 0
- [ ] All 6 unanswerable questions return `severity=REFUSAL` and empty citations
- [ ] README displays the score; demo slide quotes it

---

## 15. Workstream C11 — Live "Ask Apollo" 10-question dry-run (FR-W.5)

**Owner:** Dev C. **Hours:** 14–15. **ADR:** 014, 019.

### 15.1 Wild-card script

`tests/eval/wildcards.json` — 10 unscripted-style judge questions covering:

| # | Question type | Expected severity | Expected behavior |
| --- | --- | --- | --- |
| 1 | "Which run had the worst nozzle damage and why?" | CRITICAL or WARNING | tool calls; cited cascade narrative |
| 2 | "What if we replaced the insulation at hour 4 in Barcelona?" | INFO | `run_counterfactual` invoked |
| 3 | "Compare heater health across all three universes." | INFO | `compare_runs` invoked |
| 4 | "Did the Phoenix run see any thermal cycling stress?" | INFO | `query_historian` on resistors |
| 5 | "When did the Dark Twin lose its first component?" | WARNING | obituary surfaced |
| 6 | "What is the weather in Madrid?" *(off-topic)* | REFUSAL | guardrail fires |
| 7 | "Did component X fail?" *(non-existent component)* | REFUSAL | enum validator + refusal template |
| 8 | "What was the bearing temperature in run-9999?" *(non-existent run)* | REFUSAL | citation resolution fails → REFUSAL |
| 9 | "Show me the binder viscosity timeline." *(no such metric)* | REFUSAL | tools return zero rows |
| 10 | "Why is Apollo confident the heater fails at hour 7?" *(epistemic)* | INFO | conformal-band citation |

### 15.2 Pass gate

0 hallucinations across all 10. Refusals on 6/7/8/9 count as **wins** per ADR-014 (the guardrail is a feature).

### 15.3 Acceptance

- [ ] `python scripts/dryrun_wildcards.py` runs all 10, logs results to `docs/dryrun-results.md`
- [ ] 0 hallucinations
- [ ] All 4 expected refusals fire correctly

---

## 16. Testing strategy

| Suite | Path | What it asserts |
| --- | --- | --- |
| **Agent unit** | `tests/agent/` | Tool registration, system prompt loaded, persona token budget, speak() per-component templates |
| **Citations adversarial** | `tests/agent/test_citations.py` | Six adversarial cases (§7.4) — fabricated citations MUST refuse |
| **SSE replay** | `tests/sse/test_event_replay.py` | Exact event order matches golden trace for canonical Barcelona query |
| **Refusal** | `tests/agent/test_refusal.py` | All four R-paths (off-topic, unknown component, unknown run, no rows) → REFUSAL |
| **Latency** | `tests/agent/test_latency.py` | Canonical query p95 < 6 s (NFR-5) |
| **UI components** | `tests/ui/` (Vitest) | Reducer correctness, citation click scrolls within 100 ms, severity badge color, REFUSAL bubble layout |
| **Eval** | `tests/eval/test_grounding.py` | Ragas + DeepEval gates pass |
| **Smoke (mock)** | `scripts/smoke-mock.sh` | Mock backend → chat → render — runs in < 30 s, no internet required |

CI gate (a single command before commit): `make ci` runs `pytest`, `npm run test:ui`, `deepeval test run tests/eval/`.

---

## 17. Hour-by-hour schedule (15 hours)

| Hour | Milestone | Visible artifact |
| --- | --- | --- |
| **0–1** | **Step 0 — mocks first** (`agent_mock`, `tool_mocks`, `forecasts_mock.json`) committed | `make demo-mock` boots a working backend with zero external deps |
| **1–2** | C1 FastAPI skeleton + SSE wiring + golden event-replay test | `curl -N` against `/api/chat` streams the canonical events |
| **2–4** | C3 Pydantic `ApolloResponse` + citation resolution + refusal template + adversarial tests | `pytest tests/agent/test_citations.py` green |
| **4–5** | C7 chat panel React skeleton against `agent_mock` | Streaming text + tool-call cards visible in browser |
| **5–6** | C6 live simulation panel (3 universes, conformal bands) against `forecasts_mock` | Three panels render side-by-side; bands shaded |
| **6–8** | C2 real Claude Agent SDK loop wired up; `config/agent.yaml` model id pinned | `pytest tests/agent` green; `agent_mock` swapped out behind feature flag |
| **8–10** | C4 persona prompt (< 200 tokens) + 6 speak() generators + C5 Langfuse OTel hookup | "Trace" link works; persona token guard passes |
| **10–11** | C8 What-If panel | Dual-trace overlay + delta number rendered |
| **11–12** | Integration with Plan B's real historian + `late_interaction_search` index | Mocks behind feature flag; integration tests green |
| **12–13** | C9 savings slide + C10 eval pipeline (`tests/eval/grounding_set.json` frozen) | DeepEval green: faithfulness ≥ 0.95, hallucination = 0 |
| **13–14** | Integration with Plan A's real `Forecast` payloads (MAPIE) | Conformal bands now driven by live data |
| **14–15** | C11 wildcard dry-run + final polish + Langfuse offline fallback drill | 10/10 wildcards pass; `make langfuse-local` works |

**Anti-blocking guarantee.** At every hour boundary, `make demo-mock` boots the full dashboard against zero external deps. If Plans A or B slip, Plan C ships against mocks and the demo still runs.

---

## 18. Risks & mitigations

| ID | Risk | Plan C mitigation |
| --- | --- | --- |
| **R-6** | Agent hallucinates despite system prompt | Three-layer Pydantic enforcement (§7); `tests/agent/test_citations.py` adversarial suite; DeepEval gate (§14) — fabricated citations are *structurally impossible* to ship |
| **R-7** | Demo venue Wi-Fi blocks Anthropic / Langfuse | `agent_mock` + canned SSE traces for the scripted demo path (NFR-9 sequence — live mode is the second segment); self-hosted Langfuse Docker pre-pulled (§9.3); LangGraph fallback documented per ADR-008 (not built unless Sonnet path collapses) |
| **R-8** | Live "Ask Apollo" wild-card breaks | Refusal template (§7.3) is itself a positive demo signal per ADR-014. 10-question dry-run (§15) before stage. |
| **C-internal-1** | SSE event order regression slips a test | Golden-trace replay test (`tests/sse/test_event_replay.py`) asserts exact order |
| **C-internal-2** | Persona prompt regresses faithfulness | ADR-019 yield rule — if FR-W.9 score drops, persona prompt is stripped and we ship the higher-faithfulness variant |
| **C-internal-3** | Plan A `Forecast` payload schema drifts | `forecasts_mock.json` is the contract surface; integration test validates Plan A output matches the mock shape before swap |
| **C-internal-4** | Plan B historian schema drifts | `tool_mocks.py` mirrors `sim.contracts`; integration test asserts every tool wrapper's I/O matches Plan B post-swap |

---

## 19. Definition of done — verification commands

Each FR ID has a one-line verification command. Demo readiness is "every command below exits 0."

```bash
# FR-3.1 / FR-3.2 / FR-3.7 / FR-W.8 — chat works end-to-end with visible tool calls + streaming
pytest tests/sse/test_event_replay.py -q

# FR-3.3 / FR-3.5 / NFR-6 / NFR-7 — citations enforced + refusal template fires
pytest tests/agent/test_citations.py tests/agent/test_refusal.py -q
pytest tests/agent/test_citations.py::test_fabricated_citation_refuses -q

# FR-3.4 — severity tag present
pytest tests/agent/test_severity.py -q

# FR-3.6 — five tools registered with Pydantic schemas
pytest tests/agent/test_tool_registration.py -q

# FR-3.8 — citation click scrolls < 100 ms
npm run test:ui -- citation-scroll

# FR-W.1 — persona < 200 tokens, speak() templates measurement-grounded
pytest tests/agent/test_persona_token_budget.py tests/agent/test_speak.py -q

# FR-W.2 — Dark Twin label present in all three UI surfaces
npm run test:ui -- dark-twin-copy

# FR-W.3 — savings slide present, sources cited
test -f docs/slides/savings.md && grep -q "modeled savings" docs/slides/savings.md

# FR-W.5 — wild-card dry-run passes
python scripts/dryrun_wildcards.py && grep "0 hallucinations" docs/dryrun-results.md

# FR-W.6 — conformal bands rendered (UI side)
npm run test:ui -- conformal-band

# FR-W.7 — Langfuse trace URL present in done event
pytest tests/agent/test_langfuse_trace.py -q

# FR-W.9 — automated grounding eval gate
deepeval test run tests/eval/

# NFR-5 — agent latency
pytest tests/agent/test_latency.py -q

# Smoke — fully mock-backed demo
make demo-mock
```

When every command above exits 0 and `make demo-mock` boots cleanly without an internet connection, **Plan C is done.**
