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
- Embedder: fastembed running locally (BAAI/bge-small-en-v1.5, 384-dim, ~130MB cached on first run). No extra API key.
- Vector store: qdrant in embedded mode (file-backed under a tempdir, no server).
- Trade-off: using DeepSeek for both the agent and mem0's internal LLM means the same model decides what to extract AND what to recall — a small additional source of correlated error, but consistent with the single-LLM constraint.

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
