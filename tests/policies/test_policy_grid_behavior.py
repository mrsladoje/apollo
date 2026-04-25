import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def _avg_health(db_path, policy):
    conn = sqlite3.connect(db_path)
    return conn.execute(
        """SELECT avg(health)
           FROM runs JOIN component_states USING (run_id)
           WHERE policy = ?""",
        (policy,),
    ).fetchone()[0]


def test_ai_policy_improves_mock_backed_health(tmp_path):
    db_path = tmp_path / "historian.db"
    for policy in ("none", "fixed", "ai"):
        run_simulation(
            SimulationConfig(
                scenario_name="stressed",
                policy=policy,
                seed=42,
                horizon_minutes=240,
                historian_path=str(db_path),
            )
        )

    assert _avg_health(db_path, "ai") > _avg_health(db_path, "none")
    assert _avg_health(db_path, "fixed") > _avg_health(db_path, "none")

