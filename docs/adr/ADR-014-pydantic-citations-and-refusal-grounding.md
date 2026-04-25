# ADR-014: Pydantic-enforced citations + refusal templates for zero-hallucination grounding

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD FR-3.3, FR-3.5, NFR-6, NFR-7, R-6; ADR-008, ADR-009, ADR-018

## Context

The brief's Phase 3 framing draws a hard line: an AI that hallucinates in an industrial-operations context is a **non-starter**. PRD §2.2 calls this out as the fourth pain point and §16.2 codifies the differentiation metric: 0% hallucination on the eval set, 100% citation coverage on non-refusal responses.

The naive approach — "tell the model in the system prompt to always cite and never hallucinate" — fails reliably. LLM compliance with prompt-level grounding instructions degrades under (a) ambiguous queries, (b) missing telemetry, (c) long tool traces where the model fills gaps from training memory. Risk R-6 calls this out explicitly.

Post-hoc filtering ("regex for citation patterns and reject responses without them") catches *some* hallucinations but not the dangerous class: well-formed responses with **fabricated** citations. The failure mode is not "no citation," it is "a citation that points at a `(run_id, component, timestamp)` triple the historian doesn't actually contain."

The third option — refuse to generate at all when no telemetry exists — needs a structured refusal so the agent's behavior under-grounded is *predictable* and *demoable*, not "the model hedged this time and didn't last time."

## Decision

Every Apollo response is a **Pydantic-validated structured object** with the following non-negotiable schema:

```python
class ApolloResponse(BaseModel):
    severity: Literal["INFO", "WARNING", "CRITICAL", "REFUSAL"]
    text: str
    citations: list[Citation]  # min_length=1 if severity != "REFUSAL"
    tool_calls: list[ToolCall]

class Citation(BaseModel):
    run_id: str
    component: str  # must be in the canonical 6-component enum
    timestamp: datetime
    # validator: must resolve to a real row in component_states or drivers
```

Three enforcement layers run on every response:

1. **Schema validation** — Pydantic rejects responses missing `citations` (when not REFUSAL) or with malformed timestamp / component values.
2. **Citation resolution** — every `Citation` is verified against the historian by primary key `(run_id, t, component_id)` *before* the response is streamed to the user. Unresolvable citations downgrade the response to a REFUSAL with the structured template.
3. **Refusal template** — when the agent's tools return zero rows for the user's query, the agent emits a fixed refusal object (`severity="REFUSAL"`, empty `citations`, text from a template). This is the *only* path where `citations` is allowed empty.

The refusal template is a **product feature**, not a fallback: in the live "Ask Apollo" segment (FR-W.5), a refusal is a positive signal — judges see the guardrail work in real time.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Prompt-only grounding ("always cite, never hallucinate") | Compliance degrades under ambiguous queries and missing telemetry; cannot pass the 0% hallucination gate (NFR-6); R-6 explicitly calls this out. |
| Regex / post-hoc citation filter | Catches "no citation" but not "fabricated citation"; the dangerous failure mode is well-formed responses with bogus `(run_id, component, timestamp)` triples. |
| LLM-as-judge for grounding (a second model checks each response) | Adds latency (NFR-5 < 6 s p95); the judge LLM can itself hallucinate; doesn't solve the fabrication problem deterministically. |
| Free-text responses with optional structured citations sidecar | Citations become decorative; the response text can still hallucinate; the schema needs to be load-bearing on the *response*, not adjacent to it. |
| No refusal template — model hedges in prose when ungrounded | Hedging is non-deterministic and demos badly; refusals must be visually distinct (REFUSAL severity badge) so judges can tell guardrails fired. |
| RLHF / fine-tune on a grounding dataset | Days of work; no training pipeline; loses model agility; we don't have a labeled grounding corpus. |
| Constrained decoding (logit masking on citation slots) | Provider-API limitations on Anthropic SDK; brittle across model upgrades; engineering cost out of proportion to a 36 h hackathon. |

## Consequences

**Positive:**
- **Hallucination-by-fabricated-citation is structurally impossible** — every citation must resolve to a real historian row before the response leaves the server.
- **The refusal template turns "I don't know" into a demoable feature.** Live Q&A failure modes become guardrail wins instead of embarrassments (R-8 mitigation).
- **NFR-6 (0% hallucination) and NFR-7 (100% citation coverage) become enforceable invariants**, not aspirations. The Ragas + DeepEval CI (FR-W.9) measures the gate, but Pydantic validation *is* the gate.
- **The schema is the contract** between Phase 2 (historian) and Phase 3 (agent). Tool outputs, citations, and the response object all share the canonical 6-component enum and the `(run_id, t, component_id)` key — a single source of truth.
- **Streaming integration is clean** (ADR-017): tool-call deltas stream raw, but the *final* text+citation object is validated atomically before the `done` SSE event fires.

**Negative / accepted tradeoffs:**
- **Validation latency** — citation resolution adds an extra historian round-trip per response. Mitigated by the `(run_id, component_id, t)` index in §14; budget is single-digit milliseconds.
- **Strict schemas reduce conversational flexibility.** Apollo cannot riff casually with the operator persona — every utterance must carry citations or be a refusal. We accept this; it matches the calm-professional persona (FR-W.1) and the industrial framing.
- **A latent class of failure** remains: a response whose *prose* misrepresents a citation that nonetheless resolves. Pydantic doesn't catch "the citation is real but the agent's claim about it is wrong." Mitigated by FR-W.9 faithfulness scoring (DeepEval) and the late-interaction retrieval grounding the prose in retrieved telemetry.
- **Refusal template can be over-eager** — if a tool returns zero rows because of a query bug, the agent refuses instead of debugging. We log refusals to Langfuse (FR-W.7) so we can spot patterns during dry-runs.

**Neutral / mitigations:**
- Pydantic validation errors during the demo are caught by a final-stage exception handler that emits a refusal rather than crashing the SSE stream.
- The canonical 6-component enum is shared with ADR-002's component definitions and validated once at import time.
- The eval set (FR-W.9) explicitly contains *unanswerable* questions to verify the refusal path stays at 100%.

## References

- PRD FR-3.3 (citations required), FR-3.5 (refusal template), NFR-6 (0% hallucination), NFR-7 (100% citation coverage), R-6 (R-6 mitigation list literally names "Pydantic-enforced citations" + "refuse-to-answer template")
- §14 (data model: indexes on `(run_id, component_id, t)` make citation resolution cheap)
- §16.2 (differentiation metrics: hallucination rate, citation coverage, live-Q&A wild-card grounding)
- Pydantic v2: https://docs.pydantic.dev/
- Related: DeepEval `FaithfulnessMetric` + `HallucinationMetric` (PRD §11.8)
