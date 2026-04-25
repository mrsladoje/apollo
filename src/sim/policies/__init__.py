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
        self.thresholds = thresholds or {cid: 0.4 for cid in ComponentId}
        self.lookahead_coef = lookahead_coef

    def decide(self, state: EngineState, t: datetime) -> ComponentId | None:
        # 1. Current Health Check
        for cid, comp in state.components.items():
            if comp.health < self.thresholds.get(cid, 0.4):
                return cid
        
        # 2. Lookahead Check (ADR-011)
        # In a real impl, we'd call engine.forecast()
        # For mock, we'll just check if current health is approaching threshold
        for cid, comp in state.components.items():
            if comp.health < self.thresholds.get(cid, 0.4) + self.lookahead_coef:
                # Predictive maintenance
                return cid
                
        return None
