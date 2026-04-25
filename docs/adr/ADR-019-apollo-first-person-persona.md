# ADR-019: Apollo first-person persona

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §6.4 FR-W.1, §13, §15, §5 US-1, §4 P-1; ADR-008 (Claude Agent SDK), ADR-009 (Pattern C — Agentic Diagnosis), ADR-014 (Pydantic citations)

## Context

The HP brief frames the challenge as building "an intelligent, *living* entity that communicates" — not a dashboard, not a chatbot bolted on a CRUD app. Judges from HP's industrial side will have seen many neutral-tone "the system reports..." dashboards, and Pattern C (ADR-009) was selected precisely because it lets us go further. The persona is not decoration; it is the surface area through which the cascading-failure narrative (CSC-A/B/C) becomes legible.

We must decide between a neutral assistant tone ("The nozzle plate is at 23 % health"), a branded but impersonal product ("Apollo reports..."), and a fully first-person twin that *speaks as the printer itself* ("I'm Apollo. My recoater blade is wearing 12 % faster than usual; the powder is drier than my spec range."). The choice has direct demo and risk implications: first-person is unforgettable when it lands, mortifying when it misfires for an industrial audience.

## Decision

Apollo speaks in the **first person**, and so do its components when clicked. Apollo is the integrating voice of the printer; component-level UI (the six tiles in §15) exposes per-component `speak()` methods that return short first-person strings drawn from current state (e.g. *"My bearing is 41 °C and rising; that's outside my comfort band"*).

The persona is governed by a single system prompt loaded into the Claude Agent SDK (ADR-008): **calm, professional, technically precise, never alarmist, never theatrical**. No exclamation marks. No "OH NO!" Severity is communicated by the structured `INFO | WARNING | CRITICAL` tag (FR-3.4) and by *what* Apollo says, not by tonal escalation. Component obituaries (FR-W.4) inherit the same voice.

This decision is binding for the demo path. If the eval set (ADR-018) flags any persona prompt regressing grounding behavior, the persona prompt yields — grounding wins.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Neutral assistant ("The system reports component 3 has degraded.") | Indistinguishable from any dashboard with an LLM bolted on; no narrative pull; ignores the brief's "living entity" language. |
| Branded but impersonal ("Apollo reports that nozzle health is 0.23.") | Splits the difference and gets neither benefit. Still feels like a third-party tool announcing facts. |
| No persona at all (raw structured output) | Demo dies. Tool calls are visible (FR-3.7) but there's no voice tying them together; cascade narration becomes a wall of JSON. |
| Theatrical / dramatic personality ("I'm in pain!") | Catastrophic for an HP industrial-engineering judge. Reads as a toy, undermines every grounded-citation move we've built. |
| Per-persona switching (CFO/Engineer/Tech) | Good idea; ~2 h cost; better invested in voice quality. Logged in §21 and ADR-020. |
| Voice / audio output | Excluded outright in §3.4. Would amplify both the upside and the risk. |

## Consequences

**Positive:**
- Directly addresses the brief's "living entity" framing — a hard-to-fake differentiator.
- US-1 ("how is the printer doing?") becomes immediately compelling rather than tabular.
- Component obituaries (FR-W.4) and the wild-card Q&A (FR-W.5) gain emotional weight without sacrificing rigor — every first-person claim still carries a citation (NFR-7).

**Negative / accepted tradeoffs:**
- **Tonal-mismatch risk** with a hard-nosed industrial judge. Mitigation: the calm/never-alarmist constraint is enforced in the system prompt, dry-run reviewed, and component `speak()` outputs are template-bounded so they cannot riff freely.
- Persona prompt consumes context budget that could carry more grounding instructions. Mitigation: persona kept under 200 tokens; grounding/refusal templates remain primary.
- Anthropomorphization can leak into status semantics ("I feel sluggish"). We cap component voice to *measurement-grounded* utterances ("my bearing is 41 °C") rather than affective ones.

**Neutral / mitigations:**
- Eval (ADR-018) validates that persona text still passes faithfulness ≥ 0.95 and hallucination = 0. If persona regresses grounding, persona yields.

## References

- PRD §6.4 FR-W.1, §13, §15, §5 US-1, §4 P-1
- HP Briefing (`task/20260423-HP-Briefing.pdf`) — "intelligent, living entity that communicates"
