"""Component registry — PLAN-A §6.

Each entry maps a `ComponentId` to a singleton instance (deterministic
construction, NFR-1). The registry is the canonical iteration surface
for `engine.api.step()` — Plans B/C never construct components.
"""

from __future__ import annotations

from typing import Dict

from engine.components.base import Component
from engine.components.blade import RecoaterBlade
from engine.components.heater import HeatingElement
from engine.components.insulation import InsulationPanel
from engine.components.motor import DriveMotor
from engine.components.nozzle import NozzlePlate
from engine.components.resistor import ThermalFiringResistors
from engine.contracts import ComponentId, ROW_ORDER


def build_components() -> Dict[ComponentId, Component]:
    """Construct one instance per component, in `ROW_ORDER`."""
    return {
        ComponentId.BLADE:      RecoaterBlade(),
        ComponentId.MOTOR:      DriveMotor(),
        ComponentId.NOZZLE:     NozzlePlate(),
        ComponentId.RESISTOR:   ThermalFiringResistors(),
        ComponentId.HEATER:     HeatingElement(),
        ComponentId.INSULATION: InsulationPanel(),
    }


__all__ = [
    "Component",
    "RecoaterBlade",
    "DriveMotor",
    "NozzlePlate",
    "ThermalFiringResistors",
    "HeatingElement",
    "InsulationPanel",
    "build_components",
    "ROW_ORDER",
]
