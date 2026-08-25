# Agent Memory Benchmark

A benchmark for evaluating LLM memory systems in **multi-agent shared-memory** scenarios.

## The question this exists to answer

In 2026, MCP, A2A, and shared-memory products are pushing toward a world where **multiple LLM agents (Claude, ChatGPT, Codex, custom agents) work off the same memory layer**. Every major memory benchmark today (LongMemEval, LoCoMo, MemoryBank, HaluMem, GateMem) still assumes a single agent reads and writes its own memory.

This benchmark fills the gap: **when N agents share one memory store, do existing memory systems hold up?**

## What is measured

The project has three published evaluations. They answer different product
questions, so we report them separately rather than collapsing them into one
overall score.

| Track | Task | What it tests | Systems | Published result |
|---|---|---|---|---|
| Factual memory | **T4 — split intake** | Retaining many details written in one long statement | `no_memory`, `naive_markdown`, `pure_vector`, `AMH`, `mem0` | ✅ n=300 · [write-up](./docs/v1/t4_findings.md) |
| Factual memory | **T2 — compound update** | Applying several updates without changing unrelated facts | `no_memory`, `naive_markdown`, `pure_vector`, `AMH`, `mem0` | ✅ n=298 · [write-up](./docs/v1/t2_findings.md) |
| User preference | **Preference pilot** | Merging durable preferences, updates, temporary requests, and decisions | `naive_markdown`, `AMH`, `mem0` | ✅ n=30 pilot · [findings](./docs/v1/preference_pilot_n30_once_findings.md) |

T4 tests whether detailed factual information survives a multi-agent memory
pipeline. T2 tests multi-fact updates and collateral damage. The Preference
pilot tests whether stable preferences can be merged across agents, updated,
kept separate from temporary requirements, and used in a decision. See
[`docs/v1/`](./docs/v1/README.md) for the full task designs, scoring rules,
and limitations.

## Results at a glance

These are the latest published results, not a single leaderboard. Scores are
case-level averages; higher is better. `no_memory` is a factual-track floor,
not a competing memory product.

### T4 — split intake (n=300)

| System | Per-detail recall | Aggregate recall |
|---|---:|---:|
| `no_memory` | 0.000 | 0.000 |
| `naive_markdown` | **0.951** | **0.968** |
| `pure_vector` | **0.951** | **0.969** |
| `AMH` | **0.950** | **0.969** |
| `mem0` | 0.432 | 0.555 |

![T4 split-intake results](./docs/v1/t4_results.png)

T4's main finding is that the extraction-free baselines and AMH retain most
details in this short, single-write setting, while mem0 loses more details
during its write-time extraction and retrieval pipeline. See the
[full T4 analysis](./docs/v1/t4_findings.md) for confidence intervals and
failure examples.

### T2 — compound update (n=298; `pure_vector` n=99)

| System | Update recall | No confusion | No collateral |
|---|---:|---:|---:|
| `no_memory` | 0.000 | 1.000 | 0.000 |
| `naive_markdown` | **0.999** | **0.997** | 0.978 |
| `pure_vector` | 0.886 | 0.907 | **0.983** |
| `AMH` | 0.893 | 0.909 | 0.978 |
| `mem0` | 0.976 | 0.981 | 0.961 |

T2 shows a different pattern from T4: after fixing per-case mem0 isolation,
mem0 applies explicit multi-fact updates well and is substantially ahead of
AMH on update recall, while the verbatim markdown baseline remains strongest.
The [T2 analysis](./docs/v1/t2_findings.md) documents the judge correction,
the two excluded no-op cases, and the isolation fix.

### Preference pilot (n=30, one run)

| System | Overall | Single-item | Composite decision |
|---|---:|---:|---:|
| `naive_markdown` | **30/30** | 12/12 | 18/18 |
| `mem0` | **30/30** | 12/12 | 18/18 |
| `AMH` | 28/30 | 11/12 | 17/18 |

The preference result is a small pilot, not a definitive ranking. It is
included because preference memory is a product-relevant scenario where a
system must distinguish durable preferences from temporary requirements.
Read the [pilot findings](./docs/v1/preference_pilot_n30_once_findings.md)
for the case design and failure analysis.

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
  results/             # published production results + ignored local runs
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
pip install -r requirements.txt

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
- **Factual-track systems**: `no_memory`, `naive_markdown`, `pure_vector`, `AMH`, and `mem0`.
- **Preference-track systems**: `naive_markdown`, `AMH`, and `mem0`. `no_memory` and `pure_vector` are intentionally not part of this product comparison.
- **mem0 backend**: DeepSeek for its internal LLM, sentence-transformers (`multi-qa-MiniLM-L6-cos-v1`) for embeddings, qdrant in embedded mode.
- **Python**: 3.11+ required.

## Known limitations (v1 design)

- **Self-evaluation bias.** The DeepSeek agent and any LLM-judged subtask share the same model. Programmatic judging covers most of it.
- **Single LLM, single vendor.** Cross-vendor evaluation (Claude + GPT + Llama) is parking-lot.
- **Multi-agent is simulated.** Different writer agent IDs feed the same memory store; this captures cross-agent write/read flow, not autonomous agents with independent planning.
- **Preference pilot size.** The n=30 run is useful for validating the benchmark and exposing failure cases, but it is not large enough for a definitive market ranking.

See [`docs/v1/README.md`](./docs/v1/README.md) for the active benchmark design.
