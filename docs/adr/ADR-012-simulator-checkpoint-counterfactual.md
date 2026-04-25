# ADR-012: Simulator-checkpoint branching for counterfactual reasoning

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.4, §17 M5, FR-3.6 (`run_counterfactual` tool), US-4; ADR-009 (Pattern C)

## Context

User story US-4 is the "moment of regret" demo: a maintenance engineer points at a failure and asks *"what if we'd swapped the blade at 04:00 instead?"* Apollo must replay the simulation with the alternate decision and show the uptime delta. This is FR-3.6's `run_counterfactual` tool.

There is a deep but mostly irrelevant academic literature on causal inference (DoWhy, EconML, CausalPy, Pearl-style structural causal models). That body of work answers a different question: *given observational data with confounders, estimate the counterfactual.* It exists because in the real world we cannot rerun an experiment.

In Apollo, **we can rerun the experiment**. The simulator is fully under our control. We have all the state. We have the RNG seed. We can deepcopy the simulator at any timestep, branch with an alternate maintenance action, and run the branch forward to compare against the original timeline. There is no confounding, no missing data, no inference problem — only an engineering one.

This means picking a causal-inference library would be the *wrong* move. It would solve an observational problem we don't have, while hiding the much cleaner narrative: "We own the simulator, so the counterfactual is exact, not estimated."

## Decision

Implement counterfactuals as **simulator checkpoint + branch + diff**, with no causal-inference library. Concretely:

1. The simulator state at every persisted timestep is a Pydantic model serializable via `pickle` / `model_copy(deep=True)`. The historian retains enough state (component health vectors, RNG state, scheduled-maintenance state) to fully reconstruct a step.
2. `run_counterfactual(run_id, branch_t, alternate_action)` loads the original run's state at `branch_t`, deepcopies it, applies `alternate_action` (e.g. `swap_blade`), and re-runs the simulator to the original `t_end` with the same scenario driver trajectory and the same downstream RNG seed.
3. Returns `{ original: timeline_a, alternate: timeline_b, diff: { uptime_delta, failures_avoided, cost_delta } }`.
4. The UI overlays both timelines on the same chart; the alternate is highlighted where it outperforms.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **DoWhy** | Excellent for observational causal inference. Wrong tool: we have an executable simulator, not observed-only data. Adds a DAG-specification step that has no value here. |
| **EconML** | Treatment-effect estimation under confounding. Same category mismatch; we have no confounders to adjust for. |
| **CausalPy (PyMC-based)** | Bayesian causal inference. Powerful, but again addresses a problem we don't have, and adds PyMC as a heavy dependency. |
| **Hand-built Structural Causal Model** | We could write Pearl-style SCM equations matching the coupling matrix and PINN. Real engineering cost (8 h+) for an answer that's strictly weaker than re-executing the simulator we already wrote. |
| **Difference-in-differences statistics** | Used for policy evaluation across runs. Not for "what would have happened in *this* run." Wrong unit of analysis. |
| **Monte Carlo over alternate seeds** | Could give a distribution, but conflates "stochastic noise across seeds" with "the effect of the intervention." We want the latter, holding the seed fixed. |

## Consequences

**Positive:**
- The counterfactual is *exact*, not estimated. Same RNG seed → same driver trajectory → the only difference is the alternate decision. This is statistically the cleanest possible counterfactual.
- Demo narrative is sharp: "We don't infer the alternate universe — we run it." This is actually a stronger pitch line than any causal-DAG framing.
- Implementation is small: deepcopy + simulator step loop + diff. Estimated ~3 h for M5, matching PRD §17.
- No new heavy dependencies. PyMC / DoWhy / EconML each pulls 100+ MB of transitive deps we'd otherwise avoid.

**Negative / accepted tradeoffs:**
- Counterfactual cost = full re-simulation from `branch_t` to `t_end`. For a 10-hour simulated run branched at hour 4, that's 6 h × 60 min = 360 simulator steps. Around 1-3 s wall-clock — fits inside `run_counterfactual`'s budget but is the slowest single tool call.
- We must guarantee the simulator is *fully deterministic given (state, RNG, drivers)* (NFR-1). Any nondeterminism (e.g. dict iteration in older Python, MPS nondeterminism in PINN) breaks the counterfactual cleanness. Mitigated: PINN inference is deterministic on CPU; we pin Python ≥ 3.7 dict ordering; explicit RNG state in checkpoint.
- Cannot answer counterfactuals about the *driver trajectory* itself (e.g. "what if the weather had been different") without re-rolling drivers. Out of scope; the brief asks about *intervention* counterfactuals.

**Neutral / mitigations:**
- The technical report cites a 2026 digital-twin counterfactual reference (e.g. arXiv 2604.01325 — *Digital Twin Counterfactual Framework*) to ground the methodology. We are explicit in the report that we are doing exact re-execution, not statistical inference, and we do not make uncited causal claims in the demo.
- If we ever extend to fleet data without our own simulator, the architectural seam (`run_counterfactual` tool interface) is unchanged; only the implementation under the hood would swap to a causal estimator.

## References

- PRD §11.4, §17 (M5), FR-3.6, US-4
- arXiv 2604.01325 — *Digital Twin Counterfactual Framework* (2026, cited in report)
- PRD Appendix B: "Causal DAG library (DoWhy) → replaced with simulator-checkpoint branching"
