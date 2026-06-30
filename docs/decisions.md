# Design decisions

A frozen record of choices that shape the project. v0 entries are kept for historical context (they explain why v1 looks the way it does); v1 entries are the live design.

## v0 — atomic task pass (concluded, superseded by v1)

v0 tested **atomic memory + atomic update**: one fact per memory, explicit-style updates ("X switched to Y. They don't use Z anymore."), n=200, five systems. Conclusion: at this granularity, modern LLMs solve updates trivially from raw context, naive baselines saturate at 100%, and mem0 underperforms only because its internal LLM extraction is non-deterministic. The v0 tasks (fusion, rewrite-preservation) and the supporting baselines (`naive_markdown`, `long_context`, `regex_markdown`) live in `src/` and are kept for code reuse, but their results are not the project's headline. See git history (PR #2) for the data.

## v1 design (active)

Active task suite is specified in [`docs/v1/README.md`](./v1/README.md). Four task types: T4 split intake, T2 compound update, T1 surgical edit, T3 cross-memory. Built and run in that order.

## Agent + judge LLM
- DeepSeek-V3 for both.
- Known self-evaluation bias is acknowledged in the README.
- Judge is programmatic (word-boundary substring matching against ground-truth values) wherever possible.

## mem0 internal stack
- LLM (used by mem0 internally for fact extraction and conflict resolution): DeepSeek (same key as the agent).
- Embedder: `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` (384-dim, ~90MB), loaded from a local `models/` directory rather than downloaded at runtime.
- Vector store: qdrant in embedded mode (file-backed under a tempdir, no server).
- Trade-off: using DeepSeek for both the agent and mem0's internal LLM means the same model decides what to extract AND what to recall — a small additional source of correlated error, but consistent with the single-LLM constraint.

### Setting up the local embedding model
The `models/` directory is git-ignored. To populate it:
```bash
mkdir -p models/multi-qa-MiniLM-L6-cos-v1/1_Pooling
cd models/multi-qa-MiniLM-L6-cos-v1
BASE="https://hf-mirror.com/sentence-transformers/multi-qa-MiniLM-L6-cos-v1/resolve/main"
for f in config.json config_sentence_transformers.json modules.json \
         sentence_bert_config.json special_tokens_map.json tokenizer.json \
         tokenizer_config.json vocab.txt model.safetensors; do
  curl -L -o "$f" "$BASE/$f"
done
curl -L -o 1_Pooling/config.json "$BASE/1_Pooling/config.json"
```
Why local: this machine's network and Python stack don't play well with `huggingface_hub`'s download path (HEAD requests fail through hf-mirror even when direct `requests.get` works), so we shortcut the loader by pointing sentence-transformers at a local directory.

## Python version
- Python 3.11 (installed via `brew install python@3.11`). The system Python 3.9 from Xcode CommandLineTools is too old: ships LibreSSL 2.8.3 (breaks modern HF downloads) and lacks PEP 604 `X | None` syntax that mem0 2.0 uses.

## Case count
- Target n per v1 task: 100 (10 for smoke).
- Generated deterministically by seed; case JSONs committed for reproducibility.

## Storage
- Cases: JSON in `data/cases/`.
- Results: JSON in `data/results/`, one file per experiment run. Git-ignored.
- SQLite added only if/when a dashboard needs it.

## Out of scope (v1)
- Multi-LLM-vendor (Claude + GPT + Llama) writers and readers. Worth doing but out of scope for v1.
- Privacy / leakage testing. GateMem already does that.
- AMH adapter and other commercial memory products.
- Training, fine-tuning, or evaluating any LLM itself.

## Risks we're tracking

| Risk | How likely | What we'll do |
|---|---|---|
| A v1 task doesn't discriminate systems (saturation at 100% or floor at 0%). | Medium. Already burned by this in v0. | Each task ships with a smoke run; if smoke saturates or floors across systems, redesign before scaling to n=100. |
| Self-eval bias inflates a system. | Medium-low (judge stays programmatic). | Document in README. If LLM judging gets added, re-judge a sample with a different model. |
| Benchmark dismissed as "handpicked tasks favor naive baselines." | Low-medium. | Case generators are programmatic and seeded; anyone can rerun. v1's four tasks deliberately stress different memory capabilities so no single class of system can win on all four. |
| Time runs out before public artifact (chart + writeup). | High. | Each v1 task is independently presentable. Even one task at n=100 with a clear chart is shippable. |
