# ADR-009: Pattern C — Agentic Diagnosis with visible tool calls

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.5, §15, FR-3.2, FR-3.6, FR-3.7, FR-W.5; ADR-008 (Claude Agent SDK), ADR-010 (Late-interaction)

## Context

The HP "When AI meets reality" brief defines three Phase 3 interaction patterns:

- **Pattern A — Simple Context Injection:** dump recent telemetry into the prompt and let the LLM answer.
- **Pattern B — Contextual RAG:** retrieve relevant chunks and inject as context.
- **Pattern C — Agentic Diagnosis:** the LLM plans and executes multi-step tool calls against the historian, reads results, and decides what to do next.

Pattern C is explicitly the highest-tier pattern in the brief. It is also the only one that produces an *artifact* — a visible tool trace (FR-3.7) — that can be projected on a demo screen alongside the chat. For HP judges who score on grounding and rigor, "watch the agent run `query_historian`, then `late_interaction_search`, then synthesize a citation" is the differentiator.

The cost is real: Pattern C is the highest-engineering-risk option of the three. It requires reliable tool-calling (handled by ADR-008), strict input/output schemas, refusal-when-empty behavior (FR-3.5), citation enforcement (FR-3.3), and a UI that streams tool start/end events (FR-W.8). If any link breaks, Pattern C degrades worse than Pattern A would — instead of a wrong answer, we get a stuck agent or a hallucinated tool call.

## Decision

Implement **Pattern C** as Apollo's only Phase 3 pattern. The agent (Claude Agent SDK + Sonnet-class, per ADR-008) is given exactly five tools, matching FR-3.6:

1. `query_historian(run_id, component, time_range) → rows` — point queries on the SQLite historian.
2. `late_interaction_search(query, run_id?) → ranked_rows` — semantic retrieval over telemetry via PyLate (ADR-010).
3. `compare_runs(run_ids, metric) → comparison` — side-by-side metric comparison across NONE / FIXED / AI universes (ADR-013).
4. `run_counterfactual(run_id, branch_t, alternate_action) → diff` — checkpoint-and-branch replay (ADR-012).
5. `plot_component_history(run_id, component) → chart_payload` — emits a chart spec the frontend renders inline.

Every tool input/output is a Pydantic model. The system prompt enforces: (a) at least one tool call before any non-trivial answer, (b) every claim cited as `(run_id, component, timestamp)`, (c) refuse with the structured template if no supporting telemetry was retrieved. Tool calls are streamed to the UI via SSE (FR-W.8), where they render as collapsible cards from the moment the tool starts.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **Pattern A — Context injection only** | Prompt explosion as the historian grows; no tool trace to demo; fundamentally cannot answer cross-run or counterfactual questions (US-3, US-4). |
| **Pattern B — Plain RAG (dense embeddings + stuff into context)** | Strictly weaker than Pattern C: still no counterfactual capability, no `compare_runs`, and we lose the "watch the agent reason" demo moment. Late-interaction (ADR-010) already gives us better recall than dense RAG. |
| **Hybrid Pattern B → C escalation** | Tempting but doubles the surface area: two prompt paths to test, two refusal regimes, one more failure mode. Picking one and making it work end-to-end is the hackathon-correct choice. |
| **Pattern C with a larger tool set (10+ tools)** | More tools = more confusion in the agent's plan + more schemas to validate. Five tools cover all six user stories; we resist scope creep. |
| **Pattern C without visible tool calls** | Saves UI work but kills the differentiator. The whole reason Pattern C beats RAG on the demo floor is that you can *see* the agent reason. |

## Consequences

**Positive:**
- Highest brief-tier pattern → maximum points on the rubric Anthropic and HP literally published.
- Visible tool calls turn the agent from a black box into a demo asset (FR-3.7, FR-W.5).
- Counterfactual and cross-run queries become first-class — `run_counterfactual` and `compare_runs` are not bolted-on.
- Refusal-on-empty (FR-3.5) is structurally enforced: if no tool returned data, the agent has nothing to cite, and the validator rejects an uncited response.

**Negative / accepted tradeoffs:**
- Highest engineering risk of the three patterns. A flaky tool schema or a Sonnet planning lapse breaks the demo more visibly than Pattern A would. Mitigated by R-6 controls (Pydantic validation, refusal template, eval set with 0% hallucination gate, per FR-W.9).
- Latency budget is tight: 5 tools × ~500 ms each + model time must fit under 6 s p95 (NFR-5). We accept that complex queries may push closer to the bound; cap at three tool calls per turn unless explicitly needed.
- More moving parts to instrument. Mitigated by Langfuse (ADR-008 / FR-W.7) — one trace shows the whole loop.

**Neutral / mitigations:**
- If tool-calling reliability degrades during the build, the SDK supports forced-tool prompting, which is a graceful fallback before dropping to Pattern B.
- Tool count (5) is a hard ceiling for the hackathon. Adding a sixth tool requires re-running the eval set (FR-W.9).

## References

- PRD §11.5, §15 (sample interaction), FR-3.2, FR-3.6, FR-3.7, FR-W.5
- HP brief Phase 3 patterns A/B/C
- Anthropic agent design pattern docs
