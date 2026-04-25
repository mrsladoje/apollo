# ADR-010: Late-interaction retrieval with LightOn LateOn-Code-edge + PyLate

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.2, §18.2, NFR-4, FR-3.6 (tool 2: `late_interaction_search`); ADR-009 (Pattern C)

## Context

The agent's `late_interaction_search` tool is the semantic-retrieval arm of Pattern C: when a query like *"nozzle clog escalation"* needs to find the right rows of the historian, we need a retriever that handles industrial telemetry tokens — strings like `motor_rpm=4820`, `nozzle_clog_prob=0.31`, `bearing_temp_C=78.2`, `psd_d50=24.5um`. These are not natural-language sentences. They are code-like, numeric-heavy, schema-dense.

Dense single-vector embeddings (text-embedding-3, Voyage, BGE) compress an entire row into one ~1500-dim vector via mean-pooling. That pooling is exactly the operation that destroys the signal we care about: the precise token `clog_prob` should match the query token `clog`, not be averaged into a soup. Late-interaction retrievers (ColBERT-style) keep one vector per token and score with MaxSim, which preserves token-level alignment — the right primitive for our data shape.

The remaining question is *which* late-interaction model. We need a small footprint (NFR-4: < 200 ms p95 over 10k rows on CPU), a permissive license, and decent code-token coverage. Running on the same M3 Max that's already training the PINN means we cannot afford a 110M+-parameter retriever.

## Decision

Use **LightOn LateOn-Code-edge** (17M parameters, output dim 48, Apache 2.0) as the late-interaction retriever, served via **PyLate** (LightOn's official framework). The historian is offline-indexed once per run batch into a PyLate index file colocated with `historian.db`. The agent's `late_interaction_search` tool wraps PyLate's query API with a Pydantic schema that returns `[(run_id, component, t, score, snippet), …]`.

Output dim 48 (vs 128 for canonical ColBERT) is intentional — the index is ~3× smaller and search ~3× faster, with empirically negligible recall loss on token-dense data per LightOn's published evals.

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| **Voyage-3 dense embeddings** | Strong general-purpose retriever, but mean-pools tokens. Numeric/code tokens lose precision. Also: external API call → latency variance + offline-mode pain. |
| **OpenAI text-embedding-3-large** | Same mean-pool problem; same API-dependency problem. Higher dim doesn't fix the architecture mismatch. |
| **BGE / E5 (open dense)** | Local, but still dense single-vector. Solves the API-dependency issue but not the token-pooling issue. |
| **Canonical ColBERTv2 (110M params, dim 128)** | Right architecture, wrong size. CPU latency at 10k rows pushes past the 200 ms NFR-4 budget on M3 Max; index size 3× larger. |
| **Hybrid BM25 + dense rerank** | Two systems to maintain; BM25 over our tokenization-unfriendly telemetry strings is brittle. Late-interaction subsumes both contributions in one model. |
| **No retriever — just SQL** | We already have `query_historian` for exact lookups. Semantic search is the *complement*: "find moments that look like this story" is exactly what late-interaction does well and SQL cannot. |

## Consequences

**Positive:**
- Token-level matching is the right primitive for `motor_rpm=4820` ↔ "motor RPM spike" queries; we get a defensible "why late-interaction" pitch line in the demo.
- 17M params + dim 48 → CPU-only, no API key, works offline at the venue (mitigates R-7).
- Apache 2.0 license — usable in open-source repo with no friction.
- PyLate provides batch indexing, persistence, and MaxSim scoring out of the box — integration cost is hours, not days.

**Negative / accepted tradeoffs:**
- Late-interaction indexes are larger than dense indexes (one vector per token, not per row). At 10k rows × ~30 tokens × dim 48 we're around ~60 MB — fine for laptop, would matter at fleet scale.
- LateOn-Code-edge is a niche model. If a bug surfaces during the build, community help is thinner than for OpenAI embeddings. Mitigated by R-3 fallback: swap to Voyage / OpenAI dense embeddings as a last resort; the `late_interaction_search` tool schema stays identical.
- Output dim 48 is below ColBERT's default 128. We accept some recall loss on rare tokens; the historian vocabulary is small and structured, so this is unlikely to bite.

**Neutral / mitigations:**
- Index is regenerated per benchmark batch, not per simulation step — indexing cost doesn't enter the live latency budget.
- The tool returns a `score` field, so the agent can decide when to refuse vs. answer — enables FR-3.5 grounding behavior even on near-misses.

## References

- PRD §11.2, §18.2, NFR-4, FR-3.6
- ColBERT / late interaction: Khattab & Zaharia, 2020 — *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT*
- LightOn LateOn-Code-edge model card and PyLate documentation
- PRD Appendix B: "Dense embeddings for RAG → replaced with late-interaction"
