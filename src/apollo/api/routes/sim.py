"""Sim routes — GET /api/sim/runs and GET /api/sim/stream/:run_id (PLAN-C §5.1)."""

from __future__ import annotations

import asyncio
import json
import random
from typing import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from engine.contracts import ComponentId

router = APIRouter(prefix="/api/sim")

UNIVERSES = [
    {"id": "dark-twin", "label": "Universe A — Dark Twin", "run_id": "dark-twin-00"},
    {"id": "fixed-schedule", "label": "Universe B — Fixed Schedule", "run_id": "fixed-02"},
    {"id": "apollo", "label": "Universe C — Apollo (AI)", "run_id": "apollo-03"},
]

COMPONENTS: list[str] = [c.value for c in ComponentId]
_FORECAST_COMPONENTS: list[ComponentId] = [ComponentId.HEATER, ComponentId.NOZZLE]


@router.get("/runs")
async def get_runs() -> list[dict]:
    return UNIVERSES


def _status(h: float) -> str:
    if h >= 0.7:
        return "FUNCTIONAL"
    if h >= 0.4:
        return "DEGRADED"
    if h >= 0.1:
        return "CRITICAL"
    return "FAILED"


async def _sim_events(run_id: str, universe_id: str, seed: int) -> AsyncIterator[str]:
    rng = random.Random(seed)
    # Degradation multipliers per universe
    multipliers = {
        "dark-twin": 1.8,
        "fixed-schedule": 1.0,
        "apollo": 0.5,
    }
    mult = multipliers.get(universe_id, 1.0)

    health = {c: 1.0 for c in COMPONENTS}

    for t in range(0, 121, 2):
        states = []
        for comp in COMPONENTS:
            delta = rng.uniform(0.01, 0.05) * mult
            health[comp] = max(0.0, health[comp] - delta)
            h = round(health[comp], 3)
            states.append({
                "component_id": comp,
                "health": h,
                "status": _status(h),
                "metrics": {"temp_C": round(rng.uniform(60, 95), 1)},
            })

        tick = {
            "type": "tick",
            "run_id": run_id,
            "universe": universe_id,
            "t": t,
            "states": states,
        }
        yield json.dumps(tick)

        # Emit forecasts for a couple of components every 10 ticks
        if t % 10 == 0:
            for comp_id in _FORECAST_COMPONENTS:
                comp = comp_id.value
                h = health[comp]
                band = {
                    "type": "forecast",
                    "run_id": run_id,
                    "universe": universe_id,
                    "t": t,
                    "component": comp,
                    "band": {
                        "component_id": comp,
                        "horizon_min": 10,
                        "point": round(max(0, h - 0.05), 3),
                        "lower": round(max(0, h - 0.12), 3),
                        "upper": round(min(1, h + 0.02), 3),
                        "ci_level": 0.95,
                    },
                }
                yield json.dumps(band)

        # Emit failure + obituary when a component crosses 0.1
        for comp in COMPONENTS:
            if health[comp] <= 0.1 and health[comp] > 0.0:
                health[comp] = 0.0
                failure = {"type": "failure", "run_id": run_id, "universe": universe_id, "component": comp, "t_fail": t}
                yield json.dumps(failure)
                obit = {
                    "type": "obituary",
                    "run_id": run_id,
                    "universe": universe_id,
                    "component": comp,
                    "narrative": f"My {comp} failed at hour {t//60:.1f}. In the Dark Twin, no intervention was made.",
                    "citations": [{"run_id": run_id, "component": comp, "timestamp": f"2026-04-25T{8 + t//60:02d}:00:00Z"}],
                }
                yield json.dumps(obit)

        await asyncio.sleep(0.3)


_SEEDS = {"dark-twin-00": 5, "fixed-02": 42, "apollo-03": 99}


@router.get("/stream/{universe_id}")
async def stream_sim(universe_id: str):
    universe = next((u for u in UNIVERSES if u["id"] == universe_id), UNIVERSES[0])
    run_id = universe["run_id"]
    seed = _SEEDS.get(run_id, 1)

    async def gen():
        async for data in _sim_events(run_id, universe_id, seed):
            yield {"event": "message", "data": data}

    return EventSourceResponse(gen(), headers={"Cache-Control": "no-cache"}, ping=15)
