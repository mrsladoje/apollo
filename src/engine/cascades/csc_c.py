"""CSC-C — Powder contamination loop (matrix-only) — PLAN-A §7.3, ADR-003.

`M[nozzle, blade] = 0.2`. Blade ceramic flaking -> powder contamination ->
nozzle clog. Matrix-only; no extra ODE.
"""

from __future__ import annotations

CSC_C_NAME: str = "CSC-C"
CSC_C_DESCRIPTION: str = (
    "Blade ceramic flaking -> powder contamination -> nozzle clog acceleration. "
    "Matrix-only via M[nozzle, blade] = 0.2 (PRD §10.1, ADR-003)."
)


__all__ = ["CSC_C_NAME", "CSC_C_DESCRIPTION"]
