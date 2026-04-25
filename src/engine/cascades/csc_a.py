"""CSC-A — Recoating loop (matrix-only) — PLAN-A §7.3, ADR-003.

`M[motor, blade] = 0.4`. As blade health drops, motor decay accelerates via
the matrix term; no additional physics on top. This module exists so the
cascade is an explicit named symbol in the codebase per ADR-021 §14.7
(ubiquitous-language enforcement).
"""

from __future__ import annotations

CSC_A_NAME: str = "CSC-A"
CSC_A_DESCRIPTION: str = (
    "Blade wear -> bed unevenness -> motor torque -> bearing fatigue. "
    "Matrix-only via M[motor, blade] = 0.4 (PRD §10.1, ADR-003)."
)


__all__ = ["CSC_A_NAME", "CSC_A_DESCRIPTION"]
