"""6x6 linear coupling matrix and update rule — PLAN-A §7 / ADR-004.

The literal matrix from PRD §10.1 lives in `engine.contracts.COUPLING_MATRIX_M`
(single source of truth for the architecture test in §7.4). This module
exposes the matrix as a NumPy array and the apply_coupling update rule per
PRD §10.1:

    dH_i / dt = -alpha_i * f(drivers_i)  -  Sum_j  M_ij * (1 - H_j)
"""

from __future__ import annotations

import numpy as np

from engine.contracts import COUPLING_MATRIX_M as _M_LITERAL, ROW_ORDER

# Numpy mirror of the contracts tuple. Cached at module load.
COUPLING_MATRIX_M: np.ndarray = np.asarray(_M_LITERAL, dtype=np.float64)

def apply_coupling(
    healths: np.ndarray,
    intrinsic_dH: np.ndarray,
    dt: float,
) -> np.ndarray:
    """Advance the 6-vector of healths by intrinsic decay + matrix coupling.

    `healths` and `intrinsic_dH` are aligned with `ROW_ORDER`. The output is
    clamped to [0, 1] (FR-1.4 invariant for the aggregate root, ADR-021 §14.3).
    """
    coupled_term = COUPLING_MATRIX_M @ (1.0 - healths)
    dH = intrinsic_dH - coupled_term * dt
    return np.clip(healths + dH, 0.0, 1.0)


__all__ = [
    "COUPLING_MATRIX_M",
    "ROW_ORDER",
    "apply_coupling",
]
