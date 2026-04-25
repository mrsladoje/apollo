from __future__ import annotations

import os
from typing import Dict, Literal, Optional

import yaml
from pydantic import BaseModel, Field

from engine.contracts import ComponentId


class SimulationConfig(BaseModel):
    """Reproducibility key per §3.3 / NFR-8.

    The tuple ``(scenario_name, policy, seed, config_json)`` is the canonical
    NFR-8 key — same key ⇒ byte-identical historian. ``thresholds`` and
    ``lookahead_coef`` are normalized into ``config_json`` by the loop so the
    AIPolicy genome participates in that key.
    """

    scenario_name: Literal["barcelona-humid", "phoenix-dry", "stressed"]
    policy: Literal["none", "fixed", "ai"]
    seed: int
    time_step_minutes: int = 1                # FR-2.1
    horizon_minutes: int = 600                # 10-hour print cycle (PRD §2.1)
    historian_path: str = "historian.db"
    config_json: Dict = Field(default_factory=dict)  # NFR-8 reproducibility key

    # Policy-specific thresholds
    thresholds: Optional[Dict[ComponentId, float]] = None
    lookahead_coef: float = 0.2

    def get_run_id(self) -> str:
        """Deterministic run_id per §3.3."""
        return f"{self.scenario_name}-{self.policy}-seed{self.seed:04d}"

    @classmethod
    def from_run_params(
        cls,
        scenario_name: str,
        policy: str,
        seed: int = 42,
        yaml_path: str = "config/policies.yaml",
        **overrides,
    ) -> "SimulationConfig":
        """Load optimized thresholds from YAML if available (AI policy only).

        Extra kwargs are forwarded to the constructor so callers can override
        ``horizon_minutes`` / ``time_step_minutes`` etc. without bypassing the
        YAML lookup.
        """
        thresholds: Optional[Dict[ComponentId, float]] = None
        lookahead_coef = 0.2

        if policy == "ai" and os.path.exists(yaml_path):
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f) or {}
            ai = data.get("ai_policy", {})
            raw_thresholds = ai.get("thresholds", {})
            if raw_thresholds:
                thresholds = {
                    ComponentId(k): float(v) for k, v in raw_thresholds.items()
                }
            lookahead_coef = float(ai.get("lookahead_coef", lookahead_coef))

        return cls(
            scenario_name=scenario_name,
            policy=policy,
            seed=seed,
            thresholds=thresholds,
            lookahead_coef=lookahead_coef,
            **overrides,
        )
