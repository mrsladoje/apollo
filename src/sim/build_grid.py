import sys
from sim.config import SimulationConfig
from sim.loop import run_simulation

def build_grid():
    """Run all 9 combinations for the 3x3 grid. (PLAN-B §8.3)"""
    scenarios = ["barcelona-humid", "phoenix-dry", "stressed"]
    policies = ["none", "fixed", "ai"]
    seed = 42
    
    print(f"Building 3x3 Grid (seed={seed})...")
    
    for scenario in scenarios:
        for policy in policies:
            cfg = SimulationConfig.from_run_params(
                scenario_name=scenario,
                policy=policy,
                seed=seed,
            )
            run_id = cfg.get_run_id()
            print(f"  Running {run_id}...", end="", flush=True)
            run_simulation(cfg)
            print(" Done.")

if __name__ == "__main__":
    build_grid()
