# Design decisions (v0)

A frozen record of the choices that locked v1's scope. Anything not listed here
is up for re-discussion when the data starts coming in.

## Tasks
- **Main**: fusion (Agent A writes half, Agent B writes half, Agent C uses both).
- **Auxiliary**: rewrite-preservation (one update should not damage N-1 unrelated facts).
- v1 ships fusion only. Rewrite added once fusion is stable.

## Systems under test (v1)
- `no_memory` (floor)
- `naive_markdown` (50-line dumb shared baseline; might surprisingly win)
- `mem0` (popular OSS representative)
- Hard cap: 3 systems in v1. Expanding requires explicit decision.

## Agent + judge LLM
- DeepSeek-V3 for both.
- Known self-evaluation bias is acknowledged in the README.
- Judge is programmatic (fact-list substring matching) wherever possible.

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
- 100 cases per task is the target. 50 is the smoke threshold.
- Generated deterministically by seed; case files are committed.

## Storage
- Cases: JSON in `data/cases/`.
- Results: JSON in `data/results/`, one file per experiment run.
- SQLite added only if/when the dashboard needs it.

## Frontend
- Streamlit dashboard, deferred to v2.
- v1 ships with matplotlib static plots in a notebook.

## Out of scope (v1)
- Multi-LLM-vendor (Claude + GPT + Llama) testing.
- Conflict resolution / temporal correctness as standalone tasks.
- Privacy / leakage testing (interesting but separate benchmark).
- AMH adapter — interesting but not core to v1's question.

## Risks we're tracking

| Risk | How likely | What we'll do |
|---|---|---|
| The task is too easy — every system saturates at 1.00 and differences can't show up. | High (already observed at n=5). | Add difficulty: more facts per persona, filler turns between writes, paraphrased probes that don't name categories. |
| A 5%-ish delta at n=100 turns out to be sampling noise. | Medium. With recall clustered near 1.0, small deltas may be noise. | At n=100, also report a binary metric ("did this system miss ANY fact in this case") — more robust at the ceiling. |
| Self-eval bias inflates one or more systems. | Medium-low (judge is programmatic, not LLM-based). | Documented in README. If LLM judging gets added later, re-judge a sample with a different model. |
| Benchmark dismissed as "the author handpicked tasks that favor naive baselines." | Low-medium. | Case generator is programmatic and seeded; anyone can rerun. Adding a second task (rewrite-preservation) that doesn't a-priori favor either type of system also helps. |
| Time runs out before public artifact (chart + writeup). | High (always). | Milestone 2 — results + plot — is already presentable on its own. The writeup amplifies but isn't a prerequisite. |
