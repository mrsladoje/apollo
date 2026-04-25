# ADR-002: Six components across three subsystems

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §8, §12, §17; ADR-003, ADR-004, ADR-006

## Context

The HP brief mandates "at least one component per subsystem" across Recoating, Printhead, and Thermal — a minimum of three components total. Apollo's differentiation thesis (§1) hinges on **legible cascades**: a single component per subsystem gives no intra-subsystem coupling and makes the cascade story degenerate to a chain of three nodes, which is not visibly different from a generic dependency graph.

We are optimizing under a 36-hour budget where every additional component costs roughly 30–60 minutes of modeling time plus parameter tuning, plus one row and column in the coupling matrix `M` (ADR-004), plus visual real estate on the dashboard. More components also means more chances for the simulation timing to look implausible and more entries to defend in the technical report.

The decision space is therefore: how many components are enough to support three cascades (ADR-003) with both intra- and cross-subsystem coupling, while staying inside the time budget?

## Decision

We model **exactly 6 components**, **2 per subsystem**:

- **Recoating:** Recoater Blade (exponential + impact Weibull), Drive Motor (Weibull bearing fatigue)
- **Printhead:** Nozzle Plate (Weibull clogging), Thermal Firing Resistors (Coffin-Manson)
- **Thermal:** Heating Element (Coffin-Manson + PINN, see ADR-005), Insulation Panel (exponential `k_eff` decay)

This count is the minimum that supports all three cascades in ADR-003: CSC-A needs two recoating components (blade → motor), CSC-B needs at least one component per subsystem on its path (insulation → heater → resistor + nozzle), CSC-C needs blade and nozzle. Six is also the largest number we can hand-tune in the M1 budget (5 h) and matches the 6×6 coupling matrix size declared in PRD §10.1.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| 3 components (one per subsystem, brief minimum) | No intra-subsystem coupling, CSC-A collapses, dashboard looks empty, "cascade" reduces to a 3-node chain. |
| 4 components (one per subsystem + one extra) | Awkwardly asymmetric across subsystems; either CSC-A or CSC-C cannot be supported without overloading components. |
| 8+ components (add rails, sensors, cleaning interface) | Exceeds M1 budget; coupling matrix grows to 64 entries to defend; visual clutter on dashboard panels; deferred to MVP §3.3 deferred column. |
| 6 components but 3+1+2 split | Drops parity across subsystems; weakens the "all three subsystems matter equally" framing the brief expects. |
| 6 components, all rule-based (no PINN component) | Loses the physics-informed-ML differentiator (ADR-001). |

## Consequences

**Positive:**
- Exceeds the brief's minimum (3) by 2× — visible rigor without scope creep.
- Symmetric 2-2-2 split across subsystems makes the architecture diagram (§13) and dashboard panels (§15) cleanly partitionable.
- 6 components × 6 = 36 coupling slots in `M`, large enough to encode all three cascades, small enough to print on one page in the technical report.
- Each cascade in ADR-003 is supported by at least 2 components, giving the demo three independent failure narratives.

**Negative / accepted tradeoffs:**
- M1 (Phase 1 component models + coupling matrix) absorbs the bulk of the 5-hour budget; any additional component would force cuts to demo polish or M9b–e.
- More components ⇒ more parameter tuning ⇒ higher exposure to Risk R-1 (unrealistic timing). Mitigated by anchoring `α_i` and Weibull shape/scale to literature-cited binder-jetting wear ranges.
- A judge could ask "why not the powder hopper?" — our answer is the hopper does not participate in any of our three cascades; adding it would dilute the story without enabling a fourth narrative arc.

**Neutral / mitigations:**
- The component list is closed for the hackathon. Adding a seventh component is explicitly deferred (§3.3).
- Each component carries `health`, `status`, and component-specific metrics (FR-1.4); the schema scales to 6 cleanly without UI redesign.

## References

- PRD §8 (Component Model), §10.2 (Three parallel cascades), §12 (Strategic Decisions), §17 M1
- HP brief: `task/stage1.md` (≥ 1 component per subsystem requirement)
