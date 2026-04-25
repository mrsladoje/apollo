# ADR-013: Three-scenario benchmark + "Dark Twin" framing

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §9.3 (Scenario presets), §15 (UX), §16.2, FR-2.4, FR-W.2; ADR-011 (GA), ADR-012 (counterfactual)

## Context

The brief asks for at least one cascading-failure simulation; the success-metric §16.2 requires demonstrating an uptime delta of ≥ 25% (target +34%) for the AI policy over a fixed schedule. A single benchmark run technically satisfies both. But a single number on a slide is forgettable, and a single scenario is fragile — judges who notice the AI policy "wins by chance on a friendly scenario" will discount the result.

We need a benchmark structure that (a) shows the AI policy wins *across* environments, not just one, (b) makes the cost of *no* maintenance viscerally visible, and (c) gives the demo a narrative spine that a CFO and an engineer can both follow. The three driver presets (Barcelona-humid, Phoenix-dry, Stressed) are already specified in PRD §9.3 to cover the three failure modes we model — humidity-driven nozzle clog, thermal cycling on heater, and high-duty cumulative wear.

The deeper insight: a benchmark is a *table of numbers*, but a demo is a *story*. If we show three "no maintenance" runs as just a baseline column, judges will glaze. If we frame those runs as **the alternate universe where Apollo wasn't watching** — the Dark Twin — we have converted a benchmarking exercise into a narrative weapon.

## Decision

Run the benchmark as a **3 × 3 grid: three scenarios × three policies**.

- **Scenarios:** Barcelona-humid, Phoenix-dry, Stressed (PRD §9.3).
- **Policies:** NONE (no maintenance), FIXED (calendar-based), AI (GA-tuned thresholds, ADR-011).

All nine `(scenario, policy, seed)` triples are pre-run before the demo and persisted in the historian (FR-2.4) with stable run IDs. The dashboard's three live panels render scenarios A/B/C side-by-side, each showing the three policies as overlaid health-curve traces with explicit failure markers.

The **NONE column is renamed "Dark Twin"** in all UI copy and obituary text — "the alternate universe where Apollo wasn't watching." Apollo's first-person narration during the demo references the Dark Twin's failures as events that "would have happened" in the world without the co-pilot. Component obituaries (FR-W.4) generated for Dark Twin failures are surfaced in the timeline; the matching AI run shows the same component still alive at the same timestamp — the implicit citation of the value Apollo created.

Final demo headline: a single euro-denominated savings number derived from `(uptime_AI − uptime_FIXED) × cost/hour`, with sources in slide speaker notes (FR-W.3).

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **One scenario, three policies** | Cleaner but fragile — a critic asks "does it work in dry weather too?" and we have no answer. |
| **Three scenarios, two policies (FIXED vs AI only)** | Loses the most powerful demo asset: the no-maintenance disaster. Without Dark Twin, the AI win shrinks from "prevented catastrophic failure" to "saved a few hours." The contrast collapses. |
| **Five+ scenarios (full ablation grid)** | Diminishing returns. Three is the sweet spot for "robust across conditions" without spending hours on plot real estate. PRD §15 only fits three side-by-side panels comfortably. |
| **Plain "no maintenance" naming** | Technically accurate, narratively flat. "Dark Twin" earns the demo a memorable phrase that judges will repeat to each other afterward. Costs: zero (it's a copy change). |
| **Stochastic average across many seeds** | Right for a research paper, wrong for a 5-minute demo. Single seeded runs render cleanly on a chart; error bars over 50 seeds clutter the canvas without changing the story. |
| **Live benchmarking on stage** | Too slow (R-5). All nine runs are pre-computed; live mode replays the cached historian rows. |

## Consequences

**Positive:**
- 3 × 3 grid is *the* differentiation argument. "We beat fixed schedule by +34% on average across three environments" is a stronger claim than "we beat fixed schedule once."
- Dark Twin framing converts the NONE baseline from a boring column into an *emotional anchor*. The component obituary written for a Dark Twin failure is the demo's most quotable moment.
- Naturally supports counterfactual integration (ADR-012): "what if Apollo had been watching the Barcelona run?" maps directly onto the Dark Twin run.
- All nine runs share the same historian schema (PRD §14), so `compare_runs` (FR-3.6) works out of the box across any two runs.

**Negative / accepted tradeoffs:**
- "Dark Twin" is marketing language. We accept this only inside UI copy and demo narration; in the technical report and ADRs, it stays "the NONE-policy baseline." Mixing the two registers would erode credibility.
- Running nine simulations × pre-computing GA thresholds × indexing into PyLate is non-trivial fixture-build work. Adds ~30 min to every "rebuild from clean" cycle.
- The +34% target uptime delta is an aspiration, not a guarantee — depends on coupling-matrix tuning (R-1). Mitigation: the slide cites the *actual measured delta*, with the +34% framing kept only if the data supports it.

**Neutral / mitigations:**
- If a scenario produces a degenerate result (AI policy worse than FIXED), we keep it visible in the dashboard rather than hiding it — judges who spot honest negative results tend to *trust* the rest more, not less.
- The euro savings number (FR-W.3) is explicitly labeled "modeled savings" in speaker notes; we do not claim proprietary HP cost data (NFR-10).

## References

- PRD §9.3, §15, §16.2, FR-2.4, FR-W.2, FR-W.3, FR-W.4, NFR-10
- Apollo persona spec (FR-W.1) for Dark Twin narration tone
- PRD Appendix B: 3 scenarios + 3 policies decision
