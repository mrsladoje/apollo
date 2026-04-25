# ADR-016: Langfuse for agent observability

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.7, §6.4 FR-W.7, §17 M9c, §16.2; ADR-008 (Claude Agent SDK), ADR-009 (Pattern C — Agentic Diagnosis), ADR-017 (SSE streaming)

## Context

Pattern C — Agentic Diagnosis (ADR-009) is the highest-tier deliverable in the brief, and its value depends on the agent's reasoning being *visible*. The chat panel itself shows tool calls inline (FR-3.7), but during the live "Ask Apollo" segment we want a second, denser surface for judges: a real trace UI showing every prompt, tool-call latency, token count, and intermediate result, ideally projected side-by-side with the dashboard.

We also need this for our own debugging. Apollo's grounding protocol (FR-3.5, NFR-6) depends on the agent reliably calling tools before answering; without trace inspection we cannot diagnose silent regressions in tool-use behavior. The decision surfaced during the April 25 SOTA scan once Anthropic published their official OpenTelemetry integration for the Claude Agent SDK, which makes the integration a one-line environment variable rather than custom span instrumentation.

## Decision

Adopt **Langfuse** (free cloud tier; self-hosted Docker as offline fallback) attached to the Claude Agent SDK via the official Anthropic-blessed OpenTelemetry integration. Concretely:

- Install `langsmith[claude-agent-sdk]` plus the `langfuse` Python SDK.
- Set `LANGSMITH_OTEL_ENABLED=true` plus the Langfuse `PUBLIC_KEY` / `SECRET_KEY` / `HOST` env vars.
- Every Apollo agent invocation emits an OTel trace containing the system prompt, user query, every tool call with input/output, latency per span, token usage, and the final response.
- The frontend appends a small "Trace" link beside each Apollo response that deep-links to the corresponding Langfuse run (PRD §15).
- Demo move: split-screen Langfuse alongside the dashboard during the wild-card Q&A segment.

Demo gate: 100 % of agent invocations captured with a full tool-call timeline (PRD §16.2).

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Arize Phoenix | Self-host only; no managed cloud free tier; setup cost too high for a 36-h build. |
| Helicone | Proxy-based; intercepts at HTTP layer rather than agent-loop layer, so tool-call structure is flattened. |
| Native LangSmith | Requires migrating off Claude Agent SDK to LangChain/LangGraph; contradicts ADR-008. |
| Laminar | Newer, smaller community, no official Anthropic integration as of Apr 2026. |
| Custom OTel + Jaeger | Hours of span instrumentation; no UX for tool-call timelines. |
| No observability | Loses a literal "watch Apollo think" demo surface; debugging tool-use regressions becomes guesswork. |

## Consequences

**Positive:**
- One-line setup via official integration; ~1 h budgeted (M9c).
- Tool-call timeline becomes a screen-shareable demo asset, not just a log file.
- Token/latency data feeds directly into the technical report's performance section (NFR-5).
- Free tier sufficient for hackathon-scale traffic; no vendor commitment.

**Negative / accepted tradeoffs:**
- Cloud dependency at demo time (R-7). Mitigation: self-hosted Docker fallback pre-pulled; if both fail we fall back to chat-panel inline trace.
- Outbound network call per agent turn adds ~50 ms latency. Acceptable under NFR-5's 6 s budget.
- Adds an external service to disclose in the technical report (NFR-10).

**Neutral / mitigations:**
- Langfuse keys live in `.env`; no commit risk per project security rules. Pre-demo dry-run validates the Trace link works end-to-end.

## References

- PRD §11.7, §6.4 FR-W.7, §17 M9c, §16.2, §15
- Langfuse: https://langfuse.com/docs
- Anthropic Claude Agent SDK OTel integration: `langsmith[claude-agent-sdk]`
