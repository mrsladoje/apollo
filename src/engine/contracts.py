"""Frozen integration contracts for the Engine bounded context.

Source of truth: PLAN-A §3.1 (Pydantic surface), §6.4 (status thresholds),
§7.1 (coupling matrix literal). Plans B and C import from this module —
breaking changes require the §3 handshake.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Canonical 6-component identity (PLAN-A §3.1, ADR-002)
# ---------------------------------------------------------------------------

class ComponentId(str, Enum):
    BLADE = "blade"
    MOTOR = "motor"
    NOZZLE = "nozzle"
    RESISTOR = "resistor"
    HEATER = "heater"
    INSULATION = "insulation"


class ComponentStatus(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"  # health >= 0.7
    DEGRADED = "DEGRADED"      # 0.4 <= health < 0.7
    CRITICAL = "CRITICAL"      # 0.1 <= health < 0.4
    FAILED = "FAILED"          # health < 0.1


# Row order for the 6x6 coupling matrix (PLAN-A §7.1).
ROW_ORDER: tuple[ComponentId, ...] = (
    ComponentId.BLADE,
    ComponentId.MOTOR,
    ComponentId.NOZZLE,
    ComponentId.RESISTOR,
    ComponentId.HEATER,
    ComponentId.INSULATION,
)


def status_for_health(h: float) -> ComponentStatus:
    """PLAN-A §6.4 — single source of truth for the health→status mapping.

    Plan C's citation validator imports the same helper to avoid threshold drift.
    """
    if h >= 0.7:
        return ComponentStatus.FUNCTIONAL
    if h >= 0.4:
        return ComponentStatus.DEGRADED
    if h >= 0.1:
        return ComponentStatus.CRITICAL
    return ComponentStatus.FAILED


# ---------------------------------------------------------------------------
# Coupling matrix literal (PLAN-A §7.1, ADR-004)
# ---------------------------------------------------------------------------

# 6x6 matrix, row order == ROW_ORDER. Sparsity pattern is non-negotiable;
# only the magnitudes of the non-zero entries are tunable (PLAN-A R-1).
COUPLING_MATRIX_M: tuple[tuple[float, ...], ...] = (
    # blade  motor  nozzle resist heater insul
    (0.0,   0.0,   0.0,   0.0,   0.0,   0.0),    # blade
    (0.4,   0.0,   0.0,   0.0,   0.0,   0.0),    # motor       <- CSC-A
    (0.2,   0.0,   0.0,   0.0,   0.3,   0.0),    # nozzle      <- CSC-C, CSC-B
    (0.0,   0.0,   0.1,   0.0,   0.2,   0.0),    # resistor    <- CSC-B
    (0.0,   0.0,   0.0,   0.0,   0.0,   0.5),    # heater      <- CSC-B
    (0.0,   0.0,   0.0,   0.0,   0.0,   0.0),    # insulation
)


# ---------------------------------------------------------------------------
# State Report (FR-1.4, PLAN-A §3.1)
# ---------------------------------------------------------------------------

class ComponentState(BaseModel):
    model_config = ConfigDict(frozen=True)

    component_id: ComponentId
    health: float = Field(ge=0.0, le=1.0)
    status: ComponentStatus
    metrics: dict[str, float]


# ---------------------------------------------------------------------------
# Driver vector (PRD §9.2, FR-1.2)
# ---------------------------------------------------------------------------

class Drivers(BaseModel):
    model_config = ConfigDict(frozen=True)

    temp_C: float
    humidity: float                              # 0..1 relative humidity
    pm25: float                                  # ug/m^3
    psd_d50: float                               # micrometers
    voltage_stability: float                     # 0..1, 1.0 = perfectly stable
    cycles: int                                  # cumulative print cycles
    hours: float                                 # cumulative operating hours
    maintenance_level: dict[ComponentId, float]  # 0..1, 1.0 = freshly maintained
    operator_shift: Literal["day", "night", "weekend"]
    rng_seed: int


# ---------------------------------------------------------------------------
# World state (FR-1.4, FR-1.6)
# ---------------------------------------------------------------------------

class EngineState(BaseModel):
    model_config = ConfigDict(frozen=True)

    components: dict[ComponentId, ComponentState]
    coupling_matrix: list[list[float]]  # 6x6, row order == ROW_ORDER
    rng_state: tuple                    # serialized np.random.Generator state


# ---------------------------------------------------------------------------
# Conformal forecast triple (FR-W.6, ADR-015)
# ---------------------------------------------------------------------------

class Forecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    component_id: ComponentId
    horizon_min: int   # 1..60 (cap per ADR-015, enforced by forecast())
    point: float
    lower: float
    upper: float
    ci_level: float    # nominal coverage, default 0.95


__all__ = [
    "ComponentId",
    "ComponentStatus",
    "ROW_ORDER",
    "status_for_health",
    "COUPLING_MATRIX_M",
    "ComponentState",
    "Drivers",
    "EngineState",
    "Forecast",
]
