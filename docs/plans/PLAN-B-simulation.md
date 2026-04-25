# PLAN B — Simulation & Data Plane

> **Owner:** Developer B
> **Project:** Apollo — HP Metal Jet S100 Digital Co-Pilot (HackUPC 2026)
> **Scope:** Phase 2 "the Clock" + data plane + offline optimization + retrieval index
> **Status:** Build-ready. Three developers run in parallel; this plan is independent of Plan A and Plan C from hour zero via Step 0 mocks.
> **Time budget:** 15 hours, hour-by-hour schedule in §14.

This plan is the single source of truth for everything between the engine (Plan A) and the agent UI (Plan C). It owns the historian, the simulation loop, the 3×3 benchmark grid, the GA optimizer, the counterfactual replay engine, the failure-timeline + obituaries, and the late-interaction retrieval index. Every bullet below is binding. Nothing is deferred.

---

## 1. Goal & success criteria

### 1.1 Functional requirements owned by Plan B

Direct ownership (implementation in this plan):

- **FR-2.1** (PRD §6.2) — configurable fixed-step simulation loop, default 1 simulated minute. Verified by `tests/sim/test_loop_step_size.py`.
- **FR-2.2** (PRD §6.2) — Phase 1 `engine.step()` invoked at every tick. Acceptance: invocation count == time-step count, asserted in `tests/sim/test_invocation_count.py`.
- **FR-2.3** (PRD §6.2) — every state record persisted with timestamp + run_id + driver vector + per-component state. Asserted by `tests/historian/test_persistence_completeness.py`.
- **FR-2.4** (PRD §6.2) — three named scenarios × three policies = nine runs. Verified by `tests/sim/test_3x3_grid.py`.
- **FR-2.5** (PRD §6.2) — historian schema lets Plan C render time-series with explicit failure markers. Schema test in `tests/historian/test_schema.py`. (Visualization is Plan C's; the data contract is ours.)
- **FR-2.6** (PRD §6.2) — per-run failure summary listing component, t_fail, dominant cause. Implemented in B7. Asserted by `tests/policies/test_failure_attribution.py`.
- **FR-2.7** (PRD §6.2) and **NFR-8** (PRD §7) — `(scenario, policy, seed, config_json)` reproducibility, byte-identical historian. Asserted by `tests/sim/test_reproducibility.py`.
- **FR-3.6 — 4 of 5 tools** (PRD §6.3): we ship the implementations for `query_historian`, `late_interaction_search`, `compare_runs`, `run_counterfactual`. Plan C owns `plot_component_history` and the agent-side wrapping; Plan C calls our four functions directly.
- **FR-W.4** (PRD §6.4) — component obituary auto-generated within 5 s of failure event, every claim cited. Implemented in B7.
- **NFR-4** (PRD §7) — late-interaction retrieval p95 < 200 ms over 10k rows on CPU. Benchmarked in `tests/retrieval/test_latency_benchmark.py`.

### 1.2 Differentiation metrics we contribute to

- §16.2 uptime delta ≥ +25 %, target +34 % — produced by the GA-tuned AI policy in B5 against the FIXED policy.
- §16.2 cascading-failure demonstrations ≥ 3 — every NONE run (Dark Twin) drives at least one component to FAILED via CSC-A/B/C; B4 asserts this in `tests/policies/test_dark_twin_kills.py`.
- §16.2 reproducibility — entire historian regenerable from config; B-level test gate.

### 1.3 Done definition (one line)

`make plan_b_demo` rebuilds `historian.db`, `lateon.index`, `ga_fitness.csv`, and `obituaries` from clean in under 45 minutes; every Plan-C-consumed function returns Pydantic-typed payloads against the frozen contracts in §3; all `tests/` suites pass.

---

## 2. ADR map

Every commitment below cross-references the binding ADR. Not negotiable.

| ADR | Title | What we consume / honor |
| --- | --- | --- |
| **ADR-001** | Hybrid rule-based + PINN modeling | We treat Plan A's `step()` as a black box; we do not reach inside the engine. |
| **ADR-002** | Six components, three subsystems | Component IDs hard-coded in the historian schema enum (`blade`, `motor`, `nozzle`, `resistor`, `heater`, `insulation`). |
| **ADR-003** | Three parallel cascades | Failure-attribution logic in B7 inspects the coupling matrix to identify upstream cause for the obituary. |
| **ADR-004** | Linear coupling matrix `M` | Imported from Plan A as `engine.coupling.M`; used in B7 attribution and in the GA fitness function for cascade-aware penalties. |
| **ADR-005** | DeepXDE for heater PINN | Treated as opaque component; Plan A guarantees CPU-deterministic inference for our reproducibility tests (NFR-1). |
| **ADR-006** | Three failure-model families | Plan A-side; we surface the active model in `metrics_json` for retrieval snippets. |
| **ADR-007** | SQLite historian | **Primary ADR for B1.** WAL mode, single file, exact §14 schema. |
| **ADR-010** | Late-interaction retrieval — LateOn-Code-edge + PyLate | **Primary ADR for B8.** 17M params, dim 48, Apache 2.0; offline indexing; R-3 dense fallback. |
| **ADR-011** | GA (DEAP) for maintenance | **Primary ADR for B5.** 7-dim encoding, pop 50 × 50 generations, tournament k=3, blend-α α=0.5, Gaussian σ=0.05 p=0.2. |
| **ADR-012** | Simulator-checkpoint counterfactual | **Primary ADR for B6.** Deepcopy + branch + diff; RNG state in checkpoint; no causal-DAG library. |
| **ADR-013** | Three-scenario benchmark + Dark Twin framing | **Primary ADR for B4.** NONE column renamed "Dark Twin" in run names and obituary text. |
| ADR-014 | Pydantic citations + refusal grounding | Every obituary claim carries `(run_id, component_id, t)`; rows in `obituaries.citations_json` are validated against the same Pydantic schema Plan C uses. |
| ADR-015 | MAPIE conformal prediction | We ship the `forecasts` table; Plan A populates it via `forecast()`. We persist, we do not compute. |
| ADR-019 | Apollo first-person persona | **Obituary template in B7 follows ADR-019 voice:** calm, professional, never alarmist, no exclamation marks. |

ADRs 008, 009, 016, 017, 018, 020 belong to Plan C. We do not touch them.

---

## 3. Integration contracts (frozen)

These signatures are **frozen at hour zero**. Plan A and Plan C build against them. Any change requires a written ADR amendment and a sync with both other developers.

### 3.1 Inbound — what Plan A publishes

```python
# engine/contracts.py — Plan A owns this file
from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel

ComponentId = Literal["blade", "motor", "nozzle", "resistor", "heater", "insulation"]

class ComponentStatus(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"
    DEGRADED   = "DEGRADED"
    CRITICAL   = "CRITICAL"
    FAILED     = "FAILED"

class ComponentState(BaseModel):
    component_id: ComponentId
    health: float                # [0, 1]
    status: ComponentStatus
    metrics: dict                # component-specific scalar metrics

class Drivers(BaseModel):
    t: datetime
    temp_C: float
    humidity: float
    pm25: float
    psd_d50: float
    voltage_stability: float
    operator_shift: Literal["day", "night", "weekend"]

class EngineState(BaseModel):
    components: dict[ComponentId, ComponentState]
    rng_state: bytes             # serialized numpy.random.Generator state (NFR-8, ADR-012)
    accumulated_load: dict       # cycles, hours, etc.

class Forecast(BaseModel):
    horizon_min: int
    point: float
    lower: float
    upper: float
    ci_level: float = 0.95

def step(state: EngineState, drivers: Drivers, dt: float) -> EngineState: ...
def forecast(state: EngineState, horizon_min: int) -> dict[ComponentId, Forecast]: ...
```

Plan A also ships `engine/mock_engine.py` at hour 0 — a stub `step()` that decays health linearly per component and returns valid `EngineState`. This unblocks B from minute one.

### 3.2 Outbound — what Plan C imports from us

These are the four FR-3.6 tool implementations Plan C wraps in Claude Agent SDK tool definitions. **Frozen.**

```python
# sim/contracts.py — Plan B owns this file

from datetime import datetime
from pydantic import BaseModel
from engine.contracts import ComponentId, ComponentStatus

class HistorianRow(BaseModel):
    run_id: str
    t: datetime
    component_id: ComponentId
    health: float
    status: ComponentStatus
    metrics: dict

def query_historian(
    run_id: str,
    component: ComponentId | None,
    time_range: tuple[datetime, datetime],
) -> list[HistorianRow]: ...

def compare_runs(run_ids: list[str], metric: str) -> dict:
    """metric ∈ {'uptime_hours', 'failure_count', 'maintenance_count', 'avg_health'}.
    Returns {run_id: float, ...}. Plan C charts this directly."""

class CounterfactualResult(BaseModel):
    original: list[HistorianRow]
    alternate: list[HistorianRow]
    diff: dict   # {"uptime_delta": float, "failures_avoided": int, "cost_delta": float}

def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict,    # e.g. {"action": "swap_blade", "component_id": "blade"}
) -> CounterfactualResult: ...

class RetrievedRow(BaseModel):
    run_id: str
    component: ComponentId
    t: datetime
    score: float
    snippet: str

def late_interaction_search(
    query: str,
    run_id: str | None = None,
    top_k: int = 10,
) -> list[RetrievedRow]: ...
```

These are FROZEN. Plan C builds against these signatures from hour zero.

### 3.3 Configuration contract

```python
# sim/config.py
from pydantic import BaseModel

class SimulationConfig(BaseModel):
    scenario_name: Literal["barcelona-humid", "phoenix-dry", "stressed"]
    policy: Literal["none", "fixed", "ai"]
    seed: int
    time_step_minutes: int = 1                # FR-2.1
    horizon_minutes: int = 600                # 10-hour print cycle (PRD §2.1)
    historian_path: str = "historian.db"
    config_json: dict = {}                    # NFR-8 reproducibility key
```

`run_id` is deterministic: `f"{scenario_name}-{policy}-seed{seed:04d}"`. Plan C uses these IDs verbatim in URLs.

---

## 4. Mock-first rollout (Step 0 — hour 0–1)

**Rule:** Plan A and Plan C must be unblocked. Every artifact below ships at hour 1, before any "real" implementation.

### 4.1 `sim/mocks/historian_mock.py`

In-memory SQLite (`:memory:`) seeded at import time with **9 fake runs** covering all 3 scenarios × 3 policies. Each run:

- ~600 timesteps (one per simulated minute, matches `horizon_minutes`).
- All 6 components present at every timestep.
- Smooth monotone-ish health decay with seeded jitter — looks plausible on a chart.
- **At least one component reaches FAILED in every NONE run** (asserted in `tests/historian/test_mock_dark_twin.py`).
- FIXED runs trigger calendar maintenance every 90 min.
- AI runs use plausible-looking thresholds.
- Driver vectors filled with synthetic but scenario-consistent values (humid for Barcelona, dry for Phoenix, stressed for Stressed).

Exposes the same `query_historian` / `compare_runs` contract as the real impl. Plan C imports it as:

```python
from sim.mocks.historian_mock import query_historian, compare_runs
```

The real impl drops in transparently when `HISTORIAN_BACKEND=real` env var is set.

### 4.2 `sim/mocks/late_interaction_mock.py`

Hand-tuned `late_interaction_search` returning ranked rows for the canonical demo queries:

- "nozzle clog escalation" → returns nozzle CRITICAL transitions in barcelona-humid runs ranked first.
- "thermal cascade" → returns insulation→heater→nozzle cascade rows in CSC-B order.
- "moment of regret" → returns the latest CRITICAL row before the first FAILED in any run.

Default for any unmatched query: returns the most recent N rows by t. This keeps Plan C's UI smooth even on judge wild-cards before the real index is built.

### 4.3 `sim/mocks/gp_fitness_mock.csv`

Pre-canned 50-generation monotone fitness curve, hand-tuned to look like a real GA evolution: slow start, mid-run jump, plateau. Columns: `generation, best_fitness, mean_fitness, std_fitness`. Plan C's Recharts panel renders this from minute one.

### 4.4 `sim/mocks/counterfactual_mock.py`

Returns plausible `CounterfactualResult` payloads:

- `original` and `alternate` are slices from the mock historian.
- `diff` is computed honestly from those slices (uptime_delta = sum of FUNCTIONAL minutes in alternate − original, etc.).

Plan C's What-If panel works end-to-end against this from hour 1. Real impl swaps in at hour 11.

### 4.5 Hand-off message at hour 1

> "Plans A and C: import from `sim.mocks.*` for now. Real backends arrive at hours 5 (historian), 11 (counterfactual), and 13 (retrieval). All contracts are frozen — your code does not change when we swap."

---

## 5. Workstream B1 — Historian schema + WAL setup

**ADR:** ADR-007. **PRD:** §14, FR-2.3, FR-2.4, FR-2.7, NFR-8.

### 5.1 DDL (exact, verbatim)

`sim/historian/schema.sql`. This is shipped to disk; tests assert byte-equality with `PRAGMA table_info`.

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- Run metadata
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    policy        TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    seed          INTEGER NOT NULL,
    config_json   TEXT NOT NULL
);

-- Driver vector at each timestep
CREATE TABLE IF NOT EXISTS drivers (
    run_id            TEXT NOT NULL,
    t                 TEXT NOT NULL,
    temp_C            REAL NOT NULL,
    humidity          REAL NOT NULL,
    pm25              REAL NOT NULL,
    psd_d50           REAL NOT NULL,
    voltage_stability REAL NOT NULL,
    operator_shift    TEXT NOT NULL,
    PRIMARY KEY (run_id, t),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Component state at each timestep
CREATE TABLE IF NOT EXISTS component_states (
    run_id       TEXT NOT NULL,
    t            TEXT NOT NULL,
    component_id TEXT NOT NULL,
    health       REAL NOT NULL,
    status       TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    PRIMARY KEY (run_id, t, component_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_component_states_run_comp_t
  ON component_states (run_id, component_id, t);

-- Maintenance events
CREATE TABLE IF NOT EXISTS maintenance_events (
    run_id        TEXT NOT NULL,
    t             TEXT NOT NULL,
    component_id  TEXT NOT NULL,
    action        TEXT NOT NULL,
    triggered_by  TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_maint_run_t
  ON maintenance_events (run_id, t);

-- Failure obituaries (FR-W.4)
CREATE TABLE IF NOT EXISTS obituaries (
    run_id          TEXT NOT NULL,
    component_id    TEXT NOT NULL,
    failure_t       TEXT NOT NULL,
    narrative       TEXT NOT NULL,
    citations_json  TEXT NOT NULL,
    PRIMARY KEY (run_id, component_id, failure_t),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Conformal prediction intervals (FR-W.6) — populated by Plan A's forecast()
CREATE TABLE IF NOT EXISTS forecasts (
    run_id       TEXT NOT NULL,
    t            TEXT NOT NULL,
    component_id TEXT NOT NULL,
    horizon_min  INTEGER NOT NULL,
    point        REAL NOT NULL,
    lower        REAL NOT NULL,
    upper        REAL NOT NULL,
    ci_level     REAL NOT NULL,
    PRIMARY KEY (run_id, t, component_id, horizon_min),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

### 5.2 Module layout

```
sim/historian/
  __init__.py
  schema.sql
  connection.py        # connect() opens WAL, sets pragmas, applies schema if missing
  writer.py            # HistorianWriter — buffered batched inserts (1000 rows / commit)
  reader.py            # query_historian, compare_runs, raw queries
  migrations.py        # idempotent — re-running schema.sql is a no-op
```

### 5.3 Tests (`tests/historian/`)

- `test_schema.py` — apply schema to fresh `:memory:` DB, assert table list, primary keys, indexes via `PRAGMA index_list`.
- `test_wal_mode.py` — open file-backed DB, assert `PRAGMA journal_mode` == `wal`.
- `test_persistence_completeness.py` — write 600 ticks × 6 components, assert 3600 rows in `component_states`.
- `test_json_bag_columns.py` — round-trip `metrics_json` and `citations_json` through Python dicts.
- `test_query_by_index.py` — populate 10k rows, run `EXPLAIN QUERY PLAN` on `query_historian` and assert it uses `idx_component_states_run_comp_t`.

```bash
pytest tests/historian/ -v
```

### 5.4 Acceptance checklist

- [ ] `historian.db` opens in DB Browser; all six tables visible.
- [ ] `sqlite3 historian.db "PRAGMA journal_mode;"` returns `wal`.
- [ ] All five historian tests pass.
- [ ] `query_historian` query plan uses the composite index (no full-table scans).

---

## 6. Workstream B2 — Driver providers

**PRD:** §9.1, §9.2; **Risk:** R-7 (offline mode).

### 6.1 Driver Provider layer

```python
# sim/drivers/base.py
class DriverProvider(Protocol):
    def get(self, t: datetime, scenario_name: str, seed: int) -> Drivers: ...
```

Implementations:

| Provider | Source | Mock fallback |
| --- | --- | --- |
| `OpenWeatherProvider` | OpenWeatherMap API (temp_C, humidity) | `MockWeatherProvider` reads `data/weather/{city}.csv` |
| `AirPollutionProvider` | OpenWeather Air Pollution API (pm25) | `MockAirPollutionProvider` reads `data/air/{city}.csv` |
| `PowderPSDProvider` | Synthetic genealogy: D50 = f(powder_age_days, storage_humidity) | Same — already synthetic |
| `OperationalLoadProvider` | Reads from sim state directly | n/a |
| `OperatorShiftProvider` | Mock log: day/night/weekend piecewise from a seeded calendar | n/a |
| `VoltageStabilityProvider` | Synthetic noise model (Gaussian + occasional dropouts) | n/a |

### 6.2 Offline cache (R-7 mitigation)

Pre-demo (hour 4), run `python -m sim.drivers.cache_all` which:
1. Hits OpenWeather for Barcelona and Phoenix for the demo date window.
2. Hits OpenWeather Air Pollution for the same.
3. Persists JSONL to `data/weather/barcelona.csv`, `data/weather/phoenix.csv`, `data/air/barcelona.csv`, `data/air/phoenix.csv`.
4. The Mock providers read these files unconditionally from hour 5 onward.

Demo always uses Mock providers. Live API calls are **off** during the demo to remove R-7 entirely.

### 6.3 Composite provider

```python
class CompositeDriverProvider:
    def get(self, t, scenario_name, seed) -> Drivers:
        # Composes the six sub-providers; returns a fully-populated Drivers
```

Wired by `sim/drivers/factory.py` based on `SimulationConfig`.

### 6.4 Tests (`tests/sim/drivers/`)

- `test_offline_cache.py` — assert all four CSVs exist after `cache_all`, assert deterministic load.
- `test_composite_determinism.py` — same `(t, scenario, seed)` → bit-identical Drivers.
- `test_psd_genealogy.py` — known powder_age × humidity → known D50 (literature-cited band).
- `test_operator_shift.py` — Monday 03:00 → "night", Saturday 14:00 → "weekend".

```bash
pytest tests/sim/drivers/ -v
```

### 6.5 Acceptance checklist

- [ ] `data/weather/*.csv` and `data/air/*.csv` exist and cover demo window.
- [ ] Composite provider returns valid `Drivers` for any `(t, scenario, seed)`.
- [ ] Determinism test green.

---

## 7. Workstream B3 — Simulation loop (the Clock)

**PRD:** §6.2 FR-2.1, FR-2.2, FR-2.3; **ADR:** ADR-007.

### 7.1 Core loop

```python
# sim/loop.py
def run_simulation(cfg: SimulationConfig) -> str:
    """Returns run_id. Writes everything to historian."""
    rng = np.random.default_rng(cfg.seed)
    state = engine.bootstrap(cfg.scenario_name, rng)
    drivers_provider = build_drivers(cfg)
    policy = build_policy(cfg)
    writer = HistorianWriter(cfg.historian_path)

    run_id = f"{cfg.scenario_name}-{cfg.policy}-seed{cfg.seed:04d}"
    writer.upsert_run(run_id, cfg)

    t = start_time(cfg)
    end = t + timedelta(minutes=cfg.horizon_minutes)
    invocation_count = 0

    while t < end:
        drivers = drivers_provider.get(t, cfg.scenario_name, cfg.seed)
        state = engine.step(state, drivers, cfg.time_step_minutes)   # FR-2.2
        invocation_count += 1

        writer.write_drivers(run_id, t, drivers)                     # FR-2.3
        writer.write_component_states(run_id, t, state.components)   # FR-2.3

        action = policy.decide(state, t)
        if action is not None:
            state = engine.apply_maintenance(state, action)
            writer.write_maintenance(run_id, t, action)

        # FR-W.4: failure detection on status transitions
        for cid, comp in state.components.items():
            if comp.status == ComponentStatus.FAILED and not writer.has_obituary(run_id, cid):
                obit = generate_obituary(run_id, cid, t, state, writer)  # B7
                writer.write_obituary(obit)

        t += timedelta(minutes=cfg.time_step_minutes)

    writer.finalize_run(run_id)
    assert invocation_count == cfg.horizon_minutes // cfg.time_step_minutes  # FR-2.2
    return run_id
```

### 7.2 Stable run_id semantics

- `run_id = "{scenario}-{policy}-seed{seed:04d}"`. No timestamp suffix — restart-safe.
- If a run with the same id exists, the loop **rolls forward**: deletes prior rows for that run_id under a transaction, then re-runs. Keeps NFR-8 byte-identical guarantee.

### 7.3 Tests (`tests/sim/`)

- `test_loop_step_size.py` — `time_step=5` → 120 ticks for a 600-min horizon.
- `test_invocation_count.py` — mock `engine.step`, assert call count == tick count.
- `test_persistence_completeness.py` — for any (scenario, policy, seed), expect `horizon * 6` rows in `component_states`.
- `test_run_id_stable.py` — run twice, assert single set of rows, no duplicates.

```bash
pytest tests/sim/test_loop_step_size.py tests/sim/test_invocation_count.py -v
```

### 7.4 Acceptance checklist

- [ ] FR-2.2 invocation-count assertion green on every run.
- [ ] FR-2.3 row counts match `horizon * 6`.
- [ ] Re-running same `(scenario, policy, seed)` produces no row growth.

---

## 8. Workstream B4 — Three scenarios × three policies (the 3×3 grid)

**ADR:** ADR-013 (Dark Twin). **PRD:** §9.3, FR-2.4.

### 8.1 Scenario presets

```yaml
# config/scenarios.yaml
barcelona-humid:
  city: "Barcelona"
  base_humidity: 0.78
  pm25_peak_hours: [12, 18]
  hvac_short_cycle: true
phoenix-dry:
  city: "Phoenix"
  base_humidity: 0.18
  pm25_peak_hours: []
  hvac_short_cycle: false
stressed:
  city: "Synthetic"
  base_humidity: 0.65
  duty_multiplier: 1.6
  psd_degradation_rate: 2.0
  operator_quality: "erratic"
```

Each scenario is a **deterministic driver trajectory** keyed by `(scenario_name, seed)`. Same `(scenario_name, seed)` → same trajectory (asserted in `tests/sim/drivers/test_composite_determinism.py`).

### 8.2 Three policies

```python
# sim/policies/none_policy.py
class NonePolicy:
    def decide(self, state, t): return None      # Dark Twin

# sim/policies/fixed_policy.py
class FixedPolicy:
    def __init__(self, period_minutes: int = 90, component_rotation: list = ALL_SIX): ...
    def decide(self, state, t):
        # Calendar-based; every period, do next-in-rotation maintenance
        ...

# sim/policies/ai_policy.py
class AIPolicy:
    """Loaded thresholds from config/policies.yaml — tuned by GA in B5."""
    def __init__(self, thresholds: dict[ComponentId, float], lookahead_coef: float): ...
    def decide(self, state, t):
        # If any component health < threshold OR
        # forecasted health within lookahead window < 0.4 → maintenance
        ...
```

### 8.3 The 3×3 grid

Run names per ADR-013. Note: NONE = "Dark Twin" in user-facing copy (Plan C handles that), but the database `policy` column stays `none`.

| | NONE (Dark Twin) | FIXED | AI |
| --- | --- | --- | --- |
| **Barcelona-humid** | barcelona-humid-none-seed0042 | barcelona-humid-fixed-seed0042 | barcelona-humid-ai-seed0042 |
| **Phoenix-dry** | phoenix-dry-none-seed0042 | phoenix-dry-fixed-seed0042 | phoenix-dry-ai-seed0042 |
| **Stressed** | stressed-none-seed0042 | stressed-fixed-seed0042 | stressed-ai-seed0042 |

Default `seed=42`. Driver `make build_grid` runs all nine into `historian.db`.

### 8.4 Tests (`tests/policies/`)

- `test_3x3_grid.py` — after `build_grid`, assert exactly 9 rows in `runs` table with the expected ids.
- `test_dark_twin_kills.py` — for each NONE run, assert at least one component reaches FAILED before horizon end (acceptance for FR-2.5).
- `test_policy_ordering.py` — for the same scenario+seed, AI uptime ≥ FIXED uptime ≥ NONE uptime (target +25–34 % delta from FIXED to AI per §16.2).

```bash
pytest tests/policies/ -v
```

### 8.5 Acceptance checklist

- [ ] All 9 runs persisted with stable IDs.
- [ ] Every NONE run has at least one FAILED component (FR-2.5).
- [ ] Policy ordering test passes (AI ≥ FIXED ≥ NONE on uptime).

---

## 9. Workstream B5 — Genetic Algorithm (DEAP)

**ADR:** ADR-011. **PRD:** §11.3, §16.2, FR-2.4 AI policy, FR-W.2.

### 9.1 DEAP setup — exactly per ADR-011

```python
# sim/optimizer/ga.py
import deap.base, deap.creator, deap.tools, deap.algorithms

# Encoding: 7-dim continuous vector
#   indices 0..5 = per-component thresholds (blade, motor, nozzle, resistor, heater, insulation)
#   index   6     = global preventive lookahead coefficient ∈ [0, 1]

POP_SIZE   = 50
N_GEN      = 50
TOURNAMENT = 3
ALPHA      = 0.5      # blend-α crossover
SIGMA      = 0.05     # Gaussian mutation σ
MUT_PROB   = 0.2      # per-gene mutation probability

LAMBDA_COST    = 1.5    # cost-of-maintenance penalty per action
LAMBDA_FAILURE = 50.0   # catastrophic failure penalty per FAILED component
```

### 9.2 Fitness function

```python
def fitness(individual: list[float]) -> tuple[float]:
    thresholds = dict(zip(COMPONENT_IDS, individual[:6]))
    lookahead  = individual[6]
    cfg = SimulationConfig(
        scenario_name="stressed",       # most informative landscape per ADR-011
        policy="ai",
        seed=42,
        config_json={"thresholds": thresholds, "lookahead": lookahead},
    )
    run_id = run_simulation_in_memory(cfg)        # writes to a tmp historian
    uptime = compute_uptime_hours(run_id)
    maint  = count_maintenance_actions(run_id)
    fails  = count_catastrophic_failures(run_id)
    return (uptime - LAMBDA_COST*maint - LAMBDA_FAILURE*fails,)
```

Per-fitness-eval simulation is run **in a tmp historian** (not the main `historian.db`) to keep the demo DB clean. Parallelized via `multiprocessing.Pool` to use all M3 cores.

### 9.3 Hand-tuned seed individual

Population is *not* uniformly random. Individual 0 is the hand-tuned seed:

```python
SEED_INDIVIDUAL = [0.50, 0.55, 0.45, 0.50, 0.55, 0.40, 0.30]
```

This guarantees the GA starts from a working policy and the curve is monotone-ish from generation 1 (R-4 mitigation at the algorithm level).

### 9.4 Generation logging → CSV

```python
# sim/optimizer/log.py
def log_generation(gen: int, pop: list, csv_path: str):
    fits = [ind.fitness.values[0] for ind in pop]
    row = {
        "generation": gen,
        "best_fitness":  max(fits),
        "mean_fitness":  statistics.mean(fits),
        "std_fitness":   statistics.stdev(fits) if len(fits) > 1 else 0.0,
    }
    append_csv(csv_path, row)
```

Output: `data/ga_fitness.csv`. Plan C's Recharts panel reads this verbatim.

### 9.5 Final winner → `config/policies.yaml`

After generation 50, the best individual writes:

```yaml
# config/policies.yaml — generated, do not hand-edit
ai_policy:
  thresholds:
    blade:      0.43
    motor:      0.51
    nozzle:     0.39
    resistor:   0.47
    heater:     0.52
    insulation: 0.36
  lookahead_coef: 0.27
  trained_on:    "stressed-seed0042"
  ga_generation: 50
  best_fitness:  187.3
```

The AI runs in §8 load this file at startup. **The GA must finish before the AI runs in the 3×3 grid run** — schedule in §14 enforces this.

### 9.6 R-4 fallback (Optuna)

If by hour 9 the fitness curve looks flat or jagged, swap in:

```python
# sim/optimizer/optuna_fallback.py
import optuna
def optimize_with_optuna(n_trials=200): ...
```

Same encoding, same fitness, different algorithm. Threshold semantics survive the swap (per ADR-011 contingency). **Not deferred — built but dormant.**

### 9.7 Tests (`tests/policies/ga/`)

- `test_ga_determinism.py` — same DEAP seed → same final individual, byte-identical fitness CSV.
- `test_fitness_function.py` — known individual on tiny scenario → known fitness within ε.
- `test_csv_format.py` — header order + column names match Plan C's expectations.
- `test_optuna_fallback.py` — Optuna path produces a valid `policies.yaml`.

```bash
pytest tests/policies/ga/ -v
```

### 9.8 Acceptance checklist

- [ ] `data/ga_fitness.csv` exists with 50 rows + header.
- [ ] `config/policies.yaml` written, validates against schema.
- [ ] Best fitness in generation 50 ≥ best fitness in generation 1.
- [ ] AI policy run uses thresholds from `config/policies.yaml`, not hardcoded.
- [ ] Optuna fallback path tested end-to-end.

---

## 10. Workstream B6 — Counterfactual replay engine

**ADR:** ADR-012. **PRD:** §11.4, FR-3.6, US-4.

### 10.1 Checkpoint format

Every persisted timestep already has the data needed; the only addition is `rng_state` in `EngineState` (Plan A guarantees this is serializable). Checkpoint = `model_copy(deep=True)` of `EngineState` at timestep `t` + the seeded driver provider (which is itself deterministic given `(scenario_name, seed)`, so we don't need to checkpoint it — only the seed and t).

```python
# sim/counterfactual/checkpoint.py
class Checkpoint(BaseModel):
    run_id: str
    t: datetime
    state: EngineState
    seed: int
    scenario_name: str
    config_json: dict
```

Reconstruction: load the `EngineState` snapshot from history (we pickle it into a sidecar table `checkpoints(run_id, t, state_blob)` if we're re-checkpointing on demand; otherwise we replay the original run from `t=0` to `branch_t` to materialize the state — slower but storage-free).

**Decision:** ship both. For the 9 grid runs, pre-write checkpoints every 10 minutes into a sidecar table `checkpoints`. For ad-hoc requests at non-checkpoint times, replay from the nearest earlier checkpoint forward. ~1 s overhead worst case.

### 10.2 Checkpoint sidecar table

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id     TEXT NOT NULL,
    t          TEXT NOT NULL,
    state_blob BLOB NOT NULL,    -- pickled EngineState
    PRIMARY KEY (run_id, t),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

### 10.3 `run_counterfactual` implementation

```python
def run_counterfactual(
    run_id: str,
    branch_t: datetime,
    alternate_action: dict,
) -> CounterfactualResult:
    cfg = load_config_for_run(run_id)
    cp  = load_or_replay_checkpoint(run_id, branch_t)   # ~1 s
    branched_state = cp.state.model_copy(deep=True)
    branched_state = engine.apply_maintenance(branched_state, alternate_action)

    drivers_provider = build_drivers(cfg)
    alt_rows = []
    t = branch_t
    end = start_time(cfg) + timedelta(minutes=cfg.horizon_minutes)
    while t < end:
        drivers = drivers_provider.get(t, cfg.scenario_name, cfg.seed)
        branched_state = engine.step(branched_state, drivers, cfg.time_step_minutes)
        alt_rows.extend(state_to_rows(run_id + "-cf", t, branched_state))
        t += timedelta(minutes=cfg.time_step_minutes)

    original = query_historian(run_id, None, (branch_t, end))
    diff = compute_diff(original, alt_rows)
    return CounterfactualResult(original=original, alternate=alt_rows, diff=diff)
```

### 10.4 Diff computation

```python
def compute_diff(original: list[HistorianRow], alternate: list[HistorianRow]) -> dict:
    return {
        "uptime_delta":     uptime_minutes(alternate) - uptime_minutes(original),
        "failures_avoided": failure_count(original) - failure_count(alternate),
        "cost_delta":       cost_estimate(alternate) - cost_estimate(original),  # signed
    }
```

### 10.5 Performance budget

Per ADR-012: ~1–3 s for a 6-h tail. We measure in `tests/counterfactual/test_perf.py` and fail the build if any single call exceeds 5 s.

### 10.6 Tests (`tests/counterfactual/`)

- `test_correctness.py` — branching with `action=no-op` at any t reproduces the original timeline byte-for-byte.
- `test_determinism.py` — same `(run_id, branch_t, alternate_action)` called twice → identical `CounterfactualResult`.
- `test_perf.py` — 6-hour tail counterfactual completes in < 5 s on M3 Max CPU.
- `test_diff_signs.py` — known scenarios with known better/worse alternate actions produce correctly-signed diffs.

```bash
pytest tests/counterfactual/ -v
```

### 10.7 Acceptance checklist

- [ ] Counterfactual against `no-op` reproduces original within float tolerance.
- [ ] Same call twice → identical result (NFR-1, NFR-8).
- [ ] p95 latency < 5 s.
- [ ] Plan C What-If panel renders the result.

---

## 11. Workstream B7 — Failure timeline + obituaries

**PRD:** FR-2.6, FR-W.4. **ADR:** ADR-019 (voice), ADR-014 (citation grounding), ADR-003 (cascades), ADR-004 (coupling).

### 11.1 Failure detection

In the simulation loop (§7.1), on every tick we check each component for `status == FAILED` for the first time. `t_fail` = first timestep at which the transition holds.

### 11.2 Dominant-cause attribution (FR-2.6)

For each failed component, walk back ~30 minutes in the historian. Compute a per-suspect score:

```python
def attribute_cause(failed_id, failure_t, run_id, M):
    suspects = []
    # 1. Driver-driven cause
    drivers = query_drivers(run_id, failure_t - 30min, failure_t)
    suspects.append(driver_score(failed_id, drivers))
    # 2. Coupled-component cause (per ADR-004 matrix M)
    for upstream_id in COMPONENT_IDS:
        if M[failed_id][upstream_id] > 0:
            upstream_health = query_history(run_id, upstream_id, ...)
            suspects.append(("coupled", upstream_id, M[failed_id][upstream_id] * (1 - upstream_health.min())))
    return max(suspects, key=lambda s: s.score)
```

Returns `("driver", driver_name)` or `("coupled", upstream_component_id)`. This is the field that lights up the Plan-C UI's failure timeline.

### 11.3 Obituary generation (FR-W.4)

**Template-bounded, not free-form.** Per ADR-019, calm professional voice; per ADR-014, every claim cited.

```python
OBITUARY_TEMPLATE = """\
At {failure_t} during run {run_id}, {component_pretty} crossed the failure threshold (health {health:.2f}). \
The dominant cause was {cause_phrase}. {cascade_sentence} \
The component had been in {prior_status} status since {status_change_t}. {final_sentence}\
"""
```

Filled in by:

```python
def generate_obituary(run_id, component_id, failure_t, state, writer) -> ObituaryRecord:
    cause = attribute_cause(component_id, failure_t, run_id, M)
    citations = [
        Citation(run_id=run_id, component=component_id, t=failure_t),                # the death itself
        Citation(run_id=run_id, component=component_id, t=status_change_t),          # entered prior status
        Citation(run_id=run_id, component=cause.id_or_driver, t=cause.peak_t),       # the cause
    ]
    cascade_sentence = describe_cascade(cause)   # ADR-003 cascade names: CSC-A/B/C
    narrative = OBITUARY_TEMPLATE.format(...)
    return ObituaryRecord(
        run_id=run_id,
        component_id=component_id,
        failure_t=failure_t,
        narrative=narrative,
        citations_json=json.dumps([c.model_dump() for c in citations], default=str),
    )
```

### 11.4 Voice constraints (ADR-019)

- No exclamation marks in narrative — assertion in `test_voice_constraints.py`.
- No first-person pronouns (Apollo persona is in chat; obituaries are third-person post-mortems).
- No theatrical adjectives (`catastrophic`, `disaster`, `dead` → use `terminal`, `non-recoverable`, `failed`).
- Severity is communicated by the cause, not by adjectives.

### 11.5 Citation resolvability

Every entry in `citations_json` must satisfy:

```python
assert query_historian(c.run_id, c.component, (c.t - 1min, c.t + 1min))  # non-empty
```

Asserted in `test_citations_resolvable.py`. Plan C uses these citations for clickable scroll-to-time behavior.

### 11.6 5-second SLA (FR-W.4)

Obituary generation runs synchronously inside the sim loop. Tested with `test_obituary_latency.py` that asserts < 5 s wall clock per generation on M3 Max.

### 11.7 Tests (`tests/policies/obituaries/`)

- `test_failure_attribution.py` — known cascade scenario → expected upstream cause.
- `test_voice_constraints.py` — narrative passes lint (no `!`, no first-person, no banned adjectives).
- `test_citations_resolvable.py` — every citation in every obituary resolves to a live historian row.
- `test_obituary_latency.py` — < 5 s per obituary.

```bash
pytest tests/policies/obituaries/ -v
```

### 11.8 Acceptance checklist

- [ ] Every NONE run produces ≥ 1 obituary.
- [ ] All obituaries pass voice lint.
- [ ] Every citation resolvable in historian.
- [ ] 5-s SLA holds.

---

## 12. Workstream B8 — Late-interaction retrieval index (PyLate + LateOn-Code-edge)

**ADR:** ADR-010. **PRD:** §11.2, FR-3.6 tool 2, NFR-4.

### 12.1 Indexing pipeline

Run **once per benchmark batch** (after the 9-run grid is materialized). Output: `data/lateon.index/` colocated with `historian.db`.

```python
# sim/retrieval/indexer.py
from pylate import indexes, models

def build_index(historian_path: str, index_path: str):
    model = models.ColBERT("lightonai/lateon-code-edge")  # 17M, dim 48, Apache 2.0
    index = indexes.PLAID(index_folder=index_path, override=True)

    rows = stream_historian_rows(historian_path)
    docs, doc_ids = [], []
    for row in rows:
        doc_id = f"{row.run_id}|{row.component_id}|{row.t.isoformat()}"
        snippet = build_snippet(row)
        docs.append(snippet)
        doc_ids.append(doc_id)

    embeddings = model.encode(docs, is_query=False)
    index.add_documents(documents_ids=doc_ids, documents_embeddings=embeddings)
```

### 12.2 Snippet construction

Token-dense, code-like — matching the late-interaction strength per ADR-010:

```
"[run=barcelona-humid-none-seed0042] [component=nozzle] [t=2026-04-25T07:14:00] "
"[status=CRITICAL] [health=0.31] clog_prob=0.61 active_nozzle_count=412 "
"binder_viscosity=2.8 enclosure_temp_C=41.2 [cascade=CSC-B]"
```

### 12.3 Query path

```python
# sim/retrieval/search.py
_model = None
_index = None

def late_interaction_search(query, run_id=None, top_k=10) -> list[RetrievedRow]:
    global _model, _index
    if _model is None:
        _model = models.ColBERT("lightonai/lateon-code-edge")
        _index = indexes.PLAID(index_folder="data/lateon.index", override=False)

    q_emb = _model.encode([query], is_query=True)
    hits = _index.search(queries_embeddings=q_emb, k=top_k * 3)  # over-fetch for filter

    results = []
    for hit in hits[0]:
        run, comp, t_iso = hit.id.split("|")
        if run_id and run != run_id:
            continue
        results.append(RetrievedRow(
            run_id=run, component=comp, t=datetime.fromisoformat(t_iso),
            score=hit.score, snippet=hit.document,
        ))
        if len(results) >= top_k:
            break
    return results
```

### 12.4 NFR-4 latency benchmark

```python
# tests/retrieval/test_latency_benchmark.py
def test_p95_latency():
    queries = load_canonical_queries()  # 100 demo-style queries
    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        late_interaction_search(q, top_k=10)
        latencies.append(time.perf_counter() - t0)
    p95 = sorted(latencies)[int(0.95 * len(latencies))]
    assert p95 < 0.200, f"p95={p95*1000:.1f}ms exceeds NFR-4 budget"
```

10k rows × ~30 tokens × dim 48 ≈ 60 MB index. M3 Max CPU comfortably under 200 ms p95.

### 12.5 R-3 fallback — dense embeddings

```python
# sim/retrieval/dense_fallback.py
def build_dense_index(historian_path, index_path):
    # Voyage-3 or OpenAI text-embedding-3-large
    # Same doc_id format, same RetrievedRow output schema
    ...

def late_interaction_search_dense(query, run_id=None, top_k=10) -> list[RetrievedRow]:
    # Identical signature, identical return type
    ...
```

Wired by env var: `RETRIEVAL_BACKEND=lateon|dense`. Default `lateon`. **Built but dormant** — switching is a 5-second config flip.

### 12.6 Tests (`tests/retrieval/`)

- `test_index_build.py` — given seeded historian → index folder exists, document count matches row count.
- `test_search_returns_typed.py` — every result is a `RetrievedRow`, scores ≥ 0.
- `test_latency_benchmark.py` — p95 < 200 ms on 10k rows.
- `test_run_id_filter.py` — `run_id=X` returns only X-keyed rows.
- `test_dense_fallback.py` — fallback path returns same schema.

```bash
pytest tests/retrieval/ -v
```

### 12.7 Acceptance checklist

- [ ] `data/lateon.index/` exists after `make build_index`.
- [ ] NFR-4 p95 < 200 ms benchmark green.
- [ ] Run-id filter works.
- [ ] Dense fallback tested end-to-end.

---

## 13. Testing strategy

### 13.1 Test taxonomy

| Suite | Path | What it asserts |
| --- | --- | --- |
| Historian | `tests/historian/` | Schema, WAL, persistence completeness, index usage |
| Drivers | `tests/sim/drivers/` | Determinism, offline cache, PSD genealogy |
| Sim loop | `tests/sim/` | FR-2.1, FR-2.2, FR-2.3, FR-2.7 reproducibility |
| Policies | `tests/policies/` | 3×3 grid presence, Dark Twin kills, policy ordering |
| GA | `tests/policies/ga/` | DEAP determinism, fitness, CSV format, Optuna fallback |
| Counterfactual | `tests/counterfactual/` | Correctness, determinism, perf budget, diff signs |
| Obituaries | `tests/policies/obituaries/` | Attribution, voice, citation resolvability, 5-s SLA |
| Retrieval | `tests/retrieval/` | Build, schema, NFR-4 latency, run-id filter, dense fallback |

### 13.2 Critical invariants

- **Reproducibility (FR-2.7, NFR-8):** `make build_grid` twice → byte-identical `historian.db`. Asserted by `tests/sim/test_reproducibility.py` via SHA-256 of the `component_states` table dump.
- **GA determinism:** same `(seed, scenario)` → same final individual to 8 decimal places.
- **Counterfactual correctness:** branch with no-op == original (within float tolerance for the sim's intrinsic stochastic noise contained in seeded RNG).
- **Retrieval latency:** NFR-4 p95 < 200 ms benchmarked on every CI run.

### 13.3 CI invocation

```bash
pytest tests/ -v --tb=short
pytest tests/sim/test_reproducibility.py -v          # critical gate
pytest tests/retrieval/test_latency_benchmark.py -v  # NFR-4 gate
```

### 13.4 Coverage target

≥ 85 % line coverage on `sim/` and `engine/contracts.py` consumers. Measured by `pytest --cov=sim --cov-fail-under=85`.

---

## 14. Hour-by-hour schedule (15 hours)

Tight. Mocks first; real backends swap in transparently.

| Hour | Deliverable | Unblocks |
| --- | --- | --- |
| **0** | Read PRD §6.2, §9, §11.2–4, §14; ADRs 007, 010, 011, 012, 013, 019. Skeleton repo: `sim/`, `tests/`, `config/`, `data/`. | self |
| **0–1** | **Step 0 mocks ship.** `historian_mock.py`, `late_interaction_mock.py`, `gp_fitness_mock.csv`, `counterfactual_mock.py`. Frozen contracts in `sim/contracts.py`. | **Plan A & C from hour 1** |
| **1–2** | B1: `historian/schema.sql`, `connection.py`, `writer.py`, `reader.py`. All 5 historian tests green. | downstream B work |
| **2–3** | B2: Driver providers + offline cache. Hit OpenWeather APIs, persist CSVs. Mock providers wired. | B3 |
| **3–5** | B3: Simulation loop. Wired against Plan A's `mock_engine.py` until A ships real `step()`. **By hour 5, real historian replaces `historian_mock.py` for Plan C.** | Plan C real backend |
| **5–7** | B4: Three scenarios + three policies (NONE, FIXED stub). Build first 6 of 9 grid runs (NONE + FIXED). Dark-Twin-kill test green. | B5 fitness function |
| **7–9** | B5: DEAP GA setup. Fitness on Stressed scenario, multiprocess pool. **GA running by hour 9.** Live fitness CSV emitted. | AI policy real run |
| **9–10** | B5 continued: GA finishes (~30 min), `policies.yaml` written. AI runs (3 of 9) appended to grid. **Full 3×3 grid complete by hour 10.** | retrieval indexer |
| **10–11** | B6: Counterfactual checkpoints sidecar + `run_counterfactual` impl. **By hour 11, real counterfactual replaces `counterfactual_mock.py`.** | Plan C What-If real |
| **11–12** | B7: Obituary generation + failure attribution. ADR-019 voice lint. Backfill obituaries for the 9 grid runs. | Plan C failure timeline |
| **12–13** | B8: PyLate indexer + LateOn-Code-edge model load. Index the 9 runs (~10k rows). NFR-4 latency benchmark green. **By hour 13, real retrieval replaces `late_interaction_mock.py`.** | Plan C agent retrieval real |
| **13–14** | Integration handoff dry-run with Plan A and Plan C. End-to-end smoke: query → search → counterfactual → obituary. | demo path |
| **14–15** | Buffer / R-fallback armament: Optuna swap-in test, dense-embedding swap-in test, offline-cache validation. Final reproducibility gate green. | demo confidence |

Slack: ~1 hour absorbed across hours 14–15. If anything slips, the cut order is: latency benchmark loosened (NFR-4 → 400 ms), then Optuna swap, then dense-embedding swap. **Nothing in scope is cut.**

---

## 15. Risks & mitigations

| ID (PRD §19) | Risk | Mitigation in this plan |
| --- | --- | --- |
| **R-3** | Late-interaction retrieval too slow at demo time | (a) Pre-index offline (no live indexing). (b) NFR-4 benchmark in CI. (c) Dense-embedding fallback (Voyage / OpenAI) built and dormant; switch is one env var (§12.5). (d) Cap historian to ≤ 12k rows by setting horizon to 600 min × 9 runs × 6 components ≈ 32k → only index the latest 10k via row stride if needed. |
| **R-4** | GA fitness landscape ugly / boring curve | (a) Hand-tuned seed individual (§9.3) ensures monotone-ish curve from gen 1. (b) Optuna fallback built and dormant (§9.6). (c) λ_cost / λ_failure tuned in dry-run before real GA. |
| **R-5** | Three-scenario sim too slow live | (a) Pre-run all 9 in `make build_grid` before the demo. (b) Live mode replays from historian at 10× speed (Plan C does the playback; we ship the data). (c) `time_step_minutes` is configurable — bump to 5 if needed. |
| **R-7** | Demo venue Wi-Fi blocks API access | (a) `cache_all` driver script run pre-demo (§6.2). (b) All 9 grid runs use Mock providers reading local CSVs. (c) SQLite is file-based — nothing to dial out for. (d) PyLate model artifact downloaded and cached locally; no HuggingFace round-trip at demo. |
| Misc | Plan A's `step()` not ready when we need it | `mock_engine.py` from Plan A at hour 0 unblocks B3. We pin to that interface exactly; swap is transparent. |
| Misc | Reproducibility leak (NFR-8 fails) | Single source of stochasticity is the seeded `numpy.random.Generator` whose state is checkpointed in `EngineState.rng_state`. Test gate `test_reproducibility.py` runs every CI cycle. |

---

## 16. Definition of done

Verification commands per FR — run them in order and confirm green output.

```bash
# FR-2.1, FR-2.2 (sim loop)
pytest tests/sim/test_loop_step_size.py tests/sim/test_invocation_count.py -v

# FR-2.3 (persistence completeness)
pytest tests/historian/test_persistence_completeness.py -v

# FR-2.4 (3 × 3 grid)
make build_grid
pytest tests/policies/test_3x3_grid.py -v
sqlite3 historian.db "SELECT run_id FROM runs;"   # expect 9 rows

# FR-2.5 (at least one component reaches FAILED in NONE)
pytest tests/policies/test_dark_twin_kills.py -v

# FR-2.6 (failure attribution)
pytest tests/policies/test_failure_attribution.py -v

# FR-2.7, NFR-8 (reproducibility)
make build_grid                                    # run 1
sha256sum historian.db > /tmp/h1
make build_grid                                    # run 2
sha256sum historian.db > /tmp/h2
diff /tmp/h1 /tmp/h2                              # expect no diff

# FR-3.6 tool implementations (the four we own)
python -c "from sim.contracts import query_historian, compare_runs, run_counterfactual, late_interaction_search; print('OK')"

# FR-W.4 (obituaries)
pytest tests/policies/obituaries/ -v
sqlite3 historian.db "SELECT COUNT(*) FROM obituaries;"  # expect ≥ 3 (one per Dark Twin run)

# NFR-4 (retrieval latency)
pytest tests/retrieval/test_latency_benchmark.py -v

# Full suite + coverage gate
pytest tests/ --cov=sim --cov-fail-under=85
```

Plan B is **done** when:
- [ ] All commands above exit 0.
- [ ] `historian.db` has 9 runs, all 6 tables populated.
- [ ] `data/ga_fitness.csv` has 51 rows (header + 50 generations).
- [ ] `config/policies.yaml` exists and is loadable.
- [ ] `data/lateon.index/` exists and serves queries < 200 ms p95.
- [ ] Plan C's demo flow (chat → tool call → grounded answer with citations) works against our real backends end-to-end.
- [ ] Reproducibility hash-diff is empty across two builds.
- [ ] Every Dark Twin run has at least one obituary, every obituary has resolvable citations, and every narrative passes voice lint per ADR-019.

This plan is binding. Developer B owns every line above. No deferrals.
