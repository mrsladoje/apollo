"""NFR-1 byte-compare gate — PLAN-A §10.2.

Two-run determinism plus byte-identity against the checked-in golden file.
Regenerate via `make regen-golden` (or `python3 scripts/regen_golden.py`)
when a deliberate engine change merges.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from engine.api import initial_state, step
from engine.contracts import ComponentId, Drivers

GOLDEN = (
    Path(__file__).resolve().parents[2] / "golden" / "engine" / "stressed_seed42_t0_t600.jsonl"
)


def _stressed_drivers(t: int, *, seed: int) -> Drivers:
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
        rng_seed=seed,
    )


def _run_full_scenario(*, seed: int, minutes: int) -> list[str]:
    state = initial_state(scenario="stressed", seed=seed)
    lines = [state.model_dump_json()]
    for t in range(1, minutes + 1):
        state = step(state, _stressed_drivers(t, seed=seed), dt=1.0)
        lines.append(state.model_dump_json())
    return lines


def test_two_runs_identical():
    a = _run_full_scenario(seed=42, minutes=60)
    b = _run_full_scenario(seed=42, minutes=60)
    assert a == b


def test_stressed_seed42_byte_identical_against_golden():
    out = _run_full_scenario(seed=42, minutes=600)
    assert GOLDEN.exists(), (
        f"Golden file missing at {GOLDEN}. Regenerate via "
        "`python3 scripts/regen_golden.py`."
    )
    expected = GOLDEN.read_text(encoding="utf-8")
    assert "\n".join(out) == expected
