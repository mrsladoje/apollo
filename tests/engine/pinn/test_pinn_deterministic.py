"""Frozen-weight PINN is deterministic on CPU — PLAN-A §8.8 (NFR-1)."""

from __future__ import annotations

import numpy as np

from engine.pinn.inference import HeaterPINN
from engine.components.heater import _SAMPLE_X


def test_pinn_deterministic():
    a = HeaterPINN()(np.asarray(_SAMPLE_X, dtype=np.float64), 0.7)
    b = HeaterPINN()(np.asarray(_SAMPLE_X, dtype=np.float64), 0.7)
    np.testing.assert_array_equal(a, b)
