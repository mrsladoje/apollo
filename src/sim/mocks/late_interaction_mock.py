from datetime import datetime, timedelta
from engine.contracts import ComponentId
from sim.contracts import RetrievedRow

def late_interaction_search(
    query: str,
    run_id: str | None = None,
    top_k: int = 10,
) -> list[RetrievedRow]:
    query = query.lower()
    results = []
    
    base_time = datetime(2026, 4, 25, 8, 0, 0)
    
    if "nozzle clog" in query:
        results.append(RetrievedRow(
            run_id="barcelona-humid-none-seed0042",
            component=ComponentId.NOZZLE,
            t=base_time + timedelta(minutes=450),
            score=0.98,
            snippet="Humidity spike to 85% preceded nozzle pressure oscillation. Health dropped to 0.12 (CRITICAL)."
        ))
    elif "thermal cascade" in query:
        results.append(RetrievedRow(
            run_id="stressed-none-seed0042",
            component=ComponentId.INSULATION,
            t=base_time + timedelta(minutes=200),
            score=0.95,
            snippet="Insulation degradation detected. Temperature at heater interface rising above nominal."
        ))
        results.append(RetrievedRow(
            run_id="stressed-none-seed0042",
            component=ComponentId.HEATER,
            t=base_time + timedelta(minutes=210),
            score=0.92,
            snippet="Heater compensating for heat loss. Power draw increased 15%."
        ))
    elif "moment of regret" in query:
        results.append(RetrievedRow(
            run_id="phoenix-dry-none-seed0042",
            component=ComponentId.MOTOR,
            t=base_time + timedelta(minutes=549),
            score=0.99,
            snippet="Last stable reading before catastrophic motor seizure. Maintenance was overdue by 120 minutes."
        ))
    
    # Fallback: return generic results if empty or to fill top_k
    if not results:
        results.append(RetrievedRow(
            run_id=run_id or "default-run",
            component=ComponentId.BLADE,
            t=base_time,
            score=0.5,
            snippet=f"Generic sensor reading for query: {query}"
        ))
        
    return results[:top_k]
