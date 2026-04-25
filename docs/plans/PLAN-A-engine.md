# PLAN A — Engine & Physics (Developer A)

> **Apollo · HP Metal Jet S100 Digital Co-Pilot · HackUPC 2026**
> Owner: Developer A. Critical path for Plans B (simulation/historian) and C (agent/UI).
> Source-of-truth chain: `brief → PRD → ADRs → this plan → code`. If anything below contradicts the PRD or an ADR, the ADR/PRD wins; reconcile by editing this plan, not the code.

---

## 1. Goal & success criteria

**Goal.** Ship the entire Phase 1 "Brain" of Apollo: six deterministic component models across three subsystems, a 6×6 linear coupling matrix `M`, three explicit cascades, a DeepXDE PINN for the heating element, and a MAPIE conformal-prediction layer wrapping every per-component forecast. Expose all of this behind a single stable function `step(state, drivers, dt) -> state` plus `forecast(state, horizon_min) -> list[Forecast]`, with a Pydantic State Report schema and bit-identical determinism for identical inputs.

**Requirements satisfied (PRD traceability).**

| ID | Source | Plan A obligation |
| --- | --- | --- |
| FR-1.1 | PRD §6.1, §8 | 6 components, 3 subsystems, 2 per subsystem (ADR-002). |
| FR-1.2 | PRD §6.1, §9 | Each component consumes ≥ 1 driver from the canonical Drivers vector. |
| FR-1.3 | PRD §6.1 | 3 failure-model families: exponential, Weibull, Coffin-Manson (ADR-006). |
| FR-1.4 | PRD §6.1, §8 | Pydantic-validated `ComponentState` with health, status enum, metrics dict. |
| FR-1.5 | PRD §6.1, NFR-1 | Bit-identical outputs for identical inputs. Seeded RNG threaded through `state`. |
| FR-1.6 | PRD §6.1, §10.1 | Linear coupling matrix `M` with the §10.1 update rule (ADR-004). |
| FR-1.7 | PRD §6.1, §11.1 | DeepXDE PINN for heater; trained MPS, frozen, CPU inference < 5 ms (ADR-005). |
| FR-1.8 | PRD §6.1 | Single `step(state, drivers, dt) -> state` interface, stable across subsystems. |
| FR-W.6 | PRD §6.4, §11.6 | MAPIE 1.3 `MapieTimeSeriesRegressor` with EnbPi block bootstrap; ≥ 90 % empirical coverage on Stressed at 95 % nominal CI (ADR-015). |
| NFR-1 | PRD §7 | Determinism — verified by golden-file two-run byte-compare. |
| NFR-2 | PRD §7 | < 50 ms / `step()` for all 6 components on M3 Max CPU. |
| NFR-3 | PRD §7 | < 5 ms / PINN call on CPU. |

**Done = every box in §13 ticked, every verification command in §13 returns exit 0.**

---

## 2. ADR map

Every ADR Plan A consumes, with the one-line obligation it imposes here.

| ADR | Title | Obligation on Plan A |
| --- | --- | --- |
| ADR-001 | Hybrid rule-based + PINN | 5 components are pure-NumPy rule-based; the heater is the **only** PINN. R-2 fallback (learned regressor surrogate) wired but unused unless PINN unstable. |
| ADR-002 | 6 components / 3 subsystems | Ship exactly: Blade, Motor, Nozzle, Resistor, Heater, Insulation. No hopper, no rails, no sensors. Closed list. |
| ADR-003 | Three parallel cascades | CSC-A (Blade→Motor) and CSC-C (Blade→Nozzle) ride matrix-only. CSC-B (Insulation→Heater→Nozzle+Resistor) gets explicit Arrhenius + Coffin-Manson physics layered on top of `M`. |
| ADR-004 | Linear coupling matrix `M` | Implement the literal §10.1 matrix as a 6×6 NumPy array. Update rule `dH_i/dt = -α_i · f(drivers_i) - Σ_j M_ij · (1 - H_j)` exactly. |
| ADR-005 | DeepXDE for heater PINN | DeepXDE + PyTorch MPS for offline training, frozen weights, CPU inference. 4 hidden × 64 units. 1-D heat-diffusion PDE residual `∂T/∂t = κ ∂²T/∂x²`. Artifact at `models/heater_pinn.pt`. |
| ADR-006 | 3 failure-model families | Each family is its own pure-NumPy class with shared signature `decay(state, drivers, dt) -> dH`. Each family has a unit-test with literature-cited known-input / known-output cases. |
| ADR-015 | MAPIE conformal prediction | Wrap every per-component decay/PINN predictor in `MapieTimeSeriesRegressor(method="enbpi")` block bootstrap. Cap horizon at 60 simulated minutes. Empirical coverage ≥ 90 % on Stressed at 95 % nominal. |

(ADR-007 SQLite historian, ADR-013 Dark Twin scenarios are Plan B's surface; Plan A only emits the rows they persist.)

---

## 3. Integration contracts (frozen)

> **BREAKING-CHANGE-REQUIRES-HANDSHAKE.** Plans B and C build against the exact signatures below. Anything that changes the type, shape, or name of these symbols requires a synchronous handshake with both other developers and a bump of `apollo.engine.__version__`. No silent contract drift.

### 3.1 Pydantic / enum surface — `src/engine/contracts.py`

```python
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

# ----- Canonical 6-component identity (shared with Plan C citation validator) -----
class ComponentId(str, Enum):
    BLADE      = "blade"
    MOTOR      = "motor"
    NOZZLE     = "nozzle"
    RESISTOR   = "resistor"
    HEATER     = "heater"
    INSULATION = "insulation"

class ComponentStatus(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"   # health >= 0.7
    DEGRADED   = "DEGRADED"     # 0.4 <= health < 0.7
    CRITICAL   = "CRITICAL"     # 0.1 <= health < 0.4
    FAILED     = "FAILED"       # health < 0.1

# ----- State Report (FR-1.4) -----
class ComponentState(BaseModel):
    model_config = ConfigDict(frozen=True)
    component_id: ComponentId
    health: float = Field(ge=0.0, le=1.0)
    status: ComponentStatus
    metrics: dict[str, float]   # component-specific (blade_thickness_mm, current_draw_A, ...)

# ----- Driver vector (PRD §9.2; FR-1.2) -----
class Drivers(BaseModel):
    model_config = ConfigDict(frozen=True)
    temp_C: float
    humidity: float          # 0..1 relative humidity
    pm25: float              # ug/m^3
    psd_d50: float           # micrometers
    voltage_stability: float # 0..1, 1.0 = perfectly stable
    cycles: int              # cumulative print cycles
    hours: float             # cumulative operating hours
    maintenance_level: dict[ComponentId, float]   # 0..1, 1.0 = freshly maintained
    operator_shift: Literal["day", "night", "weekend"]
    rng_seed: int

# ----- World state -----
class EngineState(BaseModel):
    model_config = ConfigDict(frozen=True)
    components: dict[ComponentId, ComponentState]
    coupling_matrix: list[list[float]]   # 6x6, row order == ComponentId enum order
    rng_state: tuple                     # serialized np.random.Generator state

# ----- Conformal forecast triple (FR-W.6, ADR-015) -----
class Forecast(BaseModel):
    model_config = ConfigDict(frozen=True)
    component_id: ComponentId
    horizon_min: int      # 1 .. 60 (cap per ADR-015)
    point: float
    lower: float
    upper: float
    ci_level: float       # nominal coverage, default 0.95
```

### 3.2 The single function the rest of the system calls — `src/engine/api.py`

```python
def step(state: EngineState, drivers: Drivers, dt: float) -> EngineState:
    """Advance every component by dt simulated minutes.
    Pure function. Same (state, drivers, dt) -> same EngineState (FR-1.5, NFR-1).
    Total wall time < 50 ms on M3 Max CPU for all 6 components (NFR-2)."""
    ...

def forecast(state: EngineState, horizon_min: int) -> list[Forecast]:
    """Return one Forecast per component at horizon_min (1..60).
    Wraps each component's decay/PINN predictor with MapieTimeSeriesRegressor (EnbPi).
    Empirical coverage on Stressed >= 0.90 at ci_level=0.95 (FR-W.6, ADR-015)."""
    ...

def initial_state(scenario: str = "default", seed: int = 0) -> EngineState:
    """Construct a fresh EngineState with all 6 components at health=1.0,
    coupling matrix loaded from PRD §10.1, and seeded RNG."""
    ...
```

These three symbols are the only things outside `src/engine/` may import from the engine. Plan B's simulation loop and Plan C's `compare_runs` / `run_counterfactual` tools depend exclusively on them.

---

## 4. Mock-first rollout (Step 0 — hour 0–1, day-zero unblock)

The very first deliverable is a **mock engine** so Plan B (sim loop, historian) and Plan C (agent, UI) are unblocked from minute one.

### 4.1 Mock contract — `src/engine/mock_engine.py`

- Implements the exact `step`, `forecast`, `initial_state` signatures from §3.2.
- All 6 `ComponentState`s present from `initial_state(seed=s)`.
- Deterministic synthetic decay curves: `health_i(t) = 1.0 - clip(α_i · t / 600, 0, 1)` with hand-set `α_i` so:
  - In a 600-minute (10 h) Stressed run with no maintenance, the heater hits FAILED around minute ~480 and the nozzle around minute ~520.
  - Blade and motor reach DEGRADED but not FAILED.
  - Insulation drops monotonically; resistor cycles up under shift load.
- Mock PINN: `mock_pinn(temp_C, hours) -> drift_pct = sigmoid((hours - 6) / 1.5) * 0.4`. Pure NumPy, < 0.1 ms.
- Mock `MapieTimeSeriesRegressor`: returns `(point, point - 0.05*sqrt(horizon_min), point + 0.05*sqrt(horizon_min))` clamped to `[0, 1]`. Bands widen with horizon, satisfying the visual contract Plan C wires to Recharts.
- Status enum and Pydantic schemas are the **real** ones from §3.1 (no mock). Plan B and Plan C must never see a fake schema.

### 4.2 Commit gate

`tests/engine/test_mock_engine.py` ships with the mock and asserts:
- `step` is bit-deterministic for fixed seed.
- All 6 components reachable.
- `forecast` returns 6 `Forecast` rows for any `horizon_min in 1..60`.
- `forecast` rejects `horizon_min > 60` with `ValueError` (ADR-015 cap).

The mock is committed at hour 1 of day-zero, before any real component module lands. Plans B/C build against it for the first 4 hours; from hour 4 onward they switch imports module-by-module as real components ship behind the same names.

### 4.3 Replacement policy

Real modules replace mock symbols **one component at a time** behind the import path `src.engine.api`. The mock module stays in the tree, gated behind `APOLLO_ENGINE=mock` env var, for Plan B's smoke tests and demo dry-runs where engine compute should be skipped.

---

## 5. Workstream A1 — Failure model classes

### 5.1 Layout

```
src/engine/failure_models/
    __init__.py
    base.py            # FailureModel abstract base
    exponential.py     # ExponentialDecay
    weibull.py         # WeibullDecay
    coffin_manson.py   # CoffinManson
```

### 5.2 Shared signature

```python
# src/engine/failure_models/base.py
from abc import ABC, abstractmethod
import numpy as np

class FailureModel(ABC):
    @abstractmethod
    def decay(
        self,
        health: float,
        drivers: dict,        # extracted slice of Drivers relevant to this component
        dt: float,            # simulated minutes
        rng: np.random.Generator,
    ) -> float:
        """Return dH (negative or zero). Pure function except for rng draws."""
```

### 5.3 The three classes (ADR-006)

**ExponentialDecay** — `H(t) = H0 · exp(-α · stress(t))` differential form `dH = -α · stress · H · dt`.
- Used by Recoater Blade (height-loss component) and Insulation Panel.
- Coefficients anchored to literature ranges; constants live in `src/engine/components/<comp>.py`, not in this module.

**WeibullDecay** — `F(t) = 1 - exp(-(t/η)^β)`; instantaneous hazard `h(t) = (β/η) · (t/η)^(β-1)`. Health decrement per `dt`: `dH = -h(t) · dt`.
- Used by Drive Motor (bearing fatigue), Nozzle Plate (clogging probability), Recoater Blade (impact-event Weibull layered on top of the exponential).
- β > 1 (wear-out region) for all three.

**CoffinManson** — `N_f = C · (Δε_p)^(-c)`; per cycle damage `1/N_f`; we operate in cycles, not time, so the input driver carries `cycles_this_step`. Health decrement `dH = -cycles_this_step / N_f`.
- Used by Thermal Firing Resistors and (combined with the PINN) Heating Element.
- `Δε_p` derived from temperature swing in CSC-B.

### 5.4 Acceptance criteria (each is a unit test)

- [ ] `tests/engine/failure_models/test_exponential.py::test_known_input_known_output` — for `α=0.001, stress=1.0, H=1.0, dt=60`, asserts `dH ≈ -0.06` (within 1e-9, byte-compare across two runs).
- [ ] `tests/engine/failure_models/test_exponential.py::test_zero_stress_no_decay` — `stress=0` ⇒ `dH == 0.0` exactly.
- [ ] `tests/engine/failure_models/test_weibull.py::test_known_input_known_output` — `β=2.5, η=400, t=200, dt=1` reproduces the closed-form hazard to 1e-9.
- [ ] `tests/engine/failure_models/test_weibull.py::test_hazard_monotone_increasing` — for β>1, `h(t2) > h(t1)` for `t2 > t1` over 100 sample times.
- [ ] `tests/engine/failure_models/test_coffin_manson.py::test_known_input_known_output` — `C=1e6, c=2.0, Δε=0.005, cycles=10` ⇒ `dH = -10 / (1e6 · 0.005^-2)` to 1e-12.
- [ ] `tests/engine/failure_models/test_coffin_manson.py::test_zero_cycles_no_decay` — `cycles=0` ⇒ `dH == 0.0` exactly.
- [ ] `tests/engine/failure_models/test_determinism.py::test_two_runs_byte_identical` — every model class run twice with the same seeded `Generator` produces byte-identical outputs.

---

## 6. Workstream A2 — Component models

### 6.1 Layout

```
src/engine/components/
    __init__.py
    base.py            # Component abstract base
    blade.py           # RecoaterBlade
    motor.py           # DriveMotor
    nozzle.py          # NozzlePlate
    resistor.py        # ThermalFiringResistors
    heater.py          # HeatingElement (wraps PINN)
    insulation.py      # InsulationPanel
```

### 6.2 Shared interface

```python
# src/engine/components/base.py
class Component(ABC):
    component_id: ComponentId
    intrinsic_alpha: float          # α_i in PRD §10.1

    @abstractmethod
    def intrinsic_decay(self, state: ComponentState, drivers: Drivers, dt: float,
                        rng: np.random.Generator) -> float:
        """Return -α_i · f(drivers_i) · dt as dH (negative or zero)."""

    @abstractmethod
    def emit_metrics(self, state: ComponentState, drivers: Drivers) -> dict[str, float]:
        """Recompute the component-specific metrics dict for this step."""
```

### 6.3 Per-component spec

| # | Component | Subsystem | Driver(s) consumed (PRD §9) | Failure family (ADR-006) | Metrics emitted (FR-1.4, PRD §8) |
| - | --- | --- | --- | --- | --- |
| 1 | **RecoaterBlade** | Recoating | `psd_d50`, `pm25`, `cycles` | Exponential height loss + impact-event Weibull (composed) | `blade_thickness_mm`, `impact_count` |
| 2 | **DriveMotor** | Recoating | `voltage_stability`, `cycles`, plus coupled term from blade via `M[motor, blade]=0.4` | Weibull bearing fatigue | `current_draw_A`, `bearing_temp_C` |
| 3 | **NozzlePlate** | Printhead | `humidity`, `temp_C` (binder viscosity proxy), `pm25` | Weibull clogging probability | `clog_prob`, `active_nozzle_count` |
| 4 | **ThermalFiringResistors** | Printhead | `cycles_this_step` (duty), `temp_C`, `voltage_stability` | Coffin-Manson | `resistance_pct` |
| 5 | **HeatingElement** | Thermal | `temp_C` (HVAC short-cycling proxy), `hours`, `voltage_stability`, **PINN call** | Coffin-Manson on the PINN-predicted temp swing | `predicted_temp_field` (3 sample points), `drift_pct` |
| 6 | **InsulationPanel** | Thermal | cumulative heat exposure (`temp_C` integral), `hours` | Exponential `k_eff` decay | `k_eff_W_mK` |

### 6.4 Status thresholds (PRD §8)

Single shared helper:

```python
def status_for_health(h: float) -> ComponentStatus:
    if h >= 0.7: return ComponentStatus.FUNCTIONAL
    if h >= 0.4: return ComponentStatus.DEGRADED
    if h >= 0.1: return ComponentStatus.CRITICAL
    return ComponentStatus.FAILED
```

Lives in `src/engine/contracts.py` next to the enums. Plan C's citation validator imports the same helper to avoid threshold drift.

### 6.5 Acceptance criteria (per component)

For every component (6 instances of the same suite):

- [ ] `test_<comp>_driver_dependent_change` — increasing the dominant driver between two `step()` invocations strictly increases `|dH|` (FR-1.2 evidence).
- [ ] `test_<comp>_health_clamped_0_1` — under any 600-minute Stressed driver trace, health never escapes `[0, 1]`.
- [ ] `test_<comp>_status_thresholds` — at health 0.71, 0.69, 0.41, 0.39, 0.11, 0.09 the status enum is exactly FUNCTIONAL/DEGRADED/DEGRADED/CRITICAL/CRITICAL/FAILED.
- [ ] `test_<comp>_metrics_keys_present` — `emit_metrics` returns the exact key set in §6.3 (no extras, no missing).
- [ ] `test_<comp>_determinism` — 2× run, byte-compare on `ComponentState.model_dump_json()`.

Plus three component-specific cases:

- [ ] `test_blade_psd_d90_drives_wear` — D50 doubled ⇒ blade thickness drops ≥ 1.8× faster over 60 minutes.
- [ ] `test_nozzle_humidity_drives_clog` — humidity 0.3 → 0.8 increases `clog_prob` derivative by ≥ 1.5×.
- [ ] `test_heater_pinn_called_each_step` — patch the PINN object, assert `forward()` invoked once per `step()`.

---

## 7. Workstream A3 — Coupling matrix `M` and cascades

### 7.1 The matrix (literal, from PRD §10.1)

`src/engine/coupling.py`:

```python
import numpy as np
from src.engine.contracts import ComponentId

# Row order == ComponentId enum order: blade, motor, nozzle, resistor, heater, insulation
COUPLING_MATRIX_M = np.array([
    # blade  motor  nozzle resist heater insul
    [ 0.0,   0.0,   0.0,   0.0,   0.0,   0.0  ],   # blade
    [ 0.4,   0.0,   0.0,   0.0,   0.0,   0.0  ],   # motor   <- CSC-A
    [ 0.2,   0.0,   0.0,   0.0,   0.3,   0.0  ],   # nozzle  <- CSC-C (from blade), CSC-B (from heater)
    [ 0.0,   0.0,   0.1,   0.0,   0.2,   0.0  ],   # resistor <- CSC-B
    [ 0.0,   0.0,   0.0,   0.0,   0.0,   0.5  ],   # heater  <- CSC-B
    [ 0.0,   0.0,   0.0,   0.0,   0.0,   0.0  ],   # insulation
], dtype=np.float64)

ROW_ORDER = [ComponentId.BLADE, ComponentId.MOTOR, ComponentId.NOZZLE,
             ComponentId.RESISTOR, ComponentId.HEATER, ComponentId.INSULATION]
```

### 7.2 Update rule (literal, from PRD §10.1, ADR-004)

```
dH_i / dt = -α_i · f(drivers_i)  -  Σ_j  M_ij · (1 - H_j)
```

Implementation:

```python
def apply_coupling(healths: np.ndarray, intrinsic_dH: np.ndarray, dt: float) -> np.ndarray:
    """healths: shape (6,) in [0,1]. intrinsic_dH: shape (6,) per-component decay (already ≤ 0).
       Returns new healths, clamped to [0,1]."""
    coupled_term = COUPLING_MATRIX_M @ (1.0 - healths)        # shape (6,)
    dH = intrinsic_dH - coupled_term * dt
    return np.clip(healths + dH, 0.0, 1.0)
```

### 7.3 The three cascades (ADR-003)

**CSC-A — Recoating loop (matrix-only).** `M[motor, blade] = 0.4`. As blade health drops, motor decay accelerates. No additional ODE.

**CSC-B — Thermal-Printhead loop (matrix + explicit physics).** This is the demo showpiece. On top of `M[heater, insulation]=0.5`, `M[nozzle, heater]=0.3`, `M[resistor, heater]=0.2`, `M[resistor, nozzle]=0.1`, we add explicit physics in `src/engine/cascades/csc_b.py`:

```python
# Arrhenius binder-viscosity: μ(T) = μ_ref · exp(Ea/R · (1/T - 1/T_ref))
def binder_viscosity(temp_C: float) -> float:
    Ea_over_R = 4500.0     # K, literature-cited range for typical AM binders
    T_ref_K   = 298.15
    T_K       = temp_C + 273.15
    return MU_REF * np.exp(Ea_over_R * (1.0/T_K - 1.0/T_ref_K))

# Coffin-Manson cycles-to-failure for thermal-fatigue accumulation
def coffin_manson_damage(delta_T: float, cycles: int) -> float:
    delta_eps = ALPHA_TC * delta_T          # thermal expansion strain
    N_f = C_CM * (delta_eps ** -C_EXP)
    return cycles / N_f                     # damage fraction this step
```

The CSC-B layer reads the **PINN-predicted** heater temperature swing per step, computes `binder_viscosity` and `coffin_manson_damage`, and adds *additional* (non-matrix) decrements to nozzle health (viscosity-driven clog acceleration) and resistor health (thermal fatigue). These are layered after matrix coupling, not in place of it.

**CSC-C — Powder contamination loop (matrix-only).** `M[nozzle, blade] = 0.2`. Blade ceramic flaking ⇒ powder contamination ⇒ nozzle clog acceleration. No additional ODE.

### 7.4 Acceptance criteria

- [ ] `test_coupling_matrix_literal` — assert `COUPLING_MATRIX_M` is exactly the 6×6 published in PRD §10.1 (single source of truth).
- [ ] `test_csc_a_motor_accelerates_on_blade_failure` — drive blade health to 0.1; motor `dH` over next 60 min must be ≥ 1.5× the dH with blade=1.0, holding all other drivers fixed.
- [ ] `test_csc_b_arrhenius_monotone` — `binder_viscosity(50) > binder_viscosity(30)` and ratio matches Arrhenius closed form to 1e-6.
- [ ] `test_csc_b_coffin_manson_damage_monotone_in_dt` — damage strictly increases with `delta_T` for fixed cycles.
- [ ] `test_csc_b_full_path` — under Stressed scenario, in a 600-minute run with insulation seeded to health=0.6, nozzle reaches CRITICAL strictly before it would with insulation=1.0 held constant.
- [ ] `test_csc_c_nozzle_accelerates_on_blade_flaking` — analogous to CSC-A with nozzle as victim.
- [ ] `test_no_coupling_self_loops` — `np.diag(COUPLING_MATRIX_M)` is all zeros.

---

## 8. Workstream A4 — Heating Element PINN (DeepXDE)

### 8.1 Layout

```
src/engine/pinn/
    __init__.py
    pde.py             # HeatDiffusion1D PDE definition
    data_gen.py        # Synthetic training-data generator
    train.py           # Offline training script (MPS)
    inference.py       # Frozen-weights CPU inference wrapper
    fallback.py        # R-2 mitigation: scikit-learn regressor surrogate
models/
    heater_pinn.pt     # Frozen artifact, checked into the repo
```

### 8.2 PDE (ADR-005)

1-D heat diffusion: `∂T/∂t = κ · ∂²T/∂x²` on `x ∈ [0, L]`, `t ∈ [0, T_max]`.

- κ (thermal diffusivity): single scalar, literature-cited range for refractory metal heater.
- Boundary conditions:
  - `x = 0` (insulation interface): `T(0, t) = T_ambient + (heater_duty(t) · ΔT_max) · (1 - k_eff_factor(t))` — degraded insulation raises the inner-wall temperature seen by the heater.
  - `x = L` (ambient interface): `T(L, t) = T_ambient(t)`.
- Initial condition: `T(x, 0) = T_ambient(0) + (T_duty - T_ambient(0)) · (1 - x/L)` (linear preheat profile).

### 8.3 Architecture (ADR-005)

- DeepXDE `dde.maps.FNN` with 4 hidden layers × 64 units, `tanh` activation. Input dim 2 (`x`, `t`), output dim 1 (`T`). ~10–50 k params.
- Loss = `λ_pde · L_pde + λ_data · L_data + λ_bc · L_bc + λ_ic · L_ic`, with the PDE residual term computed by DeepXDE's autograd.

### 8.4 Synthetic training data (`data_gen.py`)

- Generated from the same physics: a finite-difference reference solver for `∂T/∂t = κ ∂²T/∂x²` runs over the BC space spanned by realistic Apollo drivers (HVAC short-cycling sinusoids, ambient temp ramps, duty-cycle pulses).
- 5000 collocation points + 500 boundary points + 500 IC points.
- The training data is committed to the repo under `data/pinn_training/` so any teammate can re-run training reproducibly.

### 8.5 Training (`train.py`, MPS)

```python
# Pseudocode — actual implementation in train.py
import deepxde as dde
import torch

dde.config.set_default_float("float32")
torch.set_default_device("mps")        # MPS for training only

geom = dde.geometry.Interval(0.0, L)
timedomain = dde.geometry.TimeDomain(0.0, T_MAX)
geomtime = dde.geometry.GeometryXTime(geom, timedomain)

def pde_residual(x, T):
    dT_dt   = dde.grad.jacobian(T, x, j=1)
    d2T_dx2 = dde.grad.hessian(T, x, j=0)
    return dT_dt - KAPPA * d2T_dx2

bc_inner = dde.icbc.DirichletBC(geomtime, lambda x: inner_wall_T(x[:, 0:1], x[:, 1:2]),
                                lambda x, on: np.isclose(x[0], 0.0))
bc_outer = dde.icbc.DirichletBC(geomtime, lambda x: ambient_T(x[:, 1:2]),
                                lambda x, on: np.isclose(x[0], L))
ic       = dde.icbc.IC(geomtime, lambda x: linear_preheat(x[:, 0:1]),
                       lambda _, on_initial: on_initial)

data = dde.data.TimePDE(geomtime, pde_residual,
                        [bc_inner, bc_outer, ic],
                        num_domain=5000, num_boundary=500, num_initial=500)
net  = dde.maps.FNN([2] + [64]*4 + [1], "tanh", "Glorot uniform")
model = dde.Model(data, net)
model.compile("adam", lr=1e-3, loss_weights=[1, 1, 1, 1])
model.train(iterations=20_000)
model.compile("L-BFGS")
model.train()
torch.save(model.net.state_dict(), "models/heater_pinn.pt")
```

Training expected to complete in 5–10 minutes on M3 Max MPS (per ADR-005).

### 8.6 Inference (`inference.py`, CPU)

```python
class HeaterPINN:
    def __init__(self, weights_path: str = "models/heater_pinn.pt"):
        self.net = build_fnn([2, 64, 64, 64, 64, 1])    # mirror of training arch
        self.net.load_state_dict(torch.load(weights_path, map_location="cpu"))
        self.net.eval()
        torch.set_grad_enabled(False)

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        """Returns T(x, t) for an array of x positions at a single time t.
           < 5 ms per call on M3 Max CPU (NFR-3)."""
        with torch.inference_mode():
            inp = torch.tensor(np.column_stack([x, np.full_like(x, t)]), dtype=torch.float32)
            return self.net(inp).cpu().numpy().squeeze()
```

The `HeatingElement` component calls `HeaterPINN` once per `step()`; the returned temp field feeds CSC-B's Arrhenius and Coffin-Manson layers and populates the `predicted_temp_field` and `drift_pct` metrics.

### 8.7 R-2 fallback (`fallback.py`)

If MPS training is unstable or the PINN diverges, swap in a scikit-learn `GradientBoostingRegressor` trained on the same synthetic data. Wrapper exposes the identical `__call__(x, t) -> np.ndarray` interface. Trigger: `APOLLO_PINN_FALLBACK=1` env var. The "PDE residual in the loss" pitch line is dropped; the rest of the system is unaffected (ADR-001 isolation property).

### 8.8 Acceptance criteria

- [ ] `test_pinn_pde_residual_low` — on a 100-point validation grid, mean squared PDE residual after training < 1e-3.
- [ ] `test_pinn_inference_latency` — 1000 inference calls, mean wall time < 5 ms on M3 Max CPU (NFR-3). Asserted with `pytest-benchmark`.
- [ ] `test_pinn_deterministic` — frozen weights produce byte-identical output for identical input across two CPU runs.
- [ ] `test_pinn_artifact_present` — `models/heater_pinn.pt` exists in the repo and loads without error.
- [ ] `test_pinn_fallback_loadable` — `APOLLO_PINN_FALLBACK=1` swaps the regressor cleanly; `step()` still returns a valid `EngineState`.
- [ ] `test_pinn_matches_finite_difference` — on three held-out driver traces, max abs error vs. finite-difference reference solver < 2 °C.

---

## 9. Workstream A5 — MAPIE conformal layer (FR-W.6, ADR-015)

### 9.1 Layout

```
src/engine/conformal/
    __init__.py
    wrapper.py         # MapieTimeSeriesRegressor wrapper per component
    residuals.py       # Residual storage + block-bootstrap utilities
    coverage_eval.py   # Empirical-coverage validator on Stressed scenario
data/
    conformal_residuals/
        <component_id>.npz   # Stored residuals, one file per component
```

### 9.2 Per-component wrapping

For every `ComponentId`, build a `MapieTimeSeriesRegressor(estimator=ComponentPredictor(c), method="enbpi", agg_function="mean", n_resamplings=20)`, where `ComponentPredictor(c)` is a thin sklearn-compatible adapter that calls the component's `intrinsic_decay` (rule-based) or the PINN (heater) over a horizon.

Calibration data: take the **last 2 hours** of the Barcelona-humid scenario from Plan B's historian as the calibration set. Block bootstrap with block size 30 simulated minutes (handles the cascade-onset autocorrelation ADR-015 calls out).

```python
# src/engine/conformal/wrapper.py
from mapie.regression import MapieTimeSeriesRegressor
from mapie.subsample import BlockBootstrap

class ConformalForecaster:
    def __init__(self, predictor, ci_level: float = 0.95):
        self.mapie = MapieTimeSeriesRegressor(
            estimator=predictor,
            method="enbpi",
            cv=BlockBootstrap(n_resamplings=20, length=30, overlapping=False, random_state=0),
        )
        self.alpha = 1.0 - ci_level

    def fit(self, X_calib: np.ndarray, y_calib: np.ndarray) -> "ConformalForecaster":
        self.mapie.fit(X_calib, y_calib)
        return self

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        y_pred, y_pis = self.mapie.predict(X, alpha=self.alpha)
        return y_pred, y_pis[:, 0, 0], y_pis[:, 1, 0]   # point, lower, upper
```

### 9.3 Horizon cap

`forecast(state, horizon_min)` rejects `horizon_min > 60` with `ValueError` (ADR-015). The Recharts shaded band on Plan C's UI is therefore guaranteed to live in a regime where calibration holds tightly.

### 9.4 Empirical-coverage test (the gate)

`tests/engine/conformal/test_coverage_stressed.py`:

1. Run the full engine on the Stressed scenario for 600 simulated minutes with seed=42.
2. At every minute `t`, emit a 30-minute-ahead forecast for every component → 6 × 600 = 3600 forecasts.
3. At minute `t + 30`, compare actual health to the forecast band.
4. Assert empirical coverage `≥ 0.90` on a 0.95 nominal CI for every component (per PRD §16.2).

This is the headline number Plan A reports back to the orchestrator at hour 13.

### 9.5 Acceptance criteria

- [ ] `test_conformal_returns_triple` — `forecast()` returns 6 `Forecast` rows with `lower ≤ point ≤ upper` for every horizon in 1..60.
- [ ] `test_conformal_horizon_cap` — `forecast(horizon_min=61)` raises `ValueError`.
- [ ] `test_conformal_band_widens_with_horizon` — for each component, `(upper - lower) at horizon=60` strictly greater than at horizon=10.
- [ ] `test_conformal_coverage_stressed_ge_0_90` — see §9.4. **This is the FR-W.6 gate.**
- [ ] `test_conformal_residuals_persisted` — `data/conformal_residuals/<component>.npz` exists for every component after `fit`.

---

## 10. Testing strategy

### 10.1 Pytest layout

```
tests/engine/
    test_mock_engine.py
    test_api.py                       # step / forecast / initial_state surface
    test_determinism_golden.py        # NFR-1 byte-compare gate
    test_latency_step.py              # NFR-2 < 50 ms gate
    test_latency_pinn.py              # NFR-3 < 5 ms gate
    failure_models/
        test_exponential.py
        test_weibull.py
        test_coffin_manson.py
        test_determinism.py
    components/
        test_blade.py
        test_motor.py
        test_nozzle.py
        test_resistor.py
        test_heater.py
        test_insulation.py
    cascades/
        test_csc_a.py
        test_csc_b.py
        test_csc_c.py
    pinn/
        test_pinn_latency.py
        test_pinn_residual.py
        test_pinn_deterministic.py
        test_pinn_artifact.py
        test_pinn_fallback.py
    conformal/
        test_wrapper.py
        test_coverage_stressed.py
golden/
    engine/
        stressed_seed42_t0_t600.jsonl   # one EngineState per minute, model_dump_json
```

### 10.2 Golden-file determinism (NFR-1)

`test_determinism_golden.py`:
```python
def test_stressed_seed42_byte_identical(tmp_path):
    out1 = run_full_scenario("stressed", seed=42, minutes=600)
    out2 = run_full_scenario("stressed", seed=42, minutes=600)
    assert out1 == out2                                      # same-process determinism
    golden = (Path("golden/engine/stressed_seed42_t0_t600.jsonl")).read_text()
    assert "\n".join(s.model_dump_json() for s in out1) == golden
```

Golden file is regenerated only when a deliberate engine change is merged; regen is a separate `make regen-golden` target so it cannot fire silently.

### 10.3 Latency benchmarks

- `test_latency_step.py` — `pytest-benchmark` measures `step()` over 1000 calls; assert mean < 50 ms (NFR-2).
- `test_latency_pinn.py` — `pytest-benchmark` over 1000 PINN inferences; assert mean < 5 ms (NFR-3).

Both benchmarks run in CI on the M3 Max dev box. If a different machine drops below these numbers, the CI job is permitted to skip the assertion but must emit a `WARNING` log; we do not block the build on hardware drift, but we never let an M3 Max regression sneak in.

### 10.4 Conformal coverage validation

`test_coverage_stressed.py` is the FR-W.6 gate (§9.4). Runs in `pytest -m slow`; ~30 s wall on M3 Max. CI runs it on every Plan A push.

### 10.5 Test commands

```bash
# Fast suite (every commit)
pytest tests/engine -m "not slow" -q

# Full suite (every push, every PR)
pytest tests/engine -q

# Latency benchmarks
pytest tests/engine/test_latency_step.py tests/engine/test_latency_pinn.py --benchmark-only

# Conformal coverage gate
pytest tests/engine/conformal/test_coverage_stressed.py -v
```

---

## 11. Hour-by-hour schedule (15 hours)

Plan A is on the critical path for Plans B and C. Step 0 ships the mock at hour 1 so they can build against it from minute 60.

| Hour | Workstream | Deliverable | Gate |
| --- | --- | --- | --- |
| **0–1** | Step 0 — mock | `src/engine/mock_engine.py` + `src/engine/contracts.py` + `tests/engine/test_mock_engine.py` committed. **Plans B/C unblocked.** | `pytest tests/engine/test_mock_engine.py` green |
| **1–2** | A1 | All three failure-model classes + their unit tests | `pytest tests/engine/failure_models -q` green |
| **2–4** | A2 | All 6 component modules with `intrinsic_decay` + `emit_metrics`. Heater stubs the PINN call until A4 lands. | `pytest tests/engine/components -q` green; Plans B/C switch import from mock to real for components 1–6 |
| **4–5** | A3 | `coupling.py` with literal `M`; CSC-A, CSC-B, CSC-C modules. CSC-B uses placeholder PINN until A4. | `pytest tests/engine/cascades -q` green |
| **5–6** | A2/A3 integration | `src/engine/api.py` real `step()` lands, replacing mock. Golden-file generated for the first time. | `pytest tests/engine/test_determinism_golden.py` green; Plans B/C now run on real engine |
| **6–9** | A4 | DeepXDE PDE definition, synthetic data generator, training script. Train on MPS. Freeze weights to `models/heater_pinn.pt`. CPU inference wrapper. | `pytest tests/engine/pinn -q` green; PINN latency < 5 ms |
| **9–10** | A4 wire-up | `HeatingElement` swapped from placeholder to real PINN; CSC-B reads PINN-predicted temp swing. Re-generate golden. | Re-run NFR-2 benchmark; full engine still < 50 ms / step |
| **10–11** | R-2 mitigation | `pinn/fallback.py` regressor surrogate trained on the same synthetic data. Fallback gated behind `APOLLO_PINN_FALLBACK=1`. | `APOLLO_PINN_FALLBACK=1 pytest tests/engine -q` green |
| **11–13** | A5 | MAPIE wrapper, residual storage, calibration on Barcelona-humid last 2 h, `forecast()` lands behind `src/engine/api.py`. | Coverage test runs and reports a number (gate validation in next slot) |
| **13–14** | A5 gate | Run `test_coverage_stressed.py`; tune block size if coverage < 0.90; **assert ≥ 0.90 on Stressed at 95 % nominal**. | `pytest tests/engine/conformal/test_coverage_stressed.py` green |
| **14–15** | Integration handoff | Final NFR-1/2/3 sweep. Update `apollo.engine.__version__`. Notify Plans B/C the final API is locked. Hand off the golden file. | All §13 verification commands return exit 0 |

R-1 (coupling tuning) mitigation is **continuous** across hours 4–15: every time the Stressed scenario's cascade timing looks off, retune `α_i` and matrix coefficients while keeping the `M` structure (sparsity pattern) fixed. R-2 (PINN instability) mitigation is the dedicated hour 10–11 block.

---

## 12. Risks & mitigations

PRD §19 risks owned by Plan A. **No risk is deferred — each carries scheduled mitigation work in §11.**

### R-1 — Coupling-matrix tuning produces unrealistic timing
- **Likelihood / impact:** Medium / Medium.
- **Detection:** Stressed scenario fails to push at least one component to FAILED within 600 simulated minutes, OR pushes more than three components to FAILED before minute 300, OR cascade ordering looks wrong (terminal component fails before its upstream cause).
- **Mitigation (scheduled hours 4–15, continuous):**
  1. Anchor every `α_i` to a literature-cited binder-jetting / additive-manufacturing wear range. Citations live in code comments referencing each component's failure family in ADR-006.
  2. Keep the **structure** of `M` fixed (the sparsity pattern from PRD §10.1 is non-negotiable). Only the magnitudes of the 6 non-zero entries are tunable.
  3. Tune one cascade at a time: drive its upstream component to a known low health, re-run the scenario, verify timing. Three sweeps of 20 minutes each is the time budget.
  4. Document final tuned coefficients in the technical report alongside the literature anchors.

### R-2 — PINN training unstable / slow
- **Likelihood / impact:** Medium / Medium.
- **Detection:** Training loss diverges or stalls, or final PDE residual on validation grid > 1e-2, or inference latency > 5 ms.
- **Mitigation (scheduled hour 10–11, dedicated):**
  1. Pre-train offline at hour 6–9 with a small model (4×64 — already minimal; ADR-005). If unstable, halve learning rate and double iterations.
  2. **Fallback:** `pinn/fallback.py` regressor surrogate trained on the **same** synthetic data. Identical `__call__(x, t)` interface. Activated by `APOLLO_PINN_FALLBACK=1`. Drops the PDE-residual pitch line; retains every other engine guarantee.
  3. The fallback is wired and tested at hour 10–11 even if the PINN trains successfully. We never ship without the fallback path verified.

---

## 13. Definition of done

The plan is complete when **every** checkbox below is green.

### 13.1 Functional requirements

- [ ] **FR-1.1** — six components, three subsystems, two per subsystem.
  Verify: `pytest tests/engine/test_api.py::test_initial_state_six_components`
- [ ] **FR-1.2** — each component consumes ≥ 1 driver and changes state in response.
  Verify: `pytest tests/engine/components -k driver_dependent_change`
- [ ] **FR-1.3** — three failure-model families, each unit-tested with known-input/known-output.
  Verify: `pytest tests/engine/failure_models -q`
- [ ] **FR-1.4** — Pydantic State Report with `health ∈ [0,1]`, `status ∈ ComponentStatus`, metrics dict.
  Verify: `pytest tests/engine/test_api.py::test_state_report_schema`
- [ ] **FR-1.5** — bit-identical determinism for identical inputs.
  Verify: `pytest tests/engine/test_determinism_golden.py`
- [ ] **FR-1.6** — linear coupling matrix `M`, update rule per PRD §10.1.
  Verify: `pytest tests/engine/cascades -q && pytest tests/engine/test_api.py::test_coupling_matrix_literal`
- [ ] **FR-1.7** — DeepXDE PINN for heater, frozen artifact, CPU inference < 5 ms, PDE-residual pitch defensible.
  Verify: `pytest tests/engine/pinn -q`
- [ ] **FR-1.8** — single `step(state, drivers, dt) -> state` interface.
  Verify: `pytest tests/engine/test_api.py::test_step_signature_stable`
- [ ] **FR-W.6** — MAPIE conformal, ≥ 90 % empirical coverage on Stressed at 95 % nominal.
  Verify: `pytest tests/engine/conformal/test_coverage_stressed.py -v`

### 13.2 Non-functional requirements

- [ ] **NFR-1** — determinism gate. Verify: `pytest tests/engine/test_determinism_golden.py`
- [ ] **NFR-2** — `step()` < 50 ms / call on M3 Max CPU. Verify: `pytest tests/engine/test_latency_step.py --benchmark-only`
- [ ] **NFR-3** — PINN inference < 5 ms / call on M3 Max CPU. Verify: `pytest tests/engine/test_latency_pinn.py --benchmark-only`

### 13.3 Integration handoff

- [ ] `src/engine/api.py` exposes exactly `step`, `forecast`, `initial_state` and nothing else as a public surface.
- [ ] `src/engine/contracts.py` exposes exactly `ComponentId`, `ComponentStatus`, `ComponentState`, `Drivers`, `EngineState`, `Forecast`, `status_for_health`.
- [ ] `models/heater_pinn.pt` is committed and < 1 MB.
- [ ] `apollo.engine.__version__ == "1.0.0"` set in `src/engine/__init__.py`.
- [ ] Plan B confirms its simulation loop runs against the real engine for all three scenarios × three policies (9 runs).
- [ ] Plan C confirms its `compare_runs` and `run_counterfactual` tools call `step()` and `forecast()` without errors.
- [ ] Golden file `golden/engine/stressed_seed42_t0_t600.jsonl` checked in.

### 13.4 Single end-to-end verification command

```bash
pytest tests/engine -q --benchmark-only=false \
  && pytest tests/engine/conformal/test_coverage_stressed.py -v \
  && pytest tests/engine/test_latency_step.py tests/engine/test_latency_pinn.py --benchmark-only
```

When this command exits 0 on the M3 Max, Plan A is done.

---

## 14. DDD compliance

### 14.1 Authoritative ADR

The binding source for the bounded-context structure of Plan A's work is [`ADR-021 — DDD module structure with three bounded contexts`](../adr/ADR-021-domain-driven-design-module-structure.md). This section is a quick reference, not a redefinition: every claim below restates ADR-021 in the local context of the Engine bounded context. If this section drifts from ADR-021, ADR-021 wins; deviation requires a new superseding ADR, not an in-place edit.

### 14.2 Bounded context owned

- **Name:** Engine.
- **Directory:** `src/engine/`.
- **Responsibility:** Pure-compute physics. Component decay, the 6×6 coupling matrix `M`, the three named cascades, the DeepXDE PINN for the heater, and the MAPIE conformal layer wrapping every per-component predictor. Owns no repositories — Plan A is stateless across `step()` invocations except for the seeded RNG threaded through `EngineState.rng_state`.
- **Local ubiquitous language (per ADR-021):** Component, Subsystem, Cascade, Health, Status, Driver, Forecast. These terms are the only domain vocabulary Plan A code introduces; everything else lives in Plan B or Plan C's bounded context.
- **Published language:** `src/engine/contracts.py` and the three-symbol `src/engine/api.py` surface (§3.2). Anything not exported through these two files is implementation detail and not visible to other contexts.

### 14.3 Aggregate roots

Plan A owns exactly one aggregate root.

| Aggregate | Pydantic embodiment | Invariants enforced by the aggregate |
| --- | --- | --- |
| `EngineState` | `EngineState` (§3.1) | Cascade transitions go through `step()`, never by mutating `ComponentState` instances directly (Pydantic `frozen=True` enforces this); per-component `health ∈ [0, 1]` (Pydantic `Field(ge=0.0, le=1.0)`); `status` derives deterministically from `health` via the shared `status_for_health` helper (§6.4) so threshold drift is impossible; `coupling_matrix` retains the ADR-004 sparsity pattern (asserted by `test_coupling_matrix_literal` in §7.4); `rng_state` is serializable (NFR-1, ADR-012). |

`ComponentState`, `Drivers`, `Forecast` are part of the aggregate's exposed surface but are themselves value objects (§14.4) — they have no identity and are never mutated.

### 14.4 Entities vs. value objects

Classification of every Pydantic model in `src/engine/contracts.py` (the §3 frozen contracts of this plan):

| Pydantic model | Classification | Reason |
| --- | --- | --- |
| `ComponentId` | Value Object (enum) | Identity is its string value; no lifecycle. Lives in the shared kernel. |
| `ComponentStatus` | Value Object (enum) | Discrete state; no identity beyond value. Shared kernel. |
| `ComponentState` | Value Object | `frozen=True`; identified by `(component_id, health, status, metrics)` tuple, not by a separate identity. New step ⇒ new value. |
| `Drivers` | Value Object | `frozen=True`; pure exogenous input; replaceable wholesale per tick. |
| `Forecast` | Value Object | `frozen=True`; immutable triple `(point, lower, upper)` plus metadata; no lifecycle. |
| `EngineState` | **Aggregate Root** | Composes the six `ComponentState` value objects, the coupling matrix, and `rng_state`. The transition function `step()` is the only legitimate mutator. |

Plan A defines **no entities** — there is no per-component identity that survives across ticks beyond the `ComponentId` value. A `ComponentState` at `t = 0` is a different value from the same component's state at `t = 1`; the `EngineState` aggregate root carries the through-time identity.

### 14.5 Domain services

Stateless service functions that orchestrate the aggregate. All three live behind `src/engine/api.py`; they are the only functions outside `src/engine/` may import (per §3.2).

- `step(state, drivers, dt) -> EngineState` — advances every component for `dt` simulated minutes; composes intrinsic decay, matrix coupling, and the explicit CSC-B physics layer. FR-1.8.
- `forecast(state, horizon_min) -> list[Forecast]` — wraps each component predictor in MAPIE EnbPi block-bootstrap; rejects `horizon_min > 60` (ADR-015 cap). FR-W.6.
- `initial_state(scenario, seed) -> EngineState` — constructs a fresh `EngineState` with all 6 components at `health = 1.0`, coupling matrix loaded from PRD §10.1, and seeded RNG.

The cascade composition (CSC-A matrix-only, CSC-B Arrhenius + Coffin-Manson on top of `M`, CSC-C matrix-only) is itself a domain service inside `src/engine/cascades/`, invoked by `step()` after intrinsic decay and before clamping to `[0, 1]`.

### 14.6 Repositories

**None.** The Engine context is pure compute (per ADR-021 "Decision" §4 "Repository abstractions"). It owns no persistence. The `models/heater_pinn.pt` artifact is a frozen weights file checked into the repo, not a repository in the DDD sense — it is loaded once at startup by the inference wrapper and is immutable thereafter.

Plan B's `HistorianRepository` and `RetrievalIndex` are the only repositories in the system, both inside the Simulation bounded context.

### 14.7 Domain events

Subset of the master event list (PLAN.md §9.7) emitted or consumed by Plan A:

- **Emitted:**
  - `ComponentDegraded` — emitted whenever a `ComponentState.status` transitions from FUNCTIONAL to DEGRADED inside `step()`.
  - `ComponentFailed` — emitted on transition to FAILED. Plan B's simulation loop observes this and triggers obituary generation per FR-W.4.
  - `CascadeTriggered` — emitted by the CSC-A/B/C composition when an upstream component crosses the trigger threshold for downstream coupling.
- **Consumed:** none. Plan A is upstream of every other context; events flow outward only.

### 14.8 Anti-corruption layer responsibilities

The Engine context guards against one specific corruption: **bare string component names crossing the `contracts.py` boundary.** The risk is real — every consumer (Plan B's historian, Plan C's citation validator) keys data on `(run_id, component_id, t)`, so a string-vs-enum drift would silently break joins, citation resolution, and the architecture test in §9.8 of the master plan.

Plan A's enforcement:

- `ComponentId` is an `Enum` subclass of `str`, defined exactly once in `src/engine/contracts.py`. Re-defining it elsewhere is a circular-import bug.
- Every Pydantic model that names a component uses the enum, never `str`.
- The `metrics` dict on `ComponentState` is keyed by free-form metric names (`blade_thickness_mm`, `current_draw_A`, …), not component names — there is no place for a stray component string inside the aggregate.
- The architecture test (`tests/architecture/test_no_string_components.py`, see §14.9) greps `src/` for string literals matching the six component names and fails CI if any are found outside the enum definition or test fixtures.

### 14.9 Ubiquitous-language enforcement

The lint/test rule for this plan is `tests/architecture/test_no_string_components.py`. It is a pytest module that:

1. Walks `src/` and parses every `.py` file.
2. For each string literal in the AST, asserts its value is not in `{"blade", "motor", "nozzle", "resistor", "heater", "insulation"}` unless the file is `src/engine/contracts.py` (the enum definition itself) or under `tests/`.
3. Fails the build with the file + line of any offender.

Plan A's other verification commands relevant to ubiquitous-language consistency:

- `pytest tests/engine/test_api.py::test_state_report_schema` — confirms the published Pydantic surface matches the `contracts.py` definitions byte-for-byte.
- `pytest tests/engine/test_determinism_golden.py` — ensures the aggregate's `model_dump_json()` is stable across runs; a vocabulary drift would break the byte-compare.

These three commands collectively validate that Plan A's published language stays the language ADR-021 defines.
