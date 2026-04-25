from __future__ import annotations

from sim.config import SimulationConfig
from sim.loop import run_simulation


def test_engine_step_invoked_once_per_tick(tmp_path, monkeypatch):
    from sim import loop as loop_mod

    original_step = loop_mod.engine.step
    calls = {"count": 0}

    def counting_step(state, drivers, dt):
        calls["count"] += 1
        return original_step(state, drivers, dt)

    monkeypatch.setattr(loop_mod.engine, "step", counting_step)
    run_simulation(
        SimulationConfig(
            scenario_name="stressed",
            policy="none",
            seed=42,
            horizon_minutes=60,
            time_step_minutes=5,
            historian_path=str(tmp_path / "historian.db"),
        )
    )

    assert calls["count"] == 12
