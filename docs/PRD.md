# PRD — HP Metal Jet S100 Digital Co-Pilot ("Apollo")

## 0. Document Control

| Field | Value |
| --- | --- |
| **Document** | Product Requirements Document |
| **Project** | "Apollo" — Digital Co-Pilot for HP Metal Jet S100 |
| **Hackathon** | HackUPC 2026 — HP "When AI meets reality" challenge |
| **Version** | 1.1 |
| **Status** | Build-ready draft |
| **Last updated** | 2026-04-25 |
| **Owner** | mrsladoje |
| **Source brief** | `task/hackathon.md`, `task/stage1.md`, `task/stage2.md`, `task/stage3.md`, `task/20260423-HP-Briefing.pdf` |

---

## 1. Executive Summary

**Apollo** is a Digital Co-Pilot for the HP Metal Jet S100 metal binder-jetting printer. It combines a physics-grounded simulation of cascading component degradation, an autonomous maintenance policy, and an agentic AI interface that diagnoses failures with timestamped citations.

The product targets the gap the brief identifies: as industrial hardware grows more sophisticated, operators can no longer rely on dashboards or reactive maintenance. Apollo fills that gap by *communicating* — predicting failure, explaining root cause, recommending action, and answering *"what if we'd intervened earlier."*

**Demo headline:** "Six components across three subsystems, three coupled cascades, a physics-informed neural surrogate for the heater, an agentic copilot citing every claim, and +34 % uptime vs. a fixed maintenance schedule."

**Differentiation thesis:** Apollo should stand out from generic AI dashboards by making **the physics legible**, **the cascades real**, and **the AI's reasoning visible**.

---

## 2. Problem Statement

### 2.1 Context

The HP Metal Jet S100 is a binder-jetting metal printer with thermal-inkjet nozzles, print bars, and multi-stage post-processing (curing, sintering). For demo framing, Apollo assumes a typical print cycle of ~10 hours and uses conservative cost estimates for failed batches, blade replacement, and unplanned downtime. Final euro figures must be cited in the technical report and slide speaker notes before presentation.

### 2.2 Pain points

1. **Operators cannot detect cascading failures.** A degrading insulation panel raises heater duty, which heats the enclosure, which raises binder viscosity, which clogs nozzles. By the time the dashboard alarms on the nozzle, the cascade has been running for hours. Humans don't watch six telemetry streams at once.
2. **Maintenance is reactive or fixed-schedule.** Both are wasteful. Reactive ⇒ downtime; fixed ⇒ unnecessary intervention.
3. **Failure diagnosis happens after the fact, manually.** Engineers piece together logs by hand. Root cause is often misattributed to the *terminal* component instead of the *upstream* one.
4. **AI tools that exist hallucinate.** Generic LLM dashboards either invent answers or cannot ground claims to specific data points — a non-starter for industrial operations.

### 2.3 Why now

Three capabilities matured in 2025/2026 that make this product feasible: agentic LLMs with reliable tool-use, late-interaction retrieval models small enough for CPU inference, and physics-informed neural networks trainable on commodity hardware.

---

## 3. Goals & Non-Goals

### 3.1 Goals (must-have for submission)

- **G-1** Model at least one component per subsystem (Recoating, Printhead, Thermal) with at least one input driver each. *(per brief, Phase 1)*
- **G-2** Apply ≥ 2 standard mathematical failure models. *(per brief, Phase 1)*
- **G-3** Run a continuous time-advancing simulation that calls the Phase 1 engine and persists state to a queryable historian. *(per brief, Phase 2)*
- **G-4** Visualize component health evolving over simulated time, with at least one component reaching `FAILED`. *(per brief, Phase 2)*
- **G-5** Provide a data-grounded conversational interface where every answer cites a specific data point and never hallucinates. *(per brief, Phase 3)*
- **G-6** Demonstrate measurable uptime improvement of an AI maintenance policy over a fixed schedule. *(differentiation)*

### 3.2 Stretch goals (target if time permits)

- **G-7** Cross-subsystem cascading failures with explicit physical coupling (Cascade B).
- **G-8** Counterfactual replay ("what-if" the maintenance had been triggered earlier).
- **G-9** Apollo personification, component obituaries, and "Dark Twin" framing in the demo.

### 3.3 MVP release scope

The hackathon MVP is considered complete when the system can run end-to-end through Phase 1 + Phase 2 and can demonstrate at least one grounded Phase 3 diagnostic flow.

| Scope | Included in MVP | Deferred unless time permits |
| --- | --- | --- |
| Component models | Six components, three subsystems, health/status/metrics | Additional optional components such as rails, sensors, cleaning interface |
| Failure models | Exponential, Weibull, Coffin-Manson | Additional stochastic shock models beyond seeded scenario noise |
| Cascades | Matrix coupling + CSC-B explicit physical relationships | More than three cascade families |
| Simulation | Three named scenarios and three policies persisted to SQLite | Fleet-scale simulation |
| AI interface | Text chat, visible tool calls, timestamped citations, refusal behavior | Voice, persona switching, external ticketing/work-order integration |
| Optimization | GA threshold tuning and fixed/none comparison | RL maintenance agent |
| Demo polish | Apollo persona, Dark Twin comparison, what-if replay | Photoreal 3-D twin |

### 3.4 Non-goals

- Integration with physical HP hardware *(explicitly out of scope per brief §4)*.
- Voice / audio interface.
- 3-D photoreal rendering of the printer.
- Reinforcement-learning maintenance policy.
- Custom Metal/CoreML kernels for the PINN.
- Multi-printer fleet view.
- Production-grade authentication, multi-tenancy, deployment automation.

---

## 4. Personas

| ID | Persona | Role | Primary need |
| --- | --- | --- | --- |
| P-1 | **Mara**, line operator (shift 2) | Watches the printer during a 10-hr cycle; triggers maintenance | Plain-language status; clear "should I act now?" signals |
| P-2 | **Diego**, maintenance engineer | Reviews logs after a failure to determine root cause | Cited evidence; counterfactual reasoning |
| P-3 | **Petra**, plant CFO | Quarterly fleet-uptime and TCO review | Money figures; uptime % deltas |

The Apollo experience must be legible to all three personas from the same underlying telemetry.

---

## 5. User Stories

- **US-1** *(P-1)* As an operator, I ask Apollo "how is the printer doing?" and get a calm, first-person summary citing the most recent telemetry, so I can decide whether immediate attention is needed.
- **US-2** *(P-1)* As an operator, when a component crosses CRITICAL, Apollo proactively explains the cascade behind it and recommends a specific intervention, so I act on cause not symptom.
- **US-3** *(P-2)* As a maintenance engineer, I ask "why did the printhead start failing around hour 7 in the Barcelona run?" and Apollo retrieves the relevant historian rows, traces the cascade, and answers with timestamped citations.
- **US-4** *(P-2)* As a maintenance engineer, I select a "moment of regret" and ask "what if we'd swapped the blade at 04:00 instead?" — Apollo replays the simulation with the alternate decision and shows the uptime delta.
- **US-5** *(P-3)* As a CFO, I see a single screen comparing three universes (no-copilot, fixed schedule, Apollo) with a cumulative-uptime chart and a single euro-denominated savings number.
- **US-6** *(P-2)* As a maintenance engineer, after a component fails I read its auto-generated *obituary* — a one-paragraph narrative post-mortem with citations — to understand what killed it.

---

## 6. Functional Requirements

### 6.1 Phase 1 — Logic Engine (the Brain)

| ID | Requirement | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| **FR-1.1** | The engine SHALL model six components across three subsystems (see §8). | MUST | Six components instantiable with declared state; each subsystem has ≥ 1 component. |
| **FR-1.2** | Each component SHALL accept at least one input driver from §9. | MUST | Per-component unit test asserts driver-dependent state change. |
| **FR-1.3** | The engine SHALL apply at least three distinct mathematical failure models: exponential decay, Weibull, Coffin-Manson thermal fatigue. | MUST | Each model is unit-tested with known-input known-output cases. |
| **FR-1.4** | The engine SHALL produce a structured State Report per component containing `health ∈ [0,1]`, `status ∈ {FUNCTIONAL, DEGRADED, CRITICAL, FAILED}`, and component-specific metrics. | MUST | Output validated against a Pydantic schema. |
| **FR-1.5** | The engine SHALL be deterministic — same `(state, drivers, dt)` ⇒ same output. | MUST | Two runs with identical inputs produce byte-identical outputs. Stochastic scenarios use seeded RNG. |
| **FR-1.6** | The engine SHALL implement cross-component coupling via a linear coupling matrix `M`. | MUST | `M_ij` documented; one component's degradation measurably accelerates a coupled component. |
| **FR-1.7** | The Heating Element model SHALL be implemented as a Physics-Informed Neural Network (DeepXDE), enforcing 1-D heat-diffusion PDE residuals in the loss. | SHOULD | Trained model artifact present; inference < 5 ms CPU; pitch-defensible PDE residual term. |
| **FR-1.8** | The engine SHALL expose a single callable interface `step(state, drivers, dt) -> state` for invocation by Phase 2. | MUST | Interface signature stable across subsystems. |

### 6.2 Phase 2 — Simulation Loop & Historian

| ID | Requirement | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| **FR-2.1** | The simulation loop SHALL advance time at a configurable fixed step (default 1 simulated minute). | MUST | Configurable via `SimulationConfig.time_step`. |
| **FR-2.2** | The loop SHALL call the Phase 1 engine at every time step. | MUST | Phase 1 invocation count == time-step count. |
| **FR-2.3** | The historian SHALL persist every state record with a timestamp, run id, full driver vector, and per-component state. | MUST | SQLite tables `runs`, `drivers`, `component_states`, `maintenance_events` populated; queryable by time range, component, and run id. |
| **FR-2.4** | The system SHALL support at least three named scenarios (Barcelona-humid, Phoenix-dry, Stressed) and three maintenance policies (NONE, FIXED, AI). | MUST | All nine combinations runnable; each persisted with a unique `run_id`. |
| **FR-2.5** | The system SHALL render a time-series visualization of component health per run, with explicit failure markers. | MUST | Three runs renderable side-by-side; at least one component reaches `FAILED`. |
| **FR-2.6** | The simulation SHALL identify *when* and *why* each component failed in a run. | MUST | Per-run failure summary report listing component, t_fail, dominant cause (driver or coupled component). |
| **FR-2.7** | A scenario SHALL be reproducible from its `(scenario_name, seed, config_json)` tuple. | MUST | Same triple ⇒ same historian rows. |

### 6.3 Phase 3 — Agentic Co-Pilot

| ID | Requirement | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| **FR-3.1** | The interface SHALL accept natural-language text queries. | MUST | Chat input field; queries dispatched to agent loop. |
| **FR-3.2** | The agent SHALL retrieve telemetry from the Phase 2 historian via tool calls before answering — not from training memory. | MUST | All non-trivial answers preceded by ≥ 1 tool invocation; tool-call audit log inspectable. |
| **FR-3.3** | Every response SHALL include explicit evidence citations: `(run_id, component, timestamp)`. | MUST | Citation schema validated; responses without citations are rejected by the response-validation layer. |
| **FR-3.4** | Every response SHALL carry a severity tag: `INFO | WARNING | CRITICAL`. | MUST | Tag present on every response. |
| **FR-3.5** | The agent SHALL refuse to answer (with a structured refusal template) when no supporting telemetry exists, instead of hallucinating. | MUST | "Unanswerable" eval set returns refusals 100 % of the time. |
| **FR-3.6** | The agent SHALL expose at least the following tools: `query_historian`, `late_interaction_search`, `compare_runs`, `run_counterfactual`, `plot_component_history`. | MUST | All tools callable; schemas typed. |
| **FR-3.7** | Tool calls SHALL be visible in the UI (input + output, collapsed by default, expandable). | MUST | UI inspection during demo confirms visible tool trace. |
| **FR-3.8** | Citation timestamps in chat responses SHALL be clickable; clicking scrolls the corresponding chart to that moment. | SHOULD | Click handler wired; chart scrolls within 100 ms. |

### 6.4 Demo-Differentiator Features

| ID | Feature | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| **FR-W.1** | **Apollo persona** — the agent and component voices use a consistent first-person personality (calm, professional, never alarmist). | SHOULD | Persona system prompt loaded; component `speak()` methods return first-person strings. |
| **FR-W.2** | **Dark Twin framing** — the three policies are presented as Universe A/B/C with a side-by-side cumulative-uptime chart and a single euro-denominated headline. | SHOULD | Chart present in dashboard; headline rendered. |
| **FR-W.3** | **Savings slide** — closing demo slide presents a defensible per-printer annual savings estimate derived from sim deltas + public AM cost references. | SHOULD | Slide present in deck; sources noted in speaker notes; estimate clearly labeled as modeled savings. |
| **FR-W.4** | **Component obituary** — when any component transitions to `FAILED`, the system auto-generates a narrative one-paragraph post-mortem stored in the `obituaries` table and surfaced in the UI failure timeline. | SHOULD | Obituary generated within 5 s of failure event; every claim carries a citation. |
| **FR-W.5** | **Live "Ask Apollo"** — final demo segment supports unscripted live judge questions with grounded answers (or refusals when ungrounded). | SHOULD | Dry-run with 10 wild-card questions: 0 hallucinations. |
| **FR-W.6** | **Conformal prediction intervals on health forecasts** — every RUL / time-to-failure prediction surfaces a calibrated confidence interval (e.g. `8.0 h ± 2.3 h, 95% CI`) using MAPIE 1.3 wrapped over the existing decay/PINN predictors. | SHOULD | Shaded prediction band rendered on Recharts; coverage validated empirically on a held-out scenario (≥ 90% empirical coverage on a 95% nominal CI). |
| **FR-W.7** | **Agent observability via Langfuse** — every agent invocation, tool call, latency and token usage is captured by Langfuse through the official Claude Agent SDK OpenTelemetry integration. | SHOULD | `LANGSMITH_OTEL_ENABLED=true`; Langfuse trace UI shows a complete tool-call timeline for the canonical demo query; live trace shown side-by-side during demo. |
| **FR-W.8** | **Streaming agent responses (SSE)** — the agent narrates token-by-token and emits structured events (`tool-call-start`, `tool-result`, `text-delta`) over Server-Sent Events. | SHOULD | `sse-starlette` `EventSourceResponse` stream consumed by the React client; tool calls visible in the chat panel as they execute, not only after completion. |
| **FR-W.9** | **Automated grounding eval** — a 30-question evaluation set generated via Ragas `TestsetGenerator` is scored by DeepEval `FaithfulnessMetric` + `HallucinationMetric` in a CI script; the resulting score is rendered in the README. | SHOULD | `deepeval test run` exits 0; faithfulness ≥ 0.95; hallucination = 0; eval set committed under `tests/eval/`. |
| **FR-W.10** | **GEPA-compiled system prompt** — Apollo's runtime system prompt is compiled offline by `dspy.GEPA` (Agrawal et al., ICLR 2026 Oral) over the FR-W.9 eval set, with Gemma 4 31B as student LM and Claude Opus 4.7 (via the local `claude` Bash CLI) as reflection LM. Compiled prompt is committed as a frozen artifact. *(ADR-022)* | SHOULD | `scripts/agent/compile_prompt.py` produces `config/agent.system_prompt.gepa.txt`; GEPA optimization log committed under `docs/eval/gepa_compile_log.json`; runtime agent loads the compiled prompt at startup. |
| **FR-W.11** | **Three-way grounding eval comparison** — the FR-W.9 eval is run against three configurations: vanilla Claude Opus 4.7, vanilla Gemma 4 31B, and Gemma 4 31B + GEPA-compiled prompt. Results render on the closing demo slide as a measured artifact. *(ADR-022, MLH "Best Use of Gemma" / HP narrative)* | SHOULD | All three runs logged under `docs/eval/comparison_results.json`; faithfulness + hallucination scores per config; demo slide quotes the table verbatim; the GEPA-Gemma config is within 2pp of (or beats) the Opus 4.7 baseline on faithfulness. |

---

## 7. Non-Functional Requirements

| ID | Requirement | Target |
| --- | --- | --- |
| **NFR-1** | Determinism (Phase 1) | Bit-identical outputs for identical inputs; seeded RNG for stochastic scenarios. |
| **NFR-2** | Phase 1 step latency | < 50 ms per `step()` call for all 6 components on M3 Max CPU. |
| **NFR-3** | PINN inference latency | < 5 ms per call on CPU. |
| **NFR-4** | Late-interaction retrieval latency | < 200 ms p95 over a 10 k-row historian. |
| **NFR-5** | Agent response latency | < 6 s p95 end-to-end (including tool calls) for typical diagnostic queries. |
| **NFR-6** | Hallucination rate | 0 % on the curated 30-question evaluation set; refusal acceptable when telemetry is missing. |
| **NFR-7** | Citation coverage | 100 % of non-refusal responses include ≥ 1 valid citation. |
| **NFR-8** | Reproducibility | Any historian row reproducible from `(scenario_name, policy, seed, config_json)`. |
| **NFR-9** | Demo robustness | All three scenarios pre-runnable; live mode is the *second* demo step, not the first. |
| **NFR-10** | Ethical disclosure | Synthetic data origin disclosed in demo and report; no false claims of proprietary HP data. |

---

## 8. Component Model

Six components across three mandatory subsystems. Each is governed by an intrinsic decay model + coupling contributions from `M`.

| # | Subsystem | Component | Failure model(s) | Key drivers | State outputs |
| - | --- | --- | --- | --- | --- |
| 1 | Recoating | **Recoater Blade** | Exponential decay (height loss) + impact-event Weibull | Powder PSD, ambient PM2.5, blade-passes counter | `health`, `blade_thickness_mm`, `status` |
| 2 | Recoating | **Drive Motor** | Weibull bearing fatigue | Grid voltage stability, total cycles, vibration | `health`, `current_draw_A`, `bearing_temp_C`, `status` |
| 3 | Printhead | **Nozzle Plate** | Weibull clogging probability | Binder viscosity (humidity-driven), powder dust, temp | `health`, `clog_prob`, `active_nozzle_count`, `status` |
| 4 | Printhead | **Thermal Firing Resistors** | Coffin-Manson thermal fatigue | Duty cycle, ambient temp, voltage | `health`, `resistance_pct`, `status` |
| 5 | Thermal | **Heating Element** *(PINN)* | Coffin-Manson + 1-D heat-diffusion PINN | HVAC short-cycling, ambient temp, duty hours | `health`, `predicted_temp_field`, `drift_pct`, `status` |
| 6 | Thermal | **Insulation Panel** | Exponential decay (k_eff loss) | Cumulative heat exposure, age | `health`, `k_eff_W_mK`, `status` |

**Status enum:** `FUNCTIONAL → DEGRADED → CRITICAL → FAILED`. Thresholds: `health ≥ 0.7` → FUNCTIONAL, `0.4 ≤ h < 0.7` → DEGRADED, `0.1 ≤ h < 0.4` → CRITICAL, `h < 0.1` → FAILED.

---

## 9. Driver Specifications

### 9.1 Mandatory drivers (per brief)

Temperature stress, humidity / contamination, operational load, maintenance level.

### 9.2 Concrete realization

| Driver | Source | Refresh rate | Notes |
| --- | --- | --- | --- |
| Ambient temperature | OpenWeatherMap API | 1 min interp | Drives heater duty + binder viscosity |
| Humidity / dewpoint | OpenWeatherMap API | 1 min interp | Drives binder viscosity → nozzle clog |
| PM2.5 (air quality) | OpenWeather Air Pollution / AirNow | 1 min interp | Drives blade & nozzle contamination |
| Powder PSD (D10/D50/D90) | Synthetic genealogy model (powder age × storage humidity) | per print run | Strongest causal lever for blade wear |
| Operational load (cycles, hours) | Simulation state | each step | — |
| Maintenance level | Simulation state | each step | Reset by maintenance actions |
| Operator shift pattern | Mock log (day/night/weekend) | piecewise | Affects maintenance quality randomly |
| Grid voltage stability *(optional)* | Synthetic noise model | 1 min | Drives motor / resistor stress |

### 9.3 Scenario presets

- **Barcelona-humid** — coastal humid factory floor, daily PM2.5 peaks, weekend HVAC short-cycling
- **Phoenix-dry** — climate-controlled lab, low humidity, stable grid
- **Stressed** — high duty + degraded powder PSD + erratic operator shift

---

## 10. Coupling & Cascade Specification

### 10.1 Default coupling — linear matrix

```
dH_i/dt = -α_i · f(drivers_i)  -  Σ_j  M_ij · (1 - H_j)
```
where `H_i ∈ [0,1]` is component i's health, `α_i` is its intrinsic decay coefficient, and `M_ij` is the coupling weight from j to i.

Initial coupling matrix (rows = "what affects me"):

```
                Blade  Motor  Nozzle  Resist  Heater  Insul
Blade            —     0     0       0       0       0
Motor           0.4    —     0       0       0       0
Nozzle          0.2    0     —       0       0.3     0
Resistor        0      0     0.1     —       0.2     0
Heater          0      0     0       0       —       0.5
Insulation      0      0     0       0       0       —
```

### 10.2 Three parallel cascades

| ID | Name | Path |
| --- | --- | --- |
| **CSC-A** | Recoating loop *(intra-subsystem)* | Blade wear ↑ → powder bed unevenness ↑ → motor torque ↑ → bearing fatigue ↑ |
| **CSC-B** | Thermal-Printhead loop *(cross-subsystem, demo showpiece)* | Insulation degradation → heater duty ↑ → enclosure temp ↑ → binder viscosity ↑ → nozzle clog ↑ → resistor stress ↑ |
| **CSC-C** | Powder contamination loop | Blade ceramic flaking → powder contamination ↑ → nozzle clog ↑ |

**CSC-B** is modeled with explicit physical relationships *on top of* the matrix: Arrhenius-style binder viscosity vs. temp; Coffin-Manson thermal fatigue cycles. This is the cascade the demo narrates in depth.

---

## 11. ML / AI Specifications

### 11.1 Heating-Element PINN

- Library: **DeepXDE** + PyTorch with MPS backend.
- Architecture: 4 hidden layers × 64 units (~10–50 k params).
- Loss = data loss + PDE residual (1-D heat diffusion) + boundary/initial-condition loss.
- Training: offline on synthetic data; minutes on M3 Max.
- Runtime inference: < 5 ms CPU.
- Pitch line: *"Our heater model can't violate physics — the PDE residual is in its loss function."*

### 11.2 Late-Interaction Retrieval

- Model: **LightOn LateOn-Code-edge** (17 M params, output dim 48, Apache 2.0).
- Library: **PyLate** (LightOn's framework).
- Rationale: telemetry tokens are code-like; late interaction preserves token-level signal that dense embeddings dilute.
- Indexing: pre-computed offline over the historian.
- Latency target: < 200 ms p95 over 10 k rows on CPU.

### 11.3 Maintenance Agent — Genetic Algorithm (DEAP)

- Encoding: 6-dim threshold vector (one per component) + global preventive-lookahead coefficient.
- Fitness: `uptime_hours − λ_cost · maintenance_count − λ_failure · catastrophic_failures`.
- Process: 50 generations × 50 individuals.
- Output: live fitness graph during demo; final thresholds become the deployed policy.
- LLM explainer: wraps each runtime maintenance trigger with a natural-language reason citing the relevant cascade.

### 11.4 Counterfactual "What-If Replay"

- Implementation: simulator checkpoint + branch + diff. No causal-DAG library.
- Steps: pick regret moment → checkpoint state at `t_branch` → re-run with alternate decision → diff outcomes (uptime, failures, cost).
- UI: two timeline traces overlaid; alternate trace highlighted where it outperforms; single headline number.
- Reference target: a short digital-twin counterfactual source or internal explanation in the technical report. Do not rely on uncited causal claims in the demo.

### 11.5 Agentic Loop

- **Loop framework:** Claude Agent SDK (Pydantic-typed tools, OTel hookup, refusal handling) — unchanged from the original architecture.
- **Runtime model:** **Gemma 4 31B Dense** (Google, 2026-04-02, Apache 2.0), accessed via the MLH-issued API key, wired through DSPy's `dspy.LM` adapter (`openai/google/gemma-4-31B-it`, OpenAI-compatible). *(supersedes the original Sonnet-class pin per ADR-022)*
- **Compiled system prompt:** Apollo's prompt is **not hand-written** — it is compiled offline by `dspy.GEPA` (Genetic-Pareto reflective prompt evolution; Agrawal et al., arXiv:2507.19457, ICLR 2026 Oral) using the FR-W.9 eval set as the optimization target. Reflection LM is Claude Opus 4.7 (via local `claude` Bash CLI). Compiled artifact: `config/agent.system_prompt.gepa.txt`. (FR-W.10)
- Pattern: Pattern C — Agentic Diagnosis (highest tier in brief).
- Tools (see FR-3.6): `query_historian`, `late_interaction_search`, `compare_runs`, `run_counterfactual`, `plot_component_history`.
- Persona: Apollo — first-person, calm, never alarmist (FR-W.1). The Apollo persona text is part of the GEPA-compiled prompt; the persona-token-budget guard from ADR-019 still applies as a CI check on the compiled output.
- **Pitch line:** *"Apollo runs on a 31B open-weight model, with a system prompt evolved over 150 GEPA rollouts against our own grounding eval — the same paradigm Databricks used to push gpt-oss-120b past Claude Opus 4.1."*

### 11.6 Conformal Prediction (FR-W.6)

- Library: **MAPIE 1.3** (`scikit-learn-contrib`, Apr 2026).
- Wrapper: `MapieTimeSeriesRegressor` with EnbPi block-bootstrap, applied over the per-component decay/PINN predictors.
- Output: `(point, lower, upper)` triple per forecast horizon, persisted alongside `component_states` and rendered as a shaded band on every health curve.
- Coverage validation: on a held-out scenario (e.g. *Stressed*), measured empirical coverage of the 95% nominal CI ≥ 90%.
- Pitch line: *"Apollo's predictions come with calibrated confidence — 'heater fails in 8.0 h ± 2.3 h (95% CI)' is a guarantee, not a guess."*

### 11.7 Observability & Streaming (FR-W.7, FR-W.8)

- **Langfuse** (free cloud tier or self-hosted) attached to the Claude Agent SDK via the OTel integration (`LANGSMITH_OTEL_ENABLED=true`). Captures every prompt, tool call, latency, and token count.
- **SSE streaming** via `sse-starlette` `EventSourceResponse`. Event schema: `{type: "text-delta" | "tool-call-start" | "tool-result" | "citation" | "done", payload: …}`. React client consumes via raw `EventSource` (no Vercel AI SDK to avoid framework rewrite).
- Demo move: split-screen the Langfuse trace UI alongside the dashboard during the live "Ask Apollo" segment — judges see the agent's tool graph light up in real time.

### 11.8 Grounding Evaluation (FR-W.9 / FR-W.10 / FR-W.11)

- **Ragas `TestsetGenerator`** generates 30 grounded Q/A pairs from the historian's component documentation (component descriptions + sample telemetry windows) — replaces hand-authored eval set.
- **DeepEval** runs `FaithfulnessMetric` + `HallucinationMetric` over Apollo's responses to those questions in a `pytest`-style CI script.
- Pass gate (NFR-6): faithfulness ≥ 0.95, hallucination = 0. Result printed in README and demo slide as a measured fact, not a marketing claim.
- **Dual role of the eval set (ADR-022):** the FR-W.9 set doubles as the **GEPA optimization target** for FR-W.10. `scripts/agent/compile_prompt.py` runs `dspy.GEPA` over the same Q/A triples with a `metric_with_feedback` that combines DeepEval faithfulness + schema-validity + correct-tool-selection + citation-resolves-against-historian. Optimization is offline (~150 metric calls, ~2-4 hours), not part of CI. The compiled prompt is then re-evaluated against the held-out portion of the same set in the standard FR-W.9 pipeline, so the gate that ships Apollo is independent of the gate that compiled it.
- **Three-way comparison (FR-W.11):** the same eval pipeline is run against vanilla Opus 4.7, vanilla Gemma 4 31B, and Gemma 4 31B + GEPA-compiled prompt. Faithfulness, hallucination, and per-question pass-rate are logged to `docs/eval/comparison_results.json` and rendered as a table on the closing demo slide. This is the MLH "Best Use of Gemma" / HP narrative artifact: *"31B open model + 150 GEPA rollouts ≥ frontier closed model on the gate the demo claims to pass."*

---

## 12. Strategic Product Decisions

These decisions are carried forward from the original rough-idea document and are binding unless implementation evidence proves they are infeasible during the hackathon.

| Decision | Choice | Rationale |
| --- | --- | --- |
| Modeling approach | Rule-based + 1 PINN | Defensible, explainable, demoable |
| Number of components | 6 across 3 subsystems | Exceeds the minimum without expanding scope beyond a hackathon build |
| Cascade structure | 3 parallel cascades | More realistic than one linear chain and gives multiple demo angles |
| Coupling formalism | Linear coupling matrix `M` + one detailed ODE-backed cascade | Simple to implement and easy to explain to judges |
| Driver inputs | Weather API + PM2.5 API + synthetic powder PSD + mock operator shifts | Combines real-world inputs with controlled synthetic data |
| ML differentiator | PINN for heating element | Gives a concrete AI/physics claim without making every component fragile |
| Retrieval | Late-interaction retrieval with LateOn-Code-edge | Preserves token-level signal for structured telemetry better than plain dense embeddings |
| Maintenance agent | Genetic Algorithm (DEAP) thresholds + LLM explainer | Visible optimization curve; avoids RL instability during the hackathon |
| Counterfactual reasoning | Simulator checkpoint + branch + diff | Uses the simulator directly; avoids unnecessary causal-DAG infrastructure |
| Persistence | SQLite historian | Simple, queryable, demo-friendly |
| AI pattern | Pattern C — Agentic Diagnosis with visible tool calls | Highest-value Phase 3 pattern in the challenge brief |
| Explicit skips | Voice UI, RL, custom Metal/CoreML kernels, Omniverse 3-D, direct Kaggle training | Poor hours-to-demo-value ratio |

---

## 13. Architecture Overview

```
┌──────────────────────── Phase 1: Logic Engine (the Brain) ────────────────────────┐
│                                                                                    │
│   drivers (weather, PM2.5, PSD, load, maint level)  ──►  6 component models  ──►   │
│                                                          coupling matrix M         │
│                                                          PINN (heater only)        │
│                                                          Component State Reports   │
│                                                                                    │
└────────────────────────────────────────────┬───────────────────────────────────────┘
                                             │
┌────────────────────────────── Phase 2: Simulation Loop (the Clock) ────────────────┐
│                                                                                    │
│   for t in time:                                                                   │
│       drivers = scenario_provider(t, scenario_id)                                  │
│       state = phase1_engine(state, drivers, dt)                                    │
│       historian.write(t, drivers, state, run_id)                                   │
│       if maintenance_policy.decide(state, t):                                      │
│           state = apply_maintenance(state, action)                                 │
│                                                                                    │
│   ── 3 scenarios × 3 policies = 9 named runs in the historian ──                   │
│                                                                                    │
└────────────────────────────────────────────┬───────────────────────────────────────┘
                                             │
                                       SQLite Historian
                                       (timestamped state + drivers + run_id)
                                             │
┌────────────────── Phase 3: Apollo (Agentic Co-Pilot, text) ────────────────────────┐
│                                                                                    │
│   user query  ──►  agent loop (Claude Agent SDK)                                   │
│                    runtime LM: Gemma 4 31B Dense (ADR-022)                         │
│                    system prompt: GEPA-compiled (DSPy + dspy.GEPA, FR-W.10)        │
│                    tools: query_historian, late_interaction_search,                │
│                           compare_runs, run_counterfactual,                        │
│                           plot_component_history                                   │
│                    ──►  grounded answer + citation (run_id, component, timestamp)  │
│                                                                                    │
│   UI: chat panel with VISIBLE tool calls; charts; clickable citations              │
│        + Dark Twin comparison panel + What-If panel + Obituary timeline            │
│                                                                                    │
│   Offline (one-shot, scripts/agent/compile_prompt.py):                             │
│     dspy.GEPA(student=Gemma 4 31B, reflection=Opus 4.7 via `claude` CLI,           │
│               metric=Ragas+DeepEval over FR-W.9 set, max_metric_calls=150)         │
│     ──► config/agent.system_prompt.gepa.txt   (committed artifact)                 │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Data Model

```sql
-- Run metadata
runs(run_id PK, scenario_name, policy, started_at, finished_at, seed, config_json)

-- Driver vector at each timestep
drivers(run_id FK, t, temp_C, humidity, pm25, psd_d50, voltage_stability, …)
  PRIMARY KEY (run_id, t)

-- Component state at each timestep
component_states(run_id FK, t, component_id, health, status, metrics_json)
  PRIMARY KEY (run_id, t, component_id)

-- Maintenance events
maintenance_events(run_id FK, t, component_id, action, triggered_by)

-- Failure obituaries (FR-W.4)
obituaries(run_id FK, component_id, failure_t, narrative, citations_json)
  PRIMARY KEY (run_id, component_id, failure_t)

-- Conformal prediction intervals (FR-W.6)
forecasts(run_id FK, t, component_id, horizon_min, point, lower, upper, ci_level)
  PRIMARY KEY (run_id, t, component_id, horizon_min)
```

Indexes: `(run_id, t)`, `(run_id, component_id, t)` for the agent's typical query patterns.

---

## 15. UX Requirements

Single-page web dashboard with three primary panels:

| Panel | Purpose |
| --- | --- |
| **Live simulation** | Three parallel runs (Universes A/B/C); per-component health bars; master health curve per run; failure markers; obituary cards |
| **Apollo chat** | Natural-language input; responses with visible (collapsible) tool calls; clickable timestamp citations |
| **What-If** | Pick a regret moment, choose alternate decision, see counterfactual chart + delta number |

**Stack:** Python (FastAPI) backend + SQLite + DeepXDE + DEAP + MAPIE + Claude Agent SDK (loop framework only — runtime LM is Gemma 4 31B per ADR-022) + DSPy (`dspy.GEPA` for offline prompt compile) + Langfuse OTel + `sse-starlette`; React + Recharts frontend; **SSE for streaming agent responses** (token + tool-call deltas) and live sim updates; Tailwind for polish.

**Streaming behaviour (FR-W.8):** the chat panel renders Apollo's text token-by-token; tool calls appear as collapsible cards the *moment* the tool starts, then update with input/output as events stream. Health-curve charts render conformal prediction bands (FR-W.6) as shaded regions around point forecasts. A small "Trace" link beside each Apollo response opens the corresponding Langfuse run (FR-W.7).

**Sample agent interaction:**

> **Operator:** "Why did the printhead start failing around hour 7 in the Barcelona run?"
>
> **Apollo:** *[calls `query_historian(barcelona, nozzle, 6h-8h)`]*
> *[calls `query_historian(barcelona, heater, 6h-8h)`]*
> *[calls `late_interaction_search("nozzle clog escalation", barcelona)`]*
>
> **CRITICAL** — In run `barcelona-001`, nozzle clog probability rose from 0.18 → 0.61 between 06:42 and 07:14. The trigger was Cascade B: insulation panel health dropped below 0.55 at 06:30 (`barcelona-001 / insulation / 06:30:00`), which raised heater duty by 23% and pushed enclosure temp from 28°C to 41°C (`barcelona-001 / drivers / 06:42:00`). Higher temp drove binder viscosity up, accelerating clogging. **Recommendation:** earlier insulation check would have broken the cascade. *Run a what-if?*

---

## 16. Success Metrics

### 16.1 Submission gate (must pass all)

- [ ] All FR-1.x, FR-2.x, FR-3.x marked MUST satisfied.
- [ ] All checkboxes in `task/hackathon.md` §6 (Pre-Demo Self-Check) green.
- [ ] Architecture deck + technical report delivered.
- [ ] GitHub repo with reproducible README.
- [ ] Automated grounding eval (FR-W.9) passes: faithfulness ≥ 0.95, hallucination = 0.

### 16.2 Differentiation metrics (target for winning)

| Metric | Target |
| --- | --- |
| Cascading-failure demonstrations | ≥ 3 (CSC-A, CSC-B, CSC-C) |
| Uptime delta (AI vs FIXED) | ≥ +25 %, target +34 % |
| Hallucination rate on eval set | 0 % |
| Citation coverage on agent responses | 100 % |
| Demo-differentiator features shipped | ≥ 8 of 11 (FR-W.1 – W.11) |
| GEPA-Gemma vs vanilla-Opus-4.7 on FR-W.9 eval | within 2pp on faithfulness, hallucination = 0 on both |
| Live-Q&A wild-card grounding | 0 hallucinations across 10 questions |
| Conformal interval empirical coverage | ≥ 90% on a held-out scenario at 95% nominal CI |
| DeepEval faithfulness score | ≥ 0.95 |
| Langfuse trace coverage | 100% of agent invocations captured with tool-call timeline |

---

## 17. Milestones & Time Budget (target 36 h, plan 40 h)

| ID | Milestone | Hours | Owner | Dependencies |
| --- | --- | --- | --- | --- |
| **M1** | Phase 1 component models + coupling matrix | 5 | TBD | — |
| **M2** | PINN training + integration (heater) | 5 | TBD | M1 |
| **M3** | Phase 2 sim loop + SQLite historian + 3 scenarios | 4 | TBD | M1 |
| **M4** | GA maintenance policy (DEAP) + comparison run | 4 | TBD | M3 |
| **M5** | Counterfactual replay engine | 3 | TBD | M3 |
| **M6** | Late-interaction retrieval setup (PyLate + index) | 3 | TBD | M3 |
| **M7** | Agentic loop + tools + grounding protocol | 5 | TBD | M3, M6 |
| **M8** | Frontend (3 panels) | 5 | TBD | M3 |
| **M9** | Demo-differentiator features (Apollo persona, Dark Twin, savings slide, obituary, live-Q&A prep) | 4 | TBD | M7, M8 |
| **M9b** | **Conformal prediction intervals (MAPIE) + shaded forecast bands** (FR-W.6) | 1.5 | TBD | M1, M8 |
| **M9c** | **Langfuse observability hookup** (FR-W.7) | 1 | TBD | M7 |
| **M9d** | **SSE streaming for agent + tool calls** (FR-W.8) | 2.5 | TBD | M7, M8 |
| **M9e** | **Automated grounding eval (Ragas + DeepEval)** (FR-W.9) | 2.5 | TBD | M7 |
| **M9f** | **GEPA prompt compile + three-way comparison** (FR-W.10, FR-W.11; ADR-022) | 4 | TBD | M7, M9e |
| **M10** | Polish, slide deck, dry-run demo | 2 | TBD | all |
| **Total** | | **~51** | | |

Differentiator-feature work (M9, M9b–f) is mostly presentation/prompt-engineering layered on existing infrastructure and can run in parallel with backend integration. The plan is intentionally over-budget — M9b–f are the first to be cut if the critical path slips. Cut order: M9d (streaming) → M9b (conformal) → M9c (observability) → M9e (eval). **M9f (GEPA compile + comparison) is NOT in the cut order** — it is the MLH "Best Use of Gemma" submission gate per ADR-022 and ships even if other M9 items slip. M9e is a hard prerequisite for M9f (the eval set is the GEPA optimization target), so M9e is similarly protected.

---

## 18. Dependencies & Assumptions

### 18.1 External services

- **OpenWeatherMap API** (temperature, humidity)
- **OpenWeather Air Pollution API / AirNow** (PM2.5)
- **Gemma 4 31B Dense API** (MLH-issued key) — Apollo's runtime LM (ADR-022)
- **Local `claude` Bash CLI → Claude Opus 4.7** — used in two places: GEPA reflection LM during offline prompt compile (FR-W.10), and the comparator baseline in the three-way grounding eval (FR-W.11)
- **Langfuse cloud (free tier)** *or* self-hosted instance — agent observability (FR-W.7)

### 18.2 Libraries

- DeepXDE, PyTorch (PINN)
- DEAP (genetic algorithm)
- PyLate (late-interaction retrieval)
- LightOn LateOn-Code-edge (model artifact, Apache 2.0)
- Claude Agent SDK *(loop framework only — runtime model is Gemma per ADR-022)*
- **DSPy** + **`gepa` package** — declarative LM program compilation and the GEPA optimizer (`dspy.GEPA`); FR-W.10
- **MAPIE 1.3** (conformal prediction, FR-W.6)
- **Langfuse Python SDK** + `langsmith[claude-agent-sdk]` (OTel auto-tracing, FR-W.7)
- **`sse-starlette`** (Server-Sent Events streaming, FR-W.8)
- **Ragas** + **DeepEval** (automated grounding eval, FR-W.9)
- FastAPI, SQLite, Recharts, React, Tailwind

### 18.3 Hardware

- Apple M3 Max (40-core GPU, MPS backend) — used for PINN training only.

### 18.4 Assumptions

- Internet connectivity available at demo venue (for weather + Gemma API). Gemma response cache for canonical demo questions is the offline fallback.
- The MLH-issued Gemma 4 31B API key is OpenAI-compatible (the dominant pattern for Gemma-on-managed-hosting); if Google-AI-Studio-style, the DSPy adapter switches from `openai/...` to `gemini/...` (one config line, isolated to `config/agent.yaml`).
- Coupling-matrix coefficients tunable to literature-cited Weibull params; otherwise hand-set so cascades resolve over the simulated 10-hour story.
- HP judges value rigor + grounding over photoreal graphics.
- MLH "Best Use of Gemma" mini-challenge values *non-trivial* uses of Gemma 4 (research-grade prompt optimization on a grounded agentic task) over chatbot wrappers — verified by ADR-022 narrative.

---

## 19. Risks & Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| **R-1** | Coupling-matrix tuning produces unrealistic timing | Medium | Medium | Start from literature-cited Weibull params; iterate against scenario timing; defend in technical report |
| **R-2** | PINN training unstable / slow | Medium | Medium | Pre-train offline; tiny model; **fallback:** swap to learned regressor surrogate; physics narrative still holds for rule-based components |
| **R-3** | Late-interaction retrieval index too slow at demo time | Low | Medium | Pre-index everything; cap historian rows; **fallback:** dense embeddings (Voyage / OpenAI) |
| **R-4** | GA fitness landscape ugly → boring evolution graph | Medium | Low | Tune mutation rates; pre-canned good seed; **fallback:** Bayesian opt with Optuna |
| **R-5** | Three-scenario sim runs too slow live | High | Low | Pre-run before demo; replay at 10× speed; live mode as second demo step |
| **R-6** | Agent hallucinates despite grounding protocol | Low | Critical | Pydantic-enforced citations; refuse-to-answer template; explicit empty-tool-result UI; pre-demo eval set with 0 % hallucination gate |
| **R-7** | Demo venue Wi-Fi blocks API access | Medium | Critical | Cache OpenWeather data offline; cache canonical Gemma 4 31B responses for the canned demo path (scripted segment runs from cache, not the live API); FR-W.11 comparison numbers are pre-rendered into the slide before the demo so the Opus-via-`claude` baseline doesn't need network at demo time; live "Ask Apollo" segment disabled if offline. |
| **R-8** | Live-Q&A breaks on a wild-card question | Medium | Medium | 10-question dry-run before demo; refusal template is *itself* a positive signal — "shows our guardrails work" |

---

## 20. Open Questions

- [ ] Which two cities for the weather scenarios? *(default: Barcelona, Phoenix)*
- [ ] Which member owns each milestone in §17?
- [ ] Confirm Claude Agent SDK availability for the loop framework; use LangGraph only as implementation fallback.
- [ ] Demo length and ordering — does the live sim or the chat panel open the demo?
- [ ] Final cost coefficients for the savings slide — which industrial-AM TCO study or public source to cite?
- [ ] Confirm Gemma 4 31B API shape (OpenAI-compat vs Google AI Studio) once the MLH key is issued; default assumption is OpenAI-compat.
- [ ] Final GEPA budget — `max_metric_calls` setting for the prompt compile run (default 150; raise to 300 if first run plateaus below the FR-W.11 within-2pp target).

---

## 21. Out of Scope (with rationale)

| Considered | Status | Reason |
| --- | --- | --- |
| Voice interface | Excluded | Presentation layer with high implementation cost; text interaction is sufficient for the PRD scope |
| Reinforcement-learning maintenance agent | Excluded | Needs simulator + days of training; GA gives a more reliable hackathon implementation path |
| Custom Metal / CoreML kernels for PINN | Excluded | PyTorch MPS is sufficient; custom kernels add cost without improving the demo requirements |
| NVIDIA Omniverse photoreal twin | Excluded | Outside the 36 h target; brief focuses on decision intelligence, not graphics |
| Direct training on Kaggle FDM datasets / NASA C-MAPSS | Excluded | Domain mismatch with HP Metal Jet binder-jetting use case |
| Claiming proprietary S100 failure parameters | Excluded | The team does not have proprietary HP failure data; use public literature and disclosed synthetic assumptions |
| MCP-style tool servers | Excluded | In-code tool schemas are sufficient for the hackathon scope |
| Multi-printer fleet view | Excluded | Would dilute the single-printer cascade story |
| Live Twilio emergency phone call | Excluded | Brittle dependency and not required by the challenge |
| Operator-persona switching (CFO/Engineer/Tech UI modes) | Excluded | Useful but lower priority than grounded diagnostics and Apollo voice quality |

---

## Appendix A — Pitch Sentence

> *"We built a Digital Co-Pilot grounded in published binder-jetting failure physics, with cascading degradation across all three subsystems. A physics-informed neural surrogate predicts heater drift; an agentic copilot queries the historian via late-interaction tool-use to diagnose root causes with timestamped citations; and a counterfactual engine answers 'what if we'd intervened earlier.' We compare three universes — Barcelona humid, Phoenix dry, and AI-managed — and show 34 % uptime gain from autonomous maintenance over a fixed schedule."*

Five concrete technical claims, each verifiable. None buzzword-only.

---

## Appendix B — Decision Log

Key reversals from initial brainstorm to final PRD:

- **Kaggle real-data training** → rejected. Use literature-cited Weibull params instead.
- **Custom Metal kernels** → rejected. PyTorch MPS is free.
- **Voice interface** → rejected. Polish only if all else ships, but realistically skip.
- **One linear cascade chain** → replaced with three parallel cascades. More realistic, more demo angles.
- **3 components minimum** → expanded to 6. Richer twin, more cascade options, still tight enough to model well.
- **Dense embeddings for RAG** → replaced with late-interaction (LateOn-Code-edge). Telemetry tokens are code-like.
- **Full RL maintenance agent** → replaced with GA. Visible evolution, hackathon-feasible, no training instability.
- **Causal DAG library (DoWhy)** → replaced with simulator-checkpoint branching. We own the sim; statistical causality is overkill.
- **Time-series foundation models (Chronos-2, TimesFM 2.5, Moirai-MoE)** → rejected. Sledgehammer for 6 simulated components; contradicts the PINN narrative; adds zero physics insight.
- **Survival analysis (lifelines, scikit-survival)** → rejected. Duplicative with rule-based decay + GA; needs historical failure data we don't have.
- **PyOD anomaly detection** → rejected. Would create a second source of truth that disagrees with the simulator's ground-truth events on stage.
- **ECharts swap from Recharts** → rejected. Recharts is sufficient at our data scale; mid-hackathon swaps are a trap.
- **Local LLM fallback (Ollama + Qwen 2.5)** → rejected at the time of v1.1; Apollo's runtime LM is now Gemma 4 31B per ADR-022, so the fallback question is "what if the Gemma API is unreachable at the venue" — answer: cached canonical responses + the same offline mock harness PLAN-C §4 already builds for the demo.
- **Full 3D printer model (React-Three-Fiber)** → rejected. No CC-licensed S100 model exists; an SVG isometric schematic with red overlays is a 1.5 h fallback if visual polish is needed.
- **Vercel AI SDK for streaming** → rejected. Pure `sse-starlette` + raw `EventSource` avoids a React framework rewrite (FR-W.8).
- **+ Conformal prediction (MAPIE)** → adopted as FR-W.6 — calibrated CI on every forecast turns "trust me" predictions into "8.0 h ± 2.3 h (95% CI)" with rigorous theoretical guarantees.
- **+ Langfuse observability** → adopted as FR-W.7 — official Anthropic-blessed Claude Agent SDK integration, free tier, makes the agent reasoning literally visible during the demo.
- **+ SSE token + tool-call streaming** → adopted as FR-W.8 — Apollo narrates while tools fire one by one, the dashboard "feels alive."
- **+ Automated grounding eval (Ragas + DeepEval)** → adopted as FR-W.9 — turns NFR-6's "0% hallucination" from a marketing claim into a measured CI artifact.
- **+ Gemma 4 31B + GEPA-compiled prompt as Apollo's runtime LM** → adopted as FR-W.10 / FR-W.11 (ADR-022, supersedes the model pin in ADR-008). Driven by the MLH "Best Use of Gemma" mini-challenge and Gemma 4's step change in agentic tool use (τ²-bench Retail 6.6% → 86.4% from Gemma 3 27B → Gemma 4 31B). The system prompt is compiled offline by `dspy.GEPA` (Agrawal et al., ICLR 2026 Oral) using Opus 4.7 as the reflection LM; Opus 4.7 is also the comparator on the FR-W.9 eval. Direct precedent: Databricks' gpt-oss-120b + GEPA beats Opus 4.1 by +2.2pp at 90× lower serving cost.

---

## Appendix C — Brief-Compliance Mapping

Mapping of HackUPC brief deliverables to PRD requirements, for evaluator traceability.

| Brief deliverable | PRD requirement(s) |
| --- | --- |
| Phase 1 ≥ 3 degradation models | FR-1.1, FR-1.3, §8 |
| Phase 1 each component uses ≥ 1 driver | FR-1.2, §9 |
| Phase 1 health + status + metrics output | FR-1.4 |
| Phase 2 simulation loop advancing time | FR-2.1, FR-2.2 |
| Phase 2 every record persisted with timestamp + drivers | FR-2.3 |
| Phase 2 runs identifiable separately | FR-2.4, FR-2.7, §14 |
| Phase 2 time-series visualization with failure | FR-2.5, FR-2.6 |
| Phase 3 reads from Phase 2 historian | FR-3.2 |
| Phase 3 grounded, no hallucinations | FR-3.5, NFR-6, **FR-W.9** (automated eval), **FR-W.10** (GEPA-compiled prompt), **FR-W.11** (three-way comparison incl. Opus 4.7 baseline) |
| Phase 3 every answer cites a data point | FR-3.3, NFR-7 |
| Architecture slide deck | M10 |
| Technical report | M10 |
| GitHub repo with README | §16.1 |
| Walkthrough demo | M10, §15 |

---

## Appendix D — Rough-Idea Coverage Mapping

This PRD intentionally preserves the contents of the previous `ROUGH_IDEA.md` while reorganizing it into requirements, constraints, and appendices.

| Previous rough-idea section | Preserved in PRD |
| --- | --- |
| The Pitch | §1, Appendix A |
| Strategic Decisions Summary | §12 |
| Architecture Overview | §13 |
| Component Map | §8 |
| Cascading Failures | §10 |
| Driver Inputs | §9 |
| Phase 1 — Logic Engine | §6.1, §8, §10, §11.1 |
| Phase 2 — Simulation Loop & Historian | §6.2, §13, §14 |
| Maintenance Agent — GA | §11.3 |
| Phase 3 — Agentic Co-Pilot | §6.3, §11.5, §15 |
| Counterfactual Replay | §11.4, FR-3.6 |
| UI / Demo Surface | §15 |
| WOW Factors | §6.4, §15, §21 |
| Time Budget | §17 |
| Risks & Open Questions | §19, §20 |
| Things Explicitly Not Doing | §21 |
| Decision Log | Appendix B |
