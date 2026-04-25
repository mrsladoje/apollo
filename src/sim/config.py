import os
import yaml
from typing import Literal
from pydantic import BaseModel
from engine.contracts import ComponentId

class SimulationConfig(BaseModel):
    scenario_name: Literal["barcelona-humid", "phoenix-dry", "stressed"]
    policy: Literal["none", "fixed", "ai"]
    seed: int
    time_step_minutes: int = 1                # FR-2.1
    horizon_minutes: int = 600                # 10-hour print cycle (PRD §2.1)
    historian_path: str = "historian.db"
    config_json: dict = {}                    # NFR-8 reproducibility key
    
    # Policy-specific thresholds
    thresholds: dict[ComponentId, float] | None = None
    lookahead_coef: float = 0.2

    def get_run_id(self) -> str:
        """Deterministic run_id per §3.3."""
        return f"{self.scenario_name}-{self.policy}-seed{self.seed:04d}"

    @classmethod
    def from_run_params(cls, scenario_name: str, policy: str, seed: int = 42, yaml_path: str = "config/policies.yaml"):
        """Load optimized thresholds from YAML if available."""
        thresholds = None
        lookahead_coef = 0.2
        
        if policy == "ai" and os.path.exists(yaml_path):
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
                if "ai_policy" in data:
                    thresholds = {ComponentId(k): v for k, v in data["ai_policy"]["thresholds"].items()}
                    lookahead_coef = data["ai_policy"].get("lookahead_coef", 0.2)
                    
        return cls(
            scenario_name=scenario_name,
            policy=policy,
            seed=seed,
            thresholds=thresholds,
            lookahead_coef=lookahead_coef
        )
