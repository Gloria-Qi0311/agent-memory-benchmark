# Project Plan

The full picture of this project — what we're building, why, and how. README is the public face; this is the working document.

For frozen design decisions: see `decisions.md`. For the short to-do list: see `roadmap.md`.

---

## 1. What we're building

A benchmark that measures how well existing LLM memory systems handle **multi-agent shared-memory** scenarios — multiple AI agents reading and writing to the same memory store, with a third agent later needing to use what the first two wrote.

The deliverable is not just a script. It's three things together:

1. **A reusable evaluation harness** — feed in any memory system, get back comparable scores.
2. **A first set of results** — head-to-head numbers on three reference systems.
3. **A sharp finding** — one sentence a reader can repeat back. The current candidate: *"the most-funded open-source memory system trails a 30-line baseline on multi-agent fusion."*

The artifact lives on GitHub. The finding lives in a writeup. Both are part of the product.

---

## 2. Why this exists

I use several AI agents day to day — Claude, ChatGPT, Codex, Cursor, custom ones — and I keep running into the same pattern: each one has its own memory, none of them share, and when I switch tools I have to re-explain everything. The problem gets worse as more products start sharing memory across agents (Claude Code memory, ChatGPT memory, Mem0, AMH-style memory hubs), because nobody really knows whether these shared-memory systems hold up under multi-agent use.

When I went looking for benchmarks that measure this, I couldn't find one. Existing memory benchmarks all assume a single agent:

| Benchmark | What it tests | What it doesn't |
|---|---|---|
| LongMemEval (ICLR 2025) | Long-term memory across many sessions of a single chat | Single agent only |
| LoCoMo | Long conversation coherence | Single agent only |
| HaluMem | Operation-level hallucination in memory pipelines | Single agent only |
| GateMem | Access control when *one* agent serves *multiple human users* | The reverse — multiple AI agents, one user |

This benchmark targets the gap GateMem leaves open: **one user, many AI agents, shared memory.**

---

## 3. The plan

Three milestones. Each one is independently shippable — if work stops between any two of them, what exists is still presentable.

### Milestone 1 — Skeleton + first signal (✅ DONE, 2026-06-28)
**Goal:** prove the experimental setup runs end to end and produces sensible numbers.

- Three system adapters: `no_memory` (floor), `naive_markdown` (ceiling), `mem0` (representative real system)
- Fusion task generator (programmatic, deterministic by seed)
- Programmatic judge (fact-list substring matching)
- 5 cases × 3 systems on DeepSeek-V3 → 0.00 / 1.00 / 0.95
- Public GitHub repo

### Milestone 2 — Real result + first plot (in progress)
**Goal:** turn the n=5 signal into something quotable and defensible.

- Scale fusion to **n=100** cases
- Read 5–10 failure cases by hand — look for the qualitative story behind the 5% gap
- Add **rewrite-preservation** as a second task (auxiliary signal: when an update lands, what fraction of unrelated facts survive)
- First matplotlib chart: bar chart of mean recall with error bars
- Decide whether the finding holds, evolves, or collapses

### Milestone 3 — Public artifact
**Goal:** something a reader can find, read, and react to in 60 seconds.

- README rewritten as a narrative (finding → method → implication)
- One blog post / LinkedIn post with the headline finding + chart
- A 4th system added (Letta or mem0 Platform — whichever is faster to integrate; broadens the comparison from "mem0 vs naive" to "OSS memory category vs naive")
- Optional: Streamlit dashboard (defer if time runs short — README + plot is the must-have)

---

## 4. How it's implemented

### One case, end to end

A **case** is a self-contained mini-scenario. Each case has:
- A persona (random name).
- 4 facts about that persona, split 2-and-2 between two writer agents (A and B).
- A probe question that requires *all four* facts to answer correctly.
- A ground-truth fact list for scoring.

The runner does the same thing for every (case, system) pair:

```
system.reset()
for each fact in case.facts_a:  system.write("agent_a", fact)
for each fact in case.facts_b:  system.write("agent_b", fact)
context = system.read("agent_c", case.probe_question)
answer  = DeepSeek(system_prompt, f"Memory:\n{context}\n\nQ: {case.probe_question}")
score   = fraction_of_ground_truth_substrings_in(answer)
```

Three properties make this multi-agent rather than single-agent:
- Writes are tagged with `agent_id` (systems that support provenance can use it).
- The reader is a third agent (`agent_c`), never echoing its own writes.
- The probe requires both halves, so single-side recall is 0.5 not 1.0.

### Why this design

| Decision | Alternative | Why this one |
|---|---|---|
| Programmatic substring judge | LLM-as-judge | Free, deterministic, no self-eval bias. Trades expressiveness for trustworthiness. |
| Same LLM (DeepSeek) for agent and any LLM-y bits | Stronger judge model | Cost. Self-eval bias is real but partially mitigated by programmatic judging. |
| Test 3 systems, not 7 | Comprehensive comparison | A clean 3-way story (floor / industry / ceiling) is more legible than a 7-way table that nobody reads. |
| Local embedding model (`models/`) | HuggingFace runtime download | This machine's Python 3.9 + LibreSSL stack breaks HF library downloads. Sidestepping the loader is the simplest fix. (Even after Python 3.11, keeping the local copy makes the project hermetic.) |
| Fusion as the main task | Conflict resolution / rewrite as the main task | Fusion is the cleanest test of "do multiple writers' contributions reach a third reader" — the core question. Rewrite is supplementary. |

### Anti-goals (things this project intentionally does NOT do)

- Train models, fine-tune anything, or evaluate the LLM itself.
- Build a memory system. (We benchmark existing ones.)
- Test cross-LLM-vendor compositions (Claude writes, GPT reads). Interesting, but doubles the cost and complexity for incremental insight.
- Test single-agent long-term memory. LongMemEval already does that better than we could.
- Privacy / leakage testing. GateMem does that better.

---

## 5. Risks and what we'll do about them

| Risk | How likely | What we'll do |
|---|---|---|
| The 5% gap evaporates at n=100 (just noise). | Medium. With recall clustered near 1.0, 5% might be sampling noise. | At n=100, also report a binary metric ("did this system miss ANY fact in this case") — more robust at the ceiling. |
| Self-eval bias inflates one or more systems. | Medium-low (judge is programmatic, not LLM-based). | Document the bias in README. Optionally re-judge 50 cases with a different model before publishing the result. |
| The fusion task is too easy. | Medium. naive_markdown hits 1.0 — there may be no headroom for differences to show. | Make it harder: more facts per persona, more filler sessions between writes, ambiguous probe phrasing. |
| The benchmark gets dismissed as "the author handpicked tasks that favor naive baselines." | Low-medium. Real but mitigable. | Be transparent: case generator is programmatic and seeded; anyone can rerun. Also add the rewrite task, which doesn't a-priori favor either type of system. |
| Time runs out before Milestone 3. | High (everything always takes longer than planned). | Milestone 2 is already presentable on its own. Milestone 3's blog post amplifies, but the repo + result + chart alone stands. |

---

## 6. What "done" looks like

Three pieces all exist and are linked together:

1. **GitHub repo** — code, results, READMEs, anyone can reproduce.
2. **A chart** — one image that says the finding without text.
3. **A writeup** — 500-word blog post with the chart and the one-sentence takeaway, written for someone who uses AI tools daily.

When all three are public and someone could find them from a search of the project title in under 30 seconds, this project is done.
