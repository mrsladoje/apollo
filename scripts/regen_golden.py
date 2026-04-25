"""Regenerate the Stressed/seed=42/t=0..600 golden file — PLAN-A §10.2.

Invoked manually via `make regen-golden`. Never runs in CI; the
determinism gate (`tests/engine/test_determinism_golden.py`) reads the
checked-in artifact and asserts byte equality.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.api import initial_state, step  # noqa: E402
from engine.contracts import ComponentId, Drivers  # noqa: E402

import numpy as np  # noqa: E402


def stressed_drivers(t: int, *, seed: int) -> Drivers:
    """Synthetic Stressed driver trace — must match the determinism test."""
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


def main() -> int:
    out_path = ROOT / "golden" / "engine" / "stressed_seed42_t0_t600.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    state = initial_state(scenario="stressed", seed=42)
    lines = [state.model_dump_json()]
    for t in range(1, 601):
        state = step(state, stressed_drivers(t, seed=42), dt=1.0)
        lines.append(state.model_dump_json())
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {len(lines)} lines to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
