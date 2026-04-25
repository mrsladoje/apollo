# ADR-001: Hybrid rule-based + PINN modeling approach

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.1, §12; ADR-002, ADR-005, ADR-006

## Context

The brief requires "at least one mathematical degradation model per subsystem" plus an AI/ML differentiator. The naive options span a spectrum: at one end, hand-tuned rule-based decay for every component (defensible but visually identical to a textbook plot); at the other, a learned model per component (impressive-sounding but opaque, fragile under judge questioning, and impossible to debug in 36 hours).

We are optimizing under three constraints. (1) **Time** — 36 hours, with PINN training, integration, and a UI all on the same M3 Max. (2) **Demoability** — judges from HP must believe the physics, and we cannot defend a black box that disagrees with them on stage. (3) **Determinism** (NFR-1) — bit-identical outputs for identical inputs is a MUST for reproducible obituaries, citations, and counterfactuals.

Pure-ML approaches break (3) outright (training noise, MPS nondeterminism). PINNs everywhere break (1): each PDE needs its own boundary conditions, residual weighting, and stability tuning. Pure rule-based breaks the differentiation thesis in §1 — no concrete AI claim beyond the agent.

## Decision

We model **5 of 6 components with closed-form rule-based decay** (exponential, Weibull, Coffin-Manson — see ADR-006) coupled through a linear matrix `M` (ADR-004), and **1 component — the Heating Element — with a Physics-Informed Neural Network** in DeepXDE enforcing a 1-D heat-diffusion PDE residual in the loss (ADR-005). The PINN is offline-trained, frozen, and called as a deterministic function at inference time (`<5 ms` CPU, NFR-3). All other models are pure NumPy.

The pitch line — *"the heater model can't violate physics, the PDE residual is in its loss function"* — buys the AI-credibility we need without forcing five other components into the same risk profile.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Rule-based for all 6 components, no neural net | No defensible AI/ML differentiator beyond the agent layer; fails the "AI meets reality" framing of the challenge. |
| PINN for every component | Each PDE adds boundary conditions, training instability, and fallback risk. Six PINNs in 36 h is a guaranteed cut. Contradicts time budget §17. |
| Pure-ML (LSTM/Transformer surrogate per component) | Opaque, non-deterministic on MPS, requires training data we don't have, can't be defended against a judge asking "what physics?" |
| Foundation time-series model (Chronos-2, TimesFM 2.5) | Sledgehammer for 6 simulated components; contradicts the PINN narrative; explicitly rejected in PRD Appendix B. |
| Survival models (lifelines / scikit-survival) per component | Needs historical failure data we don't have; duplicates the rule-based decay layer. Rejected in Appendix B. |

## Consequences

**Positive:**
- One concrete, defensible AI/physics claim (the PINN) instead of six fragile ones.
- Rule-based components are deterministic, fast, and unit-testable against known-input/known-output cases (FR-1.5).
- Failure modes are isolated: if the PINN is unstable, R-2 mitigation is to swap in a learned regressor — the other five components are unaffected.
- The hybrid layout naturally maps to the cascade story (ADR-003): rule-based decay + matrix coupling for breadth, PINN depth on the most thermally interesting component.

**Negative / accepted tradeoffs:**
- Five components have no learned component — a judge could ask "why isn't the blade a PINN too?" The honest answer (time + minimal ROI) is in this ADR.
- Hand-tuned rule-based parameters risk producing unrealistic timing (Risk R-1); we mitigate by anchoring to literature-cited Weibull params.
- Inconsistent modeling style across components increases mental load when reading the codebase.

**Neutral / mitigations:**
- All component models share the same `step(state, drivers, dt) -> state` interface (FR-1.8) regardless of internals; the heterogeneity is hidden from the simulation loop.
- PINN fallback (R-2): swap to a small learned regressor surrogate; the physics narrative still holds for the rule-based 5/6.

## References

- PRD §11.1 (Heating-Element PINN), §12 (Strategic Product Decisions), Appendix B (Decision Log)
- DeepXDE: Lu, Meng, Mao, Karniadakis. *DeepXDE: A deep learning library for solving differential equations.* SIAM Review, 2021.
- Raissi, Perdikaris, Karniadakis. *Physics-informed neural networks.* JCP, 2019.
