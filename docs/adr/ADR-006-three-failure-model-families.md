# ADR-006: Three failure-model families (exponential, Weibull, Coffin-Manson)

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §8, FR-1.3, §12; ADR-001, ADR-002

## Context

The HP brief requires *at least two* standard mathematical failure models in Phase 1. The minimal-compliance reading is "two Weibulls applied to two components." This is technically valid and absolutely boring — it tells judges nothing about whether we understand the physics behind binder-jetting failure modes.

Each component in ADR-002 has a *real* dominant degradation mechanism, and the textbook failure model that fits each mechanism is different. Forcing a single model family across all six components either (a) drops physical realism (Weibull doesn't naturally express ceramic wear height loss) or (b) buries the physical distinctions we want the technical report to highlight.

We are also constrained by Risk R-1: hand-tuned timing must produce believable cascades over the 10-hour print cycle. The cleaner the mapping from "physical mechanism" to "math model," the easier it is to anchor coefficients to published binder-jetting / additive-manufacturing literature instead of inventing them.

## Decision

We ship **three failure-model families**, each mapped to the components whose physics it actually fits:

| Family | Math | Components | Physical mechanism |
| --- | --- | --- | --- |
| **Exponential decay** | `H(t) = H₀ · exp(-α · stress(t))` | Recoater Blade (height loss), Insulation Panel (`k_eff` loss) | Smooth monotonic loss of a physical property under continuous stress; no characteristic life threshold. |
| **Weibull** | `F(t) = 1 - exp(-(t/η)^β)` (β > 1 ⇒ wear-out) | Drive Motor (bearing fatigue), Nozzle Plate (clogging probability), Recoater Blade (impact-event Weibull) | Time-to-failure of components with a characteristic life η and increasing hazard rate; standard for bearings and stochastic clog events. |
| **Coffin-Manson** | `N_f = C · (Δε_p)^(-c)` (thermal-fatigue cycles to failure) | Thermal Firing Resistors, Heating Element (combined with PINN — ADR-005) | Low-cycle thermal fatigue from repeated heating/cooling; standard for thermal-inkjet resistors and metal heating elements. |

Brief minimum is 2; we ship 3 because each family fits a real physical mechanism and the additional cost is one extra unit-tested model class.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Single Weibull for everything | Physically wrong for blade height loss and insulation `k_eff` (no characteristic life threshold there); makes the component table in §8 read like a homework exercise; misses the chance to cite three separate AM-literature anchors. |
| Single exponential for everything | Cannot express thermal-cycle-driven failure (Coffin-Manson is the textbook AM model for thermal resistors); makes Weibull's stochastic shape parameter unavailable for impact and clog modeling. |
| Learned per-component model (one regressor per component) | No training data; opaque; defeats ADR-001's hybrid approach; would need separate justification per component. |
| Add a 4th family (e.g. Paris-Erdogan crack growth) | Marginal demo value; needs another set of literature-anchored coefficients; M1 budget already tight. |
| Stochastic shock models on top of all three families | Deferred (§3.3); seeded scenario noise (Phoenix-stable vs. Stressed) gives the variance we need without adding a fourth model class. |
| Lifelines / scikit-survival models (Cox, Kaplan-Meier) | Survival analysis needs historical failure data we don't have; rejected in Appendix B; duplicates the rule-based decay layer. |

## Consequences

**Positive:**
- **Each component's failure model maps to a real physical mechanism**, which is exactly the kind of rigor the HP brief rewards.
- **Three model classes mean three separate unit tests** (FR-1.3 acceptance criterion: "each model unit-tested with known-input known-output cases") with non-overlapping reference solutions.
- Coefficients can be **anchored to published binder-jetting / AM literature** for each family separately, mitigating Risk R-1.
- Coffin-Manson, in particular, gives us the right vocabulary for the heater PINN's drift metric (ADR-005) and the resistor's thermal-cycle counter — both surface in CSC-B (ADR-003).

**Negative / accepted tradeoffs:**
- **Three model families ⇒ three sets of parameters to tune.** More tuning surface = more places Risk R-1 can bite. We mitigate by ranges from literature, not point estimates.
- **Coffin-Manson is the most parameter-sensitive of the three** (the exponent `c` is empirically derived and printer-specific). We do not claim our value matches an HP S100 — we cite a thermal-inkjet range and disclose the assumption.
- A judge could ask "why not Arrhenius for everything thermal?" — Arrhenius governs *rate constants*, not lifetimes; we use Arrhenius implicitly inside CSC-B's binder-viscosity term but not as a top-level failure family.
- More math classes ⇒ slightly more cognitive load reading the codebase; we mitigate by giving each family its own module under `engine/failure_models/` and the same `decay(state, drivers, dt) -> dH` signature.

**Neutral / mitigations:**
- All three families are pure NumPy, deterministic, and trivially fast (well inside NFR-2).
- The mapping in the table above is the canonical answer to "which model for which component" — printed in the technical report so it cannot be questioned mid-demo.
- Adding stochastic shock models is explicitly deferred to §3.3, not denied.

## References

- PRD §8 (Component Model — failure-model column), FR-1.3, §12, Appendix B
- HP brief: `task/stage1.md` ("at least two standard mathematical failure models")
- Coffin-Manson reference: ASTM E2714 / IPC-9701 thermal-cycle test methodology
- Weibull: Weibull (1951), *A statistical distribution function of wide applicability.*
