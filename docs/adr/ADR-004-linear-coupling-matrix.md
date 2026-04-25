# ADR-004: Linear coupling matrix `M` for component interactions

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §10.1, §12; ADR-002, ADR-003

## Context

With 6 components (ADR-002) and 3 cascades (ADR-003), every component's health depends on *its own* drivers and on the degradation state of upstream components. The PRD requires (FR-1.6) cross-component coupling implemented in a way that is documented, deterministic, and demoable. The question is **what mathematical structure** encodes that coupling.

We need a structure that satisfies four constraints. (1) **Auditability** — the technical report must show the coefficients on one page; (2) **Determinism** (NFR-1) — same `(state, drivers, dt)` ⇒ same output; (3) **Cheap inference** — Phase 1 must run < 50 ms per step (NFR-2) for all 6 components combined; (4) **Tunable in hours, not days** — Risk R-1 mitigation depends on the team being able to iteratively adjust coefficients while watching the cascade resolve over a 10-hour sim.

Bayesian-network and full-ODE-system approaches each fail at least one constraint. Doing nothing (no coupling) makes ADR-003 impossible.

## Decision

We use a single **6×6 NumPy matrix `M`** with the update rule:

```
dH_i/dt = -α_i · f(drivers_i)  -  Σ_j  M_ij · (1 - H_j)
```

where `H_i ∈ [0,1]` is component i's health, `α_i` is its intrinsic decay coefficient, `f(drivers_i)` is its rule-based decay term (exponential / Weibull / Coffin-Manson — ADR-006) or PINN call (heater only — ADR-005), and `M_ij` is the coupling weight from component j to component i. The `(1 - H_j)` factor means a healthy upstream contributes nothing; a fully-degraded upstream contributes `M_ij` to the downstream's decay rate.

The initial matrix (PRD §10.1) is sparse: 6 non-zero off-diagonals encoding only the cascade paths in ADR-003. CSC-B additionally carries explicit physics on top of the matrix (Arrhenius viscosity, Coffin-Manson fatigue cycles); CSC-A and CSC-C are matrix-only.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Bayesian network (pgmpy / pomegranate) | Probabilistic semantics conflict with deterministic NFR-1; needs CPT specification per node, far more parameters than 6 coupling weights; harder to defend on a slide. |
| Full ODE system with explicit cross-terms for every pair | Explosion of parameters (up to 30 cross-terms); needs scipy ODE solver instead of plain Euler; dwarfs the M1 budget; most cross-terms are zero for our cascades anyway. |
| No coupling, components evolve independently | Makes ADR-003 impossible; cascades become annotation rather than mechanism; defeats the differentiation thesis. |
| Causal DAG library (DoWhy) | Statistical-causality framework, overkill when we own the simulator; rejected in PRD Appendix B. |
| Graph neural network learning coupling end-to-end | Black-box, non-deterministic, no training data; defeats every reason we chose rule-based decay (ADR-001). |
| Per-cascade hand-coded rules (no shared structure) | Three independent code paths to test; no single page in the report; harder to extend if we add a 7th component post-hackathon. |

## Consequences

**Positive:**
- Coupling is **one matrix, one formula, one slide** — the technical report shows `M` directly and judges can read off who-affects-whom in 5 seconds.
- Linear superposition of decay terms is trivially deterministic and < 1 ms per step (well inside NFR-2).
- Tuning is fast: changing one coefficient changes one cascade, decoupled from the others.
- The matrix is also the object the agent's `compare_runs` and `run_counterfactual` tools reason about — coupling becomes inspectable telemetry, not implicit code.

**Negative / accepted tradeoffs:**
- **Linear coupling ignores nonlinearities.** Real binder viscosity vs. temperature is Arrhenius (exponential), not linear. We accept this limitation everywhere except CSC-B, where we add explicit physics on top of the matrix. The technical report must call out the linear approximation honestly.
- The matrix has no notion of saturation or feedback loops — `(1 - H_j)` is bounded but doesn't model "blade wear plateaus once it's flaking."
- All coupling acts on the *decay rate*, not on driver values directly. A judge could legitimately ask "why doesn't degraded insulation raise the temperature *driver* the heater sees, instead of just the heater's decay rate?" The honest answer: it would, in a fuller physical model; we encode the effect downstream rather than upstream because it preserves the `step()` contract (FR-1.8).
- Coefficient tuning is hand-anchored to literature, not learned (Risk R-1).

**Neutral / mitigations:**
- The matrix is documented in §10.1 and surfaced in the dashboard architecture panel, so the linearization assumption is visible, not hidden.
- CSC-B's explicit ODE layer is the answer to "linear isn't enough for the showpiece cascade." That cascade gets the realism budget.
- Future work (post-hackathon) could replace `M` with a sparse Jacobian inferred from data without changing the `step()` interface.

## References

- PRD §10.1 (Default coupling — linear matrix), §12 (Coupling formalism row), Appendix B (DAG library rejection)
- HP brief: `task/stage1.md` (cross-component cascading failure requirement)
