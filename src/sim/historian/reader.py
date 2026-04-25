from __future__ import annotations

import json
from datetime import datetime
from engine.contracts import ComponentId, ComponentStatus
from sim.contracts import HistorianRow
from .connection import connect

def query_historian(
    run_id: str,
    component: ComponentId | None = None,
    time_range: tuple[datetime, datetime] | None = None,
    db_path: str = "historian.db"
) -> list[HistorianRow]:
    conn = connect(db_path)
    query = """
        SELECT cs.run_id, cs.t, cs.component_id, cs.health, cs.status, cs.metrics_json
        FROM component_states cs
        WHERE cs.run_id = ?
    """
    params = [run_id]
    
    if component:
        query += " AND cs.component_id = ?"
        params.append(component.value)
        
    if time_range:
        query += " AND cs.t >= ? AND cs.t <= ?"
        params.append(time_range[0].isoformat())
        params.append(time_range[1].isoformat())
        
    query += " ORDER BY cs.t ASC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    return [
        HistorianRow(
            run_id=row["run_id"],
            t=datetime.fromisoformat(row["t"]),
            component_id=ComponentId(row["component_id"]),
            health=row["health"],
            status=ComponentStatus(row["status"]),
            metrics=json.loads(row["metrics_json"])
        )
        for row in rows
    ]

_VALID_METRICS = {
    "uptime_hours",
    "failure_count",
    "maintenance_count",
    "avg_health",
}


def _time_step_minutes(conn, run_id: str) -> int:
    """Return the run's time_step_minutes from its persisted config_json.

    Falls back to 1 if the run is missing or the field is absent — safe
    for legacy fixtures where every tick is one minute.
    """
    import json as _json

    row = conn.execute(
        "SELECT config_json FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        return 1
    try:
        cfg = _json.loads(row["config_json"]) if row["config_json"] else {}
    except (TypeError, ValueError):
        return 1
    return int(cfg.get("time_step_minutes", 1) or 1)


def compare_runs(run_ids: list, metric: str, db_path: str = "historian.db") -> dict:
    """metric ∈ {uptime_hours, failure_count, maintenance_count, avg_health}.

    Plan-B §3.2 / §17.5. Unknown metrics raise rather than returning a silent
    zero — Plan C deserves a hard signal when it asks for the wrong thing.
    """
    if metric not in _VALID_METRICS:
        raise ValueError(
            f"Unknown metric {metric!r}; valid options: {sorted(_VALID_METRICS)}"
        )

    conn = connect(db_path)
    results: dict = {}

    for rid in run_ids:
        if metric == "uptime_hours":
            # Count timesteps where ALL 6 components were non-FAILED, then
            # convert to hours. Honors the run's actual time_step_minutes —
            # earlier revision assumed 1 min/tick which silently broke the
            # GA fitness function on coarser sweeps.
            step_min = _time_step_minutes(conn, rid)
            res = conn.execute(
                """
                SELECT count(*) FROM (
                    SELECT t
                    FROM component_states
                    WHERE run_id = ? AND status != 'FAILED'
                    GROUP BY t
                    HAVING count(*) = 6
                )
                """,
                (rid,),
            ).fetchone()
            results[rid] = float(res[0]) * step_min / 60.0

        elif metric == "failure_count":
            res = conn.execute(
                """SELECT count(DISTINCT component_id) FROM component_states
                   WHERE run_id = ? AND status = 'FAILED'""",
                (rid,),
            ).fetchone()
            results[rid] = float(res[0])

        elif metric == "maintenance_count":
            res = conn.execute(
                "SELECT count(*) FROM maintenance_events WHERE run_id = ?",
                (rid,),
            ).fetchone()
            results[rid] = float(res[0])

        elif metric == "avg_health":
            res = conn.execute(
                "SELECT avg(health) FROM component_states WHERE run_id = ?",
                (rid,),
            ).fetchone()
            results[rid] = float(res[0] or 0.0)

    conn.close()
    return results
