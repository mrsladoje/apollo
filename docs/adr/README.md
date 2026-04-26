# Architecture Decision Records

This directory captures every binding architectural decision made for **Apollo** — the HP Metal Jet S100 Digital Co-Pilot built for HackUPC 2026 (HP "When AI meets reality" challenge).

Each ADR is a short, dated record of one decision: the context that forced it, what we chose, what we rejected and why, and the tradeoffs we accepted. ADRs are **not** the place to redocument the system — that's the PRD ([`../PRD.md`](../PRD.md)). They exist so that six months from now (or under a judge's question) we can reconstruct *why* something is the way it is.

All ADRs in this directory are **Status: Accepted** as of 2026-04-25. If a decision is ever revisited, the original ADR stays in place (history) and a new ADR supersedes it.

---

## Index

### Modeling & Physics (Phase 1)

| ID | Title | One-line summary |
| --- | --- | --- |
| [ADR-001](ADR-001-hybrid-rule-based-and-pinn-modeling.md) | Hybrid rule-based + PINN modeling | Rule-based math for 5 components + DeepXDE PINN for the heater only |
| [ADR-002](ADR-002-six-components-three-subsystems.md) | Six components across three subsystems | Exceeds the brief's 1-per-subsystem minimum without bloating scope |
| [ADR-003](ADR-003-three-parallel-cascades.md) | Three parallel cascades | CSC-A recoating, CSC-B thermal-printhead (showpiece), CSC-C powder contamination |
| [ADR-004](ADR-004-linear-coupling-matrix.md) | Linear coupling matrix `M` | Single 6×6 numpy matrix; one ODE-backed cascade on top for the demo |
| [ADR-005](ADR-005-deepxde-for-heating-element-pinn.md) | DeepXDE for the heater PINN | 1-D heat-diffusion PDE residual in the loss; PyTorch MPS, no custom kernels |
| [ADR-006](ADR-006-three-failure-model-families.md) | Three failure-model families | Exponential decay, Weibull, Coffin-Manson — each maps to a real physical mechanism |

### AI / Agentic Stack (Phase 3)

| ID | Title | One-line summary |
| --- | --- | --- |
| [ADR-007](ADR-007-sqlite-historian.md) | SQLite historian | File-based, queryable, demo-friendly; no server to babysit |
| [ADR-008](ADR-008-claude-agent-sdk-and-sonnet.md) | Claude Agent SDK + Sonnet-class *(model partially superseded by ADR-022)* | Loop framework: Claude Agent SDK + Pydantic-typed tools + Langfuse OTel. Runtime model is now Gemma 4 31B per ADR-022; this ADR retains the SDK/loop rationale. |
| [ADR-009](ADR-009-pattern-c-agentic-diagnosis.md) | Pattern C — Agentic Diagnosis | Highest tier in the brief; 5 typed tools with visible UI tool-call traces |
| [ADR-010](ADR-010-late-interaction-retrieval-lateon-code-edge.md) | Late-interaction retrieval | LightOn LateOn-Code-edge (17M, Apache 2.0) over dense embeddings |
| [ADR-011](ADR-011-genetic-algorithm-for-maintenance.md) | GA (DEAP) for maintenance scheduling | Island GA with in-memory fitness; visible curve without RL training instability |
| [ADR-012](ADR-012-simulator-checkpoint-counterfactual.md) | Simulator-checkpoint counterfactuals | We own the sim; deepcopy + branch + diff beats DoWhy/EconML |
| [ADR-013](ADR-013-dark-twin-three-scenarios.md) | Three scenarios + Dark Twin framing | Barcelona/Phoenix/Stressed × NONE/FIXED/AI; reframed as parallel universes |

### Quality, Observability & UX

| ID | Title | One-line summary |
| --- | --- | --- |
| [ADR-014](ADR-014-pydantic-citations-and-refusal-grounding.md) | Pydantic citations + refusal templates | Schema-enforced citations; explicit refusal when telemetry is missing |
| [ADR-015](ADR-015-mapie-conformal-prediction.md) | MAPIE conformal prediction intervals | Calibrated 95% CI bands on every forecast, validated empirically |
| [ADR-016](ADR-016-langfuse-observability.md) | Langfuse for agent observability | Free tier, OTel auto-tracing of every tool call, split-screen trace in demo |
| [ADR-017](ADR-017-sse-streaming.md) | SSE streaming for agent + tool calls | `sse-starlette` + raw `EventSource`; no Vercel AI SDK rewrite |
| [ADR-018](ADR-018-ragas-deepeval-grounding-eval.md) | Ragas + DeepEval grounding eval | Auto-generated 30-Q eval scored in CI; turns NFR-6 into a measured artifact |
| [ADR-019](ADR-019-apollo-first-person-persona.md) | Apollo first-person persona | The brief asks for a "living entity that communicates" — we build that |

### Scope

| ID | Title | One-line summary |
| --- | --- | --- |
| [ADR-020](ADR-020-out-of-scope-rationale.md) | Out-of-scope decisions | 17 deliberately-rejected paths (voice, RL, custom Metal kernels, Omniverse, …) with per-item rationale |

### Architecture & process

| ID | Title | One-line summary |
| --- | --- | --- |
| [ADR-021](ADR-021-domain-driven-design-module-structure.md) | DDD module structure with three bounded contexts | Three bounded contexts (Engine / Simulation & History / Agent & Presentation) with shared kernel limited to `ComponentId`; citation validator is the ACL |
| [ADR-022](ADR-022-gemma-4-31b-and-gepa-optimized-prompt.md) | Gemma 4 31B + GEPA-optimized prompt as Apollo's runtime LM | Supersedes ADR-008's *model* (SDK/loop unchanged): Apollo runs on Gemma 4 31B with a system prompt compiled by `dspy.GEPA` (Agrawal et al., ICLR 2026 Oral); Opus 4.7 is the offline reflection LM and the comparator on the FR-W.9 grounding eval — unlocks MLH "Best Use of Gemma" |

---

## Conventions

- **Numbering** is monotonically increasing. Don't reuse numbers, even after supersession.
- **Status values:** `Proposed` → `Accepted` → optionally `Deprecated` or `Superseded by ADR-NNN`.
- **One decision per ADR.** If you find yourself describing two unrelated things, split.
- **Be honest about tradeoffs.** Every ADR has a "Negative / accepted tradeoffs" section. If yours doesn't, the decision is probably hiding something.
- **Cite the PRD section** that motivated the decision so a reader can verify the constraint still applies.
- **List ≥3 alternatives** considered, with one-line rejection reasons each.

## When to add a new ADR

Add one when you make a decision that:
- Locks a library, framework, or model (e.g. swapping LateOn-Code-edge for a different retriever)
- Changes a data contract (schema fields, tool signatures)
- Adds or removes a system component
- Reverses a previous ADR (the new ADR's status is `Accepted`; the old one's is `Superseded by ADR-NNN`)

You do **not** need an ADR for routine implementation choices (function naming, internal helper modules, test layout) — those live in code review.

## Source-of-truth chain

```
brief (task/) → PRD (docs/PRD.md) → ADRs (docs/adr/) → code
```

If two of these disagree, the rightmost one is real and the others are stale. Open a PR to reconcile.
