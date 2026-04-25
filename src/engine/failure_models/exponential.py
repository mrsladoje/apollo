"""Exponential decay — PLAN-A §5.3 / ADR-006.

Differential form `dH = -alpha * stress * H * dt`.
Used by Recoater Blade (height loss, Archard k=1e-6) and Insulation Panel
(k_eff loss, alpha=5e-5/h). Reference ranges: ADR-006 parameter table.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from engine.failure_models.base import FailureModel


class ExponentialDecay(FailureModel):
    def decay(
        self,
        health: float,
        drivers: Mapping[str, float],
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        alpha = float(drivers["alpha"])
        stress = float(drivers["stress"])
        if stress == 0.0:
            return 0.0
        return -alpha * stress * health * dt


__all__ = ["ExponentialDecay"]
