"""1-D heat-diffusion PDE definition — PLAN-A §8.2 / ADR-005.

  Domain:   x in [0, L_ROD], t in [0, T_MAX]
  PDE:      dT/dt = kappa * d^2 T/dx^2
  BCs:      T(0, t) = 1.0       -- inner-wall (heater hot side, normalized)
            T(L, t) = 0.0       -- ambient
  IC:       T(x, 0) = 1.0 - x/L -- linear preheat profile

The kappa value is the NiCr-class refractory diffusivity from
ADR-006 §"Parameter ranges and citations" (CRC Handbook 97th ed.).
We work in normalized temperature [0, 1]; the inference wrapper
rescales to (T_ambient, T_duty) at runtime.
"""

from __future__ import annotations

KAPPA: float = 5e-6      # m^2/s -- NiCr-class (CRC Handbook 97th ed.)
L_ROD: float = 0.05      # m
T_MAX_S: float = 60.0    # one-minute duty pulse


__all__ = ["KAPPA", "L_ROD", "T_MAX_S"]
