# Roadmap

A living checklist. Keep it short. When something moves to `done`, that's a commit-worthy milestone.

## Definition of done

The project is "done" when these three things are public and findable from one search:

1. **The repo** — code, results, READMEs, anyone can reproduce.
2. **A chart** — one image that conveys a finding without text.
3. **A writeup** — 500-word blog post with the chart and the one-sentence takeaway, written for someone who uses AI tools daily.

## Done

- **Project scaffold**: DeepSeek client, runner, judge, memory adapters, per-case error handling and progress logging, and automated tests.
- **v0 atomic-task pass — concluded that atomic memory + atomic update is too trivial to discriminate systems.** Code+data removed when v1 superseded; the lesson is the only thing we kept.
- **v1 / T4 — split intake (n=100)**. mem0 0.555 per-detail recall vs naive_markdown 0.952. 95% CIs do not overlap. Failure-mode analysis: mem0's misses are 67% hallucinated wrong values (vs 38% for naive). See [`docs/v1/t4_findings.md`](./v1/t4_findings.md), [`docs/v1/t4_results.png`](./v1/t4_results.png).
- **v1 / T2 — corrected five-system result.** Matcher and authored aliases fixed; two invalid no-op cases excluded; mem0 rerun with full per-case isolation. Final n=298 result: naive update recall 0.999, mem0 0.976, AMH 0.893; no-collateral 0.978, 0.961, and 0.978 respectively. pure_vector remains a diagnostic n=99 run.
- **Preference Track pilot (n=30, one run)**. English-only benchmark inputs; `naive_markdown` 30/30, `mem0` 30/30, `AMH` 28/30. This validates the track but is not a final ranking.
- Local sentence-transformers model checked in via manual download (HF library path blocked by SSL/HEAD issues on this machine).
- Python 3.11 baseline established; documented in `docs/decisions.md`.

## Now

- Consolidate the factual and preference tracks into one reproducible public artifact while keeping their metrics and conclusions separate.

## Next

- Produce the final T2 chart from the corrected five-system result.
- Decide whether to scale the Preference Track beyond the 30-case pilot after reviewing its current saturation.

## Later factual-memory tasks

- **T1 — surgical edit on long memory.** First a richly detailed memory, then a small update that changes one embedded detail. Tests localized edit under conflict.
- **T3 — cross-memory.** One update touches several past memories scattered across sessions. Tests cross-session consolidation — the place mem0's design promises value.

## Parking lot (don't do yet)

- Streamlit dashboard. Defer until at least two tasks × four systems × 100 cases exist.
- Multi-LLM-vendor experiment (Claude writes, GPT reads). Interesting but expensive.
- Letta, Zep, mem0 Platform adapters. Each is a multi-day integration; add only after T4 + T2 results justify the breadth.
- "Implicit-style" updates ("X now uses Y", no explicit retirement signal). v1.5 variant.
- spaCy install for mem0. Currently noisy warning, not blocking.

## Anti-goals (we are explicitly NOT doing these)

- Training, fine-tuning, or evaluating any LLM itself. This benchmarks memory *systems*, not models.
- Building a new memory system. We benchmark existing ones.
- Reproducing single-agent long-term memory benchmarks. LongMemEval / LoCoMo already do that.
- Privacy / leakage testing. GateMem already does that.

## Open questions

- **Decomposition semantics for T4.** If a user statement contains 8 details, is the "correct" memory shape 1 entry or 8? See `docs/v1/README.md` design questions. v1 dodges by scoring on per-detail retrievability, not on storage shape.
- **Self-evaluation bias from DeepSeek-only.** Document explicitly before publishing any v1 number. Possibly re-judge a sample with a different model as a robustness check.
