"""Public engine surface — the only module Plans B and C may import.

Per PLAN-A §3.2 the surface is exactly three symbols: `step`, `forecast`,
`initial_state`. Until real components ship per §5–§9, the mock IS the
engine and this module re-exports it verbatim. When the real `step()`
lands, this file flips to a dispatch table that honors §4.3's
`APOLLO_ENGINE=mock` env-var gate (mock kept around for Plan B smoke
tests / demo dry-runs where engine compute should be skipped).
"""

from __future__ import annotations

from engine.mock_engine import forecast, initial_state, step

__all__ = ["step", "forecast", "initial_state"]
