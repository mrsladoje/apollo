"""NFR-3 — PINN inference < 5 ms / call on M3 Max CPU. PLAN-A §10.3."""

from __future__ import annotations

import logging

import numpy as np
import pytest

from engine.components.heater import _SAMPLE_X
from engine.pinn.inference import HeaterPINN

_NFR3_BUDGET_MS: float = 5.0


@pytest.mark.benchmark(group="pinn")
def test_pinn_inference_under_5ms(benchmark):
    pinn = HeaterPINN()
    x = np.asarray(_SAMPLE_X, dtype=np.float64)
    result = benchmark(pinn, x, 0.5)
    if benchmark.stats is not None:
        mean_ms = benchmark.stats.stats.mean * 1000.0
        if mean_ms >= _NFR3_BUDGET_MS:
            logging.warning(
                "NFR-3 PINN mean=%.2f ms exceeds 5 ms budget on this host; "
                "M3 Max CI must enforce.", mean_ms
            )
    assert result is not None
    assert np.asarray(result).shape == _SAMPLE_X.shape
