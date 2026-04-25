"""Coupling matrix structural tests — PLAN-A §7.4."""

from __future__ import annotations

import numpy as np

from engine.contracts import COUPLING_MATRIX_M as M_CONTRACT, ComponentId, ROW_ORDER
from engine.coupling import COUPLING_MATRIX_M, apply_coupling


# Literal published 6x6 from PRD §10.1 — the architecture invariant.
PRD_LITERAL = (
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),    # blade
    (0.4, 0.0, 0.0, 0.0, 0.0, 0.0),    # motor      <- CSC-A
    (0.2, 0.0, 0.0, 0.0, 0.3, 0.0),    # nozzle     <- CSC-C, CSC-B
    (0.0, 0.0, 0.1, 0.0, 0.2, 0.0),    # resistor   <- CSC-B
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.5),    # heater     <- CSC-B
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),    # insulation
)


def test_coupling_matrix_literal():
    """Assert COUPLING_MATRIX_M is exactly the 6x6 published in PRD §10.1."""
    np.testing.assert_array_equal(np.asarray(COUPLING_MATRIX_M), np.asarray(PRD_LITERAL))
    assert tuple(tuple(row) for row in M_CONTRACT) == PRD_LITERAL


def test_no_coupling_self_loops():
    assert np.all(np.diag(COUPLING_MATRIX_M) == 0.0)


def test_row_order_is_canonical():
    assert ROW_ORDER == (
        ComponentId.BLADE,
        ComponentId.MOTOR,
        ComponentId.NOZZLE,
        ComponentId.RESISTOR,
        ComponentId.HEATER,
        ComponentId.INSULATION,
    )


def test_apply_coupling_clamps_to_unit_interval():
    healths = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    intrinsic = -np.ones(6) * 5.0  # absurdly negative
    out = apply_coupling(healths, intrinsic, dt=1.0)
    assert np.all(out >= 0.0)
    assert np.all(out <= 1.0)


def test_apply_coupling_zero_when_all_healthy():
    """If every component is at 1.0 and intrinsic dH is 0, healths do not change."""
    healths = np.ones(6)
    intrinsic = np.zeros(6)
    out = apply_coupling(healths, intrinsic, dt=1.0)
    np.testing.assert_array_equal(out, healths)


def test_apply_coupling_uses_literal_plan_formula():
    """PLAN-A §7.2: dH = intrinsic_dH - (M @ (1-H)) * dt, with no hidden scale."""
    healths = np.array([0.5, 1.0, 1.0, 1.0, 1.0, 1.0])
    intrinsic = np.zeros(6)
    out = apply_coupling(healths, intrinsic, dt=1.0)
    motor_idx = ROW_ORDER.index(ComponentId.MOTOR)
    assert out[motor_idx] == 0.8
