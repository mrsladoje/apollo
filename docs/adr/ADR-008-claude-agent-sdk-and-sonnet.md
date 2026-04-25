# ADR-008: Claude Agent SDK + Sonnet-class model

- **Status:** Partially superseded by [ADR-022](ADR-022-gemma-4-31b-and-gepa-optimized-prompt.md). The Claude Agent SDK + Pydantic-typed-tools + Langfuse-OTel decision (the *loop framework*) stays in effect. The runtime *model id* is now Gemma 4 31B Dense per ADR-022. Read this ADR for the SDK/loop rationale; read ADR-022 for the model choice.
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.5 (Agentic Loop), §18.1, FR-3.2, FR-3.6, FR-W.7, NFR-5; ADR-009 (Pattern C); ADR-022 (model supersession)

## Context

Apollo's Phase 3 is an agentic loop: the model must plan a sequence of tool calls (`query_historian`, `late_interaction_search`, `compare_runs`, `run_counterfactual`, `plot_component_history`), interleave reasoning with tool results, and produce a cited, severity-tagged answer in under 6 s p95 (NFR-5). The brief itself frames Pattern C — agentic diagnosis with multi-step tool use — as the highest-tier interaction pattern. Whatever stack we pick has to make tool calls *reliable* and *observable*, because the demo literally shows the tool trace on screen (FR-3.7).

We also need cheap observability hooks: Langfuse via OpenTelemetry is FR-W.7, and the brief implies a polished demo with a live Langfuse trace next to the dashboard. The integration is officially supported by the Claude Agent SDK via `langsmith[claude-agent-sdk]` and `LANGSMITH_OTEL_ENABLED=true`. Other SDKs would force us to write the OTel bridge ourselves.

Model choice is a separate axis: cost, latency, and reasoning quality. The hackathon is on synthetic telemetry where the *hard part* is multi-hop tool sequencing and grounded narrative writing — not frontier symbolic reasoning. Anthropic-blessed Sonnet-class models hit the sweet spot most credibly. The exact Sonnet revision available at implementation time is not knowable in advance, so the decision has to commit to the *class* and let the build pin the version.

## Decision

Use the **Claude Agent SDK** (Anthropic-official) for the agent loop, and a **current Sonnet-class Claude model** as the reasoning backbone (e.g. `claude-sonnet-4-7` or whatever Sonnet-tier model is GA at build time on the Anthropic API). All tool schemas are typed Pydantic models registered with the SDK; tool calls flow through the SDK's iteration interface so we can stream `tool-call-start`/`tool-result` SSE events (FR-W.8). The exact model id is locked in `config/agent.yaml` at the start of the build window, not at architecture time.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **LangGraph** | Powerful graph-based agent orchestration, but heavier abstraction, more opinionated state-machine model, and the OTel/Langfuse story is via LangSmith, not the same first-class Anthropic path. Overkill for a 5-tool agent. Kept as fallback per PRD §20. |
| **CrewAI** | Multi-agent role-playing framework. Apollo is one agent with five tools, not a crew — CrewAI's abstractions add ceremony without solving our actual problem (grounded tool use + citation enforcement). |
| **AutoGen** | Microsoft's multi-agent framework. Same mismatch as CrewAI plus a heavier Python footprint and weaker streaming/SSE story. |
| **Custom OpenAI tool-calling loop** | Possible, but we lose Sonnet's tool-use reliability advantage and have to reimplement retry/loop semantics, observability, and refusal handling by hand. |
| **Opus-class model** | Stronger reasoning but materially slower (worse for NFR-5's 6 s p95) and 5-10× more expensive per call. Pattern C latency budget already tight; live Q&A would feel sluggish. |
| **Haiku-class model** | Fast and cheap, but tool-use planning over 3-5 hops with citation discipline is exactly where Haiku-tier models start to drop calls or hallucinate citations. We tested similar patterns previously; not worth the FR-3.5 risk. |

## Consequences

**Positive:**
- Pydantic-typed tools + SDK validation = FR-3.6 schemas stay enforced end-to-end.
- Native OTel exporter wires straight into Langfuse (FR-W.7) with one env var.
- Sonnet's tool-use reliability is the best documented public option for Pattern C; reduces agent-hallucination risk (R-6) at the model layer rather than only at the validator layer.
- Model id is a config knob, so a same-day model upgrade (e.g. Sonnet point release) is a one-line change.

**Negative / accepted tradeoffs:**
- Lock-in to Anthropic's API and a working Wi-Fi connection at the venue (R-7). Mitigation: pre-record canned responses for the scripted demo path; live mode is the second segment, not the first (NFR-9).
- Sonnet costs more than Haiku per request. Acceptable at hackathon scale; would re-evaluate for production fleet rollout.
- Agent SDK is younger than LangChain/LangGraph; rough edges around streaming and cancellation are possible. Documented as risk; LangGraph remains the contingency per PRD §20.

**Neutral / mitigations:**
- Final model id documented in `config/agent.yaml` and surfaced in the README + Langfuse trace, so any judge asking "which model?" gets an exact answer.
- If Sonnet latency creeps over 6 s for the canonical query, we shorten tool-call breadth before dropping model class.

## References

- PRD §11.5, §11.7, §18.1, §18.2; FR-3.2, FR-3.6, FR-W.7, NFR-5
- Claude Agent SDK: <https://docs.anthropic.com/claude/docs/agent-sdk>
- Langfuse + Claude Agent SDK OTel integration docs
- PRD Appendix B: "Local LLM fallback (Ollama + Qwen 2.5) → rejected"
