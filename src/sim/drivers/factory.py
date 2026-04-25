from __future__ import annotations

from sim.config import SimulationConfig

from .base import DriverProvider
from .composite import CompositeDriverProvider


def build_drivers(cfg: SimulationConfig) -> DriverProvider:
    """Build the deterministic driver provider for a simulation config.

    PLAN-B keeps demo execution offline: the composite provider reads cached
    weather/air CSVs when present and uses deterministic synthetic providers
    otherwise. The factory is the single wiring point for future live providers.
    """
    return CompositeDriverProvider()


__all__ = ["build_drivers"]
