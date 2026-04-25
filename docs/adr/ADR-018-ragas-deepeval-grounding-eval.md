# ADR-018: Ragas + DeepEval for automated grounding eval

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.8, §6.4 FR-W.9, §17 M9e, §7 NFR-6, §16.1, §16.2; ADR-009 (Pattern C — Agentic Diagnosis), ADR-014 (Pydantic citations + refusal templates)

## Context

NFR-6 commits to a **0 % hallucination rate** on the demo evaluation set, and §16.1's submission gate makes that pass-required. Without an automated, reproducible eval, "0 % hallucination" is a marketing line that any HP engineer judge can puncture in thirty seconds with one wild-card question. We need to turn the claim into a CI-style measurement: a committed test set, a deterministic scoring run, and a number printed in the README and demo slide.

The naive option is hand-authoring a 30-question Q/A set and grading by hand. That is roughly 1.5 hours of soul-crushing work that produces a brittle artifact: questions reflect *our* blind spots, answers drift as the agent prompt evolves, and re-running after every change is manual. We want the eval set itself to be generated from the historian and the component documentation, and graded by faithfulness/hallucination metrics that operate on (claim, retrieved-context) pairs.

## Decision

Adopt a two-library pipeline:

1. **Ragas `TestsetGenerator`** generates 30 grounded question/answer pairs from component descriptions plus sample telemetry windows pulled from the SQLite historian (ADR-007). The generator emits `(question, ground_truth, contexts)` triples we commit under `tests/eval/grounding_set.json`.
2. **DeepEval** runs `FaithfulnessMetric` and `HallucinationMetric` over Apollo's responses to those questions, in a `pytest`-style script invoked via `deepeval test run`. The script consumes Apollo's actual streaming response (ADR-017) end-to-end so the eval reflects the demo path, not a mocked subset.

Pass gate (NFR-6, §16.2): **faithfulness ≥ 0.95** and **hallucination = 0**. The numeric result is rendered in the README and the closing demo slide as a measured fact. CI exit-code 0 is part of the submission gate (§16.1).

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Hand-authored Q/A set + manual grading | ~1.5 h of authoring + irreproducible. Drifts every time the prompt changes. No CI artifact. |
| LLM-as-judge alone (Claude grades Claude) | Single grader, no separation between faithfulness and hallucination, prone to "the model that wrote it grades it." Lacks Ragas' contextual-precision/recall decomposition. |
| TruLens | Heavier integration; tighter to LangChain than to Claude Agent SDK; less mature `pytest` integration. |
| Promptfoo | YAML-config DSL is great for prompt A/B but weaker for grounded RAG faithfulness specifically. |
| Phoenix evals | Couples to Arize Phoenix tracing, which we already rejected in favor of Langfuse (ADR-016). |
| Just `pytest` + assertion strings | No semantic grading; cannot detect paraphrased hallucinations. |
| Use only Ragas | Ragas' generator is excellent but its *judge* metrics overlap awkwardly with DeepEval's; DeepEval's `FaithfulnessMetric` + `HallucinationMetric` are the cleaner pass/fail surface for CI. |

## Consequences

**Positive:**
- Turns NFR-6 from a claim into an artifact judges can re-run from the repo.
- Eval set is *generated* from the historian, so it always reflects the live data — no drift between code and tests.
- `deepeval test run` exit-code 0 plugs directly into the submission gate.
- Provides a defensible "faithfulness 0.97" number on the demo slide.

**Negative / accepted tradeoffs:**
- Ragas generation itself uses an LLM, costing API tokens and ~2 minutes per regeneration.
- DeepEval's hallucination metric is itself LLM-graded, so we are checking a Sonnet-class agent with Sonnet-class judges. Mitigation: the *contexts* are deterministic historian rows, and the metric's prompt is published, so the grading is at least transparent and re-runnable.
- 2.5 h on the critical path (M9e); first to be cut per §17 cut order if schedule slips.

**Neutral / mitigations:**
- We freeze a generated set into `tests/eval/grounding_set.json` and commit it; regeneration requires an explicit script invocation, not every CI run, to keep results stable.

## References

- PRD §11.8, §6.4 FR-W.9, §17 M9e, §7 NFR-6, §16.1, §16.2
- Ragas: https://docs.ragas.io/
- DeepEval: https://docs.confident-ai.com/
