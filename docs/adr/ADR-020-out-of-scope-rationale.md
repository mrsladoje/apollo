# ADR-020: Out-of-scope decisions and rationale

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §3.4, §21, Appendix B; effectively every other ADR

## Context

A 36-hour hackathon is won by what is *not* built as much as by what is. This ADR consolidates every major capability we considered and deliberately rejected, with the reasoning per item, so that during the build no one re-litigates a settled call at 03:00. Each subsection below is a separate micro-decision; the meta-decision of this ADR is the policy of writing them down.

## Decision

Skip all of the items below for the hackathon submission. Each item lists the context, the decision (= skip), the rejection rationale, and the conditions under which it could be reconsidered post-hackathon.

---

### 1. Voice / audio interface

**Context:** The HP brief's "living entity" framing tempts a voice UI. Apollo could speak its first-person lines aloud (ADR-019).
**Decision:** Skip.
**Why rejected:** A pretty wrapper that goes hollow if the backend looks shallow. Estimated 3–4 h of TTS plumbing, voice selection, and audio-routing on conference Wi-Fi for zero net wow over a well-designed text panel with streaming (ADR-017). The brief explicitly does not require it (§3.4).
**Reconsider if:** Backend ships ahead of schedule by Saturday morning *and* a clean ElevenLabs/OpenAI TTS path is one config flag away.

### 2. Reinforcement-learning maintenance agent

**Context:** A learned policy is the natural-sounding answer to "optimize maintenance," and it is exactly what a generic AI demo would propose.
**Decision:** Skip; use a Genetic Algorithm via DEAP (ADR-011, PRD §11.3).
**Why rejected:** RL needs a stable simulator plus days of training; sim-to-real generalization is openly unsolved in industrial maintenance literature; PPO/DQN training curves are unpredictable on a 36-h clock. GA gives a *visible* fitness curve — a better demo asset — and is hackathon-feasible.
**Reconsider if:** The project moves past hackathon and gains weeks of compute time on the simulator for offline RL.

### 3. Custom Metal / CoreML / MLX kernels for the PINN

**Context:** We are running on M3 Max; custom Apple-silicon kernels would sound impressive in a slide.
**Decision:** Skip.
**Why rejected:** PyTorch MPS does this for free at our tiny model size (~10–50 k params, PRD §11.1). Custom-kernel work is 6–10 h for *zero* demo improvement, and at this parameter count MPS's launch overhead can actually be slower than CPU. The PINN narrative does not depend on the substrate.
**Reconsider if:** We scale to a fleet of much larger PINNs where MPS launch overhead amortizes.

### 4. NVIDIA Omniverse photoreal twin

**Context:** "Digital twin" rhetorically invites a photoreal 3-D model.
**Decision:** Skip.
**Why rejected:** Impossible in 36 h; the brief is about *decision intelligence* not graphics; Omniverse setup alone exceeds our entire UI budget. Cascading-failure legibility (PRD §1) is a 2-D problem solved better by Recharts plus a SVG isometric.
**Reconsider if:** Post-hackathon partnership with HP grants S100 CAD and a graphics specialist.

### 5. Direct training on Kaggle FDM datasets / NASA C-MAPSS

**Context:** Public failure datasets are an obvious shortcut to "real data."
**Decision:** Skip.
**Why rejected:** Domain mismatch will be called out instantly by HP engineer judges. FDM ≠ metal binder jet (different powder, different physics, different failure modes). Turbofan thermal cycling ≠ binder rheology. Training on the wrong physics is worse than transparent synthetic data with literature-cited Weibull params.
**Reconsider if:** A binder-jet-specific dataset is released or licensed from HP.

### 6. Time-series foundation models (Chronos-2, TimesFM 2.5, Moirai-MoE)

**Context:** The 2025/2026 wave of TS foundation models would forecast component health zero-shot.
**Decision:** Skip.
**Why rejected:** Sledgehammer for six simulated components; contradicts the PINN+rule-based narrative (ADR-001) that is the whole pitch; adds *zero* physics insight. A judge asking "why does the heater fail at hour 7" deserves a Coffin-Manson answer, not a transformer's opinion.
**Reconsider if:** The product evolves toward fleet-scale forecasting where physics-per-component does not scale.

### 7. Survival analysis (lifelines, scikit-survival)

**Context:** Time-to-failure is canonically a survival problem.
**Decision:** Skip.
**Why rejected:** Duplicative with the rule-based decay + GA stack (ADR-006, ADR-011). Cox/Kaplan-Meier wants historical failure data we do not have; on synthetic seeded scenarios it is curve-fitting our own simulator. Adds a third forecasting voice that can disagree with the first two on stage.
**Reconsider if:** Real fleet failure histories become available and survival regression is a defensible add over conformal intervals (ADR-015).

### 8. PyOD anomaly detection

**Context:** A second opinion on "is something weird happening" sounds defensive.
**Decision:** Skip.
**Why rejected:** Would create a second source of truth that disagrees with the simulator's *ground-truth* events on stage. The simulator already knows when a component crosses CRITICAL; adding an unsupervised anomaly model that flags or misses the same event is pure downside risk in a live demo.
**Reconsider if:** We deploy on a real printer where ground truth is no longer ours to define.

### 9. ECharts swap from Recharts

**Context:** ECharts has fancier interactions and animation.
**Decision:** Skip; stay on Recharts (PRD §15).
**Why rejected:** Recharts is sufficient at our data scale (a few thousand points per chart). Mid-hackathon library swaps are a classic time sink — re-styling, re-wiring click handlers (FR-3.8), re-doing the conformal band rendering (ADR-015). The polish ROI is negative inside 36 h.
**Reconsider if:** The product needs interactive zoom over millions of points.

### 10. Local LLM fallback (Ollama + Qwen 2.5 / Llama 3.3)

**Context:** Conference Wi-Fi can fail (R-7).
**Decision:** Skip.
**Why rejected:** No 70B-class local model running on a single M3 Max can match Sonnet-class reasoning + tool-use reliability. Using a local model as the *primary* path drops grounding quality below NFR-6's gate. As a *fallback* it would silently degrade the demo without anyone noticing until a wild-card question fails.
**Mitigation instead:** Tether to phone hotspot; pre-record canned demo path; live mode is the *second* demo step (NFR-9).
**Reconsider if:** Frontier-class local models close the reasoning gap.

### 11. Full 3D printer model (React-Three-Fiber)

**Context:** A spinnable S100 model would look great on the dashboard.
**Decision:** Skip.
**Why rejected:** No CC-licensed S100 mesh exists; modeling one is 10+ hours of CAD work; the brief explicitly is not about graphics.
**Mitigation instead:** A 1.5-h SVG isometric schematic with red overlays on degraded components is the agreed visual fallback.
**Reconsider if:** HP releases or licenses a model.

### 12. Vercel AI SDK for streaming

**Context:** Vercel AI SDK is the textbook React streaming choice.
**Decision:** Skip; pure `sse-starlette` + native `EventSource` (ADR-017).
**Why rejected:** Vercel AI SDK assumes Next.js / `useChat` patterns; adopting it would force a React-framework rewrite of an already-built Recharts dashboard for zero added demo value.
**Reconsider if:** The frontend gets rebuilt on Next.js post-hackathon.

### 13. MCP-style tool servers

**Context:** MCP is the moment's standard for exposing tool servers.
**Decision:** Skip; define tool schemas in-code in the agent loop.
**Why rejected:** Hackathon-scope tools (FR-3.6) are five callables that share a process with the agent. Spinning up MCP servers for them adds inter-process plumbing, schema-registration latency, and a second thing that can break on stage. In-code Pydantic schemas are sufficient and faster.
**Reconsider if:** Apollo grows tools that legitimately live in separate processes (e.g. an actual MES integration).

### 14. Multi-printer fleet view

**Context:** A CFO panel showing twenty printers is a familiar SaaS visual.
**Decision:** Skip.
**Why rejected:** Would dilute the single-printer cascade story (CSC-A/B/C). The whole pitch is *one* printer's components cascading; multiplying that twenty times trades depth for breadth and confuses the narrative.
**Reconsider if:** The product targets fleet operations rather than single-machine intelligence.

### 15. Live Twilio emergency phone call

**Context:** "Apollo phones the operator when CRITICAL" is a movie moment.
**Decision:** Skip.
**Why rejected:** Gimmicky, brittle on conference Wi-Fi, can fail loudly mid-demo, and adds no rigor. A push notification or an SMS are equally gimmicky for less risk; we ship neither.
**Reconsider if:** A real operator-paging integration is part of a paid pilot.

### 16. Operator-persona switching (CFO/Engineer/Tech UI modes)

**Context:** Personas P-1/P-2/P-3 (PRD §4) tempt a per-persona UI mode.
**Decision:** Skip.
**Why rejected:** Roughly 2 h better invested in Apollo voice quality (ADR-019) and the eval harness (ADR-018). The same telemetry is already legible to all three personas through a single Apollo voice — that is the design claim of §4.
**Reconsider if:** User testing post-hackathon shows personas need distinct surfaces.

### 17. Causal DAG library (DoWhy / EconML / CausalPy)

**Context:** Counterfactual reasoning ("what if we had swapped the blade earlier?") naively suggests a causal-inference library.
**Decision:** Skip; use simulator checkpoint + branch + diff (ADR-012, PRD §11.4).
**Why rejected:** We *own the simulator*. Statistical causal inference is for when you cannot rerun the world. We can. Branching from a checkpoint produces a literal alternate universe — judge-defensible, exact, no DAG-tuning, no untestable assumptions.
**Reconsider if:** The product moves to observational data from real printers where the simulator is no longer ground truth.

---

## Consequences

**Positive:**
- A single document ends every "should we add X" debate during the build.
- Honest about *why* each item was rejected — judges reading the technical report see a deliberate scope, not a small one.
- Mitigations and reconsider-conditions document the post-hackathon roadmap.

**Negative / accepted tradeoffs:**
- We will be asked about each of these in Q&A. We have a one-sentence answer per item, ready.
- Some items (RL agent, voice UI, photoreal twin) are exactly what a non-technical observer expects from "AI digital twin." We accept that explaining *why we did not do them* is part of the pitch.

**Neutral / mitigations:**
- This ADR is the canonical home for any future "we considered but skipped" decisions during the build.

## References

- PRD §3.4, §21, Appendix B
- ADR-001, ADR-008, ADR-011, ADR-012, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019
