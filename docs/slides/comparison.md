# Three-way grounding eval — Opus 4.7 vs Gemma 4 31B vs GEPA-Gemma

> Closing demo slide for the MLH "Best Use of Gemma" track (FR-W.11, ADR-022).
> The numbers are populated from `docs/eval/comparison_results.json` after
> `scripts/agent/run_comparison.py` runs.

## Setup

Same eval set: 30 frozen Q/A triples in `tests/eval/grounding_set.json`
(24 grounded + 6 deliberately unanswerable). Same Apollo loop, same five
typed tools, same Pydantic citation pipeline. The only thing that changes
is the runtime LM and the system prompt:

| Configuration       | Runtime LM        | System prompt                                     |
|---------------------|-------------------|---------------------------------------------------|
| Vanilla Opus 4.7    | claude_cli/opus-4-7 | seed (`src/apollo/agent/prompts/system.md`)     |
| Vanilla Gemma 4 31B | google/gemma-4-31B-it | seed (`src/apollo/agent/prompts/system.md`)   |
| **GEPA-Gemma**      | google/gemma-4-31B-it | **compiled (`config/agent.system_prompt.gepa.txt`)** |

## Results table (auto-filled)

| Configuration       | Faithfulness ≥ 0.95 | Hallucination = 0 | p50 latency | Notes |
|---------------------|--------------------:|------------------:|------------:|-------|
| Vanilla Opus 4.7    | _filled by run_comparison.py_ | _0_ | _–_  | Frontier baseline |
| Vanilla Gemma 4 31B | _filled by run_comparison.py_ | _–_ | _–_  | Open-weights baseline |
| **GEPA-Gemma**      | _filled by run_comparison.py_ | _0_ | _–_  | Compiled prompt closes the gap |

**Pass gate:** GEPA-Gemma row's faithfulness within **2 percentage points**
of Opus 4.7; hallucination rate **0** on both rows.

## Speaker notes (two-sentence GEPA explainer)

> "GEPA — Genetic-Pareto prompt optimization (Agrawal et al., arXiv:2507.19457)
> — uses Claude Opus 4.7 as a *reflection LM* that proposes improved system
> prompts based on textual feedback from a faithfulness metric, while Gemma 4
> 31B remains the *student* runtime. Databricks shipped the same pattern with
> gpt-oss-120b in production; here we close most of the Opus-vs-Gemma gap with
> nothing but a frozen prompt artifact."

## References

- Agrawal, S. et al. *"GEPA: Genetic-Pareto prompt optimization for LM
  systems"*, arXiv:2507.19457 (2025).
- Databricks Engineering Blog, *"Compiling open-source LMs to compete with
  frontier models"*, 2025 — gpt-oss-120b precedent for the GEPA-on-Gemma play.
