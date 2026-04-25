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

Use a **Genetic Algorithm via DEAP**. Encoding: 7-dimensional vector — 6 per-component health thresholds in `[0, 1]` + one global preventive-lookahead coefficient. Population: 50 individuals. Generations: 50. Selection: tournament (k=3). Crossover: blend-α with α=0.5. Mutation: Gaussian per-gene with σ=0.05, p=0.2. Fitness:

```
fitness = uptime_hours − λ_cost · maintenance_count − λ_failure · catastrophic_failures
```

Each fitness evaluation is one full simulation run on the Stressed scenario (most informative landscape). Best-of-population fitness is logged per generation and rendered as a live curve in the demo. The final-generation winner becomes the deployed AI policy thresholds in `config/policies.yaml`. The runtime maintenance trigger is wrapped by an LLM explainer that turns "Blade health crossed 0.43 threshold" into a one-paragraph reason citing the active cascade.

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
- DEAP is mature, single-process, no GPU. Each generation is ~50 simulation runs in parallel processes; full GA finishes in tens of minutes on M3 Max.
- The fitness curve is a *demo asset*: a monotonically improving line behind Apollo's voiceover "and here you can see Apollo learning the right maintenance thresholds" lands cleanly.
- Tunable: λ_cost and λ_failure encode the operator's tradeoff between intervention frequency and failure cost — auditable, not magical.
- LLM explainer wraps the *output* not the *optimizer*, so the GA stays deterministic-given-seed (NFR-1) while the human-facing reason is generative.

**Negative / accepted tradeoffs:**
- GA is sample-inefficient vs. Bayesian opt. We don't care: 2,500 fitness evals × ~10 s sim each is ~7 hours wall-clock — but parallelizes over CPU cores to ~30-45 minutes.
- Threshold-policy is a *static* policy. It cannot learn online. Acceptable — the brief is about decision intelligence at the printer, not lifelong learning. RL is explicitly out of scope (PRD §3.4).
- Local optima risk. Mitigated by population diversity + α-blend crossover + restart from best-known hand-tuned seed.

**Neutral / mitigations:**
- If the fitness landscape is ugly (R-4) and produces a boring jagged curve, the contingency is to swap to Optuna and accept the visual hit. Threshold semantics survive the swap.
- The optimizer runs offline, *before* the demo. Live mode replays the cached fitness history.

## References

- PRD §11.3, §17 (M4), §16.2, §19 (R-4); FR-2.4, FR-W.2
- DEAP documentation: <https://deap.readthedocs.io>
- PRD Appendix B: "Full RL maintenance agent → replaced with GA"
