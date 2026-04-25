from __future__ import annotations

import json
from datetime import datetime, timedelta
from engine.contracts import EngineState, Drivers, ComponentId, Forecast
from .connection import connect

class HistorianWriter:
    def __init__(self, db_path: str = "historian.db", batch_size: int = 1000):
        self.conn = connect(db_path)
        self.batch_size = batch_size
        self._buffer = []
        
    def log_run(self, run_id: str, scenario: str, policy: str, seed: int, config: dict):
        # ADR-012 / PLAN-B §7.2: roll forward logic
        # Delete prior rows for this run_id to ensure a clean, deterministic re-run
        self.conn.execute("DELETE FROM checkpoints WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM forecasts WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM obituaries WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM maintenance_events WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM component_states WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM drivers WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        
        self.conn.execute(
            "INSERT INTO runs (run_id, scenario_name, policy, started_at, seed, config_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                scenario,
                policy,
                self._started_at(config).isoformat(),
                seed,
                json.dumps(config, sort_keys=True, default=str),
            )
        )
        self.conn.commit()

    def log_step(self, run_id: str, t: datetime, state: EngineState, drivers: Drivers):
        # Log drivers
        self.conn.execute(
            """INSERT INTO drivers 
               (run_id, t, temp_C, humidity, pm25, psd_d50, voltage_stability, operator_shift) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, t.isoformat(), drivers.temp_C, drivers.humidity, 
                drivers.pm25, drivers.psd_d50, drivers.voltage_stability, drivers.operator_shift
            )
        )
        
        # Log component states
        for cid, cstate in state.components.items():
            self.conn.execute(
                """INSERT INTO component_states 
                   (run_id, t, component_id, health, status, metrics_json) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run_id, t.isoformat(), cid.value, cstate.health, 
                    cstate.status.value, json.dumps(cstate.metrics)
                )
            )
        
        self.conn.commit() # Simple commit for now, could batch if needed for perf

    def log_forecasts(self, run_id: str, t: datetime, forecasts: list[Forecast]):
        for forecast in forecasts:
            self.conn.execute(
                """INSERT OR REPLACE INTO forecasts
                   (run_id, t, component_id, horizon_min, point, lower, upper, ci_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    t.isoformat(),
                    forecast.component_id.value,
                    forecast.horizon_min,
                    forecast.point,
                    forecast.lower,
                    forecast.upper,
                    forecast.ci_level,
                ),
            )
        self.conn.commit()

    def log_event(self, run_id: str, t: datetime, component_id: ComponentId, action: str, triggered_by: str):
        self.conn.execute(
            "INSERT INTO maintenance_events (run_id, t, component_id, action, triggered_by) VALUES (?, ?, ?, ?, ?)",
            (run_id, t.isoformat(), component_id.value, action, triggered_by)
        )
        self.conn.commit()

    def log_obituary(self, obit_data: dict):
        self.conn.execute(
            "INSERT INTO obituaries (run_id, component_id, failure_t, narrative, citations_json) VALUES (?, ?, ?, ?, ?)",
            (obit_data["run_id"], obit_data["component_id"], obit_data["failure_t"], obit_data["narrative"], obit_data["citations_json"])
        )
        self.conn.commit()

    def has_obituary(self, run_id: str, component_id: ComponentId) -> bool:
        res = self.conn.execute(
            "SELECT 1 FROM obituaries WHERE run_id = ? AND component_id = ?",
            (run_id, component_id.value)
        ).fetchone()
        return res is not None

    def finalize_run(self, run_id: str):
        row = self.conn.execute(
            "SELECT config_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        config = json.loads(row["config_json"]) if row else {}
        self.conn.execute(
            "UPDATE runs SET finished_at = ? WHERE run_id = ?",
            (self._finished_at(config).isoformat(), run_id)
        )
        self.conn.commit()

    def log_checkpoint(self, run_id: str, t: datetime, state: EngineState):
        import pickle
        state_blob = pickle.dumps(state)
        self.conn.execute(
            "INSERT INTO checkpoints (run_id, t, state_blob) VALUES (?, ?, ?)",
            (run_id, t.isoformat(), state_blob)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

    @staticmethod
    def _started_at(config: dict) -> datetime:
        return datetime(2026, 4, 25, 8, 0, 0)

    @classmethod
    def _finished_at(cls, config: dict) -> datetime:
        return cls._started_at(config) + timedelta(minutes=int(config.get("horizon_minutes", 600)))
