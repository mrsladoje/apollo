"""Nozzle Plate — PLAN-A §6.3 row 3, ADR-006 (Weibull clog).

Drivers: humidity (binder viscosity proxy), temp_C, pm25.
Metrics: clog_prob, active_nozzle_count.

Parameter anchors (ADR-006):
- Weibull beta = 2.5 (TIJ printhead clog time-to-event, IS&T Print4Fab 2020).
- eta calibrated in minutes; humidity, temperature, and PM2.5 multiplicatively
  accelerate the effective time per the binder-viscosity / contamination
  phenomenology described in CSC-B (PLAN-A §7.3, ADR-003).
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from engine.components.base import Component
from engine.contracts import ComponentId, ComponentState, Drivers
from engine.failure_models import WeibullDecay


class NozzlePlate(Component):
    component_id = ComponentId.NOZZLE
    intrinsic_alpha: float = 1.0

    beta: float = 2.5
    eta_min: float = 8.0e4
    humidity_accel: float = 4.0
    pm25_accel_per_ugm3: float = 0.02
    temp_accel_per_K: float = 0.04
    nozzle_count_init: int = 1024

    def __init__(self) -> None:
        self._weib = WeibullDecay()

    def _accel(self, drivers: Drivers) -> float:
        h = max(0.0, min(1.0, drivers.humidity))
        humidity_factor = 1.0 + self.humidity_accel * h
        pm_factor = 1.0 + self.pm25_accel_per_ugm3 * max(0.0, drivers.pm25)
        # Binder viscosity rises with temp drop; heater-driven enclosure
        # warming likewise drives it up. Use absolute deviation from 25 degC.
        temp_factor = 1.0 + self.temp_accel_per_K * abs(drivers.temp_C - 25.0)
        return humidity_factor * pm_factor * temp_factor

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
        clog_prob = max(0.0, min(1.0, 1.0 - state.health))
        active = int(round(self.nozzle_count_init * state.health))
        return {
            "clog_prob": float(clog_prob),
            "active_nozzle_count": float(active),
        }


__all__ = ["NozzlePlate"]
