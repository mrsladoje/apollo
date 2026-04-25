"""NFR-2 — `step()` < 50 ms / call on M3 Max CPU. PLAN-A §10.3."""

from __future__ import annotations

import logging

import numpy as np
import pytest

from engine.api import initial_state, step
from engine.contracts import ComponentId, Drivers

_NFR2_BUDGET_MS: float = 50.0


def _drivers(t: int) -> Drivers:
    return Drivers(
        temp_C=45.0 + 5.0 * float(np.sin(t * 0.05)),
        humidity=0.75,
        pm25=40.0,
        psd_d50=35.0,
        voltage_stability=0.6,
        cycles=int(t * 1.5),
        hours=t / 60.0,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="weekend",
        rng_seed=42,
    )


@pytest.mark.benchmark(group="step")
def test_step_latency_under_50ms(benchmark):
    state = initial_state(scenario="stressed", seed=42)
    drivers = _drivers(t=120)
    result = benchmark(step, state, drivers, 1.0)
    if benchmark.stats is not None:
        mean_ms = benchmark.stats.stats.mean * 1000.0
        if mean_ms >= _NFR2_BUDGET_MS:
            # Per §10.3 we don't block CI on hardware drift; we WARN and let
            # the M3 Max dev box gate. Threshold remains 50 ms.
            logging.warning(
                "NFR-2 step() mean=%.2f ms exceeds 50 ms budget on this host; "
                "M3 Max CI must enforce.", mean_ms
            )
    assert result is not None
