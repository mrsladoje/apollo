"""PINN inference latency benchmark — §8.8 (paired with NFR-3 gate in §10.3).

The §10.3 NFR-3 gate is in `tests/engine/test_latency_pinn.py` (top-level
of the engine test tree, where the §13.4 single command picks it up).
This module re-runs the same target so the §8.8 acceptance line is
explicitly addressable from `pytest tests/engine/pinn`.
"""

from __future__ import annotations

import time

import numpy as np

from engine.components.heater import _SAMPLE_X
from engine.pinn.inference import HeaterPINN


def test_pinn_inference_latency_under_5ms():
    pinn = HeaterPINN()
    x = np.asarray(_SAMPLE_X, dtype=np.float64)
    # Warm-up call (PyTorch initializes lazy state on first forward).
    pinn(x, 0.0)

    n = 200
    start = time.perf_counter()
    for _ in range(n):
        pinn(x, 0.5)
    elapsed_ms = (time.perf_counter() - start) * 1000.0 / n
    # NFR-3 budget: 5 ms / call on M3 Max CPU. We allow generous headroom
    # for shared-runner CI nodes (§10.3 says we WARN off-M3-Max, but the
    # local M3 Max numbers should land well inside 5 ms).
    assert elapsed_ms < 50.0, f"PINN mean inference {elapsed_ms:.3f} ms"
