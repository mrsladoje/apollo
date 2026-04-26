# ADR-007: SQLite as the historian

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §14 (Data Model), §6.2 (Phase 2), FR-2.3, FR-2.4, FR-2.7

## Context

Phase 2 of Apollo writes a State Report for every component at every simulated minute, plus driver vectors, maintenance events, obituaries, and conformal forecasts. Across three scenarios × three policies × ~600 simulated minutes × 6 components, we produce on the order of 30k+ component-state rows per full benchmark batch. The historian is read by the agent at query time (FR-3.2) — every Apollo answer issues at least one `query_historian` tool call — so query latency matters for the < 6 s p95 agent response budget (NFR-5).

The store is also touched by the late-interaction indexer (PyLate) offline, the GA fitness function during training, and the React frontend during replay. This is a multi-reader, single-writer workload at small scale. We are inside a 36-hour hackathon with no DevOps slack: any database that requires its own process, container, or schema-migration tooling is a tax we cannot afford.

The judging surface is also unusual. HP judges will look at the repo. A `historian.db` file they can open with `sqlite3` or DB Browser is a feature, not a bug — it makes the system inspectable without docker compose.

## Decision

Persist the historian to a single **SQLite** file (`historian.db`), accessed via Python's stdlib `sqlite3` driver with WAL mode enabled for concurrent reads during writes. Schema follows PRD §14 plus ADR-012's counterfactual checkpoint sidecar: `runs`, `drivers`, `component_states`, `maintenance_events`, `obituaries`, `forecasts`, and `checkpoints`, with composite primary keys on `(run_id, t)`, `(run_id, t, component_id)`, and checkpoint `(run_id, t)` and explicit indexes on `(run_id, component_id, t)` to match the agent's typical query patterns. JSON-bag columns (`metrics_json`, `config_json`, `citations_json`) hold component-specific or evolving fields without schema churn.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **PostgreSQL** | Operational overhead — separate process, port management, role/schema setup. No multi-tenant or write-concurrency need that justifies it for a single-machine demo. |
| **DuckDB** | Genuinely attractive for analytical scans, but its agentic-SQL story and Python-driver maturity are still behind sqlite3, and we don't need its column-store wins at 30k rows. New tool risk inside a 36 h window. |
| **InfluxDB / TimescaleDB** | Time-series-first, but heavyweight: extra service, retention policies, continuous aggregates we won't use. Our queries are point-lookups by `(run_id, component_id, t)`, not time-window aggregations over millions of rows. |
| **Parquet files + DuckDB on top** | Forces us to build an append story (rewrite or partition) for live simulation. SQLite's row-level inserts are simpler for the loop in §13. |
| **In-memory dict + pickled snapshots** | Loses queryability — the agent's `query_historian` becomes ad-hoc Python instead of declarative SQL. Kills the FR-3.2 tool-call demo. |

## Consequences

**Positive:**
- Zero deployment friction. `pip install` is enough; the file is the database.
- Inspectable by judges: `sqlite3 historian.db ".schema"` works on any laptop.
- `sqlite3` is in the Python stdlib — one fewer dep to break at the venue.
- WAL mode permits simulator writes and frontend reads concurrently with negligible contention at our scale.
- Reproducibility (NFR-8): the entire historian for a `(scenario, policy, seed)` triple is one file we can commit to a fixtures branch.

**Negative / accepted tradeoffs:**
- Single-writer. If we ever wanted to run the three scenarios truly concurrently in the same process they would serialize at the writer. We mitigate by running them as separate sub-processes, each with its own DB file, then merging — but in practice we run them sequentially.
- No native time-series compression or downsampling. At our row counts this is a non-issue; at fleet scale it would be.
- JSON-bag columns are not indexable. We accept this for `metrics_json` because per-component metrics are queried *after* filtering by `(run_id, component_id, t)`.

**Neutral / mitigations:**
- If a future iteration needs distributed access, SQLite → Postgres is a well-trodden migration; the schema is portable.
- The `forecasts` table (FR-W.6) was added late; its key `(run_id, t, component_id, horizon_min)` keeps MAPIE intervals colocated with the state row they predict from.

## References

- PRD §14 (Data Model), §6.2 (FR-2.3, FR-2.4, FR-2.7), §13 (Architecture)
- SQLite WAL mode: <https://sqlite.org/wal.html>
- Appendix B decision log entry confirming SQLite as persistence choice
