# Agent Memory Benchmark

A benchmark for evaluating LLM memory systems in **multi-agent shared-memory** scenarios.

## The question this exists to answer

In 2026, MCP, A2A, and shared-memory products are pushing toward a world where **multiple LLM agents (Claude, ChatGPT, Codex, custom agents) work off the same memory layer**. Every major memory benchmark today (LongMemEval, LoCoMo, MemoryBank, HaluMem, GateMem) still assumes a single agent reads and writes its own memory.

This benchmark fills the gap: **when N agents share one memory store, do existing memory systems hold up?**

## Status

🚧 **Active development.** The current focus is the v1 task suite — four task types designed to probe non-trivial memory operations (split intake, compound update, surgical edit, cross-memory). See [`docs/v1/`](./docs/v1/README.md) for the design.

An initial atomic-level pass (v0) is in the git history. It tested one-fact-per-memory + explicit-style updates and concluded that **atomic tasks don't discriminate memory systems** — modern LLMs reason out trivial updates from raw context, so a 30-line markdown baseline scores 100% and no headline finding emerges. The v0 scaffolding (agent client, runner, judge, mem0 adapter, baseline systems) is reused by v1; the v0 conclusions are not.

## Repo layout

```
src/
  agent.py             # DeepSeek client (used everywhere)
  judge.py             # programmatic scoring
  runner.py            # orchestrates write → read → judge per case
  systems/             # memory system adapters (one file per system)
  cases/               # task / case generators
scripts/               # CLI entrypoints
data/
  cases/               # generated case JSONs (committed for reproducibility)
  results/             # experiment outputs (git-ignored)
docs/
  v1/                  # active task spec
  decisions.md         # frozen design choices + setup gotchas
  roadmap.md           # done / now / next
  workflow.md          # how this repo makes changes
models/                # locally-vendored embedding model (git-ignored, see decisions.md)
```

## Setup

```bash
# 1. Python 3.11+ (system 3.9 will not work — SSL + syntax incompatibilities)
brew install python@3.11

# 2. Clone and virtualenv
git clone https://github.com/Gloria-Qi0311/agent-memory-benchmark.git
cd agent-memory-benchmark
python3.11 -m venv .venv && source .venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt sentence-transformers

# 4. API key
cp .env.example .env
# put your DEEPSEEK_API_KEY in .env

# 5. Embedding model — see docs/decisions.md for why this is manual
mkdir -p models/multi-qa-MiniLM-L6-cos-v1/1_Pooling
cd models/multi-qa-MiniLM-L6-cos-v1
BASE="https://hf-mirror.com/sentence-transformers/multi-qa-MiniLM-L6-cos-v1/resolve/main"
for f in config.json config_sentence_transformers.json modules.json \
         sentence_bert_config.json special_tokens_map.json tokenizer.json \
         tokenizer_config.json vocab.txt model.safetensors; do
  curl -L -o "$f" "$BASE/$f"
done
curl -L -o 1_Pooling/config.json "$BASE/1_Pooling/config.json"
cd ../..
```

## Stack

- **Agent + judge LLM**: DeepSeek-V3 (cost + capability fit). Programmatic judging wherever possible; LLM-as-judge only as fallback.
- **Memory systems under test (current set)**: `no_memory` (floor), `naive_markdown` (verbatim shared list), `long_context` (verbatim list, no agent tags), `regex_markdown` (naive + explicit retirement-pattern deletion), `mem0` (industry-default OSS).
- **mem0 backend**: DeepSeek for its internal LLM, sentence-transformers (`multi-qa-MiniLM-L6-cos-v1`) for embeddings, qdrant in embedded mode.
- **Python**: 3.11+ required.

## Known limitations (v1 design)

- **Self-evaluation bias.** The DeepSeek agent and any LLM-judged subtask share the same model. Programmatic judging covers most of it.
- **Single LLM, single vendor.** Cross-vendor evaluation (Claude + GPT + Llama) is parking-lot.
- **Multi-agent is simulated.** Different writer agent_ids feed the same memory store; this captures the data-flow shape but not full agent autonomy (each agent receiving genuinely different raw context).

See [`docs/v1/README.md`](./docs/v1/README.md) for the active benchmark design.
