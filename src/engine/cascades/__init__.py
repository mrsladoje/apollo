"""Three cascades — PLAN-A §7.3 / ADR-003.

CSC-A and CSC-C ride matrix-only (handled by `engine.coupling.apply_coupling`).
CSC-B layers explicit physics (Arrhenius binder viscosity + Coffin-Manson
thermal fatigue) on top of the matrix; this package owns it.
"""

from engine.cascades.csc_b import (
    apply_csc_b,
    binder_viscosity,
    coffin_manson_damage,
)

__all__ = [
    "apply_csc_b",
    "binder_viscosity",
    "coffin_manson_damage",
]
