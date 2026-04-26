# ADR-021: Domain-Driven Design module structure with three bounded contexts

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §6.1, §6.2, §6.3, §6.4, §10, §11, §13, §14; ADR-002 (six components / three subsystems), ADR-007 (SQLite historian), ADR-014 (Pydantic citations as ACL), ADR-019 (Apollo persona), ADR-020 (out-of-scope); project `CLAUDE.md` rule "Follow Domain-Driven Design with bounded contexts"

## Context

The project-level `CLAUDE.md` mandates DDD with bounded contexts as a behavioral rule. The PRD's three-phase structure (Phase 1 engine, Phase 2 simulation+historian, Phase 3 agent+UI) and the master plan's three-developer phase-aligned split (`docs/plans/PLAN.md` §4) already imply three bounded contexts. This ADR makes that implicit DDD structure explicit so the parallel build does not accidentally create cross-context coupling.

The 36 h hackathon budget plus a 3-developer team makes bounded-context isolation the load-bearing pattern: each developer ships and tests their slice in isolation against the frozen contracts in `PLAN.md` §3 (Plan A → Plan B, Plan B → Plan C, Plan C → user). DDD context boundaries **are** the parallel-build seams. Mocks-first (PLAN §2.2) only works because each context has a published language the other side can stub.

Without an explicit ADR, three failure modes are likely:
1. The "shared kernel" bloats — every developer adds "just one more thing" until the kernel is half the codebase and nothing is independently buildable.
2. The canonical 6-component enum (ADR-002, PLAN §3.4) gets re-typed as bare strings across modules, defeating the schema enforcement of ADR-014.
3. The Pydantic citation validator loses its identity as an Anti-Corruption Layer and becomes "yet another validator," which makes future changes to historian internals leak into agent prose.

## Decision

We adopt three bounded contexts, one shared kernel, an explicit context map, and a mechanical enforcement rule.

**Three bounded contexts.** Each owns one directory under `src/`, one developer, one `contracts.py` published-language module, and one ubiquitous language:

| Context | Path | Owner | Ubiquitous language |
| --- | --- | --- | --- |
| Engine | `src/engine/` (Plan A) | Dev A | Component, Subsystem, Cascade, Health, Status, Driver, Forecast |
| Simulation & History | `src/sim/` (Plan B) | Dev B | Run, Scenario, Policy, Tick, Obituary, Counterfactual, Dark Twin, Retrieval |
| Agent & Presentation | `src/apollo/agent/` + `src/apollo/api/` + `frontend/` (Plan C) | Dev C | Tool Call, Citation, Refusal, Severity, Trace, Persona |

**Shared kernel** is intentionally minimal: the `ComponentId` enum and the small set of cross-context value objects in `src/engine/contracts.py` (`ComponentStatus`, the component-field type used by `Citation`). Every other domain term lives inside its owning context. Adding to the shared kernel requires the 3-way handshake from `PLAN.md` §3 / §2.4 (all three developers sign off; an ADR is updated).

**Context map / integration patterns:**
- **Engine → Simulation**: Customer/Supplier with Engine as Supplier. Simulation calls `engine.step()` and `engine.forecast()` through the published-language Pydantic contract in `src/engine/contracts.py`.
- **Simulation → Agent**: Customer/Supplier with Simulation as Supplier. Agent consumes the four function tools through `src/sim/contracts.py`.
- **Agent → User (frontend)**: Open Host Service. `ApolloResponse` and `SSEEvent` are the published language consumed by the React frontend and the eval CI.
- **Agent ↔ Historian**: protected by an **Anti-Corruption Layer** = the Pydantic citation validator (ADR-014). Every outbound citation must resolve against the historian by primary key `(run_id, t, component_id)` before crossing the boundary; unresolvable citations are downgraded to REFUSAL. No agent-context concept (e.g. raw "tool call result") leaks into user-facing text without ACL transit.

**Aggregate roots** (one per context, owning their invariants):
- Engine: `EngineState` — encapsulates `ComponentState[]` + coupling matrix `M` + RNG. Invariant: cascade transitions go through the aggregate, never by mutating components directly.
- Simulation: `Run` — encapsulates the timeline of `HistorianRow`s, scenario, and policy. Invariant: `Run` is append-only; counterfactuals branch via deepcopy (ADR-012), never by editing past rows.
- Agent: `ApolloResponse` — encapsulates text, citations, tool calls, severity, trace URL. Invariant: `len(citations) ≥ 1` unless `severity == "REFUSAL"` (NFR-6, NFR-7, ADR-014).

**Domain events** that cross context boundaries are explicit, named, and Pydantic-typed:
- `ComponentDegraded`, `ComponentFailed`, `CascadeTriggered` (Engine → Simulation).
- `RunCompleted`, `ObituaryEmitted` (Simulation → Agent + UI).
- `CitationResolved`, `ResponseRefused` (Agent → eval / Langfuse, ADR-016, ADR-018).

**Repository abstractions:** `HistorianRepository` (`src/sim/historian/`, ADR-007) and `RetrievalIndex` (`src/sim/retrieval/`, ADR-010) are the only data-access surfaces in the Simulation context. The Engine context is pure compute and owns no repositories. The Agent context owns no repositories — it goes through Simulation's tools.

**Ubiquitous-language enforcement rules:**
- String component names are a bug; only `ComponentId` enum members are allowed in code, contracts, and persisted data. A pytest rule (`tests/architecture/test_no_string_components.py`) greps `src/` for string literals matching component names and fails if found outside the enum definition itself or test fixtures.
- The `ComponentId` enum lives only in `src/engine/contracts.py`. Re-defining it elsewhere is both a circular-import bug and a DDD violation.
- Each `contracts.py` is the published language of its context. Import direction is one-way: Agent imports Sim imports Engine; never the reverse.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Layered architecture (controllers / services / repos) | Scatters cascade and counterfactual logic across layers, hides the three-phase structure the PRD foregrounds, and makes the 3-dev split harder to keep clean. |
| Single-module monolith | Fastest to start, guarantees merge conflicts at hour 4; loses the parallel-build speedup the hackathon depends on. |
| Full hexagonal (ports + adapters everywhere) | Overkill for 36 h; ports for the historian and retrieval are already de-facto present via repository abstractions; adapter layers around the engine would dilute physics code. |
| Microservices (one process per context) | Operationally heavy, demo-fragile under R-7 Wi-Fi failure; contexts share a process for latency reasons (NFR-2 < 50 ms step, NFR-5 < 6 s e2e). |
| Anemic domain model (Pydantic dataclasses + free functions only, no aggregates) | The default temptation; rejected because the citation invariant and the cascade-state invariant each need a single owner. |
| "DDD-lite" — bounded contexts only, no shared-kernel discipline | Rejected because the canonical 6-component enum needs to be the single source of truth (PLAN §3.4); that **is** a shared kernel and pretending otherwise causes drift. |

## Consequences

**Positive:**
- **Parallel build is unblocked.** Mocks-first (PLAN §2.2) works because each context has a published language; contracts files are the only thing that must exist at hour 0.
- **The canonical 6-component enum is structurally protected.** One enum, one location, one architecture test that fails CI on string drift.
- **The citation validator gets a name.** Calling it the Anti-Corruption Layer between Agent and Historian makes ADR-014's three enforcement layers a context-map fixture rather than ad-hoc validation.
- **Aggregates make NFR-6 / NFR-7 enforceable invariants.** The "no citation ⇒ REFUSAL" rule lives on the `ApolloResponse` aggregate, not in scattered `if` checks.
- **The repo layout in PLAN §10 maps 1:1 to bounded contexts**, so reading the code reinforces the model rather than hiding it.

**Negative / accepted tradeoffs:**
- **Small upfront cost** in writing `contracts.py` files at hour 0 (already in the plan, not new work).
- **Cross-context features now require either a domain event or a contract change**, both of which trigger the 3-way handshake from PLAN §3 / §2.4. This is friction by design; we accept it in exchange for build-time isolation.
- **Some duplication of Pydantic model shapes** between contexts (e.g., the historian row type vs. the engine state representation). Acceptable: each context owns its own model, translated at the boundary, which is the price of bounded-context isolation.

**Neutral / mitigations:**
- This ADR cross-references all binding ADRs that constrain it (ADR-002 components, ADR-007 historian, ADR-014 citations as ACL, ADR-019 persona, ADR-020 scope) so future readers can reconstruct the lattice.
- The architecture test (`tests/architecture/test_no_string_components.py`) is part of CI; ubiquitous-language drift fails the build.
- Per `docs/adr/README.md`, any deviation from this structure requires a new ADR superseding ADR-021, not an in-place edit.

## References

- PRD §6.1, §6.2, §6.3 (three-phase functional decomposition), §6.4 (demo-differentiator features that span contexts via events), §10 (coupling and cascades — Engine context), §11 (ML/AI specs — split across Engine and Simulation), §13 (architecture overview), §14 (data model — `(run_id, t, component_id)` primary key shared via the kernel)
- `docs/plans/PLAN.md` §3 (frozen integration contracts), §3.4 (canonical 6-component enum), §4 (work split), §10 (repo layout), §2.4 (ADRs are binding)
- Project `CLAUDE.md` — "Follow Domain-Driven Design with bounded contexts"
- Related: ADR-002 (component model in the kernel), ADR-007 (historian as repository), ADR-014 (citation validator as ACL), ADR-019 (persona belongs to the Agent context), ADR-020 (scope discipline)
- Evans, *Domain-Driven Design: Tackling Complexity in the Heart of Software* (2003) — bounded contexts, shared kernel, anti-corruption layer
- Vernon, *Implementing Domain-Driven Design* (2013) — context maps, aggregate design, domain events
