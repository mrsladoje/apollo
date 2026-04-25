# ADR-005: DeepXDE for the heating-element PINN

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.1, §18, NFR-3, FR-1.7; ADR-001

## Context

ADR-001 commits us to exactly one PINN as the AI/physics differentiator. Three sub-decisions follow: **which component**, **which library**, and **which hardware backend**.

Component choice: of the 6 components in ADR-002, we need one with (a) a well-known governing PDE, (b) thermal/temporal dynamics rich enough to make the PINN earn its place, (c) a clear failure mechanism the rule-based components don't already cover, and (d) a tractable 1-D reduction so training fits in minutes on a laptop.

Library choice: PINN tooling in 2026 is mature but uneven. Hand-rolled PyTorch costs 4–6 hours of boilerplate (PDE residual computation, BC enforcement, training loop). NVIDIA Modulus is overkill — designed for industrial CFD, multi-GPU, weeks of setup. PINA is younger and has fewer worked examples for heat diffusion. DeepXDE is the de-facto reference implementation, has an MPS-compatible PyTorch backend, and ships heat-diffusion examples directly applicable to our PDE.

Hardware: M3 Max has MPS and a 40-core GPU. Custom Metal/CoreML kernels are explicitly out of scope (§3.4, §21).

## Decision

- **Component:** the **Heating Element**, with a **1-D heat-diffusion PDE** (`∂T/∂t = κ ∂²T/∂x²` with insulation- and ambient-driven boundary conditions).
- **Library:** **DeepXDE** with **PyTorch backend on MPS** for training, then frozen-model inference on CPU at runtime.
- **Architecture:** 4 hidden layers × 64 units (~10–50 k params).
- **Loss:** data loss + PDE residual + boundary/initial-condition loss.
- **Training:** offline on synthetic data generated from the same physics (drift induced by HVAC short-cycling, ambient temp, duty hours). Minutes, not hours.
- **Inference:** < 5 ms CPU per call (NFR-3); deterministic frozen weights checked into the repo.

The pitch line — *"the heater can't violate physics, the PDE residual is in its loss"* — is the entire reason this ADR exists.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| NVIDIA Modulus | Aimed at industrial multi-GPU CFD; setup cost in days; overkill for a 1-D PDE; CUDA-first, MPS support is afterthought. |
| PINA (Lightning-based PINN library) | Younger ecosystem, fewer worked heat-diffusion examples, smaller community for last-minute debugging. |
| Hand-rolled PyTorch + autograd PDE residuals | 4–6 h of boilerplate; reinvents what DeepXDE provides; high bug surface for last-minute training instability. |
| PINN on the **nozzle plate** (clogging dynamics) | Clogging physics has no clean closed-form PDE at this scale; would need empirical surrogate; defeats the "PDE residual in the loss" pitch. |
| PINN on the **blade** | Wear is dominantly impact + abrasion, modeled cleanly by exponential + Weibull (ADR-006); a PINN here would be a surrogate without PDE content. |
| PINN on the **insulation panel** (1-D heat conduction through the panel) | Plausible alternative — same PDE family. Rejected because the heater is the *driver* of CSC-B and gives the cascade a more dramatic on-stage failure; insulation degradation is better captured by exponential `k_eff` decay. |
| Custom Metal / CoreML kernels for inference | Explicitly out of scope (§21); MPS is sufficient for training and CPU is sufficient for < 5 ms inference. |
| 2-D or 3-D PDE | Training time blows up; unnecessary fidelity for a 1-D-effective component (heater is approximately a thin element with dominant axial gradient). |

## Consequences

**Positive:**
- DeepXDE's heat-diffusion examples cut implementation time to hours instead of days; the M2 budget (5 h) is realistic.
- The 1-D PDE is small enough to train in minutes on M3 Max MPS, leaving room to retrain if drivers change.
- Frozen-weights inference is deterministic on CPU, satisfying NFR-1.
- The PINN's output (`predicted_temp_field`, `drift_pct`) plugs cleanly into CSC-B's cascade story: a degraded heater drives binder viscosity in the printhead.

**Negative / accepted tradeoffs:**
- **DeepXDE adds a dependency** with a moderate API surface; if the library has a bug we hit at hour 30, fallback (Risk R-2) is to swap in a small learned regressor — at the cost of dropping the "PDE residual in the loss" pitch line.
- **MPS PyTorch is not bit-deterministic across runs** (op-order nondeterminism). We mitigate by training offline once, freezing weights, and running inference on CPU only — so NFR-1 holds for the *runtime* simulator even if training is not bit-reproducible.
- **1-D reduction is a physical approximation.** Real heater elements are 3-D; we are betting that axial gradient dominates radial for our drift metric. Honest disclosure in the technical report.
- Training data is synthetic, generated from the same physics — the PINN cannot discover anything its generator didn't know. We document this as a "consistency check" rather than a generalization claim.

**Neutral / mitigations:**
- The PINN is the only learned component (ADR-001), so its failure does not cascade across the simulator — fallback contains the blast radius.
- Inference latency is measured and asserted in CI as part of NFR-3 verification.

## References

- PRD §11.1 (Heating-Element PINN), §18.2 (Libraries), NFR-3 (PINN inference < 5 ms CPU), FR-1.7
- **PINN foundational paper:** Raissi, M., Perdikaris, P., Karniadakis, G. E. (2019). *Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations.* Journal of Computational Physics 378, 686–707. DOI:10.1016/j.jcp.2018.10.045.
- **DeepXDE library:** Lu, L., Meng, X., Mao, Z., Karniadakis, G. E. (2021). *DeepXDE: A deep learning library for solving differential equations.* SIAM Review 63(1), 208–228. DOI:10.1137/19M1274067. Repo: https://github.com/lululxvi/deepxde.
- **PINN review (state of the field):** Karniadakis, G. E., Kevrekidis, I. G., Lu, L., Perdikaris, P., Wang, S., Yang, L. (2021). *Physics-informed machine learning.* Nature Reviews Physics 3, 422–440. DOI:10.1038/s42254-021-00314-5.
- **PINN for heat / diffusion equations specifically:** Cuomo, S., Schiano Di Cola, V., Giampaolo, F., Rozza, G., Raissi, M., Piccialli, F. (2022). *Scientific Machine Learning Through Physics-Informed Neural Networks: Where We Are and What's Next.* J. Sci. Comput. 92, 88. DOI:10.1007/s10915-022-01939-z. Survey covering heat-diffusion PINN benchmarks directly applicable to our 1-D `∂T/∂t = κ ∂²T/∂x²` setup.
- **Thermal diffusivity κ for refractory heater materials** (anchors our PDE constant): NiCr ~`3e-6`–`5e-6 m²/s`, tungsten ~`6e-5 m²/s`, molybdenum ~`5e-5 m²/s`. Source: CRC Handbook of Chemistry & Physics, 97th ed. (2016), Section 12 — Thermal & Electrical Properties of Metals; H.C. Starck *Refractory Metals for Thermal Management* technical guide (2020).
- **Coffin-Manson on the heater drift metric** (cross-reference, see ADR-006): Coffin (1954) Trans. ASME 76, 931–950; Manson (1954) NACA TN-2933.
