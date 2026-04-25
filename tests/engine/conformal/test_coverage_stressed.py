"""§9.4 / §13.1 FR-W.6 coverage gate — empirical coverage >= 0.90 on
Stressed seed=42 at 95% nominal CI for every component."""

from __future__ import annotations

import numpy as np
import pytest

from engine.api import initial_state, step
from engine.conformal.wrapper import ConformalForecaster
from engine.contracts import ComponentId, Drivers, ROW_ORDER

COVERAGE_TARGET = 0.90
HORIZON_MIN = 30
RUN_MIN = 600
SEED = 42


def _stressed_drivers(t: int) -> Drivers:
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
        rng_seed=SEED,
    )


@pytest.mark.slow
def test_conformal_coverage_stressed_ge_0_90():
    state = initial_state(scenario="stressed", seed=SEED)
    healths = {cid: [state.components[cid].health] for cid in ROW_ORDER}
    forecasts_at: dict = {cid: [] for cid in ROW_ORDER}

    for t in range(1, RUN_MIN + 1):
        state = step(state, _stressed_drivers(t), dt=1.0)
        for cid in ROW_ORDER:
            h = state.components[cid].health
            healths[cid].append(h)
            f = ConformalForecaster(cid).predict(h, horizon_min=HORIZON_MIN)
            forecasts_at[cid].append((f.lower, f.point, f.upper))

    # At minute t we forecast t+30; compare to actual at t+30.
    coverages: dict = {}
    for cid in ROW_ORDER:
        hits = 0
        total = 0
        for t in range(1, RUN_MIN - HORIZON_MIN + 1):
            lower, _, upper = forecasts_at[cid][t - 1]
            actual = healths[cid][t + HORIZON_MIN]
            if lower <= actual <= upper:
                hits += 1
            total += 1
        coverages[cid] = hits / total if total else 0.0

    failures = {
        cid.value: f"{c:.4f}"
        for cid, c in coverages.items()
        if c < COVERAGE_TARGET
    }
    assert not failures, (
        f"FR-W.6 coverage gate failed: {failures}; "
        f"all components must reach >= {COVERAGE_TARGET}."
    )
