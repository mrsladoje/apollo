# Rough Idea & Decisions — HP Metal Jet S100 Digital Co-Pilot

**Hackathon:** HackUPC 2026 · HP "When AI meets reality" challenge
**Status:** Pre-build planning — decisions from initial research/discussion phase
**Date:** 2026-04-25

---

## 1. The Pitch (one paragraph)

We're building a **Digital Co-Pilot** for the HP Metal Jet S100 metal binder-jetting printer: a living digital twin that models cascading component degradation grounded in published binder-jetting tribology, runs continuously across multiple environmental scenarios, and exposes itself through an agentic AI interface that diagnoses failures with timestamped citations and answers "what if we'd intervened earlier" via simulator replay. The thesis: judges have seen 20 chatbots wrapped around 3 decay curves. We win by making the **physics legible**, the **cascades real**, and the **AI's reasoning visible**.

> **Demo headline sentence:** "Six components across three subsystems, three coupled cascades, a physics-informed neural surrogate for the heater, an agentic copilot citing every claim, and +34% uptime vs. a fixed maintenance schedule."

---

## 2. Strategic Decisions Summary

| Decision | Choice | Why |
| --- | --- | --- |
| Modeling approach | Rule-based + 1 PINN | Defensible, explainable, demoable |
| Number of components | 6 across 3 subsystems | Beats the "1 per subsystem" bar without bloat |
| Cascade structure | 3 parallel cascades (not one mega-chain) | More realistic, more demo angles |
| Coupling formalism | Linear coupling matrix `M` + 1 detailed ODE | One numpy matrix, judges grok it instantly |
| Driver inputs | Weather API + PM2.5 API + synthetic powder PSD + mock operator shifts | Mix of real APIs and defensible synthetic |
| ML differentiator | Physics-Informed Neural Network (DeepXDE) for heating element | Genuine "buzzword with substance" |
| Retrieval | Late-interaction (LightOn LateOn-Code-edge, 17M, Apache 2.0) | Token-level signal beats dense embeddings on structured telemetry |
| Maintenance agent | Genetic Algorithm (DEAP) for thresholds + LLM explainer | Visible evolution; not a black-box RL trap |
| Counterfactual reasoning | Simulator checkpoint + branch + diff | No causal-DAG library needed; we own the sim |
| Persistence | SQLite historian | Simple, queryable, demo-friendly |
| AI pattern (Phase 3) | Pattern C — Agentic Diagnosis with visible tool calls | Highest tier in the brief |
| **Skipped** | Voice UI, RL, custom Metal/CoreML kernels, Omniverse 3D, direct Kaggle training | All have unfavorable hours-to-wow ratio |

---

## 3. Architecture Overview

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
│   ── 3 scenarios run side-by-side: Barcelona-humid, Phoenix-dry, AI-managed ──     │
│   ── Maintenance policies: NONE | FIXED | AI(GA-tuned thresholds + LLM explainer)─ │
│                                                                                    │
└────────────────────────────────────────────┬───────────────────────────────────────┘
                                             │
                                       SQLite Historian
                                       (timestamped state + drivers + run_id)
                                             │
┌────────────────── Phase 3: Agentic Co-Pilot (the Voice — text not audio) ──────────┐
│                                                                                    │
│   user query  ──►  agent loop (Claude Agent SDK or LangGraph)                      │
│                    tools: query_historian, compare_runs, run_counterfactual,       │
│                           late_interaction_search (LateOn-Code-edge),              │
│                           plot_component_history                                   │
│                    ──►  grounded answer + citation (timestamp, run_id, component)  │
│                                                                                    │
│   UI: chat panel with VISIBLE tool calls; charts; clickable timestamp citations    │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Map (6 components × 3 subsystems)

| # | Subsystem | Component | Failure mode | Key input drivers | State outputs |
| - | --- | --- | --- | --- | --- |
| 1 | Recoating | **Recoater Blade** | Abrasive wear (height loss, edge chipping) | Powder PSD, ambient PM2.5, blade-passes counter | health, blade_thickness_mm, status |
| 2 | Recoating | **Drive Motor** | Bearing fatigue, current rise | Grid voltage stability, total cycles, vibration | health, current_draw_A, bearing_temp_C, status |
| 3 | Printhead | **Nozzle Plate** | Clogging probability ↑ | Binder viscosity (humidity-driven), powder dust, temp | health, clog_prob, active_nozzle_count, status |
| 4 | Printhead | **Thermal Firing Resistors** | Electrical drift (resistance ↑) | Duty cycle, ambient temp, voltage | health, resistance_pct, status |
| 5 | Thermal | **Heating Element** *(PINN-modeled)* | Resistive drift + thermal fatigue (Coffin-Manson) | HVAC short-cycling, ambient temp, duty hours | health, predicted_temp_field, drift_pct, status |
| 6 | Thermal | **Insulation Panel** | Thermal conductivity loss | Cumulative heat exposure, age | health, k_eff_W_mK, status |

**Status enum** (per the brief): `FUNCTIONAL → DEGRADED → CRITICAL → FAILED`.
**Health index:** `[0.0, 1.0]`, normalized; status thresholds at 0.7 / 0.4 / 0.1.

---

## 5. Cascading Failures — Three Parallel Cascades

Realistic systems have *parallel* failure paths, not one linear chain. We model three:

### Cascade A — Recoating loop *(intra-subsystem)*
```
Blade wear ↑  →  powder bed unevenness ↑  →  motor torque ↑  →  bearing fatigue ↑
```

### Cascade B — Thermal-Printhead loop *(cross-subsystem, the showpiece)*
```
Insulation degradation  →  heater duty ↑  →  enclosure ambient temp ↑
                       →  binder viscosity ↑  →  nozzle clog probability ↑
                                              →  firing resistor stress ↑
```
This is the **demo cascade** — modeled with explicit ODEs (not just matrix coupling) because it spans all three subsystems and tells the strongest story.

### Cascade C — Powder contamination loop
```
Blade ceramic flaking  →  powder contamination ↑  →  nozzle clog probability ↑
```

### Mathematical formalism

Default coupling: per-step linear matrix update.
```
dH_i/dt = -α_i · f(drivers_i)  -  Σ_j  M_ij · (1 - H_j)
```
where `H_i ∈ [0,1]` is component i's health, `α_i` is its intrinsic decay coefficient (Weibull or exponential), and `M_ij` is the cross-component coupling weight.

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
Coefficients are tuned to literature where possible, otherwise hand-set so the cascade timing tells a 10-hour story.

For Cascade B specifically, we add explicit physical relationships (Arrhenius-style for binder viscosity vs temp, Coffin-Manson for thermal fatigue cycles) on top of the matrix.

---

## 6. Driver Inputs

**Mandatory four (per the brief):** Temperature Stress, Humidity/Contamination, Operational Load, Maintenance Level.

**Our concrete realization:**

| Driver | Source | Refresh rate | Notes |
| --- | --- | --- | --- |
| Ambient temperature | OpenWeatherMap API (city-selectable) | 1 min interp | Drives heater duty and binder viscosity |
| Humidity / dewpoint | OpenWeatherMap API | 1 min interp | Drives binder viscosity → nozzle clog |
| **PM2.5 (air quality)** | OpenWeather Air Pollution / AirNow | 1 min interp | Drives blade & nozzle contamination |
| **Powder PSD (D10/D50/D90)** | Synthetic genealogy model (powder age × storage humidity) | per print run | Single strongest causal lever for blade wear |
| Operational load (cycles, hours) | Simulation state | each step | — |
| Maintenance level | Simulation state | each step | Reset by maintenance actions |
| **Operator shift pattern** | Mock log (day/night/weekend) | piecewise | Affects maintenance quality randomly |
| Grid voltage stability *(optional)* | Synthetic noise model | 1 min | Drives motor / resistor stress |

**Scenario presets:** Barcelona (humid factory), Phoenix (dry climate-controlled lab), Generic-stressed (high duty + poor PSD).

---

## 7. Phase 1 — Logic Engine

**Implementation:** Python, deterministic, callable from Phase 2 loop.
**Interface:**
```python
def step(state: TwinState, drivers: Drivers, dt: float) -> TwinState
```

**Per component:** one degradation function applying intrinsic decay + receiving coupling contributions from `M`.

**Failure models used (≥2 required by brief, we use 3):**
1. **Exponential decay** — recoater blade thickness, insulation conductivity
2. **Weibull distribution** — bearing fatigue, nozzle clogging probability
3. **Coffin-Manson thermal fatigue** — heating element, firing resistors

**Deterministic guarantee:** same `(state, drivers, dt)` ⇒ same output. Seeded randomness for stochastic scenarios.

**The PINN component (heating element only):**
- Library: **DeepXDE** + PyTorch, MPS backend (no custom Metal kernels — see Decision Log)
- Model: 1D heat-diffusion with time-varying boundary conditions; 4 hidden layers × 64 units (~10–50k params)
- Loss = data + PDE residual + boundary/initial conditions
- Trained offline (~minutes on M3 Max) on synthetic data; runtime inference 1–5 ms CPU
- **Pitch:** "Our heater model can't violate physics — the PDE residual is in its loss function."

---

## 8. Phase 2 — Simulation Loop & Historian

**Loop:** Standard fixed-time-step. `time_step = 1 simulated minute`, `total_duration = 24–72 simulated hours`. 10 hours of sim runs in seconds.

**Persistence:** SQLite. One row per `(timestamp, component, run_id)` plus a separate drivers table per `(timestamp, run_id)`. Indexed for time-range and run_id queries.

**Schema sketch:**
```
runs(run_id, scenario_name, policy, started_at, finished_at, seed, config_json)
drivers(run_id, t, temp_C, humidity, pm25, psd_d50, ...)
component_states(run_id, t, component_id, health, status, metrics_json)
maintenance_events(run_id, t, component_id, action, triggered_by)
```

**Three concurrent runs in the demo:**
1. **Barcelona-humid + Fixed maintenance** (every 24 sim-h)
2. **Phoenix-dry + No maintenance** (catastrophic baseline)
3. **Stressed scenario + AI maintenance** (GA-tuned thresholds + LLM explainer)

**Maintenance Policy Comparison Chart:**
```
cumulative uptime
    ▲
    │           AI ─────────────
    │      ╱───╯
    │    ╱           Fixed ─────
    │  ╱       ╱─────╯
    │ ╱      ╱
    │╱     ╱       None ────────
    │   ╱──╯  ───╱
    │  ╱       ╱
    └─────────────────────────► t
```
**Headline number:** **"+34% uptime vs. fixed schedule"** (target — actual depends on tuning).

---

## 9. Maintenance Agent — Genetic Algorithm (DEAP)

**Why GA, not RL:** RL needs hours of stable training and a high-fidelity simulator we'd be tuning during the hackathon. GA evolves a population of candidate threshold vectors in minutes, has a beautifully demoable fitness curve, and is explainable to non-ML judges.

**Encoding:** each individual = vector of 6 thresholds (one per component) at which to trigger maintenance, plus a global "preventive lookahead" coefficient.

**Fitness:**
```
fitness = uptime_hours - λ_cost · maintenance_count - λ_failure · catastrophic_failures
```

**Process:** 50 generations × 50 individuals, fitness graph shown live in demo. Final thresholds become the deployed policy.

**Runtime decisions:** at each step, simple threshold check. **The LLM explainer wraps each maintenance trigger** with a natural-language reason ("Heater health crossed 0.4 — given coupling to nozzle, intervening now to avoid Cascade B").

**Comparison runs:** GA-AI vs Fixed (24h) vs None.

---

## 10. Phase 3 — Agentic Co-Pilot

**Pattern:** **Pattern C — Agentic Diagnosis** (highest tier in brief).

**Stack:**
- **Claude Agent SDK** (or LangGraph) for the agent loop
- **Claude Sonnet 4.6** for reasoning (cheap, fast, tool-use solid)
- **LightOn LateOn-Code-edge** (17M, Apache 2.0) for late-interaction retrieval over the historian — picked because telemetry tokens are *code-like* and late interaction preserves token-level signal
- **PyLate** (LightOn's library) for the indexing harness

**Tools the agent can call (visible in UI):**
| Tool | Purpose |
| --- | --- |
| `query_historian(run_id, component, t_range)` | structured SQL over telemetry |
| `late_interaction_search(query, run_id)` | semantic search over events |
| `compare_runs(run_id_a, run_id_b, component)` | scenario comparison |
| `run_counterfactual(run_id, t_branch, alt_decision)` | what-if replay |
| `plot_component_history(run_id, component, t_range)` | embed chart in response |

**Grounding protocol (zero hallucinations):**
- Every response includes evidence citations: `(run_id, component, timestamp)`
- Severity tag: `INFO | WARNING | CRITICAL`
- Citation timestamps are clickable in the UI — clicking scrolls the chart to that exact moment
- Tool calls render in the chat panel with their input/output, so judges *see* the agent reasoning

**Example interaction:**
> **Operator:** "Why did the printhead start failing around hour 7 in the Barcelona run?"
>
> **Agent:** *[calls `query_historian(barcelona, nozzle, 6h-8h)`]*
> *[calls `query_historian(barcelona, heater, 6h-8h)`]*
> *[calls `late_interaction_search("nozzle clog escalation", barcelona)`]*
>
> **CRITICAL** — In run `barcelona-001`, nozzle clog probability rose from 0.18 → 0.61 between 06:42 and 07:14. The trigger was Cascade B: insulation panel health dropped below 0.55 at 06:30 (citation: `barcelona-001 / insulation / 06:30:00`), which raised heater duty by 23% and pushed enclosure ambient temp from 28°C to 41°C (citation: `barcelona-001 / drivers / 06:42:00`). Higher temp drove binder viscosity up, accelerating clogging. **Recommendation:** earlier insulation check would have broken the cascade. *Run a what-if?*

---

## 11. Counterfactual "What-If Replay"

**Implementation (no causal-DAG library — we own the simulator):**
1. Pick a "moment of regret" in a run (e.g., catastrophic failure at t=8h).
2. Checkpoint sim state from `t = regret_t − Δ` (deepcopy).
3. Re-run sim forward with **alternate decision** (e.g., "trigger heater maintenance at t-Δ instead of waiting").
4. Diff outcomes: uptime delta, failures avoided, maintenance cost.
5. UI: two timeline traces overlaid; alternate trace highlighted in green where it outperforms; big headline number ("**+2.3 hours uptime saved had we acted at 06:00**").

**Reference:** *Digital Twin Counterfactual Framework* (arXiv 2604.01325, 2026).

---

## 12. UI / Demo Surface

**Single-page web dashboard.** Three areas:

1. **Live simulation panel** — three parallel scenarios running, with health bars per component and a master health curve per run. Failure markers show when components died.
2. **Co-Pilot chat panel** — natural language input, responses with visible tool calls (collapsed by default, expandable to show each tool's input/output), clickable evidence citations.
3. **What-If panel** — pick a regret moment, choose an alternate decision from a dropdown, see counterfactual chart appear with delta number on top.

**Stack (lean):**
- Backend: Python (FastAPI) + SQLite + DeepXDE + DEAP + Anthropic SDK
- Frontend: React + Recharts (or D3); WebSocket for live sim updates
- Optional: Tailwind for "looks polished" speed

---

## 13. WOW Factors — the emotional layer

Technical depth alone doesn't win hackathons; the team that judges *remember at coffee* wins. The brief literally says we're building "an intelligent, *living* entity" that "communicates." Most teams will build a chatbot. We're building a colleague.

These five additions are deliberately **narrative-first, low-engineering-cost** — they convert work we're already doing into demo moments that stick.

### 13.1 Personification — meet "Apollo" ★ ~2h

The twin has a name and speaks **first-person** in the chat panel and alerts. Components also speak first-person when clicked.

> *"I'm Apollo. My recoater blade is wearing 12% faster than usual — the powder D50 has drifted out of spec for 8 hours. I have about 4 print runs left in me before I'd recommend a blade swap. Want me to schedule it for the next shift change?"*

**Implementation:**
- System prompt for the agent: persona definition (calm, professional, slightly self-aware, never alarmist)
- Component models expose a `speak()` method returning a first-person status string driven by current health + recent driver history; LLM-rendered for naturalness, grounded by the same citation rules
- UI: clicking any component opens a "voice" panel with its first-person summary
- **No new infrastructure** — purely a presentation layer over the existing agent + historian

### 13.2 The "Dark Twin" — life without the co-pilot ★ ~1h

Reframe our existing **NONE / FIXED / AI-managed** benchmark as a narrative fork. The no-maintenance run is renamed **"the alternate universe where Apollo wasn't watching."**

**Implementation:**
- Pure framing change in the dashboard: the three policies become *Universe A (no co-pilot)*, *Universe B (fixed schedule)*, *Universe C (Apollo)*
- Side-by-side cumulative-uptime chart with a single overlaid headline:
  > *"€187,000 of equipment. Same week. Same conditions. One difference: someone was paying attention."*
- Time-synced playback so the divergence is visible second-by-second

### 13.3 The €450k slide — concrete money math ★ ~30 min

HP judges work for HP. HP sells equipment. Numbers in euros land harder than numbers in `health_index`.

**Closing slide table (defensibly conservative):**

| Failure | Cost per event | Frequency w/o co-pilot | Frequency w/ co-pilot |
| --- | --- | --- | --- |
| Recoater blade catastrophic | €4,200 | 8/yr | 2/yr |
| Sintering batch lost | €18,000 | 4/yr | 0.5/yr |
| Unplanned downtime per hour | €2,800/h | 180h/yr | 40h/yr |
| **Annual savings per printer** | | | **≈ €450k** |

Tagline: *"Apollo pays for himself in 2 weeks."*

**Implementation:** one slide. Numbers cited from public industrial-AM cost-of-downtime reports + our own simulation deltas. Defensible if anyone challenges them.

### 13.4 The Obituary — narrative post-mortem of failed components ★ ~45 min

When a component crosses to `FAILED`, the LLM auto-writes a one-paragraph **obituary** stored in the historian and surfaced in the UI's failure timeline.

> *"Heating Element B passed at 14:23 after 47 hours of service. Born new at 06:00 yesterday, it weathered three thermal cycles above 280°C between 10:30–11:15 — a stress that aged it disproportionately. Insulation panel degradation (Cascade B, 12:40) added the final 23% of its wear. In retrospect: a 30-minute cooldown at 11:00 would have extended its life by an estimated 18 hours. RIP."*

**Implementation:**
- New tool `write_obituary(run_id, component, failure_t)` that pulls the component's full history from the historian, asks Claude to narrate, and stores the result in a new `obituaries` table
- Every claim in the obituary carries a citation `(run_id, component, t)` — same grounding protocol as everything else
- Triggered automatically in the sim loop when status transitions to `FAILED`
- Display: clickable card in the failure timeline; opens a modal with the full obituary + the cited timestamps

This costs almost nothing and **no other team is going to have this.** It's also a perfect narrative pairing for the counterfactual replay — the obituary reads as regret, the counterfactual answers it.

### 13.5 Live "Ask Apollo" with the judges ★ zero new code, demo-planning only

Reserve the **last 60 seconds** of the demo for: *"Anyone want to ask Apollo a question?"* Let a judge type something live. **Do not pre-script.**

**Why it works:**
- Signals total confidence in the grounding protocol
- Memorable in a way no rehearsed pitch can be
- Most teams will not dare because their RAG hallucinates; ours refuses to answer when evidence is missing

**Risk mitigation:**
- If a question has no supporting telemetry, the agent's response template is: *"I don't have telemetry to answer that confidently — could you scope it to a specific run or time window?"* This is a **win** in front of judges because it shows the refuse-to-answer guardrail
- Pre-test with 10 wild-card questions during dry-run; if any breaks the grounding, harden the system prompt before demo

### 13.6 What we deliberately rejected

| Idea | Why skipped |
| --- | --- |
| Voice synthesis for Apollo | +4h, signals "tried too hard"; first-person *text* is enough |
| Multi-printer fleet view | Crowds out the cascade story |
| Live Twilio emergency phone call | Gimmicky, brittle on conference WiFi |
| EKG-style health monitor with sound | Risk of feeling like a Halloween prop, not an industrial tool |
| Operator-persona switching (CFO/Engineer/Tech) | Genuinely good idea but ~2h that we'd rather spend on Apollo's voice quality |
| Auto-generated TikTok-style highlight reel | Cute, but distracts from grounding story |

---

## 14. Time Budget (target 36h)

| Block | Hours | Owner |
| --- | --- | --- |
| Phase 1 component models + coupling matrix | 5 | — |
| PINN training + integration (heater) | 5 | — |
| Phase 2 sim loop + SQLite historian + 3 scenarios | 4 | — |
| GA maintenance policy (DEAP) + comparison run | 4 | — |
| Counterfactual replay engine | 3 | — |
| Late-interaction retrieval setup (PyLate + index) | 3 | — |
| Agentic loop + tools + grounding protocol | 5 | — |
| Frontend (3 panels) | 5 | — |
| **WOW factors** (Apollo persona, Dark Twin reframe, money slide, obituary tool, live-Q&A prep) | 4 | — |
| Polish, slide deck, dry-run demo | 2 | — |
| **Total** | **~40** | |

Buffer comes from skipping voice, RL, Omniverse, custom Metal kernels. WOW-factor work is mostly presentation/prompt-engineering layered on top of existing infrastructure — much of it can be done in parallel with backend integration.

---

## 15. Risks & Open Questions

| Risk | Mitigation |
| --- | --- |
| Coupling-matrix tuning produces unrealistic timing | Start from literature-cited Weibull params; iterate against scenario timing; explicit defense in technical report |
| PINN training unstable / slow | Pre-train offline; keep model tiny; **fallback:** swap to a learned regressor surrogate; physics narrative still holds for the rule-based components |
| Late-interaction retrieval index too slow at demo time | Pre-index everything; cap historian rows; **fallback:** dense embeddings (Voyage / OpenAI) |
| GA fitness landscape ugly → boring evolution graph | Tune mutation rates; pre-canned good seed; **fallback:** Bayesian opt with Optuna |
| Three-scenario sim runs too slow live | Pre-run before demo, replay at 10× speed; live mode as the second demo step |
| Agent hallucinates despite grounding protocol | Use structured output (Pydantic) for citations; refuse-to-answer template if no tool result; show empty tool result clearly in UI |

**Open questions to resolve before kickoff:**
- [ ] Which two cities for the weather scenarios? (default: Barcelona, Phoenix)
- [ ] Which member owns each block in the time budget?
- [ ] Are we using Claude Agent SDK or LangGraph for the agent loop? (lean Claude Agent SDK)
- [ ] Demo length and order — does the live sim or the chat panel open the demo?

---

## 16. Things Explicitly NOT Doing — and Why

| Considered | Status | Reason |
| --- | --- | --- |
| Voice interface | ❌ skip | Pretty wrapper, hollow if backend looks shallow; +3h cost, demo says nothing about engineering |
| Reinforcement learning maintenance agent | ❌ skip | Needs simulator + days of training; sim-to-real openly unsolved; GA gives same demo for 1/3 the cost |
| Custom Metal / CoreML kernels for PINN | ❌ skip | PyTorch MPS does this for free on M3 Max; 6–10h cost for zero demo improvement |
| NVIDIA Omniverse photoreal twin | ❌ skip | Impossible in 36h; the brief is about decision intelligence, not graphics |
| Direct training on Kaggle FDM datasets / NASA C-MAPSS | ❌ skip | Domain mismatch will get called out by HP engineer judges |
| Claiming proprietary S100 failure parameters | ❌ skip | We don't have them; use literature-cited binder-jetting tribology and bearing Weibull params instead |
| MCP-style tool servers | ❌ skip | Defining tool schemas in-code is sufficient for hackathon; full MCP = overkill |

---

## 17. Pitch Sentence (memorize for demo)

> *"We built a Digital Co-Pilot grounded in published binder-jetting failure physics, with cascading degradation across all three subsystems. A physics-informed neural surrogate predicts heater drift; an agentic copilot queries the historian via late-interaction tool-use to diagnose root causes with timestamped citations; and a counterfactual engine answers 'what if we'd intervened earlier.' We compare three scenarios — Barcelona humid, Phoenix dry, and AI-managed — and show 34% uptime gain from autonomous maintenance over a fixed schedule."*

Five concrete technical claims, each verifiable. None buzzword-only.

---

## Appendix A — Decision Log (key reversals from initial brainstorm)

- **Kaggle real-data training** → rejected. Use literature-cited Weibull params instead.
- **Custom Metal kernels** → rejected. PyTorch MPS is free.
- **Voice interface** → rejected. Polish only if all else ships, but realistically skip.
- **One linear cascade chain** → replaced with three parallel cascades. More realistic, more demo angles.
- **3 components minimum** → expanded to 6. Richer twin, more cascade options, still tight enough to model well.
- **Dense embeddings for RAG** → replaced with late-interaction (LateOn-Code-edge). Telemetry tokens are code-like.
- **Full RL maintenance agent** → replaced with GA. Visible evolution, hackathon-feasible, no training instability.
- **Causal DAG library (DoWhy)** → replaced with simulator-checkpoint branching. We own the sim; statistical causality is overkill.
