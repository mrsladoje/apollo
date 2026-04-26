# ADR-011: Genetic Algorithm (DEAP) for maintenance scheduling

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.3, §17 M4, §19 R-4, FR-2.4, FR-W.2; ADR-013 (three-scenario benchmark)

## Context

The "AI" maintenance policy in the three-policy benchmark (NONE / FIXED / AI) needs to *visibly* outperform the fixed schedule by ≥ +25%, target +34% uptime (success metric §16.2). The policy itself is small: pick a per-component health threshold below which we trigger maintenance, plus a global preventive-lookahead coefficient — seven scalars total. The hard part is not the policy *space*, it's giving the demo a moment where the optimization is *visible* — judges see the algorithm getting better.

The hackathon constraint forces ruthless tool selection. We have ~4 hours for M4 (the maintenance agent milestone). The optimizer must (a) run start-to-finish in that window, (b) produce a fitness curve we can render with Recharts, and (c) be explainable in one sentence to a CFO.

Reinforcement learning (PPO, DQN, contextual bandits) was the obvious first thought because the brief mentions autonomous maintenance. But RL needs an environment, training loop, reward shaping, and — critically — sim-to-real generalization that is *publicly unsolved* even in well-funded industrial settings. Inside 4 hours, an RL agent will either fail to converge or convince us it converged when it didn't. Neither is acceptable on a demo stage.

## Decision

Use a **Genetic Algorithm via DEAP**. Encoding: 7-dimensional vector — 6 per-component health thresholds in `[0, 1]` + one global preventive-lookahead coefficient. Selection: tournament (k=3). Crossover: blend-α with α=0.5. Mutation: Gaussian per-gene with σ=0.05, p=0.2. The production configuration is intentionally small and fast: default population 32, default generations 20, four islands, migration every four generations, elitism, early stopping after five stale generations, and random immigrants when diversity collapses. Fitness:

```
fitness = uptime_hours − λ_cost · maintenance_count − λ_failure · catastrophic_failures
```

Each fitness evaluation is one full production-resolution, one-minute-timestep simulation run on the Stressed scenario (most informative landscape). The evaluator runs in memory and deliberately skips SQLite historian writes, forecast persistence, checkpoints, and obituaries; the final demo historian is still generated later from the winning `config/policies.yaml`. Best-of-population fitness is logged per generation and rendered as a live curve in the demo. The final winner becomes the deployed AI policy thresholds in `config/policies.yaml`. The runtime maintenance trigger is wrapped by an LLM explainer that turns "Blade health crossed 0.43 threshold" into a one-paragraph reason citing the active cascade.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **PPO / Q-Learning RL agent** | Needs a stable simulator API + days of training; sim-to-real generalization is openly unsolved in industrial maintenance literature. High risk of either non-convergence or false convergence inside 4 h. PRD §3.4 explicitly excludes RL. |
| **Model Predictive Control (MPC)** | Rolling-horizon optimizer is principled and would work, but building a tractable cost-to-go model + the rolling solver is 8 h+ of engineering. Doesn't give a visible "evolution" moment for the demo. |
| **Bayesian Optimization (Optuna / scikit-optimize)** | Genuinely strong for 7-dim hyperparameter search and would probably converge faster than GA. Rejected because the curve it produces — TPE expected-improvement points — is *boring* visually. GA's monotonic best-of-pop curve is the demo win (R-4). |
| **Contextual bandit per component** | Decouples components — but our cascades mean per-component decisions are coupled. A bandit that doesn't see Cascade B will under-trigger insulation maintenance. Wrong primitive. |
| **Hand-tuned thresholds** | Honest baseline, but provides no "Apollo learned this" narrative. The demo loses the optimization moment entirely. We keep hand-tuned thresholds as the *initialization* of the GA population. |
| **CMA-ES** | Slightly stronger than vanilla GA in 7-dim continuous space. Rejected because DEAP's GA is already in the team's muscle memory and CMA-ES gives an uglier evolution curve (covariance updates, not best-of-pop monotone). |

## Consequences

**Positive:**
- DEAP is mature, CPU-only, and deterministic for a fixed seed. Fitness evaluations run in parallel worker processes; the side-effect-free in-memory path keeps GA training in the minute-scale instead of writing thousands of temporary SQLite rows.
- The fitness curve is a *demo asset*: a monotonically improving line behind Apollo's voiceover "and here you can see Apollo learning the right maintenance thresholds" lands cleanly.
- Tunable: λ_cost and λ_failure encode the operator's tradeoff between intervention frequency and failure cost — auditable, not magical.
- LLM explainer wraps the *output* not the *optimizer*, so the GA stays deterministic-given-seed (NFR-1) while the human-facing reason is generative.
- Island populations, elite preservation, migration, and random immigrants reduce local-optimum and population-collapse risk while keeping the visual GA story intact.

**Negative / accepted tradeoffs:**
- GA is sample-inefficient vs. Bayesian opt. We accept that because the search space is only seven scalars, the evaluator is now in memory, and the GA curve is a visible demo moment. Optuna remains a comparator/fallback, not the primary algorithm.
- Threshold-policy is a *static* policy. It cannot learn online. Acceptable — the brief is about decision intelligence at the printer, not lifelong learning. RL is explicitly out of scope (PRD §3.4).
- Threshold-only policies appear to plateau at seven maintenance actions with zero failures on the corrected one-minute Stressed scenario. Further score improvement likely requires a richer policy representation (for example hysteresis or delay-tolerance genes), not more blind threshold search.

**Neutral / mitigations:**
- If the fitness landscape is ugly (R-4), first use the GA's built-in mitigations: seeded islands, migration, early stopping, and random immigrants. Optuna TPE remains built and benchmarked as a dormant fallback; threshold semantics survive the swap.
- The optimizer runs offline, *before* the demo. Live mode replays the cached fitness history.

## References

- PRD §11.3, §17 (M4), §16.2, §19 (R-4); FR-2.4, FR-W.2
- DEAP documentation: <https://deap.readthedocs.io>
- PRD Appendix B: "Full RL maintenance agent → replaced with GA"
