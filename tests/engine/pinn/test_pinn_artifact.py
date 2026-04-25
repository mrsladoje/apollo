"""PINN artifact present + loadable — PLAN-A §8.8."""

from __future__ import annotations

from pathlib import Path

import torch

from engine.pinn.inference import HeaterPINN, _DEFAULT_WEIGHTS, _FNN


def test_pinn_artifact_present():
    """models/heater_pinn.pt exists and is < 1 MB (§13.3)."""
    assert _DEFAULT_WEIGHTS.exists(), f"Missing PINN artifact at {_DEFAULT_WEIGHTS}"
    size_kb = _DEFAULT_WEIGHTS.stat().st_size / 1024.0
    assert size_kb < 1024.0, f"PINN artifact must be < 1 MB; got {size_kb:.1f} KB"


def test_pinn_artifact_loads():
    """Loads without error and matches the inference architecture."""
    state = torch.load(_DEFAULT_WEIGHTS, map_location="cpu", weights_only=True)
    net = _FNN()
    net.load_state_dict(state)
    pinn = HeaterPINN()
    assert pinn._net is not None
