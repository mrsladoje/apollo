"""Insulation Panel — PLAN-A §6.3 row 6, ADR-006 (exponential k_eff decay).

Drivers: cumulative heat exposure (temp_C integral), hours.
Metric: k_eff_W_mK.

Parameter anchor (ADR-006):
- Exponential decay rate alpha = 5e-5 / h ~ 8.3e-7 / min for refractory
  ceramic-fiber insulation aging (NASA TM-100255, Liu 2024 PMC11124260).
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from engine.components.base import Component
from engine.contracts import ComponentId, ComponentState, Drivers
from engine.failure_models import ExponentialDecay


class InsulationPanel(Component):
    component_id = ComponentId.INSULATION
    intrinsic_alpha: float = 5e-5 / 60.0  # 5e-5 / h converted to 1/min

    k_eff_init_W_mK: float = 0.05  # ceramic-fiber typical
    temp_ref_C: float = 25.0
    temp_scale_K: float = 50.0     # how fast stress grows above ambient

    def __init__(self) -> None:
        self._exp = ExponentialDecay()

    def _stress(self, drivers: Drivers) -> float:
        # Heat exposure stress grows linearly above ambient; clipped at 0
        # below ambient because cooling does not age refractory fiber.
        delta_T = max(0.0, drivers.temp_C - self.temp_ref_C)
        return delta_T / self.temp_scale_K

    def intrinsic_decay(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        return self._exp.decay(
            state.health,
            {"alpha": self.intrinsic_alpha, "stress": self._stress(drivers)},
            dt,
            rng,
        )

    def emit_metrics(
        self,
        state: ComponentState,
        drivers: Drivers,
    ) -> Dict[str, float]:
        return {
            "k_eff_W_mK": float(self.k_eff_init_W_mK * state.health),
        }


__all__ = ["InsulationPanel"]
