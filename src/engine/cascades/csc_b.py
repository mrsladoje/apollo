"""CSC-B — Thermal-Printhead loop (matrix + explicit physics) — PLAN-A §7.3.

The demo showpiece. On top of `M[heater, insulation]=0.5`,
`M[nozzle, heater]=0.3`, `M[resistor, heater]=0.2`,
`M[resistor, nozzle]=0.1`, this module adds explicit physics:

  - Arrhenius binder viscosity     mu(T) = mu_ref * exp(Ea/R * (1/T - 1/T_ref))
  - Coffin-Manson cycle damage     N_f = C * (alpha_TC * delta_T)^(-c)

Citations (ADR-003, ADR-006):
  Ea/R = 4500 K           -- PEG/PVP-class AM polymer binders
                             (Han et al. 2020, DOI:10.1002/adfm.202003062)
  alpha_TC = 1.5e-5 / K   -- thermal expansion of refractory thin-film
                             (CRC Handbook 97th ed., Lau IEEE CPMT 1996)
  C = 1e6, c = 2.0        -- Coffin-Manson IS&T Print4Fab 2020 thin-film range

The csc-B contributions are layered AFTER the matrix coupling to avoid
double-counting; magnitudes are calibrated so the explicit physics
provides a small, visible accelerator rather than dominating the matrix.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from engine.contracts import ComponentId, ROW_ORDER

# Arrhenius constants
EA_OVER_R: float = 4500.0       # Kelvin (Han et al. 2020)
T_REF_K: float = 298.15
MU_REF: float = 1.0             # normalized; absolute units do not matter

# Coffin-Manson constants
ALPHA_TC: float = 1.5e-5        # 1/K
C_CM: float = 1.0e6
C_EXP: float = 2.0

# Per-step accelerator scales — calibrated so explicit physics adds
# a measurable but non-dominant contribution on top of M (R-1 §12).
NOZZLE_VISCOSITY_SCALE: float = 5.0e-4
RESISTOR_FATIGUE_SCALE: float = 5.0e-4

_NOZZLE_IDX: int = ROW_ORDER.index(ComponentId.NOZZLE)
_RESISTOR_IDX: int = ROW_ORDER.index(ComponentId.RESISTOR)


def binder_viscosity(temp_C: float) -> float:
    """Arrhenius binder-cling factor. Returns mu(T) / mu_ref (dimensionless).

    Sign convention: the demo cascade in PRD §10.2 narrates "enclosure temp
    rises -> binder viscosity rises -> nozzle clog rises", and PLAN-A §7.4's
    `test_csc_b_arrhenius_monotone` asserts mu(50) > mu(30). We therefore
    use the positive form `exp(Ea/R * (1/T_ref - 1/T))` so cling/clog risk
    grows monotonically with temperature; this is the textbook Arrhenius
    rate-form rather than the textbook (decreasing) viscosity Arrhenius.
    """
    T_K = float(temp_C) + 273.15
    return MU_REF * math.exp(EA_OVER_R * (1.0 / T_REF_K - 1.0 / T_K))


def coffin_manson_damage(delta_T: float, cycles: float) -> float:
    """Per-step damage fraction = cycles / N_f. cycles >= 0, delta_T >= 0."""
    if cycles <= 0.0 or delta_T <= 0.0:
        return 0.0
    delta_eps = ALPHA_TC * float(delta_T)
    N_f = C_CM * (delta_eps ** -C_EXP)
    return float(cycles) / N_f


def _viscosity_excess(temp_C: float) -> float:
    """How much viscosity exceeds the reference; clipped at 0."""
    return max(0.0, binder_viscosity(temp_C) - 1.0)


def apply_csc_b(
    healths: np.ndarray,
    *,
    heater_temp_swing_K: float,
    enclosure_temp_C: float,
    duty_cycles_this_step: float,
    dt: float,
) -> np.ndarray:
    """Layer CSC-B explicit physics on top of matrix-coupled `healths`.

    Inputs:
      heater_temp_swing_K      -- max-min of the PINN-predicted T(x, t) field
      enclosure_temp_C         -- ambient seen by the printhead this step
      duty_cycles_this_step    -- nominal firing cycles in `dt` minutes
    Output: a new (6,) array, clamped to [0, 1].

    The contribution to nozzle health is viscosity-driven; to resistor health
    it is Coffin-Manson thermal fatigue. Heater itself decays via its own
    Coffin-Manson layer in `engine.components.heater` so we do NOT touch
    healths[heater] here.
    """
    out = np.array(healths, dtype=np.float64, copy=True)

    nozzle_dH = -_viscosity_excess(enclosure_temp_C) * NOZZLE_VISCOSITY_SCALE * dt
    out[_NOZZLE_IDX] = max(0.0, min(1.0, out[_NOZZLE_IDX] + nozzle_dH))

    damage = coffin_manson_damage(heater_temp_swing_K, duty_cycles_this_step)
    resistor_dH = -damage * RESISTOR_FATIGUE_SCALE * dt
    out[_RESISTOR_IDX] = max(0.0, min(1.0, out[_RESISTOR_IDX] + resistor_dH))

    return out


def csc_b_inputs_from(
    drivers_temp_C: float,
    pinn_temp_field: np.ndarray,
    duty_cycles_per_min: float,
    dt: float,
) -> Tuple[float, float, float]:
    """Convenience packer for `step()`: derive (swing_K, ambient_C, cycles)."""
    swing = float(np.max(pinn_temp_field) - np.min(pinn_temp_field))
    return swing, float(drivers_temp_C), float(duty_cycles_per_min * dt)


__all__ = [
    "EA_OVER_R",
    "T_REF_K",
    "ALPHA_TC",
    "C_CM",
    "C_EXP",
    "binder_viscosity",
    "coffin_manson_damage",
    "apply_csc_b",
    "csc_b_inputs_from",
]
