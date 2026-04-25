"""Thermal Firing Resistors — PLAN-A §6.3 row 4, ADR-006 (Coffin-Manson).

Drivers: cycles_this_step (duty), temp_C, voltage_stability.
Metric: resistance_pct.

Parameter anchors (ADR-006):
- Coffin-Manson exponent c = 2.0 (range 1.9-2.5, IS&T Print4Fab 2020 thin-film).
- Constant C = 1e6 cycles*eps^c (synthetic, order-of-magnitude consistent
  with thin-film TIJ heater Coffin-Manson curves).
- Thermal expansion alpha_TC = 1e-5 / K (CRC Handbook, refractory thin film).
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from engine.components.base import Component
from engine.contracts import ComponentId, ComponentState, Drivers
from engine.failure_models import CoffinManson


class ThermalFiringResistors(Component):
    component_id = ComponentId.RESISTOR
    intrinsic_alpha: float = 1.0

    cm_C: float = 1.0e6
    cm_c: float = 2.0
    alpha_tc: float = 1.0e-5      # thermal expansion coefficient (1/K)
    delta_T_ref_K: float = 80.0   # nominal pulse swing per firing
    duty_cycles_per_min: float = 60.0  # one firing per second under nominal duty
    voltage_jitter_factor: float = 1.5

    def __init__(self) -> None:
        self._cm = CoffinManson()

    def _delta_eps(self, drivers: Drivers) -> float:
        # Pulse temperature swing biased by ambient temp and voltage stability.
        instab = 1.0 - max(0.0, min(1.0, drivers.voltage_stability))
        amb_factor = 1.0 + 0.01 * (drivers.temp_C - 25.0)
        delta_T = self.delta_T_ref_K * amb_factor * (1.0 + self.voltage_jitter_factor * instab)
        return self.alpha_tc * max(1.0, delta_T)

    def _cycles(self, drivers: Drivers, dt: float) -> float:
        return self.duty_cycles_per_min * dt

    def intrinsic_decay(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        cycles = self._cycles(drivers, dt)
        return self._cm.decay(
            state.health,
            {
                "C": self.cm_C,
                "c": self.cm_c,
                "delta_eps": self._delta_eps(drivers),
                "cycles_this_step": cycles,
            },
            dt,
            rng,
        )

    def emit_metrics(
        self,
        state: ComponentState,
        drivers: Drivers,
    ) -> Dict[str, float]:
        return {
            "resistance_pct": float(100.0 - 30.0 * (1.0 - state.health)),
        }


__all__ = ["ThermalFiringResistors"]
