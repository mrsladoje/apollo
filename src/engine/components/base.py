"""Component abstract base — PLAN-A §6.2 / FR-1.8.

All six concrete components share `intrinsic_decay(state, drivers, dt, rng) -> dH`
and `emit_metrics(state, drivers) -> dict[str, float]`. The cascade composer
in `engine.api.step()` adds matrix coupling on top of `intrinsic_decay`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

import numpy as np

from engine.contracts import ComponentId, ComponentState, Drivers


class Component(ABC):
    component_id: ComponentId
    intrinsic_alpha: float

    @abstractmethod
    def intrinsic_decay(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        """Return -alpha_i * f(drivers_i) * dt as dH (<= 0)."""

    @abstractmethod
    def emit_metrics(
        self,
        state: ComponentState,
        drivers: Drivers,
    ) -> Dict[str, float]:
        """Recompute the component-specific metrics dict for this step."""


__all__ = ["Component"]
