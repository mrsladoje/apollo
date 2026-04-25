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

-- Checkpoint sidecar table (ADR-012)
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id     TEXT NOT NULL,
    t          TEXT NOT NULL,
    state_blob BLOB NOT NULL,    -- pickled EngineState
    PRIMARY KEY (run_id, t),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
