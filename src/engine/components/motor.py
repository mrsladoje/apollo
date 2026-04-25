"""Drive Motor — PLAN-A §6.3 row 2, ADR-006 (Weibull bearing fatigue).

Drivers: voltage_stability, cycles, plus matrix coupling from blade
(M[motor, blade] = 0.4) added by `engine.api.step()`.
Metrics: current_draw_A, bearing_temp_C.

Parameter anchors (ADR-006):
- Weibull beta = 1.5 (rolling-element bearings, ISO 281:2007 L10 convention).
- eta = 2000 h literature anchor; we operate in minutes and apply a
  voltage-instability acceleration factor on top so a 600-min run shows
  a measurable cascade without contradicting the L10 baseline.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from engine.components.base import Component
from engine.contracts import ComponentId, ComponentState, Drivers
from engine.failure_models import WeibullDecay


class DriveMotor(Component):
    component_id = ComponentId.MOTOR
    intrinsic_alpha: float = 1.0  # absorbed into the Weibull form below

    beta: float = 1.5
    eta_min: float = 2000.0 * 60.0  # 2000 h converted to minutes
    voltage_accel: float = 6.0      # multiplier when voltage is fully unstable
    cycle_accel_per_kcycle: float = 0.4

    def __init__(self) -> None:
        self._weib = WeibullDecay()

    def _accel(self, drivers: Drivers) -> float:
        instab = 1.0 - max(0.0, min(1.0, drivers.voltage_stability))
        cycle_factor = 1.0 + (drivers.cycles / 1000.0) * self.cycle_accel_per_kcycle
        return (1.0 + self.voltage_accel * instab) * cycle_factor

    def intrinsic_decay(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        t_min = max(1.0, drivers.hours * 60.0)
        dh = self._weib.decay(
            state.health,
            {"beta": self.beta, "eta": self.eta_min, "t": t_min},
            dt,
            rng,
        )
        return dh * self._accel(drivers)

    def emit_metrics(
        self,
        state: ComponentState,
        drivers: Drivers,
    ) -> Dict[str, float]:
        load = 1.0 - state.health
        return {
            "current_draw_A": float(5.0 + 4.0 * load),
            "bearing_temp_C": float(60.0 + 50.0 * load + 0.4 * drivers.temp_C),
        }


__all__ = ["DriveMotor"]
