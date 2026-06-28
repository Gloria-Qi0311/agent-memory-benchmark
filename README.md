# Agent Memory Benchmark

A benchmark for evaluating LLM memory systems in **multi-agent shared-memory** scenarios.

> **Preliminary finding (n=5, fusion task)**: on cross-agent fusion, the industry-default `mem0` (~0.95 recall) trails a naive shared-markdown baseline (~1.0 recall) — i.e., a 30-line baseline is competitive with a popular OSS memory system. `no_memory` floor is 0.0. Scaling to n=100 is the next step.

## Why this benchmark exists

In 2026, protocols like MCP and A2A are making it routine for multiple LLM agents (Claude, ChatGPT, Codex, custom agents) to share a single memory layer. But every major memory benchmark today — LongMemEval, LoCoMo, MemoryBank, HaluMem — assumes a single agent reading and writing its own memory.

This benchmark fills that gap: **when N agents share one memory store, do existing memory systems still work?**

## What it measures

| Capability | What we test | Why it matters |
|---|---|---|
| **Fusion** (main) | Agent A writes half the info, Agent B writes the other half, Agent C must use both | Tests whether memory survives cross-agent handoff |
| **Rewrite preservation** (auxiliary) | An update that should only affect fact #k — do the other N-1 facts survive? | Tests collateral damage of updates |

## Systems compared (v1)

- `no_memory` — floor baseline
- `naive_markdown` — 50-line shared markdown file, simplest possible "shared memory" implementation
- `mem0` — most popular OSS memory system

## Stack

- **Agent LLM**: DeepSeek-V3 (cheap, capable enough to expose memory-system differences)
- **Judge**: programmatic (fact-list matching) where possible; LLM-as-judge as fallback
- **Storage**: JSON + SQLite
- **Frontend**: Streamlit dashboard (v2)

## Known limitations

- Agent and judge are both DeepSeek, which introduces self-evaluation bias for LLM-judged subtasks. Programmatic judging is used wherever feasible to mitigate this.
- Multi-agent is simulated by running the same LLM with different system prompts. Cross-vendor (e.g., Claude + GPT) testing is out of scope for v1.

## Quick start

```bash
# 1. install deps
pip install -r requirements.txt

# 2. set API key
cp .env.example .env
# edit .env with your DEEPSEEK_API_KEY

# 3. generate cases
python scripts/generate_cases.py --task fusion --n 50

# 4. run experiment
python scripts/run_experiment.py --task fusion --systems no_memory naive_markdown
```

## Repo layout

```
src/
  agent.py             # DeepSeek wrapper
  judge.py             # scoring (programmatic + LLM)
  runner.py            # experiment orchestration
  storage.py           # results persistence
  systems/             # memory system adapters
    base.py            # abstract interface
    no_memory.py
    naive_markdown.py
    mem0_system.py
  cases/               # task / case generators
    fusion.py
    rewrite.py
scripts/               # CLI entrypoints
data/
  cases/               # generated case JSONs
  results/             # experiment runs
frontend/              # Streamlit dashboard (v2)
```

## Status

🚧 v0 — scaffolding only. No experiments run yet.
