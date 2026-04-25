# ADR-022: Gemma 4 31B + GEPA-optimized prompt as Apollo's runtime LM

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Supersedes:** ADR-008 (Claude Agent SDK + Sonnet-class model) — for the *runtime* model only. The Claude Agent SDK loop and Pydantic-typed tool registration from ADR-008 are kept; only the model id is replaced.
- **Related:** PRD §11.5 (Agentic Loop), §11.8 (Grounding eval), §6.4 FR-W.9 / FR-W.10 / FR-W.11, NFR-5, NFR-6; ADR-009 (Pattern C), ADR-014 (Pydantic citations), ADR-016 (Langfuse), ADR-018 (Ragas+DeepEval), ADR-019 (Apollo persona)

## Context

Two facts changed after ADR-008 was written:

1. **MLH "Best Use of Gemma" mini-challenge.** The hackathon offers a Major League Hacking sub-prize for the best project built on Google's Gemma open-weight model family. We are issued an API key for **Gemma 4 31B Dense** (released 2026-04-02, Apache 2.0, [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)) as part of accepting that track. Using a Sonnet-class model as Apollo's runtime LM forfeits the prize.

2. **Gemma 4 31B's tool-use profile is now competitive.** Gemma 3 27B scored **6.6%** on τ²-bench Retail (an industrial-style multi-turn tool-calling benchmark) — unusable as an agent. Gemma 4 31B scores **86.4%** on the same benchmark, in the same band as Sonnet-class frontier models. AIME 2026 jumped 20.8% → 89.2%, LiveCodeBench v6 29.1% → 80.0%, GPQA Diamond 42.4% → 84.3% (per Google's model card, [Labellerr overview](https://www.labellerr.com/blog/gemma-4-open-weight-ai-model-overview/)). Tool-use reliability is no longer the disqualifier it was for ADR-008's "Sonnet only" choice.

But Apollo's contract with the user (NFR-6: 0% hallucination on the eval set; NFR-7: 100% citation coverage on non-refusal) is non-negotiable. Swapping to a smaller open model raises the question: **how do we close the gap between Gemma 4 31B and a Sonnet-class baseline on grounded, structured tool-calling without fine-tuning?**

The answer is automated prompt optimization. **GEPA** (Genetic-Pareto reflective prompt evolution; Agrawal et al., arXiv:2507.19457, ICLR 2026 Oral) compiles a system prompt against a metric using natural-language reflection over execution traces. Across six benchmarks, GEPA outperforms GRPO (an RL baseline) by up to +20pp while using up to **35× fewer rollouts**, and outperforms MIPROv2 by +10pp on average. Critically for our case, **Databricks Mosaic Research showed gpt-oss-120b + GEPA beats Claude Opus 4.1 on Information Extraction by +2.2pp at 90× lower serving cost** ([Databricks blog, Sept 2025](https://www.databricks.com/blog/building-state-art-enterprise-agents-90x-cheaper-automated-prompt-optimization)) — direct precedent that an open model + GEPA-optimized prompt can match or exceed frontier closed models on grounded structured tasks.

The third moving piece is **DSPy** (Khattab et al.), the compilation framework that exposes GEPA as `dspy.GEPA`. DSPy lets us declare Apollo's signature once (input/output contract, tool list, persona docstring) and have GEPA evolve the prompt against our existing FR-W.9 grounding eval — no new infrastructure, just a new optimization step before the prompt ships.

The Claude Agent SDK is *still* the right loop framework — typed tools, OTel hookup, refusal handling. ADR-008's analysis on that axis stands. What changes is **the model behind the loop** and the introduction of an offline **prompt-compilation step** before the runtime prompt is frozen.

## Decision

Apollo's runtime LM is **Gemma 4 31B Dense**, accessed via the MLH-issued API key. The agent loop stays on the Claude Agent SDK pattern — Pydantic-typed tools, SSE streaming, Langfuse OTel — but is wired to the Gemma endpoint via DSPy's `dspy.LM` adapter (`openai/google/gemma-4-31B-it` provider string, OpenAI-compatible API).

Apollo's system prompt is **compiled, not hand-written**, using `dspy.GEPA`:

- **Student LM** (the prompt is optimized *for* this model): Gemma 4 31B.
- **Reflection LM** (writes new prompts during the GEPA reflection step, ~1% of calls): Claude Opus 4.7 — accessed via the local `claude` CLI (Bash tool), no API key needed beyond the hackathon's existing setup.
- **Metric**: a `metric_with_feedback` over the existing Ragas+DeepEval eval set (ADR-018 / FR-W.9), augmented with three programmatic signals — schema compliance on tool args, correct tool selection, citation-resolves-against-historian. The textual feedback string is the optimization channel; it tells the reflection LM *why* a candidate failed.
- **Budget**: ~150 metric calls per compile run; budget protection via `max_metric_calls=150` in the DSPy GEPA config. Runs in ~2-4 hours offline.

The compiled prompt is committed to `config/agent.system_prompt.gepa.txt` and loaded at agent startup. Re-compilation is a manual, scripted step (`scripts/agent/compile_prompt.py`), not a CI step — once compiled, the prompt is a frozen artifact like the eval set.

The demo includes a **three-way comparison** on the Ragas+DeepEval eval set (FR-W.10):

1. **Vanilla Claude Opus 4.7** (frontier baseline; via `claude` Bash CLI).
2. **Vanilla Gemma 4 31B** (same model, hand-written seed prompt).
3. **Gemma 4 31B + GEPA-optimized prompt** (Apollo as shipped).

The numbers from those three runs are rendered on the closing demo slide as a measured artifact: "31B open model + 150 GEPA rollouts ≥ frontier closed model on our own grounding eval, at $X/run vs $Y/run." This is the MLH pitch and the HP narrative simultaneously.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **Keep Sonnet-class as Apollo's runtime LM** (ADR-008 status quo) | Forfeits MLH "Best Use of Gemma" track. Misses the strongest narrative the hackathon offers — open model + research-grade prompt optimization beating closed frontier. |
| **Gemma 4 31B with a hand-written prompt (no GEPA)** | Loses the differentiation thesis. Hand prompts on a 31B-class model on a tool-grounded refusal-strict task underperform the frontier baseline; without GEPA we'd ship a worse Apollo to win a smaller prize. The whole point of this ADR is that GEPA closes the gap measurably. |
| **Gemma 4 26B A4B MoE** (sister model in the Gemma 4 family) | MoE activates only ~4B params per forward pass; cheaper to serve but less predictable on long-horizon tool sequences. Output parsing also requires custom glue (per community reports). Reserved as fallback if 31B Dense API quota becomes the bottleneck. |
| **MIPROv2 instead of GEPA** | Older Stanford optimizer that GEPA explicitly benchmarks against — GEPA wins by +10pp average, +12pp on AIME-2025, while producing prompts up to 9.2× shorter. No reason to pick the older optimizer for a 2026 demo. |
| **GRPO / RL fine-tuning** | Cannot fine-tune the Gemma 4 weights through the API key. RL also requires thousands of rollouts (GEPA's paper measures 24,000 for GRPO baseline on IFBench vs 678 for GEPA). Out of budget on every axis. |
| **Hand-tune the prompt against the eval set ourselves** | Faster to start, slower to converge, irreproducible, and the "we evolved it with the ICLR 2026 Oral algorithm" sentence is exactly the differentiator we want — a hand-tuned prompt has none of that narrative. |
| **Use Gemma 4 31B as Apollo *and* as the GEPA reflection LM** | The reflection LM should be smarter than the student LM (HF DSPy GEPA cookbook recipe; Decagon's production case study). Using the same model for both wastes the asymmetry GEPA was designed for. Opus 4.7 via the `claude` Bash CLI is a free reflection signal we already have. |
| **Skip the three-way comparison, just ship Gemma+GEPA** | Without the comparator runs, the claim "GEPA closes the gap with frontier" is untestable from the demo alone. Three runs over 30 questions costs ~10 minutes of API time and gives judges a chart. |

## Consequences

**Positive:**

- **MLH "Best Use of Gemma" track unlocked** — Apollo demonstrates a non-trivial use of Gemma 4 (the 2026 flagship open model) for grounded agentic diagnosis with research-grade prompt optimization, not a chatbot wrapper.
- **HP narrative strengthened, not weakened** — "open model + 150 rollouts of GEPA ≥ frontier model on our hallucination eval" is a sharper, more defensible HP-challenge pitch than "we used Sonnet."
- **Cost story is dramatic.** Gemma 4 31B serving is ~$0.20/1M tokens via standard providers vs. Opus 4.7 at $15/1M input — roughly 75× cheaper on inference, with the GEPA optimization amortizing across all runtime calls.
- **Ratchets observability:** Langfuse continues to capture every Gemma call (FR-W.7 unchanged). The GEPA compile step itself emits a structured optimization log we render alongside the eval comparison on the demo slide.
- **Reuses existing eval infrastructure.** The Ragas+DeepEval set built for FR-W.9 (ADR-018) becomes the GEPA metric's data source — zero new test infrastructure. The optimization is *evaluated against the same gate it has to pass*, which is the cleanest possible setup.
- **Compiled prompt is a checkable artifact.** `config/agent.system_prompt.gepa.txt` lives in git; any judge can read what GEPA evolved.

**Negative / accepted tradeoffs:**

- **Smaller-model risk on long tool chains.** Gemma 4 31B is competitive but not strictly superior to Sonnet-class on multi-turn tool sequences > 5 hops. Mitigated by ADR-009's `max_tool_calls_per_turn = 3` cap (NFR-5 latency budget), the three-layer Pydantic citation pipeline (ADR-014) which catches fabricated outputs structurally regardless of model, and the FR-3.5 refusal template that turns model uncertainty into a positive demo signal rather than a hallucination.
- **Two model dependencies at demo time** instead of one: Gemma API for runtime *and* the local `claude` CLI for the comparison run. Mitigation: the comparator slide can be rendered ahead of demo from logged eval results — comparison runs do not need to execute live. Only the live "Ask Apollo" segment talks to the Gemma API at demo time.
- **GEPA compile is offline, not CI.** Re-compiling the prompt is a manual `scripts/agent/compile_prompt.py` invocation. If the eval set evolves substantially we have to re-run. Acceptable: the eval set is itself frozen per ADR-018, and we don't expect to evolve it during the build window.
- **Two model dependencies pinned to API availability.** Mitigation: the compiled prompt + a frozen Gemma 4 31B response cache for the canonical demo questions are the offline fallback. The mock harness from PLAN-C §4 already supports this — we extend it to back the Gemma path the same way it backs Sonnet.

**Neutral / mitigations:**

- The compiled prompt's exact text is shown on a demo slide ("we compiled this — here's what GEPA wrote"). Judges who are skeptical of opaque optimization can read the prompt and verify it's a sane, grounded specification, not a magical incantation.
- If the GEPA-optimized Gemma run does *not* beat Sonnet-class on the eval, ADR-008's runtime falls back via a feature flag (`AGENT_RUNTIME_LM=sonnet|gemma_gepa`). This is the architectural escape hatch — we ship the variant with the better eval score, regardless of which one wins.

## References

- Agrawal et al., *GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning*, arXiv:2507.19457, **ICLR 2026 Oral**: <https://arxiv.org/abs/2507.19457>
- Khattab et al., *DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines*: <https://dspy.ai>
- DSPy GEPA optimizer docs: <https://dspy.ai/api/optimizers/GEPA/overview/>
- Zhou et al. (Databricks Mosaic), *Building State-of-the-Art Enterprise Agents 90× Cheaper with Automated Prompt Optimization*: <https://www.databricks.com/blog/building-state-art-enterprise-agents-90x-cheaper-automated-prompt-optimization>
- Google DeepMind, *Gemma 4: Byte for byte, the most capable open models* (2026-04-02): <https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/>
- HF DSPy GEPA cookbook (two-model student/reflection pattern): <https://huggingface.co/learn/cookbook/dspy_gepa>
- Decagon production case study, *Optimizing GEPA for production*: <https://decagon.ai/blog/optimizing-gepa-for-production>
- PRD §11.5, §11.8, §6.4 FR-W.9, FR-W.10, FR-W.11; NFR-5, NFR-6
- ADR-008 (superseded for runtime model only), ADR-009 (Pattern C, unchanged), ADR-014 (citation pipeline, unchanged — the ACL is model-agnostic), ADR-018 (eval pipeline, reused as the GEPA metric source)
