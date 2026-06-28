# Agent Memory Benchmark

A benchmark for evaluating LLM memory systems in **multi-agent shared-memory** scenarios.

> **Preliminary signal (n=5, fusion task):** at this scale, both `naive_markdown` (1.00 recall) and `mem0` (1.00 recall) saturate; only the `no_memory` floor (0.00) separates from them. An earlier 5-point gap between mem0 and naive_markdown turned out to be an artifact of short fact tokens colliding with common English (`Go`, `Render`) in substring matching — fixed in commit `<TBD>`. **n=5 is too small to claim a real finding; scaling to n=100 with harder probes is next.**

## The question this benchmark exists to answer

In 2026, MCP, A2A, and shared-memory products are pushing toward a world where **multiple LLM agents (Claude, ChatGPT, Codex, custom agents) work off the same memory layer**. Every major memory benchmark today (LongMemEval, LoCoMo, MemoryBank, HaluMem) still assumes a single agent reads and writes its own memory.

This benchmark fills the gap: **when N agents share one memory store, do existing memory systems still work?**

## Result so far

| System | Mean recall (n=5) | What it is |
|---|---|---|
| `no_memory` | **0.00** | Floor baseline — agent has no context |
| `mem0` | **1.00** | Industry-default OSS memory system (40k+ stars), configured with DeepSeek LLM + sentence-transformers embeddings + qdrant |
| `naive_markdown` | **1.00** | Ceiling baseline — 30 lines of code, every agent appends to one in-memory list |

Each case follows the same shape: Agent A writes half the facts about a persona, Agent B writes the other half, Agent C must answer a question that requires both halves. Scoring is programmatic substring matching against a ground-truth fact list.

## How one case flows through the system

```
        ┌────────────────┐
        │  case JSON     │  persona, facts_a, facts_b,
        │  (generated)   │  probe question, ground truth
        └───────┬────────┘
                │
   for each fact in facts_a:
   ──► memory.write("agent_a", text)
   for each fact in facts_b:
   ──► memory.write("agent_b", text)
                │
        context = memory.read("agent_c", probe_question)
                │
        ┌───────▼────────┐
        │  DeepSeek-V3   │  context + question → answer
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │  judge.py      │  count ground-truth substrings in answer
        └───────┬────────┘
                │
              recall ∈ [0, 1]
```

Three things make this multi-agent rather than single-agent:
1. **Writes are tagged** with `agent_id`, so systems that support per-agent provenance can use it.
2. **The reader is a third agent** (`agent_c`), not one of the writers — no agent ever sees its own writes echoed back.
3. **The probe question requires both halves**, so single-side recall scores 0.5 not 1.0.

## Stack

- **Agent and judge LLM**: DeepSeek-V3 (chosen for cost + capability). Single-LLM evaluation introduces a known self-evaluation bias for any LLM-based judging — partially mitigated by using programmatic judging wherever feasible.
- **Judge**: programmatic substring matching against ground-truth fact lists.
- **mem0 backend**: DeepSeek for internal LLM, sentence-transformers (`multi-qa-MiniLM-L6-cos-v1`) for embeddings, qdrant in embedded mode.
- **Python**: 3.11+ required (mem0 2.0 uses PEP 604 syntax; system 3.9 also has SSL issues on macOS).

## Setup

```bash
# 1. Python 3.11+ (system 3.9 will not work; install via brew on macOS)
brew install python@3.11

# 2. Clone and virtualenv
git clone https://github.com/Gloria-Qi0311/agent-memory-benchmark.git
cd agent-memory-benchmark
python3.11 -m venv .venv && source .venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt sentence-transformers

# 4. DeepSeek key
cp .env.example .env
# put your DEEPSEEK_API_KEY in .env

# 5. Embedding model (manual download — see docs/decisions.md for the why)
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

# 6. Run
python scripts/generate_cases.py --task fusion --n 5
python scripts/run_experiment.py \
  --cases data/cases/fusion_n5_s0.json \
  --systems no_memory naive_markdown mem0
```

## Repo layout

```
src/
  agent.py             # DeepSeek wrapper
  judge.py             # programmatic scoring
  runner.py            # orchestrates write → read → judge per case
  storage.py
  systems/             # memory system adapters (one file per system)
  cases/               # task / case generators
scripts/               # CLI entrypoints
data/
  cases/               # generated case JSONs (committed for reproducibility)
  results/             # experiment outputs (git-ignored)
docs/
  decisions.md         # frozen design choices + setup gotchas
  roadmap.md           # done / now / next
models/                # locally-vendored embedding model (git-ignored)
```

## Known limitations

- **Self-evaluation bias.** Agent and judge share the same model (DeepSeek). Programmatic judging covers most of this, but any future LLM-as-judge augmentation will need cross-model validation.
- **Single LLM, single-vendor.** Cross-vendor evaluation (Claude writes, GPT reads) is in the parking lot — see `docs/roadmap.md`.
- **n=5 is a smoke test, not a publishable number.** At this scale `mem0` and `naive_markdown` both saturate at 1.00. The first task version (with bare `Go` / `Render` as fact values and a substring judge) produced an artifactual 5-point gap; tightening both removed it. Real comparisons require harder probes and larger n.

## Status

Active. See `docs/roadmap.md` for what's next.
