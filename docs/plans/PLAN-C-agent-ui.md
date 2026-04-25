# Plan C — Agent & UI

> Owner: **Developer C** (solo slice, parallel with Plan A — Engine and Plan B — Simulation).
> Scope: Phase 3 "Apollo" agent + the entire React frontend + observability + automated grounding eval + **GEPA prompt compile + three-way Gemma/Opus comparison** (ADR-022, FR-W.10/W.11).
> Time budget: **19 hours** (was 15h before ADR-022; +4h for the C12 workstream), mocks-first so Plans A and B never block Developer C.
> Source of truth: PRD v1.1 (FR-3.x, FR-W.1/2/3/5/7/8/9/**10/11**, NFR-5/6/7), ADR-008 *(loop only — model superseded)*/009/010/013/014/016/017/018/019/020/**022**.

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
| **FR-W.10** | GEPA-compiled system prompt for Gemma 4 31B (ADR-022) | `scripts/agent/compile_prompt.py` runs `dspy.GEPA(student=Gemma-4-31B, reflection=Opus-4.7-via-claude-CLI, metric=DeepEval+schema+citation-resolves)` over the FR-W.9 set; commits `config/agent.system_prompt.gepa.txt` and `docs/eval/gepa_compile_log.json`; runtime agent loads the compiled prompt at startup |
| **FR-W.11** | Three-way grounding eval comparison (ADR-022) | `scripts/agent/run_comparison.py` runs the FR-W.9 eval against {vanilla Opus 4.7, vanilla Gemma 4 31B, GEPA-Gemma}; logs to `docs/eval/comparison_results.json`; closing demo slide quotes the table; GEPA-Gemma row within 2pp of Opus-4.7 on faithfulness, hallucination = 0 on both |

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
| **ADR-008** | Claude Agent SDK *(loop framework — model partially superseded by ADR-022)* | Loop framework for §6 (workstream C2): Pydantic-typed tools, OTel hookup, refusal handling. **Runtime model is Gemma 4 31B per ADR-022, not Sonnet.** |
| **ADR-022** | Gemma 4 31B + GEPA-compiled prompt as runtime LM | Drives the C2 model swap (§6) and the new C12 workstream (§14a) — offline `dspy.GEPA` prompt compile + three-way comparison vs vanilla Opus 4.7 + vanilla Gemma. Unlocks MLH "Best Use of Gemma". |
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

## 6. Workstream C2 — Agent loop (Claude Agent SDK + Gemma 4 31B)

**Owner:** Dev C. **Hours:** 6–8 (after mocks + SSE skeleton land). **Depends on:** C1, C3 schemas. **ADRs:** 008 *(loop framework only)*, 009, **022 *(model)***.

### 6.1 Deliverables

- `config/agent.yaml` — pins **Gemma 4 31B Dense** as runtime LM (`provider: openai`, `model: google/gemma-4-31B-it`, `api_base` from MLH-issued key); also surfaced in README and Langfuse metadata per ADR-022. *Sonnet-class model id is no longer pinned here — see ADR-022 supersession of ADR-008's model choice.*
- `src/apollo/agent/loop.py` — Claude Agent SDK loop with five tools registered as Pydantic schemas, wired to the Gemma endpoint via DSPy's `dspy.LM("openai/google/gemma-4-31B-it", api_base=..., api_key=...)`
- `src/apollo/agent/tools/` — five tool wrappers that adapt `sim.contracts` callables to SDK schemas
- `src/apollo/agent/prompts/system.md` — *seed* system prompt with grounding rules (§6.3 below). **This is the input to the GEPA compile (workstream C12); the runtime agent loads `config/agent.system_prompt.gepa.txt` instead, falling back to this seed only if the compiled artifact is missing.**
- `tests/agent/test_tool_registration.py` — asserts all five tools registered, schemas valid
- `tests/agent/test_runtime_lm_is_gemma.py` — asserts `config/agent.yaml`'s model id starts with `google/gemma-4-31B` (CI guard against accidental revert to Sonnet)

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
- [ ] `pytest tests/agent/test_runtime_lm_is_gemma.py` green (model id starts with `google/gemma-4-31B`)
- [ ] `config/agent.yaml` model id surfaces in Langfuse trace metadata as `google/gemma-4-31B-it`

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

## 14a. Workstream C12 — GEPA prompt compile + three-way comparison (FR-W.10, FR-W.11)

**Owner:** Dev C. **Hours:** 13–17 (after eval set is frozen in C10; runs while C11 dry-run prep happens in parallel — GEPA compile is offline so it can chew on the eval set in the background). **Depends on:** C2 (Gemma agent wired), C3 (citation pipeline), C10 (frozen `tests/eval/grounding_set.json`). **ADR:** 022.

### 14a.1 Why this is its own workstream, not part of C2

C2 wires the agent loop to Gemma 4 31B with a hand-written *seed* system prompt. That seed is acceptable enough to pass smoke tests but is not the prompt that ships. The **runtime prompt is compiled by `dspy.GEPA` against the FR-W.9 eval set**. Per ADR-022 the compile is offline, scripted, and produces a frozen artifact (`config/agent.system_prompt.gepa.txt`) the agent loads at startup. This is the MLH "Best Use of Gemma" deliverable and the differentiation thesis of the demo.

### 14a.2 Deliverables

- `scripts/agent/compile_prompt.py` — runs `dspy.GEPA` end-to-end:
  - Student LM: `dspy.LM("openai/google/gemma-4-31B-it", api_base=…, api_key=…)`
  - Reflection LM: a thin DSPy `LM` adapter that shells out to the local `claude` CLI (Bash) for Claude Opus 4.7 reflections — no separate API key needed beyond the existing `claude` setup
  - Metric: `metric_with_feedback` combining DeepEval `FaithfulnessMetric` (already in C10) + `HallucinationMetric` + three programmatic signals (schema valid, correct tool selected, all citations resolve via §7.2's `resolve_citation`); the textual feedback string is verbose and diagnostic — that's the optimization channel (per Decagon production notes)
  - Trainset: 20 of the 30 frozen FR-W.9 Q/A triples; valset: 10. Held-out test set lives in C10's existing pipeline so the gate that ships the prompt is independent of the gate that compiled it.
  - Budget: `max_metric_calls=150` (raise to 300 if first run plateaus — see §20 PRD open question)
- `config/agent.system_prompt.gepa.txt` — committed compiled prompt artifact; loaded by `src/apollo/agent/loop.py` at startup (falls back to `prompts/system.md` seed if missing)
- `docs/eval/gepa_compile_log.json` — committed structured optimization log: per-iteration scores, parent-candidate genealogy, total tokens consumed, wall-clock time
- `scripts/agent/run_comparison.py` — runs the FR-W.9 DeepEval pipeline against three configurations, logs to `docs/eval/comparison_results.json`:
  1. **Vanilla Opus 4.7** — Apollo loop with `claude` CLI as runtime LM, seed `prompts/system.md`
  2. **Vanilla Gemma 4 31B** — Apollo loop on Gemma, seed `prompts/system.md`
  3. **GEPA-Gemma** — Apollo loop on Gemma, compiled `config/agent.system_prompt.gepa.txt`
- `docs/slides/comparison.md` — closing demo slide table generated from `comparison_results.json`; speaker notes explain the GEPA paradigm in two sentences with the Databricks gpt-oss-120b precedent cited

### 14a.3 Two-LM architecture (HF DSPy GEPA cookbook pattern)

```python
# scripts/agent/compile_prompt.py (sketch)
import dspy, json
from dspy.teleprompt.gepa import GEPA
from src.apollo.agent.loop import build_apollo_signature, METRIC_WITH_FEEDBACK

student = dspy.LM(
    "openai/google/gemma-4-31B-it",
    api_base=os.environ["GEMMA_API_BASE"],
    api_key=os.environ["GEMMA_API_KEY"],
    model_type="chat",
)
reflector = dspy.LM("claude_cli/opus-4-7")  # adapter shells to `claude --print …`
dspy.configure(lm=student)

trainset, valset = load_split("tests/eval/grounding_set.json", n_train=20, n_val=10)

apollo = build_apollo_signature()  # dspy.ReAct over the 5 tools
optimized = GEPA(
    metric=METRIC_WITH_FEEDBACK,
    reflection_lm=reflector,
    max_metric_calls=150,
    track_stats=True,
).compile(student=apollo, trainset=trainset, valset=valset)

# persist the compiled prompt + log
optimized.save("config/agent.system_prompt.gepa.txt")
json.dump(optimized.compile_stats, open("docs/eval/gepa_compile_log.json", "w"))
```

The `claude_cli` provider is a small DSPy `LM` subclass — ~30 lines wrapping `subprocess.run(["claude", "--print", "--model", "opus-4-7", prompt])`. Lives in `src/apollo/agent/lm/claude_cli.py`.

### 14a.4 Metric with feedback (the load-bearing piece)

Per the Decagon production GEPA tuning notes, **80% of the gain comes from the textual feedback string in the metric**, not from the metric's scalar score. So the metric returns *both*:

```python
# src/apollo/agent/metric.py (sketch)
def METRIC_WITH_FEEDBACK(example, pred, trace=None) -> dspy.Prediction:
    score, feedback = 0.0, []

    # 1. Schema validity on every tool call
    for tc in pred.tool_calls:
        ok, err = validate_tool_args(tc)
        if not ok: feedback.append(f"INVALID TOOL ARGS for {tc.tool}: {err}")
    if all(validate_tool_args(tc)[0] for tc in pred.tool_calls): score += 0.2

    # 2. Citation resolves against the historian (the §7 ACL invariant)
    unresolved = [c for c in pred.citations if not resolve_citation(c, db)]
    if unresolved: feedback.append(f"FABRICATED CITATIONS: {unresolved} — these triples don't exist in the historian.")
    elif pred.severity != "REFUSAL": score += 0.3

    # 3. Refused when no telemetry exists (FR-3.5)
    if example.is_unanswerable and pred.severity != "REFUSAL":
        feedback.append("MUST REFUSE: no telemetry supports this question; do not guess.")
    elif example.is_unanswerable: score += 0.2

    # 4. DeepEval faithfulness on the prose
    faith = DeepEvalFaithfulness().score(pred.text, contexts=example.contexts)
    score += 0.3 * faith
    if faith < 0.95: feedback.append(f"LOW FAITHFULNESS ({faith:.2f}): claim {worst_claim(pred)} not supported by retrieved context.")

    return dspy.Prediction(score=score, feedback="\n".join(feedback) or "OK")
```

### 14a.5 Acceptance

- [ ] `python scripts/agent/compile_prompt.py` runs end-to-end in < 4 hours, producing a non-empty `config/agent.system_prompt.gepa.txt` and `docs/eval/gepa_compile_log.json`
- [ ] Compiled prompt token count < 800 (GEPA produces shorter prompts than MIPROv2, per Agrawal et al. — guard against bloat)
- [ ] Persona regression check (ADR-019, §8.2) still passes against the compiled prompt — if the compiled prompt drops faithfulness vs persona-stripped, ship the higher-faithfulness variant
- [ ] `python scripts/agent/run_comparison.py` produces `docs/eval/comparison_results.json` with three rows; GEPA-Gemma row's faithfulness within 2pp of Opus-4.7 row, hallucination = 0 on both
- [ ] `tests/agent/test_compiled_prompt_loads.py` — agent startup loads `config/agent.system_prompt.gepa.txt` (not the seed) when the compiled file exists
- [ ] Closing demo slide (`docs/slides/comparison.md`) renders the three-row comparison table; speaker notes cite Agrawal et al. arXiv:2507.19457 and the Databricks gpt-oss-120b precedent

### 14a.6 Risks specific to C12

| Risk | Mitigation |
| --- | --- |
| GEPA-Gemma underperforms vanilla Gemma (over-fits the trainset) | Hold-out test gate in C10 is independent; if compiled prompt loses on held-out, raise `max_metric_calls` and re-compile, or fall back to seed prompt with a feature flag |
| GEPA-Gemma comes within 5pp but not 2pp of Opus 4.7 | Acceptable — pitch becomes "open model approaches frontier" instead of "matches frontier"; still wins MLH "Best Use of Gemma" |
| `claude` CLI rate-limits during compile | GEPA only calls reflection LM ~10-15 times; rate is not a real constraint at 150 metric calls |
| Compiled prompt leaks model-specific quirks | Keep the seed prompt readable + the compiled prompt in git so any judge can diff them; transparency is a feature |

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
| **GEPA artifact** | `tests/agent/test_compiled_prompt_loads.py` | Agent loads `config/agent.system_prompt.gepa.txt` at startup; runtime LM is Gemma; compiled prompt < 800 tokens (FR-W.10) |
| **Three-way comparison** | `scripts/agent/run_comparison.py --check` | `docs/eval/comparison_results.json` exists with three rows; GEPA-Gemma faithfulness within 2pp of Opus-4.7 (FR-W.11) |
| **Smoke (mock)** | `scripts/smoke-mock.sh` | Mock backend → chat → render — runs in < 30 s, no internet required |

CI gate (a single command before commit): `make ci` runs `pytest`, `npm run test:ui`, `deepeval test run tests/eval/`.

---

## 17. Hour-by-hour schedule (19 hours, +4h vs. pre-ADR-022)

| Hour | Milestone | Visible artifact |
| --- | --- | --- |
| **0–1** | **Step 0 — mocks first** (`agent_mock`, `tool_mocks`, `forecasts_mock.json`) committed | `make demo-mock` boots a working backend with zero external deps |
| **1–2** | C1 FastAPI skeleton + SSE wiring + golden event-replay test | `curl -N` against `/api/chat` streams the canonical events |
| **2–4** | C3 Pydantic `ApolloResponse` + citation resolution + refusal template + adversarial tests | `pytest tests/agent/test_citations.py` green |
| **4–5** | C7 chat panel React skeleton against `agent_mock` | Streaming text + tool-call cards visible in browser |
| **5–6** | C6 live simulation panel (3 universes, conformal bands) against `forecasts_mock` | Three panels render side-by-side; bands shaded |
| **6–8** | C2 real Claude Agent SDK loop wired to **Gemma 4 31B** via DSPy `dspy.LM` adapter; `config/agent.yaml` pins `google/gemma-4-31B-it`; seed `prompts/system.md` in place | `pytest tests/agent` green incl. `test_runtime_lm_is_gemma`; `agent_mock` swapped out behind feature flag |
| **8–10** | C4 persona prompt (< 200 tokens) + 6 speak() generators + C5 Langfuse OTel hookup | "Trace" link works; persona token guard passes |
| **10–11** | C8 What-If panel | Dual-trace overlay + delta number rendered |
| **11–12** | Integration with Plan B's real historian + `late_interaction_search` index | Mocks behind feature flag; integration tests green |
| **12–13** | C9 savings slide + C10 eval pipeline (`tests/eval/grounding_set.json` frozen — this is the GEPA target) | DeepEval green: faithfulness ≥ 0.95, hallucination = 0 on seed prompt |
| **13–14** | Integration with Plan A's real `Forecast` payloads (MAPIE) | Conformal bands now driven by live data |
| **14–17** | **C12 GEPA prompt compile (offline, ~3h wall-clock)** + `claude_cli` reflection adapter + comparison harness | `config/agent.system_prompt.gepa.txt` committed; `docs/eval/gepa_compile_log.json` shows monotonic score improvement; `docs/eval/comparison_results.json` rendered to `docs/slides/comparison.md` |
| **17–18** | C11 wildcard dry-run against the **GEPA-compiled** Apollo + Langfuse offline fallback drill | 10/10 wildcards pass on GEPA-Gemma; `make langfuse-local` works |
| **18–19** | Final polish + slide deck + decompile-vs-seed prompt diff for the demo "we evolved this" beat | Demo deck includes both the seed and compiled prompts side-by-side |

**Anti-blocking guarantee.** At every hour boundary, `make demo-mock` boots the full dashboard against zero external deps. If Plans A or B slip, Plan C ships against mocks and the demo still runs.

**C12-specific anti-blocking.** If the GEPA compile crashes or underperforms the seed prompt on the held-out gate, `config/agent.yaml` flips one flag (`AGENT_SYSTEM_PROMPT=seed|gepa`) and Apollo runs on the seed. The comparison harness then logs only two rows (vanilla Opus, vanilla Gemma); the MLH narrative degrades to "we tried GEPA and the seed prompt was already strong" — still defensible, still uses Gemma.

---

## 18. Risks & mitigations

| ID | Risk | Plan C mitigation |
| --- | --- | --- |
| **R-6** | Agent hallucinates despite system prompt | Three-layer Pydantic enforcement (§7); `tests/agent/test_citations.py` adversarial suite; DeepEval gate (§14) — fabricated citations are *structurally impossible* to ship |
| **R-7** | Demo venue Wi-Fi blocks Gemma API / Langfuse | `agent_mock` + canned SSE traces for the scripted demo path (NFR-9 sequence — live mode is the second segment); self-hosted Langfuse Docker pre-pulled (§9.3); cached canonical Gemma responses for the demo questions; LangGraph fallback documented per ADR-008 (not built unless the Gemma path collapses) |
| **R-9 (ADR-022)** | GEPA-compiled prompt regresses vs. seed prompt on held-out gate | C12 §14a.6 — feature flag `AGENT_SYSTEM_PROMPT=seed\|gepa` swaps in one line; comparison harness still runs and produces a defensible "GEPA didn't help on this task, here's the data" demo beat |
| **R-10 (ADR-022)** | Gemma 4 31B underperforms even with GEPA-compiled prompt vs Opus 4.7 baseline | If GEPA-Gemma is more than 5pp below Opus on faithfulness, the slide pivots from "matches" to "approaches at 75× lower cost" — still a strong MLH narrative; or feature-flag back to Opus 4.7 via the same `AGENT_RUNTIME_LM` flag the demo deck describes |
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

# FR-W.10 — GEPA-compiled prompt is a frozen artifact, agent loads it at startup
test -f config/agent.system_prompt.gepa.txt
test -f docs/eval/gepa_compile_log.json
pytest tests/agent/test_compiled_prompt_loads.py -q
pytest tests/agent/test_runtime_lm_is_gemma.py -q

# FR-W.11 — three-way comparison results committed and within target
python scripts/agent/run_comparison.py --check  # exits 0 iff GEPA-Gemma row within 2pp of Opus-4.7

# NFR-5 — agent latency
pytest tests/agent/test_latency.py -q

# Smoke — fully mock-backed demo
make demo-mock
```

When every command above exits 0 and `make demo-mock` boots cleanly without an internet connection, **Plan C is done.**

---

## 20. DDD compliance

### 20.1 Authoritative ADR

The binding source for the bounded-context structure of Plan C's work is [`ADR-021 — DDD module structure with three bounded contexts`](../adr/ADR-021-domain-driven-design-module-structure.md). This section is a quick reference, not a redefinition: every claim below restates ADR-021 in the local context of the Agent & Presentation bounded context. If this section drifts from ADR-021, ADR-021 wins; deviation requires a new superseding ADR, not an in-place edit.

### 20.2 Bounded context owned

- **Name:** Agent & Presentation.
- **Directory:** `src/agent/` (Python backend) + `frontend/` (React UI).
- **Responsibility:** The Voice. Claude Agent SDK loop with five typed tool wrappers, the three-layer Pydantic citation pipeline (ADR-014), the structured refusal template, the SSE wire format (ADR-017), Langfuse OTel observability (ADR-016), the Apollo first-person persona (ADR-019), the React frontend's three Universe panels + Apollo chat panel + What-If panel, and the Ragas + DeepEval automated grounding eval (ADR-018).
- **Local ubiquitous language (per ADR-021, extended by ADR-022):** Tool Call, Citation, Refusal, Severity, Trace, Persona, **Compiled Prompt**, **Reflection LM**, **Comparison Run**. Plan C does not introduce vocabulary outside this list; Component / Run / Counterfactual / Obituary are imported from upstream contexts' published languages.
  - **Compiled Prompt:** the system-prompt artifact produced by `dspy.GEPA` (FR-W.10), committed as `config/agent.system_prompt.gepa.txt`. Distinct from the *seed prompt* (`prompts/system.md`) which is the GEPA input.
  - **Reflection LM:** the LM used by GEPA during the reflection step to propose new candidate prompts — Claude Opus 4.7 via the local `claude` CLI (ADR-022). Distinct from the *student LM* (Gemma 4 31B) which is the LM the prompt is being optimized for.
  - **Comparison Run:** one of three eval invocations under FR-W.11 — vanilla Opus 4.7, vanilla Gemma 4 31B, GEPA-Gemma. Logged to `docs/eval/comparison_results.json`.
- **Published language:** `src/agent/contracts.py` (`ApolloResponse`, `Citation`, `ToolCall`) and `frontend/src/types.ts` (`SSEEvent` union) — the Open Host Service consumed by the React frontend, the eval CI, and any future integration. See §3.2, §3.3.

### 20.3 Aggregate roots

Plan C owns exactly one aggregate root.

| Aggregate | Pydantic embodiment | Invariants enforced by the aggregate |
| --- | --- | --- |
| `ApolloResponse` | `ApolloResponse` (§3.2) | `len(citations) ≥ 1` unless `severity == "REFUSAL"` (NFR-6, NFR-7, ADR-014), enforced by the `_citations_required_unless_refusal` field validator. Every `Citation` resolves against the historian primary key `(run_id, component_id, t)` via `resolve_citation()` (§7.2) **before** the SSE `done` event fires; unresolvable citations downgrade the aggregate to `severity = "REFUSAL"` and clear `citations`. `severity` is closed under `INFO | WARNING | CRITICAL | REFUSAL`; `tool` membership in each `ToolCall` is closed under the `Literal` of five names. The aggregate is constructed once per turn by the agent loop and is immutable thereafter — the SSE stream is a serialization of the aggregate, not a parallel mutation channel. |

`Citation` and `ToolCall` are part of the aggregate's exposed surface but are themselves value objects (§20.4) — they have no identity beyond their field tuples.

### 20.4 Entities vs. value objects

Classification of every Pydantic model in `src/agent/contracts.py` (the §3 frozen contracts of this plan):

| Pydantic model | Classification | Reason |
| --- | --- | --- |
| `Citation` | Value Object | Identified by `(run_id, component, timestamp)` tuple; immutable; its meaning is entirely its field values. The `component` field is typed against the `ComponentId` enum from the shared kernel — string component names are forbidden (§3.4 of master plan, §20.8 below). |
| `ToolCall` | Value Object | Records one tool invocation snapshot (tool name, args, result, call_id, timing); never edited after the matching `tool-result` event is processed; replayable but not mutable. |
| `ApolloResponse` | **Aggregate Root** | Composes the citation list, the tool-call list, severity, text, and trace URL; enforces the citation-required-unless-refusal invariant; constructed once per agent turn. |
| `SSEEvent` (TypeScript discriminated union) | Value Object (over the wire) | Each variant is a snapshot record; the union is the published serialization of `ApolloResponse`. |

Plan C defines **no entities** — there is no per-message identity that survives across turns at the aggregate-root level; the trace URL provides observability identity but lives in Langfuse, not in the bounded-context model.

### 20.5 Domain services

Stateless service functions that orchestrate the `ApolloResponse` aggregate. They are not part of the published language; they are internal collaborators of the aggregate.

- **The agent loop** (`src/agent/loop.py`, §6) — Claude Agent SDK driver that registers the five tools, enforces the system-prompt grounding rules, caps tool calls per turn at 3 (NFR-5), and assembles the final `ApolloResponse`.
- **The citation validator** (`src/agent/citations.py`, §7.2) — `resolve_citation(c, db) -> bool`; the **Anti-Corruption Layer** between the Agent context and the Historian (Plan B). See §20.8.
- **The SSE encoder** (`src/agent/sse.py`, §5.2) — `event_stream(events)` validates each event against the frozen schema (§3.3) before yielding it to `EventSourceResponse`; emits a heartbeat every 15 s; ensures the aggregate's invariants hold across the wire.
- **The persona renderer** (`src/agent/persona.py` + `src/agent/speak.py`, §8) — the < 200-token system prompt loader and the six template-bounded `speak()` generators (one per `ComponentId`); deterministic, no LLM call inside `speak()` so component utterances cannot hallucinate.

### 20.6 Repositories

**None.** The Agent context owns no repositories (per ADR-021 "Decision" §4 "Repository abstractions"). It consumes Plan B's `HistorianRepository` and `RetrievalIndex` exclusively through the four published function tools (`query_historian`, `compare_runs`, `run_counterfactual`, `late_interaction_search`). The fifth tool, `plot_component_history`, emits a `ChartSpec` value object the React frontend renders inline — no persistence on Plan C's side.

The Langfuse trace store is observability infrastructure, not a domain repository; the `trace_url` on `ApolloResponse` is a deep link, not a primary key into a Plan C-owned aggregate.

### 20.7 Domain events

Subset of the master event list (PLAN.md §9.7) emitted or consumed by Plan C:

- **Consumed (from Simulation):**
  - `RunCompleted` — makes a run queryable; surfaces in the chat panel's run-context selector and the live-sim panel.
  - `ObituaryEmitted` — Plan C's failure-timeline panel renders the obituary card within 1 s of receipt.
- **Emitted (to eval / Langfuse):**
  - `CitationResolved` — emitted via Langfuse OTel for every `Citation` whose `resolve_citation()` returns True; consumed by the eval pipeline (ADR-018) and the demo "Trace" link (ADR-016).
  - `ResponseRefused` — emitted whenever the aggregate is downgraded to `severity = "REFUSAL"`. Per ADR-014, refusal is a positive signal, not a failure mode; the wildcard dry-run (§15) and DeepEval gate (§14) both treat it as a win when the historian cannot ground a claim.

### 20.8 Anti-corruption layer responsibilities

The Agent context's ACL is the **Pydantic citation validator** (`src/agent/citations.py`), promoted from "yet another validator" to a named architectural fixture per ADR-021 "Decision" §3 ("Agent ↔ Historian: protected by an Anti-Corruption Layer = the Pydantic citation validator (ADR-014)").

The ACL guards three corruptions:

1. **Free-form text drawn from training memory leaking into user-facing prose.** The system prompt (§6.3) forbids it; the field validator on `ApolloResponse.citations` rejects non-REFUSAL responses with empty citations; if the model ignores both, every cited claim still has to resolve against the historian primary key before `done` fires. Three independent layers, one must catch every case (R-6 mitigation).
2. **Fabricated `(run_id, component, t)` triples.** The adversarial test suite in §7.4 (`tests/agent/test_citations.py`) injects synthetic responses with non-existent triples and asserts the validator downgrades them to REFUSAL with `citations = []`. Partial fabrication (one real + one fabricated citation) also triggers REFUSAL — no partial credit.
3. **String component names crossing the bounded-context boundary.** `Citation.component` is typed against the `ComponentId` enum imported from the shared kernel; the architecture test (`tests/architecture/test_no_string_components.py`, §9.8 of master plan) enforces that no string literal in `src/` matches a component name outside the enum definition.

The refusal template (§7.3) is the legitimate egress channel when the ACL blocks a response — the user sees a structured explanation, not a fabrication.

### 20.9 Ubiquitous-language enforcement

The lint/test rules for this plan are the citation-validator unit tests and the adversarial citation set:

- `pytest tests/agent/test_citations.py` — the six adversarial cases from §7.4: `test_non_refusal_has_citation`, `test_unknown_component_rejected`, `test_fabricated_citation_refuses`, `test_partial_fabrication_refuses`, `test_refusal_template_text`, `test_pydantic_error_caught`. This is the binding ACL gate.
- `pytest tests/agent/test_refusal.py` — all four refusal pathways (off-topic, unknown component, unknown run, no rows) end in `severity = "REFUSAL"`.
- `pytest tests/agent/test_persona_token_budget.py` — Apollo persona prompt < 200 tokens (ADR-019).
- `pytest tests/agent/test_speak.py` — six template-bounded `speak()` generators, one per `ComponentId`, asserts measurement-grounded output (no affective words; ADR-019 voice lint).
- `pytest tests/sse/test_event_replay.py` — exact event-order match against the golden trace; a vocabulary drift in the SSE schema would break the replay.
- `deepeval test run tests/eval/` — Ragas + DeepEval grounding eval (ADR-018, FR-W.9): faithfulness ≥ 0.95, hallucination = 0, including the 6 deliberately-unanswerable questions that must return REFUSAL.

These six commands collectively validate that Plan C's published language stays the language ADR-021 defines and that the citation ACL holds under adversarial input.
