"""Failure-model abstract base — PLAN-A §5.2 / ADR-006.

Models are pure-math callables. Per §5.3 the parameters (alpha, beta, eta,
C, c, delta_eps) live in `src/engine/components/<comp>.py`; this module
only defines the shared `decay(health, drivers, dt, rng) -> dH` signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping

import numpy as np


class FailureModel(ABC):
    """Shared signature for ExponentialDecay, WeibullDecay, CoffinManson.

    Implementations must be pure functions of `(health, drivers, dt)` plus
    any `rng` draws. dH is non-positive (decay never improves health).
    """

    @abstractmethod
    def decay(
        self,
        health: float,
        drivers: Mapping[str, float],
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        """Return dH (<= 0). Components clamp the resulting health to [0, 1]."""


__all__ = ["FailureModel"]
