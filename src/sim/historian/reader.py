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

def compare_runs(run_ids: list[str], metric: str, db_path: str = "historian.db") -> dict[str, float]:
    conn = connect(db_path)
    results = {}
    
    for rid in run_ids:
        if metric == "uptime_hours":
            # count steps where no component is FAILED
            # This is a bit simplified: we count unique timestamps in component_states where all 6 components for that t are not FAILED
            # Actually, simpler: count minutes where the run was active and no component failed yet?
            # Let's use the FR-2.1 definition: fixed-step simulation loop.
            res = conn.execute("""
                SELECT count(distinct t) as functional_minutes
                FROM component_states
                WHERE run_id = ? AND status != 'FAILED'
                GROUP BY t
                HAVING count(*) = 6
            """, (rid,)).fetchall()
            results[rid] = len(res) / 60.0
            
        elif metric == "failure_count":
            res = conn.execute("""
                SELECT count(DISTINCT component_id) FROM component_states
                WHERE run_id = ? AND status = 'FAILED'
            """, (rid,)).fetchone()
            results[rid] = float(res[0])

        elif metric == "maintenance_count":
            res = conn.execute("""
                SELECT count(*) FROM maintenance_events
                WHERE run_id = ?
            """, (rid,)).fetchone()
            results[rid] = float(res[0])
            
        elif metric == "avg_health":
            res = conn.execute("""
                SELECT avg(health) FROM component_states
                WHERE run_id = ?
            """, (rid,)).fetchone()
            results[rid] = float(res[0] or 0.0)
            
        else:
            results[rid] = 0.0
            
    conn.close()
    return results
