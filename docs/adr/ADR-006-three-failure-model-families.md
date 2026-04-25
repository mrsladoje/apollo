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

## Parameter ranges and citations

The "literature-cited" claim made throughout this ADR is operationalized below. Each component's coefficients are anchored to a published range (not a single point estimate), and our chosen value is disclosed as a synthetic assumption falling inside that range. This is the table the technical report cites; the values are echoed in code comments in `src/engine/failure_models/` and `src/engine/components/`.

| Component | Family | Parameter | Our value | Published range / source |
| --- | --- | --- | --- | --- |
| Recoater Blade (height loss) | Exponential (Archard) | wear coefficient `k` | `1e-6` (synthetic) | `1e-7`–`1e-5` for ceramic-on-metal abrasive contact; Archard (1953); Aghababaei, Warner & Molinari, *Critical length scale controls adhesive wear mechanisms,* Nat. Commun. 7, 11816 (2016), DOI:10.1038/ncomms11816; Vakis et al., *Modeling and simulation in tribology across scales,* Tribology International 125 (2018), DOI:10.1016/j.triboint.2018.02.005 |
| Recoater Blade (impact events) | Weibull | β (shape) | `2.0` | β > 1 (wear-out) for ceramic blade impact; Weibull (1951); AM-specific blade wear: Pfeiffer et al., *Direct laser AM of high-performance oxide ceramics,* J. Eur. Ceram. Soc. (2021), DOI:10.1016/j.jeurceramsoc.2021.05.035 |
| Drive Motor | Weibull | β (shape) | `1.5` | β = 1.0–1.5 typical for rolling-element bearings; Weibull-slope convention from ISO 281:2007 *Rolling bearings — Dynamic load ratings and rating life*; Harris & Kotzalas, *Rolling Bearing Analysis,* 5th ed. (2007); L10 statistical basis (10% fail before nominal life). |
| Drive Motor | Weibull | η (characteristic life) | `2000 h` | Industrial servo-bearing L10 ranges: ISO 281; survey in Feng et al., *Vibration-based updating of wear prediction for spur gears,* Wear (2019), DOI:10.1016/j.wear.2019.01.017 |
| Nozzle Plate | Weibull | β (shape) | `2.5` | Stochastic clog time-to-event in thermal-inkjet, β > 1 wear-out; Lifetime/failure-mode study, *Lifetime and Failure Mode Study on the Micro-heater of TIJ Printhead,* Print4Fab/IS&T 2020 (https://library.imaging.org); Fujifilm Inkjet Accelerator: *How do you estimate the life of the printhead?* (industry technical note). |
| Thermal Firing Resistor | Coffin-Manson | exponent `c` | `2.0` | Range 1.9–2.5 typical for thin-film inkjet heaters; foundational: Coffin (1954) *A Study of the Effects of Cyclic Thermal Stresses on a Ductile Metal,* Trans. ASME 76:931–950; Manson (1954) *Behavior of materials under conditions of thermal stress,* NACA TN-2933; standards: IPC-9701A *Performance Test Methods and Qualification Requirements for Surface Mount Solder Attachments*; ASTM E2714-13 *Standard Practice for Creep-Fatigue Testing*; thermal-inkjet specifics: Lifetime/Failure-Mode Study (IS&T Print4Fab 2020); *Investigation of reliability problems in thermal inkjet printhead* (IEEE/ResearchGate, publ. 4082063). |
| Thermal Firing Resistor | Coffin-Manson | constant `C` | `1e6 cycles · ε^c` (synthetic) | Order-of-magnitude consistent with thin-film heater Coffin-Manson data in Print4Fab 2020 micro-heater study; specific value disclosed as synthetic assumption. |
| Heating Element | Coffin-Manson + PINN | thermal diffusivity `κ` | `5e-6 m²/s` (NiCr-class) | Refractory metal heater range: NiCr ~`3e-6`–`5e-6 m²/s`; tungsten ~`6e-5 m²/s`; molybdenum ~`5e-5 m²/s`; CRC Handbook of Chemistry & Physics (97th ed., 2016, Section 12 — Thermal & Electrical Properties of Metals); H.C. Starck *Refractory Metals for Thermal Management* technical guide (2020). |
| Heating Element | PINN PDE | 1-D heat diffusion `∂T/∂t = κ ∂²T/∂x²` | — | Foundational ML method: Raissi, Perdikaris & Karniadakis, *Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear PDEs,* J. Comput. Phys. 378 (2019) 686–707, DOI:10.1016/j.jcp.2018.10.045; review: Karniadakis et al., *Physics-informed machine learning,* Nat. Rev. Phys. 3 (2021), DOI:10.1038/s42254-021-00314-5; library: Lu et al., *DeepXDE: A Deep Learning Library for Solving Differential Equations,* SIAM Review 63(1) (2021) 208–228, DOI:10.1137/19M1274067. |
| Insulation Panel | Exponential `k_eff` decay | `α` (decay rate) | `5e-5 / h` (synthetic) | Refractory ceramic-fiber insulation aging follows Arrhenius-controlled crystallization; NASA TM-100255, *High-Temperature Properties of Ceramic Fibers and Insulations* (1988); CVSic / NUTEC ceramic-fiber technical data sheets (industry); Liu et al., *Advancements in Thermal Insulation through Ceramic Micro-/Nanofibers,* Nanomaterials (2024), PMC11124260. |
| CSC-B Cascade | Arrhenius binder viscosity | `Ea/R` | `4500 K` | PEG/PVP-class AM polymer binders; Han et al., *Recent Progress on Polymer Materials for Additive Manufacturing,* Adv. Funct. Mater. 30 (2020), DOI:10.1002/adfm.202003062; Du et al., *Jetting Performance of Polyethylene Glycol and Reactive Dye Solutions* (2019); thermal/rheological data on PEG-400/PEG-1500 (industry rheology data, ResearchGate publ. 316713550). |
| CSC-B Cascade | Coffin-Manson thermal strain | thermal expansion coeff. `α_TC` | component-specific | CTE values from CRC Handbook (97th ed.); thermal-fatigue strain `Δε = α_TC · ΔT` is the standard derivation; cited in Lau, *Solder joint reliability under thermal/mechanical/vibrational conditions,* IEEE Trans. CPMT 19(4) (1996), DOI:10.1109/96.544363, and the broader Coffin-Manson literature. |

### Disclosed assumptions (no proprietary HP S100 data)

We do **not** claim our specific values match an HP Metal Jet S100. The technical report and demo speaker notes state explicitly that:
1. Each parameter falls inside a published range for the analogous mechanism in the analogous component class (binder-jetting blade wear, industrial bearings, thermal-inkjet resistors, refractory heater elements, ceramic-fiber insulation).
2. Specific point estimates are synthetic, chosen so the three cascades resolve within the 600-minute Stressed scenario per PRD §10.2.
3. R-1 (coupling-matrix tuning) explicitly retains the *structure* (sparsity pattern) of `M` from PRD §10.1 and only adjusts magnitudes, keeping the literature-anchored qualitative behavior intact.

## References

- PRD §8 (Component Model — failure-model column), FR-1.3, §12, Appendix B
- HP brief: `task/stage1.md` ("at least two standard mathematical failure models")
- **Foundational failure-model papers:**
  - Weibull, W. (1951). *A statistical distribution function of wide applicability.* J. Appl. Mech. 18(3), 293–297.
  - Coffin, L. F. (1954). *A study of the effects of cyclic thermal stresses on a ductile metal.* Trans. ASME 76, 931–950.
  - Manson, S. S. (1954). *Behavior of materials under conditions of thermal stress.* NACA Technical Note 2933.
  - Archard, J. F. (1953). *Contact and rubbing of flat surfaces.* J. Appl. Phys. 24(8), 981–988, DOI:10.1063/1.1721448.
- **Standards bodies:**
  - ISO 281:2007 — *Rolling bearings — Dynamic load ratings and rating life.*
  - IPC-9701A — *Performance Test Methods and Qualification Requirements for Surface Mount Solder Attachments.*
  - ASTM E2714-13 — *Standard Practice for Creep-Fatigue Testing.*
- **Reliability-engineering reviews (modern):**
  - Wang, H., Liserre, M., Blaabjerg, F. (2014). *Toward Reliable Power Electronics: Challenges, Design Tools, and Opportunities.* IEEE Industrial Electronics Magazine, DOI:10.1109/mie.2013.2252958.
  - Wang, H., et al. (2014). *Transitioning to Physics-of-Failure as a Reliability Driver in Power Electronics.* IEEE JESTPE, DOI:10.1109/jestpe.2013.2290282.
  - Li, S., et al. (2020). *Modeling and Analysis of Performance Degradation Data for Reliability Assessment: A Review.* IEEE Access, DOI:10.1109/access.2020.2987332.
- **AM/binder-jetting specific:**
  - Goh, G. D., Sing, S. L., Yeong, W. Y. (2020). *A review on machine learning in 3D printing.* Artif. Intell. Rev., DOI:10.1007/s10462-020-09876-9.
  - Bernard, A., Kruth, J.-P., Cao, J., et al. (2023). *Vision on metal additive manufacturing: Developments, challenges and future trends.* CIRP J. Manufacturing Sci. & Tech., DOI:10.1016/j.cirpj.2023.08.005.
  - Hou, Z., et al. (2022). *Online Monitoring Technology of Metal Powder Bed Fusion Processes: A Review.* Materials 15, 7598, DOI:10.3390/ma15217598.
  - Han, C., et al. (2020). *Recent Progress on Polymer Materials for Additive Manufacturing,* Adv. Funct. Mater., DOI:10.1002/adfm.202003062.
- **Tribology / wear (Archard context):**
  - Aghababaei, R., Warner, D. H., Molinari, J.-F. (2016). *Critical length scale controls adhesive wear mechanisms.* Nat. Commun. 7, 11816, DOI:10.1038/ncomms11816.
  - Vakis, A. I., et al. (2018). *Modeling and simulation in tribology across scales: An overview.* Tribology International, DOI:10.1016/j.triboint.2018.02.005.
- **PINN / heat-equation (relevant to ADR-005 cross-link):**
  - Raissi, M., Perdikaris, P., Karniadakis, G. E. (2019). *Physics-informed neural networks.* J. Comput. Phys. 378, 686–707, DOI:10.1016/j.jcp.2018.10.045.
  - Lu, L., Meng, X., Mao, Z., Karniadakis, G. E. (2021). *DeepXDE: A deep learning library for solving differential equations.* SIAM Review 63(1), 208–228, DOI:10.1137/19M1274067.
  - Karniadakis, G. E., et al. (2021). *Physics-informed machine learning.* Nat. Rev. Phys. 3, DOI:10.1038/s42254-021-00314-5.
