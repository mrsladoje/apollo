# Apollo — Master Build Plan

**Project:** Apollo — HP Metal Jet S100 Digital Co-Pilot
**Hackathon:** HackUPC 2026 — HP "When AI meets reality"
**Source brief:** `task/hackathon.md`, `task/stage{1,2,3}.md`, `task/20260423-HP-Briefing.pdf`
**Authoritative spec:** [`docs/PRD.md`](../PRD.md) v1.1
**Authoritative decisions:** [`docs/adr/`](../adr/) ADR-001 through ADR-020 (all `Status: Accepted`)
**Owner:** mrsladoje + 2 collaborators (Dev A, Dev B, Dev C)
**Plan version:** 1.0 — 2026-04-25

---

## 0. How to read this plan

This is the **master plan**. It defines:

1. The **work split** across 3 developers (one per phase, not one per layer).
2. The **frozen integration contracts** — the Pydantic / function / SSE schemas at the seams between phases. Once frozen, they cannot be changed without a 3-way handshake.
3. The **mocks-first parallelization** rule that lets all three plans start at hour zero.
4. The **integration milestones** — the only points at which mocks are swapped for real implementations.
5. The **testing gates** every workstream must pass.
6. The **no-deferral policy** that overrides PRD §3.2 "stretch goals" wording: **everything in this plan ships.**

The three sub-plans live alongside this file:

- [`PLAN-A-engine.md`](PLAN-A-engine.md) — Developer A: Phase 1 engine, failure models, coupling, PINN, MAPIE
- [`PLAN-B-simulation.md`](PLAN-B-simulation.md) — Developer B: SQLite historian, sim loop, scenarios, GA, counterfactual, retrieval index
- [`PLAN-C-agent-ui.md`](PLAN-C-agent-ui.md) — Developer C: agent loop, tools, citations, SSE, Langfuse, React UI, eval

---

## 1. Goal & success criteria

Ship the full Apollo system end-to-end — every PRD-MUST and every PRD-SHOULD requirement (FR-1.x, FR-2.x, FR-3.x, FR-W.1 through FR-W.9), every NFR (NFR-1 through NFR-10), and the full submission gate (PRD §16.1) before HackUPC 2026 demo.

**Submission gate (must pass all):**
- All MUST requirements in PRD §6.1, §6.2, §6.3 satisfied (`pytest` green).
- Architecture deck + technical report delivered (PRD §17 M10).
- GitHub repo with reproducible README.
- Automated grounding eval (FR-W.9) passes: faithfulness ≥ 0.95, hallucination = 0.
- Six components × three subsystems modeled, three failure-model families implemented, three cascades demonstrable.
- Three scenarios × three policies = nine runs persisted in `historian.db`.
- Live "Ask Apollo" dry-run: 0 hallucinations across 10 wild-card questions.
- Conformal interval empirical coverage ≥ 90% on Stressed at 95% nominal CI.
- Langfuse trace UI shows complete tool-call timeline for canonical demo query.

**Differentiation target (winning):** PRD §16.2 metrics — uptime delta ≥ +25% (target +34%), 100% citation coverage, 0% hallucination, ≥ 7 of 9 demo-differentiator features shipped.

---

## 2. Binding rules (read once, apply forever)

These rules override any softer wording in PRD or ADRs.

### 2.1 No deferrals

PRD §3.2 lists "stretch goals" (G-7, G-8, G-9). PRD §17 lists a "cut order" (M9e → M9d → M9c → M9b). **For this plan, both are void.** Every G-* and every M-* in PRD §17 ships. The cut order is replaced with a *mitigation order* — if a workstream slips, we add hours to it (overflow into Sunday morning), we do not cut it.

The only legitimate omissions are the items in [ADR-020 §1–17](../adr/ADR-020-out-of-scope-rationale.md) (voice UI, RL agent, custom Metal kernels, Omniverse, etc.). Those are pre-decided rejections, not deferrals.

### 2.2 Mocks-first parallelization

No developer waits on another. Every plan's **Step 0** is to ship mocks of every interface they own, committed before any real implementation. The other two plans build against those mocks from hour zero.

The integration contracts in §3 below are the seams. Mocks must conform to those contracts byte-for-byte.

### 2.3 Test exhaustively before integration

Every workstream has its own `pytest` (Python) or `vitest` (React) suite under the project's `tests/` tree. **No code reaches integration until its module-level suite is green.** Acceptance criteria are checkbox lists in each sub-plan, each backed by a verification command.

Determinism (NFR-1) is the most-tested invariant: every component, the sim loop, the GA, and the counterfactual engine all have golden-file tests that run twice and byte-compare.

### 2.4 ADRs are binding

Every decision in `docs/adr/` is `Status: Accepted` as of 2026-04-25. They are not suggestions. If any sub-plan needs to deviate, the deviation requires a new ADR (per `docs/adr/README.md` "When to add a new ADR") signed off by all three developers, not a silent code change.

### 2.5 Pre-flight read

Every developer reads, before writing a single line of code:

1. The full PRD (`docs/PRD.md`).
2. The ADRs whose ID appears in their sub-plan's "ADR map" section.
3. ADR-020 (out-of-scope) — to know what *not* to do.

---

## 3. Frozen integration contracts

These are the seams between Plans A, B, C. Once committed in code (hour 1 of day 1), they may only change via a 3-way handshake recorded in a new ADR.

### 3.1 Plan A → Plan B (engine to simulation)

Plan A owns these definitions; Plan B imports them.

```python
# src/engine/contracts.py — owned by Plan A
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class ComponentId(str, Enum):
    BLADE = "blade"
    MOTOR = "motor"
    NOZZLE = "nozzle"
    RESISTOR = "resistor"
    HEATER = "heater"
    INSULATION = "insulation"

class ComponentStatus(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"   # health >= 0.7
    DEGRADED   = "DEGRADED"     # 0.4 <= health < 0.7
    CRITICAL   = "CRITICAL"     # 0.1 <= health < 0.4
    FAILED     = "FAILED"       # health < 0.1

class ComponentState(BaseModel):
    component_id: ComponentId
    health: float = Field(ge=0.0, le=1.0)
    status: ComponentStatus
    metrics: dict[str, float]   # blade_thickness_mm, current_draw_A, etc.

class Drivers(BaseModel):
    temp_C: float
    humidity: float
    pm25: float
    psd_d50: float              # powder PSD median
    voltage_stability: float
    cycles: int
    hours: float
    maintenance_level: dict[ComponentId, float]
    operator_shift: Literal["day", "night", "weekend"]
    rng_seed: int

class EngineState(BaseModel):
    components: dict[ComponentId, ComponentState]
    coupling_matrix: list[list[float]]   # 6x6, ADR-004
    rng_state: tuple                     # serializable for ADR-012 checkpoints

class Forecast(BaseModel):
    component_id: ComponentId
    horizon_min: int                     # capped at 60, ADR-015
    point: float
    lower: float
    upper: float
    ci_level: float                      # 0.95 by default

# THE single function the simulation loop calls — FR-1.8
def step(state: EngineState, drivers: Drivers, dt: float) -> EngineState: ...

# Conformal forecast — FR-W.6
def forecast(state: EngineState, horizon_min: int = 60) -> list[Forecast]: ...
```

**Mock obligation (Plan A Step 0):** ship `src/engine/mock_engine.py` with the same signatures, deterministic synthetic decay curves, and plausible mock conformal bands. Plan B builds against the mock until Plan A's real engine lands at the integration milestone.

### 3.2 Plan B → Plan C (simulation to agent)

Plan B owns these definitions; Plan C imports them and wraps the four function tools.

```python
# src/sim/contracts.py — owned by Plan B
from datetime import datetime
from pydantic import BaseModel
from engine.contracts import ComponentId, ComponentStatus

class HistorianRow(BaseModel):
    run_id: str
    t: datetime
    component_id: ComponentId
    health: float
    status: ComponentStatus
    metrics: dict[str, float]

class CounterfactualResult(BaseModel):
    original: list[HistorianRow]
    alternate: list[HistorianRow]
    diff: dict      # {uptime_delta_h, failures_avoided, cost_delta_eur}

class RetrievedRow(BaseModel):
    run_id: str
    component: ComponentId
    t: datetime
    score: float
    snippet: str

# Tool implementations consumed by Plan C — FR-3.6
def query_historian(
    run_id: str,
    component: ComponentId | None,
    time_range: tuple[datetime, datetime],
) -> list[HistorianRow]: ...

def compare_runs(run_ids: list[str], metric: str) -> dict: ...

def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict,
) -> CounterfactualResult: ...

def late_interaction_search(
    query: str,
    run_id: str | None = None,
    top_k: int = 10,
) -> list[RetrievedRow]: ...
```

**Mock obligation (Plan B Step 0):** ship `historian_mock.py` (in-memory SQLite seeded with all 9 fake runs), `late_interaction_mock.py`, `counterfactual_mock.py`, and `gp_fitness_mock.csv`. Plan C builds the entire chat panel and live-sim panel against these mocks before any real implementation lands.

### 3.3 Plan C → user (agent response + SSE)

Plan C owns the wire format the React frontend and the eval CI consume.

```python
# src/apollo/agent/contracts.py — owned by Plan C
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, validator
from engine.contracts import ComponentId

class Citation(BaseModel):
    run_id: str
    component: ComponentId
    timestamp: datetime
    # Resolution rule (ADR-014): every citation must resolve to a real
    # historian row by primary key (run_id, component_id, t) BEFORE the
    # SSE `done` event fires. Unresolvable -> response downgrades to REFUSAL.

class ToolCall(BaseModel):
    tool: Literal[
        "query_historian", "late_interaction_search",
        "compare_runs", "run_counterfactual", "plot_component_history",
    ]
    args: dict
    result: dict | None
    call_id: str
    started_at: datetime
    finished_at: datetime | None

class ApolloResponse(BaseModel):
    severity: Literal["INFO", "WARNING", "CRITICAL", "REFUSAL"]
    text: str
    citations: list[Citation]   # min_length=1 unless severity == "REFUSAL"
    tool_calls: list[ToolCall]
    trace_url: str              # Langfuse deep link, ADR-016
```

```ts
// frontend/src/types.ts — owned by Plan C, consumed by the React reducer
type SSEEvent =
  | { type: "text-delta";       payload: { token: string } }
  | { type: "tool-call-start";  payload: { tool: string; args: object; call_id: string } }
  | { type: "tool-result";      payload: { call_id: string; result: object } }
  | { type: "citation";         payload: { run_id: string; component: string; timestamp: string } }
  | { type: "done";             payload: { trace_url: string } };
```

These two schemas — `ApolloResponse` and `SSEEvent` — are FROZEN. They are the contract with the frontend, the eval harness, and any future integration.

### 3.4 Cross-cutting: canonical 6-component enum

`ComponentId` lives in Plan A's `engine/contracts.py` and is imported by all three plans. It is the **only** allowed source of component names. ADR-014 §3 explicitly requires that the citation validator and the State Report schema share this enum. Any string component name in code is a bug.

---

## 4. Work split (one developer per phase)

| Plan | Owner | Phase | LOC est. | ADRs primarily owned | PRD sections |
|------|-------|-------|----------|----------------------|--------------|
| **A** | Dev A | Phase 1 — Logic Engine | ~2.5k | 001, 002, 003, 004, 005, 006, 015 | §6.1, §8, §10, §11.1, §11.6 |
| **B** | Dev B | Phase 2 — Simulation, Data & Optimization | ~2.5k | 007, 010, 011, 012, 013 | §6.2, §9, §11.2, §11.3, §11.4, §14 |
| **C** | Dev C | Phase 3 — Agent, UI & Eval | ~3.5k (incl. React) | 008, 009, 014, 016, 017, 018, 019 | §6.3, §6.4, §11.5, §11.7, §11.8, §15 |

Cross-cutting ADR-020 (out-of-scope) applies to all three. ADR-019 (persona) is owned by Plan C but referenced by Plan B for obituary tone.

The split aims to be hour-equal at ~15 hours each (45 dev-hours total against PRD §17's ~47-hour budget). Plan C is slightly heavier in raw LOC because of the React frontend, balanced by Plan B's longer-running offline jobs (GA training, PyLate indexing) which Dev B can launch and walk away from.

### 4.1 Why phase-aligned, not layer-aligned

Splitting horizontally (e.g., "you do all the Python, you do all the React") would maximize merge conflicts and minimize each developer's ability to test their own slice end-to-end. Splitting by phase means each developer can run their slice through `pytest` without depending on either teammate, *because of the mocks in §3*.

---

## 5. Mocks-first parallelization plan

The first commit each developer makes is a "mocks PR" — entirely synthetic, no external deps, sufficient to unblock the other two.

```
Hour 0 ─────────────────────── Hour 1 ──────────────────────────► Hour 15
  │                              │                                      │
Plan A: write contracts.py + mock_engine.py    real engine builds       │
Plan B: write contracts.py + historian_mock.py + late_interaction_mock + ga_mock + cf_mock
Plan C: write contracts.py + agent_mock.py + tool_mocks.py + forecasts_mock.json
                                 │
                                 ▼
              All three plans now buildable in isolation.
              Each developer's pytest suite is green against mocks
              before any real implementation lands.
```

Mocks live alongside real implementations under the same module path with a `_mock` suffix. `USE_MOCKS=1` is the umbrella dry-run switch; integration switches it to `0` / unset. Individual layers may also be forced independently for targeted tests: `APOLLO_ENGINE=mock`, `HISTORIAN_BACKEND=mock`, `RETRIEVAL_BACKEND=mock`, `APOLLO_TOOLS_BACKEND=mock`, and `APOLLO_AGENT=mock`.

### 5.1 Mock fidelity rules

- **Schema-identical:** mocks return Pydantic-validated payloads matching the contract exactly. No "I'll add the field later."
- **Deterministic:** mocks use seeded RNG for any randomness. Two consecutive calls with the same args return byte-identical output.
- **Demo-shaped:** mock payloads are tuned to the canonical demo path (Barcelona printhead at hour 7, etc.). The UI can dry-run end-to-end before the real backend lands.
- **Adversarial cases included:** Plan B's `historian_mock.py` includes runs where citations resolve, runs where they do not, and runs where the answer should be a REFUSAL. Plan C's eval set exercises all three.

---

## 6. Hour-by-hour integrated timeline

This combines all three plans onto a single calendar. Each plan's individual timeline is in its own file; this is the cross-plan critical path.

| H | Plan A — Engine | Plan B — Sim/Data | Plan C — Agent/UI | Sync gate |
|---|-----------------|-------------------|-------------------|-----------|
| 0–1 | Write `contracts.py`. Ship `mock_engine.py`. | Write `contracts.py`. Ship 4 mocks. | Write `contracts.py`. Ship `agent_mock.py` + `tool_mocks.py`. | **G0 — contracts frozen.** All three commit `contracts.py` and mocks. PR review by all 3. |
| 1–4 | Failure-model classes (exp / Weibull / Coffin-Manson). Unit tests. Component models 1–3. | Historian DDL + WAL. Sim loop tick. Driver providers (mock + real). | FastAPI + sse-starlette skeleton. SSE event-order test against `agent_mock`. React chat panel renders streaming text. | — |
| 4–6 | Component models 4–6. Coupling matrix M. CSC-A and CSC-C wiring. | 3 scenarios × 3 policies grid running with mock engine. NONE/FIXED policies. Failure detection. | Live sim panel rendering against `historian_mock`. Three Universe panels with Dark Twin labels. Conformal Area band placeholder. | **G1 — engine mock replaced.** Plan A's real engine wired into Plan B's sim loop. Sim runs against real engine (no mock). Both pytest suites stay green. |
| 6–9 | PINN training (DeepXDE on MPS). Train, freeze, save artifact. CSC-B explicit physics (Arrhenius + Coffin-Manson). | DEAP island GA running on Stressed scenario with production-resolution in-memory fitness. Counterfactual engine (checkpoint+branch). Obituaries generator. | Real Claude Agent SDK loop wired with 5 tools (still pointing at Plan B mocks). Pydantic citation validator + adversarial fabricated-citation tests pass. Apollo persona prompt loaded. | — |
| 9–11 | PINN integrated as Heating Element model. NFR-3 latency benchmarked. | PyLate index built over historian. NFR-4 latency benchmarked. Late-interaction search wired. | Langfuse OTel set up. "Trace" links live. What-If panel rendering against `counterfactual_mock`. | **G2 — historian mock replaced.** Plan B's real historian, GA, counterfactual, and PyLate index are wired in. Plan C's tools call the real Plan B implementations. End-to-end smoke test: Barcelona printhead canonical query produces a fully-cited response with a real Langfuse trace. |
| 11–13 | MAPIE conformal layer wrapping all 6 component predictors. Coverage test on Stressed scenario passes ≥ 90% at 95% CI. | All 9 runs pre-computed and persisted. Obituaries written. Run IDs frozen. | Real conformal bands rendering on Recharts. Ragas test-set generator runs; 30 grounded Q/A committed. DeepEval CI: faithfulness ≥ 0.95, hallucination = 0. | **G3 — eval gate green.** `deepeval test run tests/eval/` exits 0. README badge updated. |
| 13–14 | Definition of done verification: every FR-1.x + FR-W.6 + NFR-1/2/3 verification command runs green. | Definition of done: every FR-2.x + FR-3.6 (Plan B side) + FR-W.4 + NFR-4/8 green. Reproducibility byte-compare passes. | Live "Ask Apollo" 10-question dry-run: 0 hallucinations. Savings slide drafted. | **G4 — full system integration.** All three plans on real implementations end-to-end. |
| 14–15 | Buffer / R-1 mitigation if cascade timing drifts. | Buffer / R-4 mitigation: tune GA islands, immigrant rate, and early-stop patience; Optuna remains a benchmark fallback if GA curve is still ugly. | Buffer / Demo polish. Architecture diagram. README. | — |
| 15–17 | (Sat morning) Demo polish, Apollo persona tuning, Dark Twin component obituaries staged. | (Sat morning) Pre-record canned demo path for R-7. | (Sat morning) Final dress rehearsal. Speaker notes. | **G5 — demo ready.** Full dry-run end-to-end. |

**Sync gates G0–G5 are mandatory.** No plan progresses past a gate until all three sign off in the gate's PR.

### 6.1 What "no deferrals" means in practice

PRD §17 originally listed M9e (eval) → M9d (SSE) → M9c (Langfuse) → M9b (conformal) as the cut order. In this plan, all four ship by hour 13 (gate G3). If any falls behind, hours 14–15 absorb the slip; if even that overflows, Saturday morning (hours 15–17) absorbs it. Nothing gets cut.

---

## 7. Testing strategy (cross-cutting)

### 7.1 Per-plan suites

Each plan's `Definition of done` section lists the verification commands. They run on every commit via a single root-level `pytest` invocation:

```bash
# Engine (Plan A)
pytest tests/engine/ -v                # FR-1.x, FR-W.6, NFR-1/2/3

# Simulation (Plan B)
pytest tests/sim/ tests/historian/ tests/policies/ tests/retrieval/ -v
                                       # FR-2.x, FR-3.6 backing, FR-W.4, NFR-4/8

# Agent + UI (Plan C)
pytest tests/agent/ tests/sse/ tests/eval/ -v
npm --prefix frontend run test          # FR-3.x, FR-W.1/2/3/5/7/8, NFR-5/6/7
deepeval test run tests/eval/           # FR-W.9 — must exit 0

# Reproducibility (cross-cutting)
pytest tests/reproducibility/ -v       # NFR-1, NFR-8 — byte-compare two runs
```

### 7.2 Determinism golden tests

For every component (Plan A), the simulation loop (Plan B), the GA (Plan B), and the counterfactual engine (Plan B): run twice with identical input, byte-compare output. Failure of a determinism test blocks merge.

### 7.3 Integration smoke test

A single end-to-end script (`scripts/smoke_demo.py`) runs the canonical Barcelona printhead query against the full real stack and asserts:

- `ApolloResponse.severity == "CRITICAL"`
- `len(ApolloResponse.citations) >= 3`
- Every citation's `(run_id, component, t)` resolves in `historian.db`
- The response includes a reference to Cascade B (insulation → heater → nozzle)
- Total wall-clock < 6s (NFR-5)
- Langfuse trace URL is a valid deep-link

This script runs at gates G2, G3, G4, G5.

### 7.4 Adversarial citation tests

Plan C's pipeline must REFUSE responses with fabricated citations. `tests/agent/test_citations.py` injects synthetic responses with `(run_id, component, t)` triples that do NOT exist in the historian and asserts the validator downgrades them to REFUSAL. This test is *required* to pass before Plan C reaches integration.

### 7.5 Latency budgets

Every NFR with a latency target is a `pytest` benchmark:

- NFR-2: `pytest tests/engine/test_step_latency.py` — assert < 50 ms total per step.
- NFR-3: `pytest tests/engine/test_pinn_latency.py` — assert < 5 ms PINN inference.
- NFR-4: `pytest tests/retrieval/test_latency.py` — assert p95 < 200 ms over 10k rows.
- NFR-5: `pytest tests/agent/test_e2e_latency.py` — assert p95 < 6s on canonical query.

A miss is a blocker, not a warning.

---

## 8. ADR map (master)

Every ADR with the plan(s) that own its implementation:

| ADR | Title | Plan A | Plan B | Plan C |
|-----|-------|:------:|:------:|:------:|
| [001](../adr/ADR-001-hybrid-rule-based-and-pinn-modeling.md) | Hybrid rule-based + PINN | ● | | |
| [002](../adr/ADR-002-six-components-three-subsystems.md) | Six components × three subsystems | ● | | |
| [003](../adr/ADR-003-three-parallel-cascades.md) | Three parallel cascades | ● | | |
| [004](../adr/ADR-004-linear-coupling-matrix.md) | Linear coupling matrix M | ● | | |
| [005](../adr/ADR-005-deepxde-for-heating-element-pinn.md) | DeepXDE PINN for heater | ● | | |
| [006](../adr/ADR-006-three-failure-model-families.md) | Three failure-model families | ● | | |
| [007](../adr/ADR-007-sqlite-historian.md) | SQLite historian | | ● | |
| [008](../adr/ADR-008-claude-agent-sdk-and-sonnet.md) | Claude Agent SDK + Sonnet | | | ● |
| [009](../adr/ADR-009-pattern-c-agentic-diagnosis.md) | Pattern C — Agentic Diagnosis | | | ● |
| [010](../adr/ADR-010-late-interaction-retrieval-lateon-code-edge.md) | Late-interaction retrieval | | ● | ○ (consumes) |
| [011](../adr/ADR-011-genetic-algorithm-for-maintenance.md) | Genetic algorithm (DEAP) | | ● | |
| [012](../adr/ADR-012-simulator-checkpoint-counterfactual.md) | Simulator-checkpoint counterfactual | | ● | ○ (consumes) |
| [013](../adr/ADR-013-dark-twin-three-scenarios.md) | Three scenarios + Dark Twin | | ● | ○ (UI copy) |
| [014](../adr/ADR-014-pydantic-citations-and-refusal-grounding.md) | Pydantic citations + refusal | | | ● |
| [015](../adr/ADR-015-mapie-conformal-prediction.md) | MAPIE conformal intervals | ● | | ○ (renders) |
| [016](../adr/ADR-016-langfuse-observability.md) | Langfuse observability | | | ● |
| [017](../adr/ADR-017-sse-streaming.md) | SSE streaming | | | ● |
| [018](../adr/ADR-018-ragas-deepeval-grounding-eval.md) | Ragas + DeepEval grounding eval | | | ● |
| [019](../adr/ADR-019-apollo-first-person-persona.md) | Apollo first-person persona | | ○ (obituary tone) | ● |
| [020](../adr/ADR-020-out-of-scope-rationale.md) | Out-of-scope decisions | ● | ● | ● |

Legend: ● primary owner ○ secondary consumer.

---

## 9. DDD compliance (master)

### 9.1 Authoritative ADR

The binding source for the project's Domain-Driven Design structure is [`ADR-021 — DDD module structure with three bounded contexts`](../adr/ADR-021-domain-driven-design-module-structure.md). This section is a **quick reference**, not a redefinition: every claim below is restated from ADR-021 in the local context of this master plan. If this section drifts from ADR-021, ADR-021 wins. Adding to or modifying any of the structures in §9.2–§9.8 requires a new ADR superseding ADR-021 (per `docs/adr/README.md`); no in-place edits.

### 9.2 Bounded contexts

Three bounded contexts, one per phase, one per developer, one `contracts.py` published-language module each (per ADR-021 "Decision" §1).

| Context | Owner (Plan) | Directory | Responsibility | Local ubiquitous language |
| --- | --- | --- | --- | --- |
| **Engine** | Plan A | `src/engine/` | Component physics, failure models, coupling matrix, cascades, PINN, conformal forecasting | Component, Subsystem, Cascade, Health, Status, Driver, Forecast |
| **Simulation & History** | Plan B | `src/sim/` | Tick-driven simulation loop, historian (SQLite WAL), scenario+policy grid, GA optimizer, counterfactual replay, obituaries, retrieval index | Run, Scenario, Policy, Tick, Obituary, Counterfactual, Dark Twin, Retrieval |
| **Agent & Presentation** | Plan C | `src/apollo/agent/` + `src/apollo/api/` + `frontend/` | Claude Agent SDK loop, five typed tools, Pydantic citation pipeline, refusal templates, SSE wire format, Langfuse traces, React UI | Tool Call, Citation, Refusal, Severity, Trace, Persona |

### 9.3 Context map

Integration relationships use DDD pattern names from ADR-021 "Decision" §3. The §3 frozen contracts are the integration medium; ADR-014 supplies the ACL implementation.

- **Engine → Simulation: Customer/Supplier** (Engine = Supplier). Simulation calls `engine.step()` and `engine.forecast()` through the published-language Pydantic contract in `src/engine/contracts.py` (this plan's §3.1).
- **Simulation → Agent: Customer/Supplier** (Simulation = Supplier). Agent consumes the four function tools through `src/sim/contracts.py` (this plan's §3.2). Plan C wraps them in Claude Agent SDK tool definitions.
- **Agent → User (frontend): Open Host Service**. `ApolloResponse` and the `SSEEvent` union are the published language consumed by the React frontend and the eval CI (this plan's §3.3).
- **Agent ↔ Historian: Anti-Corruption Layer**. The Pydantic citation validator (ADR-014) is the only legitimate channel from historian state into user-facing prose. Every outbound citation must resolve against the historian by primary key `(run_id, t, component_id)` before crossing the boundary; unresolvable citations downgrade the response to `severity == "REFUSAL"` per ADR-014 / NFR-6 / NFR-7.

### 9.4 Shared Kernel

The shared kernel is **intentionally minimal** (per ADR-021 "Decision" §2): only the `ComponentId` enum and the small set of cross-context value objects co-located in `src/engine/contracts.py` (`ComponentStatus`, the `status_for_health` helper, and the component-field type used by `Citation`). Every other domain term lives inside its owning context.

The kernel is **closed by default**. Adding a symbol to `src/engine/contracts.py` requires the §3 / §2.4 3-way handshake: all three developers sign off, the change rides a new ADR, the contract version bumps. This is friction by design; contract drift in the kernel would invalidate the architecture test in §9.9 and the schema enforcement in ADR-014.

### 9.5 Aggregate roots

Each bounded context owns exactly one aggregate root. Invariants are enforced by the aggregate, not by free functions outside it (per ADR-021 "Decision" §4).

| Aggregate | Owning context | Invariants |
| --- | --- | --- |
| `EngineState` | Engine (Plan A) | All cascade transitions go through the aggregate via `step()`; per-component health stays in `[0, 1]`; status enum derives deterministically from `health` via `status_for_health`; coupling matrix `M` retains its ADR-004 sparsity pattern; `rng_state` is serializable (NFR-1, ADR-012). |
| `Run` | Simulation (Plan B) | Append-only timeline of `HistorianRow`s keyed by `(run_id, t, component_id)`; counterfactuals branch via deepcopy (ADR-012), never by editing past rows; same `(scenario, policy, seed, config_json)` ⇒ byte-identical historian (NFR-8, FR-2.7). |
| `ApolloResponse` | Agent (Plan C) | `len(citations) ≥ 1` unless `severity == "REFUSAL"` (NFR-6, NFR-7, ADR-014); every `Citation` resolves against the historian primary key before the SSE `done` event fires; `tool` membership is closed under the `Literal` of five names; `severity` is closed under `INFO | WARNING | CRITICAL | REFUSAL`. |

### 9.6 Ubiquitous language glossary

Every term traces to a PRD section or an ADR. No new vocabulary; no synonyms.

| Term | Definition |
| --- | --- |
| **Component** | One of six named hardware units modeled by Plan A: blade, motor, nozzle, resistor, heater, insulation. PRD §8; ADR-002. |
| **Subsystem** | One of three groupings (Recoating, Printhead, Thermal); each contains exactly two components. PRD §6.1 FR-1.1; ADR-002. |
| **Cascade** | A coupling-driven failure path between components. CSC-A (recoating), CSC-B (thermal-printhead, showpiece), CSC-C (powder contamination). PRD §10; ADR-003, ADR-004. |
| **Health** | Per-component continuous scalar in `[0, 1]`; 1.0 = nominal, 0 = failed. PRD §8; FR-1.4. |
| **Status** | Discrete enum derived from health: FUNCTIONAL ≥ 0.7, DEGRADED ≥ 0.4, CRITICAL ≥ 0.1, FAILED otherwise. PRD §8. |
| **Driver** | An exogenous input to `step()`: temperature, humidity, PM2.5, powder PSD, voltage stability, cycles, hours, maintenance level, operator shift. PRD §9; FR-1.2. |
| **Run** | A single `(scenario, policy, seed)` simulation traced into the historian. `run_id = "{scenario}-{policy}-seed{seed:04d}"`. PRD §6.2; FR-2.4. |
| **Scenario** | One of three named driver-trajectory presets: Barcelona-humid, Phoenix-dry, Stressed. PRD §9.3; ADR-013. |
| **Policy** | One of three maintenance strategies: NONE (Dark Twin), FIXED (calendar), AI (GA-tuned thresholds). PRD §6.2 FR-2.4; ADR-011, ADR-013. |
| **Tick** | One simulated time-step (default 1 minute) at which `engine.step()` is invoked exactly once. PRD §6.2 FR-2.1. |
| **Forecast** | A horizon-bounded `(point, lower, upper, ci_level)` triple from MAPIE conformal prediction; `horizon_min ≤ 60`. PRD §6.4 FR-W.6, §11.6; ADR-015. |
| **Citation** | An evidence triple `(run_id, component, timestamp)` resolving to a real historian row. PRD §6.3 FR-3.3; ADR-014. |
| **Refusal** | A structured response with `severity == "REFUSAL"`, empty citations, and a templated explanatory text emitted when the historian cannot ground a claim. PRD §6.3 FR-3.5; ADR-014. |
| **Severity** | Closed enum `INFO | WARNING | CRITICAL | REFUSAL` on every Apollo response. PRD §6.3 FR-3.4. |
| **Tool Call** | A typed Pydantic-validated invocation of one of five registered tools (PRD §6.3 FR-3.6) by the agent loop. ADR-008, ADR-009. |
| **Trace** | A Langfuse-recorded span tree for one agent invocation, deep-linked from the `done` SSE event payload. PRD §6.4 FR-W.7; ADR-016. |
| **Obituary** | A bounded-template post-mortem narrative auto-generated within 5 s of a component's transition to FAILED, every claim cited. PRD §6.4 FR-W.4; ADR-019. |
| **Counterfactual** | A simulator-checkpoint replay branching from `(run_id, branch_t)` under an alternate action, returning a `(original, alternate, diff)` triple. PRD §11.4; ADR-012. |
| **Dark Twin** | The user-facing label for the NONE policy column in the three-universe panel; demo framing only, the database `policy` value remains `"none"`. PRD §6.4 FR-W.2; ADR-013. |
| **Persona** | Apollo's first-person voice: calm, professional, never alarmist, no exclamation marks; system prompt < 200 tokens. PRD §6.4 FR-W.1; ADR-019. |
| **Conformal Interval** | The shaded `(lower, upper)` band at a stated `ci_level` produced by MAPIE EnbPi block-bootstrap; empirical coverage validated ≥ 0.90 on Stressed at 95 % nominal. PRD §11.6 FR-W.6, §16.2; ADR-015. |

### 9.7 Domain events crossing contexts

Cross-context state transitions are explicit, named, and Pydantic-typed (per ADR-021 "Decision" §5). Each event has a single emitter and one or more consumers.

- `ComponentDegraded` — Engine emits → Simulation consumes (drives obituary candidacy, attribution).
- `ComponentFailed` — Engine emits → Simulation consumes (triggers obituary generation per FR-W.4) → Agent / UI consume (failure markers in live-sim panel).
- `CascadeTriggered` — Engine emits → Simulation consumes (logs cascade name CSC-A/B/C in obituary attribution).
- `RunCompleted` — Simulation emits → Agent / UI consume (run becomes queryable in `compare_runs`, `late_interaction_search`).
- `ObituaryEmitted` — Simulation emits → Agent / UI consume (failure-timeline card pops in within 1 s).
- `CitationResolved` — Agent emits → eval / Langfuse consume (success path; ADR-016, ADR-018).
- `ResponseRefused` — Agent emits → eval / Langfuse consume (refusal path is a positive signal per ADR-014).

### 9.8 Anti-corruption rules

Three rules protect the bounded contexts from each other (per ADR-021 "Decision" §6 "Ubiquitous-language enforcement rules"):

1. **String component names are forbidden outside the `ComponentId` enum.** Only enum members are allowed in code, contracts, and persisted data. Enforced by `tests/architecture/test_no_string_components.py`, which greps `src/` for string literals matching component names and fails CI if any are found outside the enum definition itself or test fixtures. This is the structural protection of §3.4 of this plan.
2. **The citation validator is the only legitimate channel from Historian state to user-facing prose.** No agent-context concept (e.g. raw "tool call result", free-form text drawn from training memory) leaks into the rendered response without ACL transit. ADR-014 and §7 of `PLAN-C-agent-ui.md` define the three-layer pipeline.
3. **Import direction is one-way: Agent imports Sim imports Engine; never reversed.** A reverse import is both a circular-import bug and a DDD violation. The architecture test asserts the directed import graph; CI fails on any back-edge.

### 9.9 Verification

Three commands collectively enforce the structure above:

```bash
# Bounded-context boundary + string-component drift gate
pytest tests/architecture/

# Anti-corruption layer (citation validator) — adversarial fabricated-citation tests
pytest tests/agent/test_citations.py

# Aggregate invariant: byte-identical Run reconstruction (ADR-012, NFR-8)
pytest tests/sim/test_reproducibility.py tests/engine/test_determinism_golden.py
```

`pytest tests/architecture/` validates §9.4 (kernel closure), §9.8 rule 1 (no string component names), and §9.8 rule 3 (import direction). `pytest tests/agent/test_citations.py` validates §9.8 rule 2 (ACL adversarial set already specified in §7.4 of this plan). The determinism gates validate §9.5 invariants for `EngineState` and `Run`.

---

## 10. Risk register (cross-cutting)

These are PRD §19 risks elevated to plan-level mitigations. Mitigations are scheduled, not optional.

| ID | Risk | Owner | Scheduled mitigation (no deferral) |
|----|------|-------|------------------------------------|
| R-1 | Coupling-matrix tuning produces unrealistic timing | Plan A | Hours 4–6: anchor `α_i` and Weibull params to literature ranges in `docs/refs/`; iterate against the Stressed scenario timing. Hour 14: dry-run check that all 3 cascades resolve in 10-h sim. |
| R-2 | PINN training unstable / slow | Plan A | Hour 6: smoke-train tiny PINN first; if loss diverges by hour 7, swap to learned-regressor surrogate (frozen scikit-learn `MLPRegressor`). Physics narrative still holds for rule-based 5/6. |
| R-3 | PyLate index too slow | Plan B | Hour 11: benchmark NFR-4. If p95 > 200 ms, fall back to Voyage/OpenAI dense embeddings — same `late_interaction_search` schema. |
| R-4 | GA fitness landscape ugly | Plan B | Hour 9: visual inspection of the fitness curve. First tune the DEAP island GA (seed bank, migration, elitism, random immigrants, diversity rescue, early stopping). If still jagged, compare against Optuna TPE while keeping threshold-policy semantics. |
| R-5 | Live sim too slow | Plan B | Pre-run all 9 scenarios before demo. Live mode is the *second* demo step (NFR-9). 10× replay built into the dashboard from hour 6. |
| R-6 | Agent hallucinates | Plan C | Pydantic citation validator (hour 6), adversarial fabricated-citation tests (hour 7), DeepEval CI gate (hour 13). Three layers; one must catch every case. |
| R-7 | Demo Wi-Fi blocks API access | Plan C + Plan B | Cache OpenWeather data offline (Plan B, hour 3). Pre-record canned Anthropic responses for the canned demo (Plan C, Sat morning). Phone hotspot tethered as backup. Live mode disabled if both fail. |
| R-8 | Live Q&A wild-card breaks | Plan C | Refusal template is itself a positive signal. 10-question dry-run at hour 14. If a question hallucinates, fix the resolver — refusal beats fabrication. |

---

## 11. Repo layout (target)

```
printer_newnow/
├── docs/
│   ├── PRD.md
│   ├── adr/                              # 20 ADRs, README.md
│   └── plans/
│       ├── PLAN.md                       # this file
│       ├── PLAN-A-engine.md
│       ├── PLAN-B-simulation.md
│       └── PLAN-C-agent-ui.md
├── src/
│   ├── engine/                           # Plan A
│   │   ├── contracts.py                  # FROZEN — §3.1
│   │   ├── mock_engine.py                # Step 0 deliverable
│   │   ├── failure_models/               # exp, weibull, coffin_manson
│   │   ├── components/                   # 6 modules
│   │   ├── coupling.py                   # M, ADR-004
│   │   ├── cascades/                     # CSC-A/B/C
│   │   ├── pinn/                         # DeepXDE heater
│   │   └── conformal.py                  # MAPIE wrapper
│   ├── sim/                              # Plan B
│   │   ├── contracts.py                  # FROZEN — §3.2
│   │   ├── historian_mock.py
│   │   ├── historian.py                  # SQLite WAL, ADR-007
│   │   ├── drivers/                      # weather, PM2.5, PSD, shifts
│   │   ├── loop.py                       # FR-2.1, FR-2.2
│   │   ├── scenarios.py                  # Barcelona/Phoenix/Stressed
│   │   ├── policies/                     # NONE / FIXED / AI(GA)
│   │   ├── ga.py                         # DEAP, ADR-011
│   │   ├── counterfactual.py             # ADR-012
│   │   ├── obituary.py                   # FR-W.4
│   │   └── retrieval/                    # PyLate, ADR-010
│   └── agent/                            # Plan C
│       ├── contracts.py                  # FROZEN — §3.3
│       ├── agent_mock.py
│       ├── tool_mocks.py
│       ├── loop.py                       # Claude Agent SDK
│       ├── tools/                        # 5 typed tools
│       ├── citations.py                  # ADR-014 validator
│       ├── persona.py                    # ADR-019
│       ├── sse.py                        # ADR-017
│       └── observability.py              # Langfuse OTel
├── frontend/                             # Plan C
│   ├── src/
│   │   ├── types.ts                      # SSEEvent — FROZEN
│   │   ├── panels/{LiveSim,Chat,WhatIf}.tsx
│   │   └── components/...                # Recharts, citations, obituary cards
├── tests/
│   ├── engine/    sim/    historian/    policies/    retrieval/
│   ├── agent/     sse/    eval/         ui/          reproducibility/
│   └── eval/grounding_set.json           # FR-W.9 frozen set
├── models/heater_pinn.pt                 # frozen PINN artifact
├── config/{agent.yaml,policies.yaml,scenarios.yaml}
├── data/                                 # cached weather feeds, R-7
├── scripts/{smoke_demo.py, generate_eval.py, prerun_scenarios.py}
└── README.md
```

This layout is binding for hour 0; the contracts files are the first commits.

---

## 12. Definition of done (master)

The project is done when:

- [ ] All three sub-plans' Definition-of-done sections are fully checked.
- [ ] The submission gate in §1 above is fully checked.
- [ ] `pytest` (root) exits 0.
- [ ] `npm --prefix frontend run test` exits 0.
- [ ] `deepeval test run tests/eval/` exits 0 with faithfulness ≥ 0.95 and hallucination = 0.
- [ ] `python scripts/smoke_demo.py` exits 0 with NFR-5 latency satisfied.
- [ ] `python scripts/prerun_scenarios.py` has produced 9 runs in `historian.db` with stable IDs.
- [ ] PINN artifact at `models/heater_pinn.pt`, < 5 ms CPU inference verified.
- [ ] PyLate index built; NFR-4 latency verified.
- [ ] Langfuse trace UI renders the canonical query end-to-end.
- [ ] Live "Ask Apollo" 10-question dry-run: 0 hallucinations recorded.
- [ ] Architecture deck + technical report committed under `docs/`.
- [ ] README updated with reproducibility instructions and the eval result.
- [ ] Final dress rehearsal completed at hour 17.

---

## 13. References

- PRD: [`docs/PRD.md`](../PRD.md) — sections cited inline.
- ADRs: [`docs/adr/`](../adr/) — 20 records, all `Status: Accepted`.
- Sub-plans: [`PLAN-A-engine.md`](PLAN-A-engine.md), [`PLAN-B-simulation.md`](PLAN-B-simulation.md), [`PLAN-C-agent-ui.md`](PLAN-C-agent-ui.md).
- Brief sources: `task/hackathon.md`, `task/stage{1,2,3}.md`, `task/20260423-HP-Briefing.pdf`.
