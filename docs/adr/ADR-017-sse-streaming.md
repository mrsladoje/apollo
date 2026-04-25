# ADR-017: Server-Sent Events for streaming agent responses

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.7, §6.4 FR-W.8, §17 M9d, §15; ADR-008 (Claude Agent SDK), ADR-016 (Langfuse), ADR-020 (Out-of-scope: Vercel AI SDK)

## Context

A non-streaming chat UI for an agent that takes 3–6 seconds to answer (NFR-5) is a dead demo. Judges stare at a spinner, then text appears all at once, and the carefully constructed sequence of tool calls — which is the *whole point* of Pattern C (ADR-009) — is invisible until after the fact.

We want the chat panel to feel alive: tokens stream in as Apollo speaks, and tool calls appear as collapsible cards the moment the tool starts executing, then update with input/output as the agent's loop progresses. This requires a unidirectional server-to-client streaming channel carrying *typed events*, not raw text. The decision surfaced during the April 25 SOTA scan as part of the same "make the agent visible" theme as Langfuse (ADR-016).

We are committed to the existing FastAPI + React + Recharts stack (PRD §15). Any streaming choice that forces a frontend-framework rewrite is disqualified.

## Decision

Adopt **`sse-starlette`'s `EventSourceResponse`** on the FastAPI backend, consumed by the browser's native `EventSource` API on the React side. No additional client library.

Event schema (typed JSON in each `data:` payload):

```ts
{ type: "text-delta",       payload: { token: string } }
{ type: "tool-call-start",  payload: { tool: string, args: object, call_id: string } }
{ type: "tool-result",      payload: { call_id: string, result: object } }
{ type: "citation",         payload: { run_id, component, timestamp } }
{ type: "done",             payload: { trace_url: string } }
```

The React chat component maintains a per-message reducer that appends `text-delta` payloads to the rendered text, opens a collapsible card on `tool-call-start`, fills it on `tool-result`, attaches clickable citations on `citation`, and closes the stream on `done`. The Langfuse trace URL (ADR-016) ships in the `done` payload.

Demo gate: tool calls visible in the chat panel *as they execute*, not only after completion (PRD FR-W.8).

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **Vercel AI SDK** | Excellent DX but assumes Next.js / `useChat` React hooks; forces migration of an already-built Recharts dashboard. Hours of rewrite for no demo gain. (Also recorded in Appendix B and ADR-020.) |
| WebSockets | Bidirectional channel for a unidirectional problem; needs reconnect logic, sub-protocol, and an extra dependency. Overkill. |
| HTTP long-polling | Terrible UX; bursty rendering; defeats the "narrate while thinking" goal. |
| Non-streaming JSON response | Boring demo; spinner for 3–6 s; tool-call structure invisible until after answer arrives. |
| gRPC-Web streaming | Requires Envoy/proxy and protobuf toolchain; orthogonal to FastAPI. |
| HTTP/2 server push | Browser support effectively deprecated; not designed for this pattern. |

## Consequences

**Positive:**
- Native browser API; zero client dependencies beyond what the project already ships.
- `sse-starlette` is a thin async generator wrapper around FastAPI — ~30 lines of backend code.
- Typed event schema makes the protocol self-documenting and easy to mock for the eval harness (FR-W.9).
- Plays naturally with Langfuse (ADR-016): the `done` event carries the trace URL.

**Negative / accepted tradeoffs:**
- Unidirectional only. If we ever want client-to-agent mid-stream cancellation we will need a separate `POST /cancel`. Acceptable for hackathon scope.
- Some corporate proxies buffer SSE; mitigated by `Cache-Control: no-cache` and an initial heartbeat. Demo Wi-Fi (R-7) tested in dry-run.
- Reconnection logic is the developer's problem if a stream drops mid-token. We treat dropped streams as a hard error and the user re-asks; acceptable for 36-h scope.

**Neutral / mitigations:**
- Adds 2.5 h to critical path (M9d); cuttable before M9b/M9c if schedule slips (§17 cut order).

## References

- PRD §11.7, §6.4 FR-W.8, §17 M9d, §15
- `sse-starlette`: https://github.com/sysid/sse-starlette
- MDN `EventSource`: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
