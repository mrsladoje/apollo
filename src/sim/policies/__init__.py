from __future__ import annotations

from engine.contracts import ComponentId, EngineState
from datetime import datetime

class NonePolicy:
    def decide(self, state: EngineState, t: datetime) -> ComponentId | None:
        return None

class FixedPolicy:
    def __init__(self, period_minutes: int = 90):
        self.period_minutes = period_minutes
        self.rotation = [
            ComponentId.BLADE,
            ComponentId.MOTOR,
            ComponentId.NOZZLE,
            ComponentId.RESISTOR,
            ComponentId.HEATER,
            ComponentId.INSULATION
        ]
        self.last_maint_t = None
        self.next_idx = 0

    def decide(self, state: EngineState, t: datetime) -> ComponentId | None:
        if self.last_maint_t is None:
            self.last_maint_t = t
            return None
        
        elapsed = (t - self.last_maint_t).total_seconds() / 60.0
        if elapsed >= self.period_minutes:
            cid = self.rotation[self.next_idx]
            self.next_idx = (self.next_idx + 1) % len(self.rotation)
            self.last_maint_t = t
            return cid
        return None

class AIPolicy:
    """Tuned by GA in Workstream B5. (PLAN-B §8.2)"""
    def __init__(self, thresholds: dict[ComponentId, float] | None = None, lookahead_coef: float = 0.2):
        self.thresholds = thresholds or {
            ComponentId.BLADE: 0.50,
            ComponentId.MOTOR: 0.55,
            ComponentId.NOZZLE: 0.45,
            ComponentId.RESISTOR: 0.50,
            ComponentId.HEATER: 0.55,
            ComponentId.INSULATION: 0.40,
        }
        self.lookahead_coef = lookahead_coef

    def decide(self, state: EngineState, t: datetime) -> ComponentId | None:
        # 1. Current Health Check
        for cid, comp in state.components.items():
            if comp.health < self.thresholds.get(cid, 0.4):
                return cid
        
        # 2. Forecast lookahead check (ADR-011 / PLAN-B §8.2)
        from engine import mock_engine as engine

        horizon = max(1, min(60, int(60 * self.lookahead_coef)))
        for forecast in engine.forecast(state, horizon_min=horizon):
            trigger = max(
                0.4,
                self.thresholds.get(forecast.component_id, 0.4) + self.lookahead_coef,
            )
            if forecast.point < trigger:
                return forecast.component_id
                
        return None
