# ADR-003: Three parallel cascades, not one linear chain

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §10, §12, Appendix B; ADR-002, ADR-004

## Context

The PRD's pain-point §2.2 turns on cascading failures: dashboards alarm on the *terminal* component (the nozzle that clogs), not the *upstream* one (the insulation panel that started it). For the demo to land, the cascade must be *visible* and *traceable* — and the agent (Phase 3) must be able to root-cause it across components.

A single linear cascade chain (insulation → heater → temp → viscosity → nozzle → resistor) is the simplest defensible structure, but it has two demo problems. First, it is monotonic: every component on the chain looks like it is failing for the same reason, which makes the agent's diagnostic chatter repetitive. Second, with only one cascade the live "Ask Apollo" segment (FR-W.5) has only one root-cause story to tell; ten judge questions all collapse to the same answer.

The opposite extreme — no explicit cascades at all, only the matrix `M` (ADR-004) — leaves the cross-component coupling implicit. Judges cannot point at a chart and say "*that* is the cascade." It also weakens the technical report, which needs at least one cascade with explicit physical relationships beyond a coupling weight.

## Decision

We define **three parallel cascades** spanning the 6 components in ADR-002:

| ID | Name | Path | Scope |
| --- | --- | --- | --- |
| **CSC-A** | Recoating loop (intra-subsystem) | Blade wear → bed unevenness → motor torque → bearing fatigue | Within Recoating |
| **CSC-B** | Thermal-Printhead loop (cross-subsystem, demo showpiece) | Insulation → heater duty → enclosure temp → binder viscosity → nozzle clog → resistor stress | Across Thermal + Printhead |
| **CSC-C** | Powder contamination loop | Blade ceramic flaking → powder contamination → nozzle clog | Across Recoating + Printhead |

CSC-A and CSC-C are realized via the matrix coupling alone. **CSC-B is modeled with explicit physical relationships on top of the matrix** — Arrhenius-style binder viscosity vs. temperature, Coffin-Manson thermal fatigue cycles — because this is the cascade the demo narrates in depth and the one the agent traces in the §15 sample interaction.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| One linear cascade chain | Single root-cause story; live Q&A becomes monotonic; weakens the differentiation metric "≥ 3 cascading-failure demonstrations" (§16.2). |
| No explicit cascades, matrix `M` only | Coupling becomes invisible to judges; can't point at a chart and trace causation; weakens the agent's diagnostic narrative. |
| Five or more cascades | Exceeds time budget for explicit physical modeling on each; CSC-B alone needs Arrhenius + Coffin-Manson tuning and consumes most of the cascade budget. |
| Three cascades but all intra-subsystem | Loses the cross-subsystem showpiece; brief's framing emphasizes that subsystems interact; CSC-B is the strongest "AI meets reality" moment. |
| Three cascades, all explicit ODEs | Explicit ODE modeling for three cascades blows the M1 budget; CSC-A and CSC-C are well-served by matrix coupling because their physics is dominated by linear contributions. |

## Consequences

**Positive:**
- Three independent failure narratives unlock multi-question live Q&A (FR-W.5) without repetition.
- CSC-B demonstrates cross-subsystem coupling — the cascade the brief is most likely to find compelling — with explicit physics that survive judge scrutiny.
- CSC-A and CSC-C are cheap (matrix-only) but still provide demo material for two more obituaries (FR-W.4) and two more counterfactuals (FR-3.6).
- Every cascade traces to ≥ 2 components from ADR-002, exercising the coupling matrix.

**Negative / accepted tradeoffs:**
- Three cascades means the storyboard must clearly delineate which is which during the demo, or judges conflate them. We mitigate with color-coded paths in the architecture diagram (§13) and per-cascade obituaries.
- Only CSC-B has explicit ODE-backed physics; CSC-A and CSC-C are "just matrix coupling," and a determined judge could call them less rigorous. The technical report flags this honestly: matrix coupling is sufficient where physics is dominated by linear effects.
- Tuning three cascades to all resolve over the same ~10-hour print cycle requires careful `α_i` and `M_ij` selection (Risk R-1).

**Neutral / mitigations:**
- Cascade definitions are closed for the hackathon. A "fourth cascade" idea is deferred to §3.3.
- The cascade IDs (CSC-A/B/C) are first-class citizens in the obituaries table and the agent's tool outputs, which makes them queryable evidence rather than slide annotations.

## References

- PRD §10 (Coupling & Cascade Specification), §10.2 (Three parallel cascades), §12, Appendix B (rough-idea reversal: linear chain → three parallel)
- §16.2 differentiation metric: "Cascading-failure demonstrations ≥ 3"
- HP brief: `task/stage1.md` cross-subsystem framing
- **CSC-B explicit physics — Arrhenius binder viscosity** (`Ea/R = 4500 K` in `src/engine/cascades/csc_b.py`):
  - Han, C., et al. (2020). *Recent Progress on Polymer Materials for Additive Manufacturing.* Advanced Functional Materials 30, DOI:10.1002/adfm.202003062 — survey of AM-binder polymers (PEG, PVP, PVA) and their viscosity-temperature behavior.
  - Du, W., et al. (2019). *Jetting Performance of Polyethylene Glycol and Reactive Dye Solutions* — PEG viscosity rheology under jetting conditions, ResearchGate publ. 332635932.
  - Thermal/rheological data on PEG-400 and PEG-1500 establishing Arrhenius activation energy in our chosen range; see ResearchGate publ. 316713550.
- **CSC-B explicit physics — Coffin-Manson thermal fatigue** (cycle counting on resistors and heater): foundational Coffin (1954) Trans. ASME 76, 931–950 and Manson (1954) NACA TN-2933; see ADR-006 §"Parameter ranges and citations" for the consolidated parameter table.
- **CSC-A / CSC-C matrix-only justification** (linear coupling sufficient where physics is dominated by linear effects): see ADR-004 references; mathematical anchor in PRD §10.1.
