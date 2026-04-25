"""Shared fixtures for per-component tests — PLAN-A §6.5."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from engine.contracts import (
    ComponentId,
    ComponentState,
    Drivers,
    status_for_health,
)


def make_drivers(
    *,
    temp_C: float = 25.0,
    humidity: float = 0.5,
    pm25: float = 10.0,
    psd_d50: float = 20.0,
    voltage_stability: float = 1.0,
    cycles: int = 0,
    hours: float = 0.0,
    operator_shift: str = "day",
    rng_seed: int = 42,
    maintenance_level: Mapping[ComponentId, float] | None = None,
) -> Drivers:
    if maintenance_level is None:
        maintenance_level = {c: 1.0 for c in ComponentId}
    return Drivers(
        temp_C=temp_C,
        humidity=humidity,
        pm25=pm25,
        psd_d50=psd_d50,
        voltage_stability=voltage_stability,
        cycles=cycles,
        hours=hours,
        maintenance_level=dict(maintenance_level),
        operator_shift=operator_shift,
        rng_seed=rng_seed,
    )


def stressed_drivers(t_min: float, *, rng_seed: int = 42) -> Drivers:
    """One-minute slice of the Stressed scenario (PRD §9.3): high duty,
    degraded powder PSD, erratic operator shift, hot/humid envelope."""
    return make_drivers(
        temp_C=45.0 + 5.0 * np.sin(t_min * 0.05),
        humidity=0.75,
        pm25=40.0,
        psd_d50=35.0,
        voltage_stability=0.6,
        cycles=int(t_min * 1.5),
        hours=t_min / 60.0,
        operator_shift="weekend",
        rng_seed=rng_seed,
    )


def isolated_state(component_id: ComponentId, health: float) -> ComponentState:
    return ComponentState(
        component_id=component_id,
        health=health,
        status=status_for_health(health),
        metrics={},
    )


def iterate_intrinsic(
    component,
    drivers_fn,
    *,
    h0: float = 1.0,
    minutes: int = 60,
    seed: int = 0,
) -> list[float]:
    """Drive a component in isolation through `minutes` iterations of dt=1."""
    rng = np.random.default_rng(seed)
    h = h0
    healths = []
    for t in range(minutes):
        drivers = drivers_fn(t)
        state = isolated_state(component.component_id, h)
        dh = component.intrinsic_decay(state, drivers, 1.0, rng)
        h = max(0.0, min(1.0, h + dh))
        healths.append(h)
    return healths
