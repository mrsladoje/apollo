"""Sim routes — GET /api/sim/runs and GET /api/sim/stream/:run_id (PLAN-C §5.1).

When a real historian is reachable (``HISTORIAN_PATH`` points at a populated
SQLite file written by Plan B's ``run_simulation``), the routes surface real
persisted runs and replay real ``component_states`` + ``forecasts`` +
``obituaries``. When the database is empty or missing they fall back to a
deterministic synthetic stream so the frontend keeps rendering even before
``scripts/prerun_scenarios.py`` has been run.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import sqlite3
from typing import AsyncIterator, Optional

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from engine.contracts import ComponentId

router = APIRouter(prefix="/api/sim")

# Universe → (scenario_name, policy) — the canonical Dark-Twin / Fixed /
# Apollo mapping per ADR-013 and PLAN-C §10.1.
UNIVERSE_TO_RUN_PARAMS: dict[str, tuple[str, str, str]] = {
    "dark-twin":      ("barcelona-humid", "none",  "Universe A — Dark Twin"),
    "fixed-schedule": ("barcelona-humid", "fixed", "Universe B — Fixed Schedule"),
    "apollo":         ("barcelona-humid", "ai",    "Universe C — Apollo (AI)"),
}

# Synthetic fallback when the historian is empty/missing.
_SYNTH_RUNS = [
    {"id": "dark-twin",      "label": "Universe A — Dark Twin",       "run_id": "dark-twin-00"},
    {"id": "fixed-schedule", "label": "Universe B — Fixed Schedule",  "run_id": "fixed-02"},
    {"id": "apollo",         "label": "Universe C — Apollo (AI)",     "run_id": "apollo-03"},
]
_SYNTH_SEEDS = {"dark-twin-00": 5, "fixed-02": 42, "apollo-03": 99}

COMPONENTS: list[str] = [c.value for c in ComponentId]
_FORECAST_COMPONENTS: list[ComponentId] = [ComponentId.HEATER, ComponentId.NOZZLE]


def _historian_path() -> str:
    return (
        os.environ.get("HISTORIAN_PATH")
        or os.environ.get("HISTORIAN_DB_PATH")
        or "historian.db"
    )


def _open_historian() -> Optional[sqlite3.Connection]:
    path = _historian_path()
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        # The historian writer creates these on first write; if any are
        # missing we treat the DB as effectively empty.
        for table in ("runs", "component_states"):
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if cur is None:
                conn.close()
                return None
        return conn
    except sqlite3.Error:
        return None


def _resolve_run_id(conn: sqlite3.Connection, scenario: str, policy: str) -> Optional[str]:
    row = conn.execute(
        "SELECT run_id FROM runs WHERE scenario_name=? AND policy=? "
        "ORDER BY started_at DESC LIMIT 1",
        (scenario, policy),
    ).fetchone()
    return row["run_id"] if row else None


@router.get("/runs")
async def get_runs() -> list[dict]:
    """Return one row per Universe panel.

    Real historian present → real run IDs; otherwise the synthetic fallback
    so the dashboard still has something to render before ``prerun_scenarios``
    has been executed.
    """
    conn = _open_historian()
    if conn is None:
        return _SYNTH_RUNS

    try:
        out: list[dict] = []
        for universe_id, (scenario, policy, label) in UNIVERSE_TO_RUN_PARAMS.items():
            run_id = _resolve_run_id(conn, scenario, policy)
            if run_id is None:
                # Partial pre-run. Keep the row but mark it synthetic so
                # the frontend can still display the panel.
                out.append({
                    "id": universe_id,
                    "label": label,
                    "run_id": f"{scenario}-{policy}-pending",
                    "synthetic": True,
                })
            else:
                out.append({
                    "id": universe_id,
                    "label": label,
                    "run_id": run_id,
                    "scenario": scenario,
                    "policy": policy,
                    "synthetic": False,
                })
        return out
    finally:
        conn.close()


def _status(h: float) -> str:
    if h >= 0.7:
        return "FUNCTIONAL"
    if h >= 0.4:
        return "DEGRADED"
    if h >= 0.1:
        return "CRITICAL"
    return "FAILED"


async def _historian_events(
    conn: sqlite3.Connection,
    run_id: str,
    universe_id: str,
    *,
    delay: float = 0.0,
    every_n_ticks: int = 1,
    speed: float = 1.0,
) -> AsyncIterator[str]:
    """Replay one persisted run as the live SSE stream.

    Tick = one timestamp, with all six component_states. Forecast events
    fire whenever the historian has rows in ``forecasts`` for that tick.
    Failure + obituary events fire as soon as we cross a transition into
    ``FAILED``, keyed off the ``obituaries`` table.
    """
    # Pull all timestamps for this run in chronological order.
    timestamps = [
        r["t"] for r in conn.execute(
            "SELECT DISTINCT t FROM component_states WHERE run_id=? ORDER BY t ASC",
            (run_id,),
        ).fetchall()
    ]
    if not timestamps:
        return

    # Pre-load obituaries so we know when to emit failure/obituary events.
    obit_by_t: dict[str, list[dict]] = {}
    for r in conn.execute(
        "SELECT component_id, failure_t, narrative FROM obituaries WHERE run_id=?",
        (run_id,),
    ).fetchall():
        obit_by_t.setdefault(r["failure_t"], []).append({
            "component": r["component_id"],
            "narrative": r["narrative"],
        })

    failed_emitted: set[str] = set()
    sim_start = timestamps[0]
    from datetime import datetime

    for tick_index, t_iso in enumerate(timestamps):
        t_offset = int(
            (datetime.fromisoformat(t_iso) - datetime.fromisoformat(sim_start)).total_seconds() // 60
        )
        emit_tick = (tick_index % every_n_ticks == 0)

        if emit_tick:
            state_rows = conn.execute(
                "SELECT component_id, health, status, metrics_json "
                "FROM component_states WHERE run_id=? AND t=? "
                "ORDER BY component_id ASC",
                (run_id, t_iso),
            ).fetchall()

            states = []
            for r in state_rows:
                try:
                    metrics = json.loads(r["metrics_json"] or "{}")
                except json.JSONDecodeError:
                    metrics = {}
                states.append({
                    "component_id": r["component_id"],
                    "health": float(r["health"]),
                    "status": r["status"],
                    "metrics": metrics,
                })

            yield json.dumps({
                "type": "tick",
                "run_id": run_id,
                "universe": universe_id,
                "t": t_offset,
                "states": states,
            })

            # Forecasts at this t (one row per component if Plan A persisted it).
            for fr in conn.execute(
                "SELECT component_id, horizon_min, point, lower, upper, ci_level "
                "FROM forecasts WHERE run_id=? AND t=? AND component_id IN (?, ?)",
                (run_id, t_iso, ComponentId.HEATER.value, ComponentId.NOZZLE.value),
            ).fetchall():
                yield json.dumps({
                    "type": "forecast",
                    "run_id": run_id,
                    "universe": universe_id,
                    "t": t_offset,
                    "component": fr["component_id"],
                    "band": {
                        "component_id": fr["component_id"],
                        "horizon_min": int(fr["horizon_min"]),
                        "point": float(fr["point"]),
                        "lower": float(fr["lower"]),
                        "upper": float(fr["upper"]),
                        "ci_level": float(fr["ci_level"]),
                    },
                })

        # Failure + obituary always fire on the historian tick they actually
        # land on, even when ``every_n_ticks`` would skip the surrounding tick
        # emission — otherwise failures on odd-indexed ticks vanish from both
        # the chart markers and the Failure log.
        for entry in obit_by_t.get(t_iso, []):
            comp = entry["component"]
            if comp in failed_emitted:
                continue
            failed_emitted.add(comp)
            yield json.dumps({
                "type": "failure",
                "run_id": run_id,
                "universe": universe_id,
                "component": comp,
                "t_fail": t_offset,
            })
            yield json.dumps({
                "type": "obituary",
                "run_id": run_id,
                "universe": universe_id,
                "component": comp,
                "narrative": entry["narrative"],
                "citations": [{
                    "run_id": run_id,
                    "component": comp,
                    "timestamp": t_iso,
                }],
            })

        if emit_tick:
            # ``speed`` scales playback (0.2 = 5x slower, 2.0 = 2x faster).
            scaled_delay = delay / speed if speed > 0 else delay
            if scaled_delay > 0:
                await asyncio.sleep(scaled_delay)


async def _synthetic_events(
    run_id: str,
    universe_id: str,
    seed: int,
    *,
    speed: float = 1.0,
    scenario: str = "barcelona-humid",
) -> AsyncIterator[str]:
    """Original deterministic stub — used when the historian is empty.

    Scenario shapes the wear curve: ``stressed`` decays fastest, ``phoenix-dry``
    sits in the middle, ``barcelona-humid`` is the gentlest baseline.
    """
    rng = random.Random(seed)
    multipliers = {"dark-twin": 1.8, "fixed-schedule": 1.0, "apollo": 0.5}
    scenario_mult = {
        "barcelona-humid": 1.0,
        "phoenix-dry": 1.4,
        "stressed": 2.2,
    }.get(scenario, 1.0)
    mult = multipliers.get(universe_id, 1.0) * scenario_mult
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

        yield json.dumps({
            "type": "tick",
            "run_id": run_id,
            "universe": universe_id,
            "t": t,
            "states": states,
        })

        if t % 10 == 0:
            for comp_id in _FORECAST_COMPONENTS:
                comp = comp_id.value
                h = health[comp]
                yield json.dumps({
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
                })

        for comp in COMPONENTS:
            if health[comp] <= 0.1 and health[comp] > 0.0:
                health[comp] = 0.0
                yield json.dumps({
                    "type": "failure",
                    "run_id": run_id,
                    "universe": universe_id,
                    "component": comp,
                    "t_fail": t,
                })
                yield json.dumps({
                    "type": "obituary",
                    "run_id": run_id,
                    "universe": universe_id,
                    "component": comp,
                    "narrative": f"My {comp} failed at hour {t//60:.1f}. In the Dark Twin, no intervention was made.",
                    "citations": [{
                        "run_id": run_id,
                        "component": comp,
                        "timestamp": f"2026-04-25T{8 + t//60:02d}:00:00Z",
                    }],
                })

        scaled = 0.3 / speed if speed > 0 else 0.3
        await asyncio.sleep(scaled)


_VALID_SCENARIOS = {"barcelona-humid", "phoenix-dry", "stressed"}


@router.get("/stream/{universe_id}")
async def stream_sim(universe_id: str, speed: float = 1.0, scenario: Optional[str] = None):
    """Replay the historian for the configured universe; fall back to the
    deterministic synthetic stream when no real data is present.

    The optional ``scenario`` query param overrides the default scenario
    (``barcelona-humid``) — accepted values: ``barcelona-humid``, ``phoenix-dry``,
    ``stressed``. Each universe keeps its own policy (none / fixed / ai).
    """
    conn = _open_historian()
    real_run_id: Optional[str] = None
    if conn is not None and universe_id in UNIVERSE_TO_RUN_PARAMS:
        default_scenario, policy, _ = UNIVERSE_TO_RUN_PARAMS[universe_id]
        chosen_scenario = scenario if scenario in _VALID_SCENARIOS else default_scenario
        real_run_id = _resolve_run_id(conn, chosen_scenario, policy)

    # Clamp speed to a sane range — 0.05 (20x slower) up to 8x faster.
    safe_speed = max(0.05, min(8.0, speed))

    if conn is not None and real_run_id is not None:
        async def gen_real():
            try:
                async for data in _historian_events(
                    conn,
                    real_run_id,
                    universe_id,
                    delay=0.05,
                    every_n_ticks=2,
                    speed=safe_speed,
                ):
                    yield {"event": "message", "data": data}
            finally:
                conn.close()
        return EventSourceResponse(gen_real(), headers={"Cache-Control": "no-cache"}, ping=15)

    if conn is not None:
        conn.close()

    fallback = next(
        (u for u in _SYNTH_RUNS if u["id"] == universe_id), _SYNTH_RUNS[0]
    )
    run_id = fallback["run_id"]
    seed = _SYNTH_SEEDS.get(run_id, 1)
    chosen_scenario = scenario if scenario in _VALID_SCENARIOS else "barcelona-humid"

    async def gen_synth():
        async for data in _synthetic_events(
            run_id, universe_id, seed, speed=safe_speed, scenario=chosen_scenario
        ):
            yield {"event": "message", "data": data}

    return EventSourceResponse(gen_synth(), headers={"Cache-Control": "no-cache"}, ping=15)
